# Scripts de Procesamiento y Catalogación (TFM 2026)

Preparación vigente M029: [maestros de encuadre completo](23_README_fullframe_masters.md) con `s17_prepare_fullframe_masters.py`, auditoría independiente `s32_validate_fullframe_masters.py` y configuración `exp_design/10_preprocessing_fullframe_v2_frozen.json`. Preserva proporciones/aspecto, sin cm/píxel común. `s18_prepare_metric_masters.py` y los candidatos de 12/22 cm son ensayos históricos de una alternativa descartada como corpus principal. Véase `data/processed/preprocessing/README.md` y la bitácora antes de regenerar.

Este directorio contiene los scripts de procesamiento, inventario y preparación de datos para el Trabajo de Fin de Máster (*Generación y validación taxonómica y morfológica de imágenes sintéticas de Amaranthus palmeri con evaluación de proporciones aparentes*).

## Construcción de manifiestos vigentes

Usar `s05_build_dataset_manifests.py` para los consolidados de 2025, 2026 y ambos años. Incorpora la adquisición conciliada, los metadatos y hashes actuales, las aclaraciones del investigador y `exp_design/14_species_corrections.csv`. Conserva versiones anteriores antes de sustituir los CSV/JSON. No modifica los originales ni las fotografías copiadas para revisión.

```powershell
.venv\Scripts\python.exe scripts\s05_build_dataset_manifests.py
.venv\Scripts\python.exe scratch\s03_validate_final_manifests.py
```

La corrección de 2026/c2/r2 en F26C1 y F4C4 se propaga entre fechas de las mismas macetas: la especie de trabajo es palmeri y la prevista por diseño se conserva aparte. Las etiquetas se documentan en [README_manifiestos.md](../data/processed/README_manifiestos.md), junto con sus fuentes, exclusiones y campos pendientes. Los apartados históricos de esta página y los scripts anteriores que sólo usan la cuadrícula no incluyen por sí solos estas correcciones; no deben utilizarse para sobrescribir los consolidados vigentes.

El constructor también aplica `exp_design/04_acquisition_policy.json`: las 23 fotos de `2025-06-20_c1_r2/nikon_d70` se conservan de reserva y no son candidatas para el reparto inicial. Se generan vistas `manifest_initial_pool_*.csv` y el campo `use_in_initial_partition`. Las demás sesiones Nikon completas no se excluyen. La aceptación de DSC_0380 tal como está se registra aparte de su cambio histórico; véase bitácora M022.

Las particiones v1 ya están creadas por `s09_create_group_partitions.py`, con semilla 20261112, y se preservan al regenerar. El script de creación se niega a sobrescribir v1; no ejecutarlo para volver a sortear. Usar las listas activas de [partitions/v1](../data/processed/partitions/v1/README.md): C_fit para entrenar, las dos reservas C_val para configuración/calibración, G_fit para generación, T_real para prueba final y M_aux aparte. Verificar además con `.venv\Scripts\python.exe scratch\s05_validate_group_partitions.py`.

## Auditoría del corpus completo (12 de noviembre de 2026)

El estado contrastado está en [01_AUDITORIA_DATOS_CRUDOS_2026-11-12.md](../documentacion/01_informes/01_AUDITORIA_DATOS_CRUDOS_2026-11-12.md). Se han inventariado 1.474 JPEG en 15 sesiones, incluidas subcarpetas. El informe documenta discrepancias con las notas y límites de las reglas de los scripts descritos más abajo: sus asignaciones no equivalen a confirmación botánica ni a validación visual de identidad.

```powershell
.venv\Scripts\python.exe scripts\s04_audit_raw_dataset.py
# Otra carpeta para conservar una ejecución nueva:
.venv\Scripts\python.exe scripts\s04_audit_raw_dataset.py --output_dir data/processed/audit_raw_NUEVA_FECHA
```

