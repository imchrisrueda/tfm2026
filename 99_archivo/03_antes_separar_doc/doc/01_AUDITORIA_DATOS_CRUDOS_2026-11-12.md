# Auditoría del dataset crudo — 12 de noviembre de 2026

> **Instantánea histórica anterior a tus respuestas.** Se conservan los resultados y las dudas tal como estaban al hacer esta auditoría. Después aclaraste el orden de captura y las correspondencias y retiraste 23 fotos repetidas: el corpus actual tiene 1.451 fotos. Las decisiones vigentes y sus resultados están en [BITACORA_METODOLOGICA.md](../BITACORA_METODOLOGICA.md); las copias actualizadas para tu revisión están en [data/verificacion_siembra](../data/verificacion_siembra/README.md). Las dudas de este documento no deben interpretarse automáticamente como asuntos todavía sin responder.

## Dictamen

El inventario completo contiene **1.474 fotografías JPEG en 15 sesiones**, con **7.184.881.936 bytes** de imágenes (7,185 GB decimales). Todas se han decodificado completamente, sin errores ni advertencias de lectura. No se han encontrado archivos idénticos por SHA-256 ni imágenes con los mismos píxeles RGB después de aplicar orientación EXIF.

**P0 todavía no puede darse por cerrado para entrenamiento.** La integridad de lectura está comprobada, pero quedan correspondencias de maceta por resolver, observaciones de campo que afectan a las etiquetas y una revisión visual y geométrica pendiente para la mayor parte del corpus. Una etiqueta derivada de la cuadrícula no demuestra que la fotografía contenga una planta viva de esa especie.

El conflicto más grave detectado en el recorrido está en **2026-06-01_c2_r2**: el orden por nombre contradice el orden EXIF. Cambiar a la hipótesis cronológica modificaría la especie asignada a **93 de sus 130 fotografías**, conservando exactamente los mismos totales de clase. Se ha marcado toda la sesión como conflictiva y se ha conservado una tabla candidata, sin confirmar automáticamente una nueva correspondencia.

El manifiesto global anterior contiene 423 fotos; le faltan **1.051 fotografías presentes en disco (71,30 % del total)**. Esta auditoría deja un inventario independiente y conserva los originales, manifiestos y gráficos anteriores.

## Alcance, fuentes y unidades

Se han recorrido recursivamente todas las sesiones de `data/raw`, incluida `2025-06-20_c1_r2/nikon_d70`. Los gráficos `grid_plot.png` y `verification_grid.png` se han clasificado como derivados, no como fotografías crudas. Los archivos auxiliares también tienen inventario y hash.

Fuentes utilizadas:

- [Notas de captura](../data/raw/notes.txt): recuentos declarados, incidencias y ausencia del prefijo de 82 fotos en la última sesión.
- [Diseño 2025](../exp_design/01_2025.csv), [detalles 2025](../exp_design/02_2025_details.csv) y [diseño 2026](../exp_design/03_2026.csv).
- [Documentación de scripts](../scripts/20_README.md), código de etiquetado, representación de cuadrículas y verificación entre sesiones.
- [Plan del TFM](../03_PLANIFICACION_TFM.md), [flujo de imágenes](../02_FLUJO_IMAGENES_TFM.md) y [protocolo de escala](../04_PROTOCOLO_ESCALA_MACETAS.md).
- Metadatos de las 1.474 fotografías y manifiestos preexistentes. Los hashes de los documentos y del código consultados quedan en `summary.json`.

La unidad del inventario es el **archivo de fotografía**. Una maceta fotografiada varias veces no son varios individuos. El identificador de maceta es una **propuesta de agrupación por año, repetición y posición**, pendiente de confirmar continuidad física y posibles trasplantes. La unidad biológica —planta o conjunto de plantas— no está resuelta para todo el dataset.

La comprobación técnica abarca el corpus completo. La inspección visual es **dirigida y limitada a 25 imágenes**, elegidas por incidencias, cámaras y candidatos de similitud; no estima la prevalencia de defectos en las demás fotografías. No se ha realizado una identificación botánica experta.

## Inventario por sesión

P: *A. palmeri*; H: *A. hybridus*; R: *A. retroflexus*; M: maíz auxiliar. Todos estos recuentos son **asignaciones provisionales por diseño**, no recuentos de plantas vivas confirmadas. «Posiciones» significa cobertura bajo esas reglas, incluidas posiciones cuya foto puede no contener vegetación.

