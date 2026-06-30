@echo off
title MicMaster 2.0 - Diagnostico do Sistema
color 0A
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python diagnose_system.py
pause
