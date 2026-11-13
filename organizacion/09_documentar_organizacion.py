"""Build navigation, copy recommendations and a verifiable migration receipt."""
from pathlib import Path
import ast,csv,hashlib,json,os,re
from collections import defaultdict
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'organizacion'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def md(p,text):p.write_text(text.strip()+'\n',encoding='utf-8')
rows=json.loads((OUT/'03_mapa_migracion.json').read_text(encoding='utf-8'))
mapping={r['old']:r['new'] for r in rows}
inv=json.loads((OUT/'07_inventario_imagenes.json').read_text(encoding='utf-8'))

# Root paths have no separator; collapse repeated prefix introduced by dual slash translation.
for p in [ROOT/r['new'] for r in rows if Path(r['new']).suffix in ('.md','.py','.tex','.ps1','.json')]+[ROOT/'tasks.md',ROOT/'AGENTS.md']:
    if any(r['new']==p.relative_to(ROOT).as_posix() and r['frozen_bytes_preserved'] for r in rows):continue
    text=p.read_text(encoding='utf-8')
    for old,new in mapping.items():
        if '/' not in old:
            prefix=Path(new).name[:-len(Path(old).name)]
            text=text.replace(prefix+Path(new).name,Path(new).name)
    p.write_text(text,encoding='utf-8')

# Repair relative documentation links using their original directory context.
for p in [ROOT/r['new'] for r in rows if r['new'].endswith('.md')]+[ROOT/'tasks.md',ROOT/'AGENTS.md']:
    text=p.read_text(encoding='utf-8')
    def link(m):
        target=m[1];file=target.split('#')[0]
        if not file or '://' in file:return m[0]
        absolute=Path(os.path.normpath(p.parent/unquote(file)))
        try:rel=absolute.relative_to(ROOT).as_posix()
        except ValueError:return m[0]
        if rel in mapping:
            dest=os.path.relpath(ROOT/mapping[rel],p.parent).replace('\\','/')
            return ']('+dest+target[len(file):]+')'
        return m[0]
    text=re.sub(r'\]\(([^)]+)\)',link,text)
    p.write_text(text,encoding='utf-8')
p=ROOT/mapping['doc/preliminares/portada.tex']
p.write_text(p.read_text(encoding='utf-8').replace('recursos/umu.png','recursos/02_umu.png'),encoding='utf-8')

experiments='''# Mapa de experimentos y documentos

Estado reconstruido de la bitácora M001–M042 y los archivos; esta reorganización no ejecuta experimentos nuevos.

| ID | Bloque | Estado real | Documentación / evidencia | Código de entrada actual |
|---|---|---|---|---|
| E01 | Inventario, etiquetas, siembra | Vigente, tareas 1–10 cerradas; especies de diseño y trabajo separadas | [Manifiestos](../data/processed/README_manifiestos.md), [auditoría histórica](../documentacion/01_informes/01_AUDITORIA_DATOS_CRUDOS_2026-11-12.md), M001–M023 | `scripts/s05_build_dataset_manifests.py`; no usar el etiquetador antiguo para consolidar |
| E02 | Particiones por maceta | v1 congelada, tareas 11–14 cerradas | [Particiones](../data/processed/partitions/v1/README.md), `exp_design/08_partition_plan_v1.json`, M024 | `scripts/s09_create_group_partitions.py` (creación histórica; no reasignar) |
| E03 | Escala métrica 12/22 cm | Piloto histórico; sustituido por M029 | [Piloto](../data/processed/preprocessing/README.md), `pilot_v1`, `geometry_review_v2`, M025–M028 | `scripts/s18_prepare_metric_masters.py`; no es el corpus activo |
| E04 | Comparación geométrica y encuadre completo | Desarrollo terminado; medidas pilot_only | [Revisión](../documentacion/01_informes/02_REVISION_PREPROCESADO_2026-11-12.md), `development_geometry_v3`, `strategy_comparison_v3`, M029–M032 | `scripts/s06_compare_preprocessing_strategies.py` |
| E05 | Entrega fullframe_v2_release1 | ACTIVA: 1.419 maestros; no implica cm/píxel común | [Entrega](../data/processed/preprocessing/fullframe_v2/release/README.md), [registro activo](../exp_design/12_preprocessing_registry.json), M032 | `scripts/s17_prepare_fullframe_masters.py`, `scripts/s32_validate_fullframe_masters.py`; código migrado no reanuda el fingerprint histórico |
| E06 | ROI maceta+verde | Ensayo dirigido de 12 C_fit realizado; candidata, sin migración ni aprendizaje comparado | [Informe](../data/processed/preprocessing/roi_small_trial_v1/README.md), M034–M038 | `scripts/s31_trial_green_roi_preprocessing.py`, `s11_diagnose_green_roi_trial.py`, `s12_extend_trial_auto_rectangle.py` |
| E07 | Benchmark HSV/SAM/planta/tierra | Desarrollo NO APROBADO para congelar/evaluar. L0/L1 tuning ejecutados; SAM, anotación humana y correcciones R1–R7 pendientes | [Especificación](../documentacion/02_protocolos/01_EXPERIMENTO_COMPARACION_PREPROCESADO_V1.md), [revisión](../documentacion/01_informes/03_REVISION_SEGMENTATION_BENCHMARK_V1.md), [máscaras humanas](../documentacion/02_protocolos/02_GUIA_MASCARAS_HUMANAS_BENCHMARK.md), M039–M042 | [Índice de código](../scripts/segmentation_benchmark/00_INDICE.md) |
| E08 | Clasificador, BioCLIP, LoRA, panel experto | Pendientes; no hay entrenamientos acreditados por los ensayos de preparación | [Tareas 21–60](../tasks.md), [plan](../02_PLANIFICACION_TFM.md) | Preparar entorno DRAGO y resolver entradas/referencia según cada tarea |

La bitácora es la cronología; este mapa es la vista de estado. Los informes dentro de datasets conservan rutas históricas: resolverlas con [el mapa de migración](03_mapa_migracion.json). La numeración identifica archivos, no la secuencia experimental ni un orden obligatorio de ejecución.
'''
# Root numbering was derived mechanically; use the authoritative route map.
experiments=experiments.replace('../02_PLANIFICACION_TFM.md','../'+mapping['PLANIFICACION_TFM.md'])
md(OUT/'10_MAPA_EXPERIMENTOS.md',experiments)

