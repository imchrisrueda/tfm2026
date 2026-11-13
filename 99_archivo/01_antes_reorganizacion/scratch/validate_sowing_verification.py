"""Contraste de las copias para revisión con disco, diseño y decisiones de campo."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from datetime import datetime, timezone
import pandas as pd

root = Path(__file__).resolve().parents[1]
out = root / 'data/verificacion_siembra'
df = pd.read_csv(out / 'manifest.csv', keep_default_na=False)
summary = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
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

raw = {p.relative_to(root).as_posix() for p in (root / 'data/raw').rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg')}
copies = {p.relative_to(root).as_posix() for p in out.rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg')}
check('all_current_raw_images_in_manifest', raw == set(df.source_path))
check('exactly_one_copy_for_each_current_image', len(df) == len(raw) == len(copies) and copies == set(df.verification_path) and df.source_path.is_unique and df.verification_path.is_unique)
check('current_count_and_bytes_reconcile', len(df) == 1451 == summary['images'] and df.bytes.sum() == summary['bytes'])
with ThreadPoolExecutor(max_workers=4) as pool:
    hashes_ok = list(pool.map(lambda r: digest(root / r.source_path) == r.sha256 == digest(root / r.verification_path), df.itertuples(index=False)))
check('all_1451_sources_and_copies_match_recorded_SHA256', all(hashes_ok))
check('no_partial_copies_left', not list(out.rglob('*.partial')))
check('all_filenames_include_expected_species_and_position', all(r.species_expected.replace(' ', '_') in Path(r.verification_path).name and r.posicion in Path(r.verification_path).name for r in df.itertuples()))
species = {'P': 'Amaranthus palmeri', 'H': 'Amaranthus hybridus', 'R': 'Amaranthus retroflexus', 'M': 'Zea mays'}
for year in (2025, 2026):
    design = pd.read_csv(root / f'exp_design/{year}.csv', index_col='Fila')
    check(f'design_and_scientific_species_names_{year}', all(design.loc[r.fila, r.columna] == r.species_code and species[r.species_code] == r.species_expected for r in df[df.year == year].itertuples()))
check('all_current_labels_await_visual_review', df.label_status.eq('design_label_pending_visual_review').all())
check('all_acquisitions_sorted_by_EXIF_time', all(g.exif_datetime_original.is_monotonic_increasing for _, g in df.groupby(['session_id', 'acquisition_subdir'], sort=False)))
june01 = df[df.session_id == '2026-06-01_c2_r2']
check('June01_field_confirmed_block_order', june01.iloc[0].filename_original == 'DSC_0856.JPG' and june01.iloc[-1].filename_original == 'DSC_0043.JPG' and (june01.species_code != june01.old_inventory_species).sum() == 93)
june20 = df[df.session_id == '2025-06-20_c1_r2']
iphone = june20[june20.acquisition_subdir == '.'].sort_values('design_order')
nikon = june20[june20.acquisition_subdir == 'nikon_d70'].sort_values('design_order')
check('Nikon_same_first_23_pots_as_iPhone', len(iphone) == 60 and len(nikon) == 23 and list(nikon.pot_id) == list(iphone.head(23).pot_id))
check('June16_selected_60_without_maize', len(df[df.session_id == '2025-06-16_c1_r2']) == 60 and not df.loc[df.session_id == '2025-06-16_c1_r2', 'species_code'].eq('M').any())
may14 = df[df.session_id == '2026-05-14_c2_r1']
names = may14.filename_original.tolist()
check('May14_selected_130_and_0783_then_0809', len(names) == 130 and names[names.index('DSC_0783.JPG') + 1] == 'DSC_0809.JPG')
removed = pd.read_csv(out / 'removed_since_initial_audit.csv')
check('23_removed_only_from_May14', len(removed) == 23 and removed.session_id.eq('2026-05-14_c2_r1').all())
check('9_field_identified_training_exclusions_including_band', df.exclude_from_primary_training.sum() == 9 and df.loc[df.exclusion_reason == 'visual_band_corruption', 'source_path'].tolist() == ['data/raw/2025-06-05_c1_r2/DSC_0081.JPG'])
check('8_priority_images_in_requested_positions', df.priority_visual_review.sum() == 8 and df.loc[df.priority_visual_review, 'posicion'].isin(['F26C1', 'F4C4']).all())
check('2025_seeded_counts_populated_only_2025', df.loc[df.year == 2025, 'num_plants_seeded_2025'].ne('').all() and df.loc[df.year == 2026, 'num_plants_seeded_2025'].eq('').all())
check('2026_one_nominal_plant_observed_count_unknown', df.loc[df.year == 2026, 'num_plants_nominal_2026'].astype(int).eq(1).all() and df.num_plants_observed.eq('').all())
review = pd.read_csv(out / 'revision_visual.csv', keep_default_na=False)
check('review_table_covers_every_copy', set(review.source_path) == raw and len(review) == len(df))
for source in summary['sources']:
    check('source_snapshot_' + source['path'], digest(root / source['path']) == source['sha256'])
result = dict(completed_utc=datetime.now(timezone.utc).isoformat(), checks=checks, passed=all(checks.values()),
    limitations='Checks file integrity, design mapping and declared rules; no visual or botanical confirmation.')
(out / 'validation.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'{len(checks)} comprobaciones correctas; {len(df)} originales y copias contrastados por SHA-256.')
