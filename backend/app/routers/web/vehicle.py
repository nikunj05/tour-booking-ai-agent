from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.models.vehicle import Vehicle, VehiclePhoto
from app.models.driver import Driver
from app.auth.dependencies import company_only
from app.core.templates import templates
import os
from datetime import datetime
from app.utils.flash import flash_redirect

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])

UPLOAD_DIR = "app/static/uploads/vehicles"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------------------------
# Helper: render form
# -------------------------------------------------
def render_form(
    request: Request,
    *,
    vehicle=None,
    form=None,
    errors=None,
    status_code=200,
    country_codes=None
):
    return templates.TemplateResponse(
        "vehicles/form.html",
        {
            "request": request,
            "vehicle": vehicle,
            "form": form or {},
            "errors": errors or {},
        },
        status_code=status_code
    )

# =================================================
# LIST PAGE
# =================================================
@router.get("", response_class=HTMLResponse, name="vehicle_list")
def vehicle_list(
    request: Request,
    _=Depends(company_only)
):
    return templates.TemplateResponse(
        "vehicles/list.html",
        {"request": request}
    )

# =================================================
# DATATABLE API
# =================================================
@router.get("/datatable", name="vehicle_datatable")
def vehicle_datatable(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(company_only)
):
    vehicles = db.query(Vehicle).filter(Vehicle.is_deleted == False, Vehicle.company_id == current_user.company.id).all()

    data = []
    edit_icon = "/static/assets/icon/edit.svg"
    trash_icon = "/static/assets/icon/trash.svg"
    for v in vehicles:
        data.append({
            "id": v.id,
            "name": v.name,
            "vehicle_type": v.vehicle_type,
            "vehicle_number": v.vehicle_number,
            "seats": v.seats,
            "status": "Active" if v.is_active else "Inactive",
            "actions": f"""
                <a href="{request.url_for('vehicle_edit_page', vehicle_id=v.id)}"
                   class="btn btn-sm btn-edit">
                   <img src="{edit_icon}" alt="Edit" class="table-icon">
                </a>

                <a href="javascript:void(0)"
                   class="confirm-vehicle-delete btn btn-sm btn-delete"
                   data-route="{request.url_for('vehicle_delete', vehicle_id=v.id)}">
                   <img src="{trash_icon}" alt="Delete" class="table-icon">
                </a>
            """
        })

    return JSONResponse({"data": data})

# =================================================
# CREATE PAGE
# =================================================
@router.get("/create", response_class=HTMLResponse, name="vehicle_create_page")
def vehicle_create_page(
    request: Request,
    _=Depends(company_only)
):
    return render_form(request)


# =================================================
# CREATE API
# =================================================
@router.post("/create", name="vehicle_create")
async def vehicle_create(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(company_only)
):
    form = await request.form()  # await works

    vehicle = Vehicle(
        name=form.get("name"),
        vehicle_type=form.get("vehicle_type"),
        vehicle_number=form.get("vehicle_number"),
        seats=form.get("seats"),
        company_id=current_user.company.id,
        is_active=bool(form.get("is_active"))
    )
    
    db.add(vehicle)
    db.commit()       # <-- commit so vehicle.id is generated
    db.refresh(vehicle)

    # Save multiple uploaded photos if any
    files = form.getlist("gallery_images")
    print(files)
    uploaded_paths = []

    for file in files:
        if file.filename:  # skip empty files
            filename = f"{datetime.utcnow().timestamp()}_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, filename)  # Full path on disk
            with open(file_path, "wb") as f:
                f.write(await file.read())
            
            # Store relative path in DB for URL generation
            relative_path = os.path.relpath(file_path, "app/static")
            db.add(VehiclePhoto(vehicle_id=vehicle.id, file_path=relative_path))

    db.commit()
    
    return flash_redirect(url=request.url_for("vehicle_list"), message="Vehicle created successfully")

# =================================================
# EDIT PAGE
# =================================================
@router.get("/{vehicle_id}/edit", response_class=HTMLResponse, name="vehicle_edit_page")
def vehicle_edit_page(
    vehicle_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(company_only)
):
    vehicle = db.query(Vehicle).get(vehicle_id)
    if not vehicle or vehicle.is_deleted:
        return flash_redirect(request.url_for("vehicle_list"), "Vehicle not found")

    return render_form(
        request,
        vehicle=vehicle,
        form=vehicle.__dict__
    )

# =================================================
# EDIT API
# =================================================
@router.post("/{vehicle_id}/edit", name="vehicle_update")
async def vehicle_update(
    vehicle_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(company_only)
):
    vehicle = db.query(Vehicle).get(vehicle_id)
    if not vehicle or vehicle.is_deleted:
        return flash_redirect(request.url_for("vehicle_list"), "Vehicle not found")

    form = await request.form()
    
    # Update basic fields
    vehicle.name = form.get("name")
    vehicle.vehicle_type = form.get("vehicle_type")
    vehicle.vehicle_number = form.get("vehicle_number")
    vehicle.seats = form.get("seats")
    vehicle.is_active = bool(form.get("is_active"))
    
    # Handle multiple photo upload
    files = form.getlist("gallery_images")
    if files and files[0].filename:  # if any new file is uploaded
        # Delete old photos
        for photo in vehicle.photos:
            if os.path.exists(os.path.join("app/static", photo.file_path)):
                os.remove(os.path.join("app/static", photo.file_path))
            db.delete(photo)
        db.commit()  # commit deletion

        # Save new photos
        for file in files:
            filename = f"{datetime.utcnow().timestamp()}_{file.filename}"
            # Absolute path to save the file
            save_path = os.path.join(UPLOAD_DIR, filename)
            with open(save_path, "wb") as f:
                f.write(await file.read())

            # Relative path to store in DB (after 'static/')
            relative_path = f"uploads/vehicles/{filename}"
            db.add(VehiclePhoto(vehicle_id=vehicle.id, file_path=relative_path))

    db.commit()

    
    return flash_redirect(url=request.url_for("vehicle_list"), message="Vehicle updated successfully")

# =================================================
# DELETE API
# =================================================
@router.post("/{vehicle_id}/delete", name="vehicle_delete")
def vehicle_delete(
    vehicle_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(company_only)
):
    vehicle = db.query(Vehicle).get(vehicle_id)
    if not vehicle or vehicle.is_deleted:
        return flash_redirect(request.url_for("vehicle_list"), "Vehicle not found")

    vehicle.is_deleted = True
    db.commit()
    
    return flash_redirect(url=request.url_for("vehicle_list"), message="Vehicle deleted successfully")