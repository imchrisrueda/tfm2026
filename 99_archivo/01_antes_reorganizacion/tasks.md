# Tareas del proyecto

Última actualización: 13 de noviembre de 2026.

**Comparación objetiva planificada (M039):** [especificación autónoma para implementación y revisión](doc/EXPERIMENTO_COMPARACION_PREPROCESADO_V1.md): 18 imágenes de calibración, 60 de evaluación interna en grupos nuevos y doce casos históricos de estrés, con referencia humana y comparación de HSV/SAM/recorte/planta/planta+tierra. Sólo planificación; no se ejecutó ni se cierran casillas por este documento. La entrega congelada sigue vigente.

**Prueba suplementaria de preparación (M034–M037):** completado el [contraste pequeño de encuadre y ROI maceta+verde](data/processed/preprocessing/roi_small_trial_v1/README.md). Favorece una candidata rectangular con revisión y contingencia para entradas futuras; no migra la entrega congelada ni acredita rendimiento de modelos. Las casillas existentes conservan su alcance histórico M029–M032. El contraste de aprendizaje y la decisión de entradas siguen pendientes en 25–27/33/35; no se cierran nuevas tareas con este ensayo.

Esta es la lista de seguimiento hasta la entrega del proyecto. Resume el [plan principal](PLANIFICACION_TFM.md) e incorpora las decisiones de la [bitácora metodológica](BITACORA_METODOLOGICA.md). El detalle de escala está en [su protocolo](PROTOCOLO_ESCALA_MACETAS.md).

**Cómo usarla:** `[x]` significa completado con resultado registrado; `[ ]` significa pendiente o parcialmente realizado. Al terminar un paso, marcar su casilla y registrar en la bitácora qué se hizo, el resultado y dónde está la evidencia. Conservar los números para poder referirnos a cada tarea. Una fase sólo está cerrada cuando se completan sus tareas aplicables.

**Situación actual · M029–M032:** tareas **1–20 completadas** en el alcance revisado y documentado de M029. Se compararon alternativas y se fijó encuadre completo, aspecto exacto y lado máximo 2048 px, sustituyendo 12/22 cm y la normalización métrica obligatoria. Hay **1.419 maestros auditados**, 32 filas inactivas sin maestro y listas por función con v1 intacta. Las 91 referencias de desarrollo son exploratorias (84 medidas provisionales y siete no medibles); no se afirma cm/píxel común ni calibración de producción. La tarea 45 y los lectores/entrenamientos futuros siguen abiertos. Siguiente bloque: preparación de ejecución, tarea 21. Evidencias: [entrega](data/processed/preprocessing/fullframe_v2/release/README.md), [revisión de alternativas](doc/REVISION_PREPROCESADO_2026-11-12.md) y bitácora M032.

## P0 · Inventario, etiquetas y grupos

1. [x] Inventariar todas las fotografías disponibles, incluidas las subcarpetas. El conjunto actual contiene 1.451 fotos de 15 sesiones; conservar la historia del inventario inicial y de las 23 fotos retiradas.
2. [x] Comprobar integridad, lectura, metadatos y duplicados exactos. Evidencia: [auditoría inicial](doc/AUDITORIA_DATOS_CRUDOS_2026-11-12.md) y [validación vigente](data/processed/manifest_validation.json).
3. [x] Aclarar el orden de adquisición, las selecciones, las fotos de dos cámaras y la sesión incompleta; incorporar las reglas al manifiesto vigente.
4. [x] Registrar la revisión de C2R2 y corregir a palmeri las ocho fotos de F26C1 y F4C4, conservando especie de diseño, causa y fuente de confirmación.
5. [x] Identificar las macetas y registrar su continuidad entre fechas y cámaras mediante grupos. Quedan 400 identificadores de grupo en el conjunto; esta cifra no acredita por sí sola independencia entre repeticiones.
6. [x] Establecer y registrar las nueve exclusiones conocidas del entrenamiento principal y el uso separado del maíz auxiliar.
7. [x] Generar y validar los manifiestos de 2025, 2026 y del conjunto, con fuentes, correcciones, grupos, siembra y campos desconocidos explícitos. Evidencia: [manifiestos vigentes](data/processed/README_manifiestos.md).
8. [x] Crear la bitácora metodológica y establecer su actualización continua para documentar decisiones y resultados.
9. [x] Resolver el cambio de contenido de `2025-06-20_c1_r2/nikon_d70/DSC_0380.JPG`: por decisión del investigador se conserva tal como está, manteniendo el registro histórico. Las 23 Nikon de esa subcarpeta quedan fuera del reparto inicial porque esa adquisición está incompleta; se usarán las 60 fotos completas del iPhone fuera de ella. Evidencia: bitácora M022 y política de adquisición.
10. [x] Registrar y aceptar como suficientes para avanzar las indicaciones del investigador sobre plantas secas/muertas, ausencia y cantidades cuando constan. Se cierra por su instrucción, manteniendo las exclusiones y las notas disponibles; no se inventan recuentos observados ni estadios que no se hayan aportado. Véase bitácora M023.

