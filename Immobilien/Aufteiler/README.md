# Aufteiler-Workflow (MFH-Aufteiler-Analyse)

Dieser Ordner enthält das modulare XML-Workflow-System für die MFH-Aufteiler-Analyse, plus Skills (Form-Regeln). Alles ist webfetchbar via raw.githubusercontent.com.

## Einstieg für Überarbeitungen

Vor jeder Änderung an Modulen, Skills oder dem Excel-Template lesen:

1. [`CLAUDE.md`](CLAUDE.md) — Steuerungsdatei: Pflicht-Reads vor / Pflicht-Writes nach jeder Aufgabe
2. [`DEVELOPMENT_GUIDELINES.md`](DEVELOPMENT_GUIDELINES.md) — Konventionen, Format-Regeln, Versionierung
3. [`docs/ARCHITEKTUR.md`](docs/ARCHITEKTUR.md) — Big Picture
4. [`docs/README.md`](docs/README.md) — Index der Komponenten-Doku
5. [`plans/`](plans/) — letzte Überarbeitungs-Plans (Vorlage: [`docs/UEBERARBEITUNGS_TEMPLATE.md`](docs/UEBERARBEITUNGS_TEMPLATE.md))

## Module (Inhalt / Berechnungen)

| ID | Datei | Zweck |
|----|-------|-------|
| – | [`orchestrator.xml`](orchestrator.xml) | Routing, Modus-Erkennung, Modul-Sequenzierung, Excel-Handoff-Logik |
| 0 | [`modul_0_quickcheck.xml`](modul_0_quickcheck.xml) | Quick-Check: ETW-Konsens vs. Angebotspreis, Gap-Schwelle 17,5 % |
| 1 | [`modul_1_objektbasis.xml`](modul_1_objektbasis.xml) | Objektbasis: WE-Liste, BRW, Gebäudeanteil |
| 2 | [`modul_2_massnahmen.xml`](modul_2_massnahmen.xml) | Sanierungskatalog, Energetik, EnEV-Massnahmenwirkung |
| 3 | [`modul_3_rnd_afa.xml`](modul_3_rnd_afa.xml) | Restnutzungsdauer + AfA-Korridor (ImmoWertV 2021 Anlage 2) |
| 4 | [`modul_4_miete.xml`](modul_4_miete.xml) | Mietspiegel je WE, §558 BGB Heberecht, §559 BGB Umlage, Mietsubvention |
| 5 | [`modul_5_verdict.xml`](modul_5_verdict.xml) | PDF-Export + Excel-Notizen (NIE automatisch — nur auf Anfrage) |

## Skills (Form / Layout-Regeln)

| Skill | Datei | Genutzt von |
|-------|-------|-------------|
| Aufteiler PDF-Export Design | [`skill_pdf_export.md`](skill_pdf_export.md) | Modul 5 (PFLICHT vor jedem PDF-Build) |

Skills sind technische Regeln für Form/Layout. Module bleiben für Inhalt zuständig. Skill und Modul werden beide per `web_fetch` geladen.

## Vollanalyse-Sequenz

`0 → 1 → 2 → 3 → 4` (Modul 5 nur auf explizite User-Anfrage am Ende.)

Zwischen jedem Modul wartet der Orchestrator auf Freigabe (`go`, `weiter`, `ja`, `ok`).

## Daten-Quellen (Notion)

- Mietspiegel NRW (DS): `8b000923-d5ee-45a4-8f6a-e7f3bf81f20e`
- ImmoWertV 2021 RND-Regelwerk (Page): `3360ae59-38e4-81a6-a632-f0715b46ead4`
- EnEV NRW (DS): `50c75486-37ec-45fa-a243-d0a486206f20`
- Preisdatenbank Stadt-Marktdaten (Page): `3310ae59-38e4-81f1-ad36-e8bd809d437a`

## Excel-Handoff

**Vorlage (Master):** [`template/Kalkulation_Aufteiler_mit_VK_CF.xlsx`](template/Kalkulation_Aufteiler_mit_VK_CF.xlsx)

Direkt-Download (Binary, IMMER von GitHub ziehen):
```
curl -o Kalkulation_<Strassenkurz>.xlsx https://raw.githubusercontent.com/andre-petrov-creator/meine-projekte/main/Immobilien/Aufteiler/template/Kalkulation_Aufteiler_mit_VK_CF.xlsx
```

Pro Objekt-Ordner kopieren als `Kalkulation_<Strassenkurz>.xlsx`.
