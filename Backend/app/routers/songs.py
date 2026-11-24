from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.audio_engine import MAX_AUDIO_BYTES
from app.db import get_db
from app.deps import get_current_user
from app.errors import error
from app.models import Profile, Song, User

router = APIRouter(prefix="/songs", tags=["Song releases"])
logger = logging.getLogger("sounddna")
SONG_STORAGE_DIR = Path(__file__).resolve().parents[2] / "uploads" / "songs"


def _has_mp3_frame(data: bytes) -> bool:
    offset = 0
    if data.startswith(b"ID3"):
        if len(data) < 10 or any(byte & 0x80 for byte in data[6:10]):
            return False
        tag_size = sum(data[index] << shift for index, shift in zip(range(6, 10), (21, 14, 7, 0)))
        offset = 10 + tag_size
        if data[5] & 0x10:
            offset += 10
    if offset + 4 > len(data):
        return False

    header = int.from_bytes(data[offset : offset + 4], "big")
    version = (header >> 19) & 0b11
    layer = (header >> 17) & 0b11
    bitrate_index = (header >> 12) & 0b1111
    sample_rate_index = (header >> 10) & 0b11
    return (
        header >> 21 == 0b11111111111
        and version != 0b01
        and layer != 0
        and bitrate_index not in (0, 0b1111)
        and sample_rate_index != 0b11
    )


async def _read_mp3(audio_file: UploadFile) -> bytes:
    if Path(audio_file.filename or "").suffix.lower() != ".mp3":
        error("invalid_audio", "Audio file must be an MP3", 422)
    content = await audio_file.read(MAX_AUDIO_BYTES + 1)
    if not content:
        error("empty_audio", "Audio file is empty", 422)
    if len(content) > MAX_AUDIO_BYTES:
        error("audio_too_large", "Audio file exceeds the 30 MB upload limit", 413)
    if not _has_mp3_frame(content):
        error("invalid_audio", "Uploaded file does not contain a valid MP3 audio frame", 422)
    return content


def _song_view(song: Song, artist_name: str) -> dict:
    return {
        "id": song.id,
        "title": song.title,
        "artist_name": artist_name,
        "audio_url": f"/songs/{song.id}/audio",
        "audio_size": song.audio_size,
        "created_at": song.created_at,
    }


def _song_rows(db: Session, user_id: int | None = None, limit: int | None = None):
    statement = (
        select(Song, User, Profile)
        .join(User, User.id == Song.user_id)
        .outerjoin(Profile, Profile.user_id == User.id)
        .where(Song.active.is_(True), User.active.is_(True))
        .order_by(Song.created_at.desc(), Song.id.desc())
    )
    if user_id is not None:
        statement = statement.where(Song.user_id == user_id)
    if limit is not None:
        statement = statement.limit(limit)
    return db.exec(statement)


@router.post("", status_code=201)
async def upload_song(
    title: str = Form(min_length=1, max_length=200),
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "artist":
        error("song_upload_forbidden", "Only artists can upload songs", 403)
    title = title.strip()
    if not title:
        error("invalid_title", "Song title cannot be blank", 422)

    content = await _read_mp3(audio_file)
    audio_key = f"{uuid.uuid4().hex}.mp3"
    audio_path = SONG_STORAGE_DIR / audio_key
    try:
        SONG_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(content)
    except OSError:
        logger.exception("Could not store uploaded song audio")
        error("song_storage_unavailable", "Song audio could not be stored", 503)

    song = Song(user_id=user.id, title=title, audio_key=audio_key, audio_size=len(content))
    db.add(song)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        audio_path.unlink(missing_ok=True)
        raise
    db.refresh(song)
    profile = db.exec(select(Profile).where(Profile.user_id == user.id)).first()
    return _song_view(song, profile.display_name if profile else user.name)


@router.get("/recent")
def recent_songs(
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    rows = _song_rows(db, limit=limit).all()
    items = [
        _song_view(song, profile.display_name if profile else artist.name)
        for song, artist, profile in rows
    ]
    return {"items": items, "total": len(items)}


@router.get("/mine")
def my_songs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = _song_rows(db, user.id).all()
    items = [
        _song_view(song, profile.display_name if profile else artist.name)
        for song, artist, profile in rows
    ]
    return {"items": items, "total": len(items)}


@router.get("/{song_id}/audio", response_class=FileResponse)
def play_song(song_id: int, db: Session = Depends(get_db)):
    song = db.get(Song, song_id)
    if song is None or not song.active:
        error("song_not_found", "Song not found", 404)
    audio_path = SONG_STORAGE_DIR / song.audio_key
    if not audio_path.is_file():
        error("song_audio_not_found", "Song audio is unavailable", 404)
    return FileResponse(audio_path, media_type="audio/mpeg")
