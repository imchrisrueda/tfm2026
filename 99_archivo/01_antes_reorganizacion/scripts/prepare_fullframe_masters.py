"""Create full-frame sRGB masters with exact aspect ratio, without metric normalization.

This is an alternative processor. It never overwrites authoritative manifests,
changes partition assignments, crops, pads, or validates unreviewed geometry.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform

import PIL
from PIL import Image, ImageCms

from prepare_metric_masters import digest, oriented_srgb, read_records, write_csv, yes

ROOT = Path(__file__).resolve().parents[1]


def exact_size(width, height, max_long_edge):
    """Integer multiple of the reduced aspect ratio, with no upsampling.

    max_long_edge=0 retains native dimensions. A cap below the reduced ratio
    cannot represent that aspect ratio exactly and is rejected, not rounded.
    """
    if not isinstance(max_long_edge, int) or isinstance(max_long_edge, bool) or max_long_edge < 0:
        raise ValueError('max_long_edge must be a non-negative integer')
    if width <= 0 or height <= 0:
        raise ValueError('Invalid source dimensions')
    if max_long_edge == 0 or max(width, height) <= max_long_edge:
        return width, height
    divisor = math.gcd(width, height)
    unit_w, unit_h = width // divisor, height // divisor
    multiple = max_long_edge // max(unit_w, unit_h)
    if multiple < 1:
        raise ValueError('resolution_cap_cannot_preserve_exact_aspect_ratio')
    return unit_w * multiple, unit_h * multiple


def partition_directory(row):
    if row['split_assignment'] == 'C_val':
        roles = {'model_selection': 'C_val_model_selection', 'threshold_calibration': 'C_val_calibration'}
        if row.get('validation_role') not in roles:
            raise ValueError('Unknown validation_role')
        return roles[row['validation_role']]
    if row['split_assignment'] not in {'C_fit', 'G_fit', 'T_real', 'M_aux'}:
        raise ValueError('Unknown split_assignment')
    return row['split_assignment']


def geometry_metadata(row, annotation, scale):
    """Propagate reviewed geometry only; full-frame content never needs a circle."""
    result = {'metric_reference_status': 'not_measured', 'metric_annotation': None,
              'output_px_per_cm': None, 'fullframe_field_width_cm': None,
              'fullframe_field_height_cm': None, 'pot_center_output_x_px': None,
              'pot_center_output_y_px': None, 'pot_diameter_output_px': None}
    if annotation is None:
        return result
    if annotation.get('source_sha256') != row['sha256']:
        raise ValueError('annotation_source_hash_mismatch')
    result['metric_annotation'] = annotation
    result['metric_reference_status'] = 'annotation_not_approved_for_measurement'
    approved_scopes = {'reviewed', 'investigator_review', 'codex_visual_review', 'visual_reviewed', 'development_reviewed'}
    if (annotation.get('review_status') != 'accepted' or annotation.get('reference_quality') != 'usable'
            or annotation.get('measurement_scope') not in approved_scopes):
        return result
    if annotation.get('coordinate_space') != 'exif_oriented' or not annotation.get('reviewer') or not annotation.get('review_date'):
        raise ValueError('Incomplete reviewed geometry provenance')
    cx, cy, diameter = (float(annotation[key]) for key in ('pot_center_x_px', 'pot_center_y_px', 'pot_diameter_px'))
    if not all(math.isfinite(value) for value in (cx, cy, diameter)) or diameter <= 0:
        raise ValueError('Invalid reviewed geometry')
    w, h = int(row['oriented_width']), int(row['oriented_height'])
    if not 0 <= cx <= w or not 0 <= cy <= h:
        raise ValueError('Reviewed center outside source')
    nominal = float(row['pot_diameter_exterior_cm'])
    if not math.isfinite(nominal) or nominal <= 0:
        raise ValueError('Invalid nominal pot diameter')
    if annotation.get('pot_diameter_nominal_cm') is not None and not math.isclose(float(annotation['pot_diameter_nominal_cm']), nominal):
        raise ValueError('Nominal diameter mismatch')
    px_cm = diameter / nominal
    result.update({'metric_reference_status': 'reviewed_apparent_outer_rim_scale',
                   'geometry_status': 'reviewed_apparent_rim_scale',
                   'geometry_reference_quality': 'usable',
                   'pot_center_x_px': cx, 'pot_center_y_px': cy, 'pot_diameter_px': diameter,
                   'scale_cm_per_px': 1 / px_cm, 'output_px_per_cm': px_cm * scale,
                   'fullframe_field_width_cm': w / px_cm, 'fullframe_field_height_cm': h / px_cm,
                   'pot_center_output_x_px': cx * scale, 'pot_center_output_y_px': cy * scale,
                   'pot_diameter_output_px': diameter * scale})
    return result


def make_master(row, annotation, config, output, root):
    result = dict(row)
    result.update({'master_image_path': '', 'master_sha256': '', 'preprocessing_status': 'fullframe_processing_error',
                   'preprocessing_strategy': 'full_frame_exact_aspect',
                   'scale_normalization_status': 'not_metric_normalized', 'common_field_cm': None,
                   'fullframe_use_in_assigned_partition': False, 'fullframe_use_for_classifier_fit': False,
                   'fullframe_use_for_lora_fit': False})
    try:
        source = (root / row['source_path']).resolve()
        source.relative_to(root.resolve())
        if digest(source) != row['sha256']:
            raise ValueError('source_hash_mismatch')
        with Image.open(source) as im:
            rgb, color, srgb_profile = oriented_srgb(im)
        width, height = rgb.size
        if (width, height) != (int(row['oriented_width']), int(row['oriented_height'])):
            raise ValueError('oriented_dimensions_mismatch')
        target_size = exact_size(width, height, config['max_long_edge'])
        scale = target_size[0] / width
        if target_size[0] * height != target_size[1] * width:
            raise ValueError('Internal aspect ratio mismatch')
        result.update(geometry_metadata(row, annotation, scale))
        if rgb.size != target_size:
            rgb = rgb.resize(target_size, Image.Resampling.LANCZOS)
        directory = output / 'masters' / partition_directory(row)
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (hashlib.sha256(row['image_id'].encode()).hexdigest()[:24] + '.png')
        temporary = target.with_suffix('.partial')
        rgb.save(temporary, format='PNG', compress_level=config.get('png_compress_level', 3), icc_profile=srgb_profile)
        temporary.replace(target)
        result.update({'master_image_path': target.relative_to(root).as_posix(), 'master_sha256': digest(target),
                       'preprocessing_status': 'fullframe_master_created', 'color_processing': color,
                       'master_width': target_size[0], 'master_height': target_size[1],
                       'fullframe_source_box_oriented_px': [0, 0, width, height],
                       'fullframe_resize_factor': scale, 'retained_source_area_fraction': 1.0,
                       'aspect_ratio_exact': True, 'padding_applied': False, 'cropping_applied': False,
                       'homography_applied': False, 'fullframe_use_in_assigned_partition': True,
                       'fullframe_use_for_classifier_fit': row['split_assignment'] == 'C_fit',
                       'fullframe_use_for_lora_fit': row['split_assignment'] == 'G_fit'})
    except (ValueError, TypeError, KeyError, OSError, ImageCms.PyCMSError) as error:
        result['preprocessing_reason'] = str(error)
    return result


def verify_resumed(row, original, root):
    if row['sha256'] != original['sha256'] or row['split_assignment'] != original['split_assignment']:
        raise ValueError('Resume identity/partition mismatch')
    source = (root / original['source_path']).resolve()
    source.relative_to(root.resolve())
    if digest(source) != original['sha256']:
        raise ValueError('Source changed during resume')
    if row.get('preprocessing_status') != 'fullframe_master_created':
        return False
    target = (root / row['master_image_path']).resolve()
    target.relative_to(root.resolve())
    if not target.exists() or digest(target) != row['master_sha256']:
        raise ValueError('Master changed during resume')
    with Image.open(target) as im:
        im.load()
        if im.size != (row['master_width'], row['master_height']) or im.mode != 'RGB' or not im.info.get('icc_profile'):
            raise ValueError('Master metadata changed during resume')
    return True


def run_pipeline(args, root=ROOT):
    started_utc = datetime.now(timezone.utc).isoformat()
    root = Path(root).resolve()
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    if config.get('strategy') != 'full_frame_exact_aspect':
        raise ValueError('strategy must be full_frame_exact_aspect')
    exact_size(1, 1, config['max_long_edge'])
    compression = config.get('png_compress_level', 3)
    if isinstance(compression, bool) or not isinstance(compression, int) or not 0 <= compression <= 9:
        raise ValueError('png_compress_level must be an integer from 0 to 9')
    if args.mode == 'apply' and config.get('status') != 'frozen':
        raise ValueError('apply requires frozen config')
    if args.mode == 'apply':
        frozen = datetime.fromisoformat(config.get('frozen_utc', ''))
        if frozen.tzinfo is None or frozen > datetime.fromisoformat(started_utc):
            raise ValueError('apply requires a prior timezone-aware frozen_utc')
    if args.include_test and (args.mode != 'apply' or config.get('status') != 'frozen'):
        raise ValueError('T_real requires explicit frozen apply')
    if not 1 <= args.workers <= 8:
        raise ValueError('workers must be between 1 and 8')
    manifest = read_records(args.manifest)
    by_id = {r['image_id']: r for r in manifest}
    if len(by_id) != len(manifest):
        raise ValueError('Duplicate manifest image_id')
    selection = read_records(args.selection) if args.selection else None
    selected = {r['image_id'] for r in selection} if selection else None
    if selection is not None:
        if len(selected) != len(selection) or not selected <= set(by_id):
            raise ValueError('Invalid selection image IDs')
        if any(r.get('sha256') != by_id[r['image_id']]['sha256'] for r in selection):
            raise ValueError('Selection/source hash mismatch')
    annotation_rows = read_records(args.annotations) if args.annotations else []
    annotations = {r['image_id']: r for r in annotation_rows}
    if len(annotations) != len(annotation_rows) or not set(annotations) <= set(by_id):
        raise ValueError('Invalid annotation image IDs')
    fingerprint = {'manifest_sha256': digest(args.manifest), 'config_sha256': digest(args.config),
                   'selection_sha256': digest(args.selection) if args.selection else None,
                   'annotations_sha256': digest(args.annotations) if args.annotations else None,
                   'script_sha256': digest(__file__),
                   'color_helper_sha256': digest(Path(__file__).with_name('prepare_metric_masters.py')),
                   'mode': args.mode, 'include_test': args.include_test,
                   'python': platform.python_version(), 'pillow': PIL.__version__}
    output = args.output.resolve()
    output.relative_to(root)
    if args.resume:
        saved_fingerprint = json.loads((output / 'fingerprint.json').read_text(encoding='utf-8'))
        if fingerprint != saved_fingerprint:
            raise ValueError('Resume fingerprint mismatch')
        first_started_utc = json.loads((output / 'execution_start.json').read_text(encoding='utf-8'))['started_utc']
        if args.mode == 'apply' and datetime.fromisoformat(config['frozen_utc']) > datetime.fromisoformat(first_started_utc):
            raise ValueError('Config was not frozen before the first run start')
    else:
        output.mkdir(parents=True, exist_ok=False)
        first_started_utc = started_utc
        (output / 'execution_start.json').write_text(json.dumps({'started_utc': first_started_utc}), encoding='utf-8')
        (output / 'fingerprint.json').write_text(json.dumps(fingerprint, indent=2), encoding='utf-8')
        (output / 'config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    checkpoint = output / 'completed.jsonl'
    previous = {}
    if args.resume and checkpoint.exists():
        for line in checkpoint.read_text(encoding='utf-8').splitlines():
            # A torn final line is not trusted; it can be recomputed from source.
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            previous[row['image_id']] = row
    output_rows, pending = {}, []
    for original in manifest:
        row = dict(original)
        row.update({'master_image_path': '', 'master_sha256': '',
                    'preprocessing_strategy': 'full_frame_exact_aspect',
                    'scale_normalization_status': 'not_metric_normalized', 'common_field_cm': None,
                    'fullframe_config_sha256': fingerprint['config_sha256'],
                    'fullframe_use_in_assigned_partition': False,
                    'fullframe_use_for_classifier_fit': False, 'fullframe_use_for_lora_fit': False})
        if not yes(row['use_in_assigned_partition']):
            row['preprocessing_status'] = 'inactive_partition_image'
        elif row['split_assignment'] == 'T_real' and not args.include_test:
            row['preprocessing_status'] = 'held_out_T_real_not_opened'
        elif args.mode == 'pilot' and row['split_assignment'] != 'C_fit':
            row['preprocessing_status'] = 'not_development_role'
        elif selected is not None and row['image_id'] not in selected:
            row['preprocessing_status'] = 'not_in_selected_lot'
        else:
            old = previous.get(row['image_id'])
            if old and verify_resumed(old, row, root):
                output_rows[row['image_id']] = old
            else:
                pending.append(row)
            continue
        output_rows[row['image_id']] = row
    with checkpoint.open('a', encoding='utf-8', newline='\n') as stream:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(make_master, row, annotations.get(row['image_id']), config, output, root): row['image_id'] for row in pending}
            for index, future in enumerate(as_completed(futures), 1):
                row = future.result()
                output_rows[row['image_id']] = row
                stream.write(json.dumps(row, ensure_ascii=False) + '\n')
                stream.flush()
                if index % 50 == 0 or index == len(pending):
                    print(f'Processed {index}/{len(pending)}; {row["image_id"]}', flush=True)
    rows = [output_rows[row['image_id']] for row in manifest]
    (output / 'manifest_fullframe.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    write_csv(output / 'manifest_fullframe.csv', rows)
    active_rows = [row for row in rows if row['fullframe_use_in_assigned_partition']]
    export_dir = output / 'partitions'
    export_dir.mkdir(exist_ok=True)
    for name in ['C_fit', 'C_val_model_selection', 'C_val_calibration', 'G_fit', 'T_real', 'M_aux']:
        assigned = [r for r in active_rows if partition_directory(r) == name]
        (export_dir / f'{name}.json').write_text(json.dumps(assigned, ensure_ascii=False, indent=2), encoding='utf-8')
        if assigned:
            write_csv(export_dir / f'{name}.csv', assigned)
    completed_utc = datetime.now(timezone.utc).isoformat()
    report = dict(fingerprint, config=config, started_utc=first_started_utc, latest_invocation_started_utc=started_utc,
                  completed_utc=completed_utc, created_utc=completed_utc, frozen_utc=config.get('frozen_utc'),
                  total_rows=len(rows), selected_count=len(selected) if selected is not None else None,
                  counts=dict(Counter(r['preprocessing_status'] for r in rows)),
                  active_master_counts_by_partition=dict(Counter(partition_directory(r) for r in active_rows)),
                  color_counts=dict(Counter(r['color_processing'] for r in active_rows)),
                  reviewed_reference_count=sum(r.get('metric_reference_status') == 'reviewed_apparent_outer_rim_scale' for r in rows),
                  output_dimensions=dict(Counter(f'{r["master_width"]}x{r["master_height"]}' for r in active_rows)),
                  errors=[{'image_id': r['image_id'], 'reason': r.get('preprocessing_reason')} for r in rows if r['preprocessing_status']=='fullframe_processing_error'],
                  T_real_processing_authorized=args.include_test, partition_assignments_modified=False,
                  scale_scope='apparent_proportions_preserved_no_common_cm_per_pixel',
                  source_field_coverage='all_original_pixels_no_crop_or_padding', workers=args.workers,
                  future_loader_requirement='preserve_full_frame_no_implicit_center_crop_or_RandomResizedCrop')
    (output / 'run.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT/'data/processed/manifest_all.json')
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=['pilot', 'apply'], default='pilot')
    parser.add_argument('--selection', type=Path)
    parser.add_argument('--annotations', type=Path)
    parser.add_argument('--include-test', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    report = run_pipeline(args)
    if report['errors']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
