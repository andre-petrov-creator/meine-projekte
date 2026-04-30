"""Tests für m02_email_parser."""
from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

import pytest

import config
from modules import m02_email_parser as parser


@pytest.fixture(autouse=True)
def _temp_data_dir(tmp_path, monkeypatch):
    """Schreibt PDF-Anhänge in eine isolierte Temp-Struktur pro Test."""
    monkeypatch.setattr(config, "TEMP_DIR", tmp_path / "temp")


def _build_mail(
    *,
    message_id: str | None = "<test@local>",
    subject: str = "Akquise-Mail",
    from_: str = "Andre Petrov <andre-petrov@web.de>",
    body_plain: str | None = None,
    body_html: str | None = None,
    pdf_attachments: list[tuple[str, bytes]] | None = None,
) -> bytes:
    msg = EmailMessage()
    if message_id is not None:
        msg["Message-ID"] = message_id
    msg["From"] = from_
    msg["Subject"] = subject

    if body_plain is None and body_html is None:
        body_plain = "Hallo,\nbitte siehe Anhang.\n"

    if body_plain is not None:
        msg.set_content(body_plain)
    if body_html is not None:
        if body_plain is None:
            msg.set_content("(html-only)")
        msg.add_alternative(body_html, subtype="html")

    for filename, content in (pdf_attachments or []):
        msg.add_attachment(
            content,
            maintype="application",
            subtype="pdf",
            filename=filename,
        )

    return msg.as_bytes()


# ---------------------------------------------------------------------------
# Akzeptanzkriterien aus dem Implementierungsplan
# ---------------------------------------------------------------------------


def test_anhang_und_link_korrekt_geparst():
    raw = _build_mail(
        body_plain="Schau dir das Exposé hier an: https://makler.de/expose-12345",
        pdf_attachments=[("expose.pdf", b"%PDF-1.4 fake content")],
    )
    result = parser.parse(raw)

    assert len(result["anhaenge"]) == 1
    assert len(result["links"]) == 1
    assert result["links"][0] == "https://makler.de/expose-12345"
    assert result["anhaenge"][0].name == "expose.pdf"
    assert result["anhaenge"][0].read_bytes() == b"%PDF-1.4 fake content"


def test_nur_anhang_keine_links():
    raw = _build_mail(
        body_plain="(Anhang anbei)",
        pdf_attachments=[("doc.pdf", b"%PDF-x")],
    )
    result = parser.parse(raw)

    assert len(result["anhaenge"]) == 1
    assert result["links"] == []


def test_nur_link_keine_anhaenge():
    raw = _build_mail(body_plain="Hier: https://makler.de/x")
    result = parser.parse(raw)

    assert result["anhaenge"] == []
    assert result["links"] == ["https://makler.de/x"]


# ---------------------------------------------------------------------------
# Header-Extraktion
# ---------------------------------------------------------------------------


def test_message_id_normalisiert_klammern():
    raw = _build_mail(message_id="<abc@example.com>")
    result = parser.parse(raw)
    assert result["message_id"] == "abc@example.com"


def test_message_id_fallback_bei_fehlender_id():
    raw = _build_mail(message_id=None)
    result = parser.parse(raw)
    assert result["message_id"].startswith("no-id-")
    assert len(result["message_id"]) == len("no-id-") + 16


def test_message_id_fallback_deterministisch():
    raw = _build_mail(message_id=None)
    a = parser.parse(raw)
    b = parser.parse(raw)
    assert a["message_id"] == b["message_id"]


def test_von_extrahiert_email_adresse():
    raw = _build_mail(from_="Andre Petrov <andre-petrov@web.de>")
    result = parser.parse(raw)
    assert result["von"] == "andre-petrov@web.de"


def test_subject_mit_umlauten():
    raw = _build_mail(subject="Exposé MFH Dortmund")
    result = parser.parse(raw)
    assert "Exposé MFH Dortmund" in result["subject"]


# ---------------------------------------------------------------------------
# Anhänge
# ---------------------------------------------------------------------------


def test_mehrere_pdf_anhaenge():
    raw = _build_mail(
        pdf_attachments=[
            ("expose.pdf", b"%PDF-1"),
            ("mieterliste.pdf", b"%PDF-2"),
            ("energieausweis.pdf", b"%PDF-3"),
        ],
    )
    result = parser.parse(raw)
    assert len(result["anhaenge"]) == 3
    names = sorted(p.name for p in result["anhaenge"])
    assert names == ["energieausweis.pdf", "expose.pdf", "mieterliste.pdf"]


def test_anhaenge_landen_in_message_id_unterordner(tmp_path):
    raw = _build_mail(
        message_id="<unique-id-123@x>",
        pdf_attachments=[("a.pdf", b"%PDF")],
    )
    result = parser.parse(raw)
    saved = result["anhaenge"][0]
    assert "unique-id-123" in str(saved.parent)


def test_doppelter_filename_wird_eindeutig_gemacht():
    raw = _build_mail(
        pdf_attachments=[
            ("doc.pdf", b"%PDF-A"),
            ("doc.pdf", b"%PDF-B"),
        ],
    )
    result = parser.parse(raw)
    names = sorted(p.name for p in result["anhaenge"])
    assert names == ["doc.pdf", "doc_2.pdf"]


def test_filename_mit_pfadgefaehrlichen_zeichen():
    raw = _build_mail(
        pdf_attachments=[("foo/bar:baz.pdf", b"%PDF")],
    )
    result = parser.parse(raw)
    saved = result["anhaenge"][0]
    assert "/" not in saved.name
    assert ":" not in saved.name


def test_nicht_pdf_wird_ignoriert():
    msg = EmailMessage()
    msg["Message-ID"] = "<x@y>"
    msg["From"] = "a@b"
    msg["Subject"] = "x"
    msg.set_content("foo")
    msg.add_attachment(b"PNG-DATA", maintype="image", subtype="png", filename="bild.png")
    result = parser.parse(msg.as_bytes())
    assert result["anhaenge"] == []


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------


def test_links_dedupliziert():
    raw = _build_mail(
        body_plain=(
            "Erst: https://makler.de/x\n"
            "Wieder: https://makler.de/x\n"
            "Anders: https://makler.de/y"
        ),
    )
    result = parser.parse(raw)
    assert result["links"] == ["https://makler.de/x", "https://makler.de/y"]


def test_links_aus_html_body():
    raw = _build_mail(
        body_html='<a href="https://makler.de/expose">Exposé</a>',
    )
    result = parser.parse(raw)
    assert "https://makler.de/expose" in result["links"]


def test_links_trailing_punctuation_strippen():
    raw = _build_mail(
        body_plain="Schau hier: https://makler.de/x. Weiter im Text.",
    )
    result = parser.parse(raw)
    assert result["links"] == ["https://makler.de/x"]


def test_http_und_https_links():
    raw = _build_mail(
        body_plain="http://alt.de/a und https://neu.de/b",
    )
    result = parser.parse(raw)
    assert "http://alt.de/a" in result["links"]
    assert "https://neu.de/b" in result["links"]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_run_alias_funktioniert():
    raw = _build_mail()
    result = parser.run(raw)
    assert "message_id" in result


def test_run_ohne_argument_raises():
    with pytest.raises(ValueError, match="raw_mail"):
        parser.run()
