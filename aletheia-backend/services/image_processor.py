import os
import json
import base64
from openai import OpenAI
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Lazy-loaded client
_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """Get or create OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        _client = OpenAI(api_key=api_key)
    return _client


async def process_image(image_data: bytes) -> Dict[str, any]:
    """
    Process image using GPT-4o-mini - first classify, then extract if news.

    Args:
        image_data: Raw image bytes

    Returns:
        Dictionary containing is_news, ocr_text, and description
    """
    client = get_client()

    base64_image = base64.b64encode(image_data).decode("utf-8")
    image_url = f"data:image/jpeg;base64,{base64_image}"

    # Step 1: Classify if image contains news/fact-checkable content
    classify_prompt = """Look at this image and determine if it contains NEWS or FACT-CHECKABLE content.

Return JSON: {"is_news": true/false, "reason": "brief explanation"}

MARK is_news = TRUE for ANY of these:
- News channel screenshots (ANY language - Hindi, English, etc.)
- "Breaking News" banners or tickers
- Screenshots from TV news (NDTV, Aaj Tak, Times Now, CNN, BBC, etc.)
- Social media posts with claims about events/people
- WhatsApp forwards with news claims
- Text overlays making factual claims
- Political content or statements
- Accident/incident reports
- Any image with news-style text overlays

MARK is_news = FALSE ONLY for:
- Pure selfies with no text
- Food photos
- Pet photos
- Scenic photos without claims
- Memes that are clearly jokes with no factual claims

When in doubt, mark as TRUE. Return ONLY JSON."""

    classify_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": classify_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        max_tokens=150,
    )

    classify_text = classify_response.choices[0].message.content.strip()
    print(f"[Image Classifier] Raw response: {classify_text}")
    
    # Parse classification result
    try:
        if classify_text.startswith("```"):
            classify_text = classify_text.split("```")[1]
            if classify_text.startswith("json"):
                classify_text = classify_text[4:]
        classify_result = json.loads(classify_text)
        is_news = classify_result.get("is_news", True)  # Default to True
        reason = classify_result.get("reason", "")
        print(f"[Image Classifier] is_news={is_news}, reason={reason}")
    except Exception as e:
        print(f"[Image Classifier] Parse error: {e}, defaulting to is_news=True")
        is_news = True  # Default to checking if parsing fails
        reason = "Classification unclear"

    # If not news, return early
    if not is_news:
        return {
            "is_news": False,
            "ocr_text": "",
            "description": reason
        }

    # Step 2: Extract text and description for news images
    ocr_prompt = """Extract all text visible in this image.
    If there is no text, respond with 'No text found'.
    Only return the extracted text, nothing else."""

    ocr_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": ocr_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    )

    ocr_text = ocr_response.choices[0].message.content.strip()

    description_prompt = """Describe the news/claim shown in this image.
    Focus on: what claim or news is being presented, who/what it's about.
    Keep it concise (1-2 sentences)."""

    description_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": description_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    )

    description = description_response.choices[0].message.content.strip()

    return {
        "is_news": True,
        "ocr_text": ocr_text,
        "description": description
    }
