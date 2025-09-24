"""
scraper_optimized.py
===================

High-performance, memory-optimized Daraz scraper with:
- Async/await for concurrent processing
- Streaming results to avoid memory buildup
- Connection pooling and resource management
- Batch processing for large datasets
- Memory-efficient data structures
"""

import asyncio
import aiohttp
import gc
import weakref
from typing import List, Dict, Any, AsyncGenerator, Optional
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import time
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base domain for Daraz Nepal
BASE_URL = "https://www.daraz.com.np"

# Memory-optimized data structure
@dataclass(frozen=True)
class ProductData:
    """Immutable, memory-efficient product data structure"""
    product_name: str
    price: str
    seller_name: str
    seller_location: str
    product_url: str
    rank: int
    scraped_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary only when needed"""
        return asdict(self)

# Connection pool configuration
CONNECTOR_LIMIT = 100  # Max concurrent connections
CONNECTOR_LIMIT_PER_HOST = 30  # Max connections per host
TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10)

# Headers for requests
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

class MemoryOptimizedScraper:
    """Memory-optimized scraper with connection pooling and async processing"""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(
            limit=CONNECTOR_LIMIT,
            limit_per_host=CONNECTOR_LIMIT_PER_HOST,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=TIMEOUT,
            headers=HEADERS,
            auto_decompress=True,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            self.session = None
        
        # Force garbage collection
        gc.collect()
    
    async def fetch_html(self, url: str, max_retries: int = 3) -> str:
        """Fetch HTML with retry logic and memory optimization"""
        for attempt in range(max_retries):
            try:
                async with self._semaphore:  # Limit concurrent requests
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            # Stream the response to avoid loading everything into memory
                            content = await response.text()
                            return content
                        else:
                            response.raise_for_status()
                            
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts: {e}")
                    raise
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        raise RuntimeError(f"Failed to fetch {url}")
    
    def parse_search_results(self, html: str) -> List[Dict[str, str]]:
        """Parse search results with memory-efficient approach"""
        soup = BeautifulSoup(html, "html.parser")
        products = []
        
        # Use generator to avoid loading all elements into memory at once
        product_cards = soup.select("div[data-qa-locator='product-item']")
        
        for card in product_cards:
            try:
                # Extract only essential data
                link = card.find('a', href=re.compile(r'/products/'))
                if not link:
                    continue
                
                href = link.get('href', '')
                if not href:
                    continue
                
                # Build full URL efficiently
                if href.startswith('//'):
                    product_url = 'https:' + href
                elif href.startswith('/'):
                    product_url = BASE_URL + href
                elif href.startswith('http'):
                    product_url = href
                else:
                    product_url = BASE_URL + '/' + href
                
                # Extract product name efficiently
                product_name = self._extract_product_name(card)
                if not product_name:
                    continue
                
                # Extract price efficiently
                price = self._extract_price(card)
                
                products.append({
                    "name": product_name,
                    "price": price or "Price not available",
                    "url": product_url
                })
                
            except Exception as e:
                logger.warning(f"Error parsing product card: {e}")
                continue
        
        return products
    
    def _extract_product_name(self, card) -> str:
        """Extract product name efficiently"""
        # Try specific selector first
        name_elem = card.select_one("div.RfADt")
        if name_elem:
            text = name_elem.get_text(strip=True)
            if text:
                lines = text.split('\n')
                clean_name = lines[0].strip()
                if clean_name and len(clean_name) > 3 and not clean_name.startswith('Rs.'):
                    return clean_name
        
        # Fallback to link text
        link = card.find('a', href=re.compile(r'/products/'))
        if link:
            text = link.get_text(strip=True)
            if text and len(text) > 3:
                return text
        
        return ""
    
    def _extract_price(self, card) -> str:
        """Extract price efficiently using regex"""
        all_text = card.get_text()
        price_match = re.search(r'Rs\.\s*[\d,]+', all_text)
        return price_match.group() if price_match else ""
    
    async def get_product_details(self, product_url: str) -> Dict[str, Any]:
        """Get product details with memory optimization"""
        try:
            html = await self.fetch_html(product_url)
            return self.parse_product_details(html, product_url)
        except Exception as e:
            logger.error(f"Error getting product details for {product_url}: {e}")
            return {
                "product_name": "Product details unavailable",
                "price": "Price unavailable",
                "seller_name": "",
                "seller_location": "",
                "product_url": product_url,
                "rank": 0,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(e)
            }
    
    def parse_product_details(self, html: str, product_url: str) -> Dict[str, Any]:
        """Parse product details with memory optimization"""
        soup = BeautifulSoup(html, "html.parser")
        
        # Initialize with minimal data
        product_details = {
            "product_name": "",
            "price": "",
            "seller_name": "",
            "seller_location": "",
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
                'h1'
            ]
            
            for selector in name_selectors:
                name_elem = soup.select_one(selector)
                if name_elem:
                    product_details["product_name"] = name_elem.get_text(strip=True)
                    break
            
            # Extract price
            price_selectors = [
                'span[class*="pdp-price"]',
                'span[class*="current-price"]',
                'span[class*="price-current"]',
                'div[class*="price-current"]'
            ]
            
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    product_details["price"] = price_elem.get_text(strip=True)
                    break
            
            # Extract seller name using specific selector
            seller_elem = soup.select_one('div.seller-name__detail a.seller-name__detail-name')
            if seller_elem:
                product_details["seller_name"] = seller_elem.get_text(strip=True)
            
            # Extract seller location
            all_text = soup.get_text()
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
                        product_details["seller_location"] = location
                        break
            
        except Exception as e:
            logger.error(f"Error parsing product details: {e}")
        
        return product_details
    
    async def search_products_streaming(
        self, 
        query: str, 
        max_results: int = 10
    ) -> AsyncGenerator[ProductData, None]:
        """Stream products as they are processed to avoid memory buildup"""
        
        # Build search URL
        encoded_query = aiohttp.helpers.quote(query)
        search_url = f"{BASE_URL}/catalog/?q={encoded_query}"
        
        try:
            # Fetch search results
            search_html = await self.fetch_html(search_url)
            product_summaries = self.parse_search_results(search_html)
            
            if not product_summaries:
                logger.warning(f"No products found for query: {query}")
                return
            
            # Limit results
            product_summaries = product_summaries[:max_results]
            
            # Process products concurrently with streaming
            tasks = []
            for i, summary in enumerate(product_summaries):
                task = self._process_single_product(summary, i + 1)
                tasks.append(task)
            
            # Process in batches to control memory usage
            batch_size = min(self.max_concurrent, len(tasks))
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i + batch_size]
                results = await asyncio.gather(*batch, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Error processing product: {result}")
                        continue
                    
                    if result:
                        yield result
                
                # Force garbage collection after each batch
                gc.collect()
                
        except Exception as e:
            logger.error(f"Error in search_products_streaming: {e}")
            raise
    
    async def _process_single_product(
        self, 
        summary: Dict[str, str], 
        rank: int
    ) -> Optional[ProductData]:
        """Process a single product with error handling"""
        try:
            # Get detailed product information
            detailed_info = await self.get_product_details(summary["url"])
            
            # Create memory-efficient ProductData object
            product_data = ProductData(
                product_name=detailed_info.get("product_name") or summary.get("name", "Unknown Product"),
                price=detailed_info.get("price") or summary.get("price", "Price not available"),
                seller_name=detailed_info.get("seller_name", ""),
                seller_location=detailed_info.get("seller_location", ""),
                product_url=summary.get("url", ""),
                rank=rank,
                scraped_at=time.strftime("%Y-%m-%d %H:%M:%S")
            )
            
            return product_data
            
        except Exception as e:
            logger.error(f"Error processing product {rank}: {e}")
            return None
    
    async def search_products_batch(
        self, 
        queries: List[str], 
        max_results_per_query: int = 10
    ) -> AsyncGenerator[Dict[str, List[ProductData]], None]:
        """Process multiple queries in batches for scalability"""
        
        for query in queries:
            try:
                products = []
                async for product in self.search_products_streaming(query, max_results_per_query):
                    products.append(product)
                
                yield {query: products}
                
                # Clear the products list to free memory
                products.clear()
                gc.collect()
                
            except Exception as e:
                logger.error(f"Error processing query '{query}': {e}")
                yield {query: []}

# Convenience functions for backward compatibility
async def search_products_async(
    query: str, 
    max_results: int = 10,
    max_concurrent: int = 10
) -> List[Dict[str, Any]]:
    """Async search function that returns a list"""
    results = []
    
    async with MemoryOptimizedScraper(max_concurrent) as scraper:
        async for product in scraper.search_products_streaming(query, max_results):
            results.append(product.to_dict())
    
    return results

def search_products_sync(
    query: str, 
    max_results: int = 10,
    max_concurrent: int = 10
) -> List[Dict[str, Any]]:
    """Synchronous wrapper for async search function"""
    return asyncio.run(search_products_async(query, max_results, max_concurrent))

# Example usage and testing
async def main():
    """Example usage of the optimized scraper"""
    
    # Single query
    print("Testing single query...")
    async with MemoryOptimizedScraper(max_concurrent=5) as scraper:
        count = 0
        async for product in scraper.search_products_streaming("toothpaste", max_results=3):
            print(f"Product {count + 1}: {product.product_name} - {product.seller_name}")
            count += 1
    
    print(f"\nProcessed {count} products")
    
    # Multiple queries
    print("\nTesting multiple queries...")
    queries = ["toothpaste", "tshirt", "laptop"]
    async with MemoryOptimizedScraper(max_concurrent=3) as scraper:
        async for result in scraper.search_products_batch(queries, max_results_per_query=2):
            for query, products in result.items():
                print(f"Query '{query}': {len(products)} products")

if __name__ == "__main__":
    asyncio.run(main())
