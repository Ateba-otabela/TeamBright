from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
from sqlalchemy import select
from sqlmodel import Session, SQLModel

from app.audio_engine import compare_audio_dna, extract_audio_dna
from app.database import engine
from app.models import (
    AdvisorInsight,
    CanarySignalSnapshot,
    DemoAnalysis,
    Profile,
    TrackRelease,
    User,
    ViralBenchmark,
)
from app.security import hash_pin
from app.canary_advisor import evaluate_release


ROOT = Path(__file__).parent
AUDIO_DIR = ROOT / "demo_audio"
SAMPLE_RATE = 22050
DURATION_SEC = 28


def synthesize_demo_audio(
    destination: Path,
    *,
    root_note: int,
    tempo_bpm: float,
    chorus_at_sec: float,
    amplitude: float,
) -> None:
    count = SAMPLE_RATE * DURATION_SEC
    time = np.arange(count, dtype=np.float32) / SAMPLE_RATE
    root_hz = 440.0 * 2 ** ((root_note - 69) / 12)
    beat_phase = np.mod(time * tempo_bpm / 60.0, 1.0)
    kick = np.exp(-beat_phase * 30).astype(np.float32)
    chorus = (time >= chorus_at_sec).astype(np.float32)
    level = amplitude * (0.25 + 0.75 * chorus)
    melody = (
        np.sin(2 * np.pi * root_hz * time)
        + 0.45 * np.sin(2 * np.pi * root_hz * 2 * time)
        + 0.25 * np.sin(2 * np.pi * root_hz * 1.5 * time)
    )
    signal = level * (0.55 * melody + 0.25 * kick * np.sin(2 * np.pi * 68 * time))
    signal = np.clip(signal, -0.98, 0.98)
    pcm = (signal * 32767).astype("<i2")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(SAMPLE_RATE)
        audio.writeframes(pcm.tobytes())


def _find_user(db: Session, phone: str) -> User | None:
    result = db.exec(select(User).where(User.phone == phone)).first()
    if result is None:
        return None
    return result if hasattr(result, "_sa_instance_state") else result[0]


def _unwrap_row(result, model_type):
    if result is None:
        return None
    return result if isinstance(result, model_type) else result[0]


