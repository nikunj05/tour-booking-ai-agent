from app.utils.text_formate import format_package_text
import re
def fallback():
    return (
        "Sorry, I didn’t understand that 🤖\n"
        "Our team will assist you shortly."
    )

def build_greeting(company_name: str, guest_name: str | None, returning: bool = False):

    name_part = f"{guest_name}" if guest_name else "there"
    print("returning", returning)
    if returning:
        intro = f"Welcome back {name_part}! 😊"
    else:
        intro = f"Hi {name_part}! Welcome to *{company_name}* ✨"

    return {
        "text": (
            f"{intro}\n\n"
            "How can I assist you today? Choose an option below:"
        ),
        "buttons": [
            {"id": "book_tour", "title": "Book a Tour 🏖️"},
            {"id": "ask_question", "title": "Ask About Tours?"}
        ]
    }

def build_travel_datetime_confirmation_message(date: str, time: str) -> dict:
    return {
        "text": (
            f"📅 Please confirm your travel details:\n\n"
            f"Date: *{date}*\n"
            f"Time: *{time}*\n\n"
            f"Do you want to proceed?"
        ),
        "buttons": [
            {"id": "CONFIRM_YES", "title": "Yes"},
            {"id": "CONFIRM_NO", "title": "Change date and time"},
        ],
    }

