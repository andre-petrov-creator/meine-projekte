# Modul 4 — Aktueller Stand v1.3 (Brief für neues Chat-Fenster)

**Datum:** 2026-04-26
**Zweck:** Briefing für ein neues Chat-Fenster, das einen alten `PLAN_Modul4_Ueberarbeitung.md` (aus einem anderen Chat) ausführen soll. Dieses Dokument beschreibt den **aktuellen Modul-4-Stand**, damit das neue Fenster den alten Plan an die Realität anpassen kann.

---

## Quellen der Wahrheit (alles auf GitHub gepusht)

- **`https://raw.githubusercontent.com/andre-petrov-creator/meine-projekte/main/Aufteiler/modul_4_miete.xml`** ← Modul 4 v1.3
- **`https://raw.githubusercontent.com/andre-petrov-creator/meine-projekte/main/Aufteiler/orchestrator.xml`** ← Orchestrator v2.2

Lokal gibt es **keine** XML-Kopie mehr (bewusst gelöscht zur Vermeidung von Konflikten).

---

## Was Modul 4 v1.3 jetzt macht

### Kern-Aufgabe
Pro WE die maximal-mögliche Kaltmiete via Mietspiegel-Algorithmus berechnen. Liefert Inputs für Excel-MIETER-Sheet. Excel rechnet Mieten und Renditen daraus.

### Excel-Outputs (was Modul 4 in welche Zellen schreibt)

| Sheet | Zelle/Bereich | Inhalt | Quelle |
|-------|---------------|--------|--------|
| MIETER | M6 | Mietspiegel-Mittelwert €/qm VOR Sanierung | Modul-4 Step 2 (Wohnflächen-gewichtet) |
| MIETER | P6 | Kappungsgrenze (0.15 oder 0.20) | Modul-4 Step 3 |
| MIETER | A8:K27 | WE-Stamm-Tabelle | Modul-4 Step 4 |
| **MIETER** | **Y8:Y27** | **per-WE Mietspiegel-Obergrenze €/qm** | **Modul-4 Step 1 (O = K × 1.18)** ← NEU in v1.3 |
| BESICHTIGUNG | B33-B36 | IST/SOLL Jahresnettokaltmiete (Hinweis-Werte) | Σ aus WE-Tabelle |

### Was Modul 4 NICHT mehr direkt macht
- Kappungsgrenzen-Berechnung pro WE → Excel (Spalte N nutzt jetzt `(Y+M6)/2` als Cap)
- §559-Umlage → Excel (T5 = T4×8%, T6 = T5/12/F28; fließt automatisch in R via `R = (Y+T6)*F`)
- JNKM-Summen → Excel
- VK-Berechnung → VK_CF-Sheet

### Architektur-Prinzip (3 Datenpfade, war früher 2 Hebel)

```
HEBEL 1: §558 Mietspiegel-Mittelwert     → MIETER!M6 (eine Zahl, gewichtet)
HEBEL 2: §558 Spannenobergrenze pro WE   → MIETER!Y8:Y27 (per WE)
HEBEL 3: §559 Modernisierungsumlage      → MIETER!T4 → T5 → T6 (Excel-internal)

Daraus rechnet Excel:
  MIETER!N (Kaltmiete NEU für Bestand) = IST + Kappung, gecapped auf (Y+M6)/2
  MIETER!R (Kaltmiete SOLL für Neuvermietung) = (Y + T6) * F
  MIETER!T (SOLL KM/qm) = R / F
```

### Workflow (was Modul 4 im Chat tut)

