# m06 — Folder Manager

## Zweck

Adresse + klassifizierte Files → Objekt-Ordner unter `BASE_FOLDER` anlegen,
Files reinkopieren, `_meta.json` schreiben.

## Public API

| Funktion                                                | Beschreibung |
|---------------------------------------------------------|--------------|
| `store(adresse, files, meta=None, base_folder=None)`    | Hauptfunktion |
| `run(adresse, files, meta=None, base_folder=None)`      | Pipeline-Konvention (Alias) |

Returns: `Path` zum erstellten Ordner.

## Eingabe-Formate

```python
files = [
    {"path": Path("/temp/expose.pdf"),     "typ": "expose"},
    {"path": Path("/temp/mieter.pdf"),     "typ": "mieterliste"},
    {"path": Path("/temp/energie.pdf"),    "typ": "energieausweis"},
]

meta = {
    "message_id": "abc@x",
    "von": "andre-petrov@web.de",
    "subject": "Exposé MFH Dortmund",
    "timestamp": "2026-04-30T10:00:00",   # optional, Default = jetzt
}
```

## Ordnernamen-Strategie

| Eingabe                        | Ordnername |
|--------------------------------|------------|
| Adresse vorhanden              | Adresse (Sonderzeichen `<>:"/\\|?*` → `_`) |
| Adresse `None` oder leer       | `YYYY-MM-DD_HH-MM-SS_unbekannt` |
| Ordner existiert bereits       | Suffix `_2`, `_3`, … |

## Datei-Namensstrategie

Aus `config.CLASSIFIED_FILENAMES`:

| Typ                | Ziel-Filename       |
|--------------------|---------------------|
| `expose`           | `Exposé.pdf`        |
| `mieterliste`      | `Mieterliste.pdf`   |
| `energieausweis`   | `Energieausweis.pdf`|
| `modernisierung`   | `Modernisierung.pdf`|
| `sonstiges`        | Originalname behalten |

Doppelter Typ in einer Mail (zwei Exposés) → `Exposé.pdf` + `Exposé_2.pdf`.

## `_meta.json`

```json
{
  "adresse": "Musterstr 12, 44137 Dortmund",
  "message_id": "abc@x",
  "von": "andre-petrov@web.de",
  "subject": "Exposé MFH Dortmund",
  "timestamp": "2026-04-30T10:00:00",
  "files": [
    {"name": "Exposé.pdf",        "typ": "expose",        "source": "expose_orig.pdf"},
    {"name": "Mieterliste.pdf",   "typ": "mieterliste",   "source": "mieterliste_orig.pdf"},
    {"name": "Energieausweis.pdf","typ": "energieausweis","source": "energieausweis_orig.pdf"}
  ]
}
```

UTF-8, indent=2, `ensure_ascii=False` (deutsche Umlaute lesbar).

## Verhalten bei Fehlern

- **Quelldatei fehlt** → loggen, überspringen, Pipeline läuft weiter.
- **Files = leere Liste** → leerer Ordner wird trotzdem angelegt + `_meta.json` mit `files: []`.
- **Files werden kopiert (`shutil.copy2`)**, nicht verschoben — Originale bleiben in `data/temp/`.

## Beispiel

```python
from modules.m06_folder_manager import store

target = store(
    adresse="Musterstr 12, 44137 Dortmund",
    files=[
        {"path": expose_pdf, "typ": "expose"},
        {"path": mieter_pdf, "typ": "mieterliste"},
    ],
    meta={"message_id": "abc@x", "von": "andre-petrov@web.de", "subject": "Test"},
)
# target = …/001_AQUISE/Objekte/Musterstr 12, 44137 Dortmund/
```

## Status

✅ Implementiert (Schritt 8). 20 Tests in `tests/test_m06_folder_manager.py`.
