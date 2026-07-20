# LONGIN SANCTUARY — Windows Setup Script
# Run as Administrator in PowerShell

param(
    [string]$InstallPath = "I:\LonginSanctuary",
    [switch]$SkipDocker,
    [switch]$SkipOllama,
    [switch]$WorkerOnly
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LONGIN SANCTUARY — Windows Setup" -ForegroundColor Cyan
Write-Host "  Install path: $InstallPath" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ── Check prerequisites ──────────────────────────────────────
Write-Host "`n[1/6] Checking prerequisites..." -ForegroundColor Yellow

# Python 3.11+
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "  ❌ Python not found. Installing via winget..." -ForegroundColor Red
    winget install Python.Python.3.11 --silent
} else {
    $ver = python --version 2>&1
    Write-Host "  ✅ Python: $ver" -ForegroundColor Green
}

# Git
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Host "  ❌ Git not found. Installing via winget..." -ForegroundColor Red
    winget install Git.Git --silent
} else {
    Write-Host "  ✅ Git: $(git --version)" -ForegroundColor Green
}

# Node.js
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host "  ❌ Node.js not found. Installing via winget..." -ForegroundColor Red
    winget install OpenJS.NodeJS.LTS --silent
} else {
    Write-Host "  ✅ Node.js: $(node --version)" -ForegroundColor Green
}

# ── Docker Desktop ───────────────────────────────────────────
if (-not $SkipDocker) {
    Write-Host "`n[2/6] Checking Docker Desktop..." -ForegroundColor Yellow
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) {
        Write-Host "  ⚠️  Docker Desktop not found." -ForegroundColor Yellow
        Write-Host "  Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
        Write-Host "  Then re-run this script." -ForegroundColor Yellow
    } else {
        Write-Host "  ✅ Docker: $(docker --version)" -ForegroundColor Green
    }
}

# ── Ollama ───────────────────────────────────────────────────
if (-not $SkipOllama) {
    Write-Host "`n[3/6] Checking Ollama..." -ForegroundColor Yellow
    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollama) {
        Write-Host "  📥 Installing Ollama..." -ForegroundColor Cyan
        winget install Ollama.Ollama --silent
        Write-Host "  ✅ Ollama installed" -ForegroundColor Green
    } else {
        Write-Host "  ✅ Ollama: $(ollama --version)" -ForegroundColor Green
    }
}

# ── NVIDIA GPU check ─────────────────────────────────────────
Write-Host "`n[4/6] Detecting GPU..." -ForegroundColor Yellow
try {
    $gpuInfo = & nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null
    if ($gpuInfo) {
        Write-Host "  ✅ GPU detected: $gpuInfo" -ForegroundColor Green
    }
} catch {
    Write-Host "  ⚠️  nvidia-smi not found (no NVIDIA GPU or drivers not installed)" -ForegroundColor Yellow
}

# ── Python dependencies ──────────────────────────────────────
Write-Host "`n[5/6] Installing Python dependencies..." -ForegroundColor Yellow
Set-Location "$InstallPath\backend"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Write-Host "  ✅ Python dependencies installed" -ForegroundColor Green

# ── Frontend dependencies ────────────────────────────────────
Write-Host "`n[6/6] Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location "$InstallPath\frontend"
npm install
Write-Host "  ✅ Frontend dependencies installed" -ForegroundColor Green

# ── Done ─────────────────────────────────────────────────────
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  ✅ Setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Copy .env.example to .env and configure"
Write-Host "  2. Start databases: docker compose -f docker/docker-compose.yml up -d"
Write-Host "  3. Start API:       cd backend && uvicorn main:app --reload"
Write-Host "  4. Start frontend:  cd frontend && npm run dev"
Write-Host "  5. Open browser:    http://localhost:3000"
Write-Host ""
Write-Host "  To add a device to the cluster, run on the other device:"
Write-Host "  python scripts/cluster_agent.py --master 192.168.1.15"
