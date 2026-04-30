@echo off
REM Wöchentlicher Health-Check der Akquise-Pipeline.
REM Wird vom Task Scheduler aufgerufen — Dienstag 9:00 lokal.

cd /d "%~dp0"
".venv\Scripts\python.exe" health_check.py
