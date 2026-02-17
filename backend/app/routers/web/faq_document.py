from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.templates import templates
from app.auth.dependencies import company_only
from app.models.faq_document import FAQDocument
from app.models.user import User
from app.utils.flash import flash_redirect
from fastapi.responses import JSONResponse
from app.utils.embeddings import generate_embedding

router = APIRouter(prefix="/faq-documents", tags=["FAQ Documents"])

# =================================================
# LIST
# =================================================
@router.get("", response_class=HTMLResponse, name="faq_list")
def faq_list(
    request: Request,
    _=Depends(company_only)
):
    return templates.TemplateResponse(
        "faqs/list.html",
        {"request": request}
    )

# =================================================
# DATATABLE
# =================================================
@router.get("/datatable", name="faq_datatable")
def faq_datatable(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(company_only)
):
    faqs = db.query(FAQDocument).filter(
        FAQDocument.company_id == current_user.company.id,
    ).all()

    data = []

    edit_icon = "/static/assets/icon/edit.svg"
    trash_icon = "/static/assets/icon/trash.svg"

    for f in faqs:
        data.append({
            "id": f.id,
            "title": f.title,
            "status": "Active" if f.is_active else "Inactive",
            "actions": f"""
                <a href="{request.url_for('faq_edit_page', faq_id=f.id)}"
                   class="btn btn-sm btn-edit">
                   <img src="{edit_icon}" class="table-icon">
                </a>

                <a href="javascript:void(0)"
                   class="confirm-faq-delete btn btn-sm btn-delete"
                   data-route="{request.url_for('faq_delete', faq_id=f.id)}">
                   <img src="{trash_icon}" class="table-icon">
                </a>
            """
        })

    return JSONResponse({"data": data})
# =================================================
# CREATE
# =================================================
@router.get("/create", response_class=HTMLResponse, name="faq_create_page")
def faq_create_page(
    request: Request,
    _=Depends(company_only)
):
    return templates.TemplateResponse(
        "faqs/form.html",
        {"request": request, "faq": None}
    )


@router.post("/create", name="faq_create")
def faq_create(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    is_active: bool = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(company_only)
):

    embedding = generate_embedding(title + " " + content)

    faq = FAQDocument(
        company_id=current_user.company.id,
        title=title,
        content=content,
        is_active=is_active,
        embedding=embedding
    )

    db.add(faq)
    db.commit()

    return flash_redirect(
        url=request.url_for("faq_list"),
        message="FAQ created successfully"
    )

# =================================================
# EDIT
# =================================================
@router.get("/{faq_id}/edit", response_class=HTMLResponse, name="faq_edit_page")
def faq_edit_page(
    faq_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(company_only)
):
    faq = db.query(FAQDocument).get(faq_id)

    return templates.TemplateResponse(
        "faqs/form.html",
        {"request": request, "faq": {"id": faq.id, "title": faq.title, "content": faq.content, "is_active": faq.is_active}}
    )


@router.post("/{faq_id}/edit", name="faq_update")
def faq_update(
    faq_id: int,
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    is_active: bool = Form(...),
    db: Session = Depends(get_db),
    _=Depends(company_only)
):
    faq = db.query(FAQDocument).get(faq_id)
    if not faq:
        return flash_redirect(request.url_for("faq_list"), "FAQ not found")

    faq.title = title
    faq.content = content
    faq.is_active = is_active
    faq.embedding = generate_embedding(title + " " + content)

    db.commit()

    return flash_redirect(
        url=request.url_for("faq_list"),
        message="FAQ updated successfully"
    )

# =================================================
# DELETE (SOFT)
# =================================================
@router.post("/{faq_id}/delete", name="faq_delete")
def faq_delete(
    faq_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(company_only)
):
    faq = db.query(FAQDocument).filter(
        FAQDocument.id == faq_id,
        FAQDocument.company_id == current_user.company.id
    ).first()

    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")

    db.delete(faq)
    db.commit()

    return {"success": True}

# =================================================
# SEMANTIC SEARCH
# =================================================
@router.get("/semantic-search")
def semantic_search(
    query: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(company_only)
):
    query_embedding = generate_embedding(query)

    results = db.execute(
        text("""
            SELECT id, title, content
            FROM faq_documents
            WHERE company_id = :company_id
            AND is_deleted = false
            ORDER BY embedding <-> :embedding
            LIMIT 3
        """),
        {
            "embedding": query_embedding,
            "company_id": current_user.company.id
        }
    )

    return results.fetchall()
