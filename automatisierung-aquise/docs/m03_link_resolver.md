# m03 — Link Resolver

## Zweck

URLs in lokale PDF-Pfade umwandeln. Direkter Download für `application/pdf`,
Webseiten-Rendering für `text/html` (via pluggable Renderer-Hook).

## Public API

| Funktion                          | Beschreibung |
|-----------------------------------|--------------|
| `resolve(urls, target_dir=None)`  | Hauptfunktion |
| `run(urls, target_dir=None)`      | Pipeline-Konvention (Alias) |
| `set_webpage_renderer(renderer)`  | Webseiten-zu-PDF-Renderer registrieren |

`target_dir` Default: `config.TEMP_DIR`. Aufrufer (typisch main.py)
übergibt das Mail-spezifische Temp-Verzeichnis.

## Verhalten

### Pro URL

1. **HEAD-Request** prüft `Content-Type`.
2. `application/pdf` → Streaming-GET, in `target_dir` speichern.
3. `text/html` → Webseiten-Renderer aufrufen.
4. Unbekannter / fehlender Content-Type → GET versuchen, Response-Header prüfen
   (manche Server lügen im HEAD).
5. Bei Fehler (4xx, 5xx, Timeout, Connection-Error) → loggen, **kein Crash**, weiter.

### Filename-Strategie

- Aus `URL-Path` letzter Segment-Name extrahiert.
- Pfad-gefährliche Zeichen (`<>:"/\\|?*`) → `_`.
- Kein `.pdf`-Suffix → wird angehängt.
- Doppelte Filenames im Target-Dir → `_2`, `_3`, …

### Timeouts

- HEAD: 10 Sekunden
- GET: 60 Sekunden

User-Agent: `Mozilla/5.0 (akquise-pipeline)` (manche Server blocken
default `python-requests/...`).

## Webseiten-Renderer

### Default

`_default_webpage_renderer` loggt eine Warnung und gibt `None` zurück —
HTML-Links werden also **übersprungen**, bis ein echter Renderer registriert ist.

### Renderer-Vertrag

```python
def my_renderer(url: str, target: Path) -> Path | None:
    # Schreibe ein PDF nach `target` und gib den Pfad zurück.
    # Bei Misserfolg: gib None zurück (nicht raisen).
    ...

from modules.m03_link_resolver import set_webpage_renderer
set_webpage_renderer(my_renderer)
```

### Container-Skill-Verdrahtung (offen)

Der bestehende Container-Download-Skill auf Andrés PC soll hier
eingehängt werden. Mögliche Varianten — finalisieren in Schritt 9 (main.py):

**(a)** CLI-Aufruf via `subprocess`:
```python
def container_renderer(url, target):
    subprocess.run(
        ["container-download", "--url", url, "--out", str(target)],
        check=True,
    )
    return target if target.exists() else None
```

**(b)** Selenium / Playwright als Fallback (wenn Container nicht erreichbar).

**(c)** Headless-Chrome via `chrome --headless --print-to-pdf=...`.

Welche Variante: **TBD** — Klärung beim Übergang zu Schritt 9.

## Beispiel

```python
from modules import m03_link_resolver as resolver

paths = resolver.resolve([
    "https://makler.de/objekt/expose.pdf",
    "https://makler.de/web-expose-12345",
], target_dir=Path("data/temp/abc-123"))
# → [Path("data/temp/abc-123/expose.pdf"), …]
```

## Status

✅ Implementiert (Schritt 5). 14 Tests in `tests/test_m03_link_resolver.py`.
Container-Skill-Verdrahtung **offen** — wird in Schritt 9 entschieden.
