import os
import re
from pathlib import Path
from src.core.config import config
from src.utils.logger import get_global_logger

# Client imports
from src.clients.jira import JiraClient
from src.clients.slack import SlackClient
from src.clients.notion import NotionClientWrapper

# LangChain imports
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

logger = get_global_logger()

class JiraAgent:
    def __init__(self):
        # LLM Initialization
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            groq_api_key=config.GROQ_API_KEY
        )
        
        # Skill loading - look for skills in the root directory relative to this file
        self.skills_path = Path(__file__).parent.parent.parent / "skills"
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
        logger.add(f"Generating content for: {user_prompt[:50]}...")
        
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
        logger.add("Routing content to target platform...")
        
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
                res = self.slack.send_message(channel, message_body)
                logger.add(res)
                return res
            return "❌ Could not identify Slack channel or message body."

        elif "Task Category" in content:
            # Notion Routing
            cat = next((line.split('**')[-1].strip() for line in content.split('\n') if "Task Category" in line), "Development")
            notion_result = self.notion.log_work(cat, content)
            logger.add(notion_result)
            
            # Dependency Checker (Notion -> Jira)
            jira_keys = re.findall(r'[A-Z][A-Z0-9]+-[0-9]+', content)
            dependency_results = []
            if jira_keys:
                for key in set(jira_keys):
                    res = self.jira.update_status_and_comment(key, "In Progress")
                    dependency_results.append(res)
                    logger.add(res)
            
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
            res = self.jira.create_issue(summary, content)
            logger.add(res)
            return res

