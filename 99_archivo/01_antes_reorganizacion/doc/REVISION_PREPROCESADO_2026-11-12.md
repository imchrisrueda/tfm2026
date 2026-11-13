# Revisión de escala y preparación de imágenes

Decisión M029, 12 de noviembre de 2026. La comparación se realiza sólo con C_fit; no usa resultados de modelos ni inspección de T_real para elegir parámetros.

## Decisión

Se sustituye el recorte a campos de 12/22 cm por **maestros del encuadre completo, con proporciones exactas y lado máximo de 2048 px**. Es la alternativa que conserva toda la extensión adquirida y no descarta sistemáticamente plantas por un encuadre insuficiente para un recorte centrado.

El alcance cambia explícitamente: se preservan **proporciones aparentes planta/maceta**, pero no centímetros por píxel comunes entre fotografías. La normalización métrica obligatoria se retira del corpus general. Las referencias geométricas y su calidad quedan registradas por separado y no se convierten en calibración aprobada. Esta rectificación está autorizada por el investigador al solicitar probar alternativas y elegir la más adecuada para el objetivo.

## Evidencia y denominadores

El lote tiene 91 fotografías de 76 macetas, 15 sesiones, tres especies y cuatro cámaras. Se completa la revisión exploratoria de las 91: 84 medidas provisionales y siete referencias no medibles (tres por oclusión y cuatro por borde incompleto). Se conservan centro, diámetro nominal, diámetro aparente, ejes o puntos y procedencia. Todas permanecen `pilot_only`; no se afirma que sean mediciones del investigador, confirmación botánica ni calibración metrológica.

Las medidas por extremos visibles se trazan sobre imágenes de lado máximo 490 px y se expresan después en coordenadas del original orientado. En nueve casos se conserva el ajuste de ocho puntos sobre vistas de 1000 px. La diferencia de diámetro entre ambos métodos del mismo asistente tiene mediana 0,45 % y máximo 1,22 %: es una comprobación de consistencia interna, **no repetibilidad independiente ni exactitud física**. No se estira una elipse para hacerla circular.

| Alternativa | Ventana y maceta cubiertas por la fuente / 84 referencias | Envolvente y margen de 1 cm conservados / 9 anotaciones | cm/píxel común entre años |
|---|---:|---:|---|
| Campo común 20 cm | 48 | 4 | Sí, en los casos aptos |
| Campo común 22 cm | 36 | 4 | Sí, en los casos aptos |
| Campo común 26 cm | 7 | 0 | Sí, en los casos aptos |
| Campo común 30 cm | 1 | 0 | Sí, en los casos aptos |
| Campo común 40 cm | 0 | 0 | Sí, en los casos aptos |
| 12 cm en 2025 / 22 cm en 2026 | 63 | 5 | No |
| 11 cm en 2025 / 24 cm en 2026 | 52 | 3 | No |
| 1,1 diámetros de maceta | 68 | 5 | No |
| 1,3 diámetros de maceta | 25 | 0 | No |
| Encuadre completo | No exige estimar ventana física | Conserva toda la extensión de 91/91 originales | No |

Las dos columnas cuantitativas son criterios distintos. Las 75 medidas adicionales sin envolvente no se cuentan como rechazos de vegetación. Las siete referencias no medibles tampoco prueban falta de cobertura física. La última fila garantiza retención de la extensión adquirida por construcción; no demuestra que todas las plantas estuvieran íntegras al fotografiarlas ni compara la misma variable que las otras filas. La incertidumbre de medidas exploratorias puede cambiar los casos cercanos al límite.

Los campos pequeños conservan más fuentes, pero pueden cortar hojas extendidas; aumentarlos provoca falta de cobertura. Dos campos por año no resuelven ese conflicto y añaden escalas diferentes. Un recorte ajustado a cada planta alteraría la variación aparente de tamaños y no se adopta. El lienzo cuadrado con relleno no se adopta como maestro, porque añade contenido sin referencia física; tampoco se reconstruyen partes de plantas mediante generación.

## Automatización examinada

Un detector Hough con selección por borde/centralidad y propuesta HSV produce 91 candidatos en una pasada homogénea de 400 px. Frente a los nueve pilotos aproximados, la diferencia absoluta mediana de diámetro es 3,65 %, con un máximo de 35,53 %; se detectan círculos del fondo o desplazados. Ningún candidato se aprueba automáticamente. Siete controles sintéticos correctos no validan el detector en estas escenas reales. Los candidatos y ensayos anteriores se conservan como evidencia de una alternativa descartada, separados de las anotaciones visuales.