| Step | Zweck |
|------|-------|
| 0 | Stadt-Page aus Notion Mietspiegel-DB laden |
| 1 | Für jede WE Mietspiegel-Algorithmus durchlaufen, **Soll oben EUR/qm** als per-WE-Wert ermitteln (= MIETER!Y) |
| 2 | M6-Mittelwert (Wohnflächen-gewichtet) |
| 3 | Kappungsgrenze (Stadt-spezifisch) |
| 4 | WE-Stamm-Tabelle für MIETER!A8:K27 |
| 5 | T4-Verification (Modernisierungs-Kosten aus Modul 2) |
| 6 | Mietpreisbremse-Hinweis als Text |
| 7 | Zusammenfassung + Excel-Preview |

---

## Was wir HEUTE konkret an Modul 4 geändert haben (v1.2 → v1.3)

### Inhaltliche Änderungen
1. **Excel-Transfer-Block erweitert:** Neue Zeile `MIETER!Y8:Y27` als Pflicht-Output pro WE
2. **`<ablauf_excel_uebergabe>`** aktualisiert: Modul 4 setzt jetzt zusätzlich Y, Excel rechnet R = (Y+T6)*F und N nutzt (Y+M6)/2 als Cap
3. **Workflow Step 1:** neuer Hinweis `<excel_transfer_je_we>` — `Soll oben EUR/qm` muss pro WE in `MIETER!Y(8+i)` (i=WE-Index) eingetragen werden
4. **Workflow Step 7 Output-Tabelle:** neue Zeile „Spannenobergrenze pro WE → MIETER!Y8:Y27"
5. **Workflow Step 7 `<excel_wird_rechnen>`:** Beschreibt jetzt
   - NEU-Miete pro WE = `min(IST × (1+Kappung), (Y+M6)/2)` ← war: `min(IST × (1+Kappung), M6)`
   - SOLL-Miete pro WE = `Y × m²` ← war: `NEU + T6`
6. **`<option_c_logik>` `<prinzip>`-Block:** Komplett neu geschrieben — 3 Datenpfade (M6 / Y / T6) statt 2 Hebel. Erklärt Y als HEBEL 2 explizit.
7. **Terminologie vereinheitlicht:** „Soll-Miete" → „Kaltmiete SOLL" (5 Stellen geändert: Z38, Z71-73 (im prinzip), Z352, Z361)

### Was UNVERÄNDERT geblieben ist
- Mietspiegel-Algorithmus pro WE (Step 1) — interne Logik gleich
- Notion Data-Source-IDs
- Zuschlag-Quelle-Matrix (4.1-4.12)
- Doppelrechnung-Safety-Check
- Aufteiler-2026-Behandlung (geht nicht in M6)
- Token-Budget (max 2 Tool-Calls)
- Output-Format-Block (Reihenfolge der Markdown-Tabellen)
- Safety-Checks

---

## System-Kontext (Orchestrator v2.2)

### Neue System-Regel im Orchestrator
```
ASSET_TRENNUNG (priority HIGHEST):
Wohnungen, Garagen und Stellplaetze NIE in der Verkaufspreis-Berechnung
vermischen. Wohnungs-Kaltmiete -> Cashflow-VK in VK_CF (nur Wohnungen).
Garagen/Stellplaetze -> Markt-Preis pro WE in VERKAUFSMATRIX!V
(manuelle Eingabe aus Grundstuecksmarktbericht).
```

### Excel-Architektur-Stand (was Excel bereits kann)
- MIETER: Spalte Y angelegt mit Styling (grüner Header, grauer Body, €/qm-Format)
- MIETER!R = `=IF(Y="","",IFERROR((Y+$T$6)*F,""))` (gibt "" zurück wenn Y leer)
- MIETER!N nutzt `(Y+$M$6)/2` als Cap an drei Stellen in der Formel
- VK_CF Spalten umbenannt: G=Nettokaltmiete €/Mo, H=Nettokaltmiete €/m², I=Verkaufspreis, J=Verkaufspreis €/m²
- VK_CF Bewirtschaftung wirkt INLINE in I/M/N-Formeln (nicht sichtbare Reduktions-Spalte)
- VK_CF Vergleichsblock Z41-50: Wohnungen-Markt (=`VERKAUFSMATRIX!U26`) vs. Wohnungen-Cashflow (=`I38`), Garagen NICHT enthalten
- VERKAUFSMATRIX!Y = `=IF(ISNUMBER(MIETER!F<src>),VK_CF!I<row>+V<row>+X<row>,"")` (Bundle pro WE)
- Bulletproof Empty-Row-Handling: alle VK_CF + VERKAUFSMATRIX-Formeln gewrappt mit `IF(ISNUMBER(MIETER!F<src>),...,"")`

