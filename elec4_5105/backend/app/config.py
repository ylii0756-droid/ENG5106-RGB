import json
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
EXAMPLE_SETTINGS_FILE = CONFIG_DIR / "settings.example.json"


# ============================================================
# DEFAULT SETTINGS
# ============================================================

DEFAULT_SETTINGS = {
    # Existing single-point reference comparison
    "threshold": 0.045,
    "sampling_count": 20,

    # Shared acquisition timing
    "measurement_interval_ms": 300,
    "live_update_interval_ms": 1000,

    # Real TCS34725 settings
    "sensor_mode": "tcs34725",
    "sensor_integration_time_ms": 200,
    "sensor_gain": 16,

    # Nine-point (3 x 3) rectangular-sample uniformity workflow
    "uniformity_region_ids": [
        "P1",
        "P2",
        "P3",
        "P4",
        "P5",
        "P6",
        "P7",
        "P8",
        "P9"
    ],
    "uniformity_sample_count": 20,
    "uniformity_discard_count": 3,
    "illumination_warmup_ms": 8000,
    "position_settle_ms": 1000,

    # Provisional thresholds estimated from the current
    # single-region diagnostic data. Recalibrate later.
    "uniformity_color_threshold": 0.030,
    "uniformity_repeatability_threshold": 0.020,
    "uniformity_clear_threshold": 0.300,
    "use_clear_for_decision": False,

    # Result indication duration
    "result_indication_seconds": 2.0
}


# ============================================================
# INITIALISE CONFIG
# ============================================================

def initialise_config():
    """Make sure the config directory and settings file exist."""

    CONFIG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not SETTINGS_FILE.exists():
        with open(
            SETTINGS_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                DEFAULT_SETTINGS,
                file,
                indent=4
            )


# ============================================================
# LOAD SETTINGS
# ============================================================

def load_settings():
    """Load system settings from settings.json."""

    initialise_config()

    with open(
        SETTINGS_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        settings = json.load(file)

    merged_settings = DEFAULT_SETTINGS.copy()
    merged_settings.update(settings)

    return merged_settings


# ============================================================
# SAVE SETTINGS
# ============================================================

def save_settings(settings):
    """Save system settings to settings.json."""

    initialise_config()

    merged_settings = DEFAULT_SETTINGS.copy()
    merged_settings.update(settings)

    with open(
        SETTINGS_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            merged_settings,
            file,
            indent=4
        )

    return merged_settings


# ============================================================
# GET INDIVIDUAL SETTING
# ============================================================

def get_setting(name):
    """Return one setting by name."""

    settings = load_settings()
    return settings.get(name)
