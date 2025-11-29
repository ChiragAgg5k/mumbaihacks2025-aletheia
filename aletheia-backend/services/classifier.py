from typing import Dict
from services.agent import analyze_with_agent, detect_if_news


async def classify_misinformation(text: str) -> Dict[str, any]:
    """
    Classify text for misinformation detection using AI agent with tools.

    First checks if the text is news/fact-checkable content.
    If yes, uses an AI agent with search tools to verify claims.
    If no, returns early indicating it's not news.

    Args:
        text: Text to classify

    Returns:
        Dictionary containing classification result, confidence score, and details
    """
    # Step 1: Check if this is news or a fact-checkable claim
    news_check = await detect_if_news(text)
    
    if not news_check.get("is_news", False):
        # Not news - return early
        return {
            "is_misinformation": False,
            "confidence": 0.0,
            "is_news": False,
            "summary": news_check.get("reason", "This doesn't appear to be news or a fact-checkable claim."),
            "evidence": [],
            "sources_checked": [],
            "recommendation": "No fact-check needed for this type of message."
        }
    
    # Step 2: It's news - run the fact-checking agent
    result = await analyze_with_agent(text)
    
    return {
        "is_misinformation": result["is_misinformation"],
        "confidence": result["confidence"],
        "is_news": True,
        "summary": result.get("summary", ""),
        "evidence": result.get("evidence", []),
        "sources_checked": result.get("sources_checked", []),
        "recommendation": result.get("recommendation", "")
    }
