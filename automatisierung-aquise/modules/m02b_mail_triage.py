"""m02b — Mail Triage (KI-basiert, Sonnet 4.6, Vision).

Zwischen m02 (Parser) und m03 (Link Resolver). Lässt eine KI über die Mail
schauen — inklusive Bilder via Vision — und entscheiden:

1. Wo liegt das eigentliche Exposé? (PDF-Anhang, Bild oder Link)
2. Wo liegt die Mietaufstellung? (analog)
3. Was ist die Objekt-Adresse? (aus Subject/Body/Bild)
4. Welche Anhänge sind Begleitdokumente (NDA, Datenschutz, …)?

Grundannahme: Jede eingehende Mail ist eine Akquise-Mail. Es gibt kein
`is_expose_mail`-Skip mehr. Der Caller (main.py) entscheidet via Hard-Fail-Check,
ob nichts Verwertbares extrahierbar war.

Output: TriageResult — strukturiert via Pydantic.

Public API:
    triage(parsed_mail) -> TriageResult | None

Bei API-Fehler / fehlendem Key: None → Caller fällt auf Filename-Heuristik zurück.
"""
from __future__ import annotations

import base64
from pathlib import Path

from pydantic import BaseModel, Field

import config
from modules.m08_logger import get_logger

log = get_logger(__name__)

_SYSTEM_PROMPT = """Du bist ein Klassifikator für Akquise-E-Mails eines Immobilien-Investors (André Petrov, Petrov Wohnen, Schwerpunkt MFH ab 5 Einheiten in NRW/Ruhrgebiet).

GRUNDANNAHME: Jede eingehende Mail enthält Exposé-Inhalt zu einer Immobilie. Sie kommt von Maklern, Sparkassen, Banken (LBS, Sparkasse, ImmoScout24, von Poll, Vonovia, etc.) — entweder als PDF-Anhang, als Bild (Foto/Scan eines Exposés), als Inline-Bild im HTML-Body oder als Web-Exposé-Link.

Du bekommst Subject, Absender, Body, Filenames der Anhänge UND die Bilder selbst (wenn vorhanden) als Vision-Input. Lies die Bilder genauso ernst wie Text — ein gescanntes/abfotografiertes Exposé ist gleichwertig zu einem Text-PDF.

Deine Aufgabe pro Mail:

1. **objekt_adresse**: Die ECHTE Adresse des angebotenen Objekts (NICHT die Makler-Adresse aus der Signatur).
   - Bevorzuge die genaueste Quelle: Bild > Subject > Body
   - Format: "Straße Hausnr, PLZ Stadt" wenn möglich, sonst nur PLZ + Stadt
   - null, wenn keine eindeutige Objekt-Adresse erkennbar (auch nach Bild-Analyse)

2. **expose_attachment_filenames**: Filenames der PDF-Anhänge die das HAUPT-EXPOSÉ sind.
   - "PDF-Exposé #20042.pdf" → ja
   - "Hinweise Datenschutz.pdf" → NEIN (Begleitdoku)
   - "NDA.pdf", "Geheimhaltungsvereinbarung.pdf" → NEIN (Formular zum Unterschreiben)

3. **expose_image_filenames**: Filenames der BILDER die das Haupt-Exposé sind (gescannte/abfotografierte Exposés, Lagepläne, Objekt-Fotos mit Eckdaten).
   - Logos, Signatur-Bilder, Tracking-Pixel → NEIN

4. **mietaufstellung_attachment_filenames** + **mietaufstellung_image_filenames**: Mietaufstellung/Mieterliste/Mietmatrix als PDF bzw. Bild.

5. **expose_links**: URLs die zum Web-Exposé (oder direkten PDF-Download) führen.
   - `immo.fio.de/webexposee/...` → ja
   - `expose.pdf` direkt → ja
   - `facebook.com/Sparkasse...` → NEIN
   - `immobilienscout24.de/expose/...` → ja
   - Hauptseite des Maklers → NEIN
   - Tracking-Pixel, Bilder → NEIN

6. **begleit_attachment_filenames** + **begleit_image_filenames**: Mitgeschickte PDFs/Bilder die NICHT Exposé/Mietliste sind (NDA, Datenschutz, Energieausweis, Logo-Bilder, etc.).

7. **begruendung**: Ein Satz auf Deutsch, warum du so klassifiziert hast.

Wichtig: Du darfst KEIN Feld "ist das Akquise?" beantworten. Verarbeite jede Mail. Wenn wirklich nichts Brauchbares drin ist, lasse die Listen leer und `objekt_adresse=null` — der Caller alarmiert dann."""


