"""m09 — Alert Mailer.

Schickt sofortige Mail-Benachrichtigungen bei:
1. Pipeline-Crashes (Exceptions) — mit Stack-Trace + Code-Snippet (±5 Zeilen)
2. Anomalien (Pipeline lief durch, aber Output ist verdächtig) —
   z. B. 0 PDFs trotz is_expose_mail=True, Fallback-Ordner ohne Adresse

Kein Retry: schlägt der Alert selbst fehl, wird nur geloggt
(verhindert Mail-Sturm bei SMTP-Problemen).

Public API:
    send_exception_alert(message_id, mail_subject, mail_von, exc, traceback_str)
    send_anomaly_alert(message_id, mail_subject, mail_von, reason, details)
    send_no_content_alert(message_id, mail_subject, mail_von, reason, details)
"""
from __future__ import annotations

import smtplib
import traceback as tb
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

import config
from modules.m08_logger import get_logger

log = get_logger(__name__)

_CODE_CONTEXT_LINES = 5  # ±5 Zeilen um die Fehlerzeile
_MAX_BODY_CHARS = 50_000  # SMTP-Schutz


def send_exception_alert(
    message_id: str,
    mail_subject: str,
    mail_von: str,
    exc: BaseException,
) -> None:
    """Bug-Alert mit menschlicher Story oben + Code-Block unten."""
    err_type = type(exc).__name__
    err_msg = str(exc)
    plain_explanation = _humanize_error(exc)
    project_trace = _project_only_traceback(exc.__traceback__)
    code_context = _extract_code_context(exc.__traceback__)

    subject = f"❌ Pipeline-Fehler — {_truncate(mail_subject, 60)}"

    body_lines = [
        f"❌ FEHLER bei Mail-Verarbeitung",
        "",
        f"Mail:  {mail_subject}",
        f"Zeit:  {datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "Was passiert ist:",
        f"✗ Pipeline ist beim Verarbeiten abgestürzt",
        f"✗ {plain_explanation}",
        f"✓ Mail wurde in der State-DB als 'error' markiert (kein automatischer Retry)",
        "",
        "Was du tun musst:",
        "1. Code-Snippet unten ansehen, Bug fixen",
        f"2. Reset & retry:  python reset_mail.py {message_id}",
        "3. Pipeline neu starten:  python main.py --once",
        "",
        "─" * 60,
        "",
        "=== CODE (zum direkt reinkopieren / fixen) ===",
        "",
        f"Fehler-Typ: {err_type}: {err_msg}",
        "",
    ]
    if code_context:
        body_lines.append(code_context)
        body_lines.append("")
    if project_trace:
        body_lines.append("Aufrufkette:")
        body_lines.append(project_trace)

    _send("\n".join(body_lines), subject)


# Mapping: technischer Error → Mensch-Satz auf Deutsch
_ERROR_EXPLANATIONS = {
    "KeyError": "Im Programm fehlt ein erwarteter Datenwert (Key fehlt im Dictionary)",
    "AttributeError": "Ein Wert war leer/None, aber der Code wollte etwas damit machen",
    "TypeError": "Falscher Datentyp übergeben (z.B. String statt Liste)",
    "ValueError": "Ein Wert hatte das falsche Format",
    "FileNotFoundError": "Eine Datei existiert nicht (Pfad falsch oder nicht angelegt)",
    "PermissionError": "Keine Schreib-/Leserechte für eine Datei oder Ordner",
    "ConnectionError": "Server/Webseite nicht erreichbar (Internet, Timeout, oder fremder Server down)",
    "TimeoutError": "Eine Operation hat zu lange gedauert (Timeout)",
    "JSONDecodeError": "Eine empfangene JSON-Antwort war kaputt oder unerwartet formatiert",
    "ValidationError": "Die KI-Antwort passte nicht ins erwartete Schema (Pydantic-Fehler)",
    "RateLimitError": "Anthropic API Rate-Limit erreicht — kurz warten und erneut versuchen",
    "AuthenticationError": "Anthropic API-Key ungültig oder abgelaufen — in .env prüfen",
    "APIConnectionError": "Anthropic API nicht erreichbar (Netzwerk-Problem)",
}


def _humanize_error(exc: BaseException) -> str:
    """Übersetzt technischen Error-Type in einen deutschen Satz."""
    err_type = type(exc).__name__
    return _ERROR_EXPLANATIONS.get(err_type, f"Programm-Bug ({err_type}) — Details siehe Code unten")


def _project_only_traceback(tb_obj) -> str:
    """Stack-Trace gefiltert auf Projekt-Code (kein stdlib, kein site-packages)."""
    if tb_obj is None:
        return ""
    project_root = Path(__file__).resolve().parent.parent
    lines: list[str] = []
    for frame in tb.extract_tb(tb_obj):
        try:
            resolved = Path(frame.filename).resolve()
            if not resolved.is_relative_to(project_root):
                continue
            if ".venv" in frame.filename:
                continue
            rel = resolved.relative_to(project_root)
        except (ValueError, OSError):
            continue
        lines.append(f"  {rel}:{frame.lineno} in {frame.name}()")
        if frame.line:
            lines.append(f"      {frame.line.strip()}")
    return "\n".join(lines)


