from app.chatbot.states import (
    BOOKING_ASK_VEHICLE,
    BOOKING_ASK_PICKUP_LOCATION,
    BOOKING_ASK_TRANSPORT_TYPE,
    BOOKING_ASK_PAYMENT,
)

from app.chatbot.prompts.reply import (
    INVALID_PICKUP_LOCATION_REPLY_PROMPT,
    BOOKING_SUMMARY_REPLY_PROMPT,
)

from app.services.openai_service import detect_intent_and_extract, generate_reply
from app.chatbot.prompts.reply import build_transport_type_buttons, build_payment_type_buttons, build_location_request

async def handle_booking_transport_flow(
    session,
    text,
    db,
    company,
    save_message,
    change_state,
    location=None
):
    state = session.state

    # ==========================================
    # 1️⃣ VEHICLE SELECTION
    # ==========================================
    if state == BOOKING_ASK_VEHICLE:

        if not text.startswith("VEH_OPT_"):
            reply = "Please select a vehicle option from the list."
            await save_message(db, session, company, "bot", reply)
            return reply

        try:
            index = int(text.replace("VEH_OPT_", "")) - 1
        except ValueError:
            reply = "Invalid vehicle option selected."
            await save_message(db, session, company, "bot", reply)
            return reply

        options = session.data.get("options", [])

        if index < 0 or index >= len(options):
            reply = "Invalid vehicle option selected."
            await save_message(db, session, company, "bot", reply)
            return reply

        session.data["selected_vehicles"] = options[index]["vehicles"]

        change_state(session, BOOKING_ASK_PICKUP_LOCATION, db)

        reply = build_location_request()
        await save_message(db, session, company, "bot", "Asking for pickup location")

        return reply

    # ==========================================
    # 2️⃣ PICKUP LOCATION
    # ==========================================
    if state == BOOKING_ASK_PICKUP_LOCATION:

        # ✅ CASE 1: User shared live location
        if location:
            session.data["pickup_location"] = {
                "type": "coordinates",
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
                "name": location.get("name"),
                "address": location.get("address"),
            }

            change_state(session, BOOKING_ASK_TRANSPORT_TYPE, db)

            reply = build_transport_type_buttons()
            await save_message(db, session, company, "bot", reply["text"])

            return reply

        # ✅ CASE 2: User typed address manually
        if text and len(text.strip()) >= 3:

            session.data["pickup_location"] = {
                "type": "text",
                "value": text.strip()
            }

            change_state(session, BOOKING_ASK_TRANSPORT_TYPE, db)

            reply = build_transport_type_buttons()
            await save_message(db, session, company, "bot", reply["text"])

            return reply

        reply = "📍 Please share your location using the button or type your hotel name/address."
        await save_message(db, session, company, "bot", reply)
        return reply


    # ==========================================
    # 3️⃣ TRANSPORT TYPE
    # ==========================================
    if state == BOOKING_ASK_TRANSPORT_TYPE:

        if text not in ["ONE_WAY", "ROUND_TRIP"]:
            reply = "Please select a valid transport type."
            await save_message(db, session, company, "bot", reply)
            return reply

        session.data["transport_type"] = text

        change_state(session, BOOKING_ASK_PAYMENT, db)

        summary_text = generate_reply(
            "",
            session.data,
            BOOKING_SUMMARY_REPLY_PROMPT,
        )

        reply = build_payment_type_buttons(summary_text)

        await save_message(db, session, company, "bot", reply["text"])
        return reply
