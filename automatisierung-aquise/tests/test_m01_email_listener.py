"""Tests für m01_email_listener.

Pure-Logik-Tests (Backoff, Konstruktor-Validierung). Den IDLE-Loop selbst
testen wir hier nicht — das wäre ein Integrations-Test gegen einen Mock-
oder echten IMAP-Server. Live-Test über manuellen Smoke-Run (siehe Doku).
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import config
from modules import m01_email_listener as listener


def test_modul_importiert():
    assert hasattr(listener, "run")
    assert hasattr(listener, "EmailListener")


def test_calculate_backoff_progression():
    cap = 30
    assert listener._calculate_backoff(0, cap) == 1
    assert listener._calculate_backoff(1, cap) == 2
    assert listener._calculate_backoff(2, cap) == 4
    assert listener._calculate_backoff(3, cap) == 8
    assert listener._calculate_backoff(4, cap) == 16


def test_calculate_backoff_caps_at_max():
    cap = 30
    assert listener._calculate_backoff(5, cap) == 30  # 32 → cap
    assert listener._calculate_backoff(6, cap) == 30
    assert listener._calculate_backoff(20, cap) == 30


def test_calculate_backoff_respektiert_eigenen_max(monkeypatch):
    assert listener._calculate_backoff(10, max_seconds=5) == 5


def test_konstruktor_nutzt_config_defaults(monkeypatch):
    monkeypatch.setattr(config, "GMAIL_USER", "u@x")
    monkeypatch.setattr(config, "GMAIL_APP_PASSWORD", "pw")
    monkeypatch.setattr(config, "FILTER_FROM_ADDRESS", "from@x")
    monkeypatch.setattr(config, "GMAIL_IMAP_HOST", "imap.example.com")
    monkeypatch.setattr(config, "GMAIL_IMAP_PORT", 993)
    monkeypatch.setattr(config, "IMAP_IDLE_TIMEOUT_SECONDS", 1740)
    monkeypatch.setattr(config, "IMAP_RECONNECT_BACKOFF_MAX", 30)

    inst = listener.EmailListener(callback=lambda raw: None)
    assert inst.user == "u@x"
    assert inst.password == "pw"
    assert inst.filter_from == "from@x"
    assert inst.host == "imap.example.com"
    assert inst.port == 993
    assert inst.idle_timeout == 1740
    assert inst.backoff_max == 30


def test_konstruktor_explizit_ueberschreibt_config(monkeypatch):
    monkeypatch.setattr(config, "GMAIL_USER", "default@x")
    inst = listener.EmailListener(
        callback=lambda raw: None,
        user="explicit@x",
        password="pw",
        filter_from="from@x",
    )
    assert inst.user == "explicit@x"


def test_konstruktor_raises_ohne_user(monkeypatch):
    monkeypatch.setattr(config, "GMAIL_USER", "")
    monkeypatch.setattr(config, "GMAIL_APP_PASSWORD", "pw")
    monkeypatch.setattr(config, "FILTER_FROM_ADDRESS", "x@y")
    with pytest.raises(ValueError, match="GMAIL_USER"):
        listener.EmailListener(callback=lambda raw: None)


def test_konstruktor_raises_ohne_filter(monkeypatch):
    monkeypatch.setattr(config, "GMAIL_USER", "u@x")
    monkeypatch.setattr(config, "GMAIL_APP_PASSWORD", "pw")
    monkeypatch.setattr(config, "FILTER_FROM_ADDRESS", "")
    with pytest.raises(ValueError, match="FILTER_FROM_ADDRESS"):
        listener.EmailListener(callback=lambda raw: None)


def test_run_ohne_callback_raises():
    with pytest.raises(ValueError, match="callback"):
        listener.run(callback=None)


def test_stop_setzt_flag():
    inst = listener.EmailListener(
        callback=lambda raw: None,
        user="u@x",
        password="pw",
        filter_from="x@y",
    )
    assert inst._stop is False
    inst.stop()
    assert inst._stop is True


def test_handle_uid_callback_erfolg_markiert_seen():
    """Nach erfolgreichem Callback wird Mail als \\Seen markiert."""
    callback = MagicMock()
    inst = listener.EmailListener(
        callback=callback, user="u@x", password="pw", filter_from="x@y"
    )

    imap = MagicMock()
    imap.fetch.return_value = {42: {b"RFC822": b"raw-mail-bytes"}}

    inst._handle_uid(imap, 42)

    callback.assert_called_once_with(b"raw-mail-bytes")
    imap.add_flags.assert_called_once_with([42], [b"\\Seen"])


def test_handle_uid_callback_exception_laesst_unseen():
    """Wirft Callback eine Exception, bleibt Mail UNSEEN."""
    callback = MagicMock(side_effect=RuntimeError("boom"))
    inst = listener.EmailListener(
        callback=callback, user="u@x", password="pw", filter_from="x@y"
    )

    imap = MagicMock()
    imap.fetch.return_value = {42: {b"RFC822": b"raw"}}

    inst._handle_uid(imap, 42)

    callback.assert_called_once()
    imap.add_flags.assert_not_called()


def test_handle_uid_fetch_fehler_ueberspringt():
    """Schlägt der Fetch fehl, wird Callback nicht aufgerufen, kein Crash."""
    callback = MagicMock()
    inst = listener.EmailListener(
        callback=callback, user="u@x", password="pw", filter_from="x@y"
    )

    imap = MagicMock()
    imap.fetch.side_effect = RuntimeError("network")

    inst._handle_uid(imap, 42)

    callback.assert_not_called()
    imap.add_flags.assert_not_called()
