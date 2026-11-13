"""Compare geometric feasibility on development only; no model-performance claims."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw
from prepare_metric_masters import crop_geometry, oriented_srgb

ROOT = Path(__file__).resolve().parents[1]


def exact_size(w, h, cap):
    divisor = math.gcd(w,h)
    bw,bh=w//divisor,h//divisor
    multiple = min(divisor, cap//max(bw,bh))
    if multiple < 1:
        return w,h
    return bw*multiple,bh*multiple


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotations',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    rows=json.loads((ROOT/'data/processed/preprocessing/development_v1/selection.json').read_text(encoding='utf-8'))
    annotations={x['image_id']:x for x in json.loads(args.annotations.read_text(encoding='utf-8'))}
    assert all(r['split_assignment']=='C_fit' and r['use_in_assigned_partition'] for r in rows)
    args.output.mkdir(parents=True,exist_ok=False)
    strategies={
        'common_20cm':lambda r:20., 'common_22cm':lambda r:22.,
        'common_26cm':lambda r:26., 'common_30cm':lambda r:30., 'common_40cm':lambda r:40.,
        'year_12_22cm':lambda r:12. if r['year']==2025 else 22.,
        'year_11_24cm':lambda r:11. if r['year']==2025 else 24.,
        'pot_ratio_1p1':lambda r:1.1*r['pot_diameter_exterior_cm'],
        'pot_ratio_1p3':lambda r:1.3*r['pot_diameter_exterior_cm'],
    }
    results=[]
    for r in rows:
        ann=annotations.get(r['image_id'])
        for name,fieldfn in strategies.items():
            record=dict(image_id=r['image_id'],year=r['year'],species_code=r['species_code'],camera=r['exif_camera_model'],strategy=name,field_cm=fieldfn(r),eligible=False,source_rim_evaluable=False,source_rim_fits=None)
            reference_ok=ann and ann.get('reference_quality') in {'usable','usable_provisional'} and (ann.get('review_status')=='accepted' or ann.get('development_review_completed') is True)
            if reference_ok:
                cx,cy,d=(float(ann[k]) for k in ['pot_center_x_px','pot_center_y_px','pot_diameter_px'])
                half=fieldfn(r)*d/r['pot_diameter_exterior_cm']/2
                record.update(source_rim_evaluable=True,source_rim_fits=bool(fieldfn(r)>=r['pot_diameter_exterior_cm'] and cx-half>=0 and cy-half>=0 and cx+half<=r['oriented_width'] and cy+half<=r['oriented_height']))
            if not reference_ok:
                record['reason']='reference_not_reliably_measured'
            elif ann.get('vegetation_truncated') is not False or not ann.get('vegetation_bbox'):
                record['reason']='vegetation_not_evaluable_or_truncated'
            else:
                try:
                    crop_geometry(ann,r['pot_diameter_exterior_cm'],fieldfn(r),1024,r['oriented_width'],r['oriented_height'],1)
                    record.update(eligible=True,reason='retains_rim_and_visible_vegetation_plus_1cm_margin')
                except ValueError as exc: record['reason']=str(exc)
            results.append(record)
        # Full frame has an exact mathematical retention guarantee for acquired content,
        # regardless of whether a rim/vegetation annotation is available.
        results.append(dict(image_id=r['image_id'],year=r['year'],species_code=r['species_code'],camera=r['exif_camera_model'],strategy='full_frame',field_cm=None,eligible=True,source_rim_evaluable=False,source_rim_fits=None,reason='all_source_extent_retained_not_metric_normalized'))
    summary=[]
    for name in list(strategies)+['full_frame']:
        subset=[x for x in results if x['strategy']==name]
        ok=[x for x in subset if x['eligible']]
        unknown=sum(x['reason'] in {'reference_not_reliably_measured','vegetation_not_evaluable_or_truncated'} for x in subset)
        summary.append(dict(strategy=name,development_total=len(rows),evaluated=len(subset)-unknown,unknown_or_not_evaluable=unknown,retained=len(ok),observed_failures=len(subset)-unknown-len(ok),source_rim_evaluable=sum(x['source_rim_evaluable'] for x in subset),source_rim_fits=sum(x['source_rim_fits'] is True for x in subset),source_rim_fails=sum(x['source_rim_fits'] is False for x in subset),reasons=dict(Counter(x['reason'] for x in subset if not x['eligible'])),retained_by_year_species=dict(Counter(f"{x['year']}|{x['species_code']}" for x in ok)),metric_common_across_years=name.startswith('common_'),retention_scope='acquired_frame' if name=='full_frame' else 'reviewed_rim_and_visible_envelope_with_1cm_margin'))
    (args.output/'comparison.json').write_text(json.dumps(dict(annotations_sha256=hashlib.sha256(args.annotations.read_bytes()).hexdigest(),reviewed_annotations=sum(x.get('review_status')=='accepted' for x in annotations.values()),method='Geometric feasibility only; no classifier/generator trained and no botanical validation. Full-frame retention and metric eligibility are different endpoints.',strategies=summary,details=results),ensure_ascii=False,indent=2),encoding='utf-8')
    with (args.output/'comparison.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    # Detail comparison uses fixed original-coordinate patch, enlarged only for display.
    examples=[44,46,48,62,64,66]
    for index in examples:
        r=next(x for x in rows if x['development_index']==index)
        ann=annotations.get(r['image_id'])
        if not ann or not ann.get('vegetation_bbox'):continue
        bx0,by0,bx1,by1=ann['vegetation_bbox']
        # Clamp same surrounding detail patch in original coordinates at all resolutions.
        side=max(150.,max(bx1-bx0,by1-by0)*1.2)
        cx,cy=(bx0+bx1)/2,(by0+by1)/2
        w,h=r['oriented_width'],r['oriented_height']
        box=[max(0,cx-side/2),max(0,cy-side/2),min(w,cx+side/2),min(h,cy+side/2)]
        with Image.open(ROOT/r['source_path']) as im: rgb,_,_=oriented_srgb(im)
        sheet=Image.new('RGB',(1500,550),'white');draw=ImageDraw.Draw(sheet)
        for j,cap in enumerate([1024,1536,2048]):
            size=exact_size(w,h,cap); small=rgb.resize(size,Image.Resampling.LANCZOS)
            factor=size[0]/w
            patch=small.resize((490,490),Image.Resampling.NEAREST,box=tuple(x*factor for x in box))
            sheet.paste(patch,(j*500,0))
            draw.text((j*500+5,495),f'{index:03d} cap={cap}, actual={size[0]}x{size[1]}',fill='black')
            draw.text((j*500+5,515),'Same patch; display enlargement only',fill='black')
        sheet.save(args.output/f'detail_{index:03}.jpg',quality=95)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
