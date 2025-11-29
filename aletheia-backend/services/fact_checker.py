"""
Fact Checker using Perplexity API for grounded search + OpenAI for analysis.

This module provides fast, reliable misinformation detection by:
1. Using Perplexity's search-grounded responses to find relevant facts
2. Using OpenAI to analyze and make final determination
"""

import os
import re
import json
import asyncio
from typing import Dict, Any, List, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class FactChecker:
    """Fast fact-checker using Perplexity for search + OpenAI for analysis."""
    
    def __init__(self):
        self.perplexity_client = OpenAI(
            api_key=PERPLEXITY_API_KEY,
            base_url="https://api.perplexity.ai"
        )
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
    
    async def check_claim(self, text: str) -> Dict[str, Any]:
        """
        Check a claim/message for misinformation.
        
        Args:
            text: The text to verify
            
        Returns:
            Dictionary with verification results
        """
        # Step 1: Use Perplexity to search for facts about this claim
        search_result = await self._perplexity_search(text)
        
        # Step 2: Use OpenAI to analyze and make determination
        analysis = await self._analyze_with_openai(text, search_result)
        
        return analysis
    
    def _perplexity_search_sync(self, claim: str) -> Dict[str, Any]:
        """Synchronous Perplexity search."""
        response = self.perplexity_client.chat.completions.create(
            model="sonar",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a fact-checking assistant. Search for reliable information "
                        "about the given claim. Focus on finding:\n"
                        "1. Whether this claim has been reported by credible news sources\n"
                        "2. Any fact-checks done on this claim\n"
                        "3. The actual facts related to this topic\n"
                        "Be objective and cite your sources."
                    )
                },
                {
                    "role": "user",
                    "content": f"Fact-check this claim and find relevant information:\n\n\"{claim}\""
                }
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content
        
        # Extract citations if available
        citations = []
        if hasattr(response, 'citations') and response.citations:
            citations = response.citations
        
        return {
            "search_result": content,
            "citations": citations,
            "success": True
        }
    
    async def _perplexity_search(self, claim: str) -> Dict[str, Any]:
        """Search for facts about the claim using Perplexity."""
        try:
            return await asyncio.to_thread(self._perplexity_search_sync, claim)
        except Exception as e:
            return {
                "search_result": f"Search failed: {str(e)}",
                "citations": [],
                "success": False
            }
    
    async def _analyze_with_openai(self, original_claim: str, search_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the claim using OpenAI based on Perplexity search results."""
        
        search_context = search_result.get("search_result", "No search results available")
        citations = search_result.get("citations", [])
        
        prompt = f"""Analyze this claim for misinformation based on the search results.

CLAIM TO VERIFY:
"{original_claim}"

SEARCH RESULTS FROM FACT-CHECK:
{search_context}

Based on this information, provide your analysis in the following JSON format:
{{
    "is_misinformation": true/false,
    "confidence": 0.0-1.0,
    "is_news": true/false,
    "verdict": "TRUE" | "FALSE" | "MISLEADING" | "UNVERIFIED" | "SATIRE" | "NOT_NEWS",
    "summary": "Brief 1-2 sentence summary of findings",
    "evidence": ["Key fact 1", "Key fact 2", "Key fact 3"],
    "sources": ["Source 1", "Source 2"],
    "recommendation": "What the user should do"
}}

Guidelines:
- is_misinformation: true if the claim is false, misleading, or manipulated
- confidence: how confident you are (0.5 = uncertain, 1.0 = certain)
- is_news: false if this is casual conversation, greetings, or non-news content
- For non-news content, set is_misinformation to false with low confidence
- Be conservative - only mark as misinformation if there's clear evidence

Return ONLY the JSON, no other text."""

        try:
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert fact-checker. Analyze claims objectively and return structured JSON responses."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON from response
            # Handle markdown code blocks
            if content.startswith("```"):
                content = re.sub(r'^```(?:json)?\n?', '', content)
                content = re.sub(r'\n?```$', '', content)
            
            result = json.loads(content)
            
            # Add citations from Perplexity if available
            if citations:
                result["sources_checked"] = citations[:5]
            elif result.get("sources"):
                result["sources_checked"] = result["sources"]
            else:
                result["sources_checked"] = []
            
            return {
                "is_misinformation": result.get("is_misinformation", False),
                "confidence": result.get("confidence", 0.5),
                "is_news": result.get("is_news", True),
                "verdict": result.get("verdict", "UNVERIFIED"),
                "summary": result.get("summary", ""),
                "evidence": result.get("evidence", []),
                "sources_checked": result.get("sources_checked", []),
                "recommendation": result.get("recommendation", "Verify with multiple sources."),
                "success": True
            }
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try to extract key info
            return {
                "is_misinformation": False,
                "confidence": 0.3,
                "is_news": True,
                "verdict": "UNVERIFIED",
                "summary": "Could not complete analysis",
                "evidence": [],
                "sources_checked": [],
                "recommendation": "Please verify this information manually.",
                "success": False,
                "error": f"JSON parse error: {str(e)}"
            }
        except Exception as e:
            return {
                "is_misinformation": False,
                "confidence": 0.0,
                "is_news": True,
                "verdict": "ERROR",
                "summary": f"Analysis error: {str(e)}",
                "evidence": [],
                "sources_checked": [],
                "recommendation": "Please try again later.",
                "success": False,
                "error": str(e)
            }


# Global instance
_fact_checker: Optional[FactChecker] = None


def get_fact_checker() -> FactChecker:
    """Get or create global fact checker instance."""
    global _fact_checker
    if _fact_checker is None:
        _fact_checker = FactChecker()
    return _fact_checker


async def check_misinformation(text: str) -> Dict[str, Any]:
    """
    Main function to check text for misinformation.
    
    Args:
        text: Text to verify
        
    Returns:
        Dictionary with verification results
    """
    checker = get_fact_checker()
    return await checker.check_claim(text)
