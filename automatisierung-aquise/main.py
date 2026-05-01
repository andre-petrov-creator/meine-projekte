"""Entry-Point der Akquise-Pipeline.

Verdrahtet alle Module zur End-to-End-Pipeline.

Modi:
    python main.py            → IDLE-Loop bis Ctrl+C
    python main.py --once     → ungelesene Mails einmalig verarbeiten und beenden
    python main.py --version  → Versionsinfo
"""
from __future__ import annotations

import argparse
import sys
import threading
from datetime import datetime
from pathlib import Path

import config
from modules import (
    m01_email_listener,
    m02_email_parser,
    m02b_mail_triage,
    m03_link_resolver,
    m03b_webexpose_renderer,
    m04_pdf_classifier,
    m05_address_extractor,
    m06_folder_manager,
    m07_state_store,
    m08_logger,
    m09_alert_mailer,
)

log = m08_logger.get_logger("main")

# Webexposé-Renderer (Playwright) als Webpage-Renderer in m03 registrieren
m03_link_resolver.set_webpage_renderer(m03b_webexpose_renderer.render)

# Counter für Health-Check (nur Lese-Statistik, keine Persistenz)
_processed_count = 0
_skipped_count = 0
_error_count = 0
_started_at: datetime | None = None


def process_mail(raw_mail: bytes) -> None:
    """Pipeline-Callback: verarbeitet genau eine Mail.

    Grundannahme: Jede eingehende Mail enthält Exposé-Inhalt (PDF, Bild oder Adresse).
    Wenn nichts extrahierbar ist → Hard-Fail-Alert + state=error.

    Reihenfolge:
    1. m02 parst Mail (PDFs + Bilder + Inline + Bild-PDF-Render)
    2. m07 prüft Idempotenz → wenn schon done/error: skip
    3. m07 markiert processing
    4. m02b: KI-Triage mit Vision (Bilder + Text)
    5. m03 resolved Links zu zusätzlichen PDFs
    6. Hard-Fail-Check: 0 PDFs + 0 Bilder + keine Adresse → Alert
    7. m04 klassifiziert alle Files (PDF + Bild)
    8. m05 extrahiert Adresse aus Exposé-PDF (Fallback, falls Triage keine lieferte)
    9. m06 legt Objekt-Ordner an
    10. m07 markiert done (oder error bei Exception)
    """
    global _processed_count, _skipped_count, _error_count

    parsed = m02_email_parser.parse(raw_mail)
    message_id = parsed["message_id"]

    if m07_state_store.is_processed(message_id):
        _skipped_count += 1
        log.info("Mail %s bereits verarbeitet — übersprungen.", message_id)
        return

    m07_state_store.mark_processing(message_id)

    try:
        # KI-Triage: Welche Anhänge/Bilder/Links sind das echte Exposé?
        triage = m02b_mail_triage.triage(parsed)

        if triage is not None:
            urls_to_resolve = triage.expose_links
            anhaenge_to_keep = _filter_pdfs_by_triage(parsed["anhaenge"], triage)
            bilder_to_keep = _filter_images_by_triage(parsed["bilder"], triage)
            adresse = triage.objekt_adresse
        else:
            # Fallback ohne Triage: alle Files behalten, Adresse aus PDF-Text extrahieren
            urls_to_resolve = parsed["links"]
            anhaenge_to_keep = list(parsed["anhaenge"])
            bilder_to_keep = list(parsed["bilder"])
            adresse = None

        temp_dir = m02_email_parser.temp_dir_for(message_id)
        link_pdfs = m03_link_resolver.resolve(urls_to_resolve, target_dir=temp_dir)

        all_pdfs = anhaenge_to_keep + list(link_pdfs)
        all_files = all_pdfs + bilder_to_keep
        log.info(
            "Mail %s: %d Anhang-PDFs + %d Link-PDFs + %d Bilder = %d Files",
            message_id,
            len(anhaenge_to_keep),
            len(link_pdfs),
            len(bilder_to_keep),
            len(all_files),
        )

        if not all_files and not adresse:
            _hard_fail_no_content(
                message_id=message_id,
                parsed=parsed,
                triage=triage,
            )
            return

        if adresse is None:
            adresse = _extract_address_from_pdf(all_pdfs, triage)

        classified = _classify_files(all_pdfs, bilder_to_keep, triage)

        meta = {
            "message_id": message_id,
            "von": parsed["von"],
            "subject": parsed["subject"],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "triage_begruendung": triage.begruendung if triage else None,
        }
        target = m06_folder_manager.store(
            adresse=adresse, files=classified, meta=meta
        )

        m07_state_store.mark_done(message_id, str(target))
        _processed_count += 1
        log.info("Mail %s → %s", message_id, target)

        _check_for_anomalies(
            message_id=message_id,
            mail_subject=parsed["subject"],
            mail_von=parsed["von"],
            triage=triage,
            all_files=all_files,
            adresse=adresse,
            target=target,
        )

    except Exception as exc:
        log.exception("Pipeline-Fehler für Mail %s", message_id)
        m07_state_store.mark_error(message_id, str(exc))
        _error_count += 1
        m09_alert_mailer.send_exception_alert(
            message_id=message_id,
            mail_subject=parsed["subject"] if parsed else "(unparsed)",
            mail_von=parsed["von"] if parsed else "(unknown)",
            exc=exc,
        )


