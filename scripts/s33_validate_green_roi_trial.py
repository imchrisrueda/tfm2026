"""Validate the small ROI trial artifacts and window/presentation safeguards."""
import csv
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from s31_trial_green_roi_preprocessing import ROOT,OUT,sha,read,write,window,present,contains


def main():
    config=read(OUT/'config_before_run.json');base=read(OUT/'results.json')
    extension=read(OUT/'auto_rectangle_extension/results.json')
    diagnostic=read(OUT/'margin_and_green_diagnostics.json')
    references={r['image_id']:r for r in read(OUT/'visual_reference_before_run.json')}
    rows={r['image_id']:r for r in read(ROOT/'data/processed/preprocessing/development_v1/selection.json')}
    checks={}
    checks['main_script_matches_pre_run_hash']=sha(ROOT/'99_archivo/01_antes_reorganizacion/scripts/trial_green_roi_preprocessing.py')==config['script_sha256']
    checks['twelve_active_C_fit_only']=len(references)==12 and all(rows[k]['split_assignment']=='C_fit' and rows[k]['use_in_assigned_partition'] for k in references)
    checks['original_hashes_unchanged']=all(sha(ROOT/rows[k]['source_path'])==rows[k]['sha256']==references[k]['source_sha256'] for k in references)
    checks['frozen_release_and_registry_unchanged']=all(sha((ROOT/p) if (ROOT/p).exists() else ROOT/'99_archivo/01_antes_reorganizacion'/p)==h for p,h in config['protected_inputs'].items())
    checks['main_48_records_and_96_views']=len(base['records'])==48
    checks['windows_bounded_and_png_views_valid']=True
    checks['ratio_invariance_geometry']=True
    for record in base['records']:
        row=rows[record['image_id']];box=record['crop_box_oriented_px']
        checks['windows_bounded_and_png_views_valid'] &= contains([0,0,row['oriented_width'],row['oriented_height']],box)
        for n in [224,384]:
            path=OUT/f'{record["development_index"]:03}_{record["method"]}_{n}.png'
            with Image.open(path) as im:
                im.load();checks['windows_bounded_and_png_views_valid'] &= im.mode=='RGB' and im.size==(n,n)
            circle=record['observed_pot_reference']
            if circle and record['method']!='B_auto_circle_square':
                ref=references[record['image_id']]['vegetation_bbox']
                scale=n/max(box[2]-box[0],box[3]-box[1])
                ratio_source=max(ref[2]-ref[0],ref[3]-ref[1])/circle[2]
                ratio_output=record[f'projected_reference_envelope_long_side_px_at_{n}']/(circle[2]*scale)
                checks['ratio_invariance_geometry'] &= math.isclose(ratio_source,ratio_output,rel_tol=1e-12)
    checks['extension_12_cases_and_24_views']=len(extension['records'])==12
    for r in extension['records']:
        for n in [224,384]:
            with Image.open(OUT/f'auto_rectangle_extension/{r["index"]:03}_H_{n}.png') as im:
                im.load();checks['extension_12_cases_and_24_views'] &= im.mode=='RGB' and im.size==(n,n)
    # Independent synthetic coordinates: exact geometry at scale1, and known
    # half-scale letterbox bounds, rather than repeating production arithmetic.
    test=Image.new('RGB',(200,100),'black');ImageDraw.Draw(test).rectangle((60,20,79,39),fill='red')
    shown,_,fraction=present(test,[50,0,150,100],100)
    a=np.array(shown);yy,xx=np.where((a[:,:,0]>200)&(a[:,:,1]<10)&(a[:,:,2]<10))
    checks['synthetic_exact_crop_coordinates']=(xx.min(),yy.min(),xx.max(),yy.max())==(10,20,29,39) and fraction==1
    shown,_,fraction=present(test,[0,0,200,100],100)
    a=np.array(shown)
    checks['synthetic_uniform_aspect_and_padding']=fraction==.5 and bool(np.all(a[:25]==96)) and bool(np.all(a[75:]==96))
    _,status,_=window(200,100,[100,50,80],[40,10,160,90],.1,True)
    checks['synthetic_square_fails_closed']=status=='fallback_centered_square_not_covered'
    box,status,clipped=window(200,100,[100,50,80],[20,0,180,100],.1,False)
    checks['synthetic_rectangle_clips_margin_not_capture']=box==[12,0,188,100] and status=='crop' and clipped and contains(box,[20,0,180,100])
    checks['synthetic_reference_failure_fallback']=window(200,100,None,None,.1,False)[1]=='fallback_unreliable_reference'
    checks['diagnostic_pot_only_losses_explicit']=next(r for r in diagnostic['summary'] if r['method']=='G_reviewed_pot_only_rectangle')['crop_envelope_failures']==[43,88,90]
    checks['automatic_rectangle_result_counts']=extension['summary']['effective_crops']==11 and extension['summary']['fallbacks']==[44] and not extension['summary']['crop_envelope_failures']
    receipt=dict(passed=all(checks.values()),checks=checks,artifacts={p.relative_to(ROOT).as_posix():sha(p) for p in [OUT/'config_before_run.json',OUT/'visual_reference_before_run.json',OUT/'results.json',OUT/'results.csv',OUT/'margin_and_green_diagnostics.json',OUT/'auto_rectangle_extension/results.json']},scope='Technical checks and geometric proxy evaluation; not expert segmentation or model performance',scripts={p.name:sha(p) for p in [ROOT/'scripts/s31_trial_green_roi_preprocessing.py',ROOT/'scripts/s11_diagnose_green_roi_trial.py',ROOT/'scripts/s12_extend_trial_auto_rectangle.py',Path(__file__)]})
    write(ROOT/'organizacion/14_validacion_roi_migrada.json',receipt)
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    assert receipt['passed']


if __name__=='__main__':main()
