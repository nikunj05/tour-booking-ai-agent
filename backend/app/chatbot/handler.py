from datetime import datetime, timedelta
from app.chatbot.states import *
from app.chatbot.replies import fallback
from app.chatbot.services import filter_packages,get_active_cities,get_available_drivers,create_booking
from app.utils.text_formate import format_package_text
from app.models.chat_session import ChatSession, ChatMessage

from app.services.openai_service import (
    detect_intent_and_extract,
    generate_reply
)

from app.chatbot.prompts.intent import (
    INTENT_PROMPT,
    CITY_EXTRACT_PROMPT,
    TRAVEL_DATE_EXTRACT_PROMPT,
    PAX_EXTRACT_PROMPT
)

from app.chatbot.prompts.reply import *
import phonenumbers

# ------------------------------------------------
# Save message (user / bot)
# ------------------------------------------------
def save_message(db, session, company, sender, text):
    db.add(ChatMessage(
        session_id=session.id,
        company_id=company.id,
        sender=sender,
        message=text
    ))
    session.updated_at = datetime.utcnow()
    db.commit()

def parse_whatsapp_phone(raw_phone: str):
    parsed = phonenumbers.parse(f"+{raw_phone}", None)

    country_code = f"+{parsed.country_code}"
    national_number = str(parsed.national_number)

    return country_code, national_number

def change_state(session, state, db):
    session.state = state
    db.commit()
