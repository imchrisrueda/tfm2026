"""Shared utilities, contracts, coordinate transforms, and config for segmentation_benchmark_v1."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import PIL
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
LOCAL_OPENCV_DIR = ROOT / "scratch/opencv_runtime"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if LOCAL_OPENCV_DIR.exists() and str(LOCAL_OPENCV_DIR) not in sys.path:
    sys.path.insert(0, str(LOCAL_OPENCV_DIR))

from prepare_metric_masters import digest, oriented_srgb, yes  # noqa: E402

DEFAULT_BENCHMARK_DIR = ROOT / "data/processed/preprocessing/segmentation_benchmark_v1"
REGISTRY_PATH = ROOT / "exp_design/preprocessing_registry.json"
DEV_SELECTION_PATH = ROOT / "data/processed/preprocessing/development_v1/selection.json"
STRESS_TRIAL_INDICES = [1, 3, 6, 37, 40, 43, 44, 53, 62, 86, 88, 90]
SEED_DEFAULT = "20261113-roi-benchmark-v1"

ANNOTATION_LAYERS = [
    "plant_target",
    "soil_target",
    "other_plant",
    "pot_rim_wall",
    "card_label",
    "other_background",
    "ignore_uncertain",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(obj: Any) -> str:
    canonical = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_text(canonical)


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path: Path, obj: Any) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def read_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(dict.fromkeys(k for row in rows for k in row.keys()))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    return path


def verify_protected_inputs(root: Path = ROOT) -> dict[str, Any]:
    """Verify active preprocessing registry and pinned hashes without modifying them."""
    reg_path = root / "exp_design/preprocessing_registry.json"
    registry = read_json(reg_path)
    checks = {
        "registry_path": reg_path.relative_to(root).as_posix(),
        "registry_sha256": digest(reg_path),
        "active_preparation_version": registry["active_preparation_version"],
        "verified_files": {},
    }
    pairs = [
        (registry["configuration_path"], registry["configuration_sha256"]),
        (registry["prepared_manifest_path"], registry["prepared_manifest_sha256"]),
        (registry["prepared_csv_path"], registry["prepared_csv_sha256"]),
        (registry["release_validation_path"], registry["release_validation_sha256"]),
        (registry["metadata_errata_path"], registry["metadata_errata_sha256"]),
    ]
    for role, info in registry["partition_lists"].items():
        pairs.append((info["json_path"], info["json_sha256"]))
        pairs.append((info["csv_path"], info["csv_sha256"]))

    for rel_path, expected_sha in pairs:
        full_path = root / rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"Protected input missing: {rel_path}")
        actual_sha = digest(full_path)
        if actual_sha != expected_sha:
            raise ValueError(f"Protected input hash mismatch for {rel_path}: expected {expected_sha}, got {actual_sha}")
        checks["verified_files"][rel_path] = actual_sha
    return checks


def clip_box(box: list[float], width: int, height: int) -> list[float]:
    return [
        max(0.0, min(float(width), float(box[0]))),
        max(0.0, min(float(height), float(box[1]))),
        max(0.0, min(float(width), float(box[2]))),
        max(0.0, min(float(height), float(box[3]))),
    ]


def box_area(box: list[float] | None) -> float:
    if box is None:
        return 0.0
    return max(0.0, float(box[2]) - float(box[0])) * max(0.0, float(box[3]) - float(box[1]))


def box_overlap(a: list[float] | None, b: list[float] | None) -> float:
    if a is None or b is None:
        return 0.0
    inter = [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]
    return box_area(inter)


def box_contains(outer: list[float], inner: list[float], eps: float = 1e-6) -> bool:
    return (
        outer[0] <= inner[0] + eps
        and outer[1] <= inner[1] + eps
        and outer[2] >= inner[2] - eps
        and outer[3] >= inner[3] - eps
    )


def xyxy_to_norm_cxcywh(box: list[float], width: int, height: int) -> list[float]:
    """Convert pixel half-open xyxy [x0, y0, x1, y1] to normalized [cx, cy, w, h] in [0, 1]."""
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive")
    x0, y0, x1, y1 = map(float, box)
    cx = ((x0 + x1) / 2.0) / float(width)
    cy = ((y0 + y1) / 2.0) / float(height)
    bw = (x1 - x0) / float(width)
    bh = (y1 - y0) / float(height)
    return [cx, cy, bw, bh]


def norm_cxcywh_to_xyxy(box: list[float], width: int, height: int) -> list[float]:
    """Convert normalized [cx, cy, w, h] to pixel xyxy [x0, y0, x1, y1]."""
    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive")
    cx, cy, bw, bh = map(float, box)
    x0 = (cx - bw / 2.0) * float(width)
    y0 = (cy - bh / 2.0) * float(height)
    x1 = (cx + bw / 2.0) * float(width)
    y1 = (cy + bh / 2.0) * float(height)
    return [x0, y0, x1, y1]


def present_isotropic(
    image: Image.Image,
    box: list[float],
    target_size: int,
    fill_rgb: tuple[int, int, int] = (127, 127, 127),
    is_mask: bool = False,
) -> tuple[Image.Image, dict[str, Any]]:
    """Single isotropic affine presentation into target_size x target_size without implicit crop.

    Coordinates follow PIL pixel-center convention:
    x_src = box[0] + (x_dst + 0.5 - tx) / scale - 0.5  -> PIL AFFINE (1/scale, 0, box[0] - tx/scale, ...)
    Wait: PIL.Image.transform maps output pixel center (x_dst+0.5, y_dst+0.5) via
    x_src = a*(x_dst+0.5) + b*(y_dst+0.5) + c? Actually PIL AFFINE evaluates at (x+0.5, y+0.5) for BICUBIC/LANCZOS
    and (x, y) for NEAREST; using exact center offset keeps box[0]..box[2] aligned.
    """
    x0, y0, x1, y1 = map(float, box)
    bw = x1 - x0
    bh = y1 - y0
    if bw <= 0 or bh <= 0:
        raise ValueError(f"Non-positive crop box: {box}")
    scale = float(target_size) / max(bw, bh)
    tx = (float(target_size) - bw * scale) / 2.0
    ty = (float(target_size) - bh * scale) / 2.0
    inv_scale = 1.0 / scale
    coeffs = (inv_scale, 0.0, x0 - tx * inv_scale, 0.0, inv_scale, y0 - ty * inv_scale)

    if is_mask:
        src_l = image.convert("L")
        view = src_l.transform(
            (target_size, target_size),
            Image.Transform.AFFINE,
            coeffs,
            resample=Image.Resampling.NEAREST,
            fillcolor=0,
        )
        yy, xx = np.indices((target_size, target_size))
        valid = (xx + 0.5 >= tx) & (xx + 0.5 < tx + bw * scale) & (yy + 0.5 >= ty) & (yy + 0.5 < ty + bh * scale)
        arr = np.array(view, dtype=np.uint8)
        arr[~valid] = 0
        arr = np.where(arr >= 128, 255, 0).astype(np.uint8)
        out = Image.fromarray(arr, mode="L")
    else:
        src_rgb = image.convert("RGB")
        view = src_rgb.transform(
            (target_size, target_size),
            Image.Transform.AFFINE,
            coeffs,
            resample=Image.Resampling.BICUBIC,
            fillcolor=fill_rgb,
        )
        yy, xx = np.indices((target_size, target_size))
        valid = (xx + 0.5 >= tx) & (xx + 0.5 < tx + bw * scale) & (yy + 0.5 >= ty) & (yy + 0.5 < ty + bh * scale)
        bg = Image.new("RGB", (target_size, target_size), fill_rgb)
        out = Image.composite(view, bg, Image.fromarray((valid.astype(np.uint8)) * 255, mode="L"))

    meta = {
        "target_size": int(target_size),
        "crop_box_oriented_px": [x0, y0, x1, y1],
        "scale": scale,
        "upscaled": bool(scale > 1.0),
        "tx": tx,
        "ty": ty,
        "valid_width_px": bw * scale,
        "valid_height_px": bh * scale,
        "canvas_valid_fraction": float(valid.mean()),
        "affine_canvas_to_source": [inv_scale, 0.0, x0 - tx * inv_scale, 0.0, inv_scale, y0 - ty * inv_scale],
        "affine_source_to_canvas": [scale, 0.0, tx - x0 * scale, 0.0, scale, ty - y0 * scale],
        "interpolation": "nearest_binarized" if is_mask else "bicubic_uniform_affine",
        "padding_rgb": None if is_mask else list(fill_rgb),
    }
    return out, meta


def collect_environment_info() -> dict[str, Any]:
    """Collect Python, PIL, numpy, OpenCV, PyTorch, CUDA, and SAM3 availability without fabricating."""
    info: dict[str, Any] = {
        "collected_utc": utc_now_iso(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "pillow_version": PIL.__version__,
        "numpy_version": np.__version__,
        "cv2": {"available": False, "version": None, "source": None},
        "torch": {"available": False, "version": None, "cuda_available": False, "cuda_version": None, "device_name": None},
        "sam3": {"available": False, "version": None, "error": None},
    }
    try:
        import cv2  # type: ignore

        info["cv2"] = {"available": True, "version": cv2.__version__, "source": str(Path(cv2.__file__).resolve())}
    except Exception as exc:
        info["cv2"]["error"] = repr(exc)

    try:
        import torch  # type: ignore

        info["torch"] = {
            "available": True,
            "version": torch.__version__,
            "cuda_available": bool(torch.cuda.is_available()),
            "cuda_version": torch.version.cuda,
            "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        }
    except Exception as exc:
        info["torch"]["error"] = repr(exc)

    try:
        import sam3  # type: ignore

        info["sam3"] = {
            "available": True,
            "version": getattr(sam3, "__version__", "unknown"),
            "path": str(Path(sam3.__file__).resolve()),
        }
    except Exception as exc:
        info["sam3"]["error"] = repr(exc)

    return info


def default_config() -> dict[str, Any]:
    return {
        "protocol_version": "segmentation_benchmark_v1",
        "seed": SEED_DEFAULT,
        "source_partition": "C_fit",
        "tuning_quotas": {
            "2025": {"H": 3, "P": 3, "R": 3},
            "2026": {"H": 3, "P": 3, "R": 3},
        },
        "evaluation_quotas": {
            "2025": {"H": 9, "P": 12, "R": 9},
            "2026": {"H": 9, "P": 12, "R": 9},
        },
        "double_annotation_quotas": {
            "2025": {"H": 3, "P": 4, "R": 3},
            "2026": {"H": 3, "P": 4, "R": 3},
        },
        "stress_development_indices": STRESS_TRIAL_INDICES,
        "l1_hough_hsv": {
            "hough_max_side_px": 400,
            "hough_dp": 1.2,
            "hough_min_dist_frac": 0.08,
            "hough_param1": 100,
            "hough_param2": 35,
            "hough_min_radius_frac": 0.18,
            "hough_max_radius_frac": 0.55,
            "green_analysis_max_side_px": 800,
            "hsv_low": [25, 45, 20],
            "hsv_high": [85, 255, 255],
            "G_over_R": 1.08,
            "G_over_B": 1.10,
            "closing_kernel": 5,
            "min_component_area_px": 40,
            "anchor_radius_fraction": 0.9,
            "margin_fraction_of_pot_diameter": 0.10,
        },
        "s1_sam3_auto": {
            "model_family": "sam3",
            "checkpoint_path": None,
            "checkpoint_sha256": None,
            "sam3_git_commit": None,
            "prompts": {"plant": "plant", "soil": "soil"},
            "independent_prompt_states": True,
            "confidence_threshold": 0.5,
            "confidence_grid_tuning": [0.3, 0.5, 0.7],
            "pixel_threshold": 0.5,
            "anchor_source": "L1_hough_circle",
            "soil_anchor_radius_fraction": 0.9,
            "plant_soil_dilation_diameter_fraction": 0.10,
            "label_priority": ["plant_target", "soil_target"],
            "dtype": "bfloat16",
            "warmup_runs_tuning": 3,
        },
        "assisted_budget": {
            "max_active_seconds": 120,
            "max_positive_boxes": 1,
            "max_extra_prompts": 5,
        },
        "views": {
            "w_sam_margin_long_side_fraction": 0.05,
            "exterior_rgb": [127, 127, 127],
            "presentation_sizes": [224, 384, 1024],
            "definitions": ["V0", "V1", "V2", "V3", "V4", "V5"],
        },
        "metrics": {
            "critical_tissue_loss_gt": 0.02,
            "critical_fine_point_loss_gt": 0.05,
            "bootstrap_resamples": 10000,
            "acceptance_median_retention_ge": 0.99,
            "acceptance_p95_photos_retention_ge": 0.98,
        },
    }
