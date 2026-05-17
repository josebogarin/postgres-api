import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User


async def log_action(
    db: AsyncSession,
    *,
    user: User | None,
    action: str,
    resource: str,
    resource_id: str | None = None,
    method: str,
    path: str,
    status_code: int,
    ip: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        action=action,
        resource=resource,
        resource_id=resource_id,
        method=method,
        path=path,
        status_code=status_code,
        ip_address=ip,
        details=details,
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_audit_logs(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
) -> list[AuditLog]:
    stmt = select(AuditLog)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
