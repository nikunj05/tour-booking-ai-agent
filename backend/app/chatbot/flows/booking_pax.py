from app.chatbot.states import BOOKING_ASK_PAX, BOOKING_ASK_VEHICLE
from app.services.openai_service import detect_intent_and_extract
from app.chatbot.prompts.intent import PAX_EXTRACT_PROMPT
from app.chatbot.services.vehicles import (
    get_available_drivers,
    build_vehicle_combinations
)
from app.chatbot.prompts.reply import build_vehicle_option_list

async def handle_booking_pax_flow(
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
                await save_message(db, session, company, "bot", reply)
                return reply

            session.data["adults"] = adults

            if kids is None:
                reply = "How many kids will be traveling?"
                await save_message(db, session, company, "bot", reply)
                return reply

            session.data["kids"] = kids

        # Adults stored, waiting for kids
        elif "kids" not in session.data:

            if kids is None:
                reply = "How many kids will be traveling?"
                await save_message(db, session, company, "bot", reply)
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
# VEHICLE LOGIC (Reusable)
# ==========================================
    return await process_vehicle_selection(
        db=db,
        company=company,
        session=session,
        total_pax=total_pax,
        save_message=save_message,
        change_state=change_state,
        next_state=BOOKING_ASK_VEHICLE,
    )


async def process_vehicle_selection(
    db,
    company,
    session,
    total_pax,
    save_message,
    change_state,
    next_state,
):
    """
    Reusable vehicle selection logic.
    Returns reply or None.
    """

    drivers = get_available_drivers(
        db=db,
        company_id=company.id,
        package_id=session.data.get("package_id"),
        travel_date=session.data.get("travel_date"),
    )

    if not drivers:
        reply = "Unfortunately, no vehicles are available for your selected travel date."
        change_state(session, BOOKING_ASK_PAX, db)
        session.data.pop("adults", None)
        session.data.pop("kids", None)
        session.data.pop("total_pax", None)
        session.data.pop("total_amount", None)
        await save_message(db, session, company, "bot", reply)
        return reply

    options = build_vehicle_combinations(drivers, total_pax)

    if not options:
        reply = f"We could not find suitable vehicle options for your group size of {total_pax}. Please adjust the number of passengers or contact support."
        session.data.pop("adults", None)
        session.data.pop("kids", None)
        session.data.pop("total_pax", None)
        session.data.pop("total_amount", None)
        change_state(session, BOOKING_ASK_PAX, db)
        await save_message(db, session, company, "bot", reply)
        return reply

    # Save options in session
    session.data["options"] = options

    # Move to next state
    change_state(session, next_state, db)

    reply = build_vehicle_option_list(options, total_pax)
    await save_message(db, session, company, "bot", reply)

    return reply