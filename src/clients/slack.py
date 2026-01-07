import os
from slack_sdk import WebClient

class SlackClient:
    def __init__(self):
        self.token = os.getenv("SLACK_BOT_TOKEN")
        self.client = None

        if self.token:
            try:
                self.client = WebClient(token=self.token)
                print("✅ Slack connection initialized")
            except Exception as e:
                print(f"❌ Slack Initialization Error: {e}")

    def send_message(self, channel, message):
        if not self.client:
            return "❌ Slack bot token not configured."
        
        try:
            # Convert standard Markdown **bold** to Slack *bold*
            formatted_message = message.replace('**', '*')
            
            target = channel if channel.startswith(('#', 'C', 'U')) else f"#{channel}"
            self.client.chat_postMessage(channel=target, text=formatted_message)
            return f"✅ Slack message sent to {target}"
        except Exception as e:
            return f"❌ Failed to send Slack message: {str(e)}"

