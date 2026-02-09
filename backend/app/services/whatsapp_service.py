import requests
import os
import logging
import re
from html import unescape

logger = logging.getLogger(__name__)

WHATSAPP_API_URL = "https://graph.facebook.com/v17.0"

def send_whatsapp_booking_confirmation(phone_number: str, booking):

    company = booking.tour_package.company
    access_token = company.whatsapp_access_token
    phone_number_id = company.whatsapp_phone_number_id

    if not access_token or not phone_number_id:
        raise ValueError("WhatsApp credentials missing")

    url = f"{WHATSAPP_API_URL}/{phone_number_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": "booking_confirmed_new", 
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": booking.customer.guest_name},                        # {{1}}
                        {"type": "text", "text": booking.tour_package.title},                 # {{2}}
                        {"type": "text", "text": str(booking.travel_date)},                   # {{3}}
                        {"type": "text", "text": format_time_12h(booking.travel_time) or "-"},           # {{4}}
                        {"type": "text", "text": booking.pickup_location or "-"},            # {{5}}
                        {"type": "text", "text": str(booking.adults)},                        # {{6}}
                        {"type": "text", "text": str(booking.kids)},                          # {{7}}
                        {"type": "text", "text": f"{booking.tour_package.currency} {booking.total_amount:.2f}"},
                    ],
                }
            ],
        },
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers, timeout=10)

    if response.status_code != 200:
        logger.error("WhatsApp error: %s", response.text)
        response.raise_for_status()

    logger.info("WhatsApp booking confirmation sent to %s", phone_number)
    return response.json()

from datetime import time

def format_time_12h(t):
    if not t:
        return "-"
    return t.strftime("%I:%M %p")

def send_whatsapp_driver_details(phone_number: str, booking):

    company = booking.tour_package.company
    access_token = company.whatsapp_access_token
    phone_number_id = company.whatsapp_phone_number_id

    url = f"{WHATSAPP_API_URL}/{phone_number_id}/messages"

    drivers_text = "-"
    if booking.vehicles:
        lines = []
        for i, vehicle in enumerate(booking.vehicles, start=1):
            d = vehicle.driver
            if not d:
                continue

            lines.append(
                f"{i}. {d.name}\n"
                f"📞 {format_phone(d.country_code, d.phone_number)}\n"
                f"🚗 {d.vehicle_type} ({d.vehicle_number})\n"
                f"🪑 Seats: {vehicle.seats}"
            )

        drivers_text = "\n\n".join(lines)

    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": "tour_driver_assigned",
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": booking.customer.guest_name},     # {{1}}
                        {"type": "text", "text": "text"},  # {{2}}
                        {"type": "text", "text": "test"}, # {{3}}
                        {"type": "text", "text": "test"},                     # {{4}} ← MULTI DRIVER
                        {"type": "text", "text": "test"}, # {{5}}
                    ],
                }
            ],
        },
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()


def send_whatsapp_text(phone_number: str, message: str):
    company = booking.tour_package.company
    access_token = company.whatsapp_access_token
    phone_number_id = company.whatsapp_phone_number_id

    url = f"{WHATSAPP_API_URL}/{phone_number_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {
            "body": message
        }
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers, timeout=10)

    if response.status_code != 200:
        logger.error("WhatsApp text error: %s", response.text)
        response.raise_for_status()

    return response.json()


def format_phone(country_code: str, phone: str) -> str:
    phone = phone.replace(" ", "").replace("-", "")
    phone = phone.lstrip("0")
    return f"{country_code}{phone}"

