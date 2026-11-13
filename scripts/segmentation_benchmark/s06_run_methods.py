"""Method runners (L0, L1, S1, and S2/L2 interaction logging) for segmentation_benchmark_v1.

Strictly isolated from ground_truth/annotations during prediction.
Refuses --split evaluation without a valid freeze.json.
Never simulates SAM3 outputs when dependencies/weights/GPU are unavailable.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from s02_common import (
    DEFAULT_BENCHMARK_DIR,
    ROOT,
    box_area,
    clip_box,
    digest,
    oriented_srgb,
    read_json,
    sha256_json,
    utc_now_iso,
    write_csv,
    write_json,
)


TIMINGS_COLUMNS = [
    "sample_role",
    "image_id",
    "source_sha256",
    "method_id",
    "status",
    "load_seconds",
    "inference_seconds",
    "export_seconds",
    "total_seconds",
    "peak_vram_mb",
    "device",
]


def _save_mask(path: Path, mask_bool: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    arr = np.where(mask_bool.astype(bool), 255, 0).astype(np.uint8)
    Image.fromarray(arr, mode="L").save(path, format="PNG")
    return digest(path)


def _circle_score(gray: np.ndarray, edges: np.ndarray, cx: float, cy: float, radius: float) -> tuple[float, float]:
    theta = np.linspace(0, 2 * np.pi, 180, endpoint=False)
    radii = radius + np.arange(-3, 4)
    xx = np.rint(cx + radii[:, None] * np.cos(theta)).astype(int)
    yy = np.rint(cy + radii[:, None] * np.sin(theta)).astype(int)
    valid = (xx >= 0) & (xx < gray.shape[1]) & (yy >= 0) & (yy < gray.shape[0])
    sampled = np.zeros(xx.shape, dtype=np.float32)
    sampled[valid] = edges[yy[valid], xx[valid]] / 255.0
    support = float(np.mean(np.max(sampled, axis=0)))
    center_dist = float(np.hypot(cx - gray.shape[1] / 2.0, cy - gray.shape[0] / 2.0) / min(gray.shape))
    ring = np.zeros(xx.shape, dtype=np.float32)
    ring[valid] = gray[yy[valid], xx[valid]] / 255.0
    dark_rim = float(1.0 - np.mean(np.min(ring, axis=0)))
    score = float(0.4 * support + 0.4 * dark_rim - 0.8 * center_dist + 0.2 * radius / min(gray.shape))
    return score, support


def run_l1_hough_hsv(rgb: Image.Image, l1_cfg: dict[str, Any]) -> dict[str, Any]:
    """Exact reproduction of L1 (Hough at 400px + HSV at 800px + bounded rectangle)."""
    import cv2  # type: ignore

    cv2.setNumThreads(2)
    w, h = rgb.size

    # 1) Hough circle detection at max side 400
    hough_factor = float(l1_cfg["hough_max_side_px"]) / max(w, h)
    small_hough = np.array(rgb.resize((round(w * hough_factor), round(h * hough_factor)), Image.Resampling.LANCZOS))
    gray = cv2.cvtColor(small_hough, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (7, 7), 1.8)
    edges = cv2.Canny(gray, 35, 100)
    dim = min(gray.shape)
    raw = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        float(l1_cfg["hough_dp"]),
        dim * float(l1_cfg["hough_min_dist_frac"]),
        param1=float(l1_cfg["hough_param1"]),
        param2=float(l1_cfg["hough_param2"]),
        minRadius=int(dim * float(l1_cfg["hough_min_radius_frac"])),
        maxRadius=int(dim * float(l1_cfg["hough_max_radius_frac"])),
    )

    if raw is None:
        return {
            "status": "fallback_unreliable_reference",
            "circle": None,
            "green_bbox": None,
            "crop_box_oriented_px": [0.0, 0.0, float(w), float(h)],
            "requested_margin_clipped_by_capture": False,
            "hsv_mask_native": np.zeros((h, w), dtype=bool),
            "hough_diagnostics": {"candidate_count": 0},
        }

    candidates = []
    for cx_s, cy_s, r_s in raw[0]:
        score, support = _circle_score(gray, edges, float(cx_s), float(cy_s), float(r_s))
        candidates.append({"cx": float(cx_s), "cy": float(cy_s), "r": float(r_s), "score": score, "angular_edge_support": support})
    candidates.sort(key=lambda c: c["score"], reverse=True)
    best = candidates[0]
    circle = [best["cx"] / hough_factor, best["cy"] / hough_factor, 2.0 * best["r"] / hough_factor]

    # 2) HSV green segmentation at max side 800
    hsv_factor = float(l1_cfg["green_analysis_max_side_px"]) / max(w, h)
    small_hsv = np.array(rgb.resize((round(w * hsv_factor), round(h * hsv_factor)), Image.Resampling.LANCZOS))
    hsv = cv2.cvtColor(small_hsv, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, np.array(l1_cfg["hsv_low"], dtype=np.uint8), np.array(l1_cfg["hsv_high"], dtype=np.uint8))
    a = small_hsv.astype(np.float32)
    mask[~((a[:, :, 1] > a[:, :, 0] * float(l1_cfg["G_over_R"])) & (a[:, :, 1] > a[:, :, 2] * float(l1_cfg["G_over_B"])))] = 0
    k = int(l1_cfg["closing_kernel"])
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)

    yy, xx = np.indices(mask.shape)
    xs = (xx + 0.5) * w / small_hsv.shape[1]
    ys = (yy + 0.5) * h / small_hsv.shape[0]
    anchor = (xs - circle[0]) ** 2 + (ys - circle[1]) ** 2 < (float(l1_cfg["anchor_radius_fraction"]) * circle[2] / 2.0) ** 2
    selected = np.zeros_like(mask)
    for label in range(1, count):
        comp = labels == label
        if stats[label, cv2.CC_STAT_AREA] >= int(l1_cfg["min_component_area_px"]) and np.any(comp & anchor):
            selected[comp] = 255

    vy, vx = np.where(selected > 0)
    if len(vx) == 0:
        return {
            "status": "fallback_no_green_component",
            "circle": circle,
            "green_bbox": None,
            "crop_box_oriented_px": [0.0, 0.0, float(w), float(h)],
            "requested_margin_clipped_by_capture": False,
            "hsv_mask_native": np.zeros((h, w), dtype=bool),
            "hough_diagnostics": {"candidate_count": len(candidates), "best_score": best["score"], "angular_edge_support": best["angular_edge_support"]},
        }

    green_bbox = [
        float(vx.min() * w / small_hsv.shape[1]),
        float(vy.min() * h / small_hsv.shape[0]),
        float((vx.max() + 1) * w / small_hsv.shape[1]),
        float((vy.max() + 1) * h / small_hsv.shape[0]),
    ]
    cx, cy, d = circle
    r = d / 2.0
    m = float(l1_cfg["margin_fraction_of_pot_diameter"]) * d
    requested = [min(cx - r, green_bbox[0]) - m, min(cy - r, green_bbox[1]) - m, max(cx + r, green_bbox[2]) + m, max(cy + r, green_bbox[3]) + m]
    clipped = clip_box(requested, w, h)
    native_mask = np.array(Image.fromarray(selected, mode="L").resize((w, h), Image.Resampling.NEAREST)) > 0

    return {
        "status": "ok",
        "circle": circle,
        "green_bbox": green_bbox,
        "crop_box_oriented_px": clipped,
        "requested_margin_clipped_by_capture": clipped != requested,
        "hsv_mask_native": native_mask,
        "hough_diagnostics": {"candidate_count": len(candidates), "best_score": best["score"], "angular_edge_support": best["angular_edge_support"]},
    }


def associate_sam3_instances(
    plant_masks: list[np.ndarray],
    plant_scores: list[float],
    soil_masks: list[np.ndarray],
    soil_scores: list[float],
    anchor_circle: list[float] | None,
    width: int,
    height: int,
    soil_anchor_radius_frac: float = 0.9,
    plant_soil_dilation_diam_frac: float = 0.10,
) -> dict[str, Any]:
    """Associate raw SAM3 plant & soil instances to target pot using L1 Hough anchor.

    Enforces:
    - No instance cropping to circle/soil (whole instances kept).
    - Priority plant > soil for semantic labels; binary union is plant OR soil.
    - Explicit uncertain status if no anchor circle or no linkable target.
    """
    if anchor_circle is None:
        return {
            "status": "uncertain_no_anchor",
            "plant_mask": np.zeros((height, width), dtype=bool),
            "soil_mask": np.zeros((height, width), dtype=bool),
            "union_mask": np.zeros((height, width), dtype=bool),
            "selected_soil_index": None,
            "selected_plant_indices": [],
        }

    cx, cy, d = anchor_circle
    r_anchor = (d / 2.0) * soil_anchor_radius_frac
    yy, xx = np.indices((height, width))
    central_disk = ((xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2) < (r_anchor ** 2)

    # Select soil mask with max absolute intersection with central disk
    best_soil_idx = None
    best_soil_key = (-1, -1.0, 0)
    for idx, sm in enumerate(soil_masks):
        inter = int(np.sum(sm & central_disk))
        if inter > 0:
            sc = float(soil_scores[idx]) if idx < len(soil_scores) else 0.0
            key = (inter, sc, -idx)
            if key > best_soil_key:
                best_soil_key = key
                best_soil_idx = idx

    soil_mask = soil_masks[best_soil_idx].copy() if best_soil_idx is not None else np.zeros((height, width), dtype=bool)

    # Dilate selected soil by 0.1 * d for association ONLY (never for mask output)
    assoc_region = central_disk.copy()
    if best_soil_idx is not None:
        rad_px = max(1, int(round(d * plant_soil_dilation_diam_frac)))
        try:
            import cv2  # type: ignore

            k_size = 2 * rad_px + 1
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))
            dilated_soil = cv2.dilate(soil_mask.astype(np.uint8), kernel) > 0
        except Exception:
            # Pure-numpy fallback box dilation if cv2 absent in unit test
            from PIL import ImageFilter

            dilated_soil = (
                np.array(Image.fromarray(soil_mask.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(2 * rad_px + 1)))
                > 0
            )
        assoc_region = assoc_region | dilated_soil

    selected_plant_indices: list[int] = []
    plant_mask = np.zeros((height, width), dtype=bool)
    for idx, pm in enumerate(plant_masks):
        if np.any(pm & assoc_region):
            selected_plant_indices.append(idx)
            plant_mask |= pm  # Keep WHOLE instance

    if not selected_plant_indices and best_soil_idx is None:
        status = "empty"
    elif not selected_plant_indices:
        status = "empty_plant"
    else:
        status = "ok"

    # Priority plant > soil for semantic label; union is unchanged
    soil_final = soil_mask & (~plant_mask)
    union_mask = plant_mask | soil_mask
    return {
        "status": status,
        "plant_mask": plant_mask,
        "soil_mask": soil_final,
        "union_mask": union_mask,
        "selected_soil_index": best_soil_idx,
        "selected_plant_indices": selected_plant_indices,
    }


def run_sam3_independent_prompts(
    rgb: Image.Image,
    processor: Any,
    plant_prompt: str,
    soil_prompt: str,
    confidence_threshold: float,
    pixel_threshold: float,
) -> dict[str, Any]:
    """Execute SAM3 with strictly isolated prompt states for plant and soil."""
    state_plant = processor.set_image(rgb)
    out_plant = processor.set_text_prompt(state=state_plant, prompt=plant_prompt)

    state_soil = processor.set_image(rgb)
    out_soil = processor.set_text_prompt(state=state_soil, prompt=soil_prompt)

    def _extract(out: dict[str, Any]) -> tuple[list[np.ndarray], list[float], list[list[float]]]:
        masks_raw = out.get("masks", [])
        scores_raw = out.get("scores", [])
        boxes_raw = out.get("boxes", [])
        masks_list, scores_list, boxes_list = [], [], []
        for i in range(len(masks_raw)):
            sc = float(scores_raw[i]) if i < len(scores_raw) else 1.0
            if sc < confidence_threshold:
                continue
            m = masks_raw[i]
            if hasattr(m, "detach"):
                m = m.detach().cpu().numpy()
            m_arr = np.asarray(m)
            if m_arr.ndim == 3:
                m_arr = m_arr[0]
            masks_list.append(m_arr > pixel_threshold if m_arr.dtype != bool else m_arr)
            scores_list.append(sc)
            if i < len(boxes_raw):
                b = boxes_raw[i]
                if hasattr(b, "detach"):
                    b = b.detach().cpu().tolist()
                boxes_list.append([float(x) for x in b])
        return masks_list, scores_list, boxes_list

    p_masks, p_scores, p_boxes = _extract(out_plant)
    s_masks, s_scores, s_boxes = _extract(out_soil)
    return {
        "plant_masks": p_masks,
        "plant_scores": p_scores,
        "plant_boxes": p_boxes,
        "soil_masks": s_masks,
        "soil_scores": s_scores,
        "soil_boxes": s_boxes,
    }


def load_sam3_runtime(s1_cfg: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    """Load real SAM3 model & processor. Raises RuntimeError if dependencies/weights are missing."""
    try:
        import torch  # type: ignore
        import sam3  # type: ignore
        from sam3.model_builder import build_sam3_image_model  # type: ignore
        from sam3.model.sam3_image_processor import Sam3Processor  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"dependency_missing: PyTorch/SAM3 not available ({exc})") from exc

    if not torch.cuda.is_available():
        raise RuntimeError("dependency_missing: CUDA GPU required for SAM3 inference")

    ckpt = s1_cfg.get("checkpoint_path")
    if not ckpt or not Path(ckpt).exists():
        raise RuntimeError(f"dependency_missing: SAM3 checkpoint_path not found ({ckpt})")

    model = build_sam3_image_model(checkpoint_path=str(ckpt))
    processor = Sam3Processor(model, confidence_threshold=float(s1_cfg["confidence_threshold"]))
    meta = {
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "device_name": torch.cuda.get_device_name(0),
        "sam3_path": str(Path(sam3.__file__).resolve()),
        "checkpoint_path": str(ckpt),
        "checkpoint_sha256": digest(Path(ckpt)),
    }
    return processor, meta


def verify_freeze_for_evaluation(benchmark_dir: Path) -> dict[str, Any]:
    freeze_path = benchmark_dir / "freeze.json"
    if not freeze_path.exists():
        raise RuntimeError("Evaluation blocked: freeze.json does not exist. Run calibration & adjudicate GT first.")
    freeze = read_json(freeze_path)
    checks = [
        ("config_draft.json", freeze["config_sha256"]),
        ("samples/evaluation.json", freeze["evaluation_sample_sha256"]),
        ("code_inventory.json", freeze["code_inventory_sha256"]),
    ]
    for rel, expected in checks:
        actual = digest(benchmark_dir / rel)
        if actual != expected:
            raise RuntimeError(f"Freeze mismatch for {rel}: expected {expected}, got {actual}")
    return freeze


def run_split(
    benchmark_dir: Path,
    split: str,
    methods: list[str],
    config_path: Path | None = None,
) -> dict[str, Any]:
    if split == "evaluation":
        verify_freeze_for_evaluation(benchmark_dir)

    cfg = read_json(config_path or (benchmark_dir / "config_draft.json"))
    cfg_sha = sha256_json(cfg)
    sample_rows = read_json(benchmark_dir / "samples" / f"{split}.json")

    sam3_processor = None
    sam3_error = None
    sam3_runtime_meta: dict[str, Any] = {}
    if "S1" in methods:
        try:
            sam3_processor, sam3_runtime_meta = load_sam3_runtime(cfg["s1_sam3_auto"])
        except Exception as exc:
            sam3_error = str(exc)

    timings: list[dict[str, Any]] = []
    summary_counts: dict[str, dict[str, int]] = {m: {} for m in methods}

    for row in sample_rows:
        iid = row["image_id"]
        src_path = ROOT / row["source_path"]
        actual_sha = digest(src_path)
        if actual_sha != row["sha256"]:
            raise ValueError(f"Source SHA256 changed for {iid}: expected {row['sha256']}, got {actual_sha}")

        t0 = time.perf_counter()
        with Image.open(src_path) as im:
            rgb, color_status, _ = oriented_srgb(im)
        t_load = time.perf_counter() - t0
        w, h = rgb.size
        if (w, h) != (int(row["oriented_width"]), int(row["oriented_height"])):
            raise ValueError(f"Oriented size mismatch for {iid}: {(w, h)} vs {(row['oriented_width'], row['oriented_height'])}")

        l1_res = None
        if "L1" in methods or "S1" in methods:
            t_inf0 = time.perf_counter()
            l1_res = run_l1_hough_hsv(rgb, cfg["l1_hough_hsv"])
            t_l1_inf = time.perf_counter() - t_inf0
        else:
            t_l1_inf = 0.0

        for method in methods:
            pred_dir = benchmark_dir / "predictions" / method / split / iid
            pred_file = pred_dir / "prediction.json"
            ckpt_sha = cfg["s1_sam3_auto"].get("checkpoint_sha256") or "none"

            # Cache check by (image_sha256, config_sha256, checkpoint_sha256, method_id)
            if pred_file.exists():
                cached = read_json(pred_file)
                if (
                    cached.get("source_sha256") == actual_sha
                    and cached.get("config_sha256") == cfg_sha
                    and cached.get("checkpoint_sha256") == ckpt_sha
                    and cached.get("method_id") == method
                    and cached.get("status") != "dependency_missing"
                ):
                    st = cached["status"]
                    summary_counts[method][st] = summary_counts[method].get(st, 0) + 1
                    continue

            t_exp0 = time.perf_counter()
            if method == "L0":
                rec = {
                    "method_id": "L0",
                    "method_version": "fullframe_v1",
                    "sample_role": split,
                    "image_id": iid,
                    "source_sha256": actual_sha,
                    "split_group_id": row["split_group_id"],
                    "year": row["year"],
                    "exif_camera_model": row["exif_camera_model"],
                    "species_code": row["species_code"],
                    "oriented_width": w,
                    "oriented_height": h,
                    "color_processing": color_status,
                    "config_sha256": cfg_sha,
                    "checkpoint_sha256": "none",
                    "status": "ok",
                    "crop_box_oriented_px": [0.0, 0.0, float(w), float(h)],
                    "outputs": {},
                }
                write_json(pred_file, rec)
                t_inf, t_exp, vram, dev = 0.0, time.perf_counter() - t_exp0, 0.0, "cpu"

            elif method == "L1":
                assert l1_res is not None
                mask_sha = _save_mask(pred_dir / "hsv_green.png", l1_res["hsv_mask_native"])
                rec = {
                    "method_id": "L1",
                    "method_version": "hough400_hsv800_v1",
                    "sample_role": split,
                    "image_id": iid,
                    "source_sha256": actual_sha,
                    "split_group_id": row["split_group_id"],
                    "year": row["year"],
                    "exif_camera_model": row["exif_camera_model"],
                    "species_code": row["species_code"],
                    "oriented_width": w,
                    "oriented_height": h,
                    "color_processing": color_status,
                    "config_sha256": cfg_sha,
                    "checkpoint_sha256": "none",
                    "status": l1_res["status"],
                    "circle_oriented_px": l1_res["circle"],
                    "green_bbox_oriented_px": l1_res["green_bbox"],
                    "crop_box_oriented_px": l1_res["crop_box_oriented_px"],
                    "requested_margin_clipped_by_capture": l1_res["requested_margin_clipped_by_capture"],
                    "hough_diagnostics": l1_res["hough_diagnostics"],
                    "outputs": {"hsv_green_png": str((pred_dir / "hsv_green.png").relative_to(benchmark_dir).as_posix()), "hsv_green_sha256": mask_sha},
                }
                write_json(pred_file, rec)
                t_inf, t_exp, vram, dev = t_l1_inf, time.perf_counter() - t_exp0, 0.0, "cpu"

            elif method == "S1":
                if sam3_processor is None:
                    rec = {
                        "method_id": "S1",
                        "method_version": "sam3_auto_v1",
                        "sample_role": split,
                        "image_id": iid,
                        "source_sha256": actual_sha,
                        "split_group_id": row["split_group_id"],
                        "year": row["year"],
                        "exif_camera_model": row["exif_camera_model"],
                        "species_code": row["species_code"],
                        "oriented_width": w,
                        "oriented_height": h,
                        "color_processing": color_status,
                        "config_sha256": cfg_sha,
                        "checkpoint_sha256": ckpt_sha,
                        "status": "dependency_missing",
                        "error": sam3_error,
                        "crop_box_oriented_px": [0.0, 0.0, float(w), float(h)],
                        "outputs": {},
                    }
                    write_json(pred_file, rec)
                    t_inf, t_exp, vram, dev = 0.0, time.perf_counter() - t_exp0, 0.0, "none"
                else:
                    import torch  # type: ignore

                    torch.cuda.reset_peak_memory_stats()
                    torch.cuda.synchronize()
                    t_s0 = time.perf_counter()
                    raw_sam = run_sam3_independent_prompts(
                        rgb,
                        sam3_processor,
                        plant_prompt=cfg["s1_sam3_auto"]["prompts"]["plant"],
                        soil_prompt=cfg["s1_sam3_auto"]["prompts"]["soil"],
                        confidence_threshold=float(cfg["s1_sam3_auto"]["confidence_threshold"]),
                        pixel_threshold=float(cfg["s1_sam3_auto"]["pixel_threshold"]),
                    )
                    torch.cuda.synchronize()
                    t_inf = time.perf_counter() - t_s0
                    vram = float(torch.cuda.max_memory_allocated() / (1024.0 * 1024.0))
                    dev = sam3_runtime_meta.get("device_name", "cuda")

                    assert l1_res is not None
                    assoc = associate_sam3_instances(
                        raw_sam["plant_masks"],
                        raw_sam["plant_scores"],
                        raw_sam["soil_masks"],
                        raw_sam["soil_scores"],
                        l1_res["circle"],
                        w,
                        h,
                        soil_anchor_radius_frac=float(cfg["s1_sam3_auto"]["soil_anchor_radius_fraction"]),
                        plant_soil_dilation_diam_frac=float(cfg["s1_sam3_auto"]["plant_soil_dilation_diameter_fraction"]),
                    )
                    p_sha = _save_mask(pred_dir / "plant_mask.png", assoc["plant_mask"])
                    s_sha = _save_mask(pred_dir / "soil_mask.png", assoc["soil_mask"])
                    u_sha = _save_mask(pred_dir / "union_mask.png", assoc["union_mask"])
                    rec = {
                        "method_id": "S1",
                        "method_version": "sam3_auto_v1",
                        "sample_role": split,
                        "image_id": iid,
                        "source_sha256": actual_sha,
                        "split_group_id": row["split_group_id"],
                        "year": row["year"],
                        "exif_camera_model": row["exif_camera_model"],
                        "species_code": row["species_code"],
                        "oriented_width": w,
                        "oriented_height": h,
                        "color_processing": color_status,
                        "config_sha256": cfg_sha,
                        "checkpoint_sha256": sam3_runtime_meta["checkpoint_sha256"],
                        "prompts": cfg["s1_sam3_auto"]["prompts"],
                        "status": assoc["status"],
                        "selected_soil_index": assoc["selected_soil_index"],
                        "selected_plant_indices": assoc["selected_plant_indices"],
                        "plant_scores": raw_sam["plant_scores"],
                        "soil_scores": raw_sam["soil_scores"],
                        "outputs": {
                            "plant_mask_png": str((pred_dir / "plant_mask.png").relative_to(benchmark_dir).as_posix()),
                            "plant_mask_sha256": p_sha,
                            "soil_mask_png": str((pred_dir / "soil_mask.png").relative_to(benchmark_dir).as_posix()),
                            "soil_mask_sha256": s_sha,
                            "union_mask_png": str((pred_dir / "union_mask.png").relative_to(benchmark_dir).as_posix()),
                            "union_mask_sha256": u_sha,
                        },
                    }
                    write_json(pred_file, rec)
                    t_exp = time.perf_counter() - t_exp0 - t_inf
            else:
                raise ValueError(f"Unsupported automatic method: {method}")

            st = rec["status"]
            summary_counts[method][st] = summary_counts[method].get(st, 0) + 1
            timings.append(
                {
                    "sample_role": split,
                    "image_id": iid,
                    "source_sha256": actual_sha,
                    "method_id": method,
                    "status": st,
                    "load_seconds": round(t_load, 6),
                    "inference_seconds": round(t_inf, 6),
                    "export_seconds": round(t_exp, 6),
                    "total_seconds": round(t_load + t_inf + t_exp, 6),
                    "peak_vram_mb": round(vram, 2),
                    "device": dev,
                }
            )

    if timings:
        write_csv(benchmark_dir / f"timings_{split}.csv", timings, fieldnames=TIMINGS_COLUMNS)

    return {
        "split": split,
        "methods": methods,
        "n_images": len(sample_rows),
        "status_counts": summary_counts,
        "sam3_error": sam3_error,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, default=DEFAULT_BENCHMARK_DIR)
    parser.add_argument("--split", choices=["tuning", "evaluation", "stress"], required=True)
    parser.add_argument("--methods", nargs="+", default=["L0", "L1", "S1"], choices=["L0", "L1", "S1"])
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args()

    res = run_split(args.benchmark_dir, args.split, args.methods, args.config)
    import json

    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
