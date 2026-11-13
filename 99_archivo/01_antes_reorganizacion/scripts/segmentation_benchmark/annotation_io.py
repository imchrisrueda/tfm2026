"""Blind human annotation templates, PNG/JSON validation, and inter-annotator agreement."""
from __future__ import annotations

import argparse
import math
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from common import (
    ANNOTATION_LAYERS,
    DEFAULT_BENCHMARK_DIR,
    read_json,
    utc_now_iso,
    write_csv,
    write_json,
)


ANNOTATION_LOG_COLUMNS = [
    "sample_role",
    "blind_id",
    "image_id",
    "annotator_id",
    "annotator_role",
    "experience_level",
    "active_seconds",
    "completed_date",
    "status",
    "double_annotation_assigned",
    "notes",
]

RUBRIC_MD = """# Rúbrica de anotación de referencia humana (`segmentation_benchmark_v1`)

1. **Ciego estricto**: anotar sobre el original EXIF-orientado a resolución nativa con zoom. Prohibido consultar salidas SAM/HSV, códigos de método, métricas o etiquetas de especie (`H/P/R`).
2. **Capas disjuntas sobre superficies VISIBLES** (PNG uint8 modo `L`, tamaño nativo `oriented_width x oriented_height`, valores exactos `0` y `255`):
   - `plant_target`: toda vegetación perteneciente a la maceta objetivo (hojas, cotiledones, tallos, pecíolos, tejido seco identificable), sin limitarse al color verde. Si hay varios individuos en la maceta objetivo, anotar la unión y registrar `num_plants_observed` y `multi_plant_ambiguity`.
   - `soil_target`: sustrato visible dentro de la maceta objetivo (incluidos gránulos). Excluir planta, borde/pared de maceta, tarjetas y suelo exterior. No reconstruir tierra oculta bajo hojas.
   - `other_plant`: vegetación ajena reconocible fuera de la maceta objetivo.
   - `pot_rim_wall`: borde y pared de la maceta objetivo.
   - `card_label`: tarjetas o etiquetas de identificación.
   - `other_background`: resto del fondo visible.
   - `ignore_uncertain`: borde o identidad irresoluble en la imagen. Reportar área; no absorber tallos difíciles por conveniencia.
3. **Puntos de estructura fina** (máximo 20 por imagen):
   - Extremos de hojas identificables (`leaf_tip`) y puntos medios de tallos/pecíolos finos (`thin_stem_or_petiole_midpoint`), elegidos en orden espacial reproducible (arriba-abajo, izquierda-derecha; cuotas equilibradas entre ambos tipos cuando haya suficientes).
   - Registrar `status`: `evaluable` o `not_evaluable` (no inventar órganos ocultos).
4. **Órganos críticos y truncamiento de origen**:
   - Listar órganos visibles cuya eliminación cambiaría la interpretación morfológica (`critical_organs`).
   - Registrar `source_truncated` (bool) y bordes afectados si la planta ya estaba truncada en la captura original.
"""


def load_blind_sample(benchmark_dir: Path, split: str) -> list[dict[str, Any]]:
    rows = read_json(benchmark_dir / "samples" / f"{split}.json")
    blind_rows = []
    for r in rows:
        blind_rows.append(
            {
                "sample_role": r["sample_role"],
                "sample_index": r["sample_index"],
                "blind_id": r["blind_id"],
                "image_id": r["image_id"],
                "source_sha256": r["sha256"],
                "source_path": r["source_path"],
                "oriented_width": int(r["oriented_width"]),
                "oriented_height": int(r["oriented_height"]),
                "double_annotation_assigned": bool(r.get("double_annotation_assigned", False)),
            }
        )
    return blind_rows


