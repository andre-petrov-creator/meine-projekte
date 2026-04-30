"""Tests für Health-Check und Counter in main.py."""
from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

import pytest

import config
import main
from modules import m05_address_extractor, m07_state_store


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    base = tmp_path / "Objekte"
    base.mkdir()
    monkeypatch.setattr(config, "BASE_FOLDER", base)
    monkeypatch.setattr(config, "TEMP_DIR", tmp_path / "temp")
    monkeypatch.setattr(config, "STATE_DB_PATH", tmp_path / "state.db")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")

    def fake_pdf_to_text(path: Path) -> str:
        return Path(path).read_bytes().decode("utf-8", errors="ignore")

    monkeypatch.setattr(m05_address_extractor, "_pdf_to_text", fake_pdf_to_text)
    m07_state_store.init_db()

    # Counter zurücksetzen
    main._processed_count = 0
    main._skipped_count = 0
    main._error_count = 0
    main._started_at = None
    return tmp_path


def _mail(message_id: str, body: bytes = b"Lage: Hauptstr 1, 12345 Berlin"):
    msg = EmailMessage()
    msg["Message-ID"] = message_id
    msg["From"] = "andre-petrov@web.de"
    msg["Subject"] = "Test"
    msg.set_content("body")
    msg.add_attachment(body, maintype="application", subtype="pdf", filename="expose.pdf")
    return msg.as_bytes()


def test_counter_inkrementiert_bei_erfolg(isolated):
    main.process_mail(_mail("<c1@x>"))
    main.process_mail(_mail("<c2@x>"))
    assert main._processed_count == 2
    assert main._skipped_count == 0


def test_counter_skipped_bei_doppelter_id(isolated):
    main.process_mail(_mail("<dup@x>"))
    main.process_mail(_mail("<dup@x>"))  # zweite mal → übersprungen
    assert main._processed_count == 1
    assert main._skipped_count == 1


def test_counter_error_bei_pipeline_crash(isolated, monkeypatch):
    monkeypatch.setattr(
        "modules.m06_folder_manager.store",
        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    main.process_mail(_mail("<crash@x>"))
    assert main._error_count == 1
    assert main._processed_count == 0


def test_healthcheck_tick_loggt_statistik(isolated, caplog, monkeypatch):
    """_healthcheck_tick darf nicht crashen und muss das Log schreiben."""
    # Re-arm in tick() vermeiden, sonst läuft Daemon-Thread weiter
    monkeypatch.setattr(main, "_start_healthcheck", lambda: None)
    main._started_at = main.datetime.now()
    main._processed_count = 5
    main._skipped_count = 2
    main._error_count = 1

    with caplog.at_level("INFO", logger="main"):
        main._healthcheck_tick()

    text = " ".join(r.message for r in caplog.records)
    assert "Health-Check" in text
    assert "5 verarbeitet" in text
    assert "2 übersprungen" in text
    assert "1 Fehler" in text


def test_healthcheck_tick_ohne_started_at(isolated, monkeypatch):
    """Robustheit: tick darf auch ohne gesetztes _started_at funktionieren."""
    monkeypatch.setattr(main, "_start_healthcheck", lambda: None)
    main._started_at = None
    # darf nicht crashen
    main._healthcheck_tick()


def test_start_healthcheck_erzeugt_daemon_timer(monkeypatch):
    """_start_healthcheck startet einen Daemon-Timer (kein Test-Hang)."""
    started = {}

    class FakeTimer:
        def __init__(self, interval, func):
            started["interval"] = interval
            started["func"] = func
            self.daemon = False

        def start(self):
            started["started"] = True

    monkeypatch.setattr("main.threading.Timer", FakeTimer)
    main._start_healthcheck()

    assert started["started"] is True
    assert started["interval"] == config.HEALTHCHECK_INTERVAL_SECONDS
    assert started["func"] is main._healthcheck_tick