| Sesión | Fotos disponibles | Fotos anotadas | P | H | R | M | Sin asignar | Posiciones / diseño |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025-05-13_c1_r1 | 70 | 70 | 20 | 20 | 20 | 10 | 0 | 70/70 |
| 2025-05-20_c1_r1 | 70 | 70 | 20 | 20 | 20 | 10 | 0 | 70/70 |
| 2025-05-28_c1_r1 | 70 | 70 | 20 | 20 | 20 | 10 | 0 | 70/70 |
| 2025-06-05_c1_r2 | 70 | 70 | 20 | 20 | 20 | 10 | 0 | 70/70 |
| 2025-06-12_c1_r2 | 70 | 70 | 20 | 20 | 20 | 10 | 0 | 70/70 |
| 2025-06-16_c1_r2 | 60 | 120 | 20 | 20 | 20 | 0 | 0 | 60/70 |
| 2025-06-20_c1_r2 | 83 | 70 | 20 | 20 | 20 | 0 | 23 | 60/70 |
| 2026-04-22_c2_r1 | 130 | 130 | 40 | 40 | 40 | 10 | 0 | 130/130 |
| 2026-05-06_c2_r1 | 130 | 130 | 40 | 40 | 40 | 10 | 0 | 130/130 |
| 2026-05-14_c2_r1 | 153 | 153 | 47 | 47 | 48 | 11 | 0 | 130/130 |
| 2026-06-01_c2_r2 | 130 | 130 | 40 | 40 | 40 | 10 | 0 | 130/130 |
| 2026-06-05_c2_r2 | 130 | 130 | 40 | 40 | 40 | 10 | 0 | 130/130 |
| 2026-06-08_c2_r2 | 130 | 130 | 40 | 40 | 40 | 10 | 0 | 130/130 |
| 2026-06-10_c2_r2 | 130 | 130 | 40 | 40 | 40 | 10 | 0 | 130/130 |
| 2026-06-12_c2_r2 | 48 | 48 | 15 | 14 | 15 | 4 | 0 | 48/130 |
| **Total** | **1.474** | **1.521** | **442** | **441** | **443** | **125** | **23** | **1.428/1.530** |

El total anotado no es un objetivo fiable de completitud: mezcla tomas repetidas y una sesión con dos cámaras. La diferencia neta de 47 fotos respecto a esas notas **no equivale a 47 macetas perdidas**.

En 2025 hay 493 fotos y en 2026 hay 981. Las reglas generan 400 `pot_id` distintos: 70 por cada repetición de 2025 y 130 por cada repetición de 2026. **No se han acreditado 400 macetas independientes ni 400 plantas.**

Se cubren provisionalmente 1.428 de 1.530 combinaciones de sesión y posición (93,33 %). Las 102 posiciones sin foto asignada se descomponen en 10 + 10 de las últimas dos sesiones de 2025 y 82 de la última de 2026. En junio de 2025 la interpretación depende de resolver el recorrido; el listado de faltantes no prueba por sí mismo una pérdida física.

## Integridad, cámaras y metadatos

| Comprobación | Resultado |
|---|---|
| Apertura, `verify()` y decodificación completa `load()` | 1.474/1.474 correctas; 0 advertencias |
| SHA-256 de archivo | 1.474 valores distintos |
| Hash de tamaño y píxeles RGB orientados | 1.474 valores distintos |
| Modo de imagen | 1.474 RGB |
| Fecha EXIF original | Disponible en 1.474/1.474, leyendo también el IFD EXIF anidado |
| Distancia focal EXIF | Disponible en 1.474/1.474 |
| Orientación | 1: 1.059; 3: 1; 6: 258; 8: 156 |
| Orientación distinta de 1 | 415/1.474 (28,15 %); aplicar antes de medir o recortar |
| Perfil ICC embebido | 60 fotos; otras 1.414 sin perfil embebido detectado |
| Similitud perceptual dentro de sesión | 2 pares candidatos; no duplicados confirmados |

Los hashes constituyen una referencia del estado actual. Al no existir una referencia histórica íntegra y contrastada, no demuestran que los archivos nunca hayan cambiado antes de esta auditoría. El hash de píxeles tampoco detecta recortes, conversiones con pérdida o fotografías distintas de la misma planta.

