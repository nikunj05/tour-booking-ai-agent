from app.models.tour_package import TourPackage,TourPackageDriver
from sqlalchemy import distinct

def get_active_cities(db, company_id: int):
    cities = (
        db.query(distinct(TourPackage.city)).filter(
            TourPackage.status == "active",
            TourPackage.is_deleted == False,
            TourPackage.company_id == company_id
        )
        .all()
    )

    if cities:
        cities = [c[0] for c in cities if c[0]]
        
    return cities