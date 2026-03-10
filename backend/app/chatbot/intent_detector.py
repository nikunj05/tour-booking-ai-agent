from app.services.openai_service import detect_intent_and_extract
from app.chatbot.prompts.intent import INTENT_PROMPT
import json

def detect_intent(text: str, session) -> str:
    """
    Analyzes the user's message to determine if it's booking-related,
    a general question, a greeting, or unknown.
    """
    text_clean = text.strip()
    
    # 1. Quick Reply / Button ID Short-Circuit
    # WhatsApp list/button IDs are usually uppercase with underscores (e.g., CITY_DUBAI, PACKAGE_5)
    # If the text matches this pattern, it's definitely a booking flow progression step.
    if "_" in text_clean and text_clean.replace("_", "").isalnum():
        prefixes = ["CITY_", "PACKAGE_", "DATE_", "TIME_", "TRANSPORT_", "PAY_", "BOOKING_"]
        if any(text_clean.startswith(p) for p in prefixes):
            return "book_tour"

    text_lower = text_clean.lower()
    
    # 2. Keyword Heuristics for Speed & Reliability
    booking_keywords = [
        "book tour", "show packages", "package", "dubai tour",
        "desert safari", "available tours", "plan trip", "price of tour",
        "book a tour", "book"
    ]
    if any(kw in text_lower for kw in booking_keywords):
        return "book_tour"

    greeting_keywords = ["hi", "hello", "hey", "good morning", "good evening", "good afternoon"]
    if text_lower in greeting_keywords:
        return "greeting"

    # 3. Fallback to LLM for complex queries (e.g., "What is dune bashing?", "Is food included?")
    state_str = session.state if session else "default"
    data_str = json.dumps(session.data) if session else "{}"
    
    formatted_prompt = INTENT_PROMPT.replace(
        "{state}", state_str
    ).replace(
        "{data}", data_str
    ).replace(
        "{message}", text_clean
    )
    
    # detect_intent_and_extract likely expects (text, system_prompt)
    try:
        ai_result = detect_intent_and_extract(text_clean, formatted_prompt)
        return ai_result.get("intent", "unknown")
    except Exception as e:
        print(f"Error in intent detection: {e}")
        return "unknown"
