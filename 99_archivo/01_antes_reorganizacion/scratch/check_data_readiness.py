"""Comprobación de preparación de datos; no inspecciona ni configura DRAGO."""
from datetime import datetime, timezone
import json
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[1]
out = root / 'data/processed'
records = json.loads((out / 'manifest_all.json').read_text(encoding='utf-8'))
df = pd.DataFrame(records)
validation = json.loads((out / 'manifest_validation.json').read_text(encoding='utf-8'))
c = df[df.use_for_classifier] if 'use_for_classifier' in df else df[df.is_classifier_candidate]
g = df[df.use_for_lora] if 'use_for_lora' in df else df[df.is_lora_candidate]
class_profile = c.groupby('species_scientific').agg(images=('image_id', 'size'), pot_groups=('split_group_id', 'nunique')).reset_index()
strata = c.groupby(['year', 'campana', 'repeticion', 'species_code']).agg(images=('image_id', 'size'), pot_groups=('split_group_id', 'nunique')).reset_index()
caption_columns = [column for column in df if 'caption' in column.lower()]
geometry_measured = df.pot_diameter_px.notna() & df.pot_center_x_px.notna() & df.pot_center_y_px.notna()
potential_assets = [p.relative_to(root).as_posix() for p in (root / 'data').rglob('*') if p.is_file() and (
    'caption' in p.name.lower() or 'mask' in p.name.lower() or p.suffix.lower() in ('.yaml', '.yml'))]
summary = dict(checked_utc=datetime.now(timezone.utc).isoformat(), scope='data_only_no_DRAGO_or_environment_assessment',
    manifest_build_id=df.manifest_build_id.iloc[0], images=len(df), integrity_validation_passed=validation['passed'],
    integrity_checks=len(validation['checks']), classifier_images=len(c), classifier_groups=c.split_group_id.nunique(),
    classifier_candidate_images=int(df.is_classifier_candidate.sum()), LoRA_candidate_images=int(df.is_lora_candidate.sum()),
    classifier_by_species=class_profile.to_dict('records'), LoRA_images=len(g), LoRA_groups=g.split_group_id.nunique(),
    overlap_classifier_and_LoRA_images=len(set(c.image_id) & set(g.image_id)),
    overlap_classifier_and_LoRA_groups=len(set(c.split_group_id) & set(g.split_group_id)),
    excluded_images=int(df.exclude_from_primary_training.sum()), auxiliary_maize=int(df.is_auxiliary.sum()),
    initial_partition_pool_images=int(df.use_in_initial_partition.sum()), deferred_secondary_images=int((~df.use_in_initial_partition).sum()),
    assigned_partition_images=int(df.split_assignment.ne('unassigned').sum()), measured_geometry_images=int(geometry_measured.sum()),
    active_partition_images=int(df.use_in_assigned_partition.sum()) if 'use_in_assigned_partition' in df else None,
    linked_master_images=int(df.master_image_path.notna().sum()), observed_plant_count_images=int(df.num_plants_observed.notna().sum()),
    annotated_growth_stage_images=int(df.growth_stage.notna().sum()), caption_columns=caption_columns,
    discovered_caption_mask_or_training_yaml_files=potential_assets,
    corrected_label_images=int(df.label_correction_applied.sum()), remaining_initial_sowing_priority=int(df.sowing_review_priority_unresolved.sum()),
    source_change_pending_review_images=int(df.source_change_review_status.eq('review_required_cause_unresolved').sum()),
    has_scale_reference_nominal=int(df.pot_diameter_exterior_cm.notna().sum()), strata=strata.to_dict('records'),
    interpretation=dict(development='data sufficient to implement loader and initial experiments after reserving groups',
        classifier_training='group partitions v1 assigned; preprocessing still to prepare' if 'use_for_classifier' in df else 'reserve group partitions and define preprocessing first',
        conventional_LoRA_pilot='G_fit disjoint and reserved; prepare images and factual captions before training' if 'use_for_lora' in df else 'reserve disjoint G_fit; prepare images and factual captions before training',
        plant_only_background_editing='method and region/background annotations not yet defined or prepared',
        scientific_scale_claims='not ready; no measured geometry or frozen physical field',
        base_model_generation='not blocked by these dataset preparations; does not test learned adaptation'))
(out / 'data_readiness.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
strata.to_csv(out / 'data_readiness_groups.csv', index=False, encoding='utf-8-sig')
print(json.dumps({k: v for k, v in summary.items() if k not in ('strata', 'interpretation')}, ensure_ascii=False, indent=2))
