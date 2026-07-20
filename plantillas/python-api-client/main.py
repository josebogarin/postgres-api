"""
TEMPLATE_TITLE — cliente Python para la API REST.
Punto de entrada principal del proyecto.
"""

from api_client import APIClient


def main():
    # Usar como context manager: hace login automático al entrar
    with APIClient() as api:

        # ── Ejemplo: obtener usuario actual ──────────────────────────────────
        me = api.get("/auth/me")
        print(f"Conectado como: {me['email']}")

        # ── Ejemplo: listar usuarios ──────────────────────────────────────────
        usuarios = api.get("/users/")
        print(f"Usuarios en el sistema: {len(usuarios)}")
        for u in usuarios:
            print(f"  - {u['email']} (activo: {u['is_active']})")

        # ── Ejemplo: listar tablas disponibles (admin) ───────────────────────
        tablas = api.get("/admin/tables")
        print(f"\nTablas en la BD: {[t['name'] for t in tablas]}")

        # ── Agrega tu lógica aquí ────────────────────────────────────────────
        # Ejemplo para crear un usuario:
        # nuevo = api.post("/users/", {
        #     "email": "nuevo@ejemplo.com",
        #     "password": "MiPassword123",
        #     "full_name": "Nombre Apellido"
        # })
        # print(f"Usuario creado: {nuevo['id']}")


if __name__ == "__main__":
    main()
