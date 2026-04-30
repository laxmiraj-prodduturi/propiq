import uuid
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..config import settings
from ..schemas.auth import LoginRequest, RegisterRequest
from ..schemas.user import LoginResponse, UserOut
from ..services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE = "refresh_token"
_COOKIE_OPTS = dict(httponly=True, samesite="lax", secure=settings.COOKIE_SECURE, max_age=7 * 24 * 3600, path="/api/v1/auth")


def _token_payload(user: User) -> dict:
    return {"user_id": user.id, "role": user.role, "tenant_id": user.tenant_id}


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = create_access_token(_token_payload(user))
    refresh_token = create_refresh_token(_token_payload(user))

    response.set_cookie(_REFRESH_COOKIE, refresh_token, **_COOKIE_OPTS)
    return LoginResponse(access_token=access_token, token_type="bearer", user=UserOut.model_validate(user))


@router.post("/register", response_model=LoginResponse)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    initials = (payload.first_name[0] + payload.last_name[0]).upper() if payload.first_name and payload.last_name else "??"
    user = User(
        id=f"u{uuid.uuid4().hex[:8]}",
        tenant_id=payload.tenant_id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        avatar_initials=initials,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(_token_payload(user))
    refresh_token = create_refresh_token(_token_payload(user))

    response.set_cookie(_REFRESH_COOKIE, refresh_token, **_COOKIE_OPTS)
    return LoginResponse(access_token=access_token, token_type="bearer", user=UserOut.model_validate(user))


@router.post("/refresh", response_model=LoginResponse)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access = create_access_token(_token_payload(user))
    new_refresh = create_refresh_token(_token_payload(user))  # rotate

    response.set_cookie(_REFRESH_COOKIE, new_refresh, **_COOKIE_OPTS)
    return LoginResponse(access_token=new_access, token_type="bearer", user=UserOut.model_validate(user))


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(_REFRESH_COOKIE, path="/api/v1/auth")
    return {"message": "Logged out successfully"}
