import os
from notion_client import Client as NotionClient

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
            self.client.pages.create(
                parent={"database_id": self.database_id},
                properties={
                    "Name": {"title": [{"text": {"content": f"Work Log: {category}"}}]},
                    "Category": {"select": {"name": category}},
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

