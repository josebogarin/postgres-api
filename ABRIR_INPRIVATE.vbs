Dim oShell
Set oShell = CreateObject("WScript.Shell")
oShell.Run "cmd /c start msedge --inprivate http://localhost:8000/static/becbuc-live.html", 0, False
Set oShell = Nothing
