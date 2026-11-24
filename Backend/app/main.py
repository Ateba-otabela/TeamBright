import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import inspect

from app.db import Base, engine
from app.errors import install_error_handlers, error_payload
from app.routers import auth, events, payments, tickets
from app.security import SystemClock

logger = logging.getLogger("bantu")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ticket_columns = {column["name"] for column in inspect(engine).get_columns("tickets")}
    if "event_id" not in ticket_columns:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE tickets ADD COLUMN event_id INTEGER REFERENCES events(id)"
            )
    if "price_xaf" not in ticket_columns:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE tickets ADD COLUMN price_xaf INTEGER NOT NULL DEFAULT 0"
            )
    payment_columns = {
        column["name"] for column in inspect(engine).get_columns("ticket_payments")
    }
    if "last_checked_at" not in payment_columns:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE ticket_payments ADD COLUMN last_checked_at "
                "DATETIME NULL"
            )
    claim_columns = {
        column["name"] for column in inspect(engine).get_columns("ticket_claims")
    }
    if "payment_id" not in claim_columns:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE ticket_claims ADD COLUMN payment_id INTEGER "
                "REFERENCES ticket_payments(id) ON DELETE SET NULL"
            )
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_ticket_claim_payment "
            "ON ticket_claims(payment_id)"
        )
    yield


app = FastAPI(
    title="Bantu Music 2.0 API",
    description=(
        "REST API for artist-created events, free ticket giveaways, and paid tickets via Fapshi.\n\n"
        "Use **Authorize** to provide a bearer token from `POST /auth/login` for protected "
        "operations. Public event and ticket listings can be tried without a token. "
        "Paid-ticket checkout uses Fapshi. Payment credentials stay on the backend."
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "auth", "description": "Register accounts and sign in to receive a bearer token."},
        {"name": "events", "description": "Manage artist events and read-only collaborator assignments."},
        {"name": "tickets", "description": "Create free or paid tickets and claim or purchase them."},
        {"name": "payments", "description": "Create and verify Fapshi ticket payments."},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={"tryItOutEnabled": True},
    lifespan=lifespan,
)
app.state.clock = SystemClock()


@app.middleware("http")
async def reject_oversized_bodies(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared_length = int(content_length)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content=error_payload("bad_request", "Invalid Content-Length", {}),
            )
    else:
        declared_length = 0
    if declared_length > 1_048_576:
        return JSONResponse(
            status_code=413,
            content=error_payload("body_too_large", "Request body exceeds 1 MB", {}),
        )
    body = await request.body()
    if len(body) > 1_048_576:
        return JSONResponse(
            status_code=413,
            content=error_payload("body_too_large", "Request body exceeds 1 MB", {}),
        )

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    request._receive = receive
    return await call_next(request)


install_error_handlers(app)

@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    logger.exception("Unhandled request error")
    return JSONResponse(
        status_code=500,
        content=error_payload("internal_error", "An internal error occurred", {}),
    )

app.include_router(auth.router)
app.include_router(events.router)
app.include_router(tickets.router)
app.include_router(payments.router)
