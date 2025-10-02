@echo off
REM Uvijek radi u folderu gdje je ovaj .bat
pushd "%~dp0"

REM Put do Pythona u virtualnom okruženju
set VENV_PY=.venv\Scripts\python.exe

REM Ako .venv ne postoji, napravi ga
if not exist "%VENV_PY%" (
  echo [INFO] Nema .venv – kreiram virtualno okruzenje...
  py -m venv .venv
)

REM Nadogradi pip i instaliraj potrebne pakete (ako fale)
echo [INFO] Provjera paketa...
"%VENV_PY%" -m pip install --upgrade pip >nul
"%VENV_PY%" -c "import django" 2>nul || (
  echo [INFO] Instaliram Django i dodatke...
  "%VENV_PY%" -m pip install django django-crispy-forms django-crontab
)

REM Pokreni Django server na svim adresama (LAN), port 8000
echo [INFO] Pokrecem server na 0.0.0.0:8000 ...
"%VENV_PY%" manage.py runserver 0.0.0.0:8000

echo.
echo [KRAJ] Pritisni tipku za zatvaranje prozora.
pause >nul
