# start_all.ps1 - Robust startup script for Docker, Backend, and Frontend

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Starting InterviewCopilot AI Environment " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Start Docker Desktop if not running & Launch Postgres/Redis
Write-Host "`n[1/3] Starting Docker Desktop & Containers..." -ForegroundColor Yellow
$dockerProc = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if (-not $dockerProc) {
    Write-Host "Launching Docker Desktop..." -ForegroundColor Yellow
    $dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerPath) {
        Start-Process $dockerPath
    }
}

Write-Host "Starting Postgres & Redis containers..." -ForegroundColor Green
$dockerCmd = "cd '$PSScriptRoot'; Write-Host '--- Docker Containers ---' -ForegroundColor Cyan; Write-Host 'Waiting for Docker engine and starting postgres & redis...' -ForegroundColor Yellow; `$retries=0; while (`$retries -lt 30) { docker compose up -d postgres redis; if (`$LASTEXITCODE -eq 0) { Write-Host 'Postgres & Redis are UP!' -ForegroundColor Green; break }; Start-Sleep -Seconds 4; `$retries++ }"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $dockerCmd

# 2. Check & Start Backend
Write-Host "`n[2/3] Preparing and starting Backend server (Uvicorn on port 8000)..." -ForegroundColor Yellow
$backendDir = Join-Path $PSScriptRoot "backend"
$backendCmd = "cd '$backendDir'; if (-not (Test-Path '.\.venv\Scripts\python.exe')) { Write-Host 'Creating virtual environment...' -ForegroundColor Yellow; python -m venv .venv }; Write-Host 'Checking dependencies...' -ForegroundColor Yellow; .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt; Write-Host '--- Backend Server (Port 8000) ---' -ForegroundColor Green; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Write-Host "Backend server launched in separate window." -ForegroundColor Green

# 3. Start Frontend
Write-Host "`n[3/3] Starting Frontend development server (Vite)..." -ForegroundColor Yellow
$frontendDir = Join-Path $PSScriptRoot "frontend"
$frontendCmd = "cd '$frontendDir'; Write-Host '--- Frontend Server (Port 5173) ---' -ForegroundColor Cyan; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd
Write-Host "Frontend server launched in separate window." -ForegroundColor Green

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host " All services launched successfully!" -ForegroundColor Green
Write-Host "   Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "   Frontend UI: http://localhost:5173" -ForegroundColor White
Write-Host "==========================================" -ForegroundColor Cyan
