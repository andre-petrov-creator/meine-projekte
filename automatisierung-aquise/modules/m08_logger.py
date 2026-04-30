"""m08 — Logger.

Zentrales Logging-Setup: File-Handler mit Rotation + Console-Handler.
Format: [Zeitstempel] [Modul] [Level] Nachricht.

Public API:
    setup() — initialisiert Root-Logger (idempotent)
    get_logger(name) — liefert konfigurierten Logger
    run() — Alias auf setup() (Konvention der Pipeline)
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

import config

_LOG_FORMAT = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False


def setup() -> None:
    """Initialisiert das Logging-System. Idempotent: mehrfacher Aufruf ist no-op."""
    global _initialized
    if _initialized:
        return

    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    file_handler = RotatingFileHandler(
        filename=config.LOG_FILE,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(config.LOG_LEVEL)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """Liefert einen Logger. Initialisiert das System falls nötig."""
    if not _initialized:
        setup()
    return logging.getLogger(name)


def run() -> None:
    """Pipeline-Konvention: Alias auf setup()."""
    setup()


def _reset_for_tests() -> None:
    """Nur für Tests: Setzt das Logging-System zurück."""
    global _initialized
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    _initialized = False
