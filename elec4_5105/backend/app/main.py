import threading
import time
from datetime import datetime
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .config import load_settings, save_settings
from .decision import (
    check_quality,
    evaluate_uniformity,
    get_reference,
    normalize_rgb,
    set_reference,
)
from .outputs import (
    all_outputs_off,
    clear_result_outputs,
    indicate_result,
    set_white_led,
)
from .schemas import ColorData
from .sensor import (
    read_color,
    read_color_average,
)
from .storage import (
    get_nine_point_export_info,
    load_measurements,
    load_uniformity_results,
    rebuild_nine_point_results_csv,
    save_measurement,
    save_uniformity_result,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="ENG5105 RGB Quality Inspection System",
    description="Raspberry Pi colour quality inspection prototype",
    version="2.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MULTI-POINT UNIFORMITY SESSION
# ============================================================

_uniformity_lock = threading.Lock()

uniformity_session = {
    "active": False,
    "sheet_id": None,
    "regions": {},
    "started_at": None,
}


def _session_snapshot():
    """Return the current multi-point test session."""

    return {
        "active": uniformity_session["active"],
        "sheet_id": uniformity_session["sheet_id"],
        "captured_regions": list(
            uniformity_session["regions"].keys()
        ),
        "regions": uniformity_session["regions"],
        "started_at": uniformity_session["started_at"],
    }


def _reset_uniformity_session():
    """Clear the current multi-point test session."""

    uniformity_session["active"] = False
    uniformity_session["sheet_id"] = None
    uniformity_session["regions"] = {}
    uniformity_session["started_at"] = None


# ============================================================
# SETTINGS SCHEMAS
# ============================================================

class UniformityThresholdUpdate(BaseModel):
    """Validated update for the nine-point colour threshold."""

    threshold: float = Field(
        gt=0.0,
        le=1.5,
    )


# ============================================================
# SYSTEM STATUS
# ============================================================

@app.get("/api/status")
def get_system_status():
    settings = load_settings()
    reference = get_reference()

    return {
        "system": "ENG5105 RGB Quality Inspection System",
        "status": "running",
        "sensor_mode": settings["sensor_mode"],
        "reference_available": reference is not None,
        "uniformity_session": _session_snapshot(),
    }


# ============================================================
# LIVE SENSOR DATA
# ============================================================

@app.get("/api/live")
def get_live_color():
    try:
        color = read_color()

        return {
            "sensor": load_settings()["sensor_mode"],
            "color": color,
            "normalized": normalize_rgb(color),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Sensor reading failed: {error}",
        ) from error


# ============================================================
# EXISTING REFERENCE WORKFLOW
# ============================================================

@app.get("/api/reference")
def read_reference():
    reference = get_reference()

    return {
        "reference": reference,
        "normalized": (
            normalize_rgb(reference)
            if reference is not None
            else None
        ),
    }


@app.post("/api/reference")
def update_reference(color: ColorData):
    try:
        reference = set_reference(
            color.model_dump(
                exclude_none=True
            )
        )

        return {
            "message": "Reference colour updated",
            "reference": reference,
            "normalized": normalize_rgb(reference),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update reference colour: {error}",
        ) from error


@app.post("/api/measure/{sample_id}")
def measure_sample(
    sample_id: str,
    background_tasks: BackgroundTasks,
):
    """Measure one point against the stored reference colour."""

    try:
        color = read_color()
        normalized = normalize_rgb(color)
        decision = check_quality(color)

        if decision["status"] == "NO_REFERENCE":
            raise HTTPException(
                status_code=400,
                detail="Reference colour has not been calibrated.",
            )

        threshold = decision["threshold"]

        record = save_measurement(
            sample_id=sample_id,
            color=color,
            distance=decision["difference"],
            threshold=threshold,
            result=decision["status"],
        )

        settings = load_settings()

        # Run the two-second PASS/FAIL indication after the API
        # response is returned, so the webpage is not blocked.
        background_tasks.add_task(
            indicate_result,
            decision["status"],
            duration_seconds=settings[
                "result_indication_seconds"
            ],
        )

        return {
            "measurement": record,
            "color": color,
            "normalized": normalized,
            "difference": decision["difference"],
            "threshold": threshold,
            "status": decision["status"],
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Measurement failed: {error}",
        ) from error


@app.get("/api/history")
def get_history(limit: int = 20):
    limit = max(1, min(limit, 100))

    return {
        "measurements": load_measurements(limit),
    }


# ============================================================
# MULTI-POINT UNIFORMITY WORKFLOW
# ============================================================

@app.post("/api/uniformity/start/{sheet_id}")
def start_uniformity_test(sheet_id: str):
    """
    Start one sheet test, turn on the white illumination LED,
    and wait for the configured warm-up period.
    """

    sheet_id = sheet_id.strip()

    if not sheet_id:
        raise HTTPException(
            status_code=400,
            detail="Sheet ID must not be empty.",
        )

    settings = load_settings()

    with _uniformity_lock:
        # Put all outputs into a known state before starting.
        all_outputs_off()
        clear_result_outputs()

        uniformity_session["active"] = True
        uniformity_session["sheet_id"] = sheet_id
        uniformity_session["regions"] = {}
        uniformity_session["started_at"] = datetime.now().isoformat(
            timespec="seconds"
        )

        try:
            set_white_led(True)

            time.sleep(
                max(
                    0.0,
                    float(
                        settings["illumination_warmup_ms"]
                    ) / 1000.0,
                )
            )

        except Exception as error:
            all_outputs_off()
            _reset_uniformity_session()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to start uniformity test: "
                    f"{error}"
                ),
            ) from error

    return {
        "message": (
            "Uniformity test started and illumination warmed up."
        ),
        "session": _session_snapshot(),
        "expected_regions": settings["uniformity_region_ids"],
        "provisional_thresholds": {
            "color": settings["uniformity_color_threshold"],
            "repeatability": settings[
                "uniformity_repeatability_threshold"
            ],
            "clear": settings["uniformity_clear_threshold"],
            "clear_used_for_decision": settings[
                "use_clear_for_decision"
            ],
        },
    }


