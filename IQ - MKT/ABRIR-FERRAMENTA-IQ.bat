@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Ferramenta IQ - Render Inspector

set "APP_DIR=C:\Users\brend\OneDrive\Documentos\ChatGPT\IQ - MKT\render-inspector"
if exist "%~dp0render-inspector\run.py" set "APP_DIR=%~dp0render-inspector"
set "VENV_PY=%APP_DIR%\.venv\Scripts\python.exe"
set "REQ_FILE=%APP_DIR%\requirements.txt"
set "TARGET_URL=https://iqoption.com/traderoom"

if not exist "%APP_DIR%\run.py" (
    echo.
    echo ERRO: a pasta da Ferramenta IQ nao foi encontrada.
    echo Caminho esperado: C:\Users\brend\OneDrive\Documentos\ChatGPT\IQ - MKT\render-inspector
    echo.
    pause
    exit /b 1
)

if /i "%~1"=="--check" goto check_only

for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$c=Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue; if($c){$c.OwningProcess}"`) do set "RUNNING_PID=%%P"
if defined RUNNING_PID (
    echo.
    echo A Ferramenta IQ ja esta aberta ^(processo %RUNNING_PID%^).
    echo Use a janela do Chrome que ja foi iniciada por ela.
    echo.
    powershell -NoProfile -Command "Start-Sleep -Seconds 3"
    exit /b 0
)

if exist "%VENV_PY%" goto run_tool

set "BASE_PY="
for /f "delims=" %%P in ('where python 2^>nul') do if not defined BASE_PY set "BASE_PY=%%P"
if not defined BASE_PY (
    echo.
    echo ERRO: Python 3 nao foi encontrado neste computador.
    echo Instale o Python 3 e marque a opcao "Add Python to PATH".
    echo.
    pause
    exit /b 2
)

echo.
echo Preparando a Ferramenta IQ para o primeiro uso...
"%BASE_PY%" -m venv "%APP_DIR%\.venv"
if errorlevel 1 goto setup_error

"%VENV_PY%" -m pip install --disable-pip-version-check -r "%REQ_FILE%"
if errorlevel 1 goto setup_error

:run_tool
cd /d "%APP_DIR%"
echo.
echo Abrindo a Ferramenta IQ...
echo Mantenha esta janela aberta enquanto estiver usando a plataforma.
echo Para encerrar, feche o Chrome da ferramenta ou pressione Ctrl+C aqui.
echo.
"%VENV_PY%" -u run.py --url "%TARGET_URL%"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
    echo Ferramenta encerrada normalmente.
) else (
    echo A ferramenta foi encerrada com o codigo %EXIT_CODE%.
    pause
)
exit /b %EXIT_CODE%

:check_only
echo Launcher encontrado.
echo Aplicativo: %APP_DIR%
if exist "%VENV_PY%" (
    echo Python local: pronto
) else (
    echo Python local: sera preparado no primeiro uso
)
exit /b 0

:setup_error
echo.
echo ERRO: nao foi possivel preparar as dependencias da ferramenta.
echo Verifique a conexao com a internet e tente novamente.
echo.
pause
exit /b 3
