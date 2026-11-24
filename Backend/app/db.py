from sqlmodel import Session, SQLModel
from sqlalchemy.orm import sessionmaker

from app.database import engine, get_session


Base = SQLModel
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def get_db():
    yield from get_session()
