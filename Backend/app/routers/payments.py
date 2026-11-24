import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import case, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.errors import error
from app.fapshi import FapshiClient, FapshiError
from app.models import Ticket, TicketClaim, TicketPayment, User
from app.schemas import TicketPaymentOut

logger = logging.getLogger("bantu.payments")
router = APIRouter(prefix="/payments", tags=["payments"])

STATUS_MAP = {
    "CREATED": "pending",
    "PENDING": "processing",
    "SUCCESSFUL": "complete",
    "FAILED": "failed",
    "EXPIRED": "expired",
}
TERMINAL_FAILURES = {"failed", "expired"}
STATUS_CHECK_INTERVAL = timedelta(seconds=12)


def get_fapshi_client() -> FapshiClient:
    settings = get_settings()
    if not settings.fapshi_public_user or not settings.fapshi_api_key:
        error("payment_not_configured", "Fapshi is not configured", 503)
    return FapshiClient(
        settings.fapshi_public_user.get_secret_value(),
        settings.fapshi_api_key.get_secret_value(),
        settings.fapshi_base_url,
    )


def get_fapshi_webhook_secret() -> str:
    webhook_secret = get_settings().fapshi_webhook_secret
    if not webhook_secret:
        error("webhook_not_configured", "Fapshi webhook verification is not configured", 503)
    return webhook_secret.get_secret_value()


def _payment_out(payment: TicketPayment) -> TicketPaymentOut:
    return TicketPaymentOut(
        id=payment.id,
        ticket_id=payment.ticket_id,
        reference=payment.reference,
        amount_xaf=payment.amount_xaf,
        status=payment.status,
        checkout_url=payment.authorization_url,
        created_at=payment.created_at,
    )


def _fapshi_user_id(payment: TicketPayment) -> str:
    return str(payment.user_id)


def _callback_url(base_url: str, reference: str) -> str:
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["reference"] = reference
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def _normalize_status(status: object) -> str:
    if not isinstance(status, str) or status not in STATUS_MAP:
        raise FapshiError("Fapshi returned an unknown payment status")
    return STATUS_MAP[status]


def _verify_transaction(payment: TicketPayment, transaction: dict) -> str:
    trans_id = transaction.get("transId")
    if (
        not isinstance(trans_id, str)
        or (payment.provider_payment_id and trans_id != payment.provider_payment_id)
        or transaction.get("amount") != payment.amount_xaf
        or transaction.get("externalId") != payment.reference
        or str(transaction.get("userId", "")) != _fapshi_user_id(payment)
    ):
        raise FapshiError("Fapshi transaction does not match the local order")
    return _normalize_status(transaction.get("status"))


def _release_reservation(db: Session, payment: TicketPayment) -> None:
    if not payment.reserved:
        return
    db.execute(
        update(Ticket)
        .where(Ticket.id == payment.ticket_id)
        .values(
            remaining_quantity=Ticket.remaining_quantity + 1,
            status=case(
                (
                    (Ticket.status == "closed") & (Ticket.remaining_quantity == 0),
                    "active",
                ),
                else_=Ticket.status,
            ),
        )
    )
    payment.reserved = False
    payment.reservation_key = None


def _mark_failed_and_release(db: Session, payment: TicketPayment) -> TicketPayment:
    _release_reservation(db, payment)
    payment.status = "failed"
    db.commit()
    db.refresh(payment)
    return payment


def _reserve_one(db: Session, ticket_id: int) -> bool:
    result = db.execute(
        update(Ticket)
        .where(
            Ticket.id == ticket_id,
            Ticket.status == "active",
            Ticket.remaining_quantity > 0,
        )
        .values(
            remaining_quantity=Ticket.remaining_quantity - 1,
            status=case(
                (Ticket.remaining_quantity == 1, "closed"),
                else_=Ticket.status,
            ),
        )
    )
    return result.rowcount == 1


