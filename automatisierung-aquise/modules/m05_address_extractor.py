"""m05 — Address Extractor.

Aus Exposé-PDF die Objekt-Adresse extrahieren (nicht die Makler-Adresse).

Strategie:
1. PDF → Text via pypdf
2. Adress-Kandidaten via Regex finden (PLZ als Anker)
3. Pro Kandidat Score berechnen anhand Kontext-Wörter:
   - Objekt-Trigger (Lage, Objekt, Anschrift, …) → +
   - Makler-Trigger (Makler, Telefon, @, …) → −
4. Höchster Score gewinnt. Falls Score < `ADDRESS_LLM_FALLBACK_THRESHOLD`
   und Anthropic-API-Key vorhanden → LLM entscheidet zwischen den Kandidaten.

Public API:
    extract(pdf_path) -> dict | None
    extract_from_text(text) -> dict | None  (testfreundlich)
    run(pdf_path) -> dict | None
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

import config
from modules.m08_logger import get_logger

log = get_logger(__name__)

# PLZ als Anker — danach folgt die Stadt (1-4 Wörter, evtl. mit Bindestrich)
_PLZ_CITY_RE = re.compile(
    r"(\d{5})\s+"
    r"([A-ZÄÖÜ][\wäöüß\-]*(?:\s+[A-ZÄÖÜa-zäöü][\wäöüß\-]*){0,3})"
)

# Straße + Hausnummer: 1-4 Wörter dann Nummer.
# Filterung "ist letztes Wort eine Straßen-Endung?" passiert in _find_candidates.
_TOKEN_NUMBER_RE = re.compile(
    r"((?:[A-ZÄÖÜa-zäöü][\wäöüß\-]*\.?\s+){0,3}"
    r"[A-ZÄÖÜa-zäöü][\wäöüß\-]*\.?)\s+"
    r"(\d+\s?[a-zA-Z]?(?:\s?[-/]\s?\d+\s?[a-zA-Z]?)?)\b"
)

_STREET_SUFFIXES = (
    "straße", "strasse", "str", "weg", "allee", "platz",
    "gasse", "ring", "damm", "markt", "ufer", "chaussee", "hof", "berg",
)

# Suchradius vor PLZ, in dem die Straße stehen darf
_STREET_PREFIX_WINDOW = 200

# Scoring
_SCORE_BASELINE = 0.5
_SCORE_OBJEKT_BONUS = 0.25
_SCORE_MAKLER_PENALTY = 0.30
_CONTEXT_BEFORE = 250
_CONTEXT_AFTER = 100


@dataclass(frozen=True)
class Candidate:
    street: str
    number: str
    plz: str
    city: str
    position: int  # Zeichen-Offset im Text

    def normalized(self) -> str:
        # "Musterstr." → "Musterstr"; konsekutive Whitespaces kollabieren
        street = re.sub(r"\s+", " ", self.street.replace(".", "")).strip()
        return f"{street} {self.number}, {self.plz} {self.city}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract(pdf_path: str | Path) -> dict | None:
    text = _pdf_to_text(Path(pdf_path))
    if not text:
        log.warning("Kein Text im PDF: %s", pdf_path)
        return None
    return extract_from_text(text)


def extract_from_text(text: str) -> dict | None:
    candidates = _find_candidates(text)
    if not candidates:
        log.info("Keine Adress-Kandidaten gefunden.")
        return None

    scored = [(c, _score_candidate(text, c.position)) for c in candidates]
    log.debug(
        "Adress-Kandidaten:\n%s",
        "\n".join(f"  {s:.2f}  {c.normalized()}" for c, s in scored),
    )

    # Eindeutig Makler-typisch (negativer Score) → ausschließen
    objekt = [(c, s) for c, s in scored if s > 0.0]
    if not objekt:
        log.info("Alle Kandidaten makler-typisch — keine Objekt-Adresse extrahiert.")
        return None

    best_candidate, best_score = max(objekt, key=lambda x: x[1])

    if best_score >= config.ADDRESS_LLM_FALLBACK_THRESHOLD:
        return {"adresse": best_candidate.normalized(), "confidence": best_score}

    # Score zu niedrig → LLM-Fallback (wenn API-Key vorhanden)
    llm_result = _llm_fallback(text, [c for c, _ in scored])
    if llm_result is not None:
        return llm_result

    # LLM nicht verfügbar oder nicht eindeutig → bester Heuristik-Treffer mit
    # niedriger Confidence
    return {"adresse": best_candidate.normalized(), "confidence": best_score}


def run(pdf_path: str | Path | None = None) -> dict | None:
    """Pipeline-Konvention."""
    if pdf_path is None:
        raise ValueError("pdf_path ist Pflicht für m05_address_extractor.run()")
    return extract(pdf_path)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _pdf_to_text(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        log.exception("PDF-Text-Extraktion fehlgeschlagen: %s", pdf_path)
        return ""


def _find_candidates(text: str) -> list[Candidate]:
    candidates: list[Candidate] = []
    for plz_match in _PLZ_CITY_RE.finditer(text):
        plz = plz_match.group(1)
        city = plz_match.group(2).strip()
        # Stadt-Trim: Bei mehreren Wörtern kann das Pattern zu gierig sein
        # → bei "Newline" oder ", " abschneiden
        city = re.split(r"[\n,;]", city, maxsplit=1)[0].strip()

        # Straße im Fenster vor PLZ suchen — letztes Match (= näher an PLZ).
        # Wir matchen "1-4 Wörter + Hausnummer" und filtern nachträglich auf
        # eine deutsche Straßen-Endung. Das fängt sowohl "Musterstraße 12"
        # (Endung am Wort) als auch "Am Markt 7" (Endung als eigenes Wort).
        prefix_start = max(0, plz_match.start() - _STREET_PREFIX_WINDOW)
        prefix = text[prefix_start : plz_match.start()]
        last_match = None
        for m in _TOKEN_NUMBER_RE.finditer(prefix):
            words = m.group(1).strip().rstrip(".")
            if not words:
                continue
            last_word = words.split()[-1].lower().rstrip(".")
            if any(last_word.endswith(suffix) for suffix in _STREET_SUFFIXES):
                last_match = m
        if last_match is None:
            continue

        street = re.sub(r"\s+", " ", last_match.group(1)).strip()
        number = re.sub(r"\s+", "", last_match.group(2))

        candidates.append(
            Candidate(
                street=street,
                number=number,
                plz=plz,
                city=city,
                position=prefix_start + last_match.start(),
            )
        )

    # Duplikate entfernen (gleiche normalisierte Adresse)
    seen: set[str] = set()
    unique: list[Candidate] = []
    for c in candidates:
        key = c.normalized()
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def _score_candidate(text: str, position: int) -> float:
    start = max(0, position - _CONTEXT_BEFORE)
    end = min(len(text), position + _CONTEXT_AFTER)
    ctx = text[start:end].lower()

    score = _SCORE_BASELINE
    for trigger in config.ADDRESS_OBJEKT_TRIGGER:
        if trigger.lower() in ctx:
            score += _SCORE_OBJEKT_BONUS
    for trigger in config.ADDRESS_MAKLER_TRIGGER:
        if trigger.lower() in ctx:
            score -= _SCORE_MAKLER_PENALTY

    return max(0.0, min(1.0, score))


def _llm_fallback(text: str, candidates: list[Candidate]) -> dict | None:
    if not config.ANTHROPIC_API_KEY:
        log.warning("LLM-Fallback nicht möglich: ANTHROPIC_API_KEY fehlt.")
        return None
    if not candidates:
        return None

    try:
        import anthropic
    except ImportError:
        log.error("anthropic-Paket nicht installiert.")
        return None

    options = "\n".join(
        f"{i + 1}. {c.normalized()}" for i, c in enumerate(candidates)
    )
    prompt = (
        "Du bekommst Text aus einem deutschen Immobilien-Exposé und eine Liste "
        "extrahierter Adressen. Welche Nummer ist die OBJEKT-Adresse "
        "(Adresse der angebotenen Immobilie), nicht die Makler-Adresse? "
        "Antworte ausschließlich mit der Zahl, sonst nichts.\n\n"
        f"=== Exposé-Text (Auszug) ===\n{text[:3000]}\n\n"
        f"=== Kandidaten ===\n{options}\n\n"
        "Antwort:"
    )

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response.content[0].text.strip()
    except Exception:
        log.exception("LLM-Fallback fehlgeschlagen.")
        return None

    match = re.search(r"\d+", answer)
    if not match:
        log.warning("LLM-Antwort nicht parsebar: %s", answer)
        return None

    idx = int(match.group(0)) - 1
    if not (0 <= idx < len(candidates)):
        log.warning("LLM-Antwort außerhalb der Kandidaten-Liste: %s", answer)
        return None

    log.info("LLM wählte Kandidat #%d: %s", idx + 1, candidates[idx].normalized())
    return {"adresse": candidates[idx].normalized(), "confidence": 0.95}
