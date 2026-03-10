from fastapi import FastAPI,Request,status
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.routers.web import auth, admin_dashboard, tour_package, company, manual_booking, driver, company_dashboard, customer, vehicle , revenue, faq_document, chat_messages, chat_ws
from app.routers.api.webhooks import whatsapp,strip
from sqlalchemy.orm import Session
from app.utils.flash import flash_redirect

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(admin_dashboard.router)
app.include_router(company.router)
app.include_router(tour_package.router)
app.include_router(manual_booking.router)
app.include_router(driver.router)
app.include_router(company_dashboard.router)
app.include_router(customer.router)
app.include_router(vehicle.router)
app.include_router(whatsapp.router)
app.include_router(strip.router)
app.include_router(revenue.router)
app.include_router(faq_document.router)
app.include_router(chat_messages.router)
app.include_router(chat_ws.router)

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

@app.exception_handler(RuntimeError)
async def runtime_exception_handler(request: Request, exc: RuntimeError):

    if str(exc) == "DB_CONNECTION_FAILED":
        return flash_redirect(
            url=request.url_for("login_page"),
            message="Our service is temporarily unavailable. Please try again later.",
            category="error"
        )

    return RedirectResponse(request.url_for("login_page"))