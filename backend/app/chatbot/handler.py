from datetime import datetime,timedelta

from app.chatbot.states import *
from app.chatbot.services import filter_packages,get_active_cities,get_available_drivers,create_booking,build_vehicle_combinations
from app.models.chat_session import ChatSession, ChatMessage
from app.models.manual_booking import ManualBooking

from app.services.openai_service import (
    detect_intent_and_extract,
    generate_reply
)

from app.chatbot.prompts.intent import (
    INTENT_PROMPT,
    CITY_EXTRACT_PROMPT,
    TRAVEL_DATE_EXTRACT_PROMPT,
    PAX_EXTRACT_PROMPT,
    TRAVEL_TIME_EXTRACT_PROMPT
)

from app.chatbot.prompts.reply import *
from app.chatbot.prompts.reply import build_package_list_message, build_package_detail_message
import phonenumbers

# ------------------------------------------------
# Save message (user / bot)
# ------------------------------------------------
def save_message(db, session, company, sender, message):
    if isinstance(message, dict):
        text = message.get("text", "")
    else:
        text = message

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

def normalize_time(value: str):
    try:
        value = value.upper().strip()

        # 24-hour format → 12-hour
        if ":" in value and "AM" not in value and "PM" not in value:
            dt = datetime.strptime(value, "%H:%M")
            return dt.strftime("%I:%M %p").lstrip("0")

        # Already 12-hour
        dt = datetime.strptime(value, "%I:%M %p")
        return dt.strftime("%I:%M %p").lstrip("0")

    except Exception:
        return None