`s04_audit_raw_dataset.py` lee los originales sin modificar `data/raw`. Genera inventario recursivo con SHA-256, hash de píxeles orientados, decodificación completa, EXIF anidado, cobertura provisional, notas por archivo, diferencias con el consolidado previo y candidatos de similitud. La salida predeterminada es `data/processed/audit_raw_2026-11-12/`. Las 23 Nikon de la subcarpeta del 20 de junio de 2025 quedan sin asignar; las otras etiquetas conservan su procedencia y grado de revisión. No se generan particiones ni exclusiones automáticas.

La sesión `2026-06-01_c2_r2` se marca `filename_chronology_conflict`: ordenar por nombre invierte dos bloques respecto a EXIF. La tabla `chronological_mapping_candidates.csv` ofrece una alternativa por hora para revisión de campo; no se confirma automáticamente como nueva etiqueta.

La hoja de revisión dirigida se reproduce con `.venv\Scripts\python.exe scratch\s01_audit_visual_sample.py`. Las observaciones humanas y limitaciones se recogen en el informe; no son resultados de identificación botánica automatizada.

---

## 1. `s14_label_dataset.py`

Script principal de la fase **P0 (Inventario, etiquetado y agrupación)** definida en [`03_PLANIFICACION_TFM.md`](../03_PLANIFICACION_TFM.md), [`02_FLUJO_IMAGENES_TFM.md`](../02_FLUJO_IMAGENES_TFM.md) y [`04_PROTOCOLO_ESCALA_MACETAS.md`](../04_PROTOCOLO_ESCALA_MACETAS.md).

### ¿Qué hace el script?
1. **Asignación botánica en serpentina continua**: Cruza cada captura fotográfica ordenada cronológicamente con la posición física del diseño experimental (`Fila`/`Columna`) y su especie asignada.
2. **Normalización geométrica y de escala**:
   - Asigna el diámetro exterior de referencia de la boca de la maceta (**10.0 cm en 2025**, **20.0 cm en 2026**).
   - Controla el metadato de presencia de tarjeta de referencia (`has_reference_card = True` únicamente para `2025-05-13`, `False` para todas las demás fechas).
3. **Extracción de metadatos EXIF**: Dimensiones originales, modelo de cámara (Nikon D70 / D3000), fecha/hora original, distancia focal y orientación EXIF (crucial para orientar antes de recortar o redimensionar).
4. **Integridad y trazabilidad (SHA-256)**: Calcula el hash criptográfico unívoco de cada archivo original para garantizar que no existan duplicados ni confusiones en particiones posteriores (P1).
5. **Generación de identificadores persistentes de maceta (`pot_id`)**: Permite seguir la trayectoria temporal de una misma planta/maceta a lo largo de las distintas fechas de captura sin mezclar particiones de entrenamiento y test.

---

## 2. Requisitos y Entorno Virtual

El proyecto cuenta con un entorno virtual configurado con `uv` en `.venv`.

Para ejecutar el script, asegúrate de utilizar el intérprete del entorno:

```powershell
# Desde la raíz del repositorio (C:\Users\christianr\Desktop\tfm2026)
.venv\Scripts\python.exe scripts\s14_label_dataset.py [OPCIONES]
```

Librerías principales requeridas:
* `pillow`
* `pandas`
* `openpyxl`
* `tqdm`

---

## 3. Convención de Nombres de Directorios

Cada carpeta de sesión cruda en `data/raw/` (o en discos externos) debe seguir el formato:

$$\text{\{YYYY-MM-DD\}\_\{campana\}\_\{repeticion\}}$$

### Ejemplos:
* `2025-05-13_c1_r1`: Captura del 13 de mayo de 2025, Campaña 1, Repetición 1.
* `2025-05-20_c1_r1`: Captura del 20 de mayo de 2025, Campaña 1, Repetición 1.
* `2026-06-10_c2_r2`: Captura del 10 de junio de 2026, Campaña 2, Repetición 2.

---

## 4. Diseños Experimentales y Serpentina

El script detecta automáticamente el año de la sesión a partir del nombre de la carpeta y carga el archivo de diseño correspondiente desde `exp_design/`:

