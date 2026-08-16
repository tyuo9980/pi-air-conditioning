from threading import Lock

from flask import Flask, jsonify, render_template, request

import servo
import thermometer

app = Flask(__name__)
_servo_lock = Lock()  # serialize hardware access across Flask worker threads


SETTING_TO_ANGLE_MAP = {
    "OFF": 90,
    "EXH": 30,
    "HEAT": -30,
    "LO_COOL": -90,
}

target_temp = 22.0


def _state():
    return {
        "temp": thermometer.get_temp(),
        "target": target_temp,
        "position": servo.current_position(),
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/state")
def get_state():
    return jsonify(_state())


@app.post("/state")
def post_state():
    global _target_temp
    body = request.get_json(silent=True) or {}

    if "target" in body:
        target = float(body["target"])
        _target_temp = target

    if "fan" in body:
        setting = body["fan"]
        with _servo_lock:
            servo.move_to(SETTING_TO_ANGLE_MAP[setting])

    return jsonify(_state())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
