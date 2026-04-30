# [Komponenten-Name] — `[datei.xml|md]`

> **Vorlage.** Beim Anlegen einer neuen Komponenten-Doku diese Datei kopieren als `docs/<komponente>.md`, alle `[…]`-Platzhalter ersetzen, alle Hinweis-Zeilen (Zitat-Blöcke wie diese) löschen.

> **Pflicht-Sektionen:** alle 5 unten. Reihenfolge nicht ändern. Sektionen die nicht zutreffen explizit als „n/a — \[Grund]" markieren, nicht weglassen.

============================================================

## Zweck

> 2-3 Sätze: was tut die Komponente, in welchem Modus läuft sie, wann wird sie geladen.

[…]

============================================================

## Files

> Alle zur Komponente gehörenden Dateien. Auch indirekte (z.B. Skill der von einem Modul aufgerufen wird, oder Excel-Sheet das das Modul beschreibt).

- **Hauptdatei:** `[pfad]`
- **Abhängige Skills:** `[pfad]` (wenn vorhanden)
- **Excel-Sheets:** `[Sheet-Name]` (wenn vorhanden)
- **Notion-Quellen:** `[DB/Page-Name + ID]` (wenn vorhanden)

============================================================

## Datenfluss

> Inputs → Verarbeitung → Outputs. Ein Diagramm-Block (ASCII) ist meist klarer als Fließtext.

```
[Input-Quelle] ──► [was passiert] ──► [Output-Ziel]
```

**Inputs:**
- […]

**Verarbeitung (kurz, kein Code-Dump):**
- […]

**Outputs:**
- […]

============================================================

## Schnittstellen

> Konkrete Verträge zu anderen Komponenten. Wer konsumiert das? Wo werden Werte geschrieben/gelesen?

| Schnittstelle | Typ | Adresse / Detail |
|---------------|-----|------------------|
| […] | Excel-Cell | `[Sheet]![Zelle]` |
| […] | Chat-Output | `[Format/Tabelle]` |
| […] | Notion-Read | `[DB-ID]` |
| […] | Skill-Call | `[skill_xyz.md]` |

============================================================

## Bekannte Limitierungen

> Edge-Cases, TODOs, technische Schulden, akzeptierte Trade-Offs. Was ein neuer Bearbeiter wissen muss, bevor er etwas „verbessert".

- **[Limitierung 1]** — [warum noch nicht gelöst, was wäre die Lösung]
- **[Edge-Case 1]** — [wann tritt er auf, wie wird aktuell damit umgegangen]
- **[Bewusste Vereinfachung]** — [was wurde absichtlich nicht modelliert, warum]

============================================================

## Versions-Historie

> Auf einen Blick: was hat sich wann geändert. Detail steht im XML/MD-Header der Komponente — hier nur Stichworte.

| Version | Datum | Änderung (Stichwort) | Plan-Ref |
|---------|-------|----------------------|----------|
| vX.Y | YYYY-MM-DD | […] | `plans/YYYY-MM-DD-…md` |
