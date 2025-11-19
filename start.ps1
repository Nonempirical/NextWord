# NextWord - One-Click Start Script (PowerShell)
# This script starts both backend and frontend servers

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NextWord - Starting Application" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the project directory
if (-not (Test-Path "package.json")) {
    Write-Host "ERROR: package.json not found!" -ForegroundColor Red
    Write-Host "Please run this script from the NextWord project directory." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Node.js is installed
try {
    $nodeVersion = node --version
    Write-Host "Node.js found: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Node.js is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Node.js from https://nodejs.org/" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[1/4] Setting up virtual environment..." -ForegroundColor Yellow
Write-Host ""

# Check if virtual environment exists, create if not
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create virtual environment!" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "Virtual environment created successfully!" -ForegroundColor Green
} else {
    Write-Host "Virtual environment found." -ForegroundColor Green
}

# Activate virtual environment
$activateScript = Join-Path $PWD "venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
    Write-Host "Virtual environment activated." -ForegroundColor Green
} else {
    Write-Host "ERROR: Could not find virtual environment activation script!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[2/4] Checking dependencies..." -ForegroundColor Yellow
Write-Host ""

# Check if Python dependencies are installed
$fastapiInstalled = python -m pip show fastapi 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python dependencies not found. Installing..." -ForegroundColor Yellow
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install Python dependencies!" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "Python dependencies installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Python dependencies: OK" -ForegroundColor Green
}

# Check if Node dependencies are installed
if (-not (Test-Path "node_modules")) {
    Write-Host "Node.js dependencies not found. Installing..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install Node.js dependencies!" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "Node.js dependencies installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Node.js dependencies: OK" -ForegroundColor Green
}

Write-Host ""
Write-Host "[3/4] Starting backend server..." -ForegroundColor Yellow
Write-Host ""

# Start backend in a new PowerShell window with venv activated
$projectPath = $PWD.Path
$backendScript = @"
cd '$projectPath'
& '$projectPath\venv\Scripts\Activate.ps1'
python -m uvicorn main:app --reload
Write-Host 'Backend server stopped. Press any key to close...' -ForegroundColor Yellow
`$null = `$Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript -WindowStyle Normal

# Wait a moment for backend to start
Start-Sleep -Seconds 3

Write-Host "[4/4] Starting frontend server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Backend is running in a separate window." -ForegroundColor Cyan
Write-Host "Frontend will start below. Open http://localhost:3000 in your browser." -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the frontend server." -ForegroundColor Yellow
Write-Host ""

# Start frontend in current window
npm run dev

# If npm run dev exits, pause so user can see any errors
Write-Host ""
Write-Host "Frontend server stopped." -ForegroundColor Yellow
Read-Host "Press Enter to exit"

