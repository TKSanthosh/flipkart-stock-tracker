"""
Email & Push Notification Dispatcher for Flipkart Stock Tracker
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Union

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Recipient
DEFAULT_EMAIL_TO = "tksanthosh494@gmail.com"

# SMTP Settings (Gmail by default)
DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587

def send_via_gmail_api(msg: MIMEMultipart, to_email: str) -> bool:
    """Sends email via official Google Gmail REST API using OAuth2 refresh token."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")

    if not (client_id and client_secret and refresh_token):
        return False

    try:
        import base64
        import json

        token_data = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }).encode("utf-8")
        req = urllib.request.Request("https://oauth2.googleapis.com/token", data=token_data)
        with urllib.request.urlopen(req, timeout=15) as resp:
            access_token = json.loads(resp.read().decode())["access_token"]

        raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        send_req = urllib.request.Request(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            data=json.dumps({"raw": raw_msg}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(send_req, timeout=15) as resp:
            res = json.loads(resp.read().decode())
            print(f"[Notifier] Email successfully delivered via Gmail API to {to_email}! (ID: {res.get('id')})")
            return True
    except Exception as e:
        print(f"[Notifier] Gmail API sending error: {e}")
        return False

def send_email_alert(
    product_data: Union[Dict[str, Any], List[Dict[str, Any]]],
    to_email: str = DEFAULT_EMAIL_TO,
    is_test: bool = False
) -> bool:
    """
    Sends an HTML alert email to the recipient via Gmail API or SMTP.
    """
    smtp_user = os.environ.get("GMAIL_USER") or os.environ.get("SMTP_USER") or "tksanthosh494@gmail.com"


    items: List[Dict[str, Any]] = product_data if isinstance(product_data, list) else [product_data]
    now_str = datetime.now().strftime("%d %b %Y, %I:%M %p IST")

    in_stock_items = [it for it in items if it.get("is_available", False)]
    if not in_stock_items and not is_test:
        print("[Notifier] No phone variant is currently available in stock. Skipping email delivery.")
        return False

    if is_test:
        subject = "[TEST] Vivo X200T Stock Monitor Test Alert"
    else:
        names = ", ".join([it.get("title", "Vivo X200T") for it in in_stock_items])
        subject = f"🚨 [AVAILABLE NOW] {names} is in stock on Flipkart!"

    # Plain text content
    text_lines = ["Flipkart Stock Tracker Notification\n"]
    for it in items:
        status_text = "IN STOCK & AVAILABLE" if it.get("is_available") else "OUT OF STOCK"
        if is_test:
            status_text = "TEST RUN"
        text_lines.append(f"- {it.get('title', 'vivo X200T')}")
        text_lines.append(f"  Price: {it.get('price', 'N/A')}")
        text_lines.append(f"  Status: {status_text}")
        text_lines.append(f"  Link: {it.get('url', '')}\n")
    text_lines.append(f"Checked at: {now_str}")
    text_content = "\n".join(text_lines)

    # HTML cards
    cards_html = ""
    for it in items:
        avail = it.get("is_available", False) or is_test
        badge_color = "#059669" if avail else "#dc2626"
        badge_text = "AVAILABLE NOW" if it.get("is_available") else ("TEST RUN" if is_test else "OUT OF STOCK")
        btn_html = f"""<a href="{it.get('url', '#')}" class="btn" target="_blank" style="display:inline-block; margin-top:12px; background:#fb641b; color:#ffffff !important; padding:10px 18px; text-decoration:none; font-weight:bold; border-radius:6px;">BUY ON FLIPKART</a>""" if avail else ""

        cards_html += f"""
        <div class="card" style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:18px; margin-bottom:16px;">
          <span style="display:inline-block; padding:4px 10px; border-radius:20px; font-weight:bold; font-size:12px; color:#fff; background:{badge_color}; margin-bottom:8px;">{badge_text}</span>
          <h2 style="margin:4px 0 8px 0; font-size:17px; color:#0f172a;">{it.get('title', 'vivo X200T')}</h2>
          <div style="font-size:22px; font-weight:800; color:#1e293b; margin:6px 0;">{it.get('price', 'Check website')}</div>
          {btn_html}
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
    .header {{ background: #2874f0; color: #ffffff; padding: 20px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 20px; }}
    .content {{ padding: 20px; }}
    .footer {{ padding: 14px 20px; background: #f1f5f9; text-align: center; font-size: 12px; color: #64748b; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Flipkart Stock Alert: Vivo X200T</h1>
    </div>
    <div class="content">
      <p style="margin: 0 0 16px 0; color: #475569; font-size: 14px;">Latest stock status checked at <b>{now_str}</b>:</p>
      {cards_html}
    </div>
    <div class="footer">
      Automated alert sent to {to_email}. Powered by GitHub Actions.
    </div>
  </div>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Flipkart Stock Tracker <{smtp_user}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    # 1. Try Google Gmail REST API first (recommended, zero-port block, official Google OAuth)
    if os.environ.get("GOOGLE_REFRESH_TOKEN") and os.environ.get("GOOGLE_CLIENT_ID"):
        if send_via_gmail_api(msg, to_email):
            return True

    # 2. Fallback to standard SMTP (Gmail App Password)
    smtp_pass = os.environ.get("SMTP_PASS") or os.environ.get("GMAIL_APP_PASSWORD")
    if not smtp_pass:
        print("[Notifier] No email delivery credentials found.")
        print("          Provide either GOOGLE_REFRESH_TOKEN / GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET (Gmail API)")
        print("          or GMAIL_USER / GMAIL_APP_PASSWORD (SMTP) in GitHub Secrets.")
        return False

    smtp_host = os.environ.get("SMTP_HOST", DEFAULT_SMTP_HOST)
    smtp_port = int(os.environ.get("SMTP_PORT", DEFAULT_SMTP_PORT))

    try:
        print(f"[Notifier] Connecting to SMTP server {smtp_host}:{smtp_port}...")
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_email], msg.as_string())
        server.quit()
        print(f"[Notifier] Email successfully sent to {to_email}!")
        return True
    except Exception as e:
        print(f"[Notifier] Failed to send email via SMTP: {e}")
        return False

def send_push_alert(
    product_data: Union[Dict[str, Any], List[Dict[str, Any]]],
    topic: str,
    is_test: bool = False
) -> bool:
    """
    Sends an optional instant push notification to phone via ntfy.sh.
    Zero-config: user just installs the free ntfy app or opens ntfy.sh/<topic> in browser.
    """
    if not topic:
        return False

    items: List[Dict[str, Any]] = product_data if isinstance(product_data, list) else [product_data]
    in_stock = [it for it in items if it.get("is_available")] or items
    target = in_stock[0]

    title = target.get("title", "vivo X200T")
    price = target.get("price", "₹59,999")
    url = target.get("url", "https://flipkart.com")

    msg_title = "[TEST] Vivo X200T Tracker" if is_test else "Vivo X200T is IN STOCK!"
    body = f"{title} is available now for {price}! Tap to purchase."

    try:
        req = urllib.request.Request(
            f"https://ntfy.sh/{urllib.parse.quote(topic)}",
            data=body.encode("utf-8"),
            headers={
                "Title": msg_title,
                "Priority": "high",
                "Click": url,
                "Tags": "rotating_light,shopping_cart" if not is_test else "test_tube",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print(f"[Notifier] Instant push notification sent to ntfy.sh/{topic}")
                return True
    except Exception as e:
        print(f"[Notifier] ntfy push notification error: {e}")

    return False

def dispatch_alerts(
    product_data: Union[Dict[str, Any], List[Dict[str, Any]]],
    to_email: str = DEFAULT_EMAIL_TO,
    is_test: bool = False
) -> Dict[str, bool]:
    """Dispatches all configured alert channels."""
    email_success = send_email_alert(product_data, to_email=to_email, is_test=is_test)

    push_topic = os.environ.get("NTFY_TOPIC", "santhosh-vivo-x200t-stock")
    push_success = send_push_alert(product_data, topic=push_topic, is_test=is_test)

    return {
        "email": email_success,
        "push": push_success,
    }


if __name__ == "__main__":
    test_data = {
        "title": "vivo X200T (Stellar Black, 256 GB)",
        "price": "₹59,999",
        "url": "https://www.flipkart.com/vivo-x200t-stellar-black-256-gb/p/itm1b8452d68859b?pid=MOBHJK5MBRDS3GUQ",
        "is_available": True,
    }
    print("Testing dispatch (will report SMTP credentials missing if env vars unset):")
    dispatch_alerts(test_data, is_test=True)
