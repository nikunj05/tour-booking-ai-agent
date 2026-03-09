import json
from app.services.openai_service import run_chat_agent
from app.chatbot.states import MANUAL, BOOKING_ASK_VEHICLE
from app.models.faq_document import FAQDocument
from app.models.tour_package import TourPackage
from app.utils.embeddings import generate_embedding

SYSTEM_PROMPT = """
You are a friendly, intelligent human-like travel assistant for our tour booking company.
Your goal is to help users find information, answer their questions, and assist in booking their tours.

Rules:
- Be conversational and warm. Speak naturally.
- Keep your replies short and clear (WhatsApp style).
- Accept booking information in any order. The user doesn't have to follow strict steps.
- If they ask a general question or tour-related question, use the `search_knowledge_base` tool.
- If they give you booking details (like destination, dates, or number of people), use the `update_booking_context` tool to save it.
- Never guess the answers to their questions about our tours or policies. Always use the search tool.
- If you don't know the answer, politely offer to connect them with a human agent by using `handover_to_human`.
- If they become angry or explicitly ask for a human, use the `handover_to_human` tool.
- If you have collected enough booking info (city, travel_date, adults), guide them naturally to confirmation.

Current Booking Context (What we already know):
{context}

Proceed naturally based on the latest user message.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Searches the database for FAQs or details about specific Tour Packages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query based on the user's question, e.g., 'What is the refund policy?' or 'Tell me about Dubai tours'"
                    }
                },
                "required": ["query"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_booking_context",
            "description": "Extracts and saves booking information provided by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The destination city the user wants to visit, e.g., 'Goa', 'Dubai'."
                    },
                    "travel_date": {
                        "type": "string",
                        "description": "The date they want to travel, e.g., '2026-05-10', 'tomorrow'."
                    },
                    "adults": {
                        "type": "integer",
                        "description": "Number of adults traveling."
                    },
                    "kids": {
                        "type": "integer",
                        "description": "Number of children traveling."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handover_to_human",
            "description": "Transitions the conversation to a human support agent when the AI doesn't know the answer or the user requests human help.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Reason for handover, e.g., 'User requested human', 'Unsure how to answer'."
                    }
                },
                "required": ["reason"]
            }
        }
    }
]

def search_knowledge_base(query: str, db, company):
    query_embedding = generate_embedding(query)

    faq_results = db.query(FAQDocument).filter(
        FAQDocument.company_id == company.id,
        FAQDocument.embedding != None
    ).order_by(
        FAQDocument.embedding.l2_distance(query_embedding)
    ).limit(2).all()

    tour_results = db.query(TourPackage).filter(
        TourPackage.company_id == company.id,
        TourPackage.is_deleted == False,
        TourPackage.status == "active",
        TourPackage.embedding != None
    ).order_by(
        TourPackage.embedding.l2_distance(query_embedding)
    ).limit(2).all()

    if not faq_results and not tour_results:
        return "No relevant information found in the knowledge base."

    context_parts = []
    for faq in faq_results:
        context_parts.append(f"FAQ - Q: {faq.title} | A: {faq.content}")
    for tour in tour_results:
        context_parts.append(f"Tour Package - Title: {tour.title} | City: {tour.city} | Price: {tour.currency} {tour.price} | Desc: {tour.description}")
    
    return "\n\n".join(context_parts)

def update_booking_context(args: dict, session_data: dict):
    for key, value in args.items():
        if value is not None:
            session_data[key] = value
    return "Booking context updated successfully."

def run_smart_agent(user_message: str, current_data: dict, db, company) -> tuple[str, dict, str]:
    """
    Main entry point for intelligent chat handling.
    Returns: (reply_text, updated_session_data, new_state_if_any)
    """

    context_str = json.dumps(current_data, indent=2)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context_str)},
        {"role": "user", "content": user_message}
    ]

    new_state = None

    # Loop up to 3 times for tool chaining
    for _ in range(3):
        msg = run_chat_agent(messages=messages, tools=TOOLS)
        
        # Append AI's message (which might contain tool calls) to history
        messages.append(msg.model_dump())

        # If there are no tool calls, it's a final conversational reply
        if not msg.tool_calls:
            return msg.content, current_data, new_state

        # Execute tool calls
        for tool_call in msg.tool_calls:
            function_name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments)
            except:
                args = {}

            tool_response = ""

            if function_name == "search_knowledge_base":
                tool_response = search_knowledge_base(args.get("query", ""), db, company)
                
            elif function_name == "update_booking_context":
                tool_response = update_booking_context(args, current_data)

            elif function_name == "handover_to_human":
                new_state = MANUAL
                tool_response = "Handover triggered."

            # Append the tool's result back to the conversation
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": str(tool_response)
            })

            # If manual handover occurred, break out immediately
            if new_state == MANUAL:
                break
        
        if new_state == MANUAL:
            break

    # If it broke out early or reached max loops without a final message, prompt one last time without tools
    if new_state == MANUAL:
        return "I'll connect you with someone from our team right away to help you with this.", current_data, new_state

    # Fallback response
    final_msg = run_chat_agent(messages=messages)
    return final_msg.content, current_data, new_state
