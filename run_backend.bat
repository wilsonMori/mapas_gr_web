@echo off
REM Lanzar servidor Backend FastAPI local para Mapas GR
cd /d "%~dp0"
call mapscon310\Scripts\activate.bat
set PYTHONPATH=%CD%\backend;%PYTHONPATH%
echo Iniciando Servidor Backend REST FastAPI en http://localhost:8000 ...
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
pause
