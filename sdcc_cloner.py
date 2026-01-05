#!/usr/bin/env python3
# SD Card Cloner - Production Version
# For Raspberry Pi with GPIO control
# Save as: /usr/local/bin/sdcc_cloner.py

import os
import subprocess
import time
import sys
from pathlib import Path
import json
import shutil
import RPi.GPIO as GPIO

# Configuration
TEST_MODE = False  # Set to False for production
LOG_DIR = "/var/log/sdcc"
LOG_FILE = os.path.join(LOG_DIR, "cloner.log")

# GPIO Pins (BCM numbering)
BTN_PIN = 17      # Button (pulled up, connect to GND to activate)
LED_READY = 22    # Red LED - Ready state
LED_CLONING = 23  # Yellow LED - Cloning in progress
LED_DONE = 24     # Green LED - Clone complete

class SDCardCloner:
    def __init__(self):
        self.setup_gpio()
        self.setup_logging()
        self.log("=== SD Card Cloner Started ===")
        self.log(f"Logging to: {LOG_FILE}")
        
    def setup_gpio(self):
        """Initialize GPIO pins"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup button (pulled up)
        GPIO.setup(BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Setup LEDs
        for pin in [LED_READY, LED_CLONING, LED_DONE]:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
    
    def setup_logging(self):
        """Ensure log directory exists and is writable"""
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            # Test if we can write to the log directory
            with open(LOG_FILE, 'a'):
                pass
        except Exception as e:
            print(f"Error setting up logging: {e}")
            sys.exit(1)
    
    def log(self, message):
        """Log message to file and print to console"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        try:
            with open(LOG_FILE, 'a') as f:
                f.write(log_message + "\n")
        except Exception as e:
            print(f"Error writing to log: {e}")
    
    def led_on(self, pin):
        """Turn on an LED"""
        GPIO.output(pin, GPIO.HIGH)
    
    def led_off(self, pin):
        """Turn off an LED"""
        GPIO.output(pin, GPIO.LOW)
    
    def led_off_all(self):
        """Turn off all LEDs"""
        for pin in [LED_READY, LED_CLONING, LED_DONE]:
            self.led_off(pin)
    
    def blink_ready(self):
        """Blink the ready LED"""
        current_state = GPIO.input(LED_READY)
        self.led_on(LED_READY) if not current_state else self.led_off(LED_READY)
    
    def detect_devices(self):
        """Detect available storage devices"""
        devices = []
        
        try:
            # List all block devices
            for path in Path('/sys/block').iterdir():
                if not path.is_dir() or path.name.startswith('loop') or path.name.startswith('ram'):
                    continue
                    
                device = f"/dev/{path.name}"
                
                # Skip the boot device (mmcblk0 on Raspberry Pi)
                if path.name.startswith('mmcblk0'):
                    self.log(f"Skipping boot device: {device}")
                    continue
                
                try:
                    # Get device size
                    size = int((Path(f'/sys/block/{path.name}/size').read_text().strip()))
                    size_gb = (size * 512) / (1024**3)  # Convert to GB
                    
                    # Get device model
                    model = "Unknown"
                    model_path = Path(f'/sys/block/{path.name}/device/model')
                    if model_path.exists():
                        model = model_path.read_text().strip()
                    
                    # Get device path by ID if available
                    by_id = list(Path('/dev/disk/by-id/').glob(f'*{path.name}'))
                    device_path = by_id[0].resolve() if by_id else device
                    
                    devices.append({
                        'device': str(device_path),
                        'name': path.name,
                        'size_gb': round(size_gb, 2),
                        'model': model
                    })
                    
                except Exception as e:
                    self.log(f"Error reading device {device}: {e}")
                    continue
                    
        except Exception as e:
            self.log(f"Error detecting devices: {e}")
        
        return devices
    
    def identify_source_dest(self, devices):
        """Identify source (smallest) and destination (largest) devices"""
        if len(devices) < 2:
            self.log("Error: Need at least 2 devices")
            return None, None
            
        # Sort by size
        sorted_devices = sorted(devices, key=lambda x: x['size_gb'])
        
        # Smallest device is source, largest is destination
        source = sorted_devices[0]
        dest = sorted_devices[-1]
        
        self.log(f"Selected source: {source['device']} ({source['size_gb']}GB - {source['model']})")
        self.log(f"Selected destination: {dest['device']} ({dest['size_gb']}GB - {dest['model']})")
        
        return source, dest
    
    def validate_clone(self, source, dest):
        """Validate that the clone operation is safe"""
        if source['size_gb'] > dest['size_gb']:
            self.log(f"Error: Source ({source['size_gb']}GB) is larger than destination ({dest['size_gb']}GB)")
            return False
            
        # Add more validations here if needed
        return True
    
    def clone_device(self, source, dest):
        """Clone source device to destination device"""
        self.log(f"Starting clone: {source['device']} → {dest['device']}")
        
        try:
            # Show cloning in progress
            self.led_off_all()
            self.led_on(LED_CLONING)
            
            # Use dd to clone the entire device
            # Note: This will overwrite the destination completely
            cmd = [
                'sudo', 'dd',
                f'if={source["device"]}',
                f'of={dest["device"]}',
                'bs=4M',
                'status=progress',
                'conv=fsync'
            ]
            
            self.log(f"Executing: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Stream output to log
            for line in process.stdout:
                self.log(f"DD: {line.strip()}")
                
            process.wait()
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd)
                
            # Sync to ensure all writes are flushed
            os.sync()
            
            self.log("Clone completed successfully!")
            self.led_off(LED_CLONING)
            self.led_on(LED_DONE)
            time.sleep(5)  # Show success for 5 seconds
            
        except Exception as e:
            self.log(f"Clone failed: {e}")
            self.error_pattern()
            raise
    
    def error_pattern(self):
        """Flash LEDs to indicate an error"""
        for _ in range(5):
            self.led_off_all()
            time.sleep(0.2)
            self.led_on(LED_READY)
            time.sleep(0.2)
        self.led_off_all()
    
    def main_loop(self):
        """Main application loop"""
        self.log("SD Card Cloner ready. Press button to start.")
        
        try:
            while True:
                # Blink ready LED
                if time.time() % 2 < 0.5:
                    self.blink_ready()
                else:
                    self.led_off(LED_READY)
                
                # Check for button press
                if GPIO.input(BTN_PIN) == GPIO.LOW:
                    self.log("Button pressed. Detecting devices...")
                    self.led_off_all()
                    self.led_on(LED_READY)  # Solid red while detecting
                    
                    try:
                        # Detect devices
                        devices = self.detect_devices()
                        
                        if not devices:
                            self.log("No devices found!")
                            self.error_pattern()
                            continue
                            
                        self.log(f"Found {len(devices)} devices:")
                        for i, dev in enumerate(devices, 1):
                            self.log(f"  {i}. {dev['device']} - {dev['size_gb']}GB - {dev['model']}")
                        
                        # Identify source and destination
                        source, dest = self.identify_source_dest(devices)
                        
                        if not source or not dest:
                            self.log("Could not identify source and destination")
                            self.error_pattern()
                            continue
                            
                        # Validate before cloning
                        if not self.validate_clone(source, dest):
                            self.error_pattern()
                            continue
                            
                        # Start the clone
                        self.clone_device(source, dest)
                        
                    except Exception as e:
                        self.log(f"Error: {e}")
                        self.error_pattern()
                    
                    # Wait for button release
                    while GPIO.input(BTN_PIN) == GPIO.LOW:
                        time.sleep(0.1)
                    
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.log("\nShutting down...")
        except Exception as e:
            self.log(f"Fatal error: {e}")
            raise
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up GPIO and exit"""
        self.led_off_all()
        GPIO.cleanup()
        self.log("Cleanup complete. Goodbye!")

if __name__ == "__main__":
    # Check if running as root
    if os.geteuid() != 0:
        print("This script must be run as root. Use 'sudo'.")
        sys.exit(1)
    
    cloner = SDCardCloner()
    cloner.main_loop()
