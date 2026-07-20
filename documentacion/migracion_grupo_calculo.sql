-- ============================================================
-- Migración: agregar campos grupo y calculo a diccionario
-- grupo   : integer DEFAULT 0  (0=sin agrupar, 1=nivel1, 2=nivel2, …)
-- calculo : varchar(50) NULL   ('suma','conteo','promedio' o NULL)
-- ============================================================

ALTER TABLE diccionario
  ADD COLUMN IF NOT EXISTS grupo   integer      NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS calculo varchar(50)  NULL;

COMMENT ON COLUMN diccionario.grupo   IS '0 = sin agrupar; 1,2,3…N = nivel de agrupación anidada (orden ascendente)';
COMMENT ON COLUMN diccionario.calculo IS 'Cálculo a mostrar en el grupo: suma | conteo | promedio | NULL';
