# Guía práctica de máscaras humanas para el benchmark

13 de noviembre de 2026 · recomendación operativa M042. No se han creado anotaciones humanas ni configurado una herramienta en esta sesión.

## Qué es una máscara

Es una imagen del mismo tamaño y orientación que la fotografía, con una decisión por píxel. En la máscara de planta, blanco=tejido vegetal visible de la maceta objetivo y negro=todo lo demás. Se genera otra máscara independiente de tierra. No es una caja, un contorno sin rellenar, una captura de pantalla ni la foto con el fondo borrado. En el programa se pueden usar colores translúcidos; el formato final del benchmark son PNG monocromos binarios.

Para una foto orientada de 6000×4000, cada máscara debe ser 6000×4000, aunque la planta ocupe sólo una zona. Si EXIF cambia la orientación, usar el tamaño orientado efectivo y no el almacenado antes de rotar. El recorte o reducción para el modelo se hace después de anotar.

## Software recomendado

**CVAT**, con herramienta manual Brush/Mask y polígonos convertidos a máscara. Permite pintar superficies amplias y corregir bordes/tallos con pincel y borrador; para esta tarea interesa más esa combinación que una caja rectangular o un polígono de pocos vértices. Puede usarse una instancia disponible para el investigador; aquí no se ha creado cuenta, instalado servidor ni subido fotografías.

