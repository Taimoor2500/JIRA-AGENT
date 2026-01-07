import os
from notion_client import Client as NotionClient
from datetime import datetime, timedelta

class NotionClientWrapper:
    def __init__(self):
        self.token = os.getenv("NOTION_TOKEN")
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        self.client = None

        if self.token and self.database_id:
            try:
                self.client = NotionClient(auth=self.token)
                print("✅ Notion connection initialized")
            except Exception as e:
                print(f"❌ Notion Initialization Error: {e}")

    def log_work(self, category, description):
        if not self.client:
            return "❌ Notion credentials not configured."
        
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            
            self.client.pages.create(
                parent={"database_id": self.database_id},
                properties={
                    "Name": {"title": [{"text": {"content": f"Work Log: {category}"}}]},
                    "Category": {"select": {"name": category}},
                    "Date": {"date": {"start": date_str}}
                },
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": description}}]}
                    }
                ]
            )
            return f"✅ Work logged in Notion under {category}"
        except Exception as e:
            return f"❌ Failed to log to Notion: {str(e)}"

    def get_logs_for_last_7_days(self):
        """Fetches logs from the last 7 days from Notion."""
        if not self.client:
            return []
        
        try:
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            
            query = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "Date",
                    "date": {
                        "on_or_after": seven_days_ago
                    }
                }
            )
            
            logs = []
            for page in query.get("results", []):
                properties = page.get("properties", {})
                
                # Extract category
                category = properties.get("Category", {}).get("select", {}).get("name", "Unknown")
                
                # Extract date
                date = properties.get("Date", {}).get("date", {}).get("start", "Unknown")
                
                # Extract content
                name = properties.get("Name", {}).get("title", [{}])[0].get("plain_text", "")
                
                logs.append(f"- [{date}] ({category}) {name}")
                
            return logs
        except Exception as e:
            print(f"Error fetching logs: {e}")
            return []


