# Setup

## Voraussetzungen

- Python 3.11 oder neuer (aktuell getestet mit 3.14)
- Gmail-Account mit aktiviertem IMAP und einem App-Passwort
- Schreibzugriff auf den BASE_FOLDER (OneDrive-Pfad in `config.py`)

## Erstinstallation

```bash
# venv anlegen
python -m venv .venv

# venv aktivieren (Windows / Bash)
source .venv/Scripts/activate

# Dependencies installieren
python -m pip install -r requirements.txt

# .env aus Template erzeugen
cp .env.example .env
# Werte in .env eintragen
```

## Sanity-Checks

```bash
python main.py --help     # zeigt CLI-Hilfe
pytest                    # Tests laufen durch (auch wenn leer)
```

## Verzeichnisstruktur

- `modules/` — Pipeline-Module (m01–m08), je eine Stage pro Datei
- `docs/` — pro Modul ein Doku-File
- `tests/` — pytest-Tests pro Modul
- `logs/` — Log-Files mit Rotation
- `data/` — SQLite-State + temporäre PDF-Downloads

## Status

Schritt 1 abgeschlossen: Setup, Stubs, CLI-Hilfe.
Nächste Schritte siehe `Implementierungsplan.md`.
