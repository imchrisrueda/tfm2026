# Especificación para implementar una comparación objetiva de preprocesamiento

Versión 1 propuesta · 13 de noviembre de 2026 · bitácora M039.

**Estado: planificación; no se ha seleccionado el panel, anotado verdad de referencia ni ejecutado SAM o modelos con este protocolo.** Este documento es autónomo y está dirigido a un LLM que implementará el experimento. Debe entregar código, configuración y validaciones para revisión antes de ejecutar la evaluación bloqueada. No debe migrar la preparación vigente ni interpretar esta propuesta como resultados.

## 1. Objetivo y pregunta de decisión

El proyecto estudia un clasificador de tres especies de Amaranthus y, posteriormente, generación sintética de A. palmeri con máximo detalle y fidelidad morfológica. Se desea reducir información ajena a la planta sin borrar hojas, tallos, pecíolos ni tejido sombreado. Comparar: encuadre completo, recorte guiado por maceta/verde, localización/segmentación SAM 3, planta aislada y planta+tierra sin maceta.

Separar preguntas:

1. ¿Qué método conserva mejor el tejido visible y los órganos finos, y cuánto contexto elimina?
2. ¿Qué método permite presentar más detalle al mismo tamaño de entrada sin deformar?
3. ¿Cuánto trabajo humano y cómputo requiere obtener una salida aceptable?
4. En una fase posterior, ¿mejora clasificación o fidelidad generativa? La calidad geométrica de máscaras no responde por sí sola a esta última pregunta.

No se busca reconstruir tejido oculto o fuera de captura. No se asume que SAM reconozca correctamente la especie. Planta+tierra no equivale a planta sola. No se impondrá cm/píxel común ni certificación 3D.

## 2. Contexto y contratos del repositorio

Raíz: `C:/Users/christianr/Desktop/tfm2026`. Leer `AGENTS.md`, `BITACORA_METODOLOGICA.md` (especialmente M022–M024 y M029–M039), `tasks.md` y `data/processed/preprocessing/README.md` antes de implementar.

- Etiquetas de trabajo: H=Amaranthus hybridus, P=Amaranthus palmeri, R=Amaranthus retroflexus. Conservar `design_species_code` aparte de `species_code`. No inferir etiquetas de nombres en `data/verificacion_siembra`.
- Manifiestos autoritativos: los construye `scripts/s05_build_dataset_manifests.py` con `exp_design/14_species_corrections.csv`. Leer `data/processed/README_manifiestos.md`; no regenerarlos con reglas históricas ni modificarlos a mano.
- Partición congelada v1: `exp_design/07_partition_assignments_v1.csv`, `08_partition_plan_v1.json`. Unidad de continuidad: `split_group_id`; distintas fechas/cámaras de la misma maceta permanecen juntas. No afirmar independencia biológica adicional entre repeticiones no documentada.
- Preparación vigente: `exp_design/12_preprocessing_registry.json`, que apunta a `exp_design/10_preprocessing_fullframe_v2_frozen.json` y `data/processed/preprocessing/fullframe_v2/release/manifest_prepared.json`. Hay 1.419 maestros PNG, encuadre completo, aspecto exacto, máximo 2048 px; 32 filas inactivas. Las 91 fichas de geometría son exploratorias: 84 provisionales y siete no medibles. Ninguna calibra producción.
- Consumir para este experimento la lista `data/processed/preprocessing/fullframe_v2/release/partitions/C_fit.json`: es una lista JSON de filas, 856 imágenes. Exigir `use_in_assigned_partition=true` y `split_assignment=C_fit`. Unir por `image_id` y SHA-256 original (`sha256`), nunca sólo por nombre. `source_path` es relativa a la raíz; no confundir `sha256` con `master_sha256`.
- Sólo C_fit para ajustar y evaluar preprocesamiento en esta fase. No decodificar T_real, C_val_calibration, C_val_model_selection, G_fit o M_aux. G_fit es exclusivamente entrenamiento generativo posterior; no alimenta el clasificador. La evaluación aquí es una reserva interna de desarrollo, no una prueba final independiente del proyecto.
- Reserva de adquisición: 23 Nikon de `2025-06-20_c1_r2/nikon_d70` inactivas; no excluir otras sesiones Nikon. DSC_0380.JPG está aceptado tal como está (M022), no reabrirlo ni restaurarlo.

