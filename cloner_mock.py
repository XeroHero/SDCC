#!/usr/bin/env python3
# /usr/local/bin/sd_cloner_mock.py - Testable mock version
import os
import subprocess
import time
import sys
import platform
import random
from pathlib import Path
import json
import shlex

# Mock GPIO for testing
class GPIOMock:
    BCM = 'BCM'
    IN = 'IN'
    OUT = 'OUT'
    PUD_UP = 'PUD_UP'
    LOW = 0
    HIGH = 1
    
    def __init__(self):
        self.pins = {}
        self.modes = {}
        self.pull_ups = {}
        
    def setmode(self, mode):
        print(f"[MOCK] Setting GPIO mode to {mode}")
        
    def setup(self, pin, mode, pull_up_down=None):
        print(f"[MOCK] Setup pin {pin} as {mode} with pull {pull_up_down}")
        self.pins[pin] = self.HIGH  # Default to HIGH for inputs
        self.modes[pin] = mode
        self.pull_ups[pin] = pull_up_down
        
    def output(self, pin, state):
        if pin in self.pins:
            state_str = "HIGH" if state else "LOW"
            print(f"[MOCK] Setting pin {pin} to {state_str}")
            self.pins[pin] = state
        
    def input(self, pin):
        # Simulate button press after 3 seconds
        if pin == 17:  # BTN_PIN
            if time.time() % 10 < 0.5:  # Simulate button press every 10 seconds
                print("\n[TEST] Simulating button press")
                return self.LOW
        return self.HIGH
        
    def cleanup(self):
        print("[MOCK] Cleaning up GPIO")
        self.pins.clear()
        self.modes.clear()
        self.pull_ups.clear()

# Use mock GPIO
GPIO = GPIOMock()

# Test mode flag
TEST_MODE = True

# GPIO Pins
BTN_PIN = 17
LED_READY = 22    # Red
LED_CLONING = 23  # Yellow
LED_DONE = 24     # Green

