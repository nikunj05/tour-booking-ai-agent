from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from app.services.translation_service import translation_service
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Translation"])

# Simple rate limiting (in production, use Redis or proper rate limiter)
translation_requests = {}
RATE_LIMIT_REQUESTS = 100  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds

class TranslationRequest(BaseModel):
    texts: List[str]
    target_lang: str

class TranslationResponse(BaseModel):
    translations: Dict[str, str]

def check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded rate limit."""
    current_time = time.time()
    if client_ip not in translation_requests:
        translation_requests[client_ip] = []

    # Clean old requests
    translation_requests[client_ip] = [
        req_time for req_time in translation_requests[client_ip]
        if current_time - req_time < RATE_LIMIT_WINDOW
    ]

    if len(translation_requests[client_ip]) >= RATE_LIMIT_REQUESTS:
        return False

    translation_requests[client_ip].append(current_time)
    return True

@router.post("/")
async def translate_texts(request: TranslationRequest):
    """Translate multiple texts to target language."""
    logger.info(f"Translation request for {len(request.texts)} texts to {request.target_lang}")
    
    translations = {}
    
    for text in request.texts:
        if text.strip():  # Only translate non-empty texts
            translated = translation_service.translate_text(text, request.target_lang)
            translations[text] = translated
    
    return TranslationResponse(translations=translations)

@router.post("/test")
async def test_translation():
    """Test endpoint that returns mock translations."""
    return {
        "translations": {
            "Home": "الرئيسية",
            "About": "حول",
            "Tours": "الجولات",
            "Contact Us": "اتصل بنا"
        }
    }