import os
import stripe
from fastapi import APIRouter, Request, Depends
from app.database.session import get_db
from sqlalchemy.orm import Session
from app.models.manual_booking import ManualBooking
from app.models.chat_session import ChatSession
from app.chatbot.states import PAYMENT_SUCCESS,CONFIRM_CHANGE_DETAILS
from app.routers.api.webhooks.whatsapp import send_whatsapp_message
from app.chatbot.prompts.reply import build_booking_confirmation_message

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except ValueError:
        return {"error": "Invalid payload"}
    except stripe.error.SignatureVerificationError:
        return {"error": "Invalid signature"}

    # ✅ Handle successful payment
    event_type = event["type"]
    session_obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        handle_payment_success(session_obj, db)

    elif event_type == "checkout.session.async_payment_succeeded":
        handle_payment_success(session_obj, db)

    elif event_type == "checkout.session.async_payment_failed":
        handle_payment_failure(session_obj, db)

    elif event_type == "payment_intent.payment_failed":
        handle_payment_failure(session_obj, db)

    return {"status": "ok"}

def handle_payment_success(session_obj, db):
    metadata = session_obj.get("metadata", {})

    booking_id = metadata.get("booking_id")
    chat_session_id = metadata.get("chat_session_id")

    if not booking_id or not chat_session_id:
        return

    # ✅ Update booking
    booking = db.query(ManualBooking).get(booking_id)
    if not booking:
        return

    booking.payment_status = "partial"
    booking.advance_amount = session_obj["amount_total"] / 100
    booking.payment_ref = session_obj["payment_intent"]

    # ✅ Update chat session
    chat_session = db.query(ChatSession).get(chat_session_id)
    if chat_session:
        chat_session.state = CONFIRM_CHANGE_DETAILS

        booking = db.query(ManualBooking).get(booking_id)

        phone = booking.customer.country_code + booking.customer.phone
        message = build_booking_confirmation_message(booking)

        send_whatsapp_message(
            phone=phone,
            text=message.get("text"),
            buttons=message.get("buttons"),
        )

    db.commit()

def handle_payment_failure(session_obj, db):
    metadata = session_obj.get("metadata", {})

    booking_id = metadata.get("booking_id")
    chat_session_id = metadata.get("chat_session_id")

    print("booking_id", booking_id)
    print("chat_session_id", chat_session_id)

    if not booking_id or not chat_session_id:
        return

    # ✅ Update booking
    booking = db.query(ManualBooking).get(booking_id)
    if not booking:
        return

    booking.payment_status = "failed"
    booking.paid_amount = session_obj["amount_total"] / 100
    booking.payment_ref = session_obj["payment_intent"]

    # ✅ Update chat session
    chat_session = db.query(ChatSession).get(chat_session_id)
    if chat_session:
        chat_session.state = WAITING_FOR_PAYMENT

        booking = db.query(ManualBooking).get(booking_id)

        phone = booking.customer.country_code + booking.customer.phone
        message = build_payment_failed_message(booking)

        send_whatsapp_message(
            phone=phone,
            text=message.get("text"),
            buttons=message.get("buttons"),
        )

    db.commit()