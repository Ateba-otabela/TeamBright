import json

import httpx
from sqlalchemy import select

from app.fapshi import FapshiClient, FapshiError
from app.models import Ticket, TicketClaim, TicketPayment
from app.routers.payments import get_fapshi_client, get_fapshi_webhook_secret


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
    return client.post(
        "/auth/login", json={"phone": phone, "pin": "1234"}
    ).json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


class FakeFapshi:
    def __init__(self):
        self.transactions = {}

    def initiate_payment(self, payload):
        trans_id = f"fapshi-{payload['externalId']}"
        transaction = {
            "transId": trans_id,
            "status": "CREATED",
            "amount": payload["amount"],
            "externalId": payload["externalId"],
            "userId": payload["userId"],
        }
        self.transactions[trans_id] = transaction
        return {
            "message": "Payment link generated",
            "link": f"https://sandbox.fapshi.com/pay/{trans_id}",
            "transId": trans_id,
        }

    def get_payment_status(self, trans_id):
        return self.transactions[trans_id]

    def get_transactions_by_user(self, user_id):
        return [
            item for item in self.transactions.values()
            if item["userId"] == user_id
        ]

    def expire_payment(self, trans_id):
        self.transactions[trans_id]["status"] = "EXPIRED"
        return self.transactions[trans_id]


class RejectingFapshi:
    def initiate_payment(self, payload):
        raise FapshiError(
            "Fapshi rejected the request",
            definitive=True,
            status_code=422,
        )


def test_fapshi_client_sends_credentials_and_550_xaf_payload():
    seen = {}

    def handle(request):
        seen["url"] = str(request.url)
        seen["apiuser"] = request.headers["apiuser"]
        seen["apikey"] = request.headers["apikey"]
        seen["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "message": "Payment link generated",
                "link": "https://sandbox.fapshi.com/pay/test-transaction",
                "transId": "test-transaction",
            },
        )

    client = FapshiClient(
        "sandbox-api-user",
        "sandbox-api-key",
        "https://sandbox.fapshi.com",
        transport=httpx.MockTransport(handle),
    )
    payload = {
        "amount": 550,
        "userId": "12",
        "externalId": "ticket-order-12",
        "message": "Ticket purchase",
        "redirectUrl": "http://127.0.0.1:8000/payments/fapshi/callback?reference=ticket-order-12",
    }

    result = client.initiate_payment(payload)

    assert result["transId"] == "test-transaction"
    assert seen == {
        "url": "https://sandbox.fapshi.com/initiate-pay",
        "apiuser": "sandbox-api-user",
        "apikey": "sandbox-api-key",
        "payload": payload,
    }


def test_paid_ticket_checkout_and_verified_webhook_issue_once(client, test_db):
    provider = FakeFapshi()
    client.app.dependency_overrides[get_fapshi_client] = lambda: provider
    client.app.dependency_overrides[get_fapshi_webhook_secret] = lambda: "test-secret"

    register(client, phone="690123456")
    artist_token = login(client, "690123456")
    ticket = client.post(
        "/tickets",
        json={
            "event_name": "Paid concert",
            "total_quantity": 1,
            "price_xaf": 2500,
        },
        headers=auth(artist_token),
    ).json()

    register(client, phone="690123457", role="fan")
    fan_token = login(client, "690123457")
    assert client.post(
        f"/tickets/{ticket['id']}/claim", headers=auth(fan_token)
    ).status_code == 402

    checkout = client.post(
        f"/payments/tickets/{ticket['id']}/checkout",
        headers=auth(fan_token),
    )
    assert checkout.status_code == 201
    payment = checkout.json()
    assert payment["amount_xaf"] == 2500
    assert payment["status"] == "pending"
    assert payment["checkout_url"].startswith("https://sandbox.fapshi.com/")

    retry = client.post(
        f"/payments/tickets/{ticket['id']}/checkout",
        headers=auth(fan_token),
    )
    assert retry.status_code == 200
    assert retry.json()["reference"] == payment["reference"]

    trans_id = f"fapshi-{payment['reference']}"
    provider.transactions[trans_id]["status"] = "SUCCESSFUL"
    body = json.dumps(provider.transactions[trans_id], separators=(",", ":")).encode()
    webhook = client.post(
        "/payments/fapshi/webhook",
        content=body,
        headers={"x-wh-secret": "test-secret"},
    )
    assert webhook.status_code == 200
    assert webhook.json()["status"] == "complete"
    assert client.post(
        "/payments/fapshi/webhook",
        content=body,
        headers={"x-wh-secret": "test-secret"},
    ).status_code == 200
    assert client.get(
        f"/payments/{payment['id']}", headers=auth(fan_token)
    ).json()["status"] == "complete"

    with test_db() as db:
        claim = db.query(TicketClaim).filter_by(ticket_id=ticket["id"]).one()
        assert claim.payment_id == payment["id"]
        assert db.get(Ticket, ticket["id"]).remaining_quantity == 0
        assert db.get(Ticket, ticket["id"]).status == "closed"
        assert db.get(TicketPayment, payment["id"]).status == "complete"


