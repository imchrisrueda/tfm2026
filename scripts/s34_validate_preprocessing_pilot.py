"""Verify the saved pilot against authoritative rows and current source bytes."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'data/processed/preprocessing'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = json.loads((ROOT/'data/processed/manifest_all.json').read_text(encoding='utf-8'))
    original = {r['image_id']: r for r in source}
    selected = json.loads((BASE/'development_v1/selection.json').read_text(encoding='utf-8'))
    processed = json.loads((BASE/'pilot_v1/manifest_metric.json').read_text(encoding='utf-8'))
    checks = {}
    checks['selection_only_active_C_fit'] = all(r['split_assignment']=='C_fit' and r['use_in_assigned_partition'] for r in selected)
    checks['selected_source_hashes_unchanged'] = all(sha(ROOT/r['source_path'])==r['sha256']==original[r['image_id']]['sha256'] for r in selected)
    checks['selection_covers_15_sessions_3_species_4_cameras'] = len({r['session_id'] for r in selected})==15 and len({r['species_code'] for r in selected})==3 and len({r['exif_camera_model'] for r in selected})==4
    checks['manifest_coverage_unique'] = len(processed)==len(original)==len({r['image_id'] for r in processed}) and {r['image_id'] for r in processed}==set(original)
    fields = ['split_assignment','split_group_id','species_code','design_species_code','validation_role','use_in_assigned_partition','source_path','sha256']
    checks['partition_labels_paths_hashes_preserved'] = all(str(r[k])==str(original[r['image_id']][k] if original[r['image_id']][k] is not None else '') for r in processed for k in fields)
    checks['T_real_no_master'] = all(r['preprocessing_status']=='held_out_T_real_not_opened' and not r['master_image_path'] for r in processed if r['split_assignment']=='T_real' and r['use_in_assigned_partition']=='True')
    masters = [r for r in processed if r['preprocessing_status']=='pilot_master_created']
    checks['pilot_masters_only_C_fit'] = all(r['split_assignment']=='C_fit' and r['metric_annotation']['measurement_scope']=='pilot_only' for r in masters)
    checks['master_files_hash_size_profile'] = True
    checks['scale_equations_and_real_coverage'] = True
    for r in masters:
        path = ROOT/r['master_image_path']
        with Image.open(path) as im:
            checks['master_files_hash_size_profile'] &= im.size==(1024,1024) and im.mode=='RGB' and bool(im.info.get('icc_profile')) and sha(path)==r['master_sha256']
        x0,y0,x1,y1=r['crop_box_oriented_px']
        checks['scale_equations_and_real_coverage'] &= 0<=x0<x1<=int(r['oriented_width']) and 0<=y0<y1<=int(r['oriented_height']) and abs((x1-x0)-(y1-y0))<1e-6 and abs(r['resize_factor']*r['pot_diameter_px']-r['expected_pot_diameter_output_px'])<1e-6
    grouped = defaultdict(Counter)
    for r in processed:
        if r.get('metric_annotation'):
            grouped[f"{r['year']}|{r['species_code']}|{r['exif_camera_model']}"][r['preprocessing_status']]+=1
    measured = sum(bool(r.get('metric_annotation')) for r in processed)
    report = dict(checks=checks, passed=all(checks.values()), selected=len(selected), measured=measured, created=len(masters), unmeasured_development=len(selected)-measured, pilot_coverage_by_year_species_camera={k:dict(v) for k,v in grouped.items()}, authoritative_manifest_json_sha256=sha(ROOT/'data/processed/manifest_all.json'), partition_assignments_sha256=sha(ROOT/'exp_design/07_partition_assignments_v1.csv'), tests='python -m unittest discover -s scripts -p test_30_prepare_metric_masters.py -v', visual_review='masters_review.jpg inspected by Codex; no independent repeated measurements; no full species/camera/detail approval', final_resolution_frozen=False, preprocessing_frozen=False)
    (BASE/'pilot_v1/validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    assert report['passed']


if __name__=='__main__':
    main()
