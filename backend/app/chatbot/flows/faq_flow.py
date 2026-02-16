from app.models.faq_document import FAQDocument
from app.models.tour_package import TourPackage
from app.utils.embeddings import generate_embedding
from app.services.openai_service import generate_reply
from app.chatbot.prompts.reply import FAQ_REPLY_PROMPT


def handle_faq_flow(user_message, db, company):

    query_embedding = generate_embedding(user_message)

    # 🔹 Search FAQs
    faq_results = db.query(FAQDocument).filter(
        FAQDocument.company_id == company.id,
        FAQDocument.embedding != None
    ).order_by(
        FAQDocument.embedding.l2_distance(query_embedding)
    ).limit(2).all()

    # 🔹 Search Tours
    tour_results = db.query(TourPackage).filter(
        TourPackage.company_id == company.id,
        TourPackage.is_deleted == False,
        TourPackage.status == "active",
        TourPackage.embedding != None
    ).order_by(
        TourPackage.embedding.l2_distance(query_embedding)
    ).limit(2).all()

    if not faq_results and not tour_results:
        return {"text": "Sorry, I couldn't find anything related to your question."}

    # 🔥 Build context
    context_parts = []

    for faq in faq_results:
        context_parts.append(
            f"FAQ:\nTitle: {faq.title}\nAnswer: {faq.content}"
        )

    for tour in tour_results:
        context_parts.append(
            f"""Tour Package:
Title: {tour.title}
City: {tour.city}
Price: {tour.currency} {tour.price}
Description: {tour.description}
Itinerary: {tour.itinerary}
"""
        )

    context = "\n\n".join(context_parts)

    reply_text = generate_reply(
        user_text=user_message,
        context={"company_knowledge": context},
        extra_prompt=FAQ_REPLY_PROMPT
    )

    return {"text": reply_text}