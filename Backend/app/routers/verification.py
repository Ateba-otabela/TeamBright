from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import error
from app.models import User, VerificationRequest
from app.schemas import VerificationRequestIn

router = APIRouter(tags=["verification"])

@router.post("/verification-requests", status_code=201)
def create_request(payload: VerificationRequestIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("artist", "dj", "broadcaster", "promoter"):
        error("verification_forbidden", "Your role cannot request verification", 403)
    if user.verified:
        error("already_verified", "User is already verified", 409)
    pending = db.scalar(select(VerificationRequest).where(VerificationRequest.user_id == user.id,
                                                             VerificationRequest.status == "pending"))
    if pending:
        error("verification_pending", "A verification request is already pending", 409)
    request = VerificationRequest(user_id=user.id, evidence_text=payload.evidence_text,
                                  evidence_url=payload.evidence_url, status="pending")
    db.add(request)
    db.commit()
    db.refresh(request)
    return verification_view(request)

@router.get("/verification-requests/mine")
def mine(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    requests = db.scalars(select(VerificationRequest).where(VerificationRequest.user_id == user.id)
                          .order_by(VerificationRequest.created_at.desc())).all()
    return {"items": [verification_view(item) for item in requests], "total": len(requests)}


def verification_view(item: VerificationRequest):
    return {"id": item.id, "user_id": item.user_id, "evidence_text": item.evidence_text,
            "evidence_url": item.evidence_url, "status": item.status, "note": item.note,
            "decided_by": item.decided_by, "created_at": item.created_at, "decided_at": item.decided_at}
