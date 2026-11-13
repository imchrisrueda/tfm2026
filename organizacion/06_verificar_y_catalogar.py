"""Complete migration verification and read-only image copy audit."""
from pathlib import Path
import ast, csv, hashlib, json, re
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'organizacion'
ARCH=ROOT/'99_archivo/01_antes_reorganizacion'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def repair_code():
    rows=json.loads((OUT/'03_mapa_migracion.json').read_text(encoding='utf-8'))
    mapping={r['old']:r['new'] for r in rows}
    names=defaultdict(set)
    for a,b in mapping.items():names[Path(a).name].add(Path(b).name)
    unique={a:next(iter(b)) for a,b in names.items() if len(b)==1}
    modules={Path(a).stem:Path(b).stem for a,b in unique.items() if a.endswith('.py')}
    tree=ast.parse((OUT/'01_reorganizar.py').read_text(encoding='utf-8'))
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    fn=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='translate')
    ns=dict(mapping=mapping,unique=unique,modules=modules,re=re,Path=Path)
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'migration_translate','exec'),ns)
    for a,b in mapping.items():
        if a.endswith('.py'):
            text=ns['translate']((ARCH/a).read_text(encoding='utf-8-sig'),a)
            # Historical hashes must verify preserved historical sources, not edited code.
            if a=='scripts/validate_fullframe_masters.py':
                for legacy in ('scripts/prepare_fullframe_masters.py','scripts/prepare_metric_masters.py'):
                    text=text.replace("ROOT/'"+mapping[legacy]+"'", "ROOT/'99_archivo/01_antes_reorganizacion/"+legacy+"'")
            if a=='scripts/audit_preprocessing_completion.py':
                text=text.replace('sha(ROOT/path)==expected', "sha((ROOT/path) if (ROOT/path).exists() else (ROOT/'99_archivo/01_antes_reorganizacion'/path))==expected")
            (ROOT/b).write_text(text,encoding='utf-8')
            ast.parse(text,filename=b)
    # Machine-readable history never gets silently rewritten; links resolve with this map.
    return mapping

def audit_images():
    images=[]
    for top in ('data','sample','analisis_muestra','scratch/roi_small_trial'):
        images += [p for p in (ROOT/top).rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg','.jpeg','.png','.heic','.tif','.tiff')]
    groups=defaultdict(list)
    totals=defaultdict(lambda:dict(files=0,bytes=0))
    for p in images:
        rel=p.relative_to(ROOT).as_posix()
        if rel.startswith('data/processed/preprocessing/'):bucket='/'.join(rel.split('/')[:4])
        elif rel.startswith('data/'):bucket='/'.join(rel.split('/')[:2])
        else:bucket=rel.split('/')[0]
        totals[bucket]['files']+=1;totals[bucket]['bytes']+=p.stat().st_size
        groups[p.stat().st_size].append(p)
    duplicates=[];hashed=0
    for size,ps in groups.items():
        if len(ps)<2:continue
        hs=defaultdict(list)
        for p in ps:hs[sha(p)].append(p.relative_to(ROOT).as_posix());hashed+=1
        for h,paths in hs.items():
            if len(paths)>1:duplicates.append(dict(sha256=h,bytes_each=size,paths=sorted(paths)))
    write(OUT/'07_inventario_imagenes.json',dict(totals=dict(sorted(totals.items())),image_files=len(images),files_hashed=hashed,exact_duplicate_groups=duplicates,method='Group by file byte length; SHA-256 every file in repeated-size groups. Byte identity only; no perceptual comparison, no decoding or visual inspection.'))
    with (OUT/'08_duplicados_exactos.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['sha256','bytes_each','path'])
        for g in duplicates:
            for p in g['paths']:w.writerow([g['sha256'],g['bytes_each'],p])
    print(json.dumps({'images':len(images),'hashed':hashed,'duplicate_groups':len(duplicates),'totals':totals}))

if __name__=='__main__':
    repair_code()
    audit_images()
