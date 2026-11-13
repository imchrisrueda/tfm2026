"""Record explicit visual development measurements, never approve metric production."""
import csv
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/processed/preprocessing'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extents',type=Path,default=ROOT/'exp_design/development_rim_visual_extents_v3.csv')
    parser.add_argument('--output',type=Path,default=BASE/'development_geometry_v3')
    args=parser.parse_args()
    selection=json.loads((BASE/'development_v1/selection.json').read_text(encoding='utf-8'))
    pilot={x['image_id']:x for x in json.loads((BASE/'development_v1/annotations_pilot.json').read_text(encoding='utf-8'))}
    with args.extents.open(encoding='utf-8',newline='') as f:
        marks={int(r['development_index']):r for r in csv.DictReader(f)}
    assert set(marks)==set(range(1,len(selection)+1))
    out=args.output;out.resolve().relative_to(ROOT.resolve());out.mkdir(exist_ok=True)
    if any(out.iterdir()):raise ValueError('Refusing to overwrite prior geometry review')
    records=[];comparisons=[]
    for r in selection:
        index=r['development_index'];m=marks[index]
        assert hashlib.sha256((ROOT/r['source_path']).read_bytes()).hexdigest()==r['sha256']
        ann=dict(image_id=r['image_id'],source_sha256=r['sha256'],coordinate_space='exif_oriented',development_index=index,review_status='development_review_completed',reviewer='Codex_visual_development_review_not_investigator',review_date='2026-11-12',measurement_scope='pilot_only',reference_quality=m['reference_quality'],pot_diameter_nominal_cm=r['pot_diameter_exterior_cm'],measurement_repeatability_status='not_independently_estimated',physical_accuracy_status='not_calibrated',vegetation_bbox=None,vegetation_truncated=None,vegetation_capture_review='no_obvious_vegetation_truncation_on_development_contact_not_expert_validation',notes=m['notes'])
        if m['reference_quality']=='unusable':
            ann.update(pot_center_x_px=None,pot_center_y_px=None,pot_diameter_px=None,measurement_method='visual_reference_rejected_no_forced_measurement')
        else:
            w,h=r['oriented_width'],r['oriented_height']
            factor=min(490/w,490/h)
            tw,th=round(w*factor),round(h*factor)
            ox=(500-tw)//2
            x0=(float(m['left_canvas_px'])-ox)*w/tw
            x1=(float(m['right_canvas_px'])-ox)*w/tw
            y0=float(m['top_canvas_px'])*h/th
            y1=float(m['bottom_canvas_px'])*h/th
            assert 0<=x0<x1<=w and 0<=y0<y1<=h,(index,x0,y0,x1,y1,w,h)
            dx,dy=x1-x0,y1-y0
            ann.update(pot_center_x_px=(x0+x1)/2,pot_center_y_px=(y0+y1)/2,pot_diameter_px=(dx+dy)/2,rim_extents_oriented_px=[x0,y0,x1,y1],apparent_horizontal_diameter_px=dx,apparent_vertical_diameter_px=dy,apparent_axis_ratio=max(dx,dy)/min(dx,dy),measurement_method='manual_outer_rim_visual_extents_on_490px_contact_mean_axes',display_coordinate_spec='500px tile; image at ((500-thumb_width)//2,0), maximum image dimension490px',visual_extents_canvas_px=[float(m[k]) for k in ['left_canvas_px','top_canvas_px','right_canvas_px','bottom_canvas_px']],diameter_convention='arithmetic_mean_of_horizontal_and_vertical_extents_not_metric_rectification',measurement_uncertainty='not_quantified; contact resolution and occlusion limit interpretation')
            if r['image_id'] in pilot:
                old=pilot[r['image_id']]
                comparisons.append(dict(image_id=r['image_id'],manual_extents_diameter_px=ann['pot_diameter_px'],pilot_8point_diameter_px=old['pot_diameter_px'],relative_difference=abs(ann['pot_diameter_px']/old['pot_diameter_px']-1),scope='within_assistant_different_display_methods_not_independent_observer_repeatability'))
                ann['lower_resolution_extents_measurement']=dict(ann)
                for key,value in old.items():
                    if key not in ['reviewer','review_date','image_id','source_sha256']:
                        ann[key]=value
                ann.update(review_status='accepted',reference_quality='usable_provisional',measurement_scope='pilot_only',notes='Higher-display-resolution 8-point pilot retained; both methods recorded. Still no production scale approval.')
        ann['development_review_completed']=True
        records.append(ann)
    (out/'annotations_development_reviewed.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    report=dict(records=len(records),quality=dict(Counter(r['reference_quality'] for r in records)),measured=sum(r['pot_diameter_px'] is not None for r in records),unmeasurable=[r['image_id'] for r in records if r['pot_diameter_px'] is None],comparative_measurements=comparisons,all_source_hashes_verified=True,all_coordinate_space='exif_oriented',all_pilot_only=True,metric_production_approved=0,review_scope='Exploratory visual geometry by AI; no investigator annotations or metrological validation claimed',reference_review_complete=True,extents_source=str(args.extents.relative_to(ROOT)),extents_sha256=hashlib.sha256(args.extents.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),rectification='Version3 corrects visually misplaced extent center in image083; version2 retained as history')
    (out/'measurement_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    # Reconstruct drawn visual extents on the reviewed contact evidence.
    for start in range(0,len(selection),9):
        sheet=Image.open(BASE/f'development_v1/contact_{start//9+1:02}.jpg').convert('RGB');draw=ImageDraw.Draw(sheet)
        for j,r in enumerate(records[start:start+9]):
            m=marks[r['development_index']];x=(j%3)*500;y=(j//3)*550
            if m['reference_quality']!='unusable':
                box=[float(m[k]) for k in ['left_canvas_px','top_canvas_px','right_canvas_px','bottom_canvas_px']]
                draw.ellipse((x+box[0],y+box[1],x+box[2],y+box[3]),outline='cyan',width=3)
                draw.text((x+7,y+460),'VISUAL EXTENTS - PROVISIONAL',fill='red',stroke_width=1,stroke_fill='white')
            else:draw.text((x+7,y+460),'REFERENCE UNUSABLE - NO DIAMETER',fill='red',stroke_width=1,stroke_fill='white')
        sheet.save(out/f'visual_review_{start//9+1:02}.jpg',quality=94)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
