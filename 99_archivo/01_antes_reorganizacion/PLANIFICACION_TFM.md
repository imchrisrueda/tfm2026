# Plan único del TFM de generación y validación de imágenes de Amaranthus palmeri

**Actualización operativa · M029 (12 de noviembre de 2026):** se sustituye la normalización obligatoria a campo físico común por maestros de **encuadre completo, aspecto exacto y lado máximo 2048 px**. Se preservan proporciones aparentes planta/maceta; no se afirma cm/píxel común ni escala 3D. Las referencias métricas y su calidad se registran aparte. Véase [comparación ejecutada](doc/REVISION_PREPROCESADO_2026-11-12.md). Esta decisión sustituye las formulaciones históricas de campo común, manteniendo modelos, grupos y evaluaciones.

Versión integrada del 10 de noviembre de 2026. Sustituye el plan del día 9 e incorpora FLUJO_IMAGENES_TFM.md y PROTOCOLO_ESCALA_MACETAS.md. Es el procedimiento que se seguirá; no acredita trabajo experimental ya realizado ni una aprobación adicional de la tutora.

El objetivo es generar escenas cenitales de A. palmeri y evaluar su identidad taxonómica, fidelidad morfológica y proporciones aparentes respecto a macetas conocidas, combinando ConvNeXt-Tiny, BioCLIP y tres expertos. El resultado será un corpus íntegro auditado y un subconjunto seleccionado con evidencia explícita de validación.

## 1. Documentos y decisiones de integración

Este archivo es la referencia principal de alcance, particiones, evaluación, selección y calendario. [FLUJO_IMAGENES_TFM.md](FLUJO_IMAGENES_TFM.md) contiene el diagrama y la secuencia operativa. [PROTOCOLO_ESCALA_MACETAS.md](PROTOCOLO_ESCALA_MACETAS.md) desarrolla la medición geométrica, subordinada a las decisiones de este plan. Los detalles técnicos de esos anexos no crean experimentos alternativos obligatorios.

Fuentes de partida:

- [Acta con Raquel del 4 de noviembre](<C:/Users/christianr/Desktop/tracework/tracework/05 Actividades/Reunión de planificación del TFM con Raquel Martínez — 2026-11-04.md>): clasificador, umbrales, generación, filtrado y tres expertos.
- [Resumen ECPA](<C:/Users/christianr/Desktop/ecpa2027/reports/ecpa/ECPA-2027_Abstract-Rueda-Ayala-VPRA.docx>): FLUX.1-dev con LoRA, tres ejecuciones, ConvNeXt-Tiny, BioCLIP y auditoría de anomalías.
- Aclaraciones del usuario: datos de las tres especies; generar solo A. palmeri; BioCLIP y tres entrenamientos son obligatorios; misma configuración y semillas distintas; DRAGO disponible; expertos A/B/C del 19 al 23; dedicación prevista de 10 h/día; enviar la memoria completa a Raquel el 28 como máximo, sin exigir que su revisión esté incorporada ese día.
- Archivos técnicos incorporados el 10: escenas cenitales a menos de 1 m; una o varias plantas por maceta; diámetro exterior de boca de 10 cm en 2025 y 20 cm en 2026; tarjetas amarillas en parte del material; muestra con cámaras Nikon y maíz auxiliar. El inventario comprobará estos atributos por imagen.

El resumen ECPA anticipa resultados que, según la aclaración del usuario, todavía no se han obtenido. No se usarán como evidencia. Su descripción de cámara Canon y altura de 1 m tampoco se trasladará automáticamente: se documentarán las condiciones verificadas en el inventario. La muestra revisada no determina los totales por especie.

