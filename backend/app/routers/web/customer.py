
from app.models.manual_booking import ManualBooking
from app.database.session import get_db
from app.models.user import User
from app.auth.dependencies import company_only
from fastapi import (
    APIRouter, Depends, Request, Form, UploadFile, File
)
from app.core.constants import COUNTRY_CODES
from sqlalchemy.orm import Session
from app.core.templates import templates
from app.models.customer import Customer
from app.utils.flash import flash_redirect
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy import or_

router = APIRouter(tags=["Customers"])

# -------------------------------------------------
# Helper: render form
# -------------------------------------------------
def render_form(
    request: Request,
    *,
    customer=None,
    form=None,
    errors=None,
    status_code=200,
    country_codes=None
):
    return templates.TemplateResponse(
        "customers/form.html",
        {
            "request": request,
            "customer": customer,
            "country_codes": COUNTRY_CODES,
            "form": form or {},
            "errors": errors or {},
        },
        status_code=status_code
    )


@router.get("/customers", name="customer_list")
def customer_list(
    request: Request,
    _=Depends(company_only)
):
    return templates.TemplateResponse("customers/list.html", {"request": request})

@router.get("/customers/datatable", name="customers_datatable")
def customers_datatable(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(company_only)
):
    customers = (
        db.query(Customer)
        .filter(Customer.is_deleted == False)
        .all()
    )
    edit_icon = "/static/assets/icon/edit.svg"
    trash_icon = "/static/assets/icon/trash.svg"

    data = [
        {
            "name": c.guest_name,
            "phone": f"{c.country_code} {c.phone}",
            "email": c.email,
            "actions": f"""
                <a href="{request.url_for('customer_edit_page', customer_id=c.id)}"
                   class="btn btn-sm btn-edit">
                   <img src="{edit_icon}" alt="Edit" class="table-icon">
                </a>

                <a href="javascript:void(0)"
                   class="confirm-customer-delete btn btn-sm btn-delete"
                   data-route="{request.url_for('customer_delete', customer_id=c.id)}">
                   <img src="{trash_icon}" alt="Delete" class="table-icon">
                </a>
            """
        }
        for c in customers
    ]

    return {"data": data}

@router.get("/customers/create", name="customer_create_page")
def create_page(
    request: Request,
    _=Depends(company_only)
):
    return render_form(
        request,
        customer=None,
        country_codes=COUNTRY_CODES,
        form={}
    )

@router.post("/customers/create", name="customer_create")
async def create_customer(
    request: Request,
    guest_name: str = Form(...),
    country_code: str = Form(...),
    phone: str = Form(...),
    email: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(company_only)
):
    errors = {}

    # 🔍 DUPLICATE CHECK
    duplicate = (
        db.query(Customer)
        .filter(
            Customer.company_id == current_user.company.id,
            Customer.is_deleted == False,
            or_(
                (Customer.phone == phone) & (Customer.country_code == country_code),
                Customer.email == email if email else False
            )
        )
        .first()
    )

    if duplicate:
        if duplicate.phone == phone and duplicate.country_code == country_code:
            errors["phone"] = "Phone number already exists"
        if email and duplicate.email == email:
            errors["email"] = "Email already exists"

        if errors:
            form_data = dict(await request.form())
            return render_form(
                request,
                customer=None,   # <--- customer doesn't exist yet
                form=form_data,
                errors=errors
            )

    # ✅ CREATE CUSTOMER
    customer = Customer(
        company_id=current_user.company.id,
        guest_name=guest_name,
        country_code=country_code,
        phone=phone,
        email=email,
    )

    db.add(customer)
    db.commit()

    return flash_redirect(
        request.url_for("customer_list"),
        "Customer created successfully"
    )

# =================================================
# EDIT / UPDATE
# =================================================
@router.get("/customers/{customer_id}/edit", response_class=HTMLResponse, name="customer_edit_page")
def edit_page(
    customer_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(company_only)
):
    customer = db.query(Customer).get(customer_id)
    if not customer or customer.is_deleted:
        return flash_redirect(request.url_for("customer_list"), "Customer not found")

    return render_form(
        request,
        customer=customer,
        country_codes=COUNTRY_CODES,
        form=customer.__dict__
    )

@router.post("/{customer_id}/edit", name="customer_update")
async def update_customer(
    customer_id: int,
    request: Request,
    guest_name: str = Form(...),
    country_code: str = Form(...),
    phone: str = Form(...),
    email: str = Form(None),
    db: Session = Depends(get_db),
    _=Depends(company_only)
):
    customer = db.query(Customer).get(customer_id)
    if not customer or customer.is_deleted:
        return flash_redirect(request.url_for("customer_list"), "Customer not found")

    errors = {}

    # 🔍 DUPLICATE CHECK (exclude current customer)
    duplicate = (
        db.query(Customer)
        .filter(
            Customer.company_id == customer.company_id,
            Customer.id != customer.id,
            Customer.is_deleted == False,
            or_(
                (Customer.phone == phone) & (Customer.country_code == country_code),
                Customer.email == email if email else False
            )
        )
        .first()
    )

    if duplicate:
        if duplicate.phone == phone and duplicate.country_code == country_code:
            errors["phone"] = "Phone number already exists"
        if email and duplicate.email == email:
            errors["email"] = "Email already exists"

    if errors:
        form_data = dict(await request.form())   # ✅ await here
        return render_form(
            request,
            customer=customer,
            form=form_data,
        errors=errors
    )

    # ✅ UPDATE
    customer.guest_name = guest_name
    customer.country_code = country_code
    customer.phone = phone
    customer.email = email

    db.commit()

    return flash_redirect(
        request.url_for("customer_list"),
        "Customer updated successfully"
    )


# =================================================
# DELETE (SOFT)
# =================================================
@router.post("/{customer_id}/delete", name="customer_delete")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    _=Depends(company_only)
):
    customer = db.query(Customer).get(customer_id)
    if customer:
        customer.is_deleted = True
        db.commit()
    return True
