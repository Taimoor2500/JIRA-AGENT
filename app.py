import streamlit as st
import os
import threading
import re
from datetime import datetime
from agent import JiraAgent
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Page configuration
st.set_page_config(page_title="Jira Agent Dashboard", page_icon="🚀", layout="wide")

# --- TRULY GLOBAL LOGS (Persistent across threads) ---
if "GLOBAL_LOG_LIST" not in st.session_state:
    st.session_state.GLOBAL_LOG_LIST = []

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.GLOBAL_LOG_LIST.append(f"[{ts}] {msg}")
    if len(st.session_state.GLOBAL_LOG_LIST) > 20:
        st.session_state.GLOBAL_LOG_LIST.pop(0)

# --- Slack Listener ---
@st.cache_resource
def start_slack_listener():
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")
    my_id = os.getenv("MY_SLACK_ID")

    if not bot_token or not app_token or not my_id:
        return "⚠️ Missing Credentials"

    def run_listener():
        try:
            app = App(token=bot_token)
            
            @app.event("message")
            def handle_message_events(body, client, say):
                event = body.get("event", {})
                text = event.get("text", "")
                
                if my_id and f"<@{my_id}>" in text:
                    try:
                        # Check Presence
                        p_res = client.users_getPresence(user=my_id)
                        presence = p_res.get("presence", "unknown")
                        
                        # Check DND/Snooze
                        d_res = client.dnd_info(user=my_id)
                        is_snoozing = d_res.get("snooze_enabled", False)
                        is_dnd = d_res.get("dnd_enabled", False)

                        # DEBUG: This will show in Streamlit server logs
                        print(f"🕵️ MENTION: User={my_id}, Pres={presence}, Snooze={is_snoozing}, DND={is_dnd}")

                        # ONLY reply if status is definitely AWAY or notifications are PAUSED
                        if presence == "away" or is_snoozing or is_dnd:
                            say(text="Taimoor has been notified, he will look into it!")
                    except Exception as e:
                        print(f"❌ Status Check Error: {e}")

            handler = SocketModeHandler(app, app_token)
            print("⚡ Slack Listener: Connecting...")
            handler.start()
        except Exception as e:
            print(f"❌ Slack Listener CRASHED: {e}")

    thread = threading.Thread(target=run_listener, daemon=True)
    thread.start()
    return "🟢 Online"

# Initialize
listener_status = start_slack_listener()

st.title("🚀 Jira & Multi-Skill Agent")
st.markdown("Automate your Jira tickets, Slack messages, and Notion work logs with AI.")

# Sidebar
with st.sidebar:
    st.header("Service Status")
    st.write(f"**Jira:** {'✅' if os.getenv('JIRA_URL') else '❌'}")
    st.write(f"**Slack:** {'✅' if os.getenv('SLACK_BOT_TOKEN') else '❌'}")
    st.write(f"**Notion:** {'✅' if os.getenv('NOTION_TOKEN') else '❌'}")
    st.divider()
    st.write(f"**Auto-Responder:** {listener_status}")
    st.caption(f"Listening for: {os.getenv('MY_SLACK_ID')}")
    
    if st.button("Refresh Page"):
        st.rerun()

# Main UI
# ... (rest of the generate/post code remains the same)
