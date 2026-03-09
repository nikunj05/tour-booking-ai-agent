from app.chatbot.flows.greeting_flow import handle_greeting_flow
from app.chatbot.session_manager import get_or_create_session
from app.chatbot.states import MANUAL
from app.chatbot.agent import run_smart_agent

def handle_message(phone: str, text: str, db, company, location=None):

    text = text.strip()

    session = get_or_create_session(phone, db, company)
    state = session.state

    # -------------------------
    # 🛑 MANUAL MODE GUARD
    # Company has taken over — AI must NOT send any reply.
    # Incoming user message is already saved by the webhook before
    # this function is called, so we simply return None here.
    # -------------------------
    if state == MANUAL:
        return None


    if not session.data.get("guest_name"):
        return handle_greeting_flow(phone, session, text, db, company)

    # -------------------------
    # 🧠 SMART AGENT INTEGRATION
    # -------------------------
    
    # Optional: Format location as text if provided
    if location and not text:
        text = f"[User sent a location: lat={location.get('latitude')}, lng={location.get('longitude')}]"

    response_text, updated_data, new_state = run_smart_agent(
        user_message=text,
        current_data=session.data,
        db=db,
        company=company
    )

    # Automatically save any context updates extracted by the AI tools
    session.data = updated_data
    
    # Update the session state if the AI decided to transition (e.g., to MANUAL)
    if new_state:
        session.state = new_state
    
    db.commit()

    return {
        "text": response_text
    }
