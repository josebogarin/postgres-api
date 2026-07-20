Dim oShell
Set oShell = CreateObject("WScript.Shell")

' Matar uvicorn anterior si existe
oShell.Run "cmd /c taskkill /F /IM uvicorn.exe /T 2>nul", 0, True
oShell.Run "cmd /c timeout /t 2 /nobreak", 0, True

' Iniciar uvicorn en una ventana visible
oShell.Run "cmd /k ""cd /d ""C:\proyecto FAST API\backend"" && call .venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000""", 1, False

' Esperar 10 segundos a que arranque
oShell.Run "cmd /c timeout /t 10 /nobreak", 0, True

' Abrir Edge con becbuc-live
oShell.Run "cmd /c start microsoft-edge:http://localhost:8000/static/becbuc-live.html", 0, False

Set oShell = Nothing
