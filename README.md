# Dual-Axis Solar Tracker
**Author:** Alexander Gruden

## How It Works
This robot uses a **differential sensing algorithm** to locate the brightest light source.
1. **Four Photocells** detect light intensity in quadrants.
2. A **Shadow creating cross** creates contrast when the sun is off-center.
3. The **Raspberry Pi 4** calculates the vector difference and drives two 20KG servos.

## Instructions
1. **Auto Mode:** Use a flashlight to guide the robot.
2. **Manual Mode:** Click "MANUAL" to take control via D-Pad.

## Tech Stack
* **Hardware:** Raspberry Pi 4, MCP3008 ADC
* **Software:** Python 3, Flask, Pigpio (Hardware Timing)
