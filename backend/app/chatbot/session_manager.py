from app.models.chat_session import ChatSession
from app.chatbot.states import BOOKING_ASK_GUEST_NAME,BOOKING_DONE,BOOKING_GREETING

def get_or_create_session(phone, db, company):
    session = (
        db.query(ChatSession)
        .filter_by(phone=phone, company_id=company.id)
        .order_by(ChatSession.updated_at.desc())
        .first()
    )

    if not session:
        session = ChatSession(phone=phone, company_id=company.id, state=BOOKING_ASK_GUEST_NAME, data={})
        db.add(session)
        db.commit()
        db.refresh(session)
    elif session.state == BOOKING_DONE:
        data = {}

        if session.data and session.data.get("guest_name"):
            data["guest_name"] = session.data["guest_name"]

        session = ChatSession(
            phone=phone,
            company_id=company.id,
            state=BOOKING_GREETING,
            data=data
        )

        print("New session created for booking done", session.data)
        db.add(session)
        db.commit()
        db.refresh(session)

    else:
        # ▶ Continue existing flow
        session = session

    return session
