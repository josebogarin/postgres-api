# run_analisis_fuentes.ps1
cd "C:\proyecto FAST API\backend"
.\.venv\Scripts\Activate.ps1
cd "C:\proyecto FAST API"
python analizar_fuentes.py
Read-Host "Presiona Enter para cerrar"
