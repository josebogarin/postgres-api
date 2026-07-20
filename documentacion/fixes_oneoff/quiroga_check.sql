SELECT
    COALESCE(SUM(pts_resultado),0)       AS H,
    COALESCE(SUM(pts_marcador),0)        AS I,
    COALESCE(SUM(pts_amarillas),0)       AS J,
    COALESCE(SUM(pts_rojas),0)           AS K,
    COALESCE(SUM(pts_var),0)             AS L,
    COALESCE(SUM(pts_penales_partido),0) AS M,
    COALESCE(SUM(pts_minuto),0)          AS N,
    COALESCE(SUM(pts_penales_tanda),0)   AS O,
    COALESCE(SUM(
        pts_resultado+pts_marcador+pts_amarillas+pts_rojas+
        pts_var+pts_penales_partido+pts_minuto+pts_penales_tanda+pts_equipo
    ),0) AS TOTAL
FROM puntaje_detalle d
JOIN apuesta a ON a.partido_id=d.partido_id AND a.apostador_id=d.apostador_id
WHERE a.nombre_apostador ILIKE '%quiroga%';
