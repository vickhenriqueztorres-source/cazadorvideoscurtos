@echo off
cd /d "%~dp0"
python tools\flicker_diagnose.py %*
