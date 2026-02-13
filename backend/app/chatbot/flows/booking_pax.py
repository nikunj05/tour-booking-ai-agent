from app.chatbot.states import BOOKING_ASK_PAX, BOOKING_ASK_VEHICLE
from app.services.openai_service import detect_intent_and_extract
from app.chatbot.prompts.intent import PAX_EXTRACT_PROMPT
from app.chatbot.services.vehicles import (
    get_available_drivers,
    build_vehicle_combinations
)
from app.chatbot.prompts.reply import build_vehicle_option_list


def handle_booking_pax_flow(
    session,
    text,
    db,
    company,
    save_message,
    change_state,
):
    state = session.state

    # ==========================================
    # 1️⃣ ASK PAX
    # ==========================================
    if state == BOOKING_ASK_PAX:

        ai = detect_intent_and_extract(text, PAX_EXTRACT_PROMPT)

        adults = ai.get("adults")
        kids = ai.get("kids")

        # Adults not stored yet
        if "adults" not in session.data:

            if adults is None:
                reply = "How many adults will be traveling?"
                save_message(db, session, company, "bot", reply)
                return reply

            session.data["adults"] = adults

            if kids is None:
                reply = "How many kids will be traveling?"
                save_message(db, session, company, "bot", reply)
                return reply

            session.data["kids"] = kids

        # Adults stored, waiting for kids
        elif "kids" not in session.data:

            if kids is None:
                reply = "How many kids will be traveling?"
                save_message(db, session, company, "bot", reply)
                return reply

            session.data["kids"] = kids

        # 🔥 Now both exist
        adults = session.data["adults"]
        kids = session.data["kids"]
        total_pax = adults + kids

        session.data.update({
            "total_pax": total_pax,
            "total_amount": round(
                total_pax * session.data["package_price"], 2
            ),
        })

        # ==========================================
        # VEHICLE LOGIC
        # ==========================================
        drivers = get_available_drivers(
            db=db,
            company_id=company.id,
            package_id=session.data["package_id"],
            travel_date=session.data["travel_date"],
        )

        if not drivers:
            reply = "No vehicles available for your selected travel date."
            save_message(db, session, company, "bot", reply)
            return reply

        options = build_vehicle_combinations(drivers, total_pax)

        if not options:
            reply = "No suitable vehicle combinations available for your group size."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["options"] = options
        change_state(session, BOOKING_ASK_VEHICLE, db)

        reply = build_vehicle_option_list(options, total_pax)
        save_message(db, session, company, "bot", reply)
        return reply
