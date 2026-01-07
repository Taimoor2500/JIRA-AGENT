import logging
from src.services.velocity_service import VelocityService
from src.core.config import config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_velocity():
    print("\n🧪 --- Velocity Forecaster Test ---")
    
    if not config.JIRA_BOARD_ID:
        print("❌ Error: JIRA_BOARD_ID is not set in your .env file.")
        return

    service = VelocityService()
    
    print(f"📊 Analyzing Velocity for Board ID: {config.JIRA_BOARD_ID}...")
    
    # Switch channel to bot-test for safety
    service.target_channel = "bot-test"
    
    service.forecast_sprint()
    
    print("\n✅ Test complete. Check your Slack channel #bot-test.")

if __name__ == "__main__":
    test_velocity()

