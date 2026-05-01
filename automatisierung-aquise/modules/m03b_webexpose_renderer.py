"""m03b — Webexpose Renderer (Playwright/Chromium).

Öffnet Webexposé-URLs in einem echten Browser, zieht alle PDFs (Exposé,
Mietaufstellung, etc.) und macht zusätzlich einen Print-to-PDF der Seite.

Public API:
    render(url, target_dir) -> list[Path]
    set_full_mode(bool) — falls True: zusätzlich alle Galerie-Bilder
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse, unquote

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout, Download

from modules.m08_logger import get_logger

log = get_logger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)
_VIEWPORT = {"width": 1280, "height": 800}
_GOTO_TIMEOUT = 30000  # 30s
_RENDER_WAIT_MS = 4000  # 4s JS-Settling
_DOWNLOAD_TIMEOUT = 60000  # 60s pro Download
_FORBIDDEN_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def render(url: str, target_dir: str | Path) -> list[Path]:
    """Öffnet die URL im Browser, lädt PDFs herunter, gibt Liste lokaler PDF-Pfade zurück.

    Reihenfolge im Output:
    1. Direkt als PDF erkennbare Anhänge (<a download> oder href endet auf .pdf)
    2. Print-to-PDF der Webseite (Snapshot der gesamten Seite als Fallback)
    """
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(
                user_agent=_USER_AGENT,
                viewport=_VIEWPORT,
                accept_downloads=True,
            )
            page = ctx.new_page()

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=_GOTO_TIMEOUT)
                page.wait_for_timeout(_RENDER_WAIT_MS)
            except PWTimeout:
                log.warning("Webexposé-Goto-Timeout: %s", url)
                return saved

            title = page.title()
            log.info("Webexposé geladen: %s (Title=%s)", url[:80], title[:60])

            # Error-Page erkennen (Sparkassen-Fehlerseite)
            if title.strip().lower() in ("fehler", "error", ""):
                log.warning("Webexposé-Fehlerseite erkannt (Token abgelaufen?): %s", url)
                return saved

            pdfs = _download_pdf_links(page, target)
            saved.extend(pdfs)
            # Falls keine <a>-PDFs: Buttons mit "Download/herunterladen/Exposé" probieren
            if not pdfs:
                button_pdfs = _click_download_buttons(page, target)
                saved.extend(button_pdfs)
                pdfs = button_pdfs
            # Print-to-PDF nur als Fallback wenn weiterhin nichts gefunden wurde
            if not pdfs:
                log.info("Keine PDF-Links gefunden — Fallback: Print-to-PDF der Seite")
                snapshot = _print_to_pdf(page, target, title)
                if snapshot:
                    saved.append(snapshot)
        finally:
            browser.close()

    return saved


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _download_pdf_links(page, target: Path) -> list[Path]:
    """Findet alle <a>-Tags mit download-Attribut oder .pdf-Endung, klickt sie."""
    links = page.evaluate(
        """() => Array.from(document.querySelectorAll('a')).map(a => ({
            href: a.href,
            text: (a.innerText || a.textContent || '').trim().slice(0, 80),
            download: a.hasAttribute('download')
        }))"""
    )
    pdf_links = [
        l for l in links
        if l["download"] or l["href"].lower().endswith(".pdf") or "previewer" in l["href"].lower()
    ]
    log.info("Gefunden: %d PDF-/Download-Links auf Webexposé", len(pdf_links))

    saved: list[Path] = []
    for link in pdf_links:
        href = link["href"]
        text = link["text"] or "download"
        try:
            with page.expect_download(timeout=_DOWNLOAD_TIMEOUT) as dl_info:
                page.evaluate(f"""(() => {{
                    const a = Array.from(document.querySelectorAll('a')).find(x => x.href === {href!r});
                    if (a) a.click();
                }})()""")
            download: Download = dl_info.value
            suggested = download.suggested_filename or _filename_from_url(href)
            target_path = _unique(target / _sanitize(suggested))
            download.save_as(str(target_path))
            log.info("PDF heruntergeladen: %s (%s)", target_path.name, text[:40])
            saved.append(target_path)
        except PWTimeout:
            log.warning("Download-Timeout fuer %s (%s)", href[:80], text[:40])
        except Exception:
            log.exception("Download-Fehler fuer %s", href[:80])
    return saved


_DOWNLOAD_BUTTON_KEYWORDS = (
    "download", "herunterladen", "exposé", "expose", "exposé",
)


def _click_download_buttons(page, target: Path) -> list[Path]:
    """Findet Buttons/Links die nach 'Download' / 'Exposé' aussehen, klickt sie,
    fängt resultierende Downloads ab. Manche Plattformen (von Poll/onOffice)
    triggern PDF-Downloads via JS statt mit <a download>."""
    # Selector deckt klassische Buttons/Links UND custom-clickable divs (z. B.
    # von Poll: <div class="download-all" onclick=...>) ab. Match per Klasse,
    # onclick-Handler oder Tag.
    candidates = page.evaluate(
        """(keywords) => {
            const all = Array.from(document.querySelectorAll(
                'button, a, [role=button], [onclick], [class*="download"], [class*="herunterladen"]'
            ));
            // Eindeutige Reihenfolge erhalten
            const unique = Array.from(new Set(all));
            return unique
                .map((el, idx) => {
                    const text = (el.innerText || el.textContent || '').trim().toLowerCase();
                    return {idx, text: text.slice(0, 100), tag: el.tagName, cls: (el.className+'').slice(0, 80)};
                })
                .filter(o => o.text && keywords.some(k => o.text.includes(k.toLowerCase())));
        }""",
        list(_DOWNLOAD_BUTTON_KEYWORDS),
    )
    if not candidates:
        return []
    log.info("Download-Buttons gefunden: %d", len(candidates))

    saved: list[Path] = []
    for cand in candidates:
        idx = cand["idx"]
        text = cand["text"]
        try:
            with page.expect_download(timeout=_DOWNLOAD_TIMEOUT) as dl_info:
                page.evaluate(
                    """(idx) => {
                        const all = Array.from(document.querySelectorAll(
                            'button, a, [role=button], [onclick], [class*="download"], [class*="herunterladen"]'
                        ));
                        Array.from(new Set(all))[idx].click();
                    }""",
                    idx,
                )
            download: Download = dl_info.value
            suggested = download.suggested_filename or f"download_{len(saved) + 1}.pdf"
            target_path = _unique(target / _sanitize(suggested))
            download.save_as(str(target_path))
            log.info("PDF via Button heruntergeladen: %s (%s)", target_path.name, text[:40])
            saved.append(target_path)
        except PWTimeout:
            log.debug("Button '%s' triggerte keinen Download (kein PDF-Action)", text[:40])
        except Exception:
            log.exception("Klick auf Button '%s' fehlgeschlagen", text[:40])
    return saved


def _print_to_pdf(page, target: Path, title: str) -> Path | None:
    """Druckt die Webseite als PDF (Fallback / Snapshot)."""
    safe_title = _sanitize(title)[:60] or "webexpose_snapshot.pdf"
    target_path = _unique(target / safe_title)
    try:
        page.pdf(
            path=str(target_path),
            format="A4",
            margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"},
            print_background=True,
        )
        log.info("Print-to-PDF: %s (%d Bytes)", target_path.name, target_path.stat().st_size)
        return target_path
    except Exception:
        log.exception("Print-to-PDF fehlgeschlagen")
        return None


def _filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    last = unquote(parsed.path).rstrip("/").split("/")[-1]
    return last or "download.pdf"


def _sanitize(value: str) -> str:
    cleaned = _FORBIDDEN_PATH_CHARS.sub("_", value).strip(" .")
    if not cleaned.lower().endswith(".pdf"):
        cleaned += ".pdf"
    return cleaned or "unbekannt.pdf"


def _unique(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