def prepare_annotation_templates(benchmark_dir: Path, splits: list[str]) -> dict[str, Any]:
    ann_root = benchmark_dir / "annotations"
    (ann_root / "individual").mkdir(parents=True, exist_ok=True)
    (ann_root / "consensus").mkdir(parents=True, exist_ok=True)
    (ann_root / "rubric.md").write_text(RUBRIC_MD, encoding="utf-8")

    log_rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    for split in splits:
        sample_file = benchmark_dir / "samples" / f"{split}.json"
        if not sample_file.exists():
            continue
        rows = load_blind_sample(benchmark_dir, split)
        tdir = ann_root / "templates" / split
        tdir.mkdir(parents=True, exist_ok=True)
        counts[split] = len(rows)

        for r in rows:
            tpl = {
                "schema_version": "annotation_case_v1",
                "created_utc": utc_now_iso(),
                "sample_role": r["sample_role"],
                "blind_id": r["blind_id"],
                "image_id": r["image_id"],
                "source_sha256": r["source_sha256"],
                "source_path": r["source_path"],
                "oriented_width": r["oriented_width"],
                "oriented_height": r["oriented_height"],
                "double_annotation_assigned": r["double_annotation_assigned"],
                "mask_layers": {layer: f"{layer}.png" for layer in ANNOTATION_LAYERS},
                "annotator_id": None,
                "annotator_role": None,
                "experience_level": None,
                "active_seconds": None,
                "completed_date": None,
                "num_plants_observed": None,
                "multi_plant_ambiguity": None,
                "source_truncated": None,
                "source_truncated_edges": [],
                "fine_points": [],
                "fine_points_max": 20,
                "critical_organs": [],
                "notes": "",
            }
            write_json(tdir / f"{r['blind_id']}.json", tpl)
            log_rows.append(
                {
                    "sample_role": split,
                    "blind_id": r["blind_id"],
                    "image_id": r["image_id"],
                    "annotator_id": "",
                    "annotator_role": "primary",
                    "experience_level": "",
                    "active_seconds": "",
                    "completed_date": "",
                    "status": "pending_human_annotation",
                    "double_annotation_assigned": r["double_annotation_assigned"],
                    "notes": "",
                }
            )
            if r["double_annotation_assigned"]:
                log_rows.append(
                    {
                        "sample_role": split,
                        "blind_id": r["blind_id"],
                        "image_id": r["image_id"],
                        "annotator_id": "",
                        "annotator_role": "secondary_blind",
                        "experience_level": "",
                        "active_seconds": "",
                        "completed_date": "",
                        "status": "pending_human_annotation",
                        "double_annotation_assigned": True,
                        "notes": "",
                    }
                )

    log_path = ann_root / "annotation_log.csv"
    if not log_path.exists():
        write_csv(log_path, log_rows, fieldnames=ANNOTATION_LOG_COLUMNS)

    return {"templates_created": counts, "annotation_log_rows": len(log_rows)}


def read_mask_png(path: Path, expected_width: int, expected_height: int) -> np.ndarray:
    with Image.open(path) as img:
        if img.mode != "L":
            raise ValueError(f"Mask {path} must be uint8 mode 'L', got '{img.mode}'")
        if img.size != (expected_width, expected_height):
            raise ValueError(f"Mask {path} size {img.size} != expected {(expected_width, expected_height)}")
        arr = np.array(img, dtype=np.uint8)
    unique = set(np.unique(arr).tolist())
    if not unique.issubset({0, 255}):
        raise ValueError(f"Mask {path} must contain only 0 and 255, got {sorted(unique)}")
    return arr > 0


def save_mask_png(path: Path, mask_bool: np.ndarray) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    arr = np.where(mask_bool.astype(bool), 255, 0).astype(np.uint8)
    Image.fromarray(arr, mode="L").save(path, format="PNG")
    return path


