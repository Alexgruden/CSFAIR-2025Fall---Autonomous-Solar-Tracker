import threading
import json
import csv
import time
import os
from flask import Flask, render_template, jsonifys
from gpiozero import AngularServo, MCP3008
from gpiozero.pins.pigpio import PiGPIOFactory

#CSV and pin assignments for processing
DATA_FILE = "room_calibration.csv"
PAN_PIN = 17
TILT_PIN = 18

#Globally accessable variable
system_state = {
	"tl": 0, "tr": 0, "bl": 0, "br": 0,
	"pan_angle": 0, "tilt_angle": -70,
	"mode": "Initializing"
}

#Set Bounds for servo movement
PAN_MIN = -130
PAN_MAX = 130
TILT_MIN = -90
TILT_MAX = 90

#Sensors Assignments
tl = MCP3008(channel=0)
tr = MCP3008(channel=1)
bl = MCP3008(channel=2)
br = MCP3008(channel=3)

#Servo assignments
factory = PiGPIOFactory()
pan = AngularServo(PAN_PIN, min_angle=-135, max_angle=135, min_pulse_width=0.0005, max_pulse_width=0.0025, pin_factory=factory)
tilt = AngularServo(TILT_PIN, min_angle=-90, max_angle=90, min_pulse_width=0.0005, max_pulse_width=0.0025, pin_factory=factory)


"""
Gets 3 thresholds
1. How different left and right groups of sensors must be for panning to activate
2. How different top and bottom groups of sensors must be for tilting to activate
3. The Absolute threshhold/Light Noise floor before the servo will consider moving
"""
def get_thresholds():
	#If file is non existant
	if not os.path.exists(DATA_FILE):
		print(f"Warning: {DATA_FILE} not found! Using defaults")
		return 0.2, 0.6

	try:
		#read all values of csv add to cumulative list
		all_values = []
		with open(DATA_FILE, 'r') as f:
			reader = csv.reader(f)
			next(reader)
			for row in reader:
				all_values.extend([float(x) for x in row])

		if not all_values: return 0.2, 0.6

		#Calculate thresholds 1 and 2
		max_noise = max(all_values)
		abs_threshold = max_noise + .05
		diff_threshold = .15

		#print calibrations
		print("Using the following thresholds for calibration")
		print(f"  - Ignore anything darker than: {abs_threshold:.2f}")
		print(f"  - Turn if difference > {diff_threshold:.2f}")

		return diff_threshold, abs_threshold
	except:
		return 0.2, 0.6

#loop tracking to enable visualization
def tracking_loop():
	global system_state
	#Define thresholds for main to use
	DIFF_THRESHOLD, LIGHT_THRESHOLD = get_thresholds()

	# Home Position
	current_pan = 80
	current_tilt = 80
	pan.angle = current_pan
	tilt.angle = current_tilt
	time.sleep(1)

	print("Active. Ctrl+C to stop.")

	while True:
		# 1. Read Sensors
		v_tl = tl.value
		v_tr = tr.value
		v_bl = bl.value
		v_br = br.value

		#check max
		brightest_sensor = max(v_tl, v_tr, v_bl, v_br)

		# 2. Average Sides
		avg_top = (v_tl + v_tr) / 2
		avg_bot = (v_bl + v_br) / 2
		avg_left = (v_tl + v_bl) / 2
		avg_right = (v_tr + v_br) / 2

		# 3. Calculate Differences
		diff_vert = avg_top - avg_bot
		diff_horiz = avg_left - avg_right

		#sit idle if light reading arent enough to move
		if brightest_sensor < LIGHT_THRESHOLD:
			print(f"Idle: (Light: {brightest_sensor:.2f} < {LIGHT_THRESHOLD:.2f})", end='\r')
			time.sleep(0.1)
			continue

		#shift accordingly if light is strong enough
		if abs(diff_vert) > DIFF_THRESHOLD:
			if avg_top > avg_bot:
				current_tilt -= 5
			else:
				current_tilt += 5

		if abs(diff_horiz) > DIFF_THRESHOLD:
			step = 1 if avg_left > avg_right else -1
			#if gimble is flipped
			if current_tilt < 0: step *= -1
			current_pan += step

		current_pan = max(PAN_MIN, min(PAN_MAX, current_pan))
		current_tilt = max(TILT_MIN, min(TILT_MAX, current_tilt))

		tilt.angle = current_tilt
		pan.angle = current_pan
		time.sleep(0.05)


#FLASK WEB SERVER
app = Flask (__name__)

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/data')
def data():
	return jsonify(system_state)

if __name__ == '__main__':
	tracker = threading.Thread(target=tracker_loop)
	tracker.daemon = True
	tracker.start()

	app.run(host='0.0.0.0', port=5000, debug=False)
