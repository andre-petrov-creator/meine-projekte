# m08 — Logger

## Zweck

Zentrales Logging-Setup. File- und Console-Handler.
Initialisierung ist **idempotent** — mehrfacher `setup()`-Aufruf hat keinen Effekt.

## Public API

| Funktion              | Beschreibung |
|-----------------------|--------------|
| `setup()`             | Initialisiert das Logging-System (idempotent) |
| `run()`               | Alias auf `setup()` (Pipeline-Konvention) |
| `get_logger(name)`    | Liefert konfigurierten Logger; ruft `setup()` auf, falls nötig |

## Konfiguration (aus `config.py`)

| Variable            | Default              |
|---------------------|----------------------|
| `LOG_LEVEL`         | `INFO`               |
| `LOG_FILE`          | `logs/pipeline.log`  |
| `LOG_MAX_BYTES`     | 10 MB                |
| `LOG_BACKUP_COUNT`  | 5                    |

## Format

```
[YYYY-MM-DD HH:MM:SS] [<modul>] [<LEVEL>] <Nachricht>
```

## Verhalten

- File-Handler: `RotatingFileHandler` (10 MB pro File, 5 Backups)
- Console-Handler: `StreamHandler` (stderr)
- Encoding: UTF-8
- `LOGS_DIR` wird automatisch angelegt, falls noch nicht vorhanden

## Verwendung

```python
from modules.m08_logger import get_logger
log = get_logger(__name__)
log.info("Pipeline gestartet")
```

## Status

✅ Implementiert (Schritt 2). Tests in `tests/test_m08_logger.py`.
