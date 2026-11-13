# Revisión de implementación: segmentation_benchmark_v1

13 de noviembre de 2026. Especificación: `doc/02_EXPERIMENTO_COMPARACION_PREPROCESADO_V1.md`. Entrega revisada: M040. Registro de esta revisión: M041.

**Dictamen: base útil para continuar implementación y anotación, pendiente de correcciones antes de congelar o ejecutar la evaluación bloqueada.** No basta con instalar SAM y aportar máscaras: hay defectos en las garantías de congelación, los denominadores y la detección de pérdida morfológica, además de funcionalidades aún no conectadas.

Esta sesión revisa código y metadatos, ejecuta los once tests entregados y comprobaciones adversariales en directorios temporales con imágenes/máscaras sintéticas. No ejecuta inferencia de evaluación ni SAM, no toca la muestra publicada, no instala dependencias, no modifica la implementación entregada ni migra producción. Las referencias sintéticas son fixtures de software; no se incorporan al dataset ni se presentan como anotaciones humanas.

## Hallazgos prioritarios

### R1 · P1 · La congelación no garantiza las condiciones del experimento

Localizaciones: `scripts/segmentation_benchmark/s08_validate_run.py:85`, `s06_run_methods.py:347`, `s06_run_methods.py:373`.

`create_freeze()` comprueba sólo que existan los sesenta `metadata.json`; no valida máscaras, procedencia humana, segunda revisión/adjudicación, calibración SAM o checkpoint. Acepta checkpoint nulo y puede sobrescribir una congelación. `verify_freeze_for_evaluation()` compara el hash del archivo inventario, pero no el de los scripts que éste enumera; tampoco liga las máscaras/metadata de referencia o el checkpoint cargado. Además, `--config` permite leer otra configuración después de comprobar la configuración por defecto.

**Reproducido:** sesenta metadatos sintéticos vacíos y ningún PNG/calibración/checkpoint permiten crear una congelación aceptada por la puerta; editar el código listado o la referencia no hace fallar esa puerta. Segunda llamada sobrescribe `freeze.json`. El bypass por `--config` se observa por lectura del flujo; no se lanzó un runner de evaluación para demostrarlo.

**Corrección requerida:** manifiesto completo de archivos de código y dependencias locales efectivas, pesos/revisión, selecciones y referencia individual/consenso/logs; validar su contenido/hashes al congelar y al consumir. Comprobar que GT es válida y adjudicada y que hay calibración real satisfactoria. Verificar checkpoint real y commit antes de inferencia; rechazar configuración alternativa discordante. Freeze inmutable; modificaciones abren versión nueva. Compartir puerta entre runner, render, scoring y report final para impedir mezclar resultados/configuraciones antiguos con datos nuevos. Un render previo de evaluación también debe respetar la revisión solicitada.

**Aceptación:** tests que alteren de uno en uno código, helper local, peso, config efectiva, selección, GT y log deben bloquear. Metadatos vacíos, referencia incompleta, ausencia de calibración y recongelación también deben bloquear.

### R2 · P1 · Se pueden perder casos del denominador

Localización: `scripts/segmentation_benchmark/s07_score.py:246` y ramas `continue` en 253, 264 y 300.

El scoring omite imágenes sin GT y métodos/vistas sin archivos. Las tasas se calculan sobre los registros restantes. Mencionar `n_missing_gt` es útil, pero no impide producir resúmenes comparativos incompletos; un método que se quede sin salidas puede desaparecer de la tabla. Faltan validación de hashes/configuración/procedencia de predicciones y vistas al puntuarlas.

**Reproducido:** dos casos sintéticos, uno sin GT y uno con sólo una vista V1, generan estadísticas sin error: no aparecen L1/S1/V0 ni fallos por su ausencia. Esto no es una ejecución sobre las sesenta imágenes.

**Corrección requerida:** en evaluación, GT incompleta debe bloquear puntuación definitiva; las salidas faltantes/runtime_error deben figurar para cada caso×método esperado, con máscara vacía y fallo cuando exista GT vegetal no vacío, más fallback operativo separado. Tuning puede permitir parcialidad, pero debe declarar tablas incompletas y evitar elegibilidad/ranking. Exportar n esperado, n observado, n GT válido, n evaluable y n fallos por entidad y contraste. Verificar procedencia y no emparejar subconjuntos diferentes silenciosamente.

