import json
import os
import re
import subprocess

import logger
import file_auditor

ALLOWLIST_PATH = os.path.join("config", "allowlist.json")

def load_allowlist():
    if not os.path.exists(ALLOWLIST_PATH):
        logger.log_warning("SYSTEM", f"Allowlist not found at {ALLOWLIST_PATH}. Creating empty config.")
        os.makedirs(os.path.dirname(ALLOWLIST_PATH), exist_ok=True)
        with open(ALLOWLIST_PATH, 'w') as f:
            json.dump({"approved_devices": []}, f, indent=4)
        return []
    
    try:
        with open(ALLOWLIST_PATH, 'r') as f:
            data = json.load(f)
            return data.get("approved_devices", [])
    except Exception as e:
        logger.log_error("SYSTEM", f"Failed to parse allowlist: {str(e)}")
        return []

def extract_vid_pid(device_id):
    """
    Extracts Vendor ID and Product ID from a Windows PnP DeviceID string.
    Example: USB\VID_1234&PID_5678\9&324...
    """
    vid_match = re.search(r"VID_([0-9A-Fa-f]{4})", device_id)
    pid_match = re.search(r"PID_([0-9A-Fa-f]{4})", device_id)
    
    vid = f"0x{vid_match.group(1).upper()}" if vid_match else None
    pid = f"0x{pid_match.group(1).upper()}" if pid_match else None
    
    return vid, pid

def block_device(instance_id):
    """
    Blocks a USB device using PowerShell Disable-PnpDevice.
    Requires Administrative privileges.
    """
    logger.log_event("POLICY", f"Attempting to block device: {instance_id}")
    try:
        # PowerShell command to disable the device. 
        # -Confirm:$false bypasses the confirmation prompt.
        cmd = ["powershell", "-Command", f"Disable-PnpDevice -InstanceId '{instance_id}' -Confirm:$false"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.log_event("ENFORCEMENT", f"Successfully blocked unauthorized device: {instance_id}")
        else:
            logger.log_error("ENFORCEMENT", f"Failed to block device: {result.stderr.strip()}")
            
    except Exception as e:
        logger.log_error("ENFORCEMENT", f"Error executing block command: {str(e)}")

def check_device(wmi_instance):
    """
    Checks the newly connected device against the allowlist.
    """
    device_id = wmi_instance.DeviceID
    name = wmi_instance.Name
    
    # We mainly care about actual USB storage devices or specific interfaces.
    # WMI DeviceID for USB usually contains VID and PID.
    vid, pid = extract_vid_pid(device_id)
    
    if not vid or not pid:
        # Some USB composite devices might not have straightforward VID/PID in this specific event,
        # but typical USB storage devices do.
        logger.log_warning("POLICY", f"Could not extract VID/PID from device: {device_id}")
        return

    logger.log_event("POLICY", f"Analyzing device {name} - VID: {vid}, PID: {pid}")

    allowlist = load_allowlist()
    
    is_authorized = False
    for approved in allowlist:
        # We perform a case-insensitive comparison
        if approved.get("vendor_id", "").lower() == vid.lower() and \
           approved.get("product_id", "").lower() == pid.lower():
            is_authorized = True
            # Note: Serial number checking can be added here if available in the DeviceID string
            break
            
    if is_authorized:
        logger.log_event("POLICY", f"AUTHORIZED: Device {vid}:{pid} is approved.")
        # If authorized, we might want to start file auditing if it's a storage device.
        # This will be handled by a separate WMI query to find the assigned drive letter.
        file_auditor.start_auditing_if_storage(device_id)
    else:
        logger.log_warning("POLICY", f"UNAUTHORIZED: Device {vid}:{pid} is NOT approved. Blocking...")
        block_device(device_id)