### Año 2025 (`exp_design/01_2025.csv`)
* **Dimensiones**: 10 filas (F1 a F10) $\times$ 8 columnas (C1 a C8).
* **Capacidad**: **70 macetas / fotos por sesión**:
  * 20 *Amaranthus palmeri* (`P`)
  * 20 *Amaranthus hybridus* (`H`)
  * 20 *Amaranthus retroflexus* (`R`)
  * 10 *Zea mays* / Maíz (`M`)
* **Diámetro exterior de maceta**: 10.0 cm.
* **Trazado en serpentina**:
  * $C_1$ (impar): F10 $\rightarrow$ F1 (sube, 10 fotos)
  * $C_2$ (par): F1 $\rightarrow$ F10 (baja, 10 fotos)
  * $C_3$ (impar): F10 $\rightarrow$ F1 (sube, 10 fotos)
  * $C_4$ (par): F1 $\rightarrow$ F10 (baja, 10 fotos)
  * $C_5$ (impar): F10 $\rightarrow$ F1 (sube, 10 fotos)
  * $C_6$ (par): F1 $\rightarrow$ F10 (baja, 10 fotos)
  * $C_7$ (impar): F10 $\rightarrow$ F6 (sube, 5 fotos maíz; filas 1-5 vacías)
  * $C_8$ (par): F6 $\rightarrow$ F10 (baja, 5 fotos maíz; filas 1-5 vacías)

### Año 2026 (`exp_design/03_2026.csv`)
* **Dimensiones**: 26 filas (F1 a F26) $\times$ 5 columnas (C1 a C5).
* **Capacidad**: **130 macetas / fotos por sesión**:
  * 40 *Amaranthus palmeri* (`P`)
  * 40 *Amaranthus hybridus* (`H`)
  * 40 *Amaranthus retroflexus* (`R`)
  * 10 *Zea mays* / Maíz (`M`)
* **Diámetro exterior de maceta**: 20.0 cm.
* **Trazado en serpentina**:
  * $C_1$ (impar): F26 $\rightarrow$ F1 (sube, 26 fotos)
  * $C_2$ (par): F1 $\rightarrow$ F26 (baja, 26 fotos)
  * $C_3$ (impar): F26 $\rightarrow$ F1 (sube, 26 fotos)
  * $C_4$ (par): F1 $\rightarrow$ F26 (baja, 26 fotos)
  * $C_5$ (impar): F26 $\rightarrow$ F1 (sube, 26 fotos)

### Sesiones con capturas múltiples por maceta
En ciertas sesiones de campo se tomaron 2 o más fotografías por planta o se repitieron tramos:
* **`2026-05-14_c2_r1` (153 fotos para 130 macetas)**: Las columnas 1 a 4 tienen 26 fotos para 26 macetas (1:1). En la columna 5, las primeras 23 macetas (F26 a F4) se fotografiaron dos veces (lote 1: fotos 105-127; lote 2: fotos 128-150 tras una pausa de 9 min), mientras que las 3 macetas finales (F3 a F1) tienen 1 foto. Ambas capturas quedan correctamente vinculadas a la misma maceta física (`pot_id` y `posicion`).
* El sistema detecta y soporta de forma nativa estas configuraciones sin descartar imágenes ni enviarlas a macetas desconocidas.

---

## 5. Ejemplos Prácticos de Uso

### Ejemplo 1: Procesar todo `data/raw` (2025 y 2026)
Procesa automáticamente todas las carpetas disponibles y actualiza tanto los manifiestos locales como los consolidados anuales y globales:
```powershell
.venv\Scripts\python.exe scripts\s14_label_dataset.py
```

### Ejemplo 2: Procesar una única sesión específica
Ideal para etiquetar un lote nuevo recién descargado de la cámara:
```powershell
# Si la carpeta está dentro de data/raw:
.venv\Scripts\python.exe scripts\s14_label_dataset.py --session 2026-06-10_c2_r2

# Si la carpeta está en cualquier ruta externa:
.venv\Scripts\python.exe scripts\s14_label_dataset.py --session "D:\FOTOS_CAMPO\2026-06-17_c2_r2"
```

