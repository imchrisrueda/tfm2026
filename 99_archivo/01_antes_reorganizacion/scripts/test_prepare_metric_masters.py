"""Synthetic verification: geometry, reference-plane scale, color and partition gates."""
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageCms

SCRIPT = Path(__file__).with_name("prepare_metric_masters.py")
spec = importlib.util.spec_from_file_location("metric", SCRIPT)
metric = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metric)


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.annotation = {"pot_diameter_px": 100, "pot_center_x_px": 300.25,
                           "pot_center_y_px": 300.25, "vegetation_bbox": [200, 200, 400, 400]}

    def test_same_cm_per_pixel_retains_two_pot_sizes(self):
        small = metric.crop_geometry(self.annotation, 10, 40, 1024, 1000, 1000)
        large_ann = dict(self.annotation, pot_diameter_px=200)
        large = metric.crop_geometry(large_ann, 20, 40, 1024, 1000, 1000)
        self.assertEqual(small["crop_box_oriented_px"], large["crop_box_oriented_px"])
        self.assertEqual(small["expected_pot_diameter_output_px"], 256)
        self.assertEqual(large["expected_pot_diameter_output_px"], 512)
        self.assertEqual(small["output_px_per_cm"], large["output_px_per_cm"])
        self.assertEqual(small["crop_box_oriented_px"][0], 100.25)

    def test_incomplete_capture_never_padded(self):
        with self.assertRaisesRegex(ValueError, "incomplete_source_coverage"):
            metric.crop_geometry(dict(self.annotation, pot_center_x_px=100), 10, 40, 1024, 1000, 1000)

    def test_vegetation_and_margin_must_fit(self):
        with self.assertRaisesRegex(ValueError, "vegetation_or_margin_outside_crop"):
            metric.crop_geometry(dict(self.annotation, vegetation_bbox=[90, 100, 400, 400]), 10, 40, 1024, 1000, 1000)
        with self.assertRaisesRegex(ValueError, "vegetation_or_margin_outside_crop"):
            metric.crop_geometry(self.annotation, 10, 40, 1024, 1000, 1000, margin_cm=11)

    def test_bad_measurement_rejected(self):
        for value in [float("nan"), float("inf"), 0, -1]:
            with self.assertRaises(ValueError):
                metric.crop_geometry(dict(self.annotation, pot_diameter_px=value), 10, 40, 1024, 1000, 1000)

    def test_field_cannot_cut_nominal_pot(self):
        with self.assertRaisesRegex(ValueError, "field_smaller_than_nominal_pot"):
            metric.crop_geometry(self.annotation, 20, 19.9, 1024, 1000, 1000)

    def test_explicit_fields_by_year_have_distinct_scales(self):
        config = {"field_cm_by_year": {"2025": 12, "2026": 22}, "field_cm": 40}
        small_field, _ = metric.field_for_year(config, 2025)
        large_field, _ = metric.field_for_year(config, "2026")
        small = metric.crop_geometry(dict(self.annotation, vegetation_bbox=[290, 290, 310, 310]), 10, small_field, 1024, 1000, 1000)
        large = metric.crop_geometry(dict(self.annotation, vegetation_bbox=[290, 290, 310, 310]), 20, large_field, 1024, 1000, 1000)
        self.assertNotEqual(small["output_px_per_cm"], large["output_px_per_cm"])
        self.assertAlmostEqual(small["expected_pot_diameter_output_px"], 1024 * 10 / 12)
        self.assertAlmostEqual(large["expected_pot_diameter_output_px"], 1024 * 20 / 22)
        with self.assertRaisesRegex(ValueError, "year_missing"):
            metric.field_for_year(config, 2027)
        self.assertEqual(metric.field_for_year({"field_cm": 40}, 2025), (40, "field_cm_global"))

    def test_exif_orientation_and_color(self):
        source = Image.new("RGB", (80, 40), "red")
        source.getexif()[274] = 6
        result, status, profile = metric.oriented_srgb(source)
        self.assertEqual(result.size, (40, 80))
        self.assertIn("assumed_sRGB", status)
        self.assertTrue(profile)
        source.info["icc_profile"] = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        _, status, _ = metric.oriented_srgb(source)
        self.assertEqual(status, "embedded_ICC_converted_to_sRGB")
        source.info["icc_profile"] = b"invalid"
        with self.assertRaises((OSError, ImageCms.PyCMSError)):
            metric.oriented_srgb(source)

    def test_cli_partition_gates_and_traceability(self):
        with tempfile.TemporaryDirectory(prefix="metric_test_", dir=metric.ROOT / "scratch") as tmp:
            tmp = Path(tmp)
            image = tmp / "original.png"
            Image.new("RGB", (100, 100), (30, 130, 20)).save(image)
            source_hash = metric.digest(image)
            rows = []
            for identifier, role, active in [("fit", "C_fit", True), ("test", "T_real", True), ("gen", "G_fit", True), ("excluded", "C_fit", False)]:
                rows.append({"image_id": identifier, "source_path": image.relative_to(metric.ROOT).as_posix(), "sha256": source_hash,
                             "oriented_width": 100, "oriented_height": 100, "pot_diameter_exterior_cm": 10,
                             "use_in_assigned_partition": active, "split_assignment": role, "validation_role": "",
                             "split_group_id": "GROUP_" + identifier})
            (tmp / "manifest.json").write_text(json.dumps(rows), encoding="utf-8")
            ann = {"source_sha256": source_hash, "coordinate_space": "exif_oriented", "review_status": "accepted",
                   "reference_quality": "usable", "reviewer": "synthetic_unit_test", "review_date": "2026-11-12",
                   "pot_center_x_px": 50, "pot_center_y_px": 50, "pot_diameter_px": 20,
                   "vegetation_truncated": False, "vegetation_bbox": [30, 30, 70, 70]}
            (tmp / "annotations.json").write_text(json.dumps([dict(ann, image_id=r["image_id"]) for r in rows]), encoding="utf-8")
            (tmp / "config.json").write_text(json.dumps({"field_cm": 40, "output_px": 64, "status": "pilot"}), encoding="utf-8")
            command = [sys.executable, str(SCRIPT), "--manifest", str(tmp / "manifest.json"), "--annotations", str(tmp / "annotations.json"),
                       "--config", str(tmp / "config.json"), "--output", str(tmp / "out")]
            subprocess.run(command, check=True, capture_output=True)
            results = json.loads((tmp / "out/manifest_metric.json").read_text(encoding="utf-8"))
            self.assertEqual([r["preprocessing_status"] for r in results], ["pilot_master_created", "held_out_T_real_not_opened", "not_development_role", "inactive_partition_image"])
            self.assertEqual([r["split_group_id"] for r in results], [r["split_group_id"] for r in rows])
            self.assertEqual(metric.digest(image), source_hash)
            with Image.open(metric.ROOT / results[0]["master_image_path"]) as master:
                self.assertEqual(master.size, (64, 64))
                self.assertTrue(master.info.get("icc_profile"))
            # Explicit flag does not bypass the frozen-configuration gate.
            self.assertNotEqual(subprocess.run(command + ["--include-test"], capture_output=True).returncode, 0)
            # A valid rim measurement survives a rejected field window.
            annotations = [dict(ann, image_id=r["image_id"], pot_center_x_px=10) for r in rows]
            (tmp / "annotations.json").write_text(json.dumps(annotations), encoding="utf-8")
            rejected_command = command[:-1] + [str(tmp / "rejected")]
            subprocess.run(rejected_command, check=True, capture_output=True)
            rejected = json.loads((tmp / "rejected/manifest_metric.json").read_text(encoding="utf-8"))[0]
            self.assertEqual(rejected["preprocessing_reason"], "incomplete_source_coverage")
            self.assertEqual(rejected["geometry_status"], "reviewed_apparent_rim_scale")
            self.assertEqual(rejected["pot_diameter_px"], 20)
            self.assertEqual(rejected["scale_cm_per_px"], 0.5)
            self.assertFalse(rejected["master_image_path"])
            # A frozen configuration cannot promote provisional geometry.
            (tmp / "config.json").write_text(json.dumps({"field_cm": 40, "output_px": 64, "status": "frozen"}), encoding="utf-8")
            (tmp / "annotations.json").write_text(json.dumps([dict(ann, image_id=r["image_id"], measurement_scope="pilot_only") for r in rows]), encoding="utf-8")
            apply_command = command[:-1] + [str(tmp / "apply"), "--mode", "apply"]
            subprocess.run(apply_command, check=True, capture_output=True)
            applied = json.loads((tmp / "apply/manifest_metric.json").read_text(encoding="utf-8"))
            self.assertEqual(applied[0]["preprocessing_reason"], "pilot_only_measurement_requires_production_review")
            self.assertFalse(list((tmp / "apply/masters").glob("*.png")))


if __name__ == "__main__":
    unittest.main()
