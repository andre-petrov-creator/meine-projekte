# design

Skills und Templates für visuellen Output. Standard-Design für alle Dokumente und Präsentationen.

## Skills

| Skill | Zweck |
|-------|-------|
| [`pdf/`](./pdf/) | **Standard PDF-Design** für alle Output-Typen (Angebot, Exposé, Anschreiben, Report, Onepager). IBM Plex Sans, Anthrazit + Bronze, A4. |
| [`react-pdf/`](./react-pdf/) | **Engine / Library-Referenz** für react-pdf. API-Doku, Komponenten, Quirks. Basis für `pdf/`. |

## Verwendung in Claude

In der Project-Instruction:

```
PDF-OUTPUT STANDARD:
Wenn ein PDF erstellt werden soll:
1. git clone https://github.com/andre-petrov-creator/meine-projekte /home/claude/meine-projekte
2. Lese /home/claude/meine-projekte/design/pdf/SKILL.md
3. Folge dem Setup, nutze template.tsx als Basis
4. Inhalte 1:1 vom Input übernehmen, nichts dazu erfinden
```

## Hierarchie

```
design/
├── pdf/                    ← IMMER nutzen für PDF-Output
│   ├── SKILL.md
│   ├── template.tsx
│   └── assets/example-leistungsverzeichnis.tsx
└── react-pdf/              ← Nachschlagen bei API-Fragen, freien Designs
    ├── SKILL.md            (Original von molefrog/skills, MIT)
    ├── references/
    └── assets/
```

## Erweiterung

Weitere Design-Skills werden hier ergänzt: PowerPoint-Templates, Email-Layouts, Notion-Page-Templates, etc.
