# Akquise-Pipeline-Starter (PowerShell)
# Wird von Task Scheduler aufgerufen — siehe docs/10_betrieb.md

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

$Python = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$Main   = Join-Path $ProjectDir "main.py"

if (-not (Test-Path $Python)) {
    throw "venv nicht gefunden: $Python — bitte 'python -m venv .venv' ausführen."
}

& $Python $Main