### Ejemplo 3: Procesar un directorio raíz externo completo
Si almacenas las imágenes crudas en un disco duro externo o recurso compartido:
```powershell
.venv\Scripts\python.exe scripts\s14_label_dataset.py --raw_dir "D:\TFM_DATASET\raw"
```

### Ejemplo 4: Filtrar por año de campaña
```powershell
# Procesar únicamente sesiones de 2025
.venv\Scripts\python.exe scripts\s14_label_dataset.py --year 2025

# Procesar únicamente sesiones de 2026
.venv\Scripts\python.exe scripts\s14_label_dataset.py --year 2026
```

### Ejemplo 5: Cambiar la carpeta de salida de los manifiestos
```powershell
.venv\Scripts\python.exe scripts\s14_label_dataset.py --output_dir "D:\mis_manifiestos"
```

---

## 6. Salidas Generadas

1. **Manifiestos locales por sesión**:
   - `data/raw/{sesion}/manifest.csv`
   - `data/raw/{sesion}/manifest.json`
   Permiten que cada carpeta sea autocontenida y transportable con sus propios metadatos.

2. **Manifiestos consolidados anuales**:
   - `data/processed/manifest_2025.csv` y `.json`
   - `data/processed/manifest_2026.csv` y `.json`

3. **Manifiesto consolidado general**:
   - `data/processed/manifest_all.csv` y `.json` (reúne todas las sesiones procesadas de ambos años).

---

## 7. Columnas del Manifiesto

| Columna | Tipo | Descripción |
| :--- | :---: | :--- |
| `image_id` | `str` | Identificador único de imagen (`{sesion}_{nombre_archivo}`). |
| `filename` | `str` | Nombre del archivo original (ej. `DSC_0131.JPG`). |
| `relative_path` | `str` | Ruta relativa normalizada con `/`. |
| `session_id` | `str` | Nombre de la sesión (`2026-06-10_c2_r2`). |
| `year` | `int` | Año de captura (`2025` o `2026`). |
| `date_session` | `str` | Fecha en formato `YYYY-MM-DD`. |
| `campana` | `str` | Campaña (`c1`, `c2`). |
| `repeticion` | `str` | Repetición (`r1`, `r2`). |
| `capture_order` | `int` | Número de captura en la secuencia de la sesión (1 a 70 en 2025; 1 a 130 en 2026). |
| `columna` | `str` | Columna del diseño experimental (`C1` a `C8`). |
| `fila` | `int` | Fila del diseño experimental (`1` a `26`). |
| `posicion` | `str` | Código de celda (ej. `F26C1`, `F10C8`). |
| `pot_id` | `str` | Identificador persistente de maceta para agrupamiento temporal (`POT_{año}_{rep}_{pos}`). |
| `species_code` | `str` | Código en diseño (`P`, `H`, `R`, `M`). |
| `species_scientific` | `str` | Nombre científico validado. |
| `genus` | `str` | Género taxonómico (`Amaranthus`, `Zea`). |
| `class_label` | `str` | Etiqueta de clase (`palmeri`, `hybridus`, `retroflexus`, `maize`). |
| `is_target_species` | `bool` | `True` únicamente para *Amaranthus palmeri*. |
| `is_auxiliary` | `bool` | `True` para *Zea mays* (control auxiliar de monocotiledónea). |
| `pot_diameter_exterior_cm`| `float` | Diámetro exterior nominal de la maceta (10.0 en 2025; 20.0 en 2026). |
| `has_reference_card` | `bool` | `True` solo en `2025-05-13`; `False` en el resto. |
| `sha256` | `str` | Hash SHA-256 íntegro del archivo de imagen. |
| `width`, `height` | `int` | Dimensiones en píxeles de la captura original. |
| `exif_orientation` | `int` | Etiqueta de orientación EXIF (1, 6, 8, etc.). |
| `exif_camera_make` | `str` | Fabricante de cámara (`NIKON CORPORATION`). |
| `exif_camera_model`| `str` | Modelo de cámara (`NIKON D70`, `NIKON D3000`). |
| `exif_datetime_original` | `str` | Marca temporal original grabada por la cámara. |
| `exif_focal_length_mm` | `float`| Distancia focal de la lente en milímetros. |
| `pipeline_status` | `str` | Estado en el pipeline (`raw_inventory_ok`). |

