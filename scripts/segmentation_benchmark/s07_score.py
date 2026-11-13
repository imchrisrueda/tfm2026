"""Ground-truth evaluation, metrics, failure classification, and stratified bootstrap.

This is the ONLY module allowed to read ground_truth/annotations for scoring.
Never triggers prompt/threshold optimization after reading evaluation GT.
"""
from __future__ import annotations

import argparse
import hashlib
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from s01_annotation_io import read_mask_png
from s02_common import (
    ANNOTATION_LAYERS,
    DEFAULT_BENCHMARK_DIR,
    read_json,
    utc_now_iso,
    write_csv,
    write_json,
)


def _binary_boundary(mask: np.ndarray) -> np.ndarray:
    """4-connected interior boundary of a boolean mask using pure numpy."""
    if not np.any(mask):
        return np.zeros_like(mask, dtype=bool)
    p = np.pad(mask, 1, mode="constant", constant_values=False)
    eroded = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    return mask & (~eroded)


def _dilate_disk_or_box(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0 or not np.any(mask):
        return mask
    try:
        import cv2  # type: ignore

        k = 2 * radius + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        return cv2.dilate(mask.astype(np.uint8), kernel) > 0
    except Exception:
        from PIL import ImageFilter

        return np.array(Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(2 * radius + 1))) > 0


def boundary_f1(pred: np.ndarray, gt: np.ndarray, valid: np.ndarray, delta_px: int) -> float:
    b_pred = _binary_boundary(pred) & valid
    b_gt = _binary_boundary(gt) & valid
    n_pred = int(np.sum(b_pred))
    n_gt = int(np.sum(b_gt))
    if n_gt == 0 and n_pred == 0:
        return float("nan")
    if n_gt == 0 or n_pred == 0:
        return 0.0
    d_gt = _dilate_disk_or_box(b_gt, delta_px)
    d_pred = _dilate_disk_or_box(b_pred, delta_px)
    prec = float(np.sum(b_pred & d_gt)) / float(n_pred)
    rec = float(np.sum(b_gt & d_pred)) / float(n_gt)
    if prec + rec == 0.0:
        return 0.0
    return 2.0 * prec * rec / (prec + rec)


def compute_mask_metrics(pred: np.ndarray, gt: np.ndarray, valid: np.ndarray, delta_px: int) -> dict[str, Any]:
    g = gt & valid
    m = pred & valid
    g_area = int(np.sum(g))
    m_area = int(np.sum(m))
    if g_area == 0:
        return {
            "gt_area_px": 0,
            "pred_area_px": m_area,
            "recall": float("nan"),
            "precision": float("nan"),
            "dice": float("nan"),
            "iou": float("nan"),
            "boundary_f1": float("nan"),
        }
    inter = int(np.sum(g & m))
    union = int(np.sum(g | m))
    recall = float(inter) / float(g_area)
    precision = float(inter) / float(m_area) if m_area > 0 else float("nan")
    dice = (2.0 * float(inter)) / float(g_area + m_area) if (g_area + m_area) > 0 else 0.0
    iou = float(inter) / float(union) if union > 0 else 0.0
    bf1 = boundary_f1(pred, gt, valid, delta_px)
    return {
        "gt_area_px": g_area,
        "pred_area_px": m_area,
        "recall": recall,
        "precision": precision,
        "dice": dice,
        "iou": iou,
        "boundary_f1": bf1,
    }


