"""Record runtime versions used in image preparation, without changing environment."""
import importlib.metadata
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from PIL import features

ROOT=Path(__file__).resolve().parents[1]
destination=ROOT/'data/processed/preprocessing/environment_fullframe_v2.json'
if destination.exists():raise ValueError('Environment record already exists')
packages={}
for name in ['Pillow','numpy']:
    try:packages[name]=importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:packages[name]='not_available'
record=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),python=sys.version,platform=platform.platform(),packages=packages,littlecms=features.version('littlecms2'),jpeg=features.version('jpg'),zlib=features.version('zlib'),optional_detector_environment='scratch/opencv_runtime; see geometry_review_v2/standardized91/run.json',measurement_runtime='Python3.14.2 .venv / Pillow13.0.0 / numpy2.5.4 for initial 8-point pilot; extents consolidation Python3.12.1',scope='Versions and source/output hashes support reproducibility. PNG metadata/profile serialization can vary between runs; raster reconstruction is the technical invariant, not asserted byte-identical regeneration.')
destination.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False,indent=2))
