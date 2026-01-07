from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import ValidationError
from typing import List, Optional
from uuid import uuid4
import os

from app.database.session import get_db
from app.core.templates import templates
from app.auth.dependencies import company_only, get_current_user
from app.utils.pagination import paginate
from app.models.tour_package import TourPackage, TourPackageGalleryImage
from app.schemas.tour_package import TourPackageCreate, TourPackageUpdate
from sqlalchemy import or_

from app.core.constants import COUNTRIES

router = APIRouter(prefix="/tour-packages", tags=["Tour Packages"])

UPLOAD_DIR = "app/static/uploads/tours"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def render_form(request: Request, *, package=None, form=None, errors=None, status_code=200):
    return templates.TemplateResponse(
        "tour_packages/form.html",
        {
            "request": request,
            "package": package,
            "countries": COUNTRIES,
            "form": form or {},
            "errors": errors or {},
        },
        status_code=status_code
    )
@router.get("/", response_class=HTMLResponse, name="my_tour_list")
def my_tour_list(
    request: Request,
    search: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(company_only),
):
    company = current_user.company

    query = db.query(TourPackage).filter(
        TourPackage.company_id == company.id,
        TourPackage.is_deleted == False
    )

    if search:
        query = query.filter(
            or_(
                TourPackage.title.ilike(f"%{search}%"),
                TourPackage.city.ilike(f"%{search}%"),
                TourPackage.country.ilike(f"%{search}%"),
            )
        )

    pagination = paginate(query.order_by(TourPackage.id.desc()), page)

    template = (
        "tour_packages/_table.html"
        if request.headers.get("X-Requested-With") == "XMLHttpRequest"
        else "tour_packages/list.html"
    )

    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "tours": pagination["items"],
            "pagination": pagination,
            "search": search,
        }
    )

    
@router.get("/create", response_class=HTMLResponse, name="tour_package_create_page")
def create_page(request: Request, _=Depends(company_only)):
    return render_form(request)
@router.post("/create" , response_class=HTMLResponse, name="tour_package_create")
def create_package(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    country: str = Form(...),
    city: str = Form(...),
    price: float = Form(...),
    itinerary: str = Form(None),
    excludes: str = Form(None),

    cover_image: UploadFile = File(...),
    gallery_images: Optional[List[UploadFile]] = File(None),

    db: Session = Depends(get_db),
    current_user=Depends(company_only)
):
    form_data = {
        "title": title,
        "description": description,
        "country": country,
        "city": city,
        "price": price,
        "itinerary": itinerary,
        "excludes": excludes,
    }

    try:
        validated = TourPackageCreate(**form_data)
    except ValidationError as e:
        errors = {err["loc"][0]: err["msg"] for err in e.errors()}
        return render_form(request, form=form_data, errors=errors, countries=COUNTRIES, status_code=400)
    # Save cover image
    package = TourPackage(
    company_id=current_user.company.id,
    **validated.dict()
    )
    db.add(package)
    db.flush()
    
    cover_path = save_image(cover_image)
    db.add(
        TourPackageGalleryImage(
            tour_package_id=package.id,
            image_path=cover_path,
            image_type="cover"
        )
    )
    
    if gallery_images:
        for img in gallery_images:
            if not img.content_type.startswith("image/"):
                continue

            db.add(
                TourPackageGalleryImage(
                    tour_package_id=package.id,
                    image_path=save_image(img),
                    image_type="gallery"
                )
            )

    db.commit()
    return RedirectResponse(request.url_for("my_tour_list"), status_code=303)

@router.get("/{package_id}/edit", response_class=HTMLResponse, name="tour_package_edit_page")
def edit_page(
    package_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(company_only)
):
    package = db.query(TourPackage).filter(
        TourPackage.id == package_id,
        TourPackage.company_id == current_user.company.id,
        TourPackage.is_deleted == False
    ).first()

    if not package:
        return RedirectResponse("/tour-packages", status_code=303)

    images = db.query(TourPackageGalleryImage).filter(
        TourPackageGalleryImage.tour_package_id == package.id
    ).all()

    return templates.TemplateResponse(
        "tour_packages/form.html",
        {
            "request": request,
            "package": package,
            "gallery_images": images,
            "form": package.__dict__,
            "countries": COUNTRIES
        }
    )

