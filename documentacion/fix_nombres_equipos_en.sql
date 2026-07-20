-- fix_nombres_equipos_en.sql
-- Actualiza nombres de equipos de español/mayúsculas a inglés estándar
-- Preserva el nombre español en nombre_es si estaba vacío

-- ALEMANIA
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Germany'
WHERE nombre IN ('ALEMANIA', 'Alemania');

-- COSTA DE MARFIL
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Ivory Coast'
WHERE nombre IN ('COSTA DE MARFIL', 'Costa de Marfil');

-- BOSNIA Y HERZEGOVINA
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Bosnia & Herzegovina'
WHERE nombre IN ('BOSNIA Y HERZEGOVINA', 'Bosnia y Herzegovina');

-- COREA DEL SUR
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'South Korea'
WHERE nombre IN ('COREA DEL SUR', 'Corea del Sur');

-- INGLATERRA
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'England'
WHERE nombre IN ('INGLATERRA', 'Inglaterra');

-- PAISES BAJOS
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Netherlands'
WHERE nombre IN ('PAISES BAJOS', 'Países Bajos', 'Paises Bajos');

-- ESTADOS UNIDOS
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'United States'
WHERE nombre IN ('ESTADOS UNIDOS', 'Estados Unidos');

-- SUIZA
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Switzerland'
WHERE nombre IN ('SUIZA', 'Suiza');

-- BELGICA
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Belgium'
WHERE nombre IN ('BELGICA', 'Bélgica', 'Belgica');

-- ESPANA
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Spain'
WHERE nombre IN ('ESPANA', 'España', 'Espana');

-- BRASIL
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Brazil'
WHERE nombre IN ('BRASIL', 'Brasil');

-- FRANCIA
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'France'
WHERE nombre IN ('FRANCIA', 'Francia');

-- JAPON
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Japan'
WHERE nombre IN ('JAPON', 'Japón', 'Japon');

-- NORUEGA
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Norway'
WHERE nombre IN ('NORUEGA', 'Noruega');

-- SUECIA
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Sweden'
WHERE nombre IN ('SUECIA', 'Suecia');

-- SUDAFRICA
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'South Africa'
WHERE nombre IN ('SUDAFRICA', 'Sudáfrica', 'Sudafrica');

-- ARGELIA
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Algeria'
WHERE nombre IN ('ARGELIA', 'Argelia');

-- MARRUECOS
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Morocco'
WHERE nombre IN ('MARRUECOS', 'Marruecos');

-- EGIPTO
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Egypt'
WHERE nombre IN ('EGIPTO', 'Egipto');

-- CROACIA
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Croatia'
WHERE nombre IN ('CROACIA', 'Croacia');

-- TURQUIA
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Turkey'
WHERE nombre IN ('TURQUIA', 'Turquía', 'Turquia');

-- REPUBLICA DEMOCRATICA DEL CONGO
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Congo DR'
WHERE nombre IN ('REPUBLICA DEMOCRATICA DEL CONGO', 'República Democrática del Congo', 'Congo DR');

-- CABO VERDE
UPDATE equipo SET nombre_es = COALESCE(NULLIF(nombre_es,''), nombre), nombre = 'Cape Verde Islands'
WHERE nombre IN ('CABO VERDE', 'Cabo Verde', 'Cape Verde');

-- Verificar resultado
SELECT id, nombre, nombre_es FROM equipo ORDER BY nombre;
