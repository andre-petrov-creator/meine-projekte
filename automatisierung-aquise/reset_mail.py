"""Reset-Helper: macht eine Mail wieder verarbeitbar.

  python reset_mail.py <message-id>

Setzt sie in Gmail wieder auf UNSEEN und löscht den state.db-Eintrag.
Beim nächsten `python main.py --once` wird sie neu durchlaufen.
"""
from __future__ import annotations

import sqlite3
import sys

from imapclient import IMAPClient

import config


def main(message_id: str) -> int:
    # 1. State-DB-Eintrag löschen
    with sqlite3.connect(config.STATE_DB_PATH) as conn:
        cur = conn.execute(
            "DELETE FROM processed_mails WHERE message_id = ?", (message_id,)
        )
        deleted = cur.rowcount
        conn.commit()
    print(f"State-DB: {deleted} Eintrag(e) für message_id={message_id} gelöscht")

    # 2. Gmail nach Header Message-ID suchen + UNSEEN setzen
    with IMAPClient(config.GMAIL_IMAP_HOST, config.GMAIL_IMAP_PORT, ssl=True) as imap:
        imap.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
        imap.select_folder("INBOX")
        # IMAP-Header-Suche: braucht <message-id> in spitzen Klammern
        header_value = f"<{message_id}>" if not message_id.startswith("<") else message_id
        uids = imap.search(["HEADER", "Message-ID", header_value])
        if not uids:
            # Fallback: ohne Klammern probieren
            uids = imap.search(["HEADER", "Message-ID", message_id])
        if not uids:
            print(f"Gmail: keine Mail mit Message-ID={message_id} gefunden")
            return 1
        imap.remove_flags(uids, [b"\\Seen"])
        print(f"Gmail: UID(s) {list(uids)} auf UNSEEN gesetzt")

    print("\nNächster Schritt: python main.py --once")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
