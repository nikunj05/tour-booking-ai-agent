# Multi-Language Translation System

This system provides AI-powered translation for the tour booking website, supporting English (default), Hindi, and Arabic.

## Features

- **URL-based language routing**: `/en/`, `/hi/`, `/ar/` prefixes
- **AI-powered translation**: Uses OpenAI GPT-3.5-turbo for high-quality translations
- **Client-side caching**: 24-hour localStorage caching to reduce API calls
- **RTL support**: Automatic right-to-left layout for Arabic
- **Rate limiting**: 100 requests per minute per IP
- **Graceful fallback**: Returns original text if translation fails
- **User controls**: Option to disable auto-translation

## Setup

1. Add OpenAI API key to `.env`:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

2. The system will work without API key but return original English text.

## Supported Languages

- **English (en)**: Default language
- **Hindi (hi)**: हिन्दी
- **Arabic (ar)**: العربية (with RTL support)

## API Endpoints

- `POST /translate`: Translate texts
- `GET /translate/health`: Health check

## Production Considerations

- **Caching**: Currently uses in-memory cache. For production, implement Redis.
- **Rate Limiting**: Basic in-memory rate limiting. Use Redis for distributed systems.
- **Monitoring**: Add proper logging and monitoring for translation failures.
- **Cost Management**: Monitor OpenAI API usage and costs.

## Usage

Users can switch languages using the dropdown in the navbar. The system automatically:
1. Detects language from URL
2. Translates page content using AI
3. Caches translations locally
4. Applies RTL layout for Arabic

## Troubleshooting

- If translations don't appear, check browser console for errors
- If API fails, system falls back to original English text
- Users can disable translation via the language dropdown toggle