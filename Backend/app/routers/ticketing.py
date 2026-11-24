from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from typing import Literal
from urllib.parse import quote

import qrcode
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import case, func, select, update
from sqlmodel import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_admin, get_current_user
from app.errors import error
from app.models import (
    EventCollaborator,
    PayoutLedger,
    Ticket,
    TicketEvent,
    TicketTier,
    User,
)
from app.security import normalize_phone
from app.services.ticketing import (
    checked_in_now,
    is_valid_qr_token,
    mint_ticket_batch,
    purchase_ticket,
)

router = APIRouter(tags=["Events, Tickets & Gate"])


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: Literal["concert", "conference", "wedding", "other"] = "other"
    venue: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    event_date: datetime
    total_seats: int = Field(gt=0)
    artist_momo_number: str = Field(min_length=7, max_length=32)

    @model_validator(mode="after")
    def clean_fields(self):
        self.title = self.title.strip()
        self.venue = self.venue.strip()
        self.city = self.city.strip()
        if not self.title or not self.venue or not self.city:
            raise ValueError("title, venue, and city cannot be blank")
        self.artist_momo_number = re.sub(
            r"[\s()-]", "", self.artist_momo_number
        )
        if not re.fullmatch(r"\+?[0-9]{7,15}", self.artist_momo_number):
            raise ValueError("artist_momo_number must contain 7 to 15 digits")
        return self


class EventDecision(BaseModel):
    decision: Literal["approve", "reject"]


class TicketTierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    zone_label: str = Field(min_length=1, max_length=120)
    quantity: int = Field(gt=0)

    @model_validator(mode="after")
    def strip_names(self):
        self.name = self.name.strip()
        self.zone_label = self.zone_label.strip()
        if not self.name or not self.zone_label:
            raise ValueError("name and zone_label cannot be blank")
        return self


class TicketMint(BaseModel):
    tier_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=50000)


class CollaboratorCreate(BaseModel):
    user_id: int = Field(gt=0)
    promo_code: str | None = Field(default=None, min_length=3, max_length=40)
    commission_percent: Decimal = Field(
        ge=0, le=100, max_digits=5, decimal_places=2
    )
    assigned_quota: int = Field(ge=0)
    allow_over_quota: bool = False

    @model_validator(mode="after")
    def clean_promo_code(self):
        if self.promo_code is not None:
            self.promo_code = self.promo_code.strip().upper()
            if not re.fullmatch(r"[A-Z0-9_-]{3,40}", self.promo_code):
                raise ValueError("promo_code may contain only letters, numbers, _ and -")
        return self


class TicketPurchase(BaseModel):
    tier_id: int = Field(gt=0)
    buyer_name: str = Field(min_length=1, max_length=200)
    buyer_phone: str = Field(min_length=7, max_length=32)
    promo_code: str | None = Field(default=None, max_length=40)
    payment_ref: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def normalize_fields(self):
        self.buyer_name = self.buyer_name.strip()
        self.payment_ref = self.payment_ref.strip()
        if not self.buyer_name or not self.payment_ref:
            raise ValueError("buyer_name and payment_ref cannot be blank")
        self.buyer_phone = normalize_phone(self.buyer_phone)
        if self.promo_code is not None:
            self.promo_code = self.promo_code.strip().upper()
        return self


class GateScan(BaseModel):
    qr_token: str | None = None
    ticket_code: str | None = None

    @model_validator(mode="after")
    def exactly_one_identifier(self):
        if bool(self.qr_token) == bool(self.ticket_code):
            raise ValueError("provide exactly one of qr_token or ticket_code")
        return self


def _event_owned(db: Session, event_id: int, user: User) -> TicketEvent:
    event = db.get(TicketEvent, event_id)
    if event is None or (user.role != "admin" and event.owner_id != user.id):
        error("event_not_found", "Event not found", 404)
    return event


def _event_view(event: TicketEvent) -> dict:
    return {
        "event_id": event.id,
        "title": event.title,
        "category": event.category,
        "venue": event.venue,
        "city": event.city,
        "event_date": event.event_date,
        "total_seats": event.total_tickets,
        "artist_momo_number": event.artist_momo_number,
        "status": event.status,
        "dashboard_url": f"/events/{event.id}/dashboard",
        "redirect": {"path": f"/events/{event.id}/dashboard"},
    }


