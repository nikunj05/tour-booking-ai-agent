from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from app.core.templates import templates
from app.auth.dependencies import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/", response_class=HTMLResponse, name="dashboard")
def dashboard(
    request: Request,
):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
        }
    )
