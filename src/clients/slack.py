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

    def send_message(self, channel, message, thread_ts=None):
        if not self.client:
            return "❌ Slack bot token not configured."
        
        try:
            # Convert standard Markdown **bold** to Slack *bold*
            formatted_message = message.replace('**', '*')
            
            target = channel if channel.startswith(('#', 'C', 'U')) else f"#{channel}"
            self.client.chat_postMessage(channel=target, text=formatted_message, thread_ts=thread_ts)
            return f"✅ Slack message sent to {target}"
        except Exception as e:
            error_msg = str(e)
            if "channel_not_found" in error_msg:
                return f"❌ Slack Error: Channel '{target}' not found. Ensure the bot is invited to the channel (/invite @YourBotName)."
            return f"❌ Failed to send Slack message: {error_msg}"
