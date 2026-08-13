from time import sleep

from gpiozero import AngularServo

try:
    from gpiozero.pins.pigpio import PiGPIOFactory
    pin_factory = PiGPIOFactory()
except Exception:
    pin_factory = None  # falls back to software PWM (some jitter, still works)

SERVO_PIN = 18
MIN_PULSE = 0.0005  # 0.5 ms  -> ~0 deg
MAX_PULSE = 0.0025  # 2.5 ms  -> ~180 deg

servo = AngularServo(
    SERVO_PIN,
    min_angle=0,
    max_angle=180,
    min_pulse_width=MIN_PULSE,
    max_pulse_width=MAX_PULSE,
    pin_factory=pin_factory,
)


STEP_DEG = 2.0
STEP_DELAY = 0.01  # ~0.9 s for a full 180 deg sweep
HOME_ANGLE = 90.0
CLOCKWISE = ("clockwise", "cw")
COUNTERCLOCKWISE = ("counterclockwise", "counter-clockwise", "ccw")

# Home the servo on import so the tracked position matches reality.
servo.angle = HOME_ANGLE
sleep(0.5)
_current_angle: float = HOME_ANGLE


def current_position() -> float:
    """Return the servo's last commanded angle in degrees."""
    return _current_angle


def rotate(degrees: float, direction: str) -> float:
    """Rotate by `degrees` in `direction`, clamped to [0, 180]. Returns new angle."""
    global _current_angle
    d = direction.lower()
    if d in CLOCKWISE:
        sign = 1
    elif d in COUNTERCLOCKWISE:
        sign = -1
    else:
        raise ValueError(f"direction must be clockwise or counterclockwise, got {direction!r}")
    if degrees < 0:
        raise ValueError("degrees must be non-negative")

    target = max(0.0, min(180.0, _current_angle + sign * degrees))
    step = STEP_DEG if target > _current_angle else -STEP_DEG
    angle = _current_angle
    while abs(target - angle) > abs(step):
        angle += step
        servo.angle = angle
        sleep(STEP_DELAY)
    servo.angle = target
    sleep(STEP_DELAY)
    _current_angle = target
    return target


def turn_clockwise_180() -> float:
    """Rotate the horn 180 deg clockwise (viewed from the horn side)."""
    return rotate(180, "clockwise")


def turn_counterclockwise_180() -> float:
    """Rotate the horn 180 deg counter-clockwise."""
    return rotate(180, "counterclockwise")


if __name__ == "__main__":
    try:
        while True:
            turn_clockwise_180()
            sleep(0.5)
            turn_counterclockwise_180()
            sleep(0.5)
    except KeyboardInterrupt:
        servo.angle = HOME_ANGLE
        sleep(0.5)
        servo.detach()
