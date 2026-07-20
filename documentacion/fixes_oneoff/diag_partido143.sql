-- Diagnóstico apuestas partido 143 (Mexico vs Sudafrica)
SELECT
    a.id,
    a.apostador_id,
    a.pred_local,
    a.pred_visitante,
    a.pred_amarillas,
    a.pred_rojas,
    a.puntos,
    pd.pts_resultado,
    pd.pts_marcador,
    pd.pts_total
FROM apuesta a
LEFT JOIN puntaje_detalle pd ON pd.partido_id = a.partido_id AND pd.apostador_id = a.apostador_id
WHERE a.partido_id = 143
ORDER BY a.apostador_id;
