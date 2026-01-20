from urllib import request
from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from app.database.session import get_db
from app.models.manual_booking import ManualBooking
from app.models.tour_package import TourPackage
from app.schemas.manual_booking import ManualBookingCreate
from app.core.templates import templates
from app.auth.dependencies import admin_only, company_only
from app.utils.flash import flash_redirect
from fastapi import Form
from typing import Optional


router = APIRouter(prefix="/manual-bookings", tags=["Manual Booking"])

# -------------------------------
# Route WITHOUT package_id
# -------------------------------
@router.post(
    "/manual-bookings/create",
    name="autofill_booking_create_page"
)
@router.get(
    "/manual-bookings/create",
    name="manual_booking_create_page"
)
def manual_booking_create_page(
    request: Request,
    package_id: Optional[int] = Form(None),
    travel_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(company_only),
):
    company = current_user.company

    print(package_id)
    print(travel_date)

    # Get all packages for dropdown
    packages = (
        db.query(TourPackage)
        .filter(
            TourPackage.company_id == company.id,
            TourPackage.is_deleted == False
        )
        .all()
    )

    # Pre-select package if package_id exists
    selected_package = None
    if package_id:
        selected_package = (
            db.query(TourPackage)
            .filter(
                TourPackage.id == package_id,
                TourPackage.company_id == company.id
            )
            .first()
        )

    return templates.TemplateResponse(
        "manual_booking/form.html",
        {
            "request": request,
            "packages": packages,
            "company": company,
            "selected_package": selected_package,
            "travel_date": travel_date,
            "is_edit": False,
        }
    )


@router.post("/create", name="manual_booking_create")
def create_manual_booking(
    request: Request,
    guest_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(None),
    pickup_location: str = Form(None),
    tour_package_id: int = Form(...),
    travel_date: str = Form(...),
    travel_time: str = Form(None),
    total_amount: float = Form(...),
    advance_amount: float = Form(0),
    db: Session = Depends(get_db),
    current_user=Depends(admin_only),
):
    remaining_amount = total_amount - advance_amount

    payment_status = (
        "paid" if remaining_amount == 0
        else "partial" if advance_amount > 0
        else "pending"
    )

    booking = ManualBooking(
        guest_name=guest_name,
        phone=phone,
        email=email,
        pickup_location=pickup_location,
        tour_package_id=tour_package_id,
        travel_date=travel_date,
        travel_time=travel_time,
        total_amount=total_amount,
        advance_amount=advance_amount,
        remaining_amount=remaining_amount,
        payment_status=payment_status,
    )

    db.add(booking)
    db.commit()

    return flash_redirect(
        url=request.url_for("manual_booking_list"),
        message="booking created successfully.",
    )


# =================================================
# DATATABLE API
# =================================================
@router.get("/datatable", name="manual_booking_datatable")
def manual_booking_datatable(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(company_only),
):
    bookings = (
        db.query(ManualBooking)
        .filter(ManualBooking.is_deleted == False)
        .order_by(ManualBooking.id.desc())
        .all()
    )
    
    company = current_user.company

    edit_icon = "/static/assets/icon/edit.svg"
    trash_icon = "/static/assets/icon/trash.svg"

    data = []
    for booking in bookings:
        data.append({
            "id": booking.id,
           "guest_details": f"""
                <strong>{booking.guest_name}</strong><br>
                📞 {booking.phone}<br>
                ✉️ {booking.email or "-"}
            """,

            "travel_details": f"""
                <strong>{booking.tour_package.title}</strong><br>
                📅 {booking.travel_date.strftime("%d-%m-%Y")}<br>
                ⏰ {booking.travel_time or "-"}<br>
                📍 {booking.pickup_location or "-"}
            """,

            "payment_details": f"""
                <strong>{company.currency} {booking.total_amount}</strong><br>
                Advance: {company.currency} {booking.advance_amount}<br>
                Remaining: {company.currency} {booking.remaining_amount}<br>
            """,
            
            "status": "Paid" if booking.remaining_amount == 0 else "Pending",
            "actions": f"""
                <a href="{request.url_for('manual_booking_edit', booking_id=booking.id)}"
                   class="btn btn-sm btn-edit"
                   title="Edit Booking">
                    <img src="{edit_icon}" class="table-icon">
                </a>

                <a href="javascript:void(0)"
                   class="confirm-manual-booking-delete btn btn-sm btn-delete"
                   data-route="{request.url_for('manual_booking_delete', booking_id=booking.id)}"
                   title="Delete Booking">
                    <img src="{trash_icon}" class="table-icon">
                </a>
            """
        })

    return JSONResponse({"data": data})

@router.get("/", response_class=HTMLResponse, name="manual_booking_list")
def manual_booking_list(
    request: Request,
    _=Depends(admin_only)
):
    return templates.TemplateResponse(
        "manual_booking/list.html",
        {"request": request}
    )


