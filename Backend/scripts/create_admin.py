import argparse
from getpass import getpass

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import User
from app.schemas import normalize_phone
from app.security import hash_pin


def main():
    parser = argparse.ArgumentParser(description="Create an administrator account.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--phone", required=True)
    parser.add_argument("--city", required=True)
    args = parser.parse_args()

    phone = normalize_phone(args.phone)
    pin = getpass("PIN (4-6 digits): ")
    if not pin.isdigit() or not 4 <= len(pin) <= 6:
        parser.error("PIN must contain 4 to 6 digits")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.phone == phone)):
            parser.error("An account already uses this phone number")
        db.add(
            User(
                name=args.name,
                phone=phone,
                pin_hash=hash_pin(pin),
                role="admin",
                city=args.city,
                verified=False,
                active=True,
            )
        )
        db.commit()
    print(f"Administrator created for {phone}.")


if __name__ == "__main__":
    main()
