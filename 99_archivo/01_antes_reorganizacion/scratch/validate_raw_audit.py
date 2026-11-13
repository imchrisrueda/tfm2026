"""Reconciliación independiente de los resultados de auditoría con disco y diseño."""
from pathlib import Path
import hashlib
import json
import pandas as pd

root = Path(__file__).resolve().parents[1]
out = root / 'data/processed/audit_raw_2026-11-12'
df = pd.read_csv(out / 'inventory.csv').astype(object).fillna('')
sessions = pd.read_csv(out / 'sessions.csv')
summary = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
checks = {}

def check(name, condition):
    checks[name] = bool(condition)
    if not condition:
        raise AssertionError(name)

on_disk = {p.relative_to(root).as_posix(): p.stat().st_size for p in (root / 'data/raw').rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg')}
check('exact_recursive_JPEG_path_coverage', set(df.relative_path) == set(on_disk))
check('unique_paths_and_image_ids', df.relative_path.is_unique and df.image_id.is_unique)
check('file_sizes_unchanged_since_scan', all(on_disk[r.relative_path] == r.bytes for r in df.itertuples()))
check('summary_and_session_totals_reconcile', len(df) == summary['image_count'] == sessions.images.sum() and df.bytes.sum() == summary['total_bytes'] == sessions.bytes.sum())
check('class_totals_and_unknowns_reconcile', sum(summary['species_provisional'].values()) == len(df) and len(df[df.species_code == '']) == 23)
check('no_read_errors_or_warnings', df.decode_status.eq('ok').all() and df.decode_warnings.eq('').all())
check('file_and_pixel_hash_uniqueness', df.sha256.is_unique and df.pixel_sha256.is_unique)
for year in (2025, 2026):
    grid = pd.read_csv(root / f'exp_design/{year}.csv', index_col='Fila')
    assigned = df[(df.year == year) & (df.pot_id != '')]
    check(f'design_species_consistency_{year}', all(grid.loc[int(r.fila), r.columna] == r.species_code for r in assigned.itertuples()))
for r in sessions.itertuples():
    group = df[df.session_id == r.session_id]
    check(f'session_{r.session_id}', len(group) == r.images and group.loc[group.pot_id != '', 'posicion'].nunique() == r.provisional_covered_pots)
v = df[df.session_id == '2026-06-12_c2_r2']
check('documented_missing_prefix_kept', sorted(v.verified_order.astype(int)) == list(range(83, 131)))
check('nested_Nikon_not_silently_labeled', df.loc[df.source_subdir != '.', 'pot_id'].eq('').all())
check('field_notes_attached_to_12_files', df.field_note.ne('').sum() == 12)
check('June_01_chronology_conflict_flagged', df.loc[df.session_id.eq('2026-06-01_c2_r2'), 'label_status'].eq('filename_chronology_conflict').all())
chronological = pd.read_csv(out / 'chronological_mapping_candidates.csv')
check('chronological_alternative_matches_report', len(chronological) == 130 and chronological.species_would_change.sum() == 93 and chronological.filename_order_position.ne(chronological.proposed_position).all())
check('all_dates_from_original_EXIF', df.exif_datetime_source.eq('DateTimeOriginal').all())
check('D70_day_offset_specific', df.loc[df.camera_model.eq('NIKON D70'), 'exif_date_offset_days'].eq(-1).all() and df.loc[df.camera_model.ne('NIKON D70'), 'exif_date_offset_days'].eq(0).all())
old = pd.read_csv(root / 'data/processed/manifest_all.csv')
comparison = old.assign(relative_path='data/' + old.relative_path).merge(df, on='relative_path', suffixes=('_old', '_audit'), validate='one_to_one')
check('old_423_hashes_preserved', len(comparison) == len(old) == 423 and comparison.sha256_old.eq(comparison.sha256_audit).all())
for source in summary['source_files']:
    path = root / source['path']
    check('source_hash_' + source['path'], hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256'])
check('visual_sample_paths_exist', all((root / path).is_file() for path in pd.read_csv(out / 'visual_sample.csv').relative_path))
(out / 'validation.json').write_text(json.dumps({'checks': checks, 'passed': all(checks.values()), 'scope': 'Reconciles inventory, filesystem sizes, design and source snapshot; does not re-identify plants.'}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'{len(checks)} comprobaciones correctas; {len(df)} archivos reconciliados.')
