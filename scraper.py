"""
scraper.py
==============

This module contains the core scraping logic for retrieving product and
seller information from Daraz Nepal. The public function
``search_products`` accepts a free‑form search term and returns a list of
product dictionaries in the same order that Daraz presents them on the
first results page. Each dictionary includes the product name, price,
product URL and the seller's name and location.

The scraping routines rely on the ``requests`` library to fetch HTML
pages and ``BeautifulSoup`` to parse them. A modern user agent string
is supplied with every request to reduce the chance of being blocked.
If Daraz alters its HTML structure in the future these selectors may
need to be updated accordingly.

Note: Because external websites cannot be accessed directly from
OpenAI's evaluation environment, this code has not been executed
against the live Daraz site. Nevertheless, the selectors are based on
observations of the DOM at the time of writing. Should the
structure differ, you may need to tweak the CSS selectors used
below (``product_selector``, ``title_selector`` and so on) to suit the
live site.
"""

from __future__ import annotations

import time
from typing import List, Dict, Tuple

import requests
from bs4 import BeautifulSoup

# Base domain for Daraz Nepal. If you wish to scrape a different
# marketplace (e.g. Pakistan), change this constant accordingly.
BASE_URL = "https://www.daraz.com.np"

# Pretend to be a regular web browser to minimise blocking by the site.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_html(url: str, *, max_retries: int = 3, delay: float = 1.0) -> str:
    """Fetch HTML content from the given URL.

    To improve reliability, this helper retries transient network errors a
    few times with exponential backoff. In the event of a non-200
    response, it raises an exception.

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
            if response.status_code != 200:
                response.raise_for_status()
            return response.text
        except Exception:
            # On the last attempt re‑raise the exception
            if attempt == max_retries - 1:
                raise
            # Otherwise wait and try again
            time.sleep(delay * (2 ** attempt))
    # Control should never reach here
    raise RuntimeError("Unreachable code in fetch_html")


def parse_search_results(html: str) -> List[Dict[str, str]]:
    """Parse the search results page into a list of product summaries.

    Each summary contains the product name, price and relative URL. If any
    of these elements cannot be found, the product is skipped.

    Args:
        html: The raw HTML string of a Daraz search page.

    Returns:
        A list of dictionaries with keys ``name``, ``price`` and ``url``.
    """
    soup = BeautifulSoup(html, "html.parser")
    products: List[Dict[str, str]] = []

    # From observations of the Daraz search page, each product card is
    # contained within a div whose ``data-qa-locator`` attribute begins
    # with "product-item". Should Daraz change their markup, update
    # this selector accordingly.
    product_cards = soup.find_all("div", attrs={"data-qa-locator": "product-item"})

    for card in product_cards:
        # Extract the anchor tag that wraps the product link
        link = card.find("a", href=True)
        title_elem = card.find("div", class_=lambda x: x and "title" in x)
        price_elem = card.find("span", class_=lambda x: x and "price" in x)

        if not (link and title_elem and price_elem):
            continue

        product_name = title_elem.get_text(strip=True)
        price_text = price_elem.get_text(strip=True)
        relative_url = link["href"]

        # Build a full URL if necessary. Some links begin with // or /.
        if relative_url.startswith("//"):
            product_url = "https:" + relative_url
        elif relative_url.startswith("/"):
            product_url = BASE_URL.rstrip("/") + relative_url
        elif relative_url.startswith("http"):
            product_url = relative_url
        else:
            product_url = BASE_URL.rstrip("/") + "/" + relative_url

        products.append({
            "name": product_name,
            "price": price_text,
            "url": product_url,
        })

    return products


def parse_seller_details(html: str) -> Tuple[str | None, str | None]:
    """Parse a product detail page and extract the seller's name and location.

    The seller information is usually located in a section labelled
    "Seller Information". This function attempts to locate common
    patterns for the store name and location. If either cannot be
    found, the returned tuple will contain ``None`` for that element.

    Args:
        html: The raw HTML string of a Daraz product page.

    Returns:
        A tuple ``(seller_name, seller_location)`` where each item may be
        ``None`` if not available.
    """
    soup = BeautifulSoup(html, "html.parser")
    seller_name = None
    seller_location = None

    # Attempt to find the seller name. On Daraz the store name is often
    # wrapped in an <a> tag with id beginning "module_seller_info_store_name".
    store_name_anchor = soup.find("a", id=lambda x: x and x.startswith("module_seller_info_store_name"))
    if store_name_anchor:
        seller_name = store_name_anchor.get_text(strip=True)

    # The seller location is sometimes within a span with class containing
    # "seller-name__location". If not found, try another heuristic.
    location_span = soup.find("span", class_=lambda x: x and "seller-name__location" in x)
    if location_span:
        seller_location = location_span.get_text(strip=True)
    else:
        # Fallback: search for any text near "Location" label
        label = soup.find(string=lambda s: s and "Location" in s)
        if label and label.parent:
            # The location may be the next sibling or within the next span
            sibling = label.parent.find_next("span")
            if sibling:
                seller_location = sibling.get_text(strip=True)

    return seller_name, seller_location


def get_seller_details(product_url: str) -> Tuple[str | None, str | None]:
    """Fetch a product page and extract the seller's name and location.

    Args:
        product_url: The absolute URL of the product page.

    Returns:
        A tuple ``(seller_name, seller_location)``. Either element may be
        ``None`` if not available.
    """
    html = fetch_html(product_url)
    return parse_seller_details(html)


def search_products(query: str, *, max_results: int = 10) -> List[Dict[str, str | None]]:
    """Search Daraz for a keyword and return ordered seller details.

    Performs a search on Daraz using the provided query string, parses the
    resulting product cards and then visits each product page to fetch
    seller details. Results are returned in the same order they appear on
    Daraz (usually sorted by "Best Match" by default).

    Args:
        query: A free‑text search term (e.g. ``"tooth paste"``).
        max_results: Maximum number of products to fetch. Defaults to 10.

    Returns:
        A list of dictionaries. Each dictionary contains:
            - ``product_name``: the name of the product
            - ``price``: the listed price text
            - ``seller_name``: the store selling the product, if found
            - ``seller_location``: the store's reported location, if found
            - ``product_url``: the absolute URL to the product page
    """
    # Build the search URL. Daraz uses spaces encoded as '%20'.
    encoded_query = requests.utils.quote(query)
    search_url = f"{BASE_URL}/catalog/?q={encoded_query}"
    search_html = fetch_html(search_url)
    summaries = parse_search_results(search_html)

    results: List[Dict[str, str | None]] = []
    for summary in summaries[:max_results]:
        try:
            seller_name, seller_location = get_seller_details(summary["url"])
        except Exception:
            seller_name, seller_location = None, None
        results.append({
            "product_name": summary["name"],
            "price": summary["price"],
            "seller_name": seller_name,
            "seller_location": seller_location,
            "product_url": summary["url"],
        })
    return results