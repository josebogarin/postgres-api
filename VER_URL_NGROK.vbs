Dim oShell, oExec, sOut, sUrl
Set oShell = CreateObject("WScript.Shell")

' Query ngrok API
Set oExec = oShell.Exec("cmd /c curl -s http://localhost:4040/api/tunnels")
sOut = oExec.StdOut.ReadAll()

' Try to extract the public_url
Dim re
Set re = New RegExp
re.Pattern = """public_url"":""(https://[^""]+)"""
re.IgnoreCase = True

Dim m
Set m = re.Execute(sOut)

If m.Count > 0 Then
    sUrl = m(0).SubMatches(0)
    MsgBox "URL ngrok actual:" & vbCrLf & vbCrLf & sUrl & "/static/becbuc-live.html" & vbCrLf & vbCrLf & "Copia esta URL a tu celular.", vbInformation, "BECBUC - URL ngrok"
Else
    MsgBox "ngrok no esta corriendo o no responde." & vbCrLf & vbCrLf & "Respuesta recibida:" & vbCrLf & Left(sOut, 500), vbExclamation, "BECBUC - URL ngrok"
End If

Set oShell = Nothing
