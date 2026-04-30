# VK_CF Nettokaltmiete + MIETER per-WE Spannenobergrenze — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** End-to-end Konsistenz zwischen Modul 4 (per-WE Spannenobergrenze) → MIETER (per-WE SOLL-Werte) → VK_CF (saubere Nettokaltmiete-Anzeige + korrekte Verkaufspreis-Berechnung). Bewirtschaftungskosten verschwinden aus dem VK_CF-Display, wirken nur inline in den Berechnungs-Formeln. MIETER!N erhält neue Cap-Logik mit gemitteltem Mietspiegel-Wert pro WE.

**Architecture:**
- **Modul 4** wird um eine vierte Excel-Output-Zelle (`MIETER!Y8:Y27`) erweitert: pro WE die berechnete Spannenobergrenze (€/m²).
- **MIETER** bekommt neue Eingangs-Spalte `Y` ("Spannenobergrenze €/m² (per WE)"). `R`-Formel wird radikal vereinfacht zu `=Y*F`. `T`-Formel bleibt `=R/F`. `N`-Formel ersetzt jeden `$M$6`-Bezug durch den Durchschnitt `(Y+$M$6)/2`.
- **VK_CF** Spalten G/H/I/J werden umbenannt und semantisch umgebaut: H zeigt jetzt €/m² (statt Bewirt-reduzierte €/Mo), I baut Bewirt inline ein. M und N werden synchron angepasst (H durch `G*(1-$C$8)` ersetzt).
- **orchestrator.xml** Excel-Handoff-Section wird auf neue Spalten-/Formel-Realität aktualisiert.
- **GitHub** Push: `modul_4_miete.xml` und `orchestrator.xml` nach `andre-petrov-creator/meine-projekte/Aufteiler/`.

**Tech Stack:** XML (Notepad-edits), Excel xlsx (openpyxl Python), Git (gh CLI).

**Wichtige Vorab-Entscheidung (festgehalten):**
- §559 BGB Modernisierungsumlage (T4/T5/T6) wird in der neuen `R`-Formel NICHT mehr addiert. Für die Prosperstr. ist `T4=0`, also kein Effekt. Falls bei späteren Objekten §559 wieder relevant wird, muss `R` zu `=Y*F + T6*F` erweitert werden — siehe Task 7 Note.

---

## File Structure

| Datei | Änderung |
|-------|----------|
| `modul_4_miete.xml` | Excel-Transfer-Block: Y-Range hinzufügen. Workflow Step 1+7: per-WE Spannenobergrenze als Y-Output. Terminologie konsolidieren. |
| `Kalkulation_Aufteiler_mit_VK_CF.xlsx` (Sheet `MIETER`) | Y-Spalte (Header + leere Eingangs-Zellen). R-Formeln Z8-Z27 vereinfachen. N-Formeln Z8-Z27 mit Avg-Cap umbauen. T bleibt. |
| `Kalkulation_Aufteiler_mit_VK_CF.xlsx` (Sheet `VK_CF`) | C8-Label. Formel-Box E6+E8. Headers G/H/I/J Z17. Formeln G/H/I/J/M/N Z18-Z37. SUMME Z38 H. |
| `orchestrator.xml` | Z101, Z151, Z158, Z161, Z168 — alle Bezüge auf alte VK-Formel und R-Definition aktualisieren. |
| GitHub Repo `andre-petrov-creator/meine-projekte` | Push `modul_4_miete.xml` + `orchestrator.xml` nach `Aufteiler/`. |

---

## Phase 1 — Modul 4 XML erweitern

### Task 1: Backup Modul 4

**Files:** `modul_4_miete.xml`

- [ ] **Step 1: Backup anlegen**

```bash
cp "modul_4_miete.xml" "modul_4_miete.xml.bak-2026-04-26"
```

Run von: `c:/Users/andre/OneDrive - APPV Personalvermittlung/Immobilien/001_AQUISE/Objekte/0_Aufteiler Skill/`

Expected: keine Fehler-Ausgabe.

### Task 2: Excel-Transfer-Block um Y-Range ergänzen

**Files:** `modul_4_miete.xml` (Z376-395)

- [ ] **Step 1: Y-Range-Zeile in `<ziel_zellen>` Tabelle einfügen**

Aktuelle Tabelle (Z378-386):
```
| Sheet         | Zelle/Bereich | Bedeutung                              | Quelle         |
| MIETER        | M6            | Mietspiegel VOR Sanierung EUR/qm       | Modul 4 Step 2 |
| MIETER        | P6            | Kappungsgrenze                         | Modul 4 Step 3 |
| MIETER        | A8:K27        | WE-Stamm-Tabelle                       | Modul 4 Step 4 |
| MIETER        | T4            | Aufteiler-Sanierungskosten             | Modul 2 (nicht Modul 4) |
```

Direkt **nach** der A8:K27-Zeile einfügen:
```
| MIETER        | Y8:Y27        | Spannenobergrenze pro WE EUR/qm        | Modul 4 Step 1 (O = K × 1,18) |
```

- [ ] **Step 2: `<ablauf_excel_uebergabe>` aktualisieren**

Z388-394 — bei Schritt "Modul 4 setzt M6, P6, A8:K27" ergänzen:

Alt:
```
2. Modul 4 setzt M6, P6, A8:K27
3. Excel rechnet automatisch T5, T6, Spalten L/M/N/P/Q/R/T/W
```

Neu:
```
2. Modul 4 setzt M6, P6, A8:K27, Y8:Y27 (per-WE Spannenobergrenze)
3. Excel rechnet automatisch T5, T6, Spalten L/M/N/P/Q/R/T/W (R = Y × F, N nutzt (Y+M6)/2 als Cap)
```

