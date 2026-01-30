from fastapi import FastAPI,Request,status
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.routers.web import auth, admin_dashboard, tour_package, company, manual_booking, driver, company_dashboard, customer 
from app.routers.api.webhooks import whatsapp
from sqlalchemy.orm import Session

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(admin_dashboard.router)
app.include_router(company.router)
app.include_router(tour_package.router)
app.include_router(manual_booking.router)
app.include_router(driver.router)
app.include_router(company_dashboard.router)
app.include_router(customer.router)
app.include_router(whatsapp.router)


@app.exception_handler(FastAPIHTTPException)
async def auth_exception_handler(request: Request, exc: FastAPIHTTPException):
    if exc.status_code == 401:
        response = RedirectResponse(
            url=request.url_for("login_page"),
            status_code=status.HTTP_302_FOUND
        )
        response.set_cookie(
            "flash_error",
            "Please login to continue",
            max_age=5
        )
        return response
    elif exc.status_code == 403:
        response = RedirectResponse(
            url=request.url_for("login_page"),
            status_code=status.HTTP_302_FOUND
        )
        response.set_cookie(
            "flash_error",
            "You do not have permission to access this page",
            max_age=5
        )
        return response

    # Let FastAPI handle other errors
    raise exc