La prueba anterior `data/processed/preprocessing/roi_small_trial_v1/README.md` usó doce casos dirigidos C_fit, envolventes aproximadas de Codex y parámetros exploratorios. Rectángulo automático maceta+verde: once recortes y una contingencia; no se entrenó ningún modelo. No usar esos datos como evaluación nueva ni como evidencia de exactitud de segmentación.

## 3. Submuestras y aislamiento de ajustes

Semilla propuesta única: `20261113-roi-benchmark-v1`. Crear los conjuntos antes de ejecutar algoritmos o revisar sus salidas. Registrar universo, huellas, exclusiones, probabilidades de selección y reglas exactas en `sampling.json`; conservar todas las filas candidatas con motivo de inclusión/exclusión.

### 3.1 Calibración técnica: 18 imágenes

Usar grupos ya expuestos en `data/processed/preprocessing/development_v1/selection.json`, evitando grupos del panel de doce casos si es factible. Tres grupos distintos por combinación año (2025/2026) × especie (H/P/R). Una foto por grupo. Sirve para verificar API, fijar prompts, umbrales, anotación y medir viabilidad de GPU. No entra en estimadores de evaluación. Si hay insuficiencia, informar y ajustar explícitamente el plan antes de congelarlo; no tomar grupos de la evaluación nueva.

### 3.2 Evaluación bloqueada: 60 imágenes, 60 grupos nuevos

Excluir **todos** los grupos de las 91 fotos previas, no sólo sus archivos. Inventario leído el 13/11/2026: quedan 160 grupos activos C_fit: 2025 H/P/R=17/14/15 y 2026 H/P/R=39/34/41. Este conteo verifica viabilidad del plan, no es una muestra ya seleccionada.

| Año | P | H | R | Total |
|---|---:|---:|---:|---:|
| 2025 | 12 | 9 | 9 | 30 |
| 2026 | 12 | 9 | 9 | 30 |
| Total | 24 | 18 | 18 | 60 |

Selección reproducible, sin mirar píxeles:

1. Agrupar filas elegibles por `split_group_id`; comprobar que año y especie son coherentes. Si no, detenerse y registrar incidencia sin corregir etiquetas.
2. Dentro de cada estrato año×especie, ordenar grupos por SHA256 de `seed|eval_group|split_group_id` y elegir los n requeridos. Empates por identificador lexicográfico.
3. Dentro de cada grupo elegido, ordenar imágenes activas por SHA256 de `seed|eval_image|image_id` y elegir la primera. No elegir la más nítida ni la de planta más grande.
4. Probabilidad de grupo n/N; condicional de imagen 1/m_g. Guardar ambos factores y peso N/n para estimar una media de grupos con una foto aleatoria por grupo. El objetivo primario es el panel balanceado; no llamarlo estimación de todas las fotos del corpus. Una estimación por imagen necesita pesos adicionales m_g y definición explícita.
5. Comprobar y publicar cobertura de sesión/cámara, EXIF, densidad nominal y años; no alterar la muestra para obtener resultados agradables o añadir cuotas después de ver máscaras. Si falta una cámara rara, el límite se declara y se puede abrir un panel suplementario separado.

Pesa más palmeri por el objetivo generativo; publicar siempre resultados P por separado y H/R como control de generalización. No aumentar n mediante pseudorreplicar hojas o píxeles.

### 3.3 Panel de estrés histórico

Reutilizar los doce casos anteriores únicamente como regresión conocida: hojas salientes, oclusión, margen insuficiente y error Hough. Resultados en tabla aparte, sin mezclarlos con los 60 nuevos ni presentarlos como confirmación independiente. Si comparte grupos con calibración, declararlo: no modifica independencia de los 60 nuevos.

## 4. Referencia humana y definición de objetos

