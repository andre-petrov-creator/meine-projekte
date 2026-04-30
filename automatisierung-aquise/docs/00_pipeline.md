# Pipeline — End-to-End-Beschreibung

## Ablauf pro Mail

```
┌─────────────────────┐
│  m01 IMAP-IDLE      │  Gmail-Inbox lauschen (FROM andre-petrov@web.de)
│  → callback(raw)    │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  m02 parse(raw)     │  Header (Message-ID, Subject, Von)
│                     │  PDF-Anhänge → data/temp/{message_id}/
│                     │  Links aus Body
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  m07 is_processed?  │  → ja: skip, fertig
│  m07 mark_processing│
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  m03 resolve(links) │  Links → zusätzliche PDFs in data/temp/{message_id}/
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  m04 classify(pdf)  │  Filename-Heuristik → typ ∈ {expose, mieterliste, …}
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  m05 extract(expose)│  Objekt-Adresse via Regex + Trigger-Heuristik
│                     │  Fallback: LLM (Anthropic)
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  m06 store(...)     │  Ordner unter BASE_FOLDER:
│                     │  - Adresse vorhanden → "Musterstr 12, 44137 Dortmund"
│                     │  - sonst → "YYYY-MM-DD_HH-MM-SS_unbekannt"
│                     │  - Doublette → "_2", "_3"
│                     │  PDFs umbenannt + _meta.json
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  m07 mark_done      │  (oder mark_error bei Exception → Mail nicht erneut)
└─────────────────────┘
```

## Modi

### Default: IDLE-Loop

```bash
python main.py
```

- Verbindet zu Gmail, IMAP-IDLE
- Verarbeitet ungelesene Mails sofort beim Verbinden
- Lauscht auf neue Mails (Reconnect alle 29 Min)
- Bricht nur mit Ctrl+C ab

### `--once`: Einmal-Lauf

```bash
python main.py --once
```

- Verbindet, holt UNSEEN-Mails, verarbeitet, beendet
- Gut für Cron / Task Scheduler / manuellen Aufruf
- Verarbeitete Mails werden als `\Seen` markiert

## Idempotenz

- m07 hält pro `message_id` den Status (`processing`, `done`, `error`)
- `is_processed = True` bei Endzustand (`done` oder `error`)
- Gleiche Mail zweimal → **wird beim zweiten Mal übersprungen**
- Bei Crash während `processing`: bleibt nicht-Endzustand → wird beim nächsten Lauf erneut probiert

## Fail-safe

- Eine `error`-Mail wird **nicht automatisch retried** — manuelle Freigabe nötig
  (z.B. Eintrag in `data/state.db` löschen)
- Pipeline-Exception wird geloggt + State auf `error` gesetzt
- Listener läuft trotz einzelner Mail-Fehler weiter

## Adress-First-Prinzip

- Adresse = Primärschlüssel des Systems
- Ohne valide Adresse → Timestamp-Fallback-Ordner zur manuellen Nachsortierung
- Spätere Tools (CRM, Bewertungstools) setzen auf der Ordnerstruktur auf

## Akzeptanzkriterien (alle erfüllt)

| Kriterium | Test |
|-----------|------|
| End-to-End mit Anhang → Ordner unter Basis-Pfad | `test_e2e_mail_mit_anhang_legt_ordner_an` |
| Mail mit Anhang + Link → beide PDFs im Ordner   | `test_e2e_mail_mit_link_und_anhang`        |
| Zweite Mail mit selber message_id → übersprungen| `test_e2e_zweite_mail_mit_selber_id_wird_uebersprungen` |
| Mail ohne Exposé → Fallback-Ordner mit Timestamp | `test_e2e_mail_ohne_expose_landet_in_fallback_ordner`   |
| State-Store: done nach Erfolg                   | `test_e2e_state_store_done_nach_erfolg`    |
| Pipeline-Crash → State `error`, kein erneut    | `test_e2e_state_store_error_bei_pipeline_crash` |

## Live-Test (manuell)

```bash
# Status prüfen
python main.py --help
python main.py --once  # einmal verarbeiten
```

## Offene Punkte

- **Container-Skill für Webseiten-Links** noch nicht verdrahtet (siehe `m03_link_resolver.md`).
  Aktuell überspringt Pipeline reine Webseiten-Links mit einer Warning.
  Verdrahtung in Schritt 10 (Hardening/Betrieb) — oder bei Bedarf vorher.
