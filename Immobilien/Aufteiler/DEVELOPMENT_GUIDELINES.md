# Development Guidelines — Aufteiler

Verbindliche Konventionen für alle Änderungen an Modulen, Skills, Plans und Doku.

============================================================

## 1. Datei-Typen und Verantwortlichkeiten

| Typ | Format | Inhalt | Beispiel |
|-----|--------|--------|----------|
| **Orchestrator** | XML | Routing, Modus-Erkennung, Sequenz-Logik | `orchestrator.xml` |
| **Modul** | XML | Workflow + Berechnungs-Logik einer Domäne (Inhalt) | `modul_3_rnd_afa.xml` |
| **Skill** | Markdown | Form-/Layout-Regeln, technische Bausteine (z.B. reportlab-Code) | `skill_pdf_export.md` |
| **Plan** | Markdown | Konkrete Überarbeitungs-Plan einer Iteration | `plans/2026-04-26-modul4-v2.0-integriert.md` |
| **Doc** | Markdown | Aktueller Stand einer Komponente (lebendig) | `docs/modul_4_miete.md` |
| **Template (Excel)** | xlsx | Excel-Maschine für Berechnungen | `template/Kalkulation_Aufteiler_mit_VK_CF.xlsx` |

**Modul vs. Skill:** Module beschreiben WAS gerechnet/getan wird. Skills beschreiben WIE es technisch korrekt aussehen muss. Niemals Form-Regeln in Modulen, niemals Berechnungs-Logik in Skills.

============================================================

## 2. XML-Modul-Format

### 2.1 Pflicht-Struktur

```xml
<?xml version="1.0" encoding="UTF-8"?>
<modul name="<Name>" id="<N>" version="<X.Y>" language="de">

  <!--
    MODUL <N> - <NAME>

    Zweck:
    [Kurz: was macht das Modul]

    Trigger:
    [Wann lädt der Orchestrator dieses Modul]

    INPUT-PFLICHT:
    [Welche Vor-Module müssen gelaufen sein, welche Daten erwartet]

    Outputs:
    [Excel-Zellen, Chat-Texte, Dateien]

    AENDERUNGEN v<X.Y> vs v<X.Y-1>:
    - [Diff-Punkt 1]
    - [Diff-Punkt 2]
  -->

  <identity>
    <role>...</role>
    <task>...</task>
    <scope>INKLUSIVE: ... AUSGESCHLOSSEN: ...</scope>
  </identity>

  <!-- Modul-spezifische Sektionen -->
</modul>
```

### 2.2 Versionierung (verbindlich)

- **Patch (vX.Y → vX.Y+1):** Bug-Fix, Tippfehler, klarere Formulierung — keine Verhaltensänderung
- **Minor (vX.Y → vX.Y+1, neuer Y):** neue Sub-Sektion, neue Excel-Zelle, neue Berechnung — abwärtskompatibel
- **Major (vX.Y → vX+1.0):** Breaking Change im Schnittstellen-Verhalten (z.B. Output-Format ändert sich, Excel-Zellen verschieben sich)
- **Bei jeder Änderung:** Header-Comment um `AENDERUNGEN vX.Y vs vX.Y-1`-Block ergänzen (alte Blöcke nicht löschen — Diff-Verlauf bleibt sichtbar)
- **Orchestrator** trackt im Header zusätzlich Versions-Inkompatibilitäten zu Modulen (siehe `orchestrator.xml` v2.4 Header als Referenz)

### 2.3 Sprach-Konvention im XML

- Element-Namen englisch wenn etabliert (`identity`, `task`, `scope`, `module_registry`), deutsch wenn fachlich (`farb_schema`, `mietspiegel_lookup`)
- Element-Inhalte: Deutsch
- Kommentare: Deutsch ohne Umlaute in maschinenrelevanten Stellen (Header-Diffs), Umlaute in normalem Fließtext erlaubt

============================================================

## 3. Skill-Format (Markdown)

### 3.1 Pflicht-Frontmatter

```markdown
---
name: <skill-id-kebab-case>
description: <ein Satz: Wann nutzen, was liefert er, ist er Pflicht?>
type: skill
language: de
version: <X.Y>
---
```

### 3.2 Struktur

- **Section 1: Pflicht-Regeln** (R1, R2, R3, ... — nummeriert, einzeln testbar)
- **Section 2: Code-Bausteine** (kopierbarer Code, kein Pseudo-Code)
- **Section 3: Anti-Patterns / häufige Fehler**
- **Section 4: Versions-Block** (Änderungen seit letzter Version)

### 3.3 Regel-Schreibweise

Jede Regel hat: **Titel mit ID**, **kurzes Was**, **❌ Falsch / ✅ Richtig**-Beispiel. Beispiel siehe `skill_pdf_export.md` R1.

============================================================

## 4. Excel-Handoff-Konventionen

