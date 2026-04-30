# Implementierungsplan: Akquise-Pipeline (First Look)

## Inhaltsverzeichnis

### Module (finale Architektur)

```
akquise-prototyp/
├── CLAUDE.md                       # Steuerungsdatei für Claude Code
├── DEVELOPMENT_GUIDELINES.md       # Code-Konventionen
├── README.md                       # Projektzweck und Setup-Anleitung
├── .env.example                    # Vorlage für Secrets
├── config.py                       # Zentrale Konfiguration
├── main.py                         # Entry-Point, IMAP-IDLE-Loop
│
├── modules/
│   ├── __init__.py
│   ├── m01_email_listener.py       # IMAP-IDLE, neue Mails erkennen
│   ├── m02_email_parser.py         # Mail aufschlüsseln, Anhänge + Links extrahieren
│   ├── m03_link_resolver.py        # URL → PDF (via Container-Skill)
│   ├── m04_pdf_classifier.py       # PDF → Typ (Exposé, Miet, Energie, Modern)
│   ├── m05_address_extractor.py    # Exposé-PDF → Objekt-Adresse
│   ├── m06_folder_manager.py       # Ordner anlegen, Files ablegen
│   ├── m07_state_store.py          # SQLite, Idempotenz, Status-Tracking
│   └── m08_logger.py               # Logging-Setup
│
├── docs/                           # Pro Modul ein Doku-File (Pflicht!)
│   ├── m01_email_listener.md
│   ├── m02_email_parser.md
│   ├── ...
│
├── tests/
│   ├── test_m01_email_listener.py
│   ├── test_m02_email_parser.py
│   └── ...
│
├── logs/                           # Log-Files mit Rotation
│
└── data/
    └── state.db                    # SQLite-State
```

### Modul-Verantwortlichkeiten (Schnittstellen)

| Modul | Input | Output |
|-------|-------|--------|
| m01_email_listener | IMAP-Verbindung | Trigger-Event mit raw_mail |
| m02_email_parser | raw_mail | dict {anhaenge: [PDFs], links: [URLs]} |
| m03_link_resolver | URL | Pfad zu lokalem PDF |
| m04_pdf_classifier | PDF-Pfad | dict {typ, confidence} |
| m05_address_extractor | Exposé-PDF-Pfad | dict {adresse, confidence} oder None |
| m06_folder_manager | adresse, files-Liste, meta | Ordnerpfad, abgelegte Files |
| m07_state_store | message_id, status | bool (verarbeitet ja/nein) |
| m08_logger | log-Event | Logfile-Eintrag |

---

## Schrittweise Umsetzung

Jeder Schritt = ein eigener Chat im claude.ai-Projekt. Pro Schritt: Sparring-Phase, dann finaler Claude-Code-Prompt nach Pattern aus `claude-code-blueprint`.

### Schritt 1: Projekt-Setup

**Ziel**: Repo-Struktur, CLAUDE.md, DEVELOPMENT_GUIDELINES.md, README, leere Modul-Files mit Stubs, `.env.example`, `config.py`, virtuelle Umgebung, `requirements.txt`.

**Akzeptanzkriterium**:
- `python main.py --help` läuft (auch wenn Stub)
- Alle Module-Files existieren mit `def run(): pass` Stub
- `pytest` läuft durch (auch wenn keine Tests da sind)
- CLAUDE.md enthält "Lies zuerst"-Regel und Skill-Referenzen

**Betroffene Files**: alle aus dem Verzeichnis-Tree oben

**Doku**: `docs/00_setup.md` mit Setup-Anleitung

---

### Schritt 2: m08_logger + m07_state_store (Foundation)

**Ziel**: Logging und State-Persistierung stehen zuerst, weil alle anderen Module darauf aufsetzen.

**m08_logger**:
- Standard `logging` mit File-Handler und Console-Handler
- Rotation (max 10 MB pro File, 5 Backups)
- Format: `[Zeitstempel] [Modul] [Level] Nachricht`

**m07_state_store**:
- SQLite-DB unter `data/state.db`
- Tabelle `processed_mails`: `message_id`, `status`, `timestamp`, `error_msg`, `folder_path`
- Statuswerte: `pending`, `processing`, `done`, `error`
- Funktionen: `is_processed(message_id)`, `mark_processing(message_id)`, `mark_done(message_id, folder_path)`, `mark_error(message_id, error_msg)`

**Akzeptanzkriterium**:
- Logger schreibt in Console und File
- State-Store: idempotenter Test (gleiche message_id zweimal markieren → kein Crash)

**Doku**: `docs/m07_state_store.md`, `docs/m08_logger.md`

---

### Schritt 3: m01_email_listener (IMAP-IDLE)

**Ziel**: Permanent laufender IMAP-IDLE-Listener auf Gmail-Inbox, der bei neuer Mail von andre-petrov@web.de einen Callback triggert.

