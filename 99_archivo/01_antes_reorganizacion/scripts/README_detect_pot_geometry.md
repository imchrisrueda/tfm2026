# Propuestas geométricas para revisión

`detect_pot_geometry.py` sólo acepta una selección íntegra de imágenes **activas
de C_fit**. Verifica SHA-256 antes de abrir cada original y reutiliza el helper de
orientación EXIF y color de `prepare_metric_masters.py`. No aprueba anotaciones,
no modifica manifiestos autoritativos ni abre G_fit, T_real o calibración.

```powershell
python -m pip install --target scratch/opencv_runtime opencv-python-headless
python scripts/detect_pot_geometry.py --output data/processed/preprocessing/geometry_review_v2/standardized91
python scratch/validate_geometry_detector.py
```

La instalación local probada contiene OpenCV 5.0.0 y NumPy 2.5.4. El detector reduce
a 400 px el lado mayor, suaviza con Gauss de 7 × 7, sigma 1,8, y propone círculos
con Hough gradiente. Los radios candidatos van de 0,18 a 0,55 del lado menor;
`dp=1.2`, distancia mínima de centros 0,08 del lado menor y parámetros 100/35.
Ordena propuestas mediante apoyo angular de Canny, oscuridad del anillo y
centralidad. Son heurísticas de desarrollo, sin exactitud métrica acreditada;
pueden escoger el borde interior, sombras o una circunferencia incorrecta.

La envolvente vegetal provisional utiliza HSV (H 25–85, S ≥45, V ≥20 en OpenCV),
exceso G>1,08R y G>1,10B, cierre 3 × 3 y componentes de al menos 10 píxeles que
intersecten el círculo central de radio 0,9r. Puede incluir tarjetas amarillentas
y otras plantas u omitir tejido que no sea verde. `vegetation_truncated` permanece
desconocido: una máscara no certifica que toda la planta esté en la fotografía.

Cada propuesta conserva `reference_quality=algorithm_unreviewed`,
`review_status=algorithm_unreviewed` y `measurement_scope=proposal_only`.
`geometry_proposals.json` reúne todas; `overlays/NNN.json` permite revisar de forma
incremental. En los overlays, rojo es el círculo propuesto, verde la envolvente
provisional y cian el piloto manual aproximado si existe. Los contactos incluyen
los índices NNN para identificar correcciones. Los puntos piloto no intervienen
en la detección: su contraste posterior no los convierte en ground truth.

El informe registra versiones, hashes, cantidades y contraste con el piloto.
`circle_proposed` sólo significa que el algoritmo encontró un candidato; no
significa referencia usable. La revisión debe identificar borde exterior,
inclinación/oclusión, planta de interés y truncamiento antes de transformar esas
propuestas en anotaciones admitidas por el preprocesador.

`--resume` reutiliza JSON incrementales cuyos identificadores y hashes coincidan.
Para una comparación uniforme debe ejecutarse sin reanudar una versión anterior
del detector; los diagnósticos guardan el tamaño de análisis por imagen. Las
carpetas `geometry_review_v2/overlays`, `refined` y `final` conservan intentos de
desarrollo. `standardized91` es la ejecución homogénea final a 400 px; sus
propuestas siguen necesitando revisión.
