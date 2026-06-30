@echo off
title MicMaster 2.0
cd /d "%~dp0"
call .venv\Scripts\activate.bat
start pythonw main.py
