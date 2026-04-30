# Überarbeitungs-Plan: [Modul/Skill] [Thema]

> **Vorlage.** Beim Anlegen eines neuen Plans diese Datei kopieren als `plans/YYYY-MM-DD-<modul-id>-<thema>.md`, alle `[…]`-Platzhalter und Zitat-Hinweise (wie diesen) ersetzen/löschen.

> **Pattern:** Ein Plan = eine Iteration = ein klares Ziel mit prüfbarem Akzeptanzkriterium. Wenn ein Plan zu groß wird, splitten in mehrere kleinere Plans.

---

## Meta

| Feld | Wert |
|------|------|
| **Plan-Datum** | YYYY-MM-DD |
| **Komponente** | `modul_X_thema.xml` (oder Skill / Orchestrator) |
| **Aktuelle Version** | vX.Y |
| **Ziel-Version** | vX.Y+1 (Patch / Minor / Major) |
| **Ausgelöst durch** | [User-Beobachtung / Bug / neues Feature / externe Änderung] |
| **Status** | OFFEN |

============================================================

## 1. Ausgangslage

> Was ist aktuell der Stand? Welches Verhalten existiert? Welcher konkrete Schmerz oder Wunsch löst die Überarbeitung aus? Mit Zitat aus User-Chat oder konkretem Objekt-Case.

[…]

============================================================

## 2. Ziel

> EIN Satz. Was soll am Ende der Überarbeitung anders sein?

[…]

============================================================

## 3. Scope

### IN-Scope (wird in diesem Plan angefasst)
- […]

### OUT-of-Scope (bewusst NICHT in diesem Plan)
- [… — mit kurzem Grund, falls es nahe liegen würde]

============================================================

## 4. Architektur-Entscheidungen

> Welche Design-Wahl wird getroffen, welche Alternativen wurden verworfen, warum?

| Entscheidung | Alternative(n) | Gewählt weil |
|--------------|----------------|--------------|
| […] | […] | […] |

============================================================

## 5. Schritte

> Pro Schritt: kleine, in sich abgeschlossene Änderung. Jeder Schritt soll für sich getestet werden können.

### Schritt 1: [Titel]
- **Datei(en):** [Liste]
- **Änderung:** [Was konkret]
- **Akzeptanzkriterium:** [Wie prüfbar]

### Schritt 2: [Titel]
- **Datei(en):** […]
- **Änderung:** […]
- **Akzeptanzkriterium:** […]

### Schritt N: Doku + Version-Bump
- **Datei(en):** Komponenten-XML/MD-Header, `docs/<komponente>.md`, ggf. `docs/ARCHITEKTUR.md`, `README.md`
- **Änderung:** Version-Bump auf vX.Y+1, `AENDERUNGEN`-Block im Header, Doku-Datei nach `_TEMPLATE_KOMPONENTE.md` aktualisieren
- **Akzeptanzkriterium:** `docs/README.md`-Index zeigt neuen Status; Komponenten-Doku stimmt mit XML/MD überein

============================================================

## 6. Rollback-Plan

> Was tun, wenn nach Push festgestellt wird, dass die neue Version Probleme macht?

- **Quick-Rollback:** Git-Revert des Commits → Push → `web_fetch` zieht alte Version
- **Hot-Fix-Strategie:** [wenn Revert zu grob — was wäre minimaler Fix-Pfad]
- **Daten-Risiko:** [werden Excel-Zellen umgemappt? Bricht das alte Excel-Files? → Migrations-Hinweis hier]

============================================================

## 7. Test-Cases

> Konkrete Objekt-Cases (echte Adressen aus letzten Analysen oder synthetisch konstruiert), an denen die neue Version validiert wird.

| Case | Was geprüft wird | Erwartetes Ergebnis |
|------|------------------|---------------------|
| [Adresse / synth. Case 1] | […] | […] |

============================================================

## 8. Status-Verlauf

> Pflicht zu pflegen — am Plan-Ende immer sichtbar, wo der Plan steht.

- **YYYY-MM-DD** — OFFEN, Plan erstellt
- **YYYY-MM-DD** — IN UMSETZUNG, Schritt N läuft
- **YYYY-MM-DD** — ERLEDIGT, Commit `[hash]`, neue Version vX.Y+1 produktiv
- (oder) **YYYY-MM-DD** — VERWORFEN, Grund: […]
