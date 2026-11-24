from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import Session

from app.db import Base, get_db
from app.database import engine as default_engine, get_session
from app.main import app


class FrozenClock:
    def __init__(self):
        self.current = datetime.now(timezone.utc)

    def now(self):
        return self.current

    def advance(self, delta: timedelta):
        self.current += delta


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_sessions = sessionmaker(
        bind=engine, class_=Session, autoflush=False, expire_on_commit=False
    )

    def override_get_db():
        db = test_sessions()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session] = override_get_db
    app.state.database_engine = engine
    yield test_sessions
    app.dependency_overrides.clear()
    app.state.database_engine = default_engine
    engine.dispose()


@pytest.fixture
def client(test_db):
    clock = FrozenClock()
    app.state.clock = clock
    with TestClient(app) as test_client:
        test_client.clock = clock
        yield test_client
    app.state.clock = None
