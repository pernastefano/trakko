import logging
import mimetypes

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import get_settings
from app.deps import current_user
from app.errors import AppError
from app.routers import about, auth, data, entries, event_types, preferences, pwa, stats, tracks
from app.services.pwa import STATIC_DIR

API_PREFIX = "/api/v1"


class RevalidatedStaticFiles(StaticFiles):
    """Static files that browsers must revalidate (ETag) before reusing a cached copy.

    Without this a browser may keep an old script for a while and run it against a new page.
    """

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


logger = logging.getLogger("uvicorn.error")

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
    if get_settings().secret_key_is_random:
        logger.warning(
            "TRAKKO_SECRET_KEY is not set: using a random key, so everyone is signed out "
            "whenever the app restarts. Set it in production."
        )

    app = FastAPI(title="TRAKKO", version=__version__)
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)

    api = APIRouter(prefix=API_PREFIX)
    api.include_router(auth.router)
    # Every route in here needs a signed-in user, whatever the endpoint itself asks for.
    protected = APIRouter(dependencies=[Depends(current_user)])
    for router in (tracks, event_types, entries, stats, data, preferences, about):
        protected.include_router(router.router)
    api.include_router(protected)
    app.include_router(api)
    app.include_router(pwa.router)
    app.mount("/static", RevalidatedStaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
