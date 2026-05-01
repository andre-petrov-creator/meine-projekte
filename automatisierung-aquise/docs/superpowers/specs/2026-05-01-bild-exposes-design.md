# Design: Bild-Exposés in der Akquise-Pipeline

**Datum:** 2026-05-01
**Status:** Approved (1a / 2c / 3a)
**Scope:** m02, m02b, m04, m06, m09, main.py + requirements + config

---

## Problem

Die Pipeline ignoriert bisher Bild-Anhänge (JPG/PNG/HEIC) und Bild-PDFs. Sonnet 4.6
sieht in der Triage nur Filenames + Text-Body, kann also nicht erkennen, ob ein
gescanntes/abfotografiertes Exposé vorliegt. Mails ohne Text-PDF werden still
als „skipped: keine Exposé-Mail" markiert — kein Alert, kein Ordner.

## Grundannahmen (Vorgabe)

1. Eingehende Mails am Filter-FROM gehen IMMER um Immobilien.
2. Es ist IMMER Exposé-Inhalt vorhanden (PDF, Bild oder Text).
3. Eine leere Mail kommt nie an.
4. Wenn doch nichts identifizierbar ist → Alert via bewährtes Schema.

## Architektur

Pipeline-Pattern bleibt. Erweiterungen pro Modul:

### m02 Email-Parser

Zusätzlich zu PDFs werden extrahiert:

1. **Bild-Anhänge**: jpg, jpeg, png, heic, heif, webp, tiff, gif
2. **Inline-Bilder**: `<img>` aus HTML-Body mit `cid:`-Reference (multipart/related)
3. **Bild-PDFs**: PDFs ohne extrahierbaren Text → erste 5 Seiten via PyMuPDF als JPG rendern

Jedes Bild wird:
- mit `Pillow.ImageOps.exif_transpose` orientiert (EXIF-Auto-Rotate)
- auf max. 1568px lange Kante skaliert (Anthropic-Empfehlung für Vision)
- als JPG mit Quality 85 in `data/temp/{message_id}/` gespeichert
- bei Lese-/Decode-Fehler: `log.warning`, Datei wird übersprungen (nicht in der Output-Liste)

HEIC/HEIF-Support via `pillow-heif`-Plugin (registriert beim Modul-Import).

**Output-Schema erweitert:**

```python
{
    "message_id": str,
    "subject": str,
    "von": str,
    "anhaenge": list[Path],   # PDFs (unverändert)
    "bilder": list[Path],     # NEU: normalisierte JPGs
    "links": list[str],
    "body_plain": str,
}
```

### m02b Mail-Triage

- Bilder werden als `image`-content-blocks via base64 an Sonnet 4.6 übergeben
  (max. 5 Bilder pro Triage, gesteuert via `TRIAGE_MAX_IMAGES`).
- System-Prompt erweitert um: „Bilder sind eine gleichwertige Exposé-Quelle. Erkennst du
  ein Exposé/Lageplan/Mietaufstellung im Bild → nimm es auf."
- **Pydantic-Schema-Änderungen:**
  - `is_expose_mail` ENTFERNT (Grundannahme: jede Mail wird verarbeitet)
  - `expose_image_filenames: list[str]` NEU (analog zu PDF-Filenames)
  - `mietaufstellung_image_filenames: list[str]` NEU
  - `begleit_image_filenames: list[str]` NEU
- `objekt_adresse` bleibt — bevorzugte Quelle, weil Vision Bilder + Text + Subject sieht.

### m04 PDF-Classifier

- Funktion umbenennen-frei `classify(path)` akzeptiert auch Bild-Pfade.
- Default-Mapping bleibt; Triage-Vorgabe via Filename-Set in `expose_image_filenames`
  hat in main.py Vorrang (gleiches Pattern wie für PDFs).

### m05 Address-Extractor

Keine Änderung. Die Triage liefert die Adresse jetzt fast immer (weil Vision
das Bild lesen kann). m05 bleibt Fallback für Text-PDFs ohne Triage-Treffer
(API-Fehler / fehlender Key).

### m06 Folder-Manager

- Akzeptiert Bild-Pfade in `files`-Liste (war schon agnostisch — `shutil.copy2`).
- `CLASSIFIED_FILENAMES` erweitert um Bild-Suffixe:
  - `expose_image` → `Exposé.jpg`
  - `mieterliste_image` → `Mieterliste.jpg`
  - bei mehreren Bildern gleichen Typs: `_unique_file()` hängt `_2`, `_3` an

### m09 Alert-Mailer

Neue Funktion:

```python
def send_no_content_alert(
    message_id: str,
    mail_subject: str,
    mail_von: str,
    reason: str,
    details: dict | None = None,
) -> None:
```

Schema analog zu `send_anomaly_alert` — Subject `❌ Mail-Verarbeitung — kein Inhalt`,
Body mit „Was passiert ist / Was du tun musst"-Block (bewährtes Format).

### main.py

1. **Skip-Pfad raus**: Der Block `if triage and not triage.is_expose_mail: …`
   entfällt vollständig.
2. **Bilder durchschleusen**: `parsed["bilder"]` + Triage-Filter → `image_files`.
3. **PDF + Bild zusammenführen** in `all_files`:
   ```python
   all_files = anhaenge_to_keep + list(link_pdfs) + image_files
   ```
4. **Klassifizierung**: `_classify_files(all_files, triage)` ersetzt `_classify_pdfs`,
   nutzt `expose_image_filenames` als Vorrang-Regel für Bilder.
