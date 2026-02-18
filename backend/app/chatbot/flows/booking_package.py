from app.chatbot.states import (
    BOOKING_SHOW_PACKAGE,
    BOOKING_PACKAGE_DETAIL_ACTION,
    BOOKING_ASK_TRAVEL_DATE,
)
from app.chatbot.prompts.reply import (
    build_package_detail_message,
    build_travel_date_buttons,
    build_package_detail_button
)
from app.chatbot.flows.booking_city import fetch_and_send_packages

import os

BASE_URL = os.getenv("BASE_URL")

def handle_booking_package_flow(
    phone,
    session,
    text,
    db,
    company,
    save_message,
    change_state,
    build_public_image_url,
):
    from app.routers.api.webhooks.whatsapp import send_whatsapp_message
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
                city = session.data.get("city")
                return fetch_and_send_packages(
                    session=session,
                    db=db,
                    company=company,
                    city=city,
                    save_message=save_message,
                    change_state=change_state,
                    build_public_image_url=build_public_image_url,
                    heading="Please select one of the available packages from the list below."
                )

            session.data["selected_package"] = selected_package

            change_state(session, BOOKING_PACKAGE_DETAIL_ACTION, db)

            message1 = build_package_detail_message(selected_package)
            message2 = build_package_detail_button(selected_package, BASE_URL)

            send_and_save_messages(
                phone,
                company,
                session,
                db,
                save_message,
                message1,
                message2
            )

            return None

        city = session.data.get("city")
        return fetch_and_send_packages(
            session=session,
            db=db,
            company=company,
            city=city,
            save_message=save_message,
            change_state=change_state,
            build_public_image_url=build_public_image_url,
            heading="Please select one of the available packages from the list below."
        )

    # ==========================================
    # 2️⃣ PACKAGE DETAIL ACTION STATE
    # ==========================================
    if state == BOOKING_PACKAGE_DETAIL_ACTION:

        packages = session.data.get("packages", [])

        # ✅ Allow selecting another package again
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
            
            message1 = build_package_detail_message(selected_package)
            message2 = build_package_detail_button(selected_package, BASE_URL)

            send_and_save_messages(
                phone,
                company,
                session,
                db,
                save_message,
                message1,
                message2
            )

            return None


        # ✅ Book button
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

            replies = build_travel_date_buttons()
            save_message(db, session, company, "bot", replies)

            return replies

        city = session.data.get("city")
        return fetch_and_send_packages(
            session=session,
            db=db,
            company=company,
            city=city,
            save_message=save_message,
            change_state=change_state,
            build_public_image_url=build_public_image_url,
            heading="You can select another package or tap *Book Now* to continue."
        )

def send_and_save_messages(phone, company, session, db, save_message_func, *messages):
    """
    Send one or multiple messages via WhatsApp and save them to DB.
    Accepts dicts like:
    {
        "text": "...",
        "buttons": [...],  # optional
        "image": "...",    # optional
    }
    """
    from app.routers.api.webhooks.whatsapp import send_whatsapp_message

    for msg in messages:
        # Save message in DB
        save_message_func(db, session, company, "bot", msg)
        
        # Send message via WhatsApp
        send_whatsapp_message(
            phone=phone,
            company=company,
            text=msg.get("text"),
            buttons=msg.get("buttons"),
            image=msg.get("image")
        )