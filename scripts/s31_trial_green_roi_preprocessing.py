"""Small C_fit-only trial of full frames versus pot/green-guided crop windows."""
import csv
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scratch/opencv_runtime'))
import cv2
import numpy as np
from PIL import Image, ImageDraw
from s18_prepare_metric_masters import oriented_srgb

OUT=ROOT/'data/processed/preprocessing/roi_small_trial_v1'
INDICES=[1,3,6,37,40,43,44,53,62,86,88,90]
METHODS=['A_full_frame','B_auto_circle_square','C_reviewed_circle_square','D_reviewed_circle_rectangle']
EXTRA_REFERENCE_1000={37:[174,214,581,683],40:[200,260,553,638],53:[324,70,790,557]}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')


def green_bbox(rgb,center,diameter,config):
    w,h=rgb.size;s=config['green_analysis_max_side']/max(w,h)
    small=np.array(rgb.resize((round(w*s),round(h*s)),Image.Resampling.LANCZOS))
    hsv=cv2.cvtColor(small,cv2.COLOR_RGB2HSV)
    mask=cv2.inRange(hsv,np.array(config['hsv_low']),np.array(config['hsv_high']))
    a=small.astype(np.float32)
    mask[~((a[:,:,1]>a[:,:,0]*config['G_over_R']) & (a[:,:,1]>a[:,:,2]*config['G_over_B']))]=0
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
    count,labels,stats,_=cv2.connectedComponentsWithStats(mask,8)
    yy,xx=np.indices(mask.shape)
    xs=(xx+.5)*w/small.shape[1];ys=(yy+.5)*h/small.shape[0]
    anchor=(xs-center[0])**2+(ys-center[1])**2<(config['anchor_radius_fraction']*diameter/2)**2
    selected=np.zeros_like(mask)
    for label in range(1,count):
        component=labels==label
        if stats[label,cv2.CC_STAT_AREA]>=config['min_component_area_px'] and np.any(component & anchor):selected[component]=255
    vy,vx=np.where(selected>0)
    box=None if len(vx)==0 else [float(vx.min()*w/small.shape[1]),float(vy.min()*h/small.shape[0]),float((vx.max()+1)*w/small.shape[1]),float((vy.max()+1)*h/small.shape[0])]
    return box,selected


def contains(outer,inner):return outer[0]<=inner[0]+1e-6 and outer[1]<=inner[1]+1e-6 and outer[2]>=inner[2]-1e-6 and outer[3]>=inner[3]-1e-6
def area(box):return max(0,box[2]-box[0])*max(0,box[3]-box[1])
def overlap(a,b):return area([max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])])


def window(w,h,circle,green,margin_fraction,square):
    if circle is None:return [0,0,w,h],'fallback_unreliable_reference',False
    if green is None:return [0,0,w,h],'fallback_no_green_component',False
    cx,cy,d=circle;r=d/2;m=margin_fraction*d
    if square:
        half=max(r,cx-green[0],green[2]-cx,cy-green[1],green[3]-cy)+m
        requested=[cx-half,cy-half,cx+half,cy+half]
        if not contains([0,0,w,h],requested):return [0,0,w,h],'fallback_centered_square_not_covered',False
        return requested,'crop',False
    requested=[min(cx-r,green[0])-m,min(cy-r,green[1])-m,max(cx+r,green[2])+m,max(cy+r,green[3])+m]
    clipped=[max(0,requested[0]),max(0,requested[1]),min(w,requested[2]),min(h,requested[3])]
    return clipped,'crop',clipped!=requested


def present(rgb,box,n):
    # A common diagnostic square canvas, no anisotropic resize. Padding is marked,
    # and is never a metric master or a change to the frozen full-frame release.
    bw,bh=box[2]-box[0],box[3]-box[1];scale=n/max(bw,bh)
    tx,ty=(n-bw*scale)/2,(n-bh*scale)/2
    view=rgb.transform((n,n),Image.Transform.AFFINE,(1/scale,0,box[0]-tx/scale,0,1/scale,box[1]-ty/scale),resample=Image.Resampling.BICUBIC,fillcolor=(96,96,96))
    yy,xx=np.indices((n,n));valid=(xx+.5>=tx)&(xx+.5<tx+bw*scale)&(yy+.5>=ty)&(yy+.5<ty+bh*scale)
    view=Image.composite(view,Image.new('RGB',(n,n),(96,96,96)),Image.fromarray(valid.astype('uint8')*255))
    return view,scale,float(valid.mean())


