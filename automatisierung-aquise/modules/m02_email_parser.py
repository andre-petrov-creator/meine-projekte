"""m02 — Email Parser.

Schlüsselt eine raw_mail (RFC 822 bytes) auf:
- PDF-Anhänge in `data/temp/{message_id}/` speichern
- Bild-Anhänge (jpg/png/heic/...) → EXIF-rotiert, auf 1568px skaliert, als JPG
- Inline-Bilder aus HTML-Body (cid:-References) analog
- Bild-PDFs (PDF ohne Text) → Seiten via PyMuPDF als JPG rendern
- Links aus text/plain und text/html Bodies extrahieren (dedupliziert)

Public API:
    parse(raw_mail) -> dict
    run(raw_mail) -> dict   (Pipeline-Konvention)

Output-Schema:
    {
        "message_id": str,
        "subject": str,
        "von": str,
        "anhaenge": list[Path],   # PDFs
        "bilder": list[Path],     # normalisierte JPGs (Anhänge + Inline + Bild-PDF-Seiten)
        "links": list[str],
        "body_plain": str,
    }
"""
from __future__ import annotations

import email
import email.header
import hashlib
import io
import re
from email.message import Message
from email.utils import parseaddr
from pathlib import Path

import config
from modules.m08_logger import get_logger

log = get_logger(__name__)

_URL_RE = re.compile(r"""https?://[^\s<>"'`\)\]]+""", re.IGNORECASE)
_TRAILING_PUNCT = ".,;:)]}>"
_FORBIDDEN_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_HTML_IMG_CID_RE = re.compile(r'<img[^>]+src=["\']cid:([^"\']+)["\']', re.IGNORECASE)

# HEIC/HEIF-Plugin bei Import registrieren (no-op wenn nicht installiert)
try:
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
except ImportError:
    log.debug("pillow-heif nicht installiert — HEIC/HEIF-Anhänge werden übersprungen.")


def parse(raw_mail: bytes) -> dict:
    msg = email.message_from_bytes(raw_mail)

    message_id = _extract_message_id(msg, raw_mail)
    subject = _decode_header(msg.get("Subject", ""))
    von = _extract_from(msg)

    temp_dir = config.TEMP_DIR / _sanitize_for_path(message_id)
    anhaenge = _extract_pdf_attachments(msg, temp_dir)
    bilder = _extract_image_attachments(msg, temp_dir)
    bilder.extend(_extract_inline_images(msg, temp_dir))
    bilder.extend(_render_image_pdfs(anhaenge, temp_dir))
    links = _extract_links(msg)
    body_plain = _extract_body_text(msg)

    log.info(
        "Mail geparst: id=%s, von=%s, %d PDFs, %d Bilder, %d Link(s)",
        message_id,
        von,
        len(anhaenge),
        len(bilder),
        len(links),
    )

    return {
        "message_id": message_id,
        "subject": subject,
        "von": von,
        "anhaenge": anhaenge,
        "bilder": bilder,
        "links": links,
        "body_plain": body_plain,
    }


def run(raw_mail: bytes | None = None) -> dict:
    """Pipeline-Konvention."""
    if raw_mail is None:
        raise ValueError("raw_mail ist Pflicht für m02_email_parser.run()")
    return parse(raw_mail)


def temp_dir_for(message_id: str) -> Path:
    """Konsistenter Temp-Pfad für eine Mail. m03 nutzt den, damit alle
    PDFs einer Mail (Anhänge + heruntergeladene) im selben Ordner landen."""
    return config.TEMP_DIR / _sanitize_for_path(message_id)


# ---------------------------------------------------------------------------
# Internals — Mail-Struktur
# ---------------------------------------------------------------------------


def _extract_message_id(msg: Message, raw_mail: bytes) -> str:
    raw_id = (msg.get("Message-ID") or "").strip()
    if raw_id:
        return raw_id.strip("<>").strip()
    digest = hashlib.sha256(raw_mail).hexdigest()[:16]
    return f"no-id-{digest}"


