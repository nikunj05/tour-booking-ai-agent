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

                    if interactive.get("type") == "button_reply":
                        text = interactive.get("button_reply", {}).get("id", "")

                    elif interactive.get("type") == "list_reply":
                        text = interactive.get("list_reply", {}).get("id", "")

                if not text:
                    continue

                company = db.query(Company).filter_by(
                    whatsapp_phone_number_id=whatsapp_phone_number_id
                ).first()

                if not company:
                    print(f"No company found for phone_number_id: {whatsapp_phone_number_id}")
                    continue

                result = handle_message(phone, text, db, company=company)
                print(result)

                if isinstance(result, dict):
                    send_whatsapp_message(
                        phone=phone,
                        text=result.get("text"),
                        buttons=result.get("buttons"),
                        list_data=result.get("list_data")
                    )
                else:
                    send_whatsapp_message(
                        phone=phone,
                        text=result
                    )

    return {"status": "ok"}


# -------------------------------
# Send WhatsApp Message
# -------------------------------
def send_whatsapp_message(
    phone: str,
    text: str,
    buttons: list | None = None,
    list_data: dict | None = None
):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": phone
    }

    # ---------- LIST MESSAGE ----------
    if list_data:
        payload.update({
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": text},
                "action": list_data
            }
        })

    # ---------- BUTTON MESSAGE ----------
    elif buttons:
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
                                "id": btn["id"],
                                "title": btn["title"]
                            }
                        }
                        for btn in buttons
                    ]
                }
            }
        })

    # ---------- TEXT ONLY ----------
    else:
        payload.update({
            "type": "text",
            "text": {"body": text}
        })

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()


@router.post("/test-whatsapp")
async def test_whatsapp(db: Session = Depends(get_db)):
    phone = "+91392957324"
    text = "hi"

    # Fetch a static company for testing
    company = db.query(Company).filter_by(
        id=4
    ).first()  # Get first company in DB for test

    if not company:
        return {"error": "No company found in DB. Please add one first."}

    # Call handle_message with static company
    reply = handle_message(phone, text, db, company=company)
    return {"reply": reply}