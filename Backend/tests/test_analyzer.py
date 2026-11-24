import wave

from app.models import DemoAnalysis, ViralBenchmark


def register_and_login(client, *, phone="690123456", role="artist"):
    registered = client.post(
        "/auth/register",
        json={
            "name": "Analyzer Artist",
            "phone": phone,
            "pin": "1234",
            "role": role,
            "city": "Douala",
        },
    )
    assert registered.status_code == 201
    login = client.post(
        "/auth/login",
        json={"phone": phone, "pin": "1234"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def wav_bytes(root_note=60, tempo_bpm=112, chorus_at_sec=8):
    import io
    import numpy as np

    sample_rate = 22050
    duration = 28
    count = sample_rate * duration
    time = np.arange(count, dtype=np.float32) / sample_rate
    root_hz = 440.0 * 2 ** ((root_note - 69) / 12)
    beat_phase = np.mod(time * tempo_bpm / 60.0, 1.0)
    kick = np.exp(-beat_phase * 30).astype(np.float32)
    chorus = (time >= chorus_at_sec).astype(np.float32)
    melody = (
        np.sin(2 * np.pi * root_hz * time)
        + 0.45 * np.sin(2 * np.pi * root_hz * 2 * time)
        + 0.25 * np.sin(2 * np.pi * root_hz * 1.5 * time)
    )
    signal = 0.72 * (0.25 + 0.75 * chorus) * (
        0.55 * melody + 0.25 * kick * np.sin(2 * np.pi * 68 * time)
    )
    pcm = (np.clip(signal, -0.98, 0.98) * 32767).astype("<i2")
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(pcm.tobytes())
    return output.getvalue()


def test_analyzer_benchmark_compare_and_my_studio(client):
    token = register_and_login(client)
    benchmark = client.post(
        "/analyzer/viral-benchmarks",
        headers=auth(token),
        data={
            "title": "Douala After Dark",
            "genre": "makossa",
            "broadcast_stations_count": "4",
            "viral_reach_notes": "Strong regional response",
        },
        files={"audio_file": ("viral.wav", wav_bytes(), "audio/wav")},
    )
    assert benchmark.status_code == 201
    benchmark_id = benchmark.json()["id"]
    assert benchmark.json()["dna"]["tempo_bpm"] > 0

    first = client.post(
        "/analyzer/compare",
        headers=auth(token),
        data={"benchmark_id": str(benchmark_id), "demo_title": "Follow-up single"},
        files={"audio_file": ("v1.wav", wav_bytes(62, 88, 22), "audio/wav")},
    )
    assert first.status_code == 201
    assert first.json()["version"] == "v1"
    assert first.json()["scores"]["hit_readiness_score"] >= 0

    second = client.post(
        "/analyzer/compare",
        headers=auth(token),
        data={"benchmark_id": str(benchmark_id), "demo_title": "Follow-up single"},
        files={"audio_file": ("v2.wav", wav_bytes(), "audio/wav")},
    )
    assert second.status_code == 201
    assert second.json()["version"] == "v2"

    studio = client.get("/analyzer/my-studio", headers=auth(token))
    assert studio.status_code == 200
    assert len(studio.json()["benchmarks"]) == 1
    assert len(studio.json()["demos"]) == 2


def test_analyzer_requires_artist_and_valid_audio(client):
    fan_token = register_and_login(client, phone="690123457", role="fan")
    forbidden = client.post(
        "/analyzer/viral-benchmarks",
        headers=auth(fan_token),
        data={"title": "Not allowed", "genre": "afrobeats"},
        files={"audio_file": ("fan.wav", wav_bytes(), "audio/wav")},
    )
    assert forbidden.status_code == 403

    artist_token = register_and_login(client, phone="690123458", role="artist")
    invalid = client.post(
        "/analyzer/viral-benchmarks",
        headers=auth(artist_token),
        data={"title": "Invalid", "genre": "afrobeats"},
        files={"audio_file": ("invalid.txt", b"not audio", "text/plain")},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_audio"


def test_analyzer_benchmark_is_owned_by_artist(client, test_db):
    first_token = register_and_login(client, phone="690123459")
    created = client.post(
        "/analyzer/viral-benchmarks",
        headers=auth(first_token),
        data={"title": "Private benchmark", "genre": "makossa"},
        files={"audio_file": ("private.wav", wav_bytes(), "audio/wav")},
    )
    assert created.status_code == 201

    second_token = register_and_login(client, phone="690123460")
    denied = client.post(
        "/analyzer/compare",
        headers=auth(second_token),
        data={"benchmark_id": str(created.json()["id"]), "demo_title": "Demo"},
        files={"audio_file": ("demo.wav", wav_bytes(), "audio/wav")},
    )
    assert denied.status_code == 404
