@echo off
title MicMaster Pro - Instalador
color 0A
echo.
echo  ============================================
echo   🎙️  MicMaster Pro — Instalador
echo  ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ❌ Python nao encontrado!
    echo  Baixe em: https://www.python.org/downloads/
    echo  Marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

echo  ✅ Python encontrado
echo.

:: Create venv
echo  📦 Criando ambiente virtual...
if exist ".venv" (
    echo     Ambiente ja existe, pulando...
) else (
    python -m venv .venv
    echo     Ambiente criado!
)

:: Activate and install
echo.
echo  📥 Instalando dependencias...
call .venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
echo  ✅ Dependencias instaladas!

:: Create desktop shortcut
echo.
echo  🔗 Criando atalho na Area de Trabalho...
set SCRIPT_DIR=%~dp0
set DESKTOP=%USERPROFILE%\Desktop

(
echo @echo off
echo cd /d "%SCRIPT_DIR%"
echo call .venv\Scripts\activate.bat
echo pythonw main.py
) > "%DESKTOP%\MicMaster Pro.bat"

echo  ✅ Atalho criado: "%DESKTOP%\MicMaster Pro.bat"

echo.
echo  ============================================
echo   ✅ Instalacao concluida!
echo  ============================================
echo.
echo  ⚠️  IMPORTANTE: Para usar o microfone virtual,
echo     voce precisa instalar o VB-Audio Virtual Cable:
echo     https://vb-audio.com/Cable/
echo.
echo     Depois de instalar, reinicie o PC.
echo     No MicMaster, selecione "CABLE Input" como saida.
echo     No OBS/Discord, selecione "CABLE Output" como microfone.
echo.
echo  Para iniciar: clique duas vezes em "MicMaster Pro.bat"
echo  na sua Area de Trabalho.
echo.
pause
