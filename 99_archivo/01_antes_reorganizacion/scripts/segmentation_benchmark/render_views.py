"""Render input views V0..V5 at 224/384/1024 with single isotropic resize and no implicit crop.

Strictly isolated from ground_truth/annotations.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from common import (
    DEFAULT_BENCHMARK_DIR,
    ROOT,
    clip_box,
    digest,
    oriented_srgb,
    present_isotropic,
    read_json,
    write_json,
)


def mask_bbox_xyxy(mask_bool: np.ndarray) -> list[float] | None:
    ys, xs = np.where(mask_bool)
    if len(xs) == 0:
        return None
    return [float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1)]


def compute_w_sam(union_mask: np.ndarray, width: int, height: int, margin_frac: float = 0.05) -> list[float] | None:
    bbox = mask_bbox_xyxy(union_mask)
    if bbox is None:
        return None
    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    pad = margin_frac * max(bw, bh)
    return clip_box([bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad], width, height)


def apply_exterior_fill(rgb: Image.Image, keep_mask: np.ndarray, fill_rgb: tuple[int, int, int] = (127, 127, 127)) -> Image.Image:
    """Preserve exact interior RGB and set exterior pixels to fill_rgb before resize."""
    arr = np.array(rgb.convert("RGB"), dtype=np.uint8)
    out = np.empty_like(arr)
    out[:, :] = np.array(fill_rgb, dtype=np.uint8)
    m = keep_mask.astype(bool)
    out[m] = arr[m]
    return Image.fromarray(out, mode="RGB")


def _load_bool_mask(path: Path, width: int, height: int) -> np.ndarray:
    with Image.open(path) as im:
        if im.size != (width, height):
            raise ValueError(f"Mask {path} size {im.size} != {(width, height)}")
        return np.array(im.convert("L"), dtype=np.uint8) > 0


def render_split_views(
    benchmark_dir: Path,
    split: str,
    views: list[str] | None = None,
    sizes: list[int] | None = None,
) -> dict[str, Any]:
    cfg = read_json(benchmark_dir / "config_draft.json")
    v_cfg = cfg["views"]
    target_views = views or list(v_cfg["definitions"])
    target_sizes = sizes or [int(s) for s in v_cfg["presentation_sizes"]]
    fill_rgb = tuple(int(c) for c in v_cfg["exterior_rgb"])
    margin_frac = float(v_cfg["w_sam_margin_long_side_fraction"])

    sample_rows = read_json(benchmark_dir / "samples" / f"{split}.json")
    rendered_counts: dict[str, int] = {v: 0 for v in target_views}
    fallback_counts: dict[str, int] = {v: 0 for v in target_views}

    for row in sample_rows:
        iid = row["image_id"]
        src_path = ROOT / row["source_path"]
        if digest(src_path) != row["sha256"]:
            raise ValueError(f"Source SHA256 changed for {iid}")

        with Image.open(src_path) as im:
            rgb, _, _ = oriented_srgb(im)
        w, h = rgb.size
        full_box = [0.0, 0.0, float(w), float(h)]

        p_l1_path = benchmark_dir / "predictions/L1" / split / iid / "prediction.json"
        p_s1_path = benchmark_dir / "predictions/S1" / split / iid / "prediction.json"
        l1_pred = read_json(p_l1_path) if p_l1_path.exists() else None
        s1_pred = read_json(p_s1_path) if p_s1_path.exists() else None

        # Determine W_sam and S1 masks if S1 succeeded
        s1_ok = s1_pred is not None and s1_pred.get("status") == "ok"
        w_sam = None
        s1_plant = None
        s1_union = None
        if s1_ok:
            s1_plant = _load_bool_mask(benchmark_dir / s1_pred["outputs"]["plant_mask_png"], w, h)
            s1_union = _load_bool_mask(benchmark_dir / s1_pred["outputs"]["union_mask_png"], w, h)
            w_sam = compute_w_sam(s1_union, w, h, margin_frac=margin_frac)
            if w_sam is None:
                s1_ok = False

        hsv_mask = None
        hsv_ok = l1_pred is not None and l1_pred.get("status") == "ok"
        if hsv_ok and "hsv_green_png" in l1_pred.get("outputs", {}):
            hsv_mask = _load_bool_mask(benchmark_dir / l1_pred["outputs"]["hsv_green_png"], w, h)
            if not np.any(hsv_mask):
                hsv_ok = False

        for view_id in target_views:
            if view_id == "V0":
                crop_box = full_box
                src_img = rgb
                view_status = "ok"
                fallback_reason = None
                mask_applied = False
            elif view_id == "V1":
                if l1_pred is None:
                    crop_box, view_status, fallback_reason = full_box, "fallback_fullframe", "l1_missing"
                elif l1_pred["status"] != "ok":
                    crop_box, view_status, fallback_reason = full_box, "fallback_fullframe", l1_pred["status"]
                else:
                    crop_box, view_status, fallback_reason = l1_pred["crop_box_oriented_px"], "ok", None
                src_img = rgb
                mask_applied = False
            elif view_id == "V2":
                if not s1_ok or w_sam is None:
                    crop_box = full_box
                    view_status = "fallback_fullframe"
                    fallback_reason = s1_pred["status"] if s1_pred else "s1_missing"
                else:
                    crop_box, view_status, fallback_reason = w_sam, "ok", None
                src_img = rgb
                mask_applied = False
            elif view_id == "V3":
                if not s1_ok or w_sam is None or s1_plant is None or not np.any(s1_plant):
                    crop_box = full_box
                    view_status = "fallback_fullframe"
                    fallback_reason = s1_pred["status"] if s1_pred else "s1_missing"
                    src_img = rgb
                    mask_applied = False
                else:
                    crop_box, view_status, fallback_reason = w_sam, "ok", None
                    src_img = apply_exterior_fill(rgb, s1_plant, fill_rgb=fill_rgb)
                    mask_applied = True
            elif view_id == "V4":
                if not s1_ok or w_sam is None or s1_union is None:
                    crop_box = full_box
                    view_status = "fallback_fullframe"
                    fallback_reason = s1_pred["status"] if s1_pred else "s1_missing"
                    src_img = rgb
                    mask_applied = False
                else:
                    crop_box, view_status, fallback_reason = w_sam, "ok", None
                    src_img = apply_exterior_fill(rgb, s1_union, fill_rgb=fill_rgb)
                    mask_applied = True
            elif view_id == "V5":
                if not s1_ok or w_sam is None:
                    crop_box = full_box
                    view_status = "fallback_fullframe"
                    fallback_reason = f"sam_window_unavailable:{s1_pred['status'] if s1_pred else 's1_missing'}"
                    src_img = rgb
                    mask_applied = False
                elif not hsv_ok or hsv_mask is None:
                    crop_box = full_box
                    view_status = "fallback_fullframe"
                    fallback_reason = f"hsv_unavailable:{l1_pred['status'] if l1_pred else 'l1_missing'}"
                    src_img = rgb
                    mask_applied = False
                else:
                    crop_box, view_status, fallback_reason = w_sam, "ok", None
                    src_img = apply_exterior_fill(rgb, hsv_mask, fill_rgb=fill_rgb)
                    mask_applied = True
            else:
                raise ValueError(f"Unknown view_id: {view_id}")

            if view_status != "ok":
                fallback_counts[view_id] += 1
            rendered_counts[view_id] += 1

            for sz in target_sizes:
                out_dir = benchmark_dir / "views" / view_id / str(sz) / split
                out_dir.mkdir(parents=True, exist_ok=True)
                view_img, meta = present_isotropic(src_img, crop_box, sz, fill_rgb=fill_rgb, is_mask=False)
                png_path = out_dir / f"{iid}.png"
                view_img.save(png_path, format="PNG")
                meta_out = {
                    "view_id": view_id,
                    "sample_role": split,
                    "image_id": iid,
                    "source_sha256": row["sha256"],
                    "status": view_status,
                    "fallback_reason": fallback_reason,
                    "mask_applied": mask_applied,
                    "output_png": str(png_path.relative_to(benchmark_dir).as_posix()),
                    "output_sha256": digest(png_path),
                    **meta,
                }
                write_json(out_dir / f"{iid}.json", meta_out)

    return {
        "split": split,
        "views": target_views,
        "sizes": target_sizes,
        "rendered_counts": rendered_counts,
        "fallback_counts": fallback_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, default=DEFAULT_BENCHMARK_DIR)
    parser.add_argument("--split", choices=["tuning", "evaluation", "stress"], required=True)
    parser.add_argument("--views", nargs="+", default=None)
    parser.add_argument("--sizes", nargs="+", type=int, default=None)
    args = parser.parse_args()

    res = render_split_views(args.benchmark_dir, args.split, args.views, args.sizes)
    import json

    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
