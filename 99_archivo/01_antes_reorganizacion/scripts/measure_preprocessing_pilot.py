"""Reproduce visual pilot measurements; not exhaustive annotation."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/preprocessing/development_v1'
# Coordinates manually placed by Codex on 1000 px longest-side EXIF-oriented previews.
# They describe visible outer rims, not an independent physical calibration.
SAMPLES = {
    1: ([(515,67),(700,145),(790,336),(708,521),(515,605),(320,524),(239,336),(319,146)], [380,195,710,440]),
    3: ([(500,54),(690,134),(772,325),(692,514),(500,596),(310,515),(227,325),(309,134)], [345,118,638,411]),
    6: ([(487,37),(698,126),(789,344),(700,559),(487,651),(274,559),(184,344),(274,126)], [393,180,652,469]),
    43: ([(481,273),(581,315),(629,422),(585,527),(481,573),(377,531),(335,422),(379,316)], [310,250,697,518]),
    44: ([(448,28),(594,90),(660,239),(595,389),(448,449),(301,389),(237,239),(301,89)], [420,190,492,286]),
    62: ([(328,210),(536,294),(625,502),(537,707),(328,793),(119,707),(31,502),(116,294)], [275,445,383,565]),
    86: ([(526,68),(719,147),(804,339),(720,530),(526,609),(334,531),(248,339),(331,148)], [288,100,741,582]),
    88: ([(503,85),(695,166),(776,357),(695,548),(503,631),(312,550),(230,357),(310,165)], [188,4,840,563]),
    90: ([(292,222),(468,295),(544,475),(470,651),(292,726),(113,652),(38,475),(111,296)], [65,270,650,837]),
}


def main():
    rows = json.loads((OUT / 'selection.json').read_text(encoding='utf-8'))
    annotations = []
    diagnostics = []
    for index, (points, bbox) in SAMPLES.items():
        row = rows[index-1]
        factor = max(row['oriented_width'], row['oriented_height'])/1000
        p = np.array(points, dtype=float)*factor
        a = np.column_stack((2*p[:,0], 2*p[:,1], np.ones(len(p))))
        cx, cy, c = np.linalg.lstsq(a, (p*p).sum(axis=1), rcond=None)[0]
        radius = float(np.sqrt(c+cx*cx+cy*cy))
        residual = np.sqrt(((np.linalg.norm(p-[cx,cy],axis=1)-radius)**2).mean())
        bb = (np.array(bbox)*factor).tolist()
        diameter = radius*2
        D = row['pot_diameter_exterior_cm']
        fmax = 2*min(cx,cy,row['oriented_width']-cx,row['oriented_height']-cy)*D/diameter
        extent = max(cx-bb[0],cy-bb[1],bb[2]-cx,bb[3]-cy)
        fmin = 2*extent*D/diameter+2  # illustrative 1 cm margin on each side
        ann = dict(image_id=row['image_id'], source_sha256=row['sha256'], coordinate_space='exif_oriented', review_status='accepted', reference_quality='usable', reviewer='Codex_visual_pilot_not_independent', review_date='2026-11-12', pot_center_x_px=float(cx), pot_center_y_px=float(cy), pot_diameter_px=diameter, outer_rim_points_px=p.tolist(), rim_fit_rms_px=float(residual), pot_diameter_nominal_cm=D, vegetation_bbox=bb, vegetation_truncated=False, measurement_method='manual_8_points_on_1000px_preview_algebraic_circle_fit', preview_to_source_factor=factor, measurement_repeatability_status='not_estimated', notes='Provisional pilot only. Visible vegetation envelope, not hidden tissue or botanical confirmation. No independent repeated measurement; no ellipse rectification.')
        ann['measurement_scope'] = 'pilot_only'
        annotations.append(ann)
        diagnostics.append(dict(image_id=row['image_id'], development_index=index, species_code=row['species_code'], year=row['year'], camera=row['exif_camera_model'], pot_diameter_px=diameter, circle_fit_rms_px=float(residual), reference_cm=D, field_min_vegetation_1cm_margin=fmin, field_min_complete_pot_cm=D, field_max_source_cm=fmax, pilot_field_cm=12 if row['year']==2025 else 22, field_22cm_covered=bool(22<=fmax), field_40cm_covered=bool(40<=fmax)))
        with Image.open(ROOT/row['source_path']) as source:
            preview = ImageOps.exif_transpose(source).convert('RGB')
            preview.thumbnail((1000,1000))
            draw = ImageDraw.Draw(preview)
            x,y,r=cx/factor,cy/factor,radius/factor
            draw.ellipse((x-r,y-r,x+r,y+r),outline='red',width=3)
            draw.rectangle(bbox,outline='lime',width=3)
            for px,py in points:
                draw.ellipse((px-4,py-4,px+4,py+4),fill='yellow')
            draw.text((10,10), f'PILOT {index:03} | red: outer rim; green: visible vegetation',fill='red',stroke_width=1,stroke_fill='white')
            preview.save(OUT/f'measurement_overlay_{index:03}.png')
    (OUT/'annotations_pilot.json').write_text(json.dumps(annotations,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'field_feasibility_pilot.json').write_text(json.dumps(dict(status='pilot_not_frozen', measurements=diagnostics, measured_examples=len(diagnostics), all_measured_max_common_field_cm=min(x['field_max_source_cm'] for x in diagnostics), complete_pot_min_common_field_cm=20, conclusion='No common field retains complete pots and source coverage in these examples. Investigator authorized review of two fields by year; 12/22 cm remain provisional candidates with coverage and vegetation failures.'),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(diagnostics,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
