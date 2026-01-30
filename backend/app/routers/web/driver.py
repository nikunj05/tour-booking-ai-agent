import os, uuid
from fastapi import (
    APIRouter, Depends, Request, Form, UploadFile, File
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import ValidationError
from app.core.constants import COUNTRY_CODES
from app.database.session import get_db
from app.core.templates import templates
from app.auth.dependencies import company_only
from app.models.driver import Driver
from app.schemas.driver import DriverCreate, DriverUpdate
from app.utils.flash import flash_redirect
from app.models.user import User


# -------------------------------------------------
# Router config
# -------------------------------------------------
router = APIRouter(prefix="/drivers", tags=["Drivers"])

UPLOAD_DIR = "app/static/uploads/drivers"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------------------------
# Helper: render form
# -------------------------------------------------
def render_form(
    request: Request,
    *,
    driver=None,
    form=None,
    errors=None,
    status_code=200,
    country_codes=None
):
    return templates.TemplateResponse(
        "drivers/form.html",
        {
            "request": request,
            "driver": driver,
            "country_codes": COUNTRY_CODES,
            "form": form or {},
            "errors": errors or {},
        },
        status_code=status_code
    )

# =================================================
# LIST PAGE
# =================================================
@router.get("", response_class=HTMLResponse, name="driver_list")
def driver_list(
    request: Request,
    _=Depends(company_only)
):
    return templates.TemplateResponse(
        "drivers/list.html",
        {"request": request}
    )

# =================================================
# DATATABLE API
# =================================================
@router.get("/datatable", name="driver_datatable")
def driver_datatable(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(company_only)
):
    drivers = db.query(Driver).filter(Driver.is_deleted == False, Driver.company_id == current_user.company.id).all()

    data = []
    edit_icon = "/static/assets/icon/edit.svg"
    trash_icon = "/static/assets/icon/trash.svg"
    for d in drivers:
        data.append({
            "id": d.id,
            "name": d.name,
            "vehicle": f"{d.vehicle_type} ({d.vehicle_number})",
            "seats": d.seats,
            "phone": f"{d.country_code}{d.phone_number}",
            "actions": f"""
                <a href="{request.url_for('driver_edit_page', driver_id=d.id)}"
                   class="btn btn-sm btn-edit">
                   <img src="{edit_icon}" alt="Edit" class="table-icon">
                </a>

                <a href="javascript:void(0)"
                   class="confirm-driver-delete btn btn-sm btn-delete"
                   data-route="{request.url_for('driver_delete', driver_id=d.id)}">
                   <img src="{trash_icon}" alt="Delete" class="table-icon">
                </a>
            """
        })

    return JSONResponse({"data": data})

# =================================================
# CREATE
# =================================================
@router.get("/create", response_class=HTMLResponse, name="driver_create_page")
def create_page(
    request: Request,
    _=Depends(company_only)
):
    return render_form(request, country_codes=COUNTRY_CODES)

@router.post("/create", name="driver_create")
async def driver_create(
    request: Request,
    name: str = Form(...),
    country_code: str = Form(...),
    phone_number: str = Form(...),
    vehicle_type: str = Form(...),
    vehicle_number: str = Form(...),
    seats: int = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(company_only),
):

    driver = Driver(
        company_id=current_user.company.id,
        name=name,
        country_code=country_code,
        phone_number=phone_number,
        vehicle_type=vehicle_type,
        vehicle_number=vehicle_number,
        seats=seats,
    )

    # ✅ IMAGE UPLOAD
    if image and image.filename:
        ext = image.filename.split(".")[-1]
        filename = f"driver_{uuid.uuid4().hex}.{ext}"
        path =  os.path.join(UPLOAD_DIR, filename)

        with open(path, "wb") as f:
            f.write(image.file.read())

        driver.image = f"uploads/drivers/{filename}"

    db.add(driver)
    db.commit()

    return flash_redirect(
        url=request.url_for("driver_list"),
        message="Driver created successfully"
    )


# =================================================
# EDIT / UPDATE
# =================================================
@router.get("/{driver_id}/edit", response_class=HTMLResponse, name="driver_edit_page")
def edit_page(
    driver_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(company_only)
):
    driver = db.query(Driver).get(driver_id)
    if not driver or driver.is_deleted:
        return flash_redirect(request.url_for("driver_list"), "Driver not found")

    return render_form(
        request,
        driver=driver,
        country_codes=COUNTRY_CODES,
        form=driver.__dict__
    )

@router.post("/{driver_id}/edit", name="driver_update")
def update_driver(
    driver_id: int,
    request: Request,
    name: str = Form(...),
    vehicle_type: str = Form(...),
    vehicle_number: str = Form(...),
    seats: int = Form(...),
    country_code: str = Form(...),
    phone_number: str = Form(...),
    image: UploadFile = File(None),

    db: Session = Depends(get_db),
    _=Depends(company_only)
):
    driver = db.query(Driver).get(driver_id)
    if not driver:
        return flash_redirect(request.url_for("driver_list"), "Driver not found")

    driver.name = name
    driver.vehicle_type = vehicle_type
    driver.vehicle_number = vehicle_number
    driver.seats = seats
    driver.country_code = country_code
    driver.phone_number = phone_number

    if image and image.filename:
        ext = image.filename.split(".")[-1]
        filename = f"driver_{uuid.uuid4().hex}.{ext}"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as f:
            f.write(image.file.read())
        driver.image = f"uploads/drivers/{filename}"

    db.commit()

    return flash_redirect(
        url=request.url_for("driver_list"),
        message="Driver updated successfully"
    )

# =================================================
# DELETE (SOFT)
# =================================================
@router.post("/{driver_id}/delete", name="driver_delete")
def delete_driver(
    driver_id: int,
    db: Session = Depends(get_db),
    _=Depends(company_only)
):
    driver = db.query(Driver).get(driver_id)
    if driver:
        driver.is_deleted = True
        db.commit()
    return True
