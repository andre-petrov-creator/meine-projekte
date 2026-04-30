# m04 — PDF Classifier

## Zweck

Klassifiziert ein PDF anhand seines **Filenames** (Heuristik).
Keine Inhaltsanalyse — die wäre erst in Pipeline 2 sinnvoll (LLM-Klassifikator).

## Public API

| Funktion             | Beschreibung |
|----------------------|--------------|
| `classify(pdf_path)` | Hauptfunktion |
| `run(pdf_path)`      | Pipeline-Konvention (Alias) |

## Output

```python
{"typ": str, "confidence": float}
```

## Typen und Regeln

Aus `config.PDF_CLASSIFIER_RULES` (Reihenfolge = Priorität, case-insensitive):

| Reihenfolge | Pattern (Regex)                                     | Typ              |
|-------------|------------------------------------------------------|------------------|
| 1           | `expose|exposé`                                      | `expose`         |
| 2           | `miet|mieterliste|mieterauflistung|mietmatrix`       | `mieterliste`    |
| 3           | `energie|energieausweis|epc`                         | `energieausweis` |
| 4           | `modern|sanierung|renovierung`                       | `modernisierung` |
| Default     | (kein Match)                                         | `sonstiges`      |

## Confidence

| Wert  | Wann |
|-------|------|
| `1.0` | Klarer Match auf eine Regel |
| `0.5` | Default `sonstiges` |

Confidence wird in m06 nicht (mehr) ausgewertet, ist aber als Hook für
spätere Pipeline-2-Verbesserung mitgeführt (LLM-Klassifikator könnte
0.0–1.0 liefern).

## Mehrfachmatch

Wenn mehrere Regeln matchen (z.B. `Expose-mit-Mietliste.pdf`), gewinnt die
**erste passende Regel** (höchste Priorität in der Liste).

## Beispiel

```python
from modules.m04_pdf_classifier import classify

classify("Exposé MFH Dortmund.pdf")  # → {"typ": "expose", "confidence": 1.0}
classify("Mieterliste-2026.pdf")     # → {"typ": "mieterliste", "confidence": 1.0}
classify("Energieausweis.pdf")       # → {"typ": "energieausweis", "confidence": 1.0}
classify("Doku.pdf")                 # → {"typ": "sonstiges", "confidence": 0.5}
```

## Erweitern

Neue Regel? `config.PDF_CLASSIFIER_RULES` ergänzen — kein Code-Change nötig.

## Status

✅ Implementiert (Schritt 6). 39 Tests in `tests/test_m04_pdf_classifier.py`
(20 parametrisiert für die 4 Match-Typen + 5 für `sonstiges`, Akzeptanzkriterien
aus dem Plan abgedeckt).