def send_no_content_alert(
    message_id: str,
    mail_subject: str,
    mail_von: str,
    reason: str,
    details: dict | None = None,
) -> None:
    """Hard-Fail-Alert: Mail wurde verarbeitet, aber NICHTS Verwertbares extrahierbar
    (kein PDF, kein Bild, keine Adresse). Konsistent zur Grundannahme „jede Mail
    enthält Exposé-Inhalt": wenn die Pipeline nichts findet, ist das ein Bug oder
    Edge-Case, der menschliche Aufmerksamkeit braucht."""
    subject = f"❌ Mail-Verarbeitung — kein Inhalt — {_truncate(mail_subject, 60)}"

    body_lines = [
        "❌ KEIN INHALT extrahierbar",
        "",
        f"Mail:  {mail_subject}",
        f"Von:   {mail_von}",
        f"Zeit:  {datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "Was passiert ist:",
        "✓ Mail wurde empfangen und gescannt",
        f"✗ {reason}",
        "✓ Mail wurde in der State-DB als 'error' markiert (kein automatischer Retry)",
        "",
        "Was du tun musst:",
        "1. Mail manuell im Posteingang ansehen — was ist drin?",
        "2. Falls Bild/PDF doch existiert: Pipeline-Bug — Code prüfen (m02 Parser)",
        f"3. Mail neu durchlassen:  python reset_mail.py {message_id}",
        "4. Falls die Mail tatsächlich Müll ist: Filter (FILTER_FROM_ADDRESS) prüfen",
        "",
        "─" * 60,
        "",
        "=== DETAILS ===",
        "",
    ]
    if details:
        for k, v in details.items():
            body_lines.append(f"{k}:")
            body_lines.append(f"  {v}")
            body_lines.append("")

    _send("\n".join(body_lines), subject)


def send_anomaly_alert(
    message_id: str,
    mail_subject: str,
    mail_von: str,
    reason: str,
    details: dict | None = None,
) -> None:
    """Soft-Alert: Pipeline lief durch, aber Output ist verdächtig."""
    subject = f"⚠️ Pipeline-Warnung — {_truncate(mail_subject, 60)}"

    body_lines = [
        f"⚠️  WARNUNG bei Mail-Verarbeitung",
        "",
        f"Mail:  {mail_subject}",
        f"Zeit:  {datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
        "Was passiert ist:",
        "✓ KI hat die Mail als Akquise-Exposé erkannt",
        "✓ Pipeline lief durch (kein Crash)",
        f"✗ Aber: {reason}",
        "",
        "Was du tun musst:",
        f"1. Output-Ordner manuell prüfen (siehe unten)",
        f"2. Falls nichts brauchbar drin ist:  python reset_mail.py {message_id}",
        "3. Eventuell: KI-Prompt oder Renderer-Logik anpassen",
        "",
        "─" * 60,
        "",
        "=== DETAILS (für Debug) ===",
        "",
    ]
    if details:
        for k, v in details.items():
            body_lines.append(f"{k}:")
            body_lines.append(f"  {v}")
            body_lines.append("")

    _send("\n".join(body_lines), subject)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _send(body: str, subject: str) -> None:
    """SMTP-Send mit Loop-Schutz: bei Fehler nur loggen, nicht raisen."""
    if not config.GMAIL_USER or not config.GMAIL_APP_PASSWORD:
        log.error("Alert-Mail nicht möglich: SMTP-Credentials fehlen in .env")
        return

    if len(body) > _MAX_BODY_CHARS:
        body = body[:_MAX_BODY_CHARS] + "\n\n... (truncated)"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.GMAIL_USER
    msg["To"] = config.HEALTHCHECK_ALERT_TO
    msg.set_content(body)

    try:
        with smtplib.SMTP(config.GMAIL_SMTP_HOST, config.GMAIL_SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        log.info("Alert-Mail an %s verschickt: %s", config.HEALTHCHECK_ALERT_TO, subject[:60])
    except Exception as exc:
        # KEIN Retry, KEIN Re-raise — Pipeline darf weiterlaufen
        log.exception("Alert-Mail konnte nicht verschickt werden (%s) — kein Retry", exc)


def _extract_code_context(tb_obj) -> str:
    """Liest die Fehlerzeile + Kontext aus dem Top-Frame des Tracebacks (= das was wirklich crashte).

    Bevorzugt Frames im Projekt-Code; fällt auf den letzten Frame zurück."""
    if tb_obj is None:
        return ""
    frames = tb.extract_tb(tb_obj)
    if not frames:
        return ""

    # Bevorzuge Frame im Projekt (modules/, main.py), sonst letzter Frame
    project_root = Path(__file__).resolve().parent.parent
    relevant = None
    for frame in reversed(frames):
        try:
            if Path(frame.filename).resolve().is_relative_to(project_root):
                relevant = frame
                break
        except (ValueError, OSError):
            continue
    if relevant is None:
        relevant = frames[-1]

    return _format_code_window(relevant.filename, relevant.lineno)


def _format_code_window(filename: str, lineno: int) -> str:
    """Liest Datei und gibt ±_CODE_CONTEXT_LINES um die Fehlerzeile aus."""
    try:
        lines = Path(filename).read_text(encoding="utf-8").splitlines()
    except Exception:
        return ""

    start = max(0, lineno - _CODE_CONTEXT_LINES - 1)
    end = min(len(lines), lineno + _CODE_CONTEXT_LINES)

    out: list[str] = [f"Datei: {filename}:{lineno}", ""]
    for i in range(start, end):
        marker = ">" if (i + 1) == lineno else " "
        out.append(f"  {marker} {i + 1:4d} | {lines[i]}")
    return "\n".join(out)




def _truncate(s: str, max_len: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= max_len else s[: max_len - 3] + "..."
