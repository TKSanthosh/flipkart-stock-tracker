"""
Flipkart Stock & Deliverability Checker
Scrapes and parses product availability and pincode deliverability for Vivo X200T (12GB/256GB).
"""

import json
import re
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse
import os
import sys
from typing import Dict, Any, Optional, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_PINCODES = ["625012", "625001"]

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

def fetch_page(url: str, session: Optional[Any] = None, timeout: int = 20):
    """Fetch HTML content with realistic browser headers using requests or urllib."""
    try:
        import requests
        if session is None:
            session = requests.Session()
            session.headers.update(HEADERS)
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text, session
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
        return raw.decode("utf-8", errors="ignore"), None

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

    idx = html.find("window.__INITIAL_STATE__ = ")
    if idx != -1:
        start = idx + len("window.__INITIAL_STATE__ = ")
        end = html.find(";</script>", start)
        if end != -1:
            try:
                return json.loads(html[start:end])
            except Exception as e:
                print(f"[Warning] Fallback JSON parse failed: {e}")

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

def check_pincode_deliverability(url: str, pincode: str, session: Any) -> Dict[str, Any]:
    """
    Checks if product is serviceable & deliverable to a specific pincode
    using Flipkart's location-aware page fetch API.
    """
    if not session:
        return {
            "pincode": str(pincode),
            "is_available": False,
            "is_serviceable": False,
            "is_deliverable": False,
            "reason": "Session not available"
        }

    parsed = urlparse(url)
    page_uri = parsed.path + ("?" + parsed.query if parsed.query else "")

    post_headers = {
        "Content-Type": "application/json",
        "X-User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
            "FKUA/website/42/website/Desktop"
        ),
        "Origin": "https://www.flipkart.com",
        "Referer": "https://www.flipkart.com" + page_uri,
    }

    body = {
        "pageUri": page_uri,
        "locationContext": {"pincode": str(pincode)}
    }

    try:
        resp = session.post(
            "https://www.flipkart.com/api/4/page/fetch",
            json=body,
            headers=post_headers,
            timeout=20
        )
        if resp.status_code != 200:
            return {
                "pincode": str(pincode),
                "is_available": False,
                "is_serviceable": False,
                "is_deliverable": False,
                "reason": f"API HTTP {resp.status_code}"
            }

        data = resp.json()
        page_ctx = (data.get("RESPONSE") or {}).get("pageData", {}).get("pageContext", {}) or {}
        pls = ((page_ctx.get("fdpEventTracking") or {}).get("events") or {}).get("psi", {}).get("pls") or {}

        pincode_err = None
        has_delivery_data = False
        slots = (data.get("RESPONSE") or {}).get("slots", []) or []
        for sl in slots:
            w = sl.get("widget") or {}
            if w.get("type") == "COMPOSED_PINCODE_DELIVERY":
                d = w.get("data") or {}
                has_delivery_data = bool(d.get("deliveryData"))
                pincode_data = d.get("pincodeData") or {}
                comp = pincode_data.get("pincodeComponent") or {}
                val = comp.get("value") or {}
                pincode_err = val.get("errorCode")

        is_avail = bool(pls.get("isAvailable", False))
        is_serv = bool(pls.get("isServiceable", False))
        unserv_reason = pls.get("unserviceabilityReason") or pincode_err

        is_deliverable = (
            is_avail
            and is_serv
            and (unserv_reason != "NoMatchingPlans")
            and (pincode_err is None)
        )

        return {
            "pincode": str(pincode),
            "is_available": is_avail,
            "is_serviceable": is_serv,
            "is_deliverable": is_deliverable,
            "reason": "Deliverable" if is_deliverable else (unserv_reason or "Not Serviceable")
        }
    except Exception as e:
        return {
            "pincode": str(pincode),
            "is_available": False,
            "is_serviceable": False,
            "is_deliverable": False,
            "reason": f"Error: {e}"
        }