def build_city_selection(cities: list[str], heading: str = "Where would you like to go?") -> dict:
    rows = [
        {
            "id": f"CITY_{city.lower().replace(' ', '_')}",
            "title": city,
        }
        for city in cities
    ]

    return {
        "text": heading,
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

def clean_html(text):
    return re.sub('<.*?>', '', text or "").strip()


def build_package_carousel_message(city, packages):
    cards = []

    for index, p in enumerate(packages[:10]):

        description = clean_html(p.get("description", ""))

        card = {
            "card_index": index,
            "type": "cta_url",   # ✅ CHANGE THIS LINE
            "header": {
                "type": "image",
                "image": {
                    "link": p["cover_image"]
                }
            },
            "body": {
                "text": f"*{p['name']}*\n\n₹ {p['price']} {p['currency']}\n\n{description[:120]}..."
            },
            "action": {
                "buttons": [
                    {
                        "type": "quick_reply",
                        "quick_reply": {
                            "id": f"PKG_{p['id']}",
                            "title": "View Details"
                        }
                    }
                ]
            }
        }

        cards.append(card)

    return {
        "text": f"Explore the most popular and highly recommended packages in {city}, crafted just for you:",
        "carousel": cards
    }

def build_package_list_message(city: str, packages: list[dict], heading: str = "") -> dict:
    rows = [
        {
            "id": f"PKG_{p['id']}",
            "title": p["name"],
            "description": f"{p['currency']} {p['price']}"
        }
        for p in packages
    ]

    return {
        "text": heading or f"🏷️ Available tours in *{city}*",
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

        # ---------- SINGLE VEHICLE ----------
        if len(opt["vehicles"]) == 1:
            v = opt["vehicles"][0]

            title = v["name"]                    
            desc = f"{v['seats']} seats • {v['vehicle_number']}"

        # ---------- COMBO VEHICLES ----------
        else:
            # Title: vehicle names only
            title = " + ".join(v["name"] for v in opt["vehicles"])

            # Description: seats breakdown
            seat_parts = [f"{v['vehicle_type']} {v['seats']}" for v in opt["vehicles"]]
            desc = f"Total {opt['total_seats']} seats • " + ", ".join(seat_parts)

        rows.append({
            "id": f"VEH_OPT_{idx}",
            "title": title[:24],       
            "description": desc[:72]     
        })

    return {
        "text": f"Vehicle options for {total_pax} guests",
        "list_data": {
            "button": "Select Vehicle",
            "sections": [
                {
                    "title": "Vehicle Options",   
                    "rows": rows
                }
            ]
        }
    }

def build_package_detail_message(package: dict) -> dict:
    message = {
        "text": format_package_text(package),
        "buttons": [
            {"id": "BOOK_PKG", "title": "Book now"}
        ]
    }

    if package.get("cover_image"):
        message["image"] = package["cover_image"]

    return message

def build_package_detail_button(package, base_url):
    detail_url = f"{base_url}/tour-packages/tours/{package['id']}"
    return {
        "text": (
            f"📄 *{package['name']}*\n\n"
            "Want to explore full itinerary, inclusions & gallery?\n\n"
            "Tap the button below to view complete details."
        ),
        "buttons": [
            {
                "type": "url",
                "title": "View Details",
                "url": detail_url,
            }
        ]
    }

def build_travel_date_buttons():
    return {
        "text": "📅 When would you like to travel?",
        "buttons": [
            {"id": "DATE_TODAY", "title": "Today"},
            {"id": "DATE_TOMORROW", "title": "Tomorrow"},
            {"id": "DATE_CUSTOM", "title": "Type Date"}
        ]
    }

def build_transport_type_buttons():
    return {
        "text": "Do you want hotel pickup only, or both pickup and drop-off?",
        "buttons": [
            {"id": "ONE_WAY", "title": "Pickup only"},
            {"id": "ROUND_TRIP", "title": "Pickup and drop-off"}
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
IMPORTANT:
- Do NOT change wording, emojis, spacing, or line breaks.
- Do NOT add or remove lines.
- Do NOT rephrase anything.
- Only replace variables inside {{ }}.

🧾 Hey {{guest_name}}, here is your booking summary:

🎫 Package: {{package_name}}

📅 Date: {{travel_date}} {{travel_time}}

👨 Adults: {{adults}}
👧 Kids: {{kids}}

🚗 Vehicles: {{vehicle_type}}
📍 Pickup Location: {{pickup_location}}

💰 Total Amount: {{currency}} {{total_amount}}

ℹ️ Driver contact details will be shared after payment confirmation.

💳 How would you like to pay?
"""

def build_booking_confirmation_message(booking):
    # Vehicles & Drivers
    vehicles = [bd.vehicle for bd in booking.vehicles_drivers if bd.vehicle]
    drivers = [bd.driver for bd in booking.vehicles_drivers if bd.driver]

    # Vehicle Details
    if vehicles:
        vehicle_lines = []
        for idx, vehicle in enumerate(vehicles, start=1):
            vehicle_lines.append(
                f"""• {vehicle.name} {vehicle.vehicle_type or 'N/A'} ({vehicle.seats or 'N/A'} seats) {vehicle.vehicle_number or 'N/A'}"""
            )
        vehicle_details = "\n".join(vehicle_lines)
    else:
        vehicle_details = "• Vehicle details will be assigned and shared before pickup."

    # Driver Details
    if drivers:
        driver_lines = []
        for idx, driver in enumerate(drivers, start=1):
            driver_lines.append(
                f"• *Driver {idx}:* {driver.name} ({driver.country_code or ''}{driver.phone_number or ''})"
            )
        driver_details = "\n".join(driver_lines)
    else:
        driver_details = "• Driver details will be assigned and shared before pickup."

    travel_time = (
        f" at {booking.travel_time.strftime('%I:%M %p')}" if booking.travel_time else ""
    )

    summary_text = f"""
Hello *{booking.customer.guest_name}*,

✅ Your booking has been *successfully confirmed*

📄 *Booking Details*
• Booking ID: {booking.id}
• Package: {booking.tour_package.title}
• Travel Date: {booking.travel_date}{travel_time}
• Pickup Location: {booking.pickup_location}

💳 *Payment Summary*
• Amount Paid: {booking.advance_amount}
• Remaining Amount: {booking.remaining_amount}

🚘 *Vehicle & Driver Information*
{vehicle_details}
{driver_details}

Thank you for choosing us.
We wish you a pleasant and memorable trip.
""".strip()

    return {
        "text": summary_text,
    }

def build_payment_failed_message(booking, session):
    text = f"""
Hello *{booking.customer.guest_name}*,

❌ *Payment Failed*

We were unable to process your payment for the booking below:

• Booking ID: {booking.id}
• Package: {booking.tour_package.title}
• Payable Amount: {booking.advance_amount}

This can happen due to a temporary issue or bank authorization failure.

Please tap the button below to retry the payment.
""".strip()

    return {
        "text": text,
        "buttons": [
            {
                "type": "url",               
                "title": "Retry Payment",
                "url": session.data["payment_link"], 
            }
        ]
    }

def build_payment_summary_button(booking, session):
    return {
        "text": (
            f"💳 Payment Summary\n\n"
            f"📦 Package: {session.data['package_name']}\n"
            f"💰 Amount to pay: {session.data['payable_amount']} {session.data['currency'].upper()}\n"
            f"Remaining amount: {session.data['remaining_amount']} {session.data['currency'].upper()}\n\n"
            "Tap the button below to pay."
        ),
        "buttons": [
            {
                "type": "url",               
                "title": "Pay Now",
                "url": session.data["payment_link"], 
            }
        ]
    }

def build_change_details_buttons():
    return {
        "text": f"Your detail has been updated ✅. Do you want to change anything else?",
        "buttons": [
            {"id": "CHANGE_DETAILS_YES", "title": "Yes"},
            {"id": "CHANGE_DETAILS_NO", "title": "No"}
        ]
    }

def build_location_request():
    return {
        "text": "📍 Please share your pickup location using the button below, or type your hotel name or full address.",
        "location_request": True
    }


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

FAQ_REPLY_PROMPT = """
    You are a WhatsApp tour booking assistant.

    Rules:
    - Keep replies SHORT
    - Friendly and clear
    - Use SAME language as user
    - Do NOT explain internal logic
    """

ASK_TIME_REPLY_PROMPT = """
⏰ Please enter your pickup time for {travel_date} 
in the format (e.g., 10:00 AM):
"""

ASK_PAX_REPLY_PROMPT = """
How many adults and kids are traveling?

Examples:
• 2 adults 1 kid
• 2,1
"""

INVALID_TIME_REPLY_PROMPT = "Invalid time format.\n Please enter time as *HH:MM AM/PM* (e.g., 10:00 AM)."

ASK_GUEST_NAME_REPLY_PROMPT = "Please enter your good name"

INVALID_PICKUP_LOCATION_REPLY_PROMPT = "Please enter a valid pickup location (hotel or address)."

GRATITUDE_REPLY_PROMPT = "You're welcome! Have a great day. Let me know if you need any further assistance."
