# m01 — Email Listener

## Zweck

Permanent laufender IMAP-IDLE-Listener auf Gmail-Inbox. Erkennt neue Mails
vom konfigurierten Filter-Absender und triggert einen Callback mit `raw_mail`.

## Public API

| Komponente                    | Beschreibung |
|-------------------------------|--------------|
| `EmailListener(callback, …)`  | Klasse, instanziieren mit Callback |
| `EmailListener.listen()`      | Blockiert, lauscht bis `stop()` oder Ctrl+C |
| `EmailListener.stop()`        | Beendet den Loop nach aktuellem IDLE-Tick |
| `run(callback)`               | Pipeline-Konvention: blockierender Entry-Point |

## Konfiguration (aus `config.py` / `.env`)

| Variable                       | Default                |
|--------------------------------|------------------------|
| `GMAIL_USER`                   | (Pflicht)              |
| `GMAIL_APP_PASSWORD`           | (Pflicht)              |
| `GMAIL_IMAP_HOST`              | `imap.gmail.com`       |
| `GMAIL_IMAP_PORT`              | `993`                  |
| `FILTER_FROM_ADDRESS`          | `andre-petrov@web.de`  |
| `IMAP_IDLE_TIMEOUT_SECONDS`    | `29 * 60`              |
| `IMAP_RECONNECT_BACKOFF_MAX`   | `30`                   |

Konstruktor-Argumente überschreiben jede Config-Variable (für Tests).

## Verhalten

### Initial-Pass
Beim Connect werden alle bestehenden UNSEEN-Mails vom Filter-Absender
einmalig durch den Callback geschickt — niemand fällt unter den Tisch.

### IDLE-Loop
- Server-Push via IMAP-IDLE.
- Timeout: **29 Minuten**, dann saubere Reconnect-Runde (Gmail killt nach 30).
- Bei IDLE-Event: erneut `SEARCH FROM <filter> UNSEEN` und Callback-Trigger.

### Mail-Verarbeitung
Pro UID:
1. `FETCH RFC822` → raw_mail
2. `callback(raw_mail)` aufrufen
3. Bei Erfolg: `\Seen` setzen
4. Bei Callback-Exception: Mail bleibt UNSEEN, wird beim nächsten Lauf erneut probiert (loggen, aber kein Crash)
5. Bei Fetch-Fehler: UID überspringen, weiter mit der nächsten

### Reconnect
- Exponential Backoff: 1, 2, 4, 8, 16, 30 (max) Sekunden
- Erfolgreiche Session → Counter zurück auf 0
- Erkannt wird: `IMAPClientError`, `OSError`, `ConnectionError`
- Unerwartete Exceptions führen ebenfalls zu Reconnect (geloggt mit Stack)

## Smoke-Test (manuell)

Connection-Check (nur verbinden + ausloggen, ohne IDLE):

```bash
.venv/Scripts/python.exe -c "
from imapclient import IMAPClient
import config
with IMAPClient(config.GMAIL_IMAP_HOST, config.GMAIL_IMAP_PORT, ssl=True) as c:
    c.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
    print('Login OK,', len(c.list_folders()), 'Ordner sichtbar.')
"
```

Voller Listener-Lauf (bricht mit Ctrl+C ab):

```bash
.venv/Scripts/python.exe -c "
from modules import m01_email_listener as m
m.run(lambda raw: print(f'Mail empfangen: {len(raw)} Bytes'))
"
```

Test-Szenario: Schick dir selbst eine Mail von `andre-petrov@web.de` an dein
Gmail-Postfach → Listener sollte sie innerhalb weniger Sekunden erkennen
und das `print` ausgeben.

## Status

✅ Implementiert (Schritt 3). Pure-Logik-Tests in `tests/test_m01_email_listener.py`.
Live-Verifikation per Smoke-Test (siehe oben).
