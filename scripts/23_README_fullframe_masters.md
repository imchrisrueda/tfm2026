# Alternative full-frame masters

`s17_prepare_fullframe_masters.py` implements an alternative image preparation strategy. It does not select that strategy or freeze a configuration. The methodological decision and its evidence belong in the project log.

The processor applies EXIF orientation and the shared ICC→sRGB conversion. Missing ICC is recorded as assumed sRGB. It preserves the complete oriented source field without crop, padding, homography, plant masking, or brightness adjustment. PNG is saved with a sRGB profile. A missing or unreliable pot measurement does not prevent preparing the complete frame, but the image is explicitly **not metric-normalized**.

## Exact aspect and resolution

For `max_long_edge=2048`, output dimensions are integer multiples of the reduced source aspect ratio, never exceeding the cap or upsampling. Examples:

| Oriented original | Master |
|---|---|
| 3008×2000 | 1880×1250 |
| 3872×2592 | 1936×1296 |
| 6000×4000 | 2046×1364 |
| 4032×3024 | 2048×1536 |

Portrait versions exchange axes. `max_long_edge=0` preserves native dimensions. If a cap cannot represent an image's reduced aspect ratio exactly, the image is rejected rather than rounded or distorted. No common physical field or common cm/pixel is inferred from the image dimensions.

## Configuration and execution

Example **pilot**, not a frozen project decision:

```json
{
  "status": "pilot",
  "strategy": "full_frame_exact_aspect",
  "max_long_edge": 2048,
  "png_compress_level": 3
}
```

```powershell
python scripts/s17_prepare_fullframe_masters.py --config exp_design/fullframe_candidate.json --selection data/processed/preprocessing/development_v1/selection.json --output data/processed/preprocessing/fullframe_candidate --workers 4
```

Pilot mode opens only active C_fit rows and optionally only a supplied selection. `apply` requires `status=frozen` and a timezone-aware `frozen_utc` preceding the run start; T_real additionally requires `--include-test`. Applying a frozen transform to T_real does not authorize tuning it afterwards. The supplied manifest defaults to the authoritative JSON; originals, assignments and authoritative manifests are never changed.

```powershell
python scripts/s17_prepare_fullframe_masters.py --config exp_design/fullframe_frozen.json --output data/processed/preprocessing/fullframe_final --mode apply --include-test --workers 4
```

The output directory must be new. Resume an interrupted run with the same arguments plus `--resume`; config, manifest, selection, annotations, processor, shared color helper, Python and Pillow fingerprints must match. Resumed masters are fully decoded and their hashes and original hashes checked. Processing errors remain explicit and cause a nonzero CLI exit. Source image decoding/ICC errors do not produce an eligible master. Workers must be between 1 and 8; PNG compression level from 0 to 9.

## Persistent outputs

- `manifest_fullframe.csv/json`: all authoritative rows with original labels/groups/roles, preprocessing status, source/master hashes, source box, exact resize factor, dimensions, and derived eligibility flags. No generated file implies an active model-training role different from the original partition.
- `masters/<role>/*.png`: partition-separated images. C_val_model_selection and C_val_calibration have distinct directories.
- `partitions/<role>.json` and CSV for nonempty roles: only successfully created active masters. Use C_fit for classifier fitting and G_fit exclusively for generator fitting.
- `fingerprint.json`, `config.json`, `run.json`, and append-only `completed.jsonl`: reproducibility and resumability evidence.

`--annotations reviewed_geometry.json` optionally joins geometry by image_id and source SHA-256. Missing, rejected, algorithm-unreviewed, or `pilot_only` references are not promoted to reviewed scale. Accepted usable references with reviewer/date and oriented coordinates can propagate center/diameter, nominal reference, and the **variable** physical full-frame field and cm/pixel. A source hash mismatch rejects processing rather than attaching another image's measurements. Full-frame preprocessing does not repair vegetation already truncated in the capture or certify morphological quality.

## Model-reader contract

These are rectangular images. A later loader must retain the entire field and preserve aspect ratio: no implicit center-crop, random-resized crop, or anisotropic stretching. Bucket support cannot be presumed merely because a trainer accepts images. Padding, if explicitly chosen for a later numeric model adapter, must be documented and masked/identified; it is not photographed scene or metric coverage. The master preparation does not implement model training or validate those future readers.

Tests:

```powershell
python -m unittest discover -s scripts -p test_29_prepare_fullframe_masters.py -v
```
