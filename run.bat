@echo off
title Online Project Submission Portal - Server
color 0A

echo.
echo  ============================================================
echo  ^|   ONLINE PROJECT SUBMISSION PORTAL - RUN SERVER          ^|
echo  ============================================================
echo.

:: ---------------------------------------------------------------
:: Navigate to the backend directory
:: ---------------------------------------------------------------
pushd "%~dp0python_backend"
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Could not find 'python_backend' folder.
    echo  Make sure you are running this from the project root.
    pause
    exit /b 1
)

:: ---------------------------------------------------------------
:: Check if virtual environment exists
:: ---------------------------------------------------------------
echo  [1/3] Checking virtual environment...
if not exist "venv" (
    echo.
    echo  [ERROR] Virtual environment not found!
    echo  Please run 'setup.bat' first to set up the project.
    echo.
    popd
    pause
    exit /b 1
)
echo         [OK]
echo.

:: ---------------------------------------------------------------
:: Activate virtual environment
:: ---------------------------------------------------------------
echo  [2/3] Activating virtual environment...
call venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Failed to activate virtual environment.
    echo  Try deleting the 'venv' folder and running 'setup.bat' again.
    popd
    pause
    exit /b 1
)
echo         [OK]
echo.

:: ---------------------------------------------------------------
:: Check if Flask is installed
:: ---------------------------------------------------------------
python -c "import flask" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [WARNING] Flask not found. Installing dependencies...
    pip install --quiet flask flask-cors bcrypt flask-session werkzeug
    echo.
)

:: ---------------------------------------------------------------
:: Start the server
:: ---------------------------------------------------------------
echo  [3/3] Starting Flask server...
echo.
echo  ============================================================
echo  ^|  Server running at: http://localhost:5000/               ^|
echo  ^|  Press CTRL+C to stop the server.                        ^|
echo  ^|  DO NOT close this window while using the application!   ^|
echo  ============================================================
echo.

:: Open the browser after a short delay
start "" http://localhost:5000/

:: Start the Flask application
python app.py

:: If we reach here, the server was stopped
echo.
echo  Server stopped.
popd
pause
