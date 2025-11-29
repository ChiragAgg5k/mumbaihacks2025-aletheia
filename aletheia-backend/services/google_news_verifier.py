"""
Google News Scraper and Verifier

This module uses Selenium to search Google News, extract search results,
and scrape article content for misinformation verification.
"""

import time
import re
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus, urlparse
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import os


class GoogleNewsVerifier:
    """
    Scrapes Google News to verify headlines and detect misinformation
    """
    
    def __init__(self, headless: bool = True):
        """
        Initialize the Google News scraper
        
        Args:
            headless: Run browser in headless mode (no GUI)
        """
        self.headless = headless
        self.driver = None
        
    def _init_driver(self):
        """Initialize Brave WebDriver (or Chrome as fallback)"""
        if self.driver is not None:
            return
            
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        # Common options for stability
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Try to find Brave browser first, fallback to Chrome
        brave_paths = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        
        brave_found = False
        for brave_path in brave_paths:
            if os.path.exists(brave_path):
                chrome_options.binary_location = brave_path
                brave_found = True
                print(f"Using Brave browser: {brave_path}")
                break
        
        if not brave_found:
            print("Brave not found, using Chrome")
        
        # Use Selenium's automatic driver management (available in Selenium 4.6+)
        # No need for webdriver-manager - Selenium will automatically download and use the correct driver
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print(f"Successfully initialized {'Brave' if brave_found else 'Chrome'} driver")
        except Exception as e:
            print(f"Error initializing driver: {e}")
            raise
        self.driver.implicitly_wait(10)
    
    def _close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def search_google_news(self, headline: str, max_results: int = 10) -> List[Dict[str, str]]:
        """
        Search Google News for a headline
        
        Args:
            headline: The headline to search for
            max_results: Maximum number of results to return (default: 10)
            
        Returns:
            List of dictionaries containing title, url, source, and snippet
        """
        self._init_driver()
        
        # Construct Google News search URL
        search_query = quote_plus(headline)
        url = f"https://news.google.com/search?q={search_query}&hl=en-US&gl=US&ceid=US:en"
        
        try:
            print(f"Searching Google News: {url}")
            self.driver.get(url)
            
            # Wait longer for page to load
            time.sleep(5)
            
            results = []
            
            # Try multiple strategies to find articles
            selectors_to_try = [
                'article',
                'div.xrnccd',  # Common Google News wrapper
                'c-wiz > div > div',  # Alternative structure
            ]
            
            articles = []
            for selector in selectors_to_try:
                articles = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if articles:
                    print(f"Found {len(articles)} elements with selector: {selector}")
                    break
            
            if not articles:
                # Save page source for debugging
                page_source = self.driver.page_source
                print(f"No articles found. Page title: {self.driver.title}")
                print(f"Page source length: {len(page_source)} chars")
                
                # Try to find any links as fallback
                all_links = self.driver.find_elements(By.TAG_NAME, 'a')
                print(f"Found {len(all_links)} total links on page")
                
                # Filter for news-like links
                for i, link in enumerate(all_links[:max_results * 2]):
                    try:
                        href = link.get_attribute('href')
                        text = link.text.strip()
                        
                        if text and len(text) > 10 and 'google.com/url' in href:
                            results.append({
                                'title': text,
                                'url': href,
                                'source': "Google News",
                                'snippet': "",
                                'rank': len(results) + 1
                            })
                            
                            if len(results) >= max_results:
                                break
                    except:
                        continue
                
                return results
            
            # Process found articles
            for i, article in enumerate(articles[:max_results * 2]):  # Check more than needed
                try:
                    # Try to find title link
                    link_selectors = ['a.JtKRv', 'a.gPFEn', 'a', 'h3 a', 'h4 a']
                    title_element = None
                    
                    for link_sel in link_selectors:
                        try:
                            title_element = article.find_element(By.CSS_SELECTOR, link_sel)
                            if title_element and title_element.text.strip():
                                break
                        except NoSuchElementException:
                            continue
                    
                    if not title_element:
                        continue
                    
                    title = title_element.text.strip()
                    link = title_element.get_attribute('href')
                    
                    if not title or len(title) < 10:
                        continue
                    
                    # Extract source
                    source = "Unknown"
                    source_selectors = ['div[data-n-tid]', 'div.vr1PYe', 'span.vr1PYe', 'div.CEMjEf']
                    for src_sel in source_selectors:
                        try:
                            source_element = article.find_element(By.CSS_SELECTOR, src_sel)
                            source = source_element.text.strip()
                            if source:
                                break
                        except NoSuchElementException:
                            continue
                    
                    # Extract snippet/description
                    snippet = ""
                    snippet_selectors = ['div.xBbh9', 'div.Rai5ob', 'span.xBbh9']
                    for snip_sel in snippet_selectors:
                        try:
                            snippet_element = article.find_element(By.CSS_SELECTOR, snip_sel)
                            snippet = snippet_element.text.strip()
                            if snippet:
                                break
                        except NoSuchElementException:
                            continue
                    
                    results.append({
                        'title': title,
                        'url': link,
                        'source': source,
                        'snippet': snippet,
                        'rank': len(results) + 1
                    })
                    
                    if len(results) >= max_results:
                        break
                    
                except Exception as e:
                    continue
            
            print(f"Successfully extracted {len(results)} articles")
            return results
            
        except Exception as e:
            print(f"Error searching Google News: {e}")
            return []
    
    def extract_article_content(self, url: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Extract content from a news article
        
        Args:
            url: URL of the article
            timeout: Maximum time to wait for page load
            
        Returns:
            Dictionary with article content, metadata, and backlinks
        """
        if not self.driver:
            self._init_driver()
        
        try:
            self.driver.get(url)
            
            # Wait for body to load
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            
            time.sleep(2)  # Additional wait for dynamic content
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text() if title else ""
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ""
            
            # Extract author
            author = ""
            author_meta = soup.find('meta', attrs={'name': 'author'})
            if author_meta:
                author = author_meta.get('content', '')
            
            # Extract publish date
            publish_date = ""
            date_meta = soup.find('meta', attrs={'property': 'article:published_time'})
            if date_meta:
                publish_date = date_meta.get('content', '')
            
            # Extract main content (try common article selectors)
            content = ""
            content_selectors = [
                'article',
                '[role="article"]',
                '.article-content',
                '.post-content',
                '.entry-content',
                'main'
            ]
            
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    # Get text from paragraphs
                    paragraphs = content_element.find_all('p')
                    content = ' '.join([p.get_text().strip() for p in paragraphs])
                    if content:
                        break
            
            # Extract all links (backlinks)
            links = []
            for a_tag in soup.find_all('a', href=True):
                href = a_tag.get('href', '')
                if href.startswith('http'):
                    links.append({
                        'url': href,
                        'text': a_tag.get_text().strip()[:100]  # Limit text length
                    })
            
            # Get domain
            domain = urlparse(url).netloc
            
            return {
                'url': url,
                'domain': domain,
                'title': title_text,
                'description': description,
                'author': author,
                'publish_date': publish_date,
                'content': content[:5000],  # Limit content length
                'content_length': len(content),
                'backlinks_count': len(links),
                'backlinks': links[:50],  # Limit backlinks
                'success': True
            }
            
        except TimeoutException:
            return {
                'url': url,
                'error': 'Page load timeout',
                'success': False
            }
        except Exception as e:
            return {
                'url': url,
                'error': str(e),
                'success': False
            }
    
    def verify_headline(
        self,
        headline: str,
        max_articles: int = 10
    ) -> Dict[str, Any]:
        """
        Verify a headline by searching Google News and analyzing results
        
        Args:
            headline: The headline to verify
            max_articles: Maximum number of articles to analyze
            
        Returns:
            Dictionary with verification results
        """
        try:
            # Search Google News
            search_results = self.search_google_news(headline, max_results=max_articles)
            
            if not search_results:
                return {
                    'headline': headline,
                    'verified': False,
                    'confidence': 0.0,
                    'reason': 'No news articles found for this headline',
                    'sources_checked': 0
                }
            
            # Analyze top articles
            articles_data = []
            reputable_sources = []
            
            for result in search_results[:max_articles]:
                # Extract article content
                article_data = self.extract_article_content(result['url'])
                
                if article_data['success']:
                    article_data['google_news_rank'] = result['rank']
                    article_data['google_news_source'] = result['source']
                    articles_data.append(article_data)
                    
                    # Check for reputable sources
                    domain = article_data['domain'].lower()
                    if any(source in domain for source in [
                        'bbc.com', 'cnn.com', 'nytimes.com', 'reuters.com',
                        'apnews.com', 'theguardian.com', 'washingtonpost.com',
                        'npr.org', 'bloomberg.com', 'wsj.com', 'ft.com'
                    ]):
                        reputable_sources.append(article_data)
                
                time.sleep(1)  # Be nice to servers
            
            return {
                'headline': headline,
                'search_results_count': len(search_results),
                'articles_analyzed': len(articles_data),
                'reputable_sources_count': len(reputable_sources),
                'search_results': search_results,
                'articles_data': articles_data,
                'reputable_sources': reputable_sources,
                'success': True
            }
            
        except Exception as e:
            return {
                'headline': headline,
                'error': str(e),
                'success': False
            }
        finally:
            self._close_driver()
    
    def __enter__(self):
        """Context manager entry"""
        self._init_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self._close_driver()


def verify_news_headline(headline: str) -> Dict[str, Any]:
    """
    Verify a news headline using Google News search
    
    This is the main function to be used as a tool by the ADK agent.
    
    Args:
        headline: The news headline to verify
        
    Returns:
        Dictionary with verification results including sources and analysis
    """
    verifier = GoogleNewsVerifier(headless=True)
    result = verifier.verify_headline(headline, max_articles=10)
    verifier._close_driver()
    
    return result
