from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import error
from app.models import User
from app.schemas import UserUpdate, ChangePinIn
from app.security import verify_pin, hash_pin

router = APIRouter(tags=["users"])

@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "name": user.name, "phone": user.phone, "role": user.role,
            "city": user.city, "verified": user.verified, "active": user.active}

@router.patch("/me")
def update_me(payload: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    updates = payload.model_dump(exclude_unset=True)
    for field in ("name", "city"):
        if field in updates:
            setattr(user, field, updates[field])
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name, "phone": user.phone, "role": user.role,
            "city": user.city, "verified": user.verified, "active": user.active}

@router.post("/me/change-pin")
def change_pin(payload: ChangePinIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_pin(payload.old_pin, user.pin_hash):
        error("invalid_pin", "Old PIN is incorrect", 400)
    user.pin_hash = hash_pin(payload.new_pin)
    user.failed_attempts = 0
    user.locked_until = None
    db.commit()
    return {"message": "PIN changed"}
