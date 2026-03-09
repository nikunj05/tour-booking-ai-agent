from fastapi import APIRouter, Request, Depends
import os
import requests
from datetime import datetime
from app.chatbot.message_router import route_message
from app.database.session import get_db
from sqlalchemy.orm import Session
from app.models.company import Company
from app.models.chat_session import ChatSession, ChatMessage

router = APIRouter()

# -------------------------------
# Webhook Verification (GET)
# -------------------------------
@router.get("/webhooks/whatsapp")
async def verify_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    hub_mode = request.query_params.get("hub.mode")
    hub_token = request.query_params.get("hub.verify_token")
    hub_challenge = request.query_params.get("hub.challenge")

    if hub_mode != "subscribe" or not hub_token:
        return "Invalid request"

    company = db.query(Company).filter(
        Company.whatsapp_webhook_verify_token == hub_token,
        Company.is_deleted == False
    ).first()

    if not company:
        return "Invalid token"

    return int(hub_challenge)

# -------------------------------
# Receive WhatsApp Messages (POST)
# -------------------------------
@router.post("/webhooks/whatsapp")
async def receive_message(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

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
                location = None

                if msg_type == "text":
                    text = msg.get("text", {}).get("body", "").strip()

                elif msg_type == "interactive":
                    interactive = msg.get("interactive", {})

                    if interactive.get("type") == "button_reply":
                        text = interactive.get("button_reply", {}).get("id", "")

                    elif interactive.get("type") == "list_reply":
                        text = interactive.get("list_reply", {}).get("id", "")

                elif msg_type == "button":  
                    text = msg.get("button", {}).get("payload", "")
                    
                elif msg_type == "location":
                    location = msg.get("location")

                if not text and not location:
                    continue

                company = db.query(Company).filter_by(
                    whatsapp_phone_number_id=whatsapp_phone_number_id
                ).first()

                if not company:
                    print(f"No company found for phone_number_id: {whatsapp_phone_number_id}")
                    continue

                # -------------------------------------------------------
                # Always save the incoming user message BEFORE running the
                # chatbot handler. This ensures it appears in the dashboard
                # even in MANUAL mode (where the handler skips flow logic).
                # -------------------------------------------------------
                session = (
                    db.query(ChatSession)
                    .filter_by(phone=phone, company_id=company.id)
                    .order_by(ChatSession.updated_at.desc())
                    .first()
                )

                if session and (text or location):
                    save_text = text if text else f"[Location: lat={location.get('latitude')}, lng={location.get('longitude')}]"
                    db.add(ChatMessage(
                        session_id=session.id,
                        company_id=company.id,
                        sender="user",
                        message=save_text,
                        whatsapp_message_id=msg.get("id")
                    ))
                    session.last_message_at = datetime.utcnow()
                    db.commit()

                result = route_message(phone, text, db, company, location)
                print(result)

                # result is None when session is in MANUAL mode — do not send any AI reply
                if result is None:
                    continue

                if isinstance(result, dict):
                    send_whatsapp_message(
                        phone=phone,
                        text=result.get("text"),
                        company=company,
                        buttons=result.get("buttons"),
                        list_data=result.get("list_data"),
                        location_request=result.get("location_request", False),
                        image=result.get("image"),
                        carousel=result.get("carousel")
                    )
                else:
                    send_whatsapp_message(
                        phone=phone,
                        text=result,
                        company=company
                    )

    return {"status": "ok"}


def send_whatsapp_message(phone, text, company: None, buttons=None, list_data=None, location_request=False, image=None, carousel=None):
    url = f"https://graph.facebook.com/v23.0/{company.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {company.whatsapp_access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": phone
    }

    if list_data:
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

    elif isinstance(buttons, list) and buttons and buttons[0].get("type") == "url":
        payload.update({
            "type": "interactive",
            "interactive": {
                "type": "cta_url",
                "body": {"text": text},
                "action": {
                    "name": "cta_url",
                    "parameters": {
                        "display_text": buttons[0]["title"],
                        "url": buttons[0]["url"]
                    }
                }
            }
        })

    elif isinstance(buttons, list) and buttons:
        if len(buttons) > 3:
            buttons = buttons[:3] 
        interactive_data = {
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

        if image:
            interactive_data["header"] = {
                "type": "image",
                "image": {
                    "link": image
                }
            }

        payload.update({
            "type": "interactive",
            "interactive": interactive_data
        })
    elif location_request:
        payload.update({
            "type": "interactive",
            "interactive": {
                "type": "location_request_message",
                "body": {
                    "text": text
                },
                "action": {
                    "name": "send_location"
                }
            }
        }) 
    elif carousel:
        payload.update({
            "recipient_type": "individual",
            "type": "interactive",
            "interactive": {
                "type": "carousel",
                "body": {
                    "text": text
                },
                "action": {
                    "cards": carousel
                }
            }
        })

    else:
        payload.update({
            "type": "text",
            "text": {"body": text}
        })

    try:
        response = requests.post(url, json=payload, headers=headers)
        print("PAYLOAD:", payload)
        print("RESPONSE:", response.status_code, response.text)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("ERROR:", str(e))

