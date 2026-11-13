# Registro metodológico del proyecto

## Navegación tras M043

Desde M044, `doc/` se reserva exclusivamente a la memoria del TFM, bibliografía y recursos de redacción. Los informes técnicos y auditorías están en `documentacion/01_informes`; los protocolos y guías experimentales en `documentacion/02_protocolos`. No guardar nuevos informes o resultados de revisión en `doc/`. La fuente principal es `doc/01_memoria.tex`; dirigir auxiliares de compilación a `scratch/compilacion_tfm`.

Empezar por `00_LEEME.md` y `organizacion/10_MAPA_EXPERIMENTOS.md`. Los archivos técnicos se han numerado; consultar `organizacion/03_mapa_migracion.json` para resolver rutas históricas de esta bitácora o de evidencias congeladas. `99_archivo/01_antes_reorganizacion` conserva bytes y nombres anteriores, no es código activo. No aplicar un renombrado masivo al archivo, los datasets, .venv ni dependencias de terceros. El código migrado tiene hashes nuevos y no debe reanudar ejecuciones con fingerprint antiguo. Los auditores históricos consultan fuentes conservadas y guardan comprobaciones nuevas en `organizacion`, sin sustituir recibos congelados.

El usuario solicita mantener [BITACORA_METODOLOGICA.md](BITACORA_METODOLOGICA.md) como registro continuo para la futura redacción del artículo científico.

- Leer la bitácora antes de realizar cambios metodológicos o de preparación/análisis de datos.
- Registrar allí cada decisión, su fecha, motivo, fuente, alcance, acción y resultado verificable. Indicar lo pendiente cuando aún no haya resultado.
- Diferenciar lo declarado por el usuario, lo observado en archivos, las hipótesis y lo validado experimentalmente. No presentar planes ni resultados previstos como experimentos realizados.
- Conservar las entradas históricas. Si se rectifica una decisión, añadir una entrada que identifique qué decisión sustituye y por qué.
- Al terminar un trabajo, actualizar el resultado de las acciones de esa sesión o añadir una entrada de cierre con evidencias y limitaciones.

La bitácora recoge las aclaraciones que sustituyen las hipótesis de la auditoría inicial. Consultarlas antes de reutilizar reglas de etiquetado antiguas. Las copias de `data/verificacion_siembra` se preparan para revisión visual; sus etiquetas de diseño no son confirmaciones botánicas.

Los manifiestos vigentes se construyen con `scripts/s05_build_dataset_manifests.py` y las correcciones explícitas de `exp_design/14_species_corrections.csv`. Consultar `data/processed/README_manifiestos.md`. Conservar especie de diseño y especie de trabajo por separado; las copias de verificación mantienen sus nombres originales de revisión y no deben usarse para inferir la etiqueta final. No regenerar los consolidados vigentes con reglas históricas que ignoren las correcciones.

`tasks.md` es la lista numerada de seguimiento hasta la entrega. Al completar trabajo, actualizar las casillas que estén justificadas por evidencia y registrar el resultado en la bitácora. Mantener los números existentes; no marcar tareas parcialmente realizadas como completas ni confundir una fecha prevista con una ejecución.

Para el reparto inicial aplicar `exp_design/04_acquisition_policy.json` y el campo `use_in_initial_partition`: las 23 fotos de `2025-06-20_c1_r2/nikon_d70` son una adquisición secundaria incompleta y quedan de reserva; se usan las 60 iPhone de la raíz. Esto no excluye otras sesiones Nikon completas. El archivo DSC_0380.JPG se conserva tal como está por decisión del investigador; mantener la evidencia histórica de cambio sin considerarlo una revisión pendiente (M022).

Las particiones v1 están en `exp_design/07_partition_assignments_v1.csv` y `08_partition_plan_v1.json`; las listas activas en `data/processed/partitions/v1`. Preservar la asignación al regenerar manifiestos. No reasignar silenciosamente ni entrenar con candidaturas generales: usar C_fit para entrenar, C_val_model_selection para configuración, C_val_calibration para umbrales, G_fit exclusivamente para generación, T_real sólo para prueba congelada y M_aux aparte. En el manifiesto completo exigir `use_in_assigned_partition` para excluir reserva Nikon e incidencias. Mantener íntegros los grupos entre fechas/cámaras y registrar cualquier migración antes de alterar v1.

Escala/preparación: consultar M029–M032 y `data/processed/preprocessing/README.md`. Tras autorizar el investigador revisar alternativas, M029 sustituye 12/22 cm por **encuadre completo, aspecto exacto y lado máximo 2048 px**, con configuración congelada `exp_design/10_preprocessing_fullframe_v2_frozen.json`. No afirmar cm/píxel común ni certificación 3D. Tareas 15–20 cerradas: 1.419 maestros auditados, 32 filas inactivas y 91 fichas exploratorias (84 medidas provisionales/siete no medibles). Las medidas `pilot_only` no habilitan escalado/calibración métrica de producción. El registro activo es `exp_design/12_preprocessing_registry.json`; usar los manifiestos/listas de `data/processed/preprocessing/fullframe_v2/release`, con su fe de erratas de nueve descriptores, sin alterar los números ni las entradas congeladas. Reconstruir complementos por identificador/hash sin sobrescribir originales ni consolidados. Los lectores posteriores deben preservar el rectángulo sin recortes implícitos; validación metrológica, adaptación de modelos y leyendas siguen en sus tareas futuras.
