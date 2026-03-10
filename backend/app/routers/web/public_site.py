from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.session import get_db
from app.models.company import Company
from app.models.tour_package import TourPackage
from app.models.vehicle import Vehicle

router = APIRouter(tags=["Public Website"])
templates = Jinja2Templates(directory="app/templates")

SUPPORTED_LANGUAGES = ['en', 'hi', 'ar']
DEFAULT_LANGUAGE = 'en'

def get_language_from_request(request: Request) -> str:
    # Try cookie first
    lang = request.cookies.get('lang')
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang
    # Try Accept-Language header
    accept_lang = request.headers.get('accept-language', '').split(',')[0].split('-')[0]
    if accept_lang in SUPPORTED_LANGUAGES:
        return accept_lang
    return DEFAULT_LANGUAGE

@router.get("/{company_slug}", response_class=HTMLResponse)
async def public_home(request: Request, company_slug: str, db: Session = Depends(get_db)):
    lang = get_language_from_request(request)
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
        "lang": lang,
        "supported_languages": SUPPORTED_LANGUAGES,
        "title": f"Home | {company.company_name}"
    })

@router.get("/{company_slug}/about", response_class=HTMLResponse)
async def public_about(request: Request, company_slug: str, db: Session = Depends(get_db)):
    lang = get_language_from_request(request)
    company = db.query(Company).filter(Company.slug == company_slug, Company.is_deleted == False).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return templates.TemplateResponse("public_site/about.html", {
        "request": request,
        "company": company,
        "lang": lang,
        "supported_languages": SUPPORTED_LANGUAGES,
        "title": f"About Us | {company.company_name}"
    })

@router.get("/{company_slug}/tours", response_class=HTMLResponse)
async def public_tours(
    request: Request, 
    company_slug: str, 
    search: Optional[str] = None,
    city: Optional[str] = None,
    sort: str = "newest",
    db: Session = Depends(get_db)
):
    lang = get_language_from_request(request)
    company = db.query(Company).filter(Company.slug == company_slug, Company.is_deleted == False).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Base query
    query = db.query(TourPackage).filter(
        TourPackage.company_id == company.id, 
        TourPackage.is_deleted == False, 
        TourPackage.status == 'active'
    )

    # Apply filters
    if search:
        query = query.filter(TourPackage.title.ilike(f"%{search}%"))
    if city and city != "all":
        query = query.filter(TourPackage.city == city)

    # Apply sorting
    if sort == "price_low":
        query = query.order_by(TourPackage.price.asc())
    elif sort == "price_high":
        query = query.order_by(TourPackage.price.desc())
    else:
        query = query.order_by(TourPackage.id.desc())

    tours = query.all()

    # Fetch unique cities for the filter dropdown
    cities = db.query(TourPackage.city).filter(
        TourPackage.company_id == company.id, 
        TourPackage.is_deleted == False, 
        TourPackage.status == 'active'
    ).distinct().all()
    cities = [c[0] for c in cities if c[0]]
    
    return templates.TemplateResponse("public_site/tours.html", {
        "request": request,
        "company": company,
        "tours": tours,
        "cities": sorted(cities),
        "current_search": search or "",
        "current_city": city or "all",
        "current_sort": sort,
        "lang": lang,
        "supported_languages": SUPPORTED_LANGUAGES,
        "title": f"Our Tours | {company.company_name}"
    })

@router.get("/{company_slug}/tour/{tour_id}", response_class=HTMLResponse)
async def public_tour_detail(request: Request, company_slug: str, tour_id: int, db: Session = Depends(get_db)):
    lang = get_language_from_request(request)
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
        "lang": lang,
        "supported_languages": SUPPORTED_LANGUAGES,
        "title": f"{tour.title} | {company.company_name}"
    })

@router.get("/{company_slug}/vehicles", response_class=HTMLResponse)
async def public_vehicles(request: Request, company_slug: str, db: Session = Depends(get_db)):
    lang = get_language_from_request(request)
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
        "lang": lang,
        "supported_languages": SUPPORTED_LANGUAGES,
        "title": f"Our Fleet | {company.company_name}"
    })

@router.get("/{company_slug}/contact", response_class=HTMLResponse)
async def public_contact(request: Request, company_slug: str, db: Session = Depends(get_db)):
    lang = get_language_from_request(request)
    company = db.query(Company).filter(Company.slug == company_slug, Company.is_deleted == False).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return templates.TemplateResponse("public_site/contact.html", {
        "request": request,
        "company": company,
        "lang": lang,
        "supported_languages": SUPPORTED_LANGUAGES,
        "title": f"Contact Us | {company.company_name}"
    })
