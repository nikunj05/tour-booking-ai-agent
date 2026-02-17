from sqlalchemy import distinct
from app.models.manual_booking import ManualBooking,BookingVehicleDriver
from app.models.driver import Driver
from app.models.vehicle import Vehicle
from app.models.customer import Customer
from itertools import combinations
import math

def build_vehicle_combinations(drivers, total_pax, max_combo=2):
    options = []

    # Sort vehicles by seats ascending
    drivers = sorted(drivers, key=lambda x: x["seats"])

    # 1️⃣ Best single vehicle
    single_options = [
        d for d in drivers if d["seats"] >= total_pax
    ]

    best_single = None
    if single_options:
        best_single = min(single_options, key=lambda x: x["seats"])
        options.append({
            "vehicles": [best_single],
            "total_seats": best_single["seats"]
        })

    # 2️⃣ Smart combos
    combo_options = []

    for combo in combinations(drivers, max_combo):
        seats = sum(v["seats"] for v in combo)

        if seats < total_pax:
            continue

        # Avoid useless bigger combo than single
        if best_single and seats > best_single["seats"]:
            continue

        # Avoid too much waste (max +2 seats buffer)
        if seats - total_pax > 2:
            continue

        combo_options.append({
            "vehicles": list(combo),
            "total_seats": seats
        })

    # Sort combos: closest fit first
    combo_options.sort(key=lambda x: x["total_seats"])

    options.extend(combo_options)

    return options[:5]

def get_available_drivers(db, company_id, package_id, travel_date):
    booked_vehicle_ids = (
        db.query(BookingVehicleDriver.vehicle_id)
        .join(ManualBooking, ManualBooking.id == BookingVehicleDriver.booking_id)
        .filter(
            ManualBooking.travel_date == travel_date,
            ManualBooking.is_deleted == False
        )
        .distinct()
        .all()
    )

    booked_vehicle_ids = [d[0] for d in booked_vehicle_ids]

    vehicles = (
        db.query(Vehicle)
        .filter(
            Vehicle.company_id == company_id,
            Vehicle.is_deleted == False,
            ~Vehicle.id.in_(booked_vehicle_ids),
            Vehicle.seats > 0
        )
        .all()
    )

    return [
        {
            "id": d.id,
            "name": d.name,
            "vehicle_type": d.vehicle_type,
            "vehicle_number": d.vehicle_number,
            "seats": d.seats
        }
        for d in vehicles
    ]
