from app.models.manual_booking import ManualBooking,BookingVehicleDriver
from app.models.driver import Driver
from app.models.vehicle import Vehicle
from app.models.customer import Customer
from decimal import Decimal

def to_decimal(value):
    return Decimal(str(value or 0))

def create_booking(
    *,
    db,
    company,
    guest_name,
    country_code,
    phone,
    email=None,
    adults=1,
    kids=0,
    pickup_location=None,
    tour_package_id,
    vehicles=None,  
    travel_date,
    travel_time=None,
    total_amount,
    advance_amount=0,
    remaining_amount=0,
    transport_type=None,
):
    phone = phone.strip()
    country_code = country_code.strip()

    # ✅ Find or create customer
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
        customer.guest_name = guest_name
        customer.email = email

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

    normalized = []
    for v in vehicles or []:
        if isinstance(v, dict):
            normalized.append({
                "vehicle_id": v["id"],
                "seats": v["seats"]
            })
        else:
            normalized.append({
                "vehicle_id": v,
                "seats": 0
            })

    vehicle_ids = [v["vehicle_id"] for v in normalized]

    # ✅ Availability check
    if vehicle_ids:
        conflict = (
            db.query(BookingVehicleDriver)
            .join(ManualBooking)
            .filter(
                BookingVehicleDriver.vehicle_id.in_(vehicle_ids),
                ManualBooking.travel_date == travel_date,
                ManualBooking.is_deleted == False
            )
            .first()
        )
        if conflict:
            raise ValueError("One or more selected vehicles are already booked for this date.")

    # ✅ Amount calculation
    total = to_decimal(total_amount)
    advance = to_decimal(advance_amount)
    remaining = total - advance

    # ✅ Create booking
    booking = ManualBooking(
        customer_id=customer.id,
        adults=adults,
        kids=kids,
        pickup_location=pickup_location,
        tour_package_id=tour_package_id,
        travel_date=travel_date,
        travel_time=travel_time,
        total_amount=total,
        advance_amount=advance,
        remaining_amount=remaining,
        transport_type=transport_type,
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    # ✅ Attach vehicles
    for v in normalized:
        db.add(
            BookingVehicleDriver(
                booking_id=booking.id,
                vehicle_id=v["vehicle_id"],
                seats=v["seats"]
            )
        )

    db.commit()
    return booking
