"""Select C_fit development images without consulting evaluation pixels."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/preprocessing/development_v1'
SEED = '20261112-preprocessing-v1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = ROOT / 'data/processed/manifest_all.json'
    rows = json.loads(manifest.read_text(encoding='utf-8'))
    pool = [r for r in rows if r['split_assignment'] == 'C_fit' and r['use_in_assigned_partition']]
    rank = lambda r: hashlib.sha256((SEED + r['image_id']).encode()).hexdigest()
    selected = {}
    for session, species in sorted({(r['session_id'], r['species_code']) for r in pool}):
        candidates = sorted([r for r in pool if (r['session_id'], r['species_code']) == (session, species)], key=rank)
        if candidates[0]['year'] == 2025:
            picks = [next(r for r in candidates if r['num_plants_seeded_2025'] == n) for n in (1, 4)]
        else:
            picks = candidates[:2]
        selected.update({r['image_id']: r for r in picks})
    for orientation in sorted({r['exif_orientation'] for r in pool}):
        if not any(r['exif_orientation'] == orientation for r in selected.values()):
            r = min((r for r in pool if r['exif_orientation'] == orientation), key=rank)
            selected[r['image_id']] = r
    chosen = sorted(selected.values(), key=lambda r: (r['session_id'], r['species_code'], rank(r)))
    OUT.mkdir(parents=True, exist_ok=True)
    output = []
    annotations = []
    for i, r in enumerate(chosen, 1):
        item = dict(r, development_index=i, development_selection_reason='two_per_session_species_seeded_density_1_4_2025_plus_EXIF_coverage')
        output.append(item)
        annotations.append(dict(image_id=r['image_id'], source_sha256=r['sha256'], coordinate_space='exif_oriented', review_status='pending', reference_quality='not_measured', reviewer=None, review_date=None, pot_center_x_px=None, pot_center_y_px=None, pot_diameter_px=None, vegetation_truncated=None, vegetation_bbox=None, notes=''))
    (OUT / 'selection.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    with (OUT / 'selection.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(output[0])); writer.writeheader(); writer.writerows(output)
    template = OUT / 'annotations_template.json'
    if not template.exists():
        template.write_text(json.dumps(annotations, ensure_ascii=False, indent=2), encoding='utf-8')
    # Sheets are for triage only; precision annotations use full oriented coordinates.
    for offset in range(0, len(chosen), 9):
        sheet = Image.new('RGB', (1500, 1650), 'white')
        draw = ImageDraw.Draw(sheet)
        for j, r in enumerate(chosen[offset:offset+9]):
            path = ROOT / r['source_path']
            assert digest(path) == r['sha256'], r['image_id']
            with Image.open(path) as im:
                thumb = ImageOps.exif_transpose(im).convert('RGB')
                thumb.thumbnail((490, 490))
                x, y = (j % 3)*500, (j // 3)*550
                sheet.paste(thumb, (x+(500-thumb.width)//2, y))
                draw.text((x+5, y+495), f"{offset+j+1:03d} {r['session_id']} {r['species_code']}", fill='black')
                draw.text((x+5, y+515), r['filename']+f" | {r['oriented_width']}x{r['oriented_height']}", fill='black')
        sheet.save(OUT / f'contact_{offset//9+1:02d}.jpg', quality=92)
    summary = dict(seed=SEED, selection_uses_pixels=False, manifest_sha256=digest(manifest), n=len(chosen), groups=len({r['split_group_id'] for r in chosen}), sessions=dict(Counter(r['session_id'] for r in chosen)), species=dict(Counter(r['species_code'] for r in chosen)), cameras=dict(Counter(r['exif_camera_model'] for r in chosen)), orientations=dict(Counter(r['exif_orientation'] for r in chosen)), source_hashes_verified=True, only_active_C_fit=all(r['split_assignment']=='C_fit' and r['use_in_assigned_partition'] for r in chosen), exclusions=0, geometry_status='pending_measurement')
    assert summary['only_active_C_fit'] and len(summary['sessions']) == 15
    (OUT / 'selection_validation.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
