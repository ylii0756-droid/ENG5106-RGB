import csv
import json
import threading
from datetime import datetime
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
REFERENCE_FILE = DATA_DIR / "reference.json"
MEASUREMENTS_FILE = DATA_DIR / "measurements.csv"
UNIFORMITY_RESULTS_FILE = DATA_DIR / "uniformity_results.jsonl"
NINE_POINT_RESULTS_CSV_FILE = DATA_DIR / "nine_point_uniformity_results.csv"


# ============================================================
# STORAGE LOCK
# ============================================================

_STORAGE_LOCK = threading.RLock()


# ============================================================
# NINE-POINT CSV FORMAT
# ============================================================

NINE_POINT_IDS = {
    f"P{index}"
    for index in range(1, 10)
}

NINE_POINT_CSV_FIELDS = [
    "test_index",
    "sheet_id",
    "sheet_timestamp",
    "point_id",
    "point_timestamp",
    "r",
    "g",
    "b",
    "clear",
    "rn",
    "gn",
    "bn",
    "sample_count",
    "repeatability_mean_distance",
    "repeatability_p95_distance",
    "repeatability_max_distance",
    "point_clear_cv",
    "overall_result",
    "color_status",
    "repeatability_status",
    "clear_status",
    "clear_used_for_decision",
    "max_pair_distance",
    "worst_pair",
    "max_repeatability_p95_distance",
    "mean_clear",
    "sheet_clear_cv",
    "max_clear_deviation",
    "color_threshold",
    "repeatability_threshold",
    "clear_threshold",
    "threshold_basis",
]


# ============================================================
# INITIALISE STORAGE
# ============================================================