@app.post("/api/uniformity/region/{region_id}")
def measure_uniformity_region(region_id: str):
    """
    Measure one configured point, such as P1 to P9.

    The valid IDs are read from settings.json, so this endpoint
    works for both the earlier five-region layout and the new
    nine-point layout.
    """

    settings = load_settings()
    region_id = region_id.upper().strip()
    valid_regions = settings["uniformity_region_ids"]

    if region_id not in valid_regions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid region. Expected one of {valid_regions}."
            ),
        )

    if not uniformity_session["active"]:
        raise HTTPException(
            status_code=400,
            detail="Start a uniformity test first.",
        )

    try:
        measurement = read_color_average(
            sample_count=settings["uniformity_sample_count"],
            discard_count=settings[
                "uniformity_discard_count"
            ],
            interval_ms=settings["measurement_interval_ms"],
            settle_ms=settings["position_settle_ms"],
        )

    except Exception as error:
        all_outputs_off()
        uniformity_session["active"] = False

        raise HTTPException(
            status_code=500,
            detail=f"Region measurement failed: {error}",
        ) from error

    region_record = {
        "region_id": region_id,
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        **measurement["color"],
        "normalized": measurement["normalized"],
        "repeatability": measurement["repeatability"],
        "sample_count": measurement["sample_count"],
    }

    uniformity_session["regions"][region_id] = region_record

    return {
        "sheet_id": uniformity_session["sheet_id"],
        "region": region_record,
        "captured_regions": list(
            uniformity_session["regions"].keys()
        ),
        "remaining_regions": [
            item
            for item in valid_regions
            if item not in uniformity_session["regions"]
        ],
    }


@app.post("/api/uniformity/evaluate")
def evaluate_uniformity_test(
    background_tasks: BackgroundTasks,
):
    """
    Evaluate all configured points, save the result, turn off
    the white LED, and schedule a two-second PASS/FAIL indication.
    """

    settings = load_settings()
    expected_regions = settings["uniformity_region_ids"]

    missing_regions = [
        region_id
        for region_id in expected_regions
        if region_id not in uniformity_session["regions"]
    ]

    if missing_regions:
        raise HTTPException(
            status_code=400,
            detail=f"Missing regions: {missing_regions}",
        )

    regions = [
        uniformity_session["regions"][region_id]
        for region_id in expected_regions
    ]

    try:
        result = evaluate_uniformity(regions)

        # Measurement illumination is no longer needed.
        set_white_led(False)
        uniformity_session["active"] = False

        record = save_uniformity_result(
            sheet_id=uniformity_session["sheet_id"],
            regions=regions,
            uniformity=result,
        )

        # Run the result indication after returning the response.
        background_tasks.add_task(
            indicate_result,
            result["status"],
            duration_seconds=settings[
                "result_indication_seconds"
            ],
        )

        return record

    except Exception as error:
        all_outputs_off()
        uniformity_session["active"] = False

        raise HTTPException(
            status_code=500,
            detail=f"Uniformity evaluation failed: {error}",
        ) from error


