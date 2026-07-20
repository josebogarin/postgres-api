# 🚀 Sistema Admin BD - Web Flask

## Archivos Listos para Usar

Todos los archivos necesarios ya están en `C:\proyecto FAST API\web\`

```
web/
├── app.py                 ✅ Aplicación Flask
├── requirements.txt       ✅ Dependencias
├── .env                   ✅ Configuración
└── templates/             ✅ HTML
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── applications.html
    ├── users.html
    ├── audit-logs.html
    ├── 404.html
    └── 500.html
```

## 📋 Pasos para Ejecutar

### 1️⃣ Abrir PowerShell (IMPORTANTE: Como Administrador)

Presiona `Win + X` → Selecciona **Windows PowerShell (Admin)**

### 2️⃣ Instalar Dependencias

```powershell
cd "C:\proyecto FAST API\web"
pip install -r requirements.txt
```

Espera a que termine (verás "Successfully installed")

### 3️⃣ Verificar que FastAPI está corriendo

En **otra terminal** ejecuta:

```powershell
cd "C:\proyecto FAST API\backend"
python -m uvicorn app.main:app --reload --port 8000
```

Deberías ver:
```
Uvicorn running on http://127.0.0.1:8000
```

### 4️⃣ Ejecutar Flask

En **la primera terminal** (donde instalaste dependencias):

```powershell
cd "C:\proyecto FAST API\web"
python app.py
```

Deberías ver:
```
Iniciando aplicación Flask...
API URL: http://localhost:8000
Accede a: http://localhost:5000
Running on http://127.0.0.1:5000
```

### 5️⃣ Abrir en Navegador

```
http://localhost:5000
```

## 🔐 Credenciales de Prueba

```
Email:       admin@example.com
Contraseña:  changeme123
```

## ❌ Si te da Error

### "ModuleNotFoundError: No module named 'flask'"
```powershell
pip install -r requirements.txt
```

### "Connection refused" o "Cannot connect to API"
- Verificar que FastAPI está corriendo en puerto 8000
- En DevTools (F12) → Console ver errores

### "Address already in use"
- Cambiar puerto en app.py, línea final:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Cambiar 5000 → 5001
```

### "TemplateNotFound"
- Verificar que existe carpeta `templates/` con los archivos HTML

## 📍 URLs Disponibles

Una vez que esté ejecutándose:

| Página | URL |
|--------|-----|
| Login | http://localhost:5000/login |
| Dashboard | http://localhost:5000/dashboard |
| Aplicaciones | http://localhost:5000/applications |
| Usuarios | http://localhost:5000/users |
| Auditoría | http://localhost:5000/audit-logs |

## 🎯 Flujo de Uso

1. Abre http://localhost:5000
2. Te redirige a /login automáticamente
3. Ingresa: admin@example.com / changeme123
4. ¡Ves el dashboard!
5. Explora las opciones del menú

## 🔧 Configuración

Si necesitas cambiar el puerto de FastAPI:

Edita `.env`:
```
API_URL=http://localhost:8000  # Cambiar 8000 si lo necesitas
```

## ✅ Verificar que Todo Funciona

1. **Flask corriendo:** Deberías ver texto verde en terminal
2. **Página carga:** http://localhost:5000 muestra login
3. **Login funciona:** Ingresa las credenciales
4. **Dashboard visible:** Ves data de la API

## 🛑 Para Detener

En cada terminal: presiona `Ctrl + C`

---

**¿Problemas?** Revisa que:
- [ ] FastAPI corre en puerto 8000
- [ ] Flask corre en puerto 5000
- [ ] Las credenciales son correctas
- [ ] Existen los archivos HTML
- [ ] Las dependencias se instalaron correctamente
