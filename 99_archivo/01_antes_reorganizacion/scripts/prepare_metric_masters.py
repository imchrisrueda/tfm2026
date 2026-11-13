"""Create traceable metric masters only from explicitly reviewed geometry.

Never rewrites authoritative manifests or partition assignments. Coordinates refer
to the EXIF-oriented image, with continuous pixel-edge coordinates [0,w] x [0,h].
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import platform

import PIL
from PIL import Image, ImageCms, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def yes(value):
    return value is True or str(value).lower() in {"true", "1", "yes"}


def finite(value, positive=False):
    value = float(value)
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError("Non-finite or non-positive geometry")
    return value


def read_records(path):
    path = Path(path)
    if path.suffix.lower() == ".json":
        rows = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(rows, list):
            raise ValueError("JSON annotations/manifest must be a list")
        return rows
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def field_for_year(config, year):
    """Explicit year mapping takes precedence; missing mapped years fail closed.

    Legacy field_cm is supported only if no year mapping is supplied, so a newly
    encountered year cannot silently inherit an unintended physical field.
    """
    fields = config.get("field_cm_by_year")
    if fields is not None:
        if not isinstance(fields, dict) or str(year) not in fields:
            raise ValueError("year_missing_from_field_cm_by_year: " + str(year))
        return finite(fields[str(year)], True), "field_cm_by_year:" + str(year)
    return finite(config["field_cm"], True), "field_cm_global"


def crop_geometry(annotation, nominal_cm, field_cm, output_px, width, height, margin_cm=0):
    """Reject insufficient capture coverage and vegetation loss; never pad."""
    diameter = finite(annotation["pot_diameter_px"], True)
    nominal_cm = finite(nominal_cm, True)
    field_cm = finite(field_cm, True)
    if field_cm < nominal_cm:
        raise ValueError("field_smaller_than_nominal_pot")
    cx, cy = (finite(annotation[key]) for key in ("pot_center_x_px", "pot_center_y_px"))
    if not 0 <= cx <= width or not 0 <= cy <= height:
        raise ValueError("Pot center outside oriented source")
    scale = diameter / nominal_cm
    side = field_cm * scale
    box = [cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2]
    if box[0] < 0 or box[1] < 0 or box[2] > width or box[3] > height:
        raise ValueError("incomplete_source_coverage")
    vegetation = annotation["vegetation_bbox"]
    if isinstance(vegetation, str):
        vegetation = json.loads(vegetation)
    if len(vegetation) != 4:
        raise ValueError("vegetation_bbox requires four coordinates")
    x0, y0, x1, y1 = map(finite, vegetation)
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError("Invalid vegetation bbox")
    margin = finite(margin_cm) * scale
    if margin < 0:
        raise ValueError("Negative vegetation margin")
    if x0 - margin < box[0] or y0 - margin < box[1] or x1 + margin > box[2] or y1 + margin > box[3]:
        raise ValueError("vegetation_or_margin_outside_crop")
    return {"crop_box_oriented_px": box, "crop_side_px": side,
            "source_px_per_cm": scale, "output_px_per_cm": output_px / field_cm,
            "resize_factor": output_px / side,
            "expected_pot_diameter_output_px": output_px * nominal_cm / field_cm,
            "vegetation_bbox_oriented_px": [x0, y0, x1, y1]}


def oriented_srgb(source):
    """Fail closed on invalid embedded ICC, retain explicit no-profile assumption."""
    oriented = ImageOps.exif_transpose(source)
    profile = source.info.get("icc_profile")
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
    if profile:
        rgb = ImageCms.profileToProfile(oriented, ImageCms.ImageCmsProfile(io.BytesIO(profile)), srgb, outputMode="RGB")
        status = "embedded_ICC_converted_to_sRGB"
    else:
        if oriented.mode not in {"RGB", "L"}:
            raise ValueError("No ICC profile for unsupported color mode")
        rgb = oriented.convert("RGB")
        status = "no_ICC_assumed_sRGB_not_colorimetrically_validated"
    return rgb, status, srgb.tobytes()


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                             for key, value in row.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/processed/manifest_all.csv")
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["pilot", "apply"], default="pilot")
    parser.add_argument("--include-test", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    if "field_cm_by_year" in config:
        if not isinstance(config["field_cm_by_year"], dict) or not config["field_cm_by_year"]:
            raise ValueError("field_cm_by_year must be a non-empty mapping")
        for configured_field in config["field_cm_by_year"].values():
            finite(configured_field, True)
    else:
        finite(config["field_cm"], True)
    pixels = config["output_px"]
    if isinstance(pixels, bool) or not isinstance(pixels, int) or pixels <= 0:
        raise ValueError("output_px must be a positive integer")
    if args.mode == "apply" and config.get("status") != "frozen":
        raise ValueError("apply requires status=frozen")
    if args.include_test and (args.mode != "apply" or config.get("status") != "frozen"):
        raise ValueError("T_real requires explicit apply with frozen config")
    manifest = read_records(args.manifest)
    if len({row["image_id"] for row in manifest}) != len(manifest):
        raise ValueError("Duplicate manifest image_id")
    annotation_rows = read_records(args.annotations)
    annotations = {row["image_id"]: row for row in annotation_rows}
    if len(annotations) != len(annotation_rows):
        raise ValueError("Duplicate annotation image_id")
    if set(annotations) - {row["image_id"] for row in manifest}:
        raise ValueError("Unknown annotated image_id")
    args.output = args.output.resolve()
    args.output.relative_to(ROOT.resolve())
    # New output directory prevents replacing previous experiment evidence.
    args.output.mkdir(parents=True, exist_ok=False)
    master_dir = args.output / "masters"
    master_dir.mkdir()
    config_hash = digest(args.config)
    output_rows = []
    for original in manifest:
        row = dict(original)
        row.update({"preprocessing_status": "pending_geometry_review", "master_image_path": "",
                    "metric_config_sha256": config_hash, "metric_annotation": None})
        annotation = annotations.get(row["image_id"])
        if not yes(row["use_in_assigned_partition"]):
            row["preprocessing_status"] = "inactive_partition_image"
        elif row["split_assignment"] == "T_real" and not args.include_test:
            row["preprocessing_status"] = "held_out_T_real_not_opened"
        elif args.mode == "pilot" and not (row["split_assignment"] == "C_fit" or
                (row["split_assignment"] == "C_val" and row["validation_role"] == "model_selection")):
            row["preprocessing_status"] = "not_development_role"
        elif annotation:
            row["metric_annotation"] = annotation
            try:
                field, field_source = field_for_year(config, row.get("year", ""))
                row.update({"common_field_cm": field, "metric_field_source": field_source})
                if annotation.get("coordinate_space") != "exif_oriented":
                    raise ValueError("coordinate_space must be exif_oriented")
                if annotation.get("review_status") != "accepted" or annotation.get("reference_quality") != "usable":
                    raise ValueError("reference_not_reviewed_usable")
                if not annotation.get("reviewer") or not annotation.get("review_date"):
                    raise ValueError("reviewer_and_date_required")
                if args.mode == "apply" and annotation.get("measurement_scope") == "pilot_only":
                    raise ValueError("pilot_only_measurement_requires_production_review")
                if str(annotation.get("vegetation_truncated", "")).lower() not in {"false", "0"}:
                    raise ValueError("vegetation_truncated_or_not_reviewed")
                source = (ROOT / row["source_path"]).resolve()
                source.relative_to(ROOT.resolve())
                source_hash = digest(source)
                if source_hash != row["sha256"] or source_hash != annotation.get("source_sha256"):
                    raise ValueError("source_hash_mismatch")
                with Image.open(source) as image:
                    rgb, color_status, srgb_profile = oriented_srgb(image)
                width, height = rgb.size
                if (width, height) != (int(row["oriented_width"]), int(row["oriented_height"])):
                    raise ValueError("oriented_dimensions_mismatch")
                diameter = finite(annotation["pot_diameter_px"], True)
                nominal = finite(row["pot_diameter_exterior_cm"], True)
                cx, cy = (finite(annotation[key]) for key in ("pot_center_x_px", "pot_center_y_px"))
                if not 0 <= cx <= width or not 0 <= cy <= height:
                    raise ValueError("Pot center outside oriented source")
                side = field * diameter / nominal
                # A failed field-coverage check does not invalidate an observed rim
                # measurement. Keep it distinguishable from an absent measurement.
                row.update({"geometry_status": "reviewed_apparent_rim_scale",
                            "pot_center_x_px": cx, "pot_center_y_px": cy,
                            "pot_diameter_px": diameter, "scale_cm_per_px": nominal / diameter,
                            "geometry_reference_quality": "usable", "common_field_cm": field,
                            "measurement_scope": annotation.get("measurement_scope", "not_specified"),
                            "source_px_per_cm": diameter / nominal,
                            "crop_box_oriented_px": [cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2],
                            "crop_side_px": side})
                geometry = crop_geometry(annotation, row["pot_diameter_exterior_cm"], field, pixels,
                                         width, height, config.get("minimum_vegetation_margin_cm", 0))
                # Pillow fractional box preserves the exact common field; no rounded crop or anisotropy.
                master = rgb.resize((pixels, pixels), Image.Resampling.LANCZOS,
                                    box=tuple(geometry["crop_box_oriented_px"]))
                filename = hashlib.sha256(row["image_id"].encode()).hexdigest()[:24] + ".png"
                target = master_dir / filename
                master.save(target, icc_profile=srgb_profile)
                row.update(geometry)
                row.update({"master_image_path": target.resolve().relative_to(ROOT.resolve()).as_posix(),
                            "master_sha256": digest(target), "preprocessing_status": "pilot_master_created" if args.mode == "pilot" else "master_created",
                            "color_processing": color_status, "common_field_cm": field,
                            "master_width": pixels, "master_height": pixels,
                            "geometry_status": "reviewed_apparent_rim_scale",
                            "pot_center_x_px": annotation["pot_center_x_px"],
                            "pot_center_y_px": annotation["pot_center_y_px"],
                            "pot_diameter_px": annotation["pot_diameter_px"],
                            "scale_cm_per_px": 1 / geometry["source_px_per_cm"],
                            "geometry_reference_quality": "usable"})
            except (ValueError, KeyError, TypeError, OSError, ImageCms.PyCMSError) as error:
                row["preprocessing_status"] = "not_eligible_or_processing_error"
                row["preprocessing_reason"] = str(error)
        output_rows.append(row)
    (args.output / "manifest_metric.json").write_text(json.dumps(output_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(args.output / "manifest_metric.csv", output_rows)
    report = {"created_utc": datetime.now(timezone.utc).isoformat(), "mode": args.mode,
              "config": config, "manifest_sha256": digest(args.manifest), "annotations_sha256": digest(args.annotations),
              "config_sha256": config_hash, "script_sha256": digest(__file__), "python": platform.python_version(),
              "pillow": PIL.__version__, "counts": dict(Counter(row["preprocessing_status"] for row in output_rows)),
              "total_rows": len(output_rows), "annotations": len(annotations),
              "failure_reasons": dict(Counter(row["preprocessing_reason"] for row in output_rows if row.get("preprocessing_reason"))),
              "reviewed_geometry_rows": sum(row.get("geometry_status") == "reviewed_apparent_rim_scale" for row in output_rows),
              "T_real_opened": args.include_test, "partition_assignments_modified": False,
              "scale_scope": "apparent_scale_at_outer_rim_plane_not_3D_plant_dimensions"}
    (args.output / "run.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
