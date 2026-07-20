@echo off
echo ============================================================
echo  FIX EQUIPOS R32 - P86 y P87 bracket Copa del Mundo 2026
echo ============================================================
echo.
echo Este script corrige:
echo   P86 (Switzerland, Vancouver, Jul 2):
echo     Visitante: Senegal -^> Algeria  [FIFA Match 85]
echo   P87 (Belgium, Seattle, Jul 1):
echo     Visitante: Algeria -^> Senegal  [FIFA Match 82]
echo.
echo Presiona cualquier tecla para aplicar el fix...
pause > nul

echo.
echo [1/2] Aplicando fix en BD...
powershell -Command "Get-Content 'C:\proyecto FAST API\documentacion\fix_r32_equipos.sql' | docker exec -i core-postgres psql -U app_user -d becbuc"

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: El fix SQL fallo. Verificar que Docker este corriendo.
    pause
    exit /b 1
)

echo.
echo [2/2] Fix aplicado. Ahora ejecuta POST /avanzar-bracket/2 desde
echo       el portal (Herramientas ^> Calcular siguiente fase) o via API.
echo.
echo Luego corre POST /calcular-puntajes/2 para actualizar puntajes.
echo.
pause
