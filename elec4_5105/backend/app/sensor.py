import math
import random
import threading
import time
from statistics import mean, median, pstdev

from .config import get_setting


# ============================================================
# GLOBAL SENSOR STATE
# ============================================================

_tcs_sensor = None
_sensor_lock = threading.RLock()


# ============================================================
# HELPERS
# ============================================================

def _percentile(values, percentile):
    """Return a linearly interpolated percentile without NumPy."""

    if not values:
        return 0.0

    ordered = sorted(float(value) for value in values)

    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * float(percentile) / 100.0
    lower_index = math.floor(position)
    upper_index = math.ceil(position)

    if lower_index == upper_index:
        return ordered[lower_index]

    fraction = position - lower_index

    return (
        ordered[lower_index] * (1.0 - fraction)
        + ordered[upper_index] * fraction
    )


def _normalise_rgb(color):
    r = float(color["r"])
    g = float(color["g"])
    b = float(color["b"])

    total = r + g + b

    if total <= 0:
        return {
            "r": 0.0,
            "g": 0.0,
            "b": 0.0
        }

    return {
        "r": r / total,
        "g": g / total,
        "b": b / total
    }


def _vector_distance(first, second):
    return math.sqrt(
        (first["r"] - second["r"]) ** 2
        + (first["g"] - second["g"]) ** 2
        + (first["b"] - second["b"]) ** 2
    )


# ============================================================
# SIMULATOR
# ============================================================

def read_simulated_color():
    """Return simulated RGB + Clear data."""

    r = random.randint(170, 190)
    g = random.randint(65, 85)
    b = random.randint(45, 65)
    clear = random.randint(120, 160)

    return {
        "r": r,
        "g": g,
        "b": b,
        "clear": clear
    }


# ============================================================
# INITIALISE REAL TCS34725
# ============================================================

def get_tcs34725_sensor():
    """Initialise the TCS34725 once and reuse it."""

    global _tcs_sensor

    if _tcs_sensor is not None:
        return _tcs_sensor

    try:
        import board
        import busio
        import adafruit_tcs34725

    except ImportError as error:
        raise RuntimeError(
            "TCS34725 libraries are not installed."
        ) from error

    try:
        i2c = busio.I2C(
            board.SCL,
            board.SDA
        )

        sensor = adafruit_tcs34725.TCS34725(i2c)

        sensor.integration_time = float(
            get_setting("sensor_integration_time_ms")
        )

        sensor.gain = int(
            get_setting("sensor_gain")
        )

        _tcs_sensor = sensor

    except Exception as error:
        raise RuntimeError(
            "Failed to initialise TCS34725 sensor."
        ) from error

    return _tcs_sensor


# ============================================================
# REAL TCS34725
# ============================================================

def _read_tcs34725_color_unlocked():
    sensor = get_tcs34725_sensor()

    try:
        r, g, b, clear = sensor.color_raw

    except Exception as error:
        raise RuntimeError(
            "Failed to read data from TCS34725 sensor."
        ) from error

    color = {
        "r": int(r),
        "g": int(g),
        "b": int(b),
        "clear": int(clear)
    }

    if any(value < 0 for value in color.values()):
        raise RuntimeError(
            "Invalid TCS34725 sensor data."
        )

    return color


# ============================================================
# MAIN SENSOR INTERFACE
# ============================================================

def _read_color_unlocked():
    sensor_mode = get_setting("sensor_mode")

    if sensor_mode == "simulator":
        return read_simulated_color()

    if sensor_mode == "tcs34725":
        return _read_tcs34725_color_unlocked()

    raise ValueError(
        f"Unsupported sensor mode: {sensor_mode}"
    )


def read_color():
    """Read one colour sample using a shared I2C lock."""

    with _sensor_lock:
        return _read_color_unlocked()


# ============================================================
# AVERAGED REGION MEASUREMENT
# ============================================================

def read_color_average(
    sample_count=20,
    discard_count=3,
    interval_ms=300,
    settle_ms=1000
):
    """
    Measure one fixed sample region repeatedly.

    The white LED must already be on. The first readings are
    discarded so the sensor can respond after the sample moves.
    The returned representative RGB uses channel medians, while
    the uniformity algorithm uses the median normalised vector.
    """

    sample_count = max(1, int(sample_count))
    discard_count = max(0, int(discard_count))
    interval_seconds = max(0.0, float(interval_ms) / 1000.0)
    settle_seconds = max(0.0, float(settle_ms) / 1000.0)

    readings = []

    with _sensor_lock:
        time.sleep(settle_seconds)

        total_count = sample_count + discard_count

        for index in range(total_count):
            color = _read_color_unlocked()

            if index >= discard_count:
                readings.append(color)

            if index < total_count - 1:
                time.sleep(interval_seconds)

    if not readings:
        raise RuntimeError("No sensor readings were collected.")

    representative_color = {
        channel: int(round(median(item[channel] for item in readings)))
        for channel in ("r", "g", "b", "clear")
    }

    normalised_readings = [
        _normalise_rgb(item)
        for item in readings
    ]

    normalised_center = {
        channel: median(item[channel] for item in normalised_readings)
        for channel in ("r", "g", "b")
    }

    center_total = sum(normalised_center.values())

    if center_total > 0:
        normalised_center = {
            channel: value / center_total
            for channel, value in normalised_center.items()
        }

    normalised_distances = [
        _vector_distance(item, normalised_center)
        for item in normalised_readings
    ]

    channel_statistics = {}

    for channel in ("r", "g", "b", "clear"):
        values = [float(item[channel]) for item in readings]
        channel_mean = mean(values)
        channel_std = pstdev(values) if len(values) > 1 else 0.0

        channel_statistics[channel] = {
            "mean": channel_mean,
            "median": median(values),
            "std": channel_std,
            "cv": (
                channel_std / channel_mean
                if channel_mean > 0
                else 0.0
            )
        }

    return {
        "color": representative_color,
        "normalized": normalised_center,
        "repeatability": {
            "normalized_mean_distance": mean(normalised_distances),
            "normalized_p95_distance": _percentile(
                normalised_distances,
                95
            ),
            "normalized_max_distance": max(normalised_distances),
            "clear_cv": channel_statistics["clear"]["cv"],
            "channels": channel_statistics
        },
        "sample_count": len(readings)
    }
