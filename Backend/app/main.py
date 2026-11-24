import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.db import Base, engine
from app.errors import install_error_handlers, error_payload
from app.routers import auth, users, profiles, verification, directory, follows, admin
from app.security import SystemClock

logger = logging.getLogger("bantu")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Bantu Music 2.0", version="1.0.0", lifespan=lifespan)
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
app.include_router(users.router)
app.include_router(profiles.router)
app.include_router(verification.router)
app.include_router(directory.router)
app.include_router(follows.router)
app.include_router(admin.router)
