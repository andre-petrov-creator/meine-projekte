# m02 — Email Parser

## Zweck

Schlüsselt eine `raw_mail` (RFC 822 bytes) auf:
- Header (Message-ID, Subject, Absender)
- PDF-Anhänge → in `data/temp/{message_id}/` ablegen
- Links → aus text/plain und text/html Bodies, dedupliziert

## Public API

| Funktion          | Beschreibung |
|-------------------|--------------|
| `parse(raw_mail)` | Hauptfunktion |
| `run(raw_mail)`   | Pipeline-Konvention (Alias) |

## Output-Schema

```python
{
    "message_id": str,         # ohne <> normalisiert; Fallback "no-id-<sha256-prefix>"
    "subject": str,            # decoded (RFC 2047)
    "von": str,                # nur Email-Adresse, lowercase
    "anhaenge": list[Path],    # Pfade zu gespeicherten PDFs
    "links": list[str],        # Insertion-Order, dedupliziert
}
```

## Verhalten

### Header

- `Message-ID`: `<…>` werden gestrippt. Fehlt der Header → Fallback
  `no-id-<16-stelliger SHA-256-Prefix der raw_mail>` (deterministisch).
- `Subject`: RFC 2047 decoded (`=?utf-8?B?...?=` → Unicode).
- `From`: nur die Email-Adresse extrahiert, lowercase.

### Anhänge

- Erkennung: `Content-Type: application/pdf` **ODER** Filename endet auf `.pdf`
  (Fallback für `application/octet-stream`).
- Ablageort: `config.TEMP_DIR / <sanitized_message_id> / <filename>`.
- Filename-Sanitizing: `<>:"/\\|?*` und Control-Chars werden zu `_`.
- Doppelte Filenames: `_2`, `_3`, …

### Links

- Regex: `https?://[^\s<>"\'\`)\]]+`
- Trailing Punctuation (`.,;:)]}>`) wird gestrippt.
- Dedupliziert per `set`, Insertion-Order bewahrt.
- Quelle: alle `text/*` Parts (plain + html).

## Beispiel

```python
from modules.m02_email_parser import parse

result = parse(raw_mail_bytes)
# {
#   "message_id": "abc@makler.de",
#   "subject": "Exposé MFH Dortmund",
#   "von": "andre-petrov@web.de",
#   "anhaenge": [Path(".../data/temp/abc@makler.de/expose.pdf")],
#   "links": ["https://makler.de/expose-12345"],
# }
```

## Status

✅ Implementiert (Schritt 4). 19 Tests in `tests/test_m02_email_parser.py`
decken Akzeptanzkriterien + Edge Cases (mehrere Anhänge, Doublette,
fehlende Message-ID, Umlaute, Trailing-Punctuation, …).
