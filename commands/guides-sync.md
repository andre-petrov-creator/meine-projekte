---
description: Synchronisiert die Guides-Datenbank mit dem Ordner "Anleitungen Guides" (neue Dateien analysieren, gelöschte markieren)
argument-hint: "[optional: Dateiname für Force-Refresh]"
---

# /guides-sync — Guides-Datenbank aktualisieren

**Ziel:** Den Ordner `c:\Users\andre\OneDrive - APPV Personalvermittlung\KI\Prompt´s_Anweisungen\Anleitungen Guides\` mit der Datei `Guides_Datenbank.md` im selben Ordner abgleichen und neue Inhalte aufnehmen.

## Schritte (genau in dieser Reihenfolge)

1. **Liste alle Dateien** im Ordner `Anleitungen Guides/` (außer `Guides_Datenbank.md` selbst und `.claude/`-Unterordner). Nimm Dateiname + Größe + mtime mit.

2. **Lies `Guides_Datenbank.md`** und extrahiere die Liste der dort bereits dokumentierten Dateien aus dem Block `## 📋 Inventar`.

3. **Diff bilden:**
   - **Neu** = im Ordner, aber nicht in MD
   - **Entfernt** = in MD, aber nicht mehr im Ordner
   - **Geändert** = mtime/size weicht ab → kennzeichne als „⚠️ ggf. neu prüfen"

4. **Für jede neue Datei:**
   - Lies den Inhalt (PDFs: bei >10 Seiten `pages: "1-20"`)
   - Erstelle einen Eintrag im selben Format wie bestehende Einträge (Thema, Kerninhalt, Aufteiler-Relevanz-Ampel)
   - Halte dich an das exakte Schema unten

5. **Für jede entfernte Datei:** Eintrag in `## 🗑️ Archiv (entfernt)`-Block verschieben mit Datum.

6. **Update den Header-Block** der MD: `Letzter Sync: <Datum>`, `Anzahl Guides: <n>`.

7. **Backup vor Schreiben:** Kopiere die alte `Guides_Datenbank.md` nach `Backup/Guides_Datenbank_<YYYY-MM-DD-HHMM>.md` (Backup-Ordner anlegen falls nicht da).

8. **Schreibe die aktualisierte MD.**

9. **Report an User:**
   ```
   ============================================================
   Guides-Sync abgeschlossen
   ============================================================
   ✅ Neu: <n> (<Liste>)
   🗑️ Entfernt: <n> (<Liste>)
   ⚠️ Geändert: <n>
   📊 Total: <n> Guides
   ============================================================
   ```

## Eintrags-Schema (exakt einhalten)

```markdown
### <Dateiname>
- **Thema:** <1 Zeile>
- **Größe / Datum:** <KB> / <YYYY-MM-DD>
- **Kerninhalt:**
  - <Bullet 1>
  - <Bullet 2>
  - <Bullet 3>
- **Aufteiler-Relevanz:** <🟢|🟡|🔴> — <1 Satz Begründung>
- **Übernahme-Idee:** <konkret oder "—">
```

## Wichtige Regeln

- **Sprache:** Deutsch
- **Token-Sparsam:** Nur neue/geänderte Dateien lesen, nicht alle bei jedem Sync
- **Kein Halluzinieren:** Wenn PDF nicht lesbar, schreibe „⚠️ Inhalt nicht extrahierbar" statt zu raten
- **Duplikate erkennen:** Bei identischer Größe + ähnlichem Namen (z.B. „guide.pdf" + „guide 1.pdf") → als Duplikat markieren, nur 1× zusammenfassen
- **Bei Fehler im Lesevorgang:** Eintrag mit `⚠️ FEHLER` markieren, weitermachen, am Ende sammeln und reporten

## Argument-Behandlung

Falls `$ARGUMENTS` gesetzt ist (z.B. `/guides-sync Tools-Guide.pdf`):
- Force-Refresh nur für diese Datei (auch wenn sie schon in MD steht)
- Nützlich wenn ein Guide aktualisiert wurde aber Dateiname gleich blieb
