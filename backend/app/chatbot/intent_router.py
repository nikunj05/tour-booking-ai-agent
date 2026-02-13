from app.services.openai_service import detect_intent_and_extract
from app.chatbot.prompts.intent import INTENT_PROMPT


def detect_global_intent(text: str) -> str:
    text = text.strip().lower()

    ai = detect_intent_and_extract(text, INTENT_PROMPT)
    return ai.get("intent", "unknown")