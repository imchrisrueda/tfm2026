# Bitácora metodológica del TFM y del futuro artículo científico

Iniciada el 12 de noviembre de 2026 a petición del investigador. Recoge las decisiones, lo que se hace con ellas y los resultados obtenidos. Las entradas iniciales reconstruyen lo ya realizado a partir de los archivos y de la conversación; no implican que esta bitácora existiera antes.

## Cómo mantener este registro

Cada nueva decisión se registra con un identificador, fecha, motivo, fuente, alcance, acción y resultado. Si todavía no se ha ejecutado o validado, se indica expresamente. Las rectificaciones se añaden con referencia a la entrada anterior: no se borra la historia para hacerla coincidir con el resultado final.

Las declaraciones del investigador sobre adquisición y siembra son información de campo. La coincidencia de un archivo con una regla de ordenación es una comprobación técnica. La identidad de una planta, la utilidad de un método y el rendimiento de un modelo requieren sus propias comprobaciones. Estas evidencias no se intercambian entre sí.

Fuentes principales: [plan del TFM](PLANIFICACION_TFM.md), [auditoría inicial](doc/AUDITORIA_DATOS_CRUDOS_2026-11-12.md), [respuestas del investigador](data/processed/audit_raw_2026-11-12/dudas.md), diseños de [2025](exp_design/2025.csv) y [2026](exp_design/2026.csv), y [número de plantas sembradas en 2025](exp_design/2025_details.csv). La aclaración de que la planta única corresponde a 2026 se recibió en la conversación después de leer las respuestas.

## Registro de decisiones y resultados

### M001 · 2026-11-12 · Alcance científico de partida

**Antecedente:** el plan integrado está fechado el 10 de noviembre de 2026. Se registra aquí retrospectivamente como contexto.

**Decisión:** trabajar con tres especies reales de Amaranthus para clasificación y generar escenas de *A. palmeri*. El maíz queda como material auxiliar. Se prevén ConvNeXt-Tiny, BioCLIP, tres entrenamientos LoRA con semillas distintas y evaluación experta y geométrica. Las fotos relacionadas por maceta y plantas deben mantenerse en el mismo grupo al preparar entrenamiento y evaluación.

**Fuente:** `PLANIFICACION_TFM.md` y sus anexos.

**Resultado y límite:** es el diseño previsto. Esta entrada no acredita entrenamiento, generación, particiones finales ni evaluación ya ejecutados. Las decisiones posteriores sobre generación de la planta y uso de fondos se registran en M013.

### M002 · 2026-11-12 · Inventario y auditoría técnica inicial

**Motivo:** conocer el corpus disponible antes de preparar datos para modelado.

**Acción realizada:** recorrido recursivo de `data/raw`, inventario de fotografías y auxiliares, SHA-256 de archivos, decodificación completa, extracción de EXIF incluido su directorio anidado, hash de píxeles RGB orientados, comparación con el manifiesto previo y comprobaciones de cobertura y orden. Se inspeccionaron visualmente 25 imágenes seleccionadas por incidencias y ejemplos de cámaras; no fue una muestra aleatoria ni una revisión visual exhaustiva.

**Resultado observado en ese momento:** 1.474 JPEG en 15 sesiones, 7.184.881.936 bytes, cero fallos de lectura y cero duplicados exactos de archivo o de píxeles orientados. El manifiesto global previo sólo cubría 423 fotos y omitía otras 1.051 existentes. Se detectaron 23 Nikon en una subcarpeta, discrepancias con notas de campo y un conflicto entre orden por nombre y hora. Se completaron 46 comprobaciones de reconciliación.

**Evidencia:** [carpeta de auditoría](data/processed/audit_raw_2026-11-12), `summary.json`, `inventory.csv` y `validation.json`; código en `scripts/audit_raw_dataset.py` y `scratch/validate_raw_audit.py`.

**Límite:** los resultados describen aquella instantánea. Las etiquetas eran provisionales y no se habían confirmado mirando cada planta. La retirada posterior de 23 fotos por el investigador cambia el corpus actual; no invalida ni debe ocultar aquel recuento histórico (M006). No se deben reutilizar los controles de aquella instantánea como si se acabaran de ejecutar sobre el nuevo corpus.

### M003 · 2026-11-12 · Orden de captura del 1 de junio de 2026

**Problema:** el script ordenaba por nombre. En `2026-06-01_c2_r2` colocaba las 35 fotos `DSC_0008–DSC_0043` antes que las 95 fotos `DSC_0856–DSC_0953`, pese a que las horas indicaban el orden inverso.

**Confirmación del investigador:** primero se capturó el bloque 0856–0953 y después el bloque 0008–0043; el recorrido siguió siendo serpentina. Debe usarse la hora ascendente.

**Decisión:** ordenar las fotografías de cada adquisición por fecha/hora original de la cámara antes de asignar posiciones del diseño. Mantener explícitas las excepciones por selección, cámaras y sesión incompleta. Ante horas ausentes o empatadas que impidan resolver el recorrido, no atribuir certeza a un desempate por nombre.

**Resultado conocido:** la alternativa cronológica calculada en la auditoría cambia las posiciones de las 130 fotos y la especie asignada de 93; conserva P=40, H=40, R=40 y M=10. La respuesta de campo resuelve cuál es el orden que se debe aplicar. La confirmación visual de la siembra sigue pendiente, en particular en las posiciones indicadas en M007.

**Implementación:** se aplicará en las copias para revisión y su manifiesto; el resultado de ejecución se registrará en M015. No se da por corregido con ello el antiguo `manifest_all.csv` ni el etiquetador anterior.

### M004 · 2026-11-12 · Selección de fotos del 16 de junio de 2025

**Problema:** las notas describían 120 fotos con dos tomas por planta, mientras que en `2025-06-16_c1_r2` había 60 archivos.

**Confirmación del investigador:** se seleccionaron 60 fotografías porque las tomas repetidas mantenían exactamente la misma posición. Las notas ya indicaban ausencia de maíz.

**Decisión:** tratar los 60 archivos actuales como la selección de una toma por cada posición de Amaranthus, siguiendo la serpentina. No tratarlos como una pérdida accidental de 60 archivos ni emparejar las fotos actuales de dos en dos. La interpretación del recorrido se apoya en la respuesta y en la secuencia documentada; se ofrecerá completa para revisión visual.

**Resultado actual:** 60 archivos disponibles para 60 posiciones previstas de Amaranthus. La selección original fue realizada por el investigador, no por esta auditoría. Se conserva la discrepancia histórica de las notas y se registra la aclaración en lugar de inventar archivos faltantes.

### M005 · 2026-11-12 · Correspondencia entre cámaras el 20 de junio de 2025

**Confirmación del investigador:** las 60 fotos de iPhone cubren todas las posiciones de Amaranthus, sin maíz. Las 23 Nikon corresponden a las primeras 23 posiciones del mismo recorrido en serpentina.

**Decisión:** ordenar cada adquisición por separado y asignar las iPhone a las primeras 60 posiciones y las Nikon a las primeras 23. Conservar la subcarpeta Nikon y vincular las fotos de ambas cámaras a la misma maceta cuando corresponda.

**Resultado esperado de la asignación:** 83 fotos, 60 posiciones distintas y 23 posiciones con dos cámaras. Las Nikon dejan de estar sin asignar por falta de correspondencia declarada. No son 23 macetas nuevas ni 23 duplicados exactos. El resultado comprobado y los recuentos por especie se registrarán en M015.

### M006 · 2026-11-12 · Rectificación de repeticiones del 14 de mayo de 2026

**Confirmación del investigador:** en `2026-05-14_c2_r1` debe pasarse de `DSC_0783` a `DSC_0809`; las intermedias repiten la secuencia. El investigador indicó que las retiraría manualmente.

**Resultado observado al leer las respuestas:** ya quedan 130 JPEG en esa sesión y no están los archivos del intervalo intermedio. Frente a la instantánea inicial de 153, se han retirado 23 fotos. El total actual de `data/raw` pasa de 1.474 a 1.451 JPEG. Se comprobarán los nombres exactos retirados contra el inventario histórico al preparar las copias.

**Decisión:** asignar las 130 fotos conservadas al recorrido único de 130 posiciones. Esta regla **sustituye** la interpretación inicial de dos lotes de 23 posiciones en C5 recogida en la auditoría y en el script anterior. No volver a aplicar esa interpretación ni dar por confirmadas sus etiquetas para las tomas retiradas.

**Límite:** la retirada de originales la efectuó el investigador. No se ha comprobado si conserva una copia en otro lugar. No se afirmará que todo el corpus inicial sigue íntegro en `raw`. Las copias de verificación conservarán el contenido de los archivos actualmente disponibles.

### M007 · 2026-11-12 · Verificación visual de la siembra

**Solicitud del investigador:** copiar nuevamente todos los datasets a `data/verificacion_siembra` y añadir al nombre de cada imagen la especie prevista por el diseño. Expresa dudas en `c2_r2` para `C1F26` y `C4F4`; puede haber más casos.

**Decisión:** generar copias independientes, sin alterar píxeles ni metadatos de las fotos de origen. El nombre incluirá el orden asignado, la especie prevista, la posición y el nombre original. Se normaliza únicamente la notación de posiciones a `F26C1` y `F4C4`. Marcar esas posiciones para revisión en todas las sesiones disponibles de `c2_r2`, sin cambiar su especie por suposición.

**Resultado pendiente:** comprobación visual por el investigador y registro de cualquier corrección en una tabla que conserve etiqueta de diseño, especie observada, comentario y estado de revisión. No se considerará aprobada una foto por el simple hecho de estar copiada o renombrada. La ejecución y sus verificaciones se registrarán en M015.

### M008 · 2026-11-12 · Continuidad de macetas y plantas

**Confirmación del investigador:** dentro de cada campaña y repetición las fotografías entre fechas corresponden a las mismas macetas y plantas.

**Decisión:** conservar la agrupación temporal por campaña, repetición y posición. Las fotos de distintas fechas o cámaras de esa maceta pertenecen al mismo grupo para futuras particiones.

**Resultado:** la continuidad dentro de cada campaña/repetición pasa de hipótesis a información declarada de campo. Esto no prueba por sí solo la independencia entre repeticiones ni descarta conexiones por trasplante entre ellas; esa independencia no se atribuirá sin documentación. No se han creado todavía particiones de entrenamiento o evaluación.

### M009 · 2026-11-12 · Número de plantas: siembra y presencia

**Confirmación del investigador:** las filas de `2025_details.csv` siguen la serpentina y contienen el número de plantas sembradas. Esta información sólo se registró así en 2025. Ante una frase inicialmente ambigua, aclaró después en la conversación: **en 2026 hay una planta por maceta**.

**Decisión:** relacionar las 70 filas de detalles de 2025 con las 70 posiciones del diseño por orden de serpentina. Registrar ese dato como número sembrado, no como número de plantas vivas o visibles en cada fecha. En 2026 registrar una planta nominal por maceta, según declaración del investigador; no convertirlo en una observación visual para fotos sin planta o con mortalidad.

**Resultado documental:** los detalles de 2025 suman 180 plantas sembradas por cuadrícula completa (30 posiciones con una, 30 con cuatro y 10 con tres). No son 180 plantas observadas en cada sesión ni se deben sumar entre fechas como individuos nuevos. La aclaración sobre 2026 sustituye la segunda mención a «2025» de la respuesta 6, sin modificar el texto original del investigador.

### M010 · 2026-11-12 · Fecha de sesión y hora de cámara

**Confirmación del investigador:** mantener como fecha real la de la carpeta. La Nikon D70 pudo tener el calendario incorrecto; considera que la hora probablemente es correcta.

**Decisión:** utilizar la fecha de carpeta como fecha de sesión y conservar por separado fecha y hora EXIF originales. Ordenar dentro de cada adquisición por la hora registrada, con las limitaciones anteriores. No modificar los EXIF ni afirmar que el fallo del calendario se ha diagnosticado definitivamente.

**Resultado observado:** en la instantánea inicial las 433 Nikon D70 tenían un día menos en EXIF; las otras 1.041 fotos coincidían con la fecha de carpeta. La regla permite documentar las fechas de sesión sin ocultar la discrepancia de origen.

### M011 · 2026-11-12 · Referencia para estimar tamaños

**Decisión del investigador:** usar por ahora el diámetro de la maceta para las estimaciones. La tarjeta es un pósit común; no se adoptan unas dimensiones por búsqueda genérica, ya que el formato exacto no está identificado y no será la referencia elegida ahora.

**Aplicación:** conservar 10 cm en 2025 y 20 cm en 2026 como diámetros exteriores documentados. Medir el borde exterior en las fotografías antes de calcular una escala; conservar la orientación correcta y el campo físico común previsto en el protocolo.

**Resultado y límite:** referencia elegida, todavía sin medición geométrica exhaustiva ni escala validada por imagen. No se ha fijado un nuevo campo de recorte ni demostrado exactitud tridimensional de las plantas.

### M012 · 2026-11-12 · Exclusiones de entrenamiento y conservación de incidencias

**Decisión del investigador:** no entrenar el modelo para aprender plantas secas o muertas. La imagen con banda debe marcarse, registrarse y no usarse para entrenamiento.

**Aplicación:** registrar `2025-06-05_c1_r2/DSC_0081.JPG` como excluida del entrenamiento por banda/discontinuidad visual, aunque el archivo se decodifique. Las cinco fotos anotadas con plantas secas o muertas y las tres anotadas sin planta se mantienen fuera de los ejemplos positivos del entrenamiento principal mientras se revisan. No excluir una imagen sólo porque la planta sea pequeña. Conservar todos esos archivos en las copias de verificación, con su motivo separado de la etiqueta de especie de diseño.

**Resultado y límite:** criterio decidido y anotaciones de campo identificadas; no se ha entrenado ningún modelo con esta selección. Una imagen excluida de entrenamiento no se considera automáticamente un fondo apto para generación. Su posible uso auxiliar requiere revisar contenido y definir el procedimiento (M013).

### M013 · 2026-11-12 · Objetivo de generar la planta sobre un fondo

**Propuesta del investigador:** las fotos con suelo y maceta podrían servir como fondo sobre el que generar Amaranthus. Se desea que el modelo represente la forma característica de la planta, sin que el objetivo sea aprender el suelo o la maceta.

**Decisión actual:** registrar ese objetivo y reservar los posibles fondos como material auxiliar, separado de los ejemplos positivos de planta sana. No incorporar todavía un algoritmo nuevo ni dar por elegido un método de máscaras, composición o edición localizada.

**Resultado pendiente:** definir y probar cómo generar sólo la región vegetal, cómo conservar escala y referencias, y cómo comprobar que el resultado no depende indebidamente del fondo. El entrenamiento sobre escenas completas no garantiza por sí mismo que el modelo aprenda únicamente la planta. No hay resultados experimentales de esta propuesta ni sustituye automáticamente el protocolo de generación del plan.

