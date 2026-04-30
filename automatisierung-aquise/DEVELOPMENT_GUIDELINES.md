# Development Guidelines

## Sprache

- **Code (Variablen, Funktionen, Kommentare)**: Englisch
- **Logs, Exception-Messages, User-Output**: Deutsch
- **Doku-Files**: Deutsch

## Python-Konventionen

- Python 3.11+
- `snake_case` für Variablen, Funktionen, Module
- `PascalCase` für Klassen
- Type-Hints auf allen öffentlichen Funktionen
- `from __future__ import annotations` oben in jedem Modul

## File-Struktur

- Modul pro Datei. Eine Stage = eine Datei in `modules/`.
- Keine zirkulären Imports. Wenn du sie brauchst, ist die Architektur falsch.
- `__init__.py` bleibt leer oder enthält nur Re-Exports.

## Konfiguration

- Zentral in `config.py`.
- Secrets via `.env` (siehe `.env.example` für Schema).
- Pfade als `pathlib.Path`, nie als String konkatenieren.

## Logging

- Kein `print()` außer im CLI-Stub (`main.py`).
- Modul-spezifische Logger via `m08_logger.get_logger(__name__)`.
- Format: `[Zeitstempel] [Modul] [Level] Nachricht`.

## Fehlerbehandlung

- Fail-safe: Fehler in einer Stage → Mail-Status `error`, nicht erneut verarbeiten.
- Keine generischen `except Exception: pass`. Konkrete Exceptions abfangen, sonst loggen + re-raisen.
- Keine Fallbacks für unmögliche Fälle (Schein-Robustheit).

## Tests

- pytest, ein Test-File pro Modul (`tests/test_m0X_*.py`).
- Mock-Daten unter `tests/fixtures/` (Mails als `.eml`, PDFs als kleine Test-Files).
- Mindestens ein Smoke-Test pro Modul, dass es importierbar ist.

## Kommentare

- Nur wenn das WHY nicht offensichtlich ist (versteckte Constraint, Workaround, subtile Invariante).
- Kein WHAT — der Code spricht für sich.
- Keine "added for X"-Kommentare — gehört in den Commit.

## Git

- Push direkt auf main = OK für eigene Änderungen, wenn Akzeptanzkriterium erfüllt.
- Keine destruktiven Operationen ohne Bestätigung (`reset --hard`, `force-push`, `branch -D`).
- Hooks nicht umgehen (`--no-verify` etc.).

## Ordner-Hygiene

- `data/` und `logs/` sind Gitignore — niemals committen.
- `.env` niemals committen (auch nicht versehentlich via `git add .`).
- Kein Spaziergang durch fremde Module — nur lesen was du brauchst.
