import streamlit as st
import os
import threading
import time
import re
from datetime import datetime
from agent import JiraAgent
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Page configuration
st.set_page_config(page_title="Jira Agent Dashboard", page_icon="🚀", layout="wide")

# --- Persistent Global Log Store ---
class GlobalLogger:
    def __init__(self):
        self.logs = [f"[{datetime.now().strftime('%H:%M:%S')}] 🖥️ App initialized"]
    def add(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{ts}] {msg}")
        if len(self.logs) > 20: self.logs.pop(0)
        # Also print to standard server logs for reliability
        print(f"DEBUG LOG: {msg}")

@st.cache_resource
def get_global_logger():
    return GlobalLogger()

logger = get_global_logger()

# --- Slack Listener Global Singleton ---
@st.cache_resource
def start_slack_listener():
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")
    my_id = os.getenv("MY_SLACK_ID")

    if not bot_token or not app_token or not my_id:
        print("❌ CRITICAL: Missing Slack credentials in environment!")
        return "⚠️ Missing Credentials"

    def run_listener():
        try:
            print("🚀 THREAD STARTING: Attempting to connect to Slack...")
            app = App(token=bot_token)
            
            @app.event("message")
            def handle_message_events(body, client, say):
                event = body.get("event", {})
                text = event.get("text", "")
                
                # Check for mention using ID format <@ID>
                if my_id and f"<@{my_id}>" in text:
                    logger.add(f"🔔 Mention of {my_id} detected. Checking status...")
                    try:
                        # 1. Check Presence
                        presence_res = client.users_getPresence(user=my_id)
                        presence = presence_res.get("presence", "unknown")
                        
                        # 2. Check DND
                        dnd_res = client.dnd_info(user=my_id)
                        is_snooze = dnd_res.get("snooze_enabled", False)
                        is_dnd = dnd_res.get("dnd_enabled", False)

                        logger.add(f"🕵️ Status: Pres={presence}, Snooze={is_snooze}, DND={is_dnd}")

                        # ONLY reply if status is 'away' OR any DND is active
                        if presence == "away" or is_snooze or is_dnd:
                            logger.add("✅ Sending auto-reply.")
                            say(text="Taimoor has been notified, he will look into it!")
                        else:
                            logger.add("ℹ️ User is Active. No reply sent.")
                    except Exception as e:
                        logger.add(f"❌ Status Check Error: {e}")

            handler = SocketModeHandler(app, app_token)
            logger.add("🔌 Socket Mode: Connecting...")
            handler.start() # This is a blocking call, runs inside thread
        except Exception as e:
            print(f"❌ THREAD CRASHED: {e}")
            logger.add(f"❌ Listener Critical Error: {e}")

    # Start the background thread
    thread = threading.Thread(target=run_listener, daemon=True)
    thread.start()
    return "🟢 Online"

# Initialize Listener
listener_status = start_slack_listener()

st.title("🚀 Jira & Multi-Skill Agent")
st.markdown("Automate your Jira tickets, Slack messages, and Notion work logs with AI.")

# Initialize Agent
@st.cache_resource
def get_agent():
    return JiraAgent()

if "agent" not in st.session_state:
    try:
        st.session_state.agent = get_agent()
    except Exception as e:
        st.error(f"Failed to initialize agent: {e}")

# Sidebar
with st.sidebar:
    st.header("Service Status")
    st.write(f"**Jira:** {'✅' if os.getenv('JIRA_URL') else '❌'}")
    st.write(f"**Slack:** {'✅' if os.getenv('SLACK_BOT_TOKEN') else '❌'}")
    st.write(f"**Notion:** {'✅' if os.getenv('NOTION_TOKEN') else '❌'}")
    st.divider()
    st.write(f"**Auto-Responder:** {listener_status}")
    
    if st.button("🔄 Refresh Logs"):
        st.rerun()

    st.subheader("Live Activity Logs")
    for log in reversed(logger.logs):
        st.caption(log)

# Main Chat Input
user_input = st.text_area("What would you like to do?", placeholder="e.g. Create a bug for login failure on iOS...")

if st.button("Generate", type="primary"):
    if user_input:
        with st.spinner("AI is thinking..."):
            st.session_state.original_prompt = user_input
            st.session_state.current_version = st.session_state.agent.generate_ticket(user_input)
    else:
        st.warning("Please enter a prompt.")

# Display Results
if "current_version" in st.session_state and st.session_state.current_version:
    st.divider()
    st.subheader("Generated Output")
    edited_content = st.text_area("Edit or Review", value=st.session_state.current_version, height=400)
    st.session_state.current_version = edited_content

    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        if st.button("🚀 Post to Platform"):
            # (Reuse existing routing logic...)
            content = st.session_state.current_version
            if any(x in content for x in ["Channel", "Recipient"]):
                # Slack send logic
                pass 
            # ... (the rest of the action buttons)
