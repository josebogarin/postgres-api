Get-Content "C:\proyecto FAST API\verify_cherem.sql" | docker exec -i core-postgres psql -U app_user -d becbuc | Tee-Object "C:\proyecto FAST API\verify_cherem_out.txt"
Write-Host "`nResultado guardado en verify_cherem_out.txt"
Read-Host "Presiona Enter para salir"