### M014 · 2026-11-12 · Trazabilidad de la preparación para revisión

**Decisión de implementación:** conservar la auditoría inicial como evidencia histórica y generar una nueva tabla para las copias actuales. Comparar el contenido actual con su inventario, registrar los archivos que ya no están y comprobar por SHA-256 que cada copia contiene exactamente los mismos bytes que su origen. Registrar la procedencia de las respuestas y de los diseños utilizados.

**Estado inicial de la acción:** `data/verificacion_siembra` existe y está vacía. No se sobrescribirán revisiones visuales ya rellenadas en ejecuciones posteriores. Se añadirá un script reproducible para preparar las copias y una tabla de revisión editable.

**Resultado de ejecución:** pendiente al crear esta entrada; se añadirá a continuación como M015, con recuentos reales, archivos de salida y comprobaciones. Las decisiones futuras de preparación, entrenamiento, evaluación y corrección de etiquetas se incorporarán a esta misma bitácora.

### M015 · 2026-11-12 · Cambio de archivo detectado antes de completar las copias

**Resultado del primer intento:** el control de integridad detectó que `2025-06-20_c1_r2/nikon_d70/DSC_0380.JPG` ya no coincide con el archivo de la auditoría inicial: pasó de 3.215.514 a 3.212.096 bytes y cambió su SHA-256. No se dio la ejecución por terminada ni se afirmó que todas las copias coincidieran con la instantánea antigua. En ese momento había 476 copias completas y una copia temporal, sin cambios efectuados por este proceso en `raw`.

**Decisión:** calcular una referencia actual de cada archivo antes de copiar, comparar los cambios con la auditoría histórica y, para los archivos modificados, comprobar también los píxeles orientados y la disponibilidad de EXIF original. Conservar las dos referencias y no atribuir la modificación a una causa no observada. Las copias deben coincidir con los archivos actuales; no es correcto forzarlos a coincidir con una versión histórica que ya no está disponible.

**Acción:** adaptar la preparación para registrar los cambios de origen y reanudar copias completas o temporales sólo cuando sus bytes coincidan con la referencia actual. Si falta una fecha original en un archivo cambiado, conservar explícitamente como fuente alternativa el EXIF registrado en la auditoría inicial, sin presentarlo como una lectura actual.

**Resultado final de la preparación:** se añadirá en la siguiente entrada tras comprobar la ejecución. Esta entrada amplía M014 y conserva el incidente en lugar de ocultarlo al reintentar.

### M016 · 2026-11-12 · Preparación completada y comprobada

**Acción ejecutada:** `scripts/prepare_sowing_verification.py`, seguida de la reconciliación independiente `scratch/validate_sowing_verification.py`. La preparación completada consta en `summary.json` entre 16:51:13 y 16:51:36 UTC. La validación independiente tiene su propia fecha de finalización en `validation.json`.

**Resultado:** se han preparado **1.451 copias de las 15 sesiones**, con un total de **7.083.339.707 bytes**, en [data/verificacion_siembra](data/verificacion_siembra). Cada nombre contiene orden de diseño, especie esperada, posición y nombre original. Se han contrastado nuevamente por SHA-256 los 1.451 originales actuales y las 1.451 copias: todos coinciden con la referencia actual registrada. Hay 1.451 hashes distintos y no quedan copias temporales. Las **26 comprobaciones independientes** han resultado correctas.

| Especie esperada según diseño | Fotografías actuales |
|---|---:|
| *Amaranthus palmeri* | 438 |
| *Amaranthus hybridus* | 444 |
| *Amaranthus retroflexus* | 445 |
| *Zea mays* | 124 |
| **Total** | **1.451** |

**Comprobaciones de las decisiones:**

- El 1 de junio de 2026 comienza por `DSC_0856` y termina por `DSC_0043`. Se han aplicado las 93 reasignaciones de especie derivadas del orden confirmado, conservando la etiqueta histórica en otra columna.
- El 16 de junio de 2025 se representan las 60 posiciones de Amaranthus seleccionadas, sin maíz.
- El 20 de junio de 2025 hay 83 fotos para 60 posiciones; las 23 Nikon comparten exactamente los identificadores de las primeras 23 macetas de las iPhone. En las Nikon se asignan 3 P, 10 H y 10 R según diseño.
- El 14 de mayo de 2026 contiene 130 fotos y se verifica el paso `DSC_0783` → `DSC_0809`. La comparación histórica identifica 23 retiradas: `DSC_0785–DSC_0795` y `DSC_0797–DSC_0808`. Los nombres exactos constan en `removed_since_initial_audit.csv`; no se atribuye una retirada a nombres que ya faltaban en la instantánea anterior.
- Se señalan **8 fotos prioritarias** para las posiciones `F26C1` y `F4C4` de las cuatro sesiones completas de `c2_r2`. No hay fotos de esas posiciones en la sesión incompleta del 12 de junio, porque faltaba ese tramo.
- Se marcan **9 exclusiones del entrenamiento principal**: una imagen con banda, tres anotadas sin planta y cinco con plantas secas o muertas. Permanecen en la carpeta para revisión, sin borrar originales. Las demás no quedan automáticamente aprobadas para entrenar.
- No hay empates de hora de captura dentro de las adquisiciones actuales. Los valores de plantas sembradas de 2025 se vinculan por serpentina; se registra una planta nominal por maceta en 2026. El número observado de plantas vivas queda sin rellenar.

**Cambio de origen detectado (cierre de M015):** sólo `2025-06-20_c1_r2/nikon_d70/DSC_0380.JPG` cambia respecto a los archivos que siguen presentes desde la auditoría. Su EXIF original sigue disponible y mantiene la hora registrada. También cambia su hash de píxeles RGB tras orientación: la imagen decodificada ya no es exactamente igual a la registrada. El hash **no identifica la causa, la magnitud visual del cambio ni demuestra corrupción**. No se dispone aquí del archivo antiguo para una comparación visual directa. Se copia y verifica la versión actual, conservando el incidente para revisión.

**Evidencias entregadas:** [instrucciones para revisar](data/verificacion_siembra/README.md), [manifiesto actual](data/verificacion_siembra/manifest.csv), [tabla editable de revisión](data/verificacion_siembra/revision_visual.csv), [fotos prioritarias](data/verificacion_siembra/revisar_primero.csv), [resumen de ejecución](data/verificacion_siembra/summary.json), [validación](data/verificacion_siembra/validation.json), [cambios de archivos de origen](data/verificacion_siembra/source_changes_since_initial_audit.csv) y [retiradas respecto a la auditoría](data/verificacion_siembra/removed_since_initial_audit.csv).

**Límites del resultado:** cero revisiones visuales completadas en la tabla al crearla. La especie es la esperada por diseño y orden de captura confirmados, no una identificación botánica ya validada. Los manifiestos históricos y los antiguos scripts de etiquetado no se han sustituido; la tabla de esta preparación incorpora las aclaraciones actuales. No se han entrenado modelos, generado imágenes ni medido resultados de clasificación o generación.

### M017 · 2026-11-12 · Continuidad del registro metodológico

**Solicitud:** registrar aquí cualquier decisión que se tome y su resultado para documentar después el artículo.

**Acción realizada:** se crea `AGENTS.md` en la raíz con la instrucción de consultar esta bitácora antes de cambios metodológicos, registrar cada decisión con su fuente y resultado y conservar rectificaciones y límites. Se enlaza esta bitácora desde las instrucciones de revisión. Se añade a la cabecera de la auditoría inicial un aviso de que es histórica y un enlace al estado actual, conservando su cuerpo y sus recuentos originales.

**Resultado:** queda establecido un registro único de decisiones. Las futuras correcciones de siembra deben conservar la especie esperada originalmente, la revisión del investigador, la nueva etiqueta cuando corresponda y el alcance temporal de la corrección. Los resultados de experimentos futuros se añadirán cuando se ejecuten, sin anticiparlos.

### M018 · 2026-11-12 · Corrección de identidad por revisión de la siembra en C2R2

**Confirmación del investigador:** tras revisar C2R2, las plantas de las dos posiciones señaladas son *Amaranthus palmeri*. Atribuye la discrepancia a un error con la semilla. La confirmación se recibe en la conversación; no se presenta como resultado de identificación molecular ni de un panel experto independiente.

**Decisión:** corregir de H (*A. hybridus*, especie prevista en el diseño) a P (*A. palmeri*) las posiciones `F26C1` y `F4C4`, exclusivamente en 2026, campaña c2, repetición r2. Aplicar la corrección a todas sus fotos disponibles entre fechas y cámaras por la continuidad física declarada en M008. No convertir todo C2R2 a palmeri ni cambiar esas posiciones de otras repeticiones. Mantener los identificadores de maceta y grupo.

**Trazabilidad:** conservar separadamente la especie del diseño y la especie de trabajo, la fuente de confirmación, la causa declarada y la fecha. Las dos reglas se guardan en `exp_design/species_corrections.csv` (`SC001`, `SC002`). Registrar las ocho fotos existentes como correcciones confirmadas por el investigador en la tabla de revisión, sin dar por revisadas automáticamente las demás. No renombrar las copias que ya revisó: sus nombres conservan la expectativa inicial del diseño.

**Acción prevista:** conformar `manifest_2025`, `manifest_2026` y `manifest_all` en CSV y JSON, completos para el corpus actual, con metadatos técnicos actuales, grupos, siembra, referencias geométricas, correcciones y exclusiones. Conservar una versión de los seis consolidados anteriores antes de sustituirlos. Los datos todavía no medidos o no observados se dejarán vacíos con su estado correspondiente, sin inventar medidas ni particiones.

**Resultado pendiente:** se añadirá una entrada de cierre tras ejecutar y comprobar la construcción de los manifiestos.

### M019 · 2026-11-12 · Manifiestos completos de 2025, 2026 y del conjunto

**Acción ejecutada:** se crea y ejecuta `scripts/build_dataset_manifests.py`. La construcción `20261112T172655810500Z` se realizó entre 17:26:55 y 17:27:05 UTC. Se comprobaron los bytes y metadatos actuales de los originales y se incorporó la adquisición ya conciliada. La decodificación completa previa se reutiliza sólo cuando el SHA-256 del archivo es idéntico; el archivo cambiado respecto a la auditoría se decodificó nuevamente.

**Resultado:** se han sustituido los seis consolidados CSV/JSON por versiones completas: **493 fotos de 2025**, **958 de 2026** y **1.451 en conjunto**, con **117 campos por fotografía**. Se preservaron los seis archivos anteriores y la tabla de revisión previa en `data/processed/manifest_versions/20261112T172655810500Z/` antes de escribir los nuevos. Los originales y las fotografías de verificación no se han modificado.

| Especie de trabajo tras la revisión | 2025 | 2026 | Conjunto |
|---|---:|---:|---:|
| *Amaranthus palmeri* | 143 | 303 | 446 |
| *Amaranthus hybridus* | 150 | 286 | 436 |
| *Amaranthus retroflexus* | 150 | 295 | 445 |
| *Zea mays* | 50 | 74 | 124 |
| **Total de fotografías** | **493** | **958** | **1.451** |

**Aplicación de M018:** ocho fotografías de dos grupos físicos cambian de hybridus a palmeri, manteniendo los identificadores de maceta. Hay cuatro fotos por posición en las sesiones del 1, 5, 8 y 10 de junio de 2026; esas posiciones faltan en la sesión incompleta del día 12. Las ocho revisiones se registran como `corrected`, con palmeri como especie observada y referencia a la confirmación del investigador. No se dan por confirmadas individualmente otras fotografías. Los nombres de las copias conservan hybridus como expectativa histórica de diseño, mientras que los campos `species_*` del manifiesto vigente contienen palmeri para esos casos. No se modifica la cuadrícula original para ocultar la discrepancia de siembra.

**Contenido incorporado:** identificación y rutas; especie de diseño y de trabajo; fuente y alcance de las correcciones; orden de adquisición y posición; continuidad de macetas y grupo para futuras particiones; número sembrado en 2025 y nominal en 2026; notas de campo, exclusiones y candidaturas; diámetro nominal de referencia y estado geométrico; dimensiones, orientación, cámaras, EXIF, perfil de color, hashes actuales e históricos y estados de procesado.

**Resultados de selección preliminar:** se mantienen las nueve exclusiones y las 124 fotos de maíz auxiliar. Hay **1.319 candidatas para clasificación** y **440 palmeri candidatas para LoRA**, antes de comprobar geometría y asignar reservas por grupo. Una foto de maíz también está entre las nueve exclusiones: estos recuentos se solapan y no son sumables como categorías disjuntas. No son tamaños finales de entrenamiento ni demuestran que las imágenes ya cumplan todos los criterios del plan.

**Datos no inventados:** quedan vacíos los recuentos observados de plantas, identificadores individuales de planta, estadios sin observación, centros y diámetros en píxeles, escala calculada, campo común y rutas de maestros. Las particiones figuran como `unassigned`. La tarjeta tiene presencia esperada por notas, sin simular una observación exhaustiva. La continuidad entre fechas está declarada; la independencia entre repeticiones sigue sin documentación adicional específica.

**Verificación:** `scratch/validate_final_manifests.py` completa **54 comprobaciones correctas**. Se verifica por SHA-256 cada uno de los 1.451 originales, la cobertura recursiva exacta, la igualdad de todos los valores CSV/JSON, la igualdad entre el conjunto y sus subconjuntos anuales, las reglas limitadas a las dos macetas indicadas, la coherencia taxonómica por grupo, las exclusiones, las fuentes y las copias de versiones previas. No hay nuevos cambios de archivos respecto a la preparación de verificación. El incidente histórico de `DSC_0380.JPG` sigue registrado, sin atribuirle una causa.

**Evidencias:** [documentación de campos y uso](data/processed/README_manifiestos.md), [2025](data/processed/manifest_2025.csv), [2026](data/processed/manifest_2026.csv), [conjunto](data/processed/manifest_all.csv), sus JSON equivalentes, [ocho correcciones](data/processed/manifest_label_corrections.csv), [exclusiones](data/processed/manifest_exclusions.csv), [resumen de construcción](data/processed/manifest_build_summary.json), [diccionario de estructura](data/processed/manifest_schema.json) y [validación independiente](data/processed/manifest_validation.json).

**Documentación para usos posteriores:** se indica en `AGENTS.md` y en la documentación de scripts que los consolidados se regeneran con el nuevo constructor y el archivo explícito de correcciones. Los antiguos manifiestos locales de `raw` y los scripts que sólo usan el diseño no se presentan como fuente de etiquetas vigente. Se actualiza el texto metodológico provisional de esta bitácora para incorporar la corrección, conservando las entradas históricas anteriores.