def _apply_provider_status(
    db: Session,
    payment: TicketPayment,
    transaction: dict,
) -> TicketPayment:
    status = _verify_transaction(payment, transaction)
    payment.provider_payment_id = transaction["transId"]
    payment.last_checked_at = datetime.now(timezone.utc)

    if payment.status == "complete":
        return payment
    if status == "complete":
        if not payment.reserved:
            if not _reserve_one(db, payment.ticket_id):
                payment.status = "paid_unfulfilled"
                db.commit()
                return payment
            payment.reserved = True
        claim = db.scalar(
            select(TicketClaim).where(
                TicketClaim.ticket_id == payment.ticket_id,
                TicketClaim.user_id == payment.user_id,
            )
        )
        if claim and claim.payment_id != payment.id:
            _release_reservation(db, payment)
            payment.status = "paid_unfulfilled"
            db.commit()
            return payment
        if not claim:
            db.add(
                TicketClaim(
                    ticket_id=payment.ticket_id,
                    user_id=payment.user_id,
                    payment_id=payment.id,
                )
            )
        payment.status = "complete"
        payment.reserved = False
        payment.reservation_key = None
    elif status in TERMINAL_FAILURES:
        _release_reservation(db, payment)
        payment.status = status
    else:
        payment.status = status

    payment_id = payment.id
    ticket_id = payment.ticket_id
    user_id = payment.user_id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        current_payment = db.get(TicketPayment, payment_id)
        claim = db.scalar(
            select(TicketClaim).where(
                TicketClaim.ticket_id == ticket_id,
                TicketClaim.user_id == user_id,
            )
        )
        if claim and claim.payment_id == payment_id:
            return current_payment
        if claim:
            _release_reservation(db, current_payment)
            current_payment.status = "paid_unfulfilled"
            db.commit()
            db.refresh(current_payment)
            return current_payment
        raise
    db.refresh(payment)
    return payment


def _needs_status_check(payment: TicketPayment) -> bool:
    if payment.status not in {"pending", "processing"}:
        return False
    if not payment.last_checked_at:
        return True
    last_checked_at = payment.last_checked_at
    if last_checked_at.tzinfo is None:
        last_checked_at = last_checked_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last_checked_at >= STATUS_CHECK_INTERVAL


def _reconcile_payment(
    db: Session,
    payment: TicketPayment,
    fapshi: FapshiClient,
    *,
    force: bool = False,
) -> TicketPayment:
    if not force and not _needs_status_check(payment):
        return payment

    if not payment.provider_payment_id:
        matches = fapshi.get_transactions_by_user(_fapshi_user_id(payment))
        transaction = next(
            (
                item
                for item in matches
                if item.get("externalId") == payment.reference
            ),
            None,
        )
        if not transaction:
            return _mark_failed_and_release(db, payment)
        if (
            transaction.get("amount") != payment.amount_xaf
            or str(transaction.get("userId", "")) != _fapshi_user_id(payment)
            or not isinstance(transaction.get("transId"), str)
        ):
            raise FapshiError("Fapshi transaction does not match the local order")
        payment.provider_payment_id = transaction["transId"]
        db.commit()

    transaction = fapshi.get_payment_status(payment.provider_payment_id)
    return _apply_provider_status(db, payment, transaction)


