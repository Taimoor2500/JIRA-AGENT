import os
import requests
from requests.auth import HTTPBasicAuth
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
                self.client.myself()
            except Exception as e:
                print(f"❌ Jira Connection Error: {e}")

    def create_issue(self, summary, description, issue_type="Task"):
        if not self.client:
            return "❌ Jira client not initialized."
        
        if not self.project_key:
            return "❌ No Jira project key provided (JIRA_PROJECT_KEY)"

        try:
            fields = {
                'project': {'key': self.project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type},
            }
            new_issue = self.client.issue_create(fields=fields)
            return f"✅ Success! Ticket created: {self.url}/browse/{new_issue['key']}"
        except Exception as e:
            return f"❌ Failed to create Jira ticket: {str(e)}"

    def update_status_and_comment(self, issue_key, status_name="In Progress"):
        """Updates the status via direct API call to bypass library bugs."""
        if not self.url or not self.email or not self.token:
            return "❌ Jira credentials missing."

        auth = HTTPBasicAuth(self.email, self.token)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        try:
            # 1. Get Transitions
            url = f"{self.url.rstrip('/')}/rest/api/3/issue/{issue_key}/transitions"
            response = requests.get(url, auth=auth, headers=headers)
            
            if response.status_code != 200:
                return f"❌ Jira API Error: {response.status_code} - {response.text}"
            
            transitions = response.json().get("transitions", [])
            target_names = [status_name.lower(), "backend inprogress", "backend in progress", "in progress"]
            
            transition_id = None
            found_name = ""
            for t in transitions:
                name = str(t.get("name", "")).lower()
                if name in target_names:
                    transition_id = t.get("id")
                    found_name = t.get("name")
                    break
            
            if not transition_id:
                avail = [t.get("name") for t in transitions]
                return f"⚠️ Jira {issue_key}: No 'In Progress' button found. Available: {', '.join(avail)}"

            # 2. Perform Transition
            payload = {"transition": {"id": transition_id}}
            post_res = requests.post(url, json=payload, auth=auth, headers=headers)
            
            if post_res.status_code == 204:
                return f"✅ Jira {issue_key}: Status updated via '{found_name}'"
            else:
                return f"❌ Jira Transition Failed: {post_res.status_code} - {post_res.text}"

        except Exception as e:
            return f"❌ System Error updating Jira: {str(e)}"

    def search_issues(self, jql):
        """Search for issues using JQL."""
        if not self.client:
            return []
        try:
            results = self.client.jql(jql)
            return results.get("issues", [])
        except Exception as e:
            print(f"❌ Jira Search Error: {e}")
            return []

    def get_active_sprint(self, board_id):
        """Fetches the active sprint for a given board ID."""
        if not self.client or not board_id:
            return None
        try:
            sprints = self.client.get_all_sprints_from_board(board_id)
            for sprint in sprints:
                if sprint.get("state") == "active":
                    return sprint
            return None
        except Exception as e:
            print(f"❌ Jira Sprint Fetch Error: {e}")
            return None

