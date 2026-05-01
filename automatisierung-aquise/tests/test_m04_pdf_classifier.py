"""Tests für m04_pdf_classifier."""
from __future__ import annotations

import pytest

from modules import m04_pdf_classifier as classifier


# ---------------------------------------------------------------------------
# Akzeptanzkriterium: 5 Filenames pro Typ
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        "expose.pdf",
        "Exposé MFH Dortmund.pdf",
        "Objekt-Expose-12345.pdf",
        "EXPOSE_kurz.pdf",
        "Anhang-Exposé-final.pdf",
    ],
)
def test_klassifiziert_als_expose(filename):
    assert classifier.classify(filename)["typ"] == "expose"


@pytest.mark.parametrize(
    "filename",
    [
        "Mieterliste.pdf",
        "mietauflistung.pdf",
        "Mieterauflistung-2026.pdf",
        "Mietmatrix.pdf",
        "Mieten_Stand_April.pdf",
    ],
)
def test_klassifiziert_als_mieterliste(filename):
    assert classifier.classify(filename)["typ"] == "mieterliste"


@pytest.mark.parametrize(
    "filename",
    [
        "Energieausweis.pdf",
        "energie-ausweis.pdf",
        "EPC.pdf",
        "Energie_Bedarf.pdf",
        "Objekt-Energieausweis-V2.pdf",
    ],
)
def test_klassifiziert_als_energieausweis(filename):
    assert classifier.classify(filename)["typ"] == "energieausweis"


@pytest.mark.parametrize(
    "filename",
    [
        "Modernisierung.pdf",
        "Modernisierungs-Liste.pdf",
        "Sanierung-2025.pdf",
        "Renovierungsplan.pdf",
        "modern_arbeiten.pdf",
    ],
)
def test_klassifiziert_als_modernisierung(filename):
    assert classifier.classify(filename)["typ"] == "modernisierung"


# ---------------------------------------------------------------------------
# Sonstiges + Akzeptanzkriterium "Doku.pdf → sonstiges"
# ---------------------------------------------------------------------------


def test_doku_pdf_ist_sonstiges():
    """Akzeptanzkriterium aus dem Plan."""
    result = classifier.classify("Doku.pdf")
    assert result["typ"] == "sonstiges"
    assert result["confidence"] == 0.5


@pytest.mark.parametrize(
    "filename",
    [
        "Anschreiben.pdf",
        "agb.pdf",
        "kontaktdaten.pdf",
        "vermarktung.pdf",
        "info.pdf",
    ],
)
def test_unbekannte_filenames_sonstiges(filename):
    result = classifier.classify(filename)
    assert result["typ"] == "sonstiges"
    assert result["confidence"] == 0.5


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


def test_confidence_bei_match_ist_eins():
    assert classifier.classify("expose.pdf")["confidence"] == 1.0


def test_confidence_bei_sonstiges_ist_halb():
    assert classifier.classify("xyz.pdf")["confidence"] == 0.5


# ---------------------------------------------------------------------------
# Priorität bei Mehrfachmatch (Reihenfolge in PDF_CLASSIFIER_RULES)
# ---------------------------------------------------------------------------


def test_prioritaet_expose_vor_mieterliste():
    """Reihenfolge: expose > mieterliste > energie > modern."""
    # Filename matcht beide Regeln → erste gewinnt
    assert classifier.classify("Expose-mit-Mietliste.pdf")["typ"] == "expose"


def test_prioritaet_mieterliste_vor_energieausweis():
    assert classifier.classify("Mietliste-Energie.pdf")["typ"] == "mieterliste"


# ---------------------------------------------------------------------------
# Case-Insensitivity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", ["EXPOSE.pdf", "expose.pdf", "Expose.pdf", "ExPoSe.pdf"])
def test_case_insensitive(filename):
    assert classifier.classify(filename)["typ"] == "expose"


# ---------------------------------------------------------------------------
# Pfad-Eingabe (string oder Path)
# ---------------------------------------------------------------------------


def test_akzeptiert_string():
    result = classifier.classify("expose.pdf")
    assert result["typ"] == "expose"


def test_akzeptiert_path(tmp_path):
    p = tmp_path / "expose.pdf"
    p.write_bytes(b"%PDF")
    result = classifier.classify(p)
    assert result["typ"] == "expose"


def test_voller_pfad_nutzt_nur_filename(tmp_path):
    p = tmp_path / "expose.pdf"  # tmp_path Verzeichnis enthält "modern" o.ä. nicht
    p.write_bytes(b"%PDF")
    result = classifier.classify(p)
    assert result["typ"] == "expose"


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_run_alias():
    assert classifier.run("expose.pdf")["typ"] == "expose"


def test_run_ohne_argument_raises():
    with pytest.raises(ValueError, match="pdf_path"):
        classifier.run()


# ---------------------------------------------------------------------------
# Bilder
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("Exposé-Foto.jpg", "expose"),
        ("Mieterliste.png", "mieterliste"),
        ("expose-scan.heic", "expose"),
        ("logo.jpg", "sonstiges"),
    ],
)
def test_klassifiziert_bilder_per_filename(filename, expected):
    assert classifier.classify(filename)["typ"] == expected