| Aspecto | Decisión única |
| --- | --- |
| Unidad de trabajo | Escena de una maceta con una o varias plantas de la misma especie confirmada. |
| Clasificación | Tres clases: A. palmeri, A. hybridus y A. retroflexus. |
| Generación | Solo escenas de A. palmeri, dentro de condiciones representadas en los datos. |
| Escenas con especies mezcladas o identidad incierta | Fuera del entrenamiento supervisado y del LoRA principal; conservar como incidencias o material auxiliar. |
| Encuadre | Rectángulo completo adquirido, aspecto exacto y sin zoom por planta; sin cm/píxel común (M029). |
| Homografía | No forma parte del preprocesado general. Solo una corrección validada si el piloto demuestra que hace falta y dispone de referencias suficientes. |
| Bboxes y máscaras | Sin anotación exhaustiva obligatoria. Priorizar referencias de maceta; medir envolvente vegetal en el panel de escala. Máscaras solo si se evalúa cobertura. |
| Clasificador y generador | Individuos y grupos de maceta de entrenamiento separados. |
| BioCLIP | Auditoría independiente del clasificador como instrumento; no una tercera condición automática de aceptación. |
| Filtrado y auditoría | Conservar todas las generaciones, aceptadas o no. Auditar también rechazos y ambigüedades. |
| Maíz | Comprobación auxiliar del rechazo con modelos congelados; ni cuarta clase ni datos del LoRA. |
| Producto final | Separar corpus auditado, candidatas automáticas y subconjunto efectivamente validado por expertos y escala. |

## 2. Pregunta y alcance

Pregunta: ¿en qué medida FLUX.1-dev con LoRA genera escenas de A. palmeri que conservan identidad taxonómica, morfología visible y proporciones aparentes respecto a macetas conocidas, y cómo concuerdan el clasificador, BioCLIP y los expertos al evaluarlas?

Los entregables obligatorios son: inventario y particiones por grupos; maestros con encuadre y proporciones conservados y estado de referencia separado; ConvNeXt-Tiny y sus umbrales; tres adaptadores LoRA; corpus completo y metadatos; evaluación BioCLIP; panel A/B/C y auditoría de proporciones/escena; análisis integrado; memoria y materiales de reproducción. No se presenta normalización a cm/píxel común como resultado conseguido.

Se estudia estabilidad entre semillas, sin presentar tres semillas como una optimización de hiperparámetros. No se promete exactitud dimensional 3D ni mejora de un clasificador mediante sintéticas. Reentrenamiento con sintéticas, lógica difusa, realimentación con contraejemplos, detección por cajas y condicionamiento espacial exacto quedan fuera del núcleo.

Título de trabajo para valorar con Raquel: «Generación y validación taxonómica y morfológica de imágenes sintéticas de Amaranthus palmeri con evaluación de proporciones aparentes».

## 3. P0 Inventario y agrupación

Conservar originales inalterados y asignar image_id y hash. Tratar conversiones HEIC/JPEG, recortes y aumentos de la misma captura como derivados de una observación, no como individuos independientes. Comprobar duplicados y fotografías próximas.

Registrar especie confirmada, plant_id cuando sea posible, pot_id, número de plantas, continuidad entre fechas, sesión, año, cámara, estadio fiable, diámetro de boca, tarjeta, visibilidad, daños y solapamiento. Añadir fuente de etiqueta, calidad de la referencia geométrica y motivos de exclusión. No deducir especie del nombre DSC ni del año.

La agrupación será conservadora: todas las fotos de una maceta y las trayectorias de sus plantas permanecerán juntas. Si hay trasplantes o conexiones entre macetas e individuos, usar el grupo conectado completo. El nombre o la fecha por sí solos no acreditan independencia.

Cruzar especie con año, diámetro, cámara, sesión, fondo, tarjeta, estadio y número de plantas. Una asociación total entre especie y captura impide separar sus efectos; normalizar la escala no resuelve esa confusión.

Salida: manifiesto con grupos verificables y estados de calidad. Los totales por especie, individuo y grupo se completarán cuando el usuario los facilite; no se fijan porcentajes ni recuentos ficticios.

## 4. P1 Particiones y protección de la evaluación

Asignar grupos antes de crear aumentos o ajustar el encuadre con los datos. Reservar las siguientes funciones:

