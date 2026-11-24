from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session

from app.config import get_settings
from app.models import EventCollaborator, Ticket, TicketEvent, TicketTier

CENT = Decimal("0.01")


def _sign_ticket_code(ticket_code: str, nonce: str) -> str:
    secret = get_settings().jwt_secret.encode("utf-8")
    message = f"{ticket_code}.{nonce}".encode("ascii")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def create_qr_token(ticket_code: str) -> str:
    nonce = secrets.token_urlsafe(12)
    signature = _sign_ticket_code(ticket_code, nonce)
    return f"{ticket_code}.{nonce}.{signature}"


def is_valid_qr_token(ticket_code: str, token: str) -> bool:
    try:
        token_code, nonce, signature = token.split(".", 2)
    except ValueError:
        return False
    expected = _sign_ticket_code(token_code, nonce)
    return token_code == ticket_code and hmac.compare_digest(signature, expected)


def mint_ticket_batch(
    db: Session, event: TicketEvent, tier: TicketTier, quantity: int
) -> list[dict]:
    event_claim = db.execute(
        update(TicketEvent)
        .where(
            TicketEvent.id == event.id,
            TicketEvent.minted_count + quantity <= TicketEvent.total_tickets,
        )
        .values(minted_count=TicketEvent.minted_count + quantity)
        .returning(TicketEvent.id)
    ).scalar_one_or_none()
    if event_claim is None:
        db.rollback()
        raise ValueError("event_seat_limit")
    tier_claim = db.execute(
        update(TicketTier)
        .where(
            TicketTier.id == tier.id,
            TicketTier.minted_count + quantity <= TicketTier.quantity,
        )
        .values(minted_count=TicketTier.minted_count + quantity)
        .returning(TicketTier.id)
    ).scalar_one_or_none()
    if tier_claim is None:
        db.rollback()
        raise ValueError("tier_quantity_limit")

    records = []
    for _ in range(quantity):
        code = f"EVT-{secrets.token_hex(4).upper()}"
        records.append(
            {
                "ticket_code": code,
                "qr_token": create_qr_token(code),
                "tier_id": tier.id,
                "event_id": event.id,
                "status": "available",
                "amount_paid": Decimal("0"),
            }
        )
    dialect = db.get_bind().dialect.name
    insert_stmt = sqlite_insert(Ticket) if dialect == "sqlite" else pg_insert(Ticket)
    db.execute(insert_stmt, records)
    db.commit()
    return records


def purchase_ticket(
    db: Session,
    event_id: int,
    tier_id: int,
    buyer_name: str,
    buyer_phone: str,
    payment_ref: str,
    promo_code: str | None,
) -> Ticket | None:
    event = db.scalar(
        select(TicketEvent)
        .where(TicketEvent.id == event_id)
        .with_for_update()
    )
    if event is None or event.status != "approved":
        return None
    tier = db.scalar(
        select(TicketTier).where(
            TicketTier.id == tier_id,
            TicketTier.event_id == event_id,
        )
    )
    if tier is None:
        return None
    if db.scalar(select(Ticket.id).where(Ticket.payment_ref == payment_ref)):
        raise ValueError("payment_ref_exists")

    collaborator = None
    if promo_code:
        collaborator = db.scalar(
            select(EventCollaborator)
            .where(
                EventCollaborator.event_id == event_id,
                EventCollaborator.promo_code == promo_code.strip().upper(),
                EventCollaborator.status == "accepted",
                EventCollaborator.user_id.is_not(None),
            )
            .with_for_update()
        )
        if collaborator is None:
            raise ValueError("invalid_promo_code")
        if (
            not collaborator.allow_over_quota
            and collaborator.sold_count >= collaborator.assigned_quota
        ):
            raise ValueError("collaborator_quota_exceeded")

    ticket_id_query = (
        select(Ticket.id)
        .where(Ticket.tier_id == tier_id, Ticket.status == "available")
        .order_by(Ticket.id)
        .limit(1)
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )
    claimed_id = db.execute(
        update(Ticket)
        .where(Ticket.id == ticket_id_query, Ticket.status == "available")
        .values(
            status="sold",
            buyer_name=buyer_name,
            buyer_phone=buyer_phone,
            amount_paid=tier.price,
            payment_ref=payment_ref,
            collaborator_id=collaborator.id if collaborator else None,
        )
        .returning(Ticket.id)
    ).scalar_one_or_none()
    if claimed_id is None:
        db.rollback()
        return None

    if collaborator is not None:
        updated = db.execute(
            update(EventCollaborator)
            .where(
                EventCollaborator.id == collaborator.id,
                (
                    EventCollaborator.allow_over_quota.is_(True)
                    | (
                        EventCollaborator.sold_count
                        < EventCollaborator.assigned_quota
                    )
                ),
            )
            .values(
                sold_count=EventCollaborator.sold_count + 1,
                tickets_sold=EventCollaborator.tickets_sold + 1,
            )
            .returning(EventCollaborator.id)
        ).scalar_one_or_none()
        if updated is None:
            db.rollback()
            raise ValueError("collaborator_quota_exceeded")

    ticket = db.get(Ticket, claimed_id)
    db.flush()
    return ticket


def checked_in_now() -> datetime:
    return datetime.now(timezone.utc)
