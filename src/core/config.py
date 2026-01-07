import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # AI
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # Jira
    JIRA_URL = os.getenv("JIRA_URL")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
    JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")
    
    # Slack
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
    MY_SLACK_ID = os.getenv("MY_SLACK_ID")
    
    # Notion
    NOTION_TOKEN = os.getenv("NOTION_TOKEN")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
    
    # Others
    NTFY_TOPIC = os.getenv("NTFY_TOPIC")
    PORT = int(os.getenv("PORT", 8080))

config = Config()

