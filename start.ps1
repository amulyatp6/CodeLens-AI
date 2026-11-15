$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'

if (-not (Test-Path (Join-Path $backend '.venv'))) {
    py -m venv (Join-Path $backend '.venv')
}
if (-not (Test-Path (Join-Path $backend '.env'))) {
    Copy-Item (Join-Path $backend '.env.example') (Join-Path $backend '.env')
}
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host 'Frontend dependencies are missing. Run: cd frontend; npm install' -ForegroundColor Yellow
}
Start-Process powershell -ArgumentList '-NoExit','-Command',"Set-Location '$backend'; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; python -m uvicorn app.main:app --reload --port 8000"
Start-Process powershell -ArgumentList '-NoExit','-Command',"Set-Location '$frontend'; npm run dev"
Write-Host 'Starting CodeLens AI. Frontend: http://localhost:5173 | Backend docs: http://localhost:8000/docs' -ForegroundColor Cyan
