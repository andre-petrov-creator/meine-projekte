@echo off
REM Akquise-Pipeline-Starter (Windows BAT)
REM Wird von Task Scheduler aufgerufen — siehe docs/10_betrieb.md

cd /d "%~dp0"
".venv\Scripts\python.exe" main.py
