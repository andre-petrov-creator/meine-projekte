"""m03 — Link Resolver.

URLs → lokale PDF-Pfade.

Strategie:
1. HEAD-Request prüft Content-Type.
2. application/pdf → direkter GET, Stream zu File.
3. text/html → optionaler Webseiten-Renderer (Container-Skill).
4. Fehler/404/Timeout → loggen, überspringen.

Webseiten-Renderer ist **pluggable** via `set_webpage_renderer()`.
Default: warnt und überspringt — der Container-Skill wird vom Aufrufer
oder einem späteren Bootstrap-Schritt registriert.

Public API:
    resolve(urls, target_dir=None) -> list[Path]
    run(urls, target_dir=None) -> list[Path]
    set_webpage_renderer(callable)
"""
from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

import config
from modules.m08_logger import get_logger

log = get_logger(__name__)

# Type-Alias: (url, target_dir) -> Liste der gerenderten/heruntergeladenen PDFs
# Leere Liste bei Misserfolg (z. B. Token abgelaufen, Server-Fehler).
WebpageRenderer = Callable[[str, Path], list[Path]]

_HEAD_TIMEOUT = 10
_GET_TIMEOUT = 60
_FORBIDDEN_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_USER_AGENT = "Mozilla/5.0 (akquise-pipeline)"


def _default_webpage_renderer(url: str, target_dir: Path) -> list[Path]:
    log.warning(
        "Webseiten-Link kann nicht zu PDF gerendert werden — kein Renderer "
        "konfiguriert. URL: %s",
        url,
    )
    return []


_renderer: WebpageRenderer = _default_webpage_renderer


def set_webpage_renderer(renderer: WebpageRenderer | None) -> None:
    """Registriert einen Webseiten-zu-PDF-Renderer (Container-Skill o.ä.).

    Renderer-Signatur: (url: str, target_path: Path) -> Path | None
    Bei Erfolg: gibt den geschriebenen Pfad zurück (typischerweise == target_path).
    Bei Misserfolg: gibt None zurück, ohne zu raisen.
    """
    global _renderer
    _renderer = renderer or _default_webpage_renderer


def resolve(
    urls: list[str], target_dir: str | Path | None = None
) -> list[Path]:
    """Resolved eine Liste von URLs zu lokalen PDF-Pfaden.

    Pro URL können MEHRERE Pfade zurückkommen (z. B. wenn ein Webexposé sowohl
    Exposé als auch Mietmatrix liefert) — alle landen in der Output-Liste."""
    target = Path(target_dir) if target_dir is not None else config.TEMP_DIR
    target.mkdir(parents=True, exist_ok=True)

    resolved: list[Path] = []
    for url in urls:
        paths = _resolve_one(url, target)
        resolved.extend(paths)
    return resolved


def run(
    urls: list[str] | None = None, target_dir: str | Path | None = None
) -> list[Path]:
    """Pipeline-Konvention."""
    if urls is None:
        raise ValueError("urls ist Pflicht für m03_link_resolver.run()")
    return resolve(urls, target_dir)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _resolve_one(url: str, target_dir: Path) -> list[Path]:
    try:
        ctype = _probe_content_type(url)
    except requests.RequestException as exc:
        log.warning("HEAD fehlgeschlagen für %s: %s — versuche GET trotzdem.", url, exc)
        ctype = None

    if ctype and "application/pdf" in ctype:
        path = _download_pdf(url, target_dir)
        return [path] if path else []

    if ctype and ctype.startswith("text/html"):
        return _render_webpage(url, target_dir)

    # Unbekannter Content-Type oder HEAD nicht aussagekräftig:
    # erst GET probieren — vielleicht ist's doch ein PDF.
    pdf_path = _try_download_if_pdf(url, target_dir)
    if pdf_path is not None:
        return [pdf_path]

    # Kein PDF → letzter Versuch: rendern
    return _render_webpage(url, target_dir)


def _probe_content_type(url: str) -> str | None:
    response = requests.head(
        url,
        timeout=_HEAD_TIMEOUT,
        allow_redirects=True,
        headers={"User-Agent": _USER_AGENT},
    )
    response.raise_for_status()
    return response.headers.get("Content-Type", "").lower() or None


def _download_pdf(url: str, target_dir: Path) -> Path | None:
    try:
        response = requests.get(
            url,
            timeout=_GET_TIMEOUT,
            stream=True,
            allow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        log.warning("PDF-Download fehlgeschlagen für %s: %s", url, exc)
        return None

    target = _target_path_for(url, target_dir)
    with open(target, "wb") as fh:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if chunk:
                fh.write(chunk)
    log.info("PDF heruntergeladen: %s ← %s", target.name, url)
    return target


def _try_download_if_pdf(url: str, target_dir: Path) -> Path | None:
    """GET-Versuch, prüft erst Response-Header, lädt nur wenn PDF."""
    try:
        response = requests.get(
            url,
            timeout=_GET_TIMEOUT,
            stream=True,
            allow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        log.warning("GET fehlgeschlagen für %s: %s", url, exc)
        return None

    ctype = response.headers.get("Content-Type", "").lower()
    if "application/pdf" not in ctype:
        response.close()
        return None

    target = _target_path_for(url, target_dir)
    with open(target, "wb") as fh:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if chunk:
                fh.write(chunk)
    log.info("PDF heruntergeladen: %s ← %s", target.name, url)
    return target


def _render_webpage(url: str, target_dir: Path) -> list[Path]:
    try:
        results = _renderer(url, target_dir)
    except Exception:
        log.exception("Webseiten-Renderer wirft Exception für %s", url)
        return []
    if not results:
        return []
    valid = [p for p in results if p.exists()]
    if not valid:
        log.warning("Renderer meldet Erfolg, aber keine Dateien existieren: %s", url)
        return []
    log.info("Webseite gerendert: %d Datei(en) ← %s", len(valid), url[:80])
    return valid


def _target_path_for(url: str, target_dir: Path, suffix: str | None = None) -> Path:
    """Leitet einen sicheren Filename aus einer URL ab und vermeidet Kollisionen."""
    parsed = urlparse(url)
    last = unquote(parsed.path).rstrip("/").split("/")[-1] or parsed.netloc
    name = _FORBIDDEN_PATH_CHARS.sub("_", last).strip(" .") or "download"
    if suffix:
        if not name.lower().endswith(suffix.lower()):
            name = Path(name).stem + suffix
    elif not name.lower().endswith(".pdf"):
        name += ".pdf"

    candidate = target_dir / name
    if not candidate.exists():
        return candidate
    stem, ext = candidate.stem, candidate.suffix
    counter = 2
    while True:
        c = candidate.with_name(f"{stem}_{counter}{ext}")
        if not c.exists():
            return c
        counter += 1
