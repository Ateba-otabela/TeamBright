import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.db import Base, engine
from app.errors import install_error_handlers, error_payload
from app.routers import auth, users, profiles, verification, directory, follows, admin
from app.routers import analyzer, canary_advisor, events, songs
from app.security import SystemClock

logger = logging.getLogger("sounddna")

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    app.state.database_engine = engine
    yield


app = FastAPI(
    title="SoundDNA & Canary Spider",
    description=(
        "CIMFEST 2026 music validation and career intelligence: compare studio demos "
        "against proven viral benchmarks and track release momentum with Canary Spider."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.state.clock = SystemClock()
app.state.database_engine = engine


@app.middleware("http")
async def reject_oversized_bodies(request: Request, call_next):
    max_body_size = (
        31 * 1024 * 1024
        if request.url.path.startswith("/analyzer/") or request.url.path == "/songs"
        else 1_048_576
    )
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
    if declared_length > max_body_size:
        return JSONResponse(
            status_code=413,
            content=error_payload("body_too_large", "Request body exceeds the upload limit", {}),
        )
    if request.method in {"GET", "HEAD"}:
        return await call_next(request)
    body = await request.body()
    if len(body) > max_body_size:
        return JSONResponse(
            status_code=413,
            content=error_payload("body_too_large", "Request body exceeds the upload limit", {}),
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
app.include_router(analyzer.router)
app.include_router(canary_advisor.router)
app.include_router(events.router)
app.include_router(songs.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def studio_home():
    from fastapi.responses import FileResponse

    return FileResponse(STATIC_DIR / "index.html")
