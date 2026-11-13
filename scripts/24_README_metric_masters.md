# Maestros con campo nominal común

`s18_prepare_metric_masters.py` es una aplicación separada del constructor de los
manifiestos autoritativos. No cambia etiquetas, grupos, asignaciones ni originales.
La salida contiene un manifiesto complementario completo CSV/JSON con las mismas
filas y columnas originales, enriquecido con medidas, rutas y estados. Las filas
sin maestro permanecen visibles con un estado explícito. No sustituir las listas
activas de particiones por candidaturas generales al entrenar.

Ejemplo de ejecución (las rutas de anotación/configuración son ilustrativas):

```powershell
python scripts/s18_prepare_metric_masters.py --annotations exp_design/geometry_development.json --config exp_design/preprocessing_pilot.json --output data/processed/metric_pilot_01
python scripts/test_30_prepare_metric_masters.py
```

El directorio de salida debe ser nuevo y estar dentro del proyecto. No se
sobrescriben resultados de otra ejecución. Los maestros PNG RGB incluyen perfil
sRGB; el informe `run.json` conserva hashes de entradas/código, versiones, modo y
recuentos. `master_sha256` permite verificar cada salida. La escala corresponde al
plano de la boca exterior de maceta, sin acreditar dimensiones 3D de las plantas.

La configuración JSON exige `field_cm` positivo o un mapa `field_cm_by_year`, `output_px` entero positivo y
`status` (`pilot` o `frozen`). `minimum_vegetation_margin_cm` opcional vale cero si
no se indica; sólo un valor explícito documenta un margen adicional exigido.
Ejemplo de estructura, **sin aprobar el campo numérico**:

```json
{"field_cm": 40, "output_px": 1024, "status": "pilot", "minimum_vegetation_margin_cm": 1}
```

Como ampliación explícita del diseño, el mapa
`"field_cm_by_year": {"2025": 12, "2026": 22}` permite ensayar campos diferentes.
Esto implica escalas de salida diferentes en px/cm; no debe describirse como
campo físico común entre años. Cada fila registra `common_field_cm` y
`metric_field_source`; se conserva el nombre de columna por compatibilidad,
sin implicar igualdad entre años. Si existe mapa, todos los años procesados
deben figurar en él: se rechaza un año desconocido incluso si también existe
`field_cm`. El campo global se admite como alternativa cuando no hay mapa.

Las anotaciones son una lista JSON o un CSV de una fila por imagen con:

- `image_id` y `source_sha256`, que deben coincidir con el manifiesto y archivo.
- `coordinate_space="exif_oriented"`: coordenadas continuas del borde de píxeles,
  origen superior izquierdo, dominio `[0,width] × [0,height]` después de EXIF.
- `pot_center_x_px`, `pot_center_y_px`, `pot_diameter_px` positivos/medibles. El
  diámetro nominal se toma del manifiesto, nunca del tamaño de las hojas.
- `review_status="accepted"`, `reference_quality="usable"`, `reviewer`,
  `review_date`: declaración explícita de revisión, no rellenada por el script.
- `measurement_scope="pilot_only"` identifica medidas provisionales: se aceptan
  para ensayos y se rechazan en `apply`, incluso con configuración congelada.
- `vegetation_truncated=false`: observación explícita de que la captura conserva
  la vegetación; vacío/desconocido no es equivalente a falso.
- `vegetation_bbox=[x0,y0,x1,y1]`: envolvente de toda la vegetación de la maceta de
  interés. En CSV se serializa como una cadena JSON. Se usa para verificar que el
  recorte y el margen la conservan; no define el campo ni la escala.

Se orienta EXIF antes de utilizar coordenadas. Si existe ICC embebido se convierte
a sRGB con Pillow/ImageCms; un perfil inválido detiene esa imagen con motivo
registrado. Sin ICC se declara la suposición sRGB para RGB/L, sin afirmar una
calibración colorimétrica. No se aplica normalización por imagen de brillo, color,
contraste ni balance de blancos.

El lado original del recorte es `field_cm * pot_diameter_px / nominal_cm`. Se
conserva el centro medido y se utiliza una ventana fraccional para redimensionar
isotrópicamente con Lanczos, sin redondear independientemente los ejes. Si la
ventana excede la captura o corta la envolvente y margen, no se crea maestro.
No hay relleno, inpainting, cambio de campo por imagen ni homografía.
Un campo menor que el diámetro nominal de la maceta también se rechaza. Las
medidas de borde válidas se conservan en columnas del manifiesto complementario
aunque la ventana requerida no quepa en el original; el estado de procesamiento
y motivo separan esa falta de cobertura de la ausencia de medición.

El modo `pilot` sólo abre imágenes activas anotadas de C_fit o C_val con
`validation_role=model_selection`. G_fit, calibración, M_aux y T_real no se abren
para seleccionar configuración. `--mode apply` exige `status=frozen`; T_real
requiere además `--include-test` explícito. Preparar sus píxeles con parámetros
congelados no autoriza usarlos para ajustar parámetros o modelos. El informe
conserva la petición de apertura de T_real; las filas sin anotación siguen sin
abrirse. No se producen automáticamente anotaciones para los casos restantes.

La batería sintética comprueba la escala común entre macetas nominales de 10 y
20 cm, ventana fraccional, rechazo de cobertura insuficiente y vegetación/margen
fuera del recorte, medidas no finitas, orientación EXIF, ICC válido/inválido y
protección de particiones en una ejecución completa. No equivale a una revisión
visual de los maestros reales ni permite cerrar por sí sola las tareas 18–20.
