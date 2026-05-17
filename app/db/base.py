# Re-export the single Base from models so Alembic sees the same metadata as the ORM.
# All models must inherit from app.models.base.Base — never from this module directly.
from app.models.base import Base  # noqa: F401

# Import every model so their tables are registered in Base.metadata
from app.models.application import Application  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.permission import Permission  # noqa: F401
from app.models.role import Role  # noqa: F401
from app.models.user import User  # noqa: F401
