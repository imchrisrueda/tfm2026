"""Post-trial geometric diagnostics; no HSV retuning and no production changes."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics

from s31_trial_green_roi_preprocessing import ROOT,OUT,contains,area,window


def main():
    trial=json.loads((OUT/'results.json').read_text(encoding='utf-8'))
    refs={a['image_id']:a for a in json.loads((OUT/'visual_reference_before_run.json').read_text(encoding='utf-8'))}
    selections={r['image_id']:r for r in json.loads((ROOT/'data/processed/preprocessing/development_v1/selection.json').read_text(encoding='utf-8'))}
    outputs=[]
    for row in trial['records']:
        if row['method']!='D_reviewed_circle_rectangle':continue
        src=selections[row['image_id']];w,h=src['oriented_width'],src['oriented_height'];bounds=[0,0,w,h]
        circle=row['observed_pot_reference'];green=row['green_bbox'];ref=refs[row['image_id']]['vegetation_bbox']
        methods=['E_reviewed_rectangle_strict_margin','F_reviewed_square_available_margin','G_reviewed_pot_only_rectangle']
        for method in methods:
            box=bounds;status='fallback_unreliable_reference';fraction=None
            if circle:
                cx,cy,d=circle;r=d/2;m=.10*d
                if method.startswith('G_'):
                    requested=[cx-r-m,cy-r-m,cx+r+m,cy+r+m]
                    box=[max(0,requested[0]),max(0,requested[1]),min(w,requested[2]),min(h,requested[3])];status='crop'
                elif green:
                    requested=[min(cx-r,green[0])-m,min(cy-r,green[1])-m,max(cx+r,green[2])+m,max(cy+r,green[3])+m]
                    if method.startswith('E_'):
                        if contains(bounds,requested):box=requested;status='crop'
                        else:status='fallback_requested_margin_not_covered'
                    else:
                        needed=max(r,cx-green[0],green[2]-cx,cy-green[1],green[3]-cy)
                        capacity=min(cx,cy,w-cx,h-cy)
                        if needed<=capacity:
                            half=min(needed+m,capacity);box=[cx-half,cy-half,cx+half,cy+half]
                            status='crop';fraction=(half-needed)/d
                        else:status='fallback_centered_minimum_not_covered'
                else:status='fallback_no_green_component'
            outputs.append(dict(index=row['development_index'],image_id=row['image_id'],method=method,status=status,crop_box_oriented_px=box,reference_envelope_contained=contains(box,ref),source_area_removed_fraction=1-area(box)/(w*h),geometric_zoom=max(w,h)/max(box[2]-box[0],box[3]-box[1]),effective_symmetric_margin_fraction=fraction))
    summary=[]
    for method in methods:
        rows=[x for x in outputs if x['method']==method];crops=[x for x in rows if x['status']=='crop']
        summary.append(dict(method=method,cases=len(rows),crops=len(crops),fallbacks=dict(Counter(x['status'] for x in rows if x['status']!='crop')),crop_envelope_failures=[x['index'] for x in crops if not x['reference_envelope_contained']],all_cases_median_zoom=statistics.median(x['geometric_zoom'] for x in rows),cropped_cases_median_zoom=statistics.median(x['geometric_zoom'] for x in crops) if crops else None))
    result=dict(created_utc=datetime.now(timezone.utc).isoformat(),analysis_stage='post_initial_trial_to_separate_shape_margin_policy_and_green_contribution',HSV_or_circle_inputs_retuned=False,summary=summary,records=outputs)
    path=OUT/'margin_and_green_diagnostics.json'
    if path.exists():raise ValueError('Refusing to overwrite trial diagnostics')
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
