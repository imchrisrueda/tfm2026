"""One-off separation of manuscript material from project documentation (M044)."""
from pathlib import Path
import csv,hashlib,json,os,re,shutil
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'organizacion'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    receipt=OUT/'21_migracion_documentacion.json'
    if receipt.exists():raise SystemExit('Migration already recorded; do not repeat')
    moves={
        'doc/01_AUDITORIA_DATOS_CRUDOS_2026-11-12.md':'documentacion/01_informes/01_AUDITORIA_DATOS_CRUDOS_2026-11-12.md',
        'doc/13_REVISION_PREPROCESADO_2026-11-12.md':'documentacion/01_informes/02_REVISION_PREPROCESADO_2026-11-12.md',
        'doc/14_REVISION_SEGMENTATION_BENCHMARK_V1.md':'documentacion/01_informes/03_REVISION_SEGMENTATION_BENCHMARK_V1.md',
        'doc/15_REVISION_SEGMENTATION_BENCHMARK_V1_CHECKS.json':'documentacion/01_informes/04_REVISION_SEGMENTATION_BENCHMARK_V1_CHECKS.json',
        'doc/02_EXPERIMENTO_COMPARACION_PREPROCESADO_V1.md':'documentacion/02_protocolos/01_EXPERIMENTO_COMPARACION_PREPROCESADO_V1.md',
        'doc/03_GUIA_MASCARAS_HUMANAS_BENCHMARK.md':'documentacion/02_protocolos/02_GUIA_MASCARAS_HUMANAS_BENCHMARK.md',
        'doc/11_main.tex':'doc/01_memoria.tex',
        'doc/09_main.pdf':'doc/02_memoria_previa.pdf',
        'doc/capitulos/01_01-introduccion.tex':'doc/capitulos/01_introduccion.tex',
        'doc/capitulos/02_02-estado-arte.tex':'doc/capitulos/02_estado_arte.tex',
        'doc/capitulos/03_03-metodologia.tex':'doc/capitulos/03_metodologia.tex',
        'doc/capitulos/04_04-resultados.tex':'doc/capitulos/04_resultados.tex',
        'doc/capitulos/05_04b-discusion.tex':'doc/capitulos/05_discusion.tex',
        'doc/capitulos/06_05-conclusiones.tex':'doc/capitulos/06_conclusiones.tex',
        'doc/preliminares/01_agradecimientos.tex':'doc/preliminares/02_agradecimientos.tex',
        'doc/preliminares/02_portada.tex':'doc/preliminares/01_portada.tex',
    }
    artifacts=['04_main.aux','05_main.bbl','06_main.blg','07_main.log','08_main.out','10_main.synctex.gz','12_main.toc']
    for n,name in enumerate(artifacts,1):moves['doc/'+name]=f'99_archivo/02_compilacion_previa/{n:02d}_'+name[3:]
    moves['doc/bibliografia/02_texput.log']='99_archivo/02_compilacion_previa/08_texput.log'
    # New numbering swaps two filenames: stage every source before placing destinations.
    backup=ROOT/'99_archivo/03_antes_separar_doc'
    records=[]
    for a,b in moves.items():
        src=(ROOT/a).resolve();dst=(ROOT/b).resolve()
        assert src.is_relative_to(ROOT) and dst.is_relative_to(ROOT)
        saved=backup/a;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,saved)
        records.append(dict(old=a,new=b,sha256_before=sha(src)))
    for a in moves:(ROOT/a).unlink()
    for a,b in moves.items():
        dest=ROOT/b;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(backup/a,dest)
    # Update active text only. Dataset evidence and historical ledger are immutable.
    editable=[p for folder in ('doc','documentacion','scripts','scratch','organizacion') for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.md','.tex','.py') and 'opencv_runtime' not in p.parts and '__pycache__' not in p.parts]
    editable += [p for p in ROOT.glob('*.md') if p.name!='BITACORA_METODOLOGICA.md']
    reverse={b:a for a,b in moves.items()}
    for p in editable:
        # Keep the one-off procedure and its recorded paths unmodified.
        if p==Path(__file__).resolve():continue
        text=p.read_text(encoding='utf-8')
        oldparent=(ROOT/reverse[p.relative_to(ROOT).as_posix()]).parent if p.relative_to(ROOT).as_posix() in reverse else p.parent
        def link(m):
            target=m[1];file=target.split('#')[0]
            if not file or '://' in file or file.startswith('<'):return m[0]
            resolved=Path(os.path.normpath(oldparent/unquote(file)))
            try:rel=resolved.relative_to(ROOT).as_posix()
            except ValueError:return m[0]
            destination=ROOT/moves.get(rel,rel)
            # Relative links in relocated documents must also change depth.
            return ']('+os.path.relpath(destination,p.parent).replace('\\','/')+target[len(file):]+')'
        text=re.sub(r'\]\(([^)]+)\)',link,text)
        # A single regex pass avoids renaming freshly substituted paths twice.
        pattern='|'.join(re.escape(a) for a in sorted(moves,key=len,reverse=True))
        text=re.sub(pattern,lambda m:moves[m[0]],text)
        if p.suffix=='.tex':
            replacements={a[4:-4]:b[4:-4] for a,b in moves.items() if a.startswith('doc/') and b.startswith('doc/') and a.endswith('.tex')}
            pattern='|'.join(re.escape(a) for a in sorted(replacements,key=len,reverse=True))
            text=re.sub(pattern,lambda m:replacements[m[0]],text)
        text=text.replace('Memoria, protocolos de experimentos e informes de revisión','Sólo memoria del TFM, bibliografía, figuras, tablas y recursos de redacción')
        p.write_text(text,encoding='utf-8')
    # Keep the original migration map usable from the pre-M043 names to today's locations.
    path=OUT/'03_mapa_migracion.json';rows=json.loads(path.read_text(encoding='utf-8'))
    for r in rows:
        r['new']=moves.get(r['new'],r['new']);r['current_sha256']=sha(ROOT/r['new'])
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (OUT/'04_mapa_migracion.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    for r in records:r['sha256_after']=sha(ROOT/r['new'])
    receipt.write_text(json.dumps(dict(decision='M044',moves=records,datasets_modified=False,pdf_recompiled=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'moved_or_renamed':len(moves),'experimental_documents_removed_from_doc':6}))

if __name__=='__main__':main()
