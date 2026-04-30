# meine-projekte

Zentraler lokaler Ordner für alle eigenen Skills und Projekte.
GitHub-Spiegel zur Sicherung: `github.com/andre-petrov-creator/meine-projekte`

## Pfad-Konvention

- **Lokal:** `C:\meine-projekte\`
- **Nicht** in OneDrive (Git-Konflikte) und **nicht** unter `~/.claude/` (Vermischung mit Claude-Code-Internals).

## Inhalt

| Pfad | Was | Status |
|---|---|---|
| `Immobilien/Aufteiler/` | MFH-Aufteiler-Skill (Module 0–5, Orchestrator, Excel-Template) | aktiv |
| `Immobilien/Unterlagen-Check-Ankauf/` | MFH-Due-Diligence-Skill (Junction → `~/.claude/skills/unterlagen-check-ankauf`) | aktiv |
| `skills/claude-code-blueprint/` | Skill für Claude-Code-Projekt-Setup (Junction → `~/.claude/skills/claude-code-blueprint`) | aktiv |
| `commands/` | Custom Slash-Commands (Junction → `~/.claude/commands`) | aktiv |
| `automatisierung-aquise/` | Python-Pipeline: Akquise-Mails → PDF/Adresse → Objekt-Ordner | aktiv |
| `design/` | PDF-Templates (React-PDF) | aktiv |

## Skill-Junction-Pattern

Claude-Code-Skills werden aus `~/.claude/skills/<skill-name>/` geladen. Damit der Master-Code im Mono-Repo bleibt **und** der Skill weiterhin auffindbar ist, wird pro Skill eine Windows-Junction angelegt:

```cmd
cmd /c rmdir "%USERPROFILE%\.claude\skills\<skill-name>"
cmd /c mklink /J "%USERPROFILE%\.claude\skills\<skill-name>" "C:\meine-projekte\<pfad-zum-skill>"
```

Nach Recovery / Rechnerwechsel: Junction in jedem Skill-Folder gemäß dessen README neu anlegen.

## Update-Regel

Bei **jeder Änderung** an Struktur oder Inhalt dieses Ordners → diese README aktualisieren.

## Backup

GitHub-Remote ist die einzige Sicherung. Nach Änderungen:
```bash
cd c:/meine-projekte
git status
git add -A
git commit -m "..."
git push
```

## Historie

- **2026-04-30**: Umzug von `c:\Users\andre\repos\claude-prompts\` → `C:\meine-projekte\`. `automatisierung-aquise/` aus `~/.claude/projects/Automatisierung, Mail, Exposé, Ordner/` integriert.
- **2026-04-30**: `unterlagen-check-ankauf` aus `~/.claude/skills/` ins Mono-Repo migriert (aktive 6-Schritte-Version inkl. `tools/`). Junction-Pattern eingeführt — Master liegt jetzt im Mono-Repo, Skill-Loader nutzt Junction.
- **2026-04-30**: `claude-code-blueprint` (Skill) und `guides-sync` (Slash-Command) ebenfalls ins Mono-Repo migriert. `~/.claude/commands` ist jetzt ebenfalls Junction. Damit liegen alle Claude-Code-Erweiterungen (Skills + Commands) zentral im Mono-Repo + GitHub.