def compute_support_metrics(
    support_k: np.ndarray,
    gt_layers: dict[str, np.ndarray],
    valid: np.ndarray,
    fine_points: list[dict[str, Any]],
    delta_px: int,
) -> dict[str, Any]:
    """Compute tissue retention |K∩G|/|G|, fine-point retention, and contamination decomposition."""
    g = gt_layers["plant_target"] & valid
    s = gt_layers["soil_target"] & valid
    u = g | s
    k = support_k & valid

    g_area = int(np.sum(g))
    k_area = int(np.sum(k))
    retention = float(np.sum(k & g)) / float(g_area) if g_area > 0 else float("nan")

    contam_plant_only = float(np.sum(k & (~g))) / float(k_area) if k_area > 0 else float("nan")
    contam_plant_soil = float(np.sum(k & (~u))) / float(k_area) if k_area > 0 else float("nan")

    decomp = {}
    for layer in ("soil_target", "other_plant", "pot_rim_wall", "card_label", "other_background"):
        l_mask = gt_layers[layer] & valid
        decomp[f"contam_frac_{layer}"] = float(np.sum(k & l_mask)) / float(k_area) if k_area > 0 else float("nan")

    # Fine-point retention (exact and with tolerance delta_px)
    eval_pts = [p for p in fine_points if p.get("status", "evaluable") == "evaluable"]
    n_pts = len(eval_pts)
    if n_pts > 0:
        h, w = support_k.shape
        exact_hits = 0
        tol_hits = 0
        k_dil = _dilate_disk_or_box(support_k, delta_px)
        for p in eval_pts:
            ix = min(w - 1, max(0, int(round(float(p["x"])))))
            iy = min(h - 1, max(0, int(round(float(p["y"])))))
            if bool(support_k[iy, ix]):
                exact_hits += 1
            if bool(k_dil[iy, ix]):
                tol_hits += 1
        pt_ret_exact = float(exact_hits) / float(n_pts)
        pt_ret_tol = float(tol_hits) / float(n_pts)
    else:
        pt_ret_exact = float("nan")
        pt_ret_tol = float("nan")

    return {
        "support_k_area_px": k_area,
        "tissue_retention": retention,
        "contamination_plant_only": contam_plant_only,
        "contamination_plant_soil": contam_plant_soil,
        "fine_points_evaluable": n_pts,
        "fine_point_retention_exact": pt_ret_exact,
        "fine_point_retention_tol": pt_ret_tol,
        **decomp,
    }


def wilson_ci(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float, float]:
    """Wilson 95% confidence interval for a binomial proportion."""
    if total <= 0:
        return float("nan"), float("nan"), float("nan")
    p = successes / total
    denom = 1.0 + (z * z) / total
    center = (p + (z * z) / (2.0 * total)) / denom
    half = (z * math.sqrt((p * (1.0 - p) + (z * z) / (4.0 * total)) / total)) / denom
    return p, max(0.0, center - half), min(1.0, center + half)


def summarize_numeric(values: list[float]) -> dict[str, Any]:
    clean = [float(v) for v in values if v is not None and not math.isnan(float(v))]
    if not clean:
        return {"n": 0, "mean": None, "median": None, "iqr": None, "q25": None, "q75": None}
    arr = np.array(clean, dtype=np.float64)
    q25, med, q75 = np.percentile(arr, [25, 50, 75])
    return {
        "n": len(clean),
        "mean": float(np.mean(arr)),
        "median": float(med),
        "iqr": float(q75 - q25),
        "q25": float(q25),
        "q75": float(q75),
    }


def stratified_paired_bootstrap(
    records: list[dict[str, Any]],
    metric_key: str,
    strata_keys: tuple[str, ...] = ("year", "species_code"),
    n_resamples: int = 10000,
    seed: str = "20261113-roi-benchmark-v1",
) -> dict[str, Any]:
    """Deterministic stratified paired bootstrap on paired differences (a - b) by group strata."""
    # Group paired records by stratum
    strata: dict[tuple[Any, ...], list[float]] = defaultdict(list)
    for r in records:
        va, vb = r.get("a"), r.get("b")
        if va is None or vb is None or math.isnan(float(va)) or math.isnan(float(vb)):
            continue
        key = tuple(r[k] for k in strata_keys)
        strata[key].append(float(va) - float(vb))

    all_diffs = [d for ds in strata.values() for d in ds]
    n_pairs = len(all_diffs)
    if n_pairs == 0:
        return {"metric": metric_key, "n_pairs": 0, "mean_diff": None, "median_diff": None, "ci95_mean": None, "ci95_median": None}

    seed_int = int.from_bytes(hashlib.sha256(f"{seed}|boot|{metric_key}".encode("utf-8")).digest()[:8], "big")
    rng = np.random.default_rng(seed_int)

    strata_arrays = [np.array(ds, dtype=np.float64) for _, ds in sorted(strata.items())]
    boot_means = np.empty(n_resamples, dtype=np.float64)
    boot_medians = np.empty(n_resamples, dtype=np.float64)

    for b_idx in range(n_resamples):
        sampled_parts = [arr[rng.integers(0, len(arr), size=len(arr))] for arr in strata_arrays]
        combined = np.concatenate(sampled_parts)
        boot_means[b_idx] = np.mean(combined)
        boot_medians[b_idx] = np.median(combined)

    obs_arr = np.array(all_diffs, dtype=np.float64)
    return {
        "metric": metric_key,
        "n_pairs": n_pairs,
        "mean_diff": float(np.mean(obs_arr)),
        "median_diff": float(np.median(obs_arr)),
        "ci95_mean": [float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))],
        "ci95_median": [float(np.percentile(boot_medians, 2.5)), float(np.percentile(boot_medians, 97.5))],
    }


