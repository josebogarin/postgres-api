@echo off
echo === Resultados reales vs predicciones NUEVAS de cherem (10 partidos corregidos) === > "C:\proyecto FAST API\real_scores.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "
SELECT
    p.numero_fifa,
    eq_l.nombre_es AS local,
    p.goles_local AS real_l,
    p.goles_visitante AS real_v,
    eq_v.nombre_es AS visitante,
    a.pred_local AS pred_l,
    a.pred_visitante AS pred_v,
    CASE
        WHEN p.goles_local IS NULL THEN 'sin resultado'
        WHEN a.pred_local = p.goles_local AND a.pred_visitante = p.goles_visitante THEN 'EXACTO'
        WHEN (a.pred_local > a.pred_visitante AND p.goles_local > p.goles_visitante)
          OR (a.pred_local < a.pred_visitante AND p.goles_local < p.goles_visitante)
          OR (a.pred_local = a.pred_visitante AND p.goles_local = p.goles_visitante) THEN 'resultado'
        ELSE 'fallo'
    END AS resultado,
    COALESCE(pd.pts_resultado,0) AS H_actual,
    COALESCE(pd.pts_marcador,0) AS I_actual
FROM apuesta a
JOIN partido p ON p.id = a.partido_id
JOIN equipo eq_l ON eq_l.id = p.equipo_local_id
JOIN equipo eq_v ON eq_v.id = p.equipo_visitante_id
LEFT JOIN puntaje_detalle pd ON pd.partido_id = p.id AND pd.apostador_id = a.apostador_id
WHERE a.apostador_id = 15
  AND p.numero_fifa IN (37,38,49,50,55,56,61,62,65,66)
ORDER BY p.numero_fifa;
" >> "C:\proyecto FAST API\real_scores.txt" 2>&1

echo. >> "C:\proyecto FAST API\real_scores.txt"
echo === Puntaje ESPERADO vs ACTUAL (segun resultado real) === >> "C:\proyecto FAST API\real_scores.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "
SELECT
    p.numero_fifa,
    p.goles_local AS real_l, p.goles_visitante AS real_v,
    a.pred_local AS pred_l, a.pred_visitante AS pred_v,
    COALESCE(pd.pts_resultado,0) AS H_actual,
    COALESCE(pd.pts_marcador,0) AS I_actual,
    CASE WHEN p.goles_local IS NOT NULL AND a.pred_local = p.goles_local AND a.pred_visitante = p.goles_visitante THEN 8 ELSE 0 END AS I_nuevo,
    CASE
        WHEN p.goles_local IS NULL THEN 0
        WHEN (a.pred_local > a.pred_visitante AND p.goles_local > p.goles_visitante)
          OR (a.pred_local < a.pred_visitante AND p.goles_local < p.goles_visitante)
          OR (a.pred_local = a.pred_visitante AND p.goles_local = p.goles_visitante) THEN 4
        ELSE 0
    END AS H_nuevo
FROM apuesta a
JOIN partido p ON p.id = a.partido_id
LEFT JOIN puntaje_detalle pd ON pd.partido_id = p.id AND pd.apostador_id = a.apostador_id
WHERE a.apostador_id = 15
  AND p.numero_fifa IN (37,38,49,50,55,56,61,62,65,66)
ORDER BY p.numero_fifa;
" >> "C:\proyecto FAST API\real_scores.txt" 2>&1

type "C:\proyecto FAST API\real_scores.txt"
pause
