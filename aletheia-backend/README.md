# Aletheia Backend

FastAPI-based misinformation detection API that analyzes both text and image messages using Mistral AI's vision and language models.

## Features

- **Text Analysis**: Detect misinformation in text messages
- **Image Analysis**:
  - Extract text from images using OCR (Mistral Pixtral)
  - Generate image descriptions
  - Classify combined content for misinformation
- **Unified Endpoint**: Single endpoint for both text and image analysis
- **REST API**: Easy-to-use RESTful API with automatic documentation

## Project Structure

```
aletheia-backend/
├── main.py                 # FastAPI application and endpoints
├── services/
│   ├── __init__.py
│   ├── image_processor.py  # Mistral image processing (OCR + description)
│   └── classifier.py       # Misinformation classifier (currently simulated)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Setup

### Prerequisites

- Python 3.8+
- Mistral AI API key ([Get one here](https://console.mistral.ai/))

### Installation

1. Clone or navigate to the project:
```bash
cd aletheia-backend
```

2. Create a virtual environment:
```bash
uv sync
```

3. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your Mistral API key:
```
MISTRAL_API_KEY=your_actual_api_key_here
```

## Running the Server

```bash
uv run main
```

## API Documentation

Once running, visit:
- **Interactive API docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative docs (ReDoc)**: http://localhost:8000/redoc

## API Endpoints

### 1. Health Check
```
GET /
```

### 2. Analyze Text
```
POST /analyze/text
Content-Type: application/json

{
  "text": "Your text message here"
}
```

### 3. Analyze Image
```
POST /analyze/image
Content-Type: multipart/form-data

file: [image file]
```

### 4. Unified Analysis (Recommended)
```
POST /analyze
Content-Type: multipart/form-data

text: "optional text message"
file: [optional image file]
```

## Example Usage

### Using cURL

**Text analysis:**
```bash
curl -X POST "http://localhost:8000/analyze/text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Breaking news: Scientists discover..."}'
```

**Image analysis:**
```bash
curl -X POST "http://localhost:8000/analyze/image" \
  -F "file=@/path/to/image.jpg"
```

### Using Python

```python
import requests

# Text analysis
response = requests.post(
    "http://localhost:8000/analyze/text",
    json={"text": "Your message here"}
)
print(response.json())

# Image analysis
with open("image.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/analyze/image",
        files={"file": f}
    )
print(response.json())
```

## Response Format

All endpoints return a JSON response:

```json
{
  "is_misinformation": true,
  "confidence": 0.87,
  "extracted_text": "Text found in image (for images only)",
  "image_description": "Description of image content (for images only)",
  "message_type": "text" or "image"
}
```

## Current Status

### ✅ Implemented
- FastAPI server with CORS support
- Text message endpoint
- Image upload and processing
- Mistral AI integration for OCR and image description
- Unified analysis endpoint

### 🚧 In Progress
- **Classifier**: Currently using simulated random classification
  - Returns random true/false for demonstration
  - TODO: Train and integrate actual misinformation detection model

### 🔮 Future Enhancements
- Train ML model on misinformation dataset
- Add confidence thresholds
- Implement caching for processed images
- Add rate limiting
- Support batch processing
- Add detailed explanation for classifications
- Multi-language support

## Development

### Adding a Real Classifier

When ready to replace the simulated classifier:

1. Train your model (e.g., fine-tuned BERT/RoBERTa on misinformation data)
2. Update `services/classifier.py`:
   - Load your trained model
   - Implement `classify_misinformation_with_model()`
   - Replace the call in `classify_misinformation()`

### Testing

The API includes automatic validation and error handling for:
- Invalid file types
- Missing required fields
- Image processing errors
- API key configuration issues

## License

MIT

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.
