from datetime import datetime, timedelta
import phonenumbers
import os

from app.chatbot.states import *
from app.chatbot.services.vehicles import (
    get_available_drivers,
    build_vehicle_combinations
)

from app.models.chat_session import ChatMessage
from app.models.manual_booking import ManualBooking
from app.services.stripe_service import create_payment_link
from app.services.openai_service import detect_intent_and_extract, generate_reply
from app.chatbot.prompts.intent import (
    CITY_EXTRACT_PROMPT,
    TRAVEL_DATE_EXTRACT_PROMPT,
    PAX_EXTRACT_PROMPT,
    TRAVEL_TIME_EXTRACT_PROMPT,
    GUEST_NAME_EXTRACT_PROMPT
)
from app.chatbot.prompts.reply import *
from app.chatbot.prompts.reply import build_package_list_message, build_package_detail_message

from app.chatbot.flows.booking_city import handle_booking_city_flow
from app.chatbot.flows.booking_package import handle_booking_package_flow
from app.chatbot.flows.booking_travel import handle_booking_travel_flow
from app.chatbot.flows.booking_pax import handle_booking_pax_flow
from app.chatbot.flows.booking_transport import handle_booking_transport_flow
from app.chatbot.flows.booking_payment import handle_booking_payment

BASE_URL = os.getenv("BASE_URL")


# ------------------- Helpers -------------------
def save_message(db, session, company, sender, message):
    text = message.get("text") if isinstance(message, dict) else message
    db.add(ChatMessage(session_id=session.id, company_id=company.id, sender=sender, message=text))
    session.updated_at = datetime.utcnow()
    db.commit()


def parse_whatsapp_phone(raw_phone: str):
    try:
        if not raw_phone.startswith("+"):
            raw_phone = f"+{raw_phone}"
        parsed = phonenumbers.parse(raw_phone, None)
        return f"+{parsed.country_code}", str(parsed.national_number)
    except:
        return None, None


def change_state(session, state, db):
    session.state = state
    db.commit()


def build_public_image_url(image_path: str) -> str | None:
    if not image_path:
        return None
    return f"{BASE_URL.rstrip('/')}/static/{image_path.lstrip('/')}"

# ------------------- Booking Flow -------------------
def handle_booking_flow(phone,session, text: str, db, company):
    text = text.strip()
    today_example = datetime.now().strftime("%d-%m-%Y")
    state = session.state

    # -------------------------
    # 3️⃣ If guest_name exists & state is GREETING → send greeting directly
    # -------------------------
    if state == BOOKING_GREETING:
        change_state(session, BOOKING_CITY_LIST, db)
        return build_greeting(
            company.company_name,
            guest_name=session.data.get("guest_name")
        )

    if state in [BOOKING_CITY_LIST, BOOKING_CITY]:
        return handle_booking_city_flow(
            session=session,
            text=text,
            db=db,
            company=company,
            save_message=save_message,
            change_state=change_state,
            build_public_image_url=build_public_image_url,
        )

    # ---------- PACKAGE LIST ----------
    if state in [BOOKING_SHOW_PACKAGE, BOOKING_PACKAGE_DETAIL_ACTION]:
        return handle_booking_package_flow(
            session=session,
            text=text,
            db=db,
            company=company,
            save_message=save_message,
            change_state=change_state,
            build_public_image_url=build_public_image_url,
        )

    # ---------- TRAVEL DATE ----------
    if state in [BOOKING_ASK_TRAVEL_DATE, BOOKING_ASK_CUSTOM_TRAVEL_DATE, BOOKING_ASK_TIME]:
        return handle_booking_travel_flow(
            session=session,
            text=text,
            db=db,
            company=company,
            save_message=save_message,
            change_state=change_state,
        )

    if state == BOOKING_ASK_PAX:
        return handle_booking_pax_flow(
            session=session,
            text=text,
            db=db,
            company=company,
            save_message=save_message,
            change_state=change_state,
        )
    # ---------- VEHICLE ----------
    if state in [BOOKING_ASK_VEHICLE, BOOKING_ASK_PICKUP_LOCATION, BOOKING_ASK_TRANSPORT_TYPE]:
        return handle_booking_transport_flow(
            session=session,
            text=text,
            db=db,
            company=company,
            save_message=save_message,
            change_state=change_state,
        )

    # ---------- PAYMENT ----------
    if state in [BOOKING_ASK_PAYMENT, BOOKING_WAITING_FOR_PAYMENT]:
        return handle_booking_payment(
            phone=phone,
            session=session,
            text=text,
            db=db,
            company=company,
            save_message=save_message,
            change_state=change_state,
        )

    reply = fallback()
    save_message(db, session, company, "bot", reply)
    return reply