def _tier_view(tier: TicketTier) -> dict:
    return {
        "id": tier.id,
        "event_id": tier.event_id,
        "name": tier.name,
        "price": tier.price,
        "zone_label": tier.zone_label,
        "quantity": tier.quantity,
        "minted": tier.minted_count,
        "created_at": tier.created_at,
    }


def _commission_for(
    amount: Decimal, percent: Decimal
) -> Decimal:
    return (amount * percent / Decimal("100")).quantize(Decimal("0.01"))


def _ticket_view(db: Session, ticket: Ticket) -> dict:
    tier = db.get(TicketTier, ticket.tier_id)
    return {
        "ticket_id": ticket.id,
        "ticket_code": ticket.ticket_code,
        "qr_token": ticket.qr_token,
        "qr_image_url": f"/api/tickets/qr/{quote(ticket.qr_token, safe='')}",
        "event_id": ticket.event_id,
        "tier_id": ticket.tier_id,
        "tier": tier.name,
        "zone_label": tier.zone_label,
        "status": ticket.status,
        "buyer_name": ticket.buyer_name,
        "buyer_phone": ticket.buyer_phone,
        "amount_paid": ticket.amount_paid,
        "payment_ref": ticket.payment_ref,
        "collaborator_id": ticket.collaborator_id,
    }


@router.post("/api/events", status_code=201)
def create_ticket_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in {"artist", "promoter"}:
        error("event_forbidden", "Only artists and promoters can create events", 403)
    event = TicketEvent(
        owner_id=user.id,
        title=payload.title,
        category=payload.category,
        venue=payload.venue,
        city=payload.city,
        event_date=payload.event_date,
        total_tickets=payload.total_seats,
        artist_momo_number=payload.artist_momo_number,
        status="pending",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _event_view(event)


@router.get("/api/events")
def list_ticket_events(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    events = db.scalars(
        select(TicketEvent)
        .where(TicketEvent.owner_id == user.id)
        .order_by(TicketEvent.event_date, TicketEvent.id)
    ).all()
    return {"items": [_event_view(event) for event in events], "total": len(events)}


@router.post("/api/events/{event_id}/decision")
@router.post("/api/admin/events/{event_id}/decision", include_in_schema=False)
def decide_event(
    event_id: int,
    payload: EventDecision,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin),
):
    event = db.get(TicketEvent, event_id)
    if event is None:
        error("event_not_found", "Event not found", 404)
    if event.status != "pending":
        error("event_already_decided", "Event has already been reviewed", 409)
    event.status = "approved" if payload.decision == "approve" else "rejected"
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"event_id": event.id, "status": event.status}


