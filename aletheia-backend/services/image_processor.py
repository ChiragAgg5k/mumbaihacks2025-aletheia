import os
import base64
from openai import OpenAI
from typing import Dict

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None


async def process_image(image_data: bytes) -> Dict[str, str]:
    """
    Process image using GPT-5-mini for OCR and description

    Args:
        image_data: Raw image bytes

    Returns:
        Dictionary containing OCR text and image description
    """
    if not client:
        raise ValueError("OPENAI_API_KEY not configured")

    base64_image = base64.b64encode(image_data).decode("utf-8")

    image_url = f"data:image/jpeg;base64,{base64_image}"

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

    description_prompt = """Provide a detailed description of this image.
    Focus on: main subjects, context, setting, any notable elements, and overall theme.
    Keep it concise but informative (2-3 sentences)."""

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

    return {"ocr_text": ocr_text, "description": description}
