# Protocolo de escala con macetas conocidas

**Regla vigente · M029 (12 de noviembre de 2026):** la comparación autorizada sustituye la normalización obligatoria a campo común o por año. Los maestros generales conservan **encuadre completo y aspecto exacto**, con lado máximo 2048 px, EXIF/sRGB y sin recorte/relleno. Se preservan proporciones aparentes planta/maceta; no se afirma cm/píxel común ni escala 3D. Las referencias del lote son exploratorias `pilot_only`, separadas de la aptitud técnica general. Véase [comparación ejecutada](documentacion/01_informes/02_REVISION_PREPROCESADO_2026-11-12.md). Las propuestas y fórmulas siguientes son desarrollo histórico de la rama métrica, no instrucciones para recortar los maestros vigentes. **La actualización M026 que figura debajo queda sustituida por ésta.**

**Actualización histórica, sustituida por M029 · 12 de noviembre de 2026 (M026):** el investigador autoriza revisar **dos campos separados por año** tras observar limitaciones de cobertura. Esta decisión sustituye la exigencia de campo único de las secciones siguientes; sus fórmulas siguen siendo válidas usando `F_año`. Se ensayan 12 cm (2025) y 22 cm (2026), a 1024 px, como candidatos **sin congelar**. Corresponden a 85,33 y 46,55 px/cm: no comparar píxeles como si compartieran escala ni confundir macetas casi iguales en el lienzo con tamaño físico igual. La selección del campo debe contrastarse dentro de cada año y documentar exclusiones y asociación año/cámara/especie. Mantener ambos dominios identificados en entrenamiento, condiciones de generación y evaluación; su comparabilidad requiere revisión propia. No se adopta un campo distinto por foto. Véase [resultado del piloto](data/processed/preprocessing/README.md). El texto histórico del campo común se conserva para explicar el cambio, no como regla vigente que contradiga esta actualización.

Integrado el 10 de noviembre de 2026 en el [plan único](03_PLANIFICACION_TFM.md). Este documento desarrolla su etapa P2 y la auditoría geométrica P5–P7; el [diagrama](02_FLUJO_IMAGENES_TFM.md) representa el mismo proceso. El plan principal fija alcance, particiones y selección. Se conservan aquí las fórmulas y fundamentos técnicos, sin crear un flujo experimental alternativo.

Decisiones operativas ya resueltas: unidad de trabajo de una maceta con una o varias plantas de la misma especie confirmada; escenas mixtas fuera del núcleo supervisado; campo físico común; maestros inicialmente a 1024 px para el piloto; ninguna homografía general ni anotación exhaustiva de bboxes; ausencia de referencia/cobertura fiable implica reserva fuera del corpus principal a escala. Los parámetros numéricos se fijarán con desarrollo antes de evaluar, sin usar la prueba final ni los juicios expertos para ajustarlos. Los totales por especie siguen pendientes por indicación del usuario.

## 1. Datos confirmados y objetivo

- Todas las capturas contienen una o varias plantas en maceta, incluido el maíz, y son cenitales a menos de 1 m según el usuario.
- Diámetro exterior de la boca de maceta: **10 cm en 2025** y **20 cm en 2026**.
- Algunas fotos contienen una tarjeta amarilla de dimensiones conocidas por el usuario, todavía no comunicadas.
- Se quiere conservar la proporción de tamaño al generar imágenes.

El objetivo operativo será preservar el tamaño aparente de la planta respecto a una referencia conocida y establecer una escala nominal común del plano de referencia. La exactitud de dimensiones tridimensionales de la planta no se puede dar por conseguida con esta información.

No se ha ejecutado todavía un recorte métrico: falta medir el borde de las macetas y comprobar cuánto campo necesitan las plantas. El campo de 40 cm y los factores que aparecen debajo son ejemplos calculados, no parámetros ya validados.

## 2. Cambio respecto a la propuesta inicial

