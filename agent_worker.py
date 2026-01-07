"""
Agent Worker for Koyeb/Cloud deployment.
Handles:
1. Slack Auto-Responder (Socket Mode)
2. Weekly Notion Reporting (Scheduled)
3. Health Check Server (Port 8080)
"""

import os
import logging
import threading
import requests
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from apscheduler.schedulers.background import BackgroundScheduler
from notion_client import Client as NotionClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Clients
app = App(token=os.getenv("SLACK_BOT_TOKEN"))
notion = NotionClient(auth=os.getenv("NOTION_TOKEN"))
MY_ID = os.getenv("MY_SLACK_ID")
NTFY_TOPIC = os.getenv("NTFY_TOPIC")
NOTION_DB_ID = os.getenv("NOTION_DATABASE_ID")

def send_push_notification(message, title="Agent Worker"):
    """Send a push notification via ntfy.sh."""
    if not NTFY_TOPIC: return
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode('utf-8'),
            headers={"Title": title, "Priority": "high", "Tags": "robot,chart_with_upwards_trend"}
        )
    except Exception as e:
        logger.error(f"❌ Push error: {e}")

# --- Weekly Report Logic ---
def generate_weekly_report():
    """Fetches last 7 days of logs and saves a summary to Notion."""
    logger.info("📊 Starting Weekly Report generation...")
    
    if not NOTION_DB_ID or not os.getenv("GROQ_API_KEY"):
        logger.error("❌ Missing credentials for reporting.")
        return

    try:
        # 1. Fetch logs from Notion
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        query = notion.databases.query(
            database_id=NOTION_DB_ID,
            filter={"property": "Date", "date": {"on_or_after": seven_days_ago}}
        )
        
        logs = []
        for page in query.get("results", []):
            props = page.get("properties", {})
            title = props.get("Name", {}).get("title", [{}])[0].get("plain_text", "")
            cat = props.get("Category", {}).get("select", {}).get("name", "Other")
            date = props.get("Date", {}).get("date", {}).get("start", "")
            if title: logs.append(f"- [{date}] ({cat}) {title}")

        if not logs:
            logger.info("📭 No logs found for the last 7 days. Skipping report.")
            return

        # 2. Use Groq AI to summarize
        logger.info(f"🧠 Summarizing {len(logs)} logs using AI...")
        prompt = f"Analyze these work logs from the last 7 days and write a professional, high-level summary of the week's progress and focus areas:\n\n" + "\n".join(logs)
        
        groq_res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "system", "content": "You are a senior project manager writing a weekly executive summary."},
                             {"role": "user", "content": prompt}]
            }
        )
        summary = groq_res.json()['choices'][0]['message']['content']

        # 3. Save Report back to Notion
        notion.pages.create(
            parent={"database_id": NOTION_DB_ID},
            properties={
                "Name": {"title": [{"text": {"content": f"📅 Weekly Report: {datetime.now().strftime('%b %d, %Y')}"}}]},
                "Category": {"select": {"name": "Reporting"}},
                "Date": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}}
            },
            children=[{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": summary}}]}}]
        )
        
        logger.info("✅ Weekly Report saved to Notion!")
        send_push_notification("Your Weekly Work Report has been generated and saved to Notion.", "📊 Report Ready")

    except Exception as e:
        logger.error(f"❌ Report generation failed: {e}")

# --- Slack Handlers ---
@app.event("message")
def handle_message(body, client, say):
    event = body.get("event", {})
    text = event.get("text", "")
    user_id = event.get("user", "")
    
    if event.get("bot_id") or not MY_ID or f"<@{MY_ID}>" not in text: return
    
    # Send push notification
    send_push_notification(f"Mentioned by {user_id}: {text[:50]}...", "🔔 Slack Mention")
    
    # Auto-reply if away
    try:
        presence = client.users_getPresence(user=MY_ID).get("presence", "active")
        is_snooze = client.dnd_info(user=MY_ID).get("snooze_enabled", False)
        if presence == "away" or is_snooze:
            say(text="Taimoor has been notified, he will look into it!")
    except Exception as e:
        logger.error(f"❌ Slack check error: {e}")

# --- Health Check Server ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, format, *args): return

def run_server():
    port = int(os.getenv("PORT", 8080))
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()

def main():
    if not os.getenv("SLACK_BOT_TOKEN") or not os.getenv("NOTION_TOKEN"):
        logger.error("❌ Missing critical environment variables.")
        return

    # Start Health Server
    threading.Thread(target=run_server, daemon=True).start()

    # Start Scheduler
    scheduler = BackgroundScheduler()
    # SCHEDULE: Friday at 5:00 PM (17:00)
    scheduler.add_job(generate_weekly_report, 'cron', day_of_week='fri', hour=17, minute=0)
    scheduler.start()
    logger.info("⏰ Scheduler started (Weekly Report: Fridays at 5 PM)")

    # Start Slack Listener
    logger.info("⚡️ Agent Worker starting...")
    SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN")).start()

if __name__ == "__main__":
    main()
