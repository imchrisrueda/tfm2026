"""Capture existing tests and dry-run evidence without PowerShell stderr wrapping."""
import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'organizacion'
commands=[
    ('15_pruebas_procesadores.txt',[sys.executable,'-m','unittest','discover','-s','scripts','-p','test_*.py','-v']),
    ('16_pruebas_benchmark.txt',[sys.executable,'-m','unittest','discover','-s','scripts/segmentation_benchmark/tests','-v']),
    ('18_muestreo_dry_run.json',[sys.executable,'scripts/segmentation_benchmark/s03_inventory_and_sample.py']),
]
results=[]
for name,cmd in commands:
    result=subprocess.run(cmd,cwd=root,capture_output=True)
    (out/name).write_bytes(result.stdout+result.stderr)
    results.append(dict(command=cmd,exit_code=result.returncode,evidence=name))
(out/'19_recibo_pruebas.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False))
assert all(r['exit_code']==0 for r in results)
