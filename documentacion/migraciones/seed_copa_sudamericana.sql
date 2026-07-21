-- Seed: Copa Sudamericana (CONMEBOL, clubes) - faltaba en el seed original.
-- api_league_id 11 = CONMEBOL Sudamericana en API-Football (CONFIRMAR antes de sincronizar).
-- clubes -> formato ida_vuelta, SIN partido por el 3er puesto (de semis directo a la final).
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\migraciones\seed_copa_sudamericana.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

INSERT INTO competicion (nombre, nombre_corto, tipo, formato_playoff, api_league_id, emoji)
VALUES ('Copa Sudamericana', 'Sudamericana', 'clubes', 'ida_vuelta', 11, '🥈')
ON CONFLICT (api_league_id) DO NOTHING;
