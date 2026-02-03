from sqlalchemy import distinct
from app.models.manual_booking import ManualBooking
from app.models.driver import Driver
from app.models.tour_package import TourPackage,TourPackageDriver
from app.models.customer import Customer
from decimal import Decimal

def filter_packages(db, company_id: int, city: str):
    query = db.query(TourPackage).filter(
        TourPackage.company_id == company_id,
        TourPackage.status == "active",
        TourPackage.is_deleted == False
    )

    if city != "All":
        query = query.filter(TourPackage.city == city)

    return query.all()

def get_active_cities(db, company_id: int):
    cities = (
        db.query(distinct(TourPackage.city)).filter(
            TourPackage.status == "active",
            TourPackage.is_deleted == False,
            TourPackage.company_id == company_id
        )
        .all()
    )

    # Convert [('Dubai',), ('Abu Dhabi',)] → ['Dubai', 'Abu Dhabi']
    return [c[0] for c in cities if c[0]]

def get_available_drivers(db, company_id, package_id, travel_date, total_pax):
    # 1️⃣ already booked drivers
    booked_driver_ids = (
        db.query(ManualBooking.driver_id)
        .filter(
            ManualBooking.travel_date == travel_date,
            ManualBooking.driver_id.isnot(None),
            ManualBooking.is_deleted == False
        )
        .all()
    )
    booked_driver_ids = [d[0] for d in booked_driver_ids]

    print("booked_driver_ids",booked_driver_ids)

    # 2️⃣ available drivers with enough seats
    drivers = (
        db.query(Driver)
        .outerjoin(
            TourPackageDriver,
            TourPackageDriver.driver_id == Driver.id
        )
        .filter(
            Driver.company_id == company_id,
            Driver.is_deleted == False,
            ~Driver.id.in_(booked_driver_ids),
            Driver.seats >= total_pax
        )
        .distinct()
        .all()
    )

    print("drivers",drivers)

    return [
        {
            "id": d.id,
            "name": d.name,
            "vehicle_type": d.vehicle_type,
            "vehicle_number": d.vehicle_number,
            "seats": d.seats
        }
        for d in drivers
    ]

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
    driver_id=None,
    travel_date,
    travel_time=None,
    total_amount,
    advance_amount=0,
    remaining_amount=0
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

    if not customer:
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

    # ✅ Driver conflict check
    if driver_id:
        conflict = (
            db.query(ManualBooking)
            .filter(
                ManualBooking.driver_id == driver_id,
                ManualBooking.travel_date == travel_date,
                ManualBooking.is_deleted == False
            )
            .first()
        )
        if conflict:
            raise ValueError("Selected driver is already booked for this date.")

    # ✅ Amount calculations
    total = to_decimal(total_amount)
    advance = to_decimal(advance_amount)
    remaining = total - advance

    payment_status = (
        "paid" if remaining == 0
        else "partial" if advance > 0
        else "pending"
    )

    # ✅ Create booking
    booking = ManualBooking(
        customer_id=customer.id,
        adults=adults,
        kids=kids,
        pickup_location=pickup_location,
        tour_package_id=tour_package_id,
        driver_id=driver_id,
        travel_date=travel_date,
        travel_time=travel_time,
        total_amount=total,
        advance_amount=advance,
        remaining_amount=remaining,
        payment_status=payment_status,
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    return booking