**Details**:
- `imapclient` Library
- IDLE-Modus mit Timeout (Reconnect alle 29 Minuten, weil Gmail nach 30 abbricht)
- Filter: `FROM andre-petrov@web.de UNSEEN`
- Bei neuer Mail: raw_mail laden, Callback aufrufen (nimmt raw_mail entgegen)
- Robust gegen Verbindungsabbrüche (exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s max)

**Akzeptanzkriterium**:
- Listener läuft 30 Minuten ohne Crash
- Test-Mail von andre-petrov@web.de wird erkannt und Callback wird mit raw_mail aufgerufen
- Verbindung bricht ab → reconnect ohne manuellen Eingriff

**Doku**: `docs/m01_email_listener.md`

---

### Schritt 4: m02_email_parser

**Ziel**: raw_mail aufschlüsseln, alle PDF-Anhänge extrahieren und in `data/temp/` speichern, alle Links im Body extrahieren.

**Details**:
- Standard `email`-Lib für MIME-Parsing
- PDF-Anhänge: `Content-Type: application/pdf` filtern, in `data/temp/{message_id}/` ablegen
- Links: Regex auf Plain-Text-Body und HTML-Body, Duplikate entfernen
- Output: `dict {anhaenge: [Pfade], links: [URLs], message_id, subject, von}`

**Akzeptanzkriterium**:
- Test-Mail mit 1 Anhang + 1 Link → korrektes dict
- Test-Mail mit nur Anhang → links = []
- Test-Mail mit nur Link → anhaenge = []

**Doku**: `docs/m02_email_parser.md`

---

### Schritt 5: m03_link_resolver (Container-Skill-Anbindung)

**Ziel**: URLs in PDFs umwandeln. Wiederverwendung des bestehenden Container-Skills.

**Details**:
- Input: Liste URLs
- Pro URL prüfen: ist es ein direkter PDF-Download? (HEAD-Request, Content-Type)
  - Ja → `requests.get`, Datei speichern
  - Nein (Webseite) → Container-Skill aufrufen, Webseite zu PDF rendern
- Output: Liste lokaler PDF-Pfade

**Akzeptanzkriterium**:
- Direkter PDF-Link → korrekt heruntergeladen
- Webseiten-Link → PDF-Snapshot erzeugt
- Fehler-Link (404) → geloggt, kein Crash

**Doku**: `docs/m03_link_resolver.md`

---

### Schritt 6: m04_pdf_classifier

**Ziel**: Pro PDF den Typ erkennen anhand des Filenames (Heuristik).

**Details**:
- Regelwerk:
  - `expose|exposé` im Filename → `expose`
  - `miet|mieterliste|mieterauflistung|mietmatrix` → `mieterliste`
  - `energie|energieausweis|epc` → `energieausweis`
  - `modern|sanierung|renovierung` → `modernisierung`
  - sonst → `sonstiges`
- Case-insensitive
- Wenn mehrere Matches: erstes gewinnt (Reihenfolge oben = Priorität)
- Output: `{typ, confidence}` (confidence 1.0 bei klarem Match, 0.5 wenn `sonstiges`)

**Akzeptanzkriterium**:
- 5 Beispiel-Filenames pro Typ → korrekt klassifiziert
- "Doku.pdf" → `sonstiges`

**Doku**: `docs/m04_pdf_classifier.md`

---

### Schritt 7: m05_address_extractor

**Ziel**: Aus dem Exposé-PDF die Objekt-Adresse extrahieren, NICHT die Makler-Adresse.

**Details**:
- PDF-Text via `pypdf` extrahieren
- Regex auf deutsches Adressformat: `Straße Hausnummer, PLZ Stadt`
- Heuristik zur Unterscheidung Objekt vs. Makler:
  - Adresse gewinnt, wenn in Nähe von Triggern: "Lage", "Objekt", "Anschrift", "Standort", "Adresse"
  - Adresse wird abgewertet, wenn in Nähe von: "Makler", "Anbieter", "Kontakt", "Telefon", "@", "Tel."
  - Bei mehreren Treffern: höchster Score gewinnt
- Fallback: wenn alle Treffer makler-typisch oder kein Treffer → return None
- Wenn Confidence < 0.7 → fallback LLM-Call (Anthropic API, kurzer Prompt: "Welche Adresse ist das Objekt, welche der Makler?")

**Akzeptanzkriterium**:
- 3 Test-Exposés (mit Objekt + Makler-Adresse) → korrekte Objekt-Adresse extrahiert
- Exposé ohne erkennbare Adresse → return None
- Adresse wird normalisiert: "Musterstr. 12" → "Musterstr 12, 44137 Dortmund"

**Doku**: `docs/m05_address_extractor.md`

---