- [ ] **Step 3: Verifikation**

```bash
grep -n "Y8:Y27" modul_4_miete.xml
```

Expected: zwei Treffer (eine in `<ziel_zellen>`, eine in `<ablauf_excel_uebergabe>`).

### Task 3: Workflow Step 7 Zusammenfassung-Tabelle aktualisieren

**Files:** `modul_4_miete.xml` (Z331-351)

- [ ] **Step 1: Output-Tabelle erweitern**

Z333-341 — Tabelle:
```
| Position | Wert | Excel-Ziel |
| Mietspiegel-Mittelwert VOR Sanierung | [X] EUR/qm | MIETER!M6 |
| Kappungsgrenze | [X]% | MIETER!P6 |
| WE-Anzahl | [X] | MIETER A8:K27 |
| Σ Wohnflaeche | [X] m² | F28 |
| Σ IST Kaltmiete | [X] EUR/Mo | J28 |
| Aufteiler-Kosten fuer T4 (aus Modul 2) | [X] EUR | MIETER!T4 |
```

Direkt nach "WE-Anzahl"-Zeile einfügen:
```
| Spannenobergrenze pro WE | je WE [X] EUR/qm (5 Werte) | MIETER!Y8:Y27 |
```

- [ ] **Step 2: `<excel_wird_rechnen>` aktualisieren**

Z342-350. Alte Zeilen:
```
- NEU-Miete pro WE = min(IST × (1 + Kappung), M6) [Excel Spalte N]
- SOLL-Miete pro WE = NEU + T6 [Excel Spalte R]
```

ersetzen durch:
```
- NEU-Miete pro WE = min(IST × (1 + Kappung), (Y+M6)/2) [Excel Spalte N — Cap = Avg per-WE Obergrenze + M6]
- SOLL-Miete pro WE = Y × m² [Excel Spalte R = Spannenobergrenze × Wohnflaeche]
```

- [ ] **Step 3: Verifikation**

```bash
grep -n "Y × m²" modul_4_miete.xml
grep -n "(Y+M6)/2" modul_4_miete.xml
```

Expected: je ein Treffer.

### Task 4: Step 1 Output-Tabelle ergänzen

**Files:** `modul_4_miete.xml` (Z283-285)

- [ ] **Step 1: Hinweis ergänzen, dass `Soll oben EUR/qm` direkt nach Y8:Y27 transferiert wird**

Z283-285 — aktuell:
```
<output_table>
  | WE | m² | Baujahr-Klasse | Bestand-Zuschlaege | Soll unten EUR/qm | Soll mittel EUR/qm | Soll oben EUR/qm | Aufteiler 2026 (fuer T4) |
</output_table>
```

ersetzen durch:
```
<output_table>
  | WE | m² | Baujahr-Klasse | Bestand-Zuschlaege | Soll unten EUR/qm | Soll mittel EUR/qm | Soll oben EUR/qm | Aufteiler 2026 (fuer T4) |
</output_table>
<excel_transfer_je_we>
  Spalte "Soll oben EUR/qm" wird PRO WE in MIETER!Y(8+i) eingetragen
  (i = WE-Index 0..n-1). Damit hat Excel die per-WE Spannenobergrenze
  fuer R-Formel (=Y*F) und N-Formel (Cap = (Y+M6)/2).
</excel_transfer_je_we>
```

- [ ] **Step 2: Verifikation**

```bash
grep -n "MIETER!Y(8+i)" modul_4_miete.xml
```

Expected: 1 Treffer.

### Task 5: Terminologie-Vereinheitlichung „Soll-Miete" → „Kaltmiete SOLL"

**Files:** `modul_4_miete.xml`

- [ ] **Step 1: Inventar erstellen**

```bash
grep -n "Soll-Miete\|SOLL-Miete\|Soll Miete\|SollMiete" modul_4_miete.xml
```

Expected: ca. 6 Treffer.

- [ ] **Step 2: Treffer einzeln umbenennen**

Pro Treffer prüfen, ob „Kaltmiete SOLL" inhaltlich passt (referenziert `MIETER!R`?). Wenn ja → ersetzen. Sonst stehen lassen.

Konkret zu erwartende Stellen (aus voriger Analyse):
- Z38: `Pro WE Soll-Miete per Mietspiegel-Algorithmus berechnen.` → `Pro WE Kaltmiete SOLL per Mietspiegel-Algorithmus berechnen.`
- Z71: `Excel Spalte R = N + T6 (Soll-Miete inkl. Modernisierung)` → bereits in Task 3 ersetzt (aber der `<option_c_logik>`-Block in Z71 ist eine SEPARATE Kopie der Aussage und muss separat gepflegt werden)
- Z73: `Vollstaendige Soll-Miete = Mietspiegel + Modernisierungsumlage` → bleibt — beschreibt das ALTE Prinzip, das nicht mehr gilt. **Diesen Absatz inhaltlich ersetzen** (siehe Task 6).
- Z346: `SOLL-Miete pro WE = NEU + T6 [Excel Spalte R]` → in Task 3 ersetzt.
- Z361: `Soll-Miete pro WE (NUR BESTAND-Zuschlaege, ...)` → `Kaltmiete SOLL pro WE (NUR BESTAND-Zuschlaege, ...)`
- Z385: `SOLL Jahresnettokaltmiete` → bleibt (schon "Kaltmiete" im Namen).

- [ ] **Step 3: Verifikation**

