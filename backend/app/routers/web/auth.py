from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.templates import templates
from app.database.session import get_db
from app.models.user import User
from app.core.security import verify_password, create_access_token
from app.schemas.user import LoginForm
from app.auth.dependencies import get_current_user
from fastapi.responses import HTMLResponse
from app.auth.dependencies import redirect_to_login

router = APIRouter(prefix="/auth", tags=["Auth"])

# ------------------------
# Login Page
# ------------------------
@router.get("/login", response_class=HTMLResponse, name="login_page")
def login_page(request: Request):
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "error": None
        }
    )

# ------------------------
# Login Submit
# ------------------------
@router.post("/login", response_class=HTMLResponse, name="login_submit")
def login(
    request: Request,
    form: LoginForm = Depends(LoginForm.as_form),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form.email).first()

    if not user or not verify_password(form.password, user.password_hash):
        return redirect_to_login(request, "Invalid email or password")
        
    if user.company.status == "inactive":
        return redirect_to_login(request, "Your company account is inactive. Please contact support.")

    token = create_access_token({
        "user_id": user.id,
        "role": user.role
    })

    response = RedirectResponse(
        url=request.url_for("dashboard"),
        status_code=302
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax"
    )
    
    response.set_cookie(
        key="user_role",
        value=user.role,
        httponly=False,
        samesite="lax"
    )

    return response

@router.post("/logout", name="logout")
def logout(request: Request):
    """
    Logout the user: delete cookies and respond with success.
    """
    response = JSONResponse({"success": True})  # AJAX-friendly response
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("user_role", path="/")
    return response