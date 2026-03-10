import json
from app.services.openai_service import run_chat_agent
from app.models.faq_document import FAQDocument
from app.models.tour_package import TourPackage
from app.utils.embeddings import generate_embedding

SYSTEM_PROMPT = """
You are a friendly, intelligent human-like travel assistant for our tour booking company.
Your ONLY goal right now is to answer the user's question accurately using the knowledge base.

Rules:
- Be conversational and warm. Speak naturally.
- Keep your replies short and clear (WhatsApp style).
- Always use the `search_knowledge_base` tool to find the answer. Do not guess.
- DO NOT ask the user to provide booking details (dates, destination, adults). 
- DO NOT instruct the user on how to book. Just answer the question politely.
- If you don't know the answer, say "I'm sorry, I don't have that information right now. Our team can help you soon!"
- Avoid robotic responses like "Here is the information." Say things like "Great question! Dune bashing is..."
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

def generate_ai_response(user_message: str, db, company) -> str:
    """
    Acts as a pure Q&A responder. It searches the knowledge base
    and returns a natural text string. It does not mutate state.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]

    # Run agent
    msg = run_chat_agent(messages=messages, tools=TOOLS)
        
    messages.append(msg.model_dump())

    if not msg.tool_calls:
        return msg.content

    # Execute tool calls
    for tool_call in msg.tool_calls:
        function_name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except:
            args = {}

        if function_name == "search_knowledge_base":
            tool_response = search_knowledge_base(args.get("query", ""), db, company)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": str(tool_response)
            })

    # Final response
    final_msg = run_chat_agent(messages=messages)
    return final_msg.content
