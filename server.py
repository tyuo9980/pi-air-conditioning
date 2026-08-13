from threading import Lock

from flask import Flask, jsonify, render_template, request

import servo

from w1thermsensor import W1ThermSensor

app = Flask(__name__)
_servo_lock = Lock()  # serialize hardware access across Flask worker threads

sensor = W1ThermSensor()

# Dial mapping: where the servo horn sits for "off" and across the setpoint range.
# Tune these to match the AC's actual dial travel.
OFF_ANGLE = 0.0
MIN_ANGLE = 20.0
MAX_ANGLE = 180.0
MIN_TEMP = 16.0
MAX_TEMP = 30.0

_power_on = False
_target_temp = 22.0


def _angle_for(target: float) -> float:
    """Map a setpoint in [MIN_TEMP, MAX_TEMP] onto the dial's angle range."""
    frac = (target - MIN_TEMP) / (MAX_TEMP - MIN_TEMP)
    return MIN_ANGLE + frac * (MAX_ANGLE - MIN_ANGLE)


def _read_temp():
    try:
        return sensor.get_temperature()
    except Exception:  # sensor not ready yet; the page retries on its next poll
        return None


def _state():
    return {
        "temp": _read_temp(),
        "target": _target_temp,
        "power": _power_on,
        "position": servo.current_position(),
        "min_temp": MIN_TEMP,
        "max_temp": MAX_TEMP,
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/state")
def get_state():
    return jsonify(_state())


@app.post("/state")
def post_state():
    global _power_on, _target_temp
    body = request.get_json(silent=True) or {}

    if "target" in body:
        try:
            target = float(body["target"])
        except (TypeError, ValueError):
            return jsonify({"error": "'target' must be a number"}), 400
        if not MIN_TEMP <= target <= MAX_TEMP:
            return jsonify({"error": f"'target' must be between {MIN_TEMP} and {MAX_TEMP}"}), 400
        _target_temp = target

    if "power" in body:
        if not isinstance(body["power"], bool):
            return jsonify({"error": "'power' must be a boolean"}), 400
        _power_on = body["power"]

    with _servo_lock:
        servo.move_to(_angle_for(_target_temp) if _power_on else OFF_ANGLE)

    return jsonify(_state())


@app.get("/position")
def get_position():
    return jsonify({"position": servo.current_position()})


@app.post("/rotate")
def post_rotate():
    body = request.get_json(silent=True) or {}
    try:
        degrees = float(body["degrees"])
        direction = str(body["direction"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "JSON body must contain numeric 'degrees' and string 'direction'"}), 400

    with _servo_lock:
        try:
            new_position = servo.rotate(degrees, direction)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    return jsonify({"position": new_position})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
