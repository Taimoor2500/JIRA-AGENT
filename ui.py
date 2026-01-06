import streamlit as st
import os
from agent import JiraAgent
from app import get_global_logger, start_slack_listener

# Page configuration
st.set_page_config(page_title="Jira Agent Dashboard", page_icon="🚀", layout="wide")

# Get shared logger and start listener
logger = get_global_logger()
listener_status = start_slack_listener(logger)

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

