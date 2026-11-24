from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error(code: str, message: str, status: int, details=None):
    from fastapi import HTTPException
    raise HTTPException(status_code=status, detail={"code": code, "message": message, "details": details or {}})


def error_payload(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def install_error_handlers(app):
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            code = detail["code"]
            message = detail["message"]
            details = detail.get("details", {})
        else:
            codes = {404: "not_found", 405: "method_not_allowed", 413: "body_too_large"}
            code = codes.get(exc.status_code, "http_error")
            message = str(detail) if exc.status_code in (404, 405) else "Request could not be processed"
            details = {}
        return JSONResponse(status_code=exc.status_code, content=error_payload(code, message, details))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = {"fields": [
            {"field": ".".join(str(part) for part in item["loc"] if part not in ("body",)),
             "message": item["msg"]}
            for item in exc.errors()
        ]}
        return JSONResponse(status_code=422, content=error_payload("validation_error", "Validation failed", details))