### M020 · 2026-11-12 · Comprobación de preparación de datos para clasificador y generación

**Solicitud:** verificar si se puede comenzar el clasificador inicial y alguna prueba de generación. Durante la revisión, el investigador acotó expresamente el alcance a los datos; DRAGO se tratará más adelante. El dictamen final se limita a preparación de datos y no certifica disponibilidad de ejecución ni acceso a modelos.

**Acciones ejecutadas:** nueva ejecución de `scratch/validate_final_manifests.py` y creación y ejecución de `scratch/check_data_readiness.py`. Se contrastaron originales y manifiestos, candidaturas, grupos, correcciones, exclusiones, particiones, medidas geométricas, maestros y disponibilidad de leyendas o anotaciones de entrenamiento en `data`. La comprobación del perfil consta en `data_readiness.json` a las 19:14:09 UTC.

**Resultados observados:** las 54 comprobaciones de integridad vuelven a pasar y los 1.451 originales coinciden con los hashes de los manifiestos. Las candidatas del clasificador son 440 palmeri de 122 grupos, 434 hybridus de 118 grupos y 445 retroflexus de 120 grupos: **1.319 fotografías y 360 grupos**. Hay 440 candidatas LoRA de los mismos 122 grupos palmeri. Las nueve exclusiones y las ocho correcciones de especie están registradas; las dos dudas iniciales de siembra no siguen abiertas.

**Carencias comprobadas:** ninguna fila tiene partición asignada; ninguna tiene centro y diámetro de maceta medidos; no hay maestros enlazados, campo físico común fijado, estadio ni número observado de plantas en los manifiestos. No se encontraron columnas de caption ni archivos de leyendas, máscaras o configuraciones YAML de entrenamiento en `data`. El diámetro nominal sí consta en todas las filas. La incidencia de cambio de píxeles de `DSC_0380.JPG` sigue registrada.

**Dictamen:** existe base de datos para implementar el clasificador y preparar un piloto; todavía no están terminadas las entradas para entrenar según el protocolo. Es prioritario asignar por grupos C_fit, C_val, G_fit y T_real, manteniendo maíz aparte. Las candidaturas actuales de clasificador y LoRA se solapan en las 440 palmeri: no representan dos reservas independientes. Antes de entrenar, repartir sus grupos entre funciones y definir/preparar el preprocesado; para el piloto LoRA, preparar además imágenes y leyendas factuales del lote elegido.

**Distinciones metodológicas:** no se exige anotar todos los estadios ni máscaras de todo el corpus para implementar el clasificador o un piloto convencional de escenas. Los atributos desconocidos no se inventarán en captions. La validación de escala del protocolo requiere medición y campo físico común; un ensayo técnico provisional no la demuestra. Generar sólo la planta sobre un fondo sigue siendo una propuesta cuyo procedimiento se debe definir y probar, no una capacidad garantizada por entrenar escenas completas. Una prueba sin adaptación con un modelo base no está bloqueada por la preparación de este dataset, pero no demuestra aprendizaje del corpus ni fidelidad de escala.

**Resultado entregado:** [estado de datos para modelado](data/processed/estado_datos_modelado.md), [perfil de comprobación](data/processed/data_readiness.json) y [capacidad por estratos de grupos](data/processed/data_readiness_groups.csv). Se recomienda cerrar primero las reservas por grupos y un lote de desarrollo para el preprocesado. No se han creado particiones, cambiado datos ni etiquetas, fijado porcentajes, preparado maestros, elegido una técnica de edición localizada o ejecutado entrenamientos/generaciones en esta comprobación.

### M021 · 2026-11-12 · Lista numerada de seguimiento hasta la entrega

**Solicitud del investigador:** disponer de los pasos numerados en un Markdown llamado `tasks`, para marcar lo completado y lo pendiente.

**Decisión y acción:** se crea `tasks.md` en la raíz, con 60 tareas numeradas y casillas, agrupadas según P0–P8 y un bloque futuro de preparación de ejecución. Se integra el objetivo de generación localizada como decisión todavía pendiente, sin darlo por implementado. La preparación de DRAGO se enumera como trabajo posterior, sin reabrir su comprobación ahora. Se indica que la redacción puede avanzar en paralelo.

**Resultado:** las tareas 1–8 se marcan completadas con base en las evidencias ya registradas; las otras 52 quedan pendientes o por completar. Se identifica como siguiente bloque la asignación y validación de particiones (11–14), manteniendo las revisiones de contenido pendientes en paralelo. No se da por cerrada toda P0 ni se atribuyen entrenamientos, maestros, evaluaciones o entregas no realizados. Las fechas del plan se conservan como objetivos sujetos a comprobación de vigencia, no como hechos ni plazos oficiales de depósito.

**Mantenimiento:** se añade a `AGENTS.md` la instrucción de actualizar las casillas al completar trabajo y de registrar el resultado en esta bitácora, conservando los números. `tasks.md` sirve para el seguimiento; el plan y el protocolo siguen aportando el detalle metodológico y la bitácora conserva la historia de decisiones.

### M022 · 2026-11-12 · Tarea 9 resuelta y adquisición inicial completa por cámara

**Decisión del investigador:** trabajar con el archivo actual sin corregirlo. En principio usar las imágenes fuera de la subcarpeta Nikon, completas para la repetición, y tener en cuenta que la adquisición dentro de la subcarpeta es incompleta al repartir los datos.

**Alcance aplicado:** se conserva `2025-06-20_c1_r2/nikon_d70/DSC_0380.JPG` tal como está, con su historial de cambio de bytes y píxeles. La aceptación se vincula a su SHA-256 actual, sin atribuir la causa ni afirmar que fue restaurado. Se cierra la tarea 9 por decisión del investigador; no exige otra revisión para continuar.

**Selección de adquisición:** para `2025-06-20_c1_r2` se usarán inicialmente las 60 iPhone de la raíz, que cubren las 60 posiciones de Amaranthus, sin maíz. Las 23 Nikon adicionales de las primeras posiciones se conservan en inventario y como reserva, fuera del reparto inicial. No se descartan otras sesiones completas tomadas con Nikon ni se borran imágenes. Esta decisión es de cobertura de adquisición, separada de las nueve exclusiones por calidad/contenido ya existentes.

**Acción:** se guarda la política explícita en `exp_design/acquisition_policy.json` (AP001); el constructor añade `use_in_initial_partition` y estado, fuente y motivo de selección. Las candidaturas a clasificador y LoRA respetan esa política. Los identificadores de grupo se mantienen: si se recupera la reserva Nikon para un uso posterior, cada foto deberá mantener la función de su maceta, sin crear una partición independiente de la imagen iPhone correspondiente.

**Resultado de ejecución:** se regeneran y versionan los manifiestos en la construcción `20261112T194002439400Z` (19:40:02–19:40:11 UTC), con estructura 1.1 y 123 campos. El inventario completo mantiene **1.451 fotos**: 493 de 2025 y 958 de 2026. Las vistas de reparto inicial contienen **1.428 fotos**: 470 de 2025 y 958 de 2026. Las 23 reservadas quedan enumeradas en `manifest_deferred_acquisitions.csv`, con `use_in_initial_partition=False`; se conservan sus etiquetas y grupos y no hay borrado ni edición de originales.

**Candidaturas actualizadas:** **1.296 fotos para clasificación**, de 360 grupos (437 palmeri, 424 hybridus y 435 retroflexus), y **437 palmeri candidatas a LoRA**, de 122 grupos, antes de las reservas por función y de la preparación geométrica. La reducción es de 23 fotos para clasificación y tres palmeri para LoRA, sin perder grupos porque las mismas macetas están cubiertas por la adquisición iPhone completa. Las nueve exclusiones por calidad/contenido permanecen separadas y no aumentan por esta selección de cámara.

**Verificación:** las **62 comprobaciones** de los manifiestos pasan, incluidos SHA-256 de los 1.451 originales, las tres vistas iniciales, la reserva exacta de 23 Nikon, la conservación de las 60 iPhone y el cierre de la tarea 9 sin ocultar el cambio histórico. Se actualizan el perfil de preparación, la documentación y `tasks.md` (nueve tareas completadas y 51 pendientes). La tarea 9 es una aceptación del estado actual por el investigador, no un diagnóstico de causa ni una reparación. No se asignan todavía C_fit, C_val, G_fit ni T_real.

**Evidencias:** [política de adquisición](exp_design/acquisition_policy.json), [inventario completo](data/processed/manifest_all.csv), [vista de reparto inicial](data/processed/manifest_initial_pool_all.csv), [adquisición reservada](data/processed/manifest_deferred_acquisitions.csv), [validación](data/processed/manifest_validation.json) y [estado de datos actualizado](data/processed/estado_datos_modelado.md).

### M023 · 2026-11-12 · Cierre de la tarea 10 con las indicaciones disponibles

**Instrucción del investigador:** las imágenes con plantas secas/muertas y las cantidades, cuando corresponden, ya están indicadas; marcar la tarea 10 como lista y avanzar a la división de datos del clasificador.

**Decisión y resultado:** tarea 10 completada con base en esas indicaciones y las notas existentes, conservando las nueve exclusiones, las cantidades nominales/sembradas y las observaciones textuales cuando constan. No se ha realizado ni se atribuye una inspección visual nueva de todo el corpus. Los recuentos observados no estructurados o no aportados no se rellenan a partir de la siembra, y el estadio desconocido continúa como tal. La falta de esas anotaciones no se considera un bloqueo para asignar grupos y preparar el clasificador inicial.

### M024 · 2026-11-12 · División inicial de datos por grupos de maceta

**Solicitud y alcance:** avanzar a la división del clasificador, conservando las reservas previstas para generación y prueba. Los porcentajes y la semilla siguientes son decisiones de implementación para una primera división reproducible, no resultados de optimización ni una garantía de potencia estadística.

**Criterios:** unidad de reparto `split_group_id` (misma maceta entre fechas y cámaras); estratificación por especie de trabajo corregida, año, campaña, repetición y densidad de siembra/nominal. Reservar aproximadamente el 20 % de los grupos palmeri en G_fit antes de repartir los restantes grupos principales aproximadamente 70/15/15 entre C_fit, C_val y T_real. Reservar el maíz en M_aux. Separar C_val en model_selection y threshold_calibration con grupos distintos y balance por especie/año/campaña. Semilla 20261112, orden seudoaleatorio determinista mediante SHA-256; los recuentos enteros se resuelven por mayor resto con desempate explícito, sin mirar resultados de modelos ni píxeles.

**Protecciones:** ninguna foto de la misma maceta puede cambiar de función por fecha o cámara. Las nueve exclusiones y las 23 Nikon secundarias conservan la función de su grupo para trazabilidad, pero no se incorporan a los CSV activos. Los grupos palmeri de G_fit no se usan para entrenar/validar el clasificador ni como referencias BioCLIP; T_real queda reservado para evaluación final, sin elegir con él encuadres, parámetros ni umbrales. Se conserva la adquisición parcial del 12 de junio con su cobertura real, sin inventar archivos.

**Límites:** es una reserva de macetas dentro de las campañas/repeticiones representadas, no una prueba de generalización a otra campaña. La continuidad declarada no acredita conexiones o independencia adicionales no documentadas. Las muestras de validación y calibración son pequeñas y sus resultados deberán expresar sus límites. La estratificación por densidad usa números sembrados/nominales, no afirma que todas esas plantas estén presentes en cada foto.

**Acción prevista:** guardar `partition_plan_v1.json` y `partition_assignments_v1.csv` en `exp_design`, integrarlos en la construcción de manifiestos para no perder la asignación al regenerar y exportar listas activas separadas. La versión se conserva y cualquier revisión futura requiere una nueva decisión y trazabilidad. Se añadirán resultados y comprobaciones después de ejecutar.

**Resultado ejecutado:** `scripts/create_group_partitions.py` crea la asignación v1 de los 400 grupos y el constructor genera los manifiestos con estructura 1.2 (130 campos), preservando versiones previas. Construcción `20261112T194939095053Z`, 19:49:39–19:49:46 UTC. No se modifican ni copian los originales. La asignación queda fijada antes de entrenar y se conserva por huella de entradas y hash de la tabla; se rechaza una sobrescritura o reasignación silenciosa.

| Función activa | Fotos | Macetas | P / H / R / M en fotos |
|---|---:|---:|---|
| C_fit: entrenamiento | 856 | 236 | 255 / 295 / 306 / 0 |
| C_val: configuración | 92 | 27 | 24 / 35 / 33 / 0 |
| C_val: calibración | 98 | 27 | 23 / 38 / 37 / 0 |
| T_real: prueba final | 164 | 46 | 49 / 56 / 59 / 0 |
| G_fit: LoRA | 86 | 24 | 86 / 0 / 0 / 0 |
| M_aux: maíz | 123 | 40 | 0 / 0 / 0 / 123 |

**Interpretación de recuentos:** C_val completo reúne 190 fotos y 54 macetas; sus dos subfunciones no se suman de nuevo al padre. Las funciones del clasificador reúnen 1.210 fotos de 336 macetas, y G_fit 86 de 24 macetas, sin solapamiento. Los cinco conjuntos principales reúnen 1.419 fotos activas; las 32 restantes son las nueve exclusiones y las 23 Nikon de reserva. Todas las filas conservan la función de su maceta, pero las inactivas tienen `use_in_assigned_partition=False` y no entran en los archivos activos. Los campos de candidatura general (1.296 y 437) se conservan como selección potencial previa; no deben confundirse con las listas activas asignadas.

**Validación:** 69 comprobaciones correctas de manifiestos, incluida la integridad de los 1.451 originales, y 113 controles correctos de particiones: grupos e imágenes sin solapamiento, cobertura exacta de entradas activas, roles C_val separados, tres especies y ambos años representados, G_fit palmeri de las cuatro cohortes y densidades de siembra de 2025, ausencia de imágenes excluidas/reservadas y respeto a las correcciones. En el primer intento de comparar filas, el comprobador convertía nulos JSON en NaN al pasar por pandas; se corrigió el comparador para conservar los nulos y repetir el control, sin modificar las asignaciones ni los datos para resolver ese falso desacuerdo.

**Entregables:** [documentación de particiones](data/processed/partitions/v1/README.md), CSV/JSON activos C_fit, C_val_model_selection, C_val_calibration, T_real, G_fit y M_aux; C_val completo; [tabla autoritativa de grupos](exp_design/partition_assignments_v1.csv), [plan congelado](exp_design/partition_plan_v1.json), resúmenes y [validación independiente](data/processed/partitions/v1/validation.json). Se actualizan los tres manifiestos, su documentación, el perfil de preparación y las instrucciones del proyecto para preservar v1.

