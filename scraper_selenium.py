"""
scraper_selenium.py
==================

This module contains the Selenium-based scraping logic for retrieving product and
seller information from Daraz Nepal. It handles JavaScript-rendered content
that the basic requests-based scraper cannot access.

The scraper uses Selenium WebDriver to render the page and then extracts
comprehensive product information including name, price, seller details, ratings, etc.
"""

from __future__ import annotations

import time
import re
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Base domain for Daraz Nepal
BASE_URL = "https://www.daraz.com.np"


def create_driver(headless: bool = True) -> webdriver.Chrome:
    """Create and configure a Chrome WebDriver instance.
    
    Args:
        headless: Whether to run the browser in headless mode.
        
    Returns:
        Configured Chrome WebDriver instance.
    """
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless")
    
    # Add various options to make the browser less detectable
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Disable images and CSS to speed up loading
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        raise Exception(f"Failed to create WebDriver: {str(e)}")


def search_products_selenium(query: str, *, max_results: int = 10, headless: bool = True) -> List[Dict[str, Any]]:
    """Search Daraz for a keyword using Selenium and return comprehensive product details.
    
    Args:
        query: A free‑text search term (e.g. "toothpaste", "tshirt").
        max_results: Maximum number of products to fetch. Defaults to 10.
        headless: Whether to run the browser in headless mode.
        
    Returns:
        A list of dictionaries containing comprehensive product information.
    """
    driver = None
    try:
        # Create WebDriver
        driver = create_driver(headless=headless)
        
        # Build search URL
        encoded_query = requests.utils.quote(query)
        search_url = f"{BASE_URL}/catalog/?q={encoded_query}"
        
        print(f"Loading search page: {search_url}")
        driver.get(search_url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 20)
        
        # Wait for product elements to appear
        try:
            # Try multiple possible selectors for product containers
            product_selectors = [
                "div[data-qa-locator='product-item']",
                "div[class*='product-item']",
                "div[class*='ProductItem']",
                "div[class*='product-card']",
                "div[class*='ProductCard']",
                "div[class*='item']",
                "div[class*='Item']"
            ]
            
            product_elements = []
            for selector in product_selectors:
                try:
                    elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                    if elements:
                        product_elements = elements
                        print(f"Found {len(elements)} products using selector: {selector}")
                        break
                except TimeoutException:
                    continue
            
            if not product_elements:
                # If no specific product containers found, look for any links to products
                product_links = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='/products/']")))
                if product_links:
                    print(f"Found {len(product_links)} product links")
                    # Get unique product URLs
                    product_urls = list(set([link.get_attribute('href') for link in product_links if link.get_attribute('href')]))
                    return get_products_from_urls(product_urls[:max_results], driver)
                else:
                    return []
            
        except TimeoutException:
            print("Timeout waiting for product elements to load")
            return []
        
        # Extract product information - collect URLs first to avoid stale elements
        product_urls = []
        for i, element in enumerate(product_elements[:max_results]):
            try:
                # Extract URL first before any navigation
                link = element.find_element(By.CSS_SELECTOR, "a[href*='/products/']")
                product_url = link.get_attribute('href')
                if product_url:
                    if product_url.startswith('//'):
                        product_url = 'https:' + product_url
                    elif product_url.startswith('/'):
                        product_url = BASE_URL + product_url
                    product_urls.append((i + 1, product_url))  # Store rank and URL
            except Exception as e:
                print(f"Error extracting URL from element {i+1}: {e}")
                continue
        
        # Now process each product URL
        results = []
        for rank, product_url in product_urls:
            try:
                print(f"Processing product {rank}: {product_url}")
                
                # Visit the product page
                driver.get(product_url)
                time.sleep(2)  # Wait for page to load
                
                # Extract all product information from the product page
                product_info = get_product_details_selenium(product_url, driver)
                if product_info:
                    product_info["rank"] = rank
                    results.append(product_info)
                    print(f"Extracted product {rank}: {product_info.get('product_name', 'Unknown')[:50]}...")
                
            except Exception as e:
                print(f"Error processing product {rank}: {e}")
                continue
        
        return results
        
    except Exception as e:
        print(f"Error in search_products_selenium: {str(e)}")
        return [{"error": f"Search failed: {str(e)}"}]
    
    finally:
        if driver:
            driver.quit()


