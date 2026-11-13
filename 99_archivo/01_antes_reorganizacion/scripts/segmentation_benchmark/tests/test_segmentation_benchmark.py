"""Unit tests for segmentation_benchmark_v1."""
from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

PKG_DIR = Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

from common import (  # noqa: E402
    clip_box,
    norm_cxcywh_to_xyxy,
    oriented_srgb,
    present_isotropic,
    xyxy_to_norm_cxcywh,
)
from render_views import apply_exterior_fill, compute_w_sam  # noqa: E402
from run_methods import (  # noqa: E402
    associate_sam3_instances,
    run_sam3_independent_prompts,
    verify_freeze_for_evaluation,
)
from score import (  # noqa: E402
    compute_mask_metrics,
    compute_support_metrics,
    stratified_paired_bootstrap,
    wilson_ci,
)


class _DummySam3Processor:
    """Tracks set_image / set_text_prompt calls to verify zero state leakage."""

    def __init__(self):
        self.states = []
        self.calls = []

    def set_image(self, rgb):
        state = {"id": len(self.states), "history": [], "size": rgb.size}
        self.states.append(state)
        return state

    def set_text_prompt(self, state, prompt):
        assert len(state["history"]) == 0, f"Prompt state leaked prior history: {state['history']}"
        state["history"].append(prompt)
        self.calls.append((state["id"], prompt))
        w, h = state["size"]
        m = np.zeros((h, w), dtype=bool)
        if prompt == "plant":
            m[10:20, 10:20] = True
            return {"masks": [m], "scores": [0.9], "boxes": [[10, 10, 20, 20]]}
        m[15:30, 15:30] = True
        return {"masks": [m], "scores": [0.85], "boxes": [[15, 15, 30, 30]]}


