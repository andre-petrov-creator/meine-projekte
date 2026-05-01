"""m04 — File Classifier.

Klassifiziert eine Datei (PDF oder Bild) anhand ihres Filenames (Heuristik).
Regeln aus `config.PDF_CLASSIFIER_RULES` (Reihenfolge = Priorität).

Public API:
    classify(path) -> {"typ": str, "confidence": float}
    run(path) -> dict   (Pipeline-Konvention)

Mögliche Typen:
    expose, mieterliste, energieausweis, modernisierung, sonstiges

Confidence:
    1.0 bei klarem Match
    0.5 bei `sonstiges` (kein Match)
"""
from __future__ import annotations

import re
from pathlib import Path

import config
from modules.m08_logger import get_logger

log = get_logger(__name__)

DEFAULT_TYPE = "sonstiges"
CONFIDENCE_MATCH = 1.0
CONFIDENCE_DEFAULT = 0.5


def classify(pdf_path: str | Path) -> dict:
    path = Path(pdf_path)
    name = path.stem  # ohne .pdf

    for pattern, typ in config.PDF_CLASSIFIER_RULES:
        if re.search(pattern, name, re.IGNORECASE):
            log.debug("Klassifiziert: %s → %s", path.name, typ)
            return {"typ": typ, "confidence": CONFIDENCE_MATCH}

    log.debug("Klassifiziert: %s → %s (kein Match)", path.name, DEFAULT_TYPE)
    return {"typ": DEFAULT_TYPE, "confidence": CONFIDENCE_DEFAULT}


def run(pdf_path: str | Path | None = None) -> dict:
    """Pipeline-Konvention."""
    if pdf_path is None:
        raise ValueError("pdf_path ist Pflicht für m04_pdf_classifier.run()")
    return classify(pdf_path)
