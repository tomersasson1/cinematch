# Share your local Streamlit app (port 8501) via a public URL.
# No need to install cloudflared or add to PATH — this script downloads and runs it.
#
# Usage (from project root):
#   .\scripts\tunnel.ps1
#
# Make sure Streamlit is already running in another terminal (e.g. python run_app.py).

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BinDir = Join-Path $ProjectRoot "scripts\bin"
$ExePath = Join-Path $BinDir "cloudflared.exe"
$DownloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
}

if (-not (Test-Path $ExePath)) {
    Write-Host "Downloading cloudflared (one-time)..." -ForegroundColor Cyan
    try {
        Invoke-WebRequest -Uri $DownloadUrl -OutFile $ExePath -UseBasicParsing
    } catch {
        Write-Host "Download failed. Try manually: $DownloadUrl" -ForegroundColor Red
        exit 1
    }
    Write-Host "Done. Starting tunnel..." -ForegroundColor Green
} else {
    Write-Host "Starting tunnel..." -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Make sure Streamlit is running on port 8501 in another terminal." -ForegroundColor Yellow
Write-Host "Share the https://....trycloudflare.com URL that appears below." -ForegroundColor Yellow
Write-Host ""

& $ExePath tunnel --url http://localhost:8501
