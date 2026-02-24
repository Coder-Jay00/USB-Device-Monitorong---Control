import os
import csv
from datetime import datetime
import logger

def generate_report():
    """Parses the usb_audit.log and generates a final CSV summary."""
    log_file = logger.LOG_FILE
    report_file = os.path.join(logger.LOG_DIR, f"usb_security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    if not os.path.exists(log_file):
        logger.log_error("REPORTING", "Log file not found. Nothing to report.")
        return
        
    try:
        with open(log_file, 'r') as f_in, open(report_file, 'w', newline='') as f_out:
            writer = csv.writer(f_out)
            writer.writerow(["Timestamp", "Severity", "Event Type", "Event Details"])
            
            for line in f_in:
                # Format: 2026-02-24 22:04:12,345 - INFO - [EVENT_TYPE] Detail message
                parts = line.strip().split(" - ", 2)
                if len(parts) == 3:
                    timestamp = parts[0]
                    severity = parts[1]
                    message = parts[2]
                    
                    event_type = ""
                    details = message
                    
                    if message.startswith("["):
                        end_idx = message.find("]")
                        if end_idx != -1:
                            event_type = message[1:end_idx]
                            details = message[end_idx+2:]
                            
                    writer.writerow([timestamp, severity, event_type, details])
                    
        logger.log_event("REPORTING", f"Security report generated: {report_file}")
    except Exception as e:
        logger.log_error("REPORTING", f"Failed to generate report: {str(e)}")

if __name__ == "__main__":
    generate_report()
