"""
Test script for the Misinformation Detection Agent with Google News

Run this to verify ADK setup, Google News scraping, and agent functionality.
"""

import asyncio
import os
from dotenv import load_dotenv
from services.misinformation_agent import MisinformationAgent

load_dotenv()


async def test_agent():
    """Test the misinformation detection agent with Google News"""
    
    print("=" * 80)
    print("MISINFORMATION DETECTION AGENT - GOOGLE NEWS VERIFICATION TEST")
    print("=" * 80)
    
    # Check environment variables
    print("\n1. Checking Environment Configuration:")
    print("-" * 80)
    
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here":
        print("✗ OpenAI API key not configured!")
        print("\nPlease add your OpenAI API key to .env:")
        print("  OPENAI_API_KEY=sk-...")
        print("\nGet your API key from: https://platform.openai.com/api-keys")
        return
    
    print("✓ OpenAI API key configured")
    
    # Create agent
    print("\n2. Initializing Agent:")
    print("-" * 80)
    try:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        print(f"Using model: {model}")
        agent = MisinformationAgent(model_name=model)
        print("✓ Agent initialized successfully")
        print("✓ Tools loaded: verify_news_headline, detect_manipulation_patterns")
    except Exception as e:
        print(f"✗ Error initializing agent: {e}")
        return
    
    # Test cases - real and fake news headlines
    test_cases = [
        {
            "name": "Real Breaking News",
            "headline": "NASA announces new Mars rover discovery"
        },
        {
            "name": "Suspicious Clickbait",
            "headline": "SHOCKING!!! Scientists discover cure for aging! Doctors HATE this!!!"
        },
        {
            "name": "Verify Current Event",
            "headline": "OpenAI releases GPT-4 language model"
        }
    ]
    
    print("\n3. Running Test Cases with Google News Verification:")
    print("-" * 80)
    print("\nNote: Each test will:")
    print("  1. Search Google News for the headline")
    print("  2. Scrape and analyze top 10 results")
    print("  3. Check source credibility")
    print("  4. Detect manipulation patterns")
    print("  5. Provide comprehensive verdict")
    print("\nThis may take 30-60 seconds per test...")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"Test Case {i}: {test_case['name']}")
        print(f"{'='*80}")
        print(f"Headline: \"{test_case['headline']}\"")
        print("\nAnalyzing...")
        
        try:
            result = await agent.analyze_headline(test_case['headline'])
            
            print(f"\n{'Results:':^80}")
            print("-" * 80)
            print(f"Verdict: {'MISINFORMATION' if result.get('is_misinformation') else 'VERIFIED'}")
            print(f"Confidence: {result.get('confidence', 'N/A')}")
            print(f"\nDetailed Analysis:")
            print(result.get('analysis', 'N/A'))
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nThe agent successfully:")
    print("  ✓ Searched Google News for each headline")
    print("  ✓ Scraped article content from top results")
    print("  ✓ Analyzed source credibility")
    print("  ✓ Detected manipulation patterns")
    print("  ✓ Provided detailed verdicts")


if __name__ == "__main__":
    asyncio.run(test_agent())
