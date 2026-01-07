"""
Backend services for Jira Agent - Slack listener and shared state management.
Run the UI with: streamlit run ui.py
"""

import os
import threading
from datetime import datetime

# --- Shared State & Logger ---
class GlobalLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.logs = [f"[{datetime.now().strftime('%H:%M:%S')}] 🖥️ UI initialized"]
        return cls._instance
    
    def add(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{ts}] {msg}")
        if len(self.logs) > 20:
            self.logs.pop(0)
        print(f"UI LOG: {msg}")

# Singleton accessor for the logger
_global_logger = None

def get_global_logger():
    """Get the global logger singleton instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = GlobalLogger()
    return _global_logger

# --- External Service Status ---
def get_external_status():
    """Returns status of external services."""
    return "🟢 Running on Koyeb"


# Allow running this file directly for testing
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    logger = get_global_logger()
    print("Shared state initialized. Run ui.py for the interface.")
