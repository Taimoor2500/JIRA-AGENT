import os
from atlassian import Jira

class JiraClient:
    def __init__(self):
        self.url = os.getenv("JIRA_URL")
        self.email = os.getenv("JIRA_EMAIL")
        self.token = os.getenv("JIRA_API_TOKEN")
        self.project_key = os.getenv("JIRA_PROJECT_KEY")
        self.client = None

        if self.url and self.email and self.token:
            try:
                self.client = Jira(
                    url=self.url,
                    username=self.email,
                    password=self.token,
                    cloud=True
                )
                # Verify connection
                user = self.client.myself()
                print(f"✅ Connected to Jira as: {user.get('displayName')}")
            except Exception as e:
                print(f"❌ Jira Connection Error: {e}")

    def create_issue(self, summary, description, issue_type="Task"):
        if not self.client:
            return "❌ Jira client not initialized."
        
        if not self.project_key:
            return "❌ No Jira project key provided (JIRA_PROJECT_KEY)"

        try:
            try:
                self.client.project(self.project_key)
            except:
                return f"❌ Project '{self.project_key}' not found or no access."

            fields = {
                'project': {'key': self.project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type},
            }
            new_issue = self.client.issue_create(fields=fields)
            return f"✅ Success! Ticket created: {self.url}/browse/{new_issue['key']}"
        except Exception as e:
            error_msg = str(e)
            if "reporter is required" in error_msg.lower():
                return "❌ Jira Error: Reporter field is required."
            return f"❌ Failed to create Jira ticket: {error_msg}"

