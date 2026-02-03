from app.utils.text_formate import format_package_text

def fallback():
    return (
        "Sorry, I didn’t understand that 🤖\n"
        "Our team will assist you shortly."
    )

def build_greeting(company_name: str):
    return {
        "text": (
            f"Hi! Welcome to *{company_name}* ✨\n\n"
            "How can I assist you today? Choose an option below:"
        ),
        "buttons": [
            {"id": "book_tour", "title": "Book a Tour 🏖️"},
            {"id": "ask_question", "title": "Ask About Tours?"}
        ]
    }

def build_city_selection(cities: list[str]) -> dict:
    rows = [
        {
            "id": f"CITY_{city.lower().replace(' ', '_')}",
            "title": city,
        }
        for city in cities
    ]

    return {
        "text": "📍 *Where would you like to go?*\n\nSelect a city from the list below:",
        "list_data": {
            "button": "Select City",
            "sections": [
                {
                    "title": "Available Cities",
                    "rows": rows
                }
            ]
        }
    }

def build_package_list_message(city: str, packages: list[dict]) -> dict:
    rows = [
        {
            "id": f"PKG_{p['id']}",
            "title": p["name"],
            "description": f"{p['currency']} {p['price']}"
        }
        for p in packages
    ]

    return {
        "text": f"🏷️ Available tours in *{city}*",
        "list_data": {
            "button": "View Packages",
            "sections": [
                {
                    "title": "Tour Packages",
                    "rows": rows
                }
            ]
        }
    }


def build_vehicle_option_list(options, total_pax):
    rows = []

    for idx, opt in enumerate(options, start=1):
        if len(opt["vehicles"]) == 1:
            v = opt["vehicles"][0]
            title = f"{v['vehicle_type']} – {v['seats']} seats"
            desc = f"Vehicle No: {v['vehicle_number']}"
        else:
            title = " + ".join(f"{v['vehicle_type']} ({v['seats']})" for v in opt["vehicles"])
            desc = f"Total seats: {opt['total_seats']}"

        rows.append({
            "id": f"VEH_OPT_{idx}",
            "title": title[:24],        # WhatsApp title limit
            "description": desc[:72]    # WhatsApp description limit
        })

    return {
        "text": f"Vehicle options for {total_pax} guests",
        "list_data": {
            "button": "Select Vehicle",
            "sections": [
                {
                    "title": "Available Vehicles",   # ✅ shortened to < 24 chars
                    "rows": rows
                }
            ]
        }
    }

def build_package_detail_message(package: dict) -> dict:
    return {
        "text": format_package_text(package),
        "buttons": [
            {"id": "BOOK_PKG", "title": "Book now"}
        ]
    }

def build_travel_date_buttons():
    return {
        "text": "📅 When would you like to travel?\n\n👉 Choose an option below\nor type the date (example: *13-05-2026*)",
        "buttons": [
            {"id": "DATE_TODAY", "title": "Today"},
            {"id": "DATE_TOMORROW", "title": "Tomorrow"},
        ]
    }



def build_payment_type_buttons(text: str):
    return {
        "text": text,
        "buttons": [
            {"id": "PAY_FULL", "title": "Full Payment"},
            {"id": "PAY_40", "title": "Advance Payment 40%"}
        ]
    }

BOOKING_SUMMARY_REPLY_PROMPT = """
🧾 Hey {{guest_name}}, here is your booking summary:

🎫 Package: {{package_name}}

📅 Date: {{travel_date}}
⏰ Time: {{travel_time}}

👨 Adults: {{adults}}
👧 Kids: {{kids}}

🚗 Vehicle: {{vehicle_type}}
📍 Pickup Location: {{pickup_location}}

💰 Total Amount: {{currency}} {{total_amount}}

ℹ️ Driver contact details will be shared after payment confirmation.

💳 How would you like to pay?
"""

def build_payment_mode_buttons(payable_amount: int, currency: str):
    print(payable_amount, currency, "function")
    return {
        "text": f"Amount to pay now: *{currency} {payable_amount}*\n\nSelect payment mode:",
        "buttons": [
            {"id": "PAY_CARD", "title": "Card"},
            {"id": "PAY_UPI", "title": "UPI"}
        ]
    }

    

