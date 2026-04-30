"""m06 — Folder Manager.

Adresse + Files → Objekt-Ordner unter `BASE_FOLDER` anlegen, Files
reinkopieren mit Naming nach Klassifikation, `_meta.json` schreiben.

Public API:
    store(adresse, files, meta=None, base_folder=None) -> Path
    run(adresse, files, meta=None, base_folder=None) -> Path

Eingabe `files`:
    [{"path": Path | str, "typ": str}, ...]
    typ ∈ {"expose", "mieterliste", "energieausweis", "modernisierung", "sonstiges"}

Eingabe `meta`:
    {"message_id": str, "von": str, "subject": str, "timestamp": str | None}
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import config
from modules.m08_logger import get_logger

log = get_logger(__name__)

_FORBIDDEN_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def store(
    adresse: str | None,
    files: list[dict],
    meta: dict | None = None,
    base_folder: str | Path | None = None,
) -> Path:
    """Legt Objekt-Ordner an, kopiert Files, schreibt _meta.json. Gibt den Pfad zurück."""
    base = Path(base_folder) if base_folder is not None else config.BASE_FOLDER
    base.mkdir(parents=True, exist_ok=True)

    folder_name = _folder_name_for(adresse)
    target = _unique_folder(base / folder_name)
    target.mkdir(parents=True)
    log.info("Objekt-Ordner angelegt: %s", target)

    saved_entries: list[dict] = []
    for entry in files:
        source = Path(entry["path"])
        typ = entry.get("typ", "sonstiges")

        if not source.exists():
            log.warning("Source-File fehlt, überspringe: %s", source)
            continue

        target_name = _target_filename_for(source, typ)
        target_path = _unique_file(target / target_name)
        shutil.copy2(source, target_path)
        log.info("Datei kopiert: %s → %s", source.name, target_path.name)

        saved_entries.append(
            {
                "name": target_path.name,
                "typ": typ,
                "source": source.name,
            }
        )

    meta = meta or {}
    meta_data = {
        "adresse": adresse,
        "message_id": meta.get("message_id"),
        "von": meta.get("von"),
        "subject": meta.get("subject"),
        "timestamp": meta.get("timestamp")
        or datetime.now().isoformat(timespec="seconds"),
        "files": saved_entries,
    }
    (target / "_meta.json").write_text(
        json.dumps(meta_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return target


def run(
    adresse: str | None = None,
    files: list[dict] | None = None,
    meta: dict | None = None,
    base_folder: str | Path | None = None,
) -> Path:
    """Pipeline-Konvention."""
    if files is None:
        raise ValueError("files ist Pflicht für m06_folder_manager.run()")
    return store(adresse, files, meta, base_folder)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _folder_name_for(adresse: str | None) -> str:
    if not adresse or not adresse.strip():
        return f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_unbekannt"
    return _sanitize(adresse)


def _target_filename_for(source: Path, typ: str) -> str:
    """Klassifiziert-Naming aus config; bei `sonstiges` Original behalten."""
    classified = config.CLASSIFIED_FILENAMES.get(typ)
    if classified:
        return _sanitize(classified)
    return _sanitize(source.name)


def _sanitize(value: str) -> str:
    cleaned = _FORBIDDEN_PATH_CHARS.sub("_", value).strip(" .")
    return cleaned or "unbekannt"


def _unique_folder(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.name}_{counter}")
        if not candidate.exists():
            return candidate
        counter += 1


def _unique_file(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
