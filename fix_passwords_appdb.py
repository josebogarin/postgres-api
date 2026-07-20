"""
Diagnóstico y reparación de contraseñas en app_db.
Ejecutar: python fix_passwords_appdb.py
(desde C:\proyecto FAST API con el venv activo)
"""
import asyncio
import sys

async def main():
    try:
        import bcrypt
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
    except ImportError as e:
        print(f"ERROR: falta paquete: {e}")
        print("Activá el venv: backend\\.venv\\Scripts\\Activate.ps1")
        return

    DB_URL = "postgresql+asyncpg://app_user:superpassword@localhost:5432/app_db"
    engine = create_async_engine(DB_URL, pool_pre_ping=True)

    def make_hash(pwd: str) -> str:
        return bcrypt.hashpw(pwd.strip().lower().encode(), bcrypt.gensalt()).decode()

    def check_hash(plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain.strip().lower().encode(), hashed.encode())
        except Exception:
            return False

    try:
        async with engine.connect() as conn:
            # ── Diagnóstico ──────────────────────────────────────────
            r = await conn.execute(text(
                "SELECT id, username, password_hash, is_active FROM users ORDER BY id LIMIT 60"
            ))
            rows = r.fetchall()
            print(f"\n{'='*60}")
            print(f"Usuarios en app_db: {len(rows)}")
            print(f"{'='*60}")

            bad = []
            for row in rows:
                uid, uname, phash, active = row
                ok_catalina   = check_hash('catalina',    phash)
                ok_becbuc2026 = check_hash('becbuc2026',  phash)
                ok = ok_catalina or ok_becbuc2026
                pwd_label = 'catalina' if ok_catalina else ('becbuc2026' if ok_becbuc2026 else 'INVALIDO')
                status = '✅' if ok else '❌'
                print(f"  {status} id={uid:3d} {uname:<20} hash_ok={ok} pass={pwd_label} active={active}")
                if not ok:
                    bad.append((uid, uname))

            print(f"\n{'='*60}")
            print(f"Hashes inválidos: {len(bad)}")

            if not bad:
                print("✅ Todas las contraseñas están OK")
                print("\nSi el login igual falla, verificá que uvicorn esté activo:")
                print("  cd backend && .venv\\Scripts\\Activate.ps1 && uvicorn app.main:app --reload --port 8000")
            else:
                print("\nReparando contraseñas inválidas...")
                # jose → catalina, resto → becbuc2026
                h_catalina   = make_hash('catalina')
                h_becbuc2026 = make_hash('becbuc2026')

                for uid, uname in bad:
                    new_hash = h_catalina if uname == 'jose' else h_becbuc2026
                    await conn.execute(text(
                        "UPDATE users SET password_hash=:h WHERE id=:id"
                    ), {"h": new_hash, "id": uid})
                    print(f"  ✅ id={uid} {uname} → {'catalina' if uname=='jose' else 'becbuc2026'}")

                await conn.commit()
                print("\n✅ Contraseñas reparadas. Intentá el login nuevamente.")

            # ── Verificar que jose existe ────────────────────────────
            r2 = await conn.execute(text(
                "SELECT id, username, is_active FROM users WHERE username='jose'"
            ))
            jose = r2.fetchone()
            if not jose:
                print("\n⚠️  Usuario 'jose' NO EXISTE en app_db.")
                print("   Creándolo...")
                h = make_hash('catalina')
                await conn.execute(text("""
                    INSERT INTO users (username, email, password_hash, is_active, is_superuser)
                    VALUES ('jose', 'jose@becbuc.local', :h, true, true)
                    ON CONFLICT (username) DO NOTHING
                """), {"h": h})
                await conn.commit()
                print("   ✅ jose creado con password=catalina")
            else:
                print(f"\n✅ jose existe: id={jose[0]}, active={jose[2]}")

    except Exception as e:
        print(f"\n❌ Error de conexión a app_db: {e}")
        print("\nPosibles causas:")
        print("  1. Docker no está corriendo: docker start core-postgres")
        print("  2. app_db no existe: docker exec core-postgres createdb -U app_user app_db")
        print("  3. Uvicorn no está activo (pero este script conecta directo a DB, no al API)")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
