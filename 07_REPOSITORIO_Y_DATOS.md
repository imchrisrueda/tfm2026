# Repositorio remoto y datos locales

El repositorio versiona código, documentación del TFM, bitácora metodológica, diseño experimental y evidencias de organización. Remoto: `git@github.com:imchrisrueda/tfm2026.git`.

Por solicitud del investigador, los datasets no se suben a Git. `.gitignore` excluye:

- `data/` completo: originales, copias de revisión, maestros, manifiestos y resultados de experimentos alojados allí.
- `sample/` y fotografías de `analisis_muestra/`.
- `scratch/`, entornos Python, cachés, pesos de modelos y archivos habituales de credenciales.

Los metadatos y anotaciones de diseño de `exp_design/`, los documentos de `documentacion/`, la memoria en `doc/` y el archivo histórico documental `99_archivo/` sí se conservan. Las fotografías de datasets no se sustituyen por imágenes reducidas en el remoto. Los archivos locales no se borran.

Clonar este repositorio no proporciona el dataset ni un entorno Python listo. Para reproducir análisis hay que disponer por separado del árbol local `data/` y verificar sus hashes/roles según la bitácora, el registro activo y los mapas de migración de `organizacion/`. Los enlaces hacia archivos excluidos requieren esa copia local. No regenerar particiones ni cambiar etiquetas para resolver su ausencia.

Antes de futuros commits, revisar `git diff --cached --stat` y los nombres de archivos preparados; no usar `git add -f` sobre las rutas excluidas.
