import os
import json
import stripe
from fastapi import APIRouter, Request, Depends
from app.database.session import get_db
from sqlalchemy.orm import Session
from app.models.manual_booking import ManualBooking
from app.models.chat_session import ChatSession
from app.chatbot.states import BOOKING_PAYMENT_SUCCESS,BOOKING_CONFIRM_CHANGE_DETAILS
from app.routers.api.webhooks.whatsapp import send_whatsapp_message
from app.chatbot.prompts.reply import build_booking_confirmation_message
from app.models.company import Company

router = APIRouter()

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # 🔹 Step 1: Read payload to get company_id (NO verification yet)
    try:
        payload_json = json.loads(payload.decode("utf-8"))
    except Exception:
        return {"error": "Invalid JSON"}

    metadata = payload_json.get("data", {}).get("object", {}).get("metadata", {})
    company_id = metadata.get("company_id")

    if not company_id:
        return {"error": "company_id missing in metadata"}

    # 🔹 Step 2: Fetch company
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return {"error": "Company not found"}

    # 🔹 Step 3: Set Stripe secret key dynamically (✅ THIS is the fix)
    stripe.api_key = company.stripe_secret_key

    # 🔹 Step 4: Verify webhook using company webhook secret
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=company.stripe_webhook_secret
        )
    except ValueError:
        return {"error": "Invalid payload"}
    except stripe.error.SignatureVerificationError:
        return {"error": "Invalid signature"}

    # ✅ Existing logic (NO change)
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
        chat_session.state = BOOKING_DONE

        booking = db.query(ManualBooking).get(booking_id)

        phone = booking.customer.country_code + booking.customer.phone
        message = build_booking_confirmation_message(booking)

        send_whatsapp_message(
            phone=phone,
            text=message.get("text"),
            buttons=message.get("buttons"),
            company=booking.tour_package.company
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
        chat_session.state = BOOKING_WAITING_FOR_PAYMENT

        booking = db.query(ManualBooking).get(booking_id)

        phone = booking.customer.country_code + booking.customer.phone
        message = build_payment_failed_message(booking)

        send_whatsapp_message(
            phone=phone,
            text=message.get("text"),
            buttons=message.get("buttons"),
            company=booking.tour_package.company
        )

    db.commit() 