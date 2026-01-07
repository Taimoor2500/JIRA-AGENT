from datetime import datetime

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
        print(f"LOG: {msg}")

_global_logger = None

def get_global_logger():
    """Get the global logger singleton instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = GlobalLogger()
    return _global_logger

