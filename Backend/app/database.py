from collections.abc import Generator

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


def _create_engine(database_url: str):
    url = make_url(database_url)
    options = {"pool_pre_ping": True}
    if url.drivername.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(database_url, **options)


settings = get_settings()
try:
    engine = _create_engine(settings.database_url)
except ArgumentError:
    engine = _create_engine("sqlite:///./sounddna.db")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