---

## 8. `s16_plot_experimental_grid.py`

Script de diagnóstico visual y control de calidad que genera un esquema gráfico en alta resolución (180 DPI) de la matriz del diseño experimental, superponiendo cada fotografía como un punto en su posición exacta de la cuadrícula y trazando la trayectoria cronológica en serpentina.

### Capacidades y Elementos del Gráfico

1. **Cuadrícula del diseño experimental**:
   - Dibuja la matriz completa según el año de campaña:
     - **2025**: 10 filas (`F1` a `F10`) $\times$ 8 columnas (`C1` a `C8`).
     - **2026**: 26 filas (`F1` a `F26`) $\times$ 5 columnas (`C1` a `C5`).
   - Cada celda se colorea según la especie planificada en el diseño experimental:
     - *Amaranthus palmeri* (`P`): Fondo coral suave (`#ffebee`), borde coral (`#e57373`), punto rojo (`#c62828`).
     - *Amaranthus hybridus* (`H`): Fondo azul suave (`#e3f2fd`), borde azul (`#64b5f6`), punto azul (`#1565c0`).
     - *Amaranthus retroflexus* (`R`): Fondo ámbar suave (`#fff3e0`), borde ámbar (`#ffb74d`), punto naranja (`#ef6c00`).
     - *Zea mays* / Maíz (`M`): Fondo verde suave (`#e8f5e9`), borde verde (`#81c784`), punto verde (`#2e7d32`).
     - **Celdas vacías (sin planta en diseño)**: Fondo gris con trama diagonal (`//`).
   - Eje Y simplificado a etiquetas compactas (`F1`, `F2`, ..., `F26`) sin rótulo redundante.
   - Nombres científicos en cursiva matemática en la leyenda oficial ($r"\it{...}"$).

2. **Puntos de captura e información individual**:
   - Cada imagen se proyecta como un marcador circular sobre su celda correspondiente.
   - En el centro del punto se indica el **número de orden cronológico de captura** (1, 2, ..., N).
   - En la parte inferior de cada punto se muestra:
     - El nombre del archivo original (ej. `DSC_0062.JPG`).
     - La hora exacta registrada en los metadatos EXIF (formato `hh:mm:ss`).

3. **Flechas direccionales de orientación EXIF**:
   - Cada captura incluye una flecha direccional azul que ilustra la orientación física de la cámara durante el disparo:
     - `↑` **O:1**: Horizontal estándar (*Landscape*).
     - `→` **O:6**: Vertical rotada 90° en sentido horario (*Portrait* derecha).
     - `←` **O:8**: Vertical rotada 90° en sentido antihorario (*Portrait* izquierda).
     - `↓` **O:3**: Invertida 180°.
   - Esta información es fundamental para anticipar correcciones geométricas y rotaciones antes de las fases de recorte y aumento sintético (P1/P2).

4. **Soporte nativo para múltiples fotos por maceta**:
   - Si una posición contiene 2 o más capturas (por re-tomas, múltiples ángulos o repeticiones de tramo):
     - Distribuye los puntos horizontalmente dentro de la celda de la maceta (`np.linspace(-0.20, 0.20, k)`).
     - Muestra una insignia morada en la esquina superior derecha (`2 fotos`, `3 fotos`, etc.).
     - Cada punto conserva sus datos independientes (su orden de disparo, su hora EXIF y su flecha de orientación).
   - **Caso de estudio `2026-05-14_c2_r1`**: Contiene 153 fotos para 130 macetas. Las columnas 1 a 4 tienen 1 foto por maceta. En la columna 5, las primeras 23 macetas (F26 a F4) se tomaron dos veces (lote inicial y repetición tras una pausa de 9 min), mientras que las 3 macetas finales (F3 a F1) tienen 1 foto. El gráfico representa con precisión las 23 celdas con doble marcador e insignia sin desajustes.

