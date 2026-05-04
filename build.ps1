Write-Host "Dang xoa cache build cu..." -ForegroundColor Yellow
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
if (Test-Path *.spec) { Remove-Item -Force *.spec }

Write-Host "Dang dong goi thanh EXE..." -ForegroundColor Cyan
& .venv\Scripts\Activate.ps1

# Lay duong dan Python DLLs de nhung truc tiep
$python_dir = python -c "import sys; print(sys.base_prefix)"
$dlls_path = Join-Path $python_dir "DLLs"
Write-Host "Nhung OpenSSL DLLs tu: $dlls_path" -ForegroundColor Gray

pyinstaller --onefile --windowed --name NTEVietPatch --icon=icon.ico --add-data "icon.png;." `
    --add-binary "$dlls_path\libcrypto-3-x64.dll;." `
    --add-binary "$dlls_path\libssl-3-x64.dll;." `
    --paths $dlls_path main.py

Write-Host "`nHoan tat! File EXE nam trong thu muc dist\" -ForegroundColor Green