### Schritt 8: m06_folder_manager

**Ziel**: Adresse + Files → Ordner anlegen, Files reinkopieren, Meta-File schreiben.

**Details**:
- Basis-Pfad aus `config.py`: `C:\Users\andre\OneDrive - APPV Personalvermittlung\Immobilien\001_AQUISE\Objekte\`
- Wenn Adresse vorhanden: Ordnername = Adresse (Sonderzeichen escapen, Slashes raus)
- Wenn Adresse None: Ordnername = `YYYY-MM-DD_HH-MM-SS_unbekannt`
- Wenn Ordner schon existiert (Doublette): Suffix `_2`, `_3` etc.
- Files reinkopieren mit Naming nach Klassifikation:
  - `expose` → `Exposé.pdf`
  - `mieterliste` → `Mieterliste.pdf`
  - `energieausweis` → `Energieausweis.pdf`
  - `modernisierung` → `Modernisierung.pdf`
  - `sonstiges` → Originaldateiname behalten
- `_meta.json` schreiben mit: `{adresse, message_id, von, subject, timestamp, files: [{name, typ, source}]}`

**Akzeptanzkriterium**:
- Adresse "Musterstr 12, 44137 Dortmund" + 3 Files → Ordner mit 3 Files + meta.json
- Doppelter Aufruf mit gleicher Adresse → `_2`-Ordner
- None-Adresse → Timestamp-Ordner

**Doku**: `docs/m06_folder_manager.md`

---

### Schritt 9: main.py Orchestrierung

**Ziel**: Alle Module zur Pipeline verdrahten.

**Pipeline-Ablauf**:
1. m01 erkennt neue Mail → Callback mit raw_mail
2. m07 prüft Idempotenz (Mail schon verarbeitet?) → wenn ja, skip
3. m07 markiert `processing`
4. m02 parst Mail → Anhänge + Links
5. m03 resolved Links → zusätzliche PDFs
6. Alle PDFs durch m04 → Klassifikation
7. Exposé identifizieren → m05 extrahiert Adresse
8. m06 legt Ordner an, kopiert Files
9. m07 markiert `done` (oder `error` bei Exception)
10. Logging über alle Stages

**Akzeptanzkriterium**:
- End-to-End-Test mit echter Test-Mail (Anhang + Link) → Ordner unter Basis-Pfad korrekt angelegt
- Zweite Mail mit selber message_id → wird übersprungen
- Mail ohne Exposé (nur Mieterliste) → Fallback-Ordner mit Timestamp

**Doku**: `docs/00_pipeline.md` (End-to-End-Beschreibung)

---

### Schritt 10: Hardening und Betrieb

**Ziel**: Pipeline in Dauerbetrieb nehmen.

**Details**:
- Windows-Service oder Task-Scheduler-Eintrag (Autostart bei Boot)
- Health-Check: alle 6 Stunden Log-Eintrag "Pipeline läuft, X Mails seit Start verarbeitet"
- Wöchentlicher Bericht (optional): Gmail-Email an dich selbst mit Übersicht

**Akzeptanzkriterium**:
- Nach Reboot startet Pipeline automatisch
- 24-Stunden-Test ohne Crash
- 5 echte Akquise-Mails laufen sauber durch

**Doku**: `docs/10_betrieb.md`

---

## Reihenfolge-Logik

Die Reihenfolge ist **bewusst unten-nach-oben aufgebaut**:

1. Foundation (Logger, State) zuerst, weil alle anderen darauf aufsetzen
2. Email-Empfang als isoliertes Modul testbar
3. Verarbeitungs-Module einzeln (Parser, Resolver, Classifier, Extractor)
4. Ablage-Modul
5. Erst zum Schluss main.py als Orchestrierung
6. Erst danach Hardening

So kannst du nach jedem Schritt einzeln testen, ohne dass die ganze Pipeline funktionsfähig sein muss.

## Risiken und Stopper

- **Schritt 5 (Container-Skill-Anbindung)**: Wenn der Skill auf Andrés PC nicht sauber von Python aus aufrufbar ist, müssen wir hier improvisieren (z.B. Headless-Chrome via Selenium als Fallback). **Klärung im Sparring zu Schritt 5**.
- **Schritt 7 (Adress-Extraktion)**: Heuristik kann scheitern. Plan B ist LLM-Fallback (Anthropic API). API-Key muss in `.env` liegen.
- **Schritt 10 (Windows-Service)**: Python als Windows-Service ist fummelig. Alternativ: Task Scheduler mit "Bei Anmeldung starten" + Konsolen-Fenster minimiert.

## Tracking

Pro abgeschlossenem Schritt: Implementierungsplan im claude.ai-Projekt mit `[x]` markieren. Nicht überspringen, auch wenn ein Schritt schnell ging, weil das den Überblick zerstört.
