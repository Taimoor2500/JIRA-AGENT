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
        return "⚠️ Missing Credentials"

    def run_listener():
        try:
            app = App(token=bot_token)
            logger.add("📡 Slack Listener: Connecting...")

            @app.event("message")
            def handle_message_events(body, client, say):
                event = body.get("event", {})
                text = event.get("text", "")
                
                if my_id and f"<@{my_id}>" in text:
                    logger.add(f"🔔 Mention of {my_id} detected. Checking status...")
                    try:
                        # 1. Check Presence
                        p_res = client.users_getPresence(user=my_id)
                        presence = p_res.get("presence", "unknown")
                        
                        # 2. Check DND
                        d_res = client.dnd_info(user=my_id)
                        is_snooze = d_res.get("snooze_enabled", False)
                        is_dnd = d_res.get("dnd_enabled", False)

                        logger.add(f"🕵️ Status: Pres={presence}, Snooze={is_snooze}, DND={is_dnd}")

                        # ONLY reply if status is 'away' OR any DND is active
                        if presence == "away" or is_snooze or is_dnd:
                            logger.add("✅ Sending auto-reply.")
                            say(text="Taimoor has been notified, he will look into it!")
                        else:
                            logger.add("ℹ️ User is Active. Staying silent.")
                    except Exception as e:
                        logger.add(f"❌ Status Check Error: {e}")

            handler = SocketModeHandler(app, app_token)
            handler.start()
        except Exception as e:
            logger.add(f"❌ Listener Critical Error: {e}")

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
    st.caption(f"Listening for: {os.getenv('MY_SLACK_ID')}")
    
    if st.button("🔄 Refresh Logs"):
        st.rerun()

    st.subheader("Live Activity Logs")
    for log in reversed(logger.logs):
        st.caption(log)

# Main UI
if "current_version" not in st.session_state:
    st.session_state.current_version = None
if "original_prompt" not in st.session_state:
    st.session_state.original_prompt = None

user_input = st.text_area("What would you like to do?", placeholder="e.g. Create a bug for login failure or Log my work...")

if st.button("Generate", type="primary"):
    if user_input:
        with st.spinner("AI is thinking..."):
            st.session_state.original_prompt = user_input
            st.session_state.current_version = st.session_state.agent.generate_ticket(user_input)
    else:
        st.warning("Please enter a prompt.")

if st.session_state.current_version:
    st.divider()
    st.subheader("Generated Output")
    edited_content = st.text_area("Edit or Review", value=st.session_state.current_version, height=400)
    st.session_state.current_version = edited_content

    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("🚀 Post to Platform"):
            content = st.session_state.current_version
            with st.spinner("Executing..."):
                if any(x in content for x in ["Channel", "Recipient"]):
                    channel = None
                    message_body = ""
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if any(k in line for k in ["Channel", "Recipient"]):
                            parts = line.replace('**', ':').split(':')
                            if len(parts) > 1:
                                channel = parts[-1].strip().lstrip('#').strip()
                        if "Message" in line:
                            message_body = '\n'.join(lines[i+1:]).strip()
                            break
                    if channel and message_body:
                        st.success(st.session_state.agent.slack.send_message(channel, message_body))
                    else:
                        st.error("❌ Could not identify channel or message.")
                elif "Task Category" in content:
                    cat = next((line.split('**')[-1].strip() for line in content.split('\n') if "Task Category" in line), "Development")
                    st.success(st.session_state.agent.notion.log_work(cat, content))
                else:
                    summary = ""
                    lines = [l.strip() for l in content.split('\n')]
                    for i, line in enumerate(lines):
                        if "Summary" in line:
                            summary = line.split(':', 1)[-1].strip() if ':' in line else (lines[i+1] if i+1 < len(lines) else "")
                            break
                    summary = summary.replace('**', '').replace('#', '').strip() or "New Ticket"
                    st.success(st.session_state.agent.jira.create_issue(summary, content))

    with action_col2:
        rev_notes = st.text_input("Revision Notes")
        if st.button("🔄 Revise"):
            if rev_notes:
                st.session_state.current_version = st.session_state.agent.generate_ticket(st.session_state.original_prompt, st.session_state.current_version, rev_notes)
                st.rerun()

    with action_col3:
        if st.button("🗑️ Clear"):
            st.session_state.current_version = None
            st.session_state.original_prompt = None
            st.rerun()
