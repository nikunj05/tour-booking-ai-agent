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
    buttons = [
        {"id": f"CITY_{city.lower()}", "title": city}
        for city in cities
    ]

    return {
        "text": "Where would you like to go?\nSelect a city from the options below:",
        "buttons": buttons,
    }

def build_package_list(city: str, packages: list) -> str:
    msg = f"*Available Tours in {city}*\n\n"

    for i, p in enumerate(packages, start=1):
        msg += (
            f"{i}. *{p['name']}*\n"
            f"💰 Price: AED {p['price']}\n\n"
        )

    msg += "👉 Reply with the *number* of the tour you want to book."
    return msg

def build_travel_date_buttons():
    return {
        "text": "📅 When would you like to travel?\n\n👉 Choose an option below\nor type the date (example: *13-05-2026*)",
        "buttons": [
            {"id": "DATE_TODAY", "title": "Today"},
            {"id": "DATE_TOMORROW", "title": "Tomorrow"},
        ]
    }

def build_vehicle_list(drivers):
    rows = [
        {
            "id": f"DRV_{d['id']}",
            "title": f"{d['vehicle_type']} ({d['seats']} seats)",
            # "description": f"{d['vehicle_number']} • Driver: {d['name']}"
        }
        for d in drivers
    ]

    return {
        "text": "Please select a vehicle for your trip:",
        "list_data": {
            "button": "View Vehicles",
            "sections": [
                {
                    "title": "Available Vehicles",
                    "rows": rows
                }
            ]
        }
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

ASK_CITY_REPLY_PROMPT = """
    Ask the user which city they want to travel to for the tour.

    Rules:
    - Ask only for the city name
    - Do NOT suggest or list city names
    - Keep it SHORT and clear
    - WhatsApp friendly
    - Use 1 relevant emoji
    """

ASK_TRAVEL_DATE_REPLY_PROMPT = """
    Ask for travel date.
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

ASK_DATE_REPLY_PROMPT = "Please tell me your travel date."

ASK_PAX_REPLY_PROMPT = """
How many adults and kids are traveling?

Examples:
• 2 adults 1 kid
• 2,1
"""

ASK_GUEST_NAME_REPLY_PROMPT = "Please enter your good name"

INVALID_PACKAGE_REPLY_PROMPT = "Please select a valid tour package."

INVALID_DATE_REPLY_PROMPT = "Please enter a valid travel date."

INVALID_PAX_REPLY_PROMPT = "Please enter a valid number of adults and kids."