### R3 · P1 · La pérdida de un órgano completo puede considerarse aceptable

Localización: `scripts/segmentation_benchmark/s07_score.py:322`; contrato de anotación en `s01_annotation_io.py:117`.

`critical_organs` se ofrece en la plantilla, pero no se lee al puntuar. `critical_failure` depende sólo del área perdida y los puntos finos. Por ello una hoja pequeña completa puede desaparecer sin superar el 2 % de área y sin puntos que disparen el criterio.

**Reproducido:** un fixture conserva 900 píxeles de cuerpo vegetal y elimina una hoja completa de cuatro píxeles, listada como órgano crítico: retención 99,56 %, fallo crítico falso. La forma exacta de representar órganos todavía necesita un esquema, pero el código actual no consulta ese campo bajo ningún esquema.

**Corrección requerida:** definir identificación/representación de órganos y revisión ciega de pérdidas completas, almacenar cobertura por órgano y estado humano pendiente/no evaluable. Incorporar pérdida de órgano en decisión antes de declarar aptitud; nunca convertir ausencia de revisión o puntos en prueba de conservación morfológica. Excluir también puntos en `ignore_uncertain`: actualmente se siguen contando, lo que se reprodujo en fixture.

### R4 · P2 · Estadística pareada y detalle no están conectados al experimento

Localizaciones: `scripts/segmentation_benchmark/s07_score.py:189`, `s07_score.py:350` y `s05_report.py:58`.

Existe una función bootstrap y un test determinista, pero `score_split()` no la llama ni construye los contrastes pareados especificados. Tampoco produce tablas por año/cámara, medición de detalle proyectado en 224/384/1024, pérdidas separadas por crop/máscara, ni decisión de elegibilidad/Pareto. Sólo se puntúan soportes a partir de metadata de 384. El informe vuelca algunos diccionarios y tiempos; no realiza esos análisis.

Además, la función devuelve mediana de diferencias por pareja, que no equivale a diferencia de medianas de métodos. Ejemplo sintético reproducido: a=[0,100,101], b=[0,1,100]; ambos estimandos son 1 y 99 respectivamente. Ambos pueden ser útiles si se etiquetan y preregistran correctamente.

**Corrección requerida:** integrar uniones pareadas verificadas, estimandos exactos e IC por contraste, con subconjunto P y estratos previstos. Medir detalle retenido/proyectado y estado por tamaño, no deducir fidelidad de una ampliación. Reportar métricas primarias/puntos/bordes y fallos con denominadores completos. Añadir tests de integración del informe usando fixtures con diferencias conocidas, incluidos nulos y fallos.

### R5 · P2 · Las ramas asistidas todavía no están implementadas

Localización: CLI de `scripts/segmentation_benchmark/s06_run_methods.py` (sólo L0/L1/S1).

Aunque el encabezado menciona S2/L2 y hay presupuesto en configuración, no existe flujo para esos métodos, registro de interacciones, aplicación de correcciones ni verificación del presupuesto. La función de adjudicación de referencia sólo copia archivos y añade un nombre; no debe confundirse con una interfaz para asistencia o consenso humano documentado.

**Corrección requerida:** implementar S2/L2 con operador sin GT, límites/tiempos/acciones y salidas versionadas, o delimitar explícitamente la entrega actual como automática y dejar estas ramas pendientes antes de comparar coste asistido. Completar registro de segunda revisión de las sesenta y adjudicación trazable; las 110 filas actuales representan noventa anotaciones primarias más veinte dobles, no toda la segunda revisión requerida.

### R6 · P2 · Ejecución y trazabilidad SAM aún incompletas

Localizaciones: `s06_run_methods.py:317`, `s06_run_methods.py:412` y `s06_run_methods.py:514`.

