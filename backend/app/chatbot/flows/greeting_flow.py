from app.services.openai_service import detect_intent_and_extract, generate_reply
from app.chatbot.prompts.intent import GUEST_NAME_EXTRACT_PROMPT
from app.chatbot.prompts.reply import ASK_GUEST_NAME_REPLY_PROMPT
from app.chatbot.prompts.reply import build_greeting


def handle_greeting_flow(phone, session, text, db, company):

    # 1️⃣ If guest name not saved → extract it
    if not session.data.get("guest_name"):

        ai_result = detect_intent_and_extract(text, GUEST_NAME_EXTRACT_PROMPT)
        guest_name = ai_result.get("guest_name")

        if not guest_name:
            # Ask name again
            reply = generate_reply("", {}, ASK_GUEST_NAME_REPLY_PROMPT)
            return reply

        session.data["guest_name"] = guest_name
        db.commit()

    # 2️⃣ Greet user
    response = build_greeting(
        company.company_name,
        guest_name=session.data.get("guest_name")
    )

    session.state = "BOOKING_CITY_LIST"
    db.commit()

    return response