| Cámara | Fotos | Dimensiones almacenadas |
|---|---:|---|
| Nikon D70 | 433 | 3008 × 2000 |
| Nikon D3000 | 851 | 3872 × 2592 |
| Sony ILCE-6300 | 130 | 6000 × 4000 |
| iPhone SE, 2.ª generación | 60 | 3024 × 4032: 48; 4032 × 3024: 12 |

**Las 433 fotografías Nikon D70 tienen fecha EXIF del día anterior a la fecha de su carpeta.** Las otras 1.041 coinciden en el día. La asociación con la cámara es sistemática; un reloj mal configurado es una explicación posible, no demostrada. Se conservan fecha declarada de sesión y fecha EXIF original por separado, sin modificar originales ni atribuir zona horaria no acreditada. No debe calcularse la edad de las plantas mezclando ambas fechas sin una regla documentada.

Los indicadores de luminancia, contraste y varianza de bordes en miniatura se guardan como diagnóstico. **No son umbrales validados de desenfoque, exposición o aptitud morfológica** y no se han utilizado para excluir fotos.

## Incidencias y consecuencias

### 1. Manifiesto global incompleto — prioridad alta

`data/processed/manifest_all.csv` cubre cuatro sesiones y 423 imágenes (28,70 %). Las 423 rutas siguen presentes y sus hashes, dimensiones, posiciones y especies coinciden con esta auditoría; faltan otras 1.051 rutas. El problema es de cobertura, no una discrepancia de hash en esas 423 filas.

**Riesgo:** estimar tamaños de entrenamiento o balance con una fracción del corpus. **Acción:** utilizar el inventario de auditoría como referencia de existencia; construir el manifiesto de entrenamiento sólo después de resolver etiquetas y exclusiones. Evidencia: `existing_manifest_differences.csv`.

### 2. Sesión 2025-06-16: 60 fotos frente a 120 anotadas — prioridad alta

Las notas y la regla especial del etiquetador describen 60 macetas con dos tomas, sin maíz. Hay sólo **60 archivos**, no 120. La regla especial del script sólo se activa si recibe 120; con el estado actual entra en el recorrido ordinario y asigna una foto a cada una de las primeras 60 posiciones.

La cobertura de 60 macetas es por tanto **una hipótesis**, no una conclusión resuelta. Los saltos de numeración no bastan para decidir qué toma falta ni si sobrevivió una fotografía de cada maceta.

**Riesgo:** desplazamientos en especie y `pot_id` si la secuencia disponible no representa exactamente una foto por posición. **Acción:** contrastar archivos originales o registro de adquisición y sesiones contiguas; conservar las 60 imágenes con `partial_sequence_assumed` hasta resolverlo. No duplicar archivos para alcanzar 120 ni emparejarlos consecutivamente sin evidencia.

### 3. Sesión 2025-06-20: dos cámaras y subcarpeta — prioridad alta

Hay **60 JPEG iPhone en la raíz y 23 JPEG Nikon en `nikon_d70`**, en total 83, frente a 70 anotadas. El etiquetador original sólo recorre la raíz y omite las 23 Nikon. Esta auditoría las incluye y las deja sin especie y maceta asignadas.

Las 60 iPhone reciben provisionalmente las primeras 60 posiciones del diseño; no se ha acreditado con ello su correspondencia física. Las 23 Nikon no se consideran macetas nuevas ni tomas redundantes hasta cruzarlas con las iPhone. Las diez posiciones de maíz figuran sin cobertura bajo el mapeo actual, no como ausencia botánica demostrada.

**Acción:** elaborar correspondencia explícita archivo → posición → cámara para ambas adquisiciones, apoyada por observación de campo o revisión comparativa. Mantener conectadas las fotos que se confirme que pertenecen a la misma maceta.

### 4. Sesión 2026-06-12: pérdida documentada de las primeras 82 fotos — prioridad alta

Existen 48 archivos, `DSC_0083.JPG` a `DSC_0130.JPG`. Las notas dicen que faltan las primeras 82 plantas fotografiadas. Se usa esta evidencia para asignar los órdenes **83–130**, no 1–48:

- C1–C3: sin cobertura, 78 posiciones.
- C4: faltan F1–F4; se cubren F5–F26, 22 posiciones.
- C5: 26 posiciones cubiertas.

