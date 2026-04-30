# m05 — Address Extractor

## Zweck

Aus einem Exposé-PDF die **Objekt-Adresse** extrahieren (NICHT die Makler-Adresse).

## Public API

| Funktion                        | Beschreibung |
|---------------------------------|--------------|
| `extract(pdf_path)`             | PDF → dict oder None |
| `extract_from_text(text)`       | Pure-Logik-Version, ideal für Tests |
| `run(pdf_path)`                 | Pipeline-Konvention (Alias) |

## Output

```python
{"adresse": "Musterstraße 12, 44137 Dortmund", "confidence": 0.85}
# oder
None  # wenn keine Adresse oder alle nur makler-typisch
```

## Verfahren

### 1. PDF → Text (`pypdf`)

`PdfReader(path).pages[*].extract_text()`. Bei Fehlern: leerer String, kein Crash.

### 2. Adress-Kandidaten finden

**PLZ ist der Anker.** Jede `\d{5} Stadt`-Sequenz markiert einen potentiellen
Kandidaten. Im 200-Zeichen-Fenster davor wird nach Straße + Hausnummer gesucht.

**Straßen-Erkennung**: 1-4 großgeschriebene Wörter + Hausnummer.
Akzeptiert nur, wenn das **letzte Wort** auf eine deutsche Straßen-Endung endet:

```
straße, strasse, str, weg, allee, platz, gasse, ring, damm,
markt, ufer, chaussee, hof, berg
```

Damit gehen sowohl "Musterstraße 12" (Endung am Wort) als auch "Am Markt 7"
(Endung als eigenes Wort) durch.

**Hausnummern-Formate**: `12`, `12a`, `12-14`, `8/2`, `5 a` werden alle akzeptiert.

### 3. Scoring (Objekt vs. Makler)

Pro Kandidat wird im Kontextfenster (250 Zeichen vor + 100 nach) nach
Trigger-Wörtern gesucht. Trigger aus `config.py`:

| Wirkung   | Trigger |
|-----------|---------|
| **+0.25** | `Lage`, `Objekt`, `Anschrift`, `Standort`, `Adresse` |
| **−0.30** | `Makler`, `Anbieter`, `Kontakt`, `Telefon`, `@`, `Tel.` |

Baseline 0.5, gekappt auf [0, 1].

Kandidaten mit Score = 0 (klar Makler) werden ausgeschlossen.
Höchster Score gewinnt.

### 4. LLM-Fallback

Wenn der beste Score < `ADDRESS_LLM_FALLBACK_THRESHOLD` (Default 0.7) und
`ANTHROPIC_API_KEY` gesetzt ist:

- Anthropic API-Aufruf (Modell `claude-haiku-4-5-20251001`, 10 Tokens).
- Prompt zeigt die Kandidaten-Liste und fragt: "Welche Nummer ist die Objekt-Adresse?"
- Antwort wird zur Index → Kandidat aufgelöst.
- Bei Erfolg: Confidence = 0.95.
- Bei Fehler / unklar: Heuristik-Fallback mit niedriger Confidence.

### 5. Normalisierung

`Candidate.normalized()`:
- `.` aus Straßenname entfernt: "Musterstr." → "Musterstr"
- Whitespace-Kollabierung
- Format: `<Straße> <Hausnr>, <PLZ> <Stadt>`

Beispiel: "Musterstr. 12" + "44137 Dortmund" → `Musterstr 12, 44137 Dortmund`

## Bekannte Grenzen

- **Mehrere Wörter im Stadtnamen** (z.B. "Frankfurt am Main") werden nur teilweise
  erkannt (max. 4 Tokens). Für 99% der NRW-Städte (Dortmund, Essen, …) reicht das.
- **Stadtteil-Adressen** (`44137 Dortmund-Hörde`) gehen durch.
- **Doppelhaushälften** mit `12 a-c`-Format werden zu `12a-c` normalisiert.
- **Wörter am Ende, die zufällig auf Endung enden** (z.B. "Bekanntemarkt") können
  False-Positives sein. Im Praxisalltag selten.

## Beispiel

```python
from modules.m05_address_extractor import extract_from_text

extract_from_text("""
Lage:
Musterstraße 12
44137 Dortmund

Anbieter:
Schmidt Immobilien
Hauptstr. 99, 44135 Dortmund
Tel. 0231/123456
""")
# → {"adresse": "Musterstraße 12, 44137 Dortmund", "confidence": 0.75}
```

## Status

✅ Implementiert (Schritt 7). 23 Tests in `tests/test_m05_address_extractor.py`
decken: 3 Exposés (Dortmund/Essen/Köln), kein Treffer, nur-Makler, fünf
Straßen-Varianten, Scoring, LLM-Fallback (gemockt mit Anthropic SDK).