raw_copies=[];sample=[];temp=[]
for g in inv['exact_duplicate_groups']:
    if any(p.startswith('data/raw/') for p in g['paths']):
        raw_copies += [(p,g['bytes_each']) for p in g['paths'] if p.startswith('data/verificacion_siembra/')]
        sample += [(p,g['bytes_each']) for p in g['paths'] if p.startswith('sample/')]
    if any(not p.startswith('scratch/') for p in g['paths']):
        temp += [(p,g['bytes_each']) for p in g['paths'] if p.startswith('scratch/roi_small_trial/')]
recommend={
'data/raw':('CONSERVAR','Originales adquiridos; incluye gráficos auxiliares además de los 1.451 JPEG del manifiesto.'),
'data/verificacion_siembra':('OPCIONAL CON FUNCIÓN','Copias para revisión de siembra; etiquetas de diseño, no finales. Retirables después de cerrar la revisión y conservar manifiestos/mapa de reconstrucción.'),
'data/processed/preprocessing/fullframe_v2':('CONSERVAR ACTIVO','1.419 maestros vigentes, manifiestos, listas, recibos y archivo reproducible. No sustituir por pilotos.'),
'data/processed/preprocessing/segmentation_benchmark_v1':('CONSERVAR EN DESARROLLO','Muestras, plantillas y vistas tuning. Evaluación bloqueada y defectos R1–R7 pendientes; vistas regenerables pero no equivalen a resultados SAM.'),
'data/processed/preprocessing/fullframe_development_v2':('ARCHIVO / REGENERABLE','91 maestros de desarrollo históricos. No se afirma duplicidad binaria con producción. Conservar metadatos/recibos y referencias si se retiran píxeles.'),
'data/processed/preprocessing/fullframe_development_v3':('ARCHIVO / REGENERABLE','91 maestros de desarrollo vinculados al archivo reproducible M032. No borrar carpeta completa; conservar validaciones y entradas.'),
'sample':('CANDIDATA PARCIAL','Muestra inicial; sólo las coincidencias por SHA-256 se acreditan como copias. No se considera prescindible una imagen sin original idéntico localizado.'),
'analisis_muestra':('ARCHIVO PEQUEÑO','Hoja y metadatos de muestra; evidencia histórica, ahorro mínimo.'),
'scratch':('CANDIDATA PARCIAL','Sólo tres PNG en roi_small_trial. opencv_runtime es una dependencia activa y se conserva.'),
}
lines=['# Utilidad de las copias y opciones de limpieza','','No se ha borrado ninguna imagen. GB decimales (10⁹ bytes); los tamaños cuentan sólo archivos de imagen, no el resto de cada carpeta. La igualdad se comprobó por SHA-256 tras agrupar por tamaño; no se evaluó similitud visual.','','| Carpeta | Imágenes | GB | Decisión | Motivo |','|---|---:|---:|---|---|']
for k,v in inv['totals'].items():
    status,why=recommend.get(k,('CONSERVAR EVIDENCIA / VISTAS REGENERABLES','Ensayo o revisión histórica. Conservar anotaciones, parámetros, validaciones y el informe; no es entrada de producción.'))
    lines.append(f"| `{k}` | {v['files']} | {v['bytes']/1e9:.6f} | {status} | {why} |")