def main():
    cv2.setNumThreads(2)
    source=ROOT/'data/processed/preprocessing/development_v1/selection.json'
    selection=read(source);rows=[r for r in selection if r['development_index'] in INDICES]
    assert len(rows)==12 and all(r['split_assignment']=='C_fit' and r['use_in_assigned_partition'] for r in rows)
    reviewed={a['image_id']:a for a in read(ROOT/'data/processed/preprocessing/development_geometry_v3/annotations_development_reviewed.json')}
    previous_refs={a['image_id']:a for a in read(ROOT/'data/processed/preprocessing/development_v1/annotations_pilot.json')}
    auto={a['image_id']:a for a in read(ROOT/'data/processed/preprocessing/geometry_review_v2/standardized91/geometry_proposals.json')}
    protected=[ROOT/'exp_design/12_preprocessing_registry.json',ROOT/'exp_design/10_preprocessing_fullframe_v2_frozen.json',ROOT/'data/processed/preprocessing/fullframe_v2/release/manifest_prepared.json']
    protected_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
    OUT.mkdir(parents=True,exist_ok=False)
    config=dict(created_utc=datetime.now(timezone.utc).isoformat(),selection='purposive_engineering_panel_not_random_prevalence_sample',indices=INDICES,methods=METHODS,green_analysis_max_side=800,hsv_low=[25,45,20],hsv_high=[85,255,255],G_over_R=1.08,G_over_B=1.10,anchor_radius_fraction=.9,min_component_area_px=40,closing_kernel=5,margin_fraction_of_observed_pot_diameter=.10,presentation_sizes=[224,384],presentation_interpolation='bicubic_uniform_affine',padding='neutral_gray_diagnostic_canvas_only_not_new_metric_master',existing_auto_circle_resolution=400,manual_reference_scope='AI_visual_approximate_not_independent_observer_or_expert',selection_sha256=sha(source),script_sha256=sha(Path(__file__)),protected_inputs=protected_hashes)
    write(OUT/'config_before_run.json',config)
    references=[]
    for row in rows:
        index=row['development_index'];f=max(row['oriented_width'],row['oriented_height'])/1000
        box=previous_refs[row['image_id']]['vegetation_bbox'] if row['image_id'] in previous_refs else [x*f for x in EXTRA_REFERENCE_1000[index]]
        references.append(dict(image_id=row['image_id'],source_sha256=row['sha256'],development_index=index,vegetation_bbox=box,reference_source='M026_visual_pilot_bbox' if row['image_id'] in previous_refs else 'new_Codex_visual_bbox_on_1000px_preview_before_HSV_run',coordinate_space='exif_oriented',reviewer='Codex_visual_not_expert',scope='approximate_envelope_not_pixel_segmentation_ground_truth'))
    write(OUT/'visual_reference_before_run.json',references)
    ref_by_id={r['image_id']:r for r in references}
    results=[];tiles=[]
    for row in rows:
        index=row['development_index'];image_id=row['image_id'];path=ROOT/row['source_path']
        assert sha(path)==row['sha256']
        with Image.open(path) as im:rgb,color,_=oriented_srgb(im)
        w,h=rgb.size;ann=reviewed[image_id]
        good=ann['reference_quality']!='unusable' and ann['pot_diameter_px'] is not None
        manual=None if not good else [ann['pot_center_x_px'],ann['pot_center_y_px'],ann['pot_diameter_px']]
        proposal=auto[image_id]
        detected=None if proposal.get('algorithm_status')!='circle_proposed' else [proposal['pot_center_x_px'],proposal['pot_center_y_px'],proposal['pot_diameter_px']]
        green_auto,mask_auto=green_bbox(rgb,detected[:2],detected[2],config) if detected else (None,None)
        green_review,mask_review=green_bbox(rgb,manual[:2],manual[2],config) if manual else (None,None)
        if mask_auto is not None:Image.fromarray(mask_auto).save(OUT/f'{index:03}_green_auto.png')
        if mask_review is not None:Image.fromarray(mask_review).save(OUT/f'{index:03}_green_reviewed.png')
        boxes={METHODS[0]:([0,0,w,h],'full_frame',False)}
        boxes[METHODS[1]]=window(w,h,detected,green_auto,.10,True)
        boxes[METHODS[2]]=window(w,h,manual,green_review,.10,True)
        boxes[METHODS[3]]=window(w,h,manual,green_review,.10,False)
        reference=ref_by_id[image_id]['vegetation_bbox']
        pot=None if not manual else [manual[0]-manual[2]/2,manual[1]-manual[2]/2,manual[0]+manual[2]/2,manual[1]+manual[2]/2]
        overlay=rgb.copy();overlay.thumbnail((800,800));draw=ImageDraw.Draw(overlay)
        sx,sy=overlay.width/w,overlay.height/h
        conv=lambda b:(b[0]*sx,b[1]*sy,b[2]*sx,b[3]*sy)
        draw.rectangle(conv(reference),outline='yellow',width=3)
        if manual:draw.ellipse(conv(pot),outline='white',width=2)
        if green_review:draw.rectangle(conv(green_review),outline='lime',width=2)
        draw.rectangle(conv(boxes[METHODS[3]][0]),outline='cyan',width=3)
        overlay.save(OUT/f'{index:03}_source_overlay.jpg',quality=94)
        tile=Image.new('RGB',(1940,440),'white');td=ImageDraw.Draw(tile)
        thumb=overlay.copy();thumb.thumbnail((380,384));tile.paste(thumb,((384-thumb.width)//2,0));td.text((5,388),f'{index:03} {row["species_code"]} {row["year"]}',fill='black');td.text((5,408),'yellow:ref; green:HSV; cyan:D',fill='black')
        for column,method in enumerate(METHODS):
            box,status,margin_clipped=boxes[method]
            assert contains([0,0,w,h],box) and area(box)>0
            envelope_contained=contains(box,reference)
            pot_contained=None if pot is None else contains(box,pot)
            record=dict(development_index=index,image_id=image_id,source_sha256=row['sha256'],split_group_id=row['split_group_id'],species_code=row['species_code'],year=row['year'],camera=row['exif_camera_model'],method=method,status=status,crop_box_oriented_px=box,observed_pot_reference=manual if method!=METHODS[1] else detected,green_bbox=green_auto if method==METHODS[1] else green_review,manual_reference_usable=good,reference_envelope_contained=envelope_contained,reference_envelope_area_fraction=overlap(box,reference)/area(reference),reviewed_pot_bbox_contained=pot_contained,source_area_removed_fraction=1-area(box)/(w*h),geometric_linear_zoom_vs_full_frame=max(w,h)/max(box[2]-box[0],box[3]-box[1]),requested_margin_clipped_by_capture=margin_clipped,color_processing=color)
            for n in config['presentation_sizes']:
                view,scale,valid_fraction=present(rgb,box,n)
                view.save(OUT/f'{index:03}_{method}_{n}.png')
                record[f'projected_reference_envelope_long_side_px_at_{n}']=max(reference[2]-reference[0],reference[3]-reference[1])*scale
                record[f'canvas_valid_image_fraction_at_{n}']=valid_fraction
                if n==384:tile.paste(view,(388+column*388,0))
            td.text((390+column*388,388),method,fill='black')
            td.text((390+column*388,408),f'{status}; zoom {record["geometric_linear_zoom_vs_full_frame"]:.2f}; bbox {envelope_contained}',fill='black')
            results.append(record)
        tiles.append(tile)
        assert sha(path)==row['sha256']
        print(f'Prepared trial case {index:03}',flush=True)
    for start in range(0,len(tiles),4):
        sheet=Image.new('RGB',(1940,440*len(tiles[start:start+4])),'white')
        for j,tile in enumerate(tiles[start:start+4]):sheet.paste(tile,(0,j*440))
        sheet.save(OUT/f'comparison_{start//4+1:02}.jpg',quality=94)
    summary=[]
    for method in METHODS:
        part=[r for r in results if r['method']==method];crops=[r for r in part if r['status']=='crop']
        safe=[r for r in crops if r['reference_envelope_contained'] and r['reviewed_pot_bbox_contained'] is True]
        summary.append(dict(method=method,cases=len(part),actual_crops=len(crops),fallbacks=dict(Counter(r['status'] for r in part if r['status'].startswith('fallback'))),reference_envelope_contained_after_fallback=sum(r['reference_envelope_contained'] for r in part),crop_envelope_failures=[r['development_index'] for r in crops if not r['reference_envelope_contained']],crop_pot_reference_failures=[r['development_index'] for r in crops if r['reviewed_pot_bbox_contained'] is False],safe_crops_against_both_provisional_references=len(safe),safe_crop_median_source_area_removed=statistics.median(r['source_area_removed_fraction'] for r in safe) if safe else None,safe_crop_median_geometric_zoom=statistics.median(r['geometric_linear_zoom_vs_full_frame'] for r in safe) if safe else None,all_case_median_geometric_zoom=statistics.median(r['geometric_linear_zoom_vs_full_frame'] for r in part),clipped_margin_cases=[r['development_index'] for r in crops if r['requested_margin_clipped_by_capture']]))
    for p in protected:assert sha(p)==protected_hashes[p.relative_to(ROOT).as_posix()]
    report=dict(completed_utc=datetime.now(timezone.utc).isoformat(),panel_size=12,groups=len({r['split_group_id'] for r in rows}),species=dict(Counter(r['species_code'] for r in rows)),cameras=dict(Counter(r['exif_camera_model'] for r in rows)),summary=summary,records=results,limits=['Purposefully selected 12 C_fit cases; not prevalence estimates or independent test set','Visual bbox approximate by Codex, not independent expert or pixel-level truth','Envelope area overlap is not leaf-pixel recall; source area removal is not measured background removal','Diagnostic 224/384 letterboxed views are not metric masters','No model trained; gains refer to geometric sampling density, not predictive performance','Manual rim references remain pilot_only; no metric accuracy approval'],validation=dict(only_C_fit_opened=True,source_hashes_unchanged=True,frozen_release_unchanged=True,all_windows_inside_real_sources=True,no_T_real_G_fit_calibration_or_M_aux_opened=True))
    write(OUT/'results.json',report)
    with (OUT/'results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]));writer.writeheader();writer.writerows({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in results)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
