# Betrieb (Schritt 10 — Hardening)

## Pipeline manuell starten

```powershell
# venv aktivieren (einmal pro Shell)
.venv\Scripts\Activate.ps1

# Dauerbetrieb (IDLE bis Ctrl+C)
python main.py

# Nur ungelesene Mails einmalig verarbeiten
python main.py --once
```

Kürzer: `start_pipeline.bat` oder `start_pipeline.ps1` doppelklicken / aufrufen.
Beide Skripte aktivieren das venv automatisch und starten den IDLE-Modus.

## Autostart via Windows Task Scheduler

**Empfohlen** — Python als Windows-Service ist fummelig (siehe Plan-Risiken),
Task Scheduler reicht.

### Einrichtung

1. Task Scheduler öffnen (`taskschd.msc`).
2. **Aufgabe erstellen…** (nicht "Einfache Aufgabe").
3. **Allgemein**:
   - Name: `Akquise-Pipeline`
   - "Unabhängig von Benutzeranmeldung ausführen" → AUS lassen
   - "Mit höchsten Privilegien ausführen" → nicht nötig
4. **Trigger**:
   - Neuen Trigger: **Bei Anmeldung** (oder **Beim Start**, falls die Pipeline auch ohne Login laufen soll)
5. **Aktionen**:
   - Programm/Skript: `C:\Users\andre\.claude\projects\Automatisierung, Mail, Exposé, Ordner\start_pipeline.bat`
   - oder PowerShell-Variante:
     - Programm: `powershell.exe`
     - Argumente: `-ExecutionPolicy Bypass -File "C:\Users\andre\.claude\projects\Automatisierung, Mail, Exposé, Ordner\start_pipeline.ps1"`
6. **Bedingungen**:
   - "Aufgabe nur starten, falls Computer im Netzbetrieb" → AUS (sonst läuft sie auf Akku nicht)
7. **Einstellungen**:
   - "Aufgabe nach Fehlschlag neu starten" → an, alle 5 Minuten, max. 3-mal
   - "Aufgabe stoppen, falls länger als 3 Tage" → AUS

### Test

```powershell
# Aufgabe manuell starten (zum Test)
schtasks /Run /TN "Akquise-Pipeline"

# Status prüfen
schtasks /Query /TN "Akquise-Pipeline" /V /FO LIST
```

Reboot → nach Anmeldung sollte die Pipeline automatisch starten.
Im Task Manager (`taskmgr`) sollte `python.exe` laufen.

## Health-Check

Pipeline loggt alle 6 Stunden eine Statistik:

```
[2026-04-30 16:00:00] [main] [INFO] Health-Check: Pipeline läuft (uptime=6:00:01) — 12 verarbeitet, 2 übersprungen, 0 Fehler.
```

Konfigurierbar über `HEALTHCHECK_INTERVAL_SECONDS` in `config.py`.
Counter sind In-Memory (Reset bei Neustart) — für persistente Statistik
müsste m07 erweitert werden (Pipeline-2-Thema).

## Logs lesen

```powershell
# Letzte 50 Zeilen
Get-Content logs\pipeline.log -Tail 50

# Live mitlesen
Get-Content logs\pipeline.log -Wait -Tail 20
```

Rotation: 10 MB pro File, 5 Backups (`pipeline.log.1` … `pipeline.log.5`).

## State-DB inspizieren

```powershell
.venv\Scripts\python.exe -c "
import sqlite3
conn = sqlite3.connect('data/state.db')
for row in conn.execute('SELECT message_id, status, timestamp, folder_path FROM processed_mails ORDER BY timestamp DESC LIMIT 20'):
    print(row)
"
```

## Mail manuell zur Wiederverarbeitung freigeben

Bei Status `error` wird die Mail **nicht automatisch** retried (Fail-safe).
Manueller Reset:

```powershell
.venv\Scripts\python.exe -c "
import sqlite3
conn = sqlite3.connect('data/state.db')
conn.execute('DELETE FROM processed_mails WHERE message_id = ?', ('PROBLEM-ID-HIER',))
conn.commit()
print('Reset OK.')
"
```

