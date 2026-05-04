Write-Host "Dang khoi tao moi truong ao bang uv (.venv)..." -ForegroundColor Cyan
uv venv .venv

Write-Host "`nKich hoat moi truong ao..." -ForegroundColor Cyan
& .venv\Scripts\Activate.ps1

Write-Host "`nDang cai dat cac thu vien tu pyproject.toml..." -ForegroundColor Cyan
uv pip install -e .

Write-Host "`n---------------------------------------------------" -ForegroundColor Green
Write-Host "Moi truong dev da san sang!"
Write-Host ""
Write-Host "- De chay test giao dien:  .\run.ps1"
Write-Host "- De dong goi file EXE:    .\build.ps1"
Write-Host "---------------------------------------------------" -ForegroundColor Green
