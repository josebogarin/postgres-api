Dim oShell
Set oShell = CreateObject("WScript.Shell")
oShell.Run "cmd /c start microsoft-edge:http://localhost:8000/static/becbuc-live.html", 0, False
Set oShell = Nothing
