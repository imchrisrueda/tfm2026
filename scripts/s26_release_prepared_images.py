"""Publish a locally audited preparation manifest with explicit descriptive errata.

Does not change images, frozen inputs, labels, roles, or numerical geometry.
"""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from s18_prepare_metric_masters import write_csv

ROOT=Path(__file__).resolve().parents[1]
ROLES=('C_fit','C_val_model_selection','C_val_calibration','G_fit','T_real','M_aux')
COUNTS=dict(zip(ROLES,(856,92,98,86,164,123)))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def role(row):
    if row['split_assignment']=='C_val':
        return {'model_selection':'C_val_model_selection','threshold_calibration':'C_val_calibration'}[row['validation_role']]
    return row['split_assignment']


def release(base,out):
    base=base.resolve();out=out.resolve()
    base.relative_to(ROOT);out.relative_to(ROOT)
    registry=ROOT/'exp_design/12_preprocessing_registry.json'
    if registry.exists():raise ValueError('Preparation registry already exists; explicit version migration required')
    validation=read(base/'validation_fullframe.json');run=read(base/'run.json')
    config=read(ROOT/'exp_design/10_preprocessing_fullframe_v2_frozen.json')
    receipt=read(base/'audit_receipt.json')
    assert validation['passed'] and validation['masters']==1419 and validation['rows']==1451
    assert run['mode']=='apply' and run['config']==config and not run['errors']
    assert validation['all_original_hashes_verified'] and validation['all_masters_decoded_and_reconstructed']
    assert not validation['T_real_used_for_selection'] and config['status']=='frozen'
    config_sha=sha(ROOT/'exp_design/10_preprocessing_fullframe_v2_frozen.json')
    assert validation['config_sha256']==run['config_sha256']==config_sha
    assert validation['authoritative_manifest_sha256']==run['manifest_sha256']
    assert receipt['passed'] and receipt['validation_sha256']==sha(base/'validation_fullframe.json')
    for name,expected in receipt['input_hashes'].items():
        path=(ROOT/name).resolve();path.relative_to(ROOT)
        assert sha(path)==expected,('audited_input_changed',name)
    dependencies=config['source_hashes']
    for name,expected in dependencies.items():
        path=(ROOT/name).resolve();path.relative_to(ROOT)
        assert sha(path)==expected,('frozen_dependency_changed',name)
    records=read(base/'manifest_fullframe.json')
    annotations_path=ROOT/'data/processed/preprocessing/development_geometry_v3/annotations_development_reviewed.json'
    annotations=read(annotations_path)
    assert len(annotations)==91 and sum(a['pot_diameter_px'] is not None for a in annotations)==84
    assert all(a['measurement_scope']=='pilot_only' for a in annotations)
    by_id={r['image_id']:r for r in records}
    assert len(records)==len(by_id)==1451
    amended=[a for a in annotations if a.get('lower_resolution_extents_measurement') is not None]
    assert len(amended)==9
    amendments=[]
    for a in amended:
        assert a['measurement_method']=='manual_8_points_on_1000px_preview_algebraic_circle_fit'
        old=a['diameter_convention']
        assert old=='arithmetic_mean_of_horizontal_and_vertical_extents_not_metric_rectification'
        amendments.append(dict(image_id=a['image_id'],source_sha256=a['source_sha256'],field='metric_annotation.diameter_convention',original_value=old,corrected_value='diameter_of_algebraic_circle_fitted_to_eight_visible_outer_rim_points',reason='Primary measurement is the retained eight-point circle; arithmetic mean describes only lower_resolution_extents_measurement. No numerical value or quality changed.'))
    out.mkdir(parents=True,exist_ok=False)
    errata=dict(version='geometry_metadata_errata_v1',created_utc=datetime.now(timezone.utc).isoformat(),decision_source='BITACORA_METODOLOGICA.md#M031',frozen_annotations_path=annotations_path.relative_to(ROOT).as_posix(),frozen_annotations_sha256=sha(annotations_path),numerical_values_changed=False,quality_or_scope_changed=False,amendments=amendments)
    write(out/'geometry_metadata_errata.json',errata)
    amendment_by_id={a['image_id']:a for a in amendments}
    rows=deepcopy(records)
    execution_sha=sha(base/'manifest_fullframe.json')
    errata_sha=sha(out/'geometry_metadata_errata.json')
    extra_fields={'preparation_release_version','execution_manifest_sha256','geometry_metadata_errata_applied','geometry_metadata_errata_sha256'}
    for row in rows:
        correction=amendment_by_id.get(row['image_id'])
        row.update(preparation_release_version='fullframe_v2_release1',execution_manifest_sha256=execution_sha,geometry_metadata_errata_applied=bool(correction),geometry_metadata_errata_sha256=errata_sha if correction else None)
        if correction:
            assert row['metric_annotation']['diameter_convention']==correction['original_value']
            row['metric_annotation']['diameter_convention']=correction['corrected_value']
        restored=deepcopy(row)
        for key in extra_fields:restored.pop(key)
        if correction:restored['metric_annotation']['diameter_convention']=correction['original_value']
        assert restored==by_id[row['image_id']],('unexpected_release_change',row['image_id'])
    write(out/'manifest_prepared.json',rows);write_csv(out/'manifest_prepared.csv',rows)
    partitions=out/'partitions';partitions.mkdir()
    groups={};actual_counts={}
    for name in ROLES:
        subset=[r for r in rows if r['fullframe_use_in_assigned_partition'] and role(r)==name]
        expected=read(base/'partitions'/f'{name}.json')
        assert {r['image_id'] for r in subset}=={r['image_id'] for r in expected}
        assert len(subset)==COUNTS[name],(name,len(subset))
        actual_counts[name]=len(subset);groups[name]={r['split_group_id'] for r in subset}
        write(partitions/f'{name}.json',subset);write_csv(partitions/f'{name}.csv',subset)
    for i,name in enumerate(ROLES):
        for other in ROLES[i+1:]:assert groups[name].isdisjoint(groups[other]),(name,other)
    assert Counter(r['preprocessing_status'] for r in rows)=={'fullframe_master_created':1419,'inactive_partition_image':32}
    assert sum(bool(r['metric_annotation']) for r in rows if r.get('metric_annotation'))==91
    assert sum(r.get('metric_reference_status')=='reviewed_apparent_outer_rim_scale' for r in rows)==0
    # Freeze a compact, inspectable reproduction snapshot, without duplicating pixels.
    snapshot=out/'reproduction';snapshot.mkdir()
    files=list(dependencies)+['exp_design/10_preprocessing_fullframe_v2_frozen.json','exp_design/06_development_rim_visual_extents_v3.csv','scripts/s07_consolidate_development_geometry.py','scripts/s06_compare_preprocessing_strategies.py','scripts/s28_select_preprocessing_development.py','scripts/s13_freeze_fullframe_preprocessing.py','scripts/s02_audit_fullframe_execution.py','scripts/s26_release_prepared_images.py','scripts/s03_audit_preprocessing_completion.py','scripts/s25_record_preprocessing_environment.py','scripts/test_29_prepare_fullframe_masters.py','scripts/test_30_prepare_metric_masters.py','data/processed/preprocessing/environment_fullframe_v2.json','data/processed/preprocessing/fullframe_v2/unit_tests.json','data/processed/preprocessing/fullframe_v2/unit_tests.txt']
    files += ['scripts/s15_measure_preprocessing_pilot.py','scripts/s10_detect_pot_geometry.py','scripts/22_README_detect_pot_geometry.md','scratch/s04_validate_geometry_detector.py','exp_design/09_preprocessing_fullframe_pilot_v2.json','data/processed/preprocessing/development_v1/annotations_pilot.json','data/processed/preprocessing/development_v1/selection_validation.json','data/processed/preprocessing/fullframe_development_v3/run.json','data/processed/preprocessing/geometry_review_v2/standardized91/run.json','data/processed/preprocessing/geometry_review_v2/standardized91/synthetic_validation.json','data/processed/preprocessing/geometry_review_v2/standardized91/geometry_proposals.json']
    archive=[]
    for name in dict.fromkeys(files):
        source=(ROOT/name).resolve();source.relative_to(ROOT)
        dest=snapshot/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
        assert sha(dest)==sha(source)
        archive.append(dict(source_path=name,archived_path=dest.relative_to(ROOT).as_posix(),sha256=sha(dest)))
    write(out/'reproduction_inventory.json',archive)
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),passed=True,requirements={'base_exhaustive_audit_passed':True,'frozen_dependencies_unchanged':True,'all_1451_rows_numerically_and_semantically_preserved_except_named_descriptive_errata':True,'nine_errata_only_descriptive':True,'same_1419_master_paths_and_hashes':True,'exact_role_counts_and_lists':True,'groups_disjoint_across_six_functions':True,'all_91_development_annotations_still_pilot_only':True,'no_metric_reference_promoted':True,'reproduction_snapshot_hashes_verified':True},rows=len(rows),masters=1419,inactive_rows=32,amended_descriptors=len(amendments),counts_by_role=actual_counts,execution_manifest_sha256=execution_sha,base_validation_sha256=sha(base/'validation_fullframe.json'),base_validation_check_instances=validation['check_instances'],prepared_manifest_sha256=sha(out/'manifest_prepared.json'),prepared_csv_sha256=sha(out/'manifest_prepared.csv'),errata_sha256=errata_sha,reproduction_inventory_sha256=sha(out/'reproduction_inventory.json'),script_sha256=sha(Path(__file__)),scope='General full-frame masters; no common cm/pixel, no metrological or botanical production approval, no model training or performance claim')
    write(out/'validation_release.json',report)
    write(registry,dict(active_preparation_version='fullframe_v2_release1',created_utc=datetime.now(timezone.utc).isoformat(),decision_source='BITACORA_METODOLOGICA.md#M029',configuration_path='exp_design/10_preprocessing_fullframe_v2_frozen.json',configuration_sha256=config_sha,execution_manifest_path=(base/'manifest_fullframe.json').relative_to(ROOT).as_posix(),execution_manifest_sha256=execution_sha,prepared_manifest_path=(out/'manifest_prepared.json').relative_to(ROOT).as_posix(),prepared_manifest_sha256=sha(out/'manifest_prepared.json'),prepared_csv_path=(out/'manifest_prepared.csv').relative_to(ROOT).as_posix(),prepared_csv_sha256=sha(out/'manifest_prepared.csv'),release_validation_path=(out/'validation_release.json').relative_to(ROOT).as_posix(),release_validation_sha256=sha(out/'validation_release.json'),metadata_errata_path=(out/'geometry_metadata_errata.json').relative_to(ROOT).as_posix(),metadata_errata_sha256=errata_sha,partition_lists={name:dict(json_path=(partitions/f'{name}.json').relative_to(ROOT).as_posix(),json_sha256=sha(partitions/f'{name}.json'),csv_path=(partitions/f'{name}.csv').relative_to(ROOT).as_posix(),csv_sha256=sha(partitions/f'{name}.csv')) for name in ROLES},join_keys=['image_id','sha256'],scale_scope='apparent_proportions_preserved_no_common_cm_per_pixel',metric_production_approved=0,source_manifest_policy='Preserve original authoritative manifests and v1 group assignment. Rebuild complements explicitly; never overwrite labels or infer labels from verification filenames.'))
    table='\n'.join(f'| {name} | {actual_counts[name]} |' for name in ROLES)
    (out/'README.md').write_text('# Maestros preparados · fullframe_v2_release1\n\n'
        'Entrega local auditada de 1.419 maestros PNG, con 32 filas inactivas conservadas en el manifiesto completo. '
        'Configuración M029: encuadre completo, aspecto exacto, lado máximo 2048 px, EXIF y sRGB, sin recorte ni relleno. '
        'Conserva proporciones aparentes planta/maceta; no normaliza cm/píxel ni certifica dimensiones 3D.\n\n'
        'Usar [manifest_prepared.json](manifest_prepared.json) o [CSV](manifest_prepared.csv). '
        '`master_image_path` y `source_path` son relativos a la raíz del proyecto; `relative_path` conserva la base histórica project/data indicada en `path_base`. El registro activo está en `exp_design/12_preprocessing_registry.json`. '
        'Para cada función consumir exclusivamente su lista de [partitions](partitions):\n\n'
        '| Función | Maestros |\n|---|---:|\n'+table+'\n\n'
        'Entrenar el clasificador sólo con C_fit; elegir configuración con C_val_model_selection; calibrar umbrales con C_val_calibration. '
        'G_fit se reserva exclusivamente para generación, T_real para prueba congelada y M_aux para el análisis auxiliar separado. '
        'Se mantienen especies de diseño/trabajo, correcciones y grupos v1.\n\n'
        '`width`/`height` y `oriented_width`/`oriented_height` describen el original; `master_width`/`master_height` describen el PNG. '
        '`fullframe_source_box_oriented_px` y `fullframe_resize_factor` registran el rectángulo original y su escala isotrópica. '
        'Las coordenadas provisionales de `metric_annotation` se refieren al original orientado por EXIF, no al PNG. '
        'Los campos de escala de producción permanecen nulos: no sustituirlos automáticamente por estimaciones piloto. '
        '`species_code`/`species_scientific` son la etiqueta de trabajo; `design_species_*` conserva el diseño.\n\n'
        'Las 91 fichas geométricas enlazadas incluyen 84 medidas provisionales y siete referencias no medibles. '
        'Todas permanecen pilot_only; ninguna habilita calibración métrica de producción. '
        '[La fe de erratas](geometry_metadata_errata.json) corrige únicamente nueve descriptores del método; '
        'no cambia imágenes, números, calidad, etiquetas o funciones. Los archivos congelados y el manifiesto original de ejecución se conservan sin cambios.\n\n'
        'La auditoría de imágenes está en `../validation_fullframe.json`, ligada a sus entradas mediante `../audit_receipt.json`. '
        'La [validación de entrega](validation_release.json) verifica las correcciones, listas y conservación de datos. '
        '[El inventario de reproducción](reproduction_inventory.json) identifica por hash las copias de código y entradas en reproduction. '
        'Para reproducir, restituir las rutas archivadas en una raíz de proyecto con los originales cuyos hashes constan en el inventario; '
        'el archivo de reproducción no duplica las fotografías.\n\n'
        'Los lectores de los modelos deben conservar el rectángulo completo: no aplicar recortes centrales/aleatorios implícitos ni estirar ejes. '
        'Adaptación de lectores, resolución de modelos, leyendas y tolerancias metrológicas del panel siguen en sus tareas futuras. '
        'Esta entrega no acredita entrenamiento, mejora predictiva, generación de plantas ni validación botánica.\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,default=ROOT/'data/processed/preprocessing/fullframe_v2')
    parser.add_argument('--output',type=Path,default=ROOT/'data/processed/preprocessing/fullframe_v2/release')
    args=parser.parse_args();release(args.base,args.output)


if __name__=='__main__':main()