**Seguimiento:** tareas 10–14 completadas; junto con las anteriores hay 14 tareas completas y 46 pendientes. El siguiente paso es la tarea 15, lote de desarrollo para preprocesado y escala. No se ha generado un maestro, entrenado un clasificador/LoRA, medido rendimiento ni usado T_real para ajustar un modelo. La selección por metadatos de partición no representa un resultado predictivo. La metodología de la memoria (tarea 56) deberá incorporar esta división efectivamente realizada.

## Pendientes vigentes después de la corrección de C2R2

1. Las dudas de las dos posiciones de C2R2 ya están resueltas y aplicadas (M018–M019). La tarea 9 sobre `DSC_0380.JPG` también está resuelta por aceptación del archivo actual y reserva inicial de la adquisición Nikon incompleta (M022); no es necesario repetir esas revisiones. Registrar otras discrepancias si se detectan.
2. Si aparecen nuevas correcciones de especie, registrar su fuente y alcance y comprobar a qué fotos de la misma maceta entre fechas afectan, conservando diseño y etiqueta de trabajo por separado.
3. La tarea 10 de contenido se cierra por instrucción del investigador con las indicaciones disponibles. Continuar con las referencias geométricas y el preprocesado de desarrollo; distinguir siembra nominal y presencia real sin volver a exigir una revisión exhaustiva como requisito para repartir.
4. Definir y probar el posible uso de fondos para generar sólo la planta, sin dar por elegida una técnica ni por demostrado que el modelo ignora suelo y maceta.
5. Las particiones v1 ya están asignadas y verificadas (M024). Mantenerlas al preparar imágenes y continuar el diseño experimental. Registrar aquí tamaños efectivos, exclusiones, métodos, configuraciones, semillas y resultados reales de cada fase.

## Texto metodológico provisional para el artículo

Este texto resume únicamente trabajo ya ejecutado y podrá revisarse al cerrar la revisión de siembra:

> Se realizó un inventario recursivo de las fotografías y se verificaron su decodificación, metadatos y unicidad mediante SHA-256 de archivo y hashes de píxeles RGB tras aplicar orientación EXIF. Las fotografías se relacionaron con el diseño de siembra mediante el recorrido en serpentina y el orden temporal de adquisición, incorporando las aclaraciones del responsable de la captura sobre selecciones, tomas repetidas, dos adquisiciones con cámaras distintas y una sesión incompleta. La fecha de sesión se tomó del nombre de la carpeta y se conservaron los metadatos originales de la cámara. Para 2025, el número de plantas sembradas se vinculó a las posiciones por orden de recorrido; para 2026 se registró una planta nominal por maceta según información de campo. Las fotografías de una misma maceta entre fechas y cámaras se vincularon mediante un identificador de grupo. Se prepararon copias sin modificación de su contenido, con la especie esperada y la posición en el nombre, para revisión visual del investigador. La identidad de cada copia con su origen actual se comprobó mediante SHA-256. El investigador identificó como A. palmeri las plantas de dos posiciones de la segunda repetición de 2026 que estaban previstas como A. hybridus, atribuyendo la discrepancia a un error con la semilla. La corrección se propagó a las ocho fotografías disponibles de esas macetas, conservando por separado la etiqueta de diseño y la etiqueta de trabajo con su fuente. Se consolidaron los manifiestos por año y conjunto y se verificó su correspondencia con los originales actuales. Se registraron separadamente las exclusiones por incidencias, los archivos retirados y los cambios respecto al inventario inicial. No se atribuyó una confirmación visual individual a las fotografías sin un registro específico de dicha revisión.

No se trasladarán al artículo como resultados obtenidos las fases de entrenamiento, generación o validación experta que todavía no se han ejecutado.

### M022 · 2026-11-12 · Redacción inicial de metodología del TFM

**Solicitud y alcance:** el investigador solicitó redactar la metodología del TFM hasta el estado actual, con atención a los aspectos informáticos, de inteligencia artificial y agronómicos. La fuente de hechos y estados es esta bitácora, especialmente M001–M021 y la documentación de los manifiestos vigentes; las decisiones de investigación no se modificaron.

**Acción y resultado:** se redactó `doc/capitulos/03-metodologia.tex` con el diseño, material vegetal, inventario, asignación de etiquetas, revisión y validación de manifiestos, selección preliminar y fases pendientes. Los recuentos se contrastaron con M019–M020 y `data/processed/README_manifiestos.md`. Se distingue la revisión declarada por el investigador de la validación técnica y se identifican como pendientes las particiones, el preprocesado y los experimentos. No se ejecutaron nuevos análisis ni entrenamientos.

**Límites y seguimiento:** no se localizó el complemento solicitado «scientific article helper» entre las herramientas disponibles ni en la búsqueda de complementos; se utilizó redacción científica general. No se pudo compilar el PDF en este entorno porque `pdflatex` no está disponible en la ruta de comandos. La tarea 56 continúa abierta: la metodología deberá actualizarse con procedimientos efectivamente ejecutados, particiones, transformaciones y configuraciones futuras.

### M025 · 2026-11-12 · Lote de desarrollo para escala y preparación (tarea 15)

**Solicitud, fuente y alcance:** trabajar en tareas 15–20 tras fijar datos/particiones, documentando decisiones; el investigador autoriza subagentes. Se consultan esta bitácora, protocolo, manifiestos e instrucciones y asignaciones v1. Dos subagentes apoyan implementación y revisión independiente del protocolo/herramienta, sin confirmar especies.

**Decisión y motivo:** lote sólo de C_fit activo, dos fotos por sesión y especie, equilibrando siembra 1/4 en 2025 y completando orientaciones EXIF. Orden determinista SHA-256 de semilla `20261112-preprocessing-v1` e identificador, sin consultar píxeles de evaluación ni resultados de modelos. Sirve para desarrollar el procedimiento, no para estimar prevalencias. La siembra no se convierte en presencia observada; maíz continúa en M_aux.

**Acción y resultado:** `scripts/select_preprocessing_development.py` selecciona **91 fotos/76 macetas**, 15 sesiones, H=30/P=30/R=31; Nikon D70=36, iPhone=7, Sony ILCE-6300=6 y Nikon D3000=42; EXIF 1=69, 3=1, 6=12 y 8=9. Las primeras 90 cubren sesión×especie y se añade una iPhone para EXIF 3. Se verifican los 91 hashes actuales. Selección CSV/JSON, plantilla pendiente, once contactos y validación en `data/processed/preprocessing/development_v1`. Tarea 15 completa. Sin cambios en originales, etiquetas o funciones de maceta.

### M026 · 2026-11-12 · Revisión de dos campos por año en lugar del campo único

**Observación y método:** nueve fotos tienen ocho puntos colocados visualmente por Codex sobre el borde exterior en vistas orientadas de lado máximo 1000 px, círculo algebraico ajustado y envolvente vegetal. Puntos/centro/diámetro se trasladan a coordenadas originales. Autoría `Codex_visual_pilot_not_independent`, nominal 10/20 cm, hash, residuo y `measurement_scope=pilot_only`. No son anotaciones del investigador ni confirmaciones botánicas. El residuo no estima precisión manual, incertidumbre física o repetibilidad. Puntos/superposiciones: `annotations_pilot.json`, `measurement_overlay_*.png`; reproducción: `scripts/measure_preprocessing_pilot.py`.

**Hallazgo limitado a los casos medidos:** una foto de 2025 permite unos 12,15 cm de campo centrado (`DSC_0112.JPG`); otra, 10,57 cm (`DSC_0067.JPG`). Las macetas de 2026 ya miden nominalmente 20 cm. Un campo único que conserve íntegramente esas macetas no es compatible con todas estas capturas. Dos ejemplos extendidos de 2026 requieren unos 27,97/30,80 cm para conservar envolvente y margen ensayado de 1 cm, frente a máximos cubiertos de 22,93/23,05 cm. No extrapolar a todo un año ni diagnosticar tejido ausente: son incompatibilidades de estos encuadres y medidas provisionales.

**Decisión explícita del investigador:** elige «Revisar dos campos separados por año, documentando el cambio de diseño». Sustituye la exigencia de campo único del protocolo (vinculada a M011) y la anterior tarea 17. No aprueba valores ni exclusiones definitivas. Se añade actualización al inicio del protocolo, conservando el texto histórico. Se mantienen grupos, funciones, ausencia de relleno/reconstrucción y prohibición de ajustar el campo a cada planta.

**Ensayo de implementación, sin congelar:** `exp_design/preprocessing_pilot_v1.json` propone 12 cm en 2025 y 22 cm en 2026, a 1024 px y margen vegetal de 1 cm por lado. Son 85,33/46,55 px/cm y macetas esperadas de 853,33/930,91 px: las salidas no comparten escala física aunque compartan lienzo. Guardar año/campo/px por cm y revisar comparabilidad de ambos dominios en entrenamiento, generación y evaluación. La fórmula del protocolo sigue aplicándose con F por año; no acredita exactitud 3D de hojas.

**Pendiente:** 82 imágenes sin medir, revisión de las nueve provisionales, oclusión/inclinación, repetibilidad, sensibilidad al margen y cobertura por especie/año/cámara antes de delimitar dominios. `DSC_0101.JPG` apenas permite 12,002 cm según este ajuste: aunque el recorte a 12 cm pase técnicamente, no es robusto al error de medición. No congelar estos candidatos a partir de los ejemplos. Evidencia: `development_v1/field_feasibility_pilot.json`.

### M027 · 2026-11-12 · Ejecución y cierre del piloto técnico de preparación

**Acción y procedimiento:** `scripts/prepare_metric_masters.py` consume manifiesto vigente, anotaciones por identificador/hash y configuración; aplica EXIF, convierte ICC válido a sRGB y registra la suposición sRGB sin perfil. Rechaza perfiles inválidos. Ventana fraccional, Lanczos isotrópico, PNG RGB con perfil sRGB; sin balance automático, homografía, relleno, eliminación de tarjetas ni reconstrucción. Exige referencia revisada, truncamiento explícitamente falso, envolvente/margen contenidos, campo no menor que maceta y cobertura real. `apply` exige configuración congelada y rechaza medidas `pilot_only`; T_real requiere acceso explícito. El piloto permite sólo C_fit/C_val_model_selection; esta sesión usa C_fit.

**Resultado ejecutado:** **nueve medidas, cinco maestros a 1024 × 1024 y cuatro rechazos con los candidatos**: uno por cobertura y tres por vegetación/margen fuera de ventana. Son incompatibilidades piloto, no nuevas exclusiones definitivas. Dos maestros de 2025 (P/H) y tres de 2026 (H): no hay cobertura suficiente para aprobar el corpus. La iPhone con ICC fue rechazada por vegetación/margen, por lo que falta aprobar visualmente un maestro iPhone apto. Se inspecciona `pilot_v1/masters_review.jpg`, sin fijar resolución final ni atribuir validación de detalle taxonómico. Los nueve casos cubren tres especies/cuatro cámaras, no todas las sesiones.

**Trazabilidad:** `data/processed/preprocessing/pilot_v1/manifest_metric.csv/json` conserva las 1.451 filas, etiquetas, funciones y hashes; enlaza medidas, ventanas/factores, campo por año, motivos y cinco rutas. Es un complemento, no listas definitivas de entrenamiento ni sustitución de `manifest_all`. El constructor autoritativo reinicializa geometría: conservar anotaciones/configuración y reconstruir expresamente el complemento; no copiar columnas manualmente a los consolidados. `run.json` guarda hashes de entradas/código y entorno real Python 3.12.1/Pillow 13.0.0. Las medidas usan NumPy de `.venv`, tras autorización de acceso al intérprete base fuera del proyecto.

**Verificación y límites:** ocho pruebas sintéticas correctas del procesador: geometría, cobertura, vegetación/margen, campo no menor que maceta, EXIF/color, dos campos y protección de funciones/trazabilidad. `scripts/validate_preprocessing_pilot.py` supera nueve controles sobre selección activa/cobertura, 91 hashes actuales, complemento completo, etiquetas/particiones conservadas, ausencia de maestros T_real, hashes/modo/tamaño/perfil de los cinco PNG y ecuaciones/ventanas reales. Hash JSON autoritativo antes/después: `51f1838fa4b74d7c088d8eb5b0359497fbca987d21f22dafe322042d9e3b7471`. La validación técnica no mide incertidumbre visual.

**Continuación preparada:** herramienta Tkinter `scripts/annotate_metric_geometry.py`: puntos de borde, ajuste/residuo, envolvente, calidad y truncamiento explícitos, revisor/fecha/hash, guardado separado `annotations_reviewed.json` y copias históricas. Importación/dependencias y ajuste de ocho puntos sintéticos comprobados (centro 100/200, diámetro 60, error numérico menor de 1e-8); **no se lanza ni valida visualmente la interfaz**, no se crean revisiones del investigador. Instrucciones en `scripts/README_anotacion_geometria.md`.

**Cierre:** sólo tarea 15 completa; tareas 16–20 abiertas con avances en `tasks.md`. Faltan medidas, repetibilidad, resolución, dominios y revisión de cobertura antes de congelar y generar maestros experimentales. T_real no se abre; no se entrena/genera con modelos ni se prepara DRAGO. Evidencias/reproducción y límites: `data/processed/preprocessing/README.md`, `pilot_v1/run.json` y `pilot_v1/validation.json`.

### M028 · 2026-11-12 · Reapertura crítica de la estrategia de preparación (en ejecución)

**Solicitud y autorización:** el investigador pregunta si la decisión es acertada y autoriza probar alternativas y quedarse con la que mejor sirva al objetivo, avanzando hasta tarea 20. Solicita una goal y pausa si queda menos del 5 %. Se crea goal activa; no hay presupuesto numérico definido en la herramienta, por lo que no existe porcentaje restante calculable. No se presenta un porcentaje inventado. Se revisará el límite disponible si el sistema lo expone.

**Motivo y acciones previstas:** los candidatos 12/22 cm excluyeron cuatro de nueve casos y casi agotaron cobertura en otro. No hay base para defenderlos como óptimos. Comparar campos comunes, por año, proporcionales al diámetro y conservación de encuadre completo; medir el lote de desarrollo con propuestas semiautomáticas y revisión visual, manteniendo las incertidumbres explícitas. Valorar cobertura y conservación de vegetación antes que la conveniencia de cerrar casillas. No utilizar T_real para elegir parámetros. La eventual transformación congelada se aplicará a todas las funciones manteniendo v1, con mediciones/aptitud métricas separadas cuando falte referencia fiable. No llamar métrico a un encuadre de campo variable.

**Estado inicial:** revisión en curso, sin estrategia nueva congelada ni resultados atribuidos. La revisión independiente identifica que conservar encuadre completo puede preservar proporciones aparentes, pero no equivale a normalizar cm/píxel; habrá que documentar explícitamente ese cambio si se elige. Fuentes técnicas primarias a contrastar: Pillow ImageOps (contain/fit/pad) y lector real de entrenamiento Diffusers, que puede volver a recortar. Se añadirán resultados de comparación, controles y cierre de tareas tras la ejecución.

