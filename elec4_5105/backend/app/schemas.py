from typing import Literal, Optional

from pydantic import BaseModel, Field


# ============================================================
# COLOUR DATA
# ============================================================

class ColorData(BaseModel):
    # TCS34725 color_raw values are not limited to 8-bit 0-255.
    r: int = Field(ge=0)
    g: int = Field(ge=0)
    b: int = Field(ge=0)
    clear: Optional[int] = Field(
        default=None,
        ge=0
    )


# ============================================================
# REFERENCE
# ============================================================

class ReferenceResponse(BaseModel):
    reference: Optional[ColorData] = None


class ReferenceUpdateResponse(BaseModel):
    message: str
    reference: ColorData


# ============================================================
# QUALITY DECISION
# ============================================================

class QualityResult(BaseModel):
    distance: float
    status: Literal[
        "PASS",
        "FAIL",
        "NO_REFERENCE"
    ]


# ============================================================
# LIVE SENSOR RESPONSE
# ============================================================

class LiveColorResponse(BaseModel):
    sensor: str
    color: ColorData
    difference: Optional[float] = None
    status: Literal[
        "PASS",
        "FAIL",
        "NO_REFERENCE"
    ]


# ============================================================
# MEASUREMENT REQUEST
# ============================================================

class MeasurementRequest(BaseModel):
    sample_id: str = Field(
        default="S001",
        min_length=1,
        max_length=50
    )


# ============================================================
# STORED MEASUREMENT
# ============================================================

class MeasurementRecord(BaseModel):
    sample_id: str
    timestamp: str

    r: int
    g: int
    b: int
    clear: Optional[int] = None

    distance: float
    threshold: float

    result: Literal[
        "PASS",
        "FAIL"
    ]


# ============================================================
# SYSTEM STATUS
# ============================================================

class SystemStatusResponse(BaseModel):
    system: str
    status: Literal[
        "running",
        "error"
    ]

    sensor_mode: str
    reference_available: bool
