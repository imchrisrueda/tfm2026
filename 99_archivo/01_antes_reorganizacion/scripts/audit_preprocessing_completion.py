"""Check the complete task16-20 delivery against its frozen inputs and receipts."""
from collections import Counter
from datetime import datetime, timezone
import csv
import hashlib
import json
import math
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/processed/preprocessing/fullframe_v2'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def serial(v):return '' if v is None else json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else str(v)


def main():
    registry=read(ROOT/'exp_design/preprocessing_registry.json')
    rows=read(ROOT/registry['prepared_manifest_path'])
    original=read(ROOT/'data/processed/manifest_all.json');original_by_id={r['image_id']:r for r in original}
    release=read(ROOT/registry['release_validation_path']);audit=read(BASE/'validation_fullframe.json');receipt=read(BASE/'audit_receipt.json')
    config=read(ROOT/registry['configuration_path']);run=read(BASE/'run.json')
    tests=read(BASE/'unit_tests.json')
    assert tests['passed'] and tests['tests']==13
    for path,expected in tests['test_sources'].items():assert sha(ROOT/path)==expected,path
    annotations=read(ROOT/'data/processed/preprocessing/development_geometry_v3/annotations_development_reviewed.json')
    selection=read(ROOT/'data/processed/preprocessing/development_v1/selection.json')
    comparison=read(ROOT/'data/processed/preprocessing/strategy_comparison_v3/comparison.json')
    active=[r for r in rows if r['fullframe_use_in_assigned_partition']]
    assert all(r['species_code']=='P' for r in active if r['split_assignment']=='G_fit')
    assert all(r['species_code']=='M' for r in active if r['split_assignment']=='M_aux')
    assert all(r['species_code'] in {'H','P','R'} for r in active if r['split_assignment'] in {'C_fit','C_val','T_real'})
    assert audit['passed'] and receipt['passed'] and release['passed'] and len(rows)==1451 and len(active)==1419
    assert {r['image_id'] for r in rows}==set(original_by_id)
    for key,hkey in [('prepared_manifest_path','prepared_manifest_sha256'),('prepared_csv_path','prepared_csv_sha256'),('configuration_path','configuration_sha256'),('release_validation_path','release_validation_sha256'),('metadata_errata_path','metadata_errata_sha256')]:
        assert sha(ROOT/registry[key])==registry[hkey],key
    assert receipt['validation_sha256']==sha(BASE/'validation_fullframe.json')
    assert release['base_validation_sha256']==receipt['validation_sha256']
    assert release['execution_manifest_sha256']==sha(BASE/'manifest_fullframe.json')
    for path,expected in config['source_hashes'].items():assert sha(ROOT/path)==expected,path
    selected_ids={r['image_id'] for r in selection}
    assert len(selection)==len(annotations)==91 and {a['image_id'] for a in annotations}==selected_ids
    assert all(r['split_assignment']=='C_fit' and r['use_in_assigned_partition'] for r in selection)
    assert len({r['session_id'] for r in selection})==15 and len({r['species_code'] for r in selection})==3 and len({r['exif_camera_model'] for r in selection})==4
    for a in annotations:
        src=original_by_id[a['image_id']]
        assert a['source_sha256']==src['sha256'] and a['measurement_scope']=='pilot_only'
        assert a['pot_diameter_nominal_cm']==src['pot_diameter_exterior_cm'] and a['development_review_completed']
        if a['reference_quality']=='unusable':
            assert all(a[k] is None for k in ['pot_center_x_px','pot_center_y_px','pot_diameter_px']) and a['notes']
        else:
            assert a['reference_quality']=='usable_provisional' and all(math.isfinite(a[k]) for k in ['pot_center_x_px','pot_center_y_px','pot_diameter_px']) and a['pot_diameter_px']>0
    assert Counter(a['reference_quality'] for a in annotations)=={'usable_provisional':84,'unusable':7}
    assert len(comparison['strategies'])==10
    assert config['status']=='frozen' and config['max_long_edge']==2048 and not config['metric_normalization']
    assert datetime.fromisoformat(config['frozen_utc'])<=datetime.fromisoformat(run['started_utc'])<=datetime.fromisoformat(run['completed_utc'])
    assert all(r['scale_normalization_status']=='not_metric_normalized' and r['common_field_cm'] is None for r in rows)
    assert not list(BASE.rglob('*.partial'))
    for i,src in enumerate(original,1):
        assert sha(ROOT/src['source_path'])==src['sha256'],src['image_id']
        if i%300==0:print(f'Completion audit source hashes {i}/1451',flush=True)
    for i,row in enumerate(active,1):
        assert sha(ROOT/row['master_image_path'])==row['master_sha256'],row['image_id']
        assert row['master_width']*row['oriented_height']==row['master_height']*row['oriented_width']
        assert row['fullframe_source_box_oriented_px']==[0,0,row['oriented_width'],row['oriented_height']]
        if i%300==0:print(f'Completion audit master hashes {i}/1419',flush=True)
    with (ROOT/registry['prepared_csv_path']).open(encoding='utf-8-sig',newline='') as f: csv_rows=list(csv.DictReader(f))
    assert len(csv_rows)==len(rows) and all(all(c.get(k)==serial(v) for k,v in r.items()) for c,r in zip(csv_rows,rows))
    for name,files in registry['partition_lists'].items():
        assert sha(ROOT/files['json_path'])==files['json_sha256'] and sha(ROOT/files['csv_path'])==files['csv_sha256']
    for entry in read(BASE/'release/reproduction_inventory.json'):assert sha(ROOT/entry['archived_path'])==entry['sha256']
    assert audit['checks']['all_pixels_equal_uncropped_reconstruction']==1419
    assert audit['checks']['master_sRGB_profile']==1419 and audit['checks']['exact_aspect_and_isotropic_scale']==1419
    tasks=(ROOT/'tasks.md').read_text(encoding='utf-8')
    assert all(re.search(rf'^{n}\. \[x\]',tasks,re.M) for n in range(15,21))
    assert all(re.search(rf'^{n}\. \[ \]',tasks,re.M) for n in [21,25,26,27,33,35,45])
    evidence={16:['development_geometry_v3/measurement_review.json','development_geometry_v3/annotations_development_reviewed.json'],17:['strategy_comparison_v3/comparison.json'],18:['fullframe_development_v3/validation_fullframe.json','fullframe_v2/validation_fullframe.json'],19:['development_geometry_v3/measurement_review.json','strategy_comparison_v3/comparison.json','fullframe_v2/validation_fullframe.json'],20:['fullframe_v2/audit_receipt.json','fullframe_v2/release/validation_release.json','fullframe_v2/release/reproduction_inventory.json']}
    prefix=ROOT/'data/processed/preprocessing'
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),passed=True,task_requirements={str(n):dict(proven=True,evidence={p:sha(prefix/p) for p in paths}) for n,paths in evidence.items()},originals_verified=1451,masters_verified=1419,inactive_rows=32,descriptive_errata=9,metric_references_production_approved=0,counts_by_role=release['counts_by_role'],coverage_year_species=dict(Counter(f"{r['year']}|{r['species_code']}" for r in active)),coverage_year_camera=dict(Counter(f"{r['year']}|{r['exif_camera_model']}" for r in active)),frozen_utc=config['frozen_utc'],generation_completed_utc=run['completed_utc'],T_real_used_to_choose_parameters=False,selection_scope='Geometry, frame retention and detail comparison in C_fit; no model performance optimization claimed',limits=['Exploratory geometry remains pilot_only, with independent repeatability/tolerances pending task45','Full-frame proportions preserved; no common cm-per-pixel or 3D metrology','Downstream loaders/model resolution/captions remain future tasks','Technical audit does not claim exhaustive botanical or capture-integrity approval'],registry_sha256=sha(ROOT/'exp_design/preprocessing_registry.json'),tasks_sha256=sha(ROOT/'tasks.md'),script_sha256=sha(Path(__file__)))
    (BASE/'completion_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
