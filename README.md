# Fixing my shitty AC unit so I can get some sleep

MG995 servo sweep on Raspberry Pi Zero 2 W.

Wiring:
    Servo signal (orange/yellow) -> GPIO18 (pin 12)
    Servo V+   (red)             -> external 5-6V supply (NOT the Pi's 5V rail; MG995 stall is ~1A+)
    Servo GND  (brown/black)     -> external supply GND *and* Pi GND (common ground)
