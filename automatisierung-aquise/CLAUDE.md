# CLAUDE.md — Steuerung für Claude Code

## Lies zuerst (Pflicht)

Bevor du irgendetwas an diesem Projekt änderst, lies in dieser Reihenfolge:

1. `Projektbeschreibung.md` — Scope, Tech-Stack, Architektur-Prinzipien (liegt unter `files/`)
2. `Implementierungsplan.md` — Schrittweise Umsetzung, Modul-Verantwortlichkeiten (liegt unter `files/`)
3. `DEVELOPMENT_GUIDELINES.md` — Code-Konventionen
4. `docs/00_setup.md` — Setup-Anleitung
5. Modul-spezifische Doku unter `docs/m0X_*.md`, wenn du an einem Modul arbeitest

## Skill-Referenzen

Folgende Skills sind für dieses Projekt relevant:

- **claude-code-blueprint** — Workflow-Skill (Pro-Schritt-Pattern, Doku-Pflege)
- **container-download** — bestehender Skill für URL → PDF (Webseiten-Snapshots), genutzt in m03
- **systematic-debugging** — bei Bugs vor Fix-Versuch
- **test-driven-development** — vor neuer Implementierung
- **verification-before-completion** — bevor du "fertig" sagst

## Pro-Schritt-Workflow

Jeder Schritt aus `Implementierungsplan.md` läuft so:

1. **Sparring**: Offene Fragen klären (Schnittstellen, Edge Cases, Tests).
2. **Implementierung**: Modul + Tests + Doku.
3. **Akzeptanz prüfen**: Kriterium aus dem Plan erfüllt?
4. **Plan abhaken**: Schritt im `Implementierungsplan.md` mit `[x]` markieren.

Niemals einen Schritt überspringen, auch wenn er trivial wirkt.

## Architektur-Prinzipien (kurz)

- **Pipeline-Pattern**: Eine Stage pro Modul, klar definierte Schnittstelle.
- **Tauschbar**: Module sind isoliert, austauschbar ohne Refactoring der anderen.
- **Fail-safe**: Fehler → Mail-Status `error`, nicht erneut verarbeiten.
- **Adress-First**: Adresse = Primärschlüssel. Ohne valide Adresse → Timestamp-Fallback-Ordner.
- **Lokales Setup**: Kein Cloud-Service. Migration auf n8n/Cloud Function später möglich.

## Konventionen

- Code: Englisch (Variablen, Funktionen, Kommentare)
- Logs / User-Output: Deutsch
- Naming: `snake_case` (Python)
- Modul pro Datei, keine zirkulären Imports
- Konfiguration zentral in `config.py`, Secrets via `.env`
- Tests: pytest, mindestens ein Test pro Modul

## Was NICHT zu tun ist

- Keine Doku/READMEs ohne Auftrag erweitern.
- Keine Schein-Robustheit (Fallbacks für unmögliche Fälle).
- Keine destruktiven Operationen ohne Bestätigung.
- Keine `--no-verify`, keine Hooks umgehen.
- Schritt nicht überspringen, weil "klein".
