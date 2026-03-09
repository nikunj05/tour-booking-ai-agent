def handle_fallback(phone, session, db, company):
    """
    Called when the intent is 'unknown'. Provides a polite fallback
    message to guide the user back to the primary menus.
    """
    reply_text = (
        "I'm sorry, I didn't fully understand that.\n\n"
        "You can:\n"
        "• Explore tour packages\n"
        "• Book a tour\n"
        "• Ask about destinations\n\n"
        "How can I assist you today?"
    )
    
    # We could optionally attach interactive buttons here, 
    # but a simple text reply is universally supported.
    return {
        "text": reply_text
    }