5. **Trazado en serpentina y métricas de diagnóstico**:
   - Traza una línea discontinua que une cronológicamente todos los disparos para auditar visualmente el cumplimiento del recorrido en campo.
   - **Detección de faltantes**: Si una posición planificada en el diseño carece de fotografía, se dibuja un círculo discontinuo rojo y se etiqueta como `FALTANTE`.
   - **Subtítulo con métricas de cobertura**: Indica el porcentaje de macetas cubiertas, el total de imágenes procesadas y el recuento de macetas con capturas múltiples.

6. **Fuentes de datos automáticas**:
   - Si la carpeta de la sesión ya cuenta con `manifest.csv` (generado por `s14_label_dataset.py`), lo utiliza como fuente primaria de datos.
   - Si no existe `manifest.csv`, el script analiza de forma autónoma todos los archivos `.JPG` de la sesión, extrayendo los metadatos EXIF al vuelo y aplicando el mapeo de diseño correspondiente.

---

### Argumentos de Línea de Comandos

| Argumento | Tipo | Por defecto | Descripción |
| :--- | :---: | :---: | :--- |
| `--session_dir` | `str` | `None` | Ruta al directorio de la sesión cruda a graficar (ej. `data/raw/2026-05-14_c2_r1`). |
| `--raw_dir` | `str` | `data\raw` | Directorio raíz que contiene las carpetas de sesiones crudas. |
| `--all` | `flag` | `False` | Grafica automáticamente todas las sesiones disponibles encontradas en `raw_dir`. |
| `--design_dir` | `str` | `exp_design` | Ruta a la carpeta con los archivos de diseño experimental (`01_2025.csv`, `03_2026.csv`). |
| `--output` | `str` | `None` | Ruta o nombre de archivo de salida personalizada (solo al procesar una única sesión). |

---

### Ejemplos Prácticos de Uso

```powershell
# 1. Graficar una sesión específica de 2025 (70 fotos):
.venv\Scripts\python.exe scripts\s16_plot_experimental_grid.py --session_dir "data\raw\2025-05-13_c1_r1"

# 2. Graficar una sesión estándar de 2026 (130 fotos):
.venv\Scripts\python.exe scripts\s16_plot_experimental_grid.py --session_dir "data\raw\2026-06-10_c2_r2"

# 3. Graficar una sesión con fotos múltiples (153 fotos, 23 macetas dobles):
.venv\Scripts\python.exe scripts\s16_plot_experimental_grid.py --session_dir "data\raw\2026-05-14_c2_r1"

# 4. Graficar automáticamente todas las sesiones en data/raw:
.venv\Scripts\python.exe scripts\s16_plot_experimental_grid.py --all

# 5. Graficar sesiones almacenadas en un disco o recurso externo:
.venv\Scripts\python.exe scripts\s16_plot_experimental_grid.py --all --raw_dir "D:\TFM_DATASET\raw"

# 6. Guardar la figura en una ruta o nombre personalizado:
.venv\Scripts\python.exe scripts\s16_plot_experimental_grid.py --session_dir "data\raw\2025-05-13_c1_r1" --output "mi_esquema.png"
```

---

### Salidas Generadas

* **Dentro de la carpeta de sesión**: `{session_dir}/grid_plot.png` (permite que cada carpeta de datos crudos sea autocontenida y visualizable de forma inmediata).
* **Consolidado central**: `data/processed/plots/{sesion}_grid.png` (repositorio centralizado de gráficos de auditoría para comparaciones rápidas).

---

## 9. `s35_verify_repetition_photos.py`

Script especializado de auditoría y verificación cruzada diseñado para resolver la correspondencia física real de las imágenes en sesiones incompletas o afectadas por errores de cámara (pérdida de archivos, desconexión de batería o fallos de tarjeta SD), comparándolas visualmente contra una sesión de referencia completa de la **misma campaña y repetición** (ej. `c2_r2`).

### ¿Cómo funciona la verificación?

