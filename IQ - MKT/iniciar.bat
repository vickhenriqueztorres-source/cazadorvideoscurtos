@echo off
chcp 65001 >nul
cd /d %~dp0render-inspector
title Render Inspector
python -u run.py
echo.
echo Processo encerrado. Codigo: %ERRORLEVEL%
pause
