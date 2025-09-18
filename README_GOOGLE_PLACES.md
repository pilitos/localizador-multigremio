
# Localizador multigremio — Google Places + OSM

## Requisitos
- Python 3.12 recomendado. (3.13: usa requirements_313.txt)
- Google Cloud Project con **Places API** habilitada.
- Tu **GOOGLE_API_KEY**.

## Instalación rápida
```powershell
cd C:\GREMIOS
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements_312.txt
```

## Ejecutar
```powershell
streamlit run app_google_places.py
```
Pega tu `GOOGLE_API_KEY` en la **barra lateral** o define:
```powershell
setx GOOGLE_API_KEY "TU_CLAVE"
```

## Modos de búsqueda
- **Provincia**: cubre la provincia con una malla (ajustable en km).  
- **Códigos postales**: radio alrededor del centro de cada CP.  
- **Radio**: alrededor de una dirección/ciudad dada (máx 50 km por limitación de Google).

## Salida
- Tabla + descarga CSV/Excel
- Guardado automático en `C:\GREMIOS\salidas`