## Transformación fijada

Aplicar EXIF antes de usar coordenadas; convertir ICC embebido válido a sRGB y registrar la suposición sRGB cuando no haya perfil. No corregir brillo o balance por imagen. Redimensionar todo el rectángulo con Lanczos, sin ampliar, a un múltiplo entero de la razón de aspecto reducida por MCD, con lado máximo 2048. Guardar PNG RGB con perfil sRGB y compresión 3.

Así se conserva exactamente el mismo factor en ambos ejes. Los tamaños resultantes son 1880×1250 para Nikon D70, 1936×1296 para Nikon D3000, 2046×1364 para Sony e 2048×1536 para iPhone, con las orientaciones inversas cuando corresponda. No hay recorte, relleno, homografía ni tejido reconstruido. El margen físico no se inventa: puede ser pequeño en el original y queda como propiedad de la captura.

La comparación visual 1024/1536/2048 usa el mismo parche del original. Se elige 2048 para conservar más detalle de las plántulas sin exigir resolución nativa en todo el corpus. No se afirma que sea la resolución óptima del clasificador o del generador: su elección se mantiene en las tareas de modelos. Los originales siguen disponibles.

El piloto estable de 91 maestros pasa la auditoría que verifica hashes y reconstruye todos sus píxeles desde los originales con EXIF, color y resize. Incluye siete conversiones ICC de iPhone; T_real permanece sin decodificar durante esta elección. La aplicación final debe usar la configuración congelada con fecha anterior a su inicio y guardar su propia auditoría completa.

## Uso posterior y límites

Cada modelo deberá respetar el encuadre completo al cargarlo. El lector estándar de un entrenador puede recortar aunque los archivos estén completos; se debe comprobar su código y adaptar el tratamiento de tamaños antes de entrenar. No asumir que desactivar `center_crop` elimina todo recorte, porque puede sustituirlo por otro aleatorio. No mezclar C_fit, selección, calibración, G_fit, T_real o M_aux.

Las proporciones planta/maceta son invariantes bajo esta escala isotrópica en la imagen, pero el relieve y la perspectiva siguen afectando a su interpretación física. Los fondos, tarjetas y cámaras continúan presentes; su posible influencia debe examinarse en el análisis de los modelos. Las referencias no fiables quedan fuera de la interpretación métrica, aunque una imagen pueda seguir siendo un maestro general válido. La tarea 45 conserva la rúbrica, tolerancias y anotaciones repetidas del panel; esta preparación no la resuelve.

## Archivos y reproducción

- Comparación: `data/processed/preprocessing/strategy_comparison_v3/comparison.json` y `.csv`.
- Medidas y estados: `data/processed/preprocessing/development_geometry_v3/annotations_development_reviewed.json`, `measurement_review.json` y superposiciones.
- Automatización descartada: `data/processed/preprocessing/geometry_review_v2/standardized91`.
- Piloto estable: `data/processed/preprocessing/fullframe_development_v3`.
- Configuración final: `exp_design/preprocessing_fullframe_v2_frozen.json`.
- Corpus y auditoría finales: `data/processed/preprocessing/fullframe_v2`; entrega activa en `fullframe_v2/release`, registrada en `exp_design/preprocessing_registry.json`. Generación: 1.419 maestros y 32 filas inactivas; auditoría: 23.018 controles correctos y 1.419 rasters reconstruidos. Trece tests de procesadores correctos. La pausa es M030; reanudación/corrección descriptiva M031 y cierre M032.
- `release/geometry_metadata_errata.json` corrige nueve descripciones del método de diámetro, sin alterar cifras ni calidad; `release/validation_release.json` verifica esa derivación y conserva las seis funciones v1. `release/reproduction_inventory.json` identifica las copias de código/entradas por hash. Las 91 fichas siguen exploratorias, no calibraciones de producción.

Fuentes técnicas primarias: [Pillow ImageOps](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html), [OpenCV Hough](https://docs.opencv.org/4.13.0/d4/d70/tutorial_hough_circle.html) y [Diffusers DreamBooth](https://huggingface.co/docs/diffusers/training/dreambooth). Estas fuentes describen transformaciones y lectores; los resultados cuantitativos proceden de los archivos locales citados.
