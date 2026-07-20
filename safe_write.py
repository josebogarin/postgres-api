#!/usr/bin/env python3
"""
safe_write.py  —  Herramienta de escritura segura para archivos grandes de BECBUC.

USO (desde Python bash):
    import subprocess, sys
    sys.path.insert(0, r'C:\proyecto FAST API')
    from safe_write import safe_write_html, safe_write_py

O ejecutar directamente para verificar un archivo:
    python safe_write.py <ruta_archivo>
"""

import ast, re, shutil, subprocess, sys, os
from datetime import datetime

# Rutas derivadas de la ubicacion de este archivo -> portable, no depende de C:\proyecto FAST API.
# (Se puede overridear con las env vars BECBUC_STATIC_DIR / BECBUC_BACKUP_DIR.)
_ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get('BECBUC_STATIC_DIR', os.path.join(_ROOT, 'backend', 'static'))
BACKUP_DIR = os.environ.get('BECBUC_BACKUP_DIR', os.path.join(_ROOT, '_backups'))

def _backup(path: str) -> str:
    """Crea backup antes de modificar. Retorna ruta del backup."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts  = datetime.now().strftime('%Y%m%d_%H%M%S')
    name = os.path.basename(path)
    dst  = os.path.join(BACKUP_DIR, f'{name}.{ts}.bak')
    shutil.copy2(path, dst)
    return dst

def verify_html(path: str) -> tuple[bool, str]:
    """Verifica que un archivo HTML esté completo y con JS sintácticamente correcto."""
    raw = open(path, 'rb').read()
    if not raw.rstrip().endswith(b'</html>'):
        return False, f'Falta </html> al final (últimos 60 bytes: {raw[-60:]!r})'
    scripts = re.findall(rb'<script>([\s\S]*?)</script>', raw)
    if not scripts:
        return False, 'No se encontró bloque <script>'
    r = subprocess.run(['node', '--check'], input=scripts[-1], capture_output=True)
    if r.returncode != 0:
        err = r.stderr.decode(errors='replace').strip().split('\n')[0]
        return False, f'JS SyntaxError: {err}'
    return True, 'OK'

def verify_py(path: str) -> tuple[bool, str]:
    """Verifica sintaxis Python."""
    try:
        src = open(path, encoding='utf-8').read()
        ast.parse(src)
        return True, 'OK'
    except SyntaxError as e:
        return False, f'SyntaxError line {e.lineno}: {e.msg}'

def safe_write(path: str, content: str | bytes, *, min_size_ratio: float = 0.98) -> None:
    """
    Escribe content en path de forma segura:
    1. Hace backup del original.
    2. Verifica que el nuevo contenido sea al menos min_size_ratio del original.
    3. Escribe el archivo.
    4. Verifica sintaxis (Python o HTML/JS).
    5. Si la verificación falla, restaura el backup y lanza excepción.
    """
    if not os.path.exists(path):
        # Archivo nuevo — solo escribir
        mode = 'wb' if isinstance(content, bytes) else 'w'
        with open(path, mode, encoding=(None if isinstance(content, bytes) else 'utf-8')) as f:
            f.write(content)
        return

    orig_size = os.path.getsize(path)
    new_size  = len(content) if isinstance(content, bytes) else len(content.encode('utf-8'))

    if new_size < orig_size * min_size_ratio:
        raise ValueError(
            f'ABORTADO: nuevo contenido ({new_size} bytes) es mucho más pequeño que '
            f'el original ({orig_size} bytes) — posible truncación.'
        )

    backup = _backup(path)
    try:
        mode = 'wb' if isinstance(content, bytes) else 'w'
        kw   = {} if isinstance(content, bytes) else {'encoding': 'utf-8'}
        with open(path, mode, **kw) as f:
            f.write(content)
    except Exception as e:
        shutil.copy2(backup, path)
        raise RuntimeError(f'Error escribiendo {path}, restaurado desde backup: {e}')

    # Verify
    ext = os.path.splitext(path)[1].lower()
    if ext == '.py':
        ok, msg = verify_py(path)
    elif ext in ('.html', '.htm'):
        ok, msg = verify_html(path)
    else:
        ok, msg = True, 'skip (tipo desconocido)'

    if not ok:
        shutil.copy2(backup, path)
        raise RuntimeError(
            f'Verificación falló — {msg}\n'
            f'Archivo restaurado desde {backup}'
        )

    actual_size = os.path.getsize(path)
    print(f'✅ safe_write OK: {path}')
    print(f'   Original: {orig_size} bytes → Nuevo: {actual_size} bytes  |  {msg}')
    print(f'   Backup:   {backup}')


def safe_patch_html(path: str, replacements: list[tuple[str, str]], *, max_count: int = 1) -> None:
    """
    Aplica una lista de (old, new) replacements sobre un archivo HTML de forma segura.
    Útil para modificar archivos grandes sin riesgo de truncación.
    """
    src = open(path, encoding='utf-8').read()
    for old, new in replacements:
        count = src.count(old)
        if count == 0:
            raise ValueError(f'Texto no encontrado en {path}:\n  {old[:80]!r}')
        if count > max_count:
            raise ValueError(f'Texto ambiguo ({count} ocurrencias) en {path}:\n  {old[:80]!r}')
        src = src.replace(old, new, 1)
    safe_write(path, src)


def safe_patch_py(path: str, replacements: list[tuple[str, str]], *, max_count: int = 1) -> None:
    """Igual que safe_patch_html pero para archivos Python."""
    src = open(path, encoding='utf-8').read()
    for old, new in replacements:
        count = src.count(old)
        if count == 0:
            raise ValueError(f'Texto no encontrado en {path}:\n  {old[:80]!r}')
        if count > max_count:
            raise ValueError(f'Texto ambiguo ({count} ocurrencias) en {path}:\n  {old[:80]!r}')
        src = src.replace(old, new, 1)
    safe_write(path, src)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Uso: python safe_write.py <ruta_archivo>')
        sys.exit(1)
    p = sys.argv[1]
    ext = os.path.splitext(p)[1].lower()
    if ext == '.py':
        ok, msg = verify_py(p)
    elif ext in ('.html', '.htm'):
        ok, msg = verify_html(p)
    else:
        print(f'Tipo no soportado: {ext}')
        sys.exit(1)
    size = os.path.getsize(p)
    status = '✅' if ok else '❌'
    print(f'{status} {os.path.basename(p)}: {size:,} bytes  —  {msg}')
    sys.exit(0 if ok else 1)
