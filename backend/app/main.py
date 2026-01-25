from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.routers.web import auth, admin_dashboard, tour_package, company, manual_booking, driver, company_dashboard   

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(admin_dashboard.router)
app.include_router(company.router)
app.include_router(tour_package.router)
app.include_router(manual_booking.router)
app.include_router(driver.router)
app.include_router(company_dashboard.router)


