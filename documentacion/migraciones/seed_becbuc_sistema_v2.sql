-- ============================================================
-- Seed: registrar sistema BECBUC en app_db (v3)
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\seed_becbuc_sistema_v2.sql" | docker exec -i core-postgres psql -U app_user -d app_db
-- ============================================================

DO $$
DECLARE
    v_id bigint;
    v_seq text;
BEGIN
    -- Si ya existe, solo asignar a superadmins
    SELECT id INTO v_id FROM sistema WHERE nombre = 'BECBUC';

    IF v_id IS NULL THEN
        -- Obtener nombre de la secuencia del PK
        SELECT pg_get_serial_sequence('sistema', 'id') INTO v_seq;

        -- Reservar el proximo id
        v_id := nextval(v_seq);

        -- Insertar con id e id_sistema juntos para satisfacer NOT NULL
        EXECUTE format(
            'INSERT INTO sistema (id, id_sistema, nombre, descripcion, host_bd, puerto_bd, nombre_bd, usuario_bd, %I, es_activo)
             VALUES ($1, $1, $2, $3, $4, $5, $6, $7, $8, $9)',
            U&'contrase\00F1a_bd'
        ) USING
            v_id,
            'BECBUC',
            'Sistema de torneos, fixture y apuestas deportivas',
            'localhost',
            5432::integer,
            'becbuc',
            'app_user',
            'superpassword',
            true;

        RAISE NOTICE 'Sistema BECBUC creado (id=%)', v_id;
    ELSE
        RAISE NOTICE 'Sistema BECBUC ya existia (id=%)', v_id;
    END IF;

    -- Asignar a todos los superadmin
    INSERT INTO user_sistemas (user_id, sistema_id)
    SELECT u.id, v_id
    FROM users u
    JOIN user_roles ur ON ur.user_id = u.id
    JOIN roles r ON r.id = ur.role_id AND r.name = 'superadmin'
    ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Listo.';
END $$;
