from threading import Lock

from flask import Flask, jsonify, request

import servo

from w1thermsensor import W1ThermSensor

app = Flask(__name__)
_servo_lock = Lock()  # serialize hardware access across Flask worker threads

sensor = W1ThermSensor()


@app.get("/")
def index():
    temp = sensor.get_temperature()
    return jsonify({"temp": temp})


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
