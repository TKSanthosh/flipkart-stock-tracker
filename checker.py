"""
Flipkart Stock & Deliverability Checker
Scrapes and parses product availability for Vivo X200T
"""

import json
import re
import urllib.request
import urllib.error
import os
import sys
from typing import Dict, Any, Optional, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_URL = (
    "https://www.flipkart.com/vivo-x200t-stellar-black-256-gb/p/itm1b8452d68859b?pid=MOBHJK5MBRDS3GUQ"
)

DEFAULT_VARIANTS = [
    {
        "pid": "MOBHJK5MBRDS3GUQ",
        "color": "Stellar Black",
        "name": "vivo X200T (Stellar Black, 256 GB)",
        "ram_storage": "12 GB RAM | 256 GB ROM",
        "url": "https://www.flipkart.com/vivo-x200t-stellar-black-256-gb/p/itm1b8452d68859b?pid=MOBHJK5MBRDS3GUQ",
    },
    {
        "pid": "MOBHJK5M62ZH9FAM",
        "color": "Seaside Lilac",
        "name": "vivo X200T (Seaside Lilac, 256 GB)",
        "ram_storage": "12 GB RAM | 256 GB ROM",
        "url": "https://www.flipkart.com/vivo-x200t-seaside-lilac-256-gb/p/itm1b8452d68859b?pid=MOBHJK5M62ZH9FAM",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

def fetch_page(url: str, timeout: int = 20) -> str:
    """Fetch HTML content with realistic browser headers using requests or urllib."""
    try:
        import requests
        session = requests.Session()
        session.headers.update(HEADERS)
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except ImportError:
        pass
    except Exception as e:
        print(f"[Warning] requests fetch failed: {e}. Falling back to urllib.")

    import gzip
    import zlib
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        content_encoding = response.headers.get("Content-Encoding", "").lower()
        raw = response.read()
        if "gzip" in content_encoding:
            raw = gzip.decompress(raw)
        elif "deflate" in content_encoding:
            raw = zlib.decompress(raw)
        return raw.decode("utf-8", errors="ignore")

def parse_initial_state(html: str) -> Optional[Dict[str, Any]]:
    """Extract and parse window.__INITIAL_STATE__ JSON from HTML."""
    match = re.search(
        r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});\s*(?:</script>|window\.)",
        html,
        re.DOTALL,
    )
    if match:
        try:
            return json.loads(match.group(1))
        except Exception as e:
            print(f"[Warning] Failed to parse matched JSON: {e}")

    # Fallback substring search
    idx = html.find("window.__INITIAL_STATE__ = ")
    if idx != -1:
        start = idx + len("window.__INITIAL_STATE__ = ")
        end = html.find(";</script>", start)
        if end != -1:
            try:
                return json.loads(html[start:end])
            except Exception as e:
                print(f"[Warning] Fallback JSON parse failed: {e}")

    # Fallback: JSON-LD Product schema blocks
    try:
        ld_matches = re.findall(r'<script\s+type=[\"\']application/ld\+json[\"\']>(.*?)</script>', html, re.DOTALL)
        for ld in ld_matches:
            try:
                obj = json.loads(ld)
                if isinstance(obj, dict) and obj.get("@type") == "Product":
                    return {
                        "multiWidgetState": {
                            "pageDataResponse": {
                                "seoData": {
                                    "schema": [obj]
                                }
                            }
                        }
                    }
            except Exception:
                pass
    except Exception as e:
        print(f"[Warning] JSON-LD parse failed: {e}")

    return None