def initialise_storage():
    """Make sure all data files exist."""

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not REFERENCE_FILE.exists():
        with open(
            REFERENCE_FILE,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                {"reference": None},
                file,
                indent=4,
            )

    if not MEASUREMENTS_FILE.exists():
        with open(
            MEASUREMENTS_FILE,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.writer(file)
            writer.writerow([
                "sample_id",
                "timestamp",
                "r",
                "g",
                "b",
                "clear",
                "distance",
                "threshold",
                "result",
            ])

    if not UNIFORMITY_RESULTS_FILE.exists():
        UNIFORMITY_RESULTS_FILE.touch()

    if not NINE_POINT_RESULTS_CSV_FILE.exists():
        _write_nine_point_csv(
            records=[],
        )


# ============================================================
# REFERENCE
# ============================================================

def save_reference(reference):
    initialise_storage()

    with open(
        REFERENCE_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {"reference": reference},
            file,
            indent=4,
        )

    return reference


def load_reference():
    initialise_storage()

    with open(
        REFERENCE_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    return data.get("reference")


# ============================================================
# EXISTING SINGLE-POINT MEASUREMENTS
# ============================================================

def save_measurement(
    sample_id,
    color,
    distance,
    threshold,
    result,
):
    initialise_storage()

    timestamp = datetime.now().isoformat(
        timespec="seconds"
    )

    row = [
        sample_id,
        timestamp,
        color.get("r"),
        color.get("g"),
        color.get("b"),
        color.get("clear"),
        round(distance, 6),
        round(threshold, 6),
        result,
    ]

    with open(
        MEASUREMENTS_FILE,
        "a",
        newline="",
        encoding="utf-8",
    ) as file:
        csv.writer(file).writerow(row)

    return {
        "sample_id": sample_id,
        "timestamp": timestamp,
        "r": color.get("r"),
        "g": color.get("g"),
        "b": color.get("b"),
        "clear": color.get("clear"),
        "distance": distance,
        "threshold": threshold,
        "result": result,
    }


def load_measurements(limit=20):
    initialise_storage()
    records = []

    with open(
        MEASUREMENTS_FILE,
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            records.append({
                "sample_id": row["sample_id"],
                "timestamp": row["timestamp"],
                "r": int(row["r"]),
                "g": int(row["g"]),
                "b": int(row["b"]),
                "clear": (
                    int(row["clear"])
                    if row.get("clear")
                    else None
                ),
                "distance": float(row["distance"]),
                "threshold": float(row["threshold"]),
                "result": row["result"],
            })

    return records[-limit:][::-1]


# ============================================================
# MULTI-POINT UNIFORMITY RESULTS
# ============================================================

def _load_all_uniformity_results_unlocked():
    """Load every valid JSON Lines uniformity result."""

    initialise_storage()
    records = []

    with open(
        UNIFORMITY_RESULTS_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        for line_number, line in enumerate(
            file,
            start=1,
        ):
            line = line.strip()

            if not line:
                continue

            try:
                records.append(
                    json.loads(line)
                )
            except json.JSONDecodeError:
                # Preserve access to the remaining valid records even if
                # one line is incomplete or damaged.
                print(
                    "Warning: skipped invalid uniformity JSONL line "
                    f"{line_number}."
                )

    return records


def load_uniformity_results(limit=20):
    """Load recent multi-point uniformity results, newest first."""

    with _STORAGE_LOCK:
        records = _load_all_uniformity_results_unlocked()

    if limit is None:
        return records[::-1]

    limit = max(
        1,
        int(limit),
    )

    return records[-limit:][::-1]


def _is_complete_nine_point_result(record):
    """Return True only for completed P1-P9 test records."""

    regions = record.get("regions") or []

    point_ids = {
        str(region.get("region_id", "")).upper()
        for region in regions
    }

    return (
        len(regions) == 9
        and point_ids == NINE_POINT_IDS
    )


def _point_sort_key(region):
    point_id = str(
        region.get("region_id", "")
    ).upper()

    try:
        return int(
            point_id.removeprefix("P")
        )
    except ValueError:
        return 999


def _flatten_nine_point_record(
    record,
    test_index,
):
    """Convert one completed nine-point test to nine CSV rows."""

    uniformity = record.get("uniformity") or {}
    thresholds = uniformity.get("thresholds") or {}
    worst_pair = uniformity.get("worst_pair") or {}

    worst_pair_text = ""

    if (
        worst_pair.get("first")
        and worst_pair.get("second")
    ):
        worst_pair_text = (
            f"{worst_pair['first']}-"
            f"{worst_pair['second']}"
        )

    rows = []

    for point in sorted(
        record.get("regions") or [],
        key=_point_sort_key,
    ):
        normalized = point.get("normalized") or {}
        repeatability = point.get("repeatability") or {}

        rows.append({
            "test_index": test_index,
            "sheet_id": record.get("sheet_id"),
            "sheet_timestamp": record.get("timestamp"),
            "point_id": point.get("region_id"),
            "point_timestamp": point.get("timestamp"),
            "r": point.get("r"),
            "g": point.get("g"),
            "b": point.get("b"),
            "clear": point.get("clear"),
            "rn": normalized.get("r"),
            "gn": normalized.get("g"),
            "bn": normalized.get("b"),
            "sample_count": point.get("sample_count"),
            "repeatability_mean_distance": repeatability.get(
                "normalized_mean_distance"
            ),
            "repeatability_p95_distance": repeatability.get(
                "normalized_p95_distance"
            ),
            "repeatability_max_distance": repeatability.get(
                "normalized_max_distance"
            ),
            "point_clear_cv": repeatability.get("clear_cv"),
            "overall_result": uniformity.get("status"),
            "color_status": uniformity.get("color_status"),
            "repeatability_status": uniformity.get(
                "repeatability_status"
            ),
            "clear_status": uniformity.get("clear_status"),
            "clear_used_for_decision": uniformity.get(
                "clear_used_for_decision"
            ),
            "max_pair_distance": uniformity.get(
                "max_pair_distance"
            ),
            "worst_pair": worst_pair_text,
            "max_repeatability_p95_distance": uniformity.get(
                "max_repeatability_p95_distance"
            ),
            "mean_clear": uniformity.get("mean_clear"),
            "sheet_clear_cv": uniformity.get("clear_cv"),
            "max_clear_deviation": uniformity.get(
                "max_clear_deviation"
            ),
            "color_threshold": thresholds.get("color"),
            "repeatability_threshold": thresholds.get(
                "repeatability"
            ),
            "clear_threshold": thresholds.get("clear"),
            "threshold_basis": uniformity.get("threshold_basis"),
        })

    return rows


def _write_nine_point_csv(records):
    """Atomically rebuild the aggregate nine-point CSV file."""

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = (
        NINE_POINT_RESULTS_CSV_FILE
        .with_suffix(".csv.tmp")
    )

    with open(
        temporary_file,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=NINE_POINT_CSV_FIELDS,
        )

        writer.writeheader()

        for test_index, record in enumerate(
            records,
            start=1,
        ):
            writer.writerows(
                _flatten_nine_point_record(
                    record,
                    test_index,
                )
            )

    temporary_file.replace(
        NINE_POINT_RESULTS_CSV_FILE
    )


def rebuild_nine_point_results_csv():
    """
    Rebuild one CSV containing every completed P1-P9 test.

    Each completed sheet contributes nine rows. Older five-region
    records are deliberately excluded from this nine-point export.
    """

    with _STORAGE_LOCK:
        all_records = _load_all_uniformity_results_unlocked()

        nine_point_records = [
            record
            for record in all_records
            if _is_complete_nine_point_result(record)
        ]

        _write_nine_point_csv(
            nine_point_records
        )

    return {
        "path": NINE_POINT_RESULTS_CSV_FILE,
        "test_count": len(nine_point_records),
        "point_row_count": len(nine_point_records) * 9,
    }


def get_nine_point_export_info():
    """Return persistent export availability and record counts."""

    with _STORAGE_LOCK:
        records = _load_all_uniformity_results_unlocked()

        test_count = sum(
            1
            for record in records
            if _is_complete_nine_point_result(record)
        )

    return {
        "available": test_count > 0,
        "test_count": test_count,
        "point_row_count": test_count * 9,
        "filename": NINE_POINT_RESULTS_CSV_FILE.name,
    }


def save_uniformity_result(
    sheet_id,
    regions,
    uniformity,
):
    """
    Persist one completed multi-point result.

    The JSON Lines file remains the lossless source record. After
    every completed test, the independent aggregate nine-point CSV is
    rebuilt automatically, so export never depends on a single-point
    Measure Sample operation or the browser's in-memory history.
    """

    initialise_storage()

    record = {
        "sheet_id": sheet_id,
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "regions": regions,
        "uniformity": uniformity,
    }

    with _STORAGE_LOCK:
        with open(
            UNIFORMITY_RESULTS_FILE,
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

        # Keep the persistent CSV in sync after every completed test.
        all_records = _load_all_uniformity_results_unlocked()
        nine_point_records = [
            item
            for item in all_records
            if _is_complete_nine_point_result(item)
        ]
        _write_nine_point_csv(
            nine_point_records
        )

    return record
