@echo off
chcp 65001 > nul
title FlowLexAI Backend V9.3 - Forensic Mode

cd /d %~dp0

echo ========================================================
echo   LexIA Core - Orquestador Cloud FlowLexAI
echo ========================================================
echo.

if not exist "logs" mkdir "logs"
echo. > logs\debug_osemoc.log

echo [WORKFLOW] [1/3] Verificando Migraciones Alembic...
poetry run alembic upgrade head
if %ERRORLEVEL% NEQ 0 (
    echo [FAULT] Migraciones fallidas. Abortando inicio. RequestID: ERR-M001
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [WORKFLOW] [2/3] Limpiando log anterior...
echo. > logs\debug_FlowLexAI.log

echo.
echo [WORKFLOW] [3/3] Levantando Motor Core (FastAPI)...
echo Logs: %~dp0logs\debug_FlowLexAI.log
echo.
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-exclude "logs" --log-level info

echo.
echo ========================================================
echo   LexIA Backend detenido.
echo ========================================================
pause
