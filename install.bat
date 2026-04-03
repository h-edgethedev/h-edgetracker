@echo off
title H~EDGE Tracker - Installer
color 0A

echo.
echo  ================================================
echo   H~EDGE Tracker - Installer
echo  ================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo.
    echo  Please install Python 3.10+ from https://python.org
    echo  Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

echo  [OK] Python found.
echo.

:: Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] pip not found. Please reinstall Python.
    pause
    exit /b 1
)

echo  [OK] pip found.
echo.
echo  Installing dependencies...
echo.

pip install flet==0.21.2 pywin32 psutil

if errorlevel 1 (
    echo.
    echo  [ERROR] Failed to install dependencies.
    echo  Try running this script as Administrator.
    pause
    exit /b 1
)

echo.
echo  ================================================
echo   Installation complete!
echo  ================================================
echo.
echo  To set your Anthropic API key (needed for AI features):
echo.
echo    python cli.py set-key YOUR_API_KEY_HERE
echo.
echo  To launch the app, run:
echo.
echo    run.bat
echo.
pause
