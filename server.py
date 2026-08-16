import time
from threading import Lock, Thread

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


CYCLE_MODE = "LO_COOL"
_cycle_on = False
_cycle_on_minutes = 60.0
_cycle_off_minutes = 60.0
_cycle_deadline = 0


def set_mode(mode: str) -> None:
    global _cur_mode
    with _servo_lock:
        servo.move_to(SETTING_TO_ANGLE_MAP[mode])
        _cur_mode = mode


def _cycle_minutes_for(mode: str) -> float:
    return _cycle_on_minutes if mode == CYCLE_MODE else _cycle_off_minutes


def set_cycle(isOn: bool, on_minutes: float, off_minutes: float):
    global _cycle_on_minutes, _cycle_off_minutes, _cycle_deadline, _cycle_on
    
    prev_cycle_on = _cycle_on
    _cycle_on = isOn
    _cycle_on_minutes = on_minutes
    _cycle_off_minutes = off_minutes

    if not isOn:
        _cycle_deadline = 0
        return

    if not prev_cycle_on:
        set_mode(CYCLE_MODE)
    _cycle_deadline = time.monotonic() + _cycle_minutes_for(CYCLE_MODE) * 60


def advance_cycle() -> None:
    global _cur_mode, _cycle_deadline
    with _servo_lock:
        next_mode = "OFF" if _cur_mode == CYCLE_MODE else CYCLE_MODE
        _cycle_deadline = time.monotonic() + _cycle_minutes_for(next_mode) * 60
        servo.move_to(SETTING_TO_ANGLE_MAP[next_mode])
        _cur_mode = next_mode


def cycle_worker() -> None:
    while True:
        time.sleep(5)

        remaining = _cycle_deadline - time.monotonic()
        if remaining > 0:
            continue

        if _cycle_on:
            advance_cycle()


def _state():
    cycle = {
        "on": _cycle_on,
        "on_minutes": _cycle_on_minutes,
        "off_minutes": _cycle_off_minutes,
        "next_switch_in": max(0, round(_cycle_deadline - time.monotonic())) if _cycle_on else None,
        "mode": CYCLE_MODE,
    }
    state = {
        "temp": thermometer.get_temp(),
        "target": _target_temp,
        "position": servo.current_position(),
        "mode": _cur_mode,
        "cycle": cycle,
    }
    print(state)
    return state


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/state")
def get_state():
    return jsonify(_state())


@app.post("/state")
def post_state():
    global _target_temp, CYCLE_MODE
    body = request.get_json(silent=True) or {}

    print(body)

    if "target" in body:
        target = float(body["target"])
        _target_temp = target

    if "cycle" in body:
        cycle = body["cycle"]
        isOn = bool(cycle["on"])
        on_minutes = float(cycle["on_minutes"])
        off_minutes = float(cycle["off_minutes"])
        set_cycle(isOn, on_minutes, off_minutes)

    if body.get("cycle_now"):
        if not _cycle_on:
            return jsonify({"error": "cycle is not running"}), 400
        advance_cycle()

    if "mode" in body:
        mode = body["mode"]
        if mode not in SETTING_TO_ANGLE_MAP:
            return jsonify({"error": f"unknown mode {mode!r}"}), 400
        if mode != "OFF":
            CYCLE_MODE = mode
        else:
            set_cycle(False, _cycle_on_minutes, _cycle_off_minutes)
        set_mode(mode)

    return jsonify(_state())


if __name__ == "__main__":
    servo.move_to(SETTING_TO_ANGLE_MAP[_cur_mode])
    Thread(target=cycle_worker, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
