"""Tests für health_check.py."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import config
import health_check


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Sandbox: State-DB, BASE_FOLDER, Log-File und Last-Check-File in tmp."""
    state_db = tmp_path / "state.db"
    base = tmp_path / "Objekte"
    base.mkdir()
    log_file = tmp_path / "pipeline.log"
    log_file.write_text("ok", encoding="utf-8")
    last_check = tmp_path / "last_healthcheck.json"

    monkeypatch.setattr(config, "STATE_DB_PATH", state_db)
    monkeypatch.setattr(config, "BASE_FOLDER", base)
    monkeypatch.setattr(config, "LOG_FILE", log_file)
    monkeypatch.setattr(config, "HEALTHCHECK_LAST_CHECK_FILE", last_check)
    monkeypatch.setattr(config, "GMAIL_USER", "x@y")
    monkeypatch.setattr(config, "GMAIL_APP_PASSWORD", "pw")

    # Frische DB
    conn = sqlite3.connect(state_db)
    conn.execute(
        "CREATE TABLE processed_mails ("
        "message_id TEXT PRIMARY KEY, status TEXT, timestamp TEXT, "
        "error_msg TEXT, folder_path TEXT)"
    )
    conn.commit()
    conn.close()

    return {"state_db": state_db, "base": base, "log_file": log_file, "last": last_check}


