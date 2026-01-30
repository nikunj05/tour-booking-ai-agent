from app.models.tour_package import TourPackage

def filter_packages(db, city):
    packages = db.query(TourPackage).filter(
        TourPackage.status == "active",
    ).all()

    if city != "All":
        packages = [p for p in packages if p.city == city]

    return packages
