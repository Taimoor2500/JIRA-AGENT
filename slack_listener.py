"""
Standalone Slack Listener for Fly.io deployment.
Responds to mentions when user is away or has notifications paused.

Deploy with: fly deploy
"""

import os
import logging
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


@app.event("message")
def handle_message_events(body, client, say):
    """Handle incoming messages and respond to mentions when user is away."""
    event = body.get("event", {})
    text = event.get("text", "")
    
    # Check if this message mentions the user
    if not MY_ID or f"<@{MY_ID}>" not in text:
        return
    
    logger.info("🔔 Mention detected!")
    
    # Default: DO NOT REPLY (only reply when explicitly away)
    should_reply = False
    
    try:
        # 1. Check Presence (active vs away)
        presence_res = client.users_getPresence(user=MY_ID)
        presence = presence_res.get("presence", "active")
        
        # 2. Check if notifications are paused (snooze/DND)
        dnd_res = client.dnd_info(user=MY_ID)
        is_snooze = dnd_res.get("snooze_enabled", False)
        
        logger.info(f"🕵️ Presence={presence}, Snooze={is_snooze}")
        
        # Only reply if AWAY or notifications are manually PAUSED
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
    """Handle direct @mentions of the bot itself."""
    say("👋 I'm the auto-responder bot. I'll notify Taimoor when he's away!")


def main():
    """Start the Slack listener."""
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")
    
    if not bot_token:
        logger.error("❌ Missing SLACK_BOT_TOKEN")
        return
    if not app_token:
        logger.error("❌ Missing SLACK_APP_TOKEN")
        return
    if not MY_ID:
        logger.error("❌ Missing MY_SLACK_ID")
        return
    
    logger.info(f"⚡️ Slack Listener starting...")
    logger.info(f"👤 Watching for mentions of: {MY_ID}")
    
    handler = SocketModeHandler(app, app_token)
    handler.start()


if __name__ == "__main__":
    main()
