import time

import board
import busio
import adafruit_tcs34725


# ============================================================
# TCS34725 TEST
# ============================================================

print("Starting TCS34725 test...")


i2c = busio.I2C(
    board.SCL,
    board.SDA
)


sensor = adafruit_tcs34725.TCS34725(
    i2c
)


print("TCS34725 connected.")
print("Press Ctrl+C to stop.")
print()


try:

    while True:

        r, g, b, clear = sensor.color_raw

        print(
            f"R={r:5d}  "
            f"G={g:5d}  "
            f"B={b:5d}  "
            f"C={clear:5d}"
        )

        time.sleep(0.5)


except KeyboardInterrupt:

    print()
    print("TCS34725 test stopped.")