@router.post("/{package_id}/edit", name="tour_package_update")
def update_package(
    package_id: int,
    request: Request,

    title: str = Form(...),
    description: str = Form(...),
    country: str = Form(...),
    city: str = Form(...),
    price: float = Form(...),
    itinerary: Optional[str] = Form(None),
    excludes: Optional[str] = Form(None),
    status: str = Form(...),

    cover_image: Optional[UploadFile] = File(None),
    gallery_images: Optional[List[UploadFile]] = File(None),

    db: Session = Depends(get_db),
    current_user=Depends(company_only)
):
    # -------------------------------------------------
    # 1. Fetch package (ownership + not deleted)
    # -------------------------------------------------
    package = db.query(TourPackage).filter(
        TourPackage.id == package_id,
        TourPackage.company_id == current_user.company.id,
        TourPackage.is_deleted == False
    ).first()

    if not package:
        return RedirectResponse(
            request.url_for("my_tour_list"),
            status_code=303
        )

    # -------------------------------------------------
    # 2. Update basic fields
    # -------------------------------------------------
    update_data = TourPackageUpdate(
        title=title,
        description=description,
        country=country,
        city=city,
        price=price,
        itinerary=itinerary,
        excludes=excludes,
        status=status
    )

    for field, value in update_data.dict().items():
        setattr(package, field, value)

    # -------------------------------------------------
    # 3. HANDLE COVER IMAGE (IMPORTANT FIX)
    # -------------------------------------------------
    if cover_image and cover_image.content_type.startswith("image/"):

        # Find existing cover
        old_cover = db.query(TourPackageGalleryImage).filter(
            TourPackageGalleryImage.tour_package_id == package.id,
            TourPackageGalleryImage.image_type == "cover"
        ).first()

        # Delete old cover record
        if old_cover:
            # OPTIONAL: delete file from disk
            # delete_file(old_cover.image_path)

            db.delete(old_cover)
            db.flush()

        # Save new cover
        new_cover = TourPackageGalleryImage(
            tour_package_id=package.id,
            image_path=save_image(cover_image),
            image_type="cover"
        )
        db.add(new_cover)

    # -------------------------------------------------
    # 4. HANDLE GALLERY IMAGES
    # -------------------------------------------------
    if gallery_images:
        for img in gallery_images:
            if img and img.content_type.startswith("image/"):
                db.add(
                    TourPackageGalleryImage(
                        tour_package_id=package.id,
                        image_path=save_image(img),
                        image_type="gallery"
                    )
                )

    # -------------------------------------------------
    # 5. COMMIT
    # -------------------------------------------------
    db.commit()

    return RedirectResponse(
        request.url_for("my_tour_list"),
        status_code=303
    )

@router.post("/{package_id}/delete", name="tour_package_delete")
def delete_package(
    package_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(company_only)
):
    package = db.query(TourPackage).filter(
        TourPackage.id == package_id,
        TourPackage.company_id == current_user.company.id
    ).first()

    if package:
        package.is_deleted = True
        db.commit()

    return RedirectResponse("/tour-packages", status_code=303)




def save_image(file: UploadFile) -> str:
    filename = f"{uuid4().hex}_{file.filename.replace(' ', '_')}"
    path = f"{UPLOAD_DIR}/{filename}"

    with open(path, "wb") as f:
        f.write(file.file.read())

    return path.replace("app/static/", "")

@router.get("/tours", name="public_tour_list")
def public_tour_list(request: Request, db: Session = Depends(get_db), search: str = ""):
    query = db.query(TourPackage).filter(TourPackage.is_deleted == False, TourPackage.status == "active")

    if search:
        query = query.filter(
            TourPackage.title.ilike(f"%{search}%") |
            TourPackage.city.ilike(f"%{search}%") |
            TourPackage.country.ilike(f"%{search}%")
        )

    tours = query.order_by(TourPackage.id.desc()).all()

    return templates.TemplateResponse(
        "tour_packages/public_list.html",
        {"request": request, "tours": tours, "search": search}
    )
    
@router.post("/gallery-image/{image_id}/delete", name="delete_gallery_image")
def delete_gallery_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(company_only)
):
    image = db.query(TourPackageGalleryImage).join(
        TourPackage
    ).filter(
        TourPackageGalleryImage.id == image_id,
        TourPackage.company_id == current_user.company.id
    ).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # delete file from disk (optional but recommended)
    file_path = f"static/{image.image_path}"
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(image)
    db.commit()

    return {"success": True}