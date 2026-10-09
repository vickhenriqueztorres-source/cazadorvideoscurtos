@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "dist\IQ-Visual-Launcher-console.exe" (
    echo Iniciando IQ Visual Launcher. Os logs aparecerao nesta janela.
    echo Feche a janela do aplicativo para encerrar a sessao do Chrome.
    echo.
    "dist\IQ-Visual-Launcher-console.exe" --auto
) else (
    python -u launcher.py --auto
)
echo.
echo Aplicativo encerrado. Os logs continuam acima.
pause