Antes de ejecutar predicciones de evaluación, preparar anotaciones sobre originales EXIF-orientados a resolución nativa con zoom. No usar salidas SAM/HSV para dibujar la referencia. Los anotadores no ven códigos de método, métricas ni etiquetas de diseño al trazar contornos. Se necesitan anotadores humanos; un LLM puede preparar interfaz y archivos, pero no inventar referencia experta ni rellenar máscaras como si fueran humanas.

Capas separadas, disjuntas sobre superficies **visibles**:

- `plant_target`: toda vegetación perteneciente a la maceta objetivo, no sólo verde; hojas, cotiledones, tallos, pecíolos, tejido seco identificable. Si hay varios individuos en esa maceta, incluir la unión y registrar conteo observado/ambigüedad; no fingir segmentación de individuo único ni usar número sembrado como conteo visible.
- `soil_target`: sustrato visible dentro de la maceta objetivo, incluidos gránulos del sustrato; excluir planta, borde y pared de maceta, tarjetas y suelo exterior. Tierra oculta bajo hojas no se reconstruye.
- `other_plant`: vegetación ajena reconocible. `pot_rim_wall`, `card_label`, `other_background`: clases de contaminación útiles, al menos en la región objetivo.
- `ignore_uncertain`: borde o identidad que no puede resolverse con la imagen. Reportar su área; no absorber tallos difíciles en ignore por conveniencia. Conservar si la planta ya estaba truncada al capturar y dónde.

Referencia: una persona anota las 60; una segunda revisa las 60 sin predicciones y anota independientemente 20 (8P/6H/6R, equilibradas por año, selección hash previa). Adjudicar desacuerdos antes de calcular métricas de métodos. Guardar versiones individuales y consenso, identidad/experiencia, tiempo y fechas. Publicar acuerdo entre observadores sólo sobre esas veinte; si nadie puede revisar, el benchmark queda provisional, no se etiqueta validado científicamente.

Además de máscaras, marcar en cada imagen hasta 20 puntos de estructura fina: todos los extremos de hojas identificables y puntos medios de tallos/pecíolos finos hasta el límite, elegidos con orden espacial reproducible (arriba-abajo/izquierda-derecha, cuotas iguales entre tipos cuando haya suficientes). Registrar puntos existentes y no evaluables; no inventar órganos ocultos. Anotar una lista de órganos visibles cuya eliminación cambiaría la interpretación (hoja completa, ápice, tallo principal). Definir la rúbrica sobre calibración y congelarla antes del panel nuevo.

Formato: máscaras PNG uint8 L, tamaño nativo orientado, 0/255; capas no exclusivas de incertidumbre con prioridad explícita; metadatos JSON por foto, regiones opcionales COCO RLE. Referencia de unión `U=plant_target OR soil_target`. No reutilizar las antiguas envolventes como verdad de píxeles.

## 5. Métodos: separar localización, segmentación y presentación

### 5.1 Comparación automática primaria

Cada método recibe los mismos originales. Sin puntos/cajas manuales por imagen. Fijar todo en calibración; los prompts jamás incluyen especie ni etiqueta verdadera.

**L0, encuadre completo:** conserva el rectángulo adquirido. Soporte conservado K=toda la imagen. No es segmentador: IoU de planta no se interpreta como exactitud de segmentación; sí se mide cuánta planta y cuánto fondo quedan en su entrada.

**L1, Hough + HSV + rectángulo:** reproducir exactamente la rama H del piloto como baseline, no sustituirla silenciosamente por una implementación mejor. Leer `scripts/s10_detect_pot_geometry.py`, `s31_trial_green_roi_preprocessing.py`, `s12_extend_trial_auto_rectangle.py` y sus configuraciones. Las propuestas Hough existentes a lado 400 cubren sólo 91 fotos; para nuevas imágenes ejecutar el mismo detector con código/configuración versionados. HSV a lado máximo 800; H=[25,85], S≥45, V≥20, G>1,08R, G>1,10B; cierre 5×5, componentes ≥40 píxeles que intersectan círculo central de 0,9 radios. Ventana: unión de bbox del círculo y verde, margen 0,1 diámetros, limitada a captura. Conservar componentes y coordenadas, no sólo bbox. Preservar tratamiento de fallback del código; agregar checks sin alterar criterios. Cualquier mejora constituye L1b y se declara antes de evaluación.

