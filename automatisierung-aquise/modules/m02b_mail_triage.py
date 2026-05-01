"""m02b — Mail Triage (KI-basiert, Sonnet 4.6).

Zwischen m02 (Parser) und m03 (Link Resolver). Lässt eine KI über die Mail
schauen und entscheiden:

1. Ist das überhaupt eine Akquise-Mail (Exposé)?
2. Wo liegt das eigentliche Exposé? (PDF-Anhang Filename oder Link)
3. Wo liegt die Mietaufstellung? (analog)
4. Was ist die Objekt-Adresse? (aus Subject/Body)
5. Welche Anhänge sind Begleitdokumente (NDA, Datenschutz, …)?

Output: TriageResult — strukturiert via Pydantic.

Public API:
    triage(parsed_mail) -> TriageResult | None

Bei API-Fehler / fehlendem Key: Fallback auf alte Logik (Caller wertet aus).
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

import config
from modules.m08_logger import get_logger

log = get_logger(__name__)

_SYSTEM_PROMPT = """Du bist ein Klassifikator für Akquise-E-Mails eines Immobilien-Investors (André Petrov, Petrov Wohnen, Schwerpunkt MFH ab 5 Einheiten in NRW/Ruhrgebiet).

Eingehende Mails sind weitergeleitete Exposés/Angebote von Maklern, Sparkassen, Banken (LBS, Sparkasse, ImmoScout24, von Poll, Vonovia, etc.) — meist als PDF-Anhang oder als Web-Exposé-Link.

Deine Aufgabe pro Mail:

1. **is_expose_mail**: Ist das eine echte Akquise-Mail mit Exposé-Inhalt? Nein, wenn:
   - Reine Marketing-Mail ohne konkretes Objekt
   - Newsletter, Rechnungen, Login-Bestätigungen
   - "Dankeschön, wir haben Ihre Anfrage erhalten" ohne Exposé

2. **objekt_adresse**: Die ECHTE Adresse des angebotenen Objekts (NICHT die Makler-Adresse aus der Signatur).
   - Bevorzuge Subject ("Mehrfamilienhaus in 45147 Essen") wenn das die genauste Info ist
   - Format: "Straße Hausnr, PLZ Stadt" wenn möglich, sonst nur PLZ + Stadt
   - null wenn keine eindeutige Objekt-Adresse erkennbar

3. **expose_attachment_filenames**: Filenames der Anhänge die das HAUPT-EXPOSÉ sind.
   - "PDF-Exposé #20042.pdf" → ja
   - "Hinweise Datenschutz.pdf" → NEIN (Begleitdoku)
   - "NDA.pdf", "Geheimhaltungsvereinbarung.pdf" → NEIN (Formular zum Unterschreiben)

4. **mietaufstellung_attachment_filenames**: Filenames der Anhänge die Mietaufstellung/Mieterliste/Mietmatrix sind.

5. **expose_links**: URLs die zum Web-Exposé (oder zum direkten PDF-Download) führen.
   - `immo.fio.de/webexposee/...` → ja
   - `expose.pdf` direkt → ja
   - `facebook.com/Sparkasse...` → NEIN
   - `immobilienscout24.de/expose/...` → ja
   - Hauptseite des Maklers → NEIN
   - Tracking-Pixel, Bilder → NEIN

6. **begleit_attachment_filenames**: PDFs die zwar mitgeschickt wurden aber NICHT Exposé/Mietliste sind (NDA, Datenschutz, Energieausweis, etc.).

7. **begruendung**: Ein Satz auf Deutsch, warum du so klassifiziert hast.

Sei streng — lieber `is_expose_mail=false` wenn unklar, als Müll-Ordner anlegen."""


class TriageResult(BaseModel):
    is_expose_mail: bool = Field(description="True wenn die Mail ein Akquise-Exposé enthält")
    objekt_adresse: str | None = Field(
        default=None,
        description="Adresse des angebotenen Objekts (NICHT Makler-Adresse). Format: 'Straße Hausnr, PLZ Stadt' oder 'PLZ Stadt'.",
    )
    expose_attachment_filenames: list[str] = Field(
        default_factory=list,
        description="Filenames der Haupt-Exposé-PDFs unter den Anhängen",
    )
    mietaufstellung_attachment_filenames: list[str] = Field(
        default_factory=list,
        description="Filenames der Mietaufstellungs-PDFs unter den Anhängen",
    )
    expose_links: list[str] = Field(
        default_factory=list,
        description="URLs die zum Web-Exposé oder Exposé-PDF führen (max 3, sonst die wichtigsten)",
    )
    begleit_attachment_filenames: list[str] = Field(
        default_factory=list,
        description="PDFs die mitgeschickt wurden aber nicht Exposé/Mietliste sind (NDA, Datenschutz, …)",
    )
    begruendung: str = Field(description="Ein Satz auf Deutsch, warum du so klassifiziert hast")


def triage(parsed_mail: dict) -> TriageResult | None:
    """Lässt Sonnet 4.6 über die Mail schauen und liefert strukturierten Plan.

    Returns None bei API-Fehler / fehlendem Key — Caller fällt auf alte Logik zurück.
    """
    if not config.ANTHROPIC_API_KEY:
        log.warning("Mail-Triage übersprungen: ANTHROPIC_API_KEY fehlt in .env")
        return None

    try:
        import anthropic
    except ImportError:
        log.error("anthropic-Paket nicht installiert")
        return None

    user_content = _build_user_message(parsed_mail)

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.parse(
            model=config.ANTHROPIC_MODEL_TRIAGE,
            max_tokens=2000,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
            output_format=TriageResult,
        )
    except Exception:
        log.exception("Mail-Triage fehlgeschlagen — Fallback auf alte Logik")
        return None

    result: TriageResult = response.parsed_output
    log.info(
        "Triage: is_expose=%s, adresse=%s, expose_pdfs=%d, mietliste_pdfs=%d, expose_links=%d",
        result.is_expose_mail,
        result.objekt_adresse,
        len(result.expose_attachment_filenames),
        len(result.mietaufstellung_attachment_filenames),
        len(result.expose_links),
    )
    log.debug("Triage-Begründung: %s", result.begruendung)

    if hasattr(response, "usage") and response.usage:
        u = response.usage
        log.debug(
            "Triage-Tokens: input=%d, cache_read=%d, cache_write=%d, output=%d",
            getattr(u, "input_tokens", 0),
            getattr(u, "cache_read_input_tokens", 0),
            getattr(u, "cache_creation_input_tokens", 0),
            getattr(u, "output_tokens", 0),
        )

    return result


def _build_user_message(parsed_mail: dict) -> str:
    """Baut den User-Prompt aus den geparsten Mail-Feldern."""
    subject = parsed_mail.get("subject", "")
    von = parsed_mail.get("von", "")
    body = parsed_mail.get("body_plain", "")
    anhaenge: list[Path] = parsed_mail.get("anhaenge", [])
    links: list[str] = parsed_mail.get("links", [])

    anhaenge_lines = [f"  - {p.name}" for p in anhaenge] or ["  (keine)"]
    links_lines = [f"  - {url}" for url in links[:50]] or ["  (keine)"]
    if len(links) > 50:
        links_lines.append(f"  ... +{len(links) - 50} weitere")

    return f"""Mail zur Klassifikation:

=== Subject ===
{subject}

=== Von ===
{von}

=== Body (Plain, gekürzt) ===
{body[:3000]}

=== Anhänge ({len(anhaenge)}) ===
{chr(10).join(anhaenge_lines)}

=== Links ({len(links)}) ===
{chr(10).join(links_lines)}
"""
