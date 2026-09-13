import time
from threading import Lock, Thread

from flask import Flask, jsonify, render_template, request

import servo
import thermometer

app = Flask(__name__)
_servo_lock = Lock()  # serialize hardware access across Flask worker threads

# The AC has one physical dial. These are its positions and the servo angle for each.
DIAL_TO_ANGLE_MAP = {
    "OFF": 90,
    "COOL": -90,
    "HEAT": -30,
}
SETTINGS = ("COOL", "HEAT")
MODES = ("OFF", "CONSTANT", "CYCLE", "AUTO")

_dial = "OFF"          # where the dial currently is
_setting = "COOL"      # which setting the unit runs when it is on
_mode = "OFF"          # how it runs: OFF, CONSTANT, CYCLE (timed), AUTO (thermostat)

_target_temp = 21.0
_target_sway = 2.0     # hysteresis band around the target so AUTO does not chatter

_cycle_on_minutes = 15
_cycle_off_minutes = 45
_cycle_deadline = 0.0  # monotonic time of the next CYCLE switch


def decide_dial(mode, setting, dial, temp, target, sway, cycle_deadline, now):
    """Pure rule for where the dial should go next; None means leave it alone.

    - OFF: dial at OFF.
    - CONSTANT: dial at the setting.
    - CYCLE: alternate setting and OFF; switch once `now` reaches `cycle_deadline`.
    - AUTO: thermostat. COOL turns on at temp >= target and off below target - sway;
      HEAT turns on at temp <= target and off above target + sway. A missing
      reading (None) leaves the dial alone.
    In every mode a dial that is neither OFF nor the setting is corrected.
    """
    if mode == "OFF":
        return None if dial == "OFF" else "OFF"

    if mode == "CONSTANT":
        return None if dial == setting else setting

    if mode == "CYCLE":
        on = dial != "OFF"
        if now >= cycle_deadline:
            return "OFF" if on else setting
        if on and dial != setting:
            return setting
        return None

    if mode == "AUTO":
        if dial not in ("OFF", setting):
            return "OFF"  # never keep running the other setting
        if temp is None:
            return None
        if setting == "COOL":
            want_on = temp >= target
            want_off = temp < target - sway
        else:
            want_on = temp <= target
            want_off = temp > target + sway
        if want_on and dial != setting:
            return setting
        if want_off and dial != "OFF":
            return "OFF"
        return None

    raise ValueError(f"unknown mode {mode!r}")


def _cycle_minutes_for(dial: str) -> float:
    return _cycle_off_minutes if dial == "OFF" else _cycle_on_minutes


def _read_temp():
    try:
        return thermometer.get_temp()
    except Exception as e:  # a flaky 1-wire read must not move the dial or kill the loop
        print("temp read failed:", e)
        return None


def _move_dial(dial: str) -> None:
    """Caller must hold _servo_lock."""
    global _dial
    if dial == _dial:
        return
    servo.move_to(DIAL_TO_ANGLE_MAP[dial])
    _dial = dial


def tick() -> None:
    """Apply the current mode to the dial once. Called by the worker and after every change."""
    global _cycle_deadline
    temp = _read_temp() if _mode == "AUTO" else None
    with _servo_lock:
        now = time.monotonic()
        next_dial = decide_dial(_mode, _setting, _dial, temp, _target_temp, _target_sway,
                                _cycle_deadline, now)
        if _mode == "CYCLE" and now >= _cycle_deadline:
            _cycle_deadline = now + _cycle_minutes_for(next_dial or _dial) * 60
        if next_dial is not None:
            _move_dial(next_dial)


def set_setting(setting: str) -> None:
    global _setting
    _setting = setting
    tick()  # a running mode moves the dial straight away


def set_mode(mode: str) -> None:
    global _mode, _cycle_deadline
    prev = _mode
    _mode = mode
    if mode == "CYCLE" and prev != "CYCLE":
        # a fresh cycle starts with its on phase
        with _servo_lock:
            _move_dial(_setting)
            _cycle_deadline = time.monotonic() + _cycle_on_minutes * 60
    tick()


def set_cycle_minutes(on_minutes: float, off_minutes: float) -> None:
    global _cycle_on_minutes, _cycle_off_minutes
    _cycle_on_minutes = on_minutes
    _cycle_off_minutes = off_minutes


def advance_cycle() -> None:
    """'Cycle now': switch phase immediately and restart the timer."""
    global _cycle_deadline
    with _servo_lock:
        _cycle_deadline = 0
        now = time.monotonic()
        next_dial = decide_dial("CYCLE", _setting, _dial, None, _target_temp, _target_sway,
                                _cycle_deadline, now)
        _cycle_deadline = now + _cycle_minutes_for(next_dial) * 60
        _move_dial(next_dial)


def worker() -> None:
    while True:
        time.sleep(5)
        if _mode in ("CYCLE", "AUTO"):
            tick()


def _state():
    cycle = {
        "on_minutes": _cycle_on_minutes,
        "off_minutes": _cycle_off_minutes,
        "next_switch_in": max(0, round(_cycle_deadline - time.monotonic())) if _mode == "CYCLE" else None,
    }
    state = {
        "temp": _read_temp(),
        "target": _target_temp,
        "sway": _target_sway,
        "position": servo.current_position(),
        "dial": _dial,
        "setting": _setting,
        "mode": _mode,
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
    global _target_temp
    body = request.get_json(silent=True) or {}

    print(body)

    if "target" in body:
        _target_temp = float(body["target"])

    if "cycle" in body:
        cycle = body["cycle"]
        set_cycle_minutes(float(cycle["on_minutes"]), float(cycle["off_minutes"]))

    if "setting" in body:
        setting = body["setting"]
        if setting not in SETTINGS:
            return jsonify({"error": f"unknown setting {setting!r}"}), 400
        set_setting(setting)

    if "mode" in body:
        mode = body["mode"]
        if mode not in MODES:
            return jsonify({"error": f"unknown mode {mode!r}"}), 400
        set_mode(mode)

    if body.get("cycle_now"):
        if _mode != "CYCLE":
            return jsonify({"error": "cycle is not running"}), 400
        advance_cycle()

    return jsonify(_state())


if __name__ == "__main__":
    servo.move_to(DIAL_TO_ANGLE_MAP[_dial])
    Thread(target=worker, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
