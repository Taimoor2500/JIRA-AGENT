import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Client imports
from clients.jira_client import JiraClient
from clients.slack_client import SlackClient
from clients.notion_client import NotionClientWrapper

# LangChain imports
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

# Load environment variables
load_dotenv()

class JiraAgent:
    def __init__(self):
        # LLM Initialization
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        
        # Skill loading
        self.skills_path = Path(__file__).parent / "skills"
        self.skills = self._load_skills()
        
        # Compose Clients
        self.jira = JiraClient()
        self.slack = SlackClient()
        self.notion = NotionClientWrapper()

    def _load_skills(self):
        """Loads all SKILL.md files from the skills directory."""
        skills_content = ""
        if not self.skills_path.exists():
            return skills_content

        for skill_dir in self.skills_path.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    with open(skill_file, "r") as f:
                        skills_content += f"\n\n--- Skill: {skill_dir.name} ---\n"
                        skills_content += f.read()
        return skills_content

    def generate_ticket(self, user_prompt: str, previous_version: str = None, revision_notes: str = None):
        """Generates or revises a content block using the LLM."""
        system_template = (
            "You are an expert Project Manager and Multi-Tool Agent.\n\n"
            "{skills_context}\n\n"
            "CRITICAL: Identify the target platform (Jira, Slack, or Notion) and format accordingly.\n"
            "FORMATTING RULES:\n"
            "1. Headers: Use bold text (e.g., **Description**). No colons.\n"
            "2. Lists: Use '1.' or '-'.\n"
            "3. Spacing: Exactly one blank line between sections.\n"
            "4. Column 0: All lines must start at the beginning.\n"
            "5. NO preamble or backticks."
        )
        
        system_msg = SystemMessagePromptTemplate.from_template(system_template).format(skills_context=self.skills)
        
        if previous_version and revision_notes:
            messages = [
                system_msg,
                HumanMessage(content=user_prompt),
                AIMessage(content=previous_version),
                HumanMessage(content=f"Please revise based on these notes: {revision_notes}")
            ]
        else:
            messages = [
                system_msg,
                HumanMessage(content=user_prompt)
            ]
        
        response = self.llm.invoke(messages)
        return self._post_process(response.content)

    def _post_process(self, content):
        """Cleans up the LLM output for consistent formatting."""
        content = content.strip()
        # Collapse whitespace
        content = re.sub(r'\n\s*\n+', '\n\n', content)
        # Normalize headers
        content = re.sub(r'(?m)^\s*\**\s*([^*:\n]+?)\s*\**:?\s*$', r'**\1**', content)
        # Force column 0
        lines = [line.lstrip() for line in content.split('\n')]
        return '\n'.join(lines).strip()

    def post_content(self, content):
        """Routes the content to the correct platform and triggers dependencies."""
        if any(x in content for x in ["Channel", "Recipient"]):
            # Slack Routing
            channel = None
            message_body = ""
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if any(k in line for k in ["Channel", "Recipient"]):
                    parts = line.replace('**', ':').split(':')
                    if len(parts) > 1:
                        channel = parts[-1].strip().lstrip('#').strip()
                if "Message" in line:
                    message_body = '\n'.join(lines[i+1:]).strip()
                    break
            
            if channel and message_body:
                return self.slack.send_message(channel, message_body)
            return "❌ Could not identify Slack channel or message body."

        elif "Task Category" in content:
            # Notion Routing
            cat = next((line.split('**')[-1].strip() for line in content.split('\n') if "Task Category" in line), "Development")
            notion_result = self.notion.log_work(cat, content)
            
            # Dependency Checker (Notion -> Jira)
            jira_keys = re.findall(r'[A-Z][A-Z0-9]+-[0-9]+', content)
            dependency_results = []
            if jira_keys:
                for key in set(jira_keys):
                    res = self.jira.update_status_and_comment(key, "In Progress", comment=None)
                    dependency_results.append(res)
            
            final_result = notion_result
            if dependency_results:
                final_result += "\n\n" + "\n".join(dependency_results)
            return final_result

        else:
            # Jira Routing
            summary = ""
            lines = [l.strip() for l in content.split('\n')]
            for i, line in enumerate(lines):
                if "Summary" in line:
                    summary = line.split(':', 1)[-1].strip() if ':' in line else (lines[i+1] if i+1 < len(lines) else "")
                    break
            summary = summary.replace('**', '').replace('#', '').strip() or "New Ticket"
            return self.jira.create_issue(summary, content)

def main():
    print("🚀 Jira Agent (Refactored) is starting...")
    
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY not found.")
        return

    agent = JiraAgent()
    print("\nAgent initialized with skills. Type 'exit' to quit.")
    
    while True:
        user_input = input("\nWhat would you like to do? > ")
        if user_input.lower() in ['exit', 'quit', 'q']:
            break
            
        print("\nProcessing...\n" + "-"*30)
        try:
            current_version = agent.generate_ticket(user_input)
            
            while True:
                print(current_version)
                print("-" * 30)

                choice = input("\nPost (y), Revise (r), or Cancel (n) > ").lower()
                
                if choice == 'y':
                    print(agent.post_content(current_version))
                    break

                elif choice == 'r':
                    notes = input("What would you like to change? > ")
                    print("\nRevising...\n" + "-"*30)
                    current_version = agent.generate_ticket(user_input, current_version, notes)
                else:
                    print("Skipped.")
                    break

        except Exception as e:
            print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    main()
