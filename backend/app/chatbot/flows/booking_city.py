from app.chatbot.states import (
    BOOKING_CITY_LIST,
    BOOKING_CITY,
    BOOKING_SHOW_PACKAGE,
)
from app.chatbot.services.packages import filter_packages
from app.chatbot.services.cities import get_active_cities
from app.services.openai_service import detect_intent_and_extract
from app.chatbot.prompts.intent import CITY_EXTRACT_PROMPT
from app.chatbot.prompts.reply import (
    build_city_selection,
    build_package_list_message,
)

def handle_booking_city_flow(
    session,
    text,
    db,
    company,
    save_message,
    change_state,
    build_public_image_url,
):
    state = session.state

    # ==========================================
    # 1️⃣ CITY LIST STATE
    # ==========================================
    if state == BOOKING_CITY_LIST:

        cities = get_active_cities(db, company.id)

        if not cities:
            reply_text = "Sorry, no cities are available right now."
            save_message(db, session, company, "bot", reply_text)
            return reply_text

        response = build_city_selection(cities)

        change_state(session, BOOKING_CITY, db)
        save_message(db, session, company, "bot", response["text"])

        return response

    # ==========================================
    # 2️⃣ CITY SELECTION STATE
    # ==========================================
    if state == BOOKING_CITY:

        # ---- Extract City ----
        if text and text.startswith("CITY_"):
            city = text.replace("CITY_", "")
        else:
            ai_result = detect_intent_and_extract(text, CITY_EXTRACT_PROMPT)
            city = ai_result.get("city")

        city = (city or "").strip().title()

        if not city:
            reply = "Please select a valid city from the list."
            save_message(db, session, company, "bot", reply)
            return reply

        return fetch_and_send_packages(
            session=session,
            db=db,
            company=company,
            city=city,
            save_message=save_message,
            change_state=change_state,
            build_public_image_url=build_public_image_url,
        )

# ======================================================
# 🔹 Helper: Fetch Packages & Send List
# ======================================================
def fetch_and_send_packages(
    session,
    db,
    company,
    city,
    save_message,
    change_state,
    build_public_image_url,
):
    packages = filter_packages(db, company.id, city)

    if not packages:
        reply = (
            f"Currently, there are no packages available for {city}. "
            "Kindly select a different city to continue."
        )
        save_message(db, session, company, "bot", reply)
        return reply

    session.data["city"] = city
    session.data["packages"] = [
        {
            "id": p.id,
            "name": p.title,
            "price": float(p.price),
            "currency": p.currency,
            "description": p.description,
            "itinerary": p.itinerary,
            "excludes": p.excludes,
            "cover_image": build_public_image_url(p.cover_image),
        }
        for p in packages
    ]

    change_state(session, BOOKING_SHOW_PACKAGE, db)

    response = build_package_list_message(city, session.data["packages"])
    save_message(db, session, company, "bot", response["text"])

    return response
