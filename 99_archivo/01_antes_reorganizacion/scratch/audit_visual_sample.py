"""Hoja de revisión dirigida: incidencias anotadas y cámaras, no muestra aleatoria."""
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
import pandas as pd

root = Path(__file__).resolve().parents[1]
out = root / 'data/processed/audit_raw_2026-11-12'
selected = {
 '2025-05-13_c1_r1': ['DSC_0062.JPG'],
 '2025-05-28_c1_r1': ['DSC_0025.JPG', 'DSC_0039.JPG'],
 '2025-06-05_c1_r2': ['DSC_0081.JPG', 'DSC_0110.JPG', 'DSC_0137.JPG', 'DSC_0143.JPG', 'DSC_0145.JPG'],
 '2025-06-16_c1_r2': ['DSC_0263.JPG'],
 '2025-06-20_c1_r2': ['IMG_4131.jpg', 'IMG_4153.jpg', 'IMG_4155.jpg', 'IMG_4170.jpg', 'IMG_4182.jpg', 'nikon_d70/DSC_0380.JPG'],
 '2026-05-06_c2_r1': ['DSC_0601.JPG'],
 '2026-05-14_c2_r1': ['DSC_0772.JPG', 'DSC_0797.JPG'],
 '2026-06-12_c2_r2': ['DSC_0083.JPG', 'DSC_0130.JPG'],
 '2025-06-12_c1_r2': ['DSC_0151.JPG', 'DSC_0161.JPG'],
 '2026-04-22_c2_r1': ['DSC04756.JPG', 'DSC04773.JPG', 'DSC04813.JPG'],
}
paths = [root / 'data/raw' / session / filename for session, names in selected.items() for filename in names]
paths = [p for p in paths if p.exists()]
canvas = Image.new('RGB', (4 * 300, ((len(paths) + 3) // 4) * 255), 'white')
draw = ImageDraw.Draw(canvas)
for i, path in enumerate(paths):
    with Image.open(path) as im:
        thumb = ImageOps.exif_transpose(im).convert('RGB')
        thumb.thumbnail((292, 210))
    x, y = (i % 4) * 300, (i // 4) * 255
    canvas.paste(thumb, (x + (300 - thumb.width) // 2, y))
    draw.text((x+4, y+212), str(path.parent.name), fill='black')
    draw.text((x+4, y+228), path.name, fill='black')
canvas.save(out / 'visual_sample.jpg', quality=93)
pd.DataFrame({'relative_path': [p.relative_to(root).as_posix() for p in paths], 'selection': 'directed_field_notes_and_camera_examples'}).to_csv(out / 'visual_sample.csv', index=False)
print(f'{len(paths)} imágenes en {out / "visual_sample.jpg"}')
