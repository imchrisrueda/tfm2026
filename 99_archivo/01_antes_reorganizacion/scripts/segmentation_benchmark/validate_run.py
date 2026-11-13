"""Integrity validation, freeze creation, and run receipt for segmentation_benchmark_v1."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import (
    DEFAULT_BENCHMARK_DIR,
    ROOT,
    digest,
    read_json,
    sha256_json,
    utc_now_iso,
    verify_protected_inputs,
    write_json,
)


def validate_benchmark(benchmark_dir: Path) -> dict[str, Any]:
    protected = verify_protected_inputs(ROOT)
    checks: list[dict[str, Any]] = []

    def _check(name: str, ok: bool, detail: Any = None) -> None:
        checks.append({"check": name, "passed": bool(ok), "detail": detail})
        if not ok:
            raise ValueError(f"Validation failed [{name}]: {detail}")

    # 1. Verify sample files and group disjointness
    tuning = read_json(benchmark_dir / "samples/tuning.json")
    evaluation = read_json(benchmark_dir / "samples/evaluation.json")
    stress = read_json(benchmark_dir / "samples/stress.json")

    t_g = {r["split_group_id"] for r in tuning}
    e_g = {r["split_group_id"] for r in evaluation}
    s_g = {r["split_group_id"] for r in stress}

    _check("sample_counts", len(tuning) == 18 and len(evaluation) == 60 and len(stress) == 12,
           {"tuning": len(tuning), "evaluation": len(evaluation), "stress": len(stress)})
    _check("tuning_eval_disjoint_groups", len(t_g & e_g) == 0, len(t_g & e_g))
    _check("stress_eval_disjoint_groups", len(s_g & e_g) == 0, len(s_g & e_g))
    _check("double_annotation_count", sum(1 for r in evaluation if r.get("double_annotation_assigned")) == 20, 20)

    # 2. Verify all selected original files exist and match SHA256
    for role, rows in [("tuning", tuning), ("evaluation", evaluation), ("stress", stress)]:
        for r in rows:
            p = ROOT / r["source_path"]
            if not p.exists():
                _check(f"original_exists_{role}", False, r["source_path"])
            if digest(p) != r["sha256"]:
                _check(f"original_sha_{role}", False, r["image_id"])
    _check("all_selected_originals_verified", True, len(tuning) + len(evaluation) + len(stress))

    # 3. Verify blind templates do not leak species_code or method names
    tpl_eval_dir = benchmark_dir / "annotations/templates/evaluation"
    if tpl_eval_dir.exists():
        for tpl_path in tpl_eval_dir.glob("*.json"):
            tpl = read_json(tpl_path)
            if "species_code" in tpl or "design_species_code" in tpl:
                _check("blind_templates_no_species_leak", False, str(tpl_path))
        _check("blind_templates_no_species_leak", True, len(list(tpl_eval_dir.glob("*.json"))))

    validation = {
        "validated_utc": utc_now_iso(),
        "protected_inputs_verified": True,
        "registry_sha256": protected["registry_sha256"],
        "freeze_exists": (benchmark_dir / "freeze.json").exists(),
        "checks": checks,
        "all_passed": all(c["passed"] for c in checks),
    }
    write_json(benchmark_dir / "validation.json", validation)

    receipt = {
        "created_utc": utc_now_iso(),
        "benchmark_dir": str(benchmark_dir.relative_to(ROOT).as_posix()),
        "validation_sha256": digest(benchmark_dir / "validation.json"),
        "config_sha256": digest(benchmark_dir / "config_draft.json"),
        "sampling_sha256": digest(benchmark_dir / "sampling.json"),
        "code_inventory_sha256": digest(benchmark_dir / "code_inventory.json"),
    }
    write_json(benchmark_dir / "run_receipt.json", receipt)
    return validation


def create_freeze(benchmark_dir: Path) -> Path:
    """Create freeze.json only after calibration and adjudicated evaluation GT exist."""
    gt_eval = benchmark_dir / "annotations/consensus/evaluation"
    eval_rows = read_json(benchmark_dir / "samples/evaluation.json")
    missing = [r["image_id"] for r in eval_rows if not (gt_eval / r["image_id"] / "metadata.json").exists()]
    if missing:
        raise RuntimeError(f"Cannot freeze before adjudicated evaluation GT is complete; missing {len(missing)} cases")

    cfg = read_json(benchmark_dir / "config_draft.json")
    freeze = {
        "frozen_utc": utc_now_iso(),
        "seed": cfg["seed"],
        "config_sha256": digest(benchmark_dir / "config_draft.json"),
        "config_canonical_sha256": sha256_json(cfg),
        "evaluation_sample_sha256": digest(benchmark_dir / "samples/evaluation.json"),
        "code_inventory_sha256": digest(benchmark_dir / "code_inventory.json"),
        "checkpoint_sha256": cfg["s1_sam3_auto"].get("checkpoint_sha256"),
        "gt_consensus_eval_count": len(eval_rows),
    }
    return write_json(benchmark_dir / "freeze.json", freeze)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, default=DEFAULT_BENCHMARK_DIR)
    parser.add_argument("--freeze", action="store_true", help="Create freeze.json if evaluation GT is complete")
    args = parser.parse_args()

    if args.freeze:
        p = create_freeze(args.benchmark_dir)
        print(f"Created {p}")
    res = validate_benchmark(args.benchmark_dir)
    import json

    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
