# AI Project Manager (Jira Agent)

A comprehensive, AI-powered ecosystem designed to automate engineering management and project workflows. Beyond just generating high-quality Jira tickets, this agent acts as a full-time background worker that monitors sprint health, manages team updates, and bridges the gap between Jira, Slack, and Notion. Powered by **Groq (Llama 3.3)** and **LangChain**.

## Features

-   **AI Generation**: Instantly transforms brief prompts into detailed Jira tickets (Stories, Bugs, Tasks, Epics).
-   **Industry Standard Templates**: Uses structured formatting (INVEST criteria, clear ACs, reproduction steps).
-   **Multi-Platform Integration**: Post generated content directly to Jira, Slack, or Notion.
-   **Velocity Forecaster**: Daily automated analysis of Backend sprint progress.
    - Calculates real-time velocity (Points or Ticket count).
    - Identifies overdue sprints and remaining risk.
    - Lists specific remaining tasks in Slack notifications.
-   **Smart Sprint Reminders**: Automatically pings the team on Day 5 of the sprint for updates.
    - Specifically targets Backend-related tasks.
    - Intelligently ignores non-backend (FE/Product) tickets.
    - Skips managers/specific users (e.g., Taimoor) from update requests.
-   **Slack Auto-Responder**: Monitors Slack mentions and provides automatic "away" replies if you are inactive.
-   **Weekly Notion Reporting**: Automatically summarizes your week's activity into professional reports on Notion.
-   **Interactive Revision**: Review and refine tickets through a conversation with the agent before publishing.
-   **Deployment Protection**: Built-in self-ping mechanism to keep the worker active on platforms like Koyeb.
-   **Push Notifications**: Integrated with `ntfy.sh` to keep you updated on mentions and report status.

## Project Structure

```
.
├── src/
│   ├── agents/             # AI agent logic (JiraAgent)
│   ├── clients/            # API clients (Jira, Slack, Notion)
│   ├── services/           # Background services (Slack Responder, Velocity, Reporting)
│   ├── core/               # Centralized config and constants
│   └── utils/              # Shared utilities (Logger)
├── skills/                 # AI instructions and templates (.md)
├── cli.py                  # Interactive CLI entry point
├── worker.py               # Background worker (Scheduler & Listener)
├── ui.py                   # Streamlit dashboard UI
├── requirements.txt        # Python dependencies
├── .env                    # API keys (not committed)
└── Dockerfile              # Deployment configuration
```

## Setup

### 1. Prerequisites
-   Python 3.10+
-   A [Groq API Key](https://console.groq.com/)
-   A [Jira API Token](https://id.atlassian.com/manage-profile/security/api-tokens)
-   Slack & Notion tokens (for worker/logging)

### 2. Installation
Clone the repository and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file based on the environment variables mentioned in `src/core/config.py`. Key variables include:
- `GROQ_API_KEY`: Groq AI access.
- `JIRA_URL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`, `JIRA_BOARD_ID`: Jira integration.
- `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `MY_SLACK_ID`: Slack automation.
- `NOTION_TOKEN`, `NOTION_DATABASE_ID`: Notion logging.
- `KOYEB_APP_URL`: Anti-sleep pings for deployment.

## Usage

### 1. Interactive CLI Agent
Run the main agent to generate content:
```bash
python cli.py
```

### 2. Dashboard UI
Monitor logs and generate content via web interface:
```bash
streamlit run ui.py
```

### 3. Background Worker
Run the worker for Slack mentions and scheduled reporting:
```bash
python worker.py
```

## Workflow Examples
1.  **Jira**: `Create a bug for login failure on iOS` -> Review -> Post.
2.  **Velocity Forecast**: Every morning at 9:30 AM, the bot posts a Backend velocity update to `#propone-backend-dev`.
3.  **Sprint Reminder**: On Day 5 of a Backend sprint, the bot pings everyone with pending tasks at 10:00 AM.
4.  **Notion**: `Log 2 hours of development on feature-X` -> Automatically updates Jira status to "In Progress".
5.  **Reporting**: Every Friday at 5 PM, the worker generates a summary of all Notion logs for the week.

## Deployment
This project is designed to be deployed on platforms like **Koyeb** or **Heroku**. Use the `Dockerfile` and `Procfile` provided for easy setup.

## License
MIT
