# AXIOM Backend Server Startup Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AXIOM Layer 2 & 2.5 Backend Server  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the correct directory
if (-not (Test-Path "main.py")) {
    Write-Host "Error: main.py not found. Please run this script from the backend directory." -ForegroundColor Red
    exit 1
}

Write-Host "Starting FastAPI server..." -ForegroundColor Green
Write-Host "Server will be available at: http://localhost:8000" -ForegroundColor Yellow
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press CTRL+C to stop the server" -ForegroundColor Gray
Write-Host ""

# Start uvicorn
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000