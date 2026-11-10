import markdown
import threading
import json
import csv
import time
import os
import logging
from flask import Flask, render_template, jsonify
from gpiozero import AngularServo, MCP3008
from gpiozero.pins.pigpio import PiGPIOFactory

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


#CSV and pin assignments for processing
DATA_FILE = "room_calibration.csv"
PAN_PIN = 17
TILT_PIN = 18

#Globally accessable variable
system_state = {
	"tl": 0, "tr": 0, "bl": 0, "br": 0,
	"pan_angle": 0, "tilt_angle": -70,
	"mode": "Initializing",
	"control_mode": "AUTO"
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
		try:
			if system_state['control_mode'] == "MANUAL":
				system_state['mode'] = "MANUAL CONTROL"
				#manual mode, use last known angle
				current_pan = system_state['pan_angle']
				current_tilt = system_state['tilt_angle']
				pan.angle = current_pan
				tilt.angle = current_tilt
				time.sleep(0.1)
				continue

			# 1. Read Sensors
			v_tl = tl.value
			v_tr = tr.value
			v_bl = bl.value
			v_br = br.value

			#Data to update system state
			system_state['tl'] = round(v_tl, 2)
			system_state['tr'] = round(v_tr, 2)
			system_state['bl'] = round(v_bl, 2)
			system_state['br'] = round(v_br, 2)
			system_state['pan_angle'] = current_pan
			system_state['tilt_angle'] = current_tilt

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
				system_state['mode'] = "Idle"
				time.sleep(0.1)
				continue

			system_state['mode'] = "TRACKING"


			#shift accordingly if light is strong enough
			if abs(diff_horiz) > DIFF_THRESHOLD:
				if avg_left > avg_right:
					current_pan += 4
				else:
					current_pan -= 4

				if current_tilt < 0:
					if avg_left > avg_right: current_pan -= 8
					else: current_pan += 8

				current_pan = max(PAN_MIN, min(PAN_MAX, current_pan))
				pan.angle = current_pan
				time.sleep(0.05)
				continue

			elif abs(diff_vert) > DIFF_THRESHOLD:
				if avg_top > avg_bot:
					current_tilt -= 4
				else:
					current_tilt += 4


				current_tilt = max(TILT_MIN, min(TILT_MAX, current_tilt))
				tilt.angle = current_tilt
				time.sleep(0.05)
				continue

			time.sleep(0.05)
		except Exception as e:
			print(f"Error: {e}")
			time.sleep(1)
#FLASK WEB SERVER
app = Flask (__name__)

@app.route('/')
def index():
	try:
		with open('README.md', 'r') as f:
			content = f.read()
			readme_html = markdown.markdown(content)
	except FileNotFoundError:
		readme_html = "<h2>No README.md found!</h2>"

	return render_template('index.html', readme=readme_html)
@app.route('/data')
def data():
	return jsonify(system_state)

@app.route('/set_mode/<mode>')
def set_mode(mode):
	system_state['control_mode'] = mode
	return "OK"

@app.route('/move/<axis>/<direction>')
def manual_move(axis, direction):
	if system_state['control_mode'] != "MANUAL": return "Ignored"

	step = 5
	if axis == "pan":
		new_val = system_state['pan_angle'] + (step if direction == "left" else -step)
		system_state['pan_angle'] = max(PAN_MIN, min(PAN_MAX, new_val))
	elif axis == "tilt":
		new_val = system_state['tilt_angle'] + (-step if direction == "up" else step)
		system_state['tilt_angle'] = max(TILT_MIN, min(TILT_MAX, new_val))

	return "OK"


if __name__ == '__main__':
	tracker = threading.Thread(target=tracking_loop)
	tracker.daemon = True
	tracker.start()

	app.run(host='0.0.0.0', port=5001, debug=False)
