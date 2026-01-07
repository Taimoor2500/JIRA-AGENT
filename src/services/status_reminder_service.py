import logging
from datetime import datetime, timedelta
from src.clients.jira import JiraClient
from src.clients.slack import SlackClient
from src.core.config import config

logger = logging.getLogger(__name__)

class StatusReminderService:
    def __init__(self):
        self.jira = JiraClient()
        self.slack = SlackClient()
        self.target_channel = "propone-backend-dev"

    def check_and_send_reminders(self):
        """Checks if today is 5 days after sprint start and sends reminders if so."""
        board_id = config.JIRA_BOARD_ID
        if not board_id:
            logger.warning("⚠️ JIRA_BOARD_ID not set. Skipping status reminders.")
            return

        active_sprint = self.jira.get_active_sprint(board_id)
        if not active_sprint:
            logger.info("ℹ️ No active sprint found. Skipping reminders.")
            return

        start_date_str = active_sprint.get("startDate")
        if not start_date_str:
            logger.warning(f"⚠️ Active sprint {active_sprint.get('name')} has no start date.")
            return

        # Jira date format usually '2023-10-23T09:00:00.000Z'
        try:
            # Clean up the timezone part for simple parsing
            clean_date = start_date_str.split('.')[0].replace('Z', '')
            start_date = datetime.fromisoformat(clean_date).date()
            today = datetime.now().date()
            
            days_since_start = (today - start_date).days
            
            logger.info(f"📅 Sprint '{active_sprint.get('name')}' started on {start_date}. Days since start: {days_since_start}")

            if days_since_start == 5:
                self._send_reminders(active_sprint.get("name"))
            else:
                logger.info(f"ℹ️ Not the 5th day of the sprint (Day {days_since_start}). No action taken.")

        except Exception as e:
            logger.error(f"❌ Error processing sprint dates: {e}")

    def _send_reminders(self, sprint_name):
        logger.info(f"🔍 Fetching stale tickets for sprint '{sprint_name}'...")
        
        # JQL: Tickets in active sprint NOT in BACKEND INPROGRESS, BACKEND TODO, or final states
        jql = (
            f"sprint in openSprints() "
            f"AND project = {config.JIRA_PROJECT_KEY} "
            f"AND status NOT IN ('BACKEND INPROGRESS', 'BACKEND TODO', 'DONE', 'BACKEND DONE', 'READY FOR LIVE', 'VERIFICATION') "
            f"AND assignee IS NOT EMPTY"
        )
        
        issues = self.jira.search_issues(jql)
        
        if not issues:
            logger.info("✅ No stale tickets found for reminder.")
            return

        # Group by assignee
        reminders = {}
        for issue in issues:
            assignee = issue['fields']['assignee']['displayName']
            key = issue['key']
            summary = issue['fields']['summary']
            if assignee not in reminders:
                reminders[assignee] = []
            reminders[assignee].append(f"• *{key}*: {summary}")

        # Construct Slack message
        message = f"👋 *Sprint Status Update Request ({sprint_name})*\n\nWe are 5 days into the sprint! The following tickets are not yet in 'BACKEND INPROGRESS' or 'BACKEND TODO'. Could you please provide a quick update?\n\n"
        
        for person, tasks in reminders.items():
            message += f"👤 *{person}*\n" + "\n".join(tasks) + "\n\n"

        res = self.slack.send_message(self.target_channel, message)
        logger.info(f"✅ {res}")

