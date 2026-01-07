import logging
import requests
from datetime import datetime, timedelta
from notion_client import Client as NotionClient
from src.core.config import config

logger = logging.getLogger(__name__)

class ReportService:
    def __init__(self):
        self.notion = NotionClient(auth=config.NOTION_TOKEN)
        self.db_id = config.NOTION_DATABASE_ID
        self.groq_key = config.GROQ_API_KEY
        self.ntfy_topic = config.NTFY_TOPIC

    def _send_push_notification(self, message, title="Agent Worker"):
        if not self.ntfy_topic:
            return
        try:
            requests.post(f"https://ntfy.sh/{self.ntfy_topic}",
                data=message.encode('utf-8'),
                headers={"Title": title, "Priority": "high", "Tags": "robot,chart_with_upwards_trend"}
            )
        except Exception as e:
            logger.error(f"❌ Push error: {e}")

    def generate_weekly_report(self):
        """Fetches last 7 days of logs and saves a summary to Notion."""
        logger.info("📊 Starting Weekly Report generation...")
        
        if not self.db_id or not self.groq_key:
            logger.error("❌ Missing credentials for reporting.")
            return

        try:
            # 1. Fetch logs from Notion
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            query = self.notion.databases.query(
                database_id=self.db_id,
                filter={"property": "Date", "date": {"on_or_after": seven_days_ago}}
            )
            
            logs = []
            for page in query.get("results", []):
                props = page.get("properties", {})
                title = props.get("Name", {}).get("title", [{}])[0].get("plain_text", "")
                cat = props.get("Category", {}).get("select", {}).get("name", "Other")
                date = props.get("Date", {}).get("date", {}).get("start", "")
                if title:
                    logs.append(f"- [{date}] ({cat}) {title}")

            if not logs:
                logger.info("📭 No logs found for the last 7 days. Skipping report.")
                return

            # 2. Use Groq AI to summarize
            logger.info(f"🧠 Summarizing {len(logs)} logs using AI...")
            prompt = f"Analyze these work logs from the last 7 days and write a professional, high-level summary of the week's progress and focus areas:\n\n" + "\n".join(logs)
            
            groq_res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "You are a senior project manager writing a weekly executive summary."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            summary = groq_res.json()['choices'][0]['message']['content']

            # 3. Save Report back to Notion
            self.notion.pages.create(
                parent={"database_id": self.db_id},
                properties={
                    "Name": {"title": [{"text": {"content": f"📅 Weekly Report: {datetime.now().strftime('%b %d, %Y')}"}}]},
                    "Category": {"select": {"name": "Reporting"}},
                    "Date": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}}
                },
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": summary}}]}
                    }
                ]
            )
            
            logger.info("✅ Weekly Report saved to Notion!")
            self._send_push_notification("Your Weekly Work Report has been generated and saved to Notion.", "Report Ready")

        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")


