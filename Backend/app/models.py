from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(sa_type=String(200))
    phone: str = Field(sa_type=String(20), unique=True, index=True)
    pin_hash: str = Field(sa_type=String(255))
    role: str = Field(sa_type=String(30), index=True)
    city: str = Field(sa_type=String(100))
    verified: bool = Field(default=False, sa_type=Boolean, index=True)
    active: bool = Field(default=True, sa_type=Boolean)
    failed_attempts: int = Field(default=0, sa_type=Integer)
    locked_until: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, sa_type=DateTime(timezone=True)
    )
    @property
    def is_verified(self) -> bool:
        return self.verified

    @is_verified.setter
    def is_verified(self, value: bool) -> None:
        self.verified = value


class Profile(SQLModel, table=True):
    __tablename__ = "profiles"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)
    display_name: str = Field(sa_type=String(200))
    bio: str = Field(default="", sa_type=String(500))
    genres: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    photo_url: str | None = Field(default=None, sa_type=String(2048))
    social_links: dict[str, str] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    details: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))


class VerificationRequest(SQLModel, table=True):
    __tablename__ = "verification_requests"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    evidence_text: str = Field(sa_type=Text)
    evidence_url: str | None = Field(default=None, sa_type=String(2048))
    status: str = Field(default="pending", sa_type=String(20), index=True)
    note: str | None = Field(default=None, sa_type=Text)
    decided_by: int | None = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_type=DateTime(timezone=True))
    decided_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))


class Follow(SQLModel, table=True):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_id", "artist_id", name="uq_follow"),)

    id: int | None = Field(default=None, primary_key=True)
    follower_id: int = Field(foreign_key="users.id", index=True)
    artist_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_type=DateTime(timezone=True))


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: int | None = Field(default=None, primary_key=True)
    actor_id: int = Field(foreign_key="users.id", index=True)
    action: str = Field(sa_type=String(100))
    target: str = Field(sa_type=String(100))
    timestamp: datetime = Field(default_factory=datetime.utcnow, sa_type=DateTime(timezone=True))


class ViralBenchmark(SQLModel, table=True):
    __tablename__ = "viral_benchmarks"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str = Field(sa_type=String(200))
    genre: str = Field(sa_type=String(100), index=True)
    broadcast_stations_count: int = Field(default=0, ge=0)
    viral_reach_notes: str = Field(default="", sa_type=Text)
    audio_filename: str = Field(sa_type=String(255))
    musical_key: str = Field(sa_type=String(10))
    key_index: int = Field(ge=0, le=11)
    tempo_bpm: float = Field(gt=0)
    flow_density: float = Field(ge=0)
    power_score: float = Field(ge=0, le=100)
    rms_energy: float = Field(ge=0)
    brightness_hz: float = Field(ge=0)
    hook_timestamp_sec: float = Field(ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_type=DateTime(timezone=True))


class DemoAnalysis(SQLModel, table=True):
    __tablename__ = "demo_analyses"
    __table_args__ = (
        UniqueConstraint("user_id", "demo_title", "version_number", name="uq_demo_version"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    benchmark_id: int = Field(foreign_key="viral_benchmarks.id", index=True)
    demo_title: str = Field(sa_type=String(200), index=True)
    version_number: int = Field(ge=1)
    audio_filename: str = Field(sa_type=String(255))
    musical_key: str = Field(sa_type=String(10))
    key_index: int = Field(ge=0, le=11)
    tempo_bpm: float = Field(gt=0)
    flow_density: float = Field(ge=0)
    power_score: float = Field(ge=0, le=100)
    rms_energy: float = Field(ge=0)
    brightness_hz: float = Field(ge=0)
    hook_timestamp_sec: float = Field(ge=0)
    tone_match: float = Field(ge=0, le=100)
    flow_match: float = Field(ge=0, le=100)
    power_match: float = Field(ge=0, le=100)
    hook_timing_match: float = Field(ge=0, le=100)
    hit_readiness_score: float = Field(ge=0, le=100)
    verdict: str = Field(sa_type=String(40))
    studio_fixes: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_type=DateTime(timezone=True))


class TrackRelease(SQLModel, table=True):
    __tablename__ = "track_releases"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    benchmark_id: int = Field(foreign_key="viral_benchmarks.id", index=True)
    title: str = Field(sa_type=String(200))
    release_date: datetime = Field(default_factory=datetime.utcnow, sa_type=DateTime(timezone=True))
    active: bool = Field(default=True, sa_type=Boolean)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_type=DateTime(timezone=True))


