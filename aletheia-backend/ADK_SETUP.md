# Google ADK Misinformation Detection Agent

This service uses Google's Agent Development Kit (ADK) to create an AI agent for detecting misinformation.

## Setup Complete ✓

### Installed Components:
- **google-adk** (v1.18.0) - Agent Development Kit framework
- **litellm** (v1.80.5) - Multi-provider AI model support
- **80+ dependencies** - Including OpenAI, Anthropic, and Google clients

### Supported AI Providers:

1. **OpenAI** (GPT-4, GPT-4o, GPT-3.5-turbo, etc.)
   - Set `OPENAI_API_KEY` in `.env`
   - Get key: https://platform.openai.com/api-keys

2. **Anthropic** (Claude 3 Sonnet, Claude 3 Haiku, etc.)
   - Set `ANTHROPIC_API_KEY` in `.env`
   - Get key: https://console.anthropic.com/

3. **Google Gemini** (Gemini 2.0 Flash, Gemini Pro, etc.)
   - Set `GOOGLE_API_KEY` in `.env`
   - Get key: https://aistudio.google.com/app/apikey

4. **100+ Other Providers** via LiteLLM
   - Cohere, Hugging Face, Together AI, etc.
   - See: https://docs.litellm.ai/docs/providers

## Agent Architecture

The misinformation detection agent includes:

### Tools/Capabilities:
1. **search_fact_check_database()** - Query fact-checking APIs
2. **analyze_source_credibility()** - Check source reputation
3. **detect_manipulation_patterns()** - Identify manipulation tactics

### Analysis Features:
- Emotional manipulation detection
- Logical fallacy identification
- Clickbait pattern recognition
- Conspiracy theory markers
- Source credibility assessment
- Multi-modal analysis (text + images)

## Usage

### Quick Test:
```powershell
# Add at least one API key to .env
# Then run the test script:
uv run test_agent.py
```

### In Your Code:
```python
from services.misinformation_agent import MisinformationAgent

# Create agent with specific provider
agent = MisinformationAgent(
    model_provider="openai",  # or "anthropic" or "gemini"
    model_name="gpt-4o"
)

# Analyze text
result = await agent.analyze_text("Some news article text...")

# Analyze with image context
result = await agent.analyze_with_image(
    text="Article text",
    image_description="Description from vision model",
    ocr_text="Text extracted from image"
)
```

### Integration with FastAPI:
Update `services/classifier.py` to use the ADK agent instead of random classification.

## Next Steps

1. **Add API Keys**: Configure at least one AI provider in `.env`
2. **Test Agent**: Run `uv run test_agent.py`
3. **Integrate Tools**: Connect to real fact-checking APIs:
   - Google Fact Check Tools API
   - ClaimBuster API
   - NewsGuard API
   - Full Fact API

4. **Enhance Analysis**: Add more sophisticated detection methods:
   - Image manipulation detection
   - Deepfake detection
   - Network analysis (source relationships)
   - Historical claim tracking

5. **Update FastAPI**: Replace placeholder classifier with ADK agent

## Documentation

- ADK Docs: https://google.github.io/adk-docs/
- Model Configuration: https://google.github.io/adk-docs/agents/models/
- Custom Tools: https://google.github.io/adk-docs/tools-custom/
- LiteLLM Providers: https://docs.litellm.ai/docs/providers

## Environment Variables

Required (at least one):
```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...
```

Optional:
```env
DEFAULT_AI_PROVIDER=openai  # Default: openai
DEFAULT_AI_MODEL=gpt-4o     # Default: gpt-4o
```

## Files Created

- `services/misinformation_agent.py` - Main agent implementation
- `test_agent.py` - Test script
- `.env` - Updated with all provider keys
- `ADK_SETUP.md` - This file
