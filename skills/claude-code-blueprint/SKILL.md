---
name: claude-code-blueprint
description: Use this skill whenever the user wants to start a new coding project with Claude Code, plan an MVP, build an "Implementierungsplan", set up CLAUDE.md and /docs structure, or asks how to structure prompts for Claude Code in the terminal. Trigger this for any phrase like "neues Projekt mit Claude Code", "Projekt planen", "Implementierungsplan", "MVP bauen", "Prompts für Claude Code", "Claude Code Setup", "wie gehe ich an X ran", or any time the user mentions building software with Claude Code and needs structure. Also trigger when the user has a vague coding idea and says "lass uns sparren" or "lass uns planen". The skill produces two artifacts (Projektbeschreibung + Implementierungsplan) and walks through prompt-per-step execution with Claude Code.
---

# Claude Code Blueprint

Anleitung zum Aufsetzen eines neuen Coding-Projekts mit Claude Code, von der ersten Idee bis zum laufenden MVP.

## Kernidee

Zwei-Ebenen-Setup mit klarer Trennung:

- **Web-Claude (claude.ai Projekt)**: Sparring, Planung, Prompt-Engineering
- **Claude Code (Terminal)**: Ausführung Schritt für Schritt

Output von Web-Claude wird zu Input für Claude Code. Persistenter Kontext läuft über Dateien im Projekt-Repo, nicht über Chat-History.

## Wann diesen Workflow nutzen

- Neues Projekt, MVP-Phase
- Mehr als ein Feature, mehr als eine Datei
- User will strukturiert arbeiten und Token sparen
- ADHS- oder Topic-Switch-Risiko vorhanden, externe Struktur nötig

Bei einzelnen Bugfixes oder Mini-Skripten ist das Overkill. Direkt Claude Code im Terminal nutzen.

## Phase 1: Projekt-Sparring im Web-Claude

Ziel: Zwei Markdown-Dateien als Output.

### Schritt 1.1, Claude-Projekt anlegen

In claude.ai ein neues Projekt erstellen. Custom Instructions enthalten:

- Stack (Sprachen, Frameworks, Datenbank, externe APIs)
- Sprache und Tonfall
- User-spezifische Regeln (Formatpräferenzen, verbotene Floskeln, etc.)

### Schritt 1.2, Sparring-Prompt schicken

Vorlage zum Anpassen:

```
Ich will [PROJEKT] bauen.

Kontext:
- Was: [Was macht das Tool]
- Für wen: [Nutzer]
- Warum: [Problem das gelöst wird]

Stack: [Frameworks, Datenbank, externe APIs]

Lass uns in ein intensives Sparring gehen, um Projektrahmen
und Scope zu bestimmen. Ziel am Ende der Session sind zwei Outputs:

1. Eine Projektbeschreibung als Kontext für ein Claude-Projekt.
2. Einen Implementierungsplan für den MVP, in dem jeder
   Schritt später ein eigener Prompt für Claude Code wird.

Stell mir Rückfragen bevor du ausarbeitest, insbesondere zu
Scope-Cuts (was muss rein, was kommt später).
```

### Schritt 1.3, Iterieren bis Scope sitzt

Claude stellt Rückfragen. User antwortet. Pro Runde max 3 Fragen, sonst kippt Fokus.

Typische Klärungsfelder:
- Authentifizierung (Rollen ja/nein, Admin-only?)
- Datenmodell (welche Tabellen, welche Felder zwingend)
- Externe Integrationen (welche APIs, welche Reihenfolge)
- UI-Scope (welche Screens MVP, was später)
- Deployment (lokal, Vercel, Selbst-Hosting)

### Schritt 1.4, Outputs sichern

Am Ende der Sparring-Session liefert Claude:

**Projektbeschreibung.md**, enthält:
- Überblick (was, für wen, warum)
- Tech-Stack
- Funktionsumfang MVP vs. Later
- Architekturentscheidungen mit Begründung
- Skill-Referenzen (welche installierten Skills relevant sind)

**Implementierungsplan.md**, enthält:
- Schritt 1: Projektstruktur, CLAUDE.md, /docs anlegen
- Schritt 2: Auth/Basis-Setup
- Schritt 3 bis N: Feature für Feature
- Pro Schritt: Ziel, betroffene Dateien, Akzeptanzkriterium, abhängige Schritte