# ------------------------------------------------
# Main Handler
# ------------------------------------------------
def handle_message(phone: str, text: str, db, company):
    text = text.strip()

    # ---------- SESSION ----------
    session = (
        db.query(ChatSession)
        .filter_by(phone=phone, company_id=company.id)
        .order_by(ChatSession.updated_at.desc())
        .first()
    )

    if not session or session.state == BOOKING_DONE:
        session = ChatSession(
            phone=phone,
            company_id=company.id,
            state=GREETING,
            data={}
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # ✅ Make sure state is always defined
    state = session.state

    # ---------- GREETING ----------
    if state == GREETING:
        change_state(session, CHOOSE_INTENT, db)

        response = build_greeting(company.company_name)

        save_message(db, session, company, "bot", response["text"])
        return response

    # ---------- INTENT ----------
    if state == CHOOSE_INTENT:
        user_text = text.strip().lower()
        if text in ["book_tour", "ask_question"]:
            intent = user_text
        else:
            ai_result = detect_intent_and_extract(user_text, INTENT_PROMPT)
            intent = ai_result.get("intent") or ""

        if intent == "book_tour":
            change_state(session, CITY, db)
            cities = get_active_cities(db, company.id)
            if not cities:
                reply_text = NO_CITIES_REPLY_PROMPT
                save_message(db, session, company, "bot", reply_text)
                return reply_text
            response = build_city_selection(cities)

        elif intent == "ask_question":
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
        # Get city from button or AI
        if text.startswith("CITY_"):
            city = text.replace("CITY_", "")
        else:
            ai_result = detect_intent_and_extract(text, CITY_EXTRACT_PROMPT)
            city = ai_result.get("city")

        city = (city or "").strip().title()
        if not city:
            reply = CITY_FALLBACK_PROMPT
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["city"] = city

        packages = filter_packages(db, company.id, city)
        if not packages:
            reply = f"No packages available in {city}."
            save_message(db, session, company, "bot", reply)
            return reply

        # Save minimal package info
        session.data["packages"] = [
            {"id": p.id, "name": p.title, "price": float(p.price), "currency": p.currency, "itinerary": p.itinerary,"excludes": p.excludes}
            for p in packages
        ]

        change_state(session, SHOW_PACKAGE, db)

        # Build WhatsApp list using helper
        reply = build_package_list_message(city, session.data["packages"])
        save_message(db, session, company, "bot", reply["text"])
        return reply

    # ---------- PACKAGE LIST ----------
    if state in [SHOW_PACKAGE, PACKAGE_DETAIL_ACTION]:

        packages = session.data.get("packages", [])

        # User selects any package from list
        if text.startswith("PKG_"):
            pkg_id = text.replace("PKG_", "")

            selected_package = next(
                (p for p in packages if str(p["id"]) == pkg_id),
                None
            )

            if not selected_package:
                reply = "Please select a valid package from the list."
                save_message(db, session, company, "bot", reply)
                return reply

            # Save selected package
            session.data["selected_package"] = selected_package
            change_state(session, PACKAGE_DETAIL_ACTION, db)

            # Show package detail
            reply = build_package_detail_message(selected_package)
            save_message(db, session, company, "bot", reply["text"])
            return reply

    # ---------- PACKAGE DETAIL ----------
    if state == SHOW_PACKAGE_DETAIL:
        p = session.data.get("selected_package")

        if not p:
            change_state(session, SHOW_PACKAGE, db)
            reply = "Please select a package from the list."
            save_message(db, session, company, "bot", reply)
            return reply

        reply = build_package_detail_message(p)
        change_state(session, PACKAGE_DETAIL_ACTION, db)

        save_message(db, session, company, "bot", reply["text"])
        return reply

    # ---------- DETAIL ACTIONS ----------
    if state == PACKAGE_DETAIL_ACTION:

        if text == "BOOK_PKG":
            p = session.data.get("selected_package")

            session.data.update({
                "package_id": p["id"],
                "package_name": p["name"],
                "package_price": p["price"],
                "currency": p["currency"],
                "itinerary": p["itinerary"],
                "excludes": p["excludes"]
            })

            change_state(session, ASK_TRAVEL_DATE, db)

            reply = build_travel_date_buttons()
            save_message(db, session, company, "bot", reply["text"])
            return reply

        # User typed something else → stay in preview mode
        reply = "👉 You can select another package or tap *Book Now* to continue."
        save_message(db, session, company, "bot", reply)
        return reply

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

            print(travel_date)

            if not travel_date:
                reply = "Invalid date format.\nPlease enter date as *DD-MM-YYYY*"
                save_message(db, session, company, "bot", reply)
                return reply

        # ✅ Save travel date
        session.data["travel_date"] = travel_date
        change_state(session, ASK_TIME, db)

        # ✅ Ask time next
        reply = {
            "text": generate_reply(text, {}, ASK_TIME_REPLY_PROMPT)
        }
        save_message(db, session, company, "bot", reply["text"])
        return reply

    # ---------- TRAVEL TIME ----------
    if state == ASK_TIME:

        ai = detect_intent_and_extract(text, TRAVEL_TIME_EXTRACT_PROMPT)
        extracted_time = ai.get("time")

        if not extracted_time:
            reply = generate_reply(text, {}, INVALID_TIME_REPLY_PROMPT)
            save_message(db, session, company, "bot", reply)
            return reply

        # ✅ Normalize time (22:00 → 10:00 PM)
        normalized_time = normalize_time(extracted_time)

        if not normalized_time:
            reply = generate_reply(text, {}, INVALID_TIME_REPLY_PROMPT)
            save_message(db, session, company, "bot", reply)
            return reply

        # ✅ Save time
        session.data["travel_time"] = normalized_time
        session.state = ASK_PAX
        db.commit()

        # ✅ Ask pax ONCE
        reply = {
            "text": generate_reply(text, {}, ASK_PAX_REPLY_PROMPT)
        }
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

        total_pax = adults + kids
        session.data["total_pax"] = total_pax

        price_per_person = session.data["package_price"]
        session.data["total_amount"] = round(price_per_person * adults, 2)

        # fetch ALL vehicles
        drivers = get_available_drivers(
            db=db,
            company_id=company.id,
            package_id=session.data["package_id"],
            travel_date=session.data["travel_date"]
        )

        if not drivers:
            reply = "No vehicles available for your travel date."
            save_message(db, session, company, "bot", reply)
            return reply

        # build combinations
        options = build_vehicle_combinations(drivers, total_pax)

        if not options:
            reply = "No suitable vehicle combinations available."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["options"] = options
        session.state = ASK_VEHICLE
        db.commit()

        reply = build_vehicle_option_list(options, total_pax)
        save_message(db, session, company, "bot", reply)
        return reply

    if state == ASK_VEHICLE:

        if not text.startswith("VEH_OPT_"):
            reply = "Please select a vehicle option from the list."
            save_message(db, session, company, "bot", reply)
            return reply

        index = int(text.replace("VEH_OPT_", "")) - 1
        options = session.data.get("options", [])

        if index < 0 or index >= len(options):
            reply = "❌ Invalid vehicle option selected."
            save_message(db, session, company, "bot", reply)
            return reply

        selected_option = options[index]

        # save selected vehicles (single or combo)
        session.data["selected_vehicles"] = selected_option["vehicles"]

        session.state = ASK_PICKUP_LOCATION
        db.commit()

        reply = generate_reply("", {}, ASK_PICKUP_LOCATION_REPLY_PROMPT)
        save_message(db, session, company, "bot", reply)
        return reply

    # ---------- PICKUP LOCATION ----------
    if state == ASK_PICKUP_LOCATION:

        if len(text) < 3:
            reply = generate_reply(text, {}, INVALID_PICKUP_LOCATION_REPLY_PROMPT)
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
            reply = "Please select a valid payment option."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["payable_amount"] = round(payable_amount, 2)
        session.data["remaining_amount"] = round(session.data["total_amount"] - payable_amount, 2)
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
            reply = "Please select a valid payment mode."
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
            vehicles=session.data.get("selected_vehicles", []),
            travel_date=session.data["travel_date"],
            travel_time=session.data.get("travel_time"),
            total_amount=session.data["total_amount"],
            advance_amount=session.data.get("payable_amount", 0),
            remaining_amount=session.data.get("remaining_amount", 0),
        )

        session.state = CONFIRM_CHANGE_DETAILS
        session.data["booking_id"] = booking.id
        db.commit()

        return build_booking_confirmation_message(booking)

    if state == CONFIRM_CHANGE_DETAILS:
        if text == "CHANGE_DETAILS_YES":
            # User wants to update details
            session.state = DETAILS_UPDATE
            db.commit()
            return "Please provide the details you want to change."

        elif text == "CHANGE_DETAILS_NO":
            # User is happy, finalize booking
            session.state = BOOKING_DONE
            db.commit()
            return "Your booking is confirmed ✅. Thank you!"
        
        else:
            # Invalid response
            return "Please choose Yes or No."

    if state == DETAILS_UPDATE:
        # Use AI to extract the field and new value from user's message
        ai_result = detect_intent_and_extract(text, EXTRACT_UPDATE_FIELD_PROMPT)
        field = ai_result.get("field")
        new_value = ai_result.get("value")

        print(field,new_value)
        print(session.data.get("booking_id"))

        # Fetch booking and customer
        booking = db.query(ManualBooking).filter(ManualBooking.id == session.data.get("booking_id")).first()
        customer = booking.customer if booking else None

        if not booking or not customer:
            return "Sorry, I could not find your booking to update."

        # ----------------- Update Customer Table -----------------
        if field in ["guest_name", "phone", "country_code"] and new_value:
            setattr(customer, field, new_value)
            db.commit()
            session.data[field] = new_value  # update session too

            session.state = CONFIRM_CHANGE_DETAILS
            db.commit()

            reply = build_change_details_buttons()
            
            return reply

        # ----------------- Update ManualBooking Table -----------------
        elif field == "travel_time" and new_value:
            # Convert string to time if needed
            try:
                from datetime import datetime
                travel_time_obj = datetime.strptime(new_value, "%H:%M").time()
                booking.travel_time = travel_time_obj
                db.commit()
                session.data[field] = new_value
            except ValueError:
                return "Please provide travel time in HH:MM format (e.g., 15:30)."

            session.state = CONFIRM_CHANGE_DETAILS
            db.commit()

            reply = build_change_details_buttons()
            return reply
            
    # ----------------- Invalid Field -----------------
    else:
        return (
            "Sorry, I could not understand which detail you want to change. "
            "You can change guest name, phone number, country code, or travel time."
        )


    # ---------- FALLBACK ----------
    reply = fallback()
    save_message(db, session, company, "bot", reply)
    return reply