class TicketEvent(SQLModel, table=True):
    __tablename__ = "ticket_events"

    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id", index=True)
    title: str = Field(sa_type=String(200))
    event_date: datetime = Field(sa_type=DateTime(timezone=True))
    venue: str = Field(sa_type=String(200))
    ticket_price: Decimal = Field(gt=0, sa_type=Numeric(10, 2))
    total_tickets: int = Field(gt=0)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_type=DateTime(timezone=True))


class EventCollaborator(SQLModel, table=True):
    __tablename__ = "event_collaborators"
    __table_args__ = (
        UniqueConstraint("event_id", "email", name="uq_event_collaborator_email"),
        UniqueConstraint("event_id", "phone", name="uq_event_collaborator_phone"),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="ticket_events.id", index=True)
    name: str = Field(sa_type=String(200))
    email: str | None = Field(default=None, sa_type=String(254))
    phone: str | None = Field(default=None, sa_type=String(32))
    commission_percent: Decimal = Field(ge=0, le=100, sa_type=Numeric(5, 2))
    tickets_assigned: int = Field(gt=0)
    tickets_sold: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_type=DateTime(timezone=True))


class Song(SQLModel, table=True):
    __tablename__ = "songs"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str = Field(sa_type=String(200))
    audio_key: str = Field(sa_type=String(40), unique=True)
    audio_size: int = Field(gt=0)
    active: bool = Field(default=True, sa_type=Boolean, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_type=DateTime(timezone=True))


class AirplayLog(SQLModel, table=True):
    __tablename__ = "airplay_logs"

    id: int | None = Field(default=None, primary_key=True)
    release_id: int = Field(foreign_key="track_releases.id", index=True)
    reporter_id: int = Field(foreign_key="users.id", index=True)
    city: str = Field(sa_type=String(100), index=True)
    outlet_name: str = Field(sa_type=String(200))
    spins_count: int = Field(gt=0)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_type=DateTime(timezone=True))


class CanarySignalSnapshot(SQLModel, table=True):
    __tablename__ = "canary_signal_snapshots"
    __table_args__ = (
        UniqueConstraint("release_id", "week_number", name="uq_release_week_snapshot"),
    )

    id: int | None = Field(default=None, primary_key=True)
    release_id: int = Field(foreign_key="track_releases.id", index=True)
    week_number: int = Field(ge=1)
    weekly_streams: int = Field(ge=0)
    radio_tv_spins: int = Field(ge=0)
    early_skip_rate_pct: float = Field(ge=0, le=100)
    social_mentions: int = Field(ge=0)
    top_city: str = Field(sa_type=String(100), index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_type=DateTime(timezone=True))


class AdvisorInsight(SQLModel, table=True):
    __tablename__ = "advisor_insights"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "category", name="uq_snapshot_insight_category"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    release_id: int = Field(foreign_key="track_releases.id", index=True)
    snapshot_id: int | None = Field(default=None, foreign_key="canary_signal_snapshots.id")
    category: str = Field(sa_type=String(40), index=True)
    priority: str = Field(sa_type=String(20), index=True)
    title: str = Field(sa_type=String(200))
    recommendation: str = Field(sa_type=Text)
    acknowledged: bool = Field(default=False, sa_type=Boolean, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_type=DateTime(timezone=True))
