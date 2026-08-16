from threading import Lock

from flask import Flask, jsonify, render_template, request

import servo
import thermometer

app = Flask(__name__)
_servo_lock = Lock()  # serialize hardware access across Flask worker threads

_cur_mode = "OFF"

SETTING_TO_ANGLE_MAP = {
    "OFF": 90,
    "EXH": 30,
    "HEAT": -30,
    "LO_COOL": -90,
}

_target_temp = 22.0


def _state():
    return {
        "temp": thermometer.get_temp(),
        "target": _target_temp,
        "position": servo.current_position(),
        "mode": _cur_mode,
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/state")
def get_state():
    return jsonify(_state())


@app.post("/state")
def post_state():
    global _cur_mode, _target_temp
    body = request.get_json(silent=True) or {}

    if "target" in body:
        target = float(body["target"])
        _target_temp = target

    if "mode" in body:
        mode = body["mode"]
        with _servo_lock:
            servo.move_to(SETTING_TO_ANGLE_MAP[mode])
            _cur_mode = mode

    return jsonify(_state())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    servo.move_to(SETTING_TO_ANGLE_MAP[_cur_mode])
