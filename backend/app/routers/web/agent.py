import os
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import ValidationError
from app.database.session import get_db
from app.core.templates import templates
from app.core.security import hash_password
from app.auth.dependencies import admin_only
from app.models.agent import Agent
from app.models.user import User
from app.schemas.agent import AgentCreate, AgentUpdate
from app.utils.pagination import paginate
from app.auth.dependencies import get_current_user
from fastapi import HTTPException
from fastapi import UploadFile, File
import os, uuid
from fastapi.responses import RedirectResponse



router = APIRouter(prefix="/agents", tags=["Agents"])
UPLOAD_DIR = "app/static/uploads/agents"
os.makedirs(UPLOAD_DIR, exist_ok=True)
# -------------------------------------------------
# Helper: render agent form
# -------------------------------------------------
def render_form(
    request: Request,
    *,
    agent=None,
    form=None,
    errors=None,
    is_my_profile: bool = False,  
    status_code=200,
):
    return templates.TemplateResponse(
        "agents/form.html",
        {
            "request": request,
            "agent": agent,
            "form": form or {"company_name": "", "email": "", "phone": ""},
            "errors": errors or {},
            "is_my_profile": is_my_profile
        },
        status_code=status_code
    )

# -------------------------------------------------
# List Agents
# -------------------------------------------------
@router.get("/", response_class=HTMLResponse, name="agent_list")
def list_agents(
    request: Request,
    search: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
    _=Depends(admin_only)
):
    query = db.query(Agent).filter(Agent.is_deleted == False).order_by(Agent.id.desc())

    if search:
        query = query.filter(
            or_(
                Agent.company_name.ilike(f"%{search}%"),
                Agent.phone.ilike(f"%{search}%"),
                Agent.user.has(User.email.ilike(f"%{search}%")),
                Agent.status.ilike(f"%{search}%")
            )
        )

    pagination = paginate(query, page)

    template = (
        "agents/_table.html"
        if request.headers.get("X-Requested-With") == "XMLHttpRequest"
        else "agents/list.html"
    )

    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "agents": pagination["items"],
            "pagination": pagination,
            "search": search
        }
    )



# -------------------------------------------------
# Create Page
# -------------------------------------------------
@router.get("/create", response_class=HTMLResponse, name="agent_create_page")
def create_page(request: Request, _=Depends(admin_only)):
    return render_form(request)

# -------------------------------------------------
# Create Agent
# -------------------------------------------------
@router.post("/create", name="agent_create")
def create_agent(
    request: Request,
    company_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(),
    db: Session = Depends(get_db),
    _=Depends(admin_only)
):
    # Always define this first
    form_data = {
        "company_name": company_name,
        "email": email,
        "phone": phone
    }

    # Pydantic validation
    try:
        validated = AgentCreate(
            company_name=company_name,
            email=email,
            phone=phone
        )
    except ValidationError as e:
        errors = {err["loc"][0]: err["msg"] for err in e.errors()}
        return render_form(
            request,
            form=form_data,
            errors=errors,
            status_code=400
        )

    # Email unique check
    if db.query(User).filter(User.email == validated.email).first():
        return render_form(
            request,
            form=form_data,
            errors={"email": "Email already exists"},
            status_code=400
        )

    # Create user
    user = User(
        email=validated.email,
        password_hash=hash_password("12345678"),
        role="agent",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create agent
    agent = Agent(
        user_id=user.id,
        company_name=validated.company_name,
        phone=validated.phone,
        status="active",
        is_deleted=False
    )
    db.add(agent)
    db.commit()

    return RedirectResponse(url=f"{request.url_for('agent_list')}?success=Agent created successfully", status_code=303)


# -------------------------------------------------
# Edit Page
# -------------------------------------------------
@router.get("/{agent_id}/edit", response_class=HTMLResponse, name="agent_edit_page")
def edit_page(
    agent_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(admin_only)
):
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.is_deleted == False
    ).first()

    return render_form(
        request,
        agent=agent,
        is_my_profile=False,
        form={
            "company_name": agent.company_name,
            "email": agent.user.email,
            "phone": agent.phone
        }
    )

# -------------------------------------------------
# Update Agent
# -------------------------------------------------
@router.post("/{agent_id}/edit", name="agent_update")
def update_agent(
    agent_id: int,
    request: Request,
    company_name: str = Form(...),
    phone: str = Form(),
    status: str = Form(...),
    db: Session = Depends(get_db),
    _=Depends(admin_only)
):
    try:
        form = AgentUpdate(
            company_name=company_name,
            phone=phone,
            status=status
        )
    except ValidationError as e:
        errors = {err["loc"][0]: err["msg"] for err in e.errors()}
        agent = db.query(Agent).get(agent_id)
        return render_form(request, agent=agent, form=form.dict(), errors=errors, status_code=400)

    agent = db.query(Agent).get(agent_id)
    agent.company_name = form.company_name
    agent.phone = form.phone
    agent.status = form.status

    db.commit()
    return RedirectResponse(url=f"{request.url_for('agent_list')}?success=Agent updated successfully", status_code=303)

# -------------------------------------------------
# Delete Agent (Soft)
# -------------------------------------------------
@router.post("/{agent_id}/delete", name="agent_delete")
def delete_agent(
    agent_id: int,
    request: Request,        
    db: Session = Depends(get_db),
    _=Depends(admin_only)
):
    agent = db.query(Agent).get(agent_id)
    agent.is_deleted = True
    
    db.commit()
    return RedirectResponse(url=f"{request.url_for('agent_list')}?success=Agent deleted successfully", status_code=303)

@router.get("/my-profile", response_class=HTMLResponse, name="my_profile")
def my_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.agent:
        raise HTTPException(status_code=404, detail="Agent profile not found")

    agent = current_user.agent

    return render_form(
        request,
        agent=agent,
        is_my_profile=True,   # 👈 flag
        form={
            "company_name": agent.company_name,
            "email": current_user.email,
            "phone": agent.phone,
            
        }
    )
    

@router.post("/my-profile", name="my_profile_update")
def update_my_profile(
    request: Request,

    company_name: str = Form(...),
    phone: str = Form(None),

    profile_picture: UploadFile = File(None),  # ✅ logo upload

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    agent = current_user.agent

    if not agent:
        raise HTTPException(status_code=403, detail="Agent profile not found")

    # ✅ Validate using AgentUpdate
    try:
        form = AgentUpdate(
            company_name=company_name,
            phone=phone or None,
            status=agent.status  # keep existing status
        )
    except ValidationError as e:
        errors = {err["loc"][0]: err["msg"] for err in e.errors()}
        return render_form(
            request,
            agent=agent,
            form={
                "company_name": company_name,
                "phone": phone
            },
            errors=errors,
            status_code=400
        )

    # ✅ Handle logo upload (optional)
    if profile_picture and profile_picture.filename:
        ext = profile_picture.filename.split(".")[-1].lower()
        filename = f"agent_{agent.id}_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(profile_picture.file.read())

        agent.logo = f"uploads/agents/{filename}"

    # ✅ Update fields
    agent.company_name = form.company_name
    agent.phone = form.phone

    db.commit()

    return RedirectResponse(
        url=f"{request.url_for('my_profile')}?success=Profile updated successfully",
        status_code=303
    )