from app.chatbot.session_manager import get_or_create_session
from app.chatbot.states import MANUAL
from app.models.chat_session import ChatMessage
from datetime import datetime

from app.chatbot.intent_detector import detect_intent
from app.chatbot.ai_responder import generate_ai_response
from app.chatbot.fallback_handler import handle_fallback
from app.chatbot.booking_controller import start_or_continue_booking, reprompt_current_booking_step
from app.chatbot.flows.greeting_flow import handle_greeting_flow

def route_message(phone: str, text: str, db, company, location=None):
    """
    Central Message Router.
    Decouples intent detection, AI answering, and guided flow state machines.
    """
    text = text.strip() if text else ""
    session = get_or_create_session(phone, db, company)
    
    # 🛑 1. MANUAL GUARD
    if session.state == MANUAL:
        return None

    # 🛑 2. GREETING GUARD (Force profile creation)
    if not session.data.get("guest_name"):
        return handle_greeting_flow(phone, session, text, db, company)

    if location and not text:
        text = f"[Location: lat={location.get('latitude')}, lng={location.get('longitude')}]"

    # 🧠 3. SMART INTENT DETECTION
    intent = detect_intent(text, session)
    print(f"[CHATBOT] Intent Detected: {intent} (State: {session.state})")

    response_payload = None

    # ============== ROUTING MATRIX ==============
    flow_already_saved = False

    # A. ASK QUESTION (Vector DB & FAQ)
    if intent == "ask_question":
        ai_reply = generate_ai_response(text, db, company)
        
        if session.state.startswith("BOOKING_"):
            reprompt = reprompt_current_booking_step(phone, session, db, company)
            merged_text = f"{ai_reply}\n\n---\n{reprompt.get('text', '')}"
            
            response_payload = {
                "text": merged_text,
                "buttons": reprompt.get("buttons"),
                "list_data": reprompt.get("list_data"),
                "image": reprompt.get("image"),
                "carousel": reprompt.get("carousel")
            }
        else:
            response_payload = {"text": ai_reply}

    # B. GREETING
    elif intent == "greeting":
        response_payload = handle_greeting_flow(phone, session, text, db, company)

    # C. BOOK TOUR (or presently in the middle of structured flow)
    elif intent == "book_tour" or session.state.startswith("BOOKING_"):
        response_payload = start_or_continue_booking(phone, session, text, db, company, location)
        flow_already_saved = True

    # D. UNKNOWN / FALLBACK
    else:
        response_payload = handle_fallback(phone, session, db, company)

    # ============================================

    # 💾 Final Step: Log AI message safely for Dashboard viewing
    if response_payload and not flow_already_saved:
        text_to_save = response_payload.get("text") if isinstance(response_payload, dict) else str(response_payload)
        if text_to_save:
            db.add(ChatMessage(
                session_id=session.id,
                company_id=company.id,
                sender="bot",
                message=text_to_save
            ))
            session.last_message_at = datetime.utcnow()
            db.commit()

    return response_payload
