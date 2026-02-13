from datetime import datetime, timedelta
import phonenumbers
import os

from app.chatbot.states import *

from app.chatbot.services.packages import filter_packages
from app.chatbot.services.cities import get_active_cities
from app.chatbot.services.create_booking import create_booking
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

    if state == BOOKING_CITY_LIST:
        cities = get_active_cities(db, company.id)
        if not cities:
            reply_text = NO_CITIES_REPLY_PROMPT
            save_message(db, session, company, "bot", reply_text)
            return reply_text
        response = build_city_selection(cities)
        change_state(session, BOOKING_CITY, db)
        save_message(db, session, company, "bot", response["text"])
        return response 

    # ---------- CITY ----------
    if state == BOOKING_CITY:
        if text.startswith("CITY_"):
            city = text.replace("CITY_", "")
        else:
            ai_result = detect_intent_and_extract(text, CITY_EXTRACT_PROMPT)
            city = ai_result.get("city")
            print(city)

        city = (city or "").strip().title()
        print(city,"city")
        if not city:
            reply = "Please select a valid city from the list."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["city"] = city
        packages = filter_packages(db, company.id, city)

        if not packages:
            reply = f"Currently, there are no packages available for {city}. Kindly select a different city to continue."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["packages"] = [
            {
                "id": p.id,
                "name": p.title,
                "price": float(p.price),
                "currency": p.currency,
                "description": p.description,
                "itinerary": p.itinerary,
                "excludes": p.excludes,
                "cover_image": build_public_image_url(p.cover_image)
            } for p in packages
        ]

        change_state(session, BOOKING_SHOW_PACKAGE, db)
        reply = build_package_list_message(city, session.data["packages"])
        save_message(db, session, company, "bot", reply["text"])
        return reply

    # ---------- PACKAGE LIST ----------
    if state == BOOKING_SHOW_PACKAGE:
        packages = session.data.get("packages", [])
        print(packages,"packages")
        if text.startswith("PKG_"):
            pkg_id = text.replace("PKG_", "")
            selected_package = next((p for p in packages if str(p["id"]) == pkg_id), None)
            print(selected_package,"selected_package")
            if not selected_package:
                reply = "Please select a valid package from the list."
                save_message(db, session, company, "bot", reply)
                return reply

            session.data["selected_package"] = selected_package
            change_state(session, BOOKING_PACKAGE_DETAIL_ACTION, db)
            print(selected_package,"selected_package 2")
            reply = build_package_detail_message(selected_package)
            save_message(db, session, company, "bot", reply["text"])
            return reply

    # ---------- PACKAGE DETAIL ACTION ----------
    if state == BOOKING_PACKAGE_DETAIL_ACTION:
        if text == "BOOK_PKG":
            p = session.data.get("selected_package")
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

    # ---------- TRAVEL DATE ----------
    if state == BOOKING_ASK_TRAVEL_DATE:
        if text == "DATE_TODAY":
            travel_date = datetime.now().strftime("%Y-%m-%d")
        elif text == "DATE_TOMORROW":
            travel_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        elif text == "DATE_CUSTOM":
            change_state(session, BOOKING_ASK_CUSTOM_TRAVEL_DATE, db)
            reply = f"🗓️ Please type your travel date in DD-MM-YYYY format. Example: *{today_example}*"
            save_message(db, session, company, "bot", reply)
            return reply
        else:
            reply = "Please choose an valid option."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["travel_date"] = travel_date
        change_state(session, BOOKING_ASK_TIME, db)
        reply = {"text": generate_reply(text, {}, ASK_TIME_REPLY_PROMPT)}
        save_message(db, session, company, "bot", reply["text"])
        return reply

    # ---------- CUSTOM TRAVEL DATE ----------
    if state == BOOKING_ASK_CUSTOM_TRAVEL_DATE:
        ai = detect_intent_and_extract(text, TRAVEL_DATE_EXTRACT_PROMPT)
        print(ai)

        travel_date = ai.get("travel_date")

        if not travel_date:
            reply = f"Invalid date format. Please enter DD-MM-YYYY. Example: *{today_example}*"
            save_message(db, session, company, "bot", reply)
            return reply

        try:
            # 🔥 Use AI extracted date (DD-MM-YYYY)
            travel_date_obj = datetime.strptime(travel_date, "%d-%m-%Y")

            if travel_date_obj.date() < datetime.now().date():
                reply = "It looks like you've entered a past date. Please select a future date to continue."
                save_message(db, session, company, "bot", reply)
                return reply

            # Store in DB format
            session.data["travel_date"] = travel_date_obj.strftime("%Y-%m-%d")

        except ValueError:
            reply = f"Invalid date format. Please enter DD-MM-YYYY. Example: *{today_example}*"
            save_message(db, session, company, "bot", reply)
            return reply

        change_state(session, BOOKING_ASK_TIME, db)
        reply = {"text": generate_reply(text, {}, ASK_TIME_REPLY_PROMPT)}
        save_message(db, session, company, "bot", reply["text"])
        return reply

    # ---------- TRAVEL TIME ----------
    if state == BOOKING_ASK_TIME:
        ai = detect_intent_and_extract(text, TRAVEL_TIME_EXTRACT_PROMPT)
        extracted_time = ai.get("time")

        if not extracted_time:
            reply = generate_reply(text, {}, INVALID_TIME_REPLY_PROMPT)
            save_message(db, session, company, "bot", reply)
            return reply

        # 🔥 Check if travel date is today
        travel_date_str = session.data.get("travel_date")  # format DD-MM-YYYY
        today_str = datetime.now().strftime("%d-%m-%Y")

        if travel_date_str == today_str:
            current_time = datetime.now().strftime("%H:%M")

            # Convert both to datetime objects for comparison
            user_time_obj = datetime.strptime(extracted_time, "%H:%M")
            current_time_obj = datetime.strptime(current_time, "%H:%M")

            if user_time_obj <= current_time_obj:
                reply = "The selected time has already passed. Please choose a future time."
                save_message(db, session, company, "bot", reply)
                return reply

        # ✅ Save valid time
        session.data["travel_time"] = extracted_time
        change_state(session, BOOKING_ASK_PAX, db)

        reply = {"text": generate_reply(text, {}, ASK_PAX_REPLY_PROMPT)}
        save_message(db, session, company, "bot", reply["text"])
        return reply

    # ---------- PAX ----------
    if state == BOOKING_ASK_PAX:
        ai = detect_intent_and_extract(text, PAX_EXTRACT_PROMPT)

        adults = ai.get("adults")
        kids = ai.get("kids")

        print(ai)

        # 🔹 If adults not yet stored
        if "adults" not in session.data:
            if adults is None:
                reply = "How many adults will be traveling?"
                save_message(db, session, company, "bot", reply)
                return reply

            session.data["adults"] = adults

            # If kids not provided yet → ask
            if kids is None:
                reply = "How many children will be traveling?"
                save_message(db, session, company, "bot", reply)
                return reply

            session.data["kids"] = kids

        # 🔹 Adults already stored, now waiting for kids
        elif "kids" not in session.data:
            if kids is None:
                reply = "How many children will be traveling?"
                save_message(db, session, company, "bot", reply)
                return reply

            session.data["kids"] = kids

        # 🔥 Now both values guaranteed
        adults = session.data["adults"]
        kids = session.data["kids"]
        total_pax = adults + kids

        session.data.update({
            "total_pax": total_pax,
            "total_amount": round(total_pax * session.data["package_price"], 2)
        })

        # 🔥 VEHICLE LOGIC STARTS HERE
        drivers = get_available_drivers(
            db=db,
            company_id=company.id,
            package_id=session.data["package_id"],
            travel_date=session.data["travel_date"]
        )

        if not drivers:
            reply = "No vehicles available for your selected travel date."
            save_message(db, session, company, "bot", reply)
            return reply

        options = build_vehicle_combinations(drivers, adults + kids)

        if not options:
            reply = "No suitable vehicle combinations available for your group size."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["options"] = options
        change_state(session, BOOKING_ASK_VEHICLE, db)

        reply = build_vehicle_option_list(options, adults + kids)
        save_message(db, session, company, "bot", reply)
        return reply

    # ---------- VEHICLE ----------
    if state == BOOKING_ASK_VEHICLE:
        if not text.startswith("VEH_OPT_"):
            reply = "Please select a vehicle option from the list."
            save_message(db, session, company, "bot", reply)
            return reply

        index = int(text.replace("VEH_OPT_", "")) - 1
        options = session.data.get("options", [])
        if index < 0 or index >= len(options):
            reply = "Invalid vehicle option selected."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["selected_vehicles"] = options[index]["vehicles"]
        change_state(session, BOOKING_ASK_PICKUP_LOCATION, db)
        reply = "📍 Please share your *pickup location* (hotel name / address)."
        save_message(db, session, company, "bot", reply)
        return reply

    # ---------- PICKUP LOCATION ----------
    if state == BOOKING_ASK_PICKUP_LOCATION:
        if len(text) < 3:
            reply = generate_reply(text, {}, INVALID_PICKUP_LOCATION_REPLY_PROMPT)
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["pickup_location"] = text
        change_state(session, BOOKING_ASK_TRANSPORT_TYPE, db)
        reply = build_transport_type_buttons()
        save_message(db, session, company, "bot", reply["text"])
        return reply

    # ---------- TRANSPORT TYPE ----------
    if state == BOOKING_ASK_TRANSPORT_TYPE:
        if text not in ["ONE_WAY", "ROUND_TRIP"]:
            reply = "Please select a valid transport type."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["transport_type"] = text
        change_state(session, BOOKING_ASK_PAYMENT, db)
        summary_text = generate_reply("", session.data, BOOKING_SUMMARY_REPLY_PROMPT)
        reply = build_payment_type_buttons(summary_text)
        save_message(db, session, company, "bot", reply["text"])
        return reply

    # ---------- PAYMENT ----------
    if state == BOOKING_ASK_PAYMENT:
        if text not in ["PAY_FULL", "PAY_40"]:
            reply = "Please select a valid payment option."
            save_message(db, session, company, "bot", reply)
            return reply

        if text == "PAY_FULL":
            payable_amount = session.data["total_amount"]
            session.data["payment_type"] = "FULL"
        else:
            payable_amount = session.data["total_amount"] * 0.40
            session.data["payment_type"] = "ADVANCE_40"

        session.data.update({
            "payable_amount": round(payable_amount, 2),
            "remaining_amount": round(session.data["total_amount"] - payable_amount, 2)
        })

        # Create booking if not exists
        booking_id = session.data.get("booking_id")
        raw_phone = phone
        country_code, national_phone = parse_whatsapp_phone(raw_phone)
        print(country_code,"cccc")
        print(national_phone,"dddddd")
        if booking_id:
            booking = db.get(ManualBooking, booking_id)
        else:
            booking = create_booking(
                db=db,
                company=company,
                guest_name=session.data["guest_name"],
                country_code=country_code,
                phone=national_phone,
                email=session.data.get("email"),
                adults=session.data.get("adults"),
                kids=session.data.get("kids"),
                pickup_location=session.data.get("pickup_location"),
                tour_package_id=session.data["package_id"],
                vehicles=session.data.get("selected_vehicles", []),
                travel_date=session.data["travel_date"],
                travel_time=session.data.get("travel_time"),
                total_amount=session.data["total_amount"],
                advance_amount=session.data["payable_amount"],
                remaining_amount=session.data["remaining_amount"],
                transport_type=session.data["transport_type"],
            )
            session.data["booking_id"] = booking.id
            db.commit()

        payment_url = create_payment_link(
            booking=booking,
            session_id=session.id,
            amount=session.data["payable_amount"],
            currency=session.data["currency"],
            description=f"{session.data['package_name']} Tour Booking"
        )
        session.data["payment_link"] = payment_url
        change_state(session, BOOKING_WAITING_FOR_PAYMENT, db)
        reply = build_payment_summary_button(booking, session)
        save_message(db, session, company, "bot", reply["text"])
        return reply

    if state == BOOKING_WAITING_FOR_PAYMENT:
        if text.startswith("RETRY_PAYMENT_"):
            booking_id = int(text.replace("RETRY_PAYMENT_", ""))
            booking = db.query(ManualBooking).get(booking_id)

            if not booking:
                reply = "Booking not found. Please contact support."
                save_message(db, session, company, "bot", reply)
                return reply

            # 🔁 Create NEW Stripe payment link
            payment_url = create_payment_link(
                booking=booking,
                session_id=session.id,
                amount=session.data.get("payable_amount", booking.advance_amount),
                currency=booking.currency,
                description=f"{booking.tour_package.title} Tour Booking"
            )

            session.data["booking_id"] = booking.id
            session.data["payment_link"] = payment_url
            db.commit()

            reply = (
                "💳 *Retry Payment*\n\n"
                f"📦 Package: *{booking.tour_package.title}*\n"
                f"💰 Payable Amount: *{booking.advance_amount} {booking.currency.upper()}*\n\n"
                f"👉 Click to pay:\n{payment_url}\n\n"
                "Once payment is done, we’ll confirm your booking ✅"
            )

            save_message(db, session, company, "bot", reply)
            return reply

    return fallback()

