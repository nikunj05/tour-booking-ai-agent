from app.chatbot.intent_router import detect_global_intent
from app.chatbot.flows.greeting_flow import handle_greeting_flow
from app.chatbot.flows.booking_flow import handle_booking_flow
from app.chatbot.flows.faq_flow import handle_faq_flow
from app.chatbot.session_manager import get_or_create_session
from app.chatbot.prompts.reply import build_greeting
from app.chatbot.states import BOOKING_GREETING

def handle_message(phone: str, text: str, db, company):

    text = text.strip()

    session = get_or_create_session(phone, db, company)
    state = session.state

    # -------------------------
    # 1️⃣ If guest name missing
    # -------------------------
    if not session.data.get("guest_name"):
        return handle_greeting_flow(phone, session, text, db, company)

    # -------------------------
    # 3️⃣ Global Intent Detection
    # -------------------------
    intent = detect_global_intent(text)
    print(intent,"intent")
    if intent == "book_tour":
        return handle_booking_flow(phone, session, text, db, company)

    # 🔥 FAQ intent
    if intent == "ask_question":
        return handle_faq_flow(text)

    # 🔥 Continue existing booking flow
    if session.state.startswith("BOOKING_"):
        return handle_booking_flow(phone, session, text, db, company)

    # 🔥 Continue FAQ flow
    if session.state == "FAQ":
        return handle_faq_flow(text)

    # -------------------------
    # 4️⃣ Default reply
    # -------------------------
    return {
        "text": f"How can I help you today? 😊"
    }
