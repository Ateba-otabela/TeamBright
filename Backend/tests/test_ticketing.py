from app.models import User
from app.security import hash_pin, normalize_phone


def register_and_login(client, phone, role="promoter"):
    registered = client.post(
        "/auth/register",
        json={
            "name": f"{role.title()} account",
            "phone": phone,
            "pin": "1234",
            "role": role,
            "city": "Douala",
        },
    )
    assert registered.status_code == 201
    response = client.post("/auth/login", json={"phone": phone, "pin": "1234"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def login(client, phone):
    response = client.post("/auth/login", json={"phone": phone, "pin": "1234"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def add_admin_or_gate_user(test_db, phone, role):
    with test_db() as db:
        db.add(
            User(
                name=f"{role.title()} account",
                phone=normalize_phone(phone),
                pin_hash=hash_pin("1234"),
                role=role,
                city="Douala",
                verified=False,
                active=True,
                failed_attempts=0,
            )
        )
        db.commit()


def test_ticket_event_purchase_and_gate_lifecycle(client, test_db):
    promoter = register_and_login(client, "690555101", "promoter")

    add_admin_or_gate_user(test_db, "690555102", "admin")
    admin = login(client, "690555102")

    created = client.post(
        "/api/events",
        headers=promoter,
        json={
            "title": "CIMFEST Night",
            "category": "concert",
            "venue": "Douala Arena",
            "city": "Douala",
            "event_date": "2026-12-10T19:00:00Z",
            "total_seats": 2,
            "artist_momo_number": "+237 690 555 103",
        },
    )
    assert created.status_code == 201
    event_id = created.json()["event_id"]

    approved = client.post(
        f"/api/events/{event_id}/decision",
        headers=admin,
        json={"decision": "approve"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    tier = client.post(
        f"/api/events/{event_id}/ticket-tiers",
        headers=promoter,
        json={
            "name": "VIP",
            "price": "10000.00",
            "zone_label": "Front row",
            "quantity": 2,
        },
    )
    assert tier.status_code == 201
    tier_id = tier.json()["id"]

    minted = client.post(
        f"/api/events/{event_id}/tickets/mint",
        headers=promoter,
        json={"tier_id": tier_id, "quantity": 2},
    )
    assert minted.status_code == 201
    assert minted.json()["minted"] == 2

    purchased = client.post(
        f"/api/events/{event_id}/tickets/purchase",
        json={
            "tier_id": tier_id,
            "buyer_name": "Demo Buyer",
            "buyer_phone": "690555104",
            "payment_ref": "MOMO-001",
        },
    )
    assert purchased.status_code == 201
    assert purchased.json()["status"] == "sold"

    duplicate = client.post(
        f"/api/events/{event_id}/tickets/purchase",
        json={
            "tier_id": tier_id,
            "buyer_name": "Other Buyer",
            "buyer_phone": "690555105",
            "payment_ref": "MOMO-001",
        },
    )
    assert duplicate.status_code == 409

    sold_out = client.post(
        f"/api/events/{event_id}/tickets/purchase",
        json={
            "tier_id": tier_id,
            "buyer_name": "Third Buyer",
            "buyer_phone": "690555106",
            "payment_ref": "MOMO-002",
        },
    )
    assert sold_out.status_code == 201

    no_more = client.post(
        f"/api/events/{event_id}/tickets/purchase",
        json={
            "tier_id": tier_id,
            "buyer_name": "Fourth Buyer",
            "buyer_phone": "690555107",
            "payment_ref": "MOMO-003",
        },
    )
    assert no_more.status_code == 409

    dashboard = client.get(f"/api/events/{event_id}/dashboard", headers=promoter)
    assert dashboard.status_code == 200
    assert dashboard.json()["sold"] == 2

    add_admin_or_gate_user(test_db, "690555108", "gate_staff")
    gate = login(client, "690555108")
    scanned = client.post(
        "/api/gate/scan",
        headers=gate,
        json={"ticket_code": purchased.json()["ticket_code"]},
    )
    assert scanned.status_code == 200
    assert scanned.json()["valid"] is True

    second_scan = client.post(
        "/api/gate/scan",
        headers=gate,
        json={"ticket_code": purchased.json()["ticket_code"]},
    )
    assert second_scan.status_code == 409
    assert second_scan.json()["reason"] == "ALREADY_USED"
