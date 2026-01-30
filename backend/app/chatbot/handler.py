from datetime import datetime

from app.chatbot.states import *
from app.chatbot.replies import fallback
from app.chatbot.services import filter_packages

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

        reply = generate_reply(
            user_text=text,
            context={"company_name": company_name},
            extra_prompt=GREETING_REPLY_PROMPT
        )
        save_message(db, session, company, "bot", reply)
        return reply

    # ---------- INTENT ----------
    if state == CHOOSE_INTENT:
        ai = detect_intent_and_extract(text, INTENT_PROMPT)
        intent = ai.get("intent")

        if intent == "book_tour":
            session.state = CITY
            db.commit()
            reply = generate_reply(text, {}, ASK_CITY_REPLY_PROMPT)

        elif intent == "ask_question":
            session.state = FAQ
            db.commit()
            reply = generate_reply(text, {}, FAQ_REPLY_PROMPT)

        else:
            reply = generate_reply(
                text,
                {"company_name": company_name},
                GREETING_REPLY_PROMPT
            )

        save_message(db, session, company, "bot", reply)
        return reply

    # ---------- CITY ----------
    if state == CITY:
        ai = detect_intent_and_extract(text, CITY_EXTRACT_PROMPT)
        city = ai.get("city")

        if not city:
            reply = generate_reply(text, {}, INVALID_CITY_REPLY_PROMPT)
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["city"] = city
        packages = filter_packages(db, city)

        if not packages:
            session.state = FALLBACK
            db.commit()

            reply = generate_reply(
                text,
                {"city": city},
                NO_PACKAGES_REPLY_PROMPT
            )
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["packages"] = [
            {"id": p.id, "name": p.title, "price": p.price}
            for p in packages
        ]

        session.state = SHOW_PACKAGE
        db.commit()

        reply = generate_reply(
            text,
            {"city": city, "packages": session.data["packages"]},
            SHOW_PACKAGES_REPLY_PROMPT
        )
        save_message(db, session, company, "bot", reply)
        return reply

    # ---------- PACKAGE ----------
    if state == SHOW_PACKAGE:
        packages = session.data.get("packages", [])

        if not packages:
            session.state = FALLBACK
            db.commit()
            reply = "❌ No packages available for this city."
            save_message(db, session, company, "bot", reply)
            return reply

        # If user reply is not a number, re-display list properly
        if not text.isdigit():
            msg = "🏷️ *Available Tours:* \n\n"
            for i, p in enumerate(packages, start=1):
                msg += f"{i}. {p['name']} – AED {p['price']}\n"
            msg += "\n👉 Reply with the *number* of your selected tour."
            save_message(db, session, company, "bot", msg)
            return msg

        # Validate number
        index = int(text) - 1
        if index < 0 or index >= len(packages):
            reply = "❌ Invalid number. Please select a valid tour from the list."
            save_message(db, session, company, "bot", reply)
            return reply

        # Save selected package
        p = packages[index]
        session.data["package_id"] = p["id"]
        session.data["package_name"] = p["name"]

        session.state = ASK_TRAVEL_DATE
        db.commit()

        # Ask travel date next
        reply = generate_reply(text, {}, ASK_TRAVEL_DATE_REPLY_PROMPT)
        save_message(db, session, company, "bot", reply)
        return reply

    # ---------- TRAVEL DATE ----------
    if state == ASK_TRAVEL_DATE:
        ai = detect_intent_and_extract(text, TRAVEL_DATE_EXTRACT_PROMPT)
        travel_date = ai.get("travel_date")
        print(travel_date)
        if not travel_date:
            reply = generate_reply(text, {}, INVALID_DATE_REPLY_PROMPT)
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["travel_date"] = travel_date
        session.state = ASK_PAX
        db.commit()

        reply = generate_reply(text, {}, ASK_PAX_REPLY_PROMPT)
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