```bash
grep -n "Soll-Miete\|SOLL-Miete" modul_4_miete.xml
```

Expected: 0 Treffer (oder nur Stellen die bewusst stehen bleiben — dann manuell prüfen).

### Task 6: `<option_c_logik>` Prinzip-Beschreibung anpassen

**Files:** `modul_4_miete.xml` (Z58-75)

Der Block `<prinzip>` beschreibt aktuell die ALTE Logik (Hebel 2 = §559 in `R`). Nach unserer Änderung steckt §559 nicht mehr in `R` (R ist jetzt nur Spannenobergrenze × m²). §559-Umlage T6 bleibt aber im Sheet (für eventuelle spätere Verwendung).

- [ ] **Step 1: `<prinzip>`-Block überarbeiten**

Aktuell Z58-75:
```
<prinzip>
  Zwei unabhaengige Miet-Hebel, beide werden genutzt:
  
  HEBEL 1 - §558 BGB Mietspiegel (durch Modul 4):
  - Ortsuebliche Vergleichsmiete auf Basis BESTEHENDER Modernisierungen
  - Fliesst in Excel M6
  - Excel Spalte N berechnet Kappungsgrenze auf dieser Basis
  
  HEBEL 2 - §559 BGB Modernisierungsumlage (durch Excel):
  - 8% p.a. der Aufteiler-Sanierungskosten auf Miete umlegbar
  - Excel T4 = Modernisierungskosten (aus Modul 2 RENO!O8)
  - Excel T5 = T4 * 0.08
  - Excel T6 = T5 / 12 / F28 (Umlage pro qm pro Monat)
  - Excel Spalte R = N + T6 (Soll-Miete inkl. Modernisierung)
  
  Ergebnis: Vollstaendige Soll-Miete = Mietspiegel + Modernisierungsumlage
  ohne Doppelrechnung.
</prinzip>
```

ersetzen durch:
```
<prinzip>
  Drei Datenpfade, unabhaengig:
  
  HEBEL 1 - §558 BGB Mietspiegel-Mittelwert M6 (durch Modul 4):
  - Ortsuebliche Vergleichsmiete auf Basis BESTEHENDER Modernisierungen
  - Fliesst in Excel M6 (gewichteter Mittelwert ueber alle WEs)
  - Excel Spalte N nutzt Cap = (Y+M6)/2 fuer Kappungsgrenze (per WE)
  
  HEBEL 2 - §558 BGB Spannenobergrenze pro WE Y8:Y27 (durch Modul 4):
  - Pro WE die Mietspiegel-Obergrenze nach Bestand-Zuschlaegen
  - Fliesst in Excel Y8:Y27 (per WE)
  - Excel Spalte R = Y × F (Kaltmiete SOLL fuer Neuvermietung)
  - Excel Spalte T = R/F (= Y, KM/qm Anzeige)
  
  HEBEL 3 - §559 BGB Modernisierungsumlage T4/T5/T6 (durch Excel):
  - 8% p.a. der Aufteiler-Sanierungskosten auf Miete umlegbar
  - T4 = Modernisierungskosten (aus Modul 2 RENO!O8)
  - T5 = T4 * 0.08, T6 = T5 / 12 / F28
  - HINWEIS: T6 wird in der aktuellen R-Formel NICHT mehr addiert.
    Falls fuer kuenftige Objekte gewuenscht: R = Y*F + T6*F.
  
  Ergebnis SOLL-Miete:
  - Bestandsmieter: Spalte N (begrenzt durch Kappung + Avg-Cap)
  - Neuvermietung: Spalte R = Y × m² (volle Spannenobergrenze)
</prinzip>
```

- [ ] **Step 2: Verifikation**

```bash
grep -n "Drei Datenpfade" modul_4_miete.xml
```

Expected: 1 Treffer.

---

## Phase 2 — Excel MIETER refactor

### Task 7: Excel Backup

**Files:** `Kalkulation_Aufteiler_mit_VK_CF.xlsx`

- [ ] **Step 1: Datei mit Timestamp backupen**

```bash
cp "Kalkulation_Aufteiler_mit_VK_CF.xlsx" "Kalkulation_Aufteiler_mit_VK_CF.bak-2026-04-26.xlsx"
```

Expected: kein Fehler.

### Task 8: MIETER Spalte Y anlegen (Header + leere Eingangs-Zellen)

**Files:** `Kalkulation_Aufteiler_mit_VK_CF.xlsx` Sheet `MIETER`

- [ ] **Step 1: Header Y6 + Y7 setzen**

Python-Skript:
```python
import openpyxl
fp = r"c:\Users\andre\OneDrive - APPV Personalvermittlung\Immobilien\001_AQUISE\Objekte\0_Aufteiler Skill\Kalkulation_Aufteiler_mit_VK_CF.xlsx"
wb = openpyxl.load_workbook(fp)
ws = wb['MIETER']
ws['Y6'] = 'Modul 4 Output'
ws['Y7'] = 'Spannenobergrenze €/m² (per WE)'
wb.save(fp)
```

- [ ] **Step 2: Y8-Y27 mit Test-Daten für Prosperstr. befüllen** (damit R sofort rechnet)

```python
import openpyxl
fp = r"..."
wb = openpyxl.load_workbook(fp)
ws = wb['MIETER']
test_data = {
    'Y8':  8.65,   # WE 01 EG
    'Y9':  8.69,   # WE 02 1.OG
    'Y10': 8.97,   # WE 03 2.OG
    'Y11': 8.73,   # WE 04 3.OG
    'Y12': 8.72,   # WE 05 DG
}
for cell, val in test_data.items():
    ws[cell] = val
wb.save(fp)
```

