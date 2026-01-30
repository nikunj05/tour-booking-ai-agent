def booking_confirmation_message(booking):
    return (
        f"Hello {booking.customer.guest_name} 👋\n\n"
        f"✅ *Your booking is confirmed!*\n\n"
        f"📍 Package: {booking.tour_package.title}\n"
        f"📅 Date: {booking.travel_date}\n"
        f"⏰ Time: {booking.travel_time}\n"
        f"🚗 Driver: {booking.driver.name if booking.driver else 'Assigned soon'}\n"
        f"📍 Pickup: {booking.pickup_location}\n\n"
        f"💰 Total: {booking.total_amount}\n"
        f"💵 Advance: {booking.advance_amount}\n"
        f"💳 Remaining: {booking.remaining_amount}\n\n"
        f"Thank you for booking with us 🙏"
    )
