"""
Standalone Slack Listener for Koyeb/Cloud deployment.
Includes a dummy web server for health checks and ntfy.sh integration for push notifications.
"""

import os
import logging
import threading
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Slack app
app = App(token=os.getenv("SLACK_BOT_TOKEN"))
MY_ID = os.getenv("MY_SLACK_ID")
NTFY_TOPIC = os.getenv("NTFY_TOPIC") # e.g., 'taimoor-jira-alerts'

def send_push_notification(message):
    """Send a push notification via ntfy.sh."""
    if not NTFY_TOPIC:
        logger.warning("⚠️ NTFY_TOPIC not set. Skipping push notification.")
        return
    
    try:
        url = f"https://ntfy.sh/{NTFY_TOPIC}"
        response = requests.post(
            url,
            data=message.encode('utf-8'),
            headers={
                "Title": "Slack Mention Detected",
                "Priority": "high",
                "Tags": "bell,slack"
            }
        )
        if response.status_code == 200:
            logger.info(f"📲 Push notification sent to topic: {NTFY_TOPIC}")
        else:
            logger.error(f"❌ Failed to send push notification: {response.text}")
    except Exception as e:
        logger.error(f"❌ Error sending push notification: {e}")

# --- Dummy Web Server for Health Checks ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    
    def log_message(self, format, *args):
        return

def run_health_check_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"💖 Health check server started on port {port}")
    server.serve_forever()

# --- Slack Event Handlers ---
@app.event("message")
def handle_message_events(body, client, say):
    """Handle incoming messages and respond to mentions when user is away."""
    event = body.get("event", {})
    text = event.get("text", "")
    user_who_mentioned = event.get("user", "Unknown User")
    channel = event.get("channel", "Unknown Channel")
    
    if not MY_ID or f"<@{MY_ID}>" not in text:
        return
    
    logger.info(f"🔔 Mention detected from {user_who_mentioned}!")
    
    # Notify phone immediately that a mention happened
    notification_text = f"User <@{user_who_mentioned}> mentioned you in Slack: \"{text}\""
    send_push_notification(notification_text)
    
    should_reply = False
    try:
        presence_res = client.users_getPresence(user=MY_ID)
        presence = presence_res.get("presence", "active")
        
        dnd_res = client.dnd_info(user=MY_ID)
        is_snooze = dnd_res.get("snooze_enabled", False)
        
        logger.info(f"🕵️ Presence={presence}, Snooze={is_snooze}")
        
        if presence == "away" or is_snooze:
            should_reply = True
            logger.info("➡️ User is AWAY or Snoozed. Will reply.")
        else:
            logger.info("➡️ User is ACTIVE. Staying silent.")
            
    except Exception as e:
        logger.error(f"❌ Status check failed: {e}. Staying silent.")
        should_reply = False
    
    if should_reply:
        say(text="Taimoor has been notified, he will look into it!")
        logger.info("✅ Auto-reply sent.")

@app.event("app_mention")
def handle_app_mention(body, say):
    say("👋 I'm the auto-responder bot. I'll notify Taimoor when he's away!")

def main():
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")
    
    if not bot_token or not app_token or not MY_ID:
        logger.error("❌ Missing environment variables")
        return
    
    threading.Thread(target=run_health_check_server, daemon=True).start()
    
    logger.info(f"⚡️ Slack Listener starting...")
    logger.info(f"👤 Watching for mentions of: {MY_ID}")
    
    handler = SocketModeHandler(app, app_token)
    handler.start()

if __name__ == "__main__":
    main()
