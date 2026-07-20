# Continuación — 2 de junio de 2026

## Estado del sistema al cerrar sesión

El backend FastAPI corre en `http://localhost:8000`. Docker (`core-postgres`) debe estar levantado. Arrancar con:

```powershell
cd "C:\proyecto FAST API\backend"
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

Credenciales de desarrollo: `admin` / `faute`

---

## Lo que se hizo en la sesión de hoy

### 1. Configurador visual cabecera-detalle (`/config-cabecera`)
Reescritura completa de `config_cabecera.html` con layout de 3 paneles:
- **Panel A**: árbol de todas las tablas/vistas de la BD (draggable)
- **Panel B**: lista de cabeceras ya configuradas
- **Panel C**: zona de configuración con dos drop zones separadas — una para la cabecera, otra para los detalles

La FK se auto-detecta con convención `id_<cabecera>` y se puede sobreescribir con un select que carga las columnas reales de la tabla.

### 2. Fix columna `icono` inexistente en admin.py
Los endpoints de cabecera/detalle tiraban `column "icono" does not exist` porque la migración `migracion_icono_cabecera_detalle.sql` no se ejecutó. Se reemplazaron todos los referencias con `'' AS icono` como literal. La migración queda pendiente para cuando se quiera persistir iconos.

### 3. Reconstrucción de portal.html
El script de portal.html estaba truncado a mitad de la función `doLogin()`. Se reconstruyó el bloque JS completo (~650 líneas): funciones `api()`, `openTool()`, `showView()`, `openDoc()`, `loadVinculos()`, `loadLogs()`, y todo el sistema de roles.

### 4. Corrección de parámetros de portal endpoints
Los endpoints `/portal/kpis`, `/portal/vinculos` y `/portal/menu` esperan `sistema_id` (no `id_sistema`). Los menus dinámicos de Ventas DB no cargaban por este bug.

### 5. Manuales PDF en portal
- Creado `backend/static/docs/` con `Manual_Usuario_Lambda.pdf` y `Manual_Administrador_Lambda.pdf`
- Función `openDoc(key)` abre el PDF en nueva pestaña
- En el sidebar: "📘 Manual del Sistema" visible para admin y superadmin
- En el panel Herramientas: card "Manual del Administrador" (`id="toolManualAdmin"`) visible para admin+
- En "Accesos rápidos": ambos manuales aparecen por defecto al inicio de la lista, antes de los vínculos del sistema. "Manual del Administrador" se muestra/oculta según rol (igual que el resto de elementos de rol).

### 6. Sidebar — eliminado "Cab.–Detalle" de Herramientas
Causaba confusión porque duplicaba el acceso. El acceso a `/cabecera` se hace desde el árbol de tablas (las cabeceras tienen ícono distinto).

---

## Pendiente / próximas tareas sugeridas

### Prioridad alta
- **Migración `icono`**: ejecutar `migracion_icono_cabecera_detalle.sql` y restaurar el campo icono en admin.py para que el configurador pueda persistir íconos visuales por cabecera/detalle.
- **Probar config_cabecera.html** end-to-end: crear una cabecera nueva arrastrando tablas, verificar que `/cabecera` la muestre correctamente, probar edición y eliminación.

### Prioridad media
- **Manual de Usuario**: el archivo PDF existe pero es un placeholder. Habría que generar un `.docx` equivalente al del administrador con contenido real orientado al usuario final (navegación, tablas, búsquedas, exportar XLSX).
- **Regenerar PDFs** si se actualiza el contenido de los manuales:
  ```powershell
  python "C:\proyecto FAST API\backend\scripts\office\soffice.py" --headless --convert-to pdf "C:\proyecto FAST API\documentacion\Manual_Administrador_Lambda.docx" --outdir "C:\proyecto FAST API\backend\static\docs\"
  ```

### Prioridad baja
- **Portal KPIs**: los KPIs se configuran por sistema pero aún no hay visualización gráfica (solo números). Podría sumarse un mini-gráfico de línea con Chart.js.
- **Exportar desde cabecera_detalle.html**: la vista tabla tiene exportar XLSX; cabecera-detalle no.
- **Paginación en grilla cabecera**: actualmente `CAB_LIMIT=100` con "Cargar más…". Podría reemplazarse con paginación numerada.

---

## Archivos modificados en esta sesión

| Archivo | Cambio |
|---|---|
| `backend/static/config_cabecera.html` | Reescritura completa — 3 paneles, drag & drop |
| `backend/static/portal.html` | Script JS reconstruido; fix params portal endpoints; manuales en accesos rápidos y herramientas; visibilidad por rol actualizada |
| `backend/app/api/v1/endpoints/admin.py` | `icono` → `'' AS icono` en todos los SQL de cabecera/detalle |
| `backend/static/docs/` (nueva carpeta) | PDFs de manuales |
| `documentacion/Manual_Administrador_Lambda.docx` | Manual nuevo generado con docx-js |
| `CLAUDE.md` | Secciones nuevas: config_cabecera, manuales, accesos rápidos, visibilidad por rol, convención portal params, regla 26 |
