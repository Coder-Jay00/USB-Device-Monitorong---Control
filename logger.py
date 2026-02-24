import logging
import os
from datetime import datetime

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "usb_audit.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_event(event_type, message):
    log_msg = f"[{event_type}] {message}"
    logging.info(log_msg)
    print(log_msg)

def log_warning(event_type, message):
    log_msg = f"[{event_type}] {message}"
    logging.warning(log_msg)
    print(f"WARNING: {log_msg}")

def log_error(event_type, message):
    log_msg = f"[{event_type}] {message}"
    logging.error(log_msg)
    print(f"ERROR: {log_msg}")