def _decode_header(value: str) -> str:
    if not value:
        return ""
    parts = email.header.decode_header(value)
    out: list[str] = []
    for text, charset in parts:
        if isinstance(text, bytes):
            try:
                out.append(text.decode(charset or "utf-8", errors="replace"))
            except (LookupError, TypeError):
                out.append(text.decode("utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _extract_from(msg: Message) -> str:
    raw = _decode_header(msg.get("From", ""))
    _, addr = parseaddr(raw)
    return (addr or raw).lower()


def _sanitize_for_path(value: str) -> str:
    cleaned = _FORBIDDEN_PATH_CHARS.sub("_", value).strip(" .")
    return cleaned or "unbekannt"


# ---------------------------------------------------------------------------
# Internals — PDF-Anhänge
# ---------------------------------------------------------------------------


def _extract_pdf_attachments(msg: Message, target_dir: Path) -> list[Path]:
    saved: list[Path] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        if not _looks_like_pdf(part):
            continue

        payload = part.get_payload(decode=True)
        if not payload:
            continue

        filename = _decode_header(part.get_filename() or "")
        if not filename:
            filename = f"unnamed_{len(saved) + 1}.pdf"
        filename = _sanitize_for_path(filename)
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        target_dir.mkdir(parents=True, exist_ok=True)
        target = _unique_path(target_dir / filename)
        target.write_bytes(payload)
        saved.append(target)
        log.debug("PDF-Anhang gespeichert: %s (%d Bytes)", target, len(payload))
    return saved


def _looks_like_pdf(part: Message) -> bool:
    ctype = (part.get_content_type() or "").lower()
    if ctype == "application/pdf":
        return True
    filename = _decode_header(part.get_filename() or "")
    return filename.lower().endswith(".pdf")


# ---------------------------------------------------------------------------
# Internals — Bild-Anhänge
# ---------------------------------------------------------------------------


def _extract_image_attachments(msg: Message, target_dir: Path) -> list[Path]:
    saved: list[Path] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        if not _looks_like_image(part):
            continue

        payload = part.get_payload(decode=True)
        if not payload:
            continue

        filename = _decode_header(part.get_filename() or "") or f"inline_image_{len(saved) + 1}"
        normalized = _normalize_image_payload(payload, filename, target_dir, prefix="img")
        if normalized is not None:
            saved.append(normalized)
    return saved


def _looks_like_image(part: Message) -> bool:
    ctype = (part.get_content_type() or "").lower()
    if ctype.startswith("image/"):
        return True
    filename = _decode_header(part.get_filename() or "")
    return filename.lower().endswith(config.IMAGE_EXTENSIONS)


def _extract_inline_images(msg: Message, target_dir: Path) -> list[Path]:
    """HTML-Body kann <img src='cid:xxx'> enthalten (multipart/related). Diese cid-Bilder
    extrahieren — separat von normalen Anhängen, damit wir Inline-Logos nicht doppelt nehmen.

    Heuristik: Sammle alle cids aus HTML-Body, dann finde die zugehörigen multipart-Parts
    via Content-ID-Header. Werden bereits über _extract_image_attachments gefunden? Ja, wenn
    sie als image/* Part vorliegen — dort werden sie aufgenommen. Diese Funktion ist daher
    nur für Edge-Cases, wo Mail-Clients Inline-Bilder als application/octet-stream packen.
    """
    referenced_cids = _collect_html_cids(msg)
    if not referenced_cids:
        return []

    saved: list[Path] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        cid = (part.get("Content-ID") or "").strip("<>").strip()
        if not cid or cid not in referenced_cids:
            continue
        # Schon als image/* gespeichert? Dann skip — _extract_image_attachments hat das.
        if _looks_like_image(part):
            continue
        # Octet-Stream mit Bild-Filename
        filename = _decode_header(part.get_filename() or "")
        if not filename.lower().endswith(config.IMAGE_EXTENSIONS):
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        normalized = _normalize_image_payload(
            payload, filename, target_dir, prefix=f"inline_{cid}"
        )
        if normalized is not None:
            saved.append(normalized)
    return saved


def _collect_html_cids(msg: Message) -> set[str]:
    cids: set[str] = set()
    for part in msg.walk():
        if part.is_multipart():
            continue
        if part.get_content_type() != "text/html":
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            html = payload.decode(charset, errors="replace")
        except (LookupError, TypeError):
            html = payload.decode("utf-8", errors="replace")
        cids.update(m.group(1) for m in _HTML_IMG_CID_RE.finditer(html))
    return cids


def _normalize_image_payload(
    payload: bytes,
    original_filename: str,
    target_dir: Path,
    prefix: str = "img",
) -> Path | None:
    """Liest Bild via Pillow, EXIF-rotiert, skaliert auf max. IMAGE_MAX_DIMENSION,
    speichert als JPG. Gibt None zurück, wenn Datei nicht lesbar."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        log.error("Pillow nicht installiert — Bild übersprungen: %s", original_filename)
        return None

    try:
        with Image.open(io.BytesIO(payload)) as img:
            img.load()
            img = ImageOps.exif_transpose(img)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            longest = max(img.size)
            if longest > config.IMAGE_MAX_DIMENSION:
                scale = config.IMAGE_MAX_DIMENSION / longest
                new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
                img = img.resize(new_size, Image.LANCZOS)

            target_dir.mkdir(parents=True, exist_ok=True)
            stem = Path(_sanitize_for_path(original_filename)).stem or prefix
            target = _unique_path(target_dir / f"{stem}.jpg")
            img.save(target, format="JPEG", quality=config.IMAGE_JPG_QUALITY, optimize=True)
            log.debug(
                "Bild normalisiert: %s → %s (%dx%d)",
                original_filename,
                target.name,
                img.size[0],
                img.size[1],
            )
            return target
    except Exception:
        log.exception("Bild konnte nicht gelesen/normalisiert werden: %s", original_filename)
        return None


# ---------------------------------------------------------------------------
# Internals — Bild-PDFs (gescannte Exposés)
# ---------------------------------------------------------------------------


def _render_image_pdfs(pdf_paths: list[Path], target_dir: Path) -> list[Path]:
    """Für jedes PDF prüfen ob Text drin ist. Wenn nein → erste N Seiten als JPG rendern.
    Gibt die JPG-Pfade zurück (PDF bleibt zusätzlich erhalten als Original-Anhang)."""
    rendered: list[Path] = []
    for pdf_path in pdf_paths:
        if _pdf_has_text(pdf_path):
            continue
        rendered.extend(_render_pdf_pages_to_jpg(pdf_path, target_dir))
    return rendered


def _pdf_has_text(pdf_path: Path) -> bool:
    """True wenn das PDF >= PDF_TEXT_MIN_CHARS Text enthält."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        total = 0
        for page in reader.pages:
            total += len(page.extract_text() or "")
            if total >= config.PDF_TEXT_MIN_CHARS:
                return True
        return False
    except Exception:
        log.warning("PDF-Text-Probe fehlgeschlagen — behandle als Bild-PDF: %s", pdf_path.name)
        return False


def _render_pdf_pages_to_jpg(pdf_path: Path, target_dir: Path) -> list[Path]:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        log.error("PyMuPDF nicht installiert — Bild-PDF wird nicht gerendert: %s", pdf_path.name)
        return []

    saved: list[Path] = []
    try:
        doc = fitz.open(str(pdf_path))
    except Exception:
        log.exception("Bild-PDF konnte nicht geöffnet werden: %s", pdf_path.name)
        return []

    try:
        max_pages = min(len(doc), config.PDF_RENDER_MAX_PAGES)
        zoom = config.PDF_RENDER_DPI / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        for page_idx in range(max_pages):
            page = doc.load_page(page_idx)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            png_bytes = pix.tobytes("png")
            normalized = _normalize_image_payload(
                png_bytes,
                f"{pdf_path.stem}_page{page_idx + 1}.png",
                target_dir,
                prefix=f"{pdf_path.stem}_page{page_idx + 1}",
            )
            if normalized is not None:
                saved.append(normalized)
        log.info(
            "Bild-PDF gerendert: %s → %d Seite(n) als JPG", pdf_path.name, len(saved)
        )
    finally:
        doc.close()
    return saved


# ---------------------------------------------------------------------------
# Internals — Body + Links
# ---------------------------------------------------------------------------


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _extract_body_text(msg: Message, max_len: int = 8000) -> str:
    """Liefert den Plain-Text-Body (Fallback HTML, von Tags bereinigt)."""
    for part in msg.walk():
        if part.is_multipart():
            continue
        if part.get_content_type() == "text/plain":
            payload = part.get_payload(decode=True)
            if payload:
                charset = part.get_content_charset() or "utf-8"
                try:
                    return payload.decode(charset, errors="replace")[:max_len]
                except (LookupError, TypeError):
                    return payload.decode("utf-8", errors="replace")[:max_len]
    for part in msg.walk():
        if part.is_multipart():
            continue
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            if payload:
                charset = part.get_content_charset() or "utf-8"
                try:
                    html = payload.decode(charset, errors="replace")
                except (LookupError, TypeError):
                    html = payload.decode("utf-8", errors="replace")
                text = re.sub(r"<[^>]+>", " ", html)
                text = re.sub(r"\s+", " ", text)
                return text[:max_len]
    return ""


def _extract_links(msg: Message) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = (part.get_content_type() or "").lower()
        if not ctype.startswith("text/"):
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            text = payload.decode(charset, errors="replace")
        except (LookupError, TypeError):
            text = payload.decode("utf-8", errors="replace")
        for match in _URL_RE.finditer(text):
            url = match.group(0).rstrip(_TRAILING_PUNCT)
            if url and url not in seen:
                seen.add(url)
                ordered.append(url)
    # Substring-Dedup: Plain-Text-Bodies brechen lange URLs am Zeilenende ab,
    # die ungekürzte Variante steht meist parallel im HTML-Body. Behalte die längere.
    return [u for u in ordered if not any(o != u and o.startswith(u) for o in ordered)]
