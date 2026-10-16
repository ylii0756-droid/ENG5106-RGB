from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.decision import evaluate_uniformity


def point(point_id, r, g, b, clear, p95=0.005):
    total = r + g + b

    return {
        "region_id": point_id,
        "r": r,
        "g": g,
        "b": b,
        "clear": clear,
        "normalized": {
            "r": r / total,
            "g": g / total,
            "b": b / total,
        },
        "repeatability": {
            "normalized_p95_distance": p95
        }
    }


# 3 x 3 rectangular-sheet layout:
# P1  P2  P3
# P4  P5  P6
# P7  P8  P9
points = [
    point("P1", 9000, 4300, 2500, 16000),
    point("P2", 8950, 4280, 2490, 15950),
    point("P3", 9100, 4350, 2520, 16200),
    point("P4", 8880, 4240, 2470, 15820),
    point("P5", 9020, 4310, 2510, 16080),
    point("P6", 9050, 4320, 2515, 16110),
    point("P7", 8920, 4260, 2480, 15890),
    point("P8", 8990, 4290, 2500, 16020),
    point("P9", 9080, 4340, 2520, 16180),
]

result = evaluate_uniformity(points)

assert result["region_count"] == 9
assert len(result["pair_distances"]) == 36
assert result["status"] == "PASS"

print("Status:", result["status"])
print("Point count:", result["region_count"])
print("Pair comparisons:", len(result["pair_distances"]))
print("Max pair distance:", result["max_pair_distance"])
print("Worst pair:", result["worst_pair"])
print("Max repeatability:", result["max_repeatability_p95_distance"])
print("Max Clear deviation:", result["max_clear_deviation"])
