#!/usr/bin/env python3
"""Auditoría P0 reproducible. Lee raw sin modificarlo; escribe sólo en --output_dir.

Las etiquetas proceden del diseño y de reglas de recorrido, no de identificación
botánica visual. Conserva explícitamente las asignaciones no confirmadas.
"""
import argparse
import hashlib
import json
import re
import warnings
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageOps, ImageFilter

from label_dataset import build_serpentine_sequence, get_session_pot_mapping, SPECIES_MAP


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save_csv(rows, path, columns=None):
    frame = pd.DataFrame(rows, columns=columns) if columns else pd.DataFrame(rows)
    frame.to_csv(path, index=False, encoding='utf-8-sig')
    return frame


def audit(root, output):
    raw = root / 'data/raw'
    output.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    designs = {year: build_serpentine_sequence(root / f'exp_design/{year}.csv') for year in (2025, 2026)}
    notes_path = raw / 'notes.txt'
    notes_text = notes_path.read_text(encoding='utf-8') if notes_path.exists() else ''
    note_counts = {m.group(1): int(m.group(2)) for m in re.finditer(r'^(\d{4}-\d{2}-\d{2}_c\d+_r\d+):\s*(\d+)', notes_text, re.M)}
    note_lines = {line.split(':', 1)[0]: line for line in notes_text.splitlines() if re.match(r'^\d{4}-', line)}
    rows, other_files, session_rows, missing, gaps, prior_diffs = [], [], [], [], [], []
    for path in sorted(p for p in raw.iterdir() if p.is_file()):
        other_files.append({'relative_path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)})
    for session in sorted(p for p in raw.iterdir() if p.is_dir()):
        match = re.fullmatch(r'(\d{4}-\d{2}-\d{2})_(c\d+)_(r\d+)', session.name)
        if not match:
            raise ValueError(f'Sesión sin formato reconocido: {session}')
        date, campaign, rep = match.groups()
        year = int(date[:4])
        sequence = designs[year]
        images = sorted(p for p in session.rglob('*') if p.is_file() and p.name not in {'grid_plot.png', 'verification_grid.png'} and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.heic', '.nef', '.arw', '.dng'})
        direct = [p for p in images if p.parent == session and p.suffix.lower() in {'.jpg', '.jpeg'}]
        mapping = get_session_pot_mapping(session.name, direct, sequence)
        by_path = dict(zip(direct, mapping))
        # Preserva la hipótesis específica documentada, sin convertirla en verdad validada.
        verified_path = session / 'verified_manifest.csv'
        verified = pd.read_csv(verified_path).set_index('target_filename').to_dict('index') if verified_path.exists() else {}
        for path in sorted(p for p in session.rglob('*') if p.is_file() and p not in images):
            other_files.append({'relative_path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)})
        def inspect_image(path):
            rel = path.relative_to(root).as_posix()
            row = dict(relative_path=rel, session_id=session.name, year=year, date_session=date,
                       image_id=f"{session.name}_{path.relative_to(session).as_posix()}",
                       campana=campaign, repeticion=rep, source_subdir=path.parent.relative_to(session).as_posix(),
                       filename=path.name, bytes=path.stat().st_size, sha256=digest(path),
                       decode_status='ok', decode_error='', decode_warnings='',
                       label_status='unassigned_nested', label_source='', species_code='', posicion='', pot_id='',
                       pot_diameter_nominal_cm=10 if year == 2025 else 20,
                       reference_card_expected=date == '2025-05-13', reference_card_observed='not_reviewed',
                       morphology_review='not_reviewed', plant_count_observed='', growth_stage='')
            note_line = note_lines.get(session.name, '')
            row['field_note'] = note_line if path.name.lower() in note_line.lower() else ''
            row['field_note_source'] = 'data/raw/notes.txt' if row['field_note'] else ''
            if path in by_path:
                info = by_path[path]
                row.update({k: info[k] for k in ('species_code', 'posicion', 'fila', 'columna')})
                row['capture_order_in_session'] = direct.index(path) + 1
                row['label_source'] = 'label_dataset.get_session_pot_mapping + exp_design'
                row['label_status'] = 'design_sequence_assumed'
                if len(direct) < len(sequence):
                    row['label_status'] = 'partial_sequence_assumed'
                if session.name == '2026-05-14_c2_r1' and len(direct) == 153:
                    row['label_status'] = 'documented_retake_rule_assumed'
                if path.name in verified:
                    vr = verified[path.name]
                    row.update({k: vr[k] for k in ('species_code', 'posicion', 'fila', 'columna')})
                    row.update(label_status='documented_missing_prefix_assignment', label_source='raw/notes.txt missing first 82; verified_manifest.csv; not botanical visual validation',
                               verified_order=vr['assigned_capture_order'], visual_match_rank=vr['match_rank'],
                               visual_hyp_correlation=vr['hyp_correlation'], visual_best_order=vr['best_matched_order'])
                if row['species_code'] in SPECIES_MAP:
                    row['pot_id'] = f"POT_{year}_{rep}_{row['posicion']}"
                row['species_scientific'] = SPECIES_MAP.get(row['species_code'], {}).get('species_scientific', '')
            try:
                with warnings.catch_warnings(record=True) as captured:
                    warnings.simplefilter('always')
                    with Image.open(path) as im:
                        im.verify()
                    with Image.open(path) as im:
                        im.load()  # verify() solo no comprueba la decodificación completa del JPEG
                        exif = im.getexif()
                        nested = exif.get_ifd(0x8769) if exif.get(0x8769) else {}
                        original = nested.get(36867) or exif.get(36867)
                        fallback = exif.get(306)
                        focal = nested.get(37386) or exif.get(37386)
                        row.update(width=im.width, height=im.height, mode=im.mode, format=im.format,
                                   exif_orientation=exif.get(274, 1), exif_orientation_present=274 in exif,
                                   camera_make=str(exif.get(271, '')).strip(), camera_model=str(exif.get(272, '')).strip(),
                                   exif_datetime_original=str(original or ''), exif_datetime_generic=str(fallback or ''),
                                   exif_datetime_used=str(original or fallback or ''),
                                   exif_datetime_source='DateTimeOriginal' if original else 'DateTime' if fallback else 'missing',
                                   focal_length_mm=float(focal) if focal else None, icc_profile_present=bool(im.info.get('icc_profile')))
                        oriented = ImageOps.exif_transpose(im).convert('RGB')
                        row['oriented_width'], row['oriented_height'] = oriented.size
                        row['pixel_sha256'] = hashlib.sha256(str(oriented.size).encode() + oriented.tobytes()).hexdigest()
                        small = oriented.copy()
                        small.thumbnail((256, 256))
                        gray = small.convert('L')
                        arr = np.asarray(gray, dtype=np.float32)
                        row['luminance_mean_0_255'] = round(float(arr.mean()), 3)
                        row['luminance_std'] = round(float(arr.std()), 3)
                        edge = np.asarray(gray.filter(ImageFilter.FIND_EDGES), dtype=np.float32)[1:-1, 1:-1]
                        row['edge_variance_thumbnail'] = round(float(edge.var()), 3)
                        dh = np.asarray(oriented.resize((9, 8)).convert('L'))
                        bits = dh[:, 1:] > dh[:, :-1]
                        row['dhash64'] = f"{int(''.join('1' if b else '0' for b in bits.flatten()), 2):016x}"
                    row['decode_warnings'] = ' | '.join(str(w.message) for w in captured)
                dt = row['exif_datetime_used']
                if dt:
                    try:
                        row['exif_date_offset_days'] = (datetime.strptime(dt[:10], '%Y:%m:%d') - datetime.strptime(date, '%Y-%m-%d')).days
                    except ValueError:
                        row['exif_date_parse_error'] = dt
            except Exception as exc:
                row.update(decode_status='error', decode_error=f'{type(exc).__name__}: {exc}')
            return row
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows.extend(pool.map(inspect_image, images))
        current = [r for r in rows if r['session_id'] == session.name]
        assigned = {r['posicion'] for r in current if r['pot_id']}
        counts = Counter(r['posicion'] for r in current if r['pot_id'])
        for p in sequence:
            if p['posicion'] not in assigned:
                missing.append(dict(session_id=session.name, **p, status='not_covered_under_documented_mapping'))
        # Gaps are diagnostic only: file numbering need not be continuous or start at 1.
        for parent in sorted(set(p.parent for p in images)):
            nums = sorted(int(m.group(1)) for p in images if p.parent == parent and (m := re.search(r'(\d+)$', p.stem)))
            for left, right in zip(nums, nums[1:]):
                if right > left + 1:
                    gaps.append(dict(session_id=session.name, source_subdir=parent.relative_to(session).as_posix(), before=left, after=right, gap=right-left-1))
        session_rows.append(dict(session_id=session.name, year=year, campana=campaign, repeticion=rep,
                                 images=len(current), direct_images=len(direct), nested_images=len(images)-len(direct),
                                 images_declared_notes=note_counts.get(session.name),
                                 design_pots=len(sequence), provisional_covered_pots=len(assigned),
                                 provisional_missing_pots=len(sequence)-len(assigned),
                                 provisional_multi_photo_pots=sum(n > 1 for n in counts.values()),
                                 **{f'images_{c}': sum(r['species_code'] == c for r in current) for c in ('P', 'H', 'R', 'M')},
                                 unassigned_images=sum(not r['pot_id'] for r in current),
                                 decode_errors=sum(r['decode_status'] != 'ok' for r in current),
                                 bytes=sum(r['bytes'] for r in current)))
        print(f"{session.name}: {len(current)} imágenes, {len(assigned)}/{len(sequence)} posiciones provisionales", flush=True)

    df = save_csv(rows, output / 'inventory.csv')
    sessions = save_csv(session_rows, output / 'sessions.csv')
    save_csv(missing, output / 'missing_positions.csv')
    save_csv(other_files, output / 'non_image_files.csv')
    save_csv(gaps, output / 'filename_gaps.csv')
    duplicates = []
    for key, kind in [('sha256', 'identical_file'), ('pixel_sha256', 'identical_oriented_RGB_pixels')]:
        for val, group in df.dropna(subset=[key]).groupby(key):
            if len(group) > 1:
                for path in group.relative_path:
                    duplicates.append(dict(kind=kind, hash=val, group_size=len(group), relative_path=path))
    save_csv(duplicates, output / 'duplicates.csv', ['kind', 'hash', 'group_size', 'relative_path'])
    near = []
    for session, group in df.dropna(subset=['dhash64']).groupby('session_id'):
        items = group.to_dict('records')
        for i, a in enumerate(items):
            for b in items[i+1:]:
                dist = (int(a['dhash64'], 16) ^ int(b['dhash64'], 16)).bit_count()
                if dist <= 6:
                    near.append(dict(session_id=session, path_a=a['relative_path'], path_b=b['relative_path'], dhash_distance=dist,
                                     same_provisional_pot=bool(a['pot_id']) and a['pot_id'] == b['pot_id'], status='candidate_only_not_duplicate_confirmation'))
    save_csv(near, output / 'near_duplicate_candidates.csv', ['session_id', 'path_a', 'path_b', 'dhash_distance', 'same_provisional_pot', 'status'])

    # Reconciliación del consolidado existente; no se sobrescribe evidencia previa.
    oldpath = root / 'data/processed/manifest_all.csv'
    old = pd.read_csv(oldpath) if oldpath.exists() else pd.DataFrame(columns=['relative_path'])
    existing = {f"data/{str(r['relative_path']).replace(chr(92), '/')}": r for r in old.to_dict('records')}
    for r in rows:
        prior = existing.pop(r['relative_path'], None)
        if prior is None:
            prior_diffs.append(dict(relative_path=r['relative_path'], field='row', old_value='', audit_value='missing_in_existing_global_manifest'))
        else:
            for field in ('sha256', 'species_code', 'posicion', 'pot_id', 'width', 'height'):
                if str(prior.get(field)) != str(r.get(field)):
                    prior_diffs.append(dict(relative_path=r['relative_path'], field=field, old_value=prior.get(field), audit_value=r.get(field)))
    for path in existing:
        prior_diffs.append(dict(relative_path=path, field='row', old_value='in_existing_manifest', audit_value='not_found_in_raw'))
    save_csv(prior_diffs, output / 'existing_manifest_differences.csv', ['relative_path', 'field', 'old_value', 'audit_value'])
    chronology = []
    chronological_candidates = []
    for (session, subdir), group in df.groupby(['session_id', 'source_subdir']):
        ordered = group.sort_values('filename')
        times = pd.to_datetime(ordered.exif_datetime_used, format='%Y:%m:%d %H:%M:%S', errors='coerce')
        for index in ordered.index[times.diff().dt.total_seconds().lt(0)]:
            chronology.append(dict(session_id=session, source_subdir=subdir, filename=df.loc[index, 'filename'],
                                   datetime=df.loc[index, 'exif_datetime_used'], status='filename_order_reverses_EXIF_time'))
        if times.diff().dt.total_seconds().lt(0).any():
            df.loc[group.index, 'label_status'] = 'filename_chronology_conflict'
            if subdir == '.' and len(group) == len(designs[int(group.year.iloc[0])]):
                for rank, (_, r) in enumerate(group.sort_values(['exif_datetime_used', 'filename']).iterrows()):
                    proposed = designs[int(r.year)][rank]
                    chronological_candidates.append(dict(relative_path=r.relative_path, session_id=session,
                        chronological_order=rank+1, exif_datetime=r.exif_datetime_used,
                        filename_order_position=r.posicion, filename_order_species=r.species_code,
                        proposed_position=proposed['posicion'], proposed_species=proposed['species_code'],
                        species_would_change=r.species_code != proposed['species_code'],
                        status='chronological_candidate_requires_field_confirmation'))
    save_csv(chronology, output / 'chronology_inversions.csv', ['session_id', 'source_subdir', 'filename', 'datetime', 'status'])
    save_csv(chronological_candidates, output / 'chronological_mapping_candidates.csv', ['relative_path', 'session_id', 'chronological_order', 'exif_datetime', 'filename_order_position', 'filename_order_species', 'proposed_position', 'proposed_species', 'species_would_change', 'status'])
    df.to_csv(output / 'inventory.csv', index=False, encoding='utf-8-sig')
    for field in ('camera_model', 'exif_orientation', 'label_status', 'exif_date_offset_days'):
        df.groupby(['session_id', field], dropna=False).size().reset_index(name='images').to_csv(output / f'by_{field}.csv', index=False, encoding='utf-8-sig')
    for field in ('year', 'camera_model', 'session_id'):
        pd.crosstab(df[field], df.species_code.replace('', 'UNASSIGNED')).to_csv(output / f'species_by_{field}.csv', encoding='utf-8-sig')
    provenance = []
    for path in sorted(set(list((root / 'exp_design').glob('*.csv')) + list((root / 'scripts').glob('*.py')) + list((root / 'scripts').glob('*.md')) + list(root.glob('*.md')))):
        provenance.append(dict(path=path.relative_to(root).as_posix(), sha256=digest(path), bytes=path.stat().st_size))
    summary = dict(started_utc=started, completed_utc=datetime.now(timezone.utc).isoformat(), image_count=len(df),
                   total_bytes=int(df.bytes.sum()), session_count=len(sessions), existing_manifest_rows=len(old),
                   images_missing_in_existing_manifest=sum(d['audit_value'] == 'missing_in_existing_global_manifest' for d in prior_diffs),
                   decode_errors=int((df.decode_status != 'ok').sum()), decode_warnings=int((df.decode_warnings != '').sum()),
                   unique_sha256=int(df.sha256.nunique()), unique_oriented_pixel_hashes=int(df.pixel_sha256.nunique()),
                   nested_images=int((df.source_subdir != '.').sum()), provisional_pot_ids=int(df.loc[df.pot_id != '', 'pot_id'].nunique()),
                   provisional_pot_session_pairs=int(sessions.provisional_covered_pots.sum()), design_pot_session_pairs=int(sessions.design_pots.sum()),
                   near_duplicate_candidate_pairs=len(near), label_status=df.label_status.value_counts().to_dict(),
                   chronology_inversions=len(chronology), images_with_field_notes=int(df.field_note.ne('').sum()),
                   camera_models=df.camera_model.value_counts(dropna=False).to_dict(),
                   dimensions=df.groupby(['width', 'height']).size().to_dict().__str__(),
                   missing_focal_length=int(df.focal_length_mm.isna().sum()), missing_datetime=int((df.exif_datetime_used == '').sum()),
                   species_provisional=df.species_code.replace('', 'UNASSIGNED').value_counts().to_dict(),
                   source_files=provenance + [dict(path='data/raw/notes.txt', sha256=digest(notes_path), bytes=notes_path.stat().st_size)] if notes_path.exists() else provenance,
                   rules={'scope': 'all supported images recursively under data/raw; other files inventoried separately',
                          'species': 'design-derived provisional labels, no botanical confirmation',
                          'nested': 'no assumed mapping for nested acquisition',
                          'near_duplicates': 'within session dHash Hamming <= 6, screening only; negatives do not exclude related plants',
                          'plant_counts': '2025_details.csv has no explicit position key/order contract, not joined',
                          'integrity': 'SHA256 current snapshot, no earlier baseline proving historical integrity'})
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('source_files', 'rules')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output_dir', type=Path, default=Path('data/processed/audit_raw_2026-11-12'))
    args = parser.parse_args()
    audit(args.root.resolve(), args.output_dir.resolve())
