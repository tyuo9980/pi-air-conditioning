from w1thermsensor import W1ThermSensor

sensor = W1ThermSensor()

def get_temp():
    return sensor.get_temperature()

def probe_loop():
    while True:
        print(get_temp())