def test_failed_payment_releases_ticket_and_bad_webhook_secret_is_rejected(client, test_db):
    provider = FakeFapshi()
    client.app.dependency_overrides[get_fapshi_client] = lambda: provider
    client.app.dependency_overrides[get_fapshi_webhook_secret] = lambda: "test-secret"

    register(client, phone="690123456")
    artist_token = login(client, "690123456")
    ticket = client.post(
        "/tickets",
        json={
            "event_name": "Paid concert",
            "total_quantity": 1,
            "price_xaf": 1500,
        },
        headers=auth(artist_token),
    ).json()
    register(client, phone="690123457", role="fan")
    fan_token = login(client, "690123457")

    payment = client.post(
        f"/payments/tickets/{ticket['id']}/checkout",
        headers=auth(fan_token),
    ).json()
    trans_id = f"fapshi-{payment['reference']}"
    body = json.dumps(provider.transactions[trans_id]).encode()
    assert client.post(
        "/payments/fapshi/webhook",
        content=body,
        headers={"x-wh-secret": "invalid"},
    ).status_code == 401

    provider.transactions[trans_id]["status"] = "FAILED"
    status = client.get(
        f"/payments/{payment['id']}", headers=auth(fan_token)
    )
    assert status.status_code == 200
    assert status.json()["status"] == "failed"
    with test_db() as db:
        stored_ticket = db.get(Ticket, ticket["id"])
        assert stored_ticket.remaining_quantity == 1
        assert stored_ticket.status == "active"
        assert db.scalar(
            select(TicketPayment).where(TicketPayment.id == payment["id"])
        ).reserved is False


def test_payment_status_is_private_to_the_buyer(client):
    provider = FakeFapshi()
    client.app.dependency_overrides[get_fapshi_client] = lambda: provider

    register(client, phone="690123456")
    artist_token = login(client, "690123456")
    ticket = client.post(
        "/tickets",
        json={
            "event_name": "Paid concert",
            "total_quantity": 1,
            "price_xaf": 1000,
        },
        headers=auth(artist_token),
    ).json()
    register(client, phone="690123457", role="fan")
    fan_token = login(client, "690123457")
    payment = client.post(
        f"/payments/tickets/{ticket['id']}/checkout",
        headers=auth(fan_token),
    ).json()

    register(client, phone="690123458", role="fan")
    other_token = login(client, "690123458")
    assert client.get(
        f"/payments/{payment['id']}", headers=auth(other_token)
    ).status_code == 403


def test_late_payment_success_does_not_issue_a_duplicate_ticket(client, test_db):
    provider = FakeFapshi()
    client.app.dependency_overrides[get_fapshi_client] = lambda: provider

    register(client, phone="690123456")
    artist_token = login(client, "690123456")
    ticket = client.post(
        "/tickets",
        json={
            "event_name": "Paid concert",
            "total_quantity": 2,
            "price_xaf": 1000,
        },
        headers=auth(artist_token),
    ).json()
    register(client, phone="690123457", role="fan")
    fan_token = login(client, "690123457")

    first = client.post(
        f"/payments/tickets/{ticket['id']}/checkout",
        headers=auth(fan_token),
    ).json()
    first_id = f"fapshi-{first['reference']}"
    provider.transactions[first_id]["status"] = "FAILED"
    assert client.get(
        f"/payments/{first['id']}", headers=auth(fan_token)
    ).json()["status"] == "failed"

    second = client.post(
        f"/payments/tickets/{ticket['id']}/checkout",
        headers=auth(fan_token),
    ).json()
    provider.transactions[first_id]["status"] = "SUCCESSFUL"
    assert client.get(
        "/payments/fapshi/callback",
        params={"reference": first["reference"]},
    ).json()["status"] == "complete"

    second_id = f"fapshi-{second['reference']}"
    provider.transactions[second_id]["status"] = "SUCCESSFUL"
    second_status = client.get(
        f"/payments/{second['id']}", headers=auth(fan_token)
    )
    assert second_status.status_code == 200
    assert second_status.json()["status"] == "paid_unfulfilled"

    with test_db() as db:
        assert db.query(TicketClaim).filter_by(ticket_id=ticket["id"]).count() == 1
        assert db.get(Ticket, ticket["id"]).remaining_quantity == 1
        assert db.get(TicketPayment, second["id"]).reserved is False


def test_definitive_provider_rejection_releases_inventory(client, test_db):
    client.app.dependency_overrides[get_fapshi_client] = lambda: RejectingFapshi()
    register(client, phone="690123456")
    artist_token = login(client, "690123456")
    ticket = client.post(
        "/tickets",
        json={
            "event_name": "Paid concert",
            "total_quantity": 1,
            "price_xaf": 1000,
        },
        headers=auth(artist_token),
    ).json()
    register(client, phone="690123457", role="fan")
    fan_token = login(client, "690123457")

    rejected = client.post(
        f"/payments/tickets/{ticket['id']}/checkout",
        headers=auth(fan_token),
    )
    assert rejected.status_code == 502
    with test_db() as db:
        stored_ticket = db.get(Ticket, ticket["id"])
        payment = db.scalar(
            select(TicketPayment).where(TicketPayment.ticket_id == ticket["id"])
        )
        assert stored_ticket.remaining_quantity == 1
        assert stored_ticket.status == "active"
        assert payment.status == "failed"
        assert payment.reserved is False


def test_canceling_pending_payment_releases_inventory(client, test_db):
    provider = FakeFapshi()
    client.app.dependency_overrides[get_fapshi_client] = lambda: provider
    register(client, phone="690123456")
    artist_token = login(client, "690123456")
    ticket = client.post(
        "/tickets",
        json={
            "event_name": "Paid concert",
            "total_quantity": 1,
            "price_xaf": 1000,
        },
        headers=auth(artist_token),
    ).json()
    register(client, phone="690123457", role="fan")
    fan_token = login(client, "690123457")
    payment = client.post(
        f"/payments/tickets/{ticket['id']}/checkout",
        headers=auth(fan_token),
    ).json()

    cancelled = client.post(
        f"/payments/{payment['id']}/cancel", headers=auth(fan_token)
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "expired"
    with test_db() as db:
        stored_ticket = db.get(Ticket, ticket["id"])
        assert stored_ticket.remaining_quantity == 1
        assert stored_ticket.status == "active"