# ------------------------------------------------
# Main Handler
# ------------------------------------------------
def handle_message(phone: str, text: str, db, company):
    text = text.strip()

    # ---------- SESSION ----------
    session = db.query(ChatSession).filter_by(
        phone=phone,
        company_id=company.id
    ).first()

    if not session:
        session = ChatSession(
            phone=phone,
            company_id=company.id,
            state=GREETING,
            data={}
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # ---------- SAVE USER MESSAGE ----------
    save_message(db, session, company, "user", text)

    # ---------- RESET ----------
    if text.lower() in ["menu", "start"]:
        session.state = GREETING
        session.data = {}
        db.commit()

    state = session.state
    company_name = getattr(company, "company_name", "our company")

    # ---------- GREETING ----------
    if state == GREETING:
        session.state = CHOOSE_INTENT
        db.commit()
        response = build_greeting(company.company_name)

        save_message(db, session, company, "bot", response["text"])
        return response

    # ---------- INTENT ----------
    if state == CHOOSE_INTENT:
        user_text = text

        if text not in ["book_tour", "ask_question"]:
            ai = detect_intent_and_extract(user_text, INTENT_PROMPT)
            intent = ai.get("intent")
        else:
            intent = text

        if intent == "book_tour":
            change_state(session, CITY, db)
            cities = get_active_cities(db, company.id)
            if not cities:
                reply_text = "Sorry, no cities are available right now."
                save_message(db, session, company, "bot", reply_text)
                return reply_text

            response = build_city_selection(cities)

        elif text == "ask_question":
            change_state(session, FAQ, db)
            response = {
                "text": generate_reply(text, {}, FAQ_REPLY_PROMPT)
            }

        else:
            response = build_greeting(company.company_name)

        save_message(db, session, company, "bot", response["text"])
        return response

    # ---------- CITY ----------
    if state == CITY:
        # Button reply comes like: CITY_DUBAI
        if text.startswith("CITY_"):
            city = text.replace("CITY_", "").title()
        else:
            ai = detect_intent_and_extract(text, CITY_EXTRACT_PROMPT)
            city = ai.get("city")

        if not city:
            reply = "❌ Please select a city from the list."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["city"] = city

        packages = filter_packages(db, company.id, city)

        if not packages:
            reply = f"❌ No packages available for {city}."
            save_message(db, session, company, "bot", reply)
            return reply

        # Save minimal package data
        session.data["packages"] = [
            {
                "id": p.id,
                "name": p.title,
                "price": float(p.price),
                "currency": p.currency,
                "description": p.description,
                "itinerary": p.itinerary,
                "excludes": p.excludes,
            }
            for p in packages
        ]

        session.state = SHOW_PACKAGE
        db.commit()

        # Build WhatsApp LIST
        rows = [
            {
                "id": f"PKG_{p['id']}",
                "title": p["name"],
                "description": f"AED {p['price']}"
            }
            for p in session.data["packages"]
        ]

        reply = {
            "text": f"🏷️ Available tours in *{city}*",
            "list_data": {
                "button": "View Packages",
                "sections": [
                    {
                        "title": "Tour Packages",
                        "rows": rows
                    }
                ]
            }
        }

        save_message(db, session, company, "bot", reply["text"])
        return reply


    # ---------- PACKAGE LIST ----------
    if state == SHOW_PACKAGE:
        packages = session.data.get("packages", [])

        if not text.startswith("PKG_"):
            reply = "❌ Please select a package from the list."
            save_message(db, session, company, "bot", reply)
            return reply

        pkg_id = text.replace("PKG_", "")
        selected_package = next(
            (p for p in packages if str(p["id"]) == pkg_id),
            None
        )

        if not selected_package:
            reply = "❌ Invalid package selection."
            save_message(db, session, company, "bot", reply)
            return reply

        # ✅ Save selected package
        session.data["selected_package"] = selected_package
        session.state = SHOW_PACKAGE_DETAIL
        db.commit()

        # 🔁 Force next response
        state = SHOW_PACKAGE_DETAIL


    # ---------- PACKAGE DETAIL ----------
    if state == SHOW_PACKAGE_DETAIL:
        p = session.data.get("selected_package")

        if not p:
            session.state = SHOW_PACKAGE
            db.commit()
            return "Please select a package."

        reply = {
            "text": format_package_text(p),
            "buttons": [
                {"id": "BOOK_PKG", "title": "Book now"},
                {"id": "BACK_TO_LIST", "title": "Back to list"}
            ]
        }

        session.state = PACKAGE_DETAIL_ACTION
        db.commit()

        save_message(db, session, company, "bot", reply["text"])
        return reply

    # ---------- DETAIL ACTIONS ----------
    if state == PACKAGE_DETAIL_ACTION:
        p = session.data.get("selected_package")

        if text == "BOOK_PKG":
            session.data.update({
                "package_id": p["id"],
                "package_name": p["name"],
                "package_price": p["price"],
                "currency": p["currency"]
            })

            session.state = ASK_TRAVEL_DATE
            db.commit()

            reply = build_travel_date_buttons()
            save_message(db, session, company, "bot", reply)
            return reply

        if text == "BACK_TO_LIST":
            session.state = SHOW_PACKAGE
            db.commit()

            rows = [
                {
                    "id": f"PKG_{pkg['id']}",
                    "title": pkg["name"],
                    "description": f"{pkg['currency']} {pkg['price']}"
                }
                for pkg in session.data["packages"]
            ]

            reply = {
                "text": f"🏷️ Available tours in *{session.data['city']}*",
                "list_data": {
                    "button": "View Packages",
                    "sections": [
                        {"title": "Tour Packages", "rows": rows}
                    ]
                }
            }

            save_message(db, session, company, "bot", reply["text"])
            return reply

        return "❌ Please use the buttons."

    # ---------- TRAVEL DATE ----------
    if state == ASK_TRAVEL_DATE:

        travel_date = None

        # ✅ Button clicks
        if text == "DATE_TODAY":
            travel_date = datetime.now().strftime("%Y-%m-%d")

        elif text == "DATE_TOMORROW":
            travel_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        # ✅ Manual typed date
        else:
            ai = detect_intent_and_extract(text, TRAVEL_DATE_EXTRACT_PROMPT)
            travel_date = ai.get("travel_date")

            if not travel_date:
                reply = "Invalid date format.\nPlease enter date as *DD-MM-YYYY*"
                save_message(db, session, company, "bot", reply)
                return reply

        # ✅ Save travel date
        session.data["travel_date"] = travel_date
        session.state = ASK_TIME  # Change state here
        db.commit()

        # ✅ Ask time next
        reply = {
            "text": "⏰ Please select a travel time or type in *HH:MM AM/PM* format (e.g., 10:00 AM):"
        }
        save_message(db, session, company, "bot", reply["text"])
        return reply

    # ---------- TRAVEL TIME ----------
    if state == ASK_TIME:
        import re

        time_pattern = r'^(0?[1-9]|1[0-2]):[0-5][0-9]\s?(AM|PM|am|pm)$'

        if not re.match(time_pattern, text):
            reply = (
                "❌ Invalid time format.\n"
                "Please enter time as *HH:MM AM/PM* (e.g., 10:00 AM)."
            )
            save_message(db, session, company, "bot", reply)
            return reply

        # ✅ Save time
        session.data["travel_time"] = text.upper()
        session.state = ASK_PAX
        db.commit()

        # ✅ Ask pax ONCE
        reply = "👨‍👩‍👧‍👦 How many *adults* and *kids* are traveling?"
        save_message(db, session, company, "bot", reply)
        return reply
    
    # ---------- PAX ----------
    if state == ASK_PAX:
        ai = detect_intent_and_extract(text, PAX_EXTRACT_PROMPT)
        adults = ai.get("adults")
        kids = ai.get("kids")

        if adults is None or kids is None:
            reply = generate_reply(text, {}, INVALID_PAX_REPLY_PROMPT)
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["adults"] = adults
        session.data["kids"] = kids

        # total pax
        total_pax = adults + kids
        session.data["total_pax"] = total_pax

        price_per_person = session.data["package_price"]
        total_amount = price_per_person * adults
        session.data["total_amount"] = round(total_amount, 2)

        # move to vehicle selection
        session.state = ASK_VEHICLE
        db.commit()

        # fetch available drivers
        drivers = get_available_drivers(
            db=db,
            company_id=company.id,
            package_id=session.data["package_id"],
            travel_date=session.data["travel_date"],
            total_pax=total_pax
        )

        if not drivers:
            reply = "❌ No vehicles available for your travel date."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["drivers"] = drivers

        reply = build_vehicle_list(drivers)
        save_message(db, session, company, "bot", reply["text"])
        return reply

    # ---------- VEHICLE ----------
    if state == ASK_VEHICLE:

        if not text.startswith("DRV_"):
            reply = "❌ Please select a vehicle from the list."
            save_message(db, session, company, "bot", reply)
            return reply

        driver_id = int(text.replace("DRV_", ""))

        selected_driver = next(
            (d for d in session.data["drivers"] if d["id"] == driver_id),
            None
        )

        if not selected_driver:
            reply = "❌ Invalid vehicle selection."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["driver_id"] = selected_driver["id"]
        session.data["vehicle_type"] = selected_driver["vehicle_type"]
        session.data["vehicle_number"] = selected_driver["vehicle_number"]

        # now go to summary
        session.state = ASK_PICKUP_LOCATION
        db.commit()
        
        reply = "📍 Please share your *pickup location* (hotel name / address)."

        save_message(db, session, company, "bot", reply)
        return reply

    # ---------- PICKUP LOCATION ----------
    if state == ASK_PICKUP_LOCATION:

        if len(text) < 3:
            reply = "❌ Please enter a valid pickup location (hotel or address)."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["pickup_location"] = text

        # move to payment summary
        session.state = ASK_GUEST_NAME
        db.commit()

        reply = generate_reply(
            "",
            session.data,
            ASK_GUEST_NAME_REPLY_PROMPT
        )
        
        save_message(db, session, company, "bot", reply)
        return reply

    # ---------- GUEST NAME ----------
    if state == ASK_GUEST_NAME:
        session.data["guest_name"] = text.strip()
        session.state = ASK_PAYMENT_TYPE
        db.commit()

        summary_text = generate_reply(
            "",
            session.data,
            BOOKING_SUMMARY_REPLY_PROMPT
        )

        reply = build_payment_type_buttons(summary_text)
        save_message(db, session, company, "bot", reply["text"])
        return reply


    # ---------- PAYMENT TYPE ----------
    if state == ASK_PAYMENT_TYPE:

        if text == "PAY_FULL":
            payable_amount = session.data["total_amount"]
            session.data["payment_type"] = "FULL"

        elif text == "PAY_40":
            payable_amount = session.data["total_amount"] * 0.40
            session.data["payment_type"] = "ADVANCE_40"

        else:
            reply = "❌ Please select a valid payment option."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["payable_amount"] = round(payable_amount, 2)
        session.state = ASK_PAYMENT_MODE
        db.commit()
            
        reply = build_payment_mode_buttons(
            payable_amount=session.data["payable_amount"],
            currency=session.data["currency"]
        )
        save_message(db, session, company, "bot", reply["text"])
        return reply

    if state == ASK_PAYMENT_MODE:

        if text not in ["PAY_CARD", "PAY_UPI"]:
            reply = "❌ Please select a valid payment mode."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["payment_mode"] = "CARD" if text == "PAY_CARD" else "UPI"
        # session.state = SEND_PAYMENT_LINK
        session.state = PAYMENT_SUCCESS
        db.commit()

        reply = (
            "🔗 Please complete your payment using the link below:\n\n"
            "https://example.com/dummy-payment-link\n\n"
            "⚠️ This is a test link. Live payment will be enabled soon."
        )
        save_message(db, session, company, "bot", reply)
        return reply

    if state == PAYMENT_SUCCESS:
        raw_phone = phone
        country_code, national_phone = parse_whatsapp_phone(raw_phone)

        booking = create_booking(
            db=db,
            company=company,
            guest_name=session.data["guest_name"],
            country_code=country_code,
            phone=national_phone,
            email=session.data.get("email"),
            adults=session.data.get("adults", 1),
            kids=session.data.get("kids", 0),
            pickup_location=session.data.get("pickup_location"),
            tour_package_id=session.data["package_id"],
            driver_id=session.data.get("driver_id"),
            travel_date=session.data["travel_date"],
            travel_time=session.data.get("travel_time"),
            total_amount=session.data["total_amount"],
            advance_amount=session.data.get("paid_amount", 0),
        )

        session.state = BOOKING_CONFIRMED
        db.commit()

        message = build_booking_confirmation_message(booking)
        return message

    # ---------- FALLBACK ----------
    reply = fallback()
    save_message(db, session, company, "bot", reply)
    return reply
