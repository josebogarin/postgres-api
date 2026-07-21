-- Reset LIMPIO del fixture de un torneo (borra fases/partidos/standings) para recargar.
-- Cambiar :TID por el id del torneo. Libertadores = 1 (verificar con SELECT id,nombre FROM torneo).
-- SOLO usar si el torneo NO tiene apuestas cargadas (verificar antes).
-- Ejecutar (ejemplo Libertadores id=1):
--   Get-Content "C:\proyecto FAST API\documentacion\migraciones\reset_fixture_torneo.sql" | docker exec -i core-postgres psql -U app_user -d becbuc -v TID=1

DELETE FROM puntaje_detalle WHERE partido_id IN (SELECT p.id FROM partido p JOIN fase f ON f.id=p.fase_id WHERE f.torneo_id=:TID);
DELETE FROM apuesta        WHERE partido_id IN (SELECT p.id FROM partido p JOIN fase f ON f.id=p.fase_id WHERE f.torneo_id=:TID);
DELETE FROM participacion  WHERE fase_id    IN (SELECT id FROM fase WHERE torneo_id=:TID);
DELETE FROM partido        WHERE fase_id    IN (SELECT id FROM fase WHERE torneo_id=:TID);
DELETE FROM fase           WHERE torneo_id=:TID;
UPDATE torneo SET datos_cargados=FALSE WHERE id=:TID;

SELECT :TID AS torneo_reseteado,
       (SELECT count(*) FROM fase WHERE torneo_id=:TID) AS fases_restantes,
       (SELECT count(*) FROM partido p JOIN fase f ON f.id=p.fase_id WHERE f.torneo_id=:TID) AS partidos_restantes;
