import openai
from app.core.config import settings
import json
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class TranslationService:
    def __init__(self):
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not self.api_key:
            logger.warning("OpenAI API key not configured. Translation will return original text.")
        else:
            self.client = openai.OpenAI(api_key=self.api_key)
        self.cache = {}  # In production, use Redis or database

    def get_cache_key(self, text: str, target_lang: str) -> str:
        """Generate a cache key for the translation."""
        content = f"{text}:{target_lang}"
        return hashlib.md5(content.encode()).hexdigest()

    def translate_text(self, text: str, target_lang: str) -> str:
        """Translate text to target language using OpenAI."""
        if not text or not text.strip():
            return text

        # If no API key, return original text
        if not self.api_key:
            return text

        # Check cache first
        cache_key = self.get_cache_key(text, target_lang)
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # Map language codes to full names
            lang_names = {
                'hi': 'Hindi',
                'ar': 'Arabic',
                'en': 'English'
            }

            target_name = lang_names.get(target_lang, target_lang)

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a professional translator. Translate the following text to {target_name}. Maintain the original meaning and tone. If the text contains HTML tags, preserve them. For Arabic, ensure proper RTL formatting. Only return the translated text, nothing else."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                max_tokens=1000,
                temperature=0.3,
                timeout=10  # 10 second timeout
            )

            translated_text = response.choices[0].message.content.strip()

            # Basic validation - ensure we got a response
            if not translated_text:
                logger.warning(f"Empty translation response for text: {text[:50]}...")
                return text

            # Cache the result
            self.cache[cache_key] = translated_text

            return translated_text

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return text
        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            return text
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text  # Return original text if translation fails

# Global instance
translation_service = TranslationService()