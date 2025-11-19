@echo off
REM NextWord - One-Click Start Script
REM This script starts both backend and frontend servers

REM Change to script directory
cd /d "%~dp0"

echo ========================================
echo NextWord - Starting Application
echo ========================================
echo.

REM Check if we're in the project directory
if not exist "package.json" (
    echo ERROR: package.json not found!
    echo Please run this script from the NextWord project directory.
    pause
    exit /b 1
)

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH!
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Check for virtual environment (try both venv and .venv)
set "VENV_PATH="
if exist ".venv\Scripts\activate.bat" (
    set "VENV_PATH=.venv"
) else if exist "venv\Scripts\activate.bat" (
    set "VENV_PATH=venv"
) else (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment!
        pause
        exit /b 1
    )
    set "VENV_PATH=venv"
    echo Virtual environment created.
)

echo Activating virtual environment...
call %VENV_PATH%\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment!
    pause
    exit /b 1
)

echo [1/3] Checking dependencies...
echo.

REM Check if Python dependencies are installed
python -m pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Python dependencies not found. Installing...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install Python dependencies!
        pause
        exit /b 1
    )
    echo Python dependencies installed successfully!
) else (
    echo Python dependencies: OK
)

REM Check if Node dependencies are installed
if not exist "node_modules" (
    echo Node.js dependencies not found. Installing...
    call npm install
    if errorlevel 1 (
        echo ERROR: Failed to install Node.js dependencies!
        pause
        exit /b 1
    )
    echo Node.js dependencies installed successfully!
) else (
    echo Node.js dependencies: OK
)

echo.
echo [2/3] Starting backend server...
echo.

REM Get the current directory
set "CURRENT_DIR=%~dp0"

REM Start backend in a new window with venv activated
start "NextWord Backend" cmd /k "cd /d %CURRENT_DIR% && call %VENV_PATH%\Scripts\activate.bat && python -m uvicorn main:app --reload"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

echo [3/3] Starting frontend server...
echo.
echo Backend is running in a separate window.
echo Frontend will start below. Open http://localhost:3000 in your browser.
echo.
echo Press Ctrl+C to stop the frontend server.
echo.

REM Start frontend in current window
call npm run dev

REM If npm run dev exits, pause so user can see any errors
echo.
echo Frontend server stopped.
pause