Documentación oficial: [herramienta de pincel](https://docs.cvat.ai/docs/manual/advanced/annotation-with-brush-tool/), [exportación Segmentation Mask](https://docs.cvat.ai/docs/dataset_management/formats/format-smask/). Verificar la versión de la instancia al preparar la tarea.

## Preparación de la tarea

1. Empezar con tres imágenes de las dieciocho de **tuning**, seleccionadas sin consultar predicciones para aprender el flujo. No usar las sesenta de evaluación para ensayar reglas.
2. Preparar copias sin pérdida de los originales aplicando EXIF y conversión sRGB del proyecto, a resolución nativa, sin reducir/recortar. Nombres anónimos y un mapa privado blind_id↔image_id/SHA. Conservar hashes de copias y referencia al original. **Este lote listo para CVAT y su importador/exportador todavía requieren preparación**; las plantillas JSON entregadas no son esas imágenes ni un proyecto CVAT ya configurado.
3. Crear etiquetas con exactamente los nombres de la rúbrica: plant_target, soil_target, other_plant, pot_rim_wall, card_label, other_background, ignore_uncertain. El color visible de cada etiqueta es libre y no tiene significado biológico.
4. No mostrar al anotador especie de diseño/trabajo ni resultados SAM/HSV. Identificar de forma inequívoca la maceta objetivo con una instrucción común, sin revelar contornos de referencia o predichos.
5. La referencia del benchmark se traza **manualmente desde el original**, sin iniciar con SAM, HSV, selección automática por color o una máscara de otro método que después se corrige. Las correcciones asistidas pertenecen a otra rama del experimento y no sustituyen esta referencia independiente.

## Qué debe quedar marcado

| Etiqueta | Incluir | Excluir |
|---|---|---|
| plant_target | Hojas completas, cotiledones, tallos, pecíolos y tejido no verde identificable de las plantas de la maceta objetivo; también hojas que sobresalen de ella | Plantas vecinas, huecos entre hojas, tierra y sombras proyectadas sobre el suelo |
| soil_target | Sustrato visible del interior de la maceta objetivo, incluidos sus gránulos | Borde/pared de maceta, hojas, tarjetas y tierra exterior; no inventar suelo bajo las hojas |
| other_plant | Vegetación ajena identificable | Planta objetivo |
| pot_rim_wall | Borde y pared visibles de la maceta objetivo | Sustrato |
| card_label | Tarjeta/etiqueta visible | Resto de objetos |
| other_background | Resto de píxeles válidos una vez asignadas las clases anteriores | Clases anteriores e incertidumbre |
| ignore_uncertain | Únicamente partes donde de verdad no se puede decidir borde o identidad | Estructuras finas que sí son identificables, aunque cueste trazarlas |

Las superficies visibles tienen una sola clase. Donde una hoja tapa suelo se marca planta; no se pinta suelo debajo. Un mismo píxel no pertenece a planta y tierra. other_background puede obtenerse al finalizar como complemento de las otras clases válidas, con inspección humana; no requiere colorear a mano millones de píxeles.

Si hay varios individuos en la maceta objetivo, la referencia primaria incluye su unión. Registrar conteo observado o incertidumbre, sin asumir que coincide con el número sembrado. No convertir la tarea en selección arbitraria de una sola planta.

## Cómo dibujar, fotografía por fotografía

1. Abrir la imagen, identificar la maceta objetivo y examinar todos los extremos vegetales visibles.
2. Trazar las hojas con polígonos suficientemente detallados o pincel de máscara; rellenar la superficie. Reservar un pincel pequeño para tallos/pecíolos y dientes del borde que realmente sean visibles.
3. Acercarse hasta distinguir los píxeles y ajustar con borrador. El zoom del visor no cambia el tamaño del archivo. No engordar tallos para que se vean mejor ni alisar contornos para que parezcan más limpios.
4. Alternar máscara visible/oculta y superposición translúcida para comprobar que no se pierden ápices ni aparecen halos de suelo. Los huecos de fondo entre órganos deben quedar fuera de plant_target.
5. Marcar el suelo visible y después las clases de contaminación. Usar las opciones de quitar píxeles subyacentes o corregir solapamientos, verificando que ninguna operación borra tallos ya dibujados.
6. Marcar incertidumbre sólo donde sea necesaria, con el mismo criterio en todo el lote. No completar partes ocultas o fuera de la foto; registrar truncamiento de origen.
7. Registrar tiempo activo, autor y fecha; guardar. Exportar y validar estas tres fotos piloto antes de continuar con las demás.

## Puntos finos y órganos críticos

Además de las máscaras se necesitan hasta veinte puntos sobre ápices y tallos/pecíolos finos según orden/cuotas de la rúbrica. Estos puntos ayudan a detectar pérdidas pequeñas que pesan poco en el área total. Se anotan sobre el original, no sobre una predicción, y fuera de regiones ignore.

Anotar también cuáles son los órganos críticos visibles cuya pérdida completa debe contar como fallo. **La implementación revisada aún no tiene un esquema suficiente para usar ese campo al puntuar** (R3 de M041); fijar con el implementador IDs y representación por órgano antes de realizar esa parte de las sesenta imágenes. No sustituirlo por texto libre que luego el programa ignore.

## Exportación y compatibilidad

Exportar el trabajo de CVAT en Segmentation Mask y conservar también una copia nativa de anotaciones para no perder metadatos/puntos. La exportación contiene mapas de clases/instancias y su correspondencia de etiquetas. No asumir que cada PNG exportado ya es una capa binaria válida para nuestro lector.

Hace falta un adaptador validado que use el mapa de clases para producir, por fotografía:

```text
plant_target.png
soil_target.png
other_plant.png
pot_rim_wall.png
card_label.png
other_background.png
ignore_uncertain.png
metadata.json
```

Cada PNG final: modo L, uint8, sólo 0/255, sin cambio de dimensiones, orientación o posición. Una clase ausente produce máscara negra completa. No convertir a gris un mapa multicolor y umbralizarlo: se perdería la identidad de clases. No guardar máscaras JPEG ni obtenerlas mediante capturas de pantalla.

La conversión debe comprobar tamaños, clases disjuntas, hash/origen, puntos y ausencia de interpolación que altere etiquetas; comparar visualmente superposición reimportada sobre las tres fotos piloto. El validador actual comprueba parte de estas condiciones, pero mantiene las limitaciones documentadas en M041 y no acredita por sí solo revisión humana o completitud de órganos.

## Revisión humana e independencia

Tras aprender el flujo en tuning, continuar con las dieciocho y acordar la rúbrica antes de las sesenta nuevas. En evaluación: primera anotación de las sesenta; segunda persona revisa todas y anota veinte de forma independiente, sin copiar ni ver la máscara de la primera. Comparar y adjudicar diferencias conservando versiones. Registrar quién revisó y cómo se resolvieron discrepancias. Si sólo se dispone de una persona, declararlo y mantener el estado provisional, sin fabricar una segunda revisión.

No hace falta anotar las 1.419 fotos para este benchmark. La calidad de referencia en el subconjunto, especialmente órganos finos de palmeri, es más importante que acelerar mediante una segmentación automática que estemos intentando evaluar.
