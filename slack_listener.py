import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Initialize your app with your bot token
app = App(token=os.getenv("SLACK_BOT_TOKEN"))
MY_ID = os.getenv("MY_SLACK_ID") # e.g., U012345678

@app.event("message")
def handle_message_events(body, logger, say):
    event = body.get("event", {})
    text = event.get("text", "")
    
    # Slack mentions look like <@U12345678> in the raw text
    if MY_ID and f"<@{MY_ID}>" in text:
        print(f"🔔 Mention detected! Responding...")
        say(text="Taimoor has been notified, he will look into it! 🫡")

if __name__ == "__main__":
    if os.getenv("SLACK_APP_TOKEN") and MY_ID:
        handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
        print(f"⚡️ Slack Auto-Responder is running! Listening for mentions of {MY_ID}")
        handler.start()
    else:
        print("❌ Missing SLACK_APP_TOKEN or MY_SLACK_ID in environment.")
