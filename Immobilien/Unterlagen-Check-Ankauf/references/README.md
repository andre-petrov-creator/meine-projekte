# references/ — Prüfprotokolle pro Dokumenttyp

Pro Dokumenttyp eine Datei mit der **Prüflogik** für den Subagent. Wird in [Schritt 2 (Parallele Einzelprüfung)](../docs/03_einzelpruefung.md) gelesen und auf das jeweilige Dokument angewendet.

**Trennung von Output-Schema vs. Prüflogik:**
- **Output-Schema** (Kerndaten / Befunde / Red Flags / Offene Fragen) → in [`../SKILL.md`](../SKILL.md) Schritt 2 fest definiert
- **Prüflogik** (was extrahieren, was als Red Flag, womit cross-checken, welche Paragraphen) → hier in `references/<NN>-<typ>.md`

## Mapping Dokumenttyp → Protokoll

| Nr | Dokumenttyp | Protokoll |
|---|---|---|
| 01 | Grundbuchauszug | [`01-grundbuch.md`](01-grundbuch.md) ✅ befüllt |
| 02 | Flurkarte / Liegenschaftskarte | [`02-flurkarte.md`](02-flurkarte.md) |
| 03 | Baulastenverzeichnis | [`03-baulasten.md`](03-baulasten.md) |
| 04 | Altlastenkataster | [`04-altlasten.md`](04-altlasten.md) |
| 05 | Wohnflächenberechnung | [`05-wohnflaeche.md`](05-wohnflaeche.md) |
| 06 | Mietvertrag | [`06-mietvertrag.md`](06-mietvertrag.md) |
| 07 | Mieterliste | [`07-mieterliste.md`](07-mieterliste.md) |
| 08 | Betriebskostenabrechnung | [`08-betriebskosten.md`](08-betriebskosten.md) |
| 09 | Heizkostenabrechnung | [`09-heizkosten.md`](09-heizkosten.md) |
| 10 | Energieausweis | [`10-energieausweis.md`](10-energieausweis.md) |
| 11 | Versicherungspolice / Schadenshistorie | [`11-versicherung.md`](11-versicherung.md) |
| 12 | Baugenehmigung / Bauakte | [`12-baugenehmigung.md`](12-baugenehmigung.md) |
| 13 | Schornsteinfegerprotokoll | [`13-schornsteinfeger.md`](13-schornsteinfeger.md) |
| 14 | Trinkwasseruntersuchung | [`14-trinkwasser.md`](14-trinkwasser.md) |
| 15 | Wartungsvertrag | [`15-wartungsvertraege.md`](15-wartungsvertraege.md) |
| 16 | Modernisierungsnachweise | [`16-modernisierung.md`](16-modernisierung.md) |
| 17 | Teilungserklärung | [`17-teilungserklaerung.md`](17-teilungserklaerung.md) |
| 18 | EV-Protokoll (WEG) | [`18-ev-protokolle.md`](18-ev-protokolle.md) |
| 19 | Wirtschaftsplan / Hausgeldabrechnung | [`19-wirtschaftsplan.md`](19-wirtschaftsplan.md) |
| 20 | Grundsteuerbescheid | [`20-grundsteuer.md`](20-grundsteuer.md) |

## Stand

- **Befüllt (1):** Grundbuchauszug
- **Skeleton (19):** alle übrigen — Sektionen vorhanden, Inhalt `TODO`. Subagents für diese Dokumenttypen prüfen bis zur inhaltlichen Befüllung primär aus LLM-Bauchwissen. Reihenfolge der Befüllung pflegt der User nach Priorität.

## Pflege

- Protokoll erweitern → SKILL.md unverändert lassen, der Verweispfad bleibt gleich
- Neuer Dokumenttyp → neue Datei `<NN>-<kebab>.md` aus [`_template.md`](_template.md) ableiten + diesen Index ergänzen + SKILL.md Mapping-Tabelle erweitern
- Bei Änderung der **Output-Schnittstelle** (Kerndaten/Befunde/…): das passiert in SKILL.md Schritt 2, nicht hier — die Protokolle sind input-seitig
