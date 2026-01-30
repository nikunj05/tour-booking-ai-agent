from fastapi import APIRouter, Form, Depends,BackgroundTasks, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.templates import templates
from app.database.session import get_db
from app.models.user import User
from app.core.security import ALGORITHM, SECRET_KEY, hash_password, verify_password, create_access_token, create_reset_token, verify_reset_token
from app.schemas.user import LoginForm
from app.auth.dependencies import get_current_user
from fastapi.responses import HTMLResponse
from app.auth.dependencies import redirect_to_login
from app.services.email_service import send_reset_password_email
from jose import jwt
from dotenv import load_dotenv
import os
from app.routers.web.company_dashboard import dashboard_index

BASE_URL = os.getenv("BASE_URL")

import os
load_dotenv()

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

    if user.role == "company":
        response = RedirectResponse(
            url=request.url_for("dashboard_index"),
            status_code=302
        )
    else:
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

@router.get("/forgot-password", name="forgot_password_page")
def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        "auth/forgot_password.html",
        {"request": request}
    )

@router.post("/forgot-password", name="forgot_password_submit")
def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()

    # ❌ Email NOT found → redirect with flash message
    if not user:
        return redirect_to_login(
            request,
            "Email address not found. Please check and try again."
        )

    # ✅ Email found → send reset link
    token = create_reset_token(user.id)
    reset_link = f"{BASE_URL}/auth/reset-password?token={token}"

    background_tasks.add_task(
        send_reset_password_email,
        email,
        reset_link
    )

    return redirect_to_login(
        request,
        "Password reset link has been sent to your email."
    )

    

@router.get("/reset-password", name="reset_password_page")
def reset_password_page(request: Request, token: str):
    return templates.TemplateResponse(
        "auth/reset_password.html",
        {
            "request": request,
            "token": token
        }
    )


@router.post("/reset-password", name="reset_password_submit")
def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    if password != confirm_password:
        return templates.TemplateResponse(
            "auth/reset_password.html",
            {
                "request": request,
                "token": token,
                "error": "Passwords do not match"
            },
            status_code=400
        )

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user_id = payload.get("sub")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return templates.TemplateResponse(
            "auth/reset_password.html",
            {
                "request": request,
                "error": "Invalid or expired token"
            },
            status_code=400
        )

    user.password_hash = hash_password(password)
    db.commit()

    return RedirectResponse(
        request.url_for("login_page"),
        status_code=303
    )