Beide Files als Knowledge-Files im Claude-Projekt hinterlegen. Diese sind ab jetzt der gemeinsame Kontext für alle weiteren Chats.

## Phase 2: Projekt-Setup mit Claude Code

### Schritt 2.1, Initialer Setup-Prompt

Im Terminal Claude Code starten. Ersten Prompt einfügen, der die Projektstruktur erstellt. Ableiten aus Schritt 1 des Implementierungsplans.

Standard-Setup-Prompt:

```
Erstelle die Projektstruktur für [PROJEKT].

Stack: [aus Projektbeschreibung]

Lege folgende Files im Repo-Root an:

1. CLAUDE.md (Steuerungsdatei, siehe unten)
2. DEVELOPMENT_GUIDELINES.md (Konventionen, Code-Style, Architektur)
3. /docs/ (leeres Verzeichnis, wird pro Feature gefüllt)
4. README.md (kurz, Projektzweck und Setup)

CLAUDE.md soll enthalten:
- Vor jeder Aufgabe: Lies DEVELOPMENT_GUIDELINES.md und relevante /docs
- Nach jeder Aufgabe: Aktualisiere oder erstelle /docs/[feature].md
- Skill-Referenzen: [Liste relevanter Skills]
- Stack
- Architektur-Prinzipien

Initialisiere das Projekt mit dem Stack ([npm init / cargo init / etc.])
und installiere die Basis-Dependencies.
```

### Schritt 2.2, CLAUDE.md prüfen

Nach Setup CLAUDE.md öffnen und kontrollieren:

- Vor-Aufgabe-Regel und Nach-Aufgabe-Regel klar formuliert
- Skill-Liste vollständig
- Stack korrekt
- Architektur-Entscheidungen aus der Sparring-Session übernommen

CLAUDE.md ist die einzige Datei die Claude Code automatisch beim Start liest. Was hier nicht drinsteht, muss in jedem Prompt wiederholt werden.

## Phase 3: Pro-Schritt-Prompt-Pattern

Pro Schritt im Implementierungsplan einen neuen Chat im Web-Claude-Projekt öffnen.

### Schritt 3.1, Sparring-Prompt für den Schritt

Vorlage:

```
Schritt [N] aus dem Implementierungsplan: [Titel des Schritts]

Bevor wir den Prompt für Claude Code schreiben, klär mit mir:

1. Was genau soll am Ende dieses Schritts funktionieren? Akzeptanzkriterium?
2. Welche Dateien werden neu angelegt oder geändert?
3. Welche Skills soll Claude Code referenzieren?
4. Welche Doku in /docs muss aktualisiert oder neu erstellt werden?
5. Edge-Cases die bedacht werden müssen?

Danach baust du mir den finalen Prompt für Claude Code.
```

### Schritt 3.2, Finalen Claude-Code-Prompt formen

Output ist ein vollständiger Prompt mit folgender Struktur:

```
[SCHRITT N: TITEL]

Kontext:
- Lies zuerst CLAUDE.md, DEVELOPMENT_GUIDELINES.md
- Relevante /docs: [Liste]
- Skills: [Skill-Namen]

Aufgabe:
[Konkrete Beschreibung was implementiert werden soll]

Akzeptanzkriterium:
[Was muss am Ende funktionieren, prüfbar]

Betroffene Dateien:
- Neu: [Liste]
- Geändert: [Liste]

Doku-Update:
- /docs/[feature].md anlegen oder aktualisieren mit:
  - Was das Feature macht
  - Wie es genutzt wird
  - Welche Files dazugehören

Edge-Cases:
[Aufzählung]
```

### Schritt 3.3, Prompt in Claude Code einfügen

Im Terminal pasten, Claude Code arbeiten lassen.

Während Claude Code arbeitet: nicht parallel im selben Terminal weitermachen. Wenn Probleme auftauchen, Schritt 3.4.

### Schritt 3.4, Bei Problemen zurück ins Web-Claude

Nicht im Terminal lange diskutieren. Tokens werden teuer und Claude Code verliert das größere Bild.

Stattdessen:
1. Fehlermeldung oder Verhalten kopieren
2. Im Web-Claude in den passenden Chat einfügen
3. Lösung sparren
4. Korrektur-Prompt für Claude Code bauen
5. Im Terminal pasten

