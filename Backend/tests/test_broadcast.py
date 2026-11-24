from app.models import BroadcastDispatch, Track, User


def register_and_login(client, *, phone, role, name=None, city="Douala"):
    name = name or f"{role.title()} account"
    registered = client.post(
        "/auth/register",
        json={
            "name": name,
            "phone": phone,
            "pin": "1234",
            "role": role,
            "city": city,
        },
    )
    assert registered.status_code == 201
    response = client.post(
        "/auth/login",
        json={"phone": phone, "pin": "1234"},
    )
    return registered.json()["id"], response.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def create_profile(client, token, *, role, name, **details):
    payload = {"display_name": name, **details}
    if role == "broadcaster":
        payload.setdefault("station_name", name)
    if role == "dj":
        payload.setdefault("dj_type", "radio")
    response = client.put("/profile", json=payload, headers=auth(token))
    assert response.status_code == 200
    return response.json()


def test_destinations_tracks_execute_and_receiver_inbox(client, test_db):
    artist_id, artist_token = register_and_login(
        client, phone="690123461", role="artist", name="Artist"
    )
    _, station_token = register_and_login(
        client, phone="690123462", role="broadcaster", name="Lead FM", city="Yaoundé"
    )
    station = create_profile(
        client,
        station_token,
        role="broadcaster",
        name="Lead FM Cameroon",
        medium="radio",
        frequency="94.0 MHz",
    )
    station_id = station["id"]
    with test_db() as db:
        db.get(User, station_id).verified = True
        db.commit()

    dj_id, dj_token = register_and_login(
        client, phone="690123463", role="dj", name="DJ Killa", city="Douala"
    )
    create_profile(client, dj_token, role="dj", name="DJ Killa")

    catalog = client.post(
        "/api/tracks",
        headers=auth(artist_token),
        json={
            "title": "Buea Nights",
            "genre": "Makossa",
            "duration_seconds": 185,
            "audio_url": "https://audio.example/buea-nights.mp3",
        },
    )
    assert catalog.status_code == 201
    track = catalog.json()
    assert track["artist_name"] == "Artist"
    assert client.get("/api/tracks/mine", headers=auth(artist_token)).json()["total"] == 1
    listed_tracks = client.get("/api/broadcast/tracks", headers=auth(artist_token))
    assert listed_tracks.json()["items"][0]["id"] == track["id"]

    destinations = client.get("/api/broadcast/destinations?verified_only=true")
    assert destinations.status_code == 200
    assert destinations.json()["total"] == 1
    assert destinations.json()["items"][0] == {
        "id": station_id,
        "label": "Lead FM Cameroon (94.0 MHz) — Yaoundé",
        "type": "broadcaster",
        "medium": "radio",
        "city": "Yaoundé",
        "is_verified": True,
    }
    all_destinations = client.get("/api/broadcast/destinations?q=Killa")
    assert all_destinations.json()["items"][0]["id"] == dj_id

    executed = client.post(
        "/api/broadcast/execute",
        headers=auth(artist_token),
        json={
            "track_id": track["id"],
            "destination_ids": [station_id, dj_id],
            "note": "Please introduce the new single.",
        },
    )
    assert executed.status_code == 201
    result = executed.json()
    assert result["executed"] is True
    assert len(result["dispatches"]) == 2
    assert result["dispatches"][0]["status"] == "sent"

    sent = client.get("/api/broadcast/sent", headers=auth(artist_token))
    inbox = client.get("/api/broadcast/inbox", headers=auth(station_token))
    assert sent.json()["total"] == 2
    assert inbox.json()["total"] == 1
    dispatch_id = inbox.json()["items"][0]["id"]
    delivered = client.patch(
        f"/api/broadcast/{dispatch_id}/status",
        headers=auth(station_token),
        json={"status": "delivered"},
    )
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "delivered"

    with test_db() as db:
        assert db.query(BroadcastDispatch).count() == 2
        assert db.query(Track).filter_by(owner_id=artist_id).count() == 1