class HeadlessCloner:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(LED_READY, GPIO.OUT)
        GPIO.setup(LED_CLONING, GPIO.OUT)
        GPIO.setup(LED_DONE, GPIO.OUT)

        self.source_devices = []
        self.dest_device = None
        
        # Use a user-writable log file location
        log_dir = os.path.expanduser("~/.sdcc_logs")
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, "cloner.log")
        print(f"[TEST] Logging to: {self.log_file}")

        self.led_off_all()
        self.blink_ready()

    def led_off_all(self):
        GPIO.output(LED_READY, GPIO.LOW)
        GPIO.output(LED_CLONING, GPIO.LOW)
        GPIO.output(LED_DONE, GPIO.LOW)

    def blink_ready(self):
        # Blink red LED when ready
        GPIO.output(LED_READY, not GPIO.input(LED_READY))

    def detect_devices(self):
        """Detect source (SD card/USB camera) and destination (HDD/SSD)"""
        if TEST_MODE:
            print("[TEST] Simulating device detection")
            # Return mock devices for testing with different sizes and models
            return [
                {
                    'device': '/dev/disk/by-id/usb-Test_Flash_123456-0:0',
                    'size_gb': 32.0,
                    'name': 'sdc',
                    'model': 'USB_Flash_Drive',
                    'serial': '123456'
                },
                {
                    'device': '/dev/disk/by-id/usb-Backup_Plus_789012-0:1',
                    'size_gb': 1000.0,
                    'name': 'sdd',
                    'model': 'Backup_Plus_HDD',
                    'serial': '789012'
                },
                {
                    'device': '/dev/disk/by-id/usb-SD_Card_Reader_345678-0:0',
                    'size_gb': 64.0,
                    'name': 'sde',
                    'model': 'SD_Card_Reader',
                    'serial': '345678'
                }
            ]
            
        devices = []
        # Original detection code here
        for path in Path('/sys/block').iterdir():
            if not path.is_dir():
                continue
            # ... rest of the original code ...
            return devices

        return devices

    def get_device_model(self, dev_name):
        try:
            model_path = Path(f'/sys/block/{dev_name}/device/model')
            if model_path.exists():
                return model_path.read_text().strip()
        except:
            return "Unknown"

    def identify_source_dest(self, devices):
        """Smart detection: smallest USB device = source, largest = destination"""
        if len(devices) < 2:
            return None, None

        # Sort by size
        sorted_devs = sorted(devices, key=lambda x: x['size_gb'])
        
        if TEST_MODE:
            print("\n[TEST] Detected devices (sorted by size):")
            for i, dev in enumerate(sorted_devs):
                print(f"  {i+1}. {dev['device']} - {dev['size_gb']}GB - {dev['model']}")

        # Smallest = source (SD card), largest = destination (HDD)
        source = sorted_devs[0]['device']
        dest = sorted_devs[-1]['device']
        
        if TEST_MODE:
            print(f"\n[TEST] Selected source: {source} (smallest device)")
            print(f"[TEST] Selected destination: {dest} (largest device)")

        return source, dest

    def validate_clone(self, source, dest):
        """Check if clone is safe to proceed"""
        if not source or not dest:
            return False, "Missing devices"

        # Get sizes
        source_size = self.get_device_size(source)
        dest_size = self.get_device_size(dest)

        if dest_size < source_size:
            return False, "Destination too small"

        # Check if destination is empty (optional safety)
        # You could add partition table check here

        return True, "OK"

    def get_device_size(self, device):
        try:
            result = subprocess.run(
                ['sudo', 'blockdev', '--getsize64', device],
                capture_output=True, text=True
            )
            return int(result.stdout.strip())
        except:
            return 0

    def clone_with_rsync(self, source, dest):
        """
        Clone using rsync - better for filesystem cloning
        Creates exact copy including partition table
        """
        if TEST_MODE:
            print(f"[TEST] Would clone from {source} to {dest}")
            print("[TEST] Simulating clone operation (10 seconds)")
            for i in range(10, 0, -1):
                print(f"[TEST] Cloning... {i} seconds remaining")
                time.sleep(1)
            print("[TEST] Clone complete!")
            return
            
        # Original rsync code
        print(f"Cloning partition table from {source} to {dest}")
        subprocess.run([
            'sudo', 'sgdisk', '-R', dest, source
        ], check=True)

        # Reload partition table
        subprocess.run(['sudo', 'partprobe', dest], check=True)

        # Clone each partition
        source_parts = [p for p in Path('/dev').glob(f'{os.path.basename(source)}[0-9]*')]

        for part in source_parts:
            part_num = part.name[-1]
            dest_part = f"{dest}{part_num}"

            # Get filesystem type
            fstype = self.get_filesystem_type(str(part))

            if fstype in ['ext4', 'fat32', 'vfat', 'ntfs', 'exfat']:
                # Clone filesystem data
                self.clone_filesystem(str(part), dest_part, fstype)
            else:
                # Raw copy for unknown filesystems
                self.raw_clone(str(part), dest_part)

    def clone_filesystem(self, source, dest, fstype):
        """Clone using filesystem-aware tools"""
        print(f"Cloning {source} ({fstype}) to {dest}")

        # Create filesystem
        mkfs_cmd = {
            'ext4': ['mkfs.ext4', '-F', dest],
            'vfat': ['mkfs.vfat', '-F', '32', dest],
            'fat32': ['mkfs.vfat', '-F', '32', dest],
            'ntfs': ['mkfs.ntfs', '-F', dest],
            'exfat': ['mkfs.exfat', dest]
        }

        if fstype in mkfs_cmd:
            subprocess.run(['sudo'] + mkfs_cmd[fstype], check=True)

        # Mount and copy
        temp_mount = '/mnt/temp_clone'
        os.makedirs(temp_mount, exist_ok=True)

        # Mount destination
        subprocess.run(['sudo', 'mount', dest, temp_mount], check=True)

        try:
            # Use rsync for efficient copying
            rsync_cmd = [
                'sudo', 'rsync', '-avh', '--progress',
                '--exclude', '/lost+found',
                f'{source}:/', temp_mount + '/'
            ]

            # If source isn't mounted, mount it temporarily
            source_mounted = False
            if not os.path.ismount(source):
                source_temp = '/mnt/temp_source'
                os.makedirs(source_temp, exist_ok=True)
                subprocess.run(['sudo', 'mount', source, source_temp], check=True)
                source_mounted = True
                rsync_cmd[-2] = f'{source_temp}/'

            # Execute rsync
            process = subprocess.Popen(
                rsync_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            # Monitor progress
            for line in process.stdout:
                if '%' in line:
                    print(f"Progress: {line.strip()}")

            process.wait()

            if source_mounted:
                subprocess.run(['sudo', 'umount', source_temp], check=True)

        finally:
            # Cleanup
            subprocess.run(['sudo', 'umount', temp_mount], check=True)
            os.rmdir(temp_mount)

    def raw_clone(self, source, dest):
        """Fallback to dd for raw cloning"""
        print(f"Raw cloning {source} to {dest}")
        size = self.get_device_size(source)

        # Use dd with progress
        dd_cmd = f'sudo dd if={source} of={dest} bs=4M status=progress'
        subprocess.run(dd_cmd, shell=True, check=True)

    def get_filesystem_type(self, device):
        try:
            result = subprocess.run(
                ['sudo', 'blkid', '-s', 'TYPE', '-o', 'value', device],
                capture_output=True, text=True
            )
            return result.stdout.strip().lower()
        except:
            return "unknown"

    def main_loop(self):
        print("=== SD Card Cloner (TEST MODE) ===")
        print("This is a test version that simulates hardware")
        print("The script will automatically simulate a button press every 10 seconds")
        print("and show the cloning process without touching any real devices.\n")
        
        if TEST_MODE:
            print("Test mode enabled. The script will automatically detect and select devices based on size.")
            print("Test devices will be automatically selected based on size (smallest = source, largest = destination)")
            print("Waiting for button press (simulated every 10 seconds)...")

        button_pressed = False

        while True:
            # Blink ready LED
            if time.time() % 2 < 0.5:  # Blink every second
                self.blink_ready()
            else:
                GPIO.output(LED_READY, GPIO.LOW)

            # Check button
            if GPIO.input(BTN_PIN) == GPIO.LOW and not button_pressed:
                button_pressed = True
                print("Button pressed - Starting device detection")
                self.led_off_all()
                GPIO.output(LED_READY, GPIO.HIGH)  # Solid red

                # Detect devices
                devices = self.detect_devices()
                print(f"Found {len(devices)} USB devices")

                if len(devices) >= 2:
                    source, dest = self.identify_source_dest(devices)
                    valid, msg = self.validate_clone(source, dest)

                    if valid:
                        print(f"Source: {source}, Destination: {dest}")
                        self.start_clone(source, dest)
                    else:
                        print(f"Validation failed: {msg}")
                        self.error_pattern()
                else:
                    print(f"Need 2 devices (found {len(devices)})")
                    self.error_pattern()

                # In test mode, don't wait for button release
                if not TEST_MODE:
                    while GPIO.input(BTN_PIN) == GPIO.LOW:
                        time.sleep(0.1)
                button_pressed = False

            time.sleep(0.1)

    def start_clone(self, source, dest):
        """Execute the cloning process"""
        print(f"Starting clone: {source} → {dest}")

        # Yellow LED on (cloning)
        GPIO.output(LED_CLONING, GPIO.HIGH)
        GPIO.output(LED_READY, GPIO.LOW)

        try:
            # Log start
            with open(self.log_file, 'a') as f:
                f.write(f"\n--- Clone started at {time.ctime()} ---\n")
                f.write(f"Source: {source}\n")
                f.write(f"Destination: {dest}\n")

            # Perform clone
            self.clone_with_rsync(source, dest)

            # Success
            print("Clone completed successfully!")
            with open(self.log_file, 'a') as f:
                f.write("Clone completed successfully!\n")

            # Green LED for success
            self.led_off_all()
            GPIO.output(LED_DONE, GPIO.HIGH)
            time.sleep(5)  # Show success for 5 seconds

        except Exception as e:
            print(f"Clone failed: {e}")
            with open(self.log_file, 'a') as f:
                f.write(f"Clone failed: {e}\n")
            self.error_pattern()
        finally:
            # Return to ready state
            self.led_off_all()

    def error_pattern(self):
        """Flash LEDs in error pattern"""
        for _ in range(5):
            GPIO.output(LED_READY, GPIO.HIGH)
            time.sleep(0.2)
            GPIO.output(LED_READY, GPIO.LOW)
            time.sleep(0.2)
        time.sleep(2)

if __name__ == "__main__":
    cloner = HeadlessCloner()
    try:
        cloner.main_loop()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        GPIO.cleanup()