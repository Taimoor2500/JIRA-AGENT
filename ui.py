import streamlit as st
import os
from agent import JiraAgent
from app import get_global_logger, get_external_status

# Page configuration
st.set_page_config(page_title="Jira Agent Dashboard", page_icon="🚀", layout="wide")

# Get shared logger
logger = get_global_logger()
listener_status = get_external_status()

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
                result = st.session_state.agent.post_content(content)
                if "❌" in result:
                    st.error(result)
                elif "⚠️" in result:
                    st.warning(result)
                else:
                    st.success(result)

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

