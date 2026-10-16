import time
from statistics import mean, pstdev

import board
import busio
import adafruit_tcs34725
import RPi.GPIO as GPIO


# ============================================================
# SETTINGS
# ============================================================

WHITE_LED_PIN = 18

INTEGRATION_TIME_MS = 200
GAIN = 16

DARK_SAMPLE_COUNT = 10
LIGHT_SAMPLE_COUNT = 30


# ============================================================
# INITIALISE GPIO
# ============================================================

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(
    WHITE_LED_PIN,
    GPIO.OUT,
    initial=GPIO.LOW
)


# ============================================================
# INITIALISE SENSOR
# ============================================================

i2c = busio.I2C(
    board.SCL,
    board.SDA
)

sensor = adafruit_tcs34725.TCS34725(
    i2c
)

sensor.integration_time = INTEGRATION_TIME_MS
sensor.gain = GAIN


# ============================================================
# MEASUREMENT FUNCTION
# ============================================================

def read_block(label, sample_count):
    readings = []

    print()
    print("=" * 60)
    print(label)
    print("=" * 60)

    for index in range(sample_count):
        r, g, b, clear = sensor.color_raw

        total_rgb = r + g + b

        if total_rgb > 0:
            rn = r / total_rgb
            gn = g / total_rgb
            bn = b / total_rgb
        else:
            rn = 0.0
            gn = 0.0
            bn = 0.0

        reading = {
            "r": int(r),
            "g": int(g),
            "b": int(b),
            "clear": int(clear),
            "rn": rn,
            "gn": gn,
            "bn": bn
        }

        readings.append(reading)

        print(
            f"{index + 1:02d}: "
            f"R={r:5d}  "
            f"G={g:5d}  "
            f"B={b:5d}  "
            f"C={clear:5d}  "
            f"| rn={rn:.4f} "
            f"gn={gn:.4f} "
            f"bn={bn:.4f}"
        )

        time.sleep(0.3)

    return readings


def print_summary(label, readings):
    print()
    print(f"{label} SUMMARY")

    for channel in ("r", "g", "b", "clear"):
        values = [
            float(item[channel])
            for item in readings
        ]

        channel_mean = mean(values)

        channel_std = (
            pstdev(values)
            if len(values) > 1
            else 0.0
        )

        channel_cv = (
            channel_std / channel_mean * 100
            if channel_mean > 0
            else 0.0
        )

        print(
            f"{channel.upper():5s}: "
            f"mean={channel_mean:8.2f}, "
            f"std={channel_std:8.2f}, "
            f"CV={channel_cv:6.2f}%"
        )


# ============================================================
# RUN TEST
# ============================================================

try:
    print("TCS34725 illumination diagnostic")
    print(
        f"Integration time: "
        f"{INTEGRATION_TIME_MS} ms"
    )
    print(f"Gain: {GAIN}x")

    # ----------------------------------------
    # DARK TEST
    # ----------------------------------------

    GPIO.output(
        WHITE_LED_PIN,
        GPIO.LOW
    )

    print()
    print("White LED OFF")
    print("Keep the enclosure closed.")

    time.sleep(1.0)

    dark_readings = read_block(
        "DARK / WHITE LED OFF",
        DARK_SAMPLE_COUNT
    )

    # ----------------------------------------
    # ILLUMINATED TEST
    # ----------------------------------------

    GPIO.output(
        WHITE_LED_PIN,
        GPIO.HIGH
    )

    print()
    print("White LED ON")
    print(
        "Keep one sample region fixed "
        "under the sensor."
    )

    time.sleep(1.0)

    light_readings = read_block(
        "SAMPLE / WHITE LED ON",
        LIGHT_SAMPLE_COUNT
    )

    # ----------------------------------------
    # RESULTS
    # ----------------------------------------

    print()
    print("=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)

    print_summary(
        "DARK",
        dark_readings
    )

    print_summary(
        "LED ON",
        light_readings
    )

    dark_clear_mean = mean(
        item["clear"]
        for item in dark_readings
    )

    light_clear_mean = mean(
        item["clear"]
        for item in light_readings
    )

    print()

    if dark_clear_mean > 0:
        print(
            "Clear-channel light/dark ratio: "
            f"{light_clear_mean / dark_clear_mean:.2f}"
        )
    else:
        print(
            "Clear-channel light/dark ratio: "
            "dark mean is zero"
        )

finally:
    GPIO.output(
        WHITE_LED_PIN,
        GPIO.LOW
    )

    GPIO.cleanup()

    print()
    print("White LED OFF")
    print("GPIO cleanup completed.")