@app.get("/api/uniformity/session")
def get_uniformity_session():
    settings = load_settings()

    return {
        "session": _session_snapshot(),
        "expected_regions": settings["uniformity_region_ids"],
    }


@app.post("/api/uniformity/reset")
def reset_uniformity_test():
    """Cancel the current test and switch off every output."""

    all_outputs_off()
    _reset_uniformity_session()

    return {
        "message": "Uniformity session reset.",
        "session": _session_snapshot(),
    }


@app.get("/api/uniformity/history")
def get_uniformity_history(limit: int = 20):
    """Return persisted results matching the current point layout."""

    limit = max(1, min(limit, 100))
    settings = load_settings()
    expected_ids = set(
        settings["uniformity_region_ids"]
    )

    # Load more records before filtering so older five-point tests
    # do not hide recent complete nine-point tests.
    records = load_uniformity_results(1000)

    matching_records = [
        record
        for record in records
        if {
            region.get("region_id")
            for region in record.get("regions", [])
        } == expected_ids
    ]

    return {
        "results": matching_records[:limit],
        "count": len(matching_records),
        "expected_regions": list(
            settings["uniformity_region_ids"]
        ),
    }


# ============================================================
# INDEPENDENT NINE-POINT CSV EXPORT
# ============================================================

@app.get("/api/uniformity/export-info")
def get_uniformity_export_information():
    """Return whether completed P1-P9 tests are available."""

    return get_nine_point_export_info()


@app.get("/api/uniformity/export.csv")
def export_all_nine_point_results():
    """
    Download one CSV containing every completed nine-point test.

    The export is built only from persisted uniformity_results.jsonl
    records. It is completely independent of the single-point
    Measure Sample workflow and its measurements.csv history.
    """

    export = rebuild_nine_point_results_csv()

    if export["test_count"] == 0:
        raise HTTPException(
            status_code=404,
            detail=(
                "No completed nine-point test data is available."
            ),
        )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    return FileResponse(
        path=export["path"],
        media_type="text/csv; charset=utf-8",
        filename=(
            "nine_point_uniformity_results_"
            f"{timestamp}.csv"
        ),
        headers={
            "Cache-Control": "no-store",
            "X-Nine-Point-Test-Count": str(
                export["test_count"]
            ),
            "X-Nine-Point-Row-Count": str(
                export["point_row_count"]
            ),
        },
    )


# ============================================================
# SETTINGS
# ============================================================

@app.get("/api/settings")
def get_settings():
    return load_settings()


@app.put("/api/settings/uniformity-threshold")
def update_uniformity_threshold(
    update: UniformityThresholdUpdate,
):
    """Persist the colour-uniformity threshold for future evaluations."""

    if uniformity_session["active"]:
        raise HTTPException(
            status_code=409,
            detail=(
                "Complete or reset the active nine-point test "
                "before changing the threshold."
            ),
        )

    settings = load_settings()
    settings["uniformity_color_threshold"] = float(
        update.threshold
    )

    saved_settings = save_settings(settings)

    return {
        "message": "Nine-point colour threshold saved.",
        "uniformity_color_threshold": saved_settings[
            "uniformity_color_threshold"
        ],
        "applies_to": "future evaluations",
    }


# ============================================================
# SAFE STARTUP / SHUTDOWN
# ============================================================

@app.on_event("startup")
def startup_outputs():
    """
    Put every GPIO output into a safe OFF state whenever the
    backend server starts, and clear any previous in-memory test.
    """

    all_outputs_off()
    _reset_uniformity_session()


@app.on_event("shutdown")
def shutdown_outputs():
    """Switch off every GPIO output when the server stops."""

    all_outputs_off()


# ============================================================
# FRONTEND
# ============================================================

# Keep this mount at the end so that /api/... routes are
# registered before the catch-all static frontend route.
if FRONTEND_DIR.exists():
    app.mount(
        "/",
        StaticFiles(
            directory=str(FRONTEND_DIR),
            html=True,
        ),
        name="frontend",
    )
