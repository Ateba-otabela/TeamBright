from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, Profile

router = APIRouter(tags=["directory"])

@router.get("/directory")
def directory(role: str | None = None, city: str | None = None, genre: str | None = None,
              verified: bool | None = None, q: str | None = None,
              limit: int = Query(default=20, ge=1, le=50), offset: int = Query(default=0, ge=0),
              db: Session = Depends(get_db)):
    statement = select(User, Profile).join(Profile, Profile.user_id == User.id).where(
        User.active.is_(True), User.role.in_(["artist", "dj", "broadcaster", "promoter"])
    )
    if role:
        statement = statement.where(User.role == role)
    if city:
        statement = statement.where(func.lower(User.city) == city.lower())
    if verified is not None:
        statement = statement.where(User.verified.is_(verified))
    if genre:
        genre_values = func.json_each(Profile.genres).table_valued("key", "value").alias("genre_values")
        statement = statement.where(
            select(1).select_from(genre_values)
            .where(func.lower(genre_values.c.value) == genre.strip().lower())
            .exists()
        )
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(Profile.display_name.ilike("%" + escaped + "%", escape="\\"))

    count_statement = select(func.count()).select_from(statement.subquery())
    total = db.scalar(count_statement) or 0
    statement = statement.order_by(User.id).limit(limit).offset(offset)
    rows = db.execute(statement).all()
    items = [{"id": user.id, "display_name": profile.display_name, "role": user.role,
              "city": user.city, "verified": user.verified, "bio": profile.bio,
              "genres": profile.genres, "photo_url": profile.photo_url,
              "links": profile.social_links, "details": profile.details}
             for user, profile in rows]
    return {"total": total, "items": items, "limit": limit, "offset": offset}
