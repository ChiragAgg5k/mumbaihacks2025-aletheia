import os
import json
import httpx
import urllib.parse
from typing import Dict, List, Any
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Headers to mimic a browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


# Tool definitions for the agent
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "google_search",
            "description": "Search Google for general information. Use this to find facts, verify claims, or get context about a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on Google"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "google_news_search",
            "description": "Search Google News for recent news articles. Use this to find recent news coverage and verify if a news story is being reported by credible sources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The news topic or claim to search for"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fact_check_search",
            "description": "Search for fact-checks from reputable fact-checking organizations. Use this to see if a claim has already been verified or debunked.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim": {
                        "type": "string",
                        "description": "The specific claim to fact-check"
                    }
                },
                "required": ["claim"]
            }
        }
    }
]


def parse_google_results(html: str) -> List[Dict[str, str]]:
    """Parse Google search results from HTML."""
    results = []
    
    # Simple parsing - look for result divs
    # Google's HTML structure: <div class="g"> contains each result
    import re
    
    # Find all result blocks - look for links with /url?q= pattern (Google's redirect)
    # or direct links in the search results
    link_pattern = r'<a href="(/url\?q=|)(https?://[^"&]+)[^"]*"[^>]*>([^<]+)</a>'
    matches = re.findall(link_pattern, html)
    
    seen_urls = set()
    for _, url, title in matches:
        # Skip Google's own URLs and duplicates
        if 'google.com' in url or url in seen_urls:
            continue
        if not title.strip() or len(title) < 5:
            continue
            
        seen_urls.add(url)
        
        # Try to find snippet near this result
        # Look for text after the link
        snippet = ""
        snippet_match = re.search(
            re.escape(title) + r'</a>.*?<span[^>]*>([^<]{50,300})</span>',
            html, re.DOTALL
        )
        if snippet_match:
            snippet = snippet_match.group(1).strip()
        
        # Extract domain from URL
        domain_match = re.search(r'https?://([^/]+)', url)
        source = domain_match.group(1) if domain_match else ""
        
        results.append({
            "title": title.strip(),
            "snippet": snippet,
            "link": url,
            "source": source
        })
        
        if len(results) >= 5:
            break
    
    return results


async def google_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """Perform a web search using DuckDuckGo (more reliable than scraping Google)."""
    # Use DuckDuckGo directly as it's more reliable for scraping
    return await duckduckgo_search(query, num_results)


async def duckduckgo_search(query: str, num_results: int = 5, retries: int = 3) -> List[Dict[str, str]]:
    """Search using DuckDuckGo HTML with retry logic."""
    import re
    import asyncio
    
    for attempt in range(retries):
        try:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.get(url, headers=HEADERS)
                response.raise_for_status()
                
                results = []
                
                # DuckDuckGo HTML results - find result snippets
                # Pattern for result links with class result__a
                link_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.+?)</a>'
                snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>(.+?)</a>'
                
                links = re.findall(link_pattern, response.text, re.DOTALL)
                snippets = re.findall(snippet_pattern, response.text, re.DOTALL)
                
                for i, (link, title) in enumerate(links[:num_results]):
                    # Clean up the link - DuckDuckGo uses redirect URLs
                    actual_link = link
                    if "uddg=" in link:
                        # Extract actual URL from DuckDuckGo redirect
                        uddg_match = re.search(r'uddg=([^&]+)', link)
                        if uddg_match:
                            actual_link = urllib.parse.unquote(uddg_match.group(1))
                    
                    # Clean HTML tags from title
                    clean_title = re.sub(r'<[^>]+>', '', title).strip()
                    
                    # Get snippet if available
                    snippet = ""
                    if i < len(snippets):
                        snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                    
                    # Extract domain
                    domain_match = re.search(r'https?://([^/]+)', actual_link)
                    source = domain_match.group(1) if domain_match else ""
                    
                    # Skip ads and invalid links
                    if clean_title and actual_link.startswith("http") and "duckduckgo.com" not in actual_link:
                        results.append({
                            "title": clean_title,
                            "snippet": snippet,
                            "link": actual_link,
                            "source": source
                        })
                
                if results:
                    return results
                    
                # If no results, wait and retry
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                    
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(1)
            else:
                return [{"error": f"Search failed after {retries} attempts: {str(e)}"}]
    
    return [{"error": "No results found"}]


async def google_news_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """Search for news using DuckDuckGo with news keywords."""
    # Add news-related keywords to get recent news results
    return await duckduckgo_search(f"{query} news latest 2024 2025", num_results)


async def fact_check_search(claim: str, num_results: int = 5) -> List[Dict[str, str]]:
    """Search for fact-checks from reputable fact-checking sites using scraping."""
    # Add fact-checking sites to the query
    fact_check_query = f"{claim} site:snopes.com OR site:factcheck.org OR site:politifact.com OR site:reuters.com/fact-check"
    
    try:
        return await google_search(fact_check_query, num_results)
    except Exception as e:
        return [{"error": f"Fact-check search failed: {str(e)}"}]


