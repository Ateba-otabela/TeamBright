from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import error
from app.models import User, Follow

router = APIRouter(tags=["follows"])

@router.post("/follows/{artist_id}")
def follow(artist_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if artist_id == user.id:
        error("invalid_follow", "You cannot follow yourself", 400)
    artist = db.get(User, artist_id)
    if not artist or artist.role != "artist" or not artist.active:
        error("artist_not_found", "Artist not found", 404)
    existing = db.scalar(select(Follow).where(Follow.follower_id == user.id, Follow.artist_id == artist_id))
    if not existing:
        db.add(Follow(follower_id=user.id, artist_id=artist_id))
        db.commit()
    return {"artist_id": artist_id, "following": True}

@router.delete("/follows/{artist_id}")
def unfollow(artist_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    existing = db.scalar(select(Follow).where(Follow.follower_id == user.id, Follow.artist_id == artist_id))
    if existing:
        db.delete(existing)
        db.commit()
    return {"artist_id": artist_id, "following": False}

@router.get("/me/following")
def following(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(select(User).join(Follow, Follow.artist_id == User.id)
                      .where(Follow.follower_id == user.id).order_by(User.id)).scalars().all()
    return {"items": [{"id": item.id, "name": item.name, "role": item.role, "verified": item.verified} for item in rows],
            "total": len(rows)}

@router.get("/artists/{id}/followers")
def follower_count(id: int, db: Session = Depends(get_db)):
    artist = db.get(User, id)
    if not artist or artist.role != "artist":
        error("artist_not_found", "Artist not found", 404)
    count = db.scalar(select(func.count()).select_from(Follow).where(Follow.artist_id == id)) or 0
    return {"artist_id": id, "followers": count}