### M029 · 2026-11-12 · Comparación de alternativas y congelación del encuadre completo

**Rectificación autorizada:** por la solicitud de M028, se sustituye la elección exploratoria de campos por año de M026 y la obligatoriedad de maestros a cm/píxel común del plan/protocolo. Se elige conservar **todo el encuadre adquirido con aspecto exacto** como corpus general. Se preservan proporciones aparentes planta/maceta y variabilidad de tamaños; **no se consigue ni se afirma normalización métrica absoluta común**, tampoco recuperación de tejido ausente. La referencia métrica se evalúa aparte cuando sea fiable. Este cambio de alcance es explícito, motivado por conservación morfológica/cobertura y autorizado por el investigador al permitir rectificar y elegir alternativas; no es una mejora de clasificación o generación medida con modelos.

**Medición exploratoria terminada (tarea 16):** se revisan las 91 imágenes de desarrollo y se registran 84 medidas provisionales y siete referencias no medibles, con motivo y centro/diámetro nulos. Fuente: extremos visibles de borde exterior anotados por Codex sobre contactos de lado máximo 490 px, trasladados a coordenadas EXIF orientadas; diámetro operativo = media de extensiones horizontal/vertical, conservando ambos ejes y su cociente. No es una rectificación de elipse ni calibración física. En nueve casos se conservan además los círculos de ocho puntos sobre vistas de 1000 px de M026. Las diferencias entre métodos del mismo asistente tienen mediana 0,45 % y máximo 1,22 %; no equivalen a repetibilidad de observadores independientes ni a exactitud física. Las 91 fichas mantienen `pilot_only`: ninguna habilita escala de producción. Las siete referencias no fiables son tres iPhone con oclusión y cuatro imágenes con borde parcial/en límite. Esto completa medición/revisión exploratoria y estados de referencia del lote, sin cerrar la validación metrológica de tarea 45.

**Evidencia de medición:** `exp_design/development_rim_visual_extents_v3.csv`, `scripts/consolidate_development_geometry.py`, `development_geometry_v3/annotations_development_reviewed.json` y once `visual_review_*.jpg`. Se conservan v2 e historial: v3 corrige el centro dibujado desplazado del caso 083 detectado al revisar su superposición. Se verifican los hashes de las 91 fuentes. La autoría es AI/Codex, no el investigador ni un experto botánico; la incertidumbre de clics, nominal y perspectiva no queda cuantificada.

**Alternativa automática examinada y rechazada:** `scripts/detect_pot_geometry.py` propone círculos Hough/gradientes y vegetación HSV. Tras fallos evidentes de fondo/malla se prueban ajustes de centralidad/borde oscuro/verde; todas las propuestas quedan sin aprobar. `geometry_review_v2/standardized91` conserva una pasada homogénea de 91 a 400 px; los ensayos anteriores se mantienen separados. Frente a los nueve pilotos aproximados, diferencia absoluta mediana de diámetro 3,65 %, máxima 35,53 % (caso 044); fallos visuales también en 040/048/059/061. No son errores contra verdad terreno. Siete controles sintéticos pasan, pero no justifican automatizar las medidas del corpus. OpenCV/NumPy se instalan para este ensayo en `scratch/opencv_runtime`; el intento anterior de instalación global de Python 3.12 copió NumPy antes de fallar con un ejecutable; se registran versiones efectivas y no se afirma que todo el entorno quedó idéntico. No se altera `.venv` para ese ensayo.

**Comparación geométrica ejecutada:** `scripts/compare_preprocessing_strategies.py` y `strategy_comparison_v3/comparison.json/csv`. Entre las **84 medidas exploratorias**, las ventanas completas con maceta y fuente real caben en 48 casos para 20 cm común, 36 para 22 cm, siete para 26 cm, uno para 30 cm y ninguno para 40 cm; campos por año 12/22: 63; 11/24: 52; 1,1 diámetros: 68 y 1,3 diámetros: 25. Siete referencias son desconocidas/no evaluables, no fallos geométricos demostrados. Este criterio de cobertura **no prueba** conservación de vegetación. Para envolvente completa y margen ensayado de 1 cm sólo hay nueve casos anotados: 20/22 cm conservan cuatro; 26/30/40, ninguno; 12/22, cinco; 11/24, tres; 1,1 diámetros, cinco; 1,3 diámetros, ninguno. Los otros 82 no se clasifican como rechazos por vegetación. Son criterios y denominadores distintos; no se compara 5/9 con 91/91 como si midieran lo mismo.

**Razón de elección y resolución:** el encuadre completo conserva el 100 % de la extensión capturada en 91/91, sin depender de una máscara o diámetro acertados ni excluir plantas extendidas. Los tamaños 1024/1536/2048 se comparan visualmente sobre parches idénticos de plántulas; 2048 retiene más detalle visible, sin afirmar validación taxonómica o rendimiento futuro. Se congela lado máximo **2048 px**, sin ampliar, y dimensiones como múltiplos enteros de la razón reducida por MCD para conservar aspecto **exacto**, sin redondeo distinto de ejes: Nikon D70 1880×1250 o inversa, D3000 1936×1296 o inversa, Sony 2046×1364 e iPhone 2048×1536 o inversa. EXIF, sRGB/ICC y suposición declarada sin perfil, Lanczos, PNG compresión 3; sin crop/padding/homografía/inpainting ni corrección de tejido. El tamaño 1024 cuadrado anterior sigue siendo historia de piloto.

**Piloto y comprobación previa a congelar:** `fullframe_development_v3` genera 91 maestros C_fit, siete con ICC convertido y 84 sin ICC con suposición sRGB. Cinco pruebas unitarias del procesador pasan. La auditoría independiente `scripts/validate_fullframe_masters.py` verifica 1.451 hashes originales, 91 PNG y reconstrucción de cada raster EXIF+color+resize con igualdad exacta de píxeles, aspecto, ventanas completas, CSV/JSON y funciones; 12.387 controles correctos en la primera pasada. Ningún T_real se decodifica para decidir. La corrida v2 de desarrollo fue iniciada mientras se añadían guardas de fecha al código; se conserva como ensayo histórico y se repite íntegramente como v3 con hash de código estable para las evidencias de decisión. No se atribuye reproducibilidad al código cambiado durante v2.

**Congelación y siguiente acción:** crear `exp_design/preprocessing_fullframe_v2_frozen.json` con hora UTC y hashes de código, fuentes, comparación, revisión y validación de desarrollo. Aplicar después exactamente esa configuración a las 1.419 fotos activas de todas las funciones, incluida transformación técnica de T_real sin inspección visual ni selección por sus resultados. Mantener las 32 inactivas sin maestro, las funciones v1 y sus listas separadas. La generación final y su auditoría aún están pendientes al escribir esta entrada; se añadirán resultados en M030. El complemento enlazará las 91 fichas exploratorias sin convertirlas en métricas aprobadas.

