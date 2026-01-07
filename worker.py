import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from slack_bolt.adapter.socket_mode import SocketModeHandler
from apscheduler.schedulers.background import BackgroundScheduler

from src.core.config import config
from src.services.slack_service import SlackResponderService
from src.services.report_service import ReportService
from src.services.status_reminder_service import StatusReminderService
from src.services.velocity_service import VelocityService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Health Check Server ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        return

def run_health_server():
    port = config.PORT
    logger.info(f"🏥 Health server starting on port {port}")
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()

def self_ping():
    """Pings the app itself to prevent Koyeb from sleeping."""
    if not config.KOYEB_APP_URL:
        return
    
    try:
        url = config.KOYEB_APP_URL.strip().rstrip('/')
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        response = requests.get(url, timeout=10)
        logger.info(f"🛰️ Self-ping successful: {url} ({response.status_code})")
    except Exception as e:
        logger.error(f"❌ Self-ping failed: {e}")

def main():
    if not config.SLACK_BOT_TOKEN or not config.NOTION_TOKEN:
        logger.error("❌ Missing critical environment variables.")
        return

    # 1. Start Health Server
    threading.Thread(target=run_health_server, daemon=True).start()

    # 2. Start Scheduler for Weekly Report
    report_service = ReportService()
    reminder_service = StatusReminderService()
    velocity_service = VelocityService()
    
    scheduler = BackgroundScheduler()
    # SCHEDULE: Friday at 5:00 PM (17:00)
    scheduler.add_job(report_service.generate_weekly_report, 'cron', day_of_week='fri', hour=17, minute=0)
    
    # SCHEDULE: Daily at 9:30 AM for Velocity Forecast
    scheduler.add_job(velocity_service.forecast_sprint, 'cron', hour=9, minute=30)
    
    # SCHEDULE: Daily at 10:00 AM to check for sprint progress (Day 5)
    scheduler.add_job(reminder_service.check_and_send_reminders, 'cron', hour=10, minute=0)
    
    # SCHEDULE: Every 20 minutes to keep Koyeb awake
    if config.KOYEB_APP_URL:
        scheduler.add_job(self_ping, 'interval', minutes=20)
        logger.info(f"🛰️ Anti-sleep scheduled for {config.KOYEB_APP_URL}")

    scheduler.start()
    logger.info("⏰ Scheduler started (Weekly Report: Fridays at 5 PM, Daily Sprint Check: 10 AM)")

    # 3. Start Slack Listener
    if not config.SLACK_APP_TOKEN:
        logger.error("❌ SLACK_APP_TOKEN is missing. Slack Responder cannot start.")
        # We keep the process running because the Health Server and Scheduler might still be useful
        import time
        while True:
            time.sleep(3600)
    else:
        slack_service = SlackResponderService()
        logger.info("⚡️ Slack Responder starting...")
        SocketModeHandler(slack_service.app, config.SLACK_APP_TOKEN).start()

if __name__ == "__main__":
    main()

