---
name: becbuc-ui-sync
description: "Regla del proyecto BECBUC: cualquier cambio de interfaz debe aplicarse SIEMPRE en paralelo a la web y al móvil. Usar cuando se agregue, modifique o elimine una vista, sección, botón, dato mostrado o flujo de UI en el portal de apuestas BECBUC."
---

# BECBUC — Interfaces web y móvil en paralelo

En el proyecto BECBUC existen DOS interfaces de usuario que deben mantenerse
funcionalmente equivalentes. Cada vez que se toca una, hay que tocar la otra en
el mismo cambio.

## Archivos

- Web (escritorio): `C:\proyecto FAST API\backend\static\BECBUC-portal.html`
- Móvil (celular):  `C:\proyecto FAST API\backend\static\BECBUC-movil.html`

El backend decide cuál servir según el user-agent (`/` redirige a
`/static/BECBUC-movil.html` en móvil o a `/BECBUC-portal` en escritorio — ver
`backend/app/main.py`, función `_es_movil`).

## Regla obligatoria

Ante CUALQUIER cambio de interfaz (nueva vista, sección, botón, columna, dato
mostrado, endpoint consumido, texto, lógica de render o flujo), aplicar el
cambio en AMBOS archivos en la misma tarea. No se considera terminado un cambio
de UI si quedó en una sola interfaz.

Pasos:

1. Implementar el cambio en `BECBUC-portal.html` (web).
2. Implementar el equivalente en `BECBUC-movil.html` (móvil), adaptando el
   layout a pantalla angosta (~380px): tarjetas apiladas en vez de tablas
   anchas, menús colapsables, fuentes y paddings reducidos. La FUNCIONALIDAD y
   los DATOS mostrados deben ser los mismos; solo cambia la disposición.
3. Verificar que ambas consumen los mismos endpoints y muestran los mismos
   campos.
4. Probar las dos en el navegador (login + render) antes de dar por cerrado.

## Convenciones de paridad

- Mismas vistas/secciones lógicas en ambas (dashboard, pronósticos, grupos,
  bracket/resultados, ranking, transparencia por fase, mensajes, etc.).
- Mismos nombres de endpoints `/api/v1/bets/*`.
- Mismo sistema de puntuación y doblaje por fase reflejado en ambas.
- Si una interfaz gana una funcionalidad nueva, crear un ítem de paridad
  pendiente para la otra y resolverlo en la misma sesión.

## Checklist rápido antes de cerrar un cambio de UI

- [ ] ¿El cambio está en BECBUC-portal.html?
- [ ] ¿El equivalente está en BECBUC-movil.html?
- [ ] ¿Ambas usan los mismos endpoints/campos?
- [ ] ¿Probé login + render en navegador en las dos?

## Instalación como skill de Claude (opcional)

Para que Claude lo cargue automáticamente, copiar la carpeta `becbuc-ui-sync`
(con este `SKILL.md`) al directorio de skills de Claude del equipo.
