"""Independent exhaustive technical audit of frozen full-frame masters.

Recomputes every produced RGB raster from the current original, EXIF orientation,
ICC conversion and uncropped resize. T_real is decoded only after verifying the
frozen-configuration and explicit application gate. No model or visual evaluation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path

from PIL import Image, ImageCms, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ROLES = ('C_fit', 'C_val_model_selection', 'C_val_calibration', 'G_fit', 'T_real', 'M_aux')
ALTERED_RAW_FIELDS = {'master_image_path', 'preprocessing_status', 'common_field_cm',
    'geometry_status', 'geometry_reference_quality', 'pot_center_x_px', 'pot_center_y_px',
    'pot_diameter_px', 'scale_cm_per_px'}


def sha(path):
    with Path(path).open('rb') as stream:
        result = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''): result.update(block)
    return result.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def relative(path):
    path = Path(path).resolve(); path.relative_to(ROOT)
    return path


def role(row):
    if row['split_assignment'] == 'C_val':
        return {'model_selection': 'C_val_model_selection',
                'threshold_calibration': 'C_val_calibration'}[row['validation_role']]
    assert row['split_assignment'] in ROLES
    return row['split_assignment']


def instant(text):
    result = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if result.tzinfo is None: raise ValueError('UTC/offset timestamp required')
    return result


def serialized(value):
    if value is None: return ''
    if isinstance(value, (dict, list)): return json.dumps(value, ensure_ascii=False)
    return str(value)


def expected_size(w, h, cap):
    if cap == 0 or max(w, h) <= cap: return w, h
    divisor = math.gcd(w, h)
    unit_w, unit_h = w // divisor, h // divisor
    multiplier = cap // max(unit_w, unit_h)
    if multiplier < 1: raise ValueError('Cap cannot represent source aspect exactly')
    return unit_w * multiplier, unit_h * multiplier


def reconstruct(source, size):
    # Deliberately independent of the production helper.
    with Image.open(source) as image:
        image.load()
        oriented = ImageOps.exif_transpose(image)
        profile = image.info.get('icc_profile')
        srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB'))
        if profile:
            rgb = ImageCms.profileToProfile(oriented, ImageCms.ImageCmsProfile(io.BytesIO(profile)),
                                           srgb, outputMode='RGB')
            status = 'embedded_ICC_converted_to_sRGB'
        else:
            if oriented.mode not in {'RGB', 'L'}: raise ValueError('Unsupported unprofiled color mode')
            rgb = oriented.convert('RGB')
            status = 'no_ICC_assumed_sRGB_not_colorimetrically_validated'
    if rgb.size != size: rgb = rgb.resize(size, Image.Resampling.LANCZOS)
    return rgb, status


def validate(args):
    base = relative(args.output)
    config = read(args.config)
    run, fingerprint = read(base/'run.json'), read(base/'fingerprint.json')
    originals = read(args.manifest)
    rows = read(base/'manifest_fullframe.json')
    failures, checks = [], Counter()

    def check(name, condition, detail=''):
        checks[name] += 1
        if not condition: failures.append({'check': name, 'detail': detail})

    original = {row['image_id']: row for row in originals}
    output = {row['image_id']: row for row in rows}
    check('complete_unique_manifest', len(original) == len(originals) == len(rows) == len(output)
          and set(original) == set(output))
    if failures: raise ValueError('Manifest coverage/uniqueness failed before source processing')
    check('config_semantic_snapshot', config == read(base/'config.json') == run['config'])
    check('input_hashes', sha(args.manifest) == run['manifest_sha256'] == fingerprint['manifest_sha256']
          and sha(args.config) == run['config_sha256'] == fingerprint['config_sha256'])
    for key, value in fingerprint.items(): check('fingerprint_preserved', run.get(key) == value, key)
    check('production_code_hashes', sha(ROOT/'scripts/prepare_fullframe_masters.py') == run['script_sha256']
          and sha(ROOT/'scripts/prepare_metric_masters.py') == run['color_helper_sha256'])
    check('fullframe_strategy', config.get('strategy') == 'full_frame_exact_aspect')
    if args.annotations:
        check('annotations_hash', sha(args.annotations) == run['annotations_sha256'])
        supplied_annotations = {r['image_id']: r for r in read(args.annotations)}
    else:
        check('annotations_none', run.get('annotations_sha256') is None)
        supplied_annotations = {}
    selected = None
    if args.selection:
        check('selection_hash', sha(args.selection) == run['selection_sha256'])
        selected = {r['image_id'] for r in read(args.selection)}
    else: check('selection_none', run.get('selection_sha256') is None)
    includes_test = run.get('include_test') is True
    test_produced = any(r.get('master_image_path') for r in rows if r['split_assignment'] == 'T_real')
    check('explicit_test_gate', not test_produced or (includes_test and run['mode'] == 'apply'
          and run.get('T_real_processing_authorized') is True and config.get('status') == 'frozen'))
    if run['mode'] == 'apply':
        check('frozen_before_application', config.get('status') == 'frozen'
              and instant(config['frozen_utc']) <= instant(run['started_utc']) <= instant(run['created_utc']))
        check('execution_start_and_freeze_recorded', read(base/'execution_start.json')['started_utc'] == run['started_utc']
              and run.get('frozen_utc') == config['frozen_utc'])
    # Fail closed before decoding any T_real if provenance/gates have failed.
    if failures:
        raise ValueError('Run provenance/configuration failed before decoding: ' + json.dumps(failures))

    expected_paths, expected_roles = set(), defaultdict(list)
    groups_by_role, counts = defaultdict(set), Counter()
    geometry_fields = ALTERED_RAW_FIELDS - {'master_image_path', 'preprocessing_status', 'common_field_cm'}
    for index, row in enumerate(rows, 1):
        if index % 100 == 0: print(f'Validating {index}/{len(rows)} records', flush=True)
        image_id = row['image_id']; src = original[image_id]
        source_path = relative(ROOT/src['source_path'])
        check('original_bytes_unchanged', sha(source_path) == src['sha256'], image_id)
        check('raw_keys_and_values_preserved', all(k in row and row[k] == value
              for k, value in src.items() if k not in ALTERED_RAW_FIELDS), image_id)
        check('config_reference_per_row', row.get('fullframe_config_sha256') == run['config_sha256'], image_id)
        check('no_claim_of_metric_normalization', row.get('scale_normalization_status') == 'not_metric_normalized'
              and row.get('common_field_cm') is None, image_id)
        eligible = src['use_in_assigned_partition'] is True
        status = ('inactive_partition_image' if not eligible else
                  'held_out_T_real_not_opened' if src['split_assignment'] == 'T_real' and not includes_test else
                  'not_development_role' if run['mode'] == 'pilot' and src['split_assignment'] != 'C_fit' else
                  'not_in_selected_lot' if selected is not None and image_id not in selected else
                  'fullframe_master_created')
        check('expected_processing_state', row.get('preprocessing_status') == status, image_id)
        counts[row['preprocessing_status']] += 1
        created = status == 'fullframe_master_created'
        check('usage_flags_follow_function', row.get('fullframe_use_in_assigned_partition') is created
              and row.get('fullframe_use_for_classifier_fit') is (created and src['split_assignment'] == 'C_fit')
              and row.get('fullframe_use_for_lora_fit') is (created and src['split_assignment'] == 'G_fit'), image_id)
        if not created:
            check('inactive_or_heldout_has_no_master', not row.get('master_image_path') and not row.get('master_sha256'), image_id)
            check('unprocessed_geometry_preserved', all(row.get(k) == src.get(k) for k in geometry_fields), image_id)
            continue
        assigned = role(src)
        expected_roles[assigned].append(row); groups_by_role[assigned].add(src['split_group_id'])
        path = relative(ROOT/row['master_image_path']); expected_paths.add(path)
        check('master_role_directory', path.parent == base/'masters'/assigned, image_id)
        check('master_sha256', path.exists() and sha(path) == row['master_sha256'], image_id)
        w, h = src['oriented_width'], src['oriented_height']
        dimensions = expected_size(w, h, config['max_long_edge'])
        scale = dimensions[0] / w
        check('exact_aspect_and_isotropic_scale', dimensions[0]*h == dimensions[1]*w
              and row['master_width'] == dimensions[0] and row['master_height'] == dimensions[1]
              and row['fullframe_resize_factor'] == scale and dimensions[0] <= w and dimensions[1] <= h, image_id)
        check('uncropped_unpadded_full_extent', row.get('fullframe_source_box_oriented_px') == [0,0,w,h]
              and row.get('retained_source_area_fraction') == 1.0 and row.get('aspect_ratio_exact') is True
              and all(row.get(k) is False for k in ('cropping_applied','padding_applied','homography_applied')), image_id)
        with Image.open(path) as image:
            image.load()
            check('master_decode_RGB_PNG_dimensions', image.mode == 'RGB' and image.format == 'PNG'
                  and image.size == dimensions and image.getexif().get(274) in (None, 1), image_id)
            profile = image.info.get('icc_profile')
            try:
                profile_name = ImageCms.getProfileName(ImageCms.ImageCmsProfile(io.BytesIO(profile)))
                profile_ok = 'srgb' in profile_name.lower()
            except (TypeError, OSError, ImageCms.PyCMSError): profile_ok = False
            check('master_sRGB_profile', profile_ok, image_id)
            expected_rgb, color_status = reconstruct(source_path, dimensions)
            check('all_pixels_equal_uncropped_reconstruction', image.tobytes() == expected_rgb.tobytes(), image_id)
            check('color_provenance', row.get('color_processing') == color_status, image_id)
        annotation = supplied_annotations.get(image_id)
        check('annotation_exact_provenance', row.get('metric_annotation') == annotation, image_id)
        measured = (annotation is not None and annotation.get('review_status') == 'accepted'
                    and annotation.get('reference_quality') == 'usable'
                    and annotation.get('measurement_scope') in {'reviewed', 'investigator_review',
                        'codex_visual_review', 'visual_reviewed', 'development_reviewed'})
        if measured:
            check('geometry_review_provenance', annotation['source_sha256'] == src['sha256']
                  and annotation.get('coordinate_space') == 'exif_oriented'
                  and bool(annotation.get('reviewer')) and bool(annotation.get('review_date')), image_id)
            cx, cy, d = (float(annotation[k]) for k in ('pot_center_x_px','pot_center_y_px','pot_diameter_px'))
            nominal = src['pot_diameter_exterior_cm']; pxcm = d / nominal
            expected = {'pot_center_x_px':cx, 'pot_center_y_px':cy, 'pot_diameter_px':d,
                'scale_cm_per_px':1/pxcm, 'output_px_per_cm':pxcm*scale,
                'fullframe_field_width_cm':w/pxcm, 'fullframe_field_height_cm':h/pxcm,
                'pot_center_output_x_px':cx*scale, 'pot_center_output_y_px':cy*scale,
                'pot_diameter_output_px':d*scale}
            check('measured_geometry_propagated', all(math.isclose(row.get(k, float('nan')), value,
                  rel_tol=1e-12, abs_tol=1e-9) for k,value in expected.items())
                  and row.get('metric_reference_status') == 'reviewed_apparent_outer_rim_scale', image_id)
        else:
            check('unmeasured_geometry_not_invented', all(row.get(k) == src.get(k) for k in geometry_fields)
                  and all(row.get(k) is None for k in ('output_px_per_cm', 'fullframe_field_width_cm',
                    'fullframe_field_height_cm','pot_center_output_x_px','pot_center_output_y_px','pot_diameter_output_px')), image_id)
    for name in ROLES:
        actual = read(base/'partitions'/f'{name}.json')
        check('role_list_matches_sidecar_exactly', actual == expected_roles[name], name)
        reference_ids = {r['image_id'] for r in read(ROOT/'data/processed/partitions/v1'/f'{name}.json')}
        expected_ids = {r['image_id'] for r in expected_roles[name]}
        check('role_list_respects_frozen_partition', expected_ids <= reference_ids, name)
        for other in ROLES:
            if name < other: check('groups_disjoint_by_function', not groups_by_role[name] & groups_by_role[other], f'{name}/{other}')
        csv_path = base/'partitions'/f'{name}.csv'
        if expected_roles[name]:
            with csv_path.open(encoding='utf-8-sig', newline='') as stream: csv_rows = list(csv.DictReader(stream))
            fields = set().union(*(set(row) for row in expected_roles[name]))
            check('role_csv_matches_json', len(csv_rows) == len(expected_roles[name]) and all(
                  all(c.get(k) == serialized(r.get(k)) for k in fields) for c,r in zip(csv_rows, expected_roles[name])), name)
    with (base/'manifest_fullframe.csv').open(encoding='utf-8-sig', newline='') as stream:
        csv_rows = list(csv.DictReader(stream))
    fields = set().union(*(set(row) for row in rows))
    check('sidecar_csv_matches_json', len(csv_rows) == len(rows) and all(
          all(c.get(k) == serialized(r.get(k)) for k in fields) for c,r in zip(csv_rows, rows)))
    check('exact_master_file_set', {path.resolve() for path in (base/'masters').rglob('*.png')} == expected_paths)
    check('no_partial_outputs', not list(base.rglob('*.partial')))
    check('reported_counts', dict(counts) == run['counts'] and not run['errors'])
    check('reported_role_counts', {k:len(v) for k,v in expected_roles.items() if v} == run['active_master_counts_by_partition'])
    report = dict(created_utc=datetime.now(timezone.utc).isoformat(), passed=not failures,
                  checks=dict(checks), check_instances=sum(checks.values()), failures=failures,
                  rows=len(rows), masters=len(expected_paths), counts=dict(counts),
                  master_counts_by_role={k:len(expected_roles[k]) for k in ROLES},
                  all_original_hashes_verified=not any(f['check'] == 'original_bytes_unchanged' for f in failures),
                  all_masters_decoded_and_reconstructed=not any(f['check'] in {
                      'master_decode_RGB_PNG_dimensions','all_pixels_equal_uncropped_reconstruction'} for f in failures),
                  T_real_technical_validation=test_produced, T_real_used_for_selection=False,
                  no_training_or_model_metrics=True, no_visual_or_botanical_validation=True,
                  authoritative_manifest_sha256=sha(args.manifest), config_sha256=sha(args.config),
                  partition_assignments_sha256=sha(ROOT/'exp_design/partition_assignments_v1.csv'),
                  validator_sha256=sha(__file__))
    (base/'validation_fullframe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if failures: raise SystemExit(1)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, default=ROOT/'data/processed/manifest_all.json')
    parser.add_argument('--annotations', type=Path)
    parser.add_argument('--selection', type=Path)
    validate(parser.parse_args())


if __name__ == '__main__': main()