## P1 · Particiones y protección de la evaluación

11. [x] Fijar los criterios v1: aproximadamente 20 % de grupos palmeri para generación y 70/15/15 del resto para clasificador, validación y prueba, estratificados por especie, año, repetición y densidad nominal/sembrada. Semilla 20261112 y reserva de las 23 Nikon; límites documentados en M024.
12. [x] Asignar por grupos C_fit (856 fotos/236 macetas), C_val (190/54), G_fit palmeri (86/24), T_real (164/46) y M_aux (123/40), sin macetas compartidas. Los archivos excluidos o de reserva no entran en las listas activas.
13. [x] Separar C_val en configuración (92 fotos/27 macetas) y calibración (98/27), con macetas distintas, tres especies y ambos años.
14. [x] Verificar y guardar la asignación v1, su semilla, huella de entradas y controles de ausencia de solapamiento. Evidencia: [particiones v1](data/processed/partitions/v1/README.md) y su validación. T_real queda reservado antes del entrenamiento, sin haberlo usado para ajustar un modelo.

## P2 · Escala y preparación de imágenes

15. [x] Seleccionar un lote de desarrollo representativo para preparar el preprocesado, sin usar T_real para decidirlo. Resultado: 91 fotos/76 macetas, 15 sesiones, tres especies, cuatro cámaras y EXIF 1/3/6/8; selección determinista sólo de C_fit activo.
16. [x] Completar la medición/revisión exploratoria del lote: 91 fichas, 84 medidas provisionales de centro/borde/diámetro nominal y aparente y siete referencias no medibles con nulos/motivo. Se conservan puntos/extremos, ejes, método y calidad; todas siguen `pilot_only`. No equivale a calibración o repetibilidad independiente, que sigue en tarea 45. Evidencia: `development_geometry_v3` y fe de erratas descriptiva de entrega.
17. [x] Resolver y fijar la estrategia de encuadre tras comparar diez alternativas en desarrollo: M029 sustituye la normalización física obligatoria y los campos 12/22 cm por encuadre completo y proporciones aparentes conservadas. No se consigue ni se afirma cm/píxel común o margen físico añadido al original. Cierre por decisión revisada explícita, no por haber logrado un campo métrico universal.
18. [x] Implementar y congelar EXIF, color sRGB, redimensionado isotrópico con aspecto exacto, lado máximo 2048 px y coordenadas completas de origen. Piloto de 91 y corpus final auditados; 13 pruebas unitarias correctas y los 1.419 rasters reconstruidos exactamente con la transformación fijada.
19. [x] Revisar el lote de desarrollo por especie, año y cámara, detalle a 1024/1536/2048, límites de referencia/captura y conservación del encuadre. Registrar siete referencias no medibles y fallos de las alternativas métricas sin nuevas exclusiones generales, borrado o reconstrucción de tejido. Auditoría técnica completa del corpus, separada de aptitud métrica y de validación botánica; no se atribuye inspección experta de todas las fotos.
20. [x] Congelar y entregar 1.419 maestros con 32 filas inactivas, manifiestos de ejecución/entrega de 1.451 filas, rutas/hashes, 91 fichas exploratorias y listas C_fit/C_val_model_selection/C_val_calibration/G_fit/T_real/M_aux separadas. Auditoría exhaustiva correcta (23.018 comprobaciones), fe de erratas sólo descriptiva de nueve fichas, archivo reproducible y registro activo en `exp_design/preprocessing_registry.json`. T_real se transforma técnicamente sólo después de congelar y no elige parámetros.