El recorte principal para el generador no se ajustará al tamaño de cada planta: eso haría que plantas pequeñas y grandes ocupasen un tamaño semejante al redimensionar.

Tampoco se igualará en píxeles el diámetro de todas las macetas: una maceta de 10 cm y una de 20 cm perderían así su diferencia física. Recortar a dos diámetros en cada año también produce campos distintos de 20 y 40 cm.

Se utilizará un **campo nominal común en centímetros**, centrado en la maceta, con escala uniforme y margen para las hojas que sobresalgan. Recortar exactamente al círculo o borde de la maceta puede truncar hojas y queda fuera del preprocesado principal.

## 3. Transformación para vistas aproximadamente cenitales

Tras aplicar la orientación EXIF, identificar el borde exterior de la boca de la maceta. Utilizar siempre ese borde físico; no alternar entre borde interior, superficie del sustrato y base de la maceta.

Definir:

- `D_i`: diámetro exterior conocido de esa maceta, en cm: 10 o 20.
- `d_i`: diámetro exterior medido en la imagen, en píxeles, cuando la vista sea suficientemente circular y la medición fiable.
- `F`: lado del campo nominal común de salida, en cm del plano de referencia.
- `N`: lado de la imagen final, en píxeles.

Entonces:

```text
escala_original_i = d_i / D_i                  [px/cm en el plano de referencia]
escala_salida = N / F                         [px/cm en el plano de referencia]
lado_recorte_original_i = F * d_i / D_i       [px]
factor_redimensionado_i = N * D_i / (F * d_i)
diametro_maceta_salida_i = N * D_i / F        [px]
```

Centrar ese cuadrado en la maceta, extraer contenido real y redimensionar isotrópicamente a `N × N`. Registrar centro, diámetro, ventana y factor. No estirar los ejes de manera distinta.

Ejemplo ilustrativo con `F = 40 cm` y `N = 1024 px`:

| Captura | Diámetro físico | Diámetro de salida | Escala nominal |
| --- | --- | --- | --- |
| 2025 | 10 cm | 256 px | 25,6 px/cm |
| 2026 | 20 cm | 512 px | 25,6 px/cm |

Un objeto de 5 cm situado en el mismo plano de referencia ocuparía 128 px en ambos casos. La hoja de una planta elevada sobre ese plano no cumple necesariamente esta igualdad.

## 4. Medición práctica y control de geometría

