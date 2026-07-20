"""
Aplicación Flask integrada con API FastAPI
Versión simplificada - Lista para usar
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')

# Configuración
API_URL = os.getenv('API_URL', 'http://localhost:8000')


def api_call(method: str, endpoint: str, data=None):
    """Hacer llamada a la API FastAPI usando requests (síncrono)"""
    url = f"{API_URL}/api/v1{endpoint}"
    headers = {'Content-Type': 'application/json'}

    # Obtener token de la sesión
    if 'access_token' in session:
        headers['Authorization'] = f'Bearer {session["access_token"]}'

    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method.upper() == 'PATCH':
            response = requests.patch(url, json=data, headers=headers, timeout=10)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            raise ValueError(f"Método no soportado: {method}")

        # Mostrar en consola para debugging
        print(f"[API] {method} {endpoint} → Status: {response.status_code}")

        if response.status_code in [200, 201]:
            return response.json()
        elif response.status_code == 401:
            raise Exception("No autenticado. Por favor, inicia sesión.")
        else:
            try:
                error_data = response.json()
                raise Exception(error_data.get('detail', response.text))
            except:
                raise Exception(f"Error {response.status_code}: {response.text}")

    except requests.ConnectionError:
        raise Exception("No se puede conectar a la API. ¿FastAPI está corriendo en puerto 8000?")
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        raise e


# ==================== RUTAS ====================

@app.route('/')
def index():
    """Página de inicio"""
    if 'access_token' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            result = api_call('POST', '/auth/login', {
                'email': email,
                'password': password
            })

            # Guardar tokens en sesión
            session['access_token'] = result['access_token']
            session['refresh_token'] = result.get('refresh_token')

            # Obtener datos del usuario
            user_result = api_call('GET', '/auth/me')
            session['user_email'] = user_result['email']
            session['user_name'] = user_result.get('full_name', user_result['email'])

            flash(f'¡Bienvenido {session["user_name"]}!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    """Dashboard"""
    if 'access_token' not in session:
        return redirect(url_for('login'))

    try:
        # Obtener datos del usuario
        user = api_call('GET', '/auth/me')

        # Obtener aplicaciones
        apps_result = api_call('GET', '/applications?skip=0&limit=100')
        if isinstance(apps_result, dict):
            applications = apps_result.get('items', [])
        else:
            applications = apps_result if isinstance(apps_result, list) else []

        # Obtener usuarios
        users_result = api_call('GET', '/users?skip=0&limit=100')
        if isinstance(users_result, dict):
            users = users_result.get('items', [])
        else:
            users = users_result if isinstance(users_result, list) else []

        stats = {
            'total_apps': len(applications),
            'total_users': len(users),
            'apps': applications[:5] if applications else [],
        }

        return render_template('dashboard.html', user=user, stats=stats)

    except Exception as e:
        print(f"[Dashboard Error] {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return render_template('dashboard.html', user={}, stats={})


@app.route('/applications')
def applications():
    """Listar aplicaciones"""
    if 'access_token' not in session:
        return redirect(url_for('login'))

    try:
        result = api_call('GET', '/applications?skip=0&limit=100')
        if isinstance(result, dict):
            apps = result.get('items', [])
        else:
            apps = result if isinstance(result, list) else []
        return render_template('applications.html', applications=apps)
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('applications.html', applications=[])


@app.route('/users')
def users():
    """Listar usuarios"""
    if 'access_token' not in session:
        return redirect(url_for('login'))

    try:
        result = api_call('GET', '/users?skip=0&limit=100')
        if isinstance(result, dict):
            user_list = result.get('items', [])
        else:
            user_list = result if isinstance(result, list) else []
        return render_template('users.html', users=user_list)
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('users.html', users=[])


@app.route('/audit-logs')
def audit_logs():
    """Ver logs de auditoría"""
    if 'access_token' not in session:
        return redirect(url_for('login'))

    try:
        result = api_call('GET', '/audit-logs?skip=0&limit=50')
        if isinstance(result, dict):
            logs = result.get('items', [])
        else:
            logs = result if isinstance(result, list) else []
        return render_template('audit-logs.html', logs=logs)
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return render_template('audit-logs.html', logs=[])


# ==================== MANEJO DE ERRORES ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500


# ==================== CONTEXTO PARA TEMPLATES ====================

@app.context_processor
def inject_user():
    """Inyectar datos del usuario en templates"""
    return {
        'user_name': session.get('user_name'),
        'user_email': session.get('user_email'),
    }


if __name__ == '__main__':
    print("=" * 50)
    print("Iniciando aplicación Flask...")
    print("=" * 50)
    print(f"API URL: {API_URL}")
    print("Accede a: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
