from app.models.tour_package import TourPackage,TourPackageDriver

def filter_packages(db, company_id: int, city: str):
    query = db.query(TourPackage).filter(
        TourPackage.company_id == company_id,
        TourPackage.status == "active",
        TourPackage.is_deleted == False
    )

    if city != "All":
        query = query.filter(TourPackage.city == city)

    return query.all()