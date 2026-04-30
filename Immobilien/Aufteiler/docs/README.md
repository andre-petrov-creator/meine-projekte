# Docs — Aufteiler

Lebende Dokumentation des aktuellen Stands aller Komponenten. Wird bei jeder Modul-/Skill-Änderung mitgepflegt (Pflicht aus `CLAUDE.md`).

Pläne und historische Iterationen liegen in `../plans/`, **nicht** hier.

============================================================

## Wegweiser

| Was du suchst | Datei |
|---------------|-------|
| Big Picture (Orchestrator + Module + Skills + Excel + Notion) | [`ARCHITEKTUR.md`](ARCHITEKTUR.md) |
| Vorlage für Modul-/Komponenten-Doku | [`_TEMPLATE_KOMPONENTE.md`](_TEMPLATE_KOMPONENTE.md) |
| Vorlage für Überarbeitungs-Plan (für `../plans/`) | [`UEBERARBEITUNGS_TEMPLATE.md`](UEBERARBEITUNGS_TEMPLATE.md) |

============================================================

## Komponenten-Index

Status-Legende: ✓ = dokumentiert · ○ = Skeleton · — = noch nicht angelegt

| Komponente | Datei | Status |
|------------|-------|--------|
| Orchestrator | `orchestrator.md` | — |
| Modul 0 — Quick-Check | `modul_0_quickcheck.md` | — |
| Modul 1 — Objektbasis | `modul_1_objektbasis.md` | — |
| Modul 2 — Maßnahmen | `modul_2_massnahmen.md` | — |
| Modul 3 — RND + AfA | `modul_3_rnd_afa.md` | — |
| Modul 4 — Mietsituation | `modul_4_miete.md` | — |
| Modul 5 — Verdict-Export | `modul_5_verdict.md` | — |
| Skill PDF-Export | `skill_pdf_export.md` | — |
| Excel-Template (Sheets, Zellen, Formeln) | `excel_handoff.md` | — |
| Notion-Datenquellen | `notion_quellen.md` | — |

**Vorgehen:** Bei der nächsten Überarbeitung einer Komponente die zugehörige `docs/`-Datei aus dem Template ableiten und Status auf ✓ setzen. Nicht alles auf einmal — organisch wachsen lassen, damit Doku immer dem realen Zustand entspricht und nicht hinterherläuft.

============================================================

## Doku-Pflicht-Sektionen (aus Template)

Jede Komponenten-Doku enthält:

1. **Zweck** — was tut die Komponente, in 2-3 Sätzen
2. **Files** — welche Dateien gehören dazu
3. **Datenfluss** — Inputs → Verarbeitung → Outputs
4. **Schnittstellen** — Excel-Zellen, Chat-Outputs, Notion-Reads, Skill-Verweise
5. **Bekannte Limitierungen** — Edge-Cases, TODOs, technische Schulden
