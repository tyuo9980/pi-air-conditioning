from time import sleep

from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory

factory = PiGPIOFactory()

servo = AngularServo(
    18,
    min_angle=-90,
    max_angle=90,
    min_pulse_width=0.0005,
    max_pulse_width=0.00245,
    pin_factory=factory
)

def current_position() -> int | None:
    # None until the servo has been driven to an angle; otherwise rounds to the nearest 10
    angle = servo.angle
    if angle is None:
        return None
    return int(round(angle, -1))

def move_to(angle: float) -> float:
    print("set: ", angle)
    servo.angle = angle
    sleep(1)
    print("actual: ", servo.angle)
    return servo.angle

def sweep():
    angle = -90
    while angle >= -90 and angle <= 90:
        move_to(angle)
        angle += 5

