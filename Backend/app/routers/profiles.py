from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, get_optional_user
from app.errors import error
from app.models import User, Profile
from app.schemas import ProfileIn

router = APIRouter(tags=["profiles"])

_ROLE_FIELDS = {
    "artist": ("stage_name", "manager_phone", "languages"),
    "dj": ("dj_type", "venues"),
    "broadcaster": ("station_name", "medium", "frequency", "coverage_cities"),
    "promoter": ("company_name", "venue_names"),
}

@router.put("/profile")
def put_profile(payload: ProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role in ("fan", "collaborator"):
        error("profile_forbidden", "This role cannot create a public profile", 403)

    data = payload.model_dump(exclude_none=True)
    if user.role == "artist":
        if not data.get("stage_name"):
            data["stage_name"] = payload.display_name
    elif user.role == "dj":
        if not data.get("dj_type"):
            error("validation_error", "Validation failed", 422, {"fields": [{"field": "dj_type", "message": "required for dj"}]})
    elif user.role == "broadcaster":
        if not data.get("station_name"):
            error("validation_error", "Validation failed", 422, {"fields": [{"field": "station_name", "message": "required for broadcaster"}]})
    elif user.role == "promoter":
        if not data.get("company_name"):
            error("validation_error", "Validation failed", 422, {"fields": [{"field": "company_name", "message": "required for promoter"}]})
    else:
        error("profile_forbidden", "This role cannot create a public profile", 403)

    details = {key: data[key] for key in _ROLE_FIELDS[user.role] if key in data}
    profile = user.profile or Profile(user_id=user.id)
    profile.display_name = payload.display_name
    profile.bio = payload.bio
    profile.genres = payload.genres
    profile.photo_url = payload.photo_url
    profile.social_links = payload.social_links.model_dump(exclude_none=True)
    profile.details = details
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile_view(profile, user, include_phone=True)

@router.get("/profiles/{user_id}")
def get_profile(user_id: int, db: Session = Depends(get_db), viewer: User | None = Depends(get_optional_user)):
    user = db.get(User, user_id)
    if not user or not user.profile:
        error("not_found", "Profile not found", 404)
    include_phone = viewer is not None and (viewer.id == user.id or viewer.role == "admin")
    return profile_view(user.profile, user, include_phone)


def profile_view(profile: Profile, user: User, include_phone: bool):
    result = {"id": user.id, "display_name": profile.display_name, "role": user.role, "city": user.city,
              "verified": user.verified, "active": user.active, "bio": profile.bio, "genres": profile.genres,
              "photo_url": profile.photo_url, "links": profile.social_links, "details": profile.details}
    if include_phone:
        result["phone"] = user.phone
    return result
