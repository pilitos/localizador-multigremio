@echo off
setlocal
title Localizador Multigremio v2 - Arranque
cd /d "%~dp0"

echo [1/5] Comprobando entorno virtual...
if not exist ".venv\Scripts\python.exe" (
  echo    > No existe .venv, creando entorno...
  py -m venv .venv || python -m venv .venv
  if errorlevel 1 (
    echo    ! Error creando el entorno. Asegurate de tener Python instalado en PATH.
    pause
    exit /b 1
  )
)

echo [2/5] Activando entorno...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo    ! No se pudo activar el entorno virtual.
  pause
  exit /b 1
)

echo [3/5] Actualizando pip/setuptools/wheel...
python -m pip install --upgrade pip wheel setuptools

echo [4/5] Instalando dependencias...
pip install -r requirements.txt
if errorlevel 1 (
  echo    ! Fallo instalando dependencias. Revisa requirements.txt
  pause
  exit /b 1
)

echo [5/5] Comprobando secrets...
if not exist ".streamlit" mkdir ".streamlit"
if not exist ".streamlit\secrets.toml" (
  echo GOOGLE_API_KEY="PON_AQUI_TU_API_KEY" > ".streamlit\secrets.toml"
  echo APP_PASSWORD="pon_un_password_opcional" >> ".streamlit\secrets.toml"
  echo.
  echo [INFO] He creado .streamlit\secrets.toml. Abrelo y pon tu GOOGLE_API_KEY antes de continuar.
  start notepad ".streamlit\secrets.toml"
  echo Pulsa una tecla cuando hayas guardado y cerrado Notepad...
  pause >nul
)

echo Lanzando Streamlit...
streamlit run app_google_places_custom.py
echo.
echo [FIN] Si cerraste la app o hubo error, pulsa una tecla para salir.
pause >nul