---

## Known Open Items / Lücken

| Bereich | Status | Note |
|---------|--------|------|
| Modul 0 (Quick-Check) | existiert auf GitHub | nicht in diesem Refactor angefasst |
| Modul 5 (Deal Verdict) | **fehlt** auf GitHub | wird im Orchestrator referenziert, ist aber leer |
| Garagen-Preise: Auto-Anbindung Grundstücksmarktbericht | manuell | aktuell User-Eingabe in `VERKAUFSMATRIX!V` pro WE |
| §559-Umlage in N (Bestand-Mieter) | nicht enthalten | N rechnet nur §558 (Kappung), §559 fließt nur in R (Neuvermietung) |
| Modul 4 schreibt Y momentan nicht automatisch in Excel | ist Chat-Output, User trägt manuell ein | wäre Automatisierungs-Refactor |

---

## Was für das neue Fenster wichtig ist

**Wenn der alte `PLAN_Modul4_Ueberarbeitung.md` Änderungen vorschlägt:**

1. **Prüfe Überlappung** mit den oben gelisteten v1.3-Änderungen → wenn schon erledigt, aus dem alten Plan streichen
2. **Prüfe Konflikt** mit der ASSET_TRENNUNG-Regel → keine Garagen-Mieten in MIETER!R einrechnen, keine Garage-Preise in VK_CF reinziehen
3. **Prüfe Kompatibilität** mit der neuen MIETER!Y-Architektur → wenn der alte Plan noch von „N+T6"-Logik ausgeht, an „Y*F"-Logik anpassen
4. **Prüfe Terminologie** → wenn alter Plan noch „Soll-Miete" sagt, auf „Kaltmiete SOLL" mappen

**Briefing-Block für das neue Fenster (zum Reinpasten):**

```
Lies erst diese drei Quellen als Kontext, BEVOR du irgendwas planst:

1. Plan-Datei (alt, aus früherem Chat):
   <hier den Inhalt von PLAN_Modul4_Ueberarbeitung.md einfügen>

2. Aktueller Modul-4 Stand (v1.3) — fetch:
   https://raw.githubusercontent.com/andre-petrov-creator/meine-projekte/main/Aufteiler/modul_4_miete.xml

3. Aktueller Orchestrator (v2.2) — fetch:
   https://raw.githubusercontent.com/andre-petrov-creator/meine-projekte/main/Aufteiler/orchestrator.xml

4. Briefing-Dokument (DIESE Datei) als lokaler Kontext:
   c:\Users\andre\OneDrive - APPV Personalvermittlung\Immobilien\001_AQUISE\Objekte\0_Aufteiler Skill\plans\2026-04-26-modul4-aktueller-stand-fuer-neuen-plan.md

Dann:
A) Sortiere den alten Plan: was ist durch v1.3 schon gemacht? Was ist obsolet? Was bleibt offen?
B) Verifiziere Konflikt-frei mit ASSET_TRENNUNG, MIETER!Y-Architektur, neuer Terminologie
C) Schreibe einen NEUEN, sauberen Plan im Format von superpowers:writing-plans
D) Speichere ihn nach: c:\...\0_Aufteiler Skill\plans\YYYY-MM-DD-modul4-<feature>.md
E) Erst nach Plan-Approval: Execution starten

Bei Unklarheiten: fragen, nicht raten.
```
