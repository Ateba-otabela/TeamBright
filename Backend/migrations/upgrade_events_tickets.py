from __future__ import annotations

from sqlalchemy import Engine, inspect, text
from sqlmodel import SQLModel

from app import models  # noqa: F401
from app.database import engine as default_engine


_ADDITIONS = {
    "ticket_events": {
        "category": "VARCHAR(30) NOT NULL DEFAULT 'other'",
        "city": "VARCHAR(100) NOT NULL DEFAULT ''",
        "artist_momo_number": "VARCHAR(32) NOT NULL DEFAULT ''",
        "status": "VARCHAR(20) NOT NULL DEFAULT 'approved'",
        "minted_count": "INTEGER NOT NULL DEFAULT 0",
    },
    "event_collaborators": {
        "user_id": "INTEGER REFERENCES users(id)",
        "promo_code": "VARCHAR(40)",
        "assigned_quota": "INTEGER NOT NULL DEFAULT 0",
        "allow_over_quota": "BOOLEAN NOT NULL DEFAULT FALSE",
        "sold_count": "INTEGER NOT NULL DEFAULT 0",
        "status": "VARCHAR(20) NOT NULL DEFAULT 'pending'",
    },
}


def upgrade(engine: Engine = default_engine) -> None:
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table, columns in _ADDITIONS.items():
            if not inspector.has_table(table):
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            quoted_table = engine.dialect.identifier_preparer.quote(table)
            for name, declaration in columns.items():
                if name in existing:
                    continue
                quoted_name = engine.dialect.identifier_preparer.quote(name)
                connection.execute(
                    text(
                        f"ALTER TABLE {quoted_table} ADD COLUMN "
                        f"{quoted_name} {declaration}"
                    )
                )
        if inspector.has_table("event_collaborators"):
            connection.execute(
                text(
                    "UPDATE event_collaborators "
                    "SET assigned_quota = tickets_assigned, sold_count = tickets_sold "
                    "WHERE assigned_quota = 0 AND tickets_assigned > 0"
                )
            )
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "uq_event_collaborator_user ON event_collaborators(event_id, user_id)"
                )
            )
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "uq_event_collaborator_promo ON event_collaborators(event_id, promo_code)"
                )
            )
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    upgrade()
