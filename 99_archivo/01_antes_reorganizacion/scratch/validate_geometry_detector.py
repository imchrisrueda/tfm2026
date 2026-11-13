import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from PIL import Image, ImageDraw
from detect_pot_geometry import detect, digest

image = Image.new("RGB", (600, 400), (130, 130, 130))
draw = ImageDraw.Draw(image)
draw.ellipse((160, 60, 440, 340), fill=(20, 20, 20))
draw.ellipse((175, 75, 425, 325), fill=(110, 80, 40))
draw.ellipse((250, 150, 350, 250), fill=(30, 150, 30))
result, _ = detect(image)
blank, _ = detect(Image.new("RGB", (600, 400), (130, 130, 130)))
checks = {
    "center_x_within_10px": abs(result["pot_center_x_px"] - 300) < 10,
    "diameter_within_15px": abs(result["pot_diameter_px"] - 280) < 15,
    "blank_has_no_circle": blank["algorithm_status"] == "circle_not_detected",
    "proposal_not_approved": result["review_status"] == "algorithm_unreviewed",
    "truncation_remains_unknown": result["vegetation_truncated"] is None,
    "green_bbox_approximately_matches_synthetic_leaf": all(abs(actual-expected) <= 2 for actual, expected in zip(result["vegetation_bbox"], [250.0, 150.0, 351.0, 251.0])),
    "json_serializable": bool(json.dumps(result)),
}
report = {"checks": checks, "synthetic_circle_result": result,
          "script_sha256": digest(ROOT / "scripts/detect_pot_geometry.py"),
          "scope": "synthetic_checks_only_not_validation_of_real_rim_measurement"}
output = ROOT / "data/processed/preprocessing/geometry_review_v2/final/synthetic_validation.json"
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(checks, indent=2))
assert all(checks.values())
