"""Zentrale Konfiguration der Akquise-Pipeline.

Alle Pfade, Filter, Credentials und Tuning-Parameter sammeln sich hier.
Sensible Werte werden via .env geladen (siehe .env.example).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# .env aus Projekt-Root laden
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Pflicht-Env-Variable fehlt: {name}")
    return value


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default)


# --- Gmail IMAP ---
GMAIL_USER = _optional("GMAIL_USER")
GMAIL_APP_PASSWORD = _optional("GMAIL_APP_PASSWORD")
GMAIL_IMAP_HOST = _optional("GMAIL_IMAP_HOST", "imap.gmail.com")
GMAIL_IMAP_PORT = int(_optional("GMAIL_IMAP_PORT", "993"))

# --- Filter ---
FILTER_FROM_ADDRESS = _optional("FILTER_FROM_ADDRESS", "andre-petrov@web.de")

# --- Ablage-Pfade ---
BASE_FOLDER = Path(
    _optional(
        "BASE_FOLDER",
        r"C:\Users\andre\OneDrive - APPV Personalvermittlung\Immobilien\001_AQUISE\Objekte",
    )
)
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
TEMP_DIR = DATA_DIR / "temp"
STATE_DB_PATH = DATA_DIR / "state.db"

# --- Anthropic API ---
ANTHROPIC_API_KEY = _optional("ANTHROPIC_API_KEY")
# Sonnet 4.6 für Mail-Triage (m02b): klassifiziert Mail + extrahiert Adresse + filtert Links
ANTHROPIC_MODEL_TRIAGE = _optional("ANTHROPIC_MODEL_TRIAGE", "claude-sonnet-4-6")

# --- Logging ---
LOG_LEVEL = _optional("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "pipeline.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# --- IMAP-IDLE Tuning ---
IMAP_IDLE_TIMEOUT_SECONDS = 29 * 60  # Reconnect alle 29 Min (Gmail killt nach 30)
IMAP_RECONNECT_BACKOFF_MAX = 30  # Sekunden

# --- Health-Check ---
HEALTHCHECK_INTERVAL_SECONDS = 6 * 3600  # alle 6 Stunden (in main.py)
HEALTHCHECK_PROCESSING_STALE_HOURS = 1
HEALTHCHECK_LAST_CHECK_FILE = DATA_DIR / "last_healthcheck.json"
HEALTHCHECK_ALERT_TO = "andre-petrov@web.de"

# --- SMTP (für Health-Check-Alert-Mails) ---
GMAIL_SMTP_HOST = _optional("GMAIL_SMTP_HOST", "smtp.gmail.com")
GMAIL_SMTP_PORT = int(_optional("GMAIL_SMTP_PORT", "587"))

# --- PDF-Klassifikator (Filename-Heuristik, Reihenfolge = Priorität) ---
PDF_CLASSIFIER_RULES: list[tuple[str, str]] = [
    (r"expose|exposé", "expose"),
    (r"miet|mieterliste|mieterauflistung|mietmatrix", "mieterliste"),
    (r"energie|energieausweis|epc", "energieausweis"),
    (r"modern|sanierung|renovierung", "modernisierung"),
]

# --- Adress-Extraktion ---
ADDRESS_OBJEKT_TRIGGER = ["Lage", "Objekt", "Anschrift", "Standort", "Adresse"]
ADDRESS_MAKLER_TRIGGER = ["Makler", "Anbieter", "Kontakt", "Telefon", "@", "Tel."]
ADDRESS_LLM_FALLBACK_THRESHOLD = 0.7

# --- Klassifikator → Ziel-Filename ---
CLASSIFIED_FILENAMES: dict[str, str] = {
    "expose": "Exposé.pdf",
    "mieterliste": "Mieterliste.pdf",
    "energieausweis": "Energieausweis.pdf",
    "modernisierung": "Modernisierung.pdf",
}
