from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import timedelta

from app.db import get_db
from app.deps import get_current_user
from app.errors import error
from app.models import User
from app.schemas import RegisterIn, LoginIn, UserUpdate, ChangePinIn
from app.security import hash_pin, verify_pin, create_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=201)
@router.post("/signup", status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.phone == payload.phone)):
        error("phone_exists", "A user with this phone already exists", 409)
    user = User(name=payload.name, phone=payload.phone, pin_hash=hash_pin(payload.pin), role=payload.role,
                city=payload.city, verified=False, active=True, failed_attempts=0)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name, "phone": user.phone, "role": user.role, "city": user.city,
            "verified": user.verified, "active": user.active}

@router.post("/login")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    clock = request.app.state.clock
    now = clock.now()
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if not user or not user.active:
        error("invalid_credentials", "invalid credentials", 401)

    locked_until = user.locked_until
    if locked_until:
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=now.tzinfo)
        if locked_until > now:
            error("account_locked", "Account is locked", 423)
        user.locked_until = None
        user.failed_attempts = 0

    if not verify_pin(payload.pin, user.pin_hash):
        user.failed_attempts = (user.failed_attempts or 0) + 1
        if user.failed_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
        db.commit()
        if user.failed_attempts >= 5:
            error("account_locked", "Account is locked", 423)
        error("invalid_credentials", "invalid credentials", 401)

    user.failed_attempts = 0
    user.locked_until = None
    db.commit()
    token = create_token(user.id, user.role, now)
    return {"access_token": token, "token_type": "bearer", "expires_in": 3600,
            "user": {"id": user.id, "name": user.name, "role": user.role, "verified": user.verified}}
