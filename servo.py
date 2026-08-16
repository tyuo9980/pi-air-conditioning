from time import sleep

from gpiozero import AngularServo

# Setup servo on GPIO 18 with standard pulse widths
servo = AngularServo(18, min_pulse_width=0.0006, max_pulse_width=0.0024)

def current_position() -> float:
    return servo.angle

def move_to(angle: float) -> float:
    servo.angle = angle
    sleep(2)
    print(servo.angle)
    return servo.angle
    

#move_to(-90)
#move_to(90)

