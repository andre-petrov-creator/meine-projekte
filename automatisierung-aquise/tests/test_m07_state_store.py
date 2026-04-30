"""Tests für m07_state_store."""
from __future__ import annotations

import pytest

from modules import m07_state_store as store


@pytest.fixture
def db(tmp_path):
    """Frische Test-DB pro Test."""
    path = tmp_path / "test_state.db"
    store.init_db(db_path=path)
    return path


def test_init_db_legt_tabelle_an(tmp_path):
    path = tmp_path / "fresh.db"
    store.init_db(db_path=path)
    assert path.exists()


def test_is_processed_false_bei_unbekannter_id(db):
    assert store.is_processed("unknown@id", db_path=db) is False


def test_processing_ist_kein_endzustand(db):
    store.mark_processing("msg-1", db_path=db)
    # Mail ist in Bearbeitung, aber NICHT abgeschlossen → darf erneut probiert werden
    assert store.is_processed("msg-1", db_path=db) is False
    assert store.get_status("msg-1", db_path=db) == "processing"


def test_done_ist_endzustand(db):
    store.mark_done("msg-2", folder_path="/some/path", db_path=db)
    assert store.is_processed("msg-2", db_path=db) is True
    assert store.get_status("msg-2", db_path=db) == "done"


def test_error_ist_endzustand(db):
    store.mark_error("msg-3", error_msg="boom", db_path=db)
    assert store.is_processed("msg-3", db_path=db) is True
    assert store.get_status("msg-3", db_path=db) == "error"


def test_status_lifecycle_processing_dann_done(db):
    msg = "msg-lifecycle"
    store.mark_processing(msg, db_path=db)
    assert store.get_status(msg, db_path=db) == "processing"
    store.mark_done(msg, folder_path="/x", db_path=db)
    assert store.get_status(msg, db_path=db) == "done"


def test_idempotent_doppeltes_mark_processing(db):
    """Akzeptanzkriterium: gleiche message_id zweimal markieren → kein Crash."""
    store.mark_processing("dup-1", db_path=db)
    store.mark_processing("dup-1", db_path=db)
    assert store.get_status("dup-1", db_path=db) == "processing"


def test_idempotent_doppeltes_mark_done(db):
    store.mark_done("dup-2", folder_path="/a", db_path=db)
    store.mark_done("dup-2", folder_path="/b", db_path=db)
    assert store.get_status("dup-2", db_path=db) == "done"


def test_state_persistiert_ueber_verbindungen(db):
    store.mark_done("persist", folder_path="/here", db_path=db)
    # Neue Verbindung simuliert Process-Restart
    assert store.is_processed("persist", db_path=db) is True


def test_init_db_idempotent(tmp_path):
    path = tmp_path / "twice.db"
    store.init_db(db_path=path)
    store.init_db(db_path=path)
    assert path.exists()
