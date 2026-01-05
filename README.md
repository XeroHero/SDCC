# SD Card Cloner

## About the tool

This tool is designed for photographers and people who often fill up SD cards and are far away from a laptop or PC to be able to empty the cards to a bigger storage and resume shooting
## Technologies Used
- Python 3.14
- RPi Library

## Basic Concept

A Raspberry Pi-based device that automatically clones SD card contents to an external USB drive when both are connected.

### Complete System Design - Hardware Setup

Components:
1. Raspberry Pi (any model with USB ports)
2. Physical push button (momentary switch)
3. 3x LEDs (Red, Yellow, Green)
4. Resistors (220Ω for LEDs)
5. USB card reader (for SD cards)
6. USB HDD/SSD (destination drive)
7. Power supply for Pi
8. Optional: USB camera connection support

### Wiring Diagram

- Button: GPIO17 (pin 11) to GND (pull-up internally)
- Red LED:   GPIO22 (pin 15) → Resistor → GND (Error/Ready)
- Yellow LED: GPIO23 (pin 16) → Resistor → GND (Cloning in progress)
- Green LED:  GPIO24 (pin 18) → Resistor → GND (Complete)

### Software Setup
1. Clone the repository
2. Install the dependencies usign the install_cloner.sh script
