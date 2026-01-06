import streamlit as st
import os
import threading
from agent import JiraAgent
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Page configuration
st.set_page_config(page_title="Jira Agent Dashboard", page_icon="🚀", layout="wide")

# --- Slack Listener Global Singleton ---
@st.cache_resource
def start_global_slack_listener():
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")
    my_id = os.getenv("MY_SLACK_ID")

    if not bot_token or not app_token or not my_id:
        st.warning("⚠️ Slack Listener: Missing credentials in Secrets. Auto-responder disabled.")
        return False

    def run_listener():
        try:
            app = App(token=bot_token)
            print(f"📡 Slack Listener: Global thread started. Listening for {my_id}...")

            @app.event("message")
            def handle_message_events(body, client, say):
                event = body.get("event", {})
                text = event.get("text", "")
                print(f"📩 Bot saw message: {text[:50]}...")
                
                if my_id and f"<@{my_id}>" in text:
                    try:
                        # 1. Check Presence (Active vs Away)
                        presence_res = client.users_getPresence(user=my_id)
                        is_away = presence_res.get("presence") == "away"

                        # 2. Check DND status (handles both manual Snooze and scheduled DND)
                        dnd_res = client.dnd_info(user=my_id)
                        # Check both 'snooze_enabled' (manual pause) and 'dnd_enabled' (scheduled)
                        is_dnd = dnd_res.get("snooze_enabled", False) or dnd_res.get("dnd_enabled", False)

                        print(f"🕵️ Status for {my_id}: Presence={presence_res.get('presence')}, Snooze={dnd_res.get('snooze_enabled')}, DND_Enabled={dnd_res.get('dnd_enabled')}")

                        # Only reply if you are away OR in any DND state
                        if is_away or is_dnd:
                            print(f"🔔 Mention detected while {my_id} is unavailable. Responding...")
                            say(text="Taimoor has been notified, he will look into it!")
                        else:
                            print(f"ℹ️ Mention detected, but {my_id} is Active. Bot remains silent.")
                    except Exception as e:
                        print(f"❌ Error checking user status: {e}")
                        # If the check fails (e.g. permission issue), we stay silent to be safe

            handler = SocketModeHandler(app, app_token)
            handler.start()
        except Exception as e:
            print(f"❌ Slack Listener Runtime Error: {e}")

    # Start thread
    thread = threading.Thread(target=run_listener, daemon=True)
    thread.start()
    return True

# Initialize once
start_global_slack_listener()

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

# Sidebar for configuration status
with st.sidebar:
    st.header("Service Status")
    jira_status = "✅ Configured" if os.getenv("JIRA_URL") else "❌ Not Configured"
    slack_status = "✅ Configured" if os.getenv("SLACK_BOT_TOKEN") else "❌ Not Configured"
    notion_status = "✅ Configured" if os.getenv("NOTION_TOKEN") else "❌ Not Configured"
    
    st.write(f"**Jira:** {jira_status}")
    st.write(f"**Slack:** {slack_status}")
    st.write(f"**Notion:** {notion_status}")

# Main Chat/Input Area
if "current_version" not in st.session_state:
    st.session_state.current_version = None
if "original_prompt" not in st.session_state:
    st.session_state.original_prompt = None

user_input = st.text_area("What would you like to do?", placeholder="e.g. Create a bug for login failure on iOS or Log my work in Notion...")

col1, col2 = st.columns([1, 5])

with col1:
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
    
    # Text area for manual edits or just viewing
    edited_content = st.text_area("Edit or Review", value=st.session_state.current_version, height=400)
    st.session_state.current_version = edited_content

    # Action Buttons
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("🚀 Post to Platform"):
            content = st.session_state.current_version
            with st.spinner("Executing..."):
                # Routing logic (reusing logic from agent.py)
                if any(x in content for x in ["Channel", "Recipient"]):
                    # Slack
                    channel = None
                    message_body = ""
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if "Channel" in line or "Recipient" in line:
                            import re
                            parts = line.replace('**', ':').split(':')
                            if len(parts) > 1:
                                channel = parts[-1].strip().lstrip('#').strip()
                        if "Message" in line:
                            message_body = '\n'.join(lines[i+1:]).strip()
                            break
                    
                    if channel and message_body:
                        res = st.session_state.agent.slack.send_message(channel, message_body)
                        st.success(res)
                    else:
                        st.error("Could not identify channel or message body.")
                
                elif "Task Category" in content:
                    # Notion
                    cat = next((line.split('**')[-1].strip() for line in content.split('\n') if "Task Category" in line), "Development")
                    res = st.session_state.agent.notion.log_work(cat, content)
                    st.success(res)
                
                else:
                    # Jira
                    summary = ""
                    lines = [l.strip() for l in content.split('\n')]
                    for i, line in enumerate(lines):
                        if "Summary" in line:
                            summary = line.split(':', 1)[-1].strip() if ':' in line else (lines[i+1] if i+1 < len(lines) else "")
                            break
                    summary = summary.replace('**', '').replace('#', '').strip() or "New Ticket"
                    res = st.session_state.agent.jira.create_issue(summary, content)
                    st.success(res)

    with action_col2:
        # Revision notes
        rev_notes = st.text_input("Revision Notes", placeholder="e.g. Add more detail...")
        if st.button("🔄 Revise"):
            if rev_notes:
                with st.spinner("Revising..."):
                    st.session_state.current_version = st.session_state.agent.generate_ticket(
                        st.session_state.original_prompt, 
                        st.session_state.current_version, 
                        rev_notes
                    )
                    st.rerun()
            else:
                st.warning("Enter revision notes.")

    with action_col3:
        if st.button("🗑️ Clear"):
            st.session_state.current_version = None
            st.session_state.original_prompt = None
            st.rerun()

