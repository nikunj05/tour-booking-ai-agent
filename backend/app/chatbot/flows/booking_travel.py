from datetime import datetime, timedelta

from app.chatbot.states import (
    BOOKING_ASK_TRAVEL_DATE,
    BOOKING_ASK_CUSTOM_TRAVEL_DATE,
    BOOKING_ASK_TIME,
    BOOKING_CONFIRM_DATETIME,
    BOOKING_ASK_PAX,
)

from app.services.openai_service import detect_intent_and_extract, generate_reply
from app.chatbot.prompts.intent import (
    TRAVEL_DATE_EXTRACT_PROMPT,
    TRAVEL_TIME_EXTRACT_PROMPT,
)
from app.chatbot.prompts.reply import (
    ASK_TIME_REPLY_PROMPT,
    INVALID_TIME_REPLY_PROMPT,
    ASK_PAX_REPLY_PROMPT,
    build_travel_datetime_confirmation_message
)

def handle_booking_travel_flow(
    session,
    text,
    db,
    company,
    save_message,
    change_state,
):
    state = session.state
    today_example = datetime.now().strftime("%d-%m-%Y")

    # =====================================================
    # 1️⃣ ASK TRAVEL DATE
    # =====================================================
    if state == BOOKING_ASK_TRAVEL_DATE:

        if text == "DATE_TODAY":
            travel_date = datetime.now().strftime("%Y-%m-%d")

        elif text == "DATE_TOMORROW":
            travel_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        elif text == "DATE_CUSTOM":
            change_state(session, BOOKING_ASK_CUSTOM_TRAVEL_DATE, db)

            reply = (
                f"🗓️ Please type your travel date in DD-MM-YYYY format.\n"
                f"Example: *{today_example}*"
            )
            save_message(db, session, company, "bot", reply)
            return reply

        else:
            reply = "Please choose a valid option."
            save_message(db, session, company, "bot", reply)
            return reply

        session.data["travel_date"] = travel_date
        change_state(session, BOOKING_ASK_TIME, db)

        reply = generate_reply(text, {}, ASK_TIME_REPLY_PROMPT)
        save_message(db, session, company, "bot", reply)
        return reply


    # =====================================================
    # 2️⃣ CUSTOM TRAVEL DATE
    # =====================================================
    if state == BOOKING_ASK_CUSTOM_TRAVEL_DATE:

        ai = detect_intent_and_extract(text, TRAVEL_DATE_EXTRACT_PROMPT)
        travel_date = ai.get("travel_date")

        if not travel_date:
            reply = (
                f"Invalid date format.\n"
                f"Please enter DD-MM-YYYY.\n"
                f"Example: *{today_example}*"
            )
            save_message(db, session, company, "bot", reply)
            return reply

        try:
            travel_date_obj = datetime.strptime(travel_date, "%d-%m-%Y")

            if travel_date_obj.date() < datetime.now().date():
                reply = "It looks like you've entered a past date. Please select a future date."
                save_message(db, session, company, "bot", reply)
                return reply

            session.data["travel_date"] = travel_date_obj.strftime("%Y-%m-%d")

        except ValueError:
            reply = (
                f"Invalid date format.\n"
                f"Please enter DD-MM-YYYY.\n"
                f"Example: *{today_example}*"
            )
            save_message(db, session, company, "bot", reply)
            return reply

        change_state(session, BOOKING_ASK_TIME, db)

        reply = generate_reply(text, {}, ASK_TIME_REPLY_PROMPT)
        save_message(db, session, company, "bot", reply)
        return reply


    # =====================================================
    # 3️⃣ ASK TRAVEL TIME
    # =====================================================
    if state == BOOKING_ASK_TIME:

        ai = detect_intent_and_extract(text, TRAVEL_TIME_EXTRACT_PROMPT)
        extracted_time = ai.get("time")

        if not extracted_time:
            reply = generate_reply(text, {}, INVALID_TIME_REPLY_PROMPT)
            save_message(db, session, company, "bot", reply)
            return reply

        # Validate time if date is today
        travel_date_str = session.data.get("travel_date")
        today_str = datetime.now().strftime("%Y-%m-%d")

        if travel_date_str == today_str:
            current_time = datetime.now().strftime("%H:%M")

            user_time_obj = datetime.strptime(extracted_time, "%H:%M")
            current_time_obj = datetime.strptime(current_time, "%H:%M")

            if user_time_obj <= current_time_obj:
                reply = "The selected time has already passed. Please choose a future time."
                save_message(db, session, company, "bot", reply)
                return reply

        session.data["travel_time"] = extracted_time
        change_state(session, BOOKING_CONFIRM_DATETIME, db)

        # ✅ Confirmation Message with Buttons
        formatted_date = datetime.strptime(
            session.data["travel_date"], "%Y-%m-%d"
        ).strftime("%d %B %Y")

        formatted_time = extracted_time

        reply = build_travel_datetime_confirmation_message(
            formatted_date,
            formatted_time,
        )

        save_message(db, session, company, "bot", reply)
        return reply


    # =====================================================
    # 4️⃣ CONFIRM DATE & TIME
    # =====================================================
    if state == BOOKING_CONFIRM_DATETIME:

        if text == "CONFIRM_YES":
            change_state(session, BOOKING_ASK_PAX, db)

            reply = generate_reply(text, {}, ASK_PAX_REPLY_PROMPT)
            save_message(db, session, company, "bot", reply)
            return reply

        elif text == "CONFIRM_NO":
            # Reset date & time
            session.data.pop("travel_date", None)
            session.data.pop("travel_time", None)

            change_state(session, BOOKING_ASK_CUSTOM_TRAVEL_DATE, db)

            reply = "No worries. Kindly enter your preferred travel date again."
            save_message(db, session, company, "bot", reply)
            return reply

        else:
            formatted_date = datetime.strptime(
                session.data["travel_date"], "%Y-%m-%d"
            ).strftime("%d %B %Y")

            formatted_time = session.data["travel_time"]

            reply = build_travel_datetime_confirmation_message(
                formatted_date,
                formatted_time,
            )
            save_message(db, session, company, "bot", reply)
            return reply
