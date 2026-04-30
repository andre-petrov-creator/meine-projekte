# Projektbeschreibung: Akquise-Pipeline (First Look)

## Überblick

**Was**: Lokale Python-Automatisierung, die eingehende Akquise-Mails (Exposés von Maklern) automatisch verarbeitet, alle relevanten PDFs extrahiert/herunterlädt und in einer strukturierten Ordnerablage speichert.

**Für wen**: André Petrov, Petrov Wohnen. Nutzung im täglichen Akquise-Prozess für MFH ab 5 Einheiten in NRW/Ruhrgebiet.

**Warum**: Manuelles Sortieren, Herunterladen und Ablegen von Exposés kostet Zeit. Wenn pro Tag 5 bis 20 Exposés reinkommen, ist das 30 bis 60 Minuten Routinearbeit. Die Pipeline übernimmt das automatisch und legt eine saubere Ordnerstruktur pro Objekt an, auf der spätere Tools (CRM, Bewertungstools, Aufteiler-Skill) aufsetzen können.

## Scope MVP (Pipeline 1: First Look)

**Drin**:
- Trigger via IMAP-IDLE auf Gmail (Quasi-Push, kein Polling)
- Filter: nur Mails von andre-petrov@web.de
- Extraktion: PDF-Anhänge UND Links zu Exposé-PDFs/Webseiten
- Klassifikation der PDFs (Exposé, Mieterliste, Energieausweis, Modernisierung) per Filename-Heuristik
- Adress-Extraktion aus Exposé (Objekt-Adresse, NICHT Makler-Adresse)
- Ordnerablage unter festem Pfad mit Adresse als Ordnername
- Logging und Idempotenz (Mail nicht doppelt verarbeiten)

**Raus (später)**:
- CRM-Anbindung (Excel oder HTML, kommt nach CRM-Migration)
- Pipeline 2 "Vertiefung" (Bilder runterladen, Unterlagen-Unterordner, weitere Dokumente)
- Manuelle Triage "gefällt mir" → erst danach Vertiefung
- Echtzeit-Push via Pub/Sub (für Prototyp Overkill)

## Tech-Stack

- **Sprache**: Python 3.11+
- **Email-Empfang**: IMAP via `imapclient` mit IDLE-Modus (App-Passwort schon vorhanden)
- **PDF-Verarbeitung**: `pypdf` für Text-Extraktion
- **Web-Download**: bestehender Claude-Code Container-Skill (für Webseiten-Snapshots und Link-Downloads)
- **Adress-Extraktion**: Regex + Heuristik, fallback LLM-Call (Anthropic API) wenn Regex-Matches mehrdeutig sind
- **Ablage**: Lokales Dateisystem unter `C:\Users\andre\OneDrive - APPV Personalvermittlung\Immobilien\001_AQUISE\Objekte\`
- **State**: SQLite-Datei für verarbeitete Message-IDs (Idempotenz)
- **Logging**: Standard-Python `logging`, File-Rotation in `/logs`

## Architektur-Prinzipien

1. **Pipeline-Pattern**: Jedes Modul ist eine Stage mit klar definiertem Input und Output.
2. **Tauschbar**: Jede Stage ist eine eigene Datei, isolierte Funktion, austauschbar ohne Refactoring der anderen.
3. **Fail-safe**: Wenn eine Stage scheitert, wird die Mail in den Status "Fehler" markiert und nicht erneut verarbeitet, bis sie manuell freigegeben wird.
4. **Adress-First**: Die Adresse ist der Primärschlüssel des Systems. Ohne valide Adresse → Timestamp-Fallback-Ordner zur manuellen Nachsortierung.
5. **Lokales Setup**: Kein Cloud-Service, kein Server, läuft auf Andrés PC. Migration auf n8n/Cloud Function später möglich, weil modular.

## Ordnerstruktur Output

```
C:\...\001_AQUISE\Objekte\
├── Musterstr 12, 44137 Dortmund\
│   ├── Exposé.pdf
│   ├── Mieterliste.pdf
│   ├── Energieausweis.pdf
│   └── _meta.json   (Adresse, Quelle, Mail-ID, Timestamp)
├── 2026-04-30_14-22-15_unbekannt\   (Fallback wenn Adresse nicht extrahierbar)
│   ├── Exposé.pdf
│   └── _meta.json
└── ...
```

## Skill-Referenzen

Folgende Skills werden in den Claude-Code-Prompts referenziert:

- **claude-code-blueprint**: Workflow-Skill (Setup, Pro-Schritt-Pattern, Doku-Pflege)
- **humanizer**: nicht relevant für Code-Projekt
- **container-download** (eigener Claude-Code-Skill): Wiederverwendung für URL-zu-PDF-Konvertierung von Webseiten-Exposés

## Bekannte Risiken und Limitierungen

1. **Adress-Erkennung ist heikel**: Makler-Adressen, Stadtteil-Bezeichnungen ohne Hausnummer, mehrere Adressen im Exposé. Heuristik kann scheitern, deshalb Fallback-Ordner zwingend.
2. **Webseiten-Exposés ohne PDF-Download**: Manche Makler haben nur Web-Exposés. Container-Skill rendert die Seite zu PDF.
3. **IMAP-IDLE bricht ab**: Verbindung kann nach längerer Inaktivität abreißen. Reconnect-Logik mit Exponential-Backoff zwingend.
4. **PDF-Klassifikator unscharf**: Filename-Heuristik trifft nicht jeden Fall (Makler nennen Files unterschiedlich). Im MVP akzeptiert. Verbesserung in Pipeline 2 via LLM-Klassifikation.
5. **Doppelte Objekte**: Wenn dasselbe Objekt von zwei Maklern angeboten wird, entstehen zwei Ordner mit leicht unterschiedlicher Schreibweise. Im MVP akzeptiert, manuelles Mergen später.

## Konventionen

- **Sprache im Code**: Englisch (Variablen, Funktionen, Kommentare)
- **Sprache in Logs und User-Output**: Deutsch
- **Naming**: snake_case für Python
- **File-Struktur**: Modul pro Datei, klare Imports, keine zirkulären Abhängigkeiten
- **Konfiguration**: zentrale `config.py` mit allen Pfaden, Email-Filtern, API-Keys (via .env)
- **Tests**: pytest, mindestens ein Test pro Modul, Mock-Daten für Email und PDFs
