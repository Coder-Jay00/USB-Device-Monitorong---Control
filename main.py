import time
import sys

import logger
from usb_monitor import USBMonitor
from report_generator import generate_report

def main():
    logger.log_event("SYSTEM", "Starting USB Device Control & Monitoring Framework")
    
    # Initialize the USB Monitor
    monitor = USBMonitor()
    monitor.start()
    
    try:
        print("Framework is running. Press Ctrl+C to stop.")
        while True:
            # Main thread keeps alive while the daemon thread monitors
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping the framework...")
        logger.log_event("SYSTEM", "Stopping framework per user request")
        monitor.stop()
        
        # Generate final report on exit
        print("Generating audit report...")
        generate_report()
        sys.exit(0)

if __name__ == "__main__":
    main()
