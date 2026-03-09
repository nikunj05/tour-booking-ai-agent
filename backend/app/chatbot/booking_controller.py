from app.chatbot.flows.booking_flow import handle_booking_flow
from app.chatbot.states import BOOKING_CITY_LIST

def start_or_continue_booking(phone, session, text, db, company, location=None):
    """
    Ensures the user is in the booking flow. If they are not,
    switches their state to the start of the booking flow.
    """
    if not session.state.startswith("BOOKING_"):
        session.state = BOOKING_CITY_LIST
        db.commit()
        # Clear text so the first prompt (city list) triggers cleanly
        text = ""
        
    return handle_booking_flow(phone, session, text, db, company, location)

def reprompt_current_booking_step(phone, session, db, company):
    """
    Called after an AI FAQ answer mid-booking. We pass empty text
    so the system reprints the current booking active lists/buttons.
    We pass a no-op save function so it doesn't duplicate messages in DB.
    """
    return handle_booking_flow(
        phone, session, "", db, company, 
        location=None, 
        save_message_fn=lambda *args: None
    )