@router.post(
    "/tickets/{ticket_id}/checkout",
    response_model=TicketPaymentOut,
    status_code=201,
    summary="Start paid-ticket checkout",
    description=(
        "Reserve one ticket and create a Fapshi payment link. Free tickets must use "
        "the ticket claim endpoint. Each account may purchase at most one ticket per listing."
    ),
)
def create_ticket_checkout(
    ticket_id: int,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    fapshi: FapshiClient = Depends(get_fapshi_client),
):
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        error("not_found", "Ticket not found", 404)
    if ticket.price_xaf <= 0:
        error("free_ticket", "Free tickets must be claimed instead of purchased", 409)

    claimed = db.scalar(
        select(TicketClaim).where(
            TicketClaim.ticket_id == ticket_id,
            TicketClaim.user_id == user.id,
        )
    )
    if claimed:
        error("ticket_already_claimed", "You already have a ticket for this event", 409)

    pending = db.scalar(
        select(TicketPayment)
        .where(
            TicketPayment.ticket_id == ticket_id,
            TicketPayment.user_id == user.id,
            TicketPayment.status.in_(("pending", "processing")),
        )
        .order_by(TicketPayment.id.desc())
    )
    if pending:
        if not pending.authorization_url:
            error("payment_pending", "Your checkout is still being initialized", 409)
        response.status_code = 200
        return _payment_out(pending)

    if not _reserve_one(db, ticket_id):
        error("ticket_unavailable", "No tickets are available to purchase", 409)

    payment = TicketPayment(
        ticket_id=ticket_id,
        user_id=user.id,
        reference=f"tb_{secrets.token_urlsafe(24)}",
        amount_xaf=ticket.price_xaf,
        reservation_key=f"{ticket_id}:{user.id}",
    )
    db.add(payment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_pending = db.scalar(
            select(TicketPayment).where(
                TicketPayment.ticket_id == ticket_id,
                TicketPayment.user_id == user.id,
                TicketPayment.status.in_(("pending", "processing")),
            )
        )
        if existing_pending and existing_pending.authorization_url:
            response.status_code = 200
            return _payment_out(existing_pending)
        if existing_pending:
            error("payment_pending", "Your checkout is still being initialized", 409)
        raise
    db.refresh(payment)

    settings = get_settings()
    request_payload = {
        "amount": payment.amount_xaf,
        "userId": _fapshi_user_id(payment),
        "externalId": payment.reference,
        "message": f"Ticket purchase: {ticket.event_name}"[:200],
        "redirectUrl": _callback_url(settings.fapshi_redirect_url, payment.reference),
    }
    try:
        result = fapshi.initiate_payment(request_payload)
        trans_id = result.get("transId")
        link = result.get("link")
        parsed_link = urlparse(link) if isinstance(link, str) else None
        if (
            not isinstance(trans_id, str)
            or not trans_id
            or not parsed_link
            or parsed_link.scheme != "https"
            or not parsed_link.hostname
            or not (
                parsed_link.hostname == "fapshi.com"
                or parsed_link.hostname.endswith(".fapshi.com")
            )
        ):
            raise FapshiError("Fapshi returned invalid checkout details")
    except FapshiError as exc:
        logger.warning("Fapshi checkout initialization failed for payment %s", payment.id)
        if exc.definitive:
            _mark_failed_and_release(db, payment)
            error("payment_provider_error", str(exc), 502)
        try:
            payment = _reconcile_payment(db, payment, fapshi, force=True)
        except FapshiError:
            payment.status = "processing"
            db.commit()
            error(
                "payment_initialization_unconfirmed",
                "Checkout could not be confirmed. Check this payment status before retrying.",
                502,
                {"payment_id": payment.id},
            )
        if payment.provider_payment_id:
            if payment.status == "complete":
                return _payment_out(payment)
            error(
                "payment_initialization_unconfirmed",
                "Fapshi created or may have created this payment. Check or cancel it before retrying.",
                502,
                {"payment_id": payment.id},
            )
        error(
            "payment_provider_error",
            "Fapshi did not create a transaction. You may retry checkout.",
            502,
        )

    payment.provider_payment_id = trans_id
    payment.authorization_url = link
    payment.status = "pending"
    db.commit()
    db.refresh(payment)
    return _payment_out(payment)


@router.post(
    "/{payment_id}/cancel",
    response_model=TicketPaymentOut,
    summary="Cancel my pending payment",
    description="Expire a Fapshi payment link and release its reservation after confirming its status.",
)
def cancel_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    fapshi: FapshiClient = Depends(get_fapshi_client),
):
    payment = db.get(TicketPayment, payment_id)
    if not payment:
        error("not_found", "Payment not found", 404)
    if payment.user_id != user.id:
        error("payment_forbidden", "You can only cancel your own payments", 403)
    if payment.status not in {"pending", "processing"}:
        error("payment_not_cancelable", "Only pending payments can be canceled", 409)

    try:
        payment = _reconcile_payment(db, payment, fapshi, force=True)
        if payment.status in TERMINAL_FAILURES:
            return _payment_out(payment)
        if payment.status == "complete":
            error("payment_not_cancelable", "A successful payment cannot be canceled", 409)
        fapshi.expire_payment(payment.provider_payment_id)
        verified = fapshi.get_payment_status(payment.provider_payment_id)
        payment = _apply_provider_status(db, payment, verified)
    except FapshiError as exc:
        logger.warning("Fapshi cancellation failed for payment %s", payment.id)
        if exc.status_code == 400 and payment.provider_payment_id:
            try:
                verified = fapshi.get_payment_status(payment.provider_payment_id)
                payment = _apply_provider_status(db, payment, verified)
            except FapshiError:
                error("payment_cancellation_failed", "Could not confirm payment cancellation", 502)
        else:
            error("payment_cancellation_failed", "Could not confirm payment cancellation", 502)
    if payment.status not in TERMINAL_FAILURES:
        error("payment_not_canceled", "Fapshi has not confirmed payment expiry", 409)
    return _payment_out(payment)


