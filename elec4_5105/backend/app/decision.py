import math
from itertools import combinations
from statistics import mean, pstdev

from .config import get_setting
from .storage import (
    load_reference,
    save_reference
)


# ============================================================
# SET REFERENCE
# ============================================================

def set_reference(color):
    """Save a new reference colour."""

    reference = {
        "r": int(color["r"]),
        "g": int(color["g"]),
        "b": int(color["b"])
    }

    if color.get("clear") is not None:
        reference["clear"] = int(color["clear"])

    save_reference(reference)
    return reference


# ============================================================
# GET REFERENCE
# ============================================================

def get_reference():
    """Return the currently stored reference colour."""

    return load_reference()


# ============================================================
# RGB NORMALISATION
# ============================================================

def normalize_rgb(color):
    """Normalise RGB values using R + G + B."""

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


# ============================================================
# RGB DISTANCE
# ============================================================

def _vector_distance(first, second):
    return math.sqrt(
        (first["r"] - second["r"]) ** 2
        + (first["g"] - second["g"]) ** 2
        + (first["b"] - second["b"]) ** 2
    )


def calculate_rgb_distance(color, reference):
    """Euclidean distance between normalised RGB vectors."""

    return _vector_distance(
        normalize_rgb(color),
        normalize_rgb(reference)
    )


# ============================================================
# EXISTING SINGLE-POINT QUALITY DECISION
# ============================================================

def check_quality(color):
    """Compare one measured colour with the stored reference."""

    reference = get_reference()
    threshold = float(get_setting("threshold"))

    if reference is None:
        return {
            "difference": None,
            "threshold": threshold,
            "status": "NO_REFERENCE"
        }

    distance = calculate_rgb_distance(color, reference)

    return {
        "difference": distance,
        "threshold": threshold,
        "status": "PASS" if distance <= threshold else "FAIL"
    }


# ============================================================
# FIVE-REGION COLOUR UNIFORMITY
# ============================================================

def evaluate_uniformity(regions):
    """
    Evaluate spatial colour consistency across sample regions.

    Each region should contain representative raw RGBC values,
    a representative normalised RGB vector and repeatability data.
    """

    if len(regions) < 2:
        raise ValueError(
            "At least two regions are required."
        )

    normalised_regions = {}

    for region in regions:
        region_id = region["region_id"]
        normalised_regions[region_id] = (
            region.get("normalized")
            or normalize_rgb(region)
        )

    sheet_mean_vector = {
        channel: mean(
            vector[channel]
            for vector in normalised_regions.values()
        )
        for channel in ("r", "g", "b")
    }

    region_distances = {
        region_id: _vector_distance(vector, sheet_mean_vector)
        for region_id, vector in normalised_regions.items()
    }

    pair_distances = []

    for (
        (first_id, first_vector),
        (second_id, second_vector)
    ) in combinations(normalised_regions.items(), 2):
        pair_distances.append({
            "first": first_id,
            "second": second_id,
            "distance": _vector_distance(
                first_vector,
                second_vector
            )
        })

    worst_pair = max(
        pair_distances,
        key=lambda item: item["distance"]
    )

    clear_values = [
        float(region["clear"])
        for region in regions
    ]

    mean_clear = mean(clear_values)
    clear_std = pstdev(clear_values) if len(clear_values) > 1 else 0.0
    clear_cv = clear_std / mean_clear if mean_clear > 0 else 0.0
    max_clear_deviation = (
        max(abs(value - mean_clear) / mean_clear for value in clear_values)
        if mean_clear > 0
        else 0.0
    )

    repeatability_values = [
        float(
            region["repeatability"]["normalized_p95_distance"]
        )
        for region in regions
    ]

    max_repeatability = max(repeatability_values)

    color_threshold = float(
        get_setting("uniformity_color_threshold")
    )
    repeatability_threshold = float(
        get_setting("uniformity_repeatability_threshold")
    )
    clear_threshold = float(
        get_setting("uniformity_clear_threshold")
    )
    use_clear_for_decision = bool(
        get_setting("use_clear_for_decision")
    )

    color_status = (
        "PASS"
        if worst_pair["distance"] <= color_threshold
        else "FAIL"
    )

    repeatability_status = (
        "PASS"
        if max_repeatability <= repeatability_threshold
        else "FAIL"
    )

    clear_status = (
        "PASS"
        if max_clear_deviation <= clear_threshold
        else "WARN"
    )

    overall_pass = (
        color_status == "PASS"
        and repeatability_status == "PASS"
        and (
            not use_clear_for_decision
            or clear_status == "PASS"
        )
    )

    sheet_mean_raw = {
        channel: mean(float(region[channel]) for region in regions)
        for channel in ("r", "g", "b", "clear")
    }

    return {
        "status": "PASS" if overall_pass else "FAIL",
        "color_status": color_status,
        "repeatability_status": repeatability_status,
        "clear_status": clear_status,
        "clear_used_for_decision": use_clear_for_decision,
        "threshold_basis": "provisional_from_current_single_region_diagnostic",
        "region_count": len(regions),
        "sheet_mean_raw": sheet_mean_raw,
        "sheet_mean_normalized_rgb": sheet_mean_vector,
        "region_distances_to_sheet_mean": region_distances,
        "pair_distances": pair_distances,
        "max_pair_distance": worst_pair["distance"],
        "worst_pair": {
            "first": worst_pair["first"],
            "second": worst_pair["second"]
        },
        "max_repeatability_p95_distance": max_repeatability,
        "mean_clear": mean_clear,
        "clear_cv": clear_cv,
        "max_clear_deviation": max_clear_deviation,
        "thresholds": {
            "color": color_threshold,
            "repeatability": repeatability_threshold,
            "clear": clear_threshold
        }
    }
