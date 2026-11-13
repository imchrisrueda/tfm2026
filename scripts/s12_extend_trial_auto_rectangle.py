"""Complete the trial factorial: automatic circle with the same bounded rectangle."""
from datetime import datetime, timezone
import json
import statistics
from PIL import Image, ImageDraw
from s31_trial_green_roi_preprocessing import ROOT,OUT,sha,read,write,window,contains,area,present,oriented_srgb


def main():
    base=read(OUT/'results.json');references={r['image_id']:r for r in read(OUT/'visual_reference_before_run.json')}
    selected={r['image_id']:r for r in read(ROOT/'data/processed/preprocessing/development_v1/selection.json')}
    reviewed={r['image_id']:r for r in base['records'] if r['method']=='D_reviewed_circle_rectangle'}
    records=[];tiles=[]
    output=OUT/'auto_rectangle_extension';output.mkdir(exist_ok=False)
    write(output/'protocol_before_run.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),stage='post_initial_trial_extension',parameters_retuned=False,mask_and_circle_source_sha256=sha(OUT/'results.json'),rule='Same bounded rectangle and 0.10 diameter margin as D; automatic circle/HSV inputs from B'))
    for auto in [r for r in base['records'] if r['method']=='B_auto_circle_square']:
        src=selected[auto['image_id']];index=src['development_index'];w,h=src['oriented_width'],src['oriented_height']
        box,status,clipped=window(w,h,auto['observed_pot_reference'],auto['green_bbox'],.10,False)
        manual=reviewed[auto['image_id']]['observed_pot_reference']
        pot=None if manual is None else [manual[0]-manual[2]/2,manual[1]-manual[2]/2,manual[0]+manual[2]/2,manual[1]+manual[2]/2]
        ref=references[auto['image_id']]['vegetation_bbox']
        removed=1-area(box)/(w*h)
        row=dict(index=index,image_id=auto['image_id'],method='H_auto_circle_rectangle',status=status,crop_box_oriented_px=box,reference_envelope_contained=contains(box,ref),reviewed_pot_bbox_contained=None if pot is None else contains(box,pot),source_area_removed_fraction=removed,geometric_zoom=max(w,h)/max(box[2]-box[0],box[3]-box[1]),requested_margin_clipped_by_capture=clipped,effective_crop=status=='crop' and removed>1e-6)
        assert sha(ROOT/src['source_path'])==src['sha256']
        with Image.open(ROOT/src['source_path']) as im:rgb,_,_=oriented_srgb(im)
        tile=Image.new('RGB',(1160,425),'white');draw=ImageDraw.Draw(tile)
        modes=[('A_full_frame',[0,0,w,h]),('H_auto_circle_rectangle',box),('D_reviewed_circle_rectangle',reviewed[auto['image_id']]['crop_box_oriented_px'])]
        for j,(name,roi) in enumerate(modes):
            view,_,_=present(rgb,roi,384);tile.paste(view,(j*388,0));draw.text((j*388+4,388),f'{index:03} {name}',fill='black')
            if j==1:draw.text((j*388+4,405),f'{status}; zoom {row["geometric_zoom"]:.2f}',fill='black')
        for n in [224,384]:present(rgb,box,n)[0].save(output/f'{index:03}_H_{n}.png')
        tiles.append(tile);records.append(row)
    for start in range(0,12,4):
        sheet=Image.new('RGB',(1160,1700),'white')
        for j,tile in enumerate(tiles[start:start+4]):sheet.paste(tile,(0,j*425))
        sheet.save(output/f'comparison_{start//4+1:02}.jpg',quality=94)
    crops=[r for r in records if r['effective_crop']]
    summary=dict(cases=12,effective_crops=len(crops),fallbacks=[r['index'] for r in records if r['status'].startswith('fallback')],no_effect_crop=[r['index'] for r in records if r['status']=='crop' and not r['effective_crop']],crop_envelope_failures=[r['index'] for r in crops if not r['reference_envelope_contained']],crop_reviewed_pot_failures=[r['index'] for r in crops if r['reviewed_pot_bbox_contained'] is False],crop_pot_not_evaluable=[r['index'] for r in crops if r['reviewed_pot_bbox_contained'] is None],median_geometric_zoom_all_cases=statistics.median(r['geometric_zoom'] for r in records),median_source_area_removed_all_cases=statistics.median(r['source_area_removed_fraction'] for r in records))
    write(output/'results.json',dict(completed_utc=datetime.now(timezone.utc).isoformat(),summary=summary,records=records,limits='Post-initial extension; visual references approximate and three pot references not evaluable; no model performance measured'))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