1. Empezar con anotación manual o semiautomática de una muestra por cámara, fecha, tamaño de maceta y grado de oclusión. Validar antes de automatizar todo el conjunto.
2. Ajustar un círculo a puntos visibles del borde cuando la vista sea casi cenital. No confundir tubo de riego o sombra con el borde; revisar los ajustes.
3. Registrar oclusión, residuo del ajuste y, cuando corresponda, ejes de una elipse como diagnóstico de inclinación o distorsión. No fijar umbrales numéricos de calidad sin examinar las anotaciones.
4. Si el borde está demasiado oculto, usar una referencia alternativa fiable o marcar la escala como no disponible. No adivinarla a partir del tamaño de las hojas.
5. No transformar sin más una maceta elíptica en un círculo: una rectificación justificable requiere información geométrica adicional. La calibración de cámara y un patrón plano conocido pueden permitir corregir el plano de referencia, pero no eliminan el relieve de las hojas. [OpenCV: homografías](https://docs.opencv.org/4.1.0/d9/dab/tutorial_homography.html).

La tarjeta rectangular, si se conoce su ancho y alto y se observan sus cuatro esquinas, aporta correspondencias para una transformación del plano de esa tarjeta. Si está sobre el sustrato y el borde está más alto, sus escalas no tienen por qué coincidir exactamente; no promediarlas como si fueran una única medida del mismo plano.

## 5. Elección del campo común

Medir sobre datos de desarrollo cuánto se aleja la vegetación del centro de la maceta en cada dirección. Elegir `F` suficiente para conservar la vegetación visible y un margen, con criterios comunes y documentados. El ejemplo de 40 cm solo será útil si cabe el dominio de plantas que se pretende generar.

No reducir `F` para ampliar cada plántula ni aumentarlo para cada planta grande. El núcleo utilizará un campo común; si no cubre todo el dominio, delimitar el dominio y registrar exclusiones antes de entrenar. Varios campos nominales serían una ampliación explícita del diseño con evaluación propia, no una alternativa aplicada silenciosamente.

Si la imagen original no cubre la ventana requerida, marcar la cobertura incompleta y reservarla fuera del corpus principal a escala. No rellenar ese corpus ni variar el campo por imagen para hacerlo encajar. Si las hojas ya estaban cortadas en la captura, siguen sin ser recuperables mediante preprocesado. Documentar cómo estas exclusiones afectan a la cobertura de especies y estadios.

Si el campo común vuelve demasiado pequeñas las plántulas, comprobar primero una mayor resolución en el piloto conservando el campo. Una rama secundaria de detalle para clasificación quedará como extensión fuera del núcleo; no reemplaza el maestro a escala ni se utiliza para atribuir tamaños físicos al generador.

## 6. Tarjetas y varias plantas

Medir y registrar la tarjeta antes de decidir su papel en el entrenamiento. La maceta aporta una referencia presente en todo el conjunto; la tarjeta puede servir para verificar mediciones y geometría. No es necesario generar una tarjeta para conservar la relación aparente planta/maceta.

No retirar tarjetas mediante inpainting ni recortar cada escena a un tamaño distinto para ocultarlas. Priorizar un subconjunto real sin tarjetas para el LoRA solo si conserva los individuos y tamaños necesarios. Si las tarjetas predominan en plántulas, excluir todas esas fotos introduciría un sesgo de estadio: habría que mantener y documentar ese grupo o conseguir capturas reales equivalentes sin tarjeta.

En macetas con varias plantas, la unidad generada será la escena de una maceta con todas sus plantas de A. palmeri; registrar número de plantas, identidad confirmada y solapamiento. Las escenas con mezcla de especies o identidad incierta quedan fuera del entrenamiento supervisado y del LoRA principal. La cobertura total del dosel no se atribuirá a una planta individual. Mantener juntas las capturas de una misma maceta y las trayectorias de sus individuos cuando puedan compartir información entre particiones.

## 7. Entrenamiento y generación

- Guardar maestros con el campo común y aplicar únicamente la transformación numérica que corresponda a cada modelo.
- Evitar zoom aleatorio, `RandomResizedCrop` y cualquier recorte posterior que cambie el campo nominal. Para aumentos geométricos sencillos, usar giros de 90 grados y reflejos que conserven el lienzo y la vegetación.
- Las leyendas del generador identificarán especie, diámetro de maceta, número de plantas, estadio y categoría de tamaño aparente cuando se hayan anotado. No inferir dimensiones exactas de hojas a partir del estadio.
- Mantener los tres entrenamientos y el resto de condiciones del TFM. Usar prompts comparables para los dos diámetros cuando haya datos suficientes.
- Verificar si diámetro y año están asociados a especie o estadio. La normalización no elimina esa asociación del conjunto original.

Un LoRA puede aprender distribuciones de tamaño y contexto, pero el preprocesado y una leyenda con centímetros no imponen por sí solos una restricción geométrica exacta. Si se exige un tamaño exacto por imagen, hará falta un mecanismo de condicionamiento espacial o composición y una validación propia; sería una ampliación del flujo principal.

## 8. Auditoría de escala en sintéticas

Registrar, además de la taxonomía y morfología:

- número y legibilidad de macetas, integridad del borde y diámetro aparente;
- número de plantas y correspondencia con lo solicitado;
- anchura y altura aparente de la vegetación respecto al diámetro de la maceta;
- área visible de cobertura respecto a una referencia de maceta consistente, si hay máscaras verificadas;
- diferencias de esas distribuciones entre reales y sintéticas, por estadio, diámetro y ejecución;
- desviación del diámetro generado respecto al esperado en el lienzo nominal.

Las dimensiones de cobertura son de la proyección visible; no equivalen a área foliar total, biomasa, altura ni tamaño 3D de cada hoja.

Si el diámetro generado queda a otra escala, redimensionar toda la escena puede corregir su ocupación en el lienzo, pero no corrige una relación planta/maceta incorrecta. No ampliar o encoger solo la planta para presentar como logrado un tamaño que el generador no produjo.

Una maceta sintética no es una referencia física observada: se le asigna el diámetro de la condición solicitada y se evalúa su coherencia visual. Una tarjeta o barra de escala dibujada por el generador tampoco certifica centímetros reales.

## 9. Alcance de la escala

La escala derivada del diámetro corresponde al plano de la boca de la maceta. En una aproximación de cámara cenital ideal, si la cámara está a distancia `H` de ese plano y una hoja está elevada `h` hacia la cámara, su magnificación relativa es `H / (H - h)`. Por eso a poca distancia el relieve puede influir apreciablemente. Es una explicación geométrica, no una corrección ya aplicada a estas fotos. El modelo de proyección de cámara distingue coordenadas 3D y su imagen 2D. [OpenCV: calibración](https://docs.opencv.org/5.0/main_modules/calib.html).

Para este TFM el objetivo se formulará como **conservación y evaluación de proporciones aparentes respecto a macetas de tamaño conocido**, junto con **normalización de la escala en el plano de referencia**. Su grado de cumplimiento se determinará con resultados, sin anticiparlo como logrado. La certificación de dimensiones reales de las plantas necesitaría información adicional sobre altura/profundidad, calibración o reconstrucción.

## 10. Homografía: cuándo aporta y qué anotar

Usaremos «vista cenital» para describir las fotos. Conviene distinguir el uso fotográfico de la terminología astronómica: cenit es la dirección superior y nadir, su opuesta; una cámara aérea mirando al nadir también mira hacia abajo. «Nadir» no significa por sí mismo una fotografía tomada desde el suelo hacia arriba. [RAE: cenit](https://dle.rae.es/cenit), [RAE: nadir](https://dle.rae.es/nadir).

Una homografía permite rectificar un plano conocido a una vista frontal de ese plano. No descubre automáticamente el suelo ni determina que el borde de la maceta sea paralelo a él. Se elegirá explícitamente como referencia el plano de la tarjeta, de un patrón horizontal o de la boca de la maceta, según la geometría disponible.

Para calcular una homografía métrica de la tarjeta, anotar las cuatro esquinas en orden y conocer ancho y alto. Asociarlas a las esquinas de un rectángulo de esas dimensiones, con una escala de salida explícita. La tarjeta debe ser plana, visible y estar paralela al plano que se pretende representar; si no, la rectificación corresponde a su propia orientación. Una homografía por imagen solo puede reutilizarse si la geometría relativa cámara/plano permanece fija. Si hay distorsión óptica apreciable, calibrar y corregir primero para esa cámara y configuración. [OpenCV: homografías](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html).

Un contorno circular proyectado y su diámetro físico, sin calibración ni información geométrica adicional, no determinan por sí solos una homografía métrica única. Hacer circular una elipse mediante un estiramiento no basta para acreditar la rectificación. Con intrínsecos y un modelo geométrico conocido pueden plantearse estimaciones de pose que requieren validación y resolución de ambigüedades.

Decisión operativa del plan único: no imponer una homografía a todas las imágenes. Examinar primero inclinación, distorsión y disponibilidad de referencias. Para vistas suficientemente próximas a la vertical se utilizará la normalización aparente basada en diámetro; únicamente si el piloto identifica inclinación relevante y referencias suficientes se incorporará una rectificación validada y documentada. Si no puede medirse de forma fiable, reservar el caso fuera del corpus principal. Las hojas fuera del plano seguirán teniendo relieve y oclusiones; no llamar al resultado ortofoto métrica de toda la planta.

## 11. Anotaciones mínimas para el flujo de generación

El LoRA convencional de texto a imagen se entrena con imágenes y texto; no requiere bboxes de plantas. El script FLUX.1 de Diffusers permite un texto común con `instance_prompt` o textos por imagen mediante `caption_column`. Los nombres de directorio no se convierten automáticamente en leyendas. [Script oficial](https://github.com/huggingface/diffusers/blob/main/examples/dreambooth/train_dreambooth_lora_flux.py).

| Anotación | Utilidad y prioridad |
| --- | --- |
| Especie, sesión, grupo de maceta/individuos, número de plantas y diámetro físico | Necesarios para el inventario, particiones y condiciones del experimento. |
| Leyenda por imagen con atributos confirmados | Requerida por el plan único para el LoRA, en el formato que realmente lea el entrenador. |
| Puntos del borde de maceta o círculo/elipse verificado | Necesarios cuando se utiliza esa referencia para medir escala; guardar calidad y coordenadas. |
| Cuatro esquinas de tarjeta/patrón y medidas físicas | Necesarios si se rectifica a partir de ese rectángulo conocido. |
| Bbox de toda la vegetación visible | Opcional para comprobar que el campo común no trunca la escena; no define por sí misma la escala. |
| Bbox por planta | Opcional; útil para un futuro detector o recortes por individuo, con límites ante solapamiento. |
| Máscaras de vegetación | Opcionales para medir cobertura proyectada; no sustituyen la calibración geométrica. |

Para el TFM, priorizar metadatos y referencias geométricas sobre etiquetar exhaustivamente cada planta. Una bbox rectangular alineada con los ejes no proporciona las esquinas reales de una tarjeta inclinada ni el diámetro preciso de un borde de maceta.

Guardar en un manifiesto las etiquetas y leyendas junto a las anotaciones geométricas; organizarlas por directorios puede ayudar al manejo y a la clasificación supervisada si el cargador interpreta esos directorios. En escenas mixtas, una única carpeta de especie no identifica qué planta pertenece a cada clase. Las anotaciones de bboxes solo condicionarán la posición durante la generación si se usa un método que las consuma explícitamente; añadirlas al disco no modifica el entrenamiento LoRA estándar.

## 12. Aplicación a la auditoría y selección

P5 registrará en todo el corpus el estado de maceta/escena y medirá su diámetro cuando sea fiable. P6 medirá además la envolvente vegetal y las proporciones en el panel real/sintético compartido por A/B/C. Esta distribución del esfuerzo evita exigir segmentación exhaustiva de todas las generaciones.

Las tolerancias se fijarán con mediciones repetidas y referencias reales de desarrollo antes de abrir el panel experto. **Actualización M029:** el corpus general no tiene un diámetro esperado único `N * D / F`; esa fórmula sólo corresponde a una rama métrica declarada. Evaluar relaciones planta/maceta y ocupación de lienzo frente a referencias de condiciones comparables, preservando diámetro nominal, año y encuadre. No ajustar las imágenes generadas para hacerlas coincidir con una referencia. Anchura/altura de envolvente son proyecciones, no dimensiones 3D de una planta.

Para superar el control de proporciones/escena se exigirá referencia medible, ausencia de truncamiento que invalide el uso, número de plantas conforme y relaciones planta/maceta y ocupación del lienzo plausibles según referencias comparables y rúbrica. Con M029 el diámetro nominal solicitado no determina un diámetro esperado en píxeles; no deducirlo de los centímetros del prompt. Si no hay evidencia suficiente, registrar no evaluable, no aprobado. No reescalar la sintética para hacerla coincidir con las referencias antes de medir.

La selección final de P7 exige a la vez candidatura automática de A. palmeri, validación botánica de al menos dos expertos conforme al plan y control de escala/escena superado. Una puntuación BioCLIP alta no sustituye esas condiciones. Las imágenes no seleccionadas o no revisadas por expertos permanecen en el corpus con su estado explícito.