- [ ] **Step 3: Verifikation**

```python
import openpyxl
fp = r"..."
wb = openpyxl.load_workbook(fp, data_only=False)
ws = wb['MIETER']
print('Y6:', ws['Y6'].value)
print('Y7:', ws['Y7'].value)
for r in range(8, 13):
    print(f'Y{r}:', ws[f'Y{r}'].value)
```

Expected: Y6 + Y7 als Strings, Y8-Y12 als floats 8.65/8.69/8.97/8.73/8.72.

### Task 9: MIETER Spalte R Formel umstellen (Y × F)

**Files:** `Kalkulation_Aufteiler_mit_VK_CF.xlsx` Sheet `MIETER`

- [ ] **Step 1: R8-R27 Formeln ersetzen**

```python
import openpyxl
fp = r"..."
wb = openpyxl.load_workbook(fp)
ws = wb['MIETER']
for r in range(8, 28):
    ws[f'R{r}'] = f'=IFERROR(Y{r}*F{r},"")'
wb.save(fp)
```

- [ ] **Step 2: Verifikation Formel + berechneter Wert**

```bash
python -c "import openpyxl; wb=openpyxl.load_workbook(r'...'); ws=wb['MIETER']; print('R8:', ws['R8'].value)"
```

Expected: `R8: =IFERROR(Y8*F8,"")`

Excel öffnen, Sheet MIETER, R8 sollte 8.65 × 92.98 = **804,38 €** zeigen.

- [ ] **Step 3: T-Werte plausibilisieren**

T8 ist `=IFERROR(R8/F8,"")` = 804,38 / 92,98 = 8,65 ✓ (matches Y8).

### Task 10: MIETER Spalte N Formel umstellen (Avg-Cap)

**Files:** `Kalkulation_Aufteiler_mit_VK_CF.xlsx` Sheet `MIETER`

Aktuelle N8-Formel (verkürzt):
```
=IFERROR(
  IF(J8/F8 > $M$6, J8,
     IF(I8 < EDATE($N$4,-36),
        IF(J8*(1+$P$6)/F8 <= $M$6, J8*(1+$P$6), F8*$M$6),
        J8)),
  "")
```

Jeder `$M$6`-Bezug wird durch `(Y8+$M$6)/2` ersetzt — das ist DREIMAL pro Zeile.

- [ ] **Step 1: N8-N27 Formeln per Skript umstellen**

```python
import openpyxl
fp = r"..."
wb = openpyxl.load_workbook(fp)
ws = wb['MIETER']
for r in range(8, 28):
    cap = f'(Y{r}+$M$6)/2'
    formula = (
        f'=IFERROR('
        f'IF(J{r}/F{r}>{cap},J{r},'
        f'IF(I{r}<EDATE($N$4,-36),'
        f'IF(J{r}*(1+$P$6)/F{r}<={cap},J{r}*(1+$P$6),F{r}*{cap}),'
        f'J{r})),'
        f'"")'
    )
    ws[f'N{r}'] = formula
wb.save(fp)
```

- [ ] **Step 2: Verifikation Formel**

```bash
python -c "import openpyxl; wb=openpyxl.load_workbook(r'...'); ws=wb['MIETER']; print('N8:', ws['N8'].value)"
```

Expected: Formel enthält `(Y8+$M$6)/2` an drei Stellen.

- [ ] **Step 3: Verifikation Wert in Excel öffnen**

WE 01: Y8=8,65, M6=10 → Cap = (8,65+10)/2 = 9,325. IST/F = 380/92,98 = 4,09 < 9,325. EDATE-Check geht in 36-Monats-Fristen-Branch. IST*(1+15%)/F = 380*1,15/92,98 = 4,70 < 9,325 → N8 = IST*1,15 = **437,00 €** (etwa, je nach M6).

Wenn M6 = 9 → Cap = (8,65+9)/2 = 8,825 → ähnliche Logik, N8 ≈ 437.

### Task 11: MIETER-Konsistenz-Check

**Files:** `Kalkulation_Aufteiler_mit_VK_CF.xlsx` Sheet `MIETER`

- [ ] **Step 1: Excel öffnen und visuell prüfen**

Spalten Z8-Z12:
- F (m²): 92,98 / 93,39 / 92,04 / 95,45 / 85,99
- Y (€/m²): 8,65 / 8,69 / 8,97 / 8,73 / 8,72
- R (€/Mo): **804,38 / 811,49 / 825,87 / 832,82 / 749,76**
- T (€/m²): 8,65 / 8,69 / 8,97 / 8,73 / 8,72 (= Y, weil T=R/F=Y*F/F=Y)

- [ ] **Step 2: SUMME Z28 prüfen**

R28 = SUM(R8:R12) = 804,38 + 811,49 + 825,87 + 832,82 + 749,76 = **4.024,32 €** ✓ (matches Modul 4 Screenshot Σ).

---

## Phase 3 — Excel VK_CF refactor

### Task 12: VK_CF C8-Label aktualisieren

**Files:** `Kalkulation_Aufteiler_mit_VK_CF.xlsx` Sheet `VK_CF`

- [ ] **Step 1: A8 (Label-Zelle) ändern**

```python
import openpyxl
fp = r"..."
wb = openpyxl.load_workbook(fp)
ws = wb['VK_CF']
ws['A8'] = 'Bewirtschaftungskosten (% v. Nettokaltmiete)'
wb.save(fp)
```

- [ ] **Step 2: Verifikation**