No es un defecto que falten torch/pesos y se declare `dependency_missing`; es una dependencia real correctamente expuesta. Sí faltan en el runner comprobación del hash esperado de pesos/commit, aplicación efectiva de `dtype`, calentamientos configurados y manejo por imagen de OOM/excepciones durante inferencia. Una excepción en ese bloque puede abortar el lote sin registrar `runtime_error` para el caso. Los tiempos no incluyen de forma comparable el ancla L1 compartida en S1 y no se alterna el orden. Se guardan sólo máscaras asociadas; faltan todas las instancias/cajas y probabilidades disponibles para auditar la asociación.

La caché compara configuración y hash de checkpoint declarado, pero no código ni integridad de las salidas; los timings publicados pueden sobrescribirse sólo con casos recalculados. También `--write` de inventario y la preparación de plantillas pueden sobrescribir material existente sin rechazar un benchmark congelado.

**Corrección requerida:** pin/check efectivo, autocast/dtype explícitos compatibles con GPU, calentamientos y costes compartidos declarados, registros por caso de error/éxito/caché, salidas brutas auditables y caché por entradas reales verificadas. No sobrescribir evidencia congelada o anotaciones. Smoke-test real sólo en tuning cuando existan entorno/pesos, con medición de memoria; no asumir que la GPU de 8 GB basta para el flujo configurado.

### R7 · P2 · La ausencia de tierra puede aprobar una unión incompleta

Localización: `scripts/segmentation_benchmark/s06_run_methods.py:246`.

Si hay una planta asociada al disco pero ninguna máscara de suelo, la función retorna `ok`, y V4 se presenta como planta+tierra. **Reproducido** con una instancia vegetal sintética y lista de suelos vacía. Contradice la regla propuesta de marcar incierta una unión cuando falte suelo/planta vinculable.

**Corrección requerida:** separar `plant_ok`, `soil_ok` y `union_ok`, conservar planta como resultado parcial cuando proceda y aplicar la contingencia especificada por vista. Si se prefiere aceptar automáticamente planta sin tierra, rectificar el protocolo antes de evaluación y etiquetar el caso; no cambiarlo silenciosamente.

## Qué sí quedó confirmado

- Los once tests entregados pasan al ejecutarlos de nuevo. Cubren utilidades valiosas, pero no las propiedades completas del experimento.
- Al reconstruir el muestreo en memoria, las listas tuning/evaluation/stress coinciden exactamente con las publicadas; sin materializarlas de nuevo. Se verifican roles, cuotas y disjunción en esa construcción.
- Los hashes de código del inventario entregado coinciden en esta revisión. Esto verifica su estado actual, no que el gate impida un cambio futuro.
- Los dieciocho círculos L1 almacenados en tuning coinciden exactamente con las propuestas Hough históricas correspondientes (diferencia máxima 0 px). No se detecta un desvío del ancla baseline en esos casos; no se reejecuta inferencia para afirmar equivalencia exhaustiva de toda la tubería.
- Registro y entradas protegidas verificadas. No hay `freeze.json`, predicciones/vistas de evaluación publicadas, ni casos de consenso humano. Los resultados S1 se declaran dependencias pendientes; no se observan máscaras SAM fabricadas en la entrega revisada.

`validation.json` valida seis clases de comprobaciones de inventario/plantillas/integridad. Su `all_passed=true` debe interpretarse dentro de ese alcance; no acredita masks/SAM, freeze, scoring completo ni aptitud morfológica.

## Orden recomendado para la siguiente entrega

1. Resolver R1 y R2 con fixtures adversariales y gates compartidos, antes de preparar cualquier freeze.
2. Resolver R3 y definir esquema de órganos, revisión y trazabilidad de anotación antes de encargar todas las máscaras.
3. Conectar análisis/detalle (R4), asistencia o alcance explícito (R5) y trazabilidad/estados parciales (R6/R7).
4. Completar entorno y calibración real SAM, referencia humana y revisión de esa nueva entrega. Sólo entonces congelar y ejecutar las sesenta, conservando T_real intacto.

Evidencias reproducibles: `scripts/s27_review_segmentation_benchmark_v1.py` y [recibo de comprobaciones](15_REVISION_SEGMENTATION_BENCHMARK_V1_CHECKS.json). Las comprobaciones adversariales exitosas identifican defectos, no un benchmark aprobado. No se reparó código de la implementación en esta revisión.
