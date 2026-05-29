@echo off
title Online Project Submission Portal - Setup
color 0B

echo.
echo  ============================================================
echo  ^|   ONLINE PROJECT SUBMISSION PORTAL - INITIAL SETUP       ^|
echo  ============================================================
echo.

:: ---------------------------------------------------------------
:: Check if Python is installed
:: ---------------------------------------------------------------
echo  [1/5] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo  [ERROR] Python is NOT installed or not in PATH.
    echo  Please install Python 3.8+ from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do (
    echo         Found Python %%v
)
echo         [OK]
echo.

:: ---------------------------------------------------------------
:: Navigate to the backend directory
:: ---------------------------------------------------------------
pushd "%~dp0python_backend"
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Could not find 'python_backend' folder.
    pause
    exit /b 1
)

:: ---------------------------------------------------------------
:: Create virtual environment
:: ---------------------------------------------------------------
echo  [2/5] Setting up Python virtual environment...
if not exist "venv" (
    echo         Creating virtual environment 'venv'...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo  [ERROR] Failed to create virtual environment.
        popd
        pause
        exit /b 1
    )
    echo         Virtual environment created successfully.
) else (
    echo         Virtual environment already exists. Skipping creation.
)
echo         [OK]
echo.

:: ---------------------------------------------------------------
:: Activate virtual environment
:: ---------------------------------------------------------------
echo  [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Failed to activate virtual environment.
    popd
    pause
    exit /b 1
)
echo         [OK]
echo.

:: ---------------------------------------------------------------
:: Install dependencies
:: ---------------------------------------------------------------
echo  [4/5] Installing required Python packages...
echo         - Flask
echo         - Flask-CORS
echo         - Flask-Session
echo         - bcrypt
echo         - Werkzeug
echo.
pip install --quiet flask flask-cors bcrypt flask-session werkzeug
if %ERRORLEVEL% neq 0 (
    echo.
    echo  [WARNING] Some packages may have failed to install.
    echo  Trying again without --quiet flag...
    pip install flask flask-cors bcrypt flask-session werkzeug
)
echo.
echo         [OK]
echo.

:: ---------------------------------------------------------------
:: Initialize the database
:: ---------------------------------------------------------------
echo  [5/5] Initializing the SQLite database...
python init_sqlite.py
echo         [OK]
echo.

:: ---------------------------------------------------------------
:: Create required upload directories
:: ---------------------------------------------------------------
echo  [+] Ensuring upload directories exist...
if not exist "..\backend\uploads\project_files" (
    mkdir "..\backend\uploads\project_files"
    echo         Created: backend\uploads\project_files
)
if not exist "..\backend\uploads\profile_photos" (
    mkdir "..\backend\uploads\profile_photos"
    echo         Created: backend\uploads\profile_photos
)
if not exist "..\backend\uploads\project_screenshots" (
    mkdir "..\backend\uploads\project_screenshots"
    echo         Created: backend\uploads\project_screenshots
)
echo         [OK]
echo.

:: ---------------------------------------------------------------
:: Done
:: ---------------------------------------------------------------
popd

echo.
echo  ============================================================
echo  ^|                  SETUP COMPLETE!                          ^|
echo  ============================================================
echo.
echo  Next steps:
echo    1. Double-click 'run.bat' to start the application.
echo    2. The browser will open at http://localhost:5000/
echo.
echo  Default Admin Login:
echo    Email:    admin@portal.com
echo    Password: admin123
echo.
echo  ============================================================
echo.
pause