@router.get("/{booking_id}/edit", name="manual_booking_edit")
def edit_manual_booking(
    booking_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(company_only),
):
    booking = db.query(ManualBooking).get(booking_id)
    company = current_user.company
    packages = db.query(TourPackage).filter(TourPackage.is_deleted == False).all()

    return templates.TemplateResponse(
        "manual_booking/form.html",
        {
            "request": request,
            "booking": booking,
            "packages": packages,
            "company": company
        }
    )

@router.post("/{booking_id}/update", name="manual_booking_update")
def update_manual_booking(
    request: Request,
    booking_id: int,
    guest_name: str = Form(...),
    tour_package_id: int = Form(...),
    phone: str = Form(...),
    email: str = Form(None),
    pickup_location: str = Form(None),
    travel_date: str = Form(...),
    travel_time: str = Form(None),
    total_amount: float = Form(...),
    advance_amount: float = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(admin_only),
):
    
    booking = db.query(ManualBooking).get(booking_id)

    conflict = (
        db.query(ManualBooking)
        .filter(
            ManualBooking.id != booking.id, 
            ManualBooking.tour_package_id == booking.tour_package_id,
            ManualBooking.travel_date == travel_date
        )
        .first()
    )

    if conflict:
        return flash_redirect(
            url=request.url_for(
                "manual_booking_edit",
                booking_id=booking.id
            ),
            message="This package is already booked for the selected date.",
            category="error",
        )
        
        
    booking = db.query(ManualBooking).get(booking_id)

    booking.guest_name = guest_name
    booking.phone = phone
    booking.email = email
    booking.tour_package_id = tour_package_id
    booking.pickup_location = pickup_location
    booking.travel_date = travel_date
    booking.travel_time = travel_time
    booking.total_amount = total_amount
    booking.advance_amount = advance_amount
    booking.remaining_amount = total_amount - advance_amount

    booking.payment_status = (
        "paid" if booking.remaining_amount == 0
        else "partial" if advance_amount > 0
        else "pending"
    )

    db.commit()

    return flash_redirect(
        url=request.url_for("manual_booking_list"),
        message="booking updated successfully.",
    )

@router.post("/{booking_id}/delete", name="manual_booking_delete")
def delete_manual_booking(
    request: Request,
    booking_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(admin_only),
):
    booking = db.query(ManualBooking).get(booking_id)
    db.delete(booking)
    db.commit()

    return {"success": True}


# @router.get("/booked-dates/{package_id}", name="get_booked_dates")
# def get_booked_dates(package_id: int, db: Session = Depends(get_db)):
#     bookings = db.query(ManualBooking).filter(
#         ManualBooking.tour_package_id == package_id,
#         ManualBooking.is_deleted == False
#     ).all()


#     booked_dates = [b.travel_date.strftime("%Y-%m-%d") for b in bookings] if bookings else []
#     return {"booked_dates": booked_dates}


@router.get(
    "/tour-packages/{package_id}/availability",
    name="tour_package_availability_page"
)
def tour_package_availability_page(
    request: Request,
    package_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(company_only),
):
    package = db.query(TourPackage).filter(
        TourPackage.id == package_id,
        TourPackage.is_deleted == False
    ).first()

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    return templates.TemplateResponse(
        "tour_packages/availability.html",
        {
            "request": request,
            "package": package,
            "company": current_user.company
        }
    )


# @router.get("/booked-dates/{package_id}", name="get_booked_dates")
# def booked_dates(package_id: int, db: Session = Depends(get_db)):
#     bookings = (
#         db.query(ManualBooking)
#         .filter(
#             ManualBooking.tour_package_id == package_id
#         )
#         .all()
#     )

#     data = []
#     for b in bookings:
#         data.append({
#             "guest_name": b.guest_name,
#             "pickup_location": b.pickup_location or "-",
#             "travel_date": b.travel_date.strftime("%Y-%m-%d")
#         })

#     return {"bookings": data}


@router.get("/booked-dates/{package_id}", name="get_booked_dates")
def get_booked_dates(package_id: int, db: Session = Depends(get_db)):
    bookings = (
        db.query(ManualBooking)
        .filter(
            ManualBooking.tour_package_id == package_id,
            ManualBooking.is_deleted == False
        )
        .all()
    )

    bookings_data = []
    booked_dates = []

    for b in bookings:
        date_str = b.travel_date.strftime("%Y-%m-%d")

        booked_dates.append(date_str)

        bookings_data.append({
            "guest_name": b.guest_name,
            "pickup_location": b.pickup_location or "",
            "travel_date": date_str,
            "travel_time": b.travel_time or "",
            
        })

    return {
        "booked_dates": booked_dates,
        "bookings": bookings_data
    }
