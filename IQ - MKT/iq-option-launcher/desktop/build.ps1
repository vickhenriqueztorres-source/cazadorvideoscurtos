$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    python -m PyInstaller --noconfirm --clean --onefile --console --name IQ-Visual-Launcher-console --add-data 'injector.js;.' --add-data 'config.json;.' --collect-data selenium launcher.py
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar o executável.' }
} finally {
    Pop-Location
}