def score_split(benchmark_dir: Path, split: str, gt_subdir: str = "consensus") -> dict[str, Any]:
    cfg = read_json(benchmark_dir / "config_draft.json")
    sample_rows = read_json(benchmark_dir / "samples" / f"{split}.json")
    gt_root = benchmark_dir / "annotations" / gt_subdir / split

    per_image_rows: list[dict[str, Any]] = []
    failures_rows: list[dict[str, Any]] = []
    missing_gt = []

    for row in sample_rows:
        iid = row["image_id"]
        w, h = int(row["oriented_width"]), int(row["oriented_height"])
        diag = math.hypot(w, h)
        delta_px = max(1, round(0.001 * diag))

        case_dir = gt_root / iid
        if not case_dir.exists() or not (case_dir / "metadata.json").exists():
            missing_gt.append(iid)
            continue

        meta = read_json(case_dir / "metadata.json")
        gt_layers = {layer: read_mask_png(case_dir / f"{layer}.png", w, h) for layer in ANNOTATION_LAYERS}
        valid = ~gt_layers["ignore_uncertain"]
        fine_points = meta.get("fine_points", [])

        # Score raw masks for L1 (HSV) and S1 (SAM3 plant & soil)
        for method_id in ("L1", "S1"):
            p_file = benchmark_dir / "predictions" / method_id / split / iid / "prediction.json"
            if not p_file.exists():
                continue
            pred = read_json(p_file)
            if method_id == "L1":
                m_path = pred.get("outputs", {}).get("hsv_green_png")
                m_plant = read_mask_png(benchmark_dir / m_path, w, h) if m_path else np.zeros((h, w), dtype=bool)
                m_metrics = compute_mask_metrics(m_plant, gt_layers["plant_target"], valid, delta_px)
            else:
                pm_path = pred.get("outputs", {}).get("plant_mask_png")
                sm_path = pred.get("outputs", {}).get("soil_mask_png")
                m_plant = read_mask_png(benchmark_dir / pm_path, w, h) if pm_path else np.zeros((h, w), dtype=bool)
                m_soil = read_mask_png(benchmark_dir / sm_path, w, h) if sm_path else np.zeros((h, w), dtype=bool)
                m_metrics = compute_mask_metrics(m_plant, gt_layers["plant_target"], valid, delta_px)
                s_metrics = compute_mask_metrics(m_soil, gt_layers["soil_target"], valid, delta_px)
                m_metrics["soil_iou"] = s_metrics["iou"]
                m_metrics["soil_dice"] = s_metrics["dice"]

            per_image_rows.append(
                {
                    "sample_role": split,
                    "record_type": "raw_mask",
                    "entity_id": method_id,
                    "image_id": iid,
                    "split_group_id": row["split_group_id"],
                    "year": int(row["year"]),
                    "species_code": row["species_code"],
                    "exif_camera_model": row["exif_camera_model"],
                    "status": pred["status"],
                    "delta_px": delta_px,
                    **m_metrics,
                }
            )

        # Score views V0..V5 support K
        for view_id in cfg["views"]["definitions"]:
            v_meta_path = benchmark_dir / "views" / view_id / "384" / split / f"{iid}.json"
            if not v_meta_path.exists():
                continue
            v_meta = read_json(v_meta_path)
            x0, y0, x1, y1 = v_meta["crop_box_oriented_px"]
            ix0, iy0 = max(0, int(math.floor(x0))), max(0, int(math.floor(y0)))
            ix1, iy1 = min(w, int(math.ceil(x1))), min(h, int(math.ceil(y1)))
            box_mask = np.zeros((h, w), dtype=bool)
            box_mask[iy0:iy1, ix0:ix1] = True

            if view_id in ("V0", "V1", "V2") or v_meta["status"] == "fallback_fullframe":
                support_k = box_mask
            elif view_id == "V3":
                s1_pred = read_json(benchmark_dir / "predictions/S1" / split / iid / "prediction.json")
                support_k = box_mask & read_mask_png(benchmark_dir / s1_pred["outputs"]["plant_mask_png"], w, h)
            elif view_id == "V4":
                s1_pred = read_json(benchmark_dir / "predictions/S1" / split / iid / "prediction.json")
                support_k = box_mask & read_mask_png(benchmark_dir / s1_pred["outputs"]["union_mask_png"], w, h)
            elif view_id == "V5":
                l1_pred = read_json(benchmark_dir / "predictions/L1" / split / iid / "prediction.json")
                support_k = box_mask & read_mask_png(benchmark_dir / l1_pred["outputs"]["hsv_green_png"], w, h)
            else:
                support_k = box_mask

            s_metrics = compute_support_metrics(support_k, gt_layers, valid, fine_points, delta_px)
            ret = s_metrics["tissue_retention"]
            pt_ret = s_metrics["fine_point_retention_tol"]
            crit_fail = (not math.isnan(ret) and (1.0 - ret) > cfg["metrics"]["critical_tissue_loss_gt"]) or (
                not math.isnan(pt_ret) and (1.0 - pt_ret) > cfg["metrics"]["critical_fine_point_loss_gt"]
            )
            rec = {
                "sample_role": split,
                "record_type": "view_support",
                "entity_id": view_id,
                "image_id": iid,
                "split_group_id": row["split_group_id"],
                "year": int(row["year"]),
                "species_code": row["species_code"],
                "exif_camera_model": row["exif_camera_model"],
                "status": v_meta["status"],
                "delta_px": delta_px,
                "critical_failure": crit_fail,
                **s_metrics,
            }
            per_image_rows.append(rec)
            if crit_fail or v_meta["status"] != "ok":
                failures_rows.append(rec)

    if per_image_rows:
        write_csv(benchmark_dir / f"per_image_metrics_{split}.csv", per_image_rows)
    if failures_rows:
        write_csv(benchmark_dir / f"failures_{split}.csv", failures_rows)

    # Aggregate statistics by entity_id and P-only subset
    by_entity: dict[str, dict[str, Any]] = {}
    for eid in sorted({r["entity_id"] for r in per_image_rows}):
        sub = [r for r in per_image_rows if r["entity_id"] == eid]
        sub_p = [r for r in sub if r["species_code"] == "P"]
        if sub[0]["record_type"] == "view_support":
            by_entity[eid] = {
                "all": {
                    "tissue_retention": summarize_numeric([r["tissue_retention"] for r in sub]),
                    "contamination_plant_only": summarize_numeric([r["contamination_plant_only"] for r in sub]),
                    "contamination_plant_soil": summarize_numeric([r["contamination_plant_soil"] for r in sub]),
                    "critical_failure_wilson_95": wilson_ci(sum(1 for r in sub if r["critical_failure"]), len(sub)),
                },
                "P_only": {
                    "tissue_retention": summarize_numeric([r["tissue_retention"] for r in sub_p]),
                    "critical_failure_wilson_95": wilson_ci(sum(1 for r in sub_p if r["critical_failure"]), len(sub_p)),
                },
            }
        else:
            by_entity[eid] = {
                "all": {
                    "recall": summarize_numeric([r["recall"] for r in sub]),
                    "dice": summarize_numeric([r["dice"] for r in sub]),
                    "iou": summarize_numeric([r["iou"] for r in sub]),
                },
                "P_only": {
                    "recall": summarize_numeric([r["recall"] for r in sub_p]),
                    "dice": summarize_numeric([r["dice"] for r in sub_p]),
                    "iou": summarize_numeric([r["iou"] for r in sub_p]),
                },
            }

    stats_out = {
        "scored_utc": utc_now_iso(),
        "split": split,
        "gt_subdir": gt_subdir,
        "n_sample_images": len(sample_rows),
        "n_missing_gt": len(missing_gt),
        "missing_gt_image_ids": missing_gt,
        "summary_by_entity": by_entity,
    }
    write_json(benchmark_dir / f"statistics_{split}.json", stats_out)
    return stats_out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, default=DEFAULT_BENCHMARK_DIR)
    parser.add_argument("--split", choices=["tuning", "evaluation", "stress"], required=True)
    parser.add_argument("--gt-subdir", default="consensus")
    args = parser.parse_args()

    res = score_split(args.benchmark_dir, args.split, args.gt_subdir)
    import json

    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
