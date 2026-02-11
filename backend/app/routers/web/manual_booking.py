from urllib import request
from fastapi import APIRouter, Depends,Query, Request, Form
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from app.database.session import get_db
from app.models.manual_booking import ManualBooking,BookingVehicleDriver
from app.models.tour_package import TourPackage,TourPackageDriver
from app.models.driver import Driver
from app.models.vehicle import Vehicle
from app.models.customer import Customer
from app.schemas.manual_booking import ManualBookingCreate
from app.core.templates import templates
from app.auth.dependencies import admin_only, company_only
from app.utils.flash import flash_redirect
from typing import Optional, List
from sqlalchemy import func,and_,or_, cast, String
from datetime import date
from twilio.rest import Client
from app.core.constants import COUNTRY_CODES
from app.services.whatsapp_service import send_whatsapp_booking_confirmation, format_phone, send_whatsapp_driver_details, send_whatsapp_text
from fastapi import Form
from typing import List
from datetime import datetime

router = APIRouter(prefix="/manual-bookings", tags=["Manual Booking"])

# -------------------------------
# Route WITHOUT package_id
# -------------------------------
@router.post(
    "/package/create",
    name="autofill_booking_create_page"
)
@router.get(
    "/create",
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

    packages = (
        db.query(TourPackage)
        .filter(
            TourPackage.company_id == company.id,
            TourPackage.is_deleted == False,
            TourPackage.status == "active"
        )
        .all()
    )

    drivers = (
        db.query(Driver)
        .filter(
            Driver.company_id == company.id,
            Driver.is_deleted == False
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
            "country_codes": COUNTRY_CODES,
            "selected_package": selected_package,
            "travel_date": travel_date,
            "is_edit": False,
        }
    )

@router.get("/customers/search", name="customer_search")
def customer_search(
    q: str = Query(None, min_length=1),
    db: Session = Depends(get_db)
):
    if not q:
        return {"results": []}

    customers = (
        db.query(Customer)
        .filter(
            or_(
                Customer.guest_name.ilike(f"%{q}%"),
                cast(Customer.phone, String).ilike(f"%{q}%"),
                Customer.email.ilike(f"%{q}%")
            )
        )
        .limit(10)
        .all()
    )

    results = [
        {
            "id": c.id,
            "text": f"{c.guest_name} ({c.country_code}{c.phone})",
            "guest_name": c.guest_name,
            "email": c.email,
            "phone": c.phone,
            "country_code": c.country_code
        }
        for c in customers
    ]

    return {"results": results}

@router.post("/create", name="manual_booking_create")
def create_manual_booking(
    request: Request,
    guest_name: str = Form(...),
    country_code: str = Form(...),
    phone: str = Form(...),
    email: str = Form(None),
    adults: int = Form(...),
    kids: int = Form(...),
    pickup_location: str = Form(None),
    tour_package_id: int = Form(...),
    driver_ids: List[str] = Form(default=[], alias="driver_ids[]"),
    vehicle_ids: List[str] = Form(default=[], alias="vehicle_ids[]"),
    travel_date: str = Form(...),
    travel_time: str = Form(None),
    total_amount: float = Form(...),
    advance_amount: float = Form(0),
    db: Session = Depends(get_db),
    current_user=Depends(company_only),
):
    print("driver_ids", driver_ids)
    print("vehicle_ids", vehicle_ids)
    company = current_user.company

    # Strip inputs
    guest_name = guest_name.strip()
    phone = phone.strip()
    country_code = country_code.strip()

    # Convert travel_date to date object
    try:
        travel_date_obj = datetime.strptime(travel_date, "%Y-%m-%d").date()
    except ValueError:
        return flash_redirect(
            url=request.url_for("manual_booking_create"),
            message="Invalid travel date format.",
            category="error"
        )

    # Check existing customer
    customer = (
        db.query(Customer)
        .filter(
            Customer.company_id == company.id,
            Customer.phone == phone,
            Customer.country_code == country_code,
            Customer.is_deleted == False
        )
        .first()
    )

    if customer:
        print("Existing customer:", customer.id)
    else:
        customer = Customer(
            company_id=company.id,
            guest_name=guest_name,
            country_code=country_code,
            phone=phone,
            email=email,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

    # ----------------- DRIVER/VEHICLE CONFLICT CHECK -----------------
    # Only check if both driver_ids or vehicle_ids exist
    driver_ids = [int(i) for i in driver_ids if i.strip()] if driver_ids else []
    vehicle_ids = [int(i) for i in vehicle_ids if i.strip()] if vehicle_ids else []
    if driver_ids or vehicle_ids:
        conflicts = (
            db.query(BookingVehicleDriver)
            .join(ManualBooking)
            .filter(
                ManualBooking.travel_date == travel_date_obj,
                ManualBooking.is_deleted == False,
                # check if any of these drivers or vehicles are already assigned
                ((BookingVehicleDriver.driver_id.in_(driver_ids)) if driver_ids else False) |
                ((BookingVehicleDriver.vehicle_id.in_(vehicle_ids)) if vehicle_ids else False)
            )
            .all()
        )

        if conflicts:
            return flash_redirect(
                url=request.url_for("manual_booking_create"),
                message="One or more selected drivers or vehicles are already booked for this date.",
                category="error",
            )

    # ----------------- CREATE BOOKING -----------------
    remaining_amount = total_amount - advance_amount
    payment_status = (
        "paid" if remaining_amount == 0
        else "partial" if advance_amount > 0
        else "pending"
    )

    booking = ManualBooking(
        customer_id=customer.id,
        adults=adults,
        kids=kids,
        pickup_location=pickup_location,
        tour_package_id=tour_package_id,
        travel_date=travel_date_obj,
        travel_time=travel_time,
        total_amount=total_amount,
        advance_amount=advance_amount,
        remaining_amount=remaining_amount,
        payment_status=payment_status,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # ----------------- SAVE VEHICLE + DRIVER COMBINATIONS -----------------
    for i in range(max(len(vehicle_ids), len(driver_ids))):
        vehicle_id = vehicle_ids[i] if i < len(vehicle_ids) else None
        driver_id = driver_ids[i] if i < len(driver_ids) else None

        booking_vd = BookingVehicleDriver(
            booking_id=booking.id,
            vehicle_id=vehicle_id,
            driver_id=driver_id,
        )
        db.add(booking_vd)

    db.commit()

    # ✅ WhatsApp notification
    try:
        phone_number = format_phone(country_code, phone)
        send_whatsapp_booking_confirmation(phone_number, booking)
        # send_whatsapp_driver_details(phone_number, booking)
        itinerary_text = (
            "📍 Tour Itinerary:\n\n"
            + html_to_whatsapp_text(booking.tour_package.itinerary)
        )

        send_whatsapp_text(phone_number, itinerary_text)

    except Exception as e:
        print("WhatsApp send failed", e)
        print(f"WhatsApp send failed for booking {booking.id}")

    return flash_redirect(
        url=request.url_for("manual_booking_list"),
        message="Booking created successfully.",
    )

import re
from html import unescape

def html_to_whatsapp_text(html: str) -> str:
    if not html:
        return "-"

    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"<li>", "• ", text)
    text = re.sub(r"</li>", "\n", text)
    text = re.sub(r"<.*?>", "", text)

    return unescape(text).strip()

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
        .filter(
            ManualBooking.is_deleted == False,
            ManualBooking.tour_package.has(
                TourPackage.company_id == current_user.id
            )
        )
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
                <strong>{booking.customer.guest_name}</strong><br>
                <i class="fas fa-phone-alt text-dark"></i> {booking.customer.country_code}{booking.customer.phone}<br>
                <i class="fas fa-envelope text-dark"></i> {booking.customer.email or "-"}<br>
                <i class="fas fa-users text-dark"></i> {booking.adults} - {booking.kids}
            """,

            "travel_details": f"""
                <strong>{booking.tour_package.title}</strong><br>
                <i class="fas fa-calendar-alt text-dark"></i> {booking.travel_date.strftime("%d-%m-%Y")}<br>
                <i class="far fa-clock text-dark"></i> {booking.travel_time.strftime("%I:%M %p") or "-"}<br>
                <i class="fas fa-map-marker-alt text-dark"></i> {booking.pickup_location or "-"}
            """,

            "payment_details": f"""
                <strong>{booking.tour_package.currency} {booking.total_amount}</strong><br>
                Advance: {booking.tour_package.currency} {booking.advance_amount}<br>
                Remaining: {booking.tour_package.currency} {booking.remaining_amount}<br>
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

@router.get("", response_class=HTMLResponse, name="manual_booking_list")
def manual_booking_list(
    request: Request,
    _=Depends(company_only)
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

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    packages = (
        db.query(TourPackage)
        .filter(
            TourPackage.is_deleted == False,
            TourPackage.status == "active"
        )
        .all()
    )

    # 🔹 Drivers already booked on same date (EXCEPT this booking)
    # booked_driver_ids = (
    #     db.query(BookingVehicleDriver.driver_id)
    #     .join(ManualBooking)
    #     .filter(
    #         ManualBooking.travel_date == booking.travel_date,
    #         ManualBooking.id != booking.id,
    #         ManualBooking.is_deleted == False
    #     )
    #     .all()
    # )
    # booked_driver_ids = [d[0] for d in booked_driver_ids]

    # # ✅ Drivers already assigned to THIS booking (important)
    # current_driver_ids = [
    #     bv.driver_id for bv in booking.vehicles_drivers
    # ]

    # # 🔹 Drivers assigned to selected package
    # query = (
    #     db.query(Driver)
    #     .join(TourPackageDriver, TourPackageDriver.driver_id == Driver.id)
    #     .filter(
    #         TourPackageDriver.tour_package_id == booking.tour_package_id,
    #         Driver.company_id == company.id,
    #         Driver.is_deleted == False,
    #     )
    # )

    # # 🔹 Exclude booked drivers, but KEEP current booking drivers
    # if booked_driver_ids:
    #     query = query.filter(
    #         or_(
    #             ~Driver.id.in_(booked_driver_ids),
    #             Driver.id.in_(current_driver_ids)
    #         )
    #     )

    # drivers = query.all()

    drivers = db.query(Driver).filter(
        Driver.company_id == company.id,
        Driver.is_deleted == False,
        Driver.is_active == True
    ).all()

    vihicals = db.query(Vehicle).filter(
        Vehicle.company_id == company.id,
        Vehicle.is_deleted == False,
        Vehicle.is_active == True
    ).all()

    return templates.TemplateResponse(
        "manual_booking/form.html",
        {
            "request": request,
            "booking": booking,
            "packages": packages,
            "country_codes": COUNTRY_CODES,
            "drivers": drivers,
            "vehicles":vihicals,
            "company": company,
        }
    )

@router.post("/{booking_id}/update", name="manual_booking_update")
def update_manual_booking(
    request: Request,
    booking_id: int,
    guest_name: str = Form(...),
    adults: int = Form(...),
    kids: int = Form(...),
    tour_package_id: int = Form(...),
    driver_ids: List[str] = Form(default=[], alias="driver_ids[]"),
    vehicle_ids: List[str] = Form(default=[], alias="vehicle_ids[]"),
    country_code: str = Form(...),
    phone: str = Form(...),
    email: str = Form(None),
    pickup_location: str = Form(None),
    travel_date: str = Form(...),
    travel_time: str = Form(None),
    total_amount: float = Form(...),
    advance_amount: float = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(company_only),
):

    # 1️⃣ Fetch the booking first
    booking = db.query(ManualBooking).get(booking_id)
    if not booking:
        return flash_redirect(
            url=request.url_for("manual_booking_list"),
            message="Booking not found.",
            category="error"
        )

    # 2️⃣ Update or create customer
    if booking.customer_id:
        customer = db.query(Customer).get(booking.customer_id)
        if customer:
            customer.guest_name = guest_name
            customer.country_code = country_code
            customer.phone = phone
            customer.email = email
        else:
            # Booking has customer_id but customer not found — create new
            customer = Customer(
                company_id=current_user.company.id,
                guest_name=guest_name,
                country_code=country_code,
                phone=phone,
                email=email
            )
            db.add(customer)
            db.flush()  # to get customer.id
            booking.customer_id = customer.id
    else:
        # No customer linked — create new
        customer = Customer(
            company_id=current_user.company.id,
            guest_name=guest_name,
            country_code=country_code,
            phone=phone,
            email=email
        )
        db.add(customer)
        db.flush()  # to get customer.id
        booking.customer_id = customer.id

    db.commit()
    db.refresh(customer)

    # 3️⃣ Check driver conflict
    driver_ids = [int(i) for i in driver_ids if i.strip()] if driver_ids else []
    vehicle_ids = [int(i) for i in vehicle_ids if i.strip()] if vehicle_ids else []
    print("driver_ids", driver_ids)
    print("vehicle_ids", vehicle_ids)
    if driver_ids:
        conflict = (
            db.query(BookingVehicleDriver.id)
            .join(ManualBooking)
            .filter(
                BookingVehicleDriver.driver_id.in_(driver_ids),
                ManualBooking.travel_date == travel_date,
                ManualBooking.is_deleted == False,
                ManualBooking.id != booking_id if booking_id else True
            )
            .first()
        )

        if conflict:
            return flash_redirect(
                url=request.url_for("manual_booking_edit", booking_id=booking_id),
                message="Selected driver already booked for this date.",
                category="error",
            )
    
    # 3️⃣ Check vehicle conflict
    if vehicle_ids:
        conflict = (
            db.query(BookingVehicleDriver.id)
            .join(ManualBooking)
            .filter(
                BookingVehicleDriver.vehicle_id.in_(vehicle_ids),
                ManualBooking.travel_date == travel_date,
                ManualBooking.is_deleted == False,
                ManualBooking.id != booking_id if booking_id else True
            )
            .first()
        )

    if conflict:
        return flash_redirect(
            url=request.url_for("manual_booking_edit", booking_id=booking_id),
            message="Selected vehicle already booked for this date.",
            category="error",
        )

    # 4️⃣ Update booking fields
    booking.adults = adults
    booking.kids = kids
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

    db.query(BookingVehicleDriver).filter(
        BookingVehicleDriver.booking_id == booking.id
    ).delete()

    for i in range(max(len(vehicle_ids), len(driver_ids))):
        vehicle_id = vehicle_ids[i] if i < len(vehicle_ids) else None
        driver_id = driver_ids[i] if i < len(driver_ids) else None

        booking_vd = BookingVehicleDriver(
            booking_id=booking.id,
            vehicle_id=vehicle_id,
            driver_id=driver_id,
        )
        db.add(booking_vd)

    db.commit()
    return flash_redirect(
        url=request.url_for("manual_booking_list"),
        message="Booking updated successfully.",
    )


@router.post("/{booking_id}/delete", name="manual_booking_delete")
def delete_manual_booking(
    request: Request,
    booking_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(company_only),
):
    booking = db.query(ManualBooking).get(booking_id)
    db.delete(booking)
    db.commit()

    return {"success": True}

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

    # 🔹 Fetch drivers with details
    drivers = (
        db.query(TourPackageDriver)
        .filter(
            TourPackageDriver.tour_package_id == package.id
        )
        .all()
    )

    driver_data = []
    for d in drivers:
        driver = d.driver   # relation

        driver_data.append({
            "name": driver.name,
            "country_code": driver.country_code,
            "phone_number": driver.phone_number,
        })

    return templates.TemplateResponse(
        "tour_packages/availability.html",
        {
            "request": request,
            "package": package,
            "company": current_user.company,
            "drivers": driver_data,
            "total_drivers": len(driver_data)
        }
    )

@router.get("/booked-dates/{package_id}", name="get_booked_dates")
def get_booked_dates(
    package_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(company_only)
):
    company_id = current_user.company.id

    # ---------------- Drivers assigned to this package ----------------
    # package_driver_ids = (
    #     db.query(TourPackageDriver.driver_id)
    #     .filter(TourPackageDriver.tour_package_id == package_id)
    #     .all()
    # )
    # package_driver_ids = [d[0] for d in package_driver_ids]
    # total_drivers = len(package_driver_ids)
    driver_ids = (
        db.query(Driver.id)
        .filter(
            Driver.company_id == company_id,
            Driver.is_active == True,
            Driver.is_deleted == False
        )
        .all()
    )
    driver_ids = [d[0] for d in driver_ids]
    total_drivers = len(driver_ids)

    # ---------------- Vehicles available (all active for company) ----------------
    vehicle_ids = (
        db.query(Vehicle.id)
        .filter(
            Vehicle.company_id == company_id,
            Vehicle.is_active == True,
            Vehicle.is_deleted == False
        )
        .all()
    )
    vehicle_ids = [v[0] for v in vehicle_ids]
    total_vehicles = len(vehicle_ids)

    # ---------------- All bookings for this package ----------------
    bookings = (
        db.query(ManualBooking)
        .filter(
            ManualBooking.tour_package_id == package_id,
            ManualBooking.is_deleted == False
        )
        .all()
    )

    print("bookings", bookings)

    bookings_data = []
    for b in bookings:
        bookings_data.append({
            "id": b.id,
            "guest_name": b.customer.guest_name if b.customer else "",
            "pickup_location": b.pickup_location or "",
            "travel_date": b.travel_date.strftime("%Y-%m-%d"),
            "travel_time": b.travel_time or "",
        })

    # ---------------- Count used drivers per date ----------------
    driver_usage = (
        db.query(
            ManualBooking.travel_date,
            func.count(func.distinct(BookingVehicleDriver.driver_id)).label("used")
        )
        .join(BookingVehicleDriver, BookingVehicleDriver.booking_id == ManualBooking.id)
        .filter(
            ManualBooking.is_deleted == False,
            BookingVehicleDriver.driver_id.in_(driver_ids)
        )
        .group_by(ManualBooking.travel_date)
        .all()
    )

    driver_usage_dict = {d.travel_date: d.used for d in driver_usage}

    # ---------------- Count used vehicles per date ----------------
    vehicle_usage = (
        db.query(
            ManualBooking.travel_date,
            func.count(func.distinct(BookingVehicleDriver.vehicle_id)).label("used")
        )
        .join(BookingVehicleDriver, BookingVehicleDriver.booking_id == ManualBooking.id)
        .filter(
            ManualBooking.is_deleted == False,
            BookingVehicleDriver.vehicle_id.in_(vehicle_ids)
        )
        .group_by(ManualBooking.travel_date)
        .all()
    )

    vehicle_usage_dict = {v.travel_date: v.used for v in vehicle_usage}

    # ---------------- Calculate availability per date ----------------
    booked_dates = []
    availability = {}

    all_dates = set(list(driver_usage_dict.keys()) + list(vehicle_usage_dict.keys()))
    for travel_date in all_dates:
        used_drivers = driver_usage_dict.get(travel_date, 0)
        used_vehicles = vehicle_usage_dict.get(travel_date, 0)

        remaining_drivers = max(total_drivers - used_drivers, 0)
        remaining_vehicles = max(total_vehicles - used_vehicles, 0)

        availability[str(travel_date)] = {
            "drivers": remaining_drivers,
            "vehicles": remaining_vehicles
        }

        # Disable date if no driver OR no vehicle left
        if remaining_drivers == 0 or remaining_vehicles == 0:
            booked_dates.append(str(travel_date))

    return {
        "booked_dates": booked_dates,        # disable dates in calendar
        "bookings": bookings_data,           # popup/list info
        "availability": availability,        # remaining drivers & vehicles
        "total_drivers": total_drivers,
        "total_vehicles": total_vehicles
    }

@router.get("/availability/{package_id}/{travel_date}")
def get_available_drivers(
    package_id: int,
    travel_date: date,
    booking_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(company_only),
):
    company_id = current_user.company.id

    # ---------------- Current booking driver & vehicle IDs (EDIT mode) ----------------
    current_driver_ids = []
    current_vehicle_ids = []

    if booking_id:
        current_items = (
            db.query(BookingVehicleDriver)
            .filter(BookingVehicleDriver.booking_id == booking_id)
            .all()
        )

        current_driver_ids = [item.driver_id for item in current_items if item.driver_id]
        current_vehicle_ids = [item.vehicle_id for item in current_items if item.vehicle_id]

    # ---------------- Drivers booked on same date ----------------
    booked_driver_ids = (
        db.query(BookingVehicleDriver.driver_id)
        .join(ManualBooking, ManualBooking.id == BookingVehicleDriver.booking_id)
        .filter(
            ManualBooking.travel_date == travel_date,
            ManualBooking.is_deleted == False,
            ManualBooking.id != booking_id if booking_id else True
        )
        .all()
    )
    booked_driver_ids = [d[0] for d in booked_driver_ids]

    # ---------------- Vehicles booked on same date ----------------
    booked_vehicle_ids = (
        db.query(BookingVehicleDriver.vehicle_id)
        .join(ManualBooking, ManualBooking.id == BookingVehicleDriver.booking_id)
        .filter(
            ManualBooking.travel_date == travel_date,
            ManualBooking.is_deleted == False,
            ManualBooking.id != booking_id if booking_id else True
        )
        .all()
    )
    booked_vehicle_ids = [v[0] for v in booked_vehicle_ids]

    # ---------------- Available drivers ----------------
    drivers = (
        db.query(Driver)
        .filter(
            Driver.company_id == company_id,
            Driver.is_deleted == False,
            Driver.is_active == True,
            or_(
                ~Driver.id.in_(booked_driver_ids),
                Driver.id.in_(current_driver_ids)  # allow current booking drivers
            )
        )
        .all()
    )

    # ---------------- Available vehicles ----------------
    vehicles = (
        db.query(Vehicle)
        .filter(
            Vehicle.company_id == company_id,
            Vehicle.is_deleted == False,
            Vehicle.is_active == True,
            or_(
                ~Vehicle.id.in_(booked_vehicle_ids),
                Vehicle.id.in_(current_vehicle_ids)  # allow current booking vehicles
            )
        )
        .all()
    )

    return {
        "drivers": [
            {
                "id": d.id,
                "name": d.name,
                "country_code": d.country_code,
                "phone_number": d.phone_number,
            }
            for d in drivers
        ],
        "vehicles": [
            {
                "id": v.id,
                "name": v.name,
                "vehicle_type": v.vehicle_type,
                "vehicle_number": v.vehicle_number,
                "seats": v.seats
            }
            for v in vehicles
        ]
    }



@router.get("/all-drivers/{package_id}/{travel_date}")
def get_all_package_drivers(
    package_id: int,
    travel_date: date,
    db: Session = Depends(get_db),
    current_user=Depends(company_only),
):
    company_id = current_user.company.id

    # 1️⃣ Drivers already booked on this date
    booked_driver_ids = (
        db.query(BookingVehicle.driver_id)
        .join(ManualBooking, ManualBooking.id == BookingVehicle.booking_id)
        .filter(
            ManualBooking.travel_date == travel_date,
            ManualBooking.is_deleted == False
        )
        .all()
    )
    booked_driver_ids = [d[0] for d in booked_driver_ids]

    # 2️⃣ All available drivers of company
    drivers = (
        db.query(Driver)
        .outerjoin(
            TourPackageDriver,
            TourPackageDriver.driver_id == Driver.id
        )
        .filter(
            Driver.company_id == company_id,
            Driver.is_deleted == False,
            ~Driver.id.in_(booked_driver_ids)
        )
        .distinct()
        .all()
    )

    return [
        {
            "id": d.id,
            "name": d.name,
            "country_code": d.country_code,
            "phone": d.phone_number,
            "vehicle_type": d.vehicle_type,
            "vehicle_number": d.vehicle_number,
            "seats": d.seats
        }
        for d in drivers
    ]

@router.get("/{booking_id}", response_class=HTMLResponse, name="manual_booking_detail")
def booking_detail(
    booking_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    booking = db.query(ManualBooking).filter(
        ManualBooking.id == booking_id,
        ManualBooking.is_deleted == False
    ).first()

    if not booking:
        return RedirectResponse("/manual-bookings", status_code=303)

    return templates.TemplateResponse(
        "manual_booking/detail.html",
        {
            "request": request,
            "booking": booking,
        }
    )