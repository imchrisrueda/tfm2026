"""One-off, reversible migration. No image or dataset metadata is changed."""
from pathlib import Path
import ast, csv, hashlib, json, re, shutil
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'organizacion'
ARCH = ROOT / '99_archivo/01_antes_reorganizacion'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024), b''): h.update(b)
    return h.hexdigest()
def write(p, obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    if ARCH.exists(): raise SystemExit('Migration already started; inspect receipt rather than repeat')
    selected=[]
    for top in ('scripts','exp_design','doc'):
        selected += [p for p in (ROOT/top).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    selected += [p for p in ROOT.iterdir() if p.is_file() and p.name not in ('AGENTS.md','BITACORA_METODOLOGICA.md','tasks.md')]
    selected += list((ROOT/'scratch').glob('*.py'))
    grouped=defaultdict(list)
    for p in selected: grouped[p.parent].append(p)
    mapping={}
    for parent,files in sorted(grouped.items()):
        n=0
        for p in sorted(files,key=lambda p:p.name.lower()):
            if p.name=='__init__.py': continue
            n+=1
            prefix='s' if p.suffix=='.py' else ''
            # tests keep discoverability by unittest's default pattern.
            name=(f'test_{n:02d}_'+p.name[5:] if p.name.startswith('test_') and p.suffix=='.py' else f'{prefix}{n:02d}_'+p.name)
            mapping[p.relative_to(ROOT).as_posix()]=(p.parent/name).relative_to(ROOT).as_posix()
    for old in mapping:
        p=ROOT/old; dest=ARCH/old;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    for name in ('AGENTS.md','BITACORA_METODOLOGICA.md','tasks.md'):
        shutil.copy2(ROOT/name,ARCH/name)
    # Dataset metadata is an immutable historical record; record its state separately.
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'data').rglob('*') if p.is_file() and p.suffix.lower() not in ('.jpg','.jpeg','.png','.heic','.tif','.tiff')}
    write(OUT/'02_metadatos_datasets_antes.json',protected)
    names=defaultdict(set)
    for old,new in mapping.items(): names[Path(old).name].add(Path(new).name)
    unique={k:next(iter(v)) for k,v in names.items() if len(v)==1}
    modules={Path(k).stem:Path(v).stem for k,v in unique.items() if k.endswith('.py')}
    def translate(text,old):
        # Full paths, Windows command paths, and unique standalone basenames.
        for a,b in sorted(mapping.items(),key=lambda x:-len(x[0])):
            text=text.replace(a,b).replace(a.replace('/','\\'),b.replace('/','\\'))
        for a,b in sorted(unique.items(),key=lambda x:-len(x[0])):
            text=re.sub(r'(?<![\w/\\])'+re.escape(a)+r'(?![\w])',lambda m:b,text)
        if old.endswith('.py'):
            for a,b in sorted(modules.items(),key=lambda x:-len(x[0])):
                text=re.sub(r'(?<=from )'+re.escape(a)+r'\b',lambda m:b,text)
                text=re.sub(r'(?<=import )'+re.escape(a)+r'\b',lambda m:b,text)
                text=re.sub(r'([\x27\x22])'+re.escape(a)+r'(?=\.)',lambda m:m[1]+b,text)
            # Year-specific designs were previously constructed using f-strings.
            text=text.replace("f'exp_design/{year}.csv'", "{2025: 'exp_design/"+Path(mapping['exp_design/2025.csv']).name+"', 2026: 'exp_design/"+Path(mapping['exp_design/2026.csv']).name+"'}[year]")
            text=text.replace('f"{year}.csv"', '{2025: "'+Path(mapping['exp_design/2025.csv']).name+'", 2026: "'+Path(mapping['exp_design/2026.csv']).name+'"}[year]')
        if old.endswith('.tex'):
            # TeX input/bibliography usually omit extensions.
            for a,b in mapping.items():
                if a.startswith('doc/') and Path(a).suffix in ('.tex','.bib'):
                    text=text.replace(str(Path(a[4:]).with_suffix('')).replace('\\','/'),str(Path(b[4:]).with_suffix('')).replace('\\','/'))
        # Ambiguous README names resolve within their original directory.
        for a,b in mapping.items():
            if Path(a).parent==Path(old).parent:
                text=text.replace(']('+Path(a).name+')', ']('+Path(b).name+')')
        return text
    frozen={'exp_design/preprocessing_fullframe_v2_frozen.json','exp_design/partition_assignments_v1.csv','exp_design/partition_plan_v1.json'}
    changed=[]
    for old,new in mapping.items():
        p=ROOT/old;dest=ROOT/new
        if dest.exists():raise RuntimeError(dest)
        if p.suffix.lower() in ('.py','.md','.tex','.json','.ps1','.bib') and old not in frozen:
            raw=p.read_text(encoding='utf-8-sig');updated=translate(raw,old)
            dest.write_text(updated,encoding='utf-8');p.unlink()
        else:p.rename(dest)
        changed.append(dict(old=old,new=new,original_sha256=sha(ARCH/old),current_sha256=sha(dest),frozen_bytes_preserved=old in frozen))
    # Historical ledger stays verbatim. Add an explicit route resolver in the guide.
    for name in ('AGENTS.md','tasks.md'):
        p=ROOT/name;p.write_text(translate(p.read_text(encoding='utf-8'),name),encoding='utf-8')
    write(OUT/'03_mapa_migracion.json',changed)
    with (OUT/'04_mapa_migracion.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(changed[0]));w.writeheader();w.writerows(changed)
    # The active registry changes routes only, never the frozen configuration bytes.
    registry=ROOT/mapping['exp_design/preprocessing_registry.json']
    reg=json.loads(registry.read_text(encoding='utf-8'))
    assert sha(ROOT/reg['configuration_path'])==reg['configuration_sha256']
    for old,new in mapping.items():
        if old.endswith('.py'):ast.parse((ROOT/new).read_text(encoding='utf-8'),filename=new)
    write(OUT/'05_recibo_migracion.json',dict(files=len(changed),image_files_changed=0,dataset_metadata_changed=0,archive=str(ARCH.relative_to(ROOT)),syntax_ok=True))
    print(json.dumps({'renamed':len(changed),'archive':str(ARCH.relative_to(ROOT))}))

if __name__=='__main__':main()
