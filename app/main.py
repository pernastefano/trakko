import mimetypes

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.deps import require_auth
from app.errors import AppError
from app.routers import auth, data, entries, event_types, pwa, stats, tracks
from app.services.pwa import STATIC_DIR

API_PREFIX = "/api/v1"

mimetypes.add_type("application/manifest+json", ".webmanifest")


def _validation_detail(error: RequestValidationError) -> str:
    messages = []
    for item in error.errors():
        location = ".".join(str(part) for part in item["loc"] if part not in ("body", "query"))
        message = item["msg"].removeprefix("Value error, ")
        messages.append(f"{location}: {message}" if location else message)
    return "; ".join(messages)


def _handle_app_error(_request: Request, error: AppError) -> JSONResponse:
    return JSONResponse({"detail": error.detail}, status_code=error.status_code)


def _handle_validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
    return JSONResponse({"detail": _validation_detail(error)}, status_code=422)


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.password is not None and settings.secret_key is None:
        raise RuntimeError("TRAKKO_SECRET_KEY must be set when TRAKKO_PASSWORD is set")

    app = FastAPI(title="TRAKKO")
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)

    api = APIRouter(prefix=API_PREFIX)
    api.include_router(auth.router)
    protected = APIRouter(dependencies=[Depends(require_auth)])
    for router in (tracks, event_types, entries, stats, data):
        protected.include_router(router.router)
    api.include_router(protected)
    app.include_router(api)
    app.include_router(pwa.router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
