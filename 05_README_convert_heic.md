# Convertidor de Imágenes HEIC a JPG (`01_Convert-HeicToJpg.ps1`)

Script de automatización en PowerShell y Python para la conversión masiva de imágenes de formato **HEIC / HEIF** (formato nativo de Apple iOS / iPhone) a formato estándar **JPG / JPEG**.

Diseñado específicamente para flujos de trabajo de fotogrametría, fotos de campo (`FIELD-Photos`) y catalogación científica donde la integridad de los metadatos es fundamental.

---

## 📌 Características Principales

- **Preservación total de metadatos EXIF**:
  - Conserva coordenadas de geolocalización **GPS** (latitud, longitud, altitud).
  - Conserva fecha y hora exacta de captura (`DateTimeOriginal`).
  - Conserva modelo de cámara, lente, apertura, exposición e ISO.
- **Conservación de perfil de color ICC**: Evita distorsiones cromáticas al convertir el espacio de color.
- **Filtro automático de ficheros AppleDouble (`._*`)**:
  - macOS suele crear archivos auxiliares ocultos que empiezan por `._` al transferir a sistemas Windows o discos exFAT/NTFS. El script los detecta e ignora para evitar errores falsos.
- **Modo reanudación / Omitir existentes**:
  - Por defecto omite las fotos que ya existan en la carpeta de destino, permitiendo pausar y reanudar o añadir fotos nuevas rápidamente sin reprocesar todo el conjunto.
- **Detección inteligente de rutas**:
  - Si en el parámetro de entrada se pasa la ruta de un archivo individual (ej. `IMG_4172.HEIC`), el script detecta automáticamente su directorio contenedor.
- **Instalación automática de dependencias**:
  - Comprueba la disponibilidad de Python y las librerías `pillow` y `pillow-heif`, instalándolas mediante `pip` si faltasen.

---

## ⚙️ Requisitos

1. **Windows 10 / 11** con **PowerShell 5.1** o **PowerShell 7+**.
2. **Python 3.10 o superior** instalado y accesible en el `PATH` (`python` o `py`).
3. Librerías Python requeridas:
   - `pillow >= 10.0`
   - `pillow-heif >= 0.16`
   *(El script las instala automáticamente si no estuvieran presentes).*

> [!TIP]
> Si PowerShell te bloquea la ejecución de scripts no firmados por la política de ejecución de Windows, abre PowerShell y ejecuta una vez:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

---

## 🚀 Uso Rápido

### 1. Menú de Ayuda (`--help` o `-h`)
Puedes consultar la documentación interactiva en consola en cualquier momento:
```powershell
.\01_Convert-HeicToJpg.ps1 --help
# o también:
.\01_Convert-HeicToJpg.ps1 -h
```

### 2. Conversión directa con valores por defecto del proyecto
Si ejecutas el script sin argumentos, procesará directamente la ruta de trabajo por defecto:
- **Entrada:** `D:\datos_palmeri\2025-06-20_Poveda-Palmeri\5_FIELD-Photos\HEIC`
- **Salida:** `D:\datos_palmeri\2025-06-20_Poveda-Palmeri\5_FIELD-Photos\JPG`

```powershell
.\01_Convert-HeicToJpg.ps1
```

### 3. Especificando carpetas de entrada y salida
```powershell
.\01_Convert-HeicToJpg.ps1 -InputFolder "D:\fotos_campo\HEIC" -OutputFolder "D:\fotos_campo\JPG"
```

O usando la sintaxis posicional abreviada:
```powershell
.\01_Convert-HeicToJpg.ps1 "D:\fotos_campo\HEIC" "D:\fotos_campo\JPG"
```

### 4. Forzar sobrescritura de archivos ya existentes
```powershell
.\01_Convert-HeicToJpg.ps1 -InputFolder "D:\fotos\HEIC" -OutputFolder "D:\fotos\JPG" -Overwrite
```

### 5. Ajustar calidad de compresión JPEG (1 - 100)
```powershell
# Calidad estándar (85)
.\01_Convert-HeicToJpg.ps1 -InputFolder "D:\fotos\HEIC" -OutputFolder "D:\fotos\JPG" -Quality 85

# Calidad máxima fotográfica (100)
.\01_Convert-HeicToJpg.ps1 -InputFolder "D:\fotos\HEIC" -OutputFolder "D:\fotos\JPG" -Quality 100
```

### 6. Escaneo recursivo de subdirectorios
Mantiene intacta la jerarquía de subcarpetas en el directorio de salida:
```powershell
.\01_Convert-HeicToJpg.ps1 -InputFolder "D:\campaña_2025" -OutputFolder "D:\campaña_2025_jpg" -Recursive
```

---

## 📋 Especificación de Parámetros

| Parámetro | Tipo | Alias | Valor por defecto | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `-InputFolder` | String (Posición 0) | `-InputPath`, `-Path`, `-i` | `D:\datos_palmeri\2025-06-20_Poveda-Palmeri\5_FIELD-Photos\HEIC` | Ruta de la carpeta que contiene las imágenes HEIC/HEIF (o ruta a un archivo individual). |
| `-OutputFolder` | String (Posición 1) | `-OutputPath`, `-Destination`, `-o` | Carpeta `JPG` hermana de la carpeta de entrada | Ruta de la carpeta donde se guardarán los archivos JPG convertidos. Se crea si no existe. |
| `-Quality` | Int (1-100) | `-q` | `95` | Factor de calidad JPEG. `95` ofrece fidelidad visual indistinguible de la fuente con buena compresión. |
| `-Overwrite` | Switch | *(ninguno)* | `$false` | Si se incluye, sobrescribe cualquier JPG existente en la carpeta de destino. |
| `-Recursive` | Switch | *(ninguno)* | `$false` | Si se incluye, busca imágenes en todas las subcarpetas del directorio de entrada. |
| `-ShowHelp` | Switch | `-Help`, `-h`, `--help`, `-?` | `$false` | Muestra la ayuda detallada del script y finaliza. |

---

## 🔍 Estructura de Salida y Ejemplo de Ejecución

Durante la ejecución, el script muestra una barra de progreso nativa en la parte superior y un registro detallado en consola:

```text
==========================================================
         CONVERTIDOR DE HEIC A JPG (Alta Calidad)         
==========================================================
 Origen  : D:\datos_palmeri\2025-06-20_Poveda-Palmeri\5_FIELD-Photos\HEIC
 Destino : D:\datos_palmeri\2025-06-20_Poveda-Palmeri\5_FIELD-Photos\JPG
 Calidad : 95%
 Sobrescribir: NO (omitir existentes)
 Recursivo   : NO
----------------------------------------------------------
Escaneando imágenes HEIC...
Se encontraron 60 imagen(es) para procesar.

 [1/60] IMG_4131.HEIC -> IMG_4131.jpg [OK]
 [2/60] IMG_4132.HEIC -> IMG_4132.jpg [OK]
 ...
 [60/60] IMG_4190.HEIC -> IMG_4190.jpg [OK]

----------------------------------------------------------
RESUMEN DE TRANSFORMACIÓN:
 - Total encontrados : 60
 - Convertidos       : 60
 - Omitidos          : 0
 - Errores           : 0
 - Tiempo total      : 18.42 segundos
 - Carpeta resultado : D:\datos_palmeri\2025-06-20_Poveda-Palmeri\5_FIELD-Photos\JPG
----------------------------------------------------------
```
