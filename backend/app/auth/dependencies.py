from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.database.session import get_db
from app.models.user import User
from app.core.security import SECRET_KEY, ALGORITHM

from fastapi.responses import RedirectResponse
from starlette import status

def redirect_to_login(request: Request, message: str):
    response = RedirectResponse(
        url=request.url_for("login_page"),
        status_code=status.HTTP_302_FOUND
    )
    response.set_cookie("flash_error", message)
    return response

def redirect_to_login_success(request: Request, message: str):
    response = RedirectResponse(
        url=request.url_for("login_page")
    )
    response.set_cookie("flash_success", message)
    return response


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    token = request.cookies.get("access_token")

    if not token:
        return redirect_to_login(request, "Please login to continue")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
    except JWTError:
        return redirect_to_login(request, "Session expired. Please login again")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return redirect_to_login(request, "User not found")

    return user


def admin_only(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    if current_user.role != "admin":
        return redirect_to_login(request, "Admin access only")

    return current_user


def company_only(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    if current_user.role != "company":
        return redirect_to_login(request, "Company access only")

    return current_user
