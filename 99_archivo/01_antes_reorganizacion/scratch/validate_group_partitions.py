"""Controles relacionales independientes de la asignación inicial v1."""
from itertools import combinations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[1]
out = root / 'data/processed/partitions/v1'
all_records = json.loads((root / 'data/processed/manifest_all.json').read_text(encoding='utf-8'))
df = pd.DataFrame(all_records)
plan = json.loads((root / 'exp_design/partition_plan_v1.json').read_text(encoding='utf-8'))
assignment_path = root / 'exp_design/partition_assignments_v1.csv'
groups = pd.read_csv(assignment_path, keep_default_na=False)
checks = {}

def check(name, condition):
    checks[name] = bool(condition)
    if not condition:
        raise AssertionError(name)

check('assignment_hash_matches_frozen_plan', hashlib.sha256(assignment_path.read_bytes()).hexdigest() == plan['assignments_sha256'])
check('400_unique_groups_cover_canonical_manifest', groups.split_group_id.is_unique and len(groups) == 400 and set(groups.split_group_id) == set(df.split_group_id))
check('every_photo_in_group_has_same_function', df.groupby('split_group_id').split_assignment.nunique().eq(1).all())
check('every_validation_group_has_same_validation_role', df[df.split_assignment == 'C_val'].groupby('split_group_id').validation_role.nunique().eq(1).all())
eligible = df.use_in_initial_partition & ~df.exclude_from_primary_training
check('active_flag_matches_eligibility', df.use_in_assigned_partition.eq(eligible).all())
datasets = {}
for role in ('C_fit', 'C_val', 'G_fit', 'T_real', 'M_aux', 'C_val_model_selection', 'C_val_calibration'):
    records = json.loads((out / f'{role}.json').read_text(encoding='utf-8'))
    frame = pd.DataFrame(records)
    csv = pd.read_csv(out / f'{role}.csv', keep_default_na=False)
    check(f'csv_json_image_membership_{role}', frame.image_id.is_unique and set(csv.image_id) == set(frame.image_id) and len(csv) == len(frame))
    parent = 'C_val' if role.startswith('C_val_') else role
    expected = df[eligible & df.split_assignment.eq(parent)]
    if role == 'C_val_model_selection':
        expected = expected[expected.validation_role == 'model_selection']
    elif role == 'C_val_calibration':
        expected = expected[expected.validation_role == 'threshold_calibration']
    expected_ids = set(expected.image_id)
    check(f'exact_canonical_rows_{role}', records == [r for r in all_records if r['image_id'] in expected_ids])
    datasets[role] = frame
main_roles = ('C_fit', 'C_val', 'G_fit', 'T_real', 'M_aux')
for a, b in combinations(main_roles, 2):
    check(f'no_shared_groups_{a}_{b}', not (set(datasets[a].split_group_id) & set(datasets[b].split_group_id)))
    check(f'no_shared_images_or_SHA256_{a}_{b}', not (set(datasets[a].image_id) & set(datasets[b].image_id)) and not (set(datasets[a].sha256) & set(datasets[b].sha256)))
active_union = set().union(*(set(datasets[r].image_id) for r in main_roles))
check('main_datasets_cover_every_active_image_once', active_union == set(df.loc[eligible, 'image_id']) and sum(len(datasets[r]) for r in main_roles) == len(active_union) == 1419)
inactive = pd.read_csv(out / 'excluded_or_deferred.csv', keep_default_na=False)
check('only_9_quality_and_23_reserve_images_inactive', len(inactive) == 32 and set(inactive.image_id) == set(df.loc[~eligible, 'image_id']))
check('no_reserve_Nikon_in_active_datasets', not any((r.source_path.str.contains('/nikon_d70/')).any() for r in datasets.values()))
check('G_fit_only_palmeri_M_aux_only_maize', datasets['G_fit'].species_code.eq('P').all() and datasets['M_aux'].species_code.eq('M').all())
check('all_classifier_sets_have_three_species_and_both_years', all(set(datasets[r].species_code) == {'P', 'H', 'R'} and set(datasets[r].year) == {2025, 2026} for r in ('C_fit', 'C_val', 'T_real', 'C_val_model_selection', 'C_val_calibration')))
for role in ('C_val_model_selection', 'C_val_calibration'):
    check(f'each_class_year_present_{role}', datasets[role].groupby(['species_code', 'year']).split_group_id.nunique().shape[0] == 6)
check('calibration_and_model_selection_groups_disjoint', not (set(datasets['C_val_model_selection'].split_group_id) & set(datasets['C_val_calibration'].split_group_id)))
check('validation_subsets_cover_C_val', set(datasets['C_val_model_selection'].image_id) | set(datasets['C_val_calibration'].image_id) == set(datasets['C_val'].image_id))
check('27_distinct_groups_per_validation_function', datasets['C_val_model_selection'].split_group_id.nunique() == 27 and datasets['C_val_calibration'].split_group_id.nunique() == 27)
check('G_fit_represents_all_year_repetition_cohorts', groups[groups.split_assignment == 'G_fit'].groupby(['year', 'repeticion']).size().shape[0] == 4)
check('G_fit_2025_contains_single_and_four_seeded_scenes', set(groups.loc[(groups.split_assignment == 'G_fit') & (groups.year == 2025), 'density_count']) == {1, 4})
for _, stratum in groups[groups.species_code == 'P'].groupby(plan['strata']):
    actual = (stratum.split_assignment == 'G_fit').sum()
    check('G_fit_fraction_stratum_' + str(tuple(stratum.iloc[0][plan['strata']])), abs(actual - 0.20 * len(stratum)) <= 0.5)
for _, stratum in groups[~groups.split_assignment.isin(['G_fit', 'M_aux'])].groupby(plan['strata']):
    for role, fraction in [('C_fit', .70), ('C_val', .15), ('T_real', .15)]:
        actual = (stratum.split_assignment == role).sum()
        check('classifier_fraction_' + str(tuple(stratum.iloc[0][plan['strata']])) + '_' + role, abs(actual - fraction * len(stratum)) < 1.01 and actual > 0)
check('corrected_species_kept_in_every_split', df.loc[df.label_correction_applied, 'species_code'].eq('P').all())
check('no_plant_individuals_or_measures_fabricated', df.plant_id.isna().all() and df.pot_diameter_px.isna().all())
result = dict(completed_utc=datetime.now(timezone.utc).isoformat(), version='v1', seed=plan['seed'],
    checks=checks, passed=all(checks.values()), assigned_pot_groups=400,
    limitation='Group continuity is field-declared; this validation does not prove cross-repetition independence or external campaign generalization.')
(out / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'{len(checks)} controles correctos: grupos y fotos sin solapamiento; dos reservas C_val independientes; cobertura completa de las entradas activas.')