async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Execute a tool and return the result as a string."""
    if tool_name == "google_search":
        results = await google_search(arguments.get("query", ""))
    elif tool_name == "google_news_search":
        results = await google_news_search(arguments.get("query", ""))
    elif tool_name == "fact_check_search":
        results = await fact_check_search(arguments.get("claim", ""))
    else:
        results = [{"error": f"Unknown tool: {tool_name}"}]
    
    result_json = json.dumps(results, indent=2)
    print(f"[Agent] Tool {tool_name} returned: {result_json[:500]}...")  # Log first 500 chars
    return result_json


NEWS_DETECTION_PROMPT = """Analyze the following message and determine if it is news or a claim that should be fact-checked.

Message: {text}

Respond with ONLY a JSON object in this exact format:
{{"is_news": true/false, "reason": "brief explanation"}}

Consider it NEWS or FACT-CHECKABLE if it:
- Reports on current events, politics, sports, entertainment, science, or world affairs
- Contains claims about real-world events, people, or organizations
- Appears to share information meant to inform about happenings
- Makes factual claims that can be verified
- Forwards or shares news-like content

Do NOT consider it news if it's:
- Personal conversation or greeting (e.g., "Hi, how are you?")
- Random text or spam
- Questions without factual claims
- Opinions clearly stated as opinions
- Advertisements or promotional content without news claims
- Very short messages with no substantive claims"""


SYSTEM_PROMPT = """You are an expert fact-checker and misinformation detection agent. Your job is to analyze text and determine if it contains misinformation or fake news.

You have access to the following tools:
1. google_search - Search Google for general information to verify facts
2. google_news_search - Search Google News for recent news coverage
3. fact_check_search - Search fact-checking websites for existing fact-checks

IMPORTANT INSTRUCTIONS:
1. First, identify the key claims in the text that need verification
2. Use your tools to search for evidence - check multiple sources
3. Look for:
   - Whether the claim is being reported by credible news sources
   - Whether fact-checkers have already verified/debunked the claim
   - Contradictory information from reliable sources
   - Signs of satire, parody, or obvious fabrication

4. After gathering evidence, provide your final assessment in this EXACT JSON format:
{
    "is_misinformation": true/false,
    "confidence": 0.0-1.0,
    "summary": "Brief explanation of your findings",
    "evidence": ["List of key evidence points that support your conclusion"],
    "sources_checked": ["Include actual URLs from search results, e.g. https://example.com/article"],
    "recommendation": "What the user should know or do"
}

IMPORTANT: 
- In "sources_checked", include the actual URLs/links from the search results you received
- In "evidence", provide specific facts you found that support your conclusion
- Be thorough but efficient. If a claim is obviously absurd (like a historical figure being found alive), you can make a quick determination. For nuanced claims, gather more evidence."""


async def detect_if_news(text: str) -> Dict[str, Any]:
    """
    Detect if the text is news/fact-checkable content.
    
    Returns:
        Dictionary with is_news boolean and reason
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": NEWS_DETECTION_PROMPT.format(text=text)}
            ],
            temperature=0.1,
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        return json.loads(result_text)
    except Exception as e:
        print(f"Error detecting news: {e}")
        # Default to treating it as news to be safe
        return {"is_news": True, "reason": "Could not determine, treating as potential news"}


async def analyze_with_agent(text: str) -> Dict[str, Any]:
    """
    Analyze text for misinformation using an AI agent with tools.
    
    Args:
        text: The text to analyze
        
    Returns:
        Dictionary with analysis results
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Please analyze the following text for misinformation:\n\n{text}"}
    ]
    
    max_iterations = 10  # Prevent infinite loops
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        
        # Call OpenAI with tools
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )
        
        assistant_message = response.choices[0].message
        
        # Build message dict for history
        msg_dict = {"role": "assistant", "content": assistant_message.content or ""}
        if assistant_message.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                }
                for tc in assistant_message.tool_calls
            ]
        messages.append(msg_dict)
        
        # Check if the model wants to use tools
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                print(f"[Agent] Calling tool: {tool_name} with args: {arguments}")
                
                # Execute the tool
                tool_result = await execute_tool(tool_name, arguments)
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "content": tool_result,
                    "tool_call_id": tool_call.id
                })
        else:
            # No more tool calls, agent is done - parse the final response
            break
    
    # Parse the final response
    final_content = assistant_message.content
    print(f"[Agent] Final response: {final_content[:1000] if final_content else 'None'}...")
    
    try:
        # Try to extract JSON from the response
        if "```json" in final_content:
            json_str = final_content.split("```json")[1].split("```")[0].strip()
        elif "```" in final_content:
            json_str = final_content.split("```")[1].split("```")[0].strip()
        elif "{" in final_content and "}" in final_content:
            # Find the JSON object in the response
            start = final_content.find("{")
            end = final_content.rfind("}") + 1
            json_str = final_content[start:end]
        else:
            json_str = final_content
            
        result = json.loads(json_str)
        
        # Ensure required fields exist
        return {
            "is_misinformation": result.get("is_misinformation", False),
            "confidence": result.get("confidence", 0.5),
            "summary": result.get("summary", "Analysis complete"),
            "evidence": result.get("evidence", []),
            "sources_checked": result.get("sources_checked", []),
            "recommendation": result.get("recommendation", "Verify with trusted sources")
        }
    except json.JSONDecodeError:
        # If parsing fails, return a default response
        return {
            "is_misinformation": False,
            "confidence": 0.5,
            "summary": final_content[:500] if final_content else "Could not complete analysis",
            "evidence": [],
            "sources_checked": [],
            "recommendation": "Manual verification recommended"
        }