Danach: Mail in Gmail wieder als ungelesen markieren — beim nächsten
IDLE-Tick wird sie erneut verarbeitet.

## Recovery

| Szenario | Lösung |
|----------|--------|
| Pipeline crasht, IMAP-Verbindung weg | m01 reconnected automatisch (Backoff) |
| Mail bleibt in `processing` hängen | Beim Neustart wird sie erneut probiert (Status ≠ Endzustand) |
| Mail-Status `error` | Manueller Reset (s.o.) + UNSEEN-Flag in Gmail |
| Falscher Ordner-Name (Adresse falsch erkannt) | Ordner manuell umbenennen, `_meta.json` zeigt Original-Daten |
| Doppelte Objekte verschiedener Makler | Beide Ordner manuell mergen (Pipeline-2-Thema) |

## Wöchentlicher Health-Check (Dienstag 9:00)

`health_check.py` läuft einmal pro Woche und schickt eine Mail an
`andre-petrov@web.de` **nur bei Auffälligkeiten**. Bei „alles OK" nichts.

### Was geprüft wird

- **Pipeline-Prozess läuft?** (WMIC sucht `python.exe` mit `main.py`)
- **Hängende `processing`** in State-DB (Mails älter als 1h, die nicht zu `done` oder `error` wurden → Crash-Indikator)
- **Neue `error`-Einträge** seit letztem Health-Check
- **Log-Aktualität** (`pipeline.log` <7 Tage alt)

### Manueller Lauf

```powershell
.venv\Scripts\python.exe health_check.py
# oder einfacher:
start_healthcheck.bat
```

### Task Scheduler — Dienstag 9:00 wöchentlich

1. Task Scheduler öffnen → **Aufgabe erstellen…**
2. **Allgemein**:
   - Name: `Akquise-Pipeline-HealthCheck`
3. **Trigger**:
   - Neuen Trigger: **Wöchentlich**
   - Start: Dienstag 09:00:00
   - Wiederholen alle: 1 Woche, an Dienstag
4. **Aktionen**:
   - Programm/Skript: `…\Automatisierung, Mail, Exposé, Ordner\start_healthcheck.bat`
5. **Bedingungen**:
   - "Aufgabe nur starten, falls Computer im Netzbetrieb" → AUS
6. **Einstellungen**:
   - "Aufgabe nach Fehlschlag neu starten" → AUS (kein Retry, nächster Dienstag reicht)

### Test

```powershell
schtasks /Run /TN "Akquise-Pipeline-HealthCheck"
```

Wenn aktuell etwas auffällig ist → Mail kommt sofort an.
Sonst → still, nur eine Logzeile in `logs/pipeline.log`.

### Was kommt in der Alert-Mail

```
Subject: Akquise-Pipeline: Health-Check (N Auffälligkeit(en)) DD.MM.YYYY
From:    <GMAIL_USER>
To:      andre-petrov@web.de

1. Pipeline-Prozess läuft nicht (kein python.exe mit main.py gefunden).
2. 2 Mail(s) hängen seit >1h in 'processing': msg-id-1, msg-id-2

--- Status-Snapshot ---
{
  "timestamp": "2026-05-07T09:00:00",
  "counts": {"done": 47, "error": 1, "processing": 2},
  "folder_count": 47
}
```

## Akzeptanzkriterien Schritt 10

| Kriterium | Verifikation |
|-----------|--------------|
| Nach Reboot startet Pipeline automatisch | Manuell — Task Scheduler einrichten + Reboot |
| 24-Stunden-Test ohne Crash | Manuell — Pipeline starten, Logs nach 24h prüfen |
| 5 echte Akquise-Mails laufen sauber durch | Manuell — Mails kommen rein, Ordner unter `001_AQUISE\Objekte\` prüfen |
| Health-Check loggt Statistik | ✅ getestet (`tests/test_main_healthcheck.py`) |
| Counter zählen korrekt | ✅ getestet |
| Start-Skripte vorhanden | ✅ `start_pipeline.bat`, `start_pipeline.ps1` |

Die Live-Akzeptanzkriterien (Reboot, 24h, 5 echte Mails) sind manuelle
Tests, die du selbst durchführst — nicht durch Code abdeckbar.
