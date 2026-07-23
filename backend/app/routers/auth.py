import bcrypt
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("about", (), {"__version__": getattr(bcrypt, "__version__", "4.0.0")})
import passlib.handlers.bcrypt as _bcrypt_mod
_bcrypt_mod.detect_wrap_bug = lambda ident: False

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from app.config import get_settings
from app.database import get_db
from app.models.user import User

router = APIRouter()
settings = get_settings()
security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Schemas ───────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str
    credits: int


class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    name: str | None
    plan: str
    credits: int


# ── JWT Helpers ───────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "access"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "refresh"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication credentials required")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def get_current_user_or_dev(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Returns authenticated user if token present, otherwise gets/creates a dev user for local development."""
    if credentials:
        try:
            return await get_current_user(credentials, db)
        except HTTPException:
            pass

    # Fallback dev user
    result = await db.execute(select(User).where(User.email == "dev@interviewcopilot.ai"))
    dev_user = result.scalar_one_or_none()
    if not dev_user:
        dev_user = User(
            id="dev_user",
            email="dev@interviewcopilot.ai",
            name="Developer Demo",
            hashed_password=pwd_context.hash("devpassword"),
            plan="free",
            credits=99,
        )
        db.add(dev_user)
        await db.flush()
    return dev_user


# ── Endpoints ─────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse)
async def signup(
    body: SignupRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # Check if email exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        name=body.name,
        hashed_password=pwd_context.hash(body.password),
        plan="free",
        credits=5,
    )
    db.add(user)
    await db.flush()

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user_id=user.id,
        name=user.name or "",
        email=user.email,
        credits=user.credits,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(body.password, user.hashed_password):
        raise HTTPException(
            status_code=401, detail="Invalid email or password"
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user_id=user.id,
        name=user.name or "",
        email=user.email,
        credits=user.credits,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    current_user: User = Depends(get_current_user_or_dev),
) -> UserProfileResponse:
    return UserProfileResponse(
        user_id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        plan=current_user.plan,
        credits=current_user.credits,
    )
