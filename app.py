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

# --- Persistent Global Logs ---
if "GLOBAL_LOGS" not in st.session_state:
    st.session_state.GLOBAL_LOGS = [f"[{datetime.now().strftime('%H:%M:%S')}] 🖥️ App Started"]

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.GLOBAL_LOGS.append(f"[{ts}] {msg}")
    if len(st.session_state.GLOBAL_LOGS) > 15:
        st.session_state.GLOBAL_LOGS.pop(0)

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
            print("📡 Slack Listener: Global thread initiated.")

            @app.event("message")
            def handle_message_events(body, client, say):
                event = body.get("event", {})
                text = event.get("text", "")
                
                # Check for mention
                if my_id and f"<@{my_id}>" in text:
                    try:
                        presence_res = client.users_getPresence(user=my_id)
                        presence = presence_res.get("presence", "unknown")
                        dnd_res = client.dnd_info(user=my_id)
                        is_unavailable = (presence == "away" or 
                                        dnd_res.get("snooze_enabled") or 
                                        dnd_res.get("dnd_enabled"))

                        if is_unavailable:
                            say(text="Taimoor has been notified, he will look into it!")
                    except Exception as e:
                        print(f"❌ Status Error: {e}")

            handler = SocketModeHandler(app, app_token)
            handler.start()
        except Exception as e:
            print(f"❌ Listener Runtime Error: {e}")

    thread = threading.Thread(target=run_listener, daemon=True)
    thread.start()
    return "🟢 Online"

# Initialize
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
    
    if st.button("Refresh Page"):
        st.rerun()

    st.subheader("System Logs")
    for log in reversed(st.session_state.GLOBAL_LOGS):
        st.caption(log)

# Main Chat/Input Area
if "current_version" not in st.session_state:
    st.session_state.current_version = None
if "original_prompt" not in st.session_state:
    st.session_state.original_prompt = None

user_input = st.text_area("What would you like to do?", placeholder="e.g. Create a bug for login failure on iOS...")

if st.button("Generate", type="primary"):
    if user_input:
        with st.spinner("AI is thinking..."):
            st.session_state.original_prompt = user_input
            st.session_state.current_version = st.session_state.agent.generate_ticket(user_input)
    else:
        st.warning("Please enter a prompt.")

# Display Result and Actions
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
                        if "Channel" in line or "Recipient" in line:
                            parts = line.replace('**', ':').split(':')
                            if len(parts) > 1:
                                channel = parts[-1].strip().lstrip('#').strip()
                        if "Message" in line:
                            message_body = '\n'.join(lines[i+1:]).strip()
                            break
                    if channel and message_body:
                        st.success(st.session_state.agent.slack.send_message(channel, message_body))
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
