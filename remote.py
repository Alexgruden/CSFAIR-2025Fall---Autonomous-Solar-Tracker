from flask import Flask, render_template, request
from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory
import time

# --- CONFIGURATION ---
PAN_PIN = 17  # Check your specific wiring (17 or 18)
TILT_PIN = 18 

# SERVO LIMITS
PAN_MIN = -135
PAN_MAX = 135
TILT_MIN = -90
TILT_MAX = 90

# --- HARDWARE SETUP ---
factory = PiGPIOFactory()
pan = AngularServo(PAN_PIN, min_angle=-135, max_angle=135, min_pulse_width=0.0005, max_pulse_width=0.0025, pin_factory=factory)
tilt = AngularServo(TILT_PIN, min_angle=-90, max_angle=135, min_pulse_width=0.0005, max_pulse_width=0.0025, pin_factory=factory)

# GLOBAL STATE (Where is the robot now?)
current_pan = 0
current_tilt = -70

# --- MOVE TO START POS ---
pan.angle = current_pan
tilt.angle = current_tilt

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('remote.html')

@app.route('/move/<axis>/<direction>')
def move(axis, direction):
    global current_pan, current_tilt
    
    step = 10  # Degrees to move per click
    
    # 1. Calculate New Angle
    if axis == 'pan':
        if direction == 'left':
            current_pan += step
        elif direction == 'right':
            current_pan -= step
        
        # Safety Clamp
        current_pan = max(PAN_MIN, min(PAN_MAX, current_pan))
        pan.angle = current_pan
        print(f"Panning to: {current_pan}")

    elif axis == 'tilt':
        # Note: 'up' usually means more negative for your setup (-90 is ceiling)
        if direction == 'up':
            current_tilt -= step 
        elif direction == 'down':
            current_tilt += step
            
        # Safety Clamp
        current_tilt = max(TILT_MIN, min(TILT_MAX, current_tilt))
        tilt.angle = current_tilt
        print(f"Tilting to: {current_tilt}")
        
    return "OK"

if __name__ == '__main__':
    print("Remote Control Active on Port 5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