**S1, SAM 3 automático:** checkpoint oficial de imagen, texto por separado `plant` y `soil`. Procesar sobre la imagen completa, estados de prompts independientes; no permitir que la consulta de suelo herede cajas o texto de planta. Guardar todas las instancias, scores y probabilidades disponibles. Umbral de confianza inicial 0,5 y de píxel 0,5; se permite elegir confianza entre {0,3;0,5;0,7} en calibración, con la misma regla de conservación descrita abajo y desempate por menor complejidad. No barrer prompts/umbrales en evaluación. No usar SAM 3.1 por sustitución implícita: elegir versión concreta y mantenerla fija.

Asociación automática al objetivo, igual de explícita que la máscara: usar el mismo círculo Hough de L1 como ancla, no el círculo humano. Elegir máscara de suelo con máxima intersección absoluta con el disco central de 0,9 radios, desempate por score/índice. Conservar instancias de planta que intersecten ese disco o el suelo seleccionado dilatado 0,1 diámetros; conservar **cada instancia entera**, sin cortarla al círculo o al suelo. Si una instancia incluye plantas ajenas, se evalúa como contaminación, no se corrige con referencia. Sin círculo o sin suelo/plantas vinculables: estado incierto, registrar máscaras brutas y no producir unión aprobada. Esto mide una tubería automática concreta, no el límite superior de SAM. La dilatación es para asociar, no para engordar la máscara final.

Las máscaras finales S1 se guardan en coordenadas nativas. En conflicto planta/suelo dar prioridad a planta para etiquetas; la unión binaria no cambia. No rellenar huecos grandes, eliminar componentes pequeños o suavizar bordes automáticamente sin declarar y fijar esa operación. No usar el círculo para eliminar hojas que sobresalen.

### 5.2 Ayuda humana como rama separada

**S2, SAM 3 asistido:** duplicar predicción S1; un operador distinto del anotador de referencia, sin acceso a GT, puede añadir hasta una caja positiva de localización, hasta cinco indicaciones adicionales compatibles con la API elegida y 120 segundos activos por imagen. Puede señalar errores observables mirando únicamente el original y la propuesta. Log de coordenadas, signo, orden, versión de API, segundos activos, aceptación e incidencias. Si no termina: `needs_manual_review`, no una máscara aceptada ficticia. Toda edición libre de píxeles se guarda como S3 manual, fuera de S2.

Para comparar coste de asistencia, permitir revisión/corrección del círculo L1 con el mismo presupuesto en una rama L2. No comparar S2 contra L1 llamándolo superioridad algorítmica automática. Reportar primero S1/L1 y después S2/L2 con costes. No derivar clicks óptimos desde GT. La API de conceptos y el predictor interactivo no son intercambiables: probar capacidad real en calibración y fijar adaptador, sin inventar métodos Python.

### 5.3 Vistas de entrada: ablación de máscara manteniendo ventana

Crear de S1 una ventana `W_sam`: bbox de su planta OR suelo, ampliada por 5 % de su lado mayor en los cuatro bordes, limitada a captura. Misma W y transformación para V2/V3/V4:

| Vista | Soporte conservado dentro de ventana | Qué compara |
|---|---|---|
| V0 | L0 completo | Referencia de máxima cobertura adquirida |
| V1 | Rectángulo L1 completo | Recorte clásico probado |
| V2 | W_sam completo, sin quitar píxeles | Efecto de localización SAM |
| V3 | Sólo planta S1 en W_sam | Aislamiento vegetal |
| V4 | Planta OR suelo S1 en W_sam | Contexto de tierra sin maceta |
| V5 | Máscara HSV de L1 en W_sam | Ablación de máscara HSV frente a SAM con idéntica presentación |