La cobertura es 48/130 (36,92 %) y la ausencia 82/130 (63,08 %). Las etiquetas por ese tramo son P=15, H=14, R=15 y M=4. El estado es `documented_missing_prefix_assignment`; la identidad botánica de cada foto sigue sin validación experta.

**Riesgo adicional del código:** el etiquetador general ignora `verified_manifest.csv` y reubicaría esta sesión desde el principio. El verificador calcula correlaciones pero asigna incondicionalmente el orden deducido del nombre. Sólo 6/48 asignaciones coinciden con el mejor emparejamiento visual de su propia comparación. Esto no refuta las notas de campo, pero impide llamar a ese resultado «verificación visual rigurosa». La correlación RGB de escenas completas puede responder al fondo y no a la identidad de la planta; el código inspeccionado tampoco implementa el canal ExG anunciado en el README.

**Acción:** conservar la asignación respaldada por las notas, integrar la excepción de forma explícita en un futuro etiquetado validado y reservar «confirmado visualmente» para una revisión real. La falta de archivos está acreditada; su causa técnica concreta no se puede reconstruir sólo con los JPEG.

### 5. Sesión 2026-05-14: tomas repetidas — prioridad media

La regla documentada representa 153 fotos de 130 posiciones: C1–C4 tienen una toma por maceta; en C5 se repiten F26–F4, 23 posiciones. Esto añade P=7, H=7, R=8 y M=1 respecto a una cuadrícula completa. No son 153 macetas ni duplicados binarios.

**Acción:** preservar ambas tomas y agruparlas con el mismo `pot_id`. El exceso de una imagen R frente a P/H en esta sesión es coherente con la repetición; no demuestra un error de balance. La inspección de un par del tramo repetido no verifica las 23 correspondencias.

### 6. Contenido problemático anotado, aunque los JPEG abran — prioridad alta

Las notas señalan **12 archivos distintos**:

| Sesión | Archivos | Observación de campo |
|---|---|---|
| 2025-05-28 | DSC_0025, DSC_0039 | Sin planta |
| 2025-06-05 | DSC_0081 | Imagen cortada |
| 2025-06-05 | DSC_0110, DSC_0143 | Planta muy pequeña / pequeña |
| 2025-06-05 | DSC_0137 | Tres plantas pequeñas |
| 2025-06-05 | DSC_0145 | Sin planta |
| 2025-06-16 | DSC_0263 | Planta seca o muerta |
| 2025-06-20 | IMG_4153, IMG_4155, IMG_4170, IMG_4182 | Planta(s) seca(s), muerta(s) y/o malla |

La hoja de revisión muestra una **discontinuidad horizontal y desplazamiento de contenido en DSC_0081**. Es una incidencia visual pese a pasar la decodificación. También permite ver tejido deteriorado, mallas y diferencias fuertes de encuadre en parte de las fotos anotadas. Las observaciones de ausencia y mortalidad se mantienen como registros de campo; una miniatura no sustituye la revisión botánica a resolución suficiente. En el ejemplo Sony `DSC04756` no se aprecia vegetación en la miniatura; se añade como candidato a revisar, sin extrapolarlo a las 130 fotos de esa sesión.

**Acción:** reservar los casos sin planta objetivo visible y la imagen con banda fuera del entrenamiento principal mientras se revisan. Mantener los demás con motivo de revisión, sin excluir automáticamente todas las plantas pequeñas. Fijar la política de plantas secas y mallas antes de seleccionar datos. No reparar tejido ni bandas mediante generación de imagen.

### 7. Similitud perceptual y fuga entre particiones — prioridad alta para P1

El cribado dHash detecta dos pares a distancia Hamming 6: `2025-06-12/DSC_0151–DSC_0161` y `2026-04-22/DSC04773–DSC04813`. La hoja de revisión muestra diferencias de contenido; **no se justifica borrarlos como duplicados**. Este cribado sólo compara dentro de sesión y no descarta tomas relacionadas, rotaciones, recortes o continuidad entre fechas.

**Acción:** realizar las particiones por grupos de maceta y sus trayectorias, no por archivo ni sesión. Los 400 identificadores nominales son una base de trabajo, pendiente de revisar identidad, continuidad y conexiones entre macetas. Mantener el maíz aparte según el plan. No se han generado particiones en esta auditoría.

### 8. Sesión 2026-06-01: orden por archivo incompatible con EXIF — prioridad crítica

