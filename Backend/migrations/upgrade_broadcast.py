from sqlalchemy import Engine
from sqlmodel import SQLModel

from app import models  # noqa: F401
from app.database import engine as default_engine


def upgrade(engine: Engine = default_engine) -> None:
    SQLModel.metadata.create_all(engine)