## Preparación de ejecución · Se abordará después de los datos

21. [ ] Verificar el entorno real de DRAGO, los recursos accesibles y las condiciones de ejecución, sin inferirlos de documentación histórica.
22. [ ] Preparar y fijar entorno, versiones, pesos de modelos, acceso necesario y semillas; guardar la configuración reproducible.
23. [ ] Transferir los datos y manifiestos necesarios y comprobar su integridad en destino.
24. [ ] Ejecutar una prueba corta de lectura, uso de recursos y guardado de resultados en un nodo asignado; registrar errores, memoria y duración antes de los trabajos completos.

## P3 · Clasificador inicial y referencias BioCLIP

25. [ ] Implementar el lector de datos con las tres especies, etiquetas corregidas, exclusiones, grupos y transformaciones acordadas; mantener el maíz fuera del entrenamiento del clasificador.
26. [ ] Ejecutar el primer piloto ConvNeXt-Tiny con C_fit y validación de desarrollo; comprobar carga, entrenamiento, métricas por especie y guardado de checkpoints.
27. [ ] Elegir la configuración y resolución en desarrollo —piloto a 224 × 224 y contraste a 384 × 384 sólo si se justifica—, preservando el campo y sin recortes centrales inadvertidos.
28. [ ] Entrenar el clasificador con la configuración elegida y registrar semillas, pérdidas, métricas y errores en validación; examinar posibles pistas de fondo, cámara o tarjeta.
29. [ ] Calibrar y fijar los umbrales por especie con la reserva correspondiente de C_val; comprobar la interpretación de los scores si se presentan como probabilidades.
30. [ ] Congelar pesos, transformaciones y regla de candidata/confusión/ambigua/rechazada. Registrar matriz de confusión, métricas por clase y macro-F1 de validación; reservar la evaluación final de T_real para la tarea 52.
31. [ ] Preparar BioCLIP, fijar checkpoint y transformaciones, y construir las referencias reales con C_fit; documentar su reutilización y conservar el campo de imagen.

## P4 · Piloto generativo y tres entrenamientos LoRA

32. [ ] Definir el alcance de la primera prueba: escena completa o generación localizada de la planta sobre un fondo. Para la segunda opción, elegir y preparar el procedimiento y las regiones necesarias; no asumir que un LoRA de escenas aprende sólo la planta.
33. [ ] Preparar un lote revisado de G_fit con imágenes y leyendas de texto en el formato del entrenador. Usar atributos comprobados; no convertir plantas sembradas en plantas visibles ni inventar estadios. Los posibles fondos auxiliares requieren revisión separada.
34. [ ] Ejecutar un piloto LoRA corto después de disponer del clasificador base y de las entradas preparadas; comprobar memoria, duración, carga de leyendas, encuadre y comportamiento de las salidas.
35. [ ] Fijar la configuración común de los tres entrenamientos, resolución, pasos, parámetros LoRA, criterio de checkpoint y presupuesto. Separar semillas de entrenamiento y de generación; no elegir checkpoint buscando favorecer el clasificador auditor.
36. [ ] Ejecutar y registrar el entrenamiento LoRA 1 con su primera semilla.
37. [ ] Ejecutar y registrar el entrenamiento LoRA 2 con otra semilla y la misma configuración.
38. [ ] Ejecutar y registrar el entrenamiento LoRA 3 con otra semilla y la misma configuración.
39. [ ] Fijar la matriz común de prompts, condiciones y semillas de generación para comparar los tres adaptadores, usando combinaciones respaldadas por los datos.
40. [ ] Generar y conservar el corpus completo con identificadores, adaptador, prompt, condición, semilla y checkpoint; registrar también fallos, sin seleccionar sólo imágenes favorables.

## P5 · Auditoría de todas las generaciones

