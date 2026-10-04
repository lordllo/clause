param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$Repo = Split-Path $PSScriptRoot -Parent
Set-Location (Join-Path $Repo "backend")
if (!(Test-Path ".venv/Scripts/python.exe")) { & $Python -m venv .venv }
& .venv/Scripts/python.exe -m pip install -r requirements.lock.txt
& .venv/Scripts/python.exe -m pip install --no-deps -e '.[dev]'
$Api = Start-Process -FilePath (Join-Path $Repo 'backend/.venv/Scripts/python.exe') -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory (Join-Path $Repo 'backend') -WindowStyle Hidden -PassThru
try {
    Set-Location (Join-Path $Repo "frontend")
    npm.cmd ci
    npm.cmd run dev
} finally { Stop-Process -Id $Api.Id -ErrorAction SilentlyContinue }
