"""
scraper.py
==============

This module contains the core scraping logic for retrieving product and
seller information from Daraz Nepal. The public function
``search_products`` accepts a free‑form search term and returns a list of
product dictionaries in the same order that Daraz presents them on the
first results page. Each dictionary includes comprehensive product information
including name, price, seller details, ratings, and more.

The scraping routines rely on the ``requests`` library to fetch HTML
pages and ``BeautifulSoup`` to parse them. A modern user agent string
is supplied with every request to reduce the chance of being blocked.
"""

from __future__ import annotations

import time
import re
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Base domain for Daraz Nepal
BASE_URL = "https://www.daraz.com.np"

# Headers to mimic a real browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def fetch_html(url: str, *, max_retries: int = 3, delay: float = 1.0) -> str:
    """Fetch HTML content from the given URL with retry logic.
    
    Args:
        url: The absolute URL to request.
        max_retries: How many times to retry on network failure.
        delay: Base delay in seconds between retries.
        
    Returns:
        The raw HTML document as a string.
        
    Raises:
        requests.HTTPError: If the final attempt does not return HTTP 200.
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay * (2 ** attempt))
    raise RuntimeError("Unreachable code in fetch_html")


def parse_search_results(html: str) -> List[Dict[str, str]]:
    """Parse the search results page into a list of product summaries.
    
    Args:
        html: The raw HTML string of a Daraz search page.
        
    Returns:
        A list of dictionaries with keys ``name``, ``price``, ``url``, ``image_url``.
    """
    soup = BeautifulSoup(html, "html.parser")
    products: List[Dict[str, str]] = []
    
    # Try multiple selectors for product cards as Daraz may use different structures
    product_selectors = [
        "div[data-qa-locator='product-item']",
        "div.product-item",
        "div[class*='product-item']",
        "div[class*='ProductItem']",
        "div[class*='product-card']",
        "div[class*='ProductCard']"
    ]
    
    product_cards = []
    for selector in product_selectors:
        cards = soup.select(selector)
        if cards:
            product_cards = cards
            break
    
    # If no specific product cards found, try to find any div containing product links
    if not product_cards:
        # Look for links containing '/products/'
        product_links = soup.find_all('a', href=re.compile(r'/products/'))
        for link in product_links:
            # Find the parent container that likely contains the product info
            parent = link.find_parent(['div', 'article', 'section'])
            if parent:
                product_cards.append(parent)
    
    for card in product_cards:
        try:
            # Extract product link
            link = card.find('a', href=re.compile(r'/products/'))
            if not link:
                continue
                
            href = link.get('href', '')
            if not href:
                continue
                
            # Build full URL
            if href.startswith('//'):
                product_url = 'https:' + href
            elif href.startswith('/'):
                product_url = BASE_URL + href
            elif href.startswith('http'):
                product_url = href
            else:
                product_url = BASE_URL + '/' + href
            
            # Extract product name
            name_selectors = [
                'div[class*="title"]',
                'div[class*="name"]',
                'div[class*="product-name"]',
                'h3', 'h4', 'h5',
                'span[class*="title"]',
                'span[class*="name"]'
            ]
            
            product_name = None
            for selector in name_selectors:
                name_elem = card.select_one(selector)
                if name_elem:
                    product_name = name_elem.get_text(strip=True)
                    if product_name and len(product_name) > 3:  # Ensure it's not just whitespace
                        break
            
            if not product_name:
                # Try to get text from the link itself
                product_name = link.get_text(strip=True)
            
            # Extract price
            price_selectors = [
                'span[class*="price"]',
                'div[class*="price"]',
                'span[class*="currency"]',
                'div[class*="currency"]',
                'span[class*="amount"]'
            ]
            
            price_text = None
            for selector in price_selectors:
                price_elem = card.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    if price_text and any(char.isdigit() for char in price_text):
                        break
            
            if product_name and product_url:
                products.append({
                    "name": product_name,
                    "price": price_text or "Price not available",
                    "url": product_url
                })
                
        except Exception as e:
            # Skip this product if there's an error
            continue
    
    return products


def parse_product_details(html: str, product_url: str) -> Dict[str, Any]:
    """Parse a product detail page and extract comprehensive information.
    
    Args:
        html: The raw HTML string of a Daraz product page.
        product_url: The URL of the product page.
        
    Returns:
        A dictionary containing detailed product information.
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # Initialize result dictionary
    product_details = {
        "product_name": "",
        "price": "",
        "original_price": "",
        "discount": "",
        "rating": "",
        "review_count": "",
        "seller_name": "",
        "seller_location": "",
        "seller_rating": "",
        "brand": "",
        "category": "",
        "availability": "",
        "description": "",
        "specifications": {},
        "product_url": product_url,
        "rank": 0,
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        # Extract product name
        name_selectors = [
            'h1[class*="pdp-product-name"]',
            'h1[class*="product-name"]',
            'h1[class*="title"]',
            'h1',
            'span[class*="pdp-product-name"]',
            'div[class*="product-name"]'
        ]
        
        for selector in name_selectors:
            name_elem = soup.select_one(selector)
            if name_elem:
                product_details["product_name"] = name_elem.get_text(strip=True)
                break
        
        # Extract current price
        price_selectors = [
            'span[class*="pdp-price"]',
            'span[class*="current-price"]',
            'span[class*="price-current"]',
            'div[class*="price-current"]',
            'span[class*="currency"]'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                product_details["price"] = price_elem.get_text(strip=True)
                break
        
        # Extract original price
        original_price_selectors = [
            'span[class*="original-price"]',
            'span[class*="price-original"]',
            'span[class*="price-before"]',
            'div[class*="price-original"]'
        ]
        
        for selector in original_price_selectors:
            orig_price_elem = soup.select_one(selector)
            if orig_price_elem:
                product_details["original_price"] = orig_price_elem.get_text(strip=True)
                break
        
        # Extract discount
        discount_selectors = [
            'span[class*="discount"]',
            'div[class*="discount"]',
            'span[class*="sale"]',
            'div[class*="sale"]'
        ]
        
        for selector in discount_selectors:
            discount_elem = soup.select_one(selector)
            if discount_elem:
                product_details["discount"] = discount_elem.get_text(strip=True)
                break
        
        # Extract rating
        rating_selectors = [
            'span[class*="rating"]',
            'div[class*="rating"]',
            'span[class*="score"]',
            'div[class*="score"]'
        ]
        
        for selector in rating_selectors:
            rating_elem = soup.select_one(selector)
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                if rating_text and any(char.isdigit() for char in rating_text):
                    product_details["rating"] = rating_text
                    break
        
        # Extract review count
        review_selectors = [
            'span[class*="review"]',
            'div[class*="review"]',
            'span[class*="comment"]',
            'div[class*="comment"]'
        ]
        
        for selector in review_selectors:
            review_elem = soup.select_one(selector)
            if review_elem:
                review_text = review_elem.get_text(strip=True)
                if review_text and any(char.isdigit() for char in review_text):
                    product_details["review_count"] = review_text
                    break
        
        # Extract seller information using the specific selector you provided
        try:
            seller_elem = soup.select_one('div.seller-name__detail a.seller-name__detail-name')
            if seller_elem:
                product_details["seller_name"] = seller_elem.get_text(strip=True)
        except:
            # Fallback to other selectors if the specific one doesn't work
            seller_selectors = [
                'a[class*="seller"]',
                'div[class*="seller"]',
                'span[class*="seller"]',
                'a[href*="seller"]'
            ]
            
            for selector in seller_selectors:
                try:
                    seller_elem = soup.select_one(selector)
                    if seller_elem:
                        product_details["seller_name"] = seller_elem.get_text(strip=True)
                        break
                except:
                    continue
        
        # Extract brand
        brand_selectors = [
            'span[class*="brand"]',
            'div[class*="brand"]',
            'a[class*="brand"]'
        ]
        
        for selector in brand_selectors:
            brand_elem = soup.select_one(selector)
            if brand_elem:
                product_details["brand"] = brand_elem.get_text(strip=True)
                break
        
        # Extract availability
        availability_selectors = [
            'span[class*="stock"]',
            'div[class*="stock"]',
            'span[class*="availability"]',
            'div[class*="availability"]'
        ]
        
        for selector in availability_selectors:
            avail_elem = soup.select_one(selector)
            if avail_elem:
                product_details["availability"] = avail_elem.get_text(strip=True)
                break
        
        # Image extraction removed for cleaner response
        
        # Extract description
        desc_selectors = [
            'div[class*="description"]',
            'div[class*="detail"]',
            'div[class*="content"]',
            'p[class*="description"]'
        ]
        
        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                product_details["description"] = desc_elem.get_text(strip=True)
                break
        
    except Exception as e:
        # If there's an error, at least return the basic info we have
        pass
    
    return product_details


def get_product_details(product_url: str) -> Dict[str, Any]:
    """Fetch a product page and extract detailed information.
    
    Args:
        product_url: The absolute URL of the product page.
        
    Returns:
        A dictionary containing detailed product information.
    """
    try:
        html = fetch_html(product_url)
        return parse_product_details(html, product_url)
    except Exception as e:
        # Return basic info if detailed scraping fails
        return {
            "product_name": "Product details unavailable",
            "price": "Price unavailable",
            "original_price": "",
            "discount": "",
            "rating": "",
            "review_count": "",
            "seller_name": "",
            "seller_location": "",
            "seller_rating": "",
            "brand": "",
            "category": "",
            "availability": "",
            "description": "",
            "specifications": {},
            "product_url": product_url,
            "rank": 0,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "error": str(e)
        }


def search_products(query: str, *, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search Daraz for a keyword and return comprehensive product details.
    
    This function first tries the basic requests-based approach, and if that fails
    (likely due to JavaScript-rendered content), it falls back to Selenium.
    
    Args:
        query: A free‑text search term (e.g. "toothpaste", "tshirt").
        max_results: Maximum number of products to fetch. Defaults to 10.
        
    Returns:
        A list of dictionaries containing comprehensive product information.
    """
    try:
        # Build the search URL
        encoded_query = requests.utils.quote(query)
        search_url = f"{BASE_URL}/catalog/?q={encoded_query}"
        
        # Fetch search results
        search_html = fetch_html(search_url)
        product_summaries = parse_search_results(search_html)
        
        if not product_summaries:
            # If basic scraping returns no results, try Selenium
            print("Basic scraping returned no results, trying Selenium...")
            try:
                from scraper_selenium import search_products_selenium
                return search_products_selenium(query, max_results=max_results, headless=True)
            except ImportError:
                print("Selenium not available, returning empty results")
                return []
            except Exception as e:
                print(f"Selenium scraping failed: {str(e)}")
                return []
        
        # Limit results
        product_summaries = product_summaries[:max_results]
        
        # Get detailed information for each product
        results: List[Dict[str, Any]] = []
        for i, summary in enumerate(product_summaries):
            try:
                # Get detailed product information
                detailed_info = get_product_details(summary["url"])
                
                # Merge summary info with detailed info
                result = {
                    **detailed_info,
                    "product_name": detailed_info.get("product_name") or summary.get("name", "Unknown Product"),
                    "price": detailed_info.get("price") or summary.get("price", "Price not available"),
                    "rank": i + 1,  # Set rank (1-based indexing)
                }
                
                results.append(result)
                
                # Add a small delay to be respectful to the server
                time.sleep(0.5)
                
            except Exception as e:
                # If detailed scraping fails, at least return the summary info
                results.append({
                    "product_name": summary.get("name", "Unknown Product"),
                    "price": summary.get("price", "Price not available"),
                    "seller_name": None,
                    "seller_location": None,
                    "product_url": summary.get("url", ""),
                    "rank": i + 1,  # Set rank even for failed extractions
                    "error": f"Failed to get detailed info: {str(e)}"
                })
        
        return results
        
    except Exception as e:
        # If basic approach fails completely, try Selenium
        print(f"Basic scraping failed: {str(e)}, trying Selenium...")
        try:
            from scraper_selenium import search_products_selenium
            return search_products_selenium(query, max_results=max_results, headless=True)
        except ImportError:
            print("Selenium not available")
            return [{"error": f"Search failed: {str(e)}"}]
        except Exception as selenium_error:
            print(f"Selenium also failed: {str(selenium_error)}")
            return [{"error": f"Search failed: {str(e)}. Selenium error: {str(selenium_error)}"}]