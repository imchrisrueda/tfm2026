#!/usr/bin/env python3
"""Copias con especie de diseño para revisión; reglas confirmadas en M003–M014.

No modifica raw ni los manifiestos históricos. Las especies son esperadas, no
confirmaciones visuales. La tabla de revisión humana no se sobrescribe.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

import pandas as pd
from PIL import Image, ImageOps
from label_dataset import build_serpentine_sequence, SPECIES_MAP


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def run(root, output):
    started = datetime.now(timezone.utc).isoformat()
    raw = root / 'data/raw'
    historical_path = root / 'data/processed/audit_raw_2026-11-12/inventory.csv'
    historical = pd.read_csv(historical_path, keep_default_na=False)
    cache = historical.set_index('relative_path').to_dict('index')
    seqs = {y: build_serpentine_sequence(root / f'exp_design/{y}.csv') for y in (2025, 2026)}
    counts2025 = pd.read_csv(root / 'exp_design/2025_details.csv').num_plants.tolist()
    if len(counts2025) != len(seqs[2025]):
        raise ValueError('Los detalles de siembra no tienen una fila por posición de 2025')
    counts_by_position = {r['posicion']: n for r, n in zip(seqs[2025], counts2025)}
    source_paths = sorted(p for p in raw.rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg'))
    current = {p.relative_to(root).as_posix() for p in source_paths}
    if current - cache.keys():
        raise ValueError('Hay fotografías nuevas sin metadatos auditados; inventariarlas antes de preparar copias')
    def snapshot_source(path):
        relative = path.relative_to(root).as_posix()
        prior = cache[relative]
        actual_hash = sha256(path)
        info = dict(prior)
        info['historical_sha256'] = prior['sha256']
        info['sha256'] = actual_hash
        info['source_changed_since_audit'] = actual_hash != prior['sha256']
        info['pixel_comparison'] = 'file_identical'
        info['datetime_metadata_source'] = 'initial_audit_file_hash_unchanged'
        if info['source_changed_since_audit']:
            with Image.open(path) as im:
                exif = im.getexif()
                nested = exif.get_ifd(0x8769) if exif.get(0x8769) else {}
                dt = nested.get(36867) or exif.get(36867)
                oriented = ImageOps.exif_transpose(im).convert('RGB')
                pixels = hashlib.sha256(str(oriented.size).encode() + oriented.tobytes()).hexdigest()
                info['pixel_comparison'] = 'oriented_pixels_unchanged' if pixels == prior['pixel_sha256'] else 'oriented_pixels_changed_requires_review'
                if dt:
                    info['exif_datetime_original'] = str(dt)
                    info['datetime_metadata_source'] = 'current_original_EXIF'
                else:
                    info['datetime_metadata_source'] = 'historical_audit_EXIF_current_original_tag_absent'
        return relative, info
    with ThreadPoolExecutor(max_workers=4) as pool:
        cache = dict(pool.map(snapshot_source, source_paths))
    removed = historical.loc[~historical.relative_path.isin(current)].copy()
    output.mkdir(parents=True, exist_ok=True)
    rows, time_ties = [], []
    dead = {
        ('2025-06-16_c1_r2', 'dsc_0263.jpg'),
        *{('2025-06-20_c1_r2', n) for n in ('img_4153.jpg', 'img_4155.jpg', 'img_4170.jpg', 'img_4182.jpg')},
    }
    empty = {('2025-05-28_c1_r1', 'dsc_0025.jpg'), ('2025-05-28_c1_r1', 'dsc_0039.jpg'), ('2025-06-05_c1_r2', 'dsc_0145.jpg')}
    source_time = lambda p: datetime.strptime(cache[p.relative_to(root).as_posix()]['exif_datetime_original'], '%Y:%m:%d %H:%M:%S')
    for session in sorted(p for p in raw.iterdir() if p.is_dir()):
        date, campaign, rep = session.name.split('_')
        year = int(date[:4])
        sequence = seqs[year]
        session_paths = [p for p in source_paths if p.is_relative_to(session)]
        for parent in sorted({p.parent for p in session_paths}):
            images = sorted((p for p in session_paths if p.parent == parent), key=lambda p: (source_time(p), p.name))
            timestamps = Counter(source_time(p) for p in images)
            ties = {t for t, n in timestamps.items() if n > 1}
            for path in images:
                if source_time(path) in ties:
                    time_ties.append({'relative_path': path.relative_to(root).as_posix(), 'datetime': source_time(path).isoformat()})
            if parent != session:
                if session.name != '2025-06-20_c1_r2' or parent.name != 'nikon_d70' or len(images) != 23:
                    raise ValueError(f'Adquisición anidada sin regla documentada: {parent}')
                selected_sequence = sequence[:23]
                rule = 'investigator_confirmed_Nikon_first_23_serpentine'
            elif session.name in ('2025-06-16_c1_r2', '2025-06-20_c1_r2'):
                if len(images) != 60:
                    raise ValueError(f'Se esperaban 60 imágenes seleccionadas: {session.name}')
                selected_sequence = [s for s in sequence if s['species_code'] != 'M']
                rule = 'investigator_confirmed_60_Amaranthus_positions'
            elif session.name == '2026-06-12_c2_r2':
                if [p.stem.upper() for p in images] != [f'DSC_{n:04d}' for n in range(83, 131)]:
                    raise ValueError('El tramo incompleto ya no coincide con las capturas 83–130 declaradas')
                selected_sequence = sequence[82:130]
                rule = 'field_notes_missing_first_82'
            else:
                if len(images) != len(sequence):
                    raise ValueError(f'Recuento no contemplado: {session.name}: {len(images)}')
                selected_sequence = sequence
                rule = 'chronological_serpentine_design'
                if session.name == '2026-05-14_c2_r1':
                    names = [p.stem.upper() for p in images]
                    if names[names.index('DSC_0783')+1] != 'DSC_0809':
                        raise ValueError('No se cumple la corrección 0783 → 0809 del investigador')
                    rule = 'investigator_selected_130_after_removing_retakes'
                elif session.name == '2026-06-01_c2_r2':
                    rule = 'investigator_confirmed_EXIF_chronology_then_serpentine'
            for index, (path, position) in enumerate(zip(images, selected_sequence), 1):
                relative = path.relative_to(root).as_posix()
                prior = cache[relative]
                species = SPECIES_MAP[position['species_code']]['species_scientific']
                design_order = next(i for i, s in enumerate(sequence, 1) if s['posicion'] == position['posicion'])
                subdir = parent.relative_to(session)
                name = f"{design_order:04d}_{species.replace(' ', '_')}_{position['posicion']}_{path.name}"
                target = output / session.name / subdir / name
                key = (session.name, path.name.lower())
                exclusion = 'visual_band_corruption' if key == ('2025-06-05_c1_r2', 'dsc_0081.jpg') else 'dead_or_dry_plant_field_note' if key in dead else 'no_target_plant_field_note' if key in empty else ''
                suspected = campaign == 'c2' and rep == 'r2' and position['posicion'] in ('F26C1', 'F4C4')
                rows.append(dict(source_path=relative, verification_path=target.relative_to(root).as_posix(),
                    session_id=session.name, year=year, campana=campaign, repeticion=rep,
                    acquisition_subdir=subdir.as_posix(), filename_original=path.name, filename_verification=name,
                    order_in_acquisition=index, design_order=design_order, posicion=position['posicion'],
                    fila=position['fila'], columna=position['columna'], species_code=position['species_code'],
                    species_expected=species, label_source=rule, label_status='design_label_pending_visual_review',
                    pot_id=f"POT_{year}_{rep}_{position['posicion']}", grouping_source='investigator_same_pots_and_plants_between_dates',
                    date_session=date, exif_datetime_original=prior['exif_datetime_original'],
                    datetime_metadata_source=prior['datetime_metadata_source'],
                    date_source='session_directory_investigator_confirmed',
                    chronological_time_tie=source_time(path) in ties,
                    num_plants_seeded_2025=counts_by_position[position['posicion']] if year == 2025 else '',
                    num_plants_nominal_2026=1 if year == 2026 else '', num_plants_observed='',
                    pot_diameter_nominal_cm=10 if year == 2025 else 20,
                    reference_card_expected=date == '2025-05-13', scale_reference='outer_pot_rim',
                    priority_visual_review=suspected, review_note='investigator_doubt_C2_R2_position' if suspected else '',
                    field_note=prior.get('field_note', ''), exclude_from_primary_training=bool(exclusion),
                    exclusion_reason=exclusion, possible_background_requires_review=key in dead or key in empty,
                    training_eligibility='excluded' if exclusion else 'pending_visual_review_and_dataset_partition',
                    old_inventory_species=prior['species_code'], old_inventory_position=prior['posicion'],
                    historical_sha256=prior['historical_sha256'], source_changed_since_audit=prior['source_changed_since_audit'],
                    pixel_comparison_since_audit=prior['pixel_comparison'],
                    sha256=prior['sha256'], bytes=path.stat().st_size))
    if len(rows) != len(source_paths) or len({r['verification_path'] for r in rows}) != len(rows):
        raise ValueError('Las copias no mantienen una correspondencia uno a uno')
    expected_paths = {root / r['verification_path'] for r in rows}
    existing_images = {p for p in output.rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg')}
    if existing_images - expected_paths:
        raise ValueError('La carpeta de destino contiene imágenes ajenas al plan actual; no se borran ni se mezclan automáticamente')

    def copy_checked(row):
        source, target = root / row['source_path'], root / row['verification_path']
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if sha256(source) != row['sha256'] or sha256(target) != row['sha256']:
                raise ValueError(f'La copia existente o el origen difiere del inventario: {source}')
            return 'existing_identical'
        temporary = target.with_name(target.name + '.partial')
        if temporary.exists():
            if sha256(source) != row['sha256'] or sha256(temporary) != row['sha256']:
                raise ValueError(f'La copia parcial requiere revisión: {temporary}')
            temporary.rename(target)
            shutil.copystat(source, target)
            return 'resumed_identical_verified'
        h = hashlib.sha256()
        with source.open('rb') as src, temporary.open('xb') as dst:
            for chunk in iter(lambda: src.read(1024 * 1024), b''):
                h.update(chunk)
                dst.write(chunk)
        if h.hexdigest() != row['sha256'] or sha256(temporary) != row['sha256']:
            raise ValueError(f'Los bytes no coinciden con el original auditado: {source}')
        temporary.rename(target)
        shutil.copystat(source, target)
        return 'copied_verified'

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(copy_checked, rows))
    df = pd.DataFrame(rows)
    df['copy_status'] = outcomes
    df.to_csv(output / 'manifest.csv', index=False, encoding='utf-8-sig')
    df[df.source_changed_since_audit].to_csv(output / 'source_changes_since_initial_audit.csv', index=False, encoding='utf-8-sig')
    removed['current_status'] = 'not_in_raw_after_investigator_manual_selection'
    removed['historical_label_is_not_visual_confirmation'] = True
    removed.to_csv(output / 'removed_since_initial_audit.csv', index=False, encoding='utf-8-sig')
    review_columns = ['source_path', 'verification_path', 'session_id', 'posicion', 'species_expected', 'priority_visual_review', 'exclude_from_primary_training', 'exclusion_reason']
    review = df[review_columns].copy()
    review['review_status'] = 'pending'
    review['species_observed'] = ''
    review['reviewer'] = ''
    review['review_date'] = ''
    review['comments'] = ''
    review_path = output / 'revision_visual.csv'
    if not review_path.exists():
        review.to_csv(review_path, index=False, encoding='utf-8-sig')
    else:
        oldreview = pd.read_csv(review_path, keep_default_na=False)
        if set(oldreview.source_path) != set(df.source_path):
            raise ValueError('La revisión visual existente necesita una migración explícita para preservar respuestas')
    df[df.priority_visual_review].to_csv(output / 'revisar_primero.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(time_ties, columns=['relative_path', 'datetime']).to_csv(output / 'time_ties.csv', index=False)
    session_summary = df.groupby('session_id').agg(images=('source_path', 'size'), pots=('pot_id', 'nunique'),
        excluded_primary=('exclude_from_primary_training', 'sum'), priority_review=('priority_visual_review', 'sum'))
    session_summary.to_csv(output / 'sessions.csv', encoding='utf-8-sig')
    pd.crosstab(df.session_id, df.species_expected).to_csv(output / 'species_by_session.csv', encoding='utf-8-sig')
    sources = ['scripts/prepare_sowing_verification.py', 'exp_design/2025.csv', 'exp_design/2025_details.csv', 'exp_design/2026.csv',
        'data/processed/audit_raw_2026-11-12/dudas.md', 'data/processed/audit_raw_2026-11-12/inventory.csv']
    summary = dict(started_utc=started, completed_utc=datetime.now(timezone.utc).isoformat(),
        images=len(df), sessions=int(df.session_id.nunique()), bytes=int(df.bytes.sum()),
        copies_hash_verified=len(df), unique_hashes=int(df.sha256.nunique()),
        source_files_changed_since_audit=int(df.source_changed_since_audit.sum()),
        species_expected=df.species_expected.value_counts().to_dict(),
        files_removed_since_initial_audit=len(removed), priority_review_images=int(df.priority_visual_review.sum()),
        excluded_primary_training=int(df.exclude_from_primary_training.sum()),
        time_tied_images=len(time_ties), visual_review_completed=0,
        June_01_species_changed=int(((df.session_id == '2026-06-01_c2_r2') & (df.old_inventory_species != df.species_code)).sum()),
        June_20_Nikon_assigned=int(((df.session_id == '2025-06-20_c1_r2') & (df.acquisition_subdir == 'nikon_d70')).sum()),
        sources=[dict(path=p, sha256=sha256(root / p)) for p in sources],
        environment=dict(python=sys.version, pandas=pd.__version__),
        limitations=['species are expected from sowing design, pending investigator visual review',
            '2025 counts are seeded, 2026 counts nominal, neither is observed live plant count',
            'historical audit outputs and original labeling scripts are not updated by this command'])
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('sources', 'environment', 'limitations')}, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output_dir', type=Path, default=Path('data/verificacion_siembra'))
    args = parser.parse_args()
    run(args.root.resolve(), args.output_dir.resolve())