lines += ['',f"Confirmado: {len(raw_copies)} imágenes de verificación tienen original idéntico en raw ({sum(n for _,n in raw_copies)/1e9:.6f} GB). En sample: {len(sample)} de 13 coinciden exactamente con raw ({sum(n for _,n in sample)/1e6:.3f} MB). En scratch/roi_small_trial: {len(temp)} coinciden con una copia fuera de scratch ({sum(n for _,n in temp)/1e6:.3f} MB).",'', 'La duplicidad exacta no implica falta de utilidad: una copia puede sostener una revisión con nombres distintos. Las transformaciones, miniaturas y máscaras tampoco son originales duplicados por definición. No sumar todas las apariciones de un grupo como espacio recuperable.', '', 'Recomendación: conservar originales y entrega activa; mantener la revisión de siembra hasta decidir cerrarla; considerar después los maestros de desarrollo regenerables. Las copias sin equivalencia acreditada y las evidencias de decisiones se conservan. El inventario CSV permite seleccionar rutas concretas para una limpieza posterior.', '', '[Duplicados por archivo](08_duplicados_exactos.csv) · [Inventario verificable](07_inventario_imagenes.json)']
matched={p for p,n in raw_copies+sample}
unmatched=[p.relative_to(ROOT).as_posix() for folder in ('sample','data/verificacion_siembra') for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg','.jpeg','.png') and p.relative_to(ROOT).as_posix() not in matched]
lines += ['', 'Copias sin original idéntico localizado (conservar):']+['- `'+p+'`' for p in unmatched]
md(OUT/'11_UTILIDAD_COPIAS.md','\n'.join(lines))

rootguide=f'''# Proyecto TFM · empezar aquí

1. [Mapa de experimentos y estado](organizacion/10_MAPA_EXPERIMENTOS.md): qué se hizo, qué sigue vigente y dónde está la evidencia.
2. [Utilidad de las copias de imágenes](organizacion/11_UTILIDAD_COPIAS.md): tamaños, duplicados comprobados y opciones de limpieza.
3. [Tareas numeradas](tasks.md): 1–20 cerradas; 21–60 pendientes. Esta reorganización no cierra tareas científicas.
4. [Bitácora metodológica](BITACORA_METODOLOGICA.md): cronología íntegra y decisiones M001 en adelante.
5. [Memoria LaTeX](doc/{Path(mapping['doc/main.tex']).name}): punto de entrada para redactar; el PDF existente es anterior a esta reorganización.

| Directorio | Función |
|---|---|
| [doc](doc/00_INDICE.md) | Sólo memoria del TFM, bibliografía, figuras, tablas y recursos de redacción |
| [documentacion](documentacion/00_INDICE.md) | Informes técnicos y protocolos experimentales, separados del escrito |
| [exp_design](exp_design/00_INDICE.md) | Diseños, políticas, correcciones, particiones y registro activo |
| [scripts](scripts/00_INDICE.md) | Código numerado y guías; los números no indican qué ejecutar |
| [organizacion](organizacion/00_INDICE.md) | Mapas, inventarios, migración y comprobaciones de esta sesión |
| data | Datasets, manifiestos y evidencias internas preservados |
| sample / analisis_muestra | Muestra inicial y su hoja de revisión; no son conjuntos activos de entrenamiento |
| [scratch](scratch/00_INDICE.md) | Validadores auxiliares y dependencia OpenCV; no vaciar en bloque |
| 99_archivo/01_antes_reorganizacion | Versiones técnicas anteriores con sus nombres y bytes originales; archivo histórico, no código activo |

Convención: documentación/configuraciones `NN_nombre`; módulos Python `sNN_nombre` para permitir importaciones; pruebas `test_NN_nombre` para conservar descubrimiento automático. `AGENTS.md`, `BITACORA_METODOLOGICA.md`, `tasks.md` y `__init__.py` mantienen nombres contractuales. Datasets completos, entorno .venv, dependencias de terceros y archivo histórico quedan fuera de renombrado. Cada directorio de trabajo tiene índice.

Los archivos congelados de configuración y asignación conservan sus bytes. El registro activo cambia sólo sus rutas. El código migrado tiene nuevos hashes: no usarlo para reanudar un fingerprint de código anterior ni reinterpretar informes históricos. Los auditores migrados verifican fuentes históricas contra el archivo conservado; las comprobaciones nuevas se guardan en organizacion. El mapa anterior→actual y sus hashes está en [JSON](organizacion/03_mapa_migracion.json) y [CSV](organizacion/04_mapa_migracion.csv). Los enlaces históricos de la bitácora y datasets se resuelven con ese mapa; no se reescribe su historia.

Para incorporar archivos nuevos, usar el siguiente número libre sin renumerar los anteriores. No regenerar consolidados ni particiones para ordenar carpetas.
'''
md(ROOT/'00_LEEME.md',rootguide)

# Per-directory navigation, outside datasets, archived originals and third-party dependencies.
dirs={ROOT,OUT,ROOT/'scratch'}|{(ROOT/r['new']).parent for r in rows}
for d in sorted(dirs):
    content=[f'# Índice · {d.relative_to(ROOT).as_posix()}','', '[Inicio del proyecto]('+os.path.relpath(ROOT/'00_LEEME.md',d).replace('\\','/')+')','']
    for n,p in enumerate(sorted((p for p in d.iterdir() if p.name not in ('00_INDICE.md','__pycache__','.git','.venv')),key=lambda p:(not p.is_dir(),p.name.lower())),1):
        target=p.name+'/00_INDICE.md' if p.is_dir() and p in dirs else p.name+('/' if p.is_dir() else '')
        content.append(f'{n}. [{p.name}]({target})')
    md(d/'00_INDICE.md','\n'.join(content))

# Parent navigation and manuscript-specific instructions, after the general indexes.
md(ROOT/'documentacion/00_INDICE.md', '''# Documentación técnica del proyecto

1. [Informes y auditorías](01_informes/00_INDICE.md)
2. [Protocolos y guías experimentales](02_protocolos/00_INDICE.md)

La memoria y sus recursos de redacción están exclusivamente en [doc](../doc/00_INDICE.md).
''')
index=ROOT/'doc/00_INDICE.md'
text=index.read_text(encoding='utf-8')
text=text.replace('# Índice · doc', '# Memoria del TFM')
text += '\nFuente principal: `01_memoria.tex`. `02_memoria_previa.pdf` conserva la compilación anterior; no se ha recompilado tras la reorganización.\n\nPara compilar desde doc, dirigir los auxiliares a scratch/compilacion_tfm, por ejemplo: `latexmk -pdf -outdir=../scratch/compilacion_tfm 01_memoria.tex`. No guardar informes experimentales en esta carpeta; usar [documentacion](../documentacion/00_INDICE.md).\n'
index.write_text(text,encoding='utf-8')

metadata=json.loads((OUT/'02_metadatos_datasets_antes.json').read_text(encoding='utf-8'))
changed=[p for p,h in metadata.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
assert not changed,changed
for r in rows:
    assert not (ROOT/r['old']).exists(),r['old']
    assert sha(ROOT/'99_archivo/01_antes_reorganizacion'/r['old'])==r['original_sha256']
    r['current_sha256']=sha(ROOT/r['new'])
    if r['frozen_bytes_preserved']:assert r['current_sha256']==r['original_sha256']
    if r['new'].endswith('.py'):ast.parse((ROOT/r['new']).read_text(encoding='utf-8'))
(OUT/'03_mapa_migracion.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (OUT/'04_mapa_migracion.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
broken=[];external=[]
for d in dirs:
    for p in d.glob('*.md'):
        if p.name=='BITACORA_METODOLOGICA.md':continue
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            file=target.split('#')[0].strip('<>')
            if re.match(r'^[A-Za-z]:/',file):
                external.append(dict(file=p.relative_to(ROOT).as_posix(),target=target,status='external_reference_preserved_not_verified'));continue
            if file and '://' not in file and not (p.parent/unquote(file)).exists():broken.append(dict(file=p.relative_to(ROOT).as_posix(),target=target))
receipt=dict(renamed_files=len(rows),archived_originals_verified=len(rows),dataset_metadata_verified=len(metadata),dataset_metadata_changed=changed,python_syntax_verified=True,broken_markdown_links=broken,external_references=external,image_files_deleted=0,experimental_tasks_closed=0)
(OUT/'13_validacion_organizacion.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt,ensure_ascii=False))
