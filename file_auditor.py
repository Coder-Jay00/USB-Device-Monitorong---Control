import os
import time
import wmi
import pythoncom
import threading
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import logger

class USBFileHandler(FileSystemEventHandler):
    def __init__(self, drive_letter):
        self.drive_letter = drive_letter
        super().__init__()

    def _hash_file(self, filepath):
        """Calculate SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                # Read and update hash string value in blocks of 4K
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            return f"Hash Error: {str(e)}"

    def on_created(self, event):
        if not event.is_directory:
            file_hash = self._hash_file(event.src_path)
            logger.log_event("FILE_AUDIT", f"File Created on {self.drive_letter}: {event.src_path} (SHA-256: {file_hash})")

    def on_modified(self, event):
        if not event.is_directory:
            file_hash = self._hash_file(event.src_path)
            logger.log_event("FILE_AUDIT", f"File Modified on {self.drive_letter}: {event.src_path} (SHA-256: {file_hash})")

    def on_deleted(self, event):
        if not event.is_directory:
            logger.log_event("FILE_AUDIT", f"File Deleted from {self.drive_letter}: {event.src_path}")

    def on_moved(self, event):
        if not event.is_directory:
            file_hash = self._hash_file(event.dest_path)
            logger.log_event("FILE_AUDIT", f"File Moved/Renamed on {self.drive_letter}: {event.src_path} -> {event.dest_path} (SHA-256: {file_hash})")

active_observers = {}

def start_auditing_drive(drive_letter):
    """Starts a watchdog observer on a specific drive letter."""
    if drive_letter in active_observers:
        logger.log_warning("FILE_AUDIT", f"Already auditing drive {drive_letter}")
        return

    path_to_watch = f"{drive_letter}\\"
    if not os.path.exists(path_to_watch):
        logger.log_warning("FILE_AUDIT", f"Drive path {path_to_watch} does not exist.")
        return

    logger.log_event("FILE_AUDIT", f"Starting file audit on drive {drive_letter}")
    
    event_handler = USBFileHandler(drive_letter)
    observer = Observer()
    observer.schedule(event_handler, path_to_watch, recursive=True)
    observer.start()
    
    active_observers[drive_letter] = observer

def stop_auditing_drive(drive_letter):
    """Stops the watchdog observer for a specific drive letter."""
    if drive_letter in active_observers:
        logger.log_event("FILE_AUDIT", f"Stopping file audit on drive {drive_letter}")
        observer = active_observers.pop(drive_letter)
        observer.stop()
        observer.join()

def find_drive_letter_for_device(device_id):
    """
    Queries WMI to find the logical drive letter associated with a USB PNP Device ID.
    This can be complex in WMI due to the linkage between Win32_PnPEntity,
    Win32_DiskDrive, Win32_DiskPartition, and Win32_LogicalDisk.
    For simplicity in this framework, we can actively poll for new Win32_LogicalDisk arrivals.
    """
    pythoncom.CoInitialize()
    c = wmi.WMI()
    
    # Simple approach: Check all removable drives
    # DriveType 2 corresponds to Removable Disk
    drive_letters = []
    try:
        for disk in c.Win32_LogicalDisk(DriveType=2):
            drive_letters.append(disk.DeviceID)
    except Exception as e:
        logger.log_error("SYSTEM", f"Error querying logical disks: {str(e)}")
        
    pythoncom.CoUninitialize()
    return drive_letters

def start_auditing_if_storage(device_id):
    """
    Invoked by policy_manager when an authorized device is connected.
    We need to wait slightly for Windows to mount the volume and assign a drive letter.
    """
    def _delayed_check():
        time.sleep(3) # Give Windows time to mount
        letters = find_drive_letter_for_device(device_id)
        for letter in letters:
            start_auditing_drive(letter)
            
    t = threading.Thread(target=_delayed_check)
    t.daemon = True
    t.start()
