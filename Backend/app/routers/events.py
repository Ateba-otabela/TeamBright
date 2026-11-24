from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import error
from app.models import Event, EventCollaborator, User
from app.schemas import EventCollaboratorIn, EventCollaboratorOut, EventCreateIn, EventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "",
    response_model=EventOut,
    status_code=201,
    summary="Create an event",
    description="Create an event record. The authenticated user must have the artist role.",
)
def create_event(
    payload: EventCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "artist":
        error("event_forbidden", "Only artists can create events", 403)

    event = Event(artist_id=user.id, **payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get(
    "",
    summary="List events",
    description="List public events, with optional event-name and artist filters.",
)
def list_events(
    event_name: str | None = None,
    artist_id: int | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    statement = select(Event)
    if event_name:
        escaped = event_name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(
            Event.event_name.ilike("%" + escaped + "%", escape="\\")
        )
    if artist_id is not None:
        statement = statement.where(Event.artist_id == artist_id)

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    items = db.scalars(
        statement.order_by(Event.event_date.asc(), Event.id.asc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "total": total,
        "items": [EventOut.model_validate(event) for event in items],
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/my-collaborations",
    summary="List my collaborations",
    description="List events the authenticated collaborator has been assigned to view.",
)
def my_collaborations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    if user.role != "collaborator":
        error("collaborator_forbidden", "Collaborator access required", 403)

    statement = (
        select(Event)
        .join(EventCollaborator, EventCollaborator.event_id == Event.id)
        .where(EventCollaborator.user_id == user.id)
    )
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    items = db.scalars(
        statement.order_by(Event.event_date.asc(), Event.id.asc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "total": total,
        "items": [EventOut.model_validate(event) for event in items],
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{event_id}",
    response_model=EventOut,
    summary="Get an event",
)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if not event:
        error("not_found", "Event not found", 404)
    return event


@router.post(
    "/{event_id}/collaborators",
    response_model=EventCollaboratorOut,
    status_code=201,
    summary="Add an event collaborator",
    description=(
        "Assign an existing active user with the collaborator role to an event. "
        "Only the event's owning artist can add collaborators."
    ),
)
def add_collaborator(
    event_id: int,
    payload: EventCollaboratorIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = _get_event(db, event_id)
    _require_event_owner(event, user)
    collaborator = db.get(User, payload.user_id)
    if not collaborator or not collaborator.active:
        error("collaborator_not_found", "Active collaborator account not found", 404)
    if collaborator.role != "collaborator":
        error("invalid_collaborator", "User must have the collaborator role", 422)

    association = db.scalar(
        select(EventCollaborator).where(
            EventCollaborator.event_id == event_id,
            EventCollaborator.user_id == collaborator.id,
        )
    )
    if association:
        error("collaborator_exists", "User is already assigned to this event", 409)

    association = EventCollaborator(event_id=event_id, user_id=collaborator.id)
    db.add(association)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = db.scalar(
            select(EventCollaborator).where(
                EventCollaborator.event_id == event_id,
                EventCollaborator.user_id == collaborator.id,
            )
        )
        if duplicate:
            error("collaborator_exists", "User is already assigned to this event", 409)
        raise

    db.refresh(association)
    return EventCollaboratorOut(
        user_id=collaborator.id,
        name=collaborator.name,
        created_at=association.created_at,
    )


@router.get(
    "/{event_id}/collaborators",
    response_model=list[EventCollaboratorOut],
    summary="List event collaborators",
    description="The owning artist and assigned collaborators can view the collaborator list.",
)
def list_collaborators(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = _get_event(db, event_id)
    if user.id != event.artist_id:
        assigned = db.scalar(
            select(EventCollaborator.id).where(
                EventCollaborator.event_id == event_id,
                EventCollaborator.user_id == user.id,
            )
        )
        if not assigned:
            error("event_forbidden", "You are not assigned to this event", 403)

    rows = db.execute(
        select(EventCollaborator, User)
        .join(User, User.id == EventCollaborator.user_id)
        .where(EventCollaborator.event_id == event_id)
        .order_by(User.id)
    ).all()
    return [
        EventCollaboratorOut(
            user_id=association.user_id,
            name=collaborator.name,
            created_at=association.created_at,
        )
        for association, collaborator in rows
    ]


@router.delete(
    "/{event_id}/collaborators/{collaborator_id}",
    summary="Remove an event collaborator",
    description="Only the event's owning artist can remove a collaborator.",
)
def remove_collaborator(
    event_id: int,
    collaborator_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = _get_event(db, event_id)
    _require_event_owner(event, user)
    association = db.scalar(
        select(EventCollaborator).where(
            EventCollaborator.event_id == event_id,
            EventCollaborator.user_id == collaborator_id,
        )
    )
    if not association:
        error("not_found", "Event collaborator not found", 404)

    db.delete(association)
    db.commit()
    return {"event_id": event_id, "user_id": collaborator_id, "assigned": False}


def _get_event(db: Session, event_id: int) -> Event:
    event = db.get(Event, event_id)
    if not event:
        error("not_found", "Event not found", 404)
    return event


def _require_event_owner(event: Event, user: User):
    if user.role != "artist" or event.artist_id != user.id:
        error("event_forbidden", "Only the event owner can manage collaborators", 403)
