"""m01 — Email Listener.

IMAP-IDLE auf Gmail-Inbox. Erkennt neue Mails von der konfigurierten
Filter-Adresse und triggert einen Callback mit `raw_mail: bytes`.

Architektur:
- `EmailListener`-Klasse: Stateful (start/stop, Reconnect-Counter).
- Modul-Funktion `run(callback)`: blockierender Pipeline-Entry-Point.

Verhalten:
- Initial: alle UNSEEN Mails vom Filter-Absender verarbeiten.
- IDLE: warten bis Server EXISTS-Event schickt (oder 29-Min-Timeout für Gmail-Refresh).
- Pro neue Mail: callback aufrufen → bei Erfolg `\\Seen` setzen, bei Exception
  loggen und Mail UNSEEN lassen (wird beim nächsten Lauf erneut probiert).
- Bei Verbindungsabbruch: Exponential Backoff (1s, 2s, 4s, 8s, 16s, 30s max).
"""
from __future__ import annotations

import time
from collections.abc import Callable

from imapclient import IMAPClient
from imapclient.exceptions import IMAPClientError

import config
from modules.m08_logger import get_logger

log = get_logger(__name__)


def _calculate_backoff(attempt: int, max_seconds: int) -> int:
    """Exponential backoff: 1, 2, 4, 8, 16, … gekappt bei max_seconds."""
    return min(2**attempt, max_seconds)


class EmailListener:
    """IMAP-IDLE-Listener mit Auto-Reconnect."""

    def __init__(
        self,
        callback: Callable[[bytes], None],
        user: str | None = None,
        password: str | None = None,
        host: str | None = None,
        port: int | None = None,
        filter_from: str | None = None,
        idle_timeout: int | None = None,
        backoff_max: int | None = None,
    ) -> None:
        self.callback = callback
        self.user = user or config.GMAIL_USER
        self.password = password or config.GMAIL_APP_PASSWORD
        self.host = host or config.GMAIL_IMAP_HOST
        self.port = port or config.GMAIL_IMAP_PORT
        self.filter_from = filter_from or config.FILTER_FROM_ADDRESS
        self.idle_timeout = idle_timeout or config.IMAP_IDLE_TIMEOUT_SECONDS
        self.backoff_max = backoff_max or config.IMAP_RECONNECT_BACKOFF_MAX
        self._stop = False

        if not self.user or not self.password:
            raise ValueError(
                "GMAIL_USER und GMAIL_APP_PASSWORD müssen in .env gesetzt sein."
            )
        if not self.filter_from:
            raise ValueError("FILTER_FROM_ADDRESS muss in .env gesetzt sein.")

    def stop(self) -> None:
        """Beendet den Listener nach dem aktuellen IDLE-Tick."""
        self._stop = True

    def listen(self) -> None:
        """Blockiert bis stop() aufgerufen wird oder KeyboardInterrupt."""
        attempt = 0
        log.info(
            "Listener startet (User=%s, Host=%s, Filter=FROM %s)",
            self.user,
            self.host,
            self.filter_from,
        )
        while not self._stop:
            try:
                self._run_session()
                attempt = 0  # erfolgreiche Session → Backoff zurücksetzen
            except KeyboardInterrupt:
                log.info("KeyboardInterrupt — Listener wird beendet.")
                self._stop = True
            except (IMAPClientError, OSError, ConnectionError) as exc:
                wait = _calculate_backoff(attempt, self.backoff_max)
                log.warning(
                    "IMAP-Verbindung verloren (%s). Reconnect in %ds (Versuch %d).",
                    exc,
                    wait,
                    attempt + 1,
                )
                time.sleep(wait)
                attempt += 1
            except Exception:
                log.exception("Unerwarteter Fehler im Listener — Reconnect.")
                wait = _calculate_backoff(attempt, self.backoff_max)
                time.sleep(wait)
                attempt += 1

    def _run_session(self) -> None:
        """Eine IMAP-Session: connect → initial-fetch → IDLE-Loop → disconnect."""
        with IMAPClient(host=self.host, port=self.port, ssl=True) as imap:
            imap.login(self.user, self.password)
            imap.select_folder("INBOX")
            log.info("IMAP verbunden, lausche auf Inbox.")

            # Beim Start: alle bestehenden UNSEEN-Mails vom Filter-Absender verarbeiten
            self._process_unseen(imap)

            while not self._stop:
                imap.idle()
                try:
                    responses = imap.idle_check(timeout=self.idle_timeout)
                finally:
                    imap.idle_done()

                if responses:
                    log.debug("IDLE-Event empfangen (%d).", len(responses))
                    self._process_unseen(imap)
                else:
                    # 29-Min-Timeout — Gmail killt nach 30, daher saubere Reconnect-Runde
                    log.debug("IDLE-Timeout — Refresh-Reconnect.")
                    return

    def _process_unseen(self, imap: IMAPClient) -> None:
        """Holt alle UNSEEN Mails vom Filter-Absender und ruft Callback."""
        uids = imap.search(["FROM", self.filter_from, "UNSEEN"])
        if not uids:
            return
        log.info("%d neue Mail(s) von %s gefunden.", len(uids), self.filter_from)
        for uid in uids:
            self._handle_uid(imap, uid)

    def _handle_uid(self, imap: IMAPClient, uid: int) -> None:
        try:
            response = imap.fetch([uid], ["RFC822"])
            raw_mail = response[uid][b"RFC822"]
        except Exception:
            log.exception("Fetch fehlgeschlagen für UID %s — überspringe.", uid)
            return

        try:
            self.callback(raw_mail)
        except Exception:
            log.exception(
                "Callback wirft Exception für UID %s — Mail bleibt UNSEEN.", uid
            )
            return

        try:
            imap.add_flags([uid], [b"\\Seen"])
            log.info("Mail UID %s verarbeitet, als gelesen markiert.", uid)
        except Exception:
            log.exception(
                "Konnte UID %s nicht als gelesen markieren — Callback war erfolgreich.",
                uid,
            )


def run(callback: Callable[[bytes], None] | None = None) -> None:
    """Pipeline-Konvention: blockiert bis Abbruch."""
    if callback is None:
        raise ValueError("callback ist Pflicht für m01_email_listener.run()")
    EmailListener(callback=callback).listen()