```bash
python -c "import openpyxl; wb=openpyxl.load_workbook(r'...'); ws=wb['VK_CF']; print('A8:', ws['A8'].value)"
```

Expected: `A8: Bewirtschaftungskosten (% v. Nettokaltmiete)`

### Task 13: VK_CF Formel-Box E6 + E8

**Files:** `Kalkulation_Aufteiler_mit_VK_CF.xlsx` Sheet `VK_CF`

- [ ] **Step 1: E6 + E8 ändern**

```python
import openpyxl
fp = r"..."
wb = openpyxl.load_workbook(fp)
ws = wb['VK_CF']
ws['E6'] = 'Bewirtschaftungskosten werden intern abgezogen (nicht angezeigt)'
ws['E8'] = 'VK = (Nettokaltmiete × (1 − Bewirtschaftung) × (1 − Steuer) − CF_Ziel) / k'
wb.save(fp)
```

- [ ] **Step 2: Verifikation**

```bash
python -c "import openpyxl; wb=openpyxl.load_workbook(r'...'); ws=wb['VK_CF']; print('E6:', ws['E6'].value); print('E8:', ws['E8'].value)"
```

### Task 14: VK_CF Headers G17/H17/I17/J17

**Files:** `Kalkulation_Aufteiler_mit_VK_CF.xlsx` Sheet `VK_CF`

- [ ] **Step 1: Vier Header-Zellen setzen** (mit Linebreak via `\n`)

```python
import openpyxl
fp = r"..."
wb = openpyxl.load_workbook(fp)
ws = wb['VK_CF']
ws['G17'] = 'Nettokaltmiete\nEUR/Mo'
ws['H17'] = 'Nettokaltmiete\nEUR/m²'
ws['I17'] = 'Verkaufspreis\nEUR'
ws['J17'] = 'Verkaufspreis\nEUR/m²'
wb.save(fp)
```

- [ ] **Step 2: Verifikation**

```bash
python -c "import openpyxl; wb=openpyxl.load_workbook(r'...'); ws=wb['VK_CF'];
for c in ['G17','H17','I17','J17']: print(c, ':', ws[c].value)"
```

### Task 15: VK_CF Spalte H Formeln (jetzt €/m²)

**Files:** `Kalkulation_Aufteiler_mit_VK_CF.xlsx` Sheet `VK_CF`

- [ ] **Step 1: H18-H37 ersetzen**

Alt: `=IFERROR(G18*(1-$C$8),"")` (= Bewirt-reduziert)
Neu: `=IFERROR(G18/F18,"")` (= €/m²)

```python
import openpyxl
fp = r"..."
wb = openpyxl.load_workbook(fp)
ws = wb['VK_CF']
for r in range(18, 38):
    ws[f'H{r}'] = f'=IFERROR(G{r}/F{r},"")'
wb.save(fp)
```

- [ ] **Step 2: Verifikation**

```bash
python -c "import openpyxl; wb=openpyxl.load_workbook(r'...'); ws=wb['VK_CF']; print('H18:', ws['H18'].value)"
```

Expected: `H18: =IFERROR(G18/F18,"")`

In Excel öffnen: H18 = 804,38/92,98 = **8,65** (statt vorher 643,50).

### Task 16: VK_CF Spalte I Formeln (Bewirt inline)

**Files:** `Kalkulation_Aufteiler_mit_VK_CF.xlsx` Sheet `VK_CF`

- [ ] **Step 1: I18-I37 ersetzen**

Alt: `=IFERROR((H18*(1-$C$7)-$C$11)/$C$14,"")` (H war Bewirt-reduziert)
Neu: `=IFERROR((G18*(1-$C$8)*(1-$C$7)-$C$11)/$C$14,"")` (Bewirt inline auf G)

```python
import openpyxl
fp = r"..."
wb = openpyxl.load_workbook(fp)
ws = wb['VK_CF']
for r in range(18, 38):
    ws[f'I{r}'] = f'=IFERROR((G{r}*(1-$C$8)*(1-$C$7)-$C$11)/$C$14,"")'
wb.save(fp)
```

- [ ] **Step 2: Verifikation Formel**

```bash
python -c "import openpyxl; wb=openpyxl.load_workbook(r'...'); ws=wb['VK_CF']; print('I18:', ws['I18'].value)"
```

Expected: `I18: =IFERROR((G18*(1-$C$8)*(1-$C$7)-$C$11)/$C$14,"")`

- [ ] **Step 3: Excel öffnen, I18 ablesen**

WE 01: G18 = 804,38, C8 = 0,20, C7 = 0,42, C11 = 0, C14 = 0,002334
I18 = (804,38 × 0,80 × 0,58 − 0) / 0,002334 = 373,23 / 0,002334 ≈ **159.917 €** ✓ (identisch zu vorherigem Wert).

### Task 17: VK_CF Spalte M Formeln (H → G*(1-C8))

**Files:** `Kalkulation_Aufteiler_mit_VK_CF.xlsx` Sheet `VK_CF`

- [ ] **Step 1: M18-M37 ersetzen**

Alt: `=IFERROR(-(H18-I18*$C$13*$C$5/12-L18)*$C$7,"")`
Neu: `=IFERROR(-(G18*(1-$C$8)-I18*$C$13*$C$5/12-L18)*$C$7,"")`

```python
import openpyxl
fp = r"..."
wb = openpyxl.load_workbook(fp)
ws = wb['VK_CF']
for r in range(18, 38):
    ws[f'M{r}'] = f'=IFERROR(-(G{r}*(1-$C$8)-I{r}*$C$13*$C$5/12-L{r})*$C$7,"")'
wb.save(fp)
```