def _hard_fail_no_content(message_id: str, parsed: dict, triage) -> None:
    """Mail enthielt nichts Verwertbares — Alert + state=error, kein Folder."""
    global _error_count

    reason_parts: list[str] = []
    if not parsed.get("anhaenge"):
        reason_parts.append("keine PDFs")
    if not parsed.get("bilder"):
        reason_parts.append("keine Bilder")
    if not (triage and triage.objekt_adresse):
        reason_parts.append("keine Adresse extrahierbar")
    reason = ", ".join(reason_parts) or "keine verwertbaren Inhalte"

    details = {
        "subject": parsed.get("subject", ""),
        "von": parsed.get("von", ""),
        "body_preview": (parsed.get("body_plain") or "")[:500],
        "links_count": len(parsed.get("links", [])),
        "triage_begruendung": triage.begruendung if triage else "(Triage nicht ausgeführt)",
    }

    log.warning("Hard-Fail bei Mail %s: %s", message_id, reason)
    m07_state_store.mark_error(message_id, f"no content extractable: {reason}")
    _error_count += 1

    m09_alert_mailer.send_no_content_alert(
        message_id=message_id,
        mail_subject=parsed.get("subject", "(kein Subject)"),
        mail_von=parsed.get("von", "(unbekannt)"),
        reason=reason,
        details=details,
    )


def _check_for_anomalies(
    message_id: str,
    mail_subject: str,
    mail_von: str,
    triage,
    all_files: list,
    adresse: str | None,
    target,
) -> None:
    """Soft-Alert wenn Pipeline durchlief, aber Output dünn ist (Folder ohne Adresse)."""
    if adresse is not None:
        return  # Folder mit Adresse = ok, kein Anomalie-Alert nötig

    anomalies: list[str] = ["keine Adresse extrahiert (Fallback-Ordner)"]
    details = {
        "target_folder": str(target),
        "files_count": len(all_files),
        "triage_begruendung": triage.begruendung if triage else "(Triage nicht ausgeführt)",
    }
    reason = " + ".join(anomalies)
    log.warning("Anomalie bei Mail %s: %s", message_id, reason)
    m09_alert_mailer.send_anomaly_alert(
        message_id=message_id,
        mail_subject=mail_subject,
        mail_von=mail_von,
        reason=reason,
        details=details,
    )


def _filter_pdfs_by_triage(anhaenge: list[Path], triage) -> list[Path]:
    """Behält nur PDF-Anhänge die laut Triage Exposé/Mietliste/Begleitdoku sind."""
    relevant_names = set(
        triage.expose_attachment_filenames
        + triage.mietaufstellung_attachment_filenames
        + triage.begleit_attachment_filenames
    )
    if not relevant_names:
        return list(anhaenge)
    return [p for p in anhaenge if p.name in relevant_names]


def _filter_images_by_triage(bilder: list[Path], triage) -> list[Path]:
    """Behält Bilder die laut Triage Exposé/Mietliste sind. Begleit-Bilder (Logos,
    Signatur-Pixel) werden verworfen."""
    relevant_names = set(
        triage.expose_image_filenames + triage.mietaufstellung_image_filenames
    )
    if not relevant_names:
        # Wenn die KI gar nichts markiert hat: alle Bilder behalten (safer default).
        # Hard-Fail-Check schlägt sonst fälschlich an, falls Vision Bilder gar nicht
        # markiert hat (z. B. weil API-Fehler / leeres Schema).
        return list(bilder)
    return [p for p in bilder if p.name in relevant_names]


