"""Freeze a source-backed preprocessing decision before application to held-out roles."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    output=ROOT/'exp_design/preprocessing_fullframe_v2_frozen.json'
    if output.exists():raise ValueError('Frozen config already exists; never overwrite')
    pilot=ROOT/'data/processed/preprocessing/fullframe_development_v3'
    validation=json.loads((pilot/'validation_fullframe.json').read_text(encoding='utf-8'))
    run=json.loads((pilot/'run.json').read_text(encoding='utf-8'))
    assert validation['passed'] and validation['masters']==91 and not validation['T_real_used_for_selection']
    assert run['script_sha256']==hashlib.sha256((ROOT/'scripts/prepare_fullframe_masters.py').read_bytes()).hexdigest()
    assert not run['include_test'] and run['config']['max_long_edge']==2048
    dependencies=['data/processed/manifest_all.json','exp_design/partition_assignments_v1.csv','scripts/prepare_fullframe_masters.py','scripts/prepare_metric_masters.py','scripts/validate_fullframe_masters.py','data/processed/preprocessing/development_v1/selection.json','data/processed/preprocessing/development_geometry_v3/annotations_development_reviewed.json','data/processed/preprocessing/development_geometry_v3/measurement_review.json','data/processed/preprocessing/strategy_comparison_v3/comparison.json','data/processed/preprocessing/fullframe_development_v3/validation_fullframe.json']
    hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in dependencies}
    config=dict(status='frozen',version='fullframe_v2',frozen_utc=datetime.now(timezone.utc).isoformat(),decision_source='BITACORA_METODOLOGICA.md#M029',authorization='Investigator requested critical comparison and authorized choice of best alternative on 2026-11-12',strategy='full_frame_exact_aspect',max_long_edge=2048,png_compress_level=3,orientation='EXIF_before_coordinates',color='valid_ICC_to_sRGB_else_explicit_assumption',resampling='Lanczos',crop=False,pad=False,homography=False,metric_normalization=False,scale_claim='preserves_apparent_plant_to_pot_proportions; not_common_cm_per_pixel; no_3D_size_certification',metric_references='Development annotations remain exploratory pilot_only; never silently approved',downstream_contract='Load complete rectangle with isotropic scale; no implicit center crop, RandomResizedCrop or independent-axis stretch. Any model canvas/bucket adapter must be explicit and tested before training.',source_hashes=hashes,selected_after_development_only=True,T_real_used_for_selection=False,source_content_reconstruction=False)
    output.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(config,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