def _insert(state_db, message_id, status, timestamp=None, error_msg=None):
    conn = sqlite3.connect(state_db)
    conn.execute(
        "INSERT INTO processed_mails VALUES (?, ?, ?, ?, ?)",
        (
            message_id,
            status,
            timestamp or datetime.now().isoformat(timespec="seconds"),
            error_msg,
            None,
        ),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# State-DB-Checks
# ---------------------------------------------------------------------------


def test_kein_problem_kein_issue(isolated):
    _insert(isolated["state_db"], "ok-1", "done")
    issues = health_check.check_state_db()
    assert issues == []


def test_haengende_processing_wird_erkannt(isolated):
    stale_ts = (datetime.now() - timedelta(hours=2)).isoformat(timespec="seconds")
    _insert(isolated["state_db"], "stuck-1", "processing", timestamp=stale_ts)
    issues = health_check.check_state_db()
    assert len(issues) == 1
    assert "stuck-1" in issues[0]
    assert "processing" in issues[0]


def test_frische_processing_kein_issue(isolated):
    """Mail die gerade verarbeitet wird (frisch) → kein Alarm."""
    _insert(isolated["state_db"], "fresh-1", "processing")
    issues = health_check.check_state_db()
    assert issues == []


def test_neue_errors_werden_gemeldet(isolated):
    _insert(isolated["state_db"], "err-1", "error", error_msg="boom")
    issues = health_check.check_state_db()
    assert len(issues) == 1
    assert "err-1" in issues[0]
    assert "boom" in issues[0]


def test_alte_errors_vor_letztem_check_werden_nicht_gemeldet(isolated):
    """Errors die schon im letzten Health-Check vermeldet wurden → kein Doppelalarm."""
    last_check_ts = datetime.now().isoformat(timespec="seconds")
    isolated["last"].write_text(
        json.dumps({"timestamp": last_check_ts}), encoding="utf-8"
    )
    # Error in der Vergangenheit
    old_ts = (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds")
    _insert(isolated["state_db"], "old-err", "error", timestamp=old_ts)

    issues = health_check.check_state_db()
    assert issues == []


def test_state_db_existiert_nicht(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "STATE_DB_PATH", tmp_path / "missing.db")
    issues = health_check.check_state_db()
    assert len(issues) == 1
    assert "State-DB" in issues[0]


# ---------------------------------------------------------------------------
# Log-Freshness
# ---------------------------------------------------------------------------


def test_log_aktuell_kein_issue(isolated):
    issues = health_check.check_logs_freshness()
    assert issues == []


def test_log_alt_wird_gemeldet(isolated):
    # Setze mtime auf 10 Tage zurück
    old = datetime.now() - timedelta(days=10)
    import os
    os.utime(isolated["log_file"], (old.timestamp(), old.timestamp()))
    issues = health_check.check_logs_freshness()
    assert len(issues) == 1
    assert "nicht aktualisiert" in issues[0]


def test_log_fehlt_wird_gemeldet(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOG_FILE", tmp_path / "nope.log")
    issues = health_check.check_logs_freshness()
    assert len(issues) == 1


# ---------------------------------------------------------------------------
# Prozess-Check
# ---------------------------------------------------------------------------


def test_prozess_check_findet_main_py(monkeypatch):
    monkeypatch.setattr(
        "subprocess.check_output",
        lambda *a, **kw: "Caption=python.exe\npython.exe main.py\n",
    )
    issues = health_check.check_pipeline_process()
    assert issues == []


def test_prozess_check_kein_main_py(monkeypatch):
    monkeypatch.setattr(
        "subprocess.check_output",
        lambda *a, **kw: "Caption=python.exe\npython.exe other.py\n",
    )
    issues = health_check.check_pipeline_process()
    assert len(issues) == 1
    assert "läuft nicht" in issues[0]


def test_prozess_check_wmic_fehler(monkeypatch):
    def boom(*a, **kw):
        raise FileNotFoundError("wmic not found")

    monkeypatch.setattr("subprocess.check_output", boom)
    issues = health_check.check_pipeline_process()
    assert len(issues) == 1


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def test_snapshot_zaehlt_status_und_ordner(isolated):
    _insert(isolated["state_db"], "a", "done")
    _insert(isolated["state_db"], "b", "done")
    _insert(isolated["state_db"], "c", "error")
    (isolated["base"] / "Objekt 1").mkdir()
    (isolated["base"] / "Objekt 2").mkdir()

    snap = health_check.collect_snapshot()
    assert snap["counts"]["done"] == 2
    assert snap["counts"]["error"] == 1
    assert snap["folder_count"] == 2


# ---------------------------------------------------------------------------
# Mail-Versand (gemockt)
# ---------------------------------------------------------------------------


def test_main_keine_mail_bei_alles_ok(isolated, monkeypatch):
    """Akzeptanz: wenn alles OK → keine Mail."""
    monkeypatch.setattr(health_check, "check_pipeline_process", lambda: [])
    sent = []
    monkeypatch.setattr(
        health_check, "send_alert_mail", lambda issues, snap: sent.append((issues, snap))
    )
    health_check.main()
    assert sent == []


def test_main_mail_bei_problem(isolated, monkeypatch):
    """Akzeptanz: bei Problem → Mail wird ausgelöst."""
    monkeypatch.setattr(
        health_check, "check_pipeline_process", lambda: ["Pipeline läuft nicht."]
    )
    sent = []
    monkeypatch.setattr(
        health_check, "send_alert_mail", lambda issues, snap: sent.append((issues, snap))
    )
    health_check.main()
    assert len(sent) == 1
    assert "Pipeline läuft nicht." in sent[0][0]


def test_send_alert_mail_smtp_call(isolated, monkeypatch):
    fake_smtp_instance = MagicMock()
    fake_smtp_class = MagicMock(return_value=fake_smtp_instance)
    fake_smtp_instance.__enter__ = MagicMock(return_value=fake_smtp_instance)
    fake_smtp_instance.__exit__ = MagicMock(return_value=False)

    monkeypatch.setattr("smtplib.SMTP", fake_smtp_class)

    health_check.send_alert_mail(["Issue 1"], {"timestamp": "2026-04-30"})

    fake_smtp_instance.starttls.assert_called_once()
    fake_smtp_instance.login.assert_called_once()
    fake_smtp_instance.send_message.assert_called_once()


def test_send_alert_mail_ohne_credentials_loggt_aber_crasht_nicht(monkeypatch):
    monkeypatch.setattr(config, "GMAIL_USER", "")
    monkeypatch.setattr(config, "GMAIL_APP_PASSWORD", "")
    # darf nicht raisen
    health_check.send_alert_mail(["x"], {})


# ---------------------------------------------------------------------------
# Last-Check-Datei
# ---------------------------------------------------------------------------


def test_main_speichert_last_check_timestamp(isolated, monkeypatch):
    monkeypatch.setattr(health_check, "check_pipeline_process", lambda: [])
    monkeypatch.setattr(health_check, "send_alert_mail", lambda *a, **kw: None)
    health_check.main()
    assert isolated["last"].exists()
    data = json.loads(isolated["last"].read_text(encoding="utf-8"))
    assert "timestamp" in data