def test_broadcast_rejects_unowned_tracks_and_invalid_destinations(client):
    _, artist_token = register_and_login(client, phone="690123464", role="artist")
    _, other_artist_token = register_and_login(
        client, phone="690123465", role="artist", name="Other artist"
    )
    station_id, station_token = register_and_login(
        client, phone="690123466", role="broadcaster", name="Station"
    )
    create_profile(client, station_token, role="broadcaster", name="Station")
    track_response = client.post(
        "/api/tracks",
        headers=auth(artist_token),
        json={"title": "Private track", "genre": "Urban", "file_path": "private.mp3"},
    )
    track_id = track_response.json()["id"]

    unowned = client.post(
        "/api/broadcast/execute",
        headers=auth(other_artist_token),
        json={"track_id": track_id, "destination_id": station_id},
    )
    assert unowned.status_code == 403

    invalid_destination = client.post(
        "/api/broadcast/execute",
        headers=auth(artist_token),
        json={"track_id": track_id, "destination_id": 99999},
    )
    assert invalid_destination.status_code == 400
    assert client.get("/api/broadcast/sent", headers=auth(artist_token)).json()["total"] == 0


def test_tracks_require_authorization_and_receiver_controls_inbox_status(client):
    _, artist_token = register_and_login(client, phone="690123467", role="artist")
    _, fan_token = register_and_login(client, phone="690123468", role="fan")
    station_id, station_token = register_and_login(
        client, phone="690123469", role="broadcaster", name="Station"
    )
    create_profile(client, station_token, role="broadcaster", name="Station")

    assert client.get("/api/broadcast/tracks").status_code == 401
    assert client.post(
        "/api/tracks",
        headers=auth(fan_token),
        json={"title": "No", "genre": "Urban", "audio_url": "https://audio.example/no.mp3"},
    ).status_code == 403

    track = client.post(
        "/api/tracks",
        headers=auth(artist_token),
        json={"title": "Single", "genre": "Urban", "audio_url": "https://audio.example/single.mp3"},
    ).json()
    dispatch = client.post(
        "/api/broadcast/execute",
        headers=auth(artist_token),
        json={"track_id": track["id"], "destination_id": station_id},
    )
    assert dispatch.status_code == 201
    dispatch_id = dispatch.json()["dispatches"][0]["id"]
    assert client.patch(
        f"/api/broadcast/{dispatch_id}/status",
        headers=auth(fan_token),
        json={"status": "declined"},
    ).status_code == 403

    assert client.patch(
        f"/api/broadcast/{dispatch_id}/status",
        headers=auth(station_token),
        json={"status": "played"},
    ).status_code == 400

    assert client.patch(
        f"/api/broadcast/{dispatch_id}/status",
        headers=auth(station_token),
        json={"status": "delivered"},
    ).status_code == 200

    played = client.patch(
        f"/api/broadcast/{dispatch_id}/status",
        headers=auth(station_token),
        json={"status": "played"},
    )
    assert played.status_code == 200
    assert played.json()["status"] == "played"

    final_update = client.patch(
        f"/api/broadcast/{dispatch_id}/status",
        headers=auth(station_token),
        json={"status": "declined"},
    )
    assert final_update.status_code == 400


def test_broadcast_rejects_duplicate_delivered_status(client):
    _, artist_token = register_and_login(client, phone="690123470", role="artist")
    station_id, station_token = register_and_login(
        client, phone="690123471", role="broadcaster", name="Status Radio"
    )
    create_profile(client, station_token, role="broadcaster", name="Status Radio")
    track = client.post(
        "/api/tracks",
        headers=auth(artist_token),
        json={"title": "Status Test", "genre": "Urban", "audio_url": "https://audio.example/status.mp3"},
    ).json()
    dispatch = client.post(
        "/api/broadcast/execute",
        headers=auth(artist_token),
        json={"track_id": track["id"], "destination_id": station_id},
    ).json()["dispatches"][0]

    first = client.patch(
        f"/api/broadcast/{dispatch['id']}/status",
        headers=auth(station_token),
        json={"status": "delivered"},
    )
    assert first.status_code == 200

    duplicate = client.patch(
        f"/api/broadcast/{dispatch['id']}/status",
        headers=auth(station_token),
        json={"status": "delivered"},
    )
    assert duplicate.status_code == 400
