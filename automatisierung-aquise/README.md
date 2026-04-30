# Akquise-Pipeline (First Look)

Lokale Python-Automatisierung für Akquise-Mails:
empfängt Exposés via IMAP-IDLE, extrahiert PDFs und Links,
klassifiziert sie, zieht die Objekt-Adresse raus und legt
alles strukturiert unter `…\001_AQUISE\Objekte\<Adresse>\` ab.

## Quick Start

```bash
# venv anlegen und aktivieren
python -m venv .venv
source .venv/Scripts/activate   # Windows / Bash

# Dependencies
python -m pip install -r requirements.txt

# .env anlegen (Werte siehe .env.example)
cp .env.example .env

# CLI-Hilfe
python main.py --help

# Tests
pytest
```

## Status

Aktuell **Schritt 1 (Setup)** abgeschlossen. Nächste Schritte siehe
`files/Implementierungsplan.md`.

## Dokumentation

- `files/Projektbeschreibung.md` — Scope, Tech-Stack, Architektur-Prinzipien
- `files/Implementierungsplan.md` — Schrittweise Umsetzung
- `CLAUDE.md` — Steuerung für Claude Code
- `DEVELOPMENT_GUIDELINES.md` — Code-Konventionen
- `docs/00_setup.md` — Setup-Anleitung
- `docs/m0X_*.md` — Pro-Modul-Doku

## Verzeichnisstruktur

```
.
├── main.py              # CLI-Entry-Point
├── config.py            # Zentrale Konfiguration
├── modules/             # Pipeline-Stages (m01–m08)
├── docs/                # Pro-Modul-Doku
├── tests/               # pytest-Tests
├── logs/                # Log-Files (rotiert)
└── data/                # SQLite-State + Temp-PDFs
```

## Lizenz / Nutzung

Privates Tool für Petrov Wohnen. Nicht zur Weitergabe gedacht.