def check_flipkart_stock(url: str = DEFAULT_URL) -> Dict[str, Any]:
    """
    Checks stock and deliverability for the specified Flipkart product.
    Returns a dictionary containing product info and stock status.
    """
    # Dynamic default title based on PID in URL
    title = "vivo X200T (12GB 256GB)"
    for v in DEFAULT_VARIANTS:
        if v.get("pid") in url:
            title = v.get("name", title)

    try:
        html = fetch_page(url)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch page: {e}",
            "is_available": False,
            "title": title,
            "price": "Unknown",
            "url": url,
        }

    data = parse_initial_state(html)

    # Defaults
    price = "₹59,999"
    image_url = ""
    is_available = False
    status_details = []

    if data:
        # 1. Product title & price from SEO schema
        try:
            seo_data = data.get("multiWidgetState", {}).get("pageDataResponse", {}).get("seoData", {})
            schemas = seo_data.get("schema", [])
            for item in schemas:
                if item.get("@type") == "Product":

                    title = item.get("name", title)
                    image_url = item.get("image", image_url)
                    offer = item.get("offers", {})
                    if isinstance(offer, dict):
                        p = offer.get("price")
                        if p:
                            price = f"₹{p:,}" if isinstance(p, (int, float)) else f"₹{p}"
                        schema_avail = offer.get("availability", "")
                        if "InStock" in schema_avail:
                            is_available = True
                            status_details.append("Schema reports InStock")
                        elif "OutOfStock" in schema_avail:
                            status_details.append("Schema reports OutOfStock")
        except Exception as e:
            print(f"[Warning] Error parsing SEO schema: {e}")

        # 2. Tracking events / PSI status
        try:
            events = (
                data.get("multiWidgetState", {})
                .get("pageDataResponse", {})
                .get("pageContext", {})
                .get("fdpEventTracking", {})
                .get("events", {})
            )
            pls = events.get("psi", {}).get("pls", {})
            avail_status = pls.get("availabilityStatus", "")
            if avail_status:
                status_details.append(f"PSI status: {avail_status}")
                if avail_status == "IN_STOCK":
                    is_available = True

            if pls.get("isAvailable") is True or pls.get("available") is True:
                is_available = True
                status_details.append("PSI isAvailable: True")
        except Exception as e:
            print(f"[Warning] Error parsing PSI status: {e}")

        # 3. Action Buttons (Buy Now, Add to Cart, Notify Me)
        try:
            slots = data.get("multiWidgetState", {}).get("widgetsData", {}).get("slots", [])
            has_notify_me = False
            has_buy_now = False

            for slot in slots:
                widget = slot.get("slotData", {}).get("widget", {})
                if widget.get("widgetName") == "ATLAS_PRODUCT_ACTION":
                    raw_str = json.dumps(widget)
                    if "NOTIFY_ME" in raw_str:
                        has_notify_me = True
                    if "BUY_NOW" in raw_str or "CART_ADD" in raw_str:
                        # Check if it is a real buy now button
                        if "Notify Me" not in raw_str:
                            has_buy_now = True

            if has_buy_now and not has_notify_me:
                is_available = True
                status_details.append("Action button: BUY NOW / ADD TO CART active")
            elif has_notify_me:
                is_available = False
                status_details.append("Action button: 'Notify Me' active (Out of Stock)")
        except Exception as e:
            print(f"[Warning] Error checking action buttons: {e}")

    # Fallback to HTML text parsing if JSON state was unavailable
    if not status_details:
        html_lower = html.lower()
        if "notify me" in html_lower or "currently out of stock" in html_lower or "sold out" in html_lower:
            is_available = False
            status_details.append("HTML indicates Out of Stock / Notify Me")
        elif "buy now" in html_lower or "add to cart" in html_lower:
            is_available = True
            status_details.append("HTML indicates Buy Now / Add to Cart")

    # Extract PID
    pid_match = re.search(r"pid=([A-Z0-9]+)", url)
    pid = pid_match.group(1) if pid_match else "UNKNOWN"

    # Extract swatches/variants if available
    discovered_variants = []
    if data:
        try:
            slots = data.get("multiWidgetState", {}).get("widgetsData", {}).get("slots", [])
            for s in slots:
                w = s.get("slotData", {}).get("widget", {})
                if w.get("widgetName") == "ATLAS_SWATCH_IMAGE":
                    items = (
                        w.get("data", {})
                        .get("dlsData", {})
                        .get("variant-selector-image-view_0", {})
                        .get("value", {})
                        .get("horizontalListData_0", {})
                        .get("value", [])
                    )
                    for it in items:
                        t = it.get("value", {}).get("trackerData_0", {}).get("tracking", {})
                        b = it.get("value", {}).get("box_0", {}).get("action", {})
                        swatch_pid = t.get("productId")
                        swatch_title = t.get("contentTitle")
                        swatch_url = b.get("url")
                        if swatch_pid and swatch_url:
                            clean_url = "https://www.flipkart.com" + swatch_url.split("&marketplace")[0]
                            discovered_variants.append({
                                "pid": swatch_pid,
                                "color": swatch_title,
                                "url": clean_url
                            })
        except Exception as e:
            print(f"[Warning] Failed to extract swatch variants: {e}")

    return {
        "success": True,
        "pid": pid,
        "is_available": is_available,
        "title": title,
        "price": price,
        "image_url": image_url,
        "status_summary": "AVAILABLE / IN STOCK" if is_available else "OUT OF STOCK",
        "details": status_details,
        "url": url,
        "discovered_variants": discovered_variants,
    }

def get_tracked_variants(custom_url: Optional[str] = None):
    """Returns list of variants to track."""
    if custom_url and custom_url != DEFAULT_URL:
        pid_m = re.search(r"pid=([A-Z0-9]+)", custom_url)
        return [{
            "pid": pid_m.group(1) if pid_m else "CUSTOM",
            "color": "Selected Variant",
            "name": "vivo X200T",
            "url": custom_url
        }]
    return DEFAULT_VARIANTS


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    result = check_flipkart_stock()
    print("--- Stock Check Result ---")
    print(f"Product: {result['title']}")
    print(f"Price: {result['price']}")
    print(f"Status: {result['status_summary']}")
    print(f"Is Available: {result['is_available']}")
    print("Details:", result.get("details"))
