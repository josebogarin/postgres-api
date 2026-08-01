@echo off
echo ============================================================
echo  GIT COMMIT - Sesion 52 partes 3 y 4
echo ============================================================
echo.
echo Cambios incluidos:
echo   - KO_FEEDERS revertidos a valores correctos originales
echo   - P86/P87 visitantes restaurados (Argentina/Cape Verde, Colombia/Ghana)
echo   - Bracket tree SVG rediseñado (live-playoffs + portal)
echo   - CLAUDE.md actualizado
echo.

cd /d "%~dp0..\backend"
git add -A
git commit -m "sesion 52 partes 3+4: revert KO_FEEDERS incorrecto + bracket tree SVG rediseno oficial FIFA"
echo.
echo [OK] Commit en backend hecho.

cd /d "%~dp0.."
git add -A
git commit -m "sesion 52 partes 3+4: CLAUDE.md + scripts bracket + revert r32 fix incorrecto"
echo.
echo [OK] Commit en raiz hecho.

echo.
echo Push al remoto...
cd /d "%~dp0..\backend"
git push
echo.
echo ============================================================
echo  Listo. Ahora ejecuta el backup: .\backup_becbuc.ps1
echo ============================================================
pause
