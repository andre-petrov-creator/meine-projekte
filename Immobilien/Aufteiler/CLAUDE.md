# Projekt: Aufteiler-Workflow (MFH-Analyse)

Modulares XML-Workflow-System für die Aufteiler-Analyse von Mehrfamilienhäusern (NRW/Ruhrgebiet). Wird von **Web-Claude** (claude.ai) als Projektanweisung geladen; Module + Skills werden via `web_fetch` aus diesem GitHub-Repo gezogen.

Dieses Repo ist die **einzige Quelle der Wahrheit** für Module, Skills und Excel-Template. Änderungen hier wirken beim nächsten `web_fetch` sofort produktiv.

============================================================

## Vor jeder Aufgabe (Pflicht-Reads)

1. **`DEVELOPMENT_GUIDELINES.md`** — Konventionen, Format-Regeln, Versionierung
2. **`docs/ARCHITEKTUR.md`** — Big Picture: Orchestrator → Module → Skills → Excel → Notion
3. **Relevante `docs/*.md`** zum betroffenen Modul/Skill (siehe `docs/README.md` als Index)
4. **Relevante `plans/*.md`** der letzten Überarbeitung des Moduls (Kontext, was zuletzt geändert wurde und warum)

## Nach jeder Aufgabe (Pflicht-Writes)

1. **Version-Bump** in der betroffenen Datei (Header-Attribut + Änderungsblock im Top-Comment)
2. **`docs/<komponente>.md`** anlegen oder aktualisieren (Zweck, Files, Datenfluss, Schnittstellen, Limitierungen)
3. **Bei strukturellen Änderungen:** `docs/ARCHITEKTUR.md` und `README.md` (Repo-Root) nachziehen
4. **Größere Überarbeitungen** als neuer `plans/YYYY-MM-DD-<modul>-<thema>.md` ablegen (Vorlage: `docs/UEBERARBEITUNGS_TEMPLATE.md`)
5. **Commit + Push auf `main`** (Repo `meine-projekte`, Subfolder `Immobilien/Aufteiler/`) — die XML-Module sind ohne Push nicht über `web_fetch` verfügbar

============================================================

## Stack

- **Workflow-Format:** XML (Module) + Markdown (Skills, Doku)
- **Ausführungs-Runtime:** Web-Claude (claude.ai) — Module werden via `web_fetch` geladen, nicht hier ausgeführt
- **Daten-Backend:** Notion-Datenbanken (Mietspiegel NRW, ImmoWertV, EnEV NRW, Stadt-Marktdaten) — IDs in `README.md`
- **Excel-Maschine:** `template/Kalkulation_Aufteiler_mit_VK_CF.xlsx` (Binary, pro Objekt kopieren)
- **PDF-Generator:** reportlab + matplotlib (Modul 5, gesteuert durch `skill_pdf_export.md`)
- **Hosting:** GitHub-Repo `andre-petrov-creator/meine-projekte`, Pfad `Immobilien/Aufteiler/` (case-sensitive)

## Architektur-Prinzipien

- **Module = Inhalt, Skills = Form.** Module beschreiben Workflow und Berechnungs-Logik; Skills regeln Layout, Schreibweise, technische Details. Niemals vermischen.
- **Modul-Autarkie.** Jedes Modul liefert seinen eigenen Excel-Transfer-Block. Module rufen einander nicht auf — der Orchestrator sequenziert.
- **Excel rechnet, Module liefern Inputs.** Was Excel via Formel selbst kann, gehört nicht in ein Modul. Module produzieren Werte für definierte Zellen.
- **Asset-Trennung.** Wohnungen, Garagen, Stellplätze NIE in Berechnungen vermischen. Wohnungs-Kalt → Cashflow-VK; Garagen/SP → Markt-Preis pro WE in `VERKAUFSMATRIX!V`.
- **Keine Auto-Exports.** Modul 5 (PDF) läuft nur auf explizite User-Anfrage, nie als Teil der Vollanalyse-Sequenz.
- **Freigabe-Pflicht zwischen Modulen.** Orchestrator wartet auf `go`/`weiter`/`ja`/`ok`, bevor das nächste Modul geladen wird.
- **Versionierung sichtbar im Header.** Jede inhaltliche Änderung = Version-Bump + Änderungsblock im Top-Comment (Diff-fähig auch ohne Git-Log).

## Konventionen

- **Sprache in Modul-Texten:** Deutsch
- **Sprache in Code/Identifiern (XML-Tags, Excel-Zellen, Python):** Englisch wo etabliert, Deutsch wo fachlich
- **Datei-Naming:** `modul_<id>_<thema>.xml`, `skill_<thema>.md`, Plans `plans/YYYY-MM-DD-<modul>-<thema>.md`
- **Pfad-Case:** `Aufteiler/` immer mit großem A in URLs (case-sensitive auf GitHub raw)
- **Keine Emojis** in PDF-Output (siehe `skill_pdf_export.md` R5)
- **Header-Comment-Block:** jede XML/MD-Datei beginnt mit Zweck, Trigger/Scope, Änderungsblock (vN.x vs vN.x-1)

## Skill-Referenzen

Beim Arbeiten an folgenden Themen die zugehörigen Skills laden:

| Aufgabe | Skill |
|---------|-------|
| PDF-Layout / Modul 5 | `skill_pdf_export.md` (Pflicht vor jedem PDF-Build) |
| Neue Modul-Überarbeitung planen | `superpowers:writing-plans` + `docs/UEBERARBEITUNGS_TEMPLATE.md` |
| Plan ausführen | `superpowers:executing-plans` |
| Bug in Modul-Output | `superpowers:systematic-debugging` |

============================================================

## Workflow für künftige Überarbeitungen

1. **Sparring** im Web-Claude (Aufteiler-Projekt). Output: ein konkreter Überarbeitungs-Plan.
2. **Plan ablegen** als `plans/YYYY-MM-DD-modulN-<thema>.md` (Vorlage: `docs/UEBERARBEITUNGS_TEMPLATE.md`).
3. **Implementierung** Schritt für Schritt — pro Schritt: XML/MD ändern, Version-Bump, `docs/`-File updaten.
4. **Commit + Push** (sonst kein `web_fetch`-Effekt produktiv).
5. **Test** im Web-Claude mit echtem Objekt-Case — Modul-Output gegen Akzeptanzkriterium aus dem Plan prüfen.
6. **Plan abhaken** (Status-Block am Ende des Plan-Files setzen).
