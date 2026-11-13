# Utilidad de las copias y opciones de limpieza

No se ha borrado ninguna imagen. GB decimales (10⁹ bytes); los tamaños cuentan sólo archivos de imagen, no el resto de cada carpeta. La igualdad se comprobó por SHA-256 tras agrupar por tamaño; no se evaluó similitud visual.

| Carpeta | Imágenes | GB | Decisión | Motivo |
|---|---:|---:|---|---|
| `analisis_muestra` | 1 | 0.000804 | ARCHIVO PEQUEÑO | Hoja y metadatos de muestra; evidencia histórica, ahorro mínimo. |
| `data/processed` | 7 | 0.007547 | CONSERVAR EVIDENCIA / VISTAS REGENERABLES | Ensayo o revisión histórica. Conservar anotaciones, parámetros, validaciones y el informe; no es entrada de producción. |
| `data/processed/preprocessing/comparison_initial_v2` | 2 | 0.000882 | CONSERVAR EVIDENCIA / VISTAS REGENERABLES | Ensayo o revisión histórica. Conservar anotaciones, parámetros, validaciones y el informe; no es entrada de producción. |
| `data/processed/preprocessing/development_geometry_v2` | 11 | 0.008997 | CONSERVAR EVIDENCIA / VISTAS REGENERABLES | Ensayo o revisión histórica. Conservar anotaciones, parámetros, validaciones y el informe; no es entrada de producción. |
| `data/processed/preprocessing/development_geometry_v3` | 11 | 0.008996 | CONSERVAR EVIDENCIA / VISTAS REGENERABLES | Ensayo o revisión histórica. Conservar anotaciones, parámetros, validaciones y el informe; no es entrada de producción. |
| `data/processed/preprocessing/development_v1` | 29 | 0.031431 | CONSERVAR EVIDENCIA / VISTAS REGENERABLES | Ensayo o revisión histórica. Conservar anotaciones, parámetros, validaciones y el informe; no es entrada de producción. |
| `data/processed/preprocessing/fullframe_development_v2` | 91 | 0.414214 | ARCHIVO / REGENERABLE | 91 maestros de desarrollo históricos. No se afirma duplicidad binaria con producción. Conservar metadatos/recibos y referencias si se retiran píxeles. |
| `data/processed/preprocessing/fullframe_development_v3` | 91 | 0.414214 | ARCHIVO / REGENERABLE | 91 maestros de desarrollo vinculados al archivo reproducible M032. No borrar carpeta completa; conservar validaciones y entradas. |
| `data/processed/preprocessing/fullframe_v2` | 1419 | 6.374574 | CONSERVAR ACTIVO | 1.419 maestros vigentes, manifiestos, listas, recibos y archivo reproducible. No sustituir por pilotos. |
| `data/processed/preprocessing/geometry_review_v2` | 258 | 0.037758 | CONSERVAR EVIDENCIA / VISTAS REGENERABLES | Ensayo o revisión histórica. Conservar anotaciones, parámetros, validaciones y el informe; no es entrada de producción. |
| `data/processed/preprocessing/pilot_v1` | 6 | 0.010340 | CONSERVAR EVIDENCIA / VISTAS REGENERABLES | Ensayo o revisión histórica. Conservar anotaciones, parámetros, validaciones y el informe; no es entrada de producción. |
| `data/processed/preprocessing/roi_small_trial_v1` | 159 | 0.034423 | CONSERVAR EVIDENCIA / VISTAS REGENERABLES | Ensayo o revisión histórica. Conservar anotaciones, parámetros, validaciones y el informe; no es entrada de producción. |
| `data/processed/preprocessing/segmentation_benchmark_v1` | 360 | 0.219951 | CONSERVAR EN DESARROLLO | Muestras, plantillas y vistas tuning. Evaluación bloqueada y defectos R1–R7 pendientes; vistas regenerables pero no equivalen a resultados SAM. |
| `data/processed/preprocessing/strategy_comparison_v3` | 2 | 0.000882 | CONSERVAR EVIDENCIA / VISTAS REGENERABLES | Ensayo o revisión histórica. Conservar anotaciones, parámetros, validaciones y el informe; no es entrada de producción. |
| `data/raw` | 1457 | 7.090142 | CONSERVAR | Originales adquiridos; incluye gráficos auxiliares además de los 1.451 JPEG del manifiesto. |
| `data/verificacion_siembra` | 1451 | 7.083309 | OPCIONAL CON FUNCIÓN | Copias para revisión de siembra; etiquetas de diseño, no finales. Retirables después de cerrar la revisión y conservar manifiestos/mapa de reconstrucción. |
| `sample` | 13 | 0.043514 | CANDIDATA PARCIAL | Muestra inicial; sólo las coincidencias por SHA-256 se acreditan como copias. No se considera prescindible una imagen sin original idéntico localizado. |
| `scratch` | 3 | 0.004408 | CANDIDATA PARCIAL | Sólo tres PNG en roi_small_trial. opencv_runtime es una dependencia activa y se conserva. |

Confirmado: 1450 imágenes de verificación tienen original idéntico en raw (7.079409 GB). En sample: 12 de 13 coinciden exactamente con raw (40.472 MB). En scratch/roi_small_trial: 0 coinciden con una copia fuera de scratch (0.000 MB).

La duplicidad exacta no implica falta de utilidad: una copia puede sostener una revisión con nombres distintos. Las transformaciones, miniaturas y máscaras tampoco son originales duplicados por definición. No sumar todas las apariciones de un grupo como espacio recuperable.

Recomendación: conservar originales y entrega activa; mantener la revisión de siembra hasta decidir cerrarla; considerar después los maestros de desarrollo regenerables. Las copias sin equivalencia acreditada y las evidencias de decisiones se conservan. El inventario CSV permite seleccionar rutas concretas para una limpieza posterior.

[Duplicados por archivo](08_duplicados_exactos.csv) · [Inventario verificable](07_inventario_imagenes.json)

Copias sin original idéntico localizado (conservar):
- `sample/DSC_0286.JPG`
- `data/verificacion_siembra/2026-06-10_c2_r2/0082_Amaranthus_hybridus_F4C4_DSC_0212.JPG`
