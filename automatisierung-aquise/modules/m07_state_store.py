"""m07 — State Store.

SQLite-Persistierung verarbeiteter Mails. Stellt Idempotenz sicher.

Public API:
    init_db(db_path=None) — Tabelle anlegen falls nötig
    run() — Alias auf init_db()
    is_processed(message_id, db_path=None) -> bool
    mark_processing(message_id, db_path=None)
    mark_done(message_id, folder_path, db_path=None)
    mark_error(message_id, error_msg, db_path=None)
    get_status(message_id, db_path=None) -> str | None

Status-Werte: pending, processing, done, error.
`is_processed` ist True bei Status `done` oder `error` (Mail wird nicht
erneut angefasst, manuelle Freigabe nötig — siehe fail-safe-Prinzip).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import config

STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_DONE = "done"
STATUS_ERROR = "error"

_TERMINAL_STATUSES = {STATUS_DONE, STATUS_ERROR}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_mails (
    message_id  TEXT PRIMARY KEY,
    status      TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    error_msg   TEXT,
    folder_path TEXT
)
"""


def _resolve_path(db_path: str | Path | None) -> Path:
    return Path(db_path) if db_path is not None else config.STATE_DB_PATH


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = _resolve_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db(db_path: str | Path | None = None) -> None:
    """Erstellt die Tabelle falls sie noch nicht existiert."""
    with _connect(db_path) as conn:
        conn.execute(_SCHEMA)
        conn.commit()


def run() -> None:
    """Pipeline-Konvention: Alias auf init_db()."""
    init_db()


def _upsert(
    db_path: str | Path | None,
    message_id: str,
    status: str,
    error_msg: str | None = None,
    folder_path: str | None = None,
) -> None:
    with _connect(db_path) as conn:
        conn.execute(_SCHEMA)
        conn.execute(
            """
            INSERT INTO processed_mails (message_id, status, timestamp, error_msg, folder_path)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(message_id) DO UPDATE SET
                status = excluded.status,
                timestamp = excluded.timestamp,
                error_msg = excluded.error_msg,
                folder_path = excluded.folder_path
            """,
            (message_id, status, _now(), error_msg, folder_path),
        )
        conn.commit()


def is_processed(message_id: str, db_path: str | Path | None = None) -> bool:
    """True wenn Mail einen Endzustand erreicht hat (done oder error)."""
    with _connect(db_path) as conn:
        conn.execute(_SCHEMA)
        row = conn.execute(
            "SELECT status FROM processed_mails WHERE message_id = ?",
            (message_id,),
        ).fetchone()
    if row is None:
        return False
    return row[0] in _TERMINAL_STATUSES


def get_status(message_id: str, db_path: str | Path | None = None) -> str | None:
    """Liefert den aktuellen Status oder None wenn unbekannt."""
    with _connect(db_path) as conn:
        conn.execute(_SCHEMA)
        row = conn.execute(
            "SELECT status FROM processed_mails WHERE message_id = ?",
            (message_id,),
        ).fetchone()
    return row[0] if row else None


def mark_processing(message_id: str, db_path: str | Path | None = None) -> None:
    _upsert(db_path, message_id, STATUS_PROCESSING)


def mark_done(
    message_id: str, folder_path: str, db_path: str | Path | None = None
) -> None:
    _upsert(db_path, message_id, STATUS_DONE, folder_path=folder_path)


def mark_error(
    message_id: str, error_msg: str, db_path: str | Path | None = None
) -> None:
    _upsert(db_path, message_id, STATUS_ERROR, error_msg=error_msg)
