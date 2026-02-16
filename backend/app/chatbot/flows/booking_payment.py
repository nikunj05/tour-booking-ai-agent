from app.models import ManualBooking
from app.chatbot.states import (
    BOOKING_ASK_PAYMENT,
    BOOKING_WAITING_FOR_PAYMENT
)
from app.chatbot.services.create_booking import create_booking
from app.services.stripe_service import create_payment_link
from app.chatbot.prompts.reply import build_payment_summary_button
import phonenumbers

def parse_whatsapp_phone(raw_phone: str):
    try:
        if not raw_phone.startswith("+"):
            raw_phone = f"+{raw_phone}"
        parsed = phonenumbers.parse(raw_phone, None)
        return f"+{parsed.country_code}", str(parsed.national_number)
    except:
        return None, None

def handle_booking_payment(phone, session, text, db, company,save_message,change_state):
    state = session.state

    # =====================================================
    # 💳 STEP 1: USER SELECTS PAYMENT OPTION
    # =====================================================
    if state == BOOKING_ASK_PAYMENT:

        if text not in ["PAY_FULL", "PAY_40"]:
            reply = "Please select a valid payment option."
            save_message(db, session, company, "bot", reply)
            return reply

        # ---- Calculate Payable Amount ----
        if text == "PAY_FULL":
            payable_amount = session.data["total_amount"]
            session.data["payment_type"] = "FULL"
        else:
            payable_amount = session.data["total_amount"] * 0.40
            session.data["payment_type"] = "ADVANCE_40"

        session.data.update({
            "payable_amount": round(payable_amount, 2),
            "remaining_amount": round(
                session.data["total_amount"] - payable_amount, 2
            )
        })

        # ---- Create Booking If Not Exists ----
        booking_id = session.data.get("booking_id")
        phone_number=session.phone
        country_code, national_phone = parse_whatsapp_phone(phone_number)
        print(country_code, national_phone,"country_code, national_phone")
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

        # ---- Create Stripe Payment Link ----
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

    # =====================================================
    # 🔁 STEP 2: RETRY PAYMENT
    # =====================================================
    if state == BOOKING_WAITING_FOR_PAYMENT:

        if text.startswith("RETRY_PAYMENT_"):

            booking_id = int(text.replace("RETRY_PAYMENT_", ""))

            booking = db.get(ManualBooking, booking_id)

            if not booking:
                reply = "Booking not found. Please contact support."
                save_message(db, session, company, "bot", reply)
                return reply

            # ---- Create New Stripe Payment Link ----
            payment_url = create_payment_link(
                booking=booking,
                session_id=session.id,
                amount=session.data.get(
                    "payable_amount",
                    booking.advance_amount
                ),
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

    return None