def _classify_files(pdfs: list[Path], bilder: list[Path], triage) -> list[dict]:
    """Klassifiziert PDFs + Bilder.

    Triage-Vorgabe (Filename in expose_*_filenames) hat Vorrang.
    Sonst: m04-Filename-Heuristik.
    Bilder ohne Triage-Match werden als 'sonstiges' geführt — m06 lässt sie
    mit Original-Filename liegen.
    """
    expose_pdf_names = set(triage.expose_attachment_filenames) if triage else set()
    miet_pdf_names = set(triage.mietaufstellung_attachment_filenames) if triage else set()
    expose_img_names = set(triage.expose_image_filenames) if triage else set()
    miet_img_names = set(triage.mietaufstellung_image_filenames) if triage else set()

    classified: list[dict] = []

    for pdf in pdfs:
        if pdf.name in expose_pdf_names:
            typ = "expose"
        elif pdf.name in miet_pdf_names:
            typ = "mieterliste"
        else:
            typ = m04_pdf_classifier.classify(pdf)["typ"]
        classified.append({"path": pdf, "typ": typ})

    for img in bilder:
        if img.name in expose_img_names:
            typ = "expose_image"
        elif img.name in miet_img_names:
            typ = "mieterliste_image"
        else:
            heur = m04_pdf_classifier.classify(img)["typ"]
            # Bild-Variante mappen, falls Heuristik zog
            if heur == "expose":
                typ = "expose_image"
            elif heur == "mieterliste":
                typ = "mieterliste_image"
            else:
                typ = "sonstiges"
        classified.append({"path": img, "typ": typ})

    return classified


def _extract_address_from_pdf(all_pdfs: list[Path], triage) -> str | None:
    """Sucht das erste Exposé-PDF und extrahiert dessen Adresse via m05."""
    expose_names = set(triage.expose_attachment_filenames) if triage else set()
    candidates = [p for p in all_pdfs if p.name in expose_names] or all_pdfs
    for pdf in candidates:
        result = m05_address_extractor.extract(pdf)
        if result and result.get("adresse"):
            log.info(
                "Adresse extrahiert (confidence=%.2f): %s",
                result["confidence"],
                result["adresse"],
            )
            return result["adresse"]
    log.info("Keine Adresse aus PDFs extrahierbar — Fallback-Ordner.")
    return None


# ---------------------------------------------------------------------------
# Modi
# ---------------------------------------------------------------------------


def run_once() -> int:
    """Verbindet sich, holt alle UNSEEN-Mails vom Filter-Absender, verarbeitet
    und beendet danach. Gut für Cron/manuellen Aufruf."""
    from imapclient import IMAPClient

    m07_state_store.init_db()
    log.info(
        "--once: verbinde zu %s als %s, Filter FROM %s",
        config.GMAIL_IMAP_HOST,
        config.GMAIL_USER,
        config.FILTER_FROM_ADDRESS,
    )

    with IMAPClient(config.GMAIL_IMAP_HOST, config.GMAIL_IMAP_PORT, ssl=True) as imap:
        imap.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
        imap.select_folder("INBOX")
        uids = imap.search(["FROM", config.FILTER_FROM_ADDRESS, "UNSEEN"])
        log.info("--once: %d ungelesene Mails gefunden.", len(uids))

        for uid in uids:
            try:
                response = imap.fetch([uid], ["RFC822"])
                raw_mail = response[uid][b"RFC822"]
            except Exception:
                log.exception("Fetch fehlgeschlagen für UID %s", uid)
                continue

            try:
                process_mail(raw_mail)
                imap.add_flags([uid], [b"\\Seen"])
            except Exception:
                log.exception("Pipeline-Crash bei UID %s — bleibt UNSEEN.", uid)

    return 0


def run_idle() -> int:
    """Permanenter IDLE-Listener bis Ctrl+C."""
    global _started_at
    m07_state_store.init_db()
    _started_at = datetime.now()
    log.info("Pipeline gestartet — IDLE-Modus.")
    _start_healthcheck()
    m01_email_listener.run(callback=process_mail)
    return 0


def _healthcheck_tick() -> None:
    """Loggt aktuelle Statistik. Re-armt sich selbst."""
    uptime = datetime.now() - _started_at if _started_at else None
    log.info(
        "Health-Check: Pipeline läuft (uptime=%s) — %d verarbeitet, "
        "%d übersprungen, %d Fehler.",
        uptime,
        _processed_count,
        _skipped_count,
        _error_count,
    )
    _start_healthcheck()


def _start_healthcheck() -> None:
    """Startet einen Daemon-Timer für den nächsten Health-Check-Tick."""
    timer = threading.Timer(config.HEALTHCHECK_INTERVAL_SECONDS, _healthcheck_tick)
    timer.daemon = True
    timer.start()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="akquise-pipeline",
        description=(
            "Akquise-Pipeline (First Look): Empfängt Akquise-Mails per IMAP-IDLE, "
            "extrahiert PDFs/Bilder/Links, klassifiziert sie und legt sie strukturiert ab."
        ),
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Einmal-Lauf: ungelesene Mails verarbeiten und beenden (statt IDLE-Loop).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="akquise-pipeline 0.10.0 (Bild-Exposés + Hard-Fail)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    m08_logger.setup()
    if args.once:
        return run_once()
    return run_idle()


if __name__ == "__main__":
    sys.exit(main())