def check_flipkart_stock(
    url: str = DEFAULT_URL,
    pincodes: Optional[List[str]] = None,
    session: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Checks stock and deliverability for the specified Flipkart product.
    If pincodes are provided, deliverability to those pincodes is verified.
    """
    if pincodes is None:
        pincodes = DEFAULT_PINCODES

    title = "vivo X200T (12GB 256GB)"
    for v in DEFAULT_VARIANTS:
        if v.get("pid") in url:
            title = v.get("name", title)

    try:
        html, session = fetch_page(url, session=session)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch page: {e}",
            "is_available": False,
            "title": title,
            "price": "Unknown",
            "url": url,
            "pincode_status": {},
            "deliverable_pincodes": [],
        }

    data = parse_initial_state(html)

    price = "₹59,999"
    image_url = ""
    national_in_stock = False
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
                            national_in_stock = True
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
                    national_in_stock = True

            if pls.get("isAvailable") is True or pls.get("available") is True:
                national_in_stock = True
                status_details.append("PSI isAvailable: True")
        except Exception as e:
            print(f"[Warning] Error parsing PSI status: {e}")

        # 3. Action Buttons
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
                        if "Notify Me" not in raw_str:
                            has_buy_now = True

            if has_buy_now and not has_notify_me:
                national_in_stock = True
                status_details.append("Action button: BUY NOW / ADD TO CART active")
            elif has_notify_me:
                national_in_stock = False
                status_details.append("Action button: 'Notify Me' active (Out of Stock)")
        except Exception as e:
            print(f"[Warning] Error checking action buttons: {e}")

    # Fallback to HTML text parsing if JSON state was unavailable
    if not status_details:
        html_lower = html.lower()
        if "notify me" in html_lower or "currently out of stock" in html_lower or "sold out" in html_lower:
            national_in_stock = False
            status_details.append("HTML indicates Out of Stock / Notify Me")
        elif "buy now" in html_lower or "add to cart" in html_lower:
            national_in_stock = True
            status_details.append("HTML indicates Buy Now / Add to Cart")

    # Extract PID
    pid_match = re.search(r"pid=([A-Z0-9]+)", url)
    pid = pid_match.group(1) if pid_match else "UNKNOWN"

    # Pincode deliverability check
    pincode_status = {}
    deliverable_pincodes = []
    if pincodes and session:
        for pin in pincodes:
            time.sleep(1.0)  # Gentle spacing to avoid rate limiting
            pin_result = check_pincode_deliverability(url, pin, session)
            pincode_status[pin] = pin_result
            if pin_result.get("is_deliverable"):
                deliverable_pincodes.append(pin)

    # Deliverability determines actual purchase availability
    if pincodes:
        is_available = len(deliverable_pincodes) > 0
        if is_available:
            status_summary = f"AVAILABLE & DELIVERABLE to {', '.join(deliverable_pincodes)}"
        elif national_in_stock:
            status_summary = f"IN STOCK nationally, but NOT DELIVERABLE to {', '.join(pincodes)}"
        else:
            status_summary = "OUT OF STOCK"
    else:
        is_available = national_in_stock
        status_summary = "AVAILABLE / IN STOCK" if is_available else "OUT OF STOCK"

    return {
        "success": True,
        "pid": pid,
        "is_available": is_available,
        "national_in_stock": national_in_stock,
        "title": title,
        "price": price,
        "image_url": image_url,
        "status_summary": status_summary,
        "pincodes_checked": pincodes or [],
        "deliverable_pincodes": deliverable_pincodes,
        "pincode_status": pincode_status,
        "details": status_details,
        "url": url,
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

    print("Checking default variant and pincodes (625012, 625001)...")
    result = check_flipkart_stock()
    print("--- Stock Check Result ---")
    print(f"Product: {result['title']}")
    print(f"Price: {result['price']}")
    print(f"Status: {result['status_summary']}")
    print(f"Is Available (Deliverable): {result['is_available']}")
    print(f"Deliverable Pincodes: {result['deliverable_pincodes']}")
    print("Pincode Status:", result.get("pincode_status"))