- [ ] **Step 2: Verifikation**

```bash
python -c "import openpyxl; wb=openpyxl.load_workbook(r'...'); ws=wb['VK_CF']; print('M18:', ws['M18'].value)"
```

Expected: Formel enthält `G18*(1-$C$8)`.

### Task 18: VK_CF Spalte N Formeln (H → G*(1-C8))

**Files:** `Kalkulation_Aufteiler_mit_VK_CF.xlsx` Sheet `VK_CF`

- [ ] **Step 1: N18-N37 ersetzen**

Alt: `=IFERROR(H18-K18+M18,"")`
Neu: `=IFERROR(G18*(1-$C$8)-K18+M18,"")`

```python
import openpyxl
fp = r"..."
wb = openpyxl.load_workbook(fp)
ws = wb['VK_CF']
for r in range(18, 38):
    ws[f'N{r}'] = f'=IFERROR(G{r}*(1-$C$8)-K{r}+M{r},"")'
wb.save(fp)
```

- [ ] **Step 2: Verifikation**

```bash
python -c "import openpyxl; wb=openpyxl.load_workbook(r'...'); ws=wb['VK_CF']; print('N18:', ws['N18'].value)"
```

In Excel öffnen: N18 sollte ≈ **0,00 €** anzeigen (Kontrolle CF-Ziel hit).

### Task 19: VK_CF SUMME Z38 H-Zelle

**Files:** `Kalkulation_Aufteiler_mit_VK_CF.xlsx` Sheet `VK_CF`

- [ ] **Step 1: H38 ändern (SUM → AVERAGE, weil €/m² nicht summierbar)**

```python
import openpyxl
fp = r"..."
wb = openpyxl.load_workbook(fp)
ws = wb['VK_CF']
ws['H38'] = '=IFERROR(AVERAGE(H18:H37),"")'
wb.save(fp)
```

- [ ] **Step 2: Verifikation**

```bash
python -c "import openpyxl; wb=openpyxl.load_workbook(r'...'); ws=wb['VK_CF']; print('H38:', ws['H38'].value)"
```

In Excel: H38 = AVG(8,65; 8,69; 8,97; 8,73; 8,72) ≈ **8,75 €/m²**.

### Task 20: VK_CF End-to-End Verifikation

**Files:** Excel öffnen.

- [ ] **Step 1: Alle 5 WE-Zeilen prüfen**

Erwartete Werte (alle WE):

| WE | F (m²) | G (€/Mo) | H (€/m²) | I (VK €) | J (€/m²) | K | L | M | N (≈0?) |
|----|--------|----------|----------|----------|----------|---|---|---|---------|
| 1 | 92,98 | 804,38 | 8,65 | ~159.917 | ~1.720 | ~795 | ~426 | ~152 | ~0 |
| 2 | 93,39 | 811,49 | 8,69 | ~161.330 | ~1.727 | ~802 | ~430 | ~153 | ~0 |
| 3 | 92,04 | 825,87 | 8,97 | ~164.189 | ~1.784 | ~817 | ~438 | ~156 | ~0 |
| 4 | 95,45 | 832,82 | 8,73 | ~165.571 | ~1.735 | ~823 | ~442 | ~157 | ~0 |
| 5 | 85,99 | 749,76 | 8,72 | ~149.058 | ~1.733 | ~741 | ~397 | ~141 | ~0 |

- [ ] **Step 2: SUMME-Zeile 38 prüfen**

- F38 = SUM(F18:F37) = 459,85 m²
- G38 = SUM(G18:G37) = ~4.024 €
- H38 = AVERAGE(H18:H37) = ~8,75 €/m²
- I38 = SUM(I18:I37) = ~800.000 €
- J38 = I38/F38 = ~1.740 €/m²

- [ ] **Step 3: Slider-Test C5-C12**

In Excel: C8 von 0,20 auf 0,15 ändern. Erwartung:
- I (VK) springt nach oben (weil weniger Bewirt abgezogen wird)
- N bleibt ≈ 0 (weil Formel-Logik in sich konsistent)

C8 zurück auf 0,20. Werte sollten zurückspringen.

---

## Phase 4 — orchestrator.xml + GitHub

### Task 21: orchestrator.xml Excel-Handoff aktualisieren

**Files:** `orchestrator.xml`

- [ ] **Step 1: Z101 (mieten_logik_option_c-Block) anpassen**

Aktuell Z101 (im Block über §559 Modernisierungsumlage):
```
- Excel Spalte R = N + T6 (Soll-Miete inkl. Modernisierung)
```

ersetzen durch:
```
- Excel Spalte R = Y × F (Kaltmiete SOLL = Spannenobergrenze pro WE × Wohnflaeche)
- §559-Umlage T6 wird in der aktuellen R-Formel NICHT addiert (siehe Modul 4 Hinweis)
```

- [ ] **Step 2: Z149 (MIETER-Sheet-Beschreibung) anpassen**

Aktuell Z149:
```
<sheet name="MIETER">Mieten pro WE. Inputs aus Modul 4 (M6, P6, A8:K27). Inputs aus Modul 2 (T4 via RENO!O8). Rechnet: IST/NEU/SOLL-Mieten, Kappungsgrenze pro WE, Paragraph 559 Umlage, JNKM, Renditen.</sheet>
```

