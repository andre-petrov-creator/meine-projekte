# m07 — State Store

## Zweck

SQLite-Persistierung verarbeiteter Mails. Stellt **Idempotenz** sicher:
gleiche `message_id` mehrfach markieren → kein Crash, Status wird
überschrieben.

## Public API

| Funktion                                          | Beschreibung |
|---------------------------------------------------|--------------|
| `init_db(db_path=None)`                           | Tabelle anlegen (idempotent) |
| `run()`                                           | Alias auf `init_db()` |
| `is_processed(message_id, db_path=None) -> bool`  | True bei Endzustand (`done` oder `error`) |
| `get_status(message_id, db_path=None) -> str|None`| Aktueller Status oder `None` |
| `mark_processing(message_id, db_path=None)`       | Status `processing` |
| `mark_done(message_id, folder_path, db_path=None)`| Status `done` + Ordnerpfad |
| `mark_error(message_id, error_msg, db_path=None)` | Status `error` + Fehlermeldung |

`db_path` ist immer optional — Default ist `config.STATE_DB_PATH`.
Tests können einen eigenen Pfad übergeben, ohne `config` zu mocken.

## Status-Werte

| Status       | Bedeutung |
|--------------|-----------|
| `pending`    | (reserviert, derzeit nicht aktiv genutzt) |
| `processing` | Mail wird gerade verarbeitet — bei Crash kann sie erneut laufen |
| `done`       | Erfolgreich abgelegt |
| `error`      | Fehler beim Verarbeiten — wird **nicht** automatisch erneut probiert (Fail-safe) |

`is_processed` ist **True** bei `done` oder `error`.
`processing` zählt **nicht** als verarbeitet, damit nach einem Crash
die Mail beim nächsten Lauf erneut angefasst werden kann.

## Schema

Tabelle `processed_mails`:

| Spalte        | Typ       | Beschreibung |
|---------------|-----------|--------------|
| `message_id`  | TEXT PK   | Eindeutige Mail-ID |
| `status`      | TEXT      | `pending` / `processing` / `done` / `error` |
| `timestamp`   | TEXT      | ISO 8601 (UTC) |
| `error_msg`   | TEXT      | Bei Status `error` |
| `folder_path` | TEXT      | Bei Status `done` |

## Speicherort

`data/state.db` (Pfad aus `config.py: STATE_DB_PATH`).
WAL-Modus aktiviert für robustere Concurrent-Zugriffe.

## Verwendung

```python
from modules import m07_state_store as store

store.init_db()
if not store.is_processed(message_id):
    store.mark_processing(message_id)
    try:
        folder = process_mail(...)
        store.mark_done(message_id, folder)
    except Exception as e:
        store.mark_error(message_id, str(e))
```

## Status

✅ Implementiert (Schritt 2). Tests in `tests/test_m07_state_store.py`.
