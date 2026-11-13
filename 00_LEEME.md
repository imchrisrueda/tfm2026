# Proyecto TFM · empezar aquí

1. [Mapa de experimentos y estado](organizacion/10_MAPA_EXPERIMENTOS.md): qué se hizo, qué sigue vigente y dónde está la evidencia.
2. [Utilidad de las copias de imágenes](organizacion/11_UTILIDAD_COPIAS.md): tamaños, duplicados comprobados y opciones de limpieza.
3. [Tareas numeradas](tasks.md): 1–20 cerradas; 21–60 pendientes. Esta reorganización no cierra tareas científicas.
4. [Bitácora metodológica](BITACORA_METODOLOGICA.md): cronología íntegra y decisiones M001 en adelante.
5. [Memoria LaTeX](doc/01_memoria.tex): punto de entrada para redactar; el PDF existente es anterior a esta reorganización.

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
