# Jira Agent 

An AI-powered CLI assistant designed to generate high-quality, industry-standard Jira tickets and post them directly to your Jira board. Powered by **Groq (Llama 3.3)** and **LangChain**.

## Features

-   **AI Generation**: Instantly transforms brief prompts into detailed Jira tickets (Stories, Bugs, Tasks, Epics).
-   **Industry Standard Templates**: Uses structured formatting (INVEST criteria, clear ACs, reproduction steps).
-   **Real Jira Integration**: Post generated tickets directly to your project via the Atlassian API.
-   **Interactive Revision**: Review and refine tickets through a conversation with the agent before publishing.
-   **Custom Skills**: Easily extendable by adding new `.md` templates to the `skills/` directory.
-   **Clean Formatting**: Automatic post-processing to ensure perfect bolding and spacing in the Jira UI.

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
├── app.py                  # Backend services (Slack listener)
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
# AI Configuration
GROQ_API_KEY=your_groq_api_key

# Jira Configuration
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=YOURPROJ## Usage

### Run the Dashboard UI
```bash
streamlit run ui.py
```

### Run Backend Only (Slack Listener)
```bash
python app.py
```

### Example Workflow
1.  **Prompt**: `What Jira ticket would you like to create? > Create a bug for login failure on iOS`
2.  **Review**: The agent displays the formatted sample.
3.  **Refine**: Type `r` to add more details (e.g., *"Add a note about the login service logs"*).
4.  **Publish**: Type `y` to post the ticket directly to your Jira board.

## License
MIT