ersetzen durch:
```
<sheet name="MIETER">Mieten pro WE. Inputs aus Modul 4 (M6, P6, A8:K27, Y8:Y27 per-WE Spannenobergrenze). Inputs aus Modul 2 (T4 via RENO!O8). Rechnet: IST-Miete, NEU mit Avg-Cap (Y+M6)/2, SOLL = Y*F, JNKM, Renditen.</sheet>
```

- [ ] **Step 3: Z151 (VK_CF-Sheet-Beschreibung) anpassen**

Aktuell Z151:
```
<sheet name="VK_CF">Cashflow-Rueckrechnung aus Kaeufer-Sicht. DYNAMISCH ueber Slider (Zins, Tilgung, Steuer, Bewirtschaftung, AfA, Gebaeudeanteil, CF-Ziel). Referenziert MIETER und VERKAUFSMATRIX. Rechnet max. VK pro WE bei Ziel-Cashflow plus Sensitivitaet Zins plus Vergleich mit Markt-Ansatz.</sheet>
```

ersetzen durch:
```
<sheet name="VK_CF">Cashflow-Rueckrechnung aus Kaeufer-Sicht. DYNAMISCH ueber Slider (Zins, Tilgung, Steuer, Bewirtschaftung, AfA, Gebaeudeanteil, CF-Ziel). Referenziert MIETER!R (Nettokaltmiete pro WE). Spalten: Nettokaltmiete EUR/Mo, EUR/m², Verkaufspreis, Verkaufspreis EUR/m². Bewirtschaftung wird inline in der VK-Formel abgezogen, NICHT als sichtbare Reduktions-Spalte.</sheet>
```

- [ ] **Step 4: Z158 (was_excel_automatisch_rechnet) anpassen**

Aktuell Z158:
```
MIETER: Paragraph 559 Umlage (T5=T4*0,08), Umlage pro qm/Monat (T6), Kappungsgrenze pro WE (Spalte N mit 15-Monats-Frist via EDATE), SOLL-Miete pro WE (Spalte R), JNKM IST/NEU/SOLL, Renditen.
```

ersetzen durch:
```
MIETER: Paragraph 559 Umlage (T5=T4*0,08, T6=T5/12/F28 — derzeit nur informativ, nicht in R), Kappungsgrenze pro WE (Spalte N mit 15-Monats-Frist via EDATE, Cap = (Y+M6)/2), Kaltmiete SOLL pro WE (Spalte R = Y × F), JNKM IST/NEU/SOLL, Renditen.
```

- [ ] **Step 5: Z161 (VK_CF Berechnung) anpassen**

Aktuell Z161:
```
VK_CF: VK pro WE (Cashflow) = (Netto-Miete * (1-Steuer) - CF-Ziel) / k-Faktor, Sensitivitaet Zins, Delta Markt vs. Cashflow, Empfehlungs-Ampel.
```

ersetzen durch:
```
VK_CF: VK pro WE (Cashflow) = (Nettokaltmiete × (1-Bewirtschaftung) × (1-Steuer) - CF-Ziel) / k-Faktor. Spalte H = Nettokaltmiete EUR/m². Bewirtschaftung wirkt INLINE in der VK-Formel, NICHT als sichtbare Reduktions-Spalte.
```

- [ ] **Step 6: Z168 (was_module_liefern) anpassen**

Aktuell Z168 (Modul-4-Zeile):
```
Modul 4: MIETER M6 (Mietspiegel VOR Sanierung), MIETER P6 (Kappungsgrenze), MIETER A8:K27 (WE-Stamm-Tabelle), BESICHTIGUNG B33-B36.
```

ersetzen durch:
```
Modul 4: MIETER M6 (Mietspiegel-Mittelwert VOR Sanierung), MIETER P6 (Kappungsgrenze), MIETER A8:K27 (WE-Stamm-Tabelle), MIETER Y8:Y27 (per-WE Spannenobergrenze), BESICHTIGUNG B33-B36.
```

- [ ] **Step 7: Verifikation**

```bash
grep -n "Y8:Y27\|Y × F\|Y+M6" orchestrator.xml
```

Expected: ≥ 4 Treffer.

### Task 22: orchestrator.xml core_rules ergänzen

**Files:** `orchestrator.xml` (Z125-137)

- [ ] **Step 1: Neue Regel für Y-Output ergänzen**

Nach Z136 (`<rule>Aufteiler-Massnahmen 2026 NIE in M6 einrechnen (Option C). Kosten gehen in T4.</rule>`) einfügen:

```xml
    <rule>Modul 4 muss zusätzlich zu M6/P6/A8:K27 auch MIETER!Y8:Y27 (per-WE Spannenobergrenze) befuellen. Sonst bleibt R = 0 und VK_CF zeigt keine Werte.</rule>
```

- [ ] **Step 2: Verifikation**

```bash
grep -n "MIETER!Y8:Y27" orchestrator.xml
```

Expected: ≥ 1 Treffer in `<core_rules>`.

### Task 23: Excel speichern

**Files:** `Kalkulation_Aufteiler_mit_VK_CF.xlsx`

- [ ] **Step 1: Excel manuell schließen + speichern**

Wenn Excel die Datei offen hat: speichern und schließen, damit openpyxl-Edits + manuelle Edits konsistent gespeichert sind.

- [ ] **Step 2: File mtime prüfen**

```bash
stat -c '%y' "Kalkulation_Aufteiler_mit_VK_CF.xlsx"
```

Expected: Heutiges Datum.

### Task 24: GitHub Push der XML-Module

**Files:** GitHub Repo `andre-petrov-creator/meine-projekte`

- [ ] **Step 1: Status prüfen**

```bash
gh repo view andre-petrov-creator/meine-projekte --json defaultBranchRef
```