Hay dos bloques cuya posición se invierte al ordenar por nombre:

| Bloque | Fotos | Intervalo EXIF | Orden del etiquetador |
|---|---:|---|---|
| DSC_0856–DSC_0953, con saltos | 95 | 12:58:38–13:15:01 | Después |
| DSC_0008–DSC_0043, con un salto | 35 | 13:30:05–13:34:38 | Antes |

La causa del cambio de numeración no está acreditada. Se observa una inversión temporal en el límite del orden lexicográfico, suficiente para poner en duda la asignación de la sesión entera. Si se acepta el EXIF y un recorrido continuo, la primera foto sería `DSC_0856` y la última `DSC_0043`. Los nombres y totales por sí solos no resuelven si hubo reinicio del contador, repetición o cambio de recorrido.

**Evidencia:** la alternativa cronológica cambia la posición de las 130 fotos y la especie de 93 (71,54 % de la sesión), sin cambiar P=40, H=40, R=40 y M=10. Un balance de clases aparentemente perfecto puede ocultar etiquetas erróneas.

**Acción:** toda la sesión recibe `filename_chronology_conflict`. `chronological_mapping_candidates.csv` conserva por archivo la posición y especie del etiquetado por nombre y la alternativa por hora. No se han sustituido las etiquetas por la alternativa. Resolver el orden con el registro de campo o una revisión de continuidad apoyada en otras sesiones antes de incorporar estas fotos a entrenamiento o de confiar en sus `pot_id`.

## Diseño, número de plantas, escala y factores de captura

El diseño 2025 contiene 70 celdas ocupadas en una matriz 10×8: 20 P, 20 H, 20 R y 10 M. El de 2026 contiene 130 celdas en 26×5: 40 P, 40 H, 40 R y 10 M. Las matrices son coherentes con los recorridos en serpentina implementados.

`02_2025_details.csv` contiene 70 valores: 30 de una planta, 30 de cuatro plantas y 10 de tres plantas. Su suma es **180 plantas nominales por cuadrícula**, únicamente si esos registros se vinculan correctamente a las 70 posiciones. El CSV carece de clave de posición, especie o sesión y no declara su orden. No se ha unido por índice ni se ha convertido en un total de plantas observadas. No hay detalle equivalente de 2026 en `exp_design`.

Los diámetros de 10 cm en 2025 y 20 cm en 2026 son referencias **nominales documentadas**, no mediciones comprobadas por fotografía. La tarjeta se espera en las 70 fotos de la primera sesión según las notas, y se ve en la foto revisada `DSC_0062`; su presencia y aptitud no se han verificado exhaustivamente. No se dispone de dimensiones de tarjeta consignadas ni de diámetros de maceta en píxeles.

Las tres especies principales aparecen, bajo el mapeo provisional, en ambos años y en las cuatro cámaras. Esto evita una asociación total especie–cámara a ese nivel, pero no descarta pistas de sesión o encuadre. Año y diámetro están completamente asociados; Sony sólo aparece el 22 de abril de 2026 e iPhone sólo el 20 de junio de 2025. Cámara, fecha y desarrollo están parcialmente ligados. El diseño 2025 también agrupa especies espacialmente, por lo que fondo, riego y posición pueden dar pistas al clasificador.

Quedan sin observación exhaustiva: estadio, visibilidad completa, número real de plantas, mezcla de especies, daño, solapamiento, calidad de referencia, tamaño de maceta en píxeles y cobertura del campo físico. La aptitud para el corpus a escala no se puede inferir del estado técnico `ok`. No se ha fijado un campo común ni producido maestros métricos.

## Límites de los scripts existentes

- `s14_label_dataset.py` ordena por nombre, aunque el README describe orden cronológico. Calcula hashes, pero no comprueba por sí mismo unicidad ni decodifica el JPEG completo. Puede marcar `raw_inventory_ok` incluso después de un error de apertura.
- Su extracción EXIF no recorre el IFD anidado y puede recuperar `DateTime` como si fuera fecha original y omitir focal. La auditoría lee expresamente `DateTimeOriginal` y focal del IFD correcto.
- No recorre subcarpetas ni integra la asignación de la sesión incompleta. No basta con ejecutarlo sin revisar reglas para obtener un manifiesto válido de todo el corpus.
- Las opciones de sesión o año regeneran los consolidados con lo procesado en esa invocación; no fusionan automáticamente todo el inventario previo. Un consolidado puede dejar de ser global.
- Los gráficos pueden usar manifiestos previos y comparten las mismas reglas de asignación. La concordancia entre gráfico y manifiesto no es una confirmación independiente del recorrido real.

