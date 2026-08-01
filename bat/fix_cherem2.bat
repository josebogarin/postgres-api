@echo off
echo Corrigiendo apuestas cherem... > "%~dp0..\fix_cherem_result.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "UPDATE apuesta SET pred_local=1,pred_visitante=0 WHERE apostador_id=15 AND partido_id=(SELECT id FROM partido WHERE numero_fifa=37);" >> "%~dp0..\fix_cherem_result.txt" 2>&1
docker exec core-postgres psql -U app_user -d becbuc -c "UPDATE apuesta SET pred_local=2,pred_visitante=0 WHERE apostador_id=15 AND partido_id=(SELECT id FROM partido WHERE numero_fifa=38);" >> "%~dp0..\fix_cherem_result.txt" 2>&1
docker exec core-postgres psql -U app_user -d becbuc -c "UPDATE apuesta SET pred_local=2,pred_visitante=2 WHERE apostador_id=15 AND partido_id=(SELECT id FROM partido WHERE numero_fifa=49);" >> "%~dp0..\fix_cherem_result.txt" 2>&1
docker exec core-postgres psql -U app_user -d becbuc -c "UPDATE apuesta SET pred_local=3,pred_visitante=1 WHERE apostador_id=15 AND partido_id=(SELECT id FROM partido WHERE numero_fifa=50);" >> "%~dp0..\fix_cherem_result.txt" 2>&1
docker exec core-postgres psql -U app_user -d becbuc -c "UPDATE apuesta SET pred_local=1,pred_visitante=2 WHERE apostador_id=15 AND partido_id=(SELECT id FROM partido WHERE numero_fifa=55);" >> "%~dp0..\fix_cherem_result.txt" 2>&1
docker exec core-postgres psql -U app_user -d becbuc -c "UPDATE apuesta SET pred_local=1,pred_visitante=1 WHERE apostador_id=15 AND partido_id=(SELECT id FROM partido WHERE numero_fifa=56);" >> "%~dp0..\fix_cherem_result.txt" 2>&1
docker exec core-postgres psql -U app_user -d becbuc -c "UPDATE apuesta SET pred_local=2,pred_visitante=3 WHERE apostador_id=15 AND partido_id=(SELECT id FROM partido WHERE numero_fifa=61);" >> "%~dp0..\fix_cherem_result.txt" 2>&1
docker exec core-postgres psql -U app_user -d becbuc -c "UPDATE apuesta SET pred_local=0,pred_visitante=2 WHERE apostador_id=15 AND partido_id=(SELECT id FROM partido WHERE numero_fifa=62);" >> "%~dp0..\fix_cherem_result.txt" 2>&1
docker exec core-postgres psql -U app_user -d becbuc -c "UPDATE apuesta SET pred_local=0,pred_visitante=3 WHERE apostador_id=15 AND partido_id=(SELECT id FROM partido WHERE numero_fifa=65);" >> "%~dp0..\fix_cherem_result.txt" 2>&1
docker exec core-postgres psql -U app_user -d becbuc -c "UPDATE apuesta SET pred_local=2,pred_visitante=3 WHERE apostador_id=15 AND partido_id=(SELECT id FROM partido WHERE numero_fifa=66);" >> "%~dp0..\fix_cherem_result.txt" 2>&1
echo. >> "%~dp0..\fix_cherem_result.txt"
echo Verificacion: >> "%~dp0..\fix_cherem_result.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT p.numero_fifa, a.pred_local, a.pred_visitante FROM apuesta a JOIN partido p ON p.id=a.partido_id WHERE a.apostador_id=15 AND p.numero_fifa IN (37,38,49,50,55,56,61,62,65,66) ORDER BY p.numero_fifa;" >> "%~dp0..\fix_cherem_result.txt" 2>&1
type "%~dp0..\fix_cherem_result.txt"
pause
