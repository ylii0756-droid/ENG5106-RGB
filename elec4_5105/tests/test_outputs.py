import time
import RPi.GPIO as GPIO


PASS_LED_PIN = 17
FAIL_LED_PIN = 27
WHITE_LED_PIN = 18
BUZZER_PIN = 22


GPIO.setmode(GPIO.BCM)

GPIO.setup(PASS_LED_PIN, GPIO.OUT)
GPIO.setup(FAIL_LED_PIN, GPIO.OUT)
GPIO.setup(WHITE_LED_PIN, GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)


def all_off():
    GPIO.output(PASS_LED_PIN, GPIO.LOW)
    GPIO.output(FAIL_LED_PIN, GPIO.LOW)
    GPIO.output(WHITE_LED_PIN, GPIO.LOW)
    GPIO.output(BUZZER_PIN, GPIO.LOW)


all_off()


try:

    print("Output test started")


    # =========================================
    # GREEN PASS LED
    # =========================================

    print("1. PASS LED ON")

    GPIO.output(
        PASS_LED_PIN,
        GPIO.HIGH
    )

    time.sleep(2)

    GPIO.output(
        PASS_LED_PIN,
        GPIO.LOW
    )

    print("PASS LED OFF")

    time.sleep(1)


    # =========================================
    # RED FAIL LED
    # =========================================

    print("2. FAIL LED ON")

    GPIO.output(
        FAIL_LED_PIN,
        GPIO.HIGH
    )

    time.sleep(2)

    GPIO.output(
        FAIL_LED_PIN,
        GPIO.LOW
    )

    print("FAIL LED OFF")

    time.sleep(1)


    # =========================================
    # WHITE ILLUMINATION LEDs
    # =========================================

    print("3. WHITE LEDs ON")

    GPIO.output(
        WHITE_LED_PIN,
        GPIO.HIGH
    )

    time.sleep(2)

    GPIO.output(
        WHITE_LED_PIN,
        GPIO.LOW
    )

    print("WHITE LEDs OFF")

    time.sleep(1)


    # =========================================
    # BUZZER
    # =========================================

    print("4. BUZZER ON")

    GPIO.output(
        BUZZER_PIN,
        GPIO.HIGH
    )

    time.sleep(2)

    GPIO.output(
        BUZZER_PIN,
        GPIO.LOW
    )

    print("BUZZER OFF")


    print("Output test finished")


finally:

    all_off()

    GPIO.cleanup()