- **Vorlage** liegt unter `template/Kalkulation_Aufteiler_mit_VK_CF.xlsx`. Original NIE überschreiben — pro Objekt als `Kalkulation_<Strassenkurz>.xlsx` kopieren.
- **Sheet-Namen** sind Vertrag: `MIETER`, `VK_CF`, `VERKAUFSMATRIX` u.a. — nicht umbenennen, nicht reihenfolge-ändern.
- **Zell-Adressen** in Modulen sind Vertrag: wenn Modul X auf `MIETER!Y8:Y27` schreibt, darf Modul Y dort nicht überschreiben.
- **Excel rechnet alles, was via Formel geht** (Multiplikationen, IF, SUMIFS). Module liefern nur die Inputs (Werte), keine Formel-Outputs.
- **Bewirtschaftung wirkt INLINE** in VK-Formel, nicht als sichtbare Spalte (Prinzip seit v2.2).
- **Empty-Row-Handling:** alle VK_CF + VERKAUFSMATRIX Formeln mit `IF(ISNUMBER(MIETER!F{quelle}),...,"")` wrappen.
- **Bei Strukturänderung am Template:** alte Version unter `template/Backup/Kalkulation_<vN>.xlsx` archivieren, neue Version mit Datum im Commit-Message.

============================================================

## 5. GitHub / Pfad-Konventionen

- **Repo:** `andre-petrov-creator/meine-projekte`
- **Subfolder:** `Immobilien/Aufteiler/` (case-sensitive — Großbuchstaben halten!)
- **Raw-URL-Pattern:** `https://raw.githubusercontent.com/andre-petrov-creator/meine-projekte/main/Immobilien/Aufteiler/<file>`
- **Browse-URL:** `https://github.com/andre-petrov-creator/meine-projekte/tree/main/Immobilien/Aufteiler`
- **Wichtig:** Orchestrator und alle Module verweisen aktuell auf `main/Aufteiler/` (ohne `Immobilien/`-Präfix). Bei jedem Pfad-Ändern: ALLE `module_registry`/`skill_registry`-Einträge im Orchestrator gleichzeitig aktualisieren.

============================================================

## 6. Plans und Doku

### 6.1 Plans-Ordner (`plans/`)

- **Zweck:** Eine Iteration = ein Plan. Plans sind historische Artefakte (was wurde wann warum geplant), keine lebende Doku.
- **Naming:** `YYYY-MM-DD-<modul-id>-<kurz-thema>.md` — Datum = Plan-Erstellung
- **Vorlage:** `docs/UEBERARBEITUNGS_TEMPLATE.md`
- **Status am Plan-Ende** pflegen: `OFFEN` / `IN UMSETZUNG` / `ERLEDIGT YYYY-MM-DD` / `VERWORFEN — Grund`

### 6.2 Docs-Ordner (`docs/`)

- **Zweck:** Lebende Dokumentation des aktuellen Stands. Wird bei jeder Änderung mitgepflegt.
- **Eine Datei pro Komponente** (Modul, Skill, Excel-Sheet, externe Quelle)
- **Vorlage:** `docs/_TEMPLATE_KOMPONENTE.md`
- **Pflicht-Sektionen:** Zweck · Files · Datenfluss · Schnittstellen · Bekannte Limitierungen
- **Index** in `docs/README.md` immer aktuell halten

============================================================

## 7. Git-Workflow

- **Branch:** direkt auf `main` (eigenes Repo, kein PR-Zwang)
- **Commit-Message-Pattern:**
  - `Aufteiler M<N> v<X.Y>: <kurz was>` (Modul-Änderung)
  - `Aufteiler Skill <name> v<X.Y>: <kurz was>` (Skill-Änderung)
  - `Aufteiler Plan: <name>` (neuer Plan)
  - `Aufteiler Docs: <komponente>` (Doku-Update)
- **Push direkt nach jedem Commit** — sonst kein `web_fetch`-Effekt produktiv
- **Niemals** `--force`, `--no-verify`, `reset --hard` ohne explizite User-Anweisung

============================================================

## 8. Externe Dependencies / Datenquellen

- **Notion-DBs/Pages** (siehe `README.md` für IDs): nur lesend abrufen, nie schreiben aus Modul-Workflow
- **BORIS.NRW** (Bodenrichtwerte): User ruft manuell ab, gibt Wert ins Chat
- **Mietspiegel:** ausschließlich aus Notion-DB Mietspiegel NRW (keine externen Mietspiegel-APIs)
- **Neue externe Dependency** = explizite User-Freigabe vor Aufnahme

============================================================

## 9. Anti-Patterns (verbindlich vermeiden)

| Anti-Pattern | Warum verboten | Stattdessen |
|--------------|----------------|-------------|
| Form-Regel in Modul-XML | Vermischt Inhalt + Form, schwer zu warten | Skill anlegen oder bestehenden erweitern |
| Modul ruft anderes Modul direkt auf | Verletzt Modul-Autarkie, Orchestrator verliert Kontrolle | Orchestrator sequenziert |
| Excel-Werte aus Modul überschreiben | Macht Excel-Maschine intransparent | Modul liefert Input in definierte Zelle, Excel rechnet |
| Modul 5 in Vollanalyse-Sequenz | User wollte Trennung Analyse/Export | Nur auf explizite Anfrage |
| Version ohne Header-Diff bumpen | Verlauf nicht nachvollziehbar | `AENDERUNGEN`-Block ergänzen, alte Blöcke behalten |
| Pfad mit kleinem `aufteiler/` | Case-sensitive 404 auf GitHub raw | Immer `Aufteiler/` mit großem A |
| Emoji im PDF | reportlab Font-Probleme + R5 verbietet es | Wort statt Emoji |
| Wohnungs- und Garagen-Werte vermischen | Verletzt Asset-Trennung, falsche Cashflows | Wohnungen → Cashflow-VK; Garagen/SP → `VERKAUFSMATRIX!V` |
