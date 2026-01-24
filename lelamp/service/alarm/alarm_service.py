
import threading
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AlarmService:
    def __init__(self, on_trigger=None):
        self.alarms = [] # List of {"time": "HH:MM", "label": "Label", "triggered": False}
        self.on_trigger = on_trigger
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the alarm checker loop"""
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._check_loop, daemon=True)
        self.thread.start()
        logger.info("Alarm Service started")
        
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            
    def add_alarm(self, time_str: str, label: str = "Alarm"):
        """
        Set an alarm.
        time_str: "HH:MM" (24-hour format) or "HH:MM AM/PM"
        """
        # Normalize time provided by LLM
        try:
            # Try parsing with datetime to ensure valid format
            # Support multiple formats
            parsed_time = None
            for fmt in ["%H:%M", "%I:%M %p", "%I:%M%p"]:
                try:
                    parsed_time = datetime.strptime(time_str, fmt)
                    break 
                except ValueError:
                    continue
            
            if not parsed_time:
                logger.error(f"Invalid time format: {time_str}")
                return False
                
            # Store as normalized HH:MM 24-hr string
            normalized_time = parsed_time.strftime("%H:%M")
            
            self.alarms.append({
                "time": normalized_time,
                "label": label,
                "triggered": False,
                "created_at": datetime.now()
            })
            logger.info(f"Alarm set for {normalized_time} ({label})")
            return True
            
        except Exception as e:
            logger.error(f"Error setting alarm: {e}")
            return False

    def _check_loop(self):
        """Check alarms every second"""
        while self.running:
            now_str = datetime.now().strftime("%H:%M")
            
            for alarm in self.alarms:
                if not alarm["triggered"] and alarm["time"] == now_str:
                    # Fire alarm!
                    logger.info(f"ALARM TRIGGERED: {alarm['label']}")
                    alarm["triggered"] = True # Mark as fired
                    
                    if self.on_trigger:
                        self.on_trigger(alarm["label"])
                        
            # Clean up triggered alarms that are old (next day)? 
            # For now, keep them until restart or manual clear
            
            time.sleep(1) # Check every second
