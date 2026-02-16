from app.chatbot.states import (
    BOOKING_SHOW_PACKAGE,
    BOOKING_PACKAGE_DETAIL_ACTION,
    BOOKING_ASK_TRAVEL_DATE,
)
from app.chatbot.prompts.reply import (
    build_package_detail_message,
    build_travel_date_buttons,
)

def handle_booking_package_flow(
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
    # 1️⃣ SHOW PACKAGE LIST STATE
    # ==========================================
    if state == BOOKING_SHOW_PACKAGE:

        packages = session.data.get("packages", [])

        if text and text.startswith("PKG_"):
            pkg_id = text.replace("PKG_", "")

            selected_package = next(
                (p for p in packages if str(p["id"]) == pkg_id),
                None
            )

            if not selected_package:
                reply = "Please select a valid package from the list."
                save_message(db, session, company, "bot", reply)
                return reply

            session.data["selected_package"] = selected_package

            change_state(session, BOOKING_PACKAGE_DETAIL_ACTION, db)

            reply = build_package_detail_message(selected_package)
            save_message(db, session, company, "bot", reply["text"])

            return reply

        reply = "Please select a package from the list."
        save_message(db, session, company, "bot", reply)
        return reply

    # ==========================================
    # 2️⃣ PACKAGE DETAIL ACTION STATE
    # ==========================================
    if state == BOOKING_PACKAGE_DETAIL_ACTION:

        if text == "BOOK_PKG":

            p = session.data.get("selected_package")

            if not p:
                reply = "Something went wrong. Please select the package again."
                save_message(db, session, company, "bot", reply)
                return reply

            session.data.update({
                "package_id": p["id"],
                "package_name": p["name"],
                "package_price": p["price"],
                "currency": p["currency"],
                "description": p["description"],
                "itinerary": p["itinerary"],
                "excludes": p["excludes"],
                "cover_image": build_public_image_url(p["cover_image"]),
            })

            change_state(session, BOOKING_ASK_TRAVEL_DATE, db)

            reply = build_travel_date_buttons()
            save_message(db, session, company, "bot", reply["text"])

            return reply

        reply = "You can select another package or tap *Book Now* to continue."
        save_message(db, session, company, "bot", reply)
        return reply

