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

    def update_status_and_comment(self, issue_key, status_name="In Progress"):
        """Updates the status of a Jira issue. No comments added."""
        if not self.client:
            return "❌ Jira client not initialized."
        
        try:
            # 2. Transition Status
            # We wrap the API call in its own try/except to see if the error is inside the library
            try:
                transitions = self.client.get_issue_transitions(issue_key)
            except Exception as api_err:
                return f"❌ Jira API Error (get_transitions): {str(api_err)}"

            if not isinstance(transitions, list):
                return f"⚠️ Jira {issue_key}: Unexpected response type {type(transitions)}"

            transition_id = None
            target_names = [
                str(status_name).lower(), 
                "start progress", 
                "start work", 
                "do work", 
                "in progress",
                "backend started"
            ]
            
            found_actual_name = "Unknown"
            for t in transitions:
                if not isinstance(t, dict): continue
                
                raw_name = t.get('name')
                if raw_name is None: continue
                
                # Extremely safe string conversion
                name_str = str(raw_name).lower()
                if name_str in target_names:
                    transition_id = t.get('id')
                    found_actual_name = str(raw_name)
                    break
            
            if transition_id:
                self.client.issue_transition(issue_key, transition_id)
                return f"✅ Jira {issue_key}: Status updated via '{found_actual_name}'"
            else:
                avail = [str(t.get('name', 'Unknown')) for t in transitions if isinstance(t, dict)]
                return f"⚠️ Jira {issue_key}: No 'In Progress' transition. Available: {', '.join(avail)}"
                
        except Exception as e:
            return f"❌ Failed to update Jira {issue_key}: {str(e)}"

