#!/usr/bin/env python3
"""Construye los manifiestos vigentes; aplica correcciones sin alterar raw.

Fuentes: adquisición conciliada en verificacion_siembra, EXIF y bytes actuales,
diseños, reglas explícitas de corrección y revisión del investigador (M018).
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

import pandas as pd
from PIL import Image, ImageOps
from s14_label_dataset import SPECIES_MAP
from s09_create_group_partitions import snapshot_fingerprint


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def truth(value):
    return str(value).lower() == 'true'


def optional_int(value):
    return int(float(value)) if str(value) != '' else None


def write_json(path, value):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


def write_csv(path, frame):
    temporary = path.with_name(path.name + '.tmp')
    frame.to_csv(temporary, index=False, encoding='utf-8-sig')
    temporary.replace(path)


def run(root):
    started = datetime.now(timezone.utc)
    run_id = started.strftime('%Y%m%dT%H%M%S%fZ')
    out = root / 'data/processed'
    verification_path = root / 'data/verificacion_siembra/manifest.csv'
    review_path = root / 'data/verificacion_siembra/revision_visual.csv'
    corrections_path = root / 'exp_design/14_species_corrections.csv'
    acquisition_policy_path = root / 'exp_design/04_acquisition_policy.json'
    acquisition_policy = json.loads(acquisition_policy_path.read_text(encoding='utf-8'))
    deferred_acquisitions = {(r['session_id'], r['acquisition_subdir']): r for r in acquisition_policy['deferred_acquisitions']}
    change_decisions = {r['source_path']: r for r in acquisition_policy['source_change_decisions']}
    historical_path = out / 'audit_raw_2026-11-12/inventory.csv'
    verified = pd.read_csv(verification_path, keep_default_na=False)
    reviews = pd.read_csv(review_path, keep_default_na=False)
    corrections = pd.read_csv(corrections_path, keep_default_na=False)
    historical = pd.read_csv(historical_path, keep_default_na=False).set_index('relative_path').to_dict('index')
    grids = {year: pd.read_csv(root / {2025: 'exp_design/01_2025.csv', 2026: 'exp_design/03_2026.csv'}[year], index_col='Fila') for year in (2025, 2026)}
    correction_key = ['year', 'campana', 'repeticion', 'posicion']
    if corrections.duplicated(correction_key).any():
        raise ValueError('Hay correcciones superpuestas para la misma maceta')
    rules = {tuple(r[k] for k in correction_key): r for r in corrections.to_dict('records')}
    paths = {p.relative_to(root).as_posix() for p in (root / 'data/raw').rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg')}
    if paths != set(verified.source_path) or not verified.source_path.is_unique:
        raise ValueError('El corpus actual difiere de la adquisición conciliada; revisar altas/bajas antes de asignar posiciones')
    if set(reviews.source_path) != paths or not reviews.source_path.is_unique:
        raise ValueError('La tabla de revisión no cubre exactamente las fotografías actuales')
    updated_reviews = reviews.copy()
    corrected_paths = set()
    for row in verified.to_dict('records'):
        key = tuple(row[k] for k in correction_key)
        if key not in rules:
            continue
        rule = rules[key]
        expected = str(grids[int(row['year'])].loc[int(row['fila']), row['columna']])
        if expected != rule['design_species_code']:
            raise ValueError(f'La corrección no coincide con el diseño de {row["source_path"]}')
        mask = updated_reviews.source_path == row['source_path']
        previous = updated_reviews.loc[mask, 'species_observed'].iloc[0]
        comment = f"{rule['correction_id']}: palmeri confirmado por el investigador en conversación {rule['confirmation_date']}; error con la semilla declarado; alcance: misma maceta entre fechas."
        if previous and previous != SPECIES_MAP[rule['corrected_species_code']]['species_scientific']:
            comment += f' Especie observada anteriormente registrada: {previous}.'
        oldcomment = updated_reviews.loc[mask, 'comments'].iloc[0]
        if comment not in oldcomment:
            updated_reviews.loc[mask, 'comments'] = (oldcomment + ' | ' + comment).strip(' |')
        updated_reviews.loc[mask, 'review_status'] = 'corrected'
        updated_reviews.loc[mask, 'species_observed'] = SPECIES_MAP[rule['corrected_species_code']]['species_scientific']
        updated_reviews.loc[mask, 'reviewer'] = 'investigador; confirmación en conversación'
        updated_reviews.loc[mask, 'review_date'] = rule['confirmation_date']
        corrected_paths.add(row['source_path'])
    review_lookup = updated_reviews.set_index('source_path').to_dict('index')

    def build_record(base):
        source = root / base['source_path']
        before = source.stat()
        current_hash = digest(source)
        old = historical[base['source_path']]
        rule = rules.get(tuple(base[k] for k in correction_key))
        design_code = str(grids[int(base['year'])].loc[int(base['fila']), base['columna']])
        if design_code != base['species_code']:
            raise ValueError(f'La asignación conciliada no coincide con la especie del diseño: {source}')
        code = rule['corrected_species_code'] if rule else design_code
        meta = SPECIES_MAP[code]
        review = review_lookup[base['source_path']]
        if not rule and review['species_observed'] and review['species_observed'] != meta['species_scientific']:
            raise ValueError(f'Existe una revisión de especie sin regla explícita de corrección: {source}')
        unchanged_audit = current_hash == old['sha256']
        with Image.open(source) as im:
            width, height, mode, image_format = im.width, im.height, im.mode, im.format
            exif = im.getexif()
            nested = exif.get_ifd(0x8769) if exif.get(0x8769) else {}
            original = nested.get(36867) or exif.get(36867)
            generic = exif.get(306)
            focal = nested.get(37386) or exif.get(37386)
            orientation = int(exif.get(274, 1))
            camera_make = str(exif.get(271, '')).strip()
            camera_model = str(exif.get(272, '')).strip()
            icc = bool(im.info.get('icc_profile'))
            if unchanged_audit:
                if old['decode_status'] != 'ok':
                    raise ValueError(f'La auditoría no acredita decodificación correcta: {source}')
                pixel_hash = old['pixel_sha256']
                decode_source = 'initial_full_decode_same_file_SHA256'
            else:
                im.load()
                oriented = ImageOps.exif_transpose(im).convert('RGB')
                pixel_hash = hashlib.sha256(str(oriented.size).encode() + oriented.tobytes()).hexdigest()
                decode_source = 'full_decode_this_build'
        after = source.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError(f'El original cambió durante la lectura: {source}')
        observed_dt = str(original or generic or '')
        try:
            exif_date_offset = (datetime.strptime(observed_dt[:10], '%Y:%m:%d') - datetime.strptime(base['date_session'], '%Y-%m-%d')).days
        except ValueError:
            exif_date_offset = None
        excluded = truth(base['exclude_from_primary_training'])
        auxiliary = code == 'M'
        reason = base['exclusion_reason'] or None
        deferred = deferred_acquisitions.get((base['session_id'], base['acquisition_subdir']))
        use_initial = deferred is None
        change_decision = change_decisions.get(base['source_path'])
        if change_decision and current_hash != change_decision['accepted_sha256']:
            raise ValueError(f'El archivo ha cambiado de nuevo después de la aceptación del investigador: {source}')
        pixel_changed = pixel_hash != old['pixel_sha256']
        acquisition_time = datetime.strptime(base['exif_datetime_original'], '%Y:%m:%d %H:%M:%S').strftime('%H:%M:%S')
        label_status = 'investigator_visual_confirmed_correction' if rule else 'assigned_from_design_and_confirmed_acquisition'
        return dict(
            manifest_schema_version='1.1', manifest_build_id=run_id,
            image_id=old['image_id'], filename=source.name, source_path=base['source_path'],
            relative_path=source.relative_to(root / 'data').as_posix(), path_base='project/data',
            verification_path=base['verification_path'], verification_filename_is_design_label=True,
            session_id=base['session_id'], year=int(base['year']), date_session=base['date_session'],
            date_session_source='session_directory_investigator_confirmed', campana=base['campana'], repeticion=base['repeticion'],
            acquisition_subdir=base['acquisition_subdir'], order_in_acquisition=int(base['order_in_acquisition']),
            capture_order=int(base['design_order']), fila=int(base['fila']), columna=base['columna'], posicion=base['posicion'],
            pot_id=base['pot_id'], split_group_id=f"GROUP_{base['year']}_{base['campana']}_{base['repeticion']}_{base['posicion']}",
            group_source='investigator_same_pot_and_plants_across_dates_and_cameras',
            cross_repetition_independence_status='not_separately_documented', plant_id=None,
            design_species_code=design_code, design_species_scientific=SPECIES_MAP[design_code]['species_scientific'],
            species_code=code, species_scientific=meta['species_scientific'], genus=meta['genus'], class_label=meta['class_label'],
            is_target_species=meta['is_target_species'], is_auxiliary=meta['is_auxiliary'],
            label_status=label_status, label_source=rule['confirmation_source'] if rule else base['label_source'],
            label_correction_applied=bool(rule), label_correction_id=rule['correction_id'] if rule else None,
            label_correction_reason=rule['reported_cause'] if rule else None,
            label_confirmation_date=rule['confirmation_date'] if rule else None,
            label_scope='all_dates_and_cameras_same_pot' if rule else 'design_position',
            species_review_status='corrected_and_confirmed_by_investigator' if rule else 'no_individual_visual_confirmation_recorded',
            investigator_review_status=review['review_status'], reviewer=review['reviewer'] or None,
            review_date=review['review_date'] or None, review_comments=review['comments'] or None,
            sowing_review_priority_unresolved=truth(base['priority_visual_review']) and not bool(rule),
            num_plants_seeded_2025=optional_int(base['num_plants_seeded_2025']),
            num_plants_nominal_2026=optional_int(base['num_plants_nominal_2026']), num_plants_observed=None,
            plant_count_source='2025_details_serpentine_seeded' if int(base['year']) == 2025 else 'investigator_2026_one_nominal_plant_per_pot',
            plant_presence_status='absent_field_note' if reason == 'no_target_plant_field_note' else 'not_exhaustively_reviewed',
            plant_health_status='dead_or_dry_field_note' if reason == 'dead_or_dry_plant_field_note' else 'not_exhaustively_reviewed',
            growth_stage=None, visibility_status='not_exhaustively_reviewed', field_note=base['field_note'] or None,
            field_note_source='data/raw/notes.txt' if base['field_note'] else None,
            exclude_from_primary_training=excluded, exclusion_reason=reason,
            use_in_initial_partition=use_initial,
            acquisition_selection_status=deferred['status'] if deferred else 'included_in_initial_partition_pool',
            acquisition_selection_reason=deferred['reason'] if deferred else None,
            acquisition_selection_source=f"exp_design/04_acquisition_policy.json#{acquisition_policy['policy_id']}",
            is_classifier_candidate=not excluded and not auxiliary and use_initial,
            is_lora_candidate=not excluded and code == 'P' and use_initial,
            intended_role='excluded_primary_training' if excluded else 'secondary_acquisition_reserve' if deferred else 'auxiliary_maize' if auxiliary else 'primary_species_candidate',
            possible_background_requires_review=truth(base['possible_background_requires_review']),
            training_eligibility='excluded_primary_training' if excluded else 'deferred_incomplete_secondary_acquisition' if deferred else 'auxiliary_only' if auxiliary else 'candidate_pending_geometry_and_split',
            split_assignment='unassigned', split_assignment_source='not_created',
            pot_diameter_exterior_cm=float(base['pot_diameter_nominal_cm']), pot_diameter_source='investigator_nominal_by_year',
            scale_reference='outer_pot_rim', geometry_status='not_measured',
            pot_center_x_px=None, pot_center_y_px=None, pot_diameter_px=None, scale_cm_per_px=None,
            common_field_cm=None, geometry_reference_quality=None,
            has_reference_card=truth(base['reference_card_expected']), reference_card_status='expected_from_session_field_notes',
            reference_card_observed=None, reference_card_width_cm=None, reference_card_height_cm=None,
            bytes=after.st_size, sha256=current_hash, sha256_initial_audit=old['sha256'],
            source_changed_since_initial_audit=not unchanged_audit,
            sha256_verification_preparation=base['sha256'], source_changed_since_verification=current_hash != base['sha256'],
            pixel_sha256_oriented_RGB=pixel_hash, pixels_changed_since_initial_audit=pixel_changed,
            source_change_review_status='accepted_as_is_by_investigator' if change_decision else 'review_required_cause_unresolved' if pixel_changed else 'unchanged_since_initial_audit',
            source_change_decision=change_decision['decision'] if change_decision else None,
            source_change_decision_source=f"exp_design/04_acquisition_policy.json#{acquisition_policy['policy_id']}" if change_decision else None,
            decode_status='ok', decode_evidence=decode_source,
            width=width, height=height, mode=mode, image_format=image_format,
            oriented_width=height if orientation in (5, 6, 7, 8) else width,
            oriented_height=width if orientation in (5, 6, 7, 8) else height,
            exif_orientation=orientation, exif_orientation_present=274 in exif,
            exif_camera_make=camera_make or None, exif_camera_model=camera_model or None,
            exif_datetime_original=str(original) if original else None, exif_datetime_generic=str(generic) if generic else None,
            exif_datetime_source='DateTimeOriginal' if original else 'DateTime_fallback' if generic else 'missing',
            exif_focal_length_mm=float(focal) if focal is not None else None,
            exif_date_offset_days=exif_date_offset, exif_timezone_status='not_established',
            acquisition_order_datetime=base['exif_datetime_original'], acquisition_order_source=base['datetime_metadata_source'],
            acquisition_time_of_day=acquisition_time, chronological_time_tie=truth(base['chronological_time_tie']),
            icc_profile_present=icc, processing_status='raw_original',
            master_image_path=None, preprocessing_status='not_created', pipeline_status='raw_manifest_consolidated')

    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(build_record, verified.to_dict('records')))
    frame = pd.DataFrame(records)
    partition_path = root / 'exp_design/07_partition_assignments_v1.csv'
    partition_plan_path = root / 'exp_design/08_partition_plan_v1.json'
    partition_plan = None
    if partition_path.exists() != partition_plan_path.exists():
        raise ValueError('La asignación y el plan de particiones deben existir juntos')
    if partition_path.exists():
        partition_plan = json.loads(partition_plan_path.read_text(encoding='utf-8'))
        if digest(partition_path) != partition_plan['assignments_sha256']:
            raise ValueError('La asignación de grupos fue modificada fuera de la versión congelada')
        if snapshot_fingerprint(records) != partition_plan['input_manifest_fingerprint']:
            raise ValueError('Han cambiado las entradas que sustentan la partición; se requiere una migración documentada')
        assignment_frame = pd.read_csv(partition_path, keep_default_na=False)
        if not assignment_frame.split_group_id.is_unique or set(assignment_frame.split_group_id) != set(frame.split_group_id):
            raise ValueError('Las particiones no cubren exactamente los grupos actuales')
        assignment_lookup = assignment_frame.set_index('split_group_id').to_dict('index')
        for record in records:
            group = assignment_lookup[record['split_group_id']]
            if group['species_code'] != record['species_code']:
                raise ValueError('La especie de grupo no coincide con la partición congelada')
            active = record['use_in_initial_partition'] and not record['exclude_from_primary_training']
            role = group['split_assignment']
            record.update(manifest_schema_version='1.2', split_assignment=role,
                split_assignment_source='exp_design/07_partition_assignments_v1.csv', partition_version=partition_plan['version'],
                partition_seed=partition_plan['seed'], validation_role=group['validation_role'] or None,
                use_in_assigned_partition=active,
                use_for_classifier=active and role in ('C_fit', 'C_val', 'T_real'),
                use_for_lora=active and role == 'G_fit',
                partition_filter_reason='incomplete_secondary_acquisition_reserve' if not record['use_in_initial_partition'] else record['exclusion_reason'] if record['exclude_from_primary_training'] else None)
        frame = pd.DataFrame(records)
    checks = dict(source_paths_complete=set(frame.source_path) == paths,
        image_ids_unique=frame.image_id.is_unique, SHA256_unique=frame.sha256.is_unique,
        expected_eight_confirmed_corrections=int(frame.label_correction_applied.sum()) == 8,
        two_corrected_physical_groups=frame.loc[frame.label_correction_applied, 'split_group_id'].nunique() == 2,
        no_unresolved_initial_sowing_priority=not frame.sowing_review_priority_unresolved.any(),
        excluded_band_present=((frame.filename == 'DSC_0081.JPG') & frame.exclude_from_primary_training).sum() == 1,
        partitions_consistent_with_documented_plan=frame.split_assignment.ne('unassigned').all() if partition_plan else frame.split_assignment.eq('unassigned').all(),
        no_observed_plant_counts_invented=frame.num_plants_observed.isna().all(),
        group_species_consistent=frame.groupby('split_group_id').species_code.nunique().eq(1).all())
    if not all(checks.values()):
        raise ValueError(f'Comprobaciones incumplidas: {checks}')
    # Versionar antes de sustituir cualquier consolidado o anotación de revisión.
    version = out / 'manifest_versions' / run_id
    version.mkdir(parents=True, exist_ok=False)
    backups = []
    for path in [out / f'manifest_{part}.{ext}' for part in ('2025', '2026', 'all') for ext in ('csv', 'json')] + [review_path]:
        if path.exists():
            target = version / ('revision_visual_before.csv' if path == review_path else path.name)
            shutil.copy2(path, target)
            backups.append(dict(source=path.relative_to(root).as_posix(), snapshot=target.relative_to(root).as_posix(), sha256=digest(target)))
    shutil.copy2(corrections_path, version / corrections_path.name)
    write_csv(review_path, updated_reviews)
    exports = []
    for part in ('2025', '2026', 'all'):
        subset = frame if part == 'all' else frame[frame.year == int(part)]
        selected = [r for r in records if part == 'all' or r['year'] == int(part)]
        csv_path, json_path = out / f'manifest_{part}.csv', out / f'manifest_{part}.json'
        write_csv(csv_path, subset)
        write_json(json_path, selected)
        exports.extend([dict(path=p.relative_to(root).as_posix(), sha256=digest(p), rows=len(subset)) for p in (csv_path, json_path)])
    write_csv(out / 'manifest_label_corrections.csv', frame[frame.label_correction_applied])
    write_csv(out / 'manifest_exclusions.csv', frame[frame.exclude_from_primary_training])
    write_csv(out / 'manifest_deferred_acquisitions.csv', frame[~frame.use_in_initial_partition])
    for part in ('2025', '2026', 'all'):
        selected_pool = frame[frame.use_in_initial_partition & (True if part == 'all' else frame.year == int(part))]
        write_csv(out / f'manifest_initial_pool_{part}.csv', selected_pool)
    write_csv(out / 'manifest_sessions.csv', frame.groupby(['year', 'session_id'], as_index=False).agg(
        images=('image_id', 'size'), pots=('split_group_id', 'nunique'), label_corrections=('label_correction_applied', 'sum'),
        excluded_primary=('exclude_from_primary_training', 'sum'), classifier_candidates=('is_classifier_candidate', 'sum'), lora_candidates=('is_lora_candidate', 'sum')))
    write_csv(out / 'manifest_species_counts.csv', frame.groupby(['year', 'species_scientific'], as_index=False).size().rename(columns={'size': 'images'}))
    source_files = [verification_path, review_path, corrections_path, historical_path,
        root / 'exp_design/01_2025.csv', root / 'exp_design/03_2026.csv', root / 'exp_design/02_2025_details.csv', acquisition_policy_path, Path(__file__).resolve()]
    partition_summary = None
    if partition_plan:
        partition_out = out / 'partitions' / partition_plan['version']
        partition_out.mkdir(parents=True, exist_ok=True)
        masks = {role: frame.use_in_assigned_partition & frame.split_assignment.eq(role) for role in ('C_fit', 'C_val', 'G_fit', 'T_real', 'M_aux')}
        masks['C_val_model_selection'] = masks['C_val'] & frame.validation_role.eq('model_selection')
        masks['C_val_calibration'] = masks['C_val'] & frame.validation_role.eq('threshold_calibration')
        partition_summary = []
        for role, mask in masks.items():
            subset = frame[mask]
            write_csv(partition_out / f'{role}.csv', subset)
            write_json(partition_out / f'{role}.json', [r for r, keep in zip(records, mask) if keep])
            partition_summary.append(dict(dataset=role, images=len(subset), pot_groups=int(subset.split_group_id.nunique()),
                species_images=subset.species_code.value_counts().to_dict()))
        write_csv(partition_out / 'excluded_or_deferred.csv', frame[~frame.use_in_assigned_partition])
        write_csv(partition_out / 'groups.csv', assignment_frame)
        write_csv(partition_out / 'counts_by_species.csv', frame[frame.use_in_assigned_partition].groupby(['split_assignment', 'year', 'campana', 'repeticion', 'species_code'], as_index=False).agg(images=('image_id', 'size'), groups=('split_group_id', 'nunique')))
        write_json(partition_out / 'summary.json', dict(version=partition_plan['version'], seed=partition_plan['seed'],
            datasets=partition_summary, inactive_images=int((~frame.use_in_assigned_partition).sum()),
            note='C_val subdatasets are disjoint subsets of C_val; do not sum parent and children.',
            limitations=partition_plan['limitations']))
        source_files += [partition_path, partition_plan_path, root / 'scripts/s09_create_group_partitions.py']
    result = dict(build_id=run_id, started_utc=started.isoformat(), completed_utc=datetime.now(timezone.utc).isoformat(),
        images=len(frame), images_by_year={str(k): int(v) for k, v in frame.year.value_counts().sort_index().items()},
        species_final=frame.species_scientific.value_counts().to_dict(),
        fields=len(frame.columns), sessions=int(frame.session_id.nunique()), pot_groups=int(frame.split_group_id.nunique()),
        corrected_images=int(frame.label_correction_applied.sum()), corrected_groups=2,
        excluded_primary_training=int(frame.exclude_from_primary_training.sum()),
        initial_partition_pool=int(frame.use_in_initial_partition.sum()),
        initial_partition_pool_by_year={str(k): int(v) for k, v in frame[frame.use_in_initial_partition].year.value_counts().sort_index().items()},
        deferred_secondary_images=int((~frame.use_in_initial_partition).sum()),
        classifier_candidates=int(frame.is_classifier_candidate.sum()), lora_candidates=int(frame.is_lora_candidate.sum()),
        auxiliary_maize=int(frame.is_auxiliary.sum()), current_raw_bytes=int(frame.bytes.sum()),
        changed_files_since_verification=int(frame.source_changed_since_verification.sum()),
        checks={k: bool(v) for k, v in checks.items()}, outputs=exports, backups=backups,
        partition_version=partition_plan['version'] if partition_plan else None, partition_datasets=partition_summary,
        sources=[dict(path=p.relative_to(root).as_posix(), sha256=digest(p)) for p in source_files],
        limitations=['Only SC001/SC002 have individual visual confirmation recorded by the investigator.',
            'Unknown geometry, unstructured observed plant counts and plant IDs remain null; masters not created; assigned partitions require eligible-row filters.',
            'Verification image filenames preserve historical design labels, not final species.',
            'Source byte hashes are current; unchanged audited files reuse prior full-decode evidence.'])
    write_json(out / 'manifest_build_summary.json', result)
    write_json(version / 'build_summary.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('outputs', 'backups', 'sources', 'limitations')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    run(args.root.resolve())
