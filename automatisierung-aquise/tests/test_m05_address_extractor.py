"""Tests für m05_address_extractor."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import config
from modules import m05_address_extractor as extractor

# ---------------------------------------------------------------------------
# Test-Texte (simulieren PDF-Inhalte)
# ---------------------------------------------------------------------------

EXPOSE_DORTMUND = """
Exposé Mehrfamilienhaus

Lage:
Musterstraße 12
44137 Dortmund

12 Wohneinheiten, 850 m² Wohnfläche.

Anbieter / Makler:
Immobilien Schmidt GmbH
Hauptstr. 99
44135 Dortmund
Tel. 0231/123456
kontakt@schmidt-immobilien.de
"""

EXPOSE_ESSEN = """
Objekt-Beschreibung

Anschrift des Objekts: Bahnhofallee 23-25, 45127 Essen

Das Objekt verfügt über 8 Wohneinheiten.

---
Vermarktung über:
Müller Real Estate
Marktstraße 5, 45127 Essen
Telefon: 0201/555-1234
E-Mail: info@mueller-realestate.de
"""

EXPOSE_KOELN_NUR_OBJEKT = """
Wohn- und Geschäftshaus

Standort: Am Marktplatz 7
50667 Köln

Baujahr 1965, 6 WE.
"""

EXPOSE_OHNE_ADRESSE = """
Mehrfamilienhaus, 8 Einheiten.
Baujahr 1962, voll vermietet.
Kontakt: 0201/123-456
"""

EXPOSE_NUR_MAKLER = """
Liebe Interessenten,

