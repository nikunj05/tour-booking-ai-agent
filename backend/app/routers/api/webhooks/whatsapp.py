from fastapi import APIRouter, Request, Depends
import os
import requests
from app.chatbot.handler import handle_message
from app.database.session import get_db
from sqlalchemy.orm import Session
from app.models.company import Company

router = APIRouter()

VERIFY_TOKEN = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

# -------------------------------
# Webhook Verification (GET)
# -------------------------------
@router.get("/webhooks/whatsapp")
async def verify_webhook(request: Request):
    hub_mode = request.query_params.get("hub.mode")
    hub_token = request.query_params.get("hub.verify_token")
    hub_challenge = request.query_params.get("hub.challenge")

    if hub_mode == "subscribe" and hub_token == VERIFY_TOKEN:
        return int(hub_challenge)

    return "Invalid token"

# -------------------------------
# Receive WhatsApp Messages (POST)
# -------------------------------
@router.post("/webhooks/whatsapp")
async def receive_message(request: Request, db: Session = Depends(get_db)):
    data = await request.json()

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # Ignore status updates
            if "messages" not in value:
                continue

            messages = value.get("messages", [])
            metadata = value.get("metadata", {})
            whatsapp_phone_number_id = metadata.get("phone_number_id")

            if not messages:
                continue

            for msg in messages:
                msg_type = msg.get("type")
                phone = msg.get("from")
                text = ""

                if msg_type == "text":
                    text = msg.get("text", {}).get("body", "").strip()

                elif msg_type == "interactive":
                    interactive = msg.get("interactive", {})

                    # Button click
                    if interactive.get("type") == "button_reply":
                        text = interactive.get("button_reply", {}).get("id", "")

                    # List selection
                    elif interactive.get("type") == "list_reply":
                        text = interactive.get("list_reply", {}).get("id", "")

                    # ✅ Flow submission
                    elif interactive.get("type") == "flow_reply":
                        text = "__FLOW_SUBMIT__"
                        flow_data = interactive.get("flow_reply", {}).get("response", {})

                if not text:
                    continue

                company = db.query(Company).filter_by(
                    whatsapp_phone_number_id=whatsapp_phone_number_id
                ).first()

                if not company:
                    print(f"No company found for phone_number_id: {whatsapp_phone_number_id}")
                    continue

                result = handle_message(
                    phone,
                    text,
                    db,
                    company=company,
                    flow_data=flow_data if msg_type == "interactive" else None
                )
                print(result)

                if isinstance(result, dict):
                    send_whatsapp_message(
                        phone=phone,
                        text=result.get("text"),
                        buttons=result.get("buttons"),
                        list_data=result.get("list_data"),
                        flow=result.get("flow")  
                    )
                else:
                    send_whatsapp_message(
                        phone=phone,
                        text=result
                    )

    return {"status": "ok"}


def send_whatsapp_message(phone, text, buttons=None, list_data=None, flow=None):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": phone
    }

    # ✅ FLOW (highest priority)
    if flow:
        payload.update({
            "type": "interactive",
            "interactive": {
                "type": "flow",
                "body": {"text": text},
                "action": {
                    "name": "flow",
                    "parameters": {
                        "flow_id": flow["flow_id"],
                        "flow_cta": flow.get("cta", "Continue"),
                        "flow_action": "navigate",
                        "flow_action_screen": flow.get("screen", "START")
                    }
                }
            }
        })

    # ✅ LIST
    elif list_data:
        if not isinstance(list_data, dict) or "button" not in list_data or "sections" not in list_data:
            print("Invalid list_data:", list_data)
            return

        payload.update({
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": text},
                "action": list_data
            }
        })

    # ✅ BUTTONS
    elif buttons:
        if not isinstance(buttons, list) or not buttons:
            print("Invalid buttons:", buttons)
            return

        payload.update({
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": b["id"],
                                "title": b["title"]
                            }
                        } for b in buttons
                    ]
                }
            }
        })

    # ✅ TEXT
    else:
        payload.update({
            "type": "text",
            "text": {"body": text}
        })

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        print("WhatsApp API Error:", response.status_code, response.text)
