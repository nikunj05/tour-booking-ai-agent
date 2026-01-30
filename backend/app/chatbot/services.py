from sqlalchemy import distinct
from app.models.tour_package import TourPackage

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
    print("cities",cities)

    # Convert [('Dubai',), ('Abu Dhabi',)] → ['Dubai', 'Abu Dhabi']
    return [c[0] for c in cities if c[0]]
