from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.database.session import get_db
from app.models.user import User
from app.core.security import SECRET_KEY, ALGORITHM

from fastapi.responses import RedirectResponse
from starlette import status
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.database.session import get_db
from app.models.user import User
from app.core.security import SECRET_KEY, ALGORITHM


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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

def admin_only(
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access only"
        )
    return current_user


def company_only(
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "company":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company access only"
        )
    return current_user
