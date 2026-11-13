"""Independent review checks. Synthetic fixtures only; never run evaluation inference.

Does not edit the submitted implementation or published benchmark outputs.
"""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/segmentation_benchmark'))
from s02_common import read_json, write_json, digest, verify_protected_inputs
from s03_inventory_and_sample import build_inventory_and_samples
from s08_validate_run import create_freeze
from s06_run_methods import verify_freeze_for_evaluation, associate_sam3_instances
from s01_annotation_io import save_mask_png
from s07_score import score_split, compute_support_metrics, stratified_paired_bootstrap
import numpy as np


def main():
    result = {'scope': 'Review: metadata plus temporary synthetic fixtures; no SAM, no evaluation inference'}
    protected = verify_protected_inputs()
    result['protected_inputs_verified'] = True
    bundle = build_inventory_and_samples()
    base = ROOT / 'data/processed/preprocessing/segmentation_benchmark_v1'
    result['sample_regeneration_matches'] = {
        role: read_json(base / f'samples/{role}.json') == bundle[key]
        for role, key in [('tuning','tuning_rows'), ('evaluation','evaluation_rows'), ('stress','stress_rows')]
    }
    inventory = read_json(base / 'code_inventory.json')
    result['submitted_code_inventory_matches'] = all(digest(ROOT / p) == h for p,h in inventory['files'].items())
    result['real_freeze_absent'] = not (base/'freeze.json').exists()
    result['real_evaluation_prediction_files'] = sum(len(list((base / f'predictions/{m}/evaluation').glob('*/prediction.json'))) for m in ['L0','L1','S1'])
    result['real_evaluation_view_files'] = sum(len(list((base / f'views/{v}/384/evaluation').glob('*'))) for v in ['V0','V1','V2','V3','V4','V5'])
    result['real_consensus_case_count'] = len(list((base/'annotations/consensus').rglob('metadata.json')))
    old_proposals = {r['image_id']:r for r in read_json(ROOT/'data/processed/preprocessing/geometry_review_v2/standardized91/geometry_proposals.json')}
    differences = []
    for row in read_json(base/'samples/tuning.json'):
        pred = read_json(base/'predictions/L1/tuning'/row['image_id']/'prediction.json')
        old = old_proposals[row['image_id']]
        original = [old['pot_center_x_px'],old['pot_center_y_px'],old['pot_diameter_px']]
        differences.append(max(abs(a-b) for a,b in zip(original,pred['circle_oriented_px'])))
    result['tuning_hough_circles_match_stored_baseline'] = {'cases':len(differences),'max_abs_difference_px':max(differences)}

    with tempfile.TemporaryDirectory(prefix='segmentation_review_') as td:
        f = Path(td)
        write_json(f/'config_draft.json', {'seed':'synthetic', 's1_sam3_auto':{'checkpoint_sha256':None}})
        rows = [{'image_id':f'synthetic_{i:02}'} for i in range(60)]
        write_json(f/'samples/evaluation.json', rows)
        dummy_code = f/'dummy_code.py'
        dummy_code.write_text('original = True',encoding='utf-8')
        write_json(f/'code_inventory.json', {'files':{str(dummy_code):digest(dummy_code)}})
        for row in rows:
            write_json(f / 'annotations/consensus/evaluation' / row['image_id'] / 'metadata.json', {})
        create_freeze(f)
        verify_freeze_for_evaluation(f)
        result['defect_freeze_accepts_metadata_only_no_masks_no_checkpoint_no_calibration'] = True
        dummy_code.write_text('changed = True',encoding='utf-8')
        verify_freeze_for_evaluation(f)
        result['defect_gate_accepts_changed_code_listed_in_inventory'] = True
        write_json(f/'annotations/consensus/evaluation/synthetic_00/metadata.json', {'changed_after_freeze':True})
        verify_freeze_for_evaluation(f)
        result['defect_gate_accepts_changed_reference_metadata'] = True
        old = digest(f/'freeze.json')
        create_freeze(f)
        result['defect_freeze_can_be_overwritten'] = digest(f/'freeze.json') != old

    with tempfile.TemporaryDirectory(prefix='segmentation_score_review_') as td:
        f = Path(td)
        write_json(f/'config_draft.json', {'views':{'definitions':['V0','V1']},'metrics':{'critical_tissue_loss_gt':0.02,'critical_fine_point_loss_gt':0.05}})
        rows = [dict(image_id=i,oriented_width=50,oriented_height=50,split_group_id=i,year=2025,species_code='P',exif_camera_model='synthetic') for i in ['case_present','case_no_GT']]
        write_json(f/'samples/tuning.json',rows)
        case=f/'annotations/consensus/tuning/case_present'
        plant=np.zeros((50,50),bool)
        plant[10:40,10:40]=True
        plant[2:4,2:4]=True  # small complete annotated organ, outside retained box
        layers={name:np.zeros((50,50),bool) for name in ['plant_target','soil_target','other_plant','pot_rim_wall','card_label','other_background','ignore_uncertain']}
        layers['plant_target']=plant
        layers['other_background']=~plant
        for name, mask in layers.items():save_mask_png(case/f'{name}.png',mask)
        write_json(case/'metadata.json', {'fine_points':[], 'critical_organs':[{'id':'whole_small_leaf','bbox_xyxy':[2,2,4,4]}]})
        write_json(f/'views/V1/384/tuning/case_present.json', {'crop_box_oriented_px':[10,10,40,40],'status':'ok'})
        stats=score_split(f,'tuning')
        result['defect_scorer_succeeds_with_missing_GT_and_predictions'] = {'n_sample_images':stats['n_sample_images'],'missing_GT':stats['n_missing_gt'],'entities_reported':list(stats['summary_by_entity'])}
        result['defect_whole_critical_organ_loss_not_flagged'] = stats['summary_by_entity']['V1']['P_only']['critical_failure_wilson_95'][0] == 0
        result['bootstrap_not_called_in_score_split'] = 'stratified_paired_bootstrap(' not in (ROOT/'scripts/segmentation_benchmark/s07_score.py').read_text(encoding='utf-8').split('def score_split(',1)[1]
        ignore=layers['ignore_uncertain'].copy();ignore[0,0]=True
        metrics=compute_support_metrics(np.zeros((50,50),bool), layers, ~ignore, [{'x':0,'y':0,'status':'evaluable'}],1)
        result['defect_landmark_in_ignore_still_counted'] = metrics['fine_points_evaluable']==1

    plant=np.zeros((30,30),bool);plant[10:20,10:20]=True
    assoc=associate_sam3_instances([plant],[0.9],[],[],[15,15,20],30,30)
    result['defect_no_soil_association_status_ok'] = assoc['status']=='ok'
    a=[0,100,101];b=[0,1,100]
    bootstrap=stratified_paired_bootstrap([{'year':2025,'species_code':'P','a':x,'b':y} for x,y in zip(a,b)],'synthetic_median',n_resamples=30)
    result['bootstrap_median_statistic_distinction']={'reported_median_of_paired_differences':bootstrap['median_diff'],'difference_of_method_medians':float(np.median(a)-np.median(b))}
    result['registry_sha256']=protected['registry_sha256']
    output=ROOT/'documentacion/01_informes/04_REVISION_SEGMENTATION_BENCHMARK_V1_CHECKS.json'
    write_json(output,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
