import os, uuid
from fastapi import (
    APIRouter, Depends, Request, Form, UploadFile, File, Query
)
from fastapi.responses import (
    HTMLResponse, RedirectResponse, JSONResponse
)
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import ValidationError

from app.database.session import get_db
from app.core.templates import templates
from app.core.security import hash_password
from app.auth.dependencies import admin_only, get_current_user
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.core.constants import COUNTRIES, CURRENCIES
from app.utils.flash import flash_redirect

# -------------------------------------------------
# Router config
# -------------------------------------------------
router = APIRouter(prefix="/companies", tags=["Companies"])

UPLOAD_DIR = "app/static/uploads/companies"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -------------------------------------------------
# Helper: redirect with flash message
# -------------------------------------------------
def redirect_with_message(request: Request, message: str, url_name="login_page"):
    response = RedirectResponse(
        url=request.url_for(url_name),
        status_code=302
    )
    response.set_cookie("flash_error", message)
    return response

# -------------------------------------------------
# Helper: render form
# -------------------------------------------------
def render_form(
    request: Request,
    *,
    company=None,
    form=None,
    errors=None,
    is_my_profile: bool = False,
    status_code=200,
    **context
):
    return templates.TemplateResponse(
        "companies/form.html",
        {
            "request": request,
            "company": company,
            "form": form or {},
            "errors": errors or {},
            "is_my_profile": is_my_profile,
            **context
        },
        status_code=status_code
    )
    
@router.get("/datatable", name="company_datatable")
def company_datatable(
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(admin_only)
):
    companies = (
        db.query(Company)
        .filter(
            Company.is_deleted == False,
            Company.user.has(User.role == "company")
        )
        .all()
    )

    data = []
    edit_icon = "/static/assets/icon/edit.svg"
    trash_icon = "/static/assets/icon/trash.svg"
    for company in companies:
        data.append({
            "company_name": company.company_name,
            "email": company.user.email,
            "phone": company.phone,
            "status": company.status,
            "actions": f"""
                <a href="{request.url_for('company_edit_page', company_id=company.id)}"
           class="btn btn-sm btn-edit"
           title="Edit Company">
            <img src="{edit_icon}" alt="Edit" class="table-icon">
        </a>

        <a href="javascript:void(0)"
           class="confirm-company-delete btn btn-sm btn-delete"
           data-route="{request.url_for('company_delete', company_id=company.id)}"
           title="Delete Company">
            <img src="{trash_icon}" alt="Delete" class="table-icon">
        </a>
            """
        })

    return JSONResponse({
        "data": data   # ✅ ONLY THIS
    })


# =================================================
# LIST PAGE (HTML)
# =================================================
@router.get("/", response_class=HTMLResponse, name="company_list")
def company_list(
    request: Request,
    current_user: User = Depends(admin_only)
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    return templates.TemplateResponse(
        "companies/list.html",
        {"request": request}
    )

# =================================================
# CREATE COMPANY
# =================================================
@router.get("/create", response_class=HTMLResponse, name="company_create_page")
def create_page(
    request: Request,
    current_user: User = Depends(admin_only)
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    return render_form(request, currencies=CURRENCIES, countries=COUNTRIES)

@router.post("/create", name="company_create")
def create_company(
    request: Request,
    company_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    currency: str = Form(...),
    country: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    try:
        validated = CompanyCreate(
            company_name=company_name,
            country=country,
            email=email,
            phone=phone,
            currency=currency,
        )
    except ValidationError as e:
        return render_form(
            request,
            form=locals(),
            errors={err["loc"][0]: err["msg"] for err in e.errors()},
            currencies=CURRENCIES,
            countries=COUNTRIES,
            status_code=400
        )

    if db.query(User).filter(User.email == email).first():
        return render_form(
            request,
            form=locals(),
            errors={"email": "Email already exists"},
            currencies=CURRENCIES,
            countries=COUNTRIES,
            status_code=400
        )

    user = User(
        email=email,
        password_hash=hash_password("12345678"),
        role="company",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    company = Company(
        user_id=user.id,
        company_name=company_name,
        country=country,
        phone=phone,
        currency=currency,
        status="active"
    )
    db.add(company)
    db.commit()

    return flash_redirect(
        url=request.url_for("company_list"),
        message="Company created successfully"
    )

# =================================================
# EDIT / UPDATE
# =================================================
@router.get("/{company_id}/edit", response_class=HTMLResponse, name="company_edit_page")
def edit_page(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    company = db.query(Company).get(company_id)
    if not company:
        return redirect_with_message(request, "Company not found")

    return render_form(
        request,
        company=company,
        currencies=CURRENCIES,
        countries=COUNTRIES,
        form={
            "company_name": company.company_name,
            "email": company.user.email,
            "phone": company.phone,
            "currency": company.currency,
            "country": company.country
        }
    )

@router.post("/{company_id}/edit", name="company_update")
def update_company(
    company_id: int,
    request: Request,
    company_name: str = Form(...),
    phone: str = Form(""),
    status: str = Form(...),
    country: str = Form(None),
    currency: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    company = db.query(Company).get(company_id)
    if not company:
        return redirect_with_message(request, "Company not found")

    company.company_name = company_name
    company.phone = phone
    company.status = status
    company.currency = currency
    company.country = country
    db.commit()
    
    return flash_redirect(
        url=request.url_for("company_list"),
        message="Company Details updated successfully"
    )

# =================================================
# DELETE
# =================================================
@router.post("/{company_id}/delete", name="company_delete")
def delete_company(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only)
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    company = db.query(Company).get(company_id)
    if not company:
        return redirect_with_message(request, "Company not found")

    db.delete(company.user)
    db.delete(company)
    db.commit()

    return True

# =================================================
# MY PROFILE
# =================================================
@router.get("/my-profile", response_class=HTMLResponse, name="my_profile")
def my_profile(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    if not current_user.company:
        return redirect_with_message(request, "Company profile not found")

    company = current_user.company

    return render_form(
        request,
        company=company,
        is_my_profile=True,
        currencies=CURRENCIES,
        countries=COUNTRIES,
        form={
            "company_name": company.company_name,
            "email": current_user.email,
            "phone": company.phone,
            "currency": company.currency,
            "country": company.country
        }
    )   
    
@router.post("/my-profile", name="my_profile_update")
def update_my_profile(
    request: Request,

    company_name: str = Form(...),
    phone: str = Form(None),
    currency: str = Form(...),
    country: str = Form(None),
    logo: UploadFile = File(None), 

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    company = current_user.company
    if isinstance(current_user, RedirectResponse):
        return current_user
    # ✅ Validate using CompanyUpdate
    try:
        form = CompanyUpdate(
            company_name=company_name,
            phone=phone or None,
            status=company.status,
            currency=currency,
            country=country
        )
    except ValidationError as e:
        errors = {err["loc"][0]: err["msg"] for err in e.errors()}
        return render_form(
            request,
            company=company,
            currencies=CURRENCIES,
            countries=COUNTRIES,
            form={
                "company_name": company_name,
                "phone": phone,
                "country": country
            },
            errors=errors,
            status_code=400
        )

    if logo and logo.filename:
        ext = logo.filename.split(".")[-1].lower()
        filename = f"company_{company.id}_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(logo.file.read())

        company.logo = f"uploads/companies/{filename}"

    # ✅ Update fields
    company.company_name = form.company_name
    company.phone = form.phone
    company.currency = form.currency
    company.country = form.country

    db.commit()

    return flash_redirect(
        url=request.url_for("my_profile"),
        message="Profile updated successfully"
    )