def extract_product_info_from_element(element, driver) -> Optional[Dict[str, Any]]:
    """Extract product information from a product element.
    
    Args:
        element: Selenium WebElement containing product information.
        driver: WebDriver instance.
        
    Returns:
        Dictionary containing product information or None if extraction fails.
    """
    try:
        product_info = {
            "product_name": "",
            "price": "",
            "original_price": "",
            "discount": "",
            "rating": "",
            "review_count": "",
            "seller_name": "",
            "seller_location": "",
            "brand": "",
            "availability": "",
            "product_url": "",
            "rank": 0,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Extract product URL
        try:
            link = element.find_element(By.CSS_SELECTOR, "a[href*='/products/']")
            product_url = link.get_attribute('href')
            if product_url:
                if product_url.startswith('//'):
                    product_url = 'https:' + product_url
                elif product_url.startswith('/'):
                    product_url = BASE_URL + product_url
                product_info["product_url"] = product_url
        except NoSuchElementException:
            pass
        
        # Extract product name - based on actual Daraz structure
        name_selectors = [
            "div.RfADt",  # Specific class found in testing
            "a[href*='/products/']",  # Product link often contains the name
            "div[class*='title']",
            "div[class*='name']",
            "div[class*='product-name']",
            "h3", "h4", "h5",
            "span[class*='title']",
            "span[class*='name']",
            "a[class*='title']"
        ]
        
        for selector in name_selectors:
            try:
                name_elem = element.find_element(By.CSS_SELECTOR, selector)
                name_text = name_elem.text.strip()
                # Clean up the text - remove price and other info, keep only the product name
                if name_text:
                    # Split by newlines and take the first line (usually the product name)
                    lines = name_text.split('\n')
                    clean_name = lines[0].strip()
                    if clean_name and len(clean_name) > 3 and not clean_name.startswith('Rs.'):
                        product_info["product_name"] = clean_name
                        break
            except NoSuchElementException:
                continue
        
        # Extract price - look for "Rs." pattern in text
        try:
            # Get all text content and look for price pattern
            all_text = element.text
            import re
            price_match = re.search(r'Rs\.\s*[\d,]+', all_text)
            if price_match:
                product_info["price"] = price_match.group()
        except:
            pass
        
        # Also try specific selectors as fallback
        price_selectors = [
            "span[class*='price']",
            "div[class*='price']",
            "span[class*='currency']",
            "div[class*='currency']",
            "span[class*='amount']"
        ]
        
        if not product_info["price"]:  # Only try selectors if regex didn't find price
            for selector in price_selectors:
                try:
                    price_elem = element.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_elem.text.strip()
                    if price_text and any(char.isdigit() for char in price_text):
                        product_info["price"] = price_text
                        break
                except NoSuchElementException:
                    continue
        
        # Image URL extraction removed for cleaner response
        
        # Extract rating
        rating_selectors = [
            "span[class*='rating']",
            "div[class*='rating']",
            "span[class*='score']",
            "div[class*='score']"
        ]
        
        for selector in rating_selectors:
            try:
                rating_elem = element.find_element(By.CSS_SELECTOR, selector)
                rating_text = rating_elem.text.strip()
                if rating_text and any(char.isdigit() for char in rating_text):
                    product_info["rating"] = rating_text
                    break
            except NoSuchElementException:
                continue
        
        # Extract review count
        review_selectors = [
            "span[class*='review']",
            "div[class*='review']",
            "span[class*='comment']",
            "div[class*='comment']"
        ]
        
        for selector in review_selectors:
            try:
                review_elem = element.find_element(By.CSS_SELECTOR, selector)
                review_text = review_elem.text.strip()
                if review_text and any(char.isdigit() for char in review_text):
                    product_info["review_count"] = review_text
                    break
            except NoSuchElementException:
                continue
        
        # Extract seller location - look for location patterns in text
        try:
            all_text = element.text
            import re
            # Look for common location patterns
            location_patterns = [
                r'([A-Za-z\s]+Province)',
                r'([A-Za-z\s]+District)',
                r'([A-Za-z\s]+City)',
                r'([A-Za-z\s]+Nepal)'
            ]
            
            for pattern in location_patterns:
                location_match = re.search(pattern, all_text)
                if location_match:
                    location = location_match.group(1).strip()
                    if location and len(location) > 3:
                        product_info["seller_location"] = location
                        break
        except:
            pass
        
        return product_info if product_info["product_name"] else None
        
    except Exception as e:
        print(f"Error extracting product info: {str(e)}")
        return None


def get_product_details_selenium(product_url: str, driver: webdriver.Chrome) -> Dict[str, Any]:
    """Get detailed product information from a single product URL.
    
    Args:
        product_url: Product URL to scrape.
        driver: WebDriver instance.
        
    Returns:
        Dictionary containing detailed product information.
    """
    try:
        print(f"Scraping product: {product_url}")
        driver.get(product_url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        
        product_info = {
            "product_name": "",
            "price": "",
            "original_price": "",
            "discount": "",
            "rating": "",
            "review_count": "",
            "seller_name": "",
            "seller_location": "",
            "brand": "",
            "availability": "",
            "product_url": product_url,
            "rank": 0,  # Will be set by caller
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Extract product name
        name_selectors = [
            "h1[class*='pdp-product-name']",
            "h1[class*='product-name']",
            "h1[class*='title']",
            "h1",
            "span[class*='pdp-product-name']",
            "div[class*='product-name']"
        ]
        
        for selector in name_selectors:
            try:
                name_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                if name_elem:
                    product_info["product_name"] = name_elem.text.strip()
                    break
            except TimeoutException:
                continue
        
        # Extract price
        price_selectors = [
            "span[class*='pdp-price']",
            "span[class*='current-price']",
            "span[class*='price-current']",
            "div[class*='price-current']",
            "span[class*='currency']"
        ]
        
        for selector in price_selectors:
            try:
                price_elem = driver.find_element(By.CSS_SELECTOR, selector)
                if price_elem:
                    product_info["price"] = price_elem.text.strip()
                    break
            except NoSuchElementException:
                continue
        
        # Extract seller information using the specific selector you provided
        try:
            seller_elem = driver.find_element(By.CSS_SELECTOR, "div.seller-name__detail a.seller-name__detail-name")
            if seller_elem:
                product_info["seller_name"] = seller_elem.text.strip()
        except NoSuchElementException:
            # Fallback to other selectors if the specific one doesn't work
            seller_selectors = [
                "a[class*='seller']",
                "div[class*='seller']",
                "span[class*='seller']",
                "a[href*='seller']"
            ]
            
            for selector in seller_selectors:
                try:
                    seller_elem = driver.find_element(By.CSS_SELECTOR, selector)
                    if seller_elem:
                        product_info["seller_name"] = seller_elem.text.strip()
                        break
                except NoSuchElementException:
                    continue
        
        # Extract brand
        brand_selectors = [
            "span[class*='brand']",
            "div[class*='brand']",
            "a[class*='brand']"
        ]
        
        for selector in brand_selectors:
            try:
                brand_elem = driver.find_element(By.CSS_SELECTOR, selector)
                if brand_elem:
                    product_info["brand"] = brand_elem.text.strip()
                    break
            except NoSuchElementException:
                continue
        
        # Extract availability
        availability_selectors = [
            "span[class*='stock']",
            "div[class*='stock']",
            "span[class*='availability']",
            "div[class*='availability']"
        ]
        
        for selector in availability_selectors:
            try:
                avail_elem = driver.find_element(By.CSS_SELECTOR, selector)
                if avail_elem:
                    product_info["availability"] = avail_elem.text.strip()
                    break
            except NoSuchElementException:
                continue
            
        return product_info
        
    except Exception as e:
        print(f"Error scraping product {product_url}: {str(e)}")
        return None


def get_products_from_urls(product_urls: List[str], driver: webdriver.Chrome) -> List[Dict[str, Any]]:
    """Get detailed product information from a list of product URLs.
    
    Args:
        product_urls: List of product URLs to scrape.
        driver: WebDriver instance.
        
    Returns:
        List of dictionaries containing detailed product information.
    """
    results = []
    
    for i, url in enumerate(product_urls):
        try:
            product_info = get_product_details_selenium(url, driver)
            if product_info:
                product_info["rank"] = i + 1
                results.append(product_info)
        except Exception as e:
            print(f"Error processing product {i+1}: {e}")
            continue
    
    return results


# Import requests for URL encoding
import requests
