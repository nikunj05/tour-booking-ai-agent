from app.services.openai_service import generate_reply
from app.chatbot.prompts.reply import FAQ_REPLY_PROMPT

def handle_faq_flow(text):
    # Use AI to generate reply
    reply_text = generate_reply(text, {}, FAQ_REPLY_PROMPT)
    return {"text": reply_text}
