# Reglamentos de competición (PDF)

Carpeta única para los reglamentos oficiales de cada competición del sistema.

## Reglas

- **Vigencia: 2026 o posterior.** Solo se aceptan reglamentos cuya edición/temporada
  sea **>= 2026**. Un reglamento anterior a 2026 se considera desactualizado y NO debe
  cargarse. El año va en el nombre del archivo y debe verificarse antes de importar.
- **Convención de nombre:** `<codigo>_<AAAA>.pdf`
  (ej. `libertadores_2026.pdf`, `champions_2026.pdf`, `copa_mundo_2026.pdf`).
- **Un PDF por competición-edición.** Si hay reglamento propio, prevalece sobre el
  reglamento por defecto (Copa del Mundo, engine `copa_mundo_2026`).
- Torneo SIN reglamento propio -> usa por defecto el del Mundial + AVISO ADMIN
  (ver scoring/registry.py) para que se suba el correspondiente.

## Fuentes oficiales (a descargar manualmente / desde la PC)

| codigo            | competición              | fuente oficial              | año min | estado    |
|-------------------|--------------------------|-----------------------------|---------|-----------|
| copa_mundo_2026   | Copa Mundial FIFA        | FIFA (publications.fifa.com)| 2026    | ✅ ya está (documentacion/20260608_...Reglamento_BEC_BUC_2026.pdf) |
| eurocopa          | UEFA Eurocopa            | UEFA.com                    | 2028    | pendiente |
| copa_america      | Copa América             | CONMEBOL.com                | 2028    | pendiente |
| champions         | UEFA Champions League    | UEFA.com                    | 2026    | pendiente |
| libertadores      | Copa Libertadores        | CONMEBOL.com                | 2026    | pendiente |
| sudamericana      | Copa Sudamericana        | CONMEBOL.com                | 2026    | pendiente |

## Verificación del año (2026+)

Antes de importar un PDF, validar que la edición sea >= 2026 (por el año del nombre
o el metadato del documento). Pseudochequeo:

    anio = int(nombre_archivo.split("_")[-1].split(".")[0])
    assert anio >= 2026, "Reglamento anterior a 2026: rechazar"

## Pendiente (bloqueado ahora)

La descarga automática de los PDFs oficiales no se pudo hacer en esta sesión
(bash caído + restricciones de fetch de binarios). Opciones:
1. Descargarlos a mano desde las fuentes de arriba y dejarlos en esta carpeta con
   el nombre de la convención.
2. Cuando vuelva bash: script que baje cada PDF, verifique año >= 2026 y lo copie acá.
