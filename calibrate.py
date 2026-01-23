import csv
import os
import time
from gpiozero import AngularServo, MCP3008
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

print("--- QUAD SENSOR CALIBRATION ---")
print("30 Second calibration for the baseline light level of room")
print("-----------------------------------")

#csv file name, calibration duratino, and pin assignments
CSV_FILE = "room_calibration.csv"
CALIBRATION_TIME = 30
PAN_PIN = 17
TILT_PIN = 18

#light sensors mapped to respective channels of MCP3008
tl = MCP3008(channel=0)
tr = MCP3008(channel=1)
bl = MCP3008(channel=2)
br = MCP3008(channel=3)

#Initialize only tilt servo to get reading tilting straight upwards
factory = PiGPIOFactory()
tilt = AngularServo(TILT_PIN, min_angle=-90, max_angle= 90, min_pulse_width=0.0005, max_pulse_width=0.0025, pin_factory=factory)

print(f"\n ==CALIBRATION MODE: {CALIBRATION_TIME})")
print("Now adjusting to the room")

#tilt servo straight upwards to read the light of the room
try:
	print("Tilting servo towards sky")
	tilt.angle = 0
	sleep(2)
except KeyboardInterrupt:
	print("Program stopped")

#list for data rows
data_rows = []
#Define start time
start_time = time.time()

try:
	while(time.time() - start_time) < CALIBRATION_TIME:
		#read all 4 sensors at once
		row = [tl.value, tr.value, bl.value, br.value]
		#append row of readings to row list
		data_rows.append(row)

		#Update progress
		elapsed = int(time.time() - start_time)
		print(f"Calibrating:   Time Elapsed: {elapsed}/{CALIBRATION_TIME}s", end='\r')
		time.sleep(0.1)

		#save all data to a csv
	with open(CSV_FILE, 'w', newline ='') as f:
		writer = csv.writer(f)
		#create header row
		writer.writerow(["TL","TR","BL","BR"])
		#write rest of rows
		writer.writerows(data_rows)
	print("Calibration saved to file.")
	print("Tracking is now enabled")

except KeyboardInterrupt:
	print("\nCancelled.")

