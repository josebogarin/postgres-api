@echo off
echo === Reiniciando servidor BECBUC ===
cd /d "C:\proyecto FAST API\backend"

REM Matar proceso uvicorn anterior
taskkill /F /IM python.exe /T 2>nul
timeout /t 2 /nobreak >nul

REM Iniciar servidor en background
start "BECBUC Server" .venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --reload
timeout /t 5 /nobreak >nul

REM Test: login + avanzar bracket + verificar
echo === Testing brackets ===
cd /d "C:\proyecto FAST API"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$b='http://localhost:8000';" ^
  "$t=(Invoke-RestMethod -Uri $b/api/v1/auth/login -Method POST -ContentType 'application/x-www-form-urlencoded' -Body 'username=jose&password=catalina').access_token;" ^
  "$h=@{Authorization='Bearer '+$t};" ^
  "Write-Host '--- Avanzando bracket ---' -ForegroundColor Green;" ^
  "Invoke-RestMethod -Uri $b/api/v1/bets/avanzar-bracket/2 -Method POST -Headers $h | ConvertTo-Json -Depth 2;" ^
  "Write-Host '--- Bracket Real 16avos ---' -ForegroundColor Green;" ^
  "$br=(Invoke-RestMethod -Uri $b/api/v1/bets/bracket-real/2 -Headers $h);" ^
  "$r32=$br.partidos | where tipo -eq ronda32;" ^
  "Write-Host ('Total KO: '+$br.partidos.Count+' | ronda32: '+$r32.Count);" ^
  "$r32 | select -First 8 | % { Write-Host ('P'+$_.num+': '+(if($_.local){$_.local.nombre+'['+$_.local.iso+']'}else{'VACIO'})+' vs '+(if($_.visitante){$_.visitante.nombre+'['+$_.visitante.iso+']'}else{'VACIO'})+' fin='+$_.finalizado) };" ^
  "Write-Host '=== Abriendo becbuc-live.html ===' -ForegroundColor Cyan;" ^
  "Start-Process 'http://localhost:8000/static/becbuc-live.html'"

pause
