"""Inventory and deterministic stratified group sampling for segmentation_benchmark_v1.

Dry-run by default: prints summary and verifies contracts without writing files.
Pass --write to materialize inventory.json, sampling.json, samples/, and initial config/docs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from common import (
    DEFAULT_BENCHMARK_DIR,
    DEV_SELECTION_PATH,
    ROOT,
    SEED_DEFAULT,
    STRESS_TRIAL_INDICES,
    collect_environment_info,
    default_config,
    digest,
    read_json,
    sha256_text,
    utc_now_iso,
    verify_protected_inputs,
    write_csv,
    write_json,
    yes,
)


SAMPLE_COLUMNS = [
    "sample_role",
    "sample_index",
    "blind_id",
    "image_id",
    "sha256",
    "split_group_id",
    "year",
    "species_code",
    "design_species_code",
    "session_id",
    "exif_camera_model",
    "exif_orientation",
    "oriented_width",
    "oriented_height",
    "source_path",
    "split_assignment",
    "use_in_assigned_partition",
    "stratum_N",
    "stratum_n",
    "group_size_m_g",
    "group_selection_prob",
    "image_conditional_prob",
    "group_weight",
    "double_annotation_assigned",
    "development_index",
    "selection_hash",
]


def _order_hash(seed: str, namespace: str, identifier: str) -> str:
    return sha256_text(f"{seed}|{namespace}|{identifier}")


def _coverage_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n_images": len(rows),
        "n_groups": len({r["split_group_id"] for r in rows}),
        "by_year_species": dict(sorted(Counter(f"{r['year']}_{r['species_code']}" for r in rows).items())),
        "by_camera": dict(sorted(Counter(str(r.get("exif_camera_model") or "unknown") for r in rows).items())),
        "by_exif_orientation": dict(sorted(Counter(str(r.get("exif_orientation") or "none") for r in rows).items())),
        "by_session": dict(sorted(Counter(str(r.get("session_id") or "unknown") for r in rows).items())),
        "by_nominal_plants_2026": dict(
            sorted(Counter(str(r.get("num_plants_nominal_2026")) for r in rows if int(r["year"]) == 2026).items())
        ),
        "by_seeded_plants_2025": dict(
            sorted(Counter(str(r.get("num_plants_seeded_2025")) for r in rows if int(r["year"]) == 2025).items())
        ),
    }


def _check_group_coherence(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["split_group_id"]].append(row)
    incidents = []
    for gid, members in groups.items():
        years = {int(m["year"]) for m in members}
        species = {m["species_code"] for m in members}
        if len(years) != 1 or len(species) != 1:
            incidents.append({"split_group_id": gid, "years": sorted(years), "species": sorted(species)})
    if incidents:
        raise ValueError(f"Incoherent year/species within split_group_id: {incidents}")
    return dict(groups)


def _select_stratified_groups(
    groups_map: dict[str, list[dict[str, Any]]],
    quotas: dict[str, dict[str, int]],
    seed: str,
    group_ns: str,
    image_ns: str,
    sample_role: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    by_stratum: dict[tuple[int, str], list[str]] = defaultdict(list)
    for gid, members in groups_map.items():
        y = int(members[0]["year"])
        sp = members[0]["species_code"]
        by_stratum[(y, sp)].append(gid)

    selected_rows: list[dict[str, Any]] = []
    stratum_stats: dict[str, dict[str, Any]] = {}
    idx = 0
    for year_str in sorted(quotas.keys()):
        year = int(year_str)
        for sp in sorted(quotas[year_str].keys()):
            n_req = int(quotas[year_str][sp])
            pool = by_stratum.get((year, sp), [])
            N = len(pool)
            if N < n_req:
                raise ValueError(f"Insufficient groups for {sample_role} stratum ({year}, {sp}): need {n_req}, have {N}")
            ordered_gids = sorted(pool, key=lambda g: (_order_hash(seed, group_ns, g), g))
            chosen_gids = ordered_gids[:n_req]
            stratum_stats[f"{year}_{sp}"] = {"N_eligible_groups": N, "n_selected_groups": n_req, "selection_prob": n_req / N}

            for gid in chosen_gids:
                members = groups_map[gid]
                m_g = len(members)
                ordered_imgs = sorted(members, key=lambda r: (_order_hash(seed, image_ns, r["image_id"]), r["image_id"]))
                chosen = ordered_imgs[0]
                idx += 1
                chosen_id = chosen["image_id"]
                img_hash = _order_hash(seed, image_ns, chosen_id)
                blind_id = f"{sample_role.upper()}_{sha256_text(f'{seed}|blind|{sample_role}|{chosen_id}')[:10]}"
                selected_rows.append(
                    {
                        "sample_role": sample_role,
                        "sample_index": idx,
                        "blind_id": blind_id,
                        "image_id": chosen["image_id"],
                        "sha256": chosen["sha256"],
                        "split_group_id": gid,
                        "year": year,
                        "species_code": sp,
                        "design_species_code": chosen.get("design_species_code", ""),
                        "session_id": chosen.get("session_id", ""),
                        "exif_camera_model": chosen.get("exif_camera_model", ""),
                        "exif_orientation": chosen.get("exif_orientation", ""),
                        "oriented_width": int(chosen["oriented_width"]),
                        "oriented_height": int(chosen["oriented_height"]),
                        "source_path": chosen["source_path"],
                        "split_assignment": chosen["split_assignment"],
                        "use_in_assigned_partition": bool(yes(chosen["use_in_assigned_partition"])),
                        "stratum_N": N,
                        "stratum_n": n_req,
                        "group_size_m_g": m_g,
                        "group_selection_prob": n_req / N,
                        "image_conditional_prob": 1.0 / m_g,
                        "group_weight": N / n_req,
                        "double_annotation_assigned": False,
                        "development_index": chosen.get("development_index", ""),
                        "selection_hash": img_hash,
                    }
                )
    return selected_rows, stratum_stats


def build_inventory_and_samples(root: Path = ROOT, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or default_config()
    seed = cfg["seed"]
    protected = verify_protected_inputs(root)
    registry = read_json(root / "exp_design/preprocessing_registry.json")

    c_fit_path = root / registry["partition_lists"]["C_fit"]["json_path"]
    c_fit_rows = read_json(c_fit_path)

    # Check metadata-only group disjointness against forbidden splits (no image decoding)
    c_fit_groups = {r["split_group_id"] for r in c_fit_rows}
    forbidden_overlap: dict[str, list[str]] = {}
    forbidden_group_counts: dict[str, int] = {}
    for role in ("C_val_model_selection", "C_val_calibration", "G_fit", "T_real", "M_aux"):
        role_rows = read_json(root / registry["partition_lists"][role]["json_path"])
        role_groups = {r["split_group_id"] for r in role_rows}
        forbidden_group_counts[role] = len(role_groups)
        overlap = sorted(c_fit_groups & role_groups)
        if overlap:
            forbidden_overlap[role] = overlap
    if forbidden_overlap:
        raise ValueError(f"Group overlap detected between C_fit and forbidden splits: {forbidden_overlap}")

    # Validate C_fit active flags and target species
    invalid_cfit = [
        r["image_id"]
        for r in c_fit_rows
        if r.get("split_assignment") != "C_fit"
        or not yes(r.get("use_in_assigned_partition"))
        or r.get("species_code") not in {"H", "P", "R"}
        or int(r.get("year", 0)) not in {2025, 2026}
    ]
    if invalid_cfit:
        raise ValueError(f"Invalid rows in C_fit.json: {invalid_cfit[:10]}")

    all_cfit_groups = _check_group_coherence(c_fit_rows)

    dev_rows = read_json(root / "data/processed/preprocessing/development_v1/selection.json")
    dev_by_id = {r["image_id"]: r for r in dev_rows}
    exposed_groups = {r["split_group_id"] for r in dev_rows}
    stress_rows_raw = [r for r in dev_rows if int(r["development_index"]) in set(cfg["stress_development_indices"])]
    stress_groups = {r["split_group_id"] for r in stress_rows_raw}

    # Verify development_v1 rows match C_fit by (image_id, sha256)
    c_fit_by_key = {(r["image_id"], r["sha256"]): r for r in c_fit_rows}
    for r in dev_rows:
        if (r["image_id"], r["sha256"]) not in c_fit_by_key:
            raise ValueError(f"development_v1 row not matched in C_fit by (image_id, sha256): {r['image_id']}")

    # 1) Evaluation universe: C_fit groups excluding ALL exposed groups from development_v1 (91 photos / 76 groups)
    eval_groups = {gid: members for gid, members in all_cfit_groups.items() if gid not in exposed_groups}
    eval_rows, eval_strata = _select_stratified_groups(
        eval_groups,
        cfg["evaluation_quotas"],
        seed=seed,
        group_ns="eval_group",
        image_ns="eval_image",
        sample_role="evaluation",
    )

    # Assign 20 double-annotation images (8P/6H/6R balanced by year) deterministically from evaluation
    eval_by_stratum: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in eval_rows:
        eval_by_stratum[(int(row["year"]), row["species_code"])].append(row)
    double_ids: set[str] = set()
    for year_str, sp_map in cfg["double_annotation_quotas"].items():
        year = int(year_str)
        for sp, q in sp_map.items():
            candidates = sorted(
                eval_by_stratum[(year, sp)],
                key=lambda r: (_order_hash(seed, "double_annot", r["split_group_id"]), r["split_group_id"]),
            )
            for r in candidates[: int(q)]:
                r["double_annotation_assigned"] = True
                double_ids.add(r["image_id"])

    # 2) Tuning universe: groups already exposed in development_v1, avoiding stress_groups if feasible
    tuning_groups_no_stress = {
        gid: [r for r in members if r["image_id"] in dev_by_id]
        for gid, members in all_cfit_groups.items()
        if gid in exposed_groups and gid not in stress_groups
    }
    tuning_groups_no_stress = {
        gid: [dict(r, development_index=dev_by_id[r["image_id"]]["development_index"]) for r in members]
        for gid, members in tuning_groups_no_stress.items()
        if members
    }
    tuning_rows, tuning_strata = _select_stratified_groups(
        tuning_groups_no_stress,
        cfg["tuning_quotas"],
        seed=seed,
        group_ns="tuning_group",
        image_ns="tuning_image",
        sample_role="tuning",
    )

    # 3) Stress panel: the 12 historical cases from roi_small_trial_v1
    stress_rows: list[dict[str, Any]] = []
    for idx, r in enumerate(sorted(stress_rows_raw, key=lambda x: int(x["development_index"])), 1):
        r_id = r["image_id"]
        blind_id = f"STRESS_{sha256_text(f'{seed}|blind|stress|{r_id}')[:10]}"
        stress_rows.append(
            {
                "sample_role": "stress",
                "sample_index": idx,
                "blind_id": blind_id,
                "image_id": r["image_id"],
                "sha256": r["sha256"],
                "split_group_id": r["split_group_id"],
                "year": int(r["year"]),
                "species_code": r["species_code"],
                "design_species_code": r.get("design_species_code", ""),
                "session_id": r.get("session_id", ""),
                "exif_camera_model": r.get("exif_camera_model", ""),
                "exif_orientation": r.get("exif_orientation", ""),
                "oriented_width": int(r["oriented_width"]),
                "oriented_height": int(r["oriented_height"]),
                "source_path": r["source_path"],
                "split_assignment": r["split_assignment"],
                "use_in_assigned_partition": bool(yes(r["use_in_assigned_partition"])),
                "stratum_N": "",
                "stratum_n": "",
                "group_size_m_g": len(all_cfit_groups[r["split_group_id"]]),
                "group_selection_prob": "",
                "image_conditional_prob": "",
                "group_weight": "",
                "double_annotation_assigned": False,
                "development_index": int(r["development_index"]),
                "selection_hash": "",
            }
        )

    # Verify strict group disjointness across tuning, evaluation, and stress
    t_groups = {r["split_group_id"] for r in tuning_rows}
    e_groups = {r["split_group_id"] for r in eval_rows}
    s_groups = {r["split_group_id"] for r in stress_rows}
    assert not (t_groups & e_groups), "Overlap between tuning and evaluation groups"
    assert not (s_groups & e_groups), "Overlap between stress and evaluation groups"
    assert not (t_groups & s_groups), "Overlap between tuning and stress groups"

    eval_ids = {r["image_id"] for r in eval_rows}
    tuning_ids = {r["image_id"] for r in tuning_rows}
    stress_ids = {r["image_id"] for r in stress_rows}

    candidate_records = []
    for r in c_fit_rows:
        gid = r["split_group_id"]
        iid = r["image_id"]
        if iid in eval_ids:
            status, reason = "selected_evaluation", "selected_by_hash_from_unexposed_C_fit_groups"
        elif iid in tuning_ids:
            status, reason = "selected_tuning", "selected_by_hash_from_exposed_non_stress_groups"
        elif iid in stress_ids:
            status, reason = "selected_stress", "historical_roi_small_trial_v1_panel"
        elif gid in e_groups:
            status, reason = "excluded_same_eval_group", "one_image_per_selected_group"
        elif gid in exposed_groups:
            status, reason = "excluded_exposed_development_v1", "group_exposed_in_91_development_v1_photos"
        else:
            status, reason = "unselected_eval_pool", "not_drawn_in_stratified_hash_sample"
        candidate_records.append(
            {
                "image_id": iid,
                "sha256": r["sha256"],
                "split_group_id": gid,
                "year": int(r["year"]),
                "species_code": r["species_code"],
                "inclusion_status": status,
                "reason": reason,
            }
        )

    inventory = {
        "created_utc": utc_now_iso(),
        "protocol_version": cfg["protocol_version"],
        "protected_inputs": protected,
        "c_fit_images": len(c_fit_rows),
        "c_fit_groups": len(all_cfit_groups),
        "exposed_development_v1_images": len(dev_rows),
        "exposed_development_v1_groups": len(exposed_groups),
        "eligible_eval_groups": len(eval_groups),
        "eligible_eval_groups_by_stratum": {k: v["N_eligible_groups"] for k, v in eval_strata.items()},
        "forbidden_splits_group_counts_metadata_only": forbidden_group_counts,
        "forbidden_splits_group_overlap": forbidden_overlap,
    }

    sampling = {
        "created_utc": utc_now_iso(),
        "seed": seed,
        "hash_rules": {
            "evaluation_group": "sha256(f'{seed}|eval_group|{split_group_id}')",
            "evaluation_image": "sha256(f'{seed}|eval_image|{image_id}')",
            "tuning_group": "sha256(f'{seed}|tuning_group|{split_group_id}')",
            "tuning_image": "sha256(f'{seed}|tuning_image|{image_id}')",
            "double_annotation": "sha256(f'{seed}|double_annot|{split_group_id}')",
        },
        "tuning": {"strata": tuning_strata, "coverage": _coverage_summary(tuning_rows)},
        "evaluation": {
            "strata": eval_strata,
            "coverage": _coverage_summary(eval_rows),
            "double_annotation_count": len(double_ids),
            "double_annotation_by_stratum": dict(
                sorted(Counter(f"{r['year']}_{r['species_code']}" for r in eval_rows if r["double_annotation_assigned"]).items())
            ),
        },
        "stress": {"coverage": _coverage_summary(stress_rows)},
        "disjointness_verified": True,
        "candidate_records": candidate_records,
    }

    return {
        "config": cfg,
        "inventory": inventory,
        "sampling": sampling,
        "tuning_rows": tuning_rows,
        "evaluation_rows": eval_rows,
        "stress_rows": stress_rows,
    }


def write_initial_benchmark(out_dir: Path, bundle: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "config_draft.json", bundle["config"])
    write_json(out_dir / "inventory.json", bundle["inventory"])
    write_json(out_dir / "sampling.json", bundle["sampling"])

    for role, key in [("tuning", "tuning_rows"), ("evaluation", "evaluation_rows"), ("stress", "stress_rows")]:
        rows = bundle[key]
        write_json(out_dir / "samples" / f"{role}.json", rows)
        write_csv(out_dir / "samples" / f"{role}.csv", rows, fieldnames=SAMPLE_COLUMNS)

    write_json(out_dir / "environment.json", collect_environment_info())

    scripts_dir = Path(__file__).resolve().parent
    code_hashes = {
        p.relative_to(ROOT).as_posix(): digest(p)
        for p in sorted(scripts_dir.glob("*.py"))
    }
    write_json(
        out_dir / "code_inventory.json",
        {"created_utc": utc_now_iso(), "files": code_hashes},
    )

    readme_text = (
        "# Segmentation Benchmark v1 (`segmentation_benchmark_v1`)\n\n"
        "Implementación del protocolo `doc/EXPERIMENTO_COMPARACION_PREPROCESADO_V1.md`.\n"
        "- `samples/tuning.*`: 18 imágenes de calibración técnica (grupos ya expuestos en `development_v1`, sin casos de estrés).\n"
        "- `samples/evaluation.*`: 60 imágenes (60 grupos nuevos de `C_fit` no expuestos previamente); bloqueadas hasta `freeze.json`.\n"
        "- `samples/stress.*`: 12 casos históricos de `roi_small_trial_v1` (solo tabla de regresión separada).\n"
    )
    (out_dir / "README.md").write_text(readme_text, encoding="utf-8")

    protocol_text = (
        "# Protocolo congelable de comparación de preprocesado v1\n\n"
        "1. Seleccionar muestras antes de inspeccionar píxeles nuevos (`inventory_and_sample.py`).\n"
        "2. Anotar verdad de referencia humana ciega sobre originales orientados (`annotation_io.py`).\n"
        "3. Calibrar adaptadores sobre `--split tuning` (18 imágenes) y verificar smoke-test real.\n"
        "4. Congelar parámetros, código, checkpoint y GT adjudicada en `freeze.json` antes de `--split evaluation`.\n"
        "5. Ejecutar `--split evaluation` sin modificar parámetros ni reabrir `T_real`, `C_val_*`, `G_fit` o `M_aux`.\n"
    )
    (out_dir / "protocol.md").write_text(protocol_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_BENCHMARK_DIR)
    parser.add_argument("--write", action="store_true", help="Write inventory, sampling, and sample lists to output dir")
    args = parser.parse_args()

    bundle = build_inventory_and_samples(ROOT)
    summary = {
        "mode": "write" if args.write else "dry_run",
        "output_dir": str(args.output),
        "c_fit_images": bundle["inventory"]["c_fit_images"],
        "c_fit_groups": bundle["inventory"]["c_fit_groups"],
        "eligible_eval_groups_by_stratum": bundle["inventory"]["eligible_eval_groups_by_stratum"],
        "tuning_coverage": bundle["sampling"]["tuning"]["coverage"]["by_year_species"],
        "evaluation_coverage": bundle["sampling"]["evaluation"]["coverage"]["by_year_species"],
        "double_annotation_by_stratum": bundle["sampling"]["evaluation"]["double_annotation_by_stratum"],
        "stress_coverage": bundle["sampling"]["stress"]["coverage"]["by_year_species"],
        "disjointness_verified": bundle["sampling"]["disjointness_verified"],
        "forbidden_splits_group_overlap": bundle["inventory"]["forbidden_splits_group_overlap"],
    }
    if args.write:
        write_initial_benchmark(args.output, bundle)

    import json

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
