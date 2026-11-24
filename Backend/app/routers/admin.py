from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_admin
from app.errors import error
from app.models import User, VerificationRequest, AuditLog
from app.schemas import VerificationDecisionIn

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/verification-requests")
def list_requests(status: str = Query(default="pending"), limit: int = Query(default=20, ge=1, le=50),
                 offset: int = Query(default=0, ge=0), db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    statement = select(VerificationRequest)
    if status:
        statement = statement.where(VerificationRequest.status == status)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    items = db.scalars(statement.order_by(VerificationRequest.created_at.desc()).limit(limit).offset(offset)).all()
    return {"total": total, "items": [{"id": item.id, "user_id": item.user_id,
            "evidence_text": item.evidence_text, "evidence_url": item.evidence_url,
            "status": item.status, "note": item.note, "decided_by": item.decided_by,
            "created_at": item.created_at, "decided_at": item.decided_at} for item in items],
            "limit": limit, "offset": offset}

@router.post("/verification-requests/{request_id}/decision")
def decide(request_id: int, payload: VerificationDecisionIn, db: Session = Depends(get_db),
           admin: User = Depends(get_admin)):
    if payload.decision not in ("approve", "reject"):
        error("validation_error", "Validation failed", 422,
              {"fields": [{"field": "decision", "message": "must be approve or reject"}]})
    request = db.get(VerificationRequest, request_id)
    if not request:
        error("not_found", "Verification request not found", 404)
    if request.status != "pending":
        error("already_decided", "Verification request was already decided", 409)
    user = db.get(User, request.user_id)
    request.status = "approved" if payload.decision == "approve" else "rejected"
    request.note = payload.note
    request.decided_by = admin.id
    from datetime import datetime, timezone
    request.decided_at = datetime.now(timezone.utc)
    if payload.decision == "approve":
        user.verified = True
    db.add(AuditLog(actor_id=admin.id, action="verification_decision", target=f"verification_request:{request.id}"))
    db.commit()
    return {"id": request.id, "status": request.status, "note": request.note,
            "decided_by": request.decided_by, "decided_at": request.decided_at,
            "user_verified": user.verified}

@router.get("/audit")
def audit(limit: int = Query(default=20, ge=1, le=50), offset: int = Query(default=0, ge=0),
          db: Session = Depends(get_db), admin: User = Depends(get_admin)):
    total = db.scalar(select(func.count()).select_from(AuditLog)) or 0
    items = db.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)).all()
    return {"total": total, "items": [{"id": item.id, "actor_id": item.actor_id, "action": item.action,
            "target": item.target, "timestamp": item.timestamp} for item in items],
            "limit": limit, "offset": offset}
