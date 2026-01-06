import os
from pathlib import Path
from dotenv import load_dotenv
from atlassian import Jira
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

class JiraAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        self.skills_path = Path(__file__).parent / "skills"
        self.skills = self._load_skills()
        
        self.jira = None
        email = os.getenv("JIRA_EMAIL")
        url = os.getenv("JIRA_URL")
        token = os.getenv("JIRA_API_TOKEN")
        
        if url and email and token:
            try:
                masked_email = f"{email[:3]}...{email.split('@')[-1]}"
                print(f"🔄 Attempting Jira connection to {url} with user {masked_email}...")
                
                self.jira = Jira(
                    url=url,
                    username=email,
                    password=token,
                    cloud=True
                )
                user = self.jira.myself()
                print(f"✅ Connected to Jira as: {user.get('displayName')}")
            except Exception as e:
                print(f"❌ Jira Connection Error: {e}")
                self.jira = None

    def create_jira_issue(self, summary, description, project_key=None, issue_type="Task"):
        """Creates an issue in Jira."""
        if not self.jira:
            return "❌ Jira credentials not configured in .env"
        
        project = project_key or os.getenv("JIRA_PROJECT_KEY")
        if not project:
            return "❌ No Jira project key provided (JIRA_PROJECT_KEY)"

        try:
            try:
                self.jira.project(project)
            except:
                return f"❌ Project '{project}' not found or no access. Check JIRA_PROJECT_KEY."

            fields = {
                'project': {'key': project},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type},
            }
            new_issue = self.jira.issue_create(fields=fields)
            return f"✅ Success! Ticket created: {os.getenv('JIRA_URL')}/browse/{new_issue['key']}"
        except Exception as e:
            # Try to extract a more helpful error message from Jira response
            error_msg = str(e)
            if "reporter is required" in error_msg.lower():
                return "❌ Jira Error: Reporter field is required. Your API account may not have permission to set itself as reporter."
            return f"❌ Failed to create Jira ticket: {error_msg}"

    def _load_skills(self):
        """Loads all SKILL.md files from the skills directory."""
        skills_content = ""
        if not self.skills_path.exists():
            print(f"Warning: Skills directory not found at {self.skills_path}")
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
        """Generates or revises a Jira ticket using conversation history for better context."""
        system_template = (
            "You are an expert Project Manager. Create a professional Jira ticket.\n\n"
            "{skills_context}\n\n"
            "FORMATTING RULES (To match Jira UI perfectly):\n"
            "1. Headers: Use bold text for headers, e.g., **Description**, **Acceptance Criteria**, **Environment**.\n"
            "2. NO Colons in Headers: Do NOT put a colon (:) after the header name.\n"
            "3. Lists: Use '1.' for numbered lists and '-' for bullet points.\n"
            "4. Spacing: Use exactly one blank line between headers and paragraphs.\n"
            "5. NO excessive blank lines. NO triple backticks. NO preamble."
        )
        
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
        
        if previous_version and revision_notes:
            messages = [
                system_message_prompt.format(skills_context=self.skills),
                HumanMessage(content=user_prompt),
                AIMessage(content=previous_version),
                HumanMessage(content=f"Please revise the above ticket based on these specific notes: {revision_notes}")
            ]
            response = self.llm.invoke(messages)
        else:
            human_template = "{user_input}"
            chat_prompt = ChatPromptTemplate.from_messages([
                system_message_prompt,
                HumanMessagePromptTemplate.from_template(human_template)
            ])
            chain = chat_prompt | self.llm
            response = chain.invoke({
                "skills_context": self.skills,
                "user_input": user_prompt
            })
        
        import re
        content = response.content.strip()
        
        content = re.sub(r'\n\s*\n+', '\n\n', content)
        
        content = re.sub(r'(?m)^\s*\**\s*([^*:\n]+?)\s*\**:?\s*$', r'**\1**', content)
        
        lines = [line.lstrip() for line in content.split('\n')]
        content = '\n'.join(lines)
        
        return content.strip()

def main():
    print("🚀 Jira Agent (Groq + Jira Edition) is starting...")
    
    # Check for Groq API Key
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY not found in environment variables.")
        print("Please create a .env file and add: GROQ_API_KEY=your_key_here")
        return

    agent = JiraAgent()
    
    jira_ready = agent.jira is not None
    if not jira_ready:
        print("ℹ️  Jira integration not configured. Will only generate text.")
        print("   To enable, add JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN to .env")

    print("\nAgent initialized with skills. Type 'exit' to quit.")
    while True:
        user_input = input("\nWhat Jira ticket would you like to create? > ")
        if user_input.lower() in ['exit', 'quit', 'q']:
            break
            
        print("\nCreating ticket template...\n" + "-"*30)
        try:
            current_version = agent.generate_ticket(user_input)
            
            while True:
                print(current_version)
                print("-" * 30)

                if not jira_ready:
                    break

                choice = input("\nPost to Jira (y), Revise (r), or Cancel (n) > ").lower()
                
                if choice == 'y':
                    # Extract summary
                    summary = ""
                    lines = [line.strip() for line in current_version.split('\n')]
                    for i, line in enumerate(lines):
                        if "Summary" in line:
                            if ':' in line:
                                summary = line.split(':', 1)[-1].strip()
                            if not summary and i + 1 < len(lines):
                                summary = lines[i+1].strip()
                            summary = summary.replace('#', '').strip()
                            if summary: break
                    
                    if not summary:
                        summary = "New Ticket from AI Agent"
                    
                    status = agent.create_jira_issue(summary, current_version)
                    print(status)
                    break
                
                elif choice == 'r':
                    revision_notes = input("What would you like to change? > ")
                    print("\nRevising ticket...\n" + "-"*30)
                    current_version = agent.generate_ticket(user_input, current_version, revision_notes)
                else:
                    print("Skipped.")
                    break

        except Exception as e:
            print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    main()
