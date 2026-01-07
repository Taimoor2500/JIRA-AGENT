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
            
            # Get end date as well
            end_date_str = active_sprint.get("endDate")
            formatted_end_date = "Unknown"
            if end_date_str:
                clean_end = end_date_str.split('.')[0].replace('Z', '')
                end_date = datetime.fromisoformat(clean_end).date()
                formatted_end_date = end_date.strftime("%b %d, %Y")

            today = datetime.now().date()
            
            days_since_start = (today - start_date).days
            
            logger.info(f"📅 Sprint '{active_sprint.get('name')}' started on {start_date}. Days since start: {days_since_start}")

            if days_since_start == 5:
                self._send_reminders(active_sprint.get("name"), formatted_end_date)
            else:
                logger.info(f"ℹ️ Not the 5th day of the sprint (Day {days_since_start}). No action taken.")

        except Exception as e:
            logger.error(f"❌ Error processing sprint dates: {e}")

    def _send_reminders(self, sprint_name, end_date):
        logger.info(f"🔍 Fetching active backend tickets for sprint '{sprint_name}'...")
        
        # JQL: Tickets in active sprint that ARE ONLY in BACKEND statuses and NOT frontend related
        jql = (
            f"sprint in openSprints() "
            f"AND project = {config.JIRA_PROJECT_KEY} "
            f"AND status IN ('BACKEND INPROGRESS', 'BACKEND TODO') "
            f"AND assignee IS NOT EMPTY "
            f"AND summary !~ 'FE' AND summary !~ 'Frontend'"
        )
        
        issues = self.jira.search_issues(jql)
        
        if not issues:
            logger.info("✅ No stale tickets found for reminder.")
            return

        # Group by assignee
        reminders = {}
        for issue in issues:
            summary = issue['fields'].get('summary', '')
            
            # Extra safety check: skip if FE or Frontend is in the summary
            if any(term in summary.upper() for term in ["FE ", " FE", "(FE)", "FRONTEND"]):
                continue

            assignee_name = issue['fields']['assignee']['displayName']
            
            # Skip Taimoor
            if "Taimoor" in assignee_name:
                continue
                
            key = issue['key']
            if assignee_name not in reminders:
                reminders[assignee_name] = []
            reminders[assignee_name].append(f"• *{key}*: {summary}")

        if not reminders:
            logger.info("✅ No relevant tickets found after filtering (e.g., all tickets belong to Taimoor).")
            return

        # Construct Slack message
        message = f"👋 *Active Sprint Status Update ({sprint_name})*\n\n🗓️ *Ends on*: {end_date}\n\nWe are 5 days into the sprint! Could you please provide a quick update on your active tasks in 'BACKEND TODO' and 'BACKEND INPROGRESS'?\n\n"
        
        for person_name, tasks in reminders.items():
            message += f"👤 *{person_name}*\n" + "\n".join(tasks) + "\n\n"

        res = self.slack.send_message(self.target_channel, message)
        logger.info(f"✅ {res}")

