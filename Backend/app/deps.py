from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
import jwt

from app.db import get_db
from app.models import User
from app.security import decode_token
from app.errors import error


bearer = HTTPBearer(auto_error=False)


def get_clock(request):
    return request.app.state.clock


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        error("unauthorized", "Authentication required", 401)
    try:
        payload = decode_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        error("unauthorized", "Invalid or expired token", 401)
    user = db.get(User, user_id)
    if not user or not user.active:
        error("unauthorized", "Invalid or expired token", 401)
    return user


def get_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        error("forbidden", "Admin access required", 403)
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user = db.get(User, int(payload["sub"]))
        return user if user and user.active else None
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None
