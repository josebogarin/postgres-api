@echo off
echo ============================================================
echo  FIX SWAP NUMERO FIFA - Adoptando numeracion Excel oficial
echo ============================================================
echo.
echo Aplicando intercambio de numero_fifa para los 5 pares...
Get-Content "%~dp0..\documentacion\fix_swap_numero_fifa.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
echo.
echo Listo. Verifica el output arriba para confirmar los pares corregidos.
echo.
pause
