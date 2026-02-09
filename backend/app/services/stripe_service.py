import os
import stripe


def create_payment_link(booking,session_id,amount, currency, description="Tour Booking"):
    """
    Creates a Stripe payment link and returns the URL
    """

    company = booking.tour_package.company
    stripe.api_key = company.stripe_secret_key

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
            "company_id": company.id,
            "booking_id": booking.id,
            "chat_session_id": session_id,
            "phone": booking.customer.phone
        }
    )

    return payment_link.url