Expected: `defaultBranchRef.name = "main"`

- [ ] **Step 2: Lokales Klon-Verzeichnis lokalisieren** (oder neu klonen)

```bash
gh repo clone andre-petrov-creator/meine-projekte /tmp/meine-projekte
ls /tmp/meine-projekte/Aufteiler/
```

Expected: Bisherige Modul-XMLs sichtbar.

- [ ] **Step 3: Geänderte Dateien kopieren**

```bash
cp "c:/Users/andre/OneDrive - APPV Personalvermittlung/Immobilien/001_AQUISE/Objekte/0_Aufteiler Skill/modul_4_miete.xml" /tmp/meine-projekte/Aufteiler/
cp "c:/Users/andre/OneDrive - APPV Personalvermittlung/Immobilien/001_AQUISE/Objekte/0_Aufteiler Skill/orchestrator.xml" /tmp/meine-projekte/Aufteiler/
```

- [ ] **Step 4: Commit + Push**

```bash
cd /tmp/meine-projekte
git add Aufteiler/modul_4_miete.xml Aufteiler/orchestrator.xml
git commit -m "$(cat <<'EOF'
Aufteiler: per-WE Spannenobergrenze + VK_CF Nettokaltmiete-Anzeige

- Modul 4: neuer Excel-Output MIETER!Y8:Y27 (per-WE Spannenobergrenze)
- Orchestrator: R = Y*F, N nutzt Avg-Cap (Y+M6)/2, VK_CF zeigt Nettokaltmiete EUR/Mo + EUR/m²
- §559 Modernisierungsumlage T6 vorerst nicht in R addiert (siehe Modul 4 Hinweis)
EOF
)"
git push origin main
```

- [ ] **Step 5: Verifikation Live-URL**

```bash
curl -s "https://raw.githubusercontent.com/andre-petrov-creator/meine-projekte/main/Aufteiler/modul_4_miete.xml" | grep -c "Y8:Y27"
```

Expected: ≥ 2 (matches lokalen grep aus Task 2).

### Task 25: End-to-End Smoke-Test

**Files:** Live-System (Claude-Projekt mit orchestrator.xml als Projektanweisung)

- [ ] **Step 1: In Claude-Projekt: Modus „nur_miete" auslösen**

Eingabe: „Nur Miete für Prosperstr."

Erwartet: Orchestrator lädt aktualisierten Modul 4 von GitHub. Modul 4 berechnet per-WE Spannenobergrenze und gibt Y8:Y27-Werte explizit aus.

- [ ] **Step 2: Werte in Excel-Vorlage übertragen**

Manuell die per-WE-Spannenobergrenze-Werte in MIETER!Y8:Y27 eintragen (von Modul-4-Output abschreiben).

- [ ] **Step 3: VK_CF visuell prüfen**

Spalten G/H/I/J/K/L/M/N alle plausibel. N (Kontrolle) ≈ 0 €.

- [ ] **Step 4: Zwischen-Commit (lokales Plan-Repo)**

Wenn separater Git-Workflow für lokales Aufteiler-Skill-Verzeichnis gewünscht — sonst überspringen.

---

## Verifikations-Checkliste

Nach Plan-Abschluss alle Punkte ✓?

- [ ] `modul_4_miete.xml`: `Y8:Y27` in Excel-Transfer-Block, Workflow-Step 7 zeigt neue R/N-Logik, Option-C-Prinzip-Block überarbeitet
- [ ] `orchestrator.xml`: Z101/Z149/Z151/Z158/Z161/Z168 alle aktualisiert, neue core_rule für Y8:Y27 vorhanden
- [ ] Excel `MIETER`: Spalte Y mit Header und 5 Test-Werten, R = Y×F, T = R/F, N nutzt Avg-Cap
- [ ] Excel `VK_CF`: 4 neue Headers, H ist €/m², I-Formel mit Bewirt inline, M+N inline angepasst, H38 = AVERAGE
- [ ] VK-Werte WE 01-05 ≈ 159.917 / 161.330 / 164.189 / 165.571 / 149.058 € — Summe ≈ 800.065 €
- [ ] N-Kontroll-Spalte alle ≈ 0 €
- [ ] GitHub-Push erfolgreich, Live-URL liefert neue XMLs
- [ ] Smoke-Test mit Modus „nur_miete" funktioniert end-to-end

---

## Bekannte Limitierungen / spätere Arbeit

1. **§559 BGB Modernisierungsumlage T6 nicht in `R` addiert.** Für Prosperstr. T4=0, also kein Effekt. Bei zukünftigen Objekten mit Modernisierung: `R`-Formel zu `=IFERROR(Y*F + T6*F, "")` erweitern oder eigene Spalte für SOLL-inklusiv-Umlage einführen.

2. **MIETER!Y wird manuell befüllt** (Modul 4 schreibt nicht direkt — Modul 4 ist ein Chat-Modul, nicht ein API-Modul). Das Übertragen ist Hand-Arbeit. Falls Automation gewünscht: Modul 4 könnte einen Excel-Schnipsel ausgeben, den man kopieren+einfügen kann.

3. **N-Cap-Formel** verwendet `(Y+M6)/2` als arithmetischen Mittelwert. Wenn fachlich anders gewünscht (z. B. gewichtet oder MIN), muss die Formel separat angepasst werden.

4. **Keine Tests automatisiert.** Verifikation erfolgt manuell durch Excel-Werte-Vergleich. Künftig könnte ein Python-Skript die erwarteten Werte berechnen und mit Excel-Outputs vergleichen.
