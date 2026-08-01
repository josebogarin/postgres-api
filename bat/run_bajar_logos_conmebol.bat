@echo off
chcp 65001 >nul
set DEST=%~dp0..\documentacion\iconos-copas
echo === Bajando logos oficiales CONMEBOL a %DEST% ===
if not exist "%DEST%" mkdir "%DEST%"
powershell -NoProfile -Command ^
  "$ua='Mozilla/5.0'; ^
   $d='%DEST%'; ^
   $urls=@{ ^
     'libertadores-oficial.png'='https://gol.conmebol.com/themes/custom/conmebol_libertadores/files/aux-menu-item-libertadores.png'; ^
     'sudamericana-oficial.png'='https://gol.conmebol.com/themes/custom/conmebol_libertadores/files/aux-menu-item-sudamericana.png'; ^
     'conmebol-oficial.svg'='https://gol.conmebol.com/themes/custom/conmebol_libertadores/files/aux-menu-item-conmebol.svg' ^
   }; ^
   foreach($k in $urls.Keys){ try { Invoke-WebRequest -Uri $urls[$k] -OutFile (Join-Path $d $k) -Headers @{'User-Agent'=$ua} -UseBasicParsing; Write-Host ('  OK  ' + $k) } catch { Write-Host ('  ERROR ' + $k + ' : ' + $_.Exception.Message) } }"
echo.
echo === Archivos en %DEST% ===
dir /b "%DEST%\*oficial*"
pause
