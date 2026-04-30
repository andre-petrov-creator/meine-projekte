"""Tests für m06_folder_manager."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from modules import m06_folder_manager as fm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def base_dir(tmp_path):
    """Sandbox-Basis-Ordner pro Test."""
    base = tmp_path / "Objekte"
    base.mkdir()
    return base


@pytest.fixture
def fake_pdfs(tmp_path):
    """Erzeugt 3 Fake-PDFs unter tmp_path/sources und gibt File-Liste zurück."""
    src = tmp_path / "sources"
    src.mkdir()

    files = []
    for name, typ, content in [
        ("expose_orig.pdf", "expose", b"%PDF expose"),
        ("mieterliste_orig.pdf", "mieterliste", b"%PDF mieter"),
        ("energieausweis_orig.pdf", "energieausweis", b"%PDF energie"),
    ]:
        p = src / name
        p.write_bytes(content)
        files.append({"path": p, "typ": typ})
    return files


# ---------------------------------------------------------------------------
# Akzeptanzkriterien aus dem Plan
# ---------------------------------------------------------------------------


def test_adresse_plus_3_files_legt_ordner_an(base_dir, fake_pdfs):
    """Adresse 'Musterstr 12, 44137 Dortmund' + 3 Files → Ordner mit 3 Files + meta.json."""
    target = fm.store(
        adresse="Musterstr 12, 44137 Dortmund",
        files=fake_pdfs,
        meta={"message_id": "abc@x", "von": "andre-petrov@web.de", "subject": "Test"},
        base_folder=base_dir,
    )

    assert target.exists()
    assert target.name == "Musterstr 12, 44137 Dortmund"

    # 3 PDFs + 1 meta.json
    files_in_target = sorted(p.name for p in target.iterdir())
    assert "_meta.json" in files_in_target
    assert "Exposé.pdf" in files_in_target
    assert "Mieterliste.pdf" in files_in_target
    assert "Energieausweis.pdf" in files_in_target


def test_doppelter_aufruf_erzeugt_suffix_2(base_dir, fake_pdfs):
    fm.store(adresse="Musterstr 12, 44137 Dortmund", files=fake_pdfs[:1], base_folder=base_dir)
    target2 = fm.store(
        adresse="Musterstr 12, 44137 Dortmund", files=fake_pdfs[:1], base_folder=base_dir
    )

    assert target2.name == "Musterstr 12, 44137 Dortmund_2"
    assert target2.exists()


def test_dreifacher_aufruf_erzeugt_suffix_3(base_dir, fake_pdfs):
    fm.store(adresse="X", files=fake_pdfs[:1], base_folder=base_dir)
    fm.store(adresse="X", files=fake_pdfs[:1], base_folder=base_dir)
    target3 = fm.store(adresse="X", files=fake_pdfs[:1], base_folder=base_dir)
    assert target3.name == "X_3"


def test_none_adresse_erzeugt_timestamp_ordner(base_dir, fake_pdfs):
    target = fm.store(adresse=None, files=fake_pdfs[:1], base_folder=base_dir)

    # Format: YYYY-MM-DD_HH-MM-SS_unbekannt
    assert target.name.endswith("_unbekannt")
    assert datetime.strptime(target.name.replace("_unbekannt", ""), "%Y-%m-%d_%H-%M-%S")


def test_leere_adresse_erzeugt_timestamp_ordner(base_dir, fake_pdfs):
    target = fm.store(adresse="", files=fake_pdfs[:1], base_folder=base_dir)
    assert target.name.endswith("_unbekannt")


# ---------------------------------------------------------------------------
# Naming nach Klassifikation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "typ, expected",
    [
        ("expose", "Exposé.pdf"),
        ("mieterliste", "Mieterliste.pdf"),
        ("energieausweis", "Energieausweis.pdf"),
        ("modernisierung", "Modernisierung.pdf"),
    ],
)
def test_naming_nach_typ(base_dir, tmp_path, typ, expected):
    src = tmp_path / "src.pdf"
    src.write_bytes(b"%PDF")
    target = fm.store(
        adresse="A 1, 12345 X",
        files=[{"path": src, "typ": typ}],
        base_folder=base_dir,
    )
    assert (target / expected).exists()


def test_sonstiges_behaelt_originalnamen(base_dir, tmp_path):
    src = tmp_path / "Sonderdoku-2026.pdf"
    src.write_bytes(b"%PDF")
    target = fm.store(
        adresse="A 1, 12345 X",
        files=[{"path": src, "typ": "sonstiges"}],
        base_folder=base_dir,
    )
    assert (target / "Sonderdoku-2026.pdf").exists()


def test_mehrere_dateien_gleichen_typs_werden_eindeutig(base_dir, tmp_path):
    src1 = tmp_path / "expose-a.pdf"
    src2 = tmp_path / "expose-b.pdf"
    src1.write_bytes(b"%PDF-A")
    src2.write_bytes(b"%PDF-B")

    target = fm.store(
        adresse="X 1, 12345 Y",
        files=[
            {"path": src1, "typ": "expose"},
            {"path": src2, "typ": "expose"},
        ],
        base_folder=base_dir,
    )
    names = sorted(p.name for p in target.iterdir() if p.suffix == ".pdf")
    assert names == ["Exposé.pdf", "Exposé_2.pdf"]


# ---------------------------------------------------------------------------
# Meta.json
# ---------------------------------------------------------------------------


def test_meta_json_hat_alle_felder(base_dir, fake_pdfs):
    target = fm.store(
        adresse="Musterstr 12, 44137 Dortmund",
        files=fake_pdfs,
        meta={
            "message_id": "msg@x",
            "von": "andre@y",
            "subject": "Exposé",
            "timestamp": "2026-04-30T10:00:00",
        },
        base_folder=base_dir,
    )
    meta = json.loads((target / "_meta.json").read_text(encoding="utf-8"))
    assert meta["adresse"] == "Musterstr 12, 44137 Dortmund"
    assert meta["message_id"] == "msg@x"
    assert meta["von"] == "andre@y"
    assert meta["subject"] == "Exposé"
    assert meta["timestamp"] == "2026-04-30T10:00:00"
    assert len(meta["files"]) == 3


def test_meta_json_default_timestamp(base_dir, fake_pdfs):
    target = fm.store(
        adresse="X 1, 12345 Y",
        files=fake_pdfs[:1],
        meta={"message_id": "x"},  # kein timestamp
        base_folder=base_dir,
    )
    meta = json.loads((target / "_meta.json").read_text(encoding="utf-8"))
    # default = jetzt → muss parsebar sein
    assert datetime.fromisoformat(meta["timestamp"])


def test_meta_files_haben_name_typ_source(base_dir, fake_pdfs):
    target = fm.store(adresse="X 1, 12345 Y", files=fake_pdfs, base_folder=base_dir)
    meta = json.loads((target / "_meta.json").read_text(encoding="utf-8"))
    expose_entry = next(f for f in meta["files"] if f["typ"] == "expose")
    assert expose_entry["name"] == "Exposé.pdf"
    assert expose_entry["source"] == "expose_orig.pdf"


def test_meta_json_ohne_meta_dict(base_dir, fake_pdfs):
    """meta=None ist erlaubt — Defaults greifen."""
    target = fm.store(adresse="X 1, 12345 Y", files=fake_pdfs[:1], base_folder=base_dir)
    meta = json.loads((target / "_meta.json").read_text(encoding="utf-8"))
    assert meta["message_id"] is None
    assert meta["von"] is None


# ---------------------------------------------------------------------------
# Sanitizing
# ---------------------------------------------------------------------------


def test_sonderzeichen_in_adresse_gesanitized(base_dir, fake_pdfs):
    target = fm.store(
        adresse='Bad/Path:Name<x>"y"',
        files=fake_pdfs[:1],
        base_folder=base_dir,
    )
    # Keine Pfad-gefährlichen Zeichen im Ordnernamen
    assert all(c not in target.name for c in '<>:"/\\|?*')


# ---------------------------------------------------------------------------
# Robustheit
# ---------------------------------------------------------------------------


def test_fehlende_quelldatei_wird_uebersprungen(base_dir, tmp_path):
    real = tmp_path / "real.pdf"
    real.write_bytes(b"%PDF")

    target = fm.store(
        adresse="X 1, 12345 Y",
        files=[
            {"path": tmp_path / "missing.pdf", "typ": "expose"},  # gibt's nicht
            {"path": real, "typ": "mieterliste"},
        ],
        base_folder=base_dir,
    )

    pdfs = sorted(p.name for p in target.iterdir() if p.suffix == ".pdf")
    assert pdfs == ["Mieterliste.pdf"]


def test_dateien_werden_nicht_verschoben_sondern_kopiert(base_dir, tmp_path):
    src = tmp_path / "expose.pdf"
    src.write_bytes(b"%PDF")
    fm.store(
        adresse="X 1, 12345 Y",
        files=[{"path": src, "typ": "expose"}],
        base_folder=base_dir,
    )
    assert src.exists()  # Original liegt noch da


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def test_run_alias(base_dir, fake_pdfs):
    target = fm.run(adresse="X 1, 12345 Y", files=fake_pdfs[:1], base_folder=base_dir)
    assert target.exists()


def test_run_ohne_files_raises():
    with pytest.raises(ValueError, match="files"):
        fm.run(adresse="X")
