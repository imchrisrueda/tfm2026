"""Valida consolidados vigentes, reglas de corrección, archivos y versiones."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[1]
out = root / 'data/processed'
summary = json.loads((out / 'manifest_build_summary.json').read_text(encoding='utf-8'))
checks = {}

def check(name, condition):
    checks[name] = bool(condition)
    if not condition:
        raise AssertionError(name)

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def same_value(text, value):
    if value is None:
        return text == ''
    if isinstance(value, bool):
        return text.lower() == str(value).lower()
    if isinstance(value, (int, float)):
        return float(text) == value
    return text == value

parts = {}
for part in ('2025', '2026', 'all'):
    records = json.loads((out / f'manifest_{part}.json').read_text(encoding='utf-8'))
    csv = pd.read_csv(out / f'manifest_{part}.csv', dtype=str, keep_default_na=False)
    check(f'CSV_JSON_all_values_equal_{part}', len(csv) == len(records) and all(all(same_value(text, value) for text, value in zip(crow, row.values())) for crow, row in zip(csv.itertuples(index=False, name=None), records)))
    check(f'CSV_JSON_columns_equal_{part}', list(csv.columns) == list(records[0]))
    parts[part] = records
records = parts['all']
df = pd.DataFrame(records)
check('annual_exports_exact_subsets_of_combined', all(parts[str(year)] == [r for r in records if r['year'] == year] for year in (2025, 2026)))
check('493_2025_958_2026_1451_total', len(parts['2025']) == 493 and len(parts['2026']) == 958 and len(records) == 1451)
raw = {p.relative_to(root).as_posix() for p in (root / 'data/raw').rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg')}
check('complete_recursive_current_raw_coverage', set(df.source_path) == raw and df.source_path.is_unique)
check('unique_image_ids_and_hashes', df.image_id.is_unique and df.sha256.is_unique)
check('both_path_conventions_resolve_same_original', all(root / r['source_path'] == root / 'data' / r['relative_path'] for r in records))
with ThreadPoolExecutor(max_workers=4) as pool:
    current_ok = list(pool.map(lambda r: (root / r['source_path']).stat().st_size == r['bytes'] and digest(root / r['source_path']) == r['sha256'], records))
check('all_current_original_sizes_and_SHA256_match', all(current_ok))
check('15_sessions_and_400_pot_groups', df.session_id.nunique() == 15 and df.split_group_id.nunique() == 400)
check('single_final_species_per_physical_group', df.groupby('split_group_id').species_code.nunique().eq(1).all())
taxonomy = {'P': ('Amaranthus palmeri', 'palmeri'), 'H': ('Amaranthus hybridus', 'hybridus'), 'R': ('Amaranthus retroflexus', 'retroflexus'), 'M': ('Zea mays', 'maize')}
for year in (2025, 2026):
    grid = pd.read_csv(root / f'exp_design/{year}.csv', index_col='Fila')
    check(f'original_design_labels_preserved_{year}', all(grid.loc[r['fila'], r['columna']] == r['design_species_code'] for r in records if r['year'] == year))
check('final_scientific_class_and_flags_agree', all(taxonomy[r['species_code']] == (r['species_scientific'], r['class_label']) and r['is_target_species'] == (r['species_code'] == 'P') and r['is_auxiliary'] == (r['species_code'] == 'M') for r in records))
target = (df.year == 2026) & (df.campana == 'c2') & (df.repeticion == 'r2') & df.posicion.isin(['F26C1', 'F4C4'])
check('only_two_requested_groups_corrected_eight_images', target.sum() == 8 and df.label_correction_applied.eq(target).all())
check('corrected_hybridus_to_palmeri_with_provenance', df.loc[target, 'species_code'].eq('P').all() and df.loc[target, 'design_species_code'].eq('H').all() and df.loc[target, 'label_correction_id'].notna().all() and df.loc[target, 'label_correction_reason'].eq('seed_error_reported_by_investigator').all())
check('all_other_species_unchanged_from_design', df.loc[~target, 'species_code'].eq(df.loc[~target, 'design_species_code']).all())
check('final_species_totals_reconcile', df.species_code.value_counts().to_dict() == {'P': 446, 'R': 445, 'H': 436, 'M': 124})
review = pd.read_csv(root / 'data/verificacion_siembra/revision_visual.csv', keep_default_na=False).set_index('source_path')
check('eight_user_confirmations_recorded_without_claiming_other_individual_reviews', review.loc[df.loc[target, 'source_path'], 'species_observed'].eq('Amaranthus palmeri').all() and review.loc[df.loc[target, 'source_path'], 'review_status'].eq('corrected').all() and df.loc[~target, 'species_review_status'].eq('no_individual_visual_confirmation_recorded').all())
check('corrected_group_ids_preserved_from_verification', df.loc[target, 'pot_id'].tolist() == pd.read_csv(root / 'data/verificacion_siembra/manifest.csv').set_index('source_path').loc[df.loc[target, 'source_path'], 'pot_id'].tolist())
check('nine_exclusions_retained_including_visual_band', df.exclude_from_primary_training.sum() == 9 and df.loc[df.exclusion_reason == 'visual_band_corruption', 'source_path'].tolist() == ['data/raw/2025-06-05_c1_r2/DSC_0081.JPG'])
check('excluded_images_never_classifier_or_LoRA_candidates', not df.loc[df.exclude_from_primary_training, 'is_classifier_candidate'].any() and not df.loc[df.exclude_from_primary_training, 'is_lora_candidate'].any())
check('maize_auxiliary_not_classifier_or_LoRA', not df.loc[df.is_auxiliary, 'is_classifier_candidate'].any() and not df.loc[df.is_auxiliary, 'is_lora_candidate'].any())
check('LoRA_only_palmeri', df.loc[df.is_lora_candidate, 'species_code'].eq('P').all())
deferred = (df.session_id == '2025-06-20_c1_r2') & (df.acquisition_subdir == 'nikon_d70')
check('only_23_incomplete_secondary_Nikon_images_deferred', deferred.sum() == 23 and df.use_in_initial_partition.eq(~deferred).all())
check('deferred_acquisition_never_initial_training_candidate', not df.loc[deferred, 'is_classifier_candidate'].any() and not df.loc[deferred, 'is_lora_candidate'].any())
check('candidate_counts_reconciled', df.is_classifier_candidate.sum() == 1296 and df.is_lora_candidate.sum() == 437)
check('initial_pool_1428_and_complete_iPhone_acquisition_retained', df.use_in_initial_partition.sum() == 1428 and df.loc[(df.session_id == '2025-06-20_c1_r2') & ~deferred, 'use_in_initial_partition'].sum() == 60)
check('task9_resolved_without_hiding_historical_pixel_change', df.loc[df.source_path == 'data/raw/2025-06-20_c1_r2/nikon_d70/DSC_0380.JPG', 'source_change_review_status'].eq('accepted_as_is_by_investigator').all() and df.loc[df.source_path == 'data/raw/2025-06-20_c1_r2/nikon_d70/DSC_0380.JPG', 'pixels_changed_since_initial_audit'].all())
for part in ('2025', '2026', 'all'):
    pool = pd.read_csv(out / f'manifest_initial_pool_{part}.csv', keep_default_na=False)
    expected_pool = df[df.use_in_initial_partition & (True if part == 'all' else df.year == int(part))]
    check(f'initial_pool_export_exact_{part}', set(pool.source_path) == set(expected_pool.source_path) and len(pool) == len(expected_pool))
check('seeded_and_nominal_counts_not_observed_counts', df.loc[df.year == 2025, 'num_plants_seeded_2025'].notna().all() and df.loc[df.year == 2026, 'num_plants_nominal_2026'].eq(1).all() and df.num_plants_observed.isna().all())
check('unmeasured_geometry_not_invented', df[['pot_center_x_px', 'pot_center_y_px', 'pot_diameter_px', 'scale_cm_per_px', 'common_field_cm', 'plant_id']].isna().all().all())
if summary.get('partition_version'):
    assignment = pd.read_csv(root / 'exp_design/partition_assignments_v1.csv', keep_default_na=False).set_index('split_group_id')
    check('partition_assignment_matches_frozen_group_table', all(assignment.loc[r['split_group_id'], 'split_assignment'] == r['split_assignment'] for r in records))
    check('one_function_per_group_including_deferred_images', df.groupby('split_group_id').split_assignment.nunique().eq(1).all())
    check('inactive_rows_not_used_by_any_model', not df.loc[~df.use_in_assigned_partition, 'use_for_classifier'].any() and not df.loc[~df.use_in_assigned_partition, 'use_for_lora'].any())
    check('classifier_and_generator_groups_disjoint', not (set(df.loc[df.use_for_classifier, 'split_group_id']) & set(df.loc[df.use_for_lora, 'split_group_id'])))
else:
    check('no_splits_without_documented_assignment', df.split_assignment.eq('unassigned').all())
check('chronological_acquisition_order_preserved', all(g.acquisition_order_datetime.is_monotonic_increasing for _, g in df.groupby(['session_id', 'acquisition_subdir'], sort=False)))
check('incomplete_session_orders_83_to_130', df.loc[df.session_id == '2026-06-12_c2_r2', 'capture_order'].tolist() == list(range(83, 131)))
check('date_from_folder_and_original_EXIF_retained', df.date_session.eq(df.session_id.str[:10]).all() and df.exif_datetime_original.notna().all())
for item in summary['outputs']:
    check('export_hash_' + item['path'], digest(root / item['path']) == item['sha256'])
for item in summary['sources']:
    check('source_hash_' + item['path'], digest(root / item['path']) == item['sha256'])
for item in summary['backups']:
    check('previous_version_preserved_' + item['snapshot'], digest(root / item['snapshot']) == item['sha256'])

notes = {
    'source_path': 'Ruta relativa al proyecto; apunta al original actual.',
    'relative_path': 'Ruta relativa al directorio data, por compatibilidad.',
    'species_code': 'Etiqueta de trabajo final P/H/R/M; incorpora correcciones.',
    'design_species_code': 'Especie prevista por diseño, conservada aunque se corrija.',
    'split_group_id': 'Grupo temporal de maceta; mantenerlo íntegro al particionar.',
    'capture_order': 'Orden en la serpentina completa, no índice de archivo de la sesión incompleta.',
    'num_plants_seeded_2025': 'Número sembrado según detalles de 2025, no recuento de plantas presentes.',
    'num_plants_nominal_2026': 'Una planta por maceta según declaración; no observación por foto.',
    'num_plants_observed': 'Desconocido; no se ha efectuado recuento visual exhaustivo.',
    'has_reference_card': 'Presencia esperada según fecha/notas, no confirmación por imagen.',
    'pot_diameter_exterior_cm': 'Diámetro nominal declarado; no sustituye la medición en píxeles.',
    'is_classifier_candidate': 'Candidata antes de geometría y particiones; no tamaño final de entrenamiento.',
    'is_lora_candidate': 'Palmeri sin exclusión primaria, pendiente de geometría y particiones.',
    'use_in_initial_partition': 'False para la adquisición Nikon secundaria incompleta; conservar como reserva fuera del reparto inicial.',
    'acquisition_selection_reason': 'Motivo de reserva de adquisición; independiente de las exclusiones por calidad.',
    'verification_filename_is_design_label': 'Las copias de revisión conservan especie inicialmente esperada.',
    'exif_timezone_status': 'No se infiere una zona horaria de cámara.',
}
schema = []
for column in records[0]:
    values = [r[column] for r in records]
    types = sorted({type(v).__name__ for v in values if v is not None})
    schema.append(dict(name=column, observed_non_null_types=types, null_count=sum(v is None for v in values),
                       notes=notes.get(column, 'Consultar el grupo correspondiente en README_manifiestos.md.')))
(out / 'manifest_schema.json').write_text(json.dumps(dict(schema_version=records[0]['manifest_schema_version'], columns=schema, missing_value='JSON null / CSV celda vacía; no equivale a cero'), ensure_ascii=False, indent=2), encoding='utf-8')
(out / 'manifest_validation.json').write_text(json.dumps(dict(completed_utc=datetime.now(timezone.utc).isoformat(), build_id=summary['build_id'],
    checks=checks, passed=all(checks.values()), checked_images=len(records),
    scope='Integridad, formatos, grupos y aplicación de confirmación del investigador; no implica geometría o panel experto ya realizados.'), ensure_ascii=False, indent=2), encoding='utf-8')
print(f'{len(checks)} comprobaciones correctas. {len(records)} originales reconciliados y verificados por SHA-256; CSV y JSON equivalentes.')
