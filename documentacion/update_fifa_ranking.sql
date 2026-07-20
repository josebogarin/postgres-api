-- update_fifa_ranking.sql
-- Ranking FIFA oficial junio 2026 (previo al Mundial)
-- Fuente: ESPN / FIFA - 11 junio 2026
-- Ejecutar: Get-Content "C:\proyecto FAST API\documentacion\update_fifa_ranking.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

UPDATE equipo SET fifa_ranking =  1 WHERE nombre ILIKE '%argentina%'      OR nombre_es ILIKE '%argentina%';
UPDATE equipo SET fifa_ranking =  2 WHERE nombre ILIKE '%spain%'           OR nombre_es ILIKE '%espa%';
UPDATE equipo SET fifa_ranking =  3 WHERE nombre ILIKE '%france%'          OR nombre_es ILIKE '%fran%';
UPDATE equipo SET fifa_ranking =  4 WHERE nombre ILIKE '%england%'         OR nombre_es ILIKE '%inglat%';
UPDATE equipo SET fifa_ranking =  5 WHERE nombre ILIKE '%portugal%'        OR nombre_es ILIKE '%portugal%';
UPDATE equipo SET fifa_ranking =  6 WHERE nombre ILIKE '%brazil%'          OR nombre_es ILIKE '%brasil%';
UPDATE equipo SET fifa_ranking =  7 WHERE nombre ILIKE '%morocco%'         OR nombre_es ILIKE '%marruecos%';
UPDATE equipo SET fifa_ranking =  8 WHERE nombre ILIKE '%netherlands%'     OR nombre_es ILIKE '%pa%ses bajos%' OR nombre_es ILIKE '%holanda%';
UPDATE equipo SET fifa_ranking =  9 WHERE nombre ILIKE '%belgium%'         OR nombre_es ILIKE '%b%lgica%';
UPDATE equipo SET fifa_ranking = 10 WHERE nombre ILIKE '%germany%'         OR nombre_es ILIKE '%alemania%';
UPDATE equipo SET fifa_ranking = 11 WHERE nombre ILIKE '%croatia%'         OR nombre_es ILIKE '%croacia%';
UPDATE equipo SET fifa_ranking = 12 WHERE nombre ILIKE '%italy%'           OR nombre_es ILIKE '%italia%';
UPDATE equipo SET fifa_ranking = 13 WHERE nombre ILIKE '%colombia%'        OR nombre_es ILIKE '%colombia%';
UPDATE equipo SET fifa_ranking = 14 WHERE nombre ILIKE '%mexico%'          OR nombre_es ILIKE '%m%xico%';
UPDATE equipo SET fifa_ranking = 15 WHERE nombre ILIKE '%senegal%'         OR nombre_es ILIKE '%senegal%';
UPDATE equipo SET fifa_ranking = 16 WHERE nombre ILIKE '%uruguay%'         OR nombre_es ILIKE '%uruguay%';
UPDATE equipo SET fifa_ranking = 17 WHERE nombre ILIKE '%united states%'   OR nombre ILIKE '%usa%' OR nombre_es ILIKE '%estados unidos%';
UPDATE equipo SET fifa_ranking = 18 WHERE nombre ILIKE '%japan%'           OR nombre_es ILIKE '%jap%n%';
UPDATE equipo SET fifa_ranking = 19 WHERE nombre ILIKE '%switzerland%'     OR nombre_es ILIKE '%suiza%';
UPDATE equipo SET fifa_ranking = 20 WHERE nombre ILIKE '%iran%'            OR nombre_es ILIKE '%ir%n%';
UPDATE equipo SET fifa_ranking = 21 WHERE nombre ILIKE '%denmark%'         OR nombre_es ILIKE '%dinamarca%';
UPDATE equipo SET fifa_ranking = 22 WHERE nombre ILIKE '%t%rkiye%'        OR nombre ILIKE '%turkey%' OR nombre_es ILIKE '%turqu%a%';
UPDATE equipo SET fifa_ranking = 23 WHERE nombre ILIKE '%ecuador%'         OR nombre_es ILIKE '%ecuador%';
UPDATE equipo SET fifa_ranking = 24 WHERE nombre ILIKE '%austria%'         OR nombre_es ILIKE '%austria%';
UPDATE equipo SET fifa_ranking = 25 WHERE nombre ILIKE '%south korea%'     OR nombre ILIKE '%korea republic%' OR nombre_es ILIKE '%corea del sur%';
UPDATE equipo SET fifa_ranking = 26 WHERE nombre ILIKE '%nigeria%'         OR nombre_es ILIKE '%nigeria%';
UPDATE equipo SET fifa_ranking = 27 WHERE nombre ILIKE '%australia%'       OR nombre_es ILIKE '%australia%';
UPDATE equipo SET fifa_ranking = 28 WHERE nombre ILIKE '%algeria%'         OR nombre_es ILIKE '%argelia%';
UPDATE equipo SET fifa_ranking = 29 WHERE nombre ILIKE '%egypt%'           OR nombre_es ILIKE '%egipto%';
UPDATE equipo SET fifa_ranking = 30 WHERE nombre ILIKE '%canada%'          OR nombre_es ILIKE '%canad%';
UPDATE equipo SET fifa_ranking = 31 WHERE nombre ILIKE '%norway%'          OR nombre_es ILIKE '%noruega%';
UPDATE equipo SET fifa_ranking = 32 WHERE nombre ILIKE '%ukraine%'         OR nombre_es ILIKE '%ucrania%';
UPDATE equipo SET fifa_ranking = 33 WHERE nombre ILIKE '%ivory coast%'     OR nombre ILIKE '%cote d%ivoire%' OR nombre_es ILIKE '%costa de marfil%' OR nombre_es ILIKE '%c%te d%ivoire%';
UPDATE equipo SET fifa_ranking = 34 WHERE nombre ILIKE '%panama%'          OR nombre_es ILIKE '%panam%';
UPDATE equipo SET fifa_ranking = 35 WHERE nombre ILIKE '%russia%'          OR nombre_es ILIKE '%rusia%';
UPDATE equipo SET fifa_ranking = 36 WHERE nombre ILIKE '%poland%'          OR nombre_es ILIKE '%polonia%';
UPDATE equipo SET fifa_ranking = 37 WHERE nombre ILIKE '%wales%'           OR nombre_es ILIKE '%gales%';
UPDATE equipo SET fifa_ranking = 38 WHERE nombre ILIKE '%sweden%'          OR nombre_es ILIKE '%suecia%';
UPDATE equipo SET fifa_ranking = 39 WHERE nombre ILIKE '%hungary%'         OR nombre_es ILIKE '%hungr%a%';
UPDATE equipo SET fifa_ranking = 40 WHERE nombre ILIKE '%czech%'           OR nombre_es ILIKE '%rep%blica checa%' OR nombre_es ILIKE '%chequia%';
UPDATE equipo SET fifa_ranking = 41 WHERE nombre ILIKE '%paraguay%'        OR nombre_es ILIKE '%paraguay%';
UPDATE equipo SET fifa_ranking = 42 WHERE nombre ILIKE '%scotland%'        OR nombre_es ILIKE '%escocia%';
UPDATE equipo SET fifa_ranking = 43 WHERE nombre ILIKE '%serbia%'          OR nombre_es ILIKE '%serbia%';
UPDATE equipo SET fifa_ranking = 44 WHERE nombre ILIKE '%cameroon%'        OR nombre_es ILIKE '%camer%n%';
UPDATE equipo SET fifa_ranking = 45 WHERE nombre ILIKE '%tunisia%'         OR nombre_es ILIKE '%t%nez%';
UPDATE equipo SET fifa_ranking = 46 WHERE nombre ILIKE '%congo dr%'        OR nombre ILIKE '%congo dem%' OR nombre ILIKE '%democratic republic%congo%' OR nombre_es ILIKE '%congo%';
UPDATE equipo SET fifa_ranking = 47 WHERE nombre ILIKE '%slovakia%'        OR nombre_es ILIKE '%eslovaquia%';
UPDATE equipo SET fifa_ranking = 48 WHERE nombre ILIKE '%greece%'          OR nombre_es ILIKE '%grecia%';
UPDATE equipo SET fifa_ranking = 49 WHERE nombre ILIKE '%venezuela%'       OR nombre_es ILIKE '%venezuela%';
UPDATE equipo SET fifa_ranking = 50 WHERE nombre ILIKE '%uzbekistan%'      OR nombre_es ILIKE '%uzbekist%n%';
-- Fuera del top 50 pero en el Mundial:
UPDATE equipo SET fifa_ranking = 56 WHERE nombre ILIKE '%qatar%'           OR nombre_es ILIKE '%qatar%';
UPDATE equipo SET fifa_ranking = 57 WHERE nombre ILIKE '%iraq%'            OR nombre_es ILIKE '%irak%' OR nombre_es ILIKE '%iraq%';
UPDATE equipo SET fifa_ranking = 60 WHERE nombre ILIKE '%south africa%'    OR nombre_es ILIKE '%sud%frica%';
UPDATE equipo SET fifa_ranking = 61 WHERE nombre ILIKE '%saudi arabia%'    OR nombre_es ILIKE '%arabia saudita%' OR nombre_es ILIKE '%arabia saud%';
UPDATE equipo SET fifa_ranking = 63 WHERE nombre ILIKE '%jordan%'          OR nombre_es ILIKE '%jordania%';
UPDATE equipo SET fifa_ranking = 64 WHERE nombre ILIKE '%bosnia%'          OR nombre_es ILIKE '%bosnia%';
UPDATE equipo SET fifa_ranking = 67 WHERE nombre ILIKE '%cape verde%'      OR nombre_es ILIKE '%cabo verde%';
UPDATE equipo SET fifa_ranking = 73 WHERE nombre ILIKE '%ghana%'           OR nombre_es ILIKE '%ghana%';
UPDATE equipo SET fifa_ranking = 82 WHERE nombre ILIKE '%cura%ao%'         OR nombre_es ILIKE '%curazao%' OR nombre_es ILIKE '%curac%';
UPDATE equipo SET fifa_ranking = 83 WHERE nombre ILIKE '%haiti%'           OR nombre_es ILIKE '%hait%';
UPDATE equipo SET fifa_ranking = 85 WHERE nombre ILIKE '%new zealand%'     OR nombre_es ILIKE '%nueva zelanda%';

-- Verificacion: mostrar ranking actualizado
SELECT fifa_ranking, nombre, nombre_es
FROM equipo
WHERE fifa_ranking IS NOT NULL
ORDER BY fifa_ranking;

-- Equipos sin ranking (si quedaron):
SELECT nombre, nombre_es
FROM equipo
WHERE fifa_ranking IS NULL
ORDER BY nombre;
