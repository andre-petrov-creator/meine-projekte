# Architektur — Aufteiler

Big Picture des MFH-Aufteiler-Workflow-Systems. Detail pro Komponente in den jeweiligen `docs/<komponente>.md`-Files.

============================================================

## System-Übersicht

```
┌──────────────────────────────────────────────────────────────────┐
│  Web-Claude (claude.ai Projekt "Aufteiler")                      │
│  Projektanweisung = orchestrator.xml                             │
└─────────────────────────┬────────────────────────────────────────┘
                          │
                          │ web_fetch (raw.githubusercontent.com)
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│  GitHub: meine-projekte/Immobilien/Aufteiler/                    │
│                                                                  │
│  ├─ orchestrator.xml          (Routing, Sequenzierung)           │
│  ├─ modul_0_quickcheck.xml    (ETW-Konsens, Gap-Schwelle)        │
│  ├─ modul_1_objektbasis.xml   (WE-Liste, BRW, Gebäudeanteil)     │
│  ├─ modul_2_massnahmen.xml    (Sanierung, Energetik, EnEV)       │
│  ├─ modul_3_rnd_afa.xml       (Restnutzungsdauer, AfA-Korridor)  │
│  ├─ modul_4_miete.xml         (Mietspiegel, §558/§559 BGB)       │
│  ├─ modul_5_verdict.xml       (PDF + Excel-Notizen, on-demand)   │
│  └─ skill_pdf_export.md       (Layout-Regeln R1-R13 für M5)      │
└─────────────────────────┬────────────────────────────────────────┘
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
┌──────────────────┐ ┌──────────┐ ┌──────────────────────┐
│  Notion-DBs      │ │  Excel   │ │  PDF (Modul 5 only)  │
│  (read-only)     │ │  Template│ │  reportlab+matplotlib│
│                  │ │  pro Obj.│ │  → Aufteiler_<...>.pdf│
│  Mietspiegel NRW │ │  kopiert │ └──────────────────────┘
│  ImmoWertV       │ └──────────┘
│  EnEV NRW        │
│  Stadt-Marktdat. │
└──────────────────┘
```

============================================================

## Komponenten-Verantwortlichkeiten

### Orchestrator (`orchestrator.xml`)

- **Modus erkennen** aus User-Input (`vollanalyse`, `nur_quickcheck`, `nur_export` etc.)
- **Modul-Sequenz routen** je nach Modus
- **Module via web_fetch laden** (kein Inline-Code)
- **Freigaben einholen** zwischen Modulen (`go`/`weiter`/`ja`/`ok`)
- **Excel-Handoff orchestrieren** (welches Modul liefert in welche Zelle)
- **Rechnet selbst NICHTS**

### Module (`modul_*.xml`)

Jedes Modul ist autark und liefert:
- Strukturierten Chat-Output (Tabellen, Empfehlungen)
- Excel-Transfer-Block (Werte für definierte Zellen)
- Logging-Hinweise für Spätere (Annahmen, Quellen)

Module rufen **einander nicht direkt auf**. Datenfluss zwischen Modulen läuft über Chat-Kontext + Excel.

### Skills (`skill_*.md`)

Form-/Layout-Regeln + technische Bausteine. Beispiel `skill_pdf_export.md`: Spaltenbreiten, Word-Wrap, Farbpalette, reportlab-Code-Snippets. Wird vom konsumierenden Modul per `web_fetch` vor der Ausführung geladen (Pflicht).

### Excel-Template (`template/Kalkulation_Aufteiler_mit_VK_CF.xlsx`)

Die eigentliche Rechen-Maschine. Module liefern nur Inputs in definierte Zellen — alle Multiplikationen, Summen, IF-Logik passieren in den Excel-Formeln. Sheet-Namen und Zell-Adressen sind Vertrag (siehe `excel_handoff.md` sobald angelegt).

### Notion-DBs (read-only)

Nachschlagewerke für Mietspiegel, Restnutzungsdauer-Regelwerk, Energetik-Maßnahmen, Stadt-Marktdaten. IDs in `../README.md`. Werden modulintern referenziert, niemals beschrieben.

============================================================

## Vollanalyse-Sequenz

```
User-Trigger ("Vollanalyse <Objekt>")
       │
       ▼
[Orchestrator erkennt Modus]
       │
       ▼
Modul 0 ──► (Freigabe?) ──► Modul 1 ──► (Freigabe?) ──► Modul 2
                                                            │
                                                       (Freigabe?)
                                                            │
       ┌─────────── Modul 4 ◄── (Freigabe?) ◄── Modul 3 ◄───┘
       │
  (Freigabe?)
       │
       ▼
[Orchestrator fragt: "PDF-Export gewünscht?"]
       │
       ├── ja ──► Modul 5 (lädt skill_pdf_export.md, erzeugt PDF)
       └── nein ─► Sequenz-Ende
```

**Modul 5 ist NIE Teil der automatischen Sequenz** — nur explizit auf Anfrage oder nach finaler Bestätigung am Sequenz-Ende.

============================================================

## Daten-Verträge (Schnittstellen-Übersicht)

| Modul | Liest aus | Schreibt nach (Excel) | Referenziert |
|-------|-----------|------------------------|--------------|
| M0 | User-Inputs | Quick-Check-Block | Stadt-Marktdaten (Notion) |
| M1 | M0-Output | Objektbasis-Block, `MIETER`-Stammdaten | BORIS.NRW (User-manuell) |
| M2 | M1-Output | Maßnahmen-Block, EnEV-Bewertung | EnEV NRW (Notion) |
| M3 | M1+M2-Output | RND, AfA-Korridor | ImmoWertV 2021 Anlage 2 (Notion) |
| M4 | M1-Output, Mietverträge | `MIETER!Y8:Y27`, `VK_CF`, `VERKAUFSMATRIX` | Mietspiegel NRW (Notion) |
| M5 | M0-M4 Chat-Outputs + befüllte Excel | Notizen/Comments in Excel + neue PDF-Datei | `skill_pdf_export.md` (Pflicht) |

Detail-Verträge (welche Zelle, welcher Typ) gehören in die jeweilige `docs/modul_*.md` und in `docs/excel_handoff.md`.

============================================================

## Versionierungs-Strategie auf System-Ebene

- **Module versionieren unabhängig.** M3 v2.1 koexistiert mit M4 v2.2. Orchestrator ist agnostisch — er lädt `file=...` ohne Version-Pin.
- **Orchestrator versioniert sich selbst** und trackt im Header-Comment, welche Modul-Versions-Erwartungen drinstecken (siehe `orchestrator.xml` v2.4 als Vorlage).
- **Breaking Change in einem Modul** = Major-Bump in dem Modul + Hinweis im Orchestrator-Header, ggf. Orchestrator-Bump wenn Sequenz-Logik betroffen.
- **Skill-Bump** muss im konsumierenden Modul erwähnt werden (Modul referenziert Skill ohne Version, aber Skill-Erwartung steht im Modul-Header).
