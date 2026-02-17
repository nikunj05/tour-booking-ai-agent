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

    # Convert [('Dubai',), ('Abu Dhabi',)] → ['Dubai', 'Abu Dhabi']
    return [c[0] for c in cities if c[0]]