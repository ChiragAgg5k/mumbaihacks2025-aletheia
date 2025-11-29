"""
Simple test for Google News scraper (without ADK complexity)
"""

from services.google_news_verifier import verify_news_headline

def test_google_news():
    """Test Google News scraper directly"""
    print("="*80)
    print("TESTING GOOGLE NEWS SCRAPER")
    print("="*80)
    
    headlines = [
        "NASA announces new Mars rover discovery",
        "SHOCKING!!! Scientists discover cure for aging! Doctors HATE this!!!",
    ]
    
    for i, headline in enumerate(headlines, 1):
        print(f"\n\nTest {i}: {headline}")
        print("-" * 80)
        
        try:
            result = verify_news_headline(headline)
            
            print(f"\nFound {result.get('search_results_count', 0)} results")
            print(f"Analyzed {result.get('articles_analyzed', 0)} articles")
            print(f"Reputable sources: {result.get('reputable_sources_count', 0)}")
            
            print(f"\nTop search results:")
            for j, article in enumerate(result.get('search_results', [])[:5], 1):
                print(f"  {j}. [{article.get('source', 'Unknown')}] {article.get('title', 'No title')[:80]}")
                print(f"     URL: {article.get('url', 'No URL')[:80]}")
            
            if result.get('error'):
                print(f"\nError: {result['error']}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    test_google_news()