class TestSegmentationBenchmark(unittest.TestCase):
    def test_fine_mask_not_erased(self):
        # 1-px thin stem line across 100x100 mask
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[50, 10:90] = 255
        img = Image.fromarray(mask, mode="L")
        out, meta = present_isotropic(img, [0, 0, 100, 100], 100, is_mask=True)
        arr = np.array(out)
        self.assertEqual(arr.shape, (100, 100))
        self.assertEqual(int(np.sum(arr == 255)), 80)
        self.assertEqual(meta["scale"], 1.0)

    def test_exif_rotation_and_oriented_coords(self):
        # Raw 40x20 image with EXIF Orientation=6 (rotate 270 CW / 90 CCW -> 20x40 oriented)
        raw = Image.new("RGB", (40, 20), (10, 20, 30))
        exif = raw.getexif()
        exif[0x0112] = 6
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "rot.jpg"
            raw.save(p, exif=exif)
            with Image.open(p) as loaded:
                rgb, status, _ = oriented_srgb(loaded)
        self.assertEqual(rgb.size, (20, 40))
        self.assertIn("sRGB", status)

    def test_xyxy_and_norm_cxcywh_roundtrip(self):
        box = [100.0, 50.0, 300.0, 250.0]
        norm = xyxy_to_norm_cxcywh(box, 1000, 500)
        self.assertAlmostEqual(norm[0], 0.2)
        self.assertAlmostEqual(norm[1], 0.3)
        self.assertAlmostEqual(norm[2], 0.2)
        self.assertAlmostEqual(norm[3], 0.4)
        back = norm_cxcywh_to_xyxy(norm, 1000, 500)
        for a, b in zip(box, back):
            self.assertAlmostEqual(a, b, places=6)

    def test_interior_rgb_intact_before_resize(self):
        arr = np.full((20, 20, 3), 200, dtype=np.uint8)
        arr[5:10, 5:10] = [12, 34, 56]
        rgb = Image.fromarray(arr, mode="RGB")
        keep = np.zeros((20, 20), dtype=bool)
        keep[5:10, 5:10] = True
        masked = apply_exterior_fill(rgb, keep, fill_rgb=(127, 127, 127))
        out = np.array(masked)
        self.assertTrue(np.all(out[5:10, 5:10] == np.array([12, 34, 56])))
        self.assertTrue(np.all(out[0:5, 0:5] == np.array([127, 127, 127])))

    def test_isotropic_aspect_and_no_implicit_crop(self):
        rgb = Image.new("RGB", (200, 100), (255, 0, 0))
        view, meta = present_isotropic(rgb, [0, 0, 200, 100], 100, fill_rgb=(127, 127, 127), is_mask=False)
        self.assertEqual(view.size, (100, 100))
        self.assertAlmostEqual(meta["scale"], 0.5)
        self.assertAlmostEqual(meta["canvas_valid_fraction"], 0.5)
        arr = np.array(view)
        # Top padding row must be 127, center row must be red
        self.assertTrue(np.all(arr[0, 50] == np.array([127, 127, 127])))
        self.assertTrue(np.all(arr[50, 50] == np.array([255, 0, 0])))

    def test_margin_clipped_to_capture(self):
        union = np.zeros((100, 100), dtype=bool)
        union[0:80, 0:80] = True
        w_sam = compute_w_sam(union, 100, 100, margin_frac=0.10)
        self.assertEqual(w_sam, [0.0, 0.0, 88.0, 88.0])
        self.assertEqual(clip_box([-10, -5, 120, 110], 100, 100), [0.0, 0.0, 100.0, 100.0])

    def test_no_prompt_state_leakage(self):
        proc = _DummySam3Processor()
        rgb = Image.new("RGB", (40, 40), (0, 0, 0))
        out = run_sam3_independent_prompts(rgb, proc, "plant", "soil", 0.5, 0.5)
        self.assertEqual(proc.calls, [(0, "plant"), (1, "soil")])
        self.assertEqual(len(out["plant_masks"]), 1)
        self.assertEqual(len(out["soil_masks"]), 1)

    def test_sam3_association_keeps_whole_plant_instance(self):
        # Soil in center [40:60, 40:60], plant extends outside circle [5:55, 45:55]
        soil = np.zeros((100, 100), dtype=bool)
        soil[40:60, 40:60] = True
        plant = np.zeros((100, 100), dtype=bool)
        plant[5:55, 45:55] = True
        res = associate_sam3_instances([plant], [0.9], [soil], [0.8], [50.0, 50.0, 20.0], 100, 100)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(int(np.sum(res["plant_mask"])), int(np.sum(plant)))
        # Priority plant > soil in semantic soil_mask
        self.assertEqual(int(np.sum(res["plant_mask"] & res["soil_mask"])), 0)
        # Missing anchor -> uncertain_no_anchor
        res_none = associate_sam3_instances([plant], [0.9], [soil], [0.8], None, 100, 100)
        self.assertEqual(res_none["status"], "uncertain_no_anchor")

    def test_metrics_empty_gt_empty_pred_and_ignore(self):
        valid = np.ones((20, 20), dtype=bool)
        valid[0:5, 0:5] = False  # ignore_uncertain
        gt_empty = np.zeros((20, 20), dtype=bool)
        pred_some = np.zeros((20, 20), dtype=bool)
        pred_some[10:12, 10:12] = True
        m_empty_gt = compute_mask_metrics(pred_some, gt_empty, valid, 1)
        self.assertTrue(math.isnan(m_empty_gt["recall"]))
        self.assertTrue(math.isnan(m_empty_gt["dice"]))

        gt = np.zeros((20, 20), dtype=bool)
        gt[10:15, 10:15] = True
        m_empty_pred = compute_mask_metrics(np.zeros((20, 20), dtype=bool), gt, valid, 1)
        self.assertEqual(m_empty_pred["recall"], 0.0)
        self.assertEqual(m_empty_pred["dice"], 0.0)
        self.assertEqual(m_empty_pred["iou"], 0.0)
        self.assertTrue(math.isnan(m_empty_pred["precision"]))

        # Support metrics & fine points
        layers = {
            "plant_target": gt,
            "soil_target": np.zeros((20, 20), dtype=bool),
            "other_plant": np.zeros((20, 20), dtype=bool),
            "pot_rim_wall": np.zeros((20, 20), dtype=bool),
            "card_label": np.zeros((20, 20), dtype=bool),
            "other_background": ~gt,
            "ignore_uncertain": ~valid,
        }
        pts = [{"x": 12.0, "y": 12.0, "status": "evaluable"}]
        sup = compute_support_metrics(gt, layers, valid, pts, 1)
        self.assertAlmostEqual(sup["tissue_retention"], 1.0)
        self.assertAlmostEqual(sup["fine_point_retention_exact"], 1.0)
        self.assertAlmostEqual(sup["contamination_plant_only"], 0.0)

    def test_deterministic_bootstrap_and_wilson(self):
        recs = [
            {"year": 2025, "species_code": "P", "a": 0.99, "b": 0.95},
            {"year": 2025, "species_code": "P", "a": 0.98, "b": 0.96},
            {"year": 2026, "species_code": "H", "a": 1.00, "b": 0.97},
            {"year": 2026, "species_code": "H", "a": 0.99, "b": 0.98},
        ]
        b1 = stratified_paired_bootstrap(recs, "ret", n_resamples=200, seed="seed1")
        b2 = stratified_paired_bootstrap(recs, "ret", n_resamples=200, seed="seed1")
        self.assertEqual(b1, b2)
        p, lo, hi = wilson_ci(0, 24)
        self.assertEqual(p, 0.0)
        self.assertAlmostEqual(hi, 0.138, places=2)

    def test_evaluation_blocked_without_freeze(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(RuntimeError):
                verify_freeze_for_evaluation(Path(td))


if __name__ == "__main__":
    unittest.main()
