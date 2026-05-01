"""m02 — Email Parser.

Schlüsselt eine raw_mail (RFC 822 bytes) auf:
- PDF-Anhänge in `data/temp/{message_id}/` speichern
- Links aus text/plain und text/html Bodies extrahieren (dedupliziert)

Public API:
    parse(raw_mail) -> dict
    run(raw_mail) -> dict   (Pipeline-Konvention)

Output-Schema:
    {
        "message_id": str,
        "subject": str,
        "von": str,           # Absender-Email
        "anhaenge": list[Path],
        "links": list[str],
    }
"""
from __future__ import annotations

import email
import email.header
import hashlib
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


def parse(raw_mail: bytes) -> dict:
    msg = email.message_from_bytes(raw_mail)

    message_id = _extract_message_id(msg, raw_mail)
    subject = _decode_header(msg.get("Subject", ""))
    von = _extract_from(msg)

    temp_dir = config.TEMP_DIR / _sanitize_for_path(message_id)
    anhaenge = _extract_pdf_attachments(msg, temp_dir)
    links = _extract_links(msg)
    body_plain = _extract_body_text(msg)

    log.info(
        "Mail geparst: id=%s, von=%s, %d Anhang/Anhänge, %d Link(s)",
        message_id,
        von,
        len(anhaenge),
        len(links),
    )

    return {
        "message_id": message_id,
        "subject": subject,
        "von": von,
        "anhaenge": anhaenge,
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
# Internals
# ---------------------------------------------------------------------------


def _extract_message_id(msg: Message, raw_mail: bytes) -> str:
    raw_id = (msg.get("Message-ID") or "").strip()
    if raw_id:
        return raw_id.strip("<>").strip()
    # Deterministischer Fallback, damit dieselbe Mail dieselbe ID bekommt
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
    # Fallback: manche Mailer schicken PDFs als octet-stream mit .pdf-Filename
    filename = _decode_header(part.get_filename() or "")
    return filename.lower().endswith(".pdf")


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
                # Sehr einfache HTML-Tag-Entfernung (kein vollständiges Parsing)
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
