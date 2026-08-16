from time import sleep

from gpiozero import AngularServo

# Setup servo on GPIO 18 with standard pulse widths
servo = AngularServo(18, min_pulse_width=0.0006, max_pulse_width=0.0024)

servo.angle = 0

def current_position() -> float:
    """Return the servo's last commanded angle in degrees."""
    return servo.angle

def move_to(angle: float) -> float:
    servo.angle = angle
    