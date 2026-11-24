from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import error
from app.models import BroadcastDispatch, Profile, Track, User
from app.schemas import BroadcastExecuteIn, BroadcastStatusIn, TrackCreateIn

router = APIRouter(prefix="/api", tags=["Broadcast dispatch"])


def _track_view(track: Track) -> dict:
    return {
        "id": track.id,
        "title": track.title,
        "artist_name": track.artist_name,
        "genre": track.genre,
        "duration_seconds": track.duration_seconds,
        "audio_url": track.audio_url,
        "file_path": track.file_path,
        "is_available": track.is_available,
        "created_at": track.created_at,
    }


def _destination_view(user: User, profile: Profile) -> dict:
    details = profile.details or {}
    if user.role == "dj":
        label = f"DJ — {profile.display_name} ({user.city})"
        medium = "dj"
    else:
        station_name = details.get("station_name") or profile.display_name
        medium = details.get("medium")
        frequency = details.get("frequency")
        label = station_name
        if frequency:
            label += f" ({frequency})"
        if user.city:
            label += f" — {user.city}"
        if medium not in {"radio", "tv", "online"}:
            medium = "radio"

    return {
        "id": user.id,
        "label": label,
        "type": user.role,
        "medium": medium,
        "city": user.city,
        "is_verified": user.verified,
    }


def _dispatch_view(dispatch: BroadcastDispatch, track: Track, destination: User, profile: Profile) -> dict:
    return {
        "id": dispatch.id,
        "sender_id": dispatch.sender_id,
        "track": _track_view(track),
        "destination": _destination_view(destination, profile),
        "destination_label": dispatch.destination_label,
        "note": dispatch.note,
        "status": dispatch.status,
        "sent_at": dispatch.sent_at,
    }