5. **Hard-Fail-Check** ersetzt aktuelle Anomalie-Logik:
   - Wenn `len(all_files) == 0` AND `adresse is None`
     → `m09.send_no_content_alert()`
     → `m07.mark_error(message_id, "no content extractable")`
     → früh return (kein Folder-Anlegen für leere Mail).
   - Sonst: bestehender Folder-Pfad. Anomalie-Alert (verdächtig viel weniger als erwartet)
     wird beibehalten, aber neu kalibriert: triggert nur, wenn Folder leer wäre
     (inzwischen ja Hard-Fail-Pfad).
6. **Bild-Decode-Fehler** (alle Bilder einer Mail unlesbar) werden vom m02-Parser
   nicht mehr in `bilder` aufgenommen → Hard-Fail greift, wenn sonst nichts da ist.

### config.py

```python
# --- Bild-Verarbeitung ---
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tiff", ".tif", ".gif")
IMAGE_MAX_DIMENSION = 1568          # Anthropic Vision-Empfehlung
IMAGE_JPG_QUALITY = 85
IMAGE_MAX_BYTES = 5 * 1024 * 1024   # Anthropic API-Limit pro Bild
PDF_RENDER_DPI = 150                # Bild-PDF → JPG
PDF_RENDER_MAX_PAGES = 5            # Sicherheits-Cap für gescannte Exposés
PDF_TEXT_MIN_CHARS = 200            # < dieser Schwelle = Bild-PDF (Render-Pfad)
TRIAGE_MAX_IMAGES = 5               # Token-Cap pro Triage

CLASSIFIED_FILENAMES: dict[str, str] = {
    "expose": "Exposé.pdf",
    "mieterliste": "Mieterliste.pdf",
    "energieausweis": "Energieausweis.pdf",
    "modernisierung": "Modernisierung.pdf",
    "expose_image": "Exposé.jpg",            # NEU
    "mieterliste_image": "Mieterliste.jpg",  # NEU
}
```

### requirements.txt

```
Pillow>=10.4.0
pillow-heif>=0.18.0
PyMuPDF>=1.24.0
```

## Datenfluss (End-to-End)

```
Mail (raw RFC822)
  │
  ▼
m02_email_parser.parse()
  ├─► PDFs        → data/temp/{id}/*.pdf
  ├─► Bilder      → data/temp/{id}/*.jpg     (EXIF-rotated, normalisiert)
  ├─► Bild-PDFs   → ALSO data/temp/{id}/{stem}_page{n}.jpg
  └─► dict {anhaenge, bilder, links, body_plain, ...}
  │
  ▼
m02b_mail_triage.triage()  ── Vision-Block für jedes Bild
  └─► TriageResult {objekt_adresse, expose_*_filenames, ...}
  │
  ▼
main.process_mail():
  ├─► all_files = PDFs + Link-PDFs + Bilder
  ├─► HARD-FAIL wenn 0 files + keine Adresse → m09.send_no_content_alert + state=error
  ├─► classify, store, mark_done
  └─► Anomalie-Check (jetzt nur noch für Edge-Cases)
```

## Tests

### Bestehend anpassen

- `test_m02_email_parser.py`: Output enthält jetzt `bilder: []`
- `test_m02b_mail_triage.py` (falls existiert): `is_expose_mail` raus aus Schema
- `test_main.py`: Skip-Pfad-Test entfernen, Hard-Fail-Test ergänzen

### Neu

- `test_m02_email_parser.py::test_extracts_image_attachment` — fixture mit JPG-Anhang
- `test_m02_email_parser.py::test_exif_rotates_image` — EXIF-Orientation 6 → portrait
- `test_m02_email_parser.py::test_inline_html_image` — `cid:`-Reference im HTML-Body
- `test_m02_email_parser.py::test_image_pdf_renders_pages` — PDF ohne Text → JPGs
- `test_m02_email_parser.py::test_unreadable_image_is_skipped` — kaputtes JPG, kein Crash
- `test_m04_pdf_classifier.py::test_classifies_image_filename` — JPG mit „Exposé" im Namen
- `test_m09_alert_mailer.py::test_no_content_alert` — Schema + SMTP-Mock
- `test_main.py::test_hard_fail_no_content` — Mail ohne PDFs+Bilder+Adresse → Alert+error

## Risiken / Edge Cases

- **HEIC**: Pillow-HEIF muss bei Import registriert werden. Wenn auf einem System nicht installiert, fallback: log.warning, Bild übersprungen.
- **Token-Kosten**: 5 Bilder × ~1500 Tokens ≈ 7500 Vision-Tokens pro Mail. Bei Sonnet 4.6 ~3 ct/Mail. Akquise-Volumen ist niedrig → tragbar.
- **Bild-PDF-Render-Zeit**: PyMuPDF 150 DPI auf 5 Seiten ~2 s. Akzeptabel.
- **EXIF in PNG**: PNG hat normalerweise kein EXIF — `exif_transpose` ist no-op, kein Problem.
- **Sehr große HEIC vom iPhone**: ~5 MB ist üblich. Nach Skalierung auf 1568px lange Kante meist <500 KB → API-Limit ok.

## Implementierungs-Reihenfolge

1. requirements + config (Foundation)
2. m02 Parser (Bild-Extraktion + Bild-PDF-Render) + Tests
3. m02b Triage (Vision + Schema-Änderung) + Tests
4. m04 + m06 + m09 (kleinere Anpassungen)
5. main.py Hard-Fail + Skip-Pfad raus + Tests
6. Smoke-Test mit echtem Mail-Sample