| Función | Material permitido | Uso |
| --- | --- | --- |
| C_fit | Reales de las tres especies | Entrenamiento del clasificador; también referencias BioCLIP declaradas. |
| C_val | Otros grupos reales de las tres especies | Selección de resolución, modelo y calibración/umbrales mediante separación interna por grupos. |
| G_fit | Otros grupos reales solo de A. palmeri | Piloto y tres entrenamientos LoRA; configuración y número de pasos fijados antes de la generación final. |
| T_real | Grupos reales de las tres especies ajenos a todo ajuste | Prueba final del clasificador y controles reales del panel experto. |
| M_aux | Maíz independiente | Diagnóstico separado del rechazo, sin ajustar con sus resultados. |

C_fit, C_val, G_fit y T_real no compartirán grupos. Las referencias BioCLIP se construirán con C_fit: se declara esta reutilización para no exigir una reserva adicional sin conocer el inventario. Son independientes de G_fit y T_real, aunque no de los datos del clasificador. Compartir referencias reales no convierte sus dos instrumentos en pruebas estadísticamente independientes.

Dentro de C_val, separar por grupos selección de configuración y determinación de umbrales. Si el inventario no permite dos reservas, usar un procedimiento de validación por grupos declarado, manteniendo T_real intacto, y reconocer las limitaciones. Si ni siquiera caben las reservas principales, detener el entrenamiento final y revisar el diseño; no resolverlo mezclando fotos del mismo individuo entre funciones.

No usar T_real para elegir campo, umbrales, hiperparámetros, checkpoints ni ejemplos favorables. Los controles reales serán un subconjunto de ese conjunto, con grupos y papel registrados. Tras abrir su evaluación no se reajustará el sistema para volver a presentar la misma prueba como independiente.

## 5. P2 Referencias de escala y preprocesado conservando encuadre

1. Aplicar orientación EXIF y gestionar el color hacia sRGB cuando corresponda. Guardar las coordenadas en el sistema orientado y los derivados sin orientación obsoleta.
2. Revisar el borde exterior en desarrollo; guardar centro, diámetro aparente, nominal y calidad, con nulos para referencias no medibles. Las 91 fichas exploratorias M029 no son calibraciones aprobadas; las tolerancias y anotaciones repetidas siguen en tarea 45.
3. Conservar el rectángulo completo adquirido, sin recorte centrado ni ajuste por tamaño de planta. Los campos común, por año y proporcionales al diámetro quedan como alternativas examinadas y descartadas para el corpus general.
4. Redimensionar isotrópicamente, sin ampliar, a un múltiplo entero de la razón de aspecto reducida por MCD, con lado máximo 2048 px. Guardar PNG sRGB con ventanas y hashes. El lector de cada modelo debe respetar el encuadre; adaptar y probar tamaños/lienzo antes de entrenar.
5. Separar calidad técnica general, integridad de captura y aptitud métrica. Una referencia no fiable impide atribuir escala, no obliga por sí sola a descartar el maestro general. No completar tejido ni rellenar maestros. Mantener las nueve exclusiones y 23 reservas fuera de las listas activas.

Fórmulas históricas para una eventual rama métrica con diámetro nominal D_i, observado fiable d_i, campo F y salida N × N; no se aplican al corpus general M029:

```text
lado_del_recorte_en_origen = F * d_i / D_i
factor_isotropico = N * D_i / (F * d_i)
diametro_esperado_en_salida = N * D_i / F
```

La maceta de 20 cm tendría doble diámetro en píxeles que la de 10 cm a igual campo/resolución métricos; el corpus general M029 no satisface esa premisa. No interpretar píxeles como centímetros comunes, igualar círculos ni deformar una elipse. Una homografía sólo rectifica un plano justificado, sin eliminar relieve; véase [OpenCV](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html).

Las tarjetas no se borrarán con IA. Se preservarán o se priorizarán capturas sin tarjeta para G_fit únicamente si mantienen la cobertura de individuos y estadios. Si excluirlas sesga el conjunto, se mantendrán con etiqueta y condición explícitas. No se generarán tarjetas como supuesta certificación de escala.

