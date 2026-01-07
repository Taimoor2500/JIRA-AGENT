"""
Backend services for Jira Agent - Slack listener and shared state management.
Run the UI with: streamlit run ui.py
"""

import os
import threading
from datetime import datetime
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# --- Persistent Global Log Store ---
class GlobalLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.logs = [f"[{datetime.now().strftime('%H:%M:%S')}] 🖥️ App initialized"]
        return cls._instance
    
    def add(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{ts}] {msg}")
        if len(self.logs) > 20:
            self.logs.pop(0)
        # Also print to standard server logs for reliability
        print(f"DEBUG LOG: {msg}")


# Singleton accessor for the logger
_global_logger = None

def get_global_logger():
    """Get the global logger singleton instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = GlobalLogger()
    return _global_logger


# --- Slack Listener ---
_listener_started = False
_listener_status = "⚪ Not Started"

def start_slack_listener(logger=None):
    """
    Start the Slack listener in a background thread.
    Returns the current status string.
    """
    global _listener_started, _listener_status
    
    if _listener_started:
        return _listener_status
    
    if logger is None:
        logger = get_global_logger()
    
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")
    my_id = os.getenv("MY_SLACK_ID")

    if not bot_token or not app_token or not my_id:
        _listener_status = "⚠️ Missing Credentials"
        return _listener_status

    def run_listener():
        global _listener_status
        try:
            app = App(token=bot_token)
            logger.add("📡 Slack Listener: Connecting...")

            @app.event("message")
            def handle_message_events(body, client, say):
                event = body.get("event", {})
                text = event.get("text", "")
                
                if my_id and f"<@{my_id}>" in text:
                    logger.add("🔔 Mention detected!")
                    
                    # Default: DO NOT REPLY
                    should_reply = False
                    
                    try:
                        # 1. Check Presence (active vs away)
                        p_res = client.users_getPresence(user=my_id)
                        presence = p_res.get("presence", "active")  # Default to active = no reply
                        
                        # 2. Check if notifications are currently PAUSED (snooze)
                        d_res = client.dnd_info(user=my_id)
                        is_snooze = d_res.get("snooze_enabled", False)  # Manual pause
                        
                        logger.add(f"🕵️ Pres={presence}, Snooze={is_snooze}")

                        # STRICT: Only reply if AWAY or notifications are manually PAUSED
                        if presence == "away" or is_snooze:
                            should_reply = True
                            logger.add("➡️ User is AWAY or Snoozed. Will reply.")
                        else:
                            logger.add("➡️ User is ACTIVE. Staying silent.")
                            
                    except Exception as e:
                        logger.add(f"❌ Status Check Failed: {e}. Staying silent.")
                        should_reply = False  # On ANY error, stay silent
                    
                    # Only reply if we explicitly determined we should
                    if should_reply:
                        say(text="Taimoor has been notified, he will look into it!")

            handler = SocketModeHandler(app, app_token)
            handler.start()
        except Exception as e:
            logger.add(f"❌ Listener Critical Error: {e}")
            _listener_status = f"❌ Error: {e}"

    thread = threading.Thread(target=run_listener, daemon=True)
    thread.start()
    _listener_started = True
    _listener_status = "🟢 Online"
    return _listener_status


# Allow running this file directly for testing
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    logger = get_global_logger()
    status = start_slack_listener(logger)
    print(f"Slack Listener Status: {status}")
    
    # Keep the main thread alive
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
