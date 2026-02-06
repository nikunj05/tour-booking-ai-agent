from sqlalchemy import distinct
from app.models.manual_booking import ManualBooking,BookingVehicle
from app.models.driver import Driver
from app.models.tour_package import TourPackage,TourPackageDriver
from app.models.customer import Customer
from decimal import Decimal
from itertools import combinations

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

def build_vehicle_combinations(drivers, total_pax, max_combo=2):
    options = []

    # 1️⃣ single vehicle options
    for d in drivers:
        if d["seats"] >= total_pax:
            options.append({
                "vehicles": [d],
                "total_seats": d["seats"]
            })

    # 2️⃣ combo vehicle options (2 vehicles)
    for combo in combinations(drivers, max_combo):
        seats = sum(v["seats"] for v in combo)
        if seats >= total_pax:
            options.append({
                "vehicles": list(combo),
                "total_seats": seats
            })

    # sort: single first, closest fit
    options.sort(key=lambda x: (len(x["vehicles"]), x["total_seats"]))

    return options[:5]  # limit list

def get_available_drivers(db, company_id, package_id, travel_date):
    booked_driver_ids = (
        db.query(BookingVehicle.driver_id)
        .join(ManualBooking, ManualBooking.id == BookingVehicle.booking_id)
        .filter(
            ManualBooking.travel_date == travel_date,
            ManualBooking.is_deleted == False
        )
        .distinct()
        .all()
    )

    booked_driver_ids = [d[0] for d in booked_driver_ids]

    drivers = (
        db.query(Driver)
        .filter(
            Driver.company_id == company_id,
            Driver.is_deleted == False,
            ~Driver.id.in_(booked_driver_ids),
            Driver.seats > 0
        )
        .all()
    )

    return [
        {
            "id": d.id,
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
                "driver_id": v["id"],
                "seats": v["seats"]
            })
        else:
            normalized.append({
                "driver_id": v,
                "seats": 0
            })

    driver_ids = [v["driver_id"] for v in normalized]

    # ✅ Availability check
    if driver_ids:
        conflict = (
            db.query(BookingVehicle)
            .join(ManualBooking)
            .filter(
                BookingVehicle.driver_id.in_(driver_ids),
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
            BookingVehicle(
                booking_id=booking.id,
                driver_id=v["driver_id"],
                seats=v["seats"]
            )
        )

    db.commit()
    return booking
