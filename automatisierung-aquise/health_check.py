"""Wöchentlicher Health-Check für die Akquise-Pipeline.

Wird vom Task Scheduler aufgerufen (Dienstag 9:00 lokal).
Schickt Mail an `andre-petrov@web.de` **nur bei Auffälligkeiten** —
sonst stiller Lauf mit einer Logzeile.

Was geprüft wird:
- Läuft der Pipeline-Prozess?
- State-DB: hängende `processing` (>1h alt)
- State-DB: neue `error`-Einträge seit letztem Check
- Logs: Aktualität (mtime der pipeline.log)

Was NICHT geprüft wird:
- Inhaltliche Korrektheit der angelegten Ordner — manuelle Stichprobe
"""
from __future__ import annotations

import json
import smtplib
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

import config
from modules.m08_logger import get_logger

log = get_logger("health_check")


def main() -> int:
    issues: list[str] = []
    issues.extend(check_pipeline_process())
    issues.extend(check_state_db())
    issues.extend(check_logs_freshness())

    snapshot = collect_snapshot()

    if issues:
        log.warning("Health-Check: %d Auffälligkeit(en).", len(issues))
        send_alert_mail(issues, snapshot)
    else:
        log.info(
            "Health-Check OK — counts=%s, folders=%s",
            snapshot.get("counts"),
            snapshot.get("folder_count"),
        )

    _save_last_check_timestamp()
    return 0


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_pipeline_process() -> list[str]:
    """Prüft via WMIC, ob ein python.exe mit main.py läuft."""
    try:
        out = subprocess.check_output(
            [
                "wmic",
                "process",
                "where",
                "name='python.exe'",
                "get",
                "commandline",
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except Exception as exc:
        return [f"Prozess-Check fehlgeschlagen ({exc})."]

    if "main.py" in out:
        return []
    return ["Pipeline-Prozess läuft nicht (kein python.exe mit main.py gefunden)."]


def check_state_db() -> list[str]:
    if not config.STATE_DB_PATH.exists():
        return ["State-DB existiert nicht (data/state.db) — Pipeline nie gelaufen?"]

    issues: list[str] = []
    conn = sqlite3.connect(config.STATE_DB_PATH)
    try:
        # Hängende processing
        threshold = (
            datetime.now() - timedelta(hours=config.HEALTHCHECK_PROCESSING_STALE_HOURS)
        ).isoformat(timespec="seconds")
        stale = conn.execute(
            "SELECT message_id, timestamp FROM processed_mails "
            "WHERE status = 'processing' AND timestamp < ?",
            (threshold,),
        ).fetchall()
        if stale:
            ids = ", ".join(r[0] for r in stale[:5])
            more = f" (+{len(stale) - 5} weitere)" if len(stale) > 5 else ""
            issues.append(
                f"{len(stale)} Mail(s) hängen seit "
                f">{config.HEALTHCHECK_PROCESSING_STALE_HOURS}h in 'processing': {ids}{more}"
            )

        # Neue Errors seit letztem Check
        last_ts = _load_last_check_timestamp()
        if last_ts:
            new_errors = conn.execute(
                "SELECT message_id, error_msg FROM processed_mails "
                "WHERE status = 'error' AND timestamp > ?",
                (last_ts,),
            ).fetchall()
        else:
            new_errors = conn.execute(
                "SELECT message_id, error_msg FROM processed_mails WHERE status = 'error'"
            ).fetchall()

        if new_errors:
            details = "; ".join(f"{r[0]}: {r[1]}" for r in new_errors[:3])
            more = f" (+{len(new_errors) - 3} weitere)" if len(new_errors) > 3 else ""
            issues.append(f"{len(new_errors)} neue Error-Mail(s): {details}{more}")
    finally:
        conn.close()

    return issues


def check_logs_freshness() -> list[str]:
    """Wenn pipeline.log >7 Tage nicht mehr aktualisiert wurde, hängt etwas."""
    log_file = config.LOG_FILE
    if not log_file.exists():
        return ["Pipeline-Log existiert nicht — ist die Pipeline jemals gelaufen?"]

    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
    age = datetime.now() - mtime
    if age > timedelta(days=7):
        return [f"Pipeline-Log seit {mtime:%Y-%m-%d %H:%M} nicht aktualisiert ({age.days}d)."]
    return []


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def collect_snapshot() -> dict:
    snap: dict = {"timestamp": datetime.now().isoformat(timespec="seconds")}

    if config.STATE_DB_PATH.exists():
        conn = sqlite3.connect(config.STATE_DB_PATH)
        try:
            rows = conn.execute(
                "SELECT status, COUNT(*) FROM processed_mails GROUP BY status"
            ).fetchall()
            snap["counts"] = {r[0]: r[1] for r in rows}
        finally:
            conn.close()

    if config.BASE_FOLDER.exists():
        try:
            snap["folder_count"] = sum(
                1 for p in config.BASE_FOLDER.iterdir() if p.is_dir()
            )
        except OSError:
            snap["folder_count"] = "?"

    return snap


# ---------------------------------------------------------------------------
# Last-Check-Stempel
# ---------------------------------------------------------------------------


def _load_last_check_timestamp() -> str | None:
    path = config.HEALTHCHECK_LAST_CHECK_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("timestamp")
    except Exception:
        return None


def _save_last_check_timestamp() -> None:
    path = config.HEALTHCHECK_LAST_CHECK_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"timestamp": datetime.now().isoformat(timespec="seconds")}),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Mail
# ---------------------------------------------------------------------------


def send_alert_mail(issues: list[str], snapshot: dict) -> None:
    if not config.GMAIL_USER or not config.GMAIL_APP_PASSWORD:
        log.error("Kann keine Alert-Mail schicken: SMTP-Credentials fehlen in .env.")
        return

    body_lines = [
        "Akquise-Pipeline Health-Check hat Auffälligkeiten gefunden:",
        "",
    ]
    for i, issue in enumerate(issues, 1):
        body_lines.append(f"{i}. {issue}")
    body_lines.append("")
    body_lines.append("--- Status-Snapshot ---")
    body_lines.append(json.dumps(snapshot, indent=2, ensure_ascii=False))
    body_lines.append("")
    body_lines.append("Logs prüfen: logs/pipeline.log")
    body_lines.append("State-DB:    data/state.db")
    body_lines.append("Mail bei jedem 'rm processed_mails WHERE message_id=...' freigeben.")
    body = "\n".join(body_lines)

    msg = EmailMessage()
    msg["Subject"] = (
        f"Akquise-Pipeline: Health-Check ({len(issues)} Auffälligkeit(en)) "
        f"{datetime.now():%d.%m.%Y}"
    )
    msg["From"] = config.GMAIL_USER
    msg["To"] = config.HEALTHCHECK_ALERT_TO
    msg.set_content(body)

    try:
        with smtplib.SMTP(config.GMAIL_SMTP_HOST, config.GMAIL_SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        log.info("Alert-Mail an %s verschickt.", config.HEALTHCHECK_ALERT_TO)
    except Exception:
        log.exception("Alert-Mail konnte nicht verschickt werden.")


if __name__ == "__main__":
    sys.exit(main())