El exterior de las máscaras V3/V4/V5 usa RGB sRGB=(127,127,127); preservar RGB original en el interior. No inpainting ni restauración generativa. V5 depende de W_sam: es una ablación controlada, no una tubería HSV independiente. La calidad de máscaras HSV/SAM también se evalúa sobre el original antes de recortar, para no ocultar pérdidas. Variantes asistidas se exportan por separado, no sobrescriben automáticas.

Si S1 falla, V2–V5 operativas vuelven al encuadre completo **con estado de fallback visible**; las métricas crudas de máscara siguen reflejando el fallo. Para V5 distinguir fallo HSV de fallo de ventana SAM. Una variante de planta sola con bbox más estrecha puede aumentar detalle: sólo como diagnóstico secundario declarado; no atribuir esa ganancia al algoritmo de segmentación comparando ventanas distintas.

Los campos físicos históricos (20/22/26/30/40 cm, 12/22 cm por año, 1,1/1,3 diámetros) no son segmentadores. Se mantienen en contexto histórico. Si se añade una tabla de factibilidad, usar medición provisional independiente y marcar incertidumbre; no incluirlos como máscaras fallidas ni convertirlos en nuevas calibraciones.

## 6. Preparación de píxeles y SAM

1. Leer originales por `source_path`; verificar SHA antes/después. Aplicar EXIF, convertir ICC válido a sRGB o declarar suposición sRGB usando el comportamiento ya implementado en `scripts/s18_prepare_metric_masters.py` (`oriented_srgb`). Conservar referencia a helper y hash.
2. Guardar coordenadas en original orientado: x derecha, y abajo, bbox xyxy semiabierta, origen arriba-izquierda; especificar centros de píxel y afinidad exacta. No mezclar bbox normalizada cxcywh de prompts con xyxy en píxeles.
3. SAM tiene preprocesado interno: registrar resolución/interpolación y mapeo inverso del adaptador real. En el código oficial consultado el procesador usa resolución 1008 y devuelve máscara reescalada al tamaño de entrada; esto **no significa detalle nativo recuperado**. No aplicar cambios de aspecto a la fotografía final para imitar su tensor interno. Verificar máscara de salida contra dimensiones originales.
4. Exportar RGB/alpha o máscaras sin pérdida, manteniendo fuente original intacta. Presentaciones 224/384/1024 cuadradas: transformación isótropa con relleno gris, misma implementación para todos; una sola reducción desde original, sin crop implícito. 224/384 para futuros clasificadores y 1024 sólo diagnóstico de bordes para generación, no resolución generativa elegida. Registrar si hubo ampliación; no usar superresolución. Binarizar máscaras para scoring; alpha de presentación con antialias separado y sin erosión.
5. Pin de SAM: commit Git, identificador/revisión y SHA del checkpoint, licencia, Python, PyTorch, CUDA, driver, GPU/VRAM, dtype y paquetes. El repositorio oficial requiere Python≥3.12, PyTorch≥2.7, GPU CUDA compatible y CUDA≥12.6; verificar instalación real y acceso a pesos. No fijar memoria o duración sin medir. Si no hay acceso/GPU, entregar adaptador/test con estado pendiente, sin simular resultados. No instalar/modificar el entorno de producción sin necesidad: entorno aislado, CPU para selección/métricas y GPU para inferencia.
6. Para este alcance no son obligatorios tiles ni refinadores. Si 1008 pierde estructuras finas en calibración, se permite preregistrar una segunda variante de inferencia por ROI/tiles con solape y fusión definida; no incorporarla después de ver los 60. No comparar distintas resoluciones de entrada ocultándolas.