41. [ ] Aplicar el clasificador congelado a todas las salidas y guardar scores, estados y errores de procesamiento.
42. [ ] Calcular similitudes BioCLIP frente a las referencias reales, conservando configuración y trazabilidad; no añadir un umbral de aceptación sin validación.
43. [ ] Revisar escala, maceta, vegetación cortada, número de plantas y otros defectos; buscar vecinos próximos de G_fit como comprobación de posibles copias, sin afirmar que descarta toda memorización.
44. [ ] Consolidar la tabla de auditoría con todos los resultados y sus denominadores, incluidos rechazos, ambigüedades y casos no procesables.

## P6 · Evaluación ciega y medición del panel

45. [ ] Fijar rúbrica, método de medición y tolerancias de escala con datos reales de desarrollo y anotaciones repetidas, antes de ver qué generaciones se desea aprobar.
46. [ ] Definir y congelar el panel: evaluación exhaustiva o muestreo aleatorio por ejecución y estado, incluidos rechazos e incidencias. Guardar probabilidades y pesos si hay muestreo e incluir controles reales de T_real sin usarlos para ajustar.
47. [ ] Preparar códigos, orden y formulario ciego para A, B y C, ocultando origen real/sintético, ejecución, scores y decisiones automáticas; mantener presentación y campo comparables.
48. [ ] Recoger las evaluaciones independientes de los tres expertos sobre el mismo panel, con identificación de especie, aptitud morfológica y estados inciertos o no evaluables.
49. [ ] Medir las proporciones y la escala del mismo panel; registrar referencias, errores y casos no evaluables sin corregir las imágenes para ocultar desviaciones.

## P7 · Evaluación final, selección y análisis

50. [ ] Aplicar la regla de validación experta: al menos dos expertos deben coincidir individualmente en especie palmeri y aptitud morfológica. Seleccionar sólo los casos que cumplan además candidatura automática y control de escala/escena.
51. [ ] Analizar acuerdo entre expertos e instrumentos, diferencias entre ejecuciones, falsos rechazos y fallos botánicos o geométricos; conservar todos los estados y usar ponderación cuando el panel sea una muestra desigual.
52. [ ] Evaluar el clasificador y el sistema ya congelados sobre T_real, sin reajustarlos a partir de esa prueba; presentar métricas y sus límites.
53. [ ] Evaluar el rechazo del maíz M_aux por separado, sin ajustar con sus resultados ni mezclarlo con las métricas principales de las tres especies.
54. [ ] Cerrar los resultados y materiales: corpus íntegro, candidatas automáticas, subconjunto efectivamente validado y casos discrepantes; explicitar denominadores, representatividad, sesgos y límites de generalización.

## P8 · Redacción, reproducción y entrega

La redacción y la organización de evidencias pueden avanzar en paralelo desde ahora; no hay que esperar a terminar los modelos.

55. [ ] Confirmar título, requisitos formales y calendario con Raquel, y completar introducción, objetivos y estado del arte. Las fechas oficiales de depósito y defensa no están establecidas en los archivos revisados.
56. [ ] Redactar la metodología a partir de decisiones y procedimientos realmente ejecutados en la bitácora, incluyendo particiones, transformaciones, semillas y criterios congelados.
57. [ ] Redactar resultados, discusión y conclusiones con las evidencias obtenidas; separar hallazgos, limitaciones y propuestas futuras, sin presentar resultados anticipados como realizados.
58. [ ] Preparar anexos y materiales de reproducción: manifiestos, particiones, geometría, leyendas/prompts, código, configuraciones, adaptadores y tablas de evaluación según lo permitido y disponible.
59. [ ] Revisar el documento completo: figuras, tablas, bibliografía, referencias cruzadas, compilación PDF, coherencia de cifras y acceso a los materiales.
60. [ ] Entregar la memoria completa a Raquel y registrar la fecha y la versión enviada. El objetivo del plan es el 28 de noviembre de 2026; confirmar su vigencia al revisar el calendario, sin confundirlo con un depósito o defensa oficial.

## Actualización del seguimiento

Los objetivos de fechas del plan original no significan que las tareas se hayan ejecutado. Este archivo registra el estado comprobado, no una previsión de éxito. Si cambia un procedimiento, actualizar la tarea correspondiente y añadir en la bitácora el motivo y el resultado; si cambia el alcance, añadir las tareas necesarias sin perder la referencia a los números existentes.
