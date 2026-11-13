"""Check manuscript-only scope and references without compiling or reading images."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
doc=ROOT/'doc'
checks={}
checks['root_contains_only_index_manuscript_previous_pdf']=set(p.name for p in doc.iterdir() if p.is_file())=={'00_INDICE.md','01_memoria.tex','02_memoria_previa.pdf'}
checks['no_experiment_reports_or_json_in_doc']=not any(p.suffix=='.json' or any(k in p.name for k in ('AUDITORIA','REVISION','EXPERIMENTO','BENCHMARK','GUIA_MASCARAS')) for p in doc.rglob('*') if p.is_file())
checks['no_compilation_auxiliaries_in_doc']=not any(p.suffix in ('.aux','.bbl','.blg','.log','.out','.gz','.toc') for p in doc.rglob('*') if p.is_file())
references=[]
for p in doc.rglob('*.tex'):
    for command,raw in re.findall(r'\\(input|include|bibliography|includegraphics)(?:\[[^\]]*\])?\{([^}]+)\}',p.read_text(encoding='utf-8')):
        for target in raw.split(','):
            ext='.bib' if command=='bibliography' else '.tex' if command in ('input','include') else ''
            dest=doc/target
            if ext and not dest.suffix:dest=dest.with_suffix(ext)
            references.append(dict(source=p.relative_to(ROOT).as_posix(),target=dest.relative_to(ROOT).as_posix(),exists=dest.is_file()))
checks['all_tex_includes_bibliography_and_logo_exist']=all(r['exists'] for r in references)
checks['technical_documents_outside_manuscript']=len([p for p in (ROOT/'documentacion/01_informes').glob('*.md') if p.name!='00_INDICE.md'])==3 and len([p for p in (ROOT/'documentacion/02_protocolos').glob('*.md') if p.name!='00_INDICE.md'])==2
migration=json.loads((ROOT/'organizacion/21_migracion_documentacion.json').read_text(encoding='utf-8'))
checks['all_moved_files_exist']=all((ROOT/r['new']).is_file() for r in migration['moves'])
checks['all_pre_move_backups_match']=all(hashlib.sha256((ROOT/'99_archivo/03_antes_separar_doc'/r['old']).read_bytes()).hexdigest()==r['sha256_before'] for r in migration['moves'])
report=dict(passed=all(checks.values()),checks=checks,latex_references=references,pdf_compiled=False)
(ROOT/'organizacion/23_validacion_documentacion_tfm.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
assert report['passed']
