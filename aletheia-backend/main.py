from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv

from services.image_processor import process_image
from services.classifier import classify_misinformation

load_dotenv()

app = FastAPI(title="Aletheia - Misinformation Detection API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TextMessage(BaseModel):
    text: str


class MisinformationResponse(BaseModel):
    is_misinformation: bool
    confidence: float
    is_news: Optional[bool] = True
    summary: Optional[str] = None
    evidence: Optional[List[str]] = None
    sources_checked: Optional[List[str]] = None
    recommendation: Optional[str] = None
    extracted_text: Optional[str] = None
    image_description: Optional[str] = None
    message_type: str


@app.get("/")
async def root():
    return {"message": "Aletheia Misinformation Detection API", "status": "running"}


@app.post("/analyze/text", response_model=MisinformationResponse)
async def analyze_text(message: TextMessage):
    """
    Analyze text message for misinformation using AI agent with search tools
    """
    result = await classify_misinformation(message.text)

    return MisinformationResponse(
        is_misinformation=result["is_misinformation"],
        confidence=result["confidence"],
        is_news=result.get("is_news", True),
        summary=result.get("summary"),
        evidence=result.get("evidence"),
        sources_checked=result.get("sources_checked"),
        recommendation=result.get("recommendation"),
        message_type="text",
    )


@app.post("/analyze/image", response_model=MisinformationResponse)
async def analyze_image(file: UploadFile = File(...)):
    """
    Analyze image for misinformation using OCR and image description
    """
    image_data = await file.read()
    
    # Validate it's actually image data (check magic bytes)
    if not image_data:
        raise HTTPException(status_code=400, detail="Empty file")
    
    # Check for common image magic bytes (JPEG, PNG, GIF, WebP)
    is_image = (
        image_data[:2] == b'\xff\xd8' or  # JPEG
        image_data[:8] == b'\x89PNG\r\n\x1a\n' or  # PNG
        image_data[:6] in (b'GIF87a', b'GIF89a') or  # GIF
        image_data[:4] == b'RIFF' and image_data[8:12] == b'WEBP'  # WebP
    )
    
    if not is_image:
        raise HTTPException(status_code=400, detail="File must be an image (JPEG, PNG, GIF, or WebP)")

    try:
        image_result = await process_image(image_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

    combined_text = f"{image_result['ocr_text']} {image_result['description']}"

    result = await classify_misinformation(combined_text)

    return MisinformationResponse(
        is_misinformation=result["is_misinformation"],
        confidence=result["confidence"],
        is_news=result.get("is_news", True),
        summary=result.get("summary"),
        evidence=result.get("evidence"),
        sources_checked=result.get("sources_checked"),
        recommendation=result.get("recommendation"),
        extracted_text=image_result["ocr_text"],
        image_description=image_result["description"],
        message_type="image",
    )


@app.post("/analyze", response_model=MisinformationResponse)
async def analyze_message(
    text: Optional[str] = Form(None), file: Optional[UploadFile] = File(None)
):
    """
    Unified endpoint to analyze either text or image message
    """
    if file:
        return await analyze_image(file)
    elif text:
        return await analyze_text(TextMessage(text=text))
    else:
        raise HTTPException(
            status_code=400, detail="Either text or image file must be provided"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