def build_booking_confirmation_message(booking):
    driver = booking.driver

    if driver:
        driver_details = f"""

🚗 *Driver Details*
👤 *Name:* {driver.name}
📞 *Phone:* {driver.country_code}{driver.phone_number}
🚘 *Vehicle:* {driver.vehicle_type} ({driver.seats} seats) - {driver.vehicle_number}
"""
    else:
        driver_details = f"""

🚗 *Driver Details*
Driver will be assigned and shared before pickup.
"""

    travel_time = (
        f" {booking.travel_time.strftime('%I:%M %p')}"
        if booking.travel_time
        else ""
    )
    return f"""Hey {booking.customer.guest_name}, your booking is confirmed! 🎉

🧾 *Booking ID:* {booking.id}
📍 *Package:* {booking.tour_package.title}
📅 *Travel Date:* {booking.travel_date}{travel_time}
💰 *Amount Paid:* {booking.advance_amount}
{driver_details}

Thank you for booking with us 🙏
Have a great trip!
"""

BASE_REPLY_PROMPT = """
    You are a WhatsApp tour booking assistant.

    Rules:
    - Keep replies SHORT
    - Friendly and clear
    - WhatsApp style
    - Use SAME language as user
    - Ask only ONE question at a time
    - Do NOT explain internal logic
    """

NO_CITIES_REPLY_PROMPT = "Sorry, no cities are available right now."
CITY_FALLBACK_PROMPT = "Please select a city from the list.we not provide tours in this city."

FAQ_REPLY_PROMPT = """
    You are a WhatsApp tour booking assistant.

    Rules:
    - Keep replies SHORT
    - Friendly and clear
    - WhatsApp style
    - Use SAME language as user
    - Ask only ONE question at a time
    - Do NOT explain internal logic
    """

BASE_INTENT_PROMPT = """
    You are an intent & entity extraction engine for a WhatsApp tour booking chatbot.

    Your job:
    - Analyze user input
    - Return structured data only

    DO NOT:
    - Chat
    - Ask questions
    - Explain anything

    Return ONLY valid JSON.
    """

SHOW_PACKAGES_REPLY_PROMPT = """
You are a WhatsApp tour booking assistant.

Rules:
- Show available tour packages for the selected city.
- Packages will be provided in the context as a list of dictionaries with fields: id, name, price.
- Format the reply clearly and user-friendly.
- Number each package starting from 1.
- Include name and price.
- End with instruction: "Reply with the package number to select."

Example context:
{
    "city": "Dubai",
    "packages": [
        {"id": 1, "name": "Desert Safari", "price": 150},
        {"id": 2, "name": "City Tour", "price": 120}
    ]
}

Expected reply:

🏙️ Tours available in Dubai:

1. Desert Safari – AED 150
2. City Tour – AED 120

👉 Reply with the package number to select.
"""

ASK_PACKAGE_REPLY_PROMPT = "Please select a tour package."

ASK_TIME_REPLY_PROMPT = """
⏰ Please enter pickup time in format (e.g., 10:00 AM):
"""

ASK_PAX_REPLY_PROMPT = """
How many adults and kids are traveling?

Examples:
• 2 adults 1 kid
• 2,1
"""

INVALID_TIME_REPLY_PROMPT = "Invalid time format.\n Please enter time as *HH:MM AM/PM* (e.g., 10:00 AM)."

ASK_GUEST_NAME_REPLY_PROMPT = "Please enter your good name"

INVALID_PACKAGE_REPLY_PROMPT = "Please select a valid tour package."

INVALID_DATE_REPLY_PROMPT = "Please enter a valid travel date."

INVALID_PAX_REPLY_PROMPT = "Please enter a valid number of adults and kids."

ASK_PICKUP_LOCATION_REPLY_PROMPT = "📍 Please share your *pickup location* (hotel name / address)."

INVALID_PICKUP_LOCATION_REPLY_PROMPT = "Please enter a valid pickup location (hotel or address)."