"""Tests für main.py — CLI + End-to-End-Pipeline.

Die End-to-End-Tests bauen synthetische Akquise-Mails (raw bytes) und
schicken sie durch `process_mail` mit gemockten externen Abhängigkeiten:
- m01 (IMAP) → wird nicht aufgerufen
- m03 (HTTP) → Renderer / requests gemockt
- m05's pypdf → durch Inline-Text ersetzt
- m05's LLM → kein API-Key (kein Fallback-Aufruf)
"""
from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

import pytest

import config
import main
from modules import (
    m02_email_parser,
    m05_address_extractor,
    m07_state_store,
)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_help_laeuft(capsys):
    with pytest.raises(SystemExit) as exc:
        main.parse_args(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "akquise-pipeline" in out


def test_default_args():
    args = main.parse_args([])
    assert args.once is False


def test_once_flag():
    args = main.parse_args(["--once"])
    assert args.once is True


# ---------------------------------------------------------------------------
# E2E-Helper
# ---------------------------------------------------------------------------


def _build_akquise_mail(
    *,
    message_id: str = "<akq-1@x>",
    subject: str = "Exposé MFH Dortmund",
    body: str = "Anbei das Exposé. Lage: Musterstraße 12, 44137 Dortmund",
    pdfs: list[tuple[str, bytes]] | None = None,
) -> bytes:
    msg = EmailMessage()
    msg["Message-ID"] = message_id
    msg["From"] = "Andre Petrov <andre-petrov@web.de>"
    msg["Subject"] = subject
    msg.set_content(body)
    for filename, content in pdfs or []:
        msg.add_attachment(
            content, maintype="application", subtype="pdf", filename=filename
        )
    return msg.as_bytes()


@pytest.fixture
def pipeline_env(tmp_path, monkeypatch):
    """Isoliert Pipeline-State pro Test:
    - BASE_FOLDER (Ablage), TEMP_DIR, STATE_DB_PATH alle in tmp_path
    - LLM-Fallback aus (kein API-Key)
    - pypdf gemockt: gibt den Filenamen-Stem als 'Text' zurück, damit
      m05 die Adresse aus dem Test-Inhalt liest
    """
    base = tmp_path / "Objekte"
    base.mkdir()
    monkeypatch.setattr(config, "BASE_FOLDER", base)
    monkeypatch.setattr(config, "TEMP_DIR", tmp_path / "temp")
    monkeypatch.setattr(config, "STATE_DB_PATH", tmp_path / "state.db")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")

    # PDF-Inhalt steckt als Bytes drin, m05 holt Text via pypdf — wir
    # ersetzen das durch direktes Decoding.
    def fake_pdf_to_text(path: Path) -> str:
        try:
            return Path(path).read_bytes().decode("utf-8", errors="ignore")
        except Exception:
            return ""

    monkeypatch.setattr(m05_address_extractor, "_pdf_to_text", fake_pdf_to_text)

    # frischer State-Store
    m07_state_store.init_db()
    return {"base": base, "tmp": tmp_path}


# ---------------------------------------------------------------------------
# Akzeptanzkriterien aus dem Plan
# ---------------------------------------------------------------------------


def test_e2e_mail_mit_anhang_legt_ordner_an(pipeline_env):
    """Akzeptanz: End-to-End mit Test-Mail (Anhang) → Ordner unter Basis-Pfad."""
    expose_text = (
        b"Exposee MFH\n"
        b"Lage: Musterstrasse 12, 44137 Dortmund\n"
        b"12 WE, 850 m2."
    )
    raw = _build_akquise_mail(
        message_id="<e2e-1@x>",
        pdfs=[("expose.pdf", expose_text)],
    )

    main.process_mail(raw)

    base = pipeline_env["base"]
    folders = list(base.iterdir())
    assert len(folders) == 1
    target = folders[0]
    assert "Musterstrasse 12" in target.name or "Musterstr 12" in target.name
    assert (target / "Exposé.pdf").exists()
    assert (target / "_meta.json").exists()


def test_e2e_zweite_mail_mit_selber_id_wird_uebersprungen(pipeline_env):
    """Akzeptanz: Idempotenz."""
    expose = b"Lage: Musterstrasse 12, 44137 Dortmund"
    raw = _build_akquise_mail(message_id="<dup@x>", pdfs=[("expose.pdf", expose)])

    main.process_mail(raw)
    folders_after_first = list(pipeline_env["base"].iterdir())

    main.process_mail(raw)  # zweiter Aufruf
    folders_after_second = list(pipeline_env["base"].iterdir())

    assert len(folders_after_first) == 1
    assert len(folders_after_second) == 1  # kein _2-Ordner!


def test_e2e_mail_ohne_expose_landet_in_fallback_ordner(pipeline_env):
    """Akzeptanz: Mail ohne Exposé (nur Mieterliste) → Timestamp-Ordner."""
    raw = _build_akquise_mail(
        message_id="<no-expose@x>",
        pdfs=[("Mieterliste.pdf", b"%PDF mieter")],
    )

    main.process_mail(raw)

    folders = list(pipeline_env["base"].iterdir())
    assert len(folders) == 1
    assert folders[0].name.endswith("_unbekannt")
    assert (folders[0] / "Mieterliste.pdf").exists()


# ---------------------------------------------------------------------------
# Weitere E2E-Pfade
# ---------------------------------------------------------------------------


def test_e2e_state_store_done_nach_erfolg(pipeline_env):
    raw = _build_akquise_mail(
        message_id="<state-done@x>",
        pdfs=[("expose.pdf", b"Lage: Hauptstr 5, 12345 Berlin")],
    )
    main.process_mail(raw)
    assert m07_state_store.is_processed("state-done@x")
    assert m07_state_store.get_status("state-done@x") == "done"


def test_e2e_state_store_error_bei_pipeline_crash(pipeline_env, monkeypatch):
    """Wenn ein Modul wirft, wird die Mail als 'error' markiert."""

    def boom(*args, **kw):
        raise RuntimeError("simulated crash")

    monkeypatch.setattr("modules.m06_folder_manager.store", boom)

    raw = _build_akquise_mail(
        message_id="<crash@x>",
        pdfs=[("expose.pdf", b"Lage: Hauptstr 5, 12345 Berlin")],
    )
    main.process_mail(raw)  # darf nicht raisen

    assert m07_state_store.get_status("crash@x") == "error"
    # Bei Status 'error' gilt is_processed=True (Fail-safe: nicht erneut probieren)
    assert m07_state_store.is_processed("crash@x")


def test_e2e_mail_mit_link_und_anhang(pipeline_env, monkeypatch):
    """Mail enthält Anhang UND Link → m03 lädt Link-PDF, beide landen im Ordner."""
    import requests

    # m03 lädt von "https://makler.de/extra.pdf" — wir mocken HEAD+GET
    head_resp = type(
        "R", (), {"status_code": 200, "headers": {"Content-Type": "application/pdf"}, "raise_for_status": lambda self=None: None}
    )()

    class FakeGet:
        status_code = 200
        headers = {"Content-Type": "application/pdf"}

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            return iter([b"%PDF-from-link"])

        def close(self):
            pass

    monkeypatch.setattr(requests, "head", lambda *a, **kw: head_resp)
    monkeypatch.setattr(requests, "get", lambda *a, **kw: FakeGet())

    raw = _build_akquise_mail(
        message_id="<link-and-attach@x>",
        body=(
            "Anbei das Exposé.\n"
            "Weitere Unterlagen: https://makler.de/extra.pdf"
        ),
        pdfs=[("expose.pdf", b"Lage: Hauptstr 1, 12345 Berlin")],
    )
    main.process_mail(raw)

    folders = list(pipeline_env["base"].iterdir())
    assert len(folders) == 1
    pdfs = sorted(p.name for p in folders[0].iterdir() if p.suffix == ".pdf")
    # Exposé wurde umbenannt; Link-PDF blieb "extra.pdf" (sonstiges)
    assert "Exposé.pdf" in pdfs
    assert "extra.pdf" in pdfs


def test_e2e_meta_json_inhalt(pipeline_env):
    import json

    raw = _build_akquise_mail(
        message_id="<meta@x>",
        subject="Exposé Test-Objekt",
        pdfs=[("expose.pdf", b"Lage: Hauptstr 1, 12345 Berlin")],
    )
    main.process_mail(raw)

    folder = next(pipeline_env["base"].iterdir())
    meta = json.loads((folder / "_meta.json").read_text(encoding="utf-8"))
    assert meta["message_id"] == "meta@x"
    assert meta["von"] == "andre-petrov@web.de"
    assert "Test-Objekt" in meta["subject"]
    assert meta["adresse"] is not None
