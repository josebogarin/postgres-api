-- Script de inicializacion - crea las BDs si no existen
-- Se ejecuta automaticamente al crear el contenedor por primera vez

SELECT 'CREATE DATABASE becbuc'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'becbuc')\gexec

SELECT 'CREATE DATABASE app_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'app_db')\gexec
