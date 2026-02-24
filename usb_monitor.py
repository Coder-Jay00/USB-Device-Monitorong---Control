import time
import wmi
import pythoncom
import threading

import logger
import policy_manager

class USBMonitor:
    def __init__(self):
        self.running = False
        
    def _listen_for_events(self):
        # COM initialization is required for background threads using WMI
        pythoncom.CoInitialize()
        
        c = wmi.WMI()
        
        # WQL query to watch for Win32_VolumeChangeEvent (Type 2 = Device Arrival, 3 = Device Removal)
        # Note: Win32_VolumeChangeEvent is good for storage, but Win32_DeviceChangeEvent 
        # or Win32_PnPEntity events are better for overall USB. Let's use Win32_VolumeChangeEvent 
        # for detecting logical drive letters, and Win32_USBControllerDevice for hardware info.
        
        # Actually, Win32_VolumeChangeEvent is best for finding the drive letter (which we need for file auditing)
        watcher = c.Win32_VolumeChangeEvent.watch_for(
            raw_wql="SELECT * FROM __InstanceCreationEvent WITHIN 2 WHERE TargetInstance ISA 'Win32_LogicalDisk' AND TargetInstance.DriveType = 2"
        )
        
        # To catch real-time connection events (even before mounting a drive letter, or non-storage devices)
        # we can monitor __InstanceCreationEvent for Win32_PnPEntity where DeviceID like "USB%"
        pnp_watcher = c.Win32_PnPEntity.watch_for(
            raw_wql="SELECT * FROM __InstanceCreationEvent WITHIN 2 WHERE TargetInstance ISA 'Win32_PnPEntity' AND TargetInstance.DeviceID LIKE 'USB%'"
        )

        logger.log_event("SYSTEM", "USB Monitor started. Listening for USB connection events...")

        # We will use WMI polling in a loop
        while self.running:
            try:
                # Wait for PnP device connection
                usb_device = pnp_watcher(timeout_ms=3000)
                if usb_device:
                    instance = usb_device.TargetInstance
                    device_id = instance.DeviceID
                    name = instance.Name
                    
                    logger.log_event("USB_DETECTED", f"Device Connected: {name} (DeviceID: {device_id})")
                    
                    # Pass the device ID to policy manager to check and potentially block
                    policy_manager.check_device(instance)

            except wmi.x_wmi_timed_out:
                pass
            except Exception as e:
                logger.log_error("MONITOR_ERROR", str(e))
                
        # Uninitialize COM when thread exits
        pythoncom.CoUninitialize()

    def start(self):
        self.running = True
        self.monitor_thread = threading.Thread(target=self._listen_for_events)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop(self):
        self.running = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5)
            
if __name__ == "__main__":
    monitor = USBMonitor()
    monitor.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
        print("Exiting...")