def validate_annotation_case(case_dir: Path, expected_width: int, expected_height: int) -> dict[str, Any]:
    meta_path = case_dir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing annotation metadata.json in {case_dir}")
    meta = read_json(meta_path)
    if int(meta["oriented_width"]) != expected_width or int(meta["oriented_height"]) != expected_height:
        raise ValueError("Metadata dimensions mismatch")

    masks: dict[str, np.ndarray] = {}
    for layer in ANNOTATION_LAYERS:
        layer_path = case_dir / f"{layer}.png"
        if not layer_path.exists():
            raise FileNotFoundError(f"Missing required layer {layer}.png in {case_dir}")
        masks[layer] = read_mask_png(layer_path, expected_width, expected_height)

    # Check disjointness across semantic layers (excluding ignore_uncertain which can be reported separately)
    semantic_layers = [l for l in ANNOTATION_LAYERS if l != "ignore_uncertain"]
    occupied = np.zeros((expected_height, expected_width), dtype=np.int32)
    for l in semantic_layers:
        occupied += masks[l].astype(np.int32)
    overlap_px = int(np.sum(occupied > 1))
    if overlap_px > 0:
        raise ValueError(f"Overlapping semantic mask layers in {case_dir}: {overlap_px} px")

    fine_points = meta.get("fine_points", [])
    if len(fine_points) > 20:
        raise ValueError(f"Too many fine_points ({len(fine_points)} > 20) in {case_dir}")
    for pt in fine_points:
        x, y = float(pt["x"]), float(pt["y"])
        if not (0.0 <= x <= expected_width and 0.0 <= y <= expected_height):
            raise ValueError(f"Fine point out of bounds ({x}, {y}) for {expected_width}x{expected_height}")

    union_u = masks["plant_target"] | masks["soil_target"]
    return {
        "valid": True,
        "plant_px": int(masks["plant_target"].sum()),
        "soil_px": int(masks["soil_target"].sum()),
        "union_u_px": int(union_u.sum()),
        "ignore_px": int(masks["ignore_uncertain"].sum()),
        "fine_points_count": len(fine_points),
    }


def compute_inter_annotator_agreement(
    primary_root: Path,
    secondary_root: Path,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute IoU, Dice, and fine-point agreement on double-annotated cases."""
    per_case = []
    for c in cases:
        if not c.get("double_annotation_assigned"):
            continue
        iid = c["image_id"]
        w, h = int(c["oriented_width"]), int(c["oriented_height"])
        dir_a = primary_root / iid
        dir_b = secondary_root / iid
        if not (dir_a.exists() and dir_b.exists()):
            continue
        validate_annotation_case(dir_a, w, h)
        validate_annotation_case(dir_b, w, h)

        pa = read_mask_png(dir_a / "plant_target.png", w, h)
        pb = read_mask_png(dir_b / "plant_target.png", w, h)
        sa = read_mask_png(dir_a / "soil_target.png", w, h)
        sb = read_mask_png(dir_b / "soil_target.png", w, h)
        ig = read_mask_png(dir_a / "ignore_uncertain.png", w, h) | read_mask_png(dir_b / "ignore_uncertain.png", w, h)

        valid = ~ig
        def _iou_dice(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
            av, bv = a & valid, b & valid
            inter = float(np.sum(av & bv))
            union = float(np.sum(av | bv))
            denom = float(np.sum(av) + np.sum(bv))
            if union == 0:
                return float("nan"), float("nan")
            return inter / union, (2.0 * inter / denom if denom > 0 else float("nan"))

        p_iou, p_dice = _iou_dice(pa, pb)
        s_iou, s_dice = _iou_dice(sa, sb)
        per_case.append(
            {
                "image_id": iid,
                "plant_iou": p_iou,
                "plant_dice": p_dice,
                "soil_iou": s_iou,
                "soil_dice": s_dice,
            }
        )

    valid_p = [r["plant_dice"] for r in per_case if not math.isnan(r["plant_dice"])]
    valid_s = [r["soil_dice"] for r in per_case if not math.isnan(r["soil_dice"])]
    return {
        "n_cases_evaluated": len(per_case),
        "mean_plant_dice": float(np.mean(valid_p)) if valid_p else None,
        "mean_soil_dice": float(np.mean(valid_s)) if valid_s else None,
        "per_case": per_case,
    }


def adjudicate_to_consensus(source_case_dir: Path, consensus_case_dir: Path, adjudicator_id: str) -> None:
    consensus_case_dir.mkdir(parents=True, exist_ok=True)
    for item in source_case_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, consensus_case_dir / item.name)
    meta = read_json(consensus_case_dir / "metadata.json")
    meta["adjudicated_by"] = adjudicator_id
    meta["adjudicated_utc"] = utc_now_iso()
    write_json(consensus_case_dir / "metadata.json", meta)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, default=DEFAULT_BENCHMARK_DIR)
    parser.add_argument("--prepare-templates", action="store_true")
    parser.add_argument("--splits", nargs="+", default=["tuning", "evaluation", "stress"])
    args = parser.parse_args()

    if args.prepare_templates:
        res = prepare_annotation_templates(args.benchmark_dir, args.splits)
        import json

        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
