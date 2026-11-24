from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlmodel import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import error
from app.models import EventCollaborator, TicketEvent, User

router = APIRouter(prefix="/events", tags=["Events & Ticket Collaborators"])


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    event_date: datetime
    venue: str = Field(min_length=1, max_length=200)
    ticket_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    total_tickets: int = Field(gt=0)

    @model_validator(mode="after")
    def strip_text(self):
        self.title = self.title.strip()
        self.venue = self.venue.strip()
        if not self.title or not self.venue:
            raise ValueError("title and venue cannot be blank")
        return self


class CollaboratorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=32)
    commission_percent: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    tickets_assigned: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_contact(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("name cannot be blank")
        if bool(self.email) == bool(self.phone):
            raise ValueError("provide exactly one of email or phone")
        if self.email is not None:
            self.email = self.email.strip().lower()
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", self.email):
                raise ValueError("email is not valid")
        if self.phone is not None:
            phone = re.sub(r"[\s()-]", "", self.phone)
            if not re.fullmatch(r"\+?[0-9]{7,15}", phone):
                raise ValueError("phone must contain 7 to 15 digits")
            self.phone = phone
        return self


class TicketSalesCreate(BaseModel):
    quantity: int = Field(gt=0)


def _event_view(event: TicketEvent) -> dict:
    return {
        "id": event.id,
        "title": event.title,
        "event_date": event.event_date,
        "venue": event.venue,
        "ticket_price": event.ticket_price,
        "total_tickets": event.total_tickets,
        "created_at": event.created_at,
    }


def _collaborator_view(item: EventCollaborator, ticket_price: Decimal) -> dict:
    return {
        "id": item.id,
        "event_id": item.event_id,
        "name": item.name,
        "email": item.email,
        "phone": item.phone,
        "commission_percent": item.commission_percent,
        "commission_per_ticket": (
            ticket_price * item.commission_percent / Decimal("100")
        ).quantize(Decimal("0.01")),
        "tickets_assigned": item.tickets_assigned,
        "tickets_sold": item.tickets_sold,
        "tickets_remaining": item.tickets_assigned - item.tickets_sold,
        "created_at": item.created_at,
    }


def _owned_event(db: Session, event_id: int, owner_id: int) -> TicketEvent:
    event = db.get(TicketEvent, event_id)
    if event is None or event.owner_id != owner_id:
        error("event_not_found", "Event not found", 404)
    return event


@router.post("", status_code=201)
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = TicketEvent(owner_id=user.id, **payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return _event_view(event)


@router.get("")
def list_events(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    events = db.scalars(
        select(TicketEvent)
        .where(TicketEvent.owner_id == user.id)
        .order_by(TicketEvent.event_date, TicketEvent.id)
    ).all()
    return {"items": [_event_view(event) for event in events], "total": len(events)}


@router.get("/{event_id}/collaborators")
def list_collaborators(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = _owned_event(db, event_id, user.id)
    collaborators = db.scalars(
        select(EventCollaborator)
        .where(EventCollaborator.event_id == event_id)
        .order_by(EventCollaborator.id)
    ).all()
    return {
        "items": [_collaborator_view(item, event.ticket_price) for item in collaborators],
        "total": len(collaborators),
    }


@router.post("/{event_id}/collaborators", status_code=201)
def add_collaborator(
    event_id: int,
    payload: CollaboratorCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = _owned_event(db, event_id, user.id)
    allocated = db.scalar(
        select(func.coalesce(func.sum(EventCollaborator.tickets_assigned), 0)).where(
            EventCollaborator.event_id == event_id
        )
    ) or 0
    if allocated + payload.tickets_assigned > event.total_tickets:
        error(
            "ticket_allocation_exceeded",
            "Assigned tickets exceed the event ticket capacity",
            409,
            {"available_tickets": event.total_tickets - allocated},
        )

    contact_query = (
        EventCollaborator.email == payload.email
        if payload.email is not None
        else EventCollaborator.phone == payload.phone
    )
    existing = db.scalar(
        select(EventCollaborator).where(
            EventCollaborator.event_id == event_id,
            contact_query,
        )
    )
    if existing is not None:
        error("collaborator_exists", "This contact is already assigned to the event", 409)

    collaborator = EventCollaborator(event_id=event_id, **payload.model_dump())
    db.add(collaborator)
    db.commit()
    db.refresh(collaborator)
    return _collaborator_view(collaborator, event.ticket_price)


@router.post("/{event_id}/collaborators/{collaborator_id}/sales")
def record_ticket_sales(
    event_id: int,
    collaborator_id: int,
    payload: TicketSalesCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = _owned_event(db, event_id, user.id)
    collaborator = db.scalar(
        select(EventCollaborator).where(
            EventCollaborator.id == collaborator_id,
            EventCollaborator.event_id == event_id,
        )
    )
    if collaborator is None:
        error("collaborator_not_found", "Event collaborator not found", 404)
    remaining = collaborator.tickets_assigned - collaborator.tickets_sold
    if payload.quantity > remaining:
        error(
            "ticket_sales_exceeded",
            "Recorded sales exceed the collaborator's assigned tickets",
            409,
            {"tickets_remaining": remaining},
        )
    collaborator.tickets_sold += payload.quantity
    db.add(collaborator)
    db.commit()
    db.refresh(collaborator)
    return _collaborator_view(collaborator, event.ticket_price)
