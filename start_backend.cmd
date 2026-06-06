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
    echo [FAULT] Error en las migraciones. RequestID: ERR-M001
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [AGENT] [2/3] Levantando Consola de Monitoreo (Streamlit)...
start "LexIA Console" cmd /k "chcp 65001 > nul && cd /d %~dp0 && poetry run streamlit run ..\internal_tools\cloud_console\app.py"

echo.
echo [WORKFLOW] [3/3] Levantando Motor Core (FastAPI)...
echo Logs: %~dp0logs\debug_osemoc.log
echo.
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-exclude "logs" --log-level info

echo.
echo ========================================================
echo   LexIA Backend detenido.
echo ========================================================
pause