En el núcleo se usarán giros de 90 grados y reflejos que preserven el lienzo, más variaciones fotométricas moderadas sólo en entrenamiento. No habrá zoom aleatorio ni recortes implícitos. Cada modelo tendrá su normalización numérica; comprobar que las transformaciones no cortan plantas ni cambian proporciones. La adaptación de lectores pertenece a tareas 25/33/35 y no se da por hecha al preparar archivos.

Salida: maestros generales, manifiesto complementario con funciones/rutas/hashes y referencias exploratorias, y configuración congelada. Sin afirmación de cm/píxel común ni longitudes exactas de hojas en 3D.

## 6. P3 Clasificador y filtro

Entrenar ConvNeXt-Tiny con C_fit. Piloto a 224 × 224 y contraste de 384 × 384 en desarrollo solo si el detalle lo justifica; fijar una opción antes de la prueba. Conservar el campo completo al reducir resolución. El recorte central de la transformación estándar requiere revisión; la [documentación oficial](https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.convnext_tiny.html) describe sus transformaciones.

Ajustar los umbrales por especie en la función de validación destinada a ello. Comprobar calibración si se interpretan puntuaciones como probabilidades. La función y el compromiso entre errores se fijarán antes de analizar sintéticas y expertos; no se inventa ahora un valor como 0,90.

Regla única por imagen: calcular el conjunto de especies cuyo score supera su propio umbral.

- Solo A. palmeri: candidata automática de A. palmeri.
- Solo A. hybridus o solo A. retroflexus: posible confusión taxonómica de una generación destinada a A. palmeri.
- Varias especies: ambigua.
- Ninguna especie: rechazo.

Ninguno de esos estados elimina la imagen del corpus de auditoría. Las puntuaciones de un clasificador cerrado no garantizan detectar especies desconocidas. Congelar pesos, transformaciones y umbrales antes de la generación final y del panel experto.

Salida: modelo, reglas y evaluación real con matriz de confusión, precisión/sensibilidad/F1 por especie y macro-F1. Desglosar por estadio y sesión si los grupos permiten interpretarlo. Examinar pistas de fondo, tarjetas o cámara en desarrollo, sin tomar una única perturbación artificial como prueba de independencia del contexto.

## 7. P4 Piloto y tres entrenamientos de FLUX con LoRA

Utilizar G_fit, sin introducir maíz, otras especies ni grupos compartidos con el clasificador. La unidad generada será una escena de una maceta de A. palmeri, con número de plantas declarado y condiciones dentro del dominio observado. No atribuir la cobertura de varias plantas a un individuo.

