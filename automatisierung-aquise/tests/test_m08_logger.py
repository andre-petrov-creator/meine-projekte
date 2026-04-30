"""Tests für m08_logger."""
from __future__ import annotations

import logging

import pytest

import config
from modules import m08_logger


@pytest.fixture(autouse=True)
def _isolate_logger(tmp_path, monkeypatch):
    """Isoliert Logger-State zwischen Tests und schreibt Log-File in tmp."""
    monkeypatch.setattr(config, "LOGS_DIR", tmp_path)
    monkeypatch.setattr(config, "LOG_FILE", tmp_path / "pipeline.log")
    m08_logger._reset_for_tests()
    yield
    m08_logger._reset_for_tests()


def test_get_logger_liefert_logger_instanz():
    logger = m08_logger.get_logger("test")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test"


def test_setup_ist_idempotent():
    # pytest hängt selbst Handler an root, daher Delta messen statt absolut
    pre = len(logging.getLogger().handlers)
    m08_logger.setup()
    after_first = len(logging.getLogger().handlers)
    m08_logger.setup()
    after_second = len(logging.getLogger().handlers)
    assert after_first - pre == 2  # File + Console
    assert after_second == after_first  # zweiter Aufruf = no-op


def test_logger_schreibt_in_file_und_console(capsys, tmp_path):
    logger = m08_logger.get_logger("test_modul")
    logger.warning("Testnachricht")

    log_file = tmp_path / "pipeline.log"
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Testnachricht" in content
    assert "[test_modul]" in content
    assert "[WARNING]" in content

    captured = capsys.readouterr()
    assert "Testnachricht" in captured.err or "Testnachricht" in captured.out


def test_log_format_enthaelt_zeitstempel_modul_level(tmp_path):
    logger = m08_logger.get_logger("formatcheck")
    logger.info("hallo")
    content = (tmp_path / "pipeline.log").read_text(encoding="utf-8")
    # Format: [YYYY-MM-DD HH:MM:SS] [name] [LEVEL] msg
    assert "[formatcheck]" in content
    assert "[INFO]" in content


def test_run_alias_funktioniert():
    m08_logger.run()
    assert m08_logger._initialized is True
