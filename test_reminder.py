import logging
import sys
from src.services.status_reminder_service import StatusReminderService
from src.core.config import config

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_reminder():
    print("\n🧪 --- Jira Status Reminder Test ---")
    
    if not config.JIRA_BOARD_ID:
        print("❌ Error: JIRA_BOARD_ID is not set in your .env file.")
        return

    reminder_service = StatusReminderService()
    
    print(f"\n1. Checking Sprint Status (Board ID: {config.JIRA_BOARD_ID})...")
    # This will simulate the logic that runs daily in the worker
    reminder_service.check_and_send_reminders()
    
    print("\n2. Forcing a Test Notification (Bypassing Day 5 check)...")
    # This will directly trigger the JQL search and post to Slack
    reminder_service._send_reminders("TEST_SPRINT_WORKFLOW", "Jan 25, 2026")
    
    print("\n✅ Test complete. Check your Slack channel #bot-test.")

if __name__ == "__main__":
    test_reminder()
