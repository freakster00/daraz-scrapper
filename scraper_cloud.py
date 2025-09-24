"""
scraper_cloud.py
================

Cloud-optimized scraper that handles environments without Chrome browser.
Falls back to basic HTTP scraping when Selenium is not available.
"""

import requests
from bs4 import BeautifulSoup
import time
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode, urljoin

# Base URL for Daraz Nepal
BASE_URL = "https://www.daraz.com.np"

def search_products_cloud(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search for products on Daraz Nepal with cloud-optimized approach.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        List of product dictionaries
    """
    try:
        # First try basic HTTP scraping (works in cloud)
        results = search_products_basic(query, max_results)
        if results:
            print(f"Basic scraping found {len(results)} results")
            return results
        
        # If basic scraping fails, try Selenium (may not work in cloud)
        print("Basic scraping returned no results, trying Selenium...")
        try:
            results = search_products_selenium_cloud(query, max_results)
            if results:
                print(f"Selenium scraping found {len(results)} results")
                return results
        except Exception as e:
            print(f"Selenium scraping failed: {e}")
        
        # If both fail, return empty results
        print("All scraping methods failed")
        return []
        
    except Exception as e:
        print(f"Error in search_products_cloud: {e}")
        return []

def search_products_basic(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Basic HTTP scraping without Selenium.
    Works in cloud environments but may not get all dynamic content.
    """
    try:
        # Construct search URL
        search_url = f"{BASE_URL}/catalog/?q={urlencode({'q': query})[2:]}"
        print(f"Loading search page: {search_url}")
        
        # Set headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Make request with timeout
        response = requests.get(search_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for product containers
        product_elements = soup.find_all('div', {'data-qa-locator': 'product-item'})
        
        if not product_elements:
            # Try alternative selectors
            product_elements = soup.find_all('div', class_=re.compile(r'product.*item|item.*product'))
        
        if not product_elements:
            # Look for product links
            product_links = soup.find_all('a', href=re.compile(r'/products/'))
            if product_links:
                # Extract unique product URLs
                product_urls = list(set([link.get('href') for link in product_links if link.get('href')]))
                return get_products_from_urls_basic(product_urls[:max_results])
        
        if not product_elements:
            print("No product elements found")
            return []
        
        print(f"Found {len(product_elements)} products using basic scraping")
        
        # Extract product information
        results = []
        for i, element in enumerate(product_elements[:max_results]):
            try:
                product_info = extract_product_info_basic(element)
                if product_info and product_info.get("product_url"):
                    product_info["rank"] = i + 1
                    results.append(product_info)
                    print(f"Extracted product {i+1}: {product_info.get('product_name', 'Unknown')[:50]}...")
            except Exception as e:
                print(f"Error extracting product {i+1}: {e}")
                continue
        
        return results
        
    except Exception as e:
        print(f"Error in search_products_basic: {e}")
        return []

def extract_product_info_basic(element) -> Optional[Dict[str, Any]]:
    """Extract product information from HTML element using basic parsing."""
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
        link = element.find('a', href=re.compile(r'/products/'))
        if link:
            product_url = link.get('href')
            if product_url:
                if product_url.startswith('//'):
                    product_url = 'https:' + product_url
                elif product_url.startswith('/'):
                    product_url = BASE_URL + product_url
                product_info["product_url"] = product_url
        
        # Extract product name
        name_selectors = [
            'div[class*="title"]',
            'div[class*="name"]',
            'h3', 'h4', 'h5',
            'span[class*="title"]',
            'span[class*="name"]',
            'a[class*="title"]'
        ]
        
        for selector in name_selectors:
            name_elem = element.select_one(selector)
            if name_elem and name_elem.get_text(strip=True):
                product_info["product_name"] = name_elem.get_text(strip=True)
                break
        
        # Extract price
        price_selectors = [
            'span[class*="price"]',
            'div[class*="price"]',
            'span[class*="currency"]',
            'div[class*="currency"]'
        ]
        
        for selector in price_selectors:
            price_elem = element.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                if price_text and ('Rs.' in price_text or '₹' in price_text or re.search(r'\d+', price_text)):
                    product_info["price"] = price_text
                    break
        
        # Extract rating
        rating_elem = element.select_one('span[class*="rating"], div[class*="rating"]')
        if rating_elem:
            product_info["rating"] = rating_elem.get_text(strip=True)
        
        # Extract review count
        review_elem = element.select_one('span[class*="review"], div[class*="review"]')
        if review_elem:
            product_info["review_count"] = review_elem.get_text(strip=True)
        
        return product_info
        
    except Exception as e:
        print(f"Error extracting product info: {e}")
        return None

def get_products_from_urls_basic(product_urls: List[str]) -> List[Dict[str, Any]]:
    """Get product information from URLs using basic HTTP requests."""
    results = []
    
    for i, url in enumerate(product_urls):
        try:
            print(f"Scraping product {i+1}/{len(product_urls)}: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
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
                "product_url": url,
                "rank": i + 1,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Extract product name
            name_elem = soup.select_one('h1[class*="product-name"], h1[class*="title"], h1')
            if name_elem:
                product_info["product_name"] = name_elem.get_text(strip=True)
            
            # Extract price
            price_elem = soup.select_one('span[class*="price"], div[class*="price"]')
            if price_elem:
                product_info["price"] = price_elem.get_text(strip=True)
            
            # Extract seller name
            seller_elem = soup.select_one('div.seller-name__detail a.seller-name__detail-name, a[class*="seller"], div[class*="seller"]')
            if seller_elem:
                product_info["seller_name"] = seller_elem.get_text(strip=True)
            
            results.append(product_info)
            print(f"Extracted product {i+1}: {product_info.get('product_name', 'Unknown')[:50]}...")
            
            # Small delay to be respectful
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error scraping product {i+1}: {e}")
            continue
    
    return results

def search_products_selenium_cloud(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Selenium scraping with cloud environment detection.
    Falls back gracefully if Chrome is not available.
    """
    try:
        # Try to import Selenium components
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        from selenium.common.exceptions import WebDriverException, TimeoutException
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        # Set up Chrome options for cloud environment
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-javascript')  # Try without JS first
        
        try:
            # Try to create Chrome driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Chrome driver created successfully")
        except Exception as e:
            print(f"Failed to create Chrome driver: {e}")
            return []
        
        try:
            # Construct search URL
            search_url = f"{BASE_URL}/catalog/?q={urlencode({'q': query})[2:]}"
            print(f"Loading search page: {search_url}")
            
            driver.get(search_url)
            time.sleep(3)  # Wait for page to load
            
            # Wait for product elements
            wait = WebDriverWait(driver, 10)
            
            # Try to find product elements
            product_selectors = [
                "div[data-qa-locator='product-item']",
                "div[class*='product-item']",
                "div[class*='ProductItem']",
                "div[class*='product-card']"
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
                print("No product elements found with Selenium")
                return []
            
            # Extract product information
            results = []
            for i, element in enumerate(product_elements[:max_results]):
                try:
                    product_info = extract_product_info_selenium_cloud(element, driver)
                    if product_info and product_info.get("product_url"):
                        product_info["rank"] = i + 1
                        results.append(product_info)
                        print(f"Extracted product {i+1}: {product_info.get('product_name', 'Unknown')[:50]}...")
                except Exception as e:
                    print(f"Error extracting product {i+1}: {e}")
                    continue
            
            return results
            
        finally:
            driver.quit()
            
    except ImportError:
        print("Selenium not available, skipping Selenium scraping")
        return []
    except Exception as e:
        print(f"Error in search_products_selenium_cloud: {e}")
        return []

def extract_product_info_selenium_cloud(element, driver) -> Optional[Dict[str, Any]]:
    """Extract product information using Selenium with cloud optimizations."""
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
        except:
            pass
        
        # Extract product name
        name_selectors = [
            "div.RfADt",
            "a[href*='/products/']",
            "div[class*='title']",
            "div[class*='name']",
            "h3", "h4", "h5"
        ]
        
        for selector in name_selectors:
            try:
                name_elem = element.find_element(By.CSS_SELECTOR, selector)
                name_text = name_elem.text.strip()
                if name_text:
                    product_info["product_name"] = name_text
                    break
            except:
                continue
        
        # Extract price
        price_selectors = [
            "span[class*='price']",
            "div[class*='price']",
            "span[class*='currency']"
        ]
        
        for selector in price_selectors:
            try:
                price_elem = element.find_element(By.CSS_SELECTOR, selector)
                price_text = price_elem.text.strip()
                if price_text and ('Rs.' in price_text or re.search(r'\d+', price_text)):
                    product_info["price"] = price_text
                    break
            except:
                continue
        
        return product_info
        
    except Exception as e:
        print(f"Error extracting product info: {e}")
        return None