bitte wenden Sie sich an:
Hans Müller Immobilien
Maklerweg 99
12345 Berlin
Tel. 030/9999999
"""


# ---------------------------------------------------------------------------
# Akzeptanzkriterien aus dem Plan
# ---------------------------------------------------------------------------


def test_dortmund_objekt_gewinnt_gegen_makler():
    result = extractor.extract_from_text(EXPOSE_DORTMUND)
    assert result is not None
    assert "Musterstraße 12" in result["adresse"]
    assert "44137 Dortmund" in result["adresse"]


def test_essen_objekt_gewinnt_gegen_makler():
    result = extractor.extract_from_text(EXPOSE_ESSEN)
    assert result is not None
    assert "Bahnhofallee 23-25" in result["adresse"]
    assert "45127 Essen" in result["adresse"]


def test_koeln_nur_objekt_adresse():
    result = extractor.extract_from_text(EXPOSE_KOELN_NUR_OBJEKT)
    assert result is not None
    assert "Am Marktplatz 7" in result["adresse"]
    assert "50667 Köln" in result["adresse"]


def test_ohne_adresse_returns_none():
    assert extractor.extract_from_text(EXPOSE_OHNE_ADRESSE) is None


def test_nur_makler_adresse_returns_none(monkeypatch):
    """Plan: 'wenn alle Treffer makler-typisch oder kein Treffer → None'.
    Sicherstellen dass LLM-Fallback nicht unbeabsichtigt anspringt."""
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")  # kein LLM
    assert extractor.extract_from_text(EXPOSE_NUR_MAKLER) is None


# ---------------------------------------------------------------------------
# Normalisierung
# ---------------------------------------------------------------------------


def test_normalisierung_punkt_entfernen():
    """Plan: 'Musterstr. 12' → 'Musterstr 12, 44137 Dortmund'."""
    text = """
    Lage:
    Musterstr. 12
    44137 Dortmund
    """
    result = extractor.extract_from_text(text)
    assert result["adresse"] == "Musterstr 12, 44137 Dortmund"


def test_normalisierung_whitespace_kollabiert():
    text = """
    Lage:
    Musterstraße   12
    44137  Dortmund
    """
    result = extractor.extract_from_text(text)
    assert "Musterstraße 12, 44137 Dortmund" in result["adresse"]


# ---------------------------------------------------------------------------
# Adressformat-Varianten
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "address_block, expected_substring",
    [
        ("Lage: Hauptstraße 5, 44137 Dortmund", "Hauptstraße 5"),
        ("Objekt: Hauptstr. 5a, 44137 Dortmund", "Hauptstr 5a"),
        ("Anschrift: Bahnhofweg 12-14, 44137 Dortmund", "Bahnhofweg 12-14"),
        ("Standort: Am Markt 7, 44137 Dortmund", "Am Markt 7"),
        ("Lage: Schillerring 8/2, 44137 Dortmund", "Schillerring 8/2"),
    ],
)
def test_strassen_varianten(address_block, expected_substring):
    result = extractor.extract_from_text(address_block)
    assert result is not None, f"Keine Adresse in: {address_block}"
    assert expected_substring in result["adresse"]


# ---------------------------------------------------------------------------
# Scoring / Trigger-Heuristik
# ---------------------------------------------------------------------------


def test_objekt_trigger_erhoeht_score():
    obj_text = "Lage: Musterstraße 12, 44137 Dortmund"
    plain_text = "Musterstraße 12, 44137 Dortmund"

    # Position des Adress-Anfangs in beiden Strings
    obj_pos = obj_text.find("Musterstraße")
    plain_pos = plain_text.find("Musterstraße")

    score_with_trigger = extractor._score_candidate(obj_text, obj_pos)
    score_without = extractor._score_candidate(plain_text, plain_pos)

    assert score_with_trigger > score_without


def test_makler_trigger_senkt_score():
    makler_text = "Kontakt: Hans Müller, Telefon 030/123456, Hauptstr. 5, 12345 Berlin"
    pos = makler_text.find("Hauptstr")
    score = extractor._score_candidate(makler_text, pos)
    assert score < 0.5


# ---------------------------------------------------------------------------
# Mehrere Kandidaten — höchster Score gewinnt
# ---------------------------------------------------------------------------


def test_mehrere_kandidaten_hoechster_score_gewinnt():
    text = """
    Lage des Objekts: Musterstraße 12, 44137 Dortmund

    Anbieter (Makler): Vertriebsstr. 99, 80331 München, Tel. 089/9999
    """
    result = extractor.extract_from_text(text)
    assert result is not None
    assert "Musterstraße 12" in result["adresse"]
    assert "44137 Dortmund" in result["adresse"]


# ---------------------------------------------------------------------------
# LLM-Fallback
# ---------------------------------------------------------------------------


def test_llm_fallback_wird_aufgerufen_bei_niedriger_confidence(monkeypatch):
    """Bei mehrdeutigen Texten → LLM entscheidet."""
    # Text ohne klare Trigger — beide Adressen sehen gleich aus
    text = (
        "Mehrfamilienhaus\n"
        "Adresse: Musterstraße 12, 44137 Dortmund\n"
        "Adresse: Anbieterweg 5, 60311 Frankfurt\n"
    )

    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "fake-key")
    monkeypatch.setattr(config, "ADDRESS_LLM_FALLBACK_THRESHOLD", 0.99)

    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="1")]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    with patch("anthropic.Anthropic", return_value=fake_client):
        result = extractor.extract_from_text(text)

    assert result is not None
    assert "Musterstraße 12" in result["adresse"]
    assert result["confidence"] == 0.95
    fake_client.messages.create.assert_called_once()


def test_llm_fallback_kein_api_key(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    assert extractor._llm_fallback("text", []) is None


def test_llm_fallback_unparsebare_antwort(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "fake")

    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="ich weiß nicht")]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    cand = extractor.Candidate(
        street="Musterstr", number="1", plz="12345", city="Berlin", position=0
    )
    with patch("anthropic.Anthropic", return_value=fake_client):
        assert extractor._llm_fallback("text", [cand]) is None


def test_llm_fallback_index_out_of_range(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "fake")

    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="42")]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    cand = extractor.Candidate(
        street="Musterstr", number="1", plz="12345", city="Berlin", position=0
    )
    with patch("anthropic.Anthropic", return_value=fake_client):
        assert extractor._llm_fallback("text", [cand]) is None


# ---------------------------------------------------------------------------
# PDF-Pfad-Variante (extract statt extract_from_text)
# ---------------------------------------------------------------------------


def test_extract_mit_pdf_pfad(monkeypatch):
    monkeypatch.setattr(
        extractor,
        "_pdf_to_text",
        lambda p: "Lage: Musterstraße 12, 44137 Dortmund",
    )
    result = extractor.extract("/fake/path.pdf")
    assert result is not None
    assert "Musterstraße 12" in result["adresse"]


def test_extract_leeres_pdf_returns_none(monkeypatch):
    monkeypatch.setattr(extractor, "_pdf_to_text", lambda p: "")
    assert extractor.extract("/fake/empty.pdf") is None


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_run_alias(monkeypatch):
    monkeypatch.setattr(
        extractor,
        "_pdf_to_text",
        lambda p: "Lage: Musterstraße 12, 44137 Dortmund",
    )
    result = extractor.run("/fake/path.pdf")
    assert result is not None


def test_run_ohne_argument_raises():
    with pytest.raises(ValueError, match="pdf_path"):
        extractor.run()
