# 📱 Flipkart Vivo X200T (12GB / 256GB) Stock Monitor

Automated stock tracker and alert system hosted on **GitHub Actions**. It continuously checks Flipkart to see if the **vivo X200T 12GB RAM / 256GB ROM** (both **Stellar Black** and **Seaside Lilac** colorways) becomes available and deliverable, and immediately sends an alert email to **`tksanthosh494@gmail.com`**.

---

## 🚀 Features

- **Multi-Variant Tracking**: Monitors both 12GB/256GB variants (**Stellar Black** and **Seaside Lilac**) simultaneously.
- **Automated Execution**: Runs automatically on GitHub Actions every 1 hour (`0 * * * *`).
- **Direct SSR Data Inspection**: Parses Flipkart's internal server-rendered JSON state (`window.__INITIAL_STATE__`), checking `schema.org` stock status, Flipkart's Product State Intelligence (`psi`), and interactive action buttons (`BUY_NOW` vs `NOTIFY_ME`).
- **Rich HTML Email Alerts**: Sends clean, high-priority emails with product names, price, and direct "Buy Now" links.
- **Instant Mobile Push Notifications**: Zero-setup push alerts to your phone via `ntfy.sh`.
- **State Persistence**: Remembers previous stock status between runs so it triggers an immediate alert the exact run the phone transitions to in-stock.

---

## 🛠️ Step-by-Step Setup Guide

### 1. Repository Location

Local project directory:
```powershell
cd "C:\Users\Santhosh\.gemini\antigravity\scratch\flipkart-stock-tracker"
```


Or manually:
1. Create a new repository named `flipkart-stock-tracker` on [GitHub](https://github.com/new).
2. Run:
```powershell
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/flipkart-stock-tracker.git
git branch -M main
git push -u origin main
```

---

### 2. Configure GitHub Secrets for Email Alerts

To allow GitHub Actions to send emails from your Gmail account:

1. **Generate a Google App Password**:
   - Go to [Google Account Security](https://myaccount.google.com/security).
   - Ensure **2-Step Verification** is turned ON.
   - Go to [App Passwords](https://myaccount.google.com/apppasswords).
   - Name it `Flipkart Tracker` and click **Create**.
   - Copy the 16-character password (e.g. `abcd efgh ijkl mnop`).

2. **Add Secrets to your GitHub Repository**:
   - In your GitHub repo, go to **Settings** > **Secrets and variables** > **Actions**.
   - Click **New repository secret** and add:
     - `GMAIL_USER`: Your Gmail address (e.g., `your_email@gmail.com`).
     - `GMAIL_APP_PASSWORD`: The 16-character App Password you generated.
     - `EMAIL_TO`: `tksanthosh494@gmail.com` (already default, but can be explicitly set).

---

### 3. Enable Workflow & Run a Test

1. In your GitHub repository, click on the **Actions** tab.
2. Select **Flipkart Vivo X200T Stock Monitor** from the left sidebar.
3. Click the **Run workflow** button on the right.
4. Check the box **"Send test email alert to verify configuration"** and click **Run workflow**.
5. Within 30 seconds, you should receive a test email at `tksanthosh494@gmail.com` confirming everything is configured properly!

---

### 4. Optional: Free Mobile Phone Push Notifications

If you want instant phone notifications alongside email:
1. Install the free **ntfy** app on your phone ([Android Play Store](https://play.google.com/store/apps/details?id=io.heckel.ntfy) or [iOS App Store](https://apps.apple.com/app/ntfy/id1625396347)), or open [ntfy.sh](https://ntfy.sh) in any browser.
2. Subscribe to the topic: `santhosh-vivo-x200t-stock` (or your custom topic name).
3. That's it! When stock is found, an instant push banner will pop up on your phone.

---

## 💻 Running Locally

To test locally on Windows:
```powershell
# Install requirements
pip install -r requirements.txt

# Run stock check
python main.py

# Send a test alert (make sure GMAIL_USER and GMAIL_APP_PASSWORD are set in your environment or .env)
python main.py --test
```
