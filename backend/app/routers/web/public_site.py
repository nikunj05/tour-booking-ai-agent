from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.company import Company
from app.models.tour_package import TourPackage
from app.models.vehicle import Vehicle

router = APIRouter(tags=["Public Website"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/{company_slug}", response_class=HTMLResponse)
async def public_home(request: Request, company_slug: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == company_slug, Company.is_deleted == False).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Fetch some featured tours
    tours = db.query(TourPackage).filter(
        TourPackage.company_id == company.id, 
        TourPackage.is_deleted == False, 
        TourPackage.status == 'active'
    ).limit(10).all()

    vehicles = db.query(Vehicle).filter(
        Vehicle.company_id == company.id, 
        Vehicle.is_deleted == False, 
        Vehicle.is_active == True
    ).limit(10).all()
    
    return templates.TemplateResponse("public_site/home.html", {
        "request": request,
        "company": company,
        "tours": tours,
        "vehicles": vehicles,
        "title": f"Home | {company.company_name}"
    })

@router.get("/{company_slug}/about", response_class=HTMLResponse)
async def public_about(request: Request, company_slug: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == company_slug, Company.is_deleted == False).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return templates.TemplateResponse("public_site/about.html", {
        "request": request,
        "company": company,
        "title": f"About Us | {company.company_name}"
    })

@router.get("/{company_slug}/tours", response_class=HTMLResponse)
async def public_tours(request: Request, company_slug: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == company_slug, Company.is_deleted == False).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    tours = db.query(TourPackage).filter(
        TourPackage.company_id == company.id, 
        TourPackage.is_deleted == False, 
        TourPackage.status == 'active'
    ).all()
    
    return templates.TemplateResponse("public_site/tours.html", {
        "request": request,
        "company": company,
        "tours": tours,
        "title": f"Our Tours | {company.company_name}"
    })

@router.get("/{company_slug}/tour/{tour_id}", response_class=HTMLResponse)
async def public_tour_detail(request: Request, company_slug: str, tour_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == company_slug, Company.is_deleted == False).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    tour = db.query(TourPackage).filter(
        TourPackage.id == tour_id, 
        TourPackage.company_id == company.id, 
        TourPackage.is_deleted == False
    ).first()
    
    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")
    
    return templates.TemplateResponse("public_site/tour_details.html", {
        "request": request,
        "company": company,
        "tour": tour,
        "title": f"{tour.title} | {company.company_name}"
    })

@router.get("/{company_slug}/vehicles", response_class=HTMLResponse)
async def public_vehicles(request: Request, company_slug: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == company_slug, Company.is_deleted == False).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    vehicles = db.query(Vehicle).filter(
        Vehicle.company_id == company.id, 
        Vehicle.is_deleted == False, 
        Vehicle.is_active == True
    ).all()
    
    return templates.TemplateResponse("public_site/vehicles.html", {
        "request": request,
        "company": company,
        "vehicles": vehicles,
        "title": f"Our Fleet | {company.company_name}"
    })

@router.get("/{company_slug}/contact", response_class=HTMLResponse)
async def public_contact(request: Request, company_slug: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.slug == company_slug, Company.is_deleted == False).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return templates.TemplateResponse("public_site/contact.html", {
        "request": request,
        "company": company,
        "title": f"Contact Us | {company.company_name}"
    })
