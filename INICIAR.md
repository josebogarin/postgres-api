# 🚀 Cómo Iniciar la Plataforma

## Opción 1: Una Sola Línea (RECOMENDADO)

### En PowerShell (Recomendado)

```powershell
cd "C:\proyecto FAST API"
.\iniciar-todo-simple.ps1
```

### En CMD / Explorador (Más Fácil)

**Opción A:** Haz doble click en:
```
C:\proyecto FAST API\iniciar-todo.bat
```

**Opción B:** En CMD:
```cmd
cd C:\proyecto FAST API
iniciar-todo.bat
```

---

## ¿Qué hace cada script?

### `iniciar-todo-simple.ps1` (RECOMENDADO)
✅ Rápido y simple  
✅ Abre 2 nuevas ventanas (Backend + Frontend)  
✅ Abre automáticamente los navegadores  
⏱️ Tarda ~5 segundos en iniciar todo  

### `iniciar-todo.bat`
✅ No requiere PowerShell  
✅ Ideal para hacer doble click  
✅ Abre 2 nuevas ventanas  
⏱️ Tarda ~5 segundos en iniciar todo  

### `iniciar-todo.ps1` (Completo)
ℹ️ Versión con más información  
ℹ️ Muestra PIDs de procesos  
ℹ️ Mejor para debugging  

---

## 📍 Accesos Después de Iniciar

| Componente | URL | Descripción |
|-----------|-----|------------|
| **Frontend Web** | http://localhost:5000 | Dashboard con login |
| **API Swagger** | http://localhost:8000/docs | Documentación interactiva |
| **API ReDoc** | http://localhost:8000/redoc | Documentación alternativa |
| **API Base** | http://localhost:8000/api/v1 | Endpoints REST |

---

## 👤 Credenciales de Acceso

```
Email:    admin@example.com
Password: changeme123
```

---

## ⏹️ Cómo Detener Todo

### Opción 1: Cerrar las ventanas
Simplemente cierra ambas ventanas de PowerShell/CMD que se abrieron.

### Opción 2: PowerShell
```powershell
# Ver procesos
Get-Process | grep python
Get-Process | grep uvicorn

# Matar procesos
Stop-Process -Name "python" -Force
Stop-Process -Name "uvicorn" -Force
```

### Opción 3: Liberando puertos
```powershell
# Si algo no quiere cerrarse y necesitas los puertos
Get-NetTCPConnection -LocalPort 8000 | Stop-Process -Force
Get-NetTCPConnection -LocalPort 5000 | Stop-Process -Force
```

---

## 🛠️ Si Algo Falla

### Error: "File not found" o "Comando no reconocido"

**En PowerShell:**
```powershell
# Permite ejecutar scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Error: "Puerto en uso (8000 o 5000)"

Algo ya está usando esos puertos:
```powershell
# Encuentra qué está usando el puerto
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
tasklist | findstr <PID>

# O simplemente cierra y reinicia
```

### Error: "Module not found" o dependencias

El backend necesita sus dependencias:
```powershell
cd "C:\proyecto FAST API\backend"
pip install -r requirements.txt
```

El frontend necesita sus dependencias:
```powershell
cd "C:\proyecto FAST API\web"
pip install -r requirements.txt
```

---

## 📝 Alternativa Manual (Si los scripts no funcionan)

Abre **2 PowerShells** diferentes:

**Terminal 1 (Backend):**
```powershell
cd "C:\proyecto FAST API\backend"
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```powershell
cd "C:\proyecto FAST API\web"
python app.py
```

Luego accede a:
- Frontend: http://localhost:5000
- API: http://localhost:8000/docs

---

## 🔧 Setup Inicial (Primera vez solo)

Si es la primera vez, ejecuta esto **ANTES** de usar los scripts:

```powershell
# Backend
cd "C:\proyecto FAST API\backend"
pip install -r requirements.txt
python -m alembic upgrade head

# Frontend
cd "C:\proyecto FAST API\web"
pip install -r requirements.txt
```

Después ya puedes usar los scripts sin problema.

---

## ✅ Checklist de Inicio Rápido

- [ ] Hice doble click en `iniciar-todo.bat` O ejecuté `.\iniciar-todo-simple.ps1`
- [ ] Se abrieron 2 ventanas (Backend + Frontend)
- [ ] Se abrieron los navegadores automáticamente
- [ ] Accedí a http://localhost:5000 (Frontend)
- [ ] Accedí a http://localhost:8000/docs (API)
- [ ] Hice login con admin@example.com / changeme123
- [ ] ¡Listo! 🎉

---

## 💡 Tips

1. **Mantén las ventanas abiertas** - Muestra los logs en tiempo real
2. **Mirar los logs** - Si algo falla, verás el error en las ventanas
3. **Refresh del navegador** - Si cambias código, usa F5 para refrescar
4. **Hot reload** - El backend está en `--reload`, se reinicia automáticamente al cambiar código

---

**Última actualización:** Mayo 2026  
**Versión:** 1.0