Fuentes técnicas verificadas al planificar: [repositorio e instalación SAM 3](https://github.com/facebookresearch/sam3), [API y preprocesado del procesador](https://github.com/facebookresearch/sam3/blob/main/sam3/model/sam3_image_processor.py), [capacidades de prompts](https://ai.meta.com/research/sam3). Estos enlaces son móviles: guardar commit y copia de configuración efectiva al implementar.

## 7. Métricas y fallos: definición computable

Evaluar en coordenadas nativas, excluyendo `ignore_uncertain` tanto de numerador como de denominador; publicar cobertura válida. G=planta de referencia, S=suelo de referencia, U=G∪S, M=predicción cruda del objeto correspondiente, K=soporte realmente conservado en la entrada final. G vacío: métricas vegetales NaN y conteo explícito, nunca 1 por convención favorable; no retirar la imagen del panel. Un fallo de segmentación con G no vacío usa M vacío (recall/Dice/IoU=0), además del estado de ejecución.

**Primarias, planta, especialmente P:**

- Recall visible de máscara: |M∩G|/|G|. Precisión: |M∩G|/|M|, undefined si M vacío, acompañada de recall=0. Dice e IoU con fórmulas estándar y denominadores explícitos.
- Retención final de tejido: |K∩G|/|G|; pérdidas por recorte y por máscara se descomponen. Publicar tanto resultado automático crudo como tubería con fallback, no dejar que fallback convierta un segmentador fallido en exitoso.
- Conservación de puntos finos: fracción dentro de K; tolerancia espacial δ=max(1, round(0,001×diagonal nativa)) px para error de marcado. Publicar también sin tolerancia. Boundary-F1 a δ para contornos de máscara, no para juzgar como segmentador al encuadre completo.
- Fallo morfológico crítico por foto: omitir por completo una hoja/ápice/tallo señalado en referencia, perder >2 % del tejido visible o perder >5 % de puntos evaluables. Además de regla automática, revisión humana ciega de órganos; conservar desacuerdos. No confundir truncamiento de origen con pérdida añadida. Umbrales propuestos de ingeniería, no tolerancias botánicas validadas.

**Secundarias, contexto y detalle:**

- Contaminación de entrada: |K\G|/|K| para planta sola, |K\U|/|K| para planta+tierra. Informar ambas para todas las vistas, con descomposición suelo/maceta/tarjeta/planta ajena. IoU planta y suelo por separado: una unión grande puede ocultar mala planta.
- Escala de presentación: factor isótropo aplicado, área/píxeles de planta de referencia retenidos y proyectados a 224/384/1024, lado menor de bbox vegetal proyectada y espesor proyectado de tallos anotados cuando sea medible. No llamar resolución óptica recuperada ni prueba de venación visible a un simple aumento de píxeles.
- Tiempo de carga, inferencia GPU sincronizada y exportación por separado; p50/p90, VRAM pico, batch=1, tres calentamientos fuera de medición en calibración y orden de métodos alternado. Para humanos, segundos activos de revisión/corrección, clicks y tasa aceptada dentro de presupuesto.
- Estado por caso: `ok`, `empty`, `wrong_target`, `crop_loss`, `needs_manual_review`, `runtime_error`, `fallback_fullframe`; pueden coexistir causa y acción. OOM o excepción cuenta en tasa de fracaso y coste, no se borra.

Comparaciones de órganos y fidelidad visual se muestran con códigos anónimos, orden aleatorio y misma escala de visualización; registrar cuándo la apariencia del método impide ciego completo.

## 8. Estadística y criterio de elección

Unidad independiente de análisis: grupo seleccionado (una foto por grupo). Tabla de cada imagen y resúmenes por método, especie, año y cámara cuando el n lo permita; no prometer potencia con celdas pequeñas. Informar mediana/IQR y media para retención, Dice, contaminación, detalle y tiempo; proporción de fallos con intervalo Wilson 95 %.

Comparaciones pareadas sobre **las mismas 60 imágenes**, bootstrap estratificado por año×especie, 10.000 remuestras de grupos con semilla fija, para diferencias de medias/medianas. En P usar sus 24 grupos y estratos por año. No hacer bootstrap de píxeles u hojas como independientes. Contrastes primarios: V1 vs V0 (recorte), V3 vs V2 (aislar planta), V4 vs V3 (añadir tierra), S1 vs HSV en máscara vegetal. Reportar estimación e IC, no seleccionar por p mínimo; cualquier prueba múltiple formal debe predefinir familia y ajuste Holm. Celdas de cámara son descriptivas.

Regla propuesta antes de evaluación:

1. No aceptar una opción sólo porque elimina mucho fondo. Exigir mediana de retención vegetal final ≥99 % y al menos 95 % de fotos con retención ≥98 % y sin fallo crítico; comprobar también P por separado. Mostrar intervalos y fracasos individuales.
2. Si varias cumplen, elegir frontera de Pareto entre menor contaminación, mayor detalle conservado, menor necesidad de corrección y coste. Para planta+tierra, el suelo es contexto permitido pero nunca excusa para menor retención vegetal. No inventar una suma ponderada después de ver resultados.
3. Si ninguna cumple, proponer flujo asistido o conservar ROI/fullframe según caso, con estados explícitos; no declarar un ganador universal. Los umbrales pueden fijarse definitivamente en calibración con justificación, nunca suavizarse al ver evaluación.
4. Con 24 P, cero fallos aún deja incertidumbre importante: Wilson superior bilateral 95 % es aproximadamente 13,8 %. Es una comparación de desarrollo, insuficiente para certificar tasa de fallo <5 % en palmeri. Ampliar con grupos nuevos en protocolo posterior si se necesita esa garantía.

Una buena máscara y ocupación de lienzo seleccionan candidatos de preprocesamiento, no al mejor clasificador/generador. Una máscara que recorta morfología se descarta aunque incremente una métrica predictiva por pistas espurias.

## 9. Fase posterior de modelos: contrato, no parte de esta ejecución

**Clasificador:** comparar como máximo dos opciones finalistas frente a fullframe, mismos grupos/etiquetas y arquitectura, tres semillas, inicialización, presupuesto, aumentos que preserven morfología y selección de checkpoint idénticos. Entrenar C_fit y seleccionar sólo con C_val_model_selection; no usar sus etiquetas para segmentación por especie. C_val_calibration reservado a umbrales posteriores, T_real intacto. Macro-F1, recall P, confusiones H/P/R, incertidumbre por grupo y sensibilidad a fondo. Elegir 224 vs384 en diseño separado o factorial con idéntico presupuesto explícito. El panel de 60 es benchmark geométrico interno de C_fit; no es evaluación independiente de un modelo entrenado con esas imágenes.

**Generador:** sólo G_fit activo para entrenamiento; no transferir fotos C_fit por comodidad. Preparación finalista y parámetros ya fijados antes de abrir G_fit para producir entradas. Comparar planta sola frente a planta+tierra con mismo checkpoint base, semillas, leyendas comprobadas, pasos y condiciones; especificar si pérdida enmascarada está realmente implementada. Inpainting regional no implica pérdida enmascarada en entrenamiento. Mantener conjunto común de prompts/semillas y todas las generaciones, no selección estética. Evaluación ciega experta de morfología (órganos, inserciones, proporciones y estructuras visibles), diversidad y posibles copias; score de clasificador/BioCLIP sólo complementario. La calibración repetida independiente/tolerancias del panel siguen en tarea 45. No marcar entrenamientos realizados por haber escrito este plan.

## 10. Implementación y entregables exigidos al otro LLM

Crear una carpeta nueva `data/processed/preprocessing/segmentation_benchmark_v1/`, sin sobrescribir evidencia anterior. Scripts propuestos bajo `scripts/segmentation_benchmark/`:

1. `s03_inventory_and_sample.py`: dry-run por defecto; valida contratos y produce universo/conjuntos/estadísticas/huellas. Leer metadatos de listas prohibidas para comprobar grupos es admisible; no decodificar sus imágenes.
2. `s01_annotation_io.py`: plantillas, import/export PNG/JSON, control de dimensiones/clases, anotación ciega y versiones. `ground_truth/` se mantiene inaccesible al runner de algoritmos.
3. `s06_run_methods.py`: adaptadores L0/L1/S1, primero `--split tuning`, luego evaluación sólo con config congelada; S2/L2 interactivas independientes. Cache por hash de imagen/config/checkpoint, no por nombre. Falla si el hash cambia; no descarta casos.
4. `s04_render_views.py`: ventanas, máscaras, soportes K, transformaciones y vistas con metadatos sin crop implícito.
5. `s07_score.py`: único lector de GT para medir; métricas crudas y operativas, fallos, bootstrap y estratos. Prohibir que llame a optimización/prompts tras ver GT de evaluación.
6. `s05_report.py` y `s08_validate_run.py`: informe Markdown/HTML, comparativas anónimas, CSV/JSON por imagen, tablas con denominadores y checks de integridad.

Estructura de salida mínima:

```text
segmentation_benchmark_v1/
  README.md, protocol.md, config_draft.json
  inventory.json, sampling.json, samples/{tuning,evaluation,stress}.csv
  freeze.json, environment.json, code_inventory.json
  annotations/{individual,consensus}/, annotation_log.csv
  predictions/{method_id}/, views/{view_id}/{size}/
  interactions.jsonl, timings.csv, per_image_metrics.csv
  statistics.json, failures.csv, report.md, figures/
  validation.json, run_receipt.json
```

Cada predicción/registro debe identificar `image_id`, original SHA, `split_group_id`, role, año, cámara, species_code de trabajo sólo para análisis, método/versión, config SHA, checkpoint SHA, prompts, resolución de inferencia, dtype, máscaras/cajas, ventana, afín inversa, fallback, tiempo/correcciones y rutas/hashes de salidas. Conservar score original sin presentarlo como probabilidad calibrada de exactitud.

`freeze.json` debe crearse **después de calibración y antes de la primera inferencia de evaluación**, con UTC, hashes de config/código/checkpoint/selecciones/referencia adjudicada y anotaciones, semilla, variantes, métricas/umbrales y regla estadística. El runner rechaza evaluación sin congelación y rechaza cualquier discrepancia. Un cambio posterior abre v2 y no reutiliza la evaluación como si fuera nueva.

Tests relevantes: fixture de máscara fina que no se borra; EXIF rotado y bbox de vuelta; xyxy/cxcywh normalizados; RGB interior intacto antes de resize; proporción isótropa; margen limitado sin corte; vacío/error/fallback; no fuga entre estados de prompts; separación de grupos; exclusiones activas; fórmulas de métricas y bootstrap determinista. Validar pin de modelo/API con smoke-test real en calibración, no con resultados fabricados.

Antes y después, verificar hashes de originales seleccionados, registro, configuración y manifiesto/listas activos; mantener numeración de tasks y casillas sin cambios no justificados. No repetir la auditoría costosa de 1.419 maestros si no se han tocado. Anotar decisiones, acciones y resultados reales en bitácora con nuevas entradas; conservar historia.

### Hito que debe entregar primero el implementador

Código revisable, dry-run de selección con conjuntos disjuntos y cobertura, estimación de anotación/cómputo medida en calibración, prueba real del adaptador SAM si hay pesos/GPU, plantillas y config propuesta. **No ejecutar aún evaluación bloqueada ni migrar producción:** el investigador ha pedido revisar primero la implementación. Si faltan anotadores, pesos o hardware, identificar la dependencia y avanzar con lo demás. No pedir secretos ni imprimir tokens.

## 11. Criterios de aceptación para la revisión posterior

- Submuestras reproducibles, 60 grupos nuevos separados de los 76 expuestos; exclusiones justificadas sin selección visual favorable.
- Referencia humana trazable, máscaras de planta y tierra separadas, incertidumbre y acuerdo documentados.
- Comparación automática separada de asistida; ventanas comunes para aislar efecto de máscara; vacíos/fallos presentes en denominadores.
- Mapeo nativo y transformación de presentación probados; sin tejido inventado ni erosión de detalles ocultada.
- Evaluación inmóvil tras freeze; métricas pareadas, P separado y límites de tamaño muestral explícitos.
- Ninguna promesa de exactitud botánica, mejora de modelos, tasa poblacional o cm/píxel a partir del pequeño piloto.
- Registro y entrega vigentes intactos. Implementación entregada para revisión antes de evaluación y sin cerrar tareas futuras por planes.
