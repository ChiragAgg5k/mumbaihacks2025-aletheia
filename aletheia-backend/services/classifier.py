from typing import Dict
from services.fact_checker import check_misinformation


async def classify_misinformation(text: str) -> Dict[str, any]:
    """
    Classify text for misinformation detection using Perplexity + OpenAI.

    Uses Perplexity for grounded search results and OpenAI for analysis.

    Args:
        text: Text to classify

    Returns:
        Dictionary containing classification result, confidence score, and details
    """
    result = await check_misinformation(text)
    
    return {
        "is_misinformation": result.get("is_misinformation", False),
        "confidence": result.get("confidence", 0.0),
        "is_news": result.get("is_news", True),
        "summary": result.get("summary", ""),
        "evidence": result.get("evidence", []),
        "sources_checked": result.get("sources_checked", []),
        "recommendation": result.get("recommendation", "")
    }
