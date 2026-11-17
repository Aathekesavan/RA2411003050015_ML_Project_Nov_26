@echo off
setlocal
set SCRIPT_DIR=%~dp0
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" -m src.api.cli %*
) else (
    python -m src.api.cli %*
)