class TriageResult(BaseModel):
    objekt_adresse: str | None = Field(
        default=None,
        description="Adresse des angebotenen Objekts (NICHT Makler-Adresse). Format: 'Straße Hausnr, PLZ Stadt' oder 'PLZ Stadt'.",
    )
    expose_attachment_filenames: list[str] = Field(
        default_factory=list,
        description="Filenames der Haupt-Exposé-PDFs unter den Anhängen",
    )
    expose_image_filenames: list[str] = Field(
        default_factory=list,
        description="Filenames der Bilder die das Haupt-Exposé darstellen (gescannt/abfotografiert)",
    )
    mietaufstellung_attachment_filenames: list[str] = Field(
        default_factory=list,
        description="Filenames der Mietaufstellungs-PDFs unter den Anhängen",
    )
    mietaufstellung_image_filenames: list[str] = Field(
        default_factory=list,
        description="Filenames der Bilder die eine Mietaufstellung darstellen",
    )
    expose_links: list[str] = Field(
        default_factory=list,
        description="URLs die zum Web-Exposé oder Exposé-PDF führen (max 3, sonst die wichtigsten)",
    )
    begleit_attachment_filenames: list[str] = Field(
        default_factory=list,
        description="PDFs die mitgeschickt wurden aber nicht Exposé/Mietliste sind (NDA, Datenschutz, …)",
    )
    begleit_image_filenames: list[str] = Field(
        default_factory=list,
        description="Bilder die mitgeschickt wurden aber nicht Exposé/Mietliste sind (Logos, Signatur, …)",
    )
    begruendung: str = Field(description="Ein Satz auf Deutsch, warum du so klassifiziert hast")


def triage(parsed_mail: dict) -> TriageResult | None:
    """Lässt Sonnet 4.6 (mit Vision) über die Mail schauen und liefert strukturierten Plan.

    Returns None bei API-Fehler / fehlendem Key — Caller fällt auf Filename-Heuristik zurück.
    """
    if not config.ANTHROPIC_API_KEY:
        log.warning("Mail-Triage übersprungen: ANTHROPIC_API_KEY fehlt in .env")
        return None

    try:
        import anthropic
    except ImportError:
        log.error("anthropic-Paket nicht installiert")
        return None

    user_content = _build_user_content(parsed_mail)

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
        log.exception("Mail-Triage fehlgeschlagen — Fallback auf Filename-Heuristik")
        return None

    result: TriageResult = response.parsed_output
    log.info(
        "Triage: adresse=%s, expose_pdfs=%d, expose_imgs=%d, mietliste_pdfs=%d, mietliste_imgs=%d, expose_links=%d",
        result.objekt_adresse,
        len(result.expose_attachment_filenames),
        len(result.expose_image_filenames),
        len(result.mietaufstellung_attachment_filenames),
        len(result.mietaufstellung_image_filenames),
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


def _build_user_content(parsed_mail: dict) -> list[dict]:
    """Baut Multi-Modal-Content (Text + Bilder) für die Anthropic API.

    Bilder werden als base64-image-Blocks vorangestellt (max TRIAGE_MAX_IMAGES),
    danach folgt der Text-Block mit Subject/Body/Filenames.
    """
    bilder: list[Path] = parsed_mail.get("bilder", [])[: config.TRIAGE_MAX_IMAGES]

    blocks: list[dict] = []
    for img_path in bilder:
        block = _image_block(img_path)
        if block is not None:
            blocks.append(block)

    blocks.append({"type": "text", "text": _build_text_message(parsed_mail)})
    return blocks


def _image_block(img_path: Path) -> dict | None:
    """Liest JPG → base64, baut Anthropic-Image-Block. Skipt zu große Dateien."""
    try:
        data = img_path.read_bytes()
    except Exception:
        log.exception("Bild für Triage nicht lesbar: %s", img_path.name)
        return None

    if len(data) > config.IMAGE_MAX_BYTES:
        log.warning(
            "Bild %s zu groß für Vision (%d Bytes > %d) — übersprungen",
            img_path.name,
            len(data),
            config.IMAGE_MAX_BYTES,
        )
        return None

    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": base64.b64encode(data).decode("ascii"),
        },
    }


def _build_text_message(parsed_mail: dict) -> str:
    """Baut den Text-Teil aus den geparsten Mail-Feldern."""
    subject = parsed_mail.get("subject", "")
    von = parsed_mail.get("von", "")
    body = parsed_mail.get("body_plain", "")
    anhaenge: list[Path] = parsed_mail.get("anhaenge", [])
    bilder: list[Path] = parsed_mail.get("bilder", [])
    links: list[str] = parsed_mail.get("links", [])

    pdf_lines = [f"  - {p.name}" for p in anhaenge] or ["  (keine)"]
    bild_lines = [f"  - {p.name}" for p in bilder] or ["  (keine)"]
    links_lines = [f"  - {url}" for url in links[:50]] or ["  (keine)"]
    if len(links) > 50:
        links_lines.append(f"  ... +{len(links) - 50} weitere")

    bilder_hinweis = ""
    if bilder:
        shown = min(len(bilder), config.TRIAGE_MAX_IMAGES)
        bilder_hinweis = (
            f"\n(Du siehst die ersten {shown} Bilder oben als Vision-Input. "
            f"Filenames in derselben Reihenfolge.)"
        )

    return f"""Mail zur Klassifikation:

=== Subject ===
{subject}

=== Von ===
{von}

=== Body (Plain, gekürzt) ===
{body[:3000]}

=== PDF-Anhänge ({len(anhaenge)}) ===
{chr(10).join(pdf_lines)}

=== Bilder ({len(bilder)}) ==={bilder_hinweis}
{chr(10).join(bild_lines)}

=== Links ({len(links)}) ===
{chr(10).join(links_lines)}
"""