@router.post("/tracks", status_code=201)
def create_track(
    payload: TrackCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in {"artist", "collaborator"}:
        error("track_upload_forbidden", "Only artists or collaborators can register tracks", 403)

    profile = db.exec(select(Profile).where(Profile.user_id == user.id)).first()
    track = Track(
        owner_id=user.id,
        title=payload.title,
        artist_name=payload.artist_name or (profile.display_name if profile else user.name),
        genre=payload.genre,
        duration_seconds=payload.duration_seconds,
        audio_url=payload.audio_url,
        file_path=payload.file_path,
    )
    db.add(track)
    db.commit()
    db.refresh(track)
    return _track_view(track)


@router.get("/tracks/mine")
def my_tracks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tracks = db.exec(
        select(Track)
        .where(Track.owner_id == user.id)
        .order_by(Track.created_at.desc(), Track.id.desc())
    ).scalars().all()
    return {"items": [_track_view(track) for track in tracks], "total": len(tracks)}


@router.get("/broadcast/destinations")
def destinations(
    type: str | None = Query(default=None, pattern="^(broadcaster|dj)$"),
    city: str | None = None,
    verified_only: bool = False,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    statement = (
        select(User, Profile)
        .join(Profile, Profile.user_id == User.id)
        .where(User.active.is_(True), User.role.in_(["broadcaster", "dj"]))
    )
    if type:
        statement = statement.where(User.role == type)
    if city:
        statement = statement.where(func.lower(User.city) == city.strip().lower())
    if verified_only:
        statement = statement.where(User.verified.is_(True))

    rows = db.exec(statement.order_by(User.id)).all()
    items = [_destination_view(user, profile) for user, profile in rows]
    if q:
        query = q.strip().casefold()
        items = [
            item for item in items
            if query in item["label"].casefold()
            or query in item["city"].casefold()
        ]
    return {"items": items, "total": len(items)}


@router.get("/broadcast/tracks")
def available_tracks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tracks = db.exec(
        select(Track)
        .where(Track.owner_id == user.id, Track.is_available.is_(True))
        .order_by(Track.created_at.desc(), Track.id.desc())
    ).scalars().all()
    return {
        "items": [
            {
                "id": track.id,
                "title": track.title,
                "artist_name": track.artist_name,
                "genre": track.genre,
                "audio_url": track.audio_url,
                "file_path": track.file_path,
            }
            for track in tracks
        ],
        "total": len(tracks),
    }


@router.post("/broadcast/execute", status_code=201)
def execute_broadcast(
    payload: BroadcastExecuteIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    track = db.get(Track, payload.track_id)
    if track is None:
        error("track_not_found", "Track not found", 404)
    if track.owner_id != user.id:
        error("track_not_owned", "Track does not belong to the current user", 403)
    if not track.is_available:
        error("track_unavailable", "Track is not available for broadcast", 400)

    destination_ids = (
        [payload.destination_id]
        if payload.destination_id is not None
        else payload.destination_ids
    )
    destination_rows = db.exec(
        select(User, Profile)
        .join(Profile, Profile.user_id == User.id)
        .where(
            User.id.in_(destination_ids),
            User.active.is_(True),
            User.role.in_(["broadcaster", "dj"]),
        )
    ).all()
    destination_by_id = {destination.id: (destination, profile) for destination, profile in destination_rows}
    if len(destination_by_id) != len(destination_ids):
        error("invalid_destination", "One or more destinations are not eligible receivers", 400)

    dispatches = []
    for destination_id in destination_ids:
        destination, profile = destination_by_id[destination_id]
        destination_view = _destination_view(destination, profile)
        dispatch = BroadcastDispatch(
            sender_id=user.id,
            track_id=track.id,
            destination_user_id=destination.id,
            destination_label=destination_view["label"],
            note=payload.note,
            status="sent",
        )
        db.add(dispatch)
        dispatches.append((dispatch, destination, profile))

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    for dispatch, _, _ in dispatches:
        db.refresh(dispatch)

    return {
        "executed": True,
        "dispatches": [
            _dispatch_view(dispatch, track, destination, profile)
            for dispatch, destination, profile in dispatches
        ],
    }


def _dispatch_rows(db: Session, *, sender_id: int | None = None, destination_id: int | None = None):
    statement = (
        select(BroadcastDispatch, Track, User, Profile)
        .join(Track, Track.id == BroadcastDispatch.track_id)
        .join(User, User.id == BroadcastDispatch.destination_user_id)
        .join(Profile, Profile.user_id == User.id)
    )
    if sender_id is not None:
        statement = statement.where(BroadcastDispatch.sender_id == sender_id)
    if destination_id is not None:
        statement = statement.where(BroadcastDispatch.destination_user_id == destination_id)
    return db.exec(statement.order_by(BroadcastDispatch.sent_at.desc(), BroadcastDispatch.id.desc())).all()


@router.get("/broadcast/sent")
def sent_broadcasts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = _dispatch_rows(db, sender_id=user.id)
    return {
        "items": [_dispatch_view(dispatch, track, destination, profile)
                  for dispatch, track, destination, profile in rows],
        "total": len(rows),
    }


@router.get("/broadcast/inbox")
def broadcast_inbox(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = _dispatch_rows(db, destination_id=user.id)
    return {
        "items": [_dispatch_view(dispatch, track, destination, profile)
                  for dispatch, track, destination, profile in rows],
        "total": len(rows),
    }


@router.patch("/broadcast/{dispatch_id}/status")
def update_broadcast_status(
    dispatch_id: int,
    payload: BroadcastStatusIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dispatch = db.get(BroadcastDispatch, dispatch_id)
    if dispatch is None:
        error("dispatch_not_found", "Broadcast dispatch not found", 404)
    if dispatch.destination_user_id != user.id:
        error("dispatch_forbidden", "Only the receiving destination can update this dispatch", 403)
    allowed_statuses = {
        "sent": {"delivered", "declined"},
        "delivered": {"played", "declined"},
    }
    if dispatch.status not in allowed_statuses:
        error("invalid_status_transition", "This dispatch already has a final status", 400)
    if payload.status not in allowed_statuses[dispatch.status]:
        if dispatch.status == "sent" and payload.status == "played":
            error("invalid_status_transition", "A dispatch must be delivered before it can be played", 400)
        error("invalid_status_transition", f"Cannot change status from {dispatch.status} to {payload.status}", 400)

    dispatch.status = payload.status
    db.add(dispatch)
    db.commit()
    db.refresh(dispatch)
    track = db.get(Track, dispatch.track_id)
    destination, profile = db.exec(
        select(User, Profile)
        .join(Profile, Profile.user_id == User.id)
        .where(User.id == dispatch.destination_user_id)
    ).one()
    return _dispatch_view(dispatch, track, destination, profile)