**Límites y contrato posterior:** mayor conservación de encuadre no elimina tarjetas, fondos, cámara, perspectiva, relieve ni posibles sesgos; revisarlos en tareas 28/43/45. El lector de cada modelo deberá conservar el encuadre (sin recorte central/aleatorio implícito); los maestros rectangulares no garantizan por sí solos que un entrenador FLUX/DreamBooth los respete. Deben probarse adaptación de loader/buckets o lienzo explícito al preparar el entrenamiento, sin llamar métrico a un posible lienzo añadido. No cambiar pesos/modelos aquí. Fuentes primarias: [Pillow ImageOps](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html), [Diffusers DreamBooth](https://huggingface.co/docs/diffusers/training/dreambooth) y [OpenCV Hough](https://docs.opencv.org/4.13.0/d4/d70/tutorial_hough_circle.html).

### M030 · 2026-11-12 · Pausa solicitada durante la generación final

**Instrucción y estado:** el usuario establece la goal en `paused`. Se comprueba ese estado y se detiene el proceso específico de generación; no se continúa la preparación ni se declara cumplida la goal. La pausa procede de la instrucción del usuario, no de un porcentaje de presupuesto inferido: la herramienta no expone presupuesto restante numérico.

**Resultado conservado:** configuración `exp_design/preprocessing_fullframe_v2_frozen.json` congelada a **20:32:07.246749 UTC**, generación iniciada a **20:32:07.677026 UTC**. `data/processed/preprocessing/fullframe_v2/completed.jsonl` contiene **1.381 de 1.419 salidas registradas, cero errores registrados**; quedan 38 sin registro completado y dos ficheros `.partial` de trabajos interrumpidos. El recuento procede del checkpoint, no de una auditoría final: puede haber un PNG terminado todavía no registrado. Por función principal: C_fit=830, C_val=188, G_fit=85, T_real=159 y M_aux=119; no usar estas listas parciales como corpus final. Las imágenes T_real se transforman sólo después de congelar; no se inspeccionan visualmente ni se usan para decidir parámetros.

**Pendiente antes del cierre de tarea 20:** reanudar la misma ejecución con `--resume`, configuración y anotaciones idénticas; comprobar las salidas pendientes/temporales; ejecutar la auditoría exhaustiva, exportar/verificar manifiestos y listas completos, archivar código/configuración y registrar los recuentos finales. Todavía no existe `run.json` final ni `manifest_fullframe.json` final en esa carpeta. No marcar tarea 20 ni goal como completas.

**Pendientes de consolidación detectados por revisión independiente:** en nueve fichas de ocho puntos, el campo descriptivo `diameter_convention` conserva la descripción de media de ejes de la medida alternativa; el diámetro principal y `measurement_method` corresponden al círculo, y ambos métodos están separados en `lower_resolution_extents_measurement`. Todas las fichas siguen `pilot_only`/`usable_provisional`: no hay escala de producción aprobada. Registrar una fe de erratas descriptiva sin alterar silenciosamente los hashes congelados. Corregir las frases aún históricas pero prescriptivas de P6/P7/contingencia del plan (`N*D/F`, diámetro esperado solicitado y «manteniendo F») y el último párrafo geométrico del protocolo para que sólo rijan proporciones/ocupación condicionadas, no un diámetro esperado único. Se conservan como pendientes explícitos, no corregidos tras la pausa.

**Reanudación exacta desde la raíz:** `python scripts/prepare_fullframe_masters.py --config exp_design/preprocessing_fullframe_v2_frozen.json --annotations data/processed/preprocessing/development_geometry_v3/annotations_development_reviewed.json --output data/processed/preprocessing/fullframe_v2 --mode apply --include-test --workers 4 --resume`. Después: `python scripts/validate_fullframe_masters.py --output data/processed/preprocessing/fullframe_v2 --config exp_design/preprocessing_fullframe_v2_frozen.json --annotations data/processed/preprocessing/development_geometry_v3/annotations_development_reviewed.json`. No regenerar ni editar la configuración/fichas congeladas durante la reanudación.

### M031 · 2026-11-12 · Reanudación y corrección descriptiva sin alterar entradas congeladas

**Instrucción y estado observado:** el usuario reactiva la goal. Se leen M029–M030, las tareas y las huellas vigentes; se comprueba que no hay un proceso de generación activo antes de reanudar el mismo directorio con `--resume`. La ejecución verifica huellas, fuentes y salidas anteriores y mantiene configuración/código/anotaciones congelados. La pausa anterior dejó progreso verificable, no un corpus completo.

**Decisión de trazabilidad:** corregir los nueve valores descriptivos `diameter_convention` señalados en M030 mediante una fe de erratas explícita y un manifiesto de entrega derivado, sin modificar el JSON congelado ni los píxeles. El método principal de esos nueve es círculo algebraico de ocho puntos; la media de ejes pertenece únicamente a la medida alternativa anidada. No cambian centros, diámetros, calidad, alcance `pilot_only`, etiquetas, particiones ni listas de entrada. Los demás 75 diámetros provisionales conservan la convención de media de ejes y siete referencias conservan nulos. El manifiesto de ejecución se conserva íntegro para auditarlo contra sus entradas originales; el de entrega aplicará sólo la corrección descriptiva identificada y enlazará su procedencia por hash.

**Consolidación documental:** se retiran de las reglas operativas del panel y de contingencia las exigencias de error respecto a N*D/F, diámetro sintético deducido del solicitado y «mantener F». Se sustituyen por relaciones planta/maceta, ocupación relativa del lienzo y condiciones comparables, manteniendo las tolerancias de tarea 45 pendientes. La actualización M026 queda identificada como histórica. Son consecuencias de M029, no una nueva afirmación de éxito físico o de modelos.

**Acciones pendientes al abrir esta entrada:** terminar la reanudación, auditar exhaustivamente el corpus, crear y verificar el manifiesto de entrega y sus listas por función, archivar las entradas/código reproducibles y contrastar los requisitos 16–20 antes de cerrar casillas. Los resultados se incorporarán en M032; la goal permanece activa.

### M032 · 2026-11-12 · Cierre verificado de preparación y tareas 16–20

**Resultado de ejecución:** la reanudación verifica las 1.381 salidas previas y termina las 38 pendientes. Generación completa a **21:57:11.731439 UTC**, sin errores: **1.419 maestros PNG** (6,375 GB decimales), con **32 filas inactivas sin maestro** y cero ficheros temporales pendientes. La configuración sigue siendo la congelada a 20:32:07.246749 UTC (M029), anterior al primer inicio de 20:32:07.677026 UTC. La pausa M030 no altera parámetros, entradas ni funciones. Los 1.451 originales permanecen con sus hashes actuales documentados, incluida la aceptación histórica de DSC_0380.JPG; no se modifica, borra ni reetiqueta ninguno.

| Función | Maestros |
|---|---:|
| C_fit | 856 |
| C_val_model_selection | 92 |
| C_val_calibration | 98 |
| G_fit | 86 |
| T_real | 164 |
| M_aux | 123 |

**Tratamiento de color y cobertura:** 56 maestros convierten ICC embebido válido a sRGB; 1.363 declaran suposición sRGB sin perfil de origen. Se conservan las siete dimensiones exactas previstas (incluidas sus orientaciones inversas), el rectángulo completo y el mismo factor en ambos ejes. Cobertura por cámara: D70=405, iPhone=56, Sony=130 y D3000=828. Por año/especie, 2025 H/R/P/M=138/140/134/49 y 2026 H/P/R/M=286/303/295/74. Son etiquetas de trabajo y recuentos de archivos, no nuevas confirmaciones botánicas ni individuos independientes.

**Auditoría exhaustiva ejecutada:** `scripts/audit_fullframe_execution.py` ejecuta el comprobador independiente congelado sobre todo el corpus y liga sus entradas antes/después mediante hashes. Finaliza correctamente a **22:35:13 UTC**: **23.018 instancias de comprobación, cero fallos**. Verifica los 1.451 originales, los 1.419 PNG por hash/decodificación/perfil/dimensiones, reconstrucción EXIF+ICC+Lanczos de **todos sus píxeles**, aspecto e isotropía exactos, ausencia de crop/padding/homografía, claves/etiquetas/funciones conservadas, CSV/JSON concordantes, listas exactas, grupos disjuntos y ausencia de temporales. Las 23.018 comprobaciones no se presentan como experimentos independientes. Los **13 tests unitarios de los procesadores** también pasan y se conservan en `unit_tests.txt/json`. T_real sólo recibe la transformación fijada y comprobación técnica; no se inspecciona visualmente para elegir encuadres ni se evalúa un modelo con él.

**Entrega derivada y fe de erratas:** `scripts/release_prepared_images.py` crea `fullframe_v2/release/manifest_prepared.csv/json`, las seis listas por función, README y `validation_release.json`. Sólo corrige nueve descriptores `metric_annotation.diameter_convention`: el diámetro principal procede del círculo de ocho puntos; la media de ejes pertenece a la medida alternativa. La corrección está enumerada por identificador/hash en `geometry_metadata_errata.json`. Se restaura programáticamente cada corrección y se comprueba igualdad completa con el manifiesto de ejecución: no cambian números, imágenes, rutas, hashes, etiquetas, calidad, ámbito ni funciones. Los archivos congelados y `manifest_fullframe.csv/json` se conservan íntegros. Las 91 fichas siguen `pilot_only`, con 84 medidas provisionales y siete no medibles; **cero referencias se promueven a escala de producción**.

**Materiales reproducibles:** `release/reproduction_inventory.json` identifica **36 copias de código, configuración, entradas y evidencias** verificadas por hash; el archivo no duplica las fotografías. Incluye medición/selección/comparación, procesadores, auditoría, tests y el ensayo automático rechazado. Las versiones de Python/Pillow/NumPy/LittleCMS y los límites de reproducción binaria figuran en `environment_fullframe_v2.json`. La invariante comprobada es el raster reconstruido; no se promete igualdad binaria de PNG regenerados con metadatos de perfil de otra fecha. Las rutas y dimensiones de originales/maestros, coordenadas, etiquetas de diseño/trabajo y roles quedan explicadas en el README de entrega.

**Índice activo y validación de cierre:** `exp_design/preprocessing_registry.json` apunta a la entrega, su configuración, manifiestos/listas y fe de erratas con sus hashes. `scripts/audit_preprocessing_completion.py` vuelve a verificar **todos los hashes de originales y maestros**, procedencia y archivo reproducible, CSV/JSON de entrega, roles/especies, fichas, diez alternativas, fecha de congelación y las casillas/fases futuras. Finaliza correctamente a **22:38:49 UTC** y guarda `fullframe_v2/completion_audit.json` con evidencia por tarea. La revisión independiente final no identifica errores materiales en registro, erratas, entrega o alcance; no abre T_real visualmente.

**Cierre por requisito:** tarea 16: revisión/medición exploratoria de las 91 referencias, con calidad y nulos donde corresponde; tarea 17: decisión revisada y explícita M029 tras contrastar alternativas, **sin haber logrado un campo físico universal**; tarea 18: transformación, resolución y maestros/ventanas fijados y comprobados; tarea 19: revisión de desarrollo, límites y cobertura por especie/año/cámara, separando aptitud general y métrica; tarea 20: corpus completo, enlaces persistentes, funciones v1, auditoría y materiales de reproducción entregados. Se marcan 16–20 completadas en `tasks.md`; junto a las anteriores hay **20 tareas completas y 40 pendientes**, conservando su numeración. Se actualizan plan, protocolo, flujo, documentación e instrucciones para retirar reglas prescriptivas de campo común y diámetro esperado único. La historia M025–M031 se conserva.

**Límites que permanecen abiertos y no se atribuyen como resultados:** conservación de proporciones aparentes no equivale a cm/píxel común, certificación 3D o recuperación de tejido fuera de captura. No se afirma validación botánica exhaustiva, exactitud metrológica ni mejor rendimiento predictivo/generativo; se comparó preparación geométrica y conservación de información visible en desarrollo. La tarea 45 conserva anotaciones repetidas independientes y tolerancias del panel. Lectores/adaptación de modelos y su resolución (25–27/33/35), leyendas, entrenamientos, DRAGO y evaluación siguen en sus tareas correspondientes. La goal de revisión y preparación hasta tarea 20 queda satisfecha en el alcance revisado M029, sin avanzar al bloque 21.

**Evidencias finales:** [entrega y guía](data/processed/preprocessing/fullframe_v2/release/README.md), [registro activo](exp_design/preprocessing_registry.json), [auditoría de imágenes](data/processed/preprocessing/fullframe_v2/validation_fullframe.json), [recibo de entradas](data/processed/preprocessing/fullframe_v2/audit_receipt.json), [validación de entrega](data/processed/preprocessing/fullframe_v2/release/validation_release.json), [auditoría por requisitos](data/processed/preprocessing/fullframe_v2/completion_audit.json) y [comparación razonada](doc/REVISION_PREPROCESADO_2026-11-12.md).

### M033 · 2026-11-12 · Aclaración sobre círculo de maceta y envolvente vegetal por color

**Pregunta del investigador:** si habría sido mejor detectar la circunferencia/centro de la maceta y construir una envolvente mediante filtrado del verde. Se revisan el código y resultados existentes antes de responder; no se ejecuta un nuevo experimento ni se cambia la entrega congelada.

**Observación de archivos:** `scripts/detect_pot_geometry.py` sí contiene un prototipo cercano: Hough para maceta, máscara HSV con predominio de G y componentes que intersectan una zona central de 0,9 radios, permitiendo extensión fuera del borde. `standardized91` contiene 91 propuestas sin aprobar. Los fallos documentados del detector de círculo y las limitaciones de la máscara no prueban que la estrategia completa sea inadecuada: no hay anotación exhaustiva de vegetación de referencia, comparación validada de estos recortes adaptativos ni comparación predictiva/generativa con encuadre completo.

**Matización de M029–M032:** el encuadre completo está verificado como una preparación conservadora de la extensión adquirida; no está demostrado que sea el preprocesado óptimo para aprender morfología o reducir pistas de fondo. El cierre de tareas acredita entrega, integridad y reglas explícitas, no superioridad de aprendizaje frente a una ROI bien validada. No confundir los 23.018 controles técnicos con evidencia de esa superioridad. La propuesta del investigador merece una comparación propia y no queda descartada por un prototipo imperfecto.

**Distinción geométrica:** localizar vegetación y decidir cómo presentarla son operaciones distintas. Un recorte adaptativo que contenga toda la maceta y vegetación, redimensionado isotrópicamente, conserva la relación planta/maceta; no impone cm/píxel común ni igual tamaño físico por píxel entre escenas. Un filtro verde no recupera cobertura fuera de captura y puede omitir tejido no verde o sombreado e incluir elementos ajenos. El círculo aporta centro y referencia nominal, no certifica por sí solo segmentación o exactitud 3D. No restringir la máscara al interior de la maceta si se quieren conservar hojas salientes.

**Procedimiento propuesto, aún no ejecutado/validado:** referencia de borde revisada (círculo/elipse como diagnóstico, sin rectificación automática), segmentación de vegetación vinculada a la maceta pero extendida fuera de ella, envolvente que incluya también la referencia completa y margen, rechazo/estado incierto cuando falle cobertura o identificación, y registro de ventana, factor y campo aparente. Comparar retención de tejido anotado, calidad de referencia, detalle, fondo y distribución de tamaños sobre desarrollo; si se quiere decidir utilidad para modelos, comparar posteriormente con el mismo entrenamiento/validación sin usar T_real. Una regla de campo métrico fijo debe decidirse aparte y sigue limitada por la cobertura real de cada original.

**Estado y fuentes:** aclaración conceptual y plan de contraste, no resultado nuevo ni aprobación de ROI. Se conserva `fullframe_v2_release1` sin modificaciones y su ámbito de M032. Fuentes primarias técnicas: [OpenCV, segmentación HSV/inRange](https://docs.opencv.org/4.13.0/da/d97/tutorial_threshold_inRange.html) y [OpenCV, Hough para círculos](https://docs.opencv.org/4.13.0/d4/d70/tutorial_hough_circle.html); las limitaciones concretas y propuestas pendientes se distinguen de lo comprobado en archivos.

### M034 · 2026-11-12 · Protocolo de prueba pequeña de ROI guiada por maceta y verde

**Solicitud:** contrastar experimentalmente la propuesta de círculo/centro de maceta y bounding box vegetal para decidir qué estrategia de preparación resulta más conveniente. La comparación se limita a preparación geométrica y detalle visible; no se atribuirá superioridad predictiva/generativa sin entrenar modelos.

**Decisión previa a ejecutar:** panel dirigido de 12 fotos activas C_fit del lote de desarrollo: los nueve casos con puntos/bbox anteriores (índices 1,3,6,43,44,62,86,88,90) y tres casos difíciles de referencia (37,40,53). Son casos de ingeniería con referencias disponibles y fallos conocidos, no una muestra aleatoria independiente ni una estimación de rendimiento del corpus. Mantener hashes, grupos, especies de trabajo y particiones. No abrir T_real, calibración o G_fit.

**Alternativas:** encuadre completo; círculo Hough propuesto + verde + cuadrado centrado; círculo revisado provisional + verde + cuadrado centrado; círculo revisado provisional + verde + rectángulo que contiene maceta/vegetación/margen, limitado a contenido real y permitiendo desplazar el centro de ventana. Las referencias no fiables disparan fallback explícito al encuadre completo en ramas revisadas. El verde se calcula de nuevo a mayor resolución que el prototipo de 400 px, sin recortarlo al interior de maceta. Los parámetros ensayados se guardan antes de ejecutar; cualquier ajuste posterior se separará como nueva variante, no se ocultará.

**Evaluación prevista:** comparar con envolventes vegetales visuales obtenidas sin usar la máscara, revisar las salidas y registrar pérdida de envolvente/tejido visible, proporción de fuente retenida, ganancia de resolución aparente a un mismo lienzo de presentación y calidad de referencia. La reducción de área total es un proxy de eliminación de contexto, no una medida de fondo segmentado. La contención de bbox no es recall de píxeles de una máscara de verdad terreno. Las anotaciones son aproximadas de Codex, no validación experta. Lienzos 224/384 con relleno sólo para diagnóstico de presentación, no nuevos maestros métricos. Se conservará proporción isotrópica planta/maceta; un ROI variable no impone cm/píxel común. Registrar cuándo la cobertura original impide margen o cuadrado centrado.

**Estado:** prueba aún no ejecutada al abrir la entrada. Se conservará la entrega M032 y el registro activo sin cambios; resultados, decisión y límites se añadirán al cierre.

### M035 · 2026-11-13 · Primer resultado y diagnóstico del efecto del margen

**Resultado observado de la primera ejecución:** cuatro estrategias sobre 12 C_fit. Encuadre completo conserva las 12 envolventes de referencia; automático Hough+verde+cuadrado obtiene cuatro recortes y ocho fallbacks (uno de los cuatro carece de referencia fiable para evaluar maceta); círculo revisado+verde+cuadrado obtiene cuatro recortes y ocho fallbacks; círculo revisado+verde+rectángulo limitado a captura obtiene nueve recortes y tres fallbacks por referencia no fiable. Los nueve recortes D contienen tanto la envolvente visual aproximada como la referencia de maceta. Cinco de esos nueve no disponen de todo el margen solicitado de 0,1 diámetros por alcanzar el borde original. No se reconstruye contenido ni se modifica la entrega vigente.

**Decisión de diagnóstico antes de calcularlo:** la diferencia C/D mezcla forma/centrado con política de margen. No atribuir toda la ganancia al rectángulo. Añadir un contraste geométrico posterior, identificado como tal, reutilizando las mismas 12 referencias y máscaras sin ajustar umbrales o selección: rectángulo con margen estricto; cuadrado centrado que reduzca sólo el margen a lo disponible sin cortar la maceta/verde; y rectángulo de maceta sola con el mismo margen, para comprobar qué aporta el verde cuando las hojas sobresalen. Cada fallback se informará por separado. Estas variantes no son resultados de entrenamiento ni una validación independiente de las anotaciones.

**Evidencia de primera ejecución:** `data/processed/preprocessing/roi_small_trial_v1/config_before_run.json`, `visual_reference_before_run.json`, `results.json/csv`, máscaras, 96 vistas de presentación 224/384 y tres hojas comparativas. Se inspeccionan las hojas de los 12 casos; las diferencias principales son ampliación visible y reducción de contexto cuando la ROI es apta, con conservación explícita del campo completo en fallbacks. Se añadirán al cierre las cifras definitivas, diagnóstico de margen y recomendaciones limitadas a esta prueba.

### M036 · 2026-11-13 · Completar el contraste automático con la misma ventana rectangular

**Motivo observado:** la primera pasada compara círculo automático sólo en cuadrado y círculo revisado también en rectángulo. Para no atribuir a revisión del círculo una diferencia que depende del encuadre/margen, añadir la rama automática rectangular con exactamente las propuestas Hough y máscaras ya calculadas. No volver a ajustar HSV, círculos, margen, panel o referencias tras los resultados.

**Acción prevista:** aplicar a los 12 casos la misma unión de maceta propuesta+verde y margen de 0,1 diámetros, limitada a captura; registrar ausencia de máscara, recorte sin reducción efectiva de contexto, contención de envolvente y de las nueve referencias de maceta disponibles. Comparar visualmente A/automático rectangular/D revisado. Una referencia insuficiente para metrología no demuestra por sí sola que sea imposible localizar una ROI útil; ambos criterios deben informarse por separado. Esta es una extensión diagnóstica posterior, no una comparación prerregistrada como parte de las cuatro ramas iniciales. Mantener la entrega vigente sin cambios.

### M037 · 2026-11-13 · Cierre de prueba pequeña de ROI maceta+verde

**Resultado experimental:** panel dirigido de doce C_fit, doce grupos, ambos años, H=5/P=4/R=3 y cuatro cámaras. Las ramas iniciales obtienen A=0, B=4, C=4 y D=9 recortes efectivos, con retorno explícito al encuadre completo cuando corresponde. Las doce envolventes vegetales aproximadas se conservan tras contingencia en cada rama. El diagnóstico posterior E/F/G separa margen y forma: rectángulo con margen estricto logra cuatro recortes, cuadrado con margen disponible siete (88/90 no admiten ni el cuadrado mínimo centrado), maceta sola nueve pero pierde parte de la envolvente vegetal en 43/88/90. No atribuir toda la diferencia C/D a la forma rectangular.

**Extensión automática H, ejecutada tras declararla en M036:** misma política rectangular de D y mismas propuestas/máscaras automáticas de B, sin reajustar parámetros: once recortes efectivos y una contingencia por ausencia de verde vinculado (44). Cero pérdidas de envolvente aproximada; cero fallos conocidos de referencia de maceta, con tres referencias no evaluables (37/40/53). Sobre los doce casos, incluyendo contingencia, mediana de ampliación geométrica 1,45239× y de área de fuente retirada 34,1602 %. No es porcentaje de fondo segmentado. El círculo revisado existente permite recortar 44 en D; no se presenta esa combinación posterior como validación independiente de un sistema híbrido.

**Revisión y verificación:** se inspeccionan los doce casos en las tres hojas iniciales y las tres A/H/D, sin nuevo corte vegetal aparente en recortes aceptados. Se generan 120 vistas RGB a 224/384. `scripts/validate_green_roi_trial.py` pasa quince controles: entradas activas C_fit, hashes originales intactos, registro/configuración/manifiesto de entrega congelados intactos, registros y vistas, ventanas acotadas, proporciones y pruebas sintéticas de coordenadas/margen/contingencia. `validation.json` conserva resultados y hashes. No se repite la auditoría histórica completa porque no se modifican los maestros.

**Decisión que matiza M029–M033:** para aprovechar el lienzo de entrada, la candidata favorecida es ROI rectangular automática maceta+verde, margen limitado a captura, revisión/corrección y contingencia a imagen completa. La maceta sola omite hojas en tres casos; exigir cuadrado centrado o margen completo limita recortes útiles. Se conservan maestros completos como fuente y entrega activa sin migración. La propuesta del investigador obtiene apoyo para preparación geométrica, no superioridad de aprendizaje demostrada. La regla vigente de preservar campo para lectores se mantiene hasta una decisión explícita de migración; el ensayo justifica contrastar la candidata en desarrollo.

**Límites y pendientes:** muestra pequeña dirigida, envolventes aproximadas de Codex sin segmentación experta independiente ni garantía de retención de todos los píxeles vegetales. Referencias revisadas provisionales; una ROI útil no certifica metrología. La ampliación no recupera detalle óptico ni impone cm/píxel común. No se entrenan modelos ni se abren T_real/G_fit/validaciones para ajustar ventanas. Falta comparar entradas con igual entrenamiento y selección en desarrollo en tareas 25–27/33/35; tarea 45 sigue abierta. No se cierran nuevas casillas con este ensayo suplementario.

**Evidencia:** [informe, comparativas y reproducción](data/processed/preprocessing/roi_small_trial_v1/README.md), configuración y referencias previas, resultados iniciales, diagnóstico E/F/G, protocolo/resultados H y validación con hashes en esa carpeta. Scripts: `trial_green_roi_preprocessing.py`, `diagnose_green_roi_trial.py`, `extend_trial_auto_rectangle.py`, `validate_green_roi_trial.py`. Se actualizan documentación de preparación y nota de seguimiento sin modificar entrega congelada.

### M038 · 2026-11-13 · Prioridad declarada: detalle y fidelidad morfológica de palmeri

**Declarado por el investigador:** clasificador seguido de generador sintético centrados únicamente en la planta, con máximo detalle y fidelidad morfológica de palmeri. Esta prioridad orienta la selección de entradas; no confirma por sí sola identidades botánicas de imágenes.

**Recomendación, pendiente de validación:** conservar originales y maestros completos; derivar ROI de planta con margen y máscara vegetal revisada. Usar maceta para localizar/referenciar, sin obligar a incluir toda la maceta en la entrada final si el objetivo es aislar planta. El HSV probado sirve como propuesta de localización, no máscara definitiva: preservar tallos, pecíolos, tejido sombreado/no verde y hojas completas; separar individuos cuando proceda. El ensayo M037 validó sólo envolventes maceta+verde en doce casos, no esta segmentación ni su rendimiento de aprendizaje. Para detalle, derivar de originales orientados/sRGB y reducir una sola vez a la resolución del modelo, comparando resolución y, si hace falta, vistas complementarias sin sustituir la arquitectura global de la planta.

**Aplicaciones propuestas:** clasificador: contrastar ROI conservadora frente a planta aislada con tratamiento de fondo uniforme entre especies y control de artefactos. Generador: estudiar entrenamiento localizado/máscara de pérdida compatible o plantas segmentadas con fondos controlados; una máscara de inpainting controla región de edición pero no garantiza aprendizaje exclusivamente vegetal ni fidelidad botánica. No atribuir esta capacidad a un LoRA de escenas completas. Comparar fidelidad, diversidad y posibles copias, con revisión experta de morfología, además de métricas del clasificador. Entrenar clasificador con C_fit y generador con G_fit; selección/calibración según roles vigentes, T_real congelado.

**Acción y estado:** se registra el objetivo y se explica la recomendación; no se generan nuevas máscaras/imágenes ni se ejecutan entrenamientos o migraciones. No se cambia la entrega activa ni se cierra tarea 32 por una recomendación aún no fijada. Pendientes validación de máscaras, elección de entradas/resolución y configuración generativa en sus tareas. Fuente experimental: M034–M037. Referencia técnica de región de edición, sin prueba de fidelidad en este proyecto: [Diffusers, inpainting](https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/inpaint).

### M039 · 2026-11-13 · Plan de comparación objetiva de preprocesamiento para implementación externa

**Solicitud del investigador:** planificar una comparación objetiva sobre un subsample y entregar especificaciones técnicas autónomas para otro LLM sin contexto; la implementación se revisará posteriormente. Registrar el detalle del experimento. La propuesta de SAM 3 para separar tierra/planta es una hipótesis a contrastar, no un resultado ya conseguido.

**Fuentes y observación nueva limitada a metadatos:** se leen bitácora, documentación de manifiestos, registro vigente, listas C_fit, plan v1 y configuraciones del piloto. Al excluir todos los grupos de las 91 fotos exploratorias, quedan 160 grupos activos C_fit: 2025 H/P/R=17/14/15 y 2026 H/P/R=39/34/41. Se comprueba así viabilidad de cuotas; no se inspeccionan fotos nuevas ni se selecciona todavía la muestra. El baseline conserva la entrega fullframe y el piloto M034–M037 como antecedentes, sin equiparar envolventes aproximadas con segmentación de referencia.

**Diseño propuesto:** 18 imágenes de calibración procedentes de grupos ya expuestos (tres por año/especie); evaluación interna bloqueada de 60 fotos de 60 grupos nuevos, 30 por año, con P=12/H=9/R=9 en cada año; panel histórico de doce casos sólo como estrés, separado de estimadores. Muestreo mediante orden SHA-256 con semilla `20261113-roi-benchmark-v1`, primero grupo por estrato y luego una imagen activa aleatoria reproducible por grupo. Registrar probabilidades, cobertura, exclusiones y hashes, sin favorecer visualmente casos fáciles ni alterar roles. No usar T_real, validaciones, G_fit o M_aux para ajustar esta comparación.

**Métodos planificados:** fullframe; Hough+HSV+rectángulo reproduciendo baseline; SAM 3 de imagen con consultas planta/suelo separadas y asociación al objetivo explícita. Separar ramas automáticas de asistidas, con igual presupuesto de revisión/corrección cuando se comparen. Exportar fullframe, rectángulo HSV, ventana SAM sin máscara, sólo planta SAM, planta+tierra SAM y máscara HSV en la misma ventana SAM como ablación controlada. Mantener ventana y escala comunes para comparar máscaras; medir máscaras antes de crop y fallos crudos además de contingencias. Preservar hojas salientes; tierra y planta en capas distintas, sin reconstrucción de regiones ocultas ni relleno generativo.

**Referencia y métricas planificadas:** anotación humana de planta/tierra/contaminación/incertidumbre a resolución nativa orientada en las 60, segunda revisión de todas y doble anotación independiente de veinte (8P/6H/6R), con adjudicación previa a predicciones de evaluación. Puntos de estructuras finas y órganos críticos para no favorecer máscaras que pierdan tallos. Medir recall/Dice/IoU por objeto, retención añadida por máscara/recorte, puntos finos, boundary-F1, contaminación, detalle proyectado a 224/384/1024, fallos, coste GPU y segundos/correcciones humanas. Los anotadores y la referencia real siguen pendientes; un LLM no los simulará como revisión experta.

**Análisis y decisión propuestos:** comparaciones pareadas, bootstrap de grupos estratificado (10.000 réplicas), intervalos Wilson de fallos, P separado y cobertura por año/cámara; no contar píxeles como réplicas independientes. Priorizar retención y órganos antes que eliminación de contexto. Umbrales iniciales de ingeniería: mediana de retención ≥99 %, al menos 95 % de fotos con retención ≥98 % y sin fallo crítico, además de comprobación separada en P; fijar al terminar calibración antes de evaluar. Elegir entre opciones aptas por compromiso detalle/contaminación/coste, no por una suma de pesos posterior. Con sólo 24 P, cero fallos deja límite Wilson superior cercano al 13,8 %; no certifica tasa poblacional <5 %. Los modelos posteriores requieren sus propios experimentos y roles intactos.

**Acción realizada y evidencia:** se redacta [especificación autónoma completa](doc/EXPERIMENTO_COMPARACION_PREPROCESADO_V1.md), con contratos de archivos, muestreo, anotación, algoritmos, prompts, versiones, formatos, transformación, métricas/fórmulas, reglas estadísticas, congelación, pruebas, entregables y criterios de revisión; se añade `exp_design/segmentation_benchmark_v1_plan.json` como plan estructurado con flags falsos de selección/congelación/ejecución. Se verifica documentación oficial de SAM 3: [repositorio](https://github.com/facebookresearch/sam3) y [procesador](https://github.com/facebookresearch/sam3/blob/main/sam3/model/sam3_image_processor.py). Versiones/checkpoint/API y capacidad real de hardware se fijarán en implementación, sin sustitución implícita por SAM 3.1 ni promesas de exactitud nativa.

**Estado de cierre de planificación:** documentos entregados para otro LLM; no se ejecutan selección, anotación, inferencia SAM, evaluación, entrenamientos ni migración. Primer hito del implementador: código revisable, dry-run del muestreo, plantillas, smoke-test/calibración y dependencias; evaluación bloqueada sólo después de revisión solicitada por el investigador y freeze. No cambian casillas numeradas ni registro/configuración/manifiestos/maestros congelados. Las fases de modelos y validación experta siguen pendientes.


### M040 · 2026-11-13 · Implementación revisable, muestreo reproducible, plantillas ciegas y calibración L0/L1 de `segmentation_benchmark_v1`

**Alcance y regla seguida:** se implementa la especificación [doc/EXPERIMENTO_COMPARACION_PREPROCESADO_V1.md](doc/EXPERIMENTO_COMPARACION_PREPROCESADO_V1.md) para el primer hito revisable, sin ejecutar la evaluación bloqueada (`--split evaluation`), sin migrar producción y sin simular anotaciones humanas ni salidas de SAM 3. Se conservan intactos `exp_design/preprocessing_registry.json`, `exp_design/preprocessing_fullframe_v2_frozen.json`, los manifiestos/listas vigentes y `tasks.md`.

**Código implementado bajo `scripts/segmentation_benchmark/`:**
- `common.py`: verificación de entradas protegidas por SHA-256, `oriented_srgb`, conversión `xyxy`/`cxcywh` normalizada, transformación isótropa única `present_isotropic` con relleno gris `(127, 127, 127)` y registro de entorno.
- `inventory_and_sample.py`: dry-run por defecto y materialización con `--write`. Comprueba 856 imágenes activas y 236 grupos coherentes en `C_fit`, 0 solapamiento de `split_group_id` con `C_val_model_selection`, `C_val_calibration`, `G_fit`, `T_real` y `M_aux` (sólo metadatos), excluye los 76 grupos expuestos en `development_v1/selection.json` para el panel nuevo y selecciona por SHA-256 (`20261113-roi-benchmark-v1`): 18 de calibración (`tuning`, 3 por año×especie sin casos de estrés), 60 de evaluación (`evaluation`, 2025/2026 con `P=12/H=9/R=9` y 20 asignadas a doble anotación `8P/6H/6R`), y 12 de estrés histórico (`stress`).
- `annotation_io.py`: rúbrica, registro `annotation_log.csv` (110 filas pendientes) y 90 plantillas JSON ciegas (`tuning=18`, `evaluation=60`, `stress=12`) sin `species_code`, `design_species_code`, códigos de método ni métricas; validación PNG uint8 `L` 0/255, disjunción de capas, puntos finos (máx. 20) y acuerdo entre observadores.
- `run_methods.py`: adaptadores `L0` (encuadre completo), `L1` (Hough a 400 px + HSV a 800 px + rectángulo acotado), `S1` (adaptador real SAM 3 con estados independientes para `"plant"` y `"soil"` y asociación por disco `0,9r` y suelo dilatado `0,1D` conservando instancias enteras) y bloqueo estricto de `--split evaluation` sin `freeze.json`.
- `render_views.py`, `score.py`, `report.py`, `validate_run.py`: renderizado `V0..V5` a `224/384/1024` con fallback explícito, métricas en coordenadas nativas excluyendo `ignore_uncertain`, bootstrap estratificado determinista (10.000 réplicas), intervalos Wilson 95 %, informe/hojas anónimas y verificación de integridad.

**Resultados reales observados en esta sesión:**
- Pruebas unitarias (`python -m unittest discover -s scripts\segmentation_benchmark\tests -v`): **11/11 tests correctos** en 0,317 s (máscara fina 1 px, rotación EXIF, `xyxy`/`cxcywh`, RGB interior intacto, aspecto isótropo, recorte de margen, aislamiento de prompts en adaptador `S1`, asociación de instancia completa, métricas con `G` vacío / `M` vacío / `ignore_uncertain`, bootstrap determinista / Wilson y bloqueo sin `freeze.json`).
- Entorno verificado: Python 3.12.1, Pillow 13.0.0, NumPy 2.5.4, OpenCV 5.0.0 (`scratch/opencv_runtime`), GPU detectada `NVIDIA GeForce RTX 3070 Ti Laptop GPU` (8192 MiB, driver 581.29).
- Calibración real sobre `--split tuning` (18 imágenes) en `data/processed/preprocessing/segmentation_benchmark_v1/`:
  - `L0`: 18 `ok` (mediana total 0,133 s).
  - `L1`: 17 `ok`, 1 `fallback_no_green_component` (mediana total 0,756 s; inferencia 0,503 s).
  - `S1`: 18 `dependency_missing` (`PyTorch/SAM3 not available (No module named 'torch')`), sin resultados simulados.
  - Vistas `tuning` (`224/384/1024`): `V0` 18/18 `ok`, `V1` 17 `ok` + 1 `fallback_fullframe`, `V2..V5` 18/18 `fallback_fullframe` por dependencia `S1` pendiente; 18 hojas anónimas en `figures/tuning/` y `report_tuning.md`.
- Validación (`validate_run.py`): `all_passed=true`, `protected_inputs_verified=true`, 90 originales verificados por SHA-256, 60 plantillas de evaluación sin fuga de especie y `freeze_exists=false`.

**Dependencias pendientes antes de completar calibración `S1`, congelación y evaluación:**
1. Entorno GPU aislado con PyTorch ≥ 2.7, CUDA ≥ 12.6, paquete oficial `sam3` y checkpoint oficial verificado por SHA-256/commit para ejecutar el smoke-test real de `S1` sobre `tuning` (18 imágenes) y fijar umbral/VRAM/tiempos.
2. Anotadores humanos para trazar y adjudicar la verdad de referencia (`annotations/consensus/`) sobre `tuning` y posteriormente las 60 de `evaluation` (con 20 dobles ciegas) antes de crear `freeze.json`.

### M041 · 2026-11-13 · Revisión independiente de la implementación entregada en M040

**Alcance:** ante la entrega del implementador se revisa el código contra M039 y su especificación. No se ejecuta evaluación bloqueada, SAM o entrenamiento, no se instalan paquetes, no se modifica la implementación recibida ni se migra producción. Se añaden sólo informe, comprobador independiente y evidencia de revisión. Las pruebas adversariales usan archivos temporales y máscaras sintéticas; no son anotaciones humanas ni salidas SAM del dataset.

**Comprobaciones positivas observadas:** los once tests entregados pasan de nuevo. Reconstrucción en memoria del muestreo: listas tuning/evaluation/stress exactamente iguales a las publicadas, con cuotas y disjunción previstas. Los hashes del código inventariado coinciden en este momento. Los dieciocho círculos L1 de tuning coinciden con las propuestas Hough históricas correspondientes, diferencia máxima cero píxeles; no se afirma equivalencia exhaustiva de toda la tubería. Se verifica registro y entradas protegidas. Ausentes freeze, predicciones/vistas de evaluación y casos de consenso humano. S1 sigue sin ejecución real; sus dependencias pendientes no se consideran resultados de segmentación.

**Defectos reproducidos en fixtures temporales:** (R1) crear freeze sólo con sesenta metadata vacíos, sin máscaras/calibración/checkpoint, es aceptado; editar después un script listado o la referencia no es detectado por la puerta, y se puede sobrescribir freeze. (R2) scoring con GT/predicciones/vistas faltantes finaliza omitiendo entidades/casos del denominador. (R3) eliminar un órgano crítico completo pequeño sin perder más del 2 % de área no dispara fallo porque el campo de órganos no se consulta; también se cuentan puntos dentro de ignore. (R7) planta sin suelo devuelve ok para la asociación y permite presentar planta+tierra incompleta. La función bootstrap devuelve mediana de diferencias pareadas, distinta de diferencia de medianas: el fixture distingue 1 frente a 99; definir estimando antes de usarlo.

**Hallazgos por lectura de código:** configuración alternativa no ligada a freeze; inventario no verificado contra archivos efectivos y GT no ligada por hash; bootstrap no integrado en score_split, faltan detalle por resolución/contrastes completos y revisión de órganos; ramas S2/L2 aún no implementadas pese a mención en encabezado/configuración. En SAM faltan pin efectivo, dtype/calentamientos, registro por imagen de errores de inferencia, resultados brutos y costes/caché completos. No se prueba rendimiento GPU ni suficiencia de 8 GB. El all_passed del validador cubre seis clases de comprobación de inventario/plantillas, no garantiza corrección metodológica completa.

**Dictamen y acción pendiente:** base útil para continuar desarrollo, no aprobada aún para congelar/evaluar. Corregir primero garantías de freeze/denominadores y criterio morfológico; después conectar análisis, asistencia o alcance explícito y trazabilidad SAM, y completar referencia humana y calibración real. No basta con instalar dependencias y anotar para cerrar estas incidencias. La revisión no cambia umbrales, muestras, particiones, maestros ni casillas futuras.

**Evidencias:** [informe con R1–R7, localizaciones y criterios de aceptación](doc/REVISION_SEGMENTATION_BENCHMARK_V1.md), [resultado de fixtures y comprobaciones](doc/REVISION_SEGMENTATION_BENCHMARK_V1_CHECKS.json), `scripts/review_segmentation_benchmark_v1.py`. Sus flags defect_* verdaderos indican defectos reproducidos, no aceptación del benchmark. Se conserva M040 como historia de entrega y se matiza su alcance mediante esta entrada.

### M042 · 2026-11-13 · Guía práctica para producir máscaras humanas independientes

**Consulta:** cómo deben ser las máscaras humanas, qué software usar y cómo trazarlas. Se consulta la rúbrica/validador implementados y las incidencias M041 antes de recomendar un flujo.

**Recomendación, no adopción ejecutada:** CVAT con máscara/pincel y polígonos manuales, empezando con tres imágenes de tuning para verificar ida/vuelta antes del lote. Usar copias nativas EXIF-orientadas/sRGB, nombres anónimos y mapa privado de procedencia. Mantener planta y suelo separados; planta incluye órganos finos y hojas salientes, suelo sólo superficie visible dentro de maceta. Conservar clases de contaminación e incertidumbre y no completar tejido/suelo ocultos. La referencia independiente no parte de SAM/HSV ni de selección automática por color; asistencia algorítmica pertenece a otra rama.

**Acción realizada:** se entrega [guía práctica](doc/GUIA_MASCARAS_HUMANAS_BENCHMARK.md) con etiquetas, secuencia de dibujo/revisión, puntos/órganos, exportación y límites. Los PNG finales deben ser L uint8 0/255 y tamaño nativo orientado; un export de clases CVAT necesita conversión por mapa de etiquetas, no un umbral de luminancia. Se documenta que lote de copias para CVAT/adaptador de importación y esquema de órganos críticos siguen pendientes; las plantillas existentes no son una tarea CVAT lista ni máscaras humanas. No se modifican código, rúbrica congelable, muestras o producción.

**Fuentes verificadas:** [CVAT, pincel/máscara](https://docs.cvat.ai/docs/manual/advanced/annotation-with-brush-tool/) y [Segmentation Mask export](https://docs.cvat.ai/docs/dataset_management/formats/format-smask/). La capacidad de software no certifica calidad de las anotaciones del proyecto. No se instala herramienta, suben imágenes, anotan casos ni ejecuta evaluación en esta sesión. Continúan pendientes correcciones M041 y anotación/revisión humanas de M039.

### M043 · 2026-11-13 · Reorganización numerada, mapa de experimentos y utilidad de copias

**Solicitud y autorización:** el investigador declara haber perdido el hilo de experimentos/documentación y solicita reorganizar y numerar archivos salvo datasets de imágenes, además de estudiar si las copias son útiles. Ante la distinción entre numerar documentación e indexar archivos técnicos o migrar también sus nombres, elige explícitamente migrar los nombres técnicos. La acción es administrativa y de trazabilidad; no cambia el diseño, etiquetas, grupos, funciones, transformaciones ni conclusiones experimentales.

**Decisión y alcance:** numeración local de 103 archivos en raíz, doc, scripts, exp_design y scripts auxiliares de scratch; módulos `sNN_` y tests `test_NN_` mantienen identificadores Python y descubrimiento de pruebas. Se actualizan importaciones, rutas literales/dinámicas de diseños, comandos y enlaces activos, entradas/bibliografía/logo de LaTeX. Se mantienen los nombres contractuales AGENTS.md, BITACORA_METODOLOGICA.md, tasks.md y __init__.py. Datasets completos y metadatos internos, .venv, dependencias de terceros y payload del archivo histórico quedan exceptuados. No se renumeran las tareas ni se atribuye orden de ejecución a los números de archivo.

**Preservación explícita:** antes del cambio se copian los originales técnicos con nombres y bytes anteriores a `99_archivo/01_antes_reorganizacion`; el mapa `organizacion/03_mapa_migracion.json` y CSV registra rutas anteriores/actuales y hashes de ambos. Configuración fullframe congelada, tabla de asignaciones y plan v1 conservan sus bytes aun con nuevo nombre. El registro activo `exp_design/12_preprocessing_registry.json` actualiza rutas sin cambiar las huellas de configuración, entrega o listas. La bitácora histórica y los informes dentro de datasets no se reescriben: sus rutas anteriores se resuelven por el mapa. Los auditores migrados distinguen código de producción histórico preservado y código activo con hashes nuevos; guardan recibos nuevos en organizacion. No reanudar con código migrado el fingerprint de una ejecución histórica. No se presenta esta migración como una nueva versión de imágenes o una repetición del experimento de preparación.

**Navegación entregada:** [inicio](00_LEEME.md), [mapa E01–E08](organizacion/10_MAPA_EXPERIMENTOS.md), índices 00_INDICE por directorio de trabajo, [utilidad de copias](organizacion/11_UTILIDAD_COPIAS.md), inventario JSON y duplicados CSV. Se distinguen manifiestos/particiones y fullframe activos, escala métrica histórica, ensayo ROI realizado, benchmark en desarrollo con R1–R7 pendientes y modelos/panel aún no ejecutados. tasks.md enlaza estas guías sin cerrar nuevas casillas científicas.

**Observaciones verificadas sobre copias:** inventario de 5.371 archivos de imagen en data, sample, analisis_muestra y scratch/roi_small_trial. Incluye figuras auxiliares; no son 5.371 fotografías independientes. Agrupación por longitud de archivo y SHA-256 de los 3.693 archivos con tamaño repetido: 1.648 grupos de identidad binaria. Se localizan originales idénticos en raw para 1.450 de las 1.451 copias de verificación (7,079409 GB), y para doce de trece imágenes de sample (40,472 MB). La carpeta de verificación completa ocupa 7,083309 GB en imágenes y conserva utilidad de revisión; sus nombres no son etiquetas finales. Se conservan sin equivalente exacto localizado sample/DSC_0286.JPG y data/verificacion_siembra/2026-06-10_c2_r2/0082_Amaranthus_hybridus_F4C4_DSC_0212.JPG. No se atribuye causa a esa diferencia ni se relaciona con DSC_0380; M022 permanece aceptada y no se reabre. Las tres vistas scratch/roi_small_trial no tienen duplicado binario externo localizado, aunque pueden ser regenerables. Los dos lotes fullframe_development_v2/v3 suman 828,428501 MB de imágenes históricas; su carácter de desarrollo no demuestra identidad binaria ni autoriza borrar sus metadatos/evidencias. Los maestros activos ocupan 6,374574 GB. Se conserva scratch/opencv_runtime como dependencia usada por el benchmark.

**Resultado comprobado:** 24 pruebas existentes correctas (13 de procesadores y 11 de benchmark), muestreo dry-run correcto con 856 C_fit/236 grupos y cuotas intactas, constructor de manifiestos carga y muestra ayuda con el entorno existente, auditoría de cierre migrada correcta sobre hashes de los 1.451 originales y 1.419 maestros, validación ROI con quince comprobaciones correctas. Se verifica sintaxis Python, los 103 originales archivados, bytes de entradas congeladas y 922 archivos de metadatos de datasets sin cambios. No se regenera el corpus ni se inspecciona T_real visualmente. Las comprobaciones actuales son de integridad/migración y no superioridad predictiva ni aceptación del benchmark. Evidencias: `organizacion/12_auditoria_cierre_migrado.json`, `13_validacion_organizacion.json`, `14_validacion_roi_migrada.json` y registro de pruebas.

**Límites y pendientes:** no se elimina ninguna imagen ni se reclama espacio recuperado. Se documentan candidaturas condicionales de limpieza; conservar originales, entrega activa, referencias/evidencias y toda copia sin equivalencia acreditada. Dos referencias externas del plan se conservan sin verificarlas. Se revisan referencias LaTeX pero no se compila ni se afirma actualizado el PDF preexistente. Las rutas históricas requieren el mapa y las verificaciones de hashes históricos consultan el archivo preservado. No se ejecutan SAM, evaluación bloqueada, anotación humana o entrenamientos; M041 y las tareas futuras mantienen su estado.

### M044 · 2026-11-13 · Reserva de doc para el escrito del TFM y ajuste de numeración

**Solicitud del investigador:** `doc/` debe contener exclusivamente los documentos destinados al escrito del TFM. Se sustituye la organización de M043 que mezclaba allí memoria, informes técnicos y protocolos; no se rectifica ninguna conclusión experimental.

**Acción realizada:** se trasladan seis documentos técnicos: auditoría de datos, revisión de preprocesado, revisión del benchmark y su JSON de comprobaciones a `documentacion/01_informes` (01–04); especificación de comparación y guía de máscaras humanas a `documentacion/02_protocolos` (01–02). Los auxiliares de compilación anteriores (ocho archivos) se conservan en `99_archivo/02_compilacion_previa`. Los 24 archivos movidos o renombrados tienen copia previa verificada por hash en `99_archivo/03_antes_separar_doc` y recibo en `organizacion/21_migracion_documentacion.json`.

**Numeración y referencias:** la fuente principal pasa a `doc/01_memoria.tex` y el PDF existente a `doc/02_memoria_previa.pdf`. Los seis capítulos quedan `01_introduccion`, `02_estado_arte`, `03_metodologia`, `04_resultados`, `05_discusion`, `06_conclusiones`, eliminando los prefijos duplicados. Preliminares: 01_portada, 02_agradecimientos, 03_resumen. Se actualizan inclusiones LaTeX, referencias activas, índices, generador de navegación y rutas de documentación emitidas por scripts. El mapa general anterior→actual se actualiza sin perder sus nombres originales. La selección previa de capítulos incluidos en la memoria no se altera.

**Resultado verificado:** la raíz de doc contiene sólo índice de redacción, fuente y PDF previo; subcarpetas de capítulos, preliminares, anexos, bibliografía, figuras, tablas, configuración y recursos sirven al escrito. No quedan JSON, informes/protocolos experimentales ni auxiliares de compilación dentro de doc. Once referencias LaTeX (incluido agradecimiento comentado, bibliografía y logo) resuelven a archivos existentes. Las siete comprobaciones de alcance/referencias/archivo son correctas en `organizacion/23_validacion_documentacion_tfm.json`. El comprobador general confirma sintaxis Python, los 103 originales archivados, 922 metadatos de datasets sin cambios y ausencia de enlaces Markdown activos rotos; conserva dos referencias externas sin verificar. Se documenta dirigir futuras compilaciones a scratch/compilacion_tfm.

**Alcance y límites:** sólo organización documental; no se compila el PDF ni se afirma actualizado. No se modifican imágenes, manifiestos de datasets, particiones, parámetros, anotaciones ni estado de tareas científicas. tasks.md y AGENTS.md incorporan la separación para próximas sesiones. La bitácora y los documentos congelados conservan sus rutas históricas, resolubles mediante el mapa de migración.
