from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlmodel import Session

from app.canary_advisor import evaluate_release, evaluate_release_background, insight_priority
from app.db import get_db
from app.deps import get_current_user
from app.errors import error
from app.models import (
    AdvisorInsight,
    AirplayLog,
    CanarySignalSnapshot,
    TrackRelease,
    User,
    ViralBenchmark,
)

router = APIRouter(tags=["Canary Spider & Advisor"])


class ReleaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    benchmark_id: int = Field(gt=0)


class AirplayCreate(BaseModel):
    city: str = Field(min_length=1, max_length=100)
    outlet_name: str = Field(min_length=1, max_length=200)
    spins_count: int = Field(gt=0, le=10000)


class SnapshotCreate(BaseModel):
    week_number: int = Field(ge=1)
    weekly_streams: int = Field(ge=0)
    radio_tv_spins: int = Field(ge=0)
    early_skip_rate_pct: float = Field(ge=0, le=100)
    social_mentions: int = Field(ge=0)
    top_city: str = Field(min_length=1, max_length=100)


def _insight_view(item: AdvisorInsight) -> dict:
    return {
        "id": item.id,
        "release_id": item.release_id,
        "category": item.category,
        "priority": item.priority,
        "title": item.title,
        "recommendation": item.recommendation,
        "acknowledged": item.acknowledged,
        "created_at": item.created_at,
    }


@router.post("/releases", status_code=201)
def publish_release(
    payload: ReleaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "artist":
        error("release_forbidden", "Only artists can publish releases", 403)
    if not payload.title.strip():
        error("validation_error", "Validation failed", 422, {"fields": [{"field": "title", "message": "cannot be blank"}]})
    benchmark = db.get(ViralBenchmark, payload.benchmark_id)
    if benchmark is None or benchmark.user_id != user.id:
        error("benchmark_not_found", "Viral benchmark not found", 404)
    release = TrackRelease(
        user_id=user.id,
        benchmark_id=benchmark.id,
        title=payload.title.strip(),
    )
    db.add(release)
    db.commit()
    db.refresh(release)
    return {
        "id": release.id,
        "title": release.title,
        "benchmark_id": release.benchmark_id,
        "release_date": release.release_date,
        "active": release.active,
    }


@router.post("/releases/{release_id}/airplay", status_code=201)
def log_airplay(
    release_id: int,
    payload: AirplayCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in {"broadcaster", "dj"} or not user.is_verified:
        error("airplay_forbidden", "Verified broadcasters and DJs can log official airplay", 403)
    if not payload.city.strip():
        error("validation_error", "Validation failed", 422, {"fields": [{"field": "city", "message": "cannot be blank"}]})
    if not payload.outlet_name.strip():
        error("validation_error", "Validation failed", 422, {"fields": [{"field": "outlet_name", "message": "cannot be blank"}]})
    release = db.get(TrackRelease, release_id)
    if release is None or not release.active:
        error("release_not_found", "Active release not found", 404)
    log = AirplayLog(
        release_id=release.id,
        reporter_id=user.id,
        city=payload.city.strip(),
        outlet_name=payload.outlet_name.strip(),
        spins_count=payload.spins_count,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    background_tasks.add_task(
        evaluate_release_background, release.id, request.app.state.database_engine
    )
    return {
        "id": log.id,
        "release_id": log.release_id,
        "city": log.city,
        "outlet_name": log.outlet_name,
        "spins_count": log.spins_count,
        "created_at": log.created_at,
    }


@router.post("/canary/crawl/{release_id}", status_code=201)
def crawl_release(
    release_id: int,
    payload: SnapshotCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "artist":
        error("crawl_forbidden", "Only artists can crawl release snapshots", 403)
    release = db.get(TrackRelease, release_id)
    if release is None or release.user_id != user.id or not release.active:
        error("release_not_found", "Release not found", 404)
    if not payload.top_city.strip():
        error("validation_error", "Validation failed", 422, {"fields": [{"field": "top_city", "message": "cannot be blank"}]})
    payload.top_city = payload.top_city.strip()
    duplicate = db.scalars(
        select(CanarySignalSnapshot).where(
            CanarySignalSnapshot.release_id == release_id,
            CanarySignalSnapshot.week_number == payload.week_number,
        )
    ).first()
    if duplicate is not None:
        error("snapshot_exists", "A snapshot already exists for that week", 409)
    snapshot = CanarySignalSnapshot(release_id=release.id, **payload.model_dump())
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    created = evaluate_release(db, release_id)
    return {
        "snapshot": {
            "id": snapshot.id,
            "release_id": snapshot.release_id,
            "week_number": snapshot.week_number,
            "weekly_streams": snapshot.weekly_streams,
            "radio_tv_spins": snapshot.radio_tv_spins,
            "early_skip_rate_pct": snapshot.early_skip_rate_pct,
            "social_mentions": snapshot.social_mentions,
            "top_city": snapshot.top_city,
            "created_at": snapshot.created_at,
        },
        "insights": [_insight_view(item) for item in created],
    }


@router.get("/advisor/dashboard")
def advisor_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    releases = db.scalars(
        select(TrackRelease)
        .where(TrackRelease.user_id == user.id, TrackRelease.active.is_(True))
        .order_by(TrackRelease.created_at.desc())
    ).all()
    release_ids = [release.id for release in releases]
    snapshots = (
        db.scalars(
            select(CanarySignalSnapshot)
            .where(CanarySignalSnapshot.release_id.in_(release_ids))
            .order_by(CanarySignalSnapshot.week_number)
        ).all()
        if release_ids
        else []
    )
    insights = (
        db.scalars(
            select(AdvisorInsight).where(AdvisorInsight.user_id == user.id)
        ).all()
    )
    insights.sort(key=lambda item: (insight_priority(item), -item.created_at.timestamp()))
    latest = snapshots[-1] if snapshots else None
    latest_release_snapshots = (
        [item for item in snapshots if item.release_id == latest.release_id]
        if latest
        else []
    )
    latest_categories = {
        item.category
        for item in insights
        if latest and item.snapshot_id == latest.id
    }
    if "MOMENTUM_DECAY" in latest_categories:
        status = "momentum_decay"
    elif len(latest_release_snapshots) >= 2 and (
        latest_release_snapshots[-1].weekly_streams
        > latest_release_snapshots[-2].weekly_streams
    ):
        status = "growing"
    elif latest:
        status = "steady"
    else:
        status = "no_data"
    return {
        "weekly_momentum_status": status,
        "unread_alerts_count": sum(not item.acknowledged for item in insights),
        "trajectory": [
            {
                "release_id": item.release_id,
                "week_number": item.week_number,
                "weekly_streams": item.weekly_streams,
                "radio_tv_spins": item.radio_tv_spins,
                "early_skip_rate_pct": item.early_skip_rate_pct,
                "social_mentions": item.social_mentions,
                "top_city": item.top_city,
            }
            for item in snapshots
        ],
        "insights": [_insight_view(item) for item in insights],
        "generated_at": datetime.utcnow(),
    }


@router.post("/advisor/insights/{insight_id}/acknowledge")
def acknowledge_insight(
    insight_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    insight = db.get(AdvisorInsight, insight_id)
    if insight is None or insight.user_id != user.id:
        error("insight_not_found", "Advisor insight not found", 404)
    insight.acknowledged = True
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return _insight_view(insight)
