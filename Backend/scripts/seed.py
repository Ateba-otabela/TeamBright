import os

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import Profile, User
from app.security import hash_pin
from app.schemas import normalize_phone


DEMO_ACCOUNTS = [
    {
        "name": "Bantu Music Demo Admin",
        "phone": "+237690000001",
        "role": "admin",
        "city": "Yaoundé",
    },
    {
        "name": "Demo Makossa Artist",
        "phone": "+237690000002",
        "role": "artist",
        "city": "Douala",
        "genres": ["makossa"],
        "details": {"stage_name": "Demo Makossa Artist", "languages": ["French", "Duala"]},
    },
    {
        "name": "Demo Bikutsi Artist",
        "phone": "+237690000003",
        "role": "artist",
        "city": "Yaoundé",
        "genres": ["bikutsi"],
        "details": {"stage_name": "Demo Bikutsi Artist", "languages": ["French", "Ewondo"]},
    },
    {
        "name": "Demo Afrobeats Artist",
        "phone": "+237690000004",
        "role": "artist",
        "city": "Buea",
        "genres": ["afrobeats"],
        "details": {"stage_name": "Demo Afrobeats Artist", "languages": ["English", "Pidgin"]},
    },
    {
        "name": "Demo Ambasse Bey Artist",
        "phone": "+237690000005",
        "role": "artist",
        "city": "Bamenda",
        "genres": ["ambasse bey"],
        "details": {"stage_name": "Demo Ambasse Bey Artist", "languages": ["English"]},
    },
    {
        "name": "Demo Bend Skin Artist",
        "phone": "+237690000006",
        "role": "artist",
        "city": "Douala",
        "genres": ["bend skin"],
        "details": {"stage_name": "Demo Bend Skin Artist", "languages": ["French"]},
    },
    {
        "name": "Demo Cameroon Artist",
        "phone": "+237690000007",
        "role": "artist",
        "city": "Buea",
        "genres": ["makossa", "afrobeats"],
        "details": {"stage_name": "Demo Cameroon Artist", "languages": ["English", "French"]},
    },
    {
        "name": "Demo Club DJ",
        "phone": "+237690000008",
        "role": "dj",
        "city": "Douala",
        "genres": ["afrobeats"],
        "details": {"dj_type": "club", "venues": ["DEMO venue"]},
    },
    {
        "name": "Demo Radio DJ",
        "phone": "+237690000009",
        "role": "dj",
        "city": "Yaoundé",
        "genres": ["bikutsi"],
        "details": {"dj_type": "radio", "venues": ["DEMO station"]},
    },
    {
        "name": "Demo Event DJ",
        "phone": "+237690000010",
        "role": "dj",
        "city": "Buea",
        "genres": ["makossa"],
        "details": {"dj_type": "event", "venues": ["DEMO event space"]},
    },
    {
        "name": "CRTV Demo Station",
        "phone": "+237690000011",
        "role": "broadcaster",
        "city": "Yaoundé",
        "genres": ["radio"],
        "details": {
            "station_name": "CRTV Demo Station",
            "medium": "radio",
            "coverage_cities": ["Yaoundé"],
        },
    },
    {
        "name": "Buea Demo Radio",
        "phone": "+237690000012",
        "role": "broadcaster",
        "city": "Buea",
        "genres": ["radio"],
        "details": {
            "station_name": "Buea Demo Radio",
            "medium": "radio",
            "coverage_cities": ["Buea"],
        },
    },
    {
        "name": "Douala Demo Radio",
        "phone": "+237690000013",
        "role": "broadcaster",
        "city": "Douala",
        "genres": ["radio"],
        "details": {
            "station_name": "Douala Demo Radio",
            "medium": "radio",
            "coverage_cities": ["Douala"],
        },
    },
    {
        "name": "Demo Events Company",
        "phone": "+237690000014",
        "role": "promoter",
        "city": "Douala",
        "genres": ["events"],
        "details": {"company_name": "Demo Events Company", "venue_names": ["DEMO venue"]},
    },
    {
        "name": "Demo Buea Promoter",
        "phone": "+237690000015",
        "role": "promoter",
        "city": "Buea",
        "genres": ["events"],
        "details": {"company_name": "Demo Buea Promoter", "venue_names": ["DEMO venue"]},
    },
    *[
        {
            "name": f"Demo Fan {number}",
            "phone": f"+2376900000{15 + number:02d}",
            "role": "fan",
            "city": city,
        }
        for number, city in enumerate(
            ["Douala", "Yaoundé", "Buea", "Bamenda", "Douala"], start=1
        )
    ],
]


def seed() -> int:
    pin = os.getenv("DEMO_PIN", "1234")
    if not pin.isdigit() or not 4 <= len(pin) <= 6:
        raise ValueError("DEMO_PIN must contain 4 to 6 digits")

    Base.metadata.create_all(bind=engine)
    created = 0
    with SessionLocal() as db:
        for account in DEMO_ACCOUNTS:
            phone = normalize_phone(account["phone"])
            user = db.scalar(select(User).where(User.phone == phone))
            if user is None:
                user = User(
                    name=account["name"],
                    phone=phone,
                    pin_hash=hash_pin(pin),
                    role=account["role"],
                    city=account["city"],
                    verified=False,
                    active=True,
                )
                db.add(user)
                db.flush()
                created += 1
            elif user.role != account["role"]:
                raise ValueError(f"Existing account {phone} has a different role")

            if user.role in {"artist", "dj", "broadcaster", "promoter"}:
                details = account["details"]
                profile = user.profile or Profile(user_id=user.id)
                profile.display_name = account["name"]
                profile.bio = "DEMO account for local development; not an endorsement."
                profile.genres = account.get("genres", [])
                profile.social_links = {}
                profile.photo_url = None
                profile.details = details
                db.add(profile)
        db.commit()
    return created


if __name__ == "__main__":
    print(f"Seeded {seed()} new demo accounts; all seeded accounts remain unverified.")
