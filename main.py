"""
Main execution script for Flipkart Stock Tracker
Coordinates scraping, state management, and alerting for Vivo X200T (12GB 256GB).
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta
from checker import check_flipkart_stock, get_tracked_variants, DEFAULT_URL, DEFAULT_VARIANTS
from notifier import dispatch_alerts, DEFAULT_EMAIL_TO

STATE_FILE = "last_status.json"

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def load_previous_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "variants" in data:
                    return data
                # Migrate older flat structure
                return {
                    "last_check_time": data.get("last_check_time"),
                    "variants": {
                        "MOBHJK5MBRDS3GUQ": {
                            "is_available": data.get("is_available", False),
                            "last_alert_time": data.get("last_alert_time"),
                            "price": data.get("price"),
                            "title": data.get("title"),
                        }
                    }
                }
        except Exception as e:
            print(f"[Warning] Failed to read {STATE_FILE}: {e}")
    return {"last_check_time": None, "variants": {}}

def save_current_state(state: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[Warning] Failed to write {STATE_FILE}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Flipkart Vivo X200T (12GB/256GB) Stock Monitor")
    parser.add_argument("--test", action="store_true", help="Send a test notification to verify email configuration")
    parser.add_argument("--force", action="store_true", help="Force send alert for available items even if already alerted")
    parser.add_argument("--url", default=None, help="Custom Flipkart product URL (checks all 12GB/256GB variants if omitted)")
    parser.add_argument("--email", default=os.environ.get("EMAIL_TO", DEFAULT_EMAIL_TO), help="Recipient email address")
    args = parser.parse_args()

    now_iso = datetime.now(timezone.utc).isoformat()
    now_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"[{now_local}] Starting Flipkart Stock Check for Vivo X200T (12GB 256GB)...")
    print(f"Target Email: {args.email}")

    # 1. Test mode requested
    if args.test:
        print("\n--- TEST MODE REQUESTED ---")
        dummy_data = [
            {
                "title": "vivo X200T (Stellar Black, 256 GB)",
                "price": "₹59,999",
                "url": DEFAULT_URL,
                "is_available": True,
                "status_summary": "TEST RUN",
            },
            {
                "title": "vivo X200T (Seaside Lilac, 256 GB)",
                "price": "₹59,999",
                "url": "https://www.flipkart.com/vivo-x200t-seaside-lilac-256-gb/p/itm1b8452d68859b?pid=MOBHJK5M62ZH9FAM",
                "is_available": True,
                "status_summary": "TEST RUN",
            }
        ]
        res = dispatch_alerts(dummy_data, to_email=args.email, is_test=True)
        print(f"Test dispatch result: {res}")
        return

    # 2. Determine target variants to check
    targets = get_tracked_variants(args.url)
    print(f"Tracking {len(targets)} variant(s):")
    for t in targets:
        print(f"  - {t.get('name', t.get('color'))} ({t.get('url')})")

    prev_state = load_previous_state()
    prev_variants = prev_state.get("variants", {})

    current_results = []
    items_to_alert = []

    for t in targets:
        target_url = t["url"]
        print(f"\nChecking: {target_url} ...")
        prod = check_flipkart_stock(target_url)
        current_results.append(prod)

        pid = prod.get("pid", t.get("pid", target_url))
        is_avail = prod.get("is_available", False)
        title = prod.get("title", t.get("name", "vivo X200T"))
        price = prod.get("price", "₹59,999")
        status_summary = prod.get("status_summary", "UNKNOWN")

        print(f"  Title: {title}")
        print(f"  Price: {price}")
        print(f"  Status: {status_summary}")
        print(f"  Available: {is_avail}")

        var_prev = prev_variants.get(pid, {})
        was_avail = var_prev.get("is_available", False)
        last_alert_str = var_prev.get("last_alert_time")

        should_alert = False
        if is_avail:
            if not was_avail:
                print(f"  🚨 [STOCK ALERT] {title} is now AVAILABLE on Flipkart!")
                should_alert = True
            elif args.force:
                print(f"  ⚡ [FORCE ALERT] {title} is in stock and force flag is set.")
                should_alert = True
            elif not last_alert_str:
                print(f"  🚨 [STOCK ALERT] {title} is in stock!")
                should_alert = True

        if should_alert:
            items_to_alert.append(prod)

        # Update variant state
        var_state = {
            "title": title,
            "price": price,
            "url": target_url,
            "is_available": is_avail,
            "last_status": status_summary,
            "last_alert_time": now_iso if should_alert else var_prev.get("last_alert_time"),
        }
        prev_variants[pid] = var_state

    # 3. Dispatch alerts ONLY when phone is available
    if items_to_alert:
        print(f"\n[ALERT] Phone is AVAILABLE! Sending email to {args.email} for {len(items_to_alert)} item(s)...")
        results = dispatch_alerts(items_to_alert, to_email=args.email, is_test=False)
        print(f"Dispatch results: {results}")
    else:
        print("\n[INFO] Phone is currently OUT OF STOCK. No email sent.")


    # 4. Save state
    prev_state["last_check_time"] = now_iso
    prev_state["variants"] = prev_variants
    save_current_state(prev_state)
    print(f"\nState saved to {STATE_FILE}.")

if __name__ == "__main__":
    main()

