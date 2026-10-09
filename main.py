"""
Main execution script for Flipkart Stock Tracker
Coordinates scraping, state management, and alerting.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from checker import check_flipkart_stock, DEFAULT_URL
from notifier import dispatch_alerts, DEFAULT_EMAIL_TO

STATE_FILE = "last_status.json"

def load_previous_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Warning] Failed to read {STATE_FILE}: {e}")
    return {"is_available": False, "last_alert_time": None}

def save_current_state(state: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[Warning] Failed to write {STATE_FILE}: {e}")

def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Flipkart Vivo X200T Stock Monitor")
    parser.add_argument("--test", action="store_true", help="Send a test notification to verify email configuration")
    parser.add_argument("--url", default=DEFAULT_URL, help="Custom Flipkart product URL")
    parser.add_argument("--email", default=os.environ.get("EMAIL_TO", DEFAULT_EMAIL_TO), help="Recipient email address")
    args = parser.parse_args()

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Flipkart Stock Check...")
    print(f"Target URL: {args.url}")
    print(f"Target Email: {args.email}")

    prev_state = load_previous_state()
    prev_available = prev_state.get("is_available", False)

    # 1. Test run requested
    if args.test:
        print("\n--- TEST MODE REQUESTED ---")
        dummy_data = {
            "title": "vivo X200T (Stellar Black, 256 GB)",
            "price": "₹59,999",
            "url": args.url,
            "is_available": True,
            "status_summary": "TEST RUN",
        }
        res = dispatch_alerts(dummy_data, to_email=args.email, is_test=True)
        print(f"Test dispatch result: {res}")
        return

    # 2. Fetch stock status
    product_data = check_flipkart_stock(args.url)
    is_available = product_data.get("is_available", False)
    title = product_data.get("title")
    price = product_data.get("price")
    status_summary = product_data.get("status_summary")
    details = product_data.get("details", [])

    print(f"\nProduct: {title}")
    print(f"Price: {price}")
    print(f"Current Status: {status_summary}")
    print(f"Detection details: {details}")

    # 3. Decision logic
    should_alert = False

    if is_available:
        if not prev_available:
            print("\n🚨 [STOCK FOUND] Item has transitioned from OUT OF STOCK to AVAILABLE!")
            should_alert = True
        else:
            print("\nItem is still available. Sending periodic reminder alert.")
            should_alert = True
    else:
        print("\nItem is currently OUT OF STOCK. No alert needed at this time.")

    if should_alert:
        print(f"Sending alert to {args.email}...")
        dispatch_results = dispatch_alerts(product_data, to_email=args.email, is_test=False)
        print(f"Dispatch results: {dispatch_results}")
        prev_state["last_alert_time"] = datetime.now(timezone.utc).isoformat()

    # Update state
    prev_state["is_available"] = is_available
    prev_state["last_check_time"] = datetime.now(timezone.utc).isoformat()
    prev_state["price"] = price
    prev_state["title"] = title
    prev_state["status_summary"] = status_summary
    save_current_state(prev_state)

    print(f"\nCheck completed successfully. State saved to {STATE_FILE}.")

if __name__ == "__main__":
    main()