Preparar leyendas por imagen con especie, vista cenital, diámetro físico confirmado, número de plantas, estadio y categoría de tamaño aparente anotados. No introducir medidas inventadas de hojas. No se requieren bboxes como entrada del LoRA convencional; las leyendas deben estar en un formato que lea efectivamente el entrenador. Véase la [guía oficial de FLUX LoRA](https://github.com/huggingface/diffusers/blob/main/examples/dreambooth/README_flux.md).

Realizar una prueba corta para medir memoria, duración y fidelidad del preprocesado. Fijar resolución, pasos, parámetros LoRA, criterio de checkpoint y presupuesto antes de los entrenamientos finales. El criterio de checkpoint no se elegirá buscando puntuaciones altas en el clasificador que después se utilizará para auditar.

Ejecutar tres entrenamientos sobre G_fit con la misma configuración y semillas de entrenamiento distintas. Usar en los tres adaptadores la misma matriz de prompts y semillas de generación; distinguir ambas clases de semilla. Condicionar diámetro de 10/20 cm, estadio y número de plantas solo en combinaciones respaldadas por los datos. No comparar combinaciones inexistentes como si estuvieran aprendidas.

Salida: tres adaptadores, configuraciones, registros y corpus íntegro con image_id, run_id, prompt, condición, semilla y checkpoint. No conservar únicamente la mejor ejecución ni seleccionar imágenes por apariencia favorable. Un fallo total de generación se registrará también, con denominador separado.

## 8. P5 Auditoría de todo el corpus generado

Sobre las salidas originales de generación, sin reescalar a posteriori para ocultar errores:

1. Aplicar el clasificador y registrar los cuatro estados de P3 y las tres puntuaciones.
2. Extraer representaciones BioCLIP con checkpoint y transformaciones fijados. Construir centroides con representaciones reales C_fit normalizadas, promediadas y renormalizadas; comparar similitud coseno con las tres especies. Añadir referencias por estadio cuando haya etiquetas y grupos suficientes. Verificar que la transformación espacial preserve el campo o registrar su adaptación. [Uso oficial de BioCLIP](https://github.com/Imageomics/bioclip).
3. Registrar maceta visible y medible, integridad, truncamiento aparente y cumplimiento del número de plantas. Medir el diámetro de maceta en píxeles cuando sea fiable; marcar la imposibilidad de medir como resultado, sin excluirla silenciosamente.
4. Revisar vecinos próximos de G_fit para detectar copias evidentes, sin afirmar que esa prueba descarta toda memorización.

BioCLIP será una variable de auditoría: no se ajustará un umbral a posteriori para forzar coincidencia con los expertos. Los casos no procesables tendrán estado explícito. Se compararán los tres instrumentos y la escala, sin tratar una puntuación como certificación botánica.

Salida: tabla enlazada por image_id y run_id. No adaptar el recorte al diámetro sintético antes de evaluar: eso borraría la desviación geométrica que se quiere medir.

## 9. P6 Panel ciego y auditoría de proporciones

Antes de abrir respuestas, fijar panel, rúbrica, tolerancias geométricas y regla de selección. Establecer las tolerancias de medición con anotaciones repetidas de datos reales de desarrollo; las referencias de proporción se estratificarán por diámetro, estadio y número de plantas cuando sea viable. No fijarlas mirando cuáles sintéticas se desean aprobar.

Si no cabe la evaluación exhaustiva, seleccionar aleatoriamente por ejecución y estado del filtro, incluyendo aceptadas, confusiones, ambiguas y rechazadas, y cobertura de incidencias de escala. Guardar estrato, probabilidad de inclusión y peso. No se necesita conocer todavía los recuentos para definir esta regla; sí antes de construir el panel. Incluir controles T_real de las tres especies sin revelar su origen.

A, B y C evaluarán el mismo panel de forma independiente, con códigos y orden aleatorio, sin scores, run_id, decisión automática ni indicación real/sintética. La presentación conservará el campo y permitirá ver detalle; cualquier zoom será explícito, no un cambio de escala del corpus.

Rúbrica por experto:

- Especie percibida, con opción incierta/no evaluable.
- Compatibilidad morfológica visible con A. palmeri y rasgos/anomalías que la sustentan.
- Aptitud de la escena y oclusión/visibilidad, sin exigir adivinar rasgos ocultos.
- Coherencia aparente de la escena y número de plantas cuando se pueda juzgar.

En ese panel se medirá también la envolvente de vegetación, relación anchura/diámetro de maceta y altura proyectada/diámetro, y ocupación relativa de la maceta respecto a anchura y altura del lienzo. Con M029 no existe un diámetro esperado único N*D/F: comparar distribuciones de condiciones reales/sintéticas equivalentes y fijar tolerancias con desarrollo, sin deducir píxeles desde los centímetros del prompt. Son dimensiones proyectadas de la escena, no altura vertical de la planta. Si no se distingue la vegetación o la maceta, registrar no evaluable. El área de cobertura sólo se añadirá si se dispone de máscaras verificadas.

Comparar distribuciones reales/sintéticas de esas proporciones con referencias de desarrollo comparables y reportar las de controles T_real sin reajustar tolerancias. En una maceta generada el diámetro físico es una condición solicitada, no una medida física observada. Ni el prompt con centímetros ni el LoRA garantizan geometría exacta.

## 10. P7 Selección y análisis integrado

Una escena tendrá validación botánica cuando al menos dos de los tres expertos coincidan, cada uno en su propia respuesta, tanto en A. palmeri como en aptitud morfológica. Una mayoría de especie y otra de aptitud formada por personas distintas no sustituirá esta regla conjunta.

La selección final combinará tres condiciones:

```text
seleccionada = candidata_automatica_A_palmeri
              Y validacion_botanica_por_al_menos_dos_expertos
              Y control_de_escala_y_escena_superado
```

El control de proporciones/escena exige referencia sintética medible, vegetación sin truncamiento que invalide el uso, número de plantas conforme y relaciones planta/maceta y ocupación del lienzo plausibles según la rúbrica y referencias comparables de la condición. El diámetro nominal solicitado no determina un diámetro esperado en píxeles ni certifica centímetros físicos en una sintética. Las tolerancias se prerregistran con desarrollo. Si no hay referencias suficientes para juzgar una condición, marcar pendiente/no evaluable; no darla por superada.

Conservar separadas cuatro salidas:

1. Corpus íntegro de generación y auditoría, incluidos defectos y rechazos.
2. Candidatas automáticas, sin llamarlas validadas si no han pasado el panel.
3. Subconjunto seleccionado con las tres condiciones y trazabilidad de los juicios.
4. Casos válidos para expertos pero rechazados por el filtro: evidencia de posibles falsos rechazos, sin borrarlos ni introducirlos retrospectivamente en la selección automática.

Informar aceptación automática, aptitud experta antes/después del filtro, falsos rechazos, fallos taxonómicos/morfológicos/geométricos, no evaluables y discrepancias con BioCLIP. Declarar todos los denominadores. Si el panel tiene muestreo desigual, ponderar las estimaciones del corpus; las cifras sin ponderar describen únicamente el panel.

Medir acuerdo observado y acuerdo entre A/B/C por variable. Comparar ejecuciones descriptivamente; tres entrenamientos no autorizan a tratar cada imagen como un entrenamiento independiente. Las comparaciones de escala se condicionarán al estadio, diámetro y número de plantas cuando el diseño lo permita. No confundir una asociación de cámara/año/diámetro con un efecto causal de la especie.

Evaluar M_aux con el clasificador congelado y registrar la fracción de maíz aceptada como cualquier amaranto y como A. palmeri. Presentarlo aparte, sin mejorar con sus casos fáciles las métricas principales. No ajustar con ese maíz y presentarlo luego como prueba independiente.

El maíz debe permitir la misma transformación espacial declarada. Si solo hay escenas truncadas o sin referencia fiable, declararlas como diagnóstico de esas condiciones; no rellenarlas ni presentar ese contraste como evaluación de maíz completo. Si no hay material elegible suficiente, registrar la limitación del contraste auxiliar.

## 11. P8 Memoria y entrega

Redactar desde P0 y mantener los capítulos Introducción, Metodología, Resultados, Discusión y Conclusiones. No presentar como obtenidos los resultados anticipados de ECPA.

La introducción integrará el estado del arte en este orden:

1. Contexto agronómico y motivación de reconocer A. palmeri.
2. Discriminación frente a A. hybridus y A. retroflexus y límites de la vista cenital.
3. Visión artificial, clasificación de escenas y escasez/representatividad de datos.
4. Generación sintética, difusión y adaptación LoRA.
5. Fidelidad taxonómica/morfológica, diversidad y riesgo de memorización.
6. Proporciones aparentes y referencias de escala: por qué la normalización métrica del plano no certifica dimensiones 3D.
7. Evaluación complementaria mediante umbrales, BioCLIP y expertos.
8. Vacío de conocimiento, pregunta, objetivos y alcance.
9. Estructura de la memoria.

Metodología seguirá P0–P7, con origen real de datos, particiones, transformaciones, decisiones congeladas y rúbrica. Resultados separará prueba real, generaciones, escala, expertos, selección y maíz auxiliar. Discusión abordará sesgos de contexto, visibilidad, transferencia real/sintético y límites de generalización. Conclusiones responderá a los objetivos sin afirmar mejora de clasificación o eficacia en campo no ensayadas.

Los anexos contendrán manifiesto, esquema de particiones, geometría, leyendas/prompts, configuración/semillas, rúbrica, tablas de auditoría y guía de reproducción. Verificar compilación, figuras, bibliografía, referencias cruzadas y disponibilidad de los materiales antes del envío.

## 12. Calendario actualizado al 10 de noviembre

Las fechas siguen siendo objetivos, no trabajo ya ejecutado. Los recuentos y la prueba de GPU determinarán el presupuesto concreto. No se ha iniciado entrenamiento por redactar este plan.

| Fechas | Etapas y resultado |
| --- | --- |
| 10–11 | P0–P2: inventario, grupos, particiones y piloto de escala; índice y bibliografía en paralelo. |
| 12–13 | P3: clasificador y umbrales; prueba corta LoRA después de disponer del clasificador base. |
| 14–17 | P4: tres entrenamientos finales; preparar BioCLIP, formulario y rúbrica. |
| 18 | P5: corpus final, clasificación/BioCLIP, medidas iniciales y panel congelado. |
| 19–23 | P6: evaluación A/B/C y mediciones del panel; redacción de metodología. |
| 24–25 | P7: análisis integrado, selección, maíz auxiliar, resultados y discusión; memoria completa. |
| 26–27 | P8: revisión, bibliografía, anexos y compilación. |
| 28 | Comprobación final y envío de memoria completa a Raquel. |

Con 10 h/día del 10 al 28 hay 190 h nominales antes de descontar lo ya transcurrido hoy. Reparto orientativo: inventario/particiones/escala 24 h; clasificador y umbrales 28 h; piloto y gestión de tres LoRA 32 h; BioCLIP 10 h; panel y escala sintética 20 h; análisis 16 h; redacción/bibliografía 36 h; verificación 12 h. Total 178 h; margen nominal máximo 12 h. La duración de cómputo y el trabajo de los expertos no equivalen a dedicación del autor.

Puntos de decisión: al cerrar P2, comprobar que caben las reservas independientes; el 13, que caben los tres entrenamientos; el 18, congelar el corpus y enviar panel; el 23, cerrar respuestas. Si los recuentos llegan tarde, el calendario deberá reestimarse: no saltarse particiones ni atribuir validez a una evaluación inexistente para mantener fechas.

## 13. Parámetros pendientes y contingencias

El proceso está unificado. Quedan pendientes de fijación en su etapa correspondiente:

- Totales por especie, individuos y grupos, que el usuario facilitará después; de ellos se derivarán reservas y recuentos de generación/panel.
- M029 fija encuadre completo y lado máximo 2048 para maestros generales. Quedan calidad mínima y tolerancias del panel, adaptación/resolución de los modelos y, sólo si se retoma una rama métrica explícita, su campo físico y validación independiente.
- Medidas de la tarjeta únicamente si se usa como referencia alternativa; no bloquean el uso de la maceta cuando su borde es fiable.
- Parámetros comunes LoRA, presupuesto de GPU, valores de umbral y mínimo de rendimiento útil, definidos en desarrollo antes de evaluar.
- Etiquetas de estadio, número de plantas y combinaciones de condiciones efectivamente representadas.
- Requisitos formales/título con Raquel; no se han fijado fechas oficiales de depósito o defensa.

Si falla el cómputo, reducir de forma documentada pasos o resolución antes de los tres entrenamientos, preservando encuadre completo, aspecto y configuración común entre ejecuciones. Si falla el tamaño de muestra experta, reducir el panel mediante muestreo declarado. Si el clasificador no resulta útil, informar esa limitación y conservar auditoría BioCLIP/experta/proporciones; no afirmar selección automática eficaz. Si la geometría no puede medirse, registrar el resultado y limitar la afirmación de conservación de proporciones. No eliminar BioCLIP ni una de las tres ejecuciones para añadir extensiones.
