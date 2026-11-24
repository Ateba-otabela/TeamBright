from app.models import Event, EventCollaborator, Ticket, TicketClaim


def register(client, *, phone, role="artist", name="Test user"):
    return client.post(
        "/auth/register",
        json={
            "name": name,
            "phone": phone,
            "pin": "1234",
            "role": role,
            "city": "Douala",
        },
    )


def login(client, phone):
    response = client.post("/auth/login", json={"phone": phone, "pin": "1234"})
    return response.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_openapi_exposes_only_auth_events_and_tickets(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert paths
    assert all(
        path.startswith(("/auth/", "/events", "/tickets", "/payments"))
        for path in paths
    )
    assert "/events" in paths
    assert "/tickets/{ticket_id}/claim" in paths
    assert "/events/{event_id}/collaborators" in paths
    assert "/events/my-collaborations" in paths
    assert "/payments/tickets/{ticket_id}/checkout" in paths
    assert "/payments/fapshi/webhook" in paths
    assert client.get("/me").status_code == 404
    assert client.get("/directory").status_code == 404


def test_artist_can_create_and_list_events(client, test_db):
    register(client, phone="690123456")
    artist_token = login(client, "690123456")

    created = client.post(
        "/events",
        json={
            "event_name": "  Douala Live  ",
            "description": "A live music event",
            "event_date": "2026-12-20T18:00:00Z",
            "venue": "Akwa",
            "city": "Douala",
        },
        headers=auth(artist_token),
    )
    assert created.status_code == 201
    event = created.json()
    assert event["event_name"] == "Douala Live"
    assert event["artist_id"] == 1
    assert client.get(f"/events/{event['id']}").json()["venue"] == "Akwa"
    filtered = client.get("/events?event_name=douala&artist_id=1")
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["id"] == event["id"]
    assert client.get("/events?event_name=%25").json()["total"] == 0

    with test_db() as db:
        assert db.get(Event, event["id"]).artist_id == 1

    register(client, phone="690123457", role="fan")
    fan_token = login(client, "690123457")
    forbidden = client.post(
        "/events",
        json={"event_name": "Fan event"},
        headers=auth(fan_token),
    )
    assert forbidden.status_code == 403
    assert client.get("/events/not-an-id").status_code == 422
    assert client.get("/events/999999").status_code == 404


def test_ticket_giveaway_links_to_artist_event_and_claims_once(client, test_db):
    register(client, phone="690123456")
    artist_token = login(client, "690123456")
    event = client.post(
        "/events",
        json={"event_name": "Buea Festival", "city": "Buea"},
        headers=auth(artist_token),
    ).json()
    created = client.post(
        "/tickets",
        json={
            "event_id": event["id"],
            "event_name": "Different name is replaced by event",
            "total_quantity": 2,
            "description": "Free tickets",
        },
        headers=auth(artist_token),
    )
    assert created.status_code == 201
    ticket = created.json()
    assert ticket["event_id"] == event["id"]
    assert ticket["event_name"] == "Buea Festival"
    assert ticket["remaining_quantity"] == 2

    register(client, phone="690123457", role="fan")
    fan_token = login(client, "690123457")
    claimed = client.post(
        f"/tickets/{ticket['id']}/claim", headers=auth(fan_token)
    )
    assert claimed.status_code == 200
    assert claimed.json()["remaining_quantity"] == 1
    assert client.post(
        f"/tickets/{ticket['id']}/claim", headers=auth(fan_token)
    ).status_code == 409
    assert client.get(f"/tickets/{ticket['id']}").json()["remaining_quantity"] == 1

    fan = register(client, phone="690123458", role="fan").json()
    second_fan_token = login(client, "690123458")
    sold_out = client.post(
        f"/tickets/{ticket['id']}/claim", headers=auth(second_fan_token)
    )
    assert sold_out.status_code == 200
    assert sold_out.json()["remaining_quantity"] == 0
    assert sold_out.json()["status"] == "closed"

    with test_db() as db:
        assert db.query(TicketClaim).filter_by(ticket_id=ticket["id"]).count() == 2
        assert db.get(Ticket, ticket["id"]).event_id == event["id"]
    assert client.get(f"/tickets?event_id={event['id']}").json()["total"] == 1


def test_ticket_validation_and_event_ownership(client):
    register(client, phone="690123456")
    artist_token = login(client, "690123456")
    event = client.post(
        "/events",
        json={"event_name": "Owner event"},
        headers=auth(artist_token),
    ).json()

    register(client, phone="690123457")
    other_artist_token = login(client, "690123457")
    forbidden = client.post(
        "/tickets",
        json={"event_id": event["id"], "event_name": "Owner event", "total_quantity": 1},
        headers=auth(other_artist_token),
    )
    assert forbidden.status_code == 403

    for payload in (
        {"event_name": "Event", "total_quantity": 0},
        {"event_name": "Event", "total_quantity": 10001},
        {"event_name": " ", "total_quantity": 1},
        {"event_name": "Event", "total_quantity": 1, "price_xaf": 50},
    ):
        response = client.post("/tickets", json=payload, headers=auth(artist_token))
        assert response.status_code == 422

    missing = client.post(
        "/tickets",
        json={"event_id": 999999, "event_name": "Missing event", "total_quantity": 1},
        headers=auth(artist_token),
    )
    assert missing.status_code == 404
    assert client.get("/tickets/not-an-id").status_code == 422


def test_artist_manages_collaborators_and_collaborators_only_view(client, test_db):
    register(client, phone="690123456")
    artist_token = login(client, "690123456")
    collaborator = register(
        client, phone="690123457", role="collaborator", name="Event collaborator"
    ).json()
    collaborator_token = login(client, "690123457")
    fan = register(client, phone="690123458", role="fan").json()
    fan_token = login(client, "690123458")

    event = client.post(
        "/events",
        json={"event_name": "Shared event"},
        headers=auth(artist_token),
    ).json()
    assert client.post(
        f"/events/{event['id']}/collaborators",
        json={"user_id": 999999},
        headers=auth(artist_token),
    ).status_code == 404
    assert client.post(
        f"/events/{event['id']}/collaborators",
        json={"user_id": fan["id"]},
        headers=auth(artist_token),
    ).status_code == 422
    assert client.get(
        "/events/my-collaborations", headers=auth(artist_token)
    ).status_code == 403
    assigned = client.post(
        f"/events/{event['id']}/collaborators",
        json={"user_id": collaborator["id"]},
        headers=auth(artist_token),
    )
    assert assigned.status_code == 201
    assert assigned.json()["user_id"] == collaborator["id"]
    assert assigned.json()["name"] == "Event collaborator"

    collaborations = client.get(
        "/events/my-collaborations", headers=auth(collaborator_token)
    )
    assert collaborations.status_code == 200
    assert collaborations.json()["total"] == 1
    assert collaborations.json()["items"][0]["id"] == event["id"]
    assert client.get(
        f"/events/{event['id']}/collaborators", headers=auth(collaborator_token)
    ).json()[0]["user_id"] == collaborator["id"]
    assert client.post(
        f"/tickets",
        json={"event_name": "Shared event", "event_id": event["id"], "total_quantity": 1},
        headers=auth(collaborator_token),
    ).status_code == 403

    duplicate = client.post(
        f"/events/{event['id']}/collaborators",
        json={"user_id": collaborator["id"]},
        headers=auth(artist_token),
    )
    assert duplicate.status_code == 409
    assert client.get(
        f"/events/{event['id']}/collaborators", headers=auth(fan_token)
    ).status_code == 403

    register(client, phone="690123459")
    other_artist_token = login(client, "690123459")
    assert client.delete(
        f"/events/{event['id']}/collaborators/{collaborator['id']}",
        headers=auth(other_artist_token),
    ).status_code == 403
    removed = client.delete(
        f"/events/{event['id']}/collaborators/{collaborator['id']}",
        headers=auth(artist_token),
    )
    assert removed.status_code == 200
    assert removed.json()["assigned"] is False
    assert client.get(
        "/events/my-collaborations", headers=auth(collaborator_token)
    ).json()["total"] == 0

    with test_db() as db:
        assert db.query(EventCollaborator).filter_by(event_id=event["id"]).count() == 0
