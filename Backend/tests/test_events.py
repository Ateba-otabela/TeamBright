def register_and_login(client, phone):
    registered = client.post(
        "/auth/register",
        json={
            "name": "Event organizer",
            "phone": phone,
            "pin": "1234",
            "role": "promoter",
            "city": "Douala",
        },
    )
    assert registered.status_code == 201
    response = client.post(
        "/auth/login",
        json={"phone": phone, "pin": "1234"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_event(client, headers, *, total_tickets=10):
    response = client.post(
        "/events",
        headers=headers,
        json={
            "title": "CIMFEST",
            "event_date": "2026-12-10T19:00:00Z",
            "venue": "Douala Arena",
            "ticket_price": "10000.00",
            "total_tickets": total_tickets,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_collaborator_assignment_and_sales_are_limited_to_allocation(client):
    headers = register_and_login(client, "690123471")
    event = create_event(client, headers)

    assigned = client.post(
        f"/events/{event['id']}/collaborators",
        headers=headers,
        json={
            "name": "Ticket seller",
            "email": "Seller@Example.com",
            "commission_percent": "12.5",
            "tickets_assigned": 5,
        },
    )
    assert assigned.status_code == 201
    collaborator = assigned.json()
    assert collaborator["email"] == "seller@example.com"
    assert collaborator["commission_per_ticket"] == 1250
    assert collaborator["tickets_remaining"] == 5

    sold = client.post(
        f"/events/{event['id']}/collaborators/{collaborator['id']}/sales",
        headers=headers,
        json={"quantity": 3},
    )
    assert sold.status_code == 200
    assert sold.json()["tickets_sold"] == 3
    assert sold.json()["tickets_remaining"] == 2

    too_many = client.post(
        f"/events/{event['id']}/collaborators/{collaborator['id']}/sales",
        headers=headers,
        json={"quantity": 3},
    )
    assert too_many.status_code == 409
    assert too_many.json()["error"]["details"]["tickets_remaining"] == 2

    allocation_exceeded = client.post(
        f"/events/{event['id']}/collaborators",
        headers=headers,
        json={
            "name": "Another seller",
            "phone": "+237690123472",
            "commission_percent": "10",
            "tickets_assigned": 6,
        },
    )
    assert allocation_exceeded.status_code == 409


def test_collaborators_require_one_contact_and_event_owner(client):
    owner_headers = register_and_login(client, "690123473")
    other_headers = register_and_login(client, "690123474")
    event = create_event(client, owner_headers)

    missing_contact = client.post(
        f"/events/{event['id']}/collaborators",
        headers=owner_headers,
        json={
            "name": "No contact",
            "commission_percent": 10,
            "tickets_assigned": 1,
        },
    )
    assert missing_contact.status_code == 422

    forbidden = client.get(
        f"/events/{event['id']}/collaborators",
        headers=other_headers,
    )
    assert forbidden.status_code == 404

    assigned = client.post(
        f"/events/{event['id']}/collaborators",
        headers=owner_headers,
        json={
            "name": "Ticket seller",
            "phone": "+237690123475",
            "commission_percent": 10,
            "tickets_assigned": 1,
        },
    )
    assert assigned.status_code == 201

    duplicate = client.post(
        f"/events/{event['id']}/collaborators",
        headers=owner_headers,
        json={
            "name": "Same seller",
            "phone": "+237 690 123 475",
            "commission_percent": 10,
            "tickets_assigned": 1,
        },
    )
    assert duplicate.status_code == 409
