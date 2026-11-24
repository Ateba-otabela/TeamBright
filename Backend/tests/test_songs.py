from app.routers import songs
from app.audio_engine import MAX_AUDIO_BYTES


def register_and_login(client, *, phone, role):
    registration = client.post(
        "/auth/register",
        json={
            "name": f"{role.title()} account",
            "phone": phone,
            "pin": "1234",
            "role": role,
            "city": "Douala",
        },
    )
    assert registration.status_code == 201
    response = client.post(
        "/auth/login",
        json={"phone": phone, "pin": "1234"},
    )
    return response.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_artist_mp3_upload_is_playable_and_public(client, monkeypatch, tmp_path):
    monkeypatch.setattr(songs, "SONG_STORAGE_DIR", tmp_path)
    artist_token = register_and_login(client, phone="690123456", role="artist")
    fan_token = register_and_login(client, phone="690123457", role="fan")
    audio = bytes.fromhex("fffb9064") + b"\x00" * 64

    uploaded = client.post(
        "/songs",
        headers=auth(artist_token),
        data={"title": "After Dark"},
        files={"audio_file": ("after-dark.mp3", audio, "audio/mpeg")},
    )

    assert uploaded.status_code == 201
    song = uploaded.json()
    assert song["title"] == "After Dark"
    assert song["artist_name"] == "Artist account"
    assert song["audio_size"] == len(audio)
    assert (client.get("/songs/recent").json()["items"][0]["id"]) == song["id"]
    assert client.get("/songs/mine", headers=auth(artist_token)).json()["total"] == 1
    assert client.get("/songs/mine", headers=auth(fan_token)).json()["total"] == 0

    playback = client.get(song["audio_url"])
    assert playback.status_code == 200
    assert playback.headers["content-type"].startswith("audio/mpeg")
    assert playback.content == audio


def test_song_upload_requires_artist_and_valid_mp3(client):
    fan_token = register_and_login(client, phone="690123458", role="fan")
    forbidden = client.post(
        "/songs",
        headers=auth(fan_token),
        data={"title": "Not allowed"},
        files={"audio_file": ("song.mp3", b"not an mp3", "audio/mpeg")},
    )
    assert forbidden.status_code == 403

    artist_token = register_and_login(client, phone="690123459", role="artist")
    invalid = client.post(
        "/songs",
        headers=auth(artist_token),
        data={"title": "Invalid audio"},
        files={"audio_file": ("song.mp3", b"not an mp3", "audio/mpeg")},
    )
    assert invalid.status_code == 422


def test_song_upload_enforces_audio_size_limit(client, monkeypatch, tmp_path):
    monkeypatch.setattr(songs, "SONG_STORAGE_DIR", tmp_path)
    artist_token = register_and_login(client, phone="690123460", role="artist")
    oversized_audio = bytes.fromhex("fffb9064") + b"\x00" * MAX_AUDIO_BYTES

    response = client.post(
        "/songs",
        headers=auth(artist_token),
        data={"title": "Too large"},
        files={"audio_file": ("large.mp3", oversized_audio, "audio/mpeg")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "audio_too_large"
