"""Bind the exhaustive image audit to unchanged manifest/configuration inputs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/processed/preprocessing/fullframe_v2'
CONFIG=ROOT/'exp_design/10_preprocessing_fullframe_v2_frozen.json'
ANNOTATIONS=ROOT/'data/processed/preprocessing/development_geometry_v3/annotations_development_reviewed.json'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    receipt=BASE/'audit_receipt.json'
    if receipt.exists():raise ValueError('Refusing to overwrite audit receipt')
    inputs=[BASE/n for n in ['manifest_fullframe.json','manifest_fullframe.csv','run.json','fingerprint.json','config.json','execution_start.json']]
    inputs += sorted((BASE/'partitions').glob('*.json'))+sorted((BASE/'partitions').glob('*.csv'))
    inputs += [CONFIG,ANNOTATIONS,ROOT/'data/processed/manifest_all.json',ROOT/'exp_design/07_partition_assignments_v1.csv']
    before={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    report=dict(started_utc=datetime.now(timezone.utc).isoformat(),input_hashes=before)
    command=[sys.executable,str(ROOT/'scripts/s32_validate_fullframe_masters.py'),'--output',str(BASE),'--config',str(CONFIG),'--annotations',str(ANNOTATIONS)]
    result=subprocess.run(command,cwd=ROOT,check=False)
    after={p.relative_to(ROOT).as_posix():sha(p) for p in inputs}
    validation=json.loads((BASE/'validation_fullframe.json').read_text(encoding='utf-8')) if (BASE/'validation_fullframe.json').exists() else {}
    report.update(completed_utc=datetime.now(timezone.utc).isoformat(),audit_exit_code=result.returncode,inputs_unchanged=before==after,validation_sha256=sha(BASE/'validation_fullframe.json') if validation else None,validator_sha256=sha(ROOT/'scripts/s32_validate_fullframe_masters.py'),passed=result.returncode==0 and before==after and validation.get('passed') is True)
    receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='input_hashes'},indent=2),flush=True)
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
