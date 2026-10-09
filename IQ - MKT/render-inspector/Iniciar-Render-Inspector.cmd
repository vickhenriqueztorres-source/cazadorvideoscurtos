@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Render Inspector - Console
python -u run.py --url https://iqoption.com/traderoom
echo.
echo Render Inspector encerrado. Codigo: %ERRORLEVEL%
pause
