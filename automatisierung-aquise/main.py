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

    Reihenfolge:
    1. m02 parst Mail (vor Idempotenz-Check, weil wir die message_id brauchen)
    2. m07 prüft Idempotenz → wenn schon done/error: skip
    3. m07 markiert processing
    4. m03 resolved Links zu zusätzlichen PDFs
    5. m04 klassifiziert alle PDFs
    6. m05 extrahiert Adresse aus dem Exposé (falls vorhanden)
    7. m06 legt Objekt-Ordner an
    8. m07 markiert done (oder error bei Exception)
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
        temp_dir = m02_email_parser.temp_dir_for(message_id)

        # KI-Triage: Welche Anhänge/Links sind das echte Exposé?
        triage = m02b_mail_triage.triage(parsed)

        if triage is not None and not triage.is_expose_mail:
            log.info(
                "Mail %s ist keine Akquise-Mail (%s) — übersprungen, kein Ordner.",
                message_id,
                triage.begruendung,
            )
            m07_state_store.mark_done(message_id, "(skipped: keine Exposé-Mail)")
            _skipped_count += 1
            return

        # Links nur die von der KI ausgewählten resolven (nicht alle 70 Tracking-Links)
        if triage is not None:
            urls_to_resolve = triage.expose_links
            anhaenge_to_keep = _filter_anhaenge_by_triage(parsed["anhaenge"], triage)
            adresse = triage.objekt_adresse
        else:
            # Fallback: alte Logik (alle Links, alle Anhänge, Adresse aus PDF)
            urls_to_resolve = parsed["links"]
            anhaenge_to_keep = list(parsed["anhaenge"])
            adresse = None

        link_pdfs = m03_link_resolver.resolve(urls_to_resolve, target_dir=temp_dir)

        all_pdfs = anhaenge_to_keep + list(link_pdfs)
        log.info(
            "Mail %s: %d Anhänge + %d Link-PDFs = %d total",
            message_id,
            len(anhaenge_to_keep),
            len(link_pdfs),
            len(all_pdfs),
        )

        classified = _classify_pdfs(all_pdfs, triage)

        if adresse is None:
            adresse = _extract_address_from_expose(classified)

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

        # Anomalie-Detection: Pipeline lief durch, aber Output verdaechtig?
        _check_for_anomalies(
            message_id=message_id,
            mail_subject=parsed["subject"],
            mail_von=parsed["von"],
            triage=triage,
            all_pdfs=all_pdfs,
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


def _check_for_anomalies(
    message_id: str,
    mail_subject: str,
    mail_von: str,
    triage,
    all_pdfs: list,
    adresse: str | None,
    target,
) -> None:
    """Soft-Alert wenn die Mail laut Triage Exposé enthält, aber das Ergebnis unbrauchbar ist."""
    # Nur wenn KI sagte "ist Exposé-Mail" — sonst kein Alert
    if triage is None or not triage.is_expose_mail:
        return

    anomalies: list[str] = []
    details: dict = {"target_folder": str(target)}

    if not all_pdfs:
        anomalies.append("0 PDFs heruntergeladen")
        details["expose_links_in_triage"] = triage.expose_links
        details["expose_attachments_in_triage"] = triage.expose_attachment_filenames

    if adresse is None:
        anomalies.append("keine Adresse extrahiert (Fallback-Ordner)")

    if not anomalies:
        return

    reason = " + ".join(anomalies)
    log.warning("Anomalie bei Mail %s: %s", message_id, reason)
    m09_alert_mailer.send_anomaly_alert(
        message_id=message_id,
        mail_subject=mail_subject,
        mail_von=mail_von,
        reason=reason,
        details=details,
    )


def _filter_anhaenge_by_triage(anhaenge: list, triage) -> list:
    """Behält nur Anhänge die laut Triage Exposé/Mietliste/Begleitdoku sind.
    Verwirft alles andere (z. B. signature.png, unbekannte Filenames)."""
    relevant_names = set(
        triage.expose_attachment_filenames
        + triage.mietaufstellung_attachment_filenames
        + triage.begleit_attachment_filenames
    )
    if not relevant_names:
        # Triage hat nichts markiert — alle Anhänge behalten (safer default)
        return list(anhaenge)
    return [p for p in anhaenge if p.name in relevant_names]


def _classify_pdfs(pdfs: list, triage) -> list[dict]:
    """Klassifiziert PDFs. Nutzt Triage-Info wenn vorhanden, sonst Filename-Heuristik."""
    expose_names = set(triage.expose_attachment_filenames) if triage else set()
    miet_names = set(triage.mietaufstellung_attachment_filenames) if triage else set()

    classified = []
    for pdf in pdfs:
        if pdf.name in expose_names:
            typ = "expose"
        elif pdf.name in miet_names:
            typ = "mieterliste"
        else:
            typ = m04_pdf_classifier.classify(pdf)["typ"]
        classified.append({"path": pdf, "typ": typ})
    return classified


def _extract_address_from_expose(classified: list[dict]) -> str | None:
    """Sucht das erste Exposé-PDF und extrahiert dessen Adresse."""
    for entry in classified:
        if entry["typ"] != "expose":
            continue
        result = m05_address_extractor.extract(entry["path"])
        if result and result.get("adresse"):
            log.info(
                "Adresse extrahiert (confidence=%.2f): %s",
                result["confidence"],
                result["adresse"],
            )
            return result["adresse"]
    log.info("Kein Exposé oder keine Adresse extrahierbar — Fallback-Ordner.")
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
            "extrahiert PDFs/Links, klassifiziert sie und legt sie strukturiert ab."
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
        version="akquise-pipeline 0.9.0 (Schritt 9 — End-to-End)",
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
