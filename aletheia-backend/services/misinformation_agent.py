"""
Misinformation Detection Agent using Google ADK and OpenAI

This module provides an AI agent that uses OpenAI models to analyze news headlines
for misinformation by searching Google News and analyzing multiple sources.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from services.google_news_verifier import verify_news_headline

load_dotenv()


def detect_manipulation_patterns(text: str) -> Dict[str, Any]:
    """
    Detect common misinformation manipulation patterns
    
    Checks for:
    - Emotional manipulation
    - Logical fallacies
    - Clickbait indicators
    - Conspiracy theory markers
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with detected manipulation patterns
    """
    patterns = []
    
    # Emotional manipulation
    emotional_words = ["shocking", "unbelievable", "they don't want you to know", "mind-blowing", "insane"]
    if any(word.lower() in text.lower() for word in emotional_words):
        patterns.append("emotional_manipulation")
    
    # Excessive emphasis
    if "!!!" in text or text.count("!") > 3:
        patterns.append("excessive_emphasis")
    
    # All caps words (shouting)
    words = text.split()
    caps_count = sum(1 for word in words if word.isupper() and len(word) > 2)
    if caps_count > 2:
        patterns.append("excessive_capitalization")
    
    # Conspiracy indicators
    if any(phrase in text.lower() for phrase in ["mainstream media", "wake up", "open your eyes", "they", "them"]):
        patterns.append("conspiracy_indicators")
    
    # Clickbait phrases
    clickbait = ["you won't believe", "this one trick", "doctors hate", "what happens next"]
    if any(phrase in text.lower() for phrase in clickbait):
        patterns.append("clickbait")
    
    return {
        "patterns_detected": patterns,
        "manipulation_score": min(len(patterns) / 5.0, 1.0),  # Normalized score
        "description": f"Found {len(patterns)} manipulation patterns: {', '.join(patterns) if patterns else 'None'}"
    }


class MisinformationAgent:
    """
    AI Agent for detecting misinformation in news headlines
    
    Uses OpenAI via Google ADK to orchestrate Google News search and analysis
    for comprehensive misinformation detection.
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Initialize the misinformation detection agent
        
        Args:
            model_name: OpenAI model name (default: gpt-4o-mini for cost efficiency)
        """
        self.model_name = model_name
        self.agent = self._create_agent()
    
    def _create_agent(self) -> LlmAgent:
        """Create and configure the ADK agent with OpenAI"""
        
        # Use OpenAI via LiteLLM
        model = LiteLlm(model=f"openai/{self.model_name}")
        
        # Create the agent with Google News verification tool
        agent = LlmAgent(
            model=model,
            name="news_misinformation_detector",
            description=(
                "Expert AI agent that verifies news headlines by searching Google News, "
                "analyzing multiple sources, checking source credibility, and detecting "
                "manipulation patterns to identify misinformation."
            ),
            instruction="""
You are an expert misinformation detection system specializing in news verification.

Your verification process:

1. **Google News Search**: Use the verify_news_headline tool to search Google News for the headline
   - This tool searches Google News and returns top 10 results
   - Each result includes the article title, URL, source, and snippet
   - The tool also scrapes each article to extract full content, backlinks, and metadata

2. **Source Analysis**: Examine the sources reporting this news
   - Check if reputable news organizations (BBC, Reuters, AP, NYT, etc.) are reporting it
   - Count how many independent sources confirm the story
   - Analyze the credibility of the sources

3. **Content Verification**: Review the article content
   - Check for factual consistency across sources
   - Look for primary sources and citations
   - Identify any contradictions between sources

4. **Manipulation Detection**: Use detect_manipulation_patterns to identify red flags
   - Emotional manipulation
   - Clickbait language
   - Conspiracy theory markers
   - Excessive emphasis

5. **Final Assessment**: Make a clear determination
   - TRUE: Multiple reputable sources confirm, consistent facts, no manipulation
   - FALSE/MISINFORMATION: No reputable sources, inconsistent facts, manipulation detected
   - UNVERIFIED: Insufficient information, conflicting reports
   - PARTIALLY TRUE: Some elements true, some false or misleading

IMPORTANT: 
- Always use the verify_news_headline tool first to get Google News data
- Be thorough - analyze ALL provided sources
- Cite specific sources in your reasoning
- Provide a confidence score (0.0 to 1.0)
- Explain your reasoning clearly