def _get_or_create_user(
    db: Session,
    *,
    phone: str,
    name: str,
    role: str,
    city: str,
    pin: str,
    verified: bool = False,
) -> User:
    user = _find_user(db, phone)
    if user is None:
        user = User(
            name=name,
            phone=phone,
            pin_hash=hash_pin(pin),
            role=role,
            city=city,
            verified=verified,
            active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.name = name
        user.role = role
        user.city = city
        user.verified = verified
        user.active = True
        db.add(user)
        db.commit()
    return user


def _upsert_analysis(
    db: Session,
    artist: User,
    benchmark: ViralBenchmark,
    title: str,
    version_number: int,
    filename: str,
    dna: dict,
) -> DemoAnalysis:
    existing = _unwrap_row(db.exec(
        select(DemoAnalysis).where(
            DemoAnalysis.user_id == artist.id,
            DemoAnalysis.demo_title == title,
            DemoAnalysis.version_number == version_number,
        )
    ).first(), DemoAnalysis)
    benchmark_values = benchmark.model_dump()
    benchmark_values.update(
        {
            "musical_key": benchmark.musical_key,
            "key_index": benchmark.key_index,
            "tempo_bpm": benchmark.tempo_bpm,
            "flow_density": benchmark.flow_density,
            "power_score": benchmark.power_score,
            "rms_energy": benchmark.rms_energy,
            "brightness_hz": benchmark.brightness_hz,
            "hook_timestamp_sec": benchmark.hook_timestamp_sec,
        }
    )
    result = compare_audio_dna(benchmark_values, dna)
    values = {
        "benchmark_id": benchmark.id,
        "audio_filename": filename,
        **dna,
        **result,
    }
    if existing is None:
        existing = DemoAnalysis(
            user_id=artist.id,
            demo_title=title,
            version_number=version_number,
            **values,
        )
    else:
        for key, value in values.items():
            setattr(existing, key, value)
    db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


def seed_demo() -> None:
    SQLModel.metadata.create_all(engine)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    viral_path = AUDIO_DIR / "viral_hit.wav"
    weak_path = AUDIO_DIR / "follow_up_demo_v1_weak.wav"
    fixed_path = AUDIO_DIR / "follow_up_demo_v2_fixed.wav"
    synthesize_demo_audio(viral_path, root_note=60, tempo_bpm=112, chorus_at_sec=8, amplitude=0.72)
    synthesize_demo_audio(weak_path, root_note=62, tempo_bpm=88, chorus_at_sec=22, amplitude=0.22)
    synthesize_demo_audio(fixed_path, root_note=60, tempo_bpm=112, chorus_at_sec=8, amplitude=0.64)

    with Session(engine) as db:
        artist = _get_or_create_user(
            db,
            phone="+237699556677",
            name="Malaika Muna",
            role="artist",
            city="Douala",
            pin="5555",
        )
        broadcaster = _get_or_create_user(
            db,
            phone="+237222210001",
            name="CRTV Centre",
            role="broadcaster",
            city="Yaoundé",
            pin="5555",
            verified=True,
        )
        profile = _unwrap_row(
            db.exec(select(Profile).where(Profile.user_id == artist.id)).first(),
            Profile,
        )
        if profile is None:
            profile = Profile(
                user_id=artist.id,
                display_name="Malaika Muna",
                bio="Makossa and Afropop artist from Douala.",
                genres=["makossa", "afropop"],
                details={"stage_name": "Malaika Muna"},
            )
        db.add(profile)
        station_profile = _unwrap_row(
            db.exec(select(Profile).where(Profile.user_id == broadcaster.id)).first(),
            Profile,
        )
        if station_profile is None:
            station_profile = Profile(
                user_id=broadcaster.id,
                display_name="CRTV Centre",
                bio="Verified public broadcaster.",
                genres=["radio"],
                details={"station_name": "CRTV", "medium": "radio", "frequency": "94.5 FM"},
            )
        db.add(station_profile)
        db.commit()

        dna = extract_audio_dna(viral_path.read_bytes(), viral_path.name)
        benchmark = _unwrap_row(
            db.exec(select(ViralBenchmark).where(
                ViralBenchmark.user_id == artist.id,
                ViralBenchmark.title == "Douala After Dark",
            )).first(),
            ViralBenchmark,
        )
        values = {
            "genre": "makossa",
            "broadcast_stations_count": 4,
            "viral_reach_notes": "CRTV airplay, Douala and Yaoundé audience growth.",
            "audio_filename": viral_path.name,
            **dna,
        }
        if benchmark is None:
            benchmark = ViralBenchmark(
                user_id=artist.id,
                title="Douala After Dark",
                **values,
            )
        else:
            for key, value in values.items():
                setattr(benchmark, key, value)
        db.add(benchmark)
        db.commit()
        db.refresh(benchmark)

        _upsert_analysis(
            db,
            artist,
            benchmark,
            "Follow-up single",
            1,
            weak_path.name,
            extract_audio_dna(weak_path.read_bytes(), weak_path.name),
        )
        _upsert_analysis(
            db,
            artist,
            benchmark,
            "Follow-up single",
            2,
            fixed_path.name,
            extract_audio_dna(fixed_path.read_bytes(), fixed_path.name),
        )

        release = _unwrap_row(
            db.exec(select(TrackRelease).where(
                TrackRelease.user_id == artist.id,
                TrackRelease.title == "After Dark (CIMFEST demo release)",
            )).first(),
            TrackRelease,
        )
        if release is None:
            release = TrackRelease(
                user_id=artist.id,
                benchmark_id=benchmark.id,
                title="After Dark (CIMFEST demo release)",
            )
            db.add(release)
            db.commit()
            db.refresh(release)

        weeks = (
            (1, 120000, 18, 19.0, 70, "Douala"),
            (2, 68000, 25, 43.0, 165, "Douala"),
        )
        for week_number, streams, spins, skip, mentions, city in weeks:
            snapshot = _unwrap_row(
                db.exec(select(CanarySignalSnapshot).where(
                    CanarySignalSnapshot.release_id == release.id,
                    CanarySignalSnapshot.week_number == week_number,
                )).first(),
                CanarySignalSnapshot,
            )
            if snapshot is None:
                db.add(
                    CanarySignalSnapshot(
                        release_id=release.id,
                        week_number=week_number,
                        weekly_streams=streams,
                        radio_tv_spins=spins,
                        early_skip_rate_pct=skip,
                        social_mentions=mentions,
                        top_city=city,
                    )
                )
            else:
                snapshot.weekly_streams = streams
                snapshot.radio_tv_spins = spins
                snapshot.early_skip_rate_pct = skip
                snapshot.social_mentions = mentions
                snapshot.top_city = city
                db.add(snapshot)
        db.commit()
        evaluate_release(db, release.id)

    print("SoundDNA stage demo is ready.")
    print("Artist login: +237699556677 / PIN 5555")
    print("Verified broadcaster: +237222210001")
    print("Audio files:")
    for path in (viral_path, weak_path, fixed_path):
        print(f"  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    seed_demo()
