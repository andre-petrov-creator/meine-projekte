# pdf

Standard-Design für alle PDF-Outputs. IBM Plex Sans, Anthrazit + Bronze, A4.

Funktioniert für jeden Dokument-Typ: Angebot, Leistungsverzeichnis, Exposé, Anschreiben, Report, Onepager, Pitch, etc.

## Quickstart

```bash
# 1. Setup
mkdir -p /home/claude/pdf-work/fonts && cd /home/claude/pdf-work
npm init -y > /dev/null
npm install react @react-pdf/renderer
npm install -D tsx @types/react

# 2. Fonts
URLS=($(curl -sL "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" -A "Mozilla/5.0" | grep -oP "https://[^)]+\.ttf"))
curl -sL "${URLS[0]}" -o fonts/IBMPlexSans-Italic.ttf
curl -sL "${URLS[1]}" -o fonts/IBMPlexSans-Regular.ttf
curl -sL "${URLS[2]}" -o fonts/IBMPlexSans-Medium.ttf
curl -sL "${URLS[3]}" -o fonts/IBMPlexSans-SemiBold.ttf
curl -sL "${URLS[4]}" -o fonts/IBMPlexSans-Bold.ttf

# 3. Template kopieren
cp /home/claude/meine-projekte/design/pdf/template.tsx document.tsx

# 4. Daten-Block anpassen, dann Render
npx tsx document.tsx
```

## Files

- `SKILL.md` — Vollständige Skill-Anweisungen für Claude
- `template.tsx` — Wiederverwendbares Skelett mit allen Komponenten
- `assets/example-leistungsverzeichnis.tsx` — Vollständiges Beispiel (LV Fassade / WDVS)

## Components

| Component | Purpose |
|-----------|---------|
| `<HeaderFooter>` | Fixed Header mit Bronze-Akzentlinie + Footer mit Seitenzahl |
| `<CoverBlock>` | Großer Titel-Block (Eyebrow + Title + Subtitle) |
| `<TableOfContents>` | Inhaltsverzeichnis aus Items-Array |
| `<SectionHeader>` | Eyebrow-Label + Section-Title |
| `<DataTable>` | 4-Spalten-Tabelle mit Zebra-Streifen |
| `<ChapterBlock>` | Section + Tabelle + optional Note (wrap={false}) |
| `<HinweisBox>` | Italic-Box mit Bronze-Linie |
| `<ExcludedBox>` | Bullet-Liste mit Bronze-Linie |
| `<NumberedHints>` | Nummerierte Hinweise mit Bronze-Nummern |
| `<SummaryGrid>` | 2-Spalten-Karten-Grid |
| `<BodyText>` | Standard-Fließtext für Briefe / Reports |

## Color Tokens

```ts
anthrazit:     #1F2937   // Primary dark
textDark:      #374151   // Body
textMid:       #6B7280   // Secondary
lineLight:     #E5E7EB   // Dividers
bgSoft:        #F9FAFB   // Zebra, cards
bronze:        #B45309   // Accent
```

## License

MIT
