# Revisión geométrica local

Desde la raíz del proyecto, con Pillow, numpy y Tkinter disponibles:

```powershell
.venv\Scripts\python.exe scripts\s01_annotate_metric_geometry.py
```

La herramienta abre exclusivamente las imágenes C_fit activas de `data/processed/preprocessing/development_v1/selection.json`. No inicia servidores ni accede a la red. No se ha ejecutado aquí la interfaz ni se han creado revisiones por el investigador.

1. Escribir el nombre del revisor y comprobar la fecha ISO.
2. En modo borde, pulsar al menos seis puntos bien distribuidos alrededor del **borde exterior de la boca**. Evitar sombras, tubos y el borde interior. El círculo y el residuo RMS se muestran al disponer de puntos suficientes. El residuo no mide por sí solo inclinación, exactitud métrica ni incertidumbre.
3. En modo envolvente, pulsar dos esquinas opuestas del rectángulo que contiene **toda la vegetación visible de la maceta**. No confundir la envolvente con una anotación por planta o con tejido oculto. Una tercera pulsación comienza otra envolvente. Se puede deshacer el último punto del modo activo.
4. Elegir explícitamente `usable` o `unusable` para la referencia, e indicar `true` o `false` sobre vegetación cortada en el original. Ambos campos empiezan vacíos. Si no puede decidirse, dejar la imagen pendiente sin guardarla. Una referencia no usable necesita motivo escrito y puede guardarse sin geometría. Una referencia usable exige puntos suficientes y envolvente completa.
5. Registrar oclusión, inclinación, mala visibilidad, falta de precisión y otros límites en notas. Un círculo ajustado no aprueba automáticamente una referencia ni confirma especie. La escala corresponde al plano nominal de la boca, no a dimensiones 3D de las plantas.
6. Pulsar **Guardar revisión**. Navegar no guarda automáticamente: si hay cambios, se ofrece guardar, descartarlos o cancelar. Cerrar tiene la misma protección.

La salida es `annotations_reviewed.json`, separada del piloto y de la plantilla. Se pueden cerrar y reabrir las anotaciones; cada guardado conserva una copia histórica de la salida anterior con fecha UTC. No editar ni reutilizar esas copias como listas independientes. La salida incluye sólo imágenes efectivamente revisadas y guardadas; las demás siguen pendientes. Se verifican SHA-256 y dimensiones antes de mostrar cada imagen. Las coordenadas guardadas están expresadas en píxeles del original **después de orientar por EXIF**, compensando la escala de visualización; los puntos y el residuo se conservan. Los perfiles ICC válidos se convierten a sRGB para mostrar; sin perfil se registra la suposición sRGB.

La pantalla adapta la imagen al espacio disponible. Maximizar la ventana mejora la precisión; no atribuir precisión subpíxel al clic sobre una vista reducida. Si no se distinguen los extremos de la vegetación o la referencia, mantener pendiente o registrar `unusable`. Esta herramienta no congela campo, resolución, tolerancias ni aptitud del corpus; esas decisiones necesitan la revisión del lote y las comprobaciones del protocolo. La medición repetida independiente aún debe planificarse y registrarse; no se estima automáticamente reproducibilidad.

No usar `annotations_pilot.json` como si fuera esta revisión. Una imagen con referencia usable y vegetación cortada permanece fuera de los maestros elegibles. El script de maestros consume este JSON a través de `--annotations`; no es necesario copiar medidas al manifiesto crudo.
