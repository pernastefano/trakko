from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from app.services import pwa

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=pwa.TEMPLATES_DIR)


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.get("/service-worker.js")
def service_worker() -> Response:
    # Served from the root so its scope covers the whole app; never cached by the browser.
    return Response(
        pwa.render_service_worker(),
        media_type="text/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"},
    )