@router.post("/api/events/{event_id}/ticket-tiers", status_code=201)
def create_ticket_tier(
    event_id: int,
    payload: TicketTierCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = _event_owned(db, event_id, user)
    if event.status == "rejected":
        error("event_rejected", "Ticket tiers cannot be added to a rejected event", 409)
    event = db.scalar(
        select(TicketEvent).where(TicketEvent.id == event_id).with_for_update()
    )
    tier_capacity = db.scalar(
        select(func.coalesce(func.sum(TicketTier.quantity), 0)).where(
            TicketTier.event_id == event_id
        )
    ) or 0
    if tier_capacity + payload.quantity > event.total_tickets:
        error(
            "event_seat_limit",
            "Ticket tier capacity exceeds the event seat limit",
            409,
            {"available_seats": event.total_tickets - tier_capacity},
        )
    tier = TicketTier(event_id=event_id, **payload.model_dump())
    db.add(tier)
    db.commit()
    db.refresh(tier)
    return _tier_view(tier)


@router.post("/api/events/{event_id}/tickets/mint", status_code=201)
def mint_tickets(
    event_id: int,
    payload: TicketMint,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = _event_owned(db, event_id, user)
    if event.status == "rejected":
        error("event_rejected", "Tickets cannot be minted for a rejected event", 409)
    event = db.scalar(
        select(TicketEvent).where(TicketEvent.id == event_id).with_for_update()
    )
    tier = db.scalar(
        select(TicketTier).where(
            TicketTier.id == payload.tier_id,
            TicketTier.event_id == event_id,
        )
    )
    if tier is None:
        error("ticket_tier_not_found", "Ticket tier not found", 404)
    try:
        records = mint_ticket_batch(db, event, tier, payload.quantity)
    except ValueError as exc:
        db.rollback()
        if str(exc) == "event_seat_limit":
            error("event_seat_limit", "Minted tickets exceed event capacity", 409)
        if str(exc) == "tier_quantity_limit":
            error("tier_quantity_limit", "Minted tickets exceed tier quantity", 409)
        raise
    return {
        "event_id": event_id,
        "tier_id": tier.id,
        "minted": len(records),
        "tickets": [
            {"ticket_code": row["ticket_code"], "qr_token": row["qr_token"]}
            for row in records
        ],
    }


@router.post("/api/events/{event_id}/collaborators", status_code=201)
def assign_collaborator(
    event_id: int,
    payload: CollaboratorCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = _event_owned(db, event_id, user)
    if event.status == "rejected":
        error("event_rejected", "Collaborators cannot be assigned to a rejected event", 409)
    collaborator_user = db.get(User, payload.user_id)
    if (
        collaborator_user is None
        or not collaborator_user.active
        or collaborator_user.role not in {"collaborator", "dj", "promoter", "influencer"}
    ):
        error("collaborator_user_not_found", "Eligible collaborator user not found", 404)
    if collaborator_user.id == event.owner_id:
        error("invalid_collaborator", "Event owners cannot collaborate on their own event", 400)
    existing = db.scalar(
        select(EventCollaborator).where(
            EventCollaborator.event_id == event_id,
            EventCollaborator.user_id == collaborator_user.id,
        )
    )
    if existing is not None:
        error("collaborator_exists", "User is already assigned to this event", 409)

    promo_code = payload.promo_code or f"TB{secrets.token_hex(4).upper()}"
    if db.scalar(
        select(EventCollaborator.id).where(
            EventCollaborator.event_id == event_id,
            EventCollaborator.promo_code == promo_code,
        )
    ):
        error("promo_code_exists", "Promo code is already used for this event", 409)
    collaborator = EventCollaborator(
        event_id=event_id,
        user_id=collaborator_user.id,
        name=collaborator_user.name,
        phone=collaborator_user.phone,
        commission_percent=payload.commission_percent,
        tickets_assigned=max(payload.assigned_quota, 1),
        assigned_quota=payload.assigned_quota,
        allow_over_quota=payload.allow_over_quota,
        promo_code=promo_code,
        status="pending",
    )
    db.add(collaborator)
    db.commit()
    db.refresh(collaborator)
    return {
        "id": collaborator.id,
        "event_id": event_id,
        "user_id": collaborator.user_id,
        "promo_code": collaborator.promo_code,
        "commission_percent": collaborator.commission_percent,
        "assigned_quota": collaborator.assigned_quota,
        "allow_over_quota": collaborator.allow_over_quota,
        "sold_count": collaborator.sold_count,
        "status": collaborator.status,
    }


@router.post("/api/collaborators/{collaborator_id}/accept")
def accept_collaboration(
    collaborator_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    collaborator = db.scalar(
        select(EventCollaborator)
        .where(
            EventCollaborator.id == collaborator_id,
            EventCollaborator.user_id == user.id,
        )
        .with_for_update()
    )
    if collaborator is None:
        error("collaboration_not_found", "Collaboration offer not found", 404)
    if collaborator.status != "pending":
        error("collaboration_already_accepted", "Collaboration offer is not pending", 409)
    collaborator.status = "accepted"
    db.add(collaborator)
    db.commit()
    db.refresh(collaborator)
    return {
        "id": collaborator.id,
        "event_id": collaborator.event_id,
        "promo_code": collaborator.promo_code,
        "status": collaborator.status,
    }


@router.post("/api/events/{event_id}/tickets/purchase", status_code=201)
def buy_ticket(
    event_id: int,
    payload: TicketPurchase,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    try:
        ticket = purchase_ticket(
            db,
            event_id,
            payload.tier_id,
            payload.buyer_name,
            payload.buyer_phone,
            payload.payment_ref,
            payload.promo_code,
        )
    except ValueError as exc:
        db.rollback()
        reasons = {
            "payment_ref_exists": ("payment_ref_exists", "Payment reference has already been used", 409),
            "invalid_promo_code": ("invalid_promo_code", "Promo code is invalid or inactive", 422),
            "collaborator_quota_exceeded": ("collaborator_quota_exceeded", "Collaborator quota has been reached", 409),
        }
        code, message, status = reasons.get(str(exc), ("purchase_failed", "Ticket purchase failed", 409))
        error(code, message, status)
    if ticket is None:
        db.rollback()
        event = db.get(TicketEvent, event_id)
        if event is None:
            error("event_not_found", "Event not found", 404)
        if event.status != "approved":
            error("event_not_approved", "Ticket sales are not open for this event", 409)
        error("tickets_sold_out", "No tickets are available in this tier", 409)

    collaborator = (
        db.get(EventCollaborator, ticket.collaborator_id)
        if ticket.collaborator_id is not None
        else None
    )
    collaborator_amount = (
        _commission_for(ticket.amount_paid, collaborator.commission_percent)
        if collaborator is not None
        else Decimal("0.00")
    )
    platform_fee = _commission_for(
        ticket.amount_paid, settings.platform_fee_percent
    )
    organizer_amount = ticket.amount_paid - collaborator_amount - platform_fee
    if organizer_amount < 0:
        db.rollback()
        error(
            "invalid_revenue_split",
            "Commission and platform fee exceed the ticket price",
            409,
        )
    db.add(
        PayoutLedger(
            ticket_id=ticket.id,
            event_id=event_id,
            collaborator_id=collaborator.id if collaborator else None,
            amount_paid=ticket.amount_paid,
            organizer_amount=organizer_amount,
            collaborator_amount=collaborator_amount,
            platform_fee=platform_fee,
        )
    )
    db.commit()
    db.refresh(ticket)
    result = _ticket_view(db, ticket)
    result["payout"] = {
        "organizer_amount": organizer_amount,
        "collaborator_amount": collaborator_amount,
        "platform_fee": platform_fee,
    }
    return result


@router.get("/api/tickets/qr/{qr_token}")
def ticket_qr_image(qr_token: str, db: Session = Depends(get_db)):
    ticket = db.scalar(select(Ticket).where(Ticket.qr_token == qr_token))
    if (
        ticket is None
        or ticket.status not in {"sold", "checked_in"}
        or not is_valid_qr_token(ticket.ticket_code, qr_token)
    ):
        error("ticket_not_found", "Ticket QR code not found", 404)
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(qr_token)
    qr.make(fit=True)
    image = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
    output = BytesIO()
    image.save(output)
    return Response(content=output.getvalue(), media_type="image/svg+xml")


def _event_metrics(db: Session, event_id: int) -> dict:
    tier_rows = db.execute(
        select(
            TicketTier,
            func.count(Ticket.id).label("minted"),
            func.sum(case((Ticket.status == "available", 1), else_=0)).label("available"),
            func.sum(case((Ticket.status == "sold", 1), else_=0)).label("sold"),
            func.sum(case((Ticket.status == "checked_in", 1), else_=0)).label("checked_in"),
        )
        .outerjoin(Ticket, Ticket.tier_id == TicketTier.id)
        .where(TicketTier.event_id == event_id)
        .group_by(TicketTier.id)
        .order_by(TicketTier.id)
    ).all()
    tiers = [
        {
            "tier_id": tier.id,
            "name": tier.name,
            "zone_label": tier.zone_label,
            "price": tier.price,
            "minted": minted or 0,
            "available": available or 0,
            "sold": sold or 0,
            "checked_in": checked_in or 0,
        }
        for tier, minted, available, sold, checked_in in tier_rows
    ]
    collaborators = db.scalars(
        select(EventCollaborator)
        .where(
            EventCollaborator.event_id == event_id,
            EventCollaborator.user_id.is_not(None),
        )
        .order_by(EventCollaborator.sold_count.desc(), EventCollaborator.id)
    ).all()
    collaborators_view = []
    for collaborator in collaborators:
        commission = db.scalar(
            select(func.coalesce(func.sum(PayoutLedger.collaborator_amount), 0)).where(
                PayoutLedger.collaborator_id == collaborator.id
            )
        ) or Decimal("0")
        collaborators_view.append(
            {
                "id": collaborator.id,
                "user_id": collaborator.user_id,
                "promo_code": collaborator.promo_code,
                "status": collaborator.status,
                "assigned_quota": collaborator.assigned_quota,
                "sold_count": collaborator.sold_count,
                "assigned_quota_remaining": max(
                    0, collaborator.assigned_quota - collaborator.sold_count
                ),
                "remaining_quota": (
                    None
                    if collaborator.allow_over_quota
                    else max(0, collaborator.assigned_quota - collaborator.sold_count)
                ),
                "allow_over_quota": collaborator.allow_over_quota,
                "commission_earned": commission,
            }
        )
    overall = db.execute(
        select(
            func.count(Ticket.id),
            func.sum(case((Ticket.status == "available", 1), else_=0)),
            func.sum(case((Ticket.status == "sold", 1), else_=0)),
            func.sum(case((Ticket.status == "checked_in", 1), else_=0)),
        ).where(Ticket.event_id == event_id)
    ).one()
    gross = db.scalar(
        select(func.coalesce(func.sum(PayoutLedger.amount_paid), 0)).where(
            PayoutLedger.event_id == event_id
        )
    ) or Decimal("0")
    return {
        "total_minted": overall[0] or 0,
        "available": overall[1] or 0,
        "sold": overall[2] or 0,
        "checked_in": overall[3] or 0,
        "gross_momo_revenue": gross,
        "tiers": tiers,
        "collaborators": collaborators_view,
    }


@router.get("/api/events/{event_id}/availability")
def event_availability(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _event_owned(db, event_id, user)
    return {"event_id": event_id, **_event_metrics(db, event_id)}


@router.get("/api/events/{event_id}/dashboard")
def event_dashboard(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = _event_owned(db, event_id, user)
    return {
        "event": _event_view(event),
        **_event_metrics(db, event_id),
        "generated_at": datetime.now(timezone.utc),
    }


@router.post("/api/gate/scan")
def gate_scan(
    payload: GateScan,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "gate_staff" and user.role != "admin":
        ticket_event = db.scalar(
            select(TicketEvent)
            .join(Ticket, Ticket.event_id == TicketEvent.id)
            .where(
                Ticket.qr_token == payload.qr_token
                if payload.qr_token
                else Ticket.ticket_code == payload.ticket_code,
                TicketEvent.owner_id == user.id,
            )
        )
        if user.role not in {"artist", "promoter"} or ticket_event is None:
            error("gate_forbidden", "Gate staff or event organizer access required", 403)
    ticket = db.scalar(
        select(Ticket)
        .where(
            Ticket.qr_token == payload.qr_token
            if payload.qr_token
            else Ticket.ticket_code == payload.ticket_code
        )
        .with_for_update()
    )
    if ticket is None or (
        payload.qr_token
        and not is_valid_qr_token(ticket.ticket_code, payload.qr_token)
    ):
        return Response(
            content='{"valid":false,"reason":"INVALID_OR_UNPAID_TICKET"}',
            status_code=404,
            media_type="application/json",
        )
    event = db.get(TicketEvent, ticket.event_id)
    tier = db.get(TicketTier, ticket.tier_id)
    if event.status != "approved" or ticket.status == "available":
        return Response(
            content='{"valid":false,"reason":"INVALID_OR_UNPAID_TICKET"}',
            status_code=400,
            media_type="application/json",
        )
    if ticket.status == "checked_in":
        return Response(
            content=(
                '{"valid":false,"reason":"ALREADY_USED",'
                f'"checked_in_at":"{ticket.checked_in_at.isoformat()}",'
                f'"buyer_name":{_json_string(ticket.buyer_name)},'
                f'"tier":{_json_string(tier.name)}}}'
            ),
            status_code=409,
            media_type="application/json",
        )
    now = checked_in_now()
    checked_id = db.execute(
        update(Ticket)
        .where(Ticket.id == ticket.id, Ticket.status == "sold")
        .values(status="checked_in", checked_in_at=now, checked_in_by=user.id)
        .returning(Ticket.id)
    ).scalar_one_or_none()
    if checked_id is None:
        db.rollback()
        return Response(
            content='{"valid":false,"reason":"ALREADY_USED"}',
            status_code=409,
            media_type="application/json",
        )
    db.commit()
    collaborator = (
        db.get(EventCollaborator, ticket.collaborator_id)
        if ticket.collaborator_id is not None
        else None
    )
    return {
        "valid": True,
        "ticket_code": ticket.ticket_code,
        "buyer_name": ticket.buyer_name,
        "buyer_phone": ticket.buyer_phone,
        "tier": tier.name,
        "zone_label": tier.zone_label,
        "amount_paid": ticket.amount_paid,
        "sold_by_promo_code": collaborator.promo_code if collaborator else None,
    }


def _json_string(value: str | None) -> str:
    import json

    return json.dumps(value)


@router.post("/api/admin/users/{user_id}/gate-staff")
def promote_gate_staff(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin),
):
    user = db.get(User, user_id)
    if user is None or not user.active:
        error("user_not_found", "Active user not found", 404)
    user.role = "gate_staff"
    db.add(user)
    db.commit()
    return {"user_id": user.id, "role": user.role}