1. **Emparejamiento por Campaña y Repetición**:
   - Identifica la campaña y repetición del dataset auditado (ej. `2026-06-12_c2_r2` pertenece a la Campaña 2, Repetición 2).
   - Localiza la sesión completa patrón tomada en fechas contiguas (ej. `2026-06-10_c2_r2`, capturada solo 2 días antes con las mismas plantas físicas).
2. **Correlación Visual Multiescala e Invariante a la Rotación**:
   - Extrae la firma morfológica y cromática de cada planta (canales RGB normalizados y canal ExG de vegetación).
   - Evalúa cada fotograma contra las 4 rotaciones ortogonales (0°, 90°, 180°, 270°) para compensar diferencias en la orientación física de disparo de la cámara (etiquetas EXIF Landscape O:1 vs Portrait O:6/O:8).
3. **Resolución Determinista de Posiciones Físicas**:
   - Determina el intervalo exacto del diseño experimental al que corresponden los fotogramas recuperados.
   - **Caso `2026-06-12_c2_r2` (48 fotos recuperadas de 130)**:
     - Las fotos `DSC_0083.JPG` a `DSC_0130.JPG` corresponden **exactamente a las capturas 83 a 130** del diseño experimental de 2026.
     - **Columna 4 (`C4`)**: 22 fotos cubiertas (desde `F5C4` hasta `F26C4`). Las primeras 4 macetas (`F1C4` a `F4C4`) se perdieron por el fallo.
     - **Columna 5 (`C5`)**: 26 fotos cubiertas (desde `F26C5` bajando hasta `F1C5`), cubriendo el 100% de la columna.
     - **Macetas Faltantes (82 macetas)**: Columnas 1, 2 y 3 completas (78 macetas) y las filas 1 a 4 de la Columna 4 (4 macetas).

---

### Argumentos de Línea de Comandos

| Argumento | Tipo | Por defecto | Descripción |
| :--- | :---: | :---: | :--- |
| `--target` | `str` | `2026-06-12_c2_r2` | Nombre o ruta de la sesión objetivo auditada. |
| `--ref` | `str` | `2026-06-10_c2_r2` | Nombre o ruta de la sesión patrón de referencia. |
| `--raw_dir` | `str` | `data\raw` | Directorio raíz de datos crudos. |
| `--design_dir` | `str` | `exp_design` | Directorio con los diseños experimentales (`03_2026.csv`). |
| `--output_dir` | `str` | `data\processed` | Directorio central de salida para informes. |
| `--no_plot` | `flag` | `False` | Desactiva la generación del gráfico visual (solo genera CSVs). |

---

### Ejemplos de Uso

```powershell
# 1. Comparación directa entre la sesión incompleta y su referencia patrón:
.venv\Scripts\python.exe scripts\s35_verify_repetition_photos.py --target 2026-06-12_c2_r2 --ref 2026-06-10_c2_r2

# 2. Ejecución rápida sin generar gráficos (solo genera manifiesto y reporte de faltantes):
.venv\Scripts\python.exe scripts\s35_verify_repetition_photos.py --target 2026-06-12_c2_r2 --no_plot
```

---

### Salidas Generadas

1. **`{session_dir}/verified_manifest.csv`**:
   - Manifiesto riguroso con cada fotografía vinculada a su posición real (`posicion`, `fila`, `columna`), especie botánica confirmada (`species_code`, `species_scientific`), orden asignado (83 a 130), correlación visual e identificador unívoco de maceta (`pot_id`).
2. **`{session_dir}/missing_pots.csv`**:
   - Catálogo exhaustivo de las macetas planificadas en el diseño que carecen de captura por el fallo de la cámara (82 registros en `2026-06-12_c2_r2`).
3. **`{session_dir}/verification_grid.png`** y copia en **`data/processed/plots/{sesion}_verification.png`**:
   - Esquema visual de alta resolución de la matriz experimental que distingue con claridad las celdas cubiertas (marcador circular sólido de especie y nombre de archivo) frente a las macetas perdidas por el fallo de la cámara (círculo rojo discontinuo con etiqueta `SIN FOTO`).


