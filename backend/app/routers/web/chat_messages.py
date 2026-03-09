from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi.templating import Jinja2Templates
from datetime import datetime

from app.database.session import get_db
from app.models.chat_session import ChatSession, ChatMessage
from app.models.user import User
from app.models.customer import Customer
from app.auth.dependencies import get_current_user
from app.routers.api.webhooks.whatsapp import send_whatsapp_message
from app.chatbot.states import MANUAL

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/company/messages", tags=["Chat Messages"])


def _build_session_list(db: Session, company_id: int):
    """
    Load all chat sessions for a company ordered by last_message_at desc.
    For each session also fetch the last message for preview and the customer name.
    """
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.company_id == company_id)
        .order_by(desc(ChatSession.last_message_at))
        .all()
    )

    session_data = []
    for s in sessions:
        last_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == s.id)
            .order_by(desc(ChatMessage.created_at))
            .first()
        )
        phone = s.phone

        # remove country code if present
        if phone.startswith("91") and len(phone) > 10:
            phone = phone[-10:]

        customer = (
            db.query(Customer)
            .filter(
                Customer.phone == phone,
                Customer.company_id == company_id,
                Customer.is_deleted == False
            )
            .first()
        )
        session_data.append({"session": s, "last_message": last_msg, "customer": customer})

    return session_data



# =================================================
# MESSAGES LIST (all sessions)
# =================================================
@router.get("/", response_class=HTMLResponse, name="chat_messages_list")
def chat_messages_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Renders all chat sessions for the company in a WhatsApp-style layout.
    No session is selected; the right panel shows an empty-state placeholder.
    """
    company = current_user.company
    session_data = _build_session_list(db, company.id)

    return templates.TemplateResponse(
        "chat_messages/index.html",
        {
            "request": request,
            "current_user": current_user,
            "session_data": session_data,
            "selected_session": None,
            "messages": [],
            "title": "Messages",
        },
    )


# =================================================
# CONVERSATION VIEW (selected session)
# =================================================
@router.get("/{session_id}", response_class=HTMLResponse, name="chat_conversation")
def chat_conversation(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Renders full conversation for a specific session.
    Validates the session belongs to the current company.
    """
    company = current_user.company

    selected_session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.company_id == company.id,
        )
        .first()
    )

    if not selected_session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    session_data = _build_session_list(db, company.id)


    return templates.TemplateResponse(
        "chat_messages/conversation.html",
        {
            "request": request,
            "current_user": current_user,
            "session_data": session_data,
            "selected_session": selected_session,
            "messages": messages,
            "title": f"Chat – {selected_session.phone}",
        },
    )


# =================================================
# MANUAL REPLY – send admin message to WhatsApp
# =================================================
@router.post("/{session_id}/reply", name="chat_reply")
def chat_reply(
    session_id: int,
    request: Request,
    message: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Saves an admin reply, switches the session to MANUAL mode,
    and sends the message to the user's WhatsApp number.
    """
    company = current_user.company

    selected_session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.company_id == company.id,
        )
        .first()
    )

    if not selected_session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not message or not message.strip():
        return RedirectResponse(
            url=request.url_for("chat_conversation", session_id=session_id),
            status_code=303,
        )

    # 1️⃣  Persist admin message
    db.add(ChatMessage(
        session_id=selected_session.id,
        company_id=company.id,
        sender="admin",
        message_type="text",
        message=message.strip(),
    ))

    # 2️⃣  Switch session to MANUAL mode so AI stays silent
    selected_session.state = MANUAL
    selected_session.last_message_at = datetime.utcnow()
    selected_session.updated_at = datetime.utcnow()
    db.commit()

    # 3️⃣  Send via WhatsApp API
    try:
        send_whatsapp_message(
            phone=selected_session.phone,
            text=message.strip(),
            company=company,
        )
    except Exception as e:
        print(f"[chat_reply] WhatsApp send failed: {e}")

    # 4️⃣  PRG – redirect back to conversation view
    return RedirectResponse(
        url=request.url_for("chat_conversation", session_id=session_id),
        status_code=303,
    )
