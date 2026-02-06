import os
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def create_payment_link(booking,session_id,amount, currency, description="Tour Booking"):
    """
    Creates a Stripe payment link and returns the URL
    """
    price = stripe.Price.create(
        unit_amount=int(float(amount) * 100), 
        currency=currency.lower(),
        product_data={
            "name": description
        }
    )

    payment_link = stripe.PaymentLink.create(
        line_items=[{
            "price": price.id,
            "quantity": 1
        }],
        metadata={
            "booking_id": booking.id,
            "chat_session_id": session_id,
            "phone": booking.customer.phone
        }
    )

    return payment_link.url



