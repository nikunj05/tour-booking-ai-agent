from openai import OpenAI
import os, json
from app.chatbot.prompts.intent import BASE_INTENT_PROMPT
from app.chatbot.prompts.reply import BASE_REPLY_PROMPT

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def detect_intent_and_extract(
    text: str,
    extra_prompt: str
) -> dict:
    if not extra_prompt:
        raise ValueError("extra_prompt is required")

    system_prompt = BASE_INTENT_PROMPT + "\n" + extra_prompt

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        temperature=0
    )

    return json.loads(response.choices[0].message.content)

# ---------- REPLY ----------
def generate_reply(
    user_text: str,
    context: dict,
    extra_prompt: str = ""
) -> str:
    system_prompt = BASE_REPLY_PROMPT + "\n" + extra_prompt

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""
                    User message: {user_text}
                    Context:
                    {context}
                    """
            }
        ],
        temperature=0.8
    )

    return response.choices[0].message.content.strip()
