from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.database import engine
from app.models import (
    AdvisorInsight,
    AirplayLog,
    CanarySignalSnapshot,
    TrackRelease,
    ViralBenchmark,
)


def evaluate_release(db: Session, release_id: int) -> list[AdvisorInsight]:
    release = db.get(TrackRelease, release_id)
    if release is None:
        return []
    snapshots = db.scalars(
        select(CanarySignalSnapshot)
        .where(CanarySignalSnapshot.release_id == release_id)
        .order_by(CanarySignalSnapshot.week_number.desc())
    ).all()
    if not snapshots:
        return []

    current = snapshots[0]
    previous = snapshots[1] if len(snapshots) > 1 else None
    benchmark = db.get(ViralBenchmark, release.benchmark_id)
    signals: list[tuple[str, str, str, str]] = []

    if previous and previous.weekly_streams > 0:
        drop = (previous.weekly_streams - current.weekly_streams) / previous.weekly_streams
        if drop >= 0.25:
            target = (
                f"Build the follow-up demo around {benchmark.tempo_bpm:.1f} BPM "
                f"in {benchmark.musical_key}."
                if benchmark
                else "Build the follow-up demo around the strongest-performing benchmark."
            )
            signals.append(
                (
                    "MOMENTUM_DECAY",
                    "urgent",
                    "Momentum is slowing",
                    f"Streams fell {drop:.0%} week over week. {target}",
                )
            )

    if current.early_skip_rate_pct > 35:
        signals.append(
            (
                "HOOK_DROP_OFF",
                "urgent",
                "Listeners are skipping before the hook",
                "Cut a 15-second chorus clip for WhatsApp and TikTok, and bring the hook "
                "forward to arrive before 18 seconds.",
            )
        )

    city_spins = db.scalar(
        select(func.coalesce(func.sum(AirplayLog.spins_count), 0)).where(
            AirplayLog.release_id == release_id,
            func.lower(AirplayLog.city) == current.top_city.strip().lower(),
        )
    ) or 0
    if city_spins >= 10 or current.social_mentions >= 100:
        signals.append(
            (
                "REGIONAL_SURGE",
                "opportunity",
                f"{current.top_city} is gaining traction",
                f"Use the {current.top_city} surge to pitch the track to verified broadcasters "
                "and local promoters while interest is high.",
            )
        )

    if not signals:
        signals.append(
            (
                "FOLLOWUP_WINDOW",
                "growth",
                "Test your next release while momentum is steady",
                "Compare your next demo with the Viral DNA Analyzer, then plan a focused "
                "follow-up release for your most responsive audience.",
            )
        )

    existing = set(
        db.scalars(
            select(AdvisorInsight.category).where(
                AdvisorInsight.snapshot_id == current.id
            )
        ).all()
    )
    created: list[AdvisorInsight] = []
    for category, priority, title, recommendation in signals:
        if category in existing:
            continue
        insight = AdvisorInsight(
            user_id=release.user_id,
            release_id=release.id,
            snapshot_id=current.id,
            category=category,
            priority=priority,
            title=title,
            recommendation=recommendation,
        )
        db.add(insight)
        created.append(insight)
    if created:
        db.commit()
        for insight in created:
            db.refresh(insight)
    return created


def evaluate_release_background(release_id: int, database_engine: Engine = engine) -> None:
    with Session(database_engine) as db:
        evaluate_release(db, release_id)


def insight_priority(insight: AdvisorInsight) -> int:
    return {"urgent": 0, "opportunity": 1, "growth": 2}.get(insight.priority, 3)
