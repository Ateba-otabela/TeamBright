from datetime import timedelta

import pytest

from app.models import AuditLog, User, VerificationRequest
from app.security import create_token, hash_pin


def register(client, *, name="Test user", phone="690123456", pin="1234", role="artist", city="Douala"):
    return client.post(
        "/auth/register",
        json={"name": name, "phone": phone, "pin": pin, "role": role, "city": city},
    )


def login(client, phone="690123456", pin="1234"):
    response = client.post("/auth/login", json={"phone": phone, "pin": pin})
    return response.json().get("access_token")


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def create_admin(test_db, phone="699999999"):
    with test_db() as db:
        admin = User(
            name="Module admin",
            phone="+237" + phone,
            pin_hash=hash_pin("9876"),
            role="admin",
            city="Yaoundé",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin.id


def profile(client, token, *, role="artist", display_name="Test artist", **fields):
    payload = {"display_name": display_name, "bio": "DEMO profile", **fields}
    if role == "artist":
        payload.setdefault("stage_name", display_name)
    elif role == "dj":
        payload.setdefault("dj_type", "club")
    elif role == "broadcaster":
        payload.setdefault("station_name", display_name)
    elif role == "promoter":
        payload.setdefault("company_name", display_name)
    return client.put("/profile", json=payload, headers=auth(token))


def test_phone_formats_normalize_and_duplicates_conflict(client):
    formats = ["690123456", "237 690 123 456", "+237-690-123-456", "00237 690123456"]
    first = register(client, phone=formats[0])
    assert first.status_code == 201
    assert first.json()["phone"] == "+237690123456"
    for phone in formats[1:]:
        duplicate = register(client, phone=phone)
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "phone_exists"


@pytest.mark.parametrize("phone", ["69012345", "590123456", "+237590123456", "2376901234567", "abc"])
def test_invalid_phone_formats_are_rejected(client, phone):
    response = register(client, phone=phone)
    assert response.status_code == 422
    assert response.json()["error"]["details"]["fields"][0]["field"] == "phone"


def test_weak_pin_and_admin_self_registration_are_rejected(client):
    assert register(client, pin="123").status_code == 422
    response = register(client, role="admin")
    assert response.status_code == 422
    assert response.json()["error"]["details"]["fields"][0]["field"] == "role"


def test_login_generic_error_lockout_and_clock_unlock(client):
    register(client)
    wrong = client.post("/auth/login", json={"phone": "690123456", "pin": "9999"})
    unknown = client.post("/auth/login", json={"phone": "690123457", "pin": "9999"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()

    for _ in range(3):
        assert client.post("/auth/login", json={"phone": "690123456", "pin": "9999"}).status_code == 401
    locked = client.post("/auth/login", json={"phone": "690123456", "pin": "9999"})
    assert locked.status_code == 423
    assert client.post("/auth/login", json={"phone": "690123456", "pin": "1234"}).status_code == 423

    client.clock.advance(timedelta(minutes=15, seconds=1))
    unlocked = client.post("/auth/login", json={"phone": "690123456", "pin": "1234"})
    assert unlocked.status_code == 200


def test_login_success_tampered_and_expired_tokens(client):
    user_id = register(client).json()["id"]
    token = login(client)
    assert token
    assert client.get("/me", headers=auth(token)).status_code == 200

    tampered = client.get("/me", headers=auth(token + "x"))
    assert tampered.status_code == 401
    expired = create_token(user_id, "artist", client.clock.now() - timedelta(hours=2))
    assert client.get("/me", headers=auth(expired)).status_code == 401


def test_deactivated_user_cannot_log_in(client, test_db):
    user_id = register(client).json()["id"]
    with test_db() as db:
        db.get(User, user_id).active = False
        db.commit()
    response = client.post("/auth/login", json={"phone": "690123456", "pin": "1234"})
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "invalid credentials"


def test_change_pin_and_mass_assignment_protection(client):
    token = login_after_register(client)
    response = client.post(
        "/me/change-pin",
        json={"old_pin": "1234", "new_pin": "5678"},
        headers=auth(token),
    )
    assert response.status_code == 200
    assert client.post("/auth/login", json={"phone": "690123456", "pin": "1234"}).status_code == 401
    assert client.post("/auth/login", json={"phone": "690123456", "pin": "5678"}).status_code == 200

    updated = client.patch(
        "/me",
        json={"name": "Changed", "role": "admin", "verified": True, "user_id": 999},
        headers=auth(token),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Changed"
    assert updated.json()["role"] == "artist"
    assert updated.json()["verified"] is False
    prof = profile(
        client,
        token,
        display_name="Public artist",
        role="artist",
        verified=True,
        user_id=999,
        stage_name="Stage",
    )
    assert prof.status_code == 200
    assert prof.json()["role"] == "artist"
    assert prof.json()["verified"] is False


def login_after_register(client):
    register(client)
    return login(client)


@pytest.mark.parametrize(
    "role,missing_field",
    [("broadcaster", "station_name"), ("promoter", "company_name"), ("dj", "dj_type")],
)
def test_role_specific_profile_requirements(client, role, missing_field):
    register(client, role=role)
    token = login(client)
    response = client.put(
        "/profile",
        json={"display_name": "Missing field"},
        headers=auth(token),
    )
    assert response.status_code == 422
    assert missing_field in str(response.json()["error"]["details"]["fields"])


@pytest.mark.parametrize(
    "payload",
    [
        {"display_name": "Bad URL", "photo_url": "javascript:alert(1)"},
        {"display_name": "Bad social", "social_links": {"youtube": "http://"}},
        {"display_name": "Too many", "genres": ["a", "b", "c", "d", "e", "f"]},
        {"display_name": "Long bio", "bio": "x" * 501},
    ],
)
def test_profile_urls_genre_limit_and_bio_limit(client, payload):
    register(client)
    response = client.put("/profile", json=payload, headers=auth(login(client)))
    assert response.status_code == 422


def test_fan_cannot_create_profile_and_public_phone_is_private(client, test_db):
    register(client, phone="690123456")
    artist_token = login(client)
    artist_id = register(
        client, name="Fan", phone="690123457", role="fan"
    ).json()["id"]
    fan_token = login(client, phone="690123457")
    assert client.put("/profile", json={"display_name": "Nope"}, headers=auth(fan_token)).status_code == 403

    profile(client, artist_token, display_name="Public artist", bio="Makossa")
    artist_id = 1
    public = client.get(f"/profiles/{artist_id}")
    assert public.status_code == 200
    assert "phone" not in public.json()
    assert public.json()["bio"] == "Makossa"
    assert client.get(f"/profiles/{artist_id}", headers=auth(artist_token)).json()["phone"] == "+237690123456"

    admin_id = create_admin(test_db)
    with test_db() as db:
        admin_phone = db.get(User, admin_id).phone
    admin_token = login(client, phone=admin_phone, pin="9876")
    assert client.get(f"/profiles/{artist_id}", headers=auth(admin_token)).json()["phone"] == "+237690123456"
    assert client.get(f"/profiles/{artist_id + 500}").status_code == 404
    assert artist_id != 0


def test_verification_approval_rejection_and_audit(client, test_db):
    fan_id = register(client, role="fan").json()["id"]
    fan_token = login(client)
    assert client.post(
        "/verification-requests",
        json={"evidence_text": "Evidence"},
        headers=auth(fan_token),
    ).status_code == 403

    broadcaster_id = register(
        client,
        name="Yaoundé Radio",
        phone="690123457",
        role="broadcaster",
        city="Yaoundé",
    ).json()["id"]
    broadcaster_token = login(client, phone="690123457")
    assert profile(
        client,
        broadcaster_token,
        role="broadcaster",
        display_name="Yaoundé Radio",
        genres=["radio"],
    ).status_code == 200
    requested = client.post(
        "/verification-requests",
        json={"evidence_text": "Demo station evidence"},
        headers=auth(broadcaster_token),
    )
    assert requested.status_code == 201
    request_id = requested.json()["id"]
    assert client.post(
        "/verification-requests",
        json={"evidence_text": "Duplicate"},
        headers=auth(broadcaster_token),
    ).status_code == 409
    mine = client.get("/verification-requests/mine", headers=auth(broadcaster_token))
    assert mine.json()["total"] == 1

    artist_id = register(
        client, name="Already verified", phone="690123458"
    ).json()["id"]
    with test_db() as db:
        db.get(User, artist_id).verified = True
        db.commit()
    verified_token = login(client, phone="690123458")
    assert client.post(
        "/verification-requests",
        json={"evidence_text": "Again"},
        headers=auth(verified_token),
    ).status_code == 409

    admin_id = create_admin(test_db)
    with test_db() as db:
        admin_phone = db.get(User, admin_id).phone
    admin_token = login(client, phone=admin_phone, pin="9876")
    assert client.get("/admin/verification-requests").status_code == 401
    assert client.get(
        "/admin/verification-requests", headers=auth(broadcaster_token)
    ).status_code == 403
    requests = client.get("/admin/verification-requests", headers=auth(admin_token))
    assert requests.status_code == 200
    assert requests.json()["total"] == 1

    invalid = client.post(
        f"/admin/verification-requests/{request_id}/decision",
        json={"decision": "later"},
        headers=auth(admin_token),
    )
    assert invalid.status_code == 422
    approved = client.post(
        f"/admin/verification-requests/{request_id}/decision",
        json={"decision": "approve", "note": "Demo approval"},
        headers=auth(admin_token),
    )
    assert approved.status_code == 200
    assert approved.json()["user_verified"] is True
    assert client.post(
        f"/admin/verification-requests/{request_id}/decision",
        json={"decision": "reject"},
        headers=auth(admin_token),
    ).status_code == 409
    assert client.get(f"/profiles/{broadcaster_id}").json()["verified"] is True
    assert client.get("/directory?role=broadcaster&city=Yaound%C3%A9&verified=true").json()["total"] == 1
    audit = client.get("/admin/audit", headers=auth(admin_token))
    assert audit.status_code == 200
    assert audit.json()["total"] == 1
    with test_db() as db:
        row = db.query(AuditLog).one()
        assert row.actor_id == admin_id
        assert row.target == f"verification_request:{request_id}"


def test_rejected_request_can_be_resubmitted(client, test_db):
    register(client)
    token = login(client)
    request_id = client.post(
        "/verification-requests",
        json={"evidence_text": "First"},
        headers=auth(token),
    ).json()["id"]
    admin_id = create_admin(test_db)
    with test_db() as db:
        admin_phone = db.get(User, admin_id).phone
    admin_token = login(client, phone=admin_phone, pin="9876")
    rejected = client.post(
        f"/admin/verification-requests/{request_id}/decision",
        json={"decision": "reject"},
        headers=auth(admin_token),
    )
    assert rejected.status_code == 200
    resubmitted = client.post(
        "/verification-requests",
        json={"evidence_text": "Updated evidence"},
        headers=auth(token),
    )
    assert resubmitted.status_code == 201
    assert resubmitted.json()["id"] != request_id


def test_directory_filters_pagination_and_injection_safety(client, test_db):
    entries = [
        ("Makossa artist", "artist", "Douala", ["makossa"], False),
        ("Bikutsi artist", "artist", "Yaoundé", ["bikutsi"], True),
        ("Afrobeats DJ", "dj", "Buea", ["afrobeats"], False),
        ("Yaoundé Radio", "broadcaster", "Yaoundé", ["radio"], True),
        ("Verified promoter", "promoter", "Buea", ["events"], True),
    ]
    for index, (name, role, city, genres, verified) in enumerate(entries):
        phone = f"6901234{index:02d}"
        user_id = register(
            client, name=name, phone=phone, role=role, city=city
        ).json()["id"]
        token = login(client, phone=phone)
        profile(client, token, role=role, display_name=name, genres=genres)
        if verified:
            with test_db() as db:
                db.get(User, user_id).verified = True
                db.commit()
    register(client, name="Fan nobody", phone="690123499", role="fan")

    assert client.get("/directory?role=artist").json()["total"] == 2
    assert client.get("/directory?city=Douala").json()["total"] == 1
    assert client.get("/directory?genre=MAKOSSA").json()["items"][0]["display_name"] == "Makossa artist"
    assert client.get("/directory?verified=true").json()["total"] == 3
    assert client.get("/directory?role=broadcaster&city=Yaound%C3%A9&verified=true&q=Radio").json()["total"] == 1
    assert client.get("/directory?limit=2&offset=1").json()["total"] == 5
    assert len(client.get("/directory?limit=2&offset=1").json()["items"]) == 2
    assert client.get("/directory?q=%25").json()["total"] == 0
    assert client.get("/directory?q=_").json()["total"] == 0
    injection = client.get("/directory?q=%27%20OR%201%3D1%20--")
    assert injection.status_code == 200
    assert injection.json()["total"] == 0
    assert all(item["role"] != "fan" for item in client.get("/directory").json()["items"])


def test_follows_idempotency_validation_and_counts(client):
    register(client, name="Artist", phone="690123456", role="artist")
    artist_token = login(client)
    artist_id = profile(client, artist_token, display_name="Artist").json()["id"]
    fan_id = register(client, name="Fan", phone="690123457", role="fan").json()["id"]
    fan_token = login(client, phone="690123457")

    assert client.post(f"/follows/{artist_id}", headers=auth(fan_token)).status_code == 200
    assert client.post(f"/follows/{artist_id}", headers=auth(fan_token)).status_code == 200
    assert client.get(f"/artists/{artist_id}/followers").json()["followers"] == 1
    assert client.get("/me/following", headers=auth(fan_token)).json()["total"] == 1
    assert client.post(f"/follows/{fan_id}", headers=auth(fan_token)).status_code == 400
    assert client.post("/follows/9999", headers=auth(fan_token)).status_code == 404
    assert client.delete(f"/follows/{artist_id}", headers=auth(fan_token)).json()["following"] is False
    assert client.get(f"/artists/{artist_id}/followers").json()["followers"] == 0
    assert client.get("/me/following", headers=auth(fan_token)).json()["total"] == 0


def test_json_errors_and_body_limits(client):
    unknown = client.get("/definitely-not-a-route")
    assert unknown.status_code == 404
    assert "error" in unknown.json()
    wrong_method = client.put("/directory")
    assert wrong_method.status_code == 405
    assert "error" in wrong_method.json()
    oversized = client.post(
        "/auth/register",
        content=b"x" * (1_048_577),
        headers={"content-type": "application/json"},
    )
    assert oversized.status_code == 413
    malformed = client.post(
        "/auth/register",
        content=b'{"name":',
        headers={"content-type": "application/json"},
    )
    assert malformed.status_code in (400, 422)


def test_end_to_end_scenario(client, test_db):
    artist_id = register(
        client, name="Buea Makossa Artist", phone="690123456", city="Buea"
    ).json()["id"]
    artist_token = login(client)
    assert profile(
        client, artist_token, display_name="Buea Makossa Artist", genres=["makossa"]
    ).status_code == 200

    station_id = register(
        client,
        name="Yaoundé Radio",
        phone="690123457",
        role="broadcaster",
        city="Yaoundé",
    ).json()["id"]
    station_token = login(client, phone="690123457")
    assert profile(
        client, station_token, role="broadcaster", display_name="Yaoundé Radio"
    ).status_code == 200
    request = client.post(
        "/verification-requests",
        json={"evidence_text": "Demo station evidence"},
        headers=auth(station_token),
    )
    assert request.status_code == 201

    admin_id = create_admin(test_db)
    with test_db() as db:
        admin_phone = db.get(User, admin_id).phone
    admin_token = login(client, phone=admin_phone, pin="9876")
    decision = client.post(
        f"/admin/verification-requests/{request.json()['id']}/decision",
        json={"decision": "approve"},
        headers=auth(admin_token),
    )
    assert decision.status_code == 200

    fan_id = register(client, name="Fan", phone="690123458", role="fan").json()["id"]
    fan_token = login(client, phone="690123458")
    followed = client.post(f"/follows/{artist_id}", headers=auth(fan_token))
    assert followed.status_code == 200
    result = client.get(
        "/directory?role=broadcaster&city=Yaound%C3%A9&verified=true&q=Radio"
    )
    assert result.status_code == 200
    assert result.json()["total"] == 1
    assert result.json()["items"][0]["id"] == station_id
    assert result.json()["items"][0]["verified"] is True
    assert fan_id != artist_id
