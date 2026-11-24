from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import error
from app.models import SplitContract, SplitContractParticipant, User
from app.security import normalize_phone

router = APIRouter(prefix="/split-contracts", tags=["split-contracts"])


class ParticipantIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    role: str = Field(default="Collaborator", max_length=100)
    phone: str
    momo_number: str = Field(default="", max_length=32)
    share_percent: Decimal = Field(ge=0, le=100)

    @field_validator("name", "role")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("phone")
    @classmethod
    def normalize_participant_phone(cls, value: str) -> str:
        return normalize_phone(value)


class SplitContractCreateIn(BaseModel):
    track_title: str = Field(min_length=1, max_length=200)
    participants: list[ParticipantIn] = Field(min_length=2, max_length=20)

    @field_validator("track_title")
    @classmethod
    def trim_track_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Track title cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_contract(self):
        if sum((item.share_percent for item in self.participants), Decimal("0")) != Decimal("100"):
            raise ValueError("Participant shares must total exactly 100 percent")
        phones = [item.phone for item in self.participants]
        if len(set(phones)) != len(phones):
            raise ValueError("Each participant must have a different phone number")
        return self


def serialize_contract(db: Session, contract: SplitContract) -> dict:
    participants = db.scalars(
        select(SplitContractParticipant)
        .where(SplitContractParticipant.contract_id == contract.id)
        .order_by(SplitContractParticipant.id)
    ).all()
    return {
        "id": contract.public_id,
        "track_title": contract.track_title,
        "status": contract.status,
        "created_at": contract.created_at.isoformat(),
        "participants": [
            {
                "name": person.display_name,
                "role": person.role,
                "momo_number": person.momo_number,
                "share_percent": float(person.share_percent),
                "signed": person.signed_at is not None,
                "signed_at": person.signed_at.isoformat() if person.signed_at else None,
            }
            for person in participants
        ],
    }


@router.post("", status_code=201)
def create_split_contract(
    payload: SplitContractCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "artist":
        error("forbidden", "Only an artist account can create a split contract", 403)

    users_by_phone = {
        item.phone: db.scalar(select(User).where(User.phone == item.phone, User.active.is_(True)))
        for item in payload.participants
    }
    missing = [item.phone for item in payload.participants if users_by_phone[item.phone] is None]
    if missing:
        error(
            "participants_must_have_accounts",
            "Every collaborator must have an active CamerHits account before signing",
            422,
        )
    if user.phone not in users_by_phone:
        error("artist_must_be_participant", "The signed-in artist must be included in the split", 422)

    contract = SplitContract(
        public_id=str(uuid4()),
        owner_id=user.id,
        track_title=payload.track_title,
        status="pending",
    )
    db.add(contract)
    db.flush()
    for item in payload.participants:
        participant_user = users_by_phone[item.phone]
        db.add(
            SplitContractParticipant(
                contract_id=contract.id,
                user_id=participant_user.id,
                display_name=item.name,
                role=item.role,
                momo_number=item.momo_number,
                share_percent=item.share_percent,
            )
        )
    db.commit()
    db.refresh(contract)
    return serialize_contract(db, contract)


@router.get("/{public_id}")
def get_split_contract(public_id: str, db: Session = Depends(get_db)):
    contract = db.scalar(select(SplitContract).where(SplitContract.public_id == public_id))
    if not contract:
        error("split_contract_not_found", "Split contract was not found", 404)
    return serialize_contract(db, contract)


@router.post("/{public_id}/sign")
def sign_split_contract(
    public_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contract = db.scalar(select(SplitContract).where(SplitContract.public_id == public_id))
    if not contract:
        error("split_contract_not_found", "Split contract was not found", 404)
    participant = db.scalar(
        select(SplitContractParticipant).where(
            SplitContractParticipant.contract_id == contract.id,
            SplitContractParticipant.user_id == user.id,
        )
    )
    if not participant:
        error("not_a_contract_participant", "This CamerHits account is not listed on the contract", 403)
    if participant.signed_at is None:
        participant.signed_at = datetime.utcnow()
        participants = db.scalars(
            select(SplitContractParticipant).where(SplitContractParticipant.contract_id == contract.id)
        ).all()
        if all(person.signed_at is not None or person.id == participant.id for person in participants):
            contract.status = "signed"
        contract.updated_at = participant.signed_at
        db.add(participant)
        db.add(contract)
        db.commit()
        db.refresh(contract)
    return serialize_contract(db, contract)
