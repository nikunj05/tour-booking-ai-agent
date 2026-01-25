from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.session import get_db
from app.models.manual_booking import ManualBooking
from app.models.user import User
from app.models.tour_package import TourPackage
from app.auth.dependencies import get_current_user
from typing import Optional
from datetime import datetime
from sqlalchemy import extract, func
from fastapi import Depends
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

# Templates directory
templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/company/dashboard", tags=["Dashboard"])

# =================================================
# MAIN DASHBOARD PAGE
# =================================================
@router.get("/", response_class=HTMLResponse, name="dashboard_index")
def dashboard_index(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Renders main dashboard page.
    """
    return templates.TemplateResponse(
        "company_dashboard/index.html",
        {"request": request, "current_user": current_user}
    )

# =================================================
# CUSTOMER DATATABLE API
# =================================================
@router.get("/customers/datatable", name="dashboard_customers_datatable")
def customers_datatable(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    bookings = (
        db.query(ManualBooking)
        .filter(ManualBooking.is_deleted == False)
        .all()
    )

    data = [
        {
            "name": b.guest_name,
            "contact": f"{b.country_code}{b.phone} <br> {b.email}",
        }
        for b in bookings
    ]

    return {"data": data}

@router.get("/datatable/active-packages", name="dashboard_active_packages")
def active_packages_datatable(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = current_user.company

    packages = (
        db.query(TourPackage)
        .filter(
            TourPackage.company_id == company.id,
            TourPackage.status == "active",
            TourPackage.is_deleted == False
        )
        .all()
    )

    data = [
        {
            "name": f"{p.title} - {p.country}, {p.city}",
            "price": f"{p.price} {p.currency}",
        }
        for p in packages
    ]

    return {"data": data}
# =================================================
# KPI SUMMARY
# =================================================
@router.get("/summary", name="dashboard_summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns dashboard KPI summary (bookings, revenue, pending payments)
    """
    total_bookings = db.query(ManualBooking).filter(ManualBooking.is_deleted == False).count()

    pending_payments = db.query(ManualBooking).filter(
        ManualBooking.is_deleted == False,
        ManualBooking.payment_status != "paid"
    ).count()

    total_revenue = db.query(
        func.coalesce(func.sum(ManualBooking.total_amount), 0)
    ).filter(ManualBooking.is_deleted == False).scalar()

    return JSONResponse({
        "total_bookings": total_bookings,
        "pending_payments": pending_payments,
        "total_revenue": float(total_revenue)
    })

@router.get("/dashboard-stats", name="dashboard_stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    company = current_user.company if current_user else None
    currency = company.currency if company else "USD"

    # Monthly bookings array for chart
    monthly_bookings = []
    for month in range(1, 13):
        count = (
            db.query(func.count(ManualBooking.id))
            .filter(
                ManualBooking.is_deleted == False,
                extract("year", ManualBooking.created_at) == current_year,
                extract("month", ManualBooking.created_at) == month
            )
            .scalar()
        )
        monthly_bookings.append(count)

    # Yearly and current month bookings
    yearly_bookings = sum(monthly_bookings)
    monthly_bookings_current = monthly_bookings[current_month - 1]

    # Yearly revenue (paid only)
    yearly_revenue = (
        db.query(func.coalesce(func.sum(ManualBooking.total_amount), 0))
        .filter(
            ManualBooking.is_deleted == False,
            ManualBooking.payment_status == "paid",
            extract("year", ManualBooking.created_at) == current_year
        )
        .scalar()
    )

    # Monthly revenue (paid only)
    monthly_revenue = (
        db.query(func.coalesce(func.sum(ManualBooking.total_amount), 0))
        .filter(
            ManualBooking.is_deleted == False,
            ManualBooking.payment_status == "paid",
            extract("year", ManualBooking.created_at) == current_year,
            extract("month", ManualBooking.created_at) == current_month
        )
        .scalar()
    )

    return JSONResponse({
        "year": current_year,
        "month": current_month,
        "currency": currency,
        "yearly_bookings": yearly_bookings,
        "monthly_bookings": monthly_bookings_current,
        "monthly_bookings_per_year": monthly_bookings,
        "yearly_revenue": float(yearly_revenue),
        "monthly_revenue": float(monthly_revenue),
    })
