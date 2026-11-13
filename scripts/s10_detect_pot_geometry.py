"""Propose, never approve, rim circles and green-vegetation boxes in C_fit.

Requires OpenCV and numpy. A local pip --target scratch/opencv_runtime install
is supported; no source/authoritative manifest is changed.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / "scratch/opencv_runtime"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))
import cv2
import numpy as np
from PIL import Image, ImageDraw
from s18_prepare_metric_masters import oriented_srgb, digest, yes

cv2.setNumThreads(2)


def circle_score(gray, edges, cx, cy, radius):
    theta = np.linspace(0, 2 * np.pi, 180, endpoint=False)
    radii = radius + np.arange(-3, 4)
    xx = np.rint(cx + radii[:, None] * np.cos(theta)).astype(int)
    yy = np.rint(cy + radii[:, None] * np.sin(theta)).astype(int)
    valid = (xx >= 0) & (xx < gray.shape[1]) & (yy >= 0) & (yy < gray.shape[0])
    sampled = np.zeros(xx.shape, dtype=np.float32)
    sampled[valid] = edges[yy[valid], xx[valid]] / 255
    support = float(np.mean(np.max(sampled, axis=0)))
    # Centrality is only a weak tie-breaker, never evidence of a valid rim.
    center_dist = np.hypot(cx - gray.shape[1] / 2, cy - gray.shape[0] / 2) / min(gray.shape)
    ring = np.zeros(xx.shape, dtype=np.float32)
    ring[valid] = gray[yy[valid], xx[valid]] / 255
    dark_rim = float(1 - np.mean(np.min(ring, axis=0)))
    return float(.4 * support + .4 * dark_rim - .8 * center_dist + .2 * radius / min(gray.shape)), support


def detect(rgb):
    width, height = rgb.size
    factor = 400 / max(width, height)
    small = np.array(rgb.resize((round(width * factor), round(height * factor)), Image.Resampling.LANCZOS))
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (7, 7), 1.8)
    edges = cv2.Canny(gray, 35, 100)
    dim = min(gray.shape)
    raw = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1.2, dim * 0.08,
                           param1=100, param2=35, minRadius=int(dim * .18), maxRadius=int(dim * .55))
    if raw is None:
        return {"algorithm_status": "circle_not_detected"}, small
    candidates = []
    for cx, cy, radius in raw[0]:
        score, support = circle_score(gray, edges, cx, cy, radius)
        candidates.append({"cx": float(cx), "cy": float(cy), "r": float(radius), "score": score, "angular_edge_support": support})
    candidates.sort(key=lambda value: value["score"], reverse=True)
    best = candidates[0]
    cx, cy, radius = best["cx"], best["cy"], best["r"]
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    green = cv2.inRange(hsv, np.array([25, 45, 20]), np.array([85, 255, 255]))
    channels = small.astype(np.float32)
    excess = (channels[:,:,1] > channels[:,:,0]*1.08) & (channels[:,:,1] > channels[:,:,2]*1.10)
    green[~excess] = 0
    green = cv2.morphologyEx(green, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(green, 8)
    selected = np.zeros_like(green)
    yy, xx = np.indices(green.shape)
    central = (xx - cx) ** 2 + (yy - cy) ** 2 < (radius * 0.9) ** 2
    for label in range(1, count):
        component = labels == label
        if stats[label, cv2.CC_STAT_AREA] >= 10 and np.any(component & central):
            selected[component] = 255
    ys, xs = np.where(selected > 0)
    box = [float(xs.min() / factor), float(ys.min() / factor), float((xs.max() + 1) / factor), float((ys.max() + 1) / factor)] if len(xs) else None
    touches = bool(len(xs) and (xs.min() == 0 or ys.min() == 0 or xs.max() == small.shape[1] - 1 or ys.max() == small.shape[0] - 1))
    result = {"algorithm_status": "circle_proposed", "pot_center_x_px": cx / factor,
              "pot_center_y_px": cy / factor, "pot_diameter_px": 2 * radius / factor,
              "algorithm_diagnostics": {"angular_edge_support": best["angular_edge_support"],
                "score": best["score"], "candidate_count": len(candidates), "analysis_max_side_px": 400,
                "top_candidates_oriented_px": [{"center_x": c["cx"] / factor, "center_y": c["cy"] / factor,
                  "diameter": 2 * c["r"] / factor, "score": c["score"]} for c in candidates[:3]]},
              "vegetation_bbox": box, "vegetation_bbox_method": "HSV_green_components_intersecting_0.9_rim_radius",
              "vegetation_mask_area_analysis_px": len(xs), "vegetation_touches_frame_algorithm": touches,
              "vegetation_truncated": None, "reference_quality": "algorithm_unreviewed",
              "review_status": "algorithm_unreviewed", "measurement_scope": "proposal_only"}
    return result, small


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=ROOT / "data/processed/preprocessing/development_v1/selection.json")
    parser.add_argument("--pilot", type=Path, default=ROOT / "data/processed/preprocessing/development_v1/annotations_pilot.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/preprocessing/geometry_review_v2")
    parser.add_argument("--resume", action="store_true", help="Reuse per-image proposals with matching source hashes")
    args = parser.parse_args()
    rows = json.loads(args.selection.read_text(encoding="utf-8-sig"))
    if any(r["split_assignment"] != "C_fit" or not yes(r["use_in_assigned_partition"]) for r in rows):
        raise ValueError("Selection must contain active C_fit only; no other role opened")
    args.output.mkdir(parents=True, exist_ok=args.resume)
    (args.output / "overlays").mkdir(exist_ok=args.resume)
    pilot = {a["image_id"]: a for a in json.loads(args.pilot.read_text(encoding="utf-8-sig"))}
    proposals, contrasts, tiles = [], [], []
    for index, row in enumerate(rows, 1):
        path = ROOT / row["source_path"]
        if digest(path) != row["sha256"]:
            raise ValueError("Source changed " + row["image_id"])
        cached = args.output / "overlays" / f"{index:03d}.json"
        if args.resume and cached.exists():
            result = json.loads(cached.read_text(encoding="utf-8"))
            if result["image_id"] != row["image_id"] or result["source_sha256"] != row["sha256"]:
                raise ValueError("Cached proposal input mismatch")
            with Image.open(args.output / "overlays" / f"{index:03d}.jpg") as preview:
                small = np.array(preview.convert("RGB"))
            color = result["color_processing"]
            oriented_size = (row["oriented_width"], row["oriented_height"])
        else:
            with Image.open(path) as image:
                rgb, color, _ = oriented_srgb(image)
            oriented_size = rgb.size
            result, small = detect(rgb)
        result.update({"image_id": row["image_id"], "source_sha256": row["sha256"], "coordinate_space": "exif_oriented",
                       "review_index": index, "year": row["year"], "species_code": row["species_code"],
                       "source_path": row["source_path"], "color_processing": color})
        proposals.append(result)
        # Incremental records allow review while later sources are still decoded.
        (args.output / "overlays" / f"{index:03d}.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        overlay = Image.fromarray(small)
        draw = ImageDraw.Draw(overlay)
        scale = max(small.shape[:2]) / max(oriented_size)
        if result["algorithm_status"] == "circle_proposed":
            cx, cy, radius = result["pot_center_x_px"] * scale, result["pot_center_y_px"] * scale, result["pot_diameter_px"] * scale / 2
            draw.ellipse([cx-radius,cy-radius,cx+radius,cy+radius], outline="red", width=3)
            draw.line([cx-5,cy,cx+5,cy], fill="red", width=2)
            draw.line([cx,cy-5,cx,cy+5], fill="red", width=2)
            if result["vegetation_bbox"]:
                draw.rectangle([v*scale for v in result["vegetation_bbox"]], outline="lime", width=2)
            manual = pilot.get(row["image_id"])
            if manual:
                m_cx,m_cy,m_r=manual["pot_center_x_px"]*scale,manual["pot_center_y_px"]*scale,manual["pot_diameter_px"]*scale/2
                draw.ellipse([m_cx-m_r,m_cy-m_r,m_cx+m_r,m_cy+m_r], outline="cyan", width=2)
                contrasts.append({"image_id":row["image_id"],"review_index":index,
                   "diameter_relative_difference_vs_approx_pilot":result["pot_diameter_px"]/manual["pot_diameter_px"]-1,
                   "center_difference_px":float(np.hypot(result["pot_center_x_px"]-manual["pot_center_x_px"],result["pot_center_y_px"]-manual["pot_center_y_px"])),
                   "not_ground_truth":True})
        overlay.save(args.output / "overlays" / f"{index:03d}.jpg", quality=92)
        tile = Image.new("RGB", (600, 660), "white")
        tile.paste(overlay, ((600-overlay.width)//2,0))
        label=f"{index:03d} {row['session_id']} {row['species_code']} {row['filename']}"
        text = f"{label}\nRED rim proposal / GREEN vegetation / CYAN approximate pilot\n{result['algorithm_status']}"
        if result["algorithm_status"] == "circle_proposed":
            text += f" support={result['algorithm_diagnostics']['angular_edge_support']:.2f}"
        ImageDraw.Draw(tile).text((5,610),text,fill="black")
        tiles.append(tile)
        if len(tiles)==9 or index==len(rows):
            page = Image.new("RGB",(1800,1980),"white")
            for j,tile_image in enumerate(tiles):page.paste(tile_image,((j%3)*600,(j//3)*660))
            page.save(args.output/f"contact_{(index-1)//9+1:02d}.jpg",quality=92)
            tiles=[]
            print(f"processed {index}/{len(rows)}", flush=True)
    (args.output/"geometry_proposals.json").write_text(json.dumps(proposals,ensure_ascii=False,indent=2),encoding="utf-8")
    report={"created_utc":datetime.now(timezone.utc).isoformat(),"opencv":cv2.__version__,"numpy":np.__version__,
       "selection_sha256":digest(args.selection),"script_sha256":digest(__file__),"rows":len(rows),
       "counts":dict(Counter(p["algorithm_status"] for p in proposals)),"review_status":"all_algorithm_unreviewed",
       "pilot_comparison":contrasts,"other_partitions_opened":False,
       "limitations":["Hough may select inner rim, shadow or unrelated circle; no automatic approval",
       "Green mask may omit yellow/red/dry tissue and include unrelated vegetation; bbox requires visual review",
       "Pilot points are approximate, non-independent annotations, not measurement ground truth"]}
    (args.output/"run.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":main()