Esta auditoría reutiliza las funciones de diseño y las reglas documentadas, pero **no ejecuta los comandos originales que reescriben manifiestos dentro de `raw`**. Tampoco convierte sus estados de éxito en una aceptación para modelado. No se han modificado esos scripts: los defectos quedan documentados para una corrección posterior con la correspondencia de campo resuelta.

## Condiciones para cerrar P0

1. Resolver las sesiones 2025-06-16 y 2025-06-20: número de tomas, recorrido y cruce iPhone–Nikon. Resolver además el conflicto de orden de 2026-06-01. Registrar una tabla explícita por archivo y confirmar o rectificar la continuidad de `pot_id` entre fechas.
2. Revisar las 12 incidencias anotadas y completar una evaluación visual de contenido, especie y aptitud por imagen. Separar estados de lectura, etiqueta, morfología y escala; no llamar «sin incidencias» a lo no revisado.
3. Vincular `02_2025_details.csv` mediante una clave de posición y confirmar qué número de plantas representa en cada fecha; aportar el equivalente de 2026 o mantenerlo como desconocido. Documentar germinación, mortalidad, reposiciones y trasplantes cuando proceda.
4. Documentar la regla para el desfase EXIF de Nikon D70; mantener ambas fechas. Confirmar tarjeta y maceta por imagen y medir referencias en desarrollo para P2.
5. Generar el manifiesto de uso con etiquetas confirmadas o exclusiones motivadas, grupos conservadores y reservas de maíz. Sólo entonces dimensionar C_fit, C_val, G_fit y T_real sin solapamiento de grupos.

Comprobaciones estables recomendadas para mantener el inventario: cobertura recursiva de archivos, unicidad de identificadores y hashes, decodificación completa, posición válida y especie coherente con diseño, excepciones explícitas de secuencia y ausencia de grupos compartidos al crear particiones. Los saltos de numeración y los indicadores de imagen son alertas, no causas automáticas de eliminación.

## Evidencias y reproducción

Los resultados están en [data/processed/audit_raw_2026-11-12](../data/processed/audit_raw_2026-11-12):

- [inventory.csv](../data/processed/audit_raw_2026-11-12/inventory.csv): una fila por foto, rutas, hashes, EXIF, asignación provisional, procedencia, estado y notas de campo.
- [sessions.csv](../data/processed/audit_raw_2026-11-12/sessions.csv), [missing_positions.csv](../data/processed/audit_raw_2026-11-12/missing_positions.csv) y `species_by_*.csv`: cobertura y balance provisionales, con denominadores explícitos.
- [summary.json](../data/processed/audit_raw_2026-11-12/summary.json): totales, reglas, fechas UTC de ejecución y hashes de fuentes.
- `duplicates.csv`, `near_duplicate_candidates.csv`, `existing_manifest_differences.csv`, `filename_gaps.csv`, `chronology_inversions.csv`, `chronological_mapping_candidates.csv`, `by_*.csv` y `non_image_files.csv`: controles detallados. Un archivo de controles sin filas significa que no se encontraron casos bajo esa comprobación concreta.
- `validation.json`: reconciliación independiente entre inventario, rutas y tamaños en disco, diseño experimental y hashes de las fuentes; no constituye validación botánica.
- [Hoja de revisión de 25 fotos](../data/processed/audit_raw_2026-11-12/visual_sample.jpg) y `visual_sample.csv`: muestra dirigida trazable; la inspección humana está descrita en este informe.

Desde la raíz del repositorio:

```powershell
.venv\Scripts\python.exe scripts\s04_audit_raw_dataset.py
.venv\Scripts\python.exe scratch\s01_audit_visual_sample.py
.venv\Scripts\python.exe scratch\s06_validate_raw_audit.py
```

El [script de auditoría](../scripts/s04_audit_raw_dataset.py) sólo lee `data/raw` y escribe en la carpeta de salida. Para conservar ejecuciones futuras por separado, usar `--output_dir data/processed/audit_raw_FECHA`. El inventario conserva explícitamente las asignaciones inciertas; **no es todavía una lista de imágenes aprobadas para entrenar**.
