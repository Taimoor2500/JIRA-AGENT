import logging
import requests
from slack_bolt import App
from src.core.config import config

logger = logging.getLogger(__name__)

class SlackResponderService:
    def __init__(self):
        self.app = App(token=config.SLACK_BOT_TOKEN)
        self.my_id = config.MY_SLACK_ID
        self.ntfy_topic = config.NTFY_TOPIC
        self._setup_handlers()

    def _send_push_notification(self, message, title="Agent Worker"):
        """Send a push notification via ntfy.sh."""
        if not self.ntfy_topic:
            return
        try:
            requests.post(
                f"https://ntfy.sh/{self.ntfy_topic}",
                data=message.encode('utf-8'),
                headers={"Title": title, "Priority": "high", "Tags": "robot,chart_with_upwards_trend"}
            )
        except Exception as e:
            logger.error(f"❌ Push error: {e}")

    def _setup_handlers(self):
        @self.app.event("message")
        def handle_message(body, client, say):
            event = body.get("event", {})
            text = event.get("text", "")
            user_id = event.get("user", "")
            channel_id = event.get("channel", "")
            
            if event.get("bot_id") or not self.my_id or f"<@{self.my_id}>" not in text:
                return
            
            # Resolve names
            user_name = "Someone"
            try:
                u_info = client.users_info(user=user_id)
                if u_info.get("ok"):
                    user_name = u_info.get("user", {}).get("real_name") or u_info.get("user", {}).get("name", "Someone")
            except:
                pass

            channel_name = "a channel"
            try:
                if channel_id.startswith("D"):
                    channel_name = "Direct Message"
                else:
                    c_info = client.conversations_info(channel=channel_id)
                    if c_info.get("ok"):
                        channel_name = f"#{c_info.get('channel', {}).get('name', 'unknown')}"
            except:
                pass

            clean_text = text.replace(f"<@{self.my_id}>", "").strip()
            if not clean_text:
                clean_text = "(just tagged you)"

            self._send_push_notification(f"{user_name}: {clean_text}", f"Mention in {channel_name}")
            
            # Auto-reply if away
            try:
                presence = client.users_getPresence(user=self.my_id).get("presence", "active")
                is_snooze = client.dnd_info(user=self.my_id).get("snooze_enabled", False)
                if presence == "away" or is_snooze:
                    say(text="Taimoor has been notified, he will look into it!")
            except Exception as e:
                logger.error(f"❌ Slack check error: {e}")

