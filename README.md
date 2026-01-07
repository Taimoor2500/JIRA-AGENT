# Jira Agent 

An AI-powered CLI assistant designed to generate high-quality, industry-standard Jira tickets and post them directly to your Jira board. Powered by **Groq (Llama 3.3)** and **LangChain**.

## Features

-   **AI Generation**: Instantly transforms brief prompts into detailed Jira tickets (Stories, Bugs, Tasks, Epics).
-   **Industry Standard Templates**: Uses structured formatting (INVEST criteria, clear ACs, reproduction steps).
-   **Multi-Platform Integration**: Post generated content directly to Jira, Slack, or Notion.
-   **Slack Auto-Responder**: Monitors Slack mentions and provides automatic "away" replies if you are inactive.
-   **Weekly Notion Reporting**: Automatically summarizes your week's activity into professional reports on Notion.
-   **Interactive Revision**: Review and refine tickets through a conversation with the agent before publishing.
-   **Custom Skills**: Easily extendable by adding new `.md` templates to the `skills/` directory.
-   **Push Notifications**: Integrated with `ntfy.sh` to keep you updated on mentions and report status.

## Project Structure

```
.
├── skills/
│   ├── jira-ticket-template/
│   │   └── SKILL.md        # AI instructions and ticket templates
│   ├── slack-message/
│   │   └── SKILL.md        # Slack message templates
│   └── notion-work-log/
│       └── SKILL.md        # Notion work log templates
├── clients/
│   ├── jira_client.py      # Jira API client
│   ├── slack_client.py     # Slack API client
│   └── notion_client.py    # Notion API client
├── agent.py                # Core AI agent logic
├── agent_worker.py         # Background worker (Slack listener, Scheduler)
├── app.py                  # Backend shared state/logger
├── ui.py                   # Streamlit dashboard UI
├── requirements.txt        # Python dependencies
├── .env                    # API keys (not committed)
└── .gitignore              # Project exclusions
```

## Setup

### 1. Prerequisites
-   Python 3.10+
-   A [Groq API Key](https://console.groq.com/) (Free)
-   A [Jira API Token](https://id.atlassian.com/manage-profile/security/api-tokens)

### 2. Installation
Clone the repository and install the dependencies:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt### 3. Configuration
Create a `.env` file in the root directory:
```bash
# AI Configuration
GROQ_API_KEY=your_groq_api_key

# Jira Configuration
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=YOURPROJ

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
MY_SLACK_ID=U12345678

# Notion Configuration
NOTION_TOKEN=secret_your_notion_token
NOTION_DATABASE_ID=your_database_id

# Other
NTFY_TOPIC=your_optional_topic
PORT=8080
```

## Usage

### 1. Interactive CLI Agent
Run the main agent to generate tickets, Slack messages, or Notion logs:
```bash
python agent.py
```

### 2. Dashboard UI
Run the Streamlit dashboard to monitor logs and status:
```bash
streamlit run ui.py
```

### 3. Background Worker
Run the worker for Slack auto-responding and scheduled reporting:
```bash
python agent_worker.py
```

## Workflow Examples
1.  **Jira**: `Create a bug for login failure on iOS` -> Review -> Post.
2.  **Slack**: `Draft a message to #general about the upcoming release` -> Review -> Send.
3.  **Notion**: `Log 2 hours of development on feature-X` -> Automatically updates Jira status to "In Progress".
4.  **Reporting**: Every Friday at 5 PM, the worker generates a summary of all Notion logs for the week.

## Deployment
This project is designed to be deployed on platforms like **Koyeb** or **Heroku**. Use the `Dockerfile` and `Procfile` provided for easy setup.

## License
MIT