### Schritt 3.5, Schritt abhaken

Nach erfolgreichem Schritt:
- /docs prüfen, wurde aktualisiert?
- Akzeptanzkriterium manuell testen
- Implementierungsplan im Web-Claude markieren (Schritt N erledigt)
- Nächster Schritt

## Phase 4: Doku-Pflege

`/docs` ist die einzige Quelle der Wahrheit über das System nach dem Code selbst. Pflicht in CLAUDE.md, dass jede Änderung dort landet.

Struktur pro Feature-Doku:

```markdown
# [Feature-Name]

## Zweck
[Was macht das Feature]

## Files
[Liste der zugehörigen Dateien]

## Datenfluss
[Wie Daten durchs Feature laufen]

## Schnittstellen
[APIs, Events, Hooks die es anbietet oder konsumiert]

## Bekannte Limitierungen
[Edge-Cases, TODOs, technische Schulden]
```

Bei jedem neuen Feature: neue Datei. Bei Änderung: bestehende Datei updaten. Diese Files macht Claude Code beim nächsten Prompt zum Kontext.

## Anti-Patterns

Häufige Fehler und Gegenmaßnahmen:

**Direkt im Terminal anfangen ohne Plan**
Führt zu fragmentiertem Code, doppelter Logik, kein gemeinsamer Kontext. Immer Phase 1 zuerst.

**CLAUDE.md ohne "Lies zuerst" Regel**
Claude Code hat dann keinen erzwungenen Kontext-Read und ignoriert /docs. Regel ist zwingend.

**Mehrere Features parallel im selben Chat**
Topic-Switch zerstört Sparring-Tiefe. Pro Schritt ein eigener Chat.

**Web-Claude und Claude Code beide den gleichen Code generieren lassen**
Doppelte Arbeit, divergierende Lösungen. Web-Claude plant, Claude Code baut. Trennung halten.

**Keine /docs-Updates**
Nach drei Features ist der Kontext verloren, jeder neue Prompt muss alles erklären. Doku-Pflicht durchsetzen.

## Templates zum Kopieren

### CLAUDE.md Vorlage

```markdown
# Projekt: [Name]

## Vor jeder Aufgabe
1. Lies DEVELOPMENT_GUIDELINES.md
2. Lies relevante Dateien in /docs
3. Referenziere installierte Skills: [Liste]

## Nach jeder Aufgabe
1. Aktualisiere oder erstelle /docs/[feature].md
2. Halte Code-Style und Konventionen aus GUIDELINES ein
3. Schreibe oder aktualisiere Tests wenn relevant

## Stack
[Stack hier]

## Architektur-Prinzipien
- [Prinzip 1]
- [Prinzip 2]

## Konventionen
- Sprache im Code: [Englisch/Deutsch]
- Naming: [camelCase / snake_case]
- File-Struktur: [Beschreibung]
```

### DEVELOPMENT_GUIDELINES.md Vorlage

```markdown
# Development Guidelines

## Code-Style
[Linter, Formatter, Konventionen]

## Architektur
[Layering, Folder-Struktur, Verantwortlichkeiten]

## Testing
[Was wird getestet, mit welchem Tool]

## Git-Workflow
[Branch-Naming, Commit-Messages, PR-Regeln falls vorhanden]

## Externe Dependencies
[Wann neue Dependency erlauben, wann eigene Lösung]
```

## Vorgehen wenn der User mit diesem Skill arbeitet

Wenn der User sagt "ich will ein neues Projekt aufsetzen" oder ähnliches:

1. Frage zuerst was er bauen will, für wen, mit welchem Stack. Drei Fragen reichen erstmal.
2. Wenn unklar: Interview-Modus, max 3 Fragen pro Runde, bauen erst nach explizitem Go.
3. Wenn klar: Sparring-Prompt aus Phase 1.2 anpassen und gemeinsam durchgehen.
4. Liefere am Ende der Sparring-Session beide Markdown-Files (Projektbeschreibung, Implementierungsplan) als saubere Artefakte.
5. Pro Schritt im Plan: Pattern aus Phase 3 anwenden.

Halte den User dran. Bei Topic-Switch oder Ablenkung kurz darauf hinweisen, aktuellen Schritt nennen, weiter.