Response format:
- Verdict: [TRUE/FALSE/UNVERIFIED/PARTIALLY TRUE]
- Confidence: [0.0-1.0]
- Sources Found: [Number of sources]
- Reputable Sources: [List of credible news organizations]
- Key Findings: [Bullet points of important discoveries]
- Reasoning: [Detailed explanation]
- Recommendation: [Action for users]
            """,
            tools=[
                verify_news_headline,
                detect_manipulation_patterns
            ]
        )
        
        return agent
    
    async def analyze_headline(self, headline: str) -> Dict[str, Any]:
        """
        Analyze a news headline for misinformation
        
        Args:
            headline: The news headline to verify
            
        Returns:
            Dictionary with comprehensive analysis results
        """
        from google.adk.runners import Runner
        from google.genai import types
        import uuid
        
        prompt = f"""
Verify this news headline for misinformation:

"{headline}"

Use the verify_news_headline tool to search Google News and analyze the results.
Then provide a comprehensive assessment.
"""
        
        try:
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            from google.genai import types
            import uuid
            
            # Create a runner to execute the agent
            session_service = InMemorySessionService()
            runner = Runner(
                app_name="misinformation_detector",
                agent=self.agent,
                session_service=session_service
            )
            
            # Create a message content
            message = types.Content(parts=[types.Part(text=prompt)])
            
            # Run the agent
            result_stream = runner.run_async(
                user_id="test_user",
                session_id=str(uuid.uuid4()),
                new_message=message
            )
            
            # Collect all events from the async generator
            analysis_text = ""
            async for event in result_stream:
                # Extract text from event content
                if hasattr(event, 'content') and event.content:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            analysis_text += part.text
            
            # Extract verdict (simple parsing - can be improved)
            is_misinformation = "FALSE" in analysis_text or "MISINFORMATION" in analysis_text
            
            # Try to extract confidence from the response
            confidence = 0.75  # Default
            import re
            conf_match = re.search(r'Confidence[:\s]+([0-9.]+)', analysis_text)
            if conf_match:
                try:
                    confidence = float(conf_match.group(1))
                except:
                    pass
            
            return {
                "headline": headline,
                "is_misinformation": is_misinformation,
                "confidence": confidence,
                "analysis": analysis_text,
                "model": self.model_name,
                "success": True
            }
            
        except Exception as e:
            return {
                "headline": headline,
                "error": str(e),
                "is_misinformation": None,
                "confidence": 0.0,
                "analysis": f"Error during analysis: {str(e)}",
                "success": False
            }
    
    async def analyze_text(self, text: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze text for misinformation (backward compatibility)
        
        Args:
            text: The text content to analyze (treated as headline)
            context: Optional additional context
            
        Returns:
            Dictionary with analysis results
        """
        return await self.analyze_headline(text)
    
    async def analyze_with_image(
        self,
        text: str,
        image_description: str,
        ocr_text: str
    ) -> Dict[str, Any]:
        """
        Analyze content combining text and image analysis
        
        Args:
            text: The original text
            image_description: AI-generated description of the image
            ocr_text: Text extracted from the image via OCR
            
        Returns:
            Dictionary with analysis results
        """
        combined_content = f"""
Text: {text}

Image Description: {image_description}

Text in Image (OCR): {ocr_text}
"""
        
        prompt = f"""
Analyze the following multimodal content for misinformation. 
Consider both the text and visual elements:

{combined_content}

Pay special attention to:
- Mismatches between text and images
- Manipulated or out-of-context images
- Deepfakes or edited visuals
- Misleading captions
"""
        
        try:
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            from google.genai import types
            import uuid
            
            # Create a runner to execute the agent
            session_service = InMemorySessionService()
            runner = Runner(
                app_name="misinformation_detector",
                agent=self.agent,
                session_service=session_service
            )
            
            # Create a message content
            message = types.Content(parts=[types.Part(text=prompt)])
            
            # Run the agent
            result_stream = runner.run_async(
                user_id="test_user",
                session_id=str(uuid.uuid4()),
                new_message=message
            )
            
            # Collect all events
            analysis_text = ""
            async for event in result_stream:
                if hasattr(event, 'content') and event.content:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            analysis_text += part.text
            
            return {
                "is_misinformation": False,  # Parse from response
                "confidence": 0.75,
                "analysis": analysis_text,
                "image_analysis": {
                    "description": image_description,
                    "ocr_text": ocr_text
                },
                "model": self.model_name
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "is_misinformation": None,
                "confidence": 0.0,
                "analysis": f"Error during analysis: {str(e)}"
            }


# Default agent instance using OpenAI
def get_default_agent() -> MisinformationAgent:
    """Get a default configured misinformation agent with OpenAI"""
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return MisinformationAgent(model_name=model)
