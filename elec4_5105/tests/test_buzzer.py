import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(22, GPIO.OUT)

GPIO.output(22, GPIO.HIGH)

print("GPIO22 HIGH for 30 seconds")
time.sleep(30)

GPIO.output(22, GPIO.LOW)
GPIO.cleanup()