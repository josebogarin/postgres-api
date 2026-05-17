from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.auth import LoginRequest, RefreshRequest, Token
from app.schemas.user import UserResponse
from app.services import auth as auth_service

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(body: LoginRequest, db: DBSession):
    user = await auth_service.authenticate(db, email=body.email, password=body.password)
    return auth_service.generate_tokens(user)


@router.post("/refresh", response_model=Token)
async def refresh(body: RefreshRequest, db: DBSession):
    return await auth_service.refresh_tokens(db, refresh_token=body.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    return current_user
