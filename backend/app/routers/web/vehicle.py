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
            "name": f"{v.name} ({v.vehicle_type})",
            "vehicle_number": v.vehicle_number,
            "seats": f"{v.seats} Seater",
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
    
    vehicle.name = form.get("name")
    vehicle.vehicle_type = form.get("vehicle_type")
    vehicle.vehicle_number = form.get("vehicle_number")
    vehicle.seats = form.get("seats")
    vehicle.is_active = bool(form.get("is_active"))

    # Handle multiple new gallery images (add only, do NOT delete old ones)
    files = form.getlist("gallery_images")  # input name="gallery_images" in form
    for file in files:
        if file.filename:  # skip empty files
            filename = f"{datetime.utcnow().timestamp()}_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(await file.read())
            # Store relative path in DB
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


@router.post("/gallery-image/{image_id}/delete", name="vehicle_gallery_image_delete")
def delete_vehicle_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(company_only)
):
    # Fetch the image
    photo = db.query(VehiclePhoto).get(image_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Image not found")

    # Optional: verify the vehicle belongs to the user's company
    if photo.vehicle.company_id != current_user.company.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Delete file from disk
    if os.path.exists(photo.file_path):
        os.remove(photo.file_path)

    # Delete DB record
    db.delete(photo)
    db.commit()

    return {"success": True, "message": "Image deleted successfully"}