Dim oShell
Set oShell = CreateObject("WScript.Shell")
oShell.Run "cmd /k ""C:\proyecto FAST API\INICIAR_UVICORN.bat""", 1, False
Set oShell = Nothing
