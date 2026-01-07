import logging
from datetime import datetime
from src.clients.jira import JiraClient
from src.clients.slack import SlackClient
from src.core.config import config

logger = logging.getLogger(__name__)

class VelocityService:
    def __init__(self):
        self.jira = JiraClient()
        self.slack = SlackClient()
        self.target_channel = "propone-backend-dev"
        # Story point fields identified
        self.point_fields = ["customfield_10004", "customfield_11441"]

    def _get_points(self, issue):
        """Extract story points from an issue."""
        fields = issue.get("fields", {})
        for field in self.point_fields:
            val = fields.get(field)
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    continue
        return 0.0

    def forecast_sprint(self):
        """Analyzes the current sprint velocity and forecasts completion."""
        board_id = config.JIRA_BOARD_ID
        if not board_id:
            logger.warning("⚠️ JIRA_BOARD_ID not set. Skipping velocity forecast.")
            return

        active_sprint = self.jira.get_active_sprint(board_id)
        if not active_sprint:
            logger.info("ℹ️ No active sprint found for velocity forecasting.")
            return

        sprint_name = active_sprint.get("name")
        sprint_id = active_sprint.get("id")
        
        # Fetch all issues in the sprint
        jql = f"sprint = {sprint_id} AND project = {config.JIRA_PROJECT_KEY}"
        all_issues = self.jira.search_issues(jql)
        
        if not all_issues:
            logger.info(f"📭 No issues found in sprint {sprint_name}.")
            return

        # Backend-only logic: Exclude Product and Deprecated
        backend_issues = []
        for issue in all_issues:
            status = issue['fields']['status']['name'].upper()
            if "PRODUCT" not in status and "DEPRECATED" not in status:
                backend_issues.append(issue)

        if not backend_issues:
            logger.info(f"📭 No backend issues identified in {sprint_name}.")
            return

        # Define Done States based on Workflow Image
        # Now including 'BE PR REVIEW' and 'VERIFICATION' as completed work
        done_states = ['DONE', 'BACKEND DONE', 'VERIFICATION', 'QA APPROVED', 'READY FOR LIVE', 'BE PR REVIEW']
        
        remaining_tasks = []
        total_points = 0.0
        completed_points = 0.0
        
        for issue in backend_issues:
            points = self._get_points(issue)
            total_points += points
            status = issue['fields']['status']['name'].upper()
            if status in done_states:
                completed_points += points
            else:
                remaining_tasks.append(f"• *{issue['key']}*: {issue['fields'].get('summary', 'No summary')}")
        
        using_ticket_count = False
        if total_points == 0:
            using_ticket_count = True
            total_points = float(len(backend_issues))
            completed_points = float(sum(1 for i in backend_issues if i['fields']['status']['name'].upper() in done_states))

        # Date calculations
        try:
            start_date_str = active_sprint.get("startDate").split('.')[0].replace('Z', '')
            end_date_str = active_sprint.get("endDate").split('.')[0].replace('Z', '')
            
            start_date = datetime.fromisoformat(start_date_str).date()
            end_date = datetime.fromisoformat(end_date_str).date()
            today = datetime.now().date()
            
            total_duration = max((end_date - start_date).days, 1)
            elapsed_days = max((today - start_date).days, 1)
            remaining_days = (end_date - today).days
            
            is_overdue = remaining_days < 0
            
            current_velocity = completed_points / elapsed_days
            remaining_points = total_points - completed_points
            
            # For required velocity, if overdue, we need to finish "now" (1 day)
            required_velocity = remaining_points / (1 if is_overdue or remaining_days <= 0 else remaining_days)
            
            progress_pct = (completed_points / total_points * 100) if total_points > 0 else 0
            
            status_emoji = "🟢"
            if is_overdue and remaining_points > 0:
                status_emoji = "🔴"
            elif required_velocity > current_velocity * 1.2:
                status_emoji = "🔴"
            elif required_velocity > current_velocity:
                status_emoji = "🟡"

            metric_name = "Backend Tickets" if using_ticket_count else "Backend Points"
            
            # Construct Message
            message = (
                f"{status_emoji} *Backend Velocity Forecast: {sprint_name}*\n\n"
                f"📊 *Progress*: {completed_points:.0f} / {total_points:.0f} {metric_name} ({progress_pct:.0f}%)\n"
                f"⏳ *Time*: {elapsed_days} days elapsed / {max(0, remaining_days)} days left\n\n"
                f"🚀 *Current Velocity*: {current_velocity:.1f} {metric_name}/day\n"
                f"🎯 *Required Velocity*: {required_velocity:.1f} {metric_name}/day\n\n"
            )

            if remaining_tasks:
                message += "*Remaining Tasks*:\n" + "\n".join(remaining_tasks[:10]) + "\n"
                if len(remaining_tasks) > 10:
                    message += f"_...and {len(remaining_tasks) - 10} more tasks_\n"
                message += "\n"

            if is_overdue and remaining_points > 0:
                message += f"🚨 *Overdue Alert*: This sprint was scheduled to end on {end_date.strftime('%b %d')} but still has {remaining_points:.0f} tasks to finish!"
            elif status_emoji == "🔴":
                message += "⚠️ *Risk Alert*: The backend team is falling behind. Consider moving tasks to the next sprint."
            elif status_emoji == "🟡":
                message += "⚖️ *Pace Warning*: Team needs to accelerate to hit the deadline."
            else:
                message += "✅ *On Track*: Backend progress is looking solid!"

            # Only send the message if it's within 4 days of ending or overdue
            if remaining_days <= 4 or is_overdue:
                self.slack.send_message(self.target_channel, message)
                logger.info(f"✅ Backend Velocity forecast sent for {sprint_name} (Days left: {remaining_days})")
            else:
                logger.info(f"ℹ️ Forecast skipped: {remaining_days} days left (Reminders start at 4 days left).")

        except Exception as e:
            logger.error(f"❌ Velocity forecast failed: {e}")
