"""
Script para corregir el hash del password del admin.
Ejecutar desde PowerShell:
  cd "C:\proyecto FAST API\backend"
  .\.venv\Scripts\python.exe fix_admin_password.py
"""
import asyncio
import sys

async def main():
    try:
        import asyncpg
    except ImportError:
        print("Instalando asyncpg...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "asyncpg"])
        import asyncpg

    try:
        from passlib.context import CryptContext
    except ImportError:
        print("Instalando passlib...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "passlib[bcrypt]"])
        from passlib.context import CryptContext

    ctx = CryptContext(schemes=["bcrypt"])
    new_hash = ctx.hash("faute")
    print(f"Hash generado: {new_hash[:20]}...")

    conn = await asyncpg.connect(
        "postgresql://app_user:superpassword@localhost:5432/app_db"
    )
    try:
        result = await conn.fetchrow(
            "UPDATE users SET password_hash = $1 WHERE email = $2 RETURNING id, email",
            new_hash,
            "admin@example.com",
        )
        if result:
            print(f"Password actualizado para: {result['email']} (id={result['id']})")
        else:
            print("ADVERTENCIA: No se encontro el usuario admin@example.com")
            # Mostrar usuarios existentes
            rows = await conn.fetch("SELECT id, email FROM users LIMIT 5")
            print("Usuarios en la BD:")
            for row in rows:
                print(f"  id={row['id']} email={row['email']}")
    finally:
        await conn.close()

    print("Listo. Ahora puedes hacer login con admin@example.com / changeme123")

asyncio.run(main())
