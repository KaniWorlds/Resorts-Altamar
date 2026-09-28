@echo off
setlocal
cd /d "%~dp0"
set "ALTAMAR_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%ALTAMAR_PY%" (
  "%ALTAMAR_PY%" app.py --open
) else (
  py -3 app.py --open
)
if errorlevel 1 (
  echo No se pudo iniciar. Comprueba que Python 3.11 o posterior esta instalado y el puerto 8080 esta libre.
  pause
)