@router.get(
    "/fapshi/callback",
    response_model=TicketPaymentOut,
    summary="Verify a Fapshi return",
    description="Reconcile the payment with Fapshi before issuing a ticket.",
)
def fapshi_callback(
    reference: str,
    db: Session = Depends(get_db),
    fapshi: FapshiClient = Depends(get_fapshi_client),
):
    payment = db.scalar(select(TicketPayment).where(TicketPayment.reference == reference))
    if not payment:
        error("not_found", "Payment not found", 404)
    if payment.status in {"complete", "paid_unfulfilled"}:
        return _payment_out(payment)
    try:
        payment = _reconcile_payment(db, payment, fapshi, force=True)
    except FapshiError:
        logger.warning("Fapshi callback verification failed for payment %s", payment.id)
        error("payment_verification_failed", "Could not verify this payment", 502)
    return _payment_out(payment)


@router.post(
    "/fapshi/webhook",
    summary="Receive Fapshi webhook",
    description="Validates the shared webhook secret and verifies the transaction with Fapshi.",
)
async def fapshi_webhook(
    request: Request,
    db: Session = Depends(get_db),
    fapshi: FapshiClient = Depends(get_fapshi_client),
    webhook_secret: str = Depends(get_fapshi_webhook_secret),
):
    if not hmac.compare_digest(
        webhook_secret, request.headers.get("x-wh-secret", "")
    ):
        error("invalid_webhook_secret", "Invalid Fapshi webhook secret", 401)

    try:
        event = json.loads(await request.body())
    except json.JSONDecodeError:
        error("invalid_webhook_payload", "Webhook body must be valid JSON", 400)
    if not isinstance(event, dict):
        error("invalid_webhook_payload", "Webhook body must be a JSON object", 400)

    trans_id = event.get("transId")
    reference = event.get("externalId")
    if not isinstance(trans_id, str) or not trans_id:
        error("invalid_webhook_payload", "Fapshi event is missing its transaction ID", 400)
    payment = None
    if isinstance(reference, str):
        payment = db.scalar(
            select(TicketPayment).where(TicketPayment.reference == reference)
        )
    if not payment:
        payment = db.scalar(
            select(TicketPayment).where(
                TicketPayment.provider_payment_id == trans_id
            )
        )
    if not payment:
        return {"received": True, "processed": False}
    if payment.provider_payment_id and payment.provider_payment_id != trans_id:
        error("payment_mismatch", "Fapshi transaction does not match the local order", 400)
    if payment.status in {"complete", "paid_unfulfilled"}:
        return {"received": True, "processed": True, "status": payment.status}

    try:
        verified = fapshi.get_payment_status(trans_id)
        payment = _apply_provider_status(db, payment, verified)
    except FapshiError:
        logger.warning("Fapshi webhook verification failed for payment %s", payment.id)
        error("payment_verification_failed", "Could not verify this payment", 502)
    return {
        "received": True,
        "processed": payment.status != "paid_unfulfilled",
        "status": payment.status,
    }


@router.get(
    "/{payment_id}",
    response_model=TicketPaymentOut,
    summary="Get my payment status",
    description="Returns only the authenticated user's payment and reconciles status with Fapshi.",
)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    fapshi: FapshiClient = Depends(get_fapshi_client),
):
    payment = db.get(TicketPayment, payment_id)
    if not payment:
        error("not_found", "Payment not found", 404)
    if payment.user_id != user.id:
        error("payment_forbidden", "You can only view your own payments", 403)
    if _needs_status_check(payment):
        try:
            payment = _reconcile_payment(db, payment, fapshi)
        except FapshiError:
            logger.warning("Fapshi status check failed for payment %s", payment.id)
            error("payment_verification_failed", "Could not verify this payment", 502)
    return _payment_out(payment)
