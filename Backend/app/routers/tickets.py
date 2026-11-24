from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import error
from app.models import Event, Ticket, TicketClaim, User
from app.schemas import TicketCreateIn, TicketOut

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post(
    "",
    response_model=TicketOut,
    status_code=201,
    summary="Create a ticket listing",
    description=(
        "Create active free or paid tickets. Set price_xaf to 0 for a giveaway or a positive "
        "XAF amount for paid tickets. The authenticated user must have the artist role."
    ),
)
def create_ticket(
    payload: TicketCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "artist":
        error("ticket_forbidden", "Only artists can create tickets", 403)

    event = None
    if payload.event_id is not None:
        event = db.get(Event, payload.event_id)
        if not event:
            error("not_found", "Event not found", 404)
        if event.artist_id != user.id:
            error("event_forbidden", "You can only create tickets for your own events", 403)

    ticket = Ticket(
        artist_id=user.id,
        event_id=event.id if event else None,
        event_name=event.event_name if event else payload.event_name,
        total_quantity=payload.total_quantity,
        remaining_quantity=payload.total_quantity,
        price_xaf=payload.price_xaf,
        description=payload.description,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get(
    "/my",
    summary="List my ticket listings",
    description="Return the authenticated artist's tickets, including prices and remaining quantities.",
)
def my_tickets(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    if user.role != "artist":
        error("ticket_forbidden", "Only artists can view their tickets", 403)
    return _list_tickets(
        db,
        artist_id=user.id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "",
    summary="List ticket listings",
    description=(
        "Search ticket listings by event, event name, status, or artist. Results are paginated."
    ),
)
def list_tickets(
    event_name: str | None = None,
    event_id: int | None = None,
    status: Literal["active", "closed", "expired"] | None = None,
    artist_id: int | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return _list_tickets(
        db,
        event_name=event_name,
        event_id=event_id,
        status=status,
        artist_id=artist_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{ticket_id}",
    response_model=TicketOut,
    summary="Get a ticket listing",
)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        error("not_found", "Ticket not found", 404)
    return ticket


@router.post(
    "/{ticket_id}/claim",
    response_model=TicketOut,
    summary="Claim a ticket",
    description=(
        "Claim one available free ticket. Paid tickets must use Fapshi checkout. "
        "Authentication is required, and each user may claim at most once per listing."
    ),
)
def claim_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        error("not_found", "Ticket not found", 404)
    if ticket.price_xaf > 0:
        error("payment_required", "Paid tickets must be purchased through checkout", 402)

    existing = db.scalar(
        select(TicketClaim).where(
            TicketClaim.ticket_id == ticket_id,
            TicketClaim.user_id == user.id,
        )
    )
    if existing:
        error("ticket_already_claimed", "You have already claimed this ticket", 409)

    result = db.execute(
        update(Ticket)
        .where(
            Ticket.id == ticket_id,
            Ticket.status == "active",
            Ticket.remaining_quantity > 0,
        )
        .values(
            remaining_quantity=Ticket.remaining_quantity - 1,
            status=case(
                (Ticket.remaining_quantity == 1, "closed"),
                else_=Ticket.status,
            ),
        )
    )
    if result.rowcount != 1:
        error("ticket_unavailable", "No tickets are available to claim", 409)

    db.add(TicketClaim(ticket_id=ticket_id, user_id=user.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = db.scalar(
            select(TicketClaim).where(
                TicketClaim.ticket_id == ticket_id,
                TicketClaim.user_id == user.id,
            )
        )
        if duplicate:
            error("ticket_already_claimed", "You have already claimed this ticket", 409)
        raise

    db.refresh(ticket)
    return ticket


def _list_tickets(
    db: Session,
    *,
    event_name: str | None = None,
    event_id: int | None = None,
    status: str | None = None,
    artist_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
):
    statement = select(Ticket)
    if event_name:
        escaped = event_name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(
            Ticket.event_name.ilike("%" + escaped + "%", escape="\\")
        )
    if event_id is not None:
        statement = statement.where(Ticket.event_id == event_id)
    if status:
        statement = statement.where(Ticket.status == status)
    if artist_id is not None:
        statement = statement.where(Ticket.artist_id == artist_id)

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    items = db.scalars(
        statement.order_by(Ticket.created_at.desc(), Ticket.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "total": total,
        "items": [TicketOut.model_validate(ticket) for ticket in items],
        "limit": limit,
        "offset": offset,
    }
