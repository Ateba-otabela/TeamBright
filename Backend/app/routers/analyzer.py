from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import func, select
from sqlmodel import Session

from app.audio_engine import MAX_AUDIO_BYTES, compare_audio_dna, extract_audio_dna
from app.db import get_db
from app.deps import get_current_user
from app.errors import error
from app.models import DemoAnalysis, User, ViralBenchmark

router = APIRouter(prefix="/analyzer", tags=["SoundDNA Analyzer"])


async def _read_audio_upload(audio_file: UploadFile) -> bytes:
    content = await audio_file.read(MAX_AUDIO_BYTES + 1)
    if len(content) > MAX_AUDIO_BYTES:
        error("audio_too_large", "Audio file exceeds the 30 MB upload limit", 413)
    if not content:
        error("empty_audio", "Audio file is empty", 422)
    return content


def _features(model: ViralBenchmark | DemoAnalysis) -> dict:
    return {
        "musical_key": model.musical_key,
        "key_index": model.key_index,
        "tempo_bpm": model.tempo_bpm,
        "flow_density": model.flow_density,
        "power_score": model.power_score,
        "rms_energy": model.rms_energy,
        "brightness_hz": model.brightness_hz,
        "hook_timestamp_sec": model.hook_timestamp_sec,
    }


def _benchmark_result(item: ViralBenchmark) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "genre": item.genre,
        "broadcast_stations_count": item.broadcast_stations_count,
        "viral_reach_notes": item.viral_reach_notes,
        "dna": _features(item),
        "created_at": item.created_at,
    }


def _analysis_result(item: DemoAnalysis) -> dict:
    return {
        "id": item.id,
        "benchmark_id": item.benchmark_id,
        "demo_title": item.demo_title,
        "version": f"v{item.version_number}",
        "version_number": item.version_number,
        "dna": _features(item),
        "scores": {
            "tone_match": item.tone_match,
            "flow_match": item.flow_match,
            "power_match": item.power_match,
            "hook_timing_match": item.hook_timing_match,
            "hit_readiness_score": item.hit_readiness_score,
        },
        "verdict": item.verdict,
        "studio_fixes": item.studio_fixes,
        "created_at": item.created_at,
    }


@router.post("/viral-benchmarks", status_code=201)
async def create_viral_benchmark(
    title: str = Form(min_length=1, max_length=200),
    genre: str = Form(min_length=1, max_length=100),
    broadcast_stations_count: int = Form(default=0, ge=0),
    viral_reach_notes: str = Form(default="", max_length=5000),
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "artist":
        error("analyzer_forbidden", "Only artists can create viral benchmarks", 403)
    filename = audio_file.filename or ""
    try:
        dna = extract_audio_dna(await _read_audio_upload(audio_file), filename)
    except ValueError as exc:
        error("invalid_audio", str(exc), 422)
    item = ViralBenchmark(
        user_id=user.id,
        title=title.strip(),
        genre=genre.strip(),
        broadcast_stations_count=broadcast_stations_count,
        viral_reach_notes=viral_reach_notes.strip(),
        audio_filename=filename[:255],
        **dna,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _benchmark_result(item)


@router.post("/compare", status_code=201)
async def compare_demo(
    benchmark_id: int = Form(gt=0),
    demo_title: str = Form(min_length=1, max_length=200),
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "artist":
        error("analyzer_forbidden", "Only artists can compare studio demos", 403)
    benchmark = db.get(ViralBenchmark, benchmark_id)
    if benchmark is None or benchmark.user_id != user.id:
        error("benchmark_not_found", "Viral benchmark not found", 404)
    filename = audio_file.filename or ""
    try:
        dna = extract_audio_dna(await _read_audio_upload(audio_file), filename)
    except ValueError as exc:
        error("invalid_audio", str(exc), 422)
    result = compare_audio_dna(_features(benchmark), dna)
    version_number = (
        db.scalar(
            select(func.max(DemoAnalysis.version_number)).where(
                DemoAnalysis.user_id == user.id,
                func.lower(DemoAnalysis.demo_title) == demo_title.strip().lower(),
            )
        )
        or 0
    ) + 1
    analysis = DemoAnalysis(
        user_id=user.id,
        benchmark_id=benchmark.id,
        demo_title=demo_title.strip(),
        version_number=version_number,
        audio_filename=filename[:255],
        **dna,
        **result,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return _analysis_result(analysis)


@router.get("/my-studio")
def my_studio(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    benchmarks = db.scalars(
        select(ViralBenchmark)
        .where(ViralBenchmark.user_id == user.id)
        .order_by(ViralBenchmark.created_at.desc())
    ).all()
    analyses = db.scalars(
        select(DemoAnalysis)
        .where(DemoAnalysis.user_id == user.id)
        .order_by(DemoAnalysis.created_at.desc(), DemoAnalysis.version_number.desc())
    ).all()
    return {
        "benchmarks": [_benchmark_result(item) for item in benchmarks],
        "demos": [_analysis_result(item) for item in analyses],
    }
