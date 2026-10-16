import threading
import time

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None


PASS_LED_PIN = 17
FAIL_LED_PIN = 27
WHITE_LED_PIN = 18
BUZZER_PIN = 22

_outputs_initialised = False
_output_lock = threading.RLock()


def initialise_outputs():
    """Initialise Raspberry Pi output pins once."""

    global _outputs_initialised

    if GPIO is None or _outputs_initialised:
        return

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(PASS_LED_PIN, GPIO.OUT)
    GPIO.setup(FAIL_LED_PIN, GPIO.OUT)
    GPIO.setup(WHITE_LED_PIN, GPIO.OUT)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)

    GPIO.output(PASS_LED_PIN, GPIO.LOW)
    GPIO.output(FAIL_LED_PIN, GPIO.LOW)
    GPIO.output(WHITE_LED_PIN, GPIO.LOW)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

    _outputs_initialised = True


def set_white_led(enabled: bool):
    """Switch the white illumination LED on or off."""

    with _output_lock:
        initialise_outputs()

        if GPIO is None:
            return

        GPIO.output(
            WHITE_LED_PIN,
            GPIO.HIGH if enabled else GPIO.LOW
        )


def clear_result_outputs():
    """Switch off PASS, FAIL and buzzer outputs."""

    with _output_lock:
        initialise_outputs()

        if GPIO is None:
            return

        GPIO.output(PASS_LED_PIN, GPIO.LOW)
        GPIO.output(FAIL_LED_PIN, GPIO.LOW)
        GPIO.output(BUZZER_PIN, GPIO.LOW)


def indicate_result(status: str, duration_seconds: float = 2.0):
    """Show a short PASS or FAIL indication."""

    with _output_lock:
        initialise_outputs()

        if GPIO is None:
            return

        clear_result_outputs()

        if status == "PASS":
            GPIO.output(PASS_LED_PIN, GPIO.HIGH)

        elif status == "FAIL":
            GPIO.output(FAIL_LED_PIN, GPIO.HIGH)
            GPIO.output(BUZZER_PIN, GPIO.HIGH)

        else:
            return

        try:
            time.sleep(
                max(
                    0.0,
                    float(duration_seconds)
                )
            )

        finally:
            clear_result_outputs()


def all_outputs_off():
    """Switch off illumination, result LEDs and buzzer."""

    with _output_lock:
        initialise_outputs()

        if GPIO is None:
            return

        GPIO.output(PASS_LED_PIN, GPIO.LOW)
        GPIO.output(FAIL_LED_PIN, GPIO.LOW)
        GPIO.output(WHITE_LED_PIN, GPIO.LOW)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
