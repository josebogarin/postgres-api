SELECT
    COUNT(*)                                          AS total_apuestas,
    SUM(CASE WHEN p.estado='finalizado' THEN 1 END)  AS finalizados,
    SUM(CASE WHEN COALESCE(p.rojas,0)=0 THEN 1 END)  AS partidos_0_rojas_real,
    SUM(CASE WHEN COALESCE(a.pred_rojas,0)=0 THEN 1 END) AS apuestas_0_rojas_pred,
    SUM(CASE WHEN COALESCE(p.rojas,0)=0
          AND p.estado='finalizado' THEN 1 END)       AS deberia_puntuar_k,
    SUM(COALESCE(d.pts_rojas,0))                      AS pts_k_actual,
    COUNT(d.pts_rojas)                                AS filas_puntaje_detalle
FROM apuesta a
JOIN partido p ON p.id = a.partido_id
LEFT JOIN puntaje_detalle d ON d.partido_id = a.partido_id AND d.apostador_id = a.apostador_id
WHERE a.nombre_apostador ILIKE '%quiroga%';
