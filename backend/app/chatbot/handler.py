from datetime import datetime

from app.chatbot.states import *
from app.chatbot.replies import fallback
from app.chatbot.services import filter_packages,get_active_cities

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
        ai = detect_intent_and_extract(text, INTENT_PROMPT)
        intent = ai.get("intent")

        if intent == "book_tour":
            session.state = CITY
            db.commit()

            cities = get_active_cities(db, company.id)
            if not cities:
                reply_text = "Sorry, no cities are available right now."
                save_message(db, session, company, "bot", reply_text)
                return reply_text

            response = build_city_selection(cities)

        elif intent == "ask_question":
            session.state = FAQ
            db.commit()

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
            {"id": p.id, "name": p.title, "price": p.price}
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

        
    # ---------- PACKAGE ----------
    if state == SHOW_PACKAGE:
        packages = session.data.get("packages", [])

        # ✅ Case 1: WhatsApp LIST / BUTTON reply → PKG_18
        if text.startswith("PKG_"):
            pkg_id = text.replace("PKG_", "")

            selected_package = next(
                (p for p in packages if str(p["id"]) == pkg_id),
                None
            )

        # ✅ Case 2: User typed number manually
        elif text.isdigit():
            index = int(text) - 1
            if 0 <= index < len(packages):
                selected_package = packages[index]

        # ❌ Invalid selection
        if not selected_package:
            reply = "❌ Please select a valid tour from the list."
            save_message(db, session, company, "bot", reply)
            return reply

        # ✅ Save selected package
        session.data["package_id"] = selected_package["id"]
        session.data["package_name"] = selected_package["name"]

        session.state = ASK_TRAVEL_DATE
        db.commit()

        # ✅ Ask travel date
        reply = build_travel_date_buttons()
        save_message(db, session, company, "bot", reply["text"])
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
        print("PAX")
        ai = detect_intent_and_extract(text, PAX_EXTRACT_PROMPT)
        print(ai)
        adults = ai.get("adults")
        kids = ai.get("kids")

        if adults is None or kids is None:
            reply = generate_reply(text, {}, INVALID_PAX_REPLY_PROMPT)
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["adults"] = adults
        session.data["kids"] = kids
        session.state = CONFIRM_BOOKING
        db.commit()

        reply = generate_reply(
            text,
            session.data,
            BOOKING_SUMMARY_REPLY_PROMPT
        )
        save_message(db, session, company, "bot", reply)
        return reply

    # ---------- FALLBACK ----------
    reply = fallback()
    save_message(db, session, company, "bot", reply)
    return reply
