# app/routers/revenue.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from collections import defaultdict

from app.database.session import get_db
from app.models.manual_booking import ManualBooking,BookingVehicleDriver
from app.models.tour_package import TourPackage
from app.models.vehicle import Vehicle
from app.auth.dependencies import company_only
from app.models.user import User
from datetime import datetime
from app.core.templates import templates

router = APIRouter(tags=["Revenue"])

@router.get("/revenue", response_class=HTMLResponse, name="revenue_matrix_page")
def revenue_matrix_page(
    request: Request,
    year: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(company_only),
):
    if not year:
        year = datetime.now().year

    # ===============================
    # Fetch Aggregated Data
    # ===============================
    results = (
        db.query(
            TourPackage.title.label("tour_name"),
            extract("month", ManualBooking.travel_date).label("month"),
            func.sum(ManualBooking.total_amount).label("revenue"),
            func.count(ManualBooking.id).label("bookings"),
        )
        .join(TourPackage, ManualBooking.tour_package_id == TourPackage.id)
        .filter(
            TourPackage.company_id == current_user.company.id,
            extract("year", ManualBooking.travel_date) == year,
        )
        .group_by(TourPackage.title, "month")
        .all()
    )

    # ===============================
    # Convert to Matrix Structure
    # ===============================
    revenue_data = defaultdict(lambda: {
        "months": {i: {"revenue": 0, "bookings": 0} for i in range(1, 13)},
        "total_revenue": 0,
        "total_bookings": 0,
    })

    for r in results:
        month = int(r.month)
        revenue = float(r.revenue or 0)
        bookings = r.bookings or 0

        revenue_data[r.tour_name]["months"][month] = {
            "revenue": revenue,
            "bookings": bookings,
        }

        revenue_data[r.tour_name]["total_revenue"] += revenue
        revenue_data[r.tour_name]["total_bookings"] += bookings

    # ===============================
    # Grand Totals
    # ===============================
    grand_total_revenue = sum(
        t["total_revenue"] for t in revenue_data.values()
    )

    grand_total_bookings = sum(
        t["total_bookings"] for t in revenue_data.values()
    )

    return templates.TemplateResponse(
        "revenue/matrix.html",
        {
            "company": current_user.company,
            "current_year": datetime.now().year,
            "request": request,
            "revenue_data": revenue_data,
            "year": year,
            "grand_total_revenue": grand_total_revenue,
            "grand_total_bookings": grand_total_bookings,
        },
    )


@router.get("/vehicle", name="vehicle_matrix")
def vehicle_matrix(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(company_only),
    year: int = datetime.now().year
):

    company_id = current_user.company.id

    # Get vehicles of this company
    vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.company_id == company_id, Vehicle.is_deleted == False)
        .all()
    )

    vehicle_data = {}
    grand_total_bookings = 0

    for vehicle in vehicles:

        vehicle_data[vehicle.name] = {
            "months": {m: 0 for m in range(1, 13)},
            "total_bookings": 0
        }

        results = (
            db.query(
                extract("month", ManualBooking.travel_date).label("month"),
                func.count(ManualBooking.id).label("total")
            )
            .join(BookingVehicleDriver, BookingVehicleDriver.booking_id == ManualBooking.id)
            .join(TourPackage, TourPackage.id == ManualBooking.tour_package_id)
            .filter(
                BookingVehicleDriver.vehicle_id == vehicle.id,   # ✅ FIXED
                extract("year", ManualBooking.travel_date) == year,
                TourPackage.company_id == company_id,
                ManualBooking.is_deleted == False
            )
            .group_by("month")
            .all()
        )

        for row in results:
            month = int(row.month)
            bookings = row.total

            vehicle_data[vehicle.name]["months"][month] = bookings
            vehicle_data[vehicle.name]["total_bookings"] += bookings
            grand_total_bookings += bookings

    current_year = datetime.now().year

    return templates.TemplateResponse(
        "revenue/vehicle_matrix.html",
        {
            "request": request,
            "vehicle_data": vehicle_data,
            "year": year,
            "current_year": current_year,
            "grand_total_bookings": grand_total_bookings,
        }
    )