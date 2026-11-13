<#
.SYNOPSIS
    Convierte imágenes en formato HEIC/HEIF a formato JPG/JPEG en lote.

.DESCRIPTION
    Script de PowerShell para convertir imágenes HEIC (típicas de iPhone/iOS) a formato JPG.
    Conserva los metadatos EXIF completos (geolocalización GPS, fecha/hora, modelo de cámara)
    y el perfil de color ICC.

.PARAMETER InputFolder
    Ruta de la carpeta de origen que contiene las imágenes HEIC.
    Si se pasa la ruta de un archivo individual, el script usará su carpeta contenedora.
    Por defecto: D:\datos_palmeri\2025-06-20_Poveda-Palmeri\5_FIELD-Photos\HEIC

.PARAMETER OutputFolder
    Ruta de la carpeta de destino donde se guardarán los archivos JPG.
    Por defecto: Carpeta 'JPG' paralela a la de entrada.

.PARAMETER Quality
    Calidad de compresión JPEG (de 1 a 100). Por defecto: 95 (alta calidad fotográfica).

.PARAMETER Overwrite
    Si se especifica, sobrescribe los archivos JPG existentes en el destino.
    Por defecto omite los que ya existen para ahorrar tiempo.

.PARAMETER Recursive
    Si se especifica, busca archivos HEIC recursivamente en subdirectorios.

.EXAMPLE
    .\01_Convert-HeicToJpg.ps1
    Convierte usando las rutas por defecto del proyecto.

.EXAMPLE
    .\01_Convert-HeicToJpg.ps1 -InputFolder "D:\fotos\HEIC" -OutputFolder "D:\fotos\JPG"

.EXAMPLE
    .\01_Convert-HeicToJpg.ps1 -InputFolder "D:\fotos\HEIC" -OutputFolder "D:\fotos\JPG" -Quality 90 -Overwrite
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $false, HelpMessage = "Carpeta de origen con las imágenes HEIC")]
    [Alias("InputPath", "Path", "i")]
    [string]$InputFolder = "D:\datos_palmeri\2025-06-20_Poveda-Palmeri\5_FIELD-Photos\HEIC",

    [Parameter(Position = 1, Mandatory = $false, HelpMessage = "Carpeta de destino para los archivos JPG")]
    [Alias("OutputPath", "Destination", "o")]
    [string]$OutputFolder = "",

    [Parameter(Mandatory = $false)]
    [ValidateRange(1, 100)]
    [Alias("q")]
    [int]$Quality = 100,

    [Parameter(Mandatory = $false)]
    [switch]$Overwrite,

    [Parameter(Mandatory = $false)]
    [switch]$Recursive,

    [Parameter(Mandatory = $false)]
    [Alias("h", "help", "-help", "?")]
    [switch]$ShowHelp
)

# -------------------------------------------------------------------------
# 0. Menú de ayuda (--help / -h / -?)
# -------------------------------------------------------------------------
function Show-ScriptHelp {
    Write-Host @"
================================================================================
 CONVERTIDOR DE IMÁGENES HEIC A JPG / JPEG
 Script de automatización por lotes para fotos de campo y dispositivos móviles
================================================================================

SINOPSIS:
    .\01_Convert-HeicToJpg.ps1 [[-InputFolder] <String>] [[-OutputFolder] <String>]
                            [-Quality <Int32>] [-Overwrite] [-Recursive]
                            [-Help | -h | --help]

DESCRIPCIÓN:
    Convierte imágenes en formato HEIC/HEIF a JPG preservando al 100%:
      • Metadatos EXIF completos (etiquetas GPS, fecha de captura, cámara, exposición)
      • Perfil de color ICC incrustado
      • Orientación real de la imagen
    Ignora automáticamente archivos auxiliares creados por macOS (ficheros '._*').
    Verifica e instala dependencias requeridas (pillow, pillow-heif) automáticamente.

PARÁMETROS:
    -InputFolder, -InputPath, -Path, -i <String>
        Ruta del directorio que contiene los archivos HEIC/HEIF.
        Si se pasa la ruta de un archivo (.heic), se usará su carpeta contenedora.
        Valor por defecto:
        'D:\datos_palmeri\2025-06-20_Poveda-Palmeri\5_FIELD-Photos\HEIC'

    -OutputFolder, -OutputPath, -Destination, -o <String>
        Ruta del directorio de destino donde se escribirán los JPG resultantes.
        Si no se especifica, se utiliza la carpeta 'JPG' hermana al directorio de entrada.

    -Quality, -q <Int32>
        Nivel de compresión de calidad JPEG (rango válido: 1 a 100).
        Valor por defecto: 95 (calidad óptima recomendada para fotogrametría/campo).

    -Overwrite
        [Switch] Fuerza la conversión y sobrescritura de los archivos JPG existentes.
        Por defecto: DESACTIVADO (omite ficheros ya existentes para agilizar ejecuciones).

    -Recursive
        [Switch] Escanea y procesa subdirectorios recursivamente manteniendo
        la estructura de carpetas en el destino.

    -Help, -h, --help, -?
        [Switch] Muestra este mensaje de ayuda detallado y termina la ejecución.

EJEMPLOS:
    1. Ejecutar con la configuración por defecto del proyecto:
       .\01_Convert-HeicToJpg.ps1

    2. Convertir un directorio personalizado a otra carpeta:
       .\01_Convert-HeicToJpg.ps1 -InputFolder "D:\fotos\HEIC" -OutputFolder "D:\fotos\JPG"

    3. Usar sintaxis posicional abreviada:
       .\01_Convert-HeicToJpg.ps1 "D:\fotos\HEIC" "D:\fotos\JPG"

    4. Forzar sobrescritura con calidad máxima (100%):
       .\01_Convert-HeicToJpg.ps1 -InputFolder "D:\fotos\HEIC" -Quality 100 -Overwrite

    5. Procesar directorios recursivamente:
       .\01_Convert-HeicToJpg.ps1 -InputFolder "D:\fotos" -OutputFolder "D:\fotos_jpg" -Recursive

================================================================================
"@ -ForegroundColor Cyan
    exit 0
}

if ($ShowHelp -or ($InputFolder -in @('-h', '--help', '-help', '/?', '-?', 'help', '--h'))) {
    Show-ScriptHelp
}

# -------------------------------------------------------------------------
# 1. Normalización y validación de rutas
# -------------------------------------------------------------------------
# Si el usuario pasó la ruta a un archivo (p. ej. IMG_4172.HEIC), extraer el directorio
if (Test-Path -LiteralPath $InputFolder -PathType Leaf) {
    Write-Host "[i] Se detectó la ruta de un archivo. Usando su directorio contenedor." -ForegroundColor DarkCyan
    $InputFolder = Split-Path -Parent (Resolve-Path -LiteralPath $InputFolder).Path
} elseif (Test-Path -LiteralPath $InputFolder -PathType Container) {
    $InputFolder = (Resolve-Path -LiteralPath $InputFolder).Path
} else {
    Write-Error "El directorio de entrada no existe: '$InputFolder'"
    exit 1
}

# Si no se especificó carpeta de salida, crear o usar 'JPG' a nivel hermano
if ([string]::IsNullOrWhiteSpace($OutputFolder)) {
    $parentDir = Split-Path -Parent $InputFolder
    $OutputFolder = Join-Path $parentDir "JPG"
}

# Crear la carpeta de salida si no existe
if (-not (Test-Path -LiteralPath $OutputFolder)) {
    try {
        New-Item -ItemType Directory -Path $OutputFolder -Force | Out-Null
        Write-Host "[+] Carpeta de salida creada: $OutputFolder" -ForegroundColor DarkCyan
    } catch {
        Write-Error "No se pudo crear la carpeta de salida '$OutputFolder': $_"
        exit 1
    }
} else {
    $OutputFolder = (Resolve-Path -LiteralPath $OutputFolder).Path
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "         CONVERTIDOR DE HEIC A JPG (Alta Calidad)         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Origen  : $InputFolder" -ForegroundColor Gray
Write-Host " Destino : $OutputFolder" -ForegroundColor Gray
Write-Host " Calidad : $Quality%" -ForegroundColor Gray
Write-Host " Sobrescribir: $(if ($Overwrite) { 'SÍ' } else { 'NO (omitir existentes)' })" -ForegroundColor Gray
Write-Host " Recursivo   : $(if ($Recursive) { 'SÍ' } else { 'NO' })" -ForegroundColor Gray
Write-Host "----------------------------------------------------------" -ForegroundColor Cyan

# -------------------------------------------------------------------------
# 2. Detección y verificación del entorno (Python + pillow-heif)
# -------------------------------------------------------------------------
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
}

if (-not $pythonCmd) {
    Write-Error "No se encontró Python instalado en el sistema. Instálalo desde https://www.python.org o mediante 'winget install Python.Python.3.12'."
    exit 1
}

# Comprobar si pillow y pillow-heif están instalados
& $pythonCmd -c "import PIL, pillow_heif" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Falta la librería 'pillow-heif' necesaria para decodificar HEIC." -ForegroundColor Yellow
    Write-Host "[*] Instalando 'pillow' y 'pillow-heif' automáticamente vía pip..." -ForegroundColor Yellow
    & $pythonCmd -m pip install --upgrade pillow pillow-heif
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Fallo al instalar 'pillow-heif'. Por favor ejecuta: pip install pillow-heif"
        exit 1
    }
}

# -------------------------------------------------------------------------
# 3. Código Python optimizado para conversión por lotes
# -------------------------------------------------------------------------
$pyWorker = @'
import os
import sys
import time
from PIL import Image
import pillow_heif

pillow_heif.register_heif_opener()

def main():
    if len(sys.argv) < 5:
        print("ERROR: Argumentos insuficientes", file=sys.stderr)
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    quality = int(sys.argv[3])
    overwrite = sys.argv[4].lower() == 'true'
    recursive = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else False

    heic_files = []
    if recursive:
        for root, _, files in os.walk(input_dir):
            for f in sorted(files):
                if f.startswith('.') or f.startswith('._'):
                    continue
                if f.lower().endswith(('.heic', '.heif')):
                    rel = os.path.relpath(root, input_dir)
                    heic_files.append((os.path.join(root, f), rel, f))
    else:
        for f in sorted(os.listdir(input_dir)):
            if f.startswith('.') or f.startswith('._'):
                continue
            if f.lower().endswith(('.heic', '.heif')):
                full_p = os.path.join(input_dir, f)
                if os.path.isfile(full_p):
                    heic_files.append((full_p, '', f))

    total = len(heic_files)
    print(f"COUNT:{total}", flush=True)
    if total == 0:
        return

    converted = 0
    skipped = 0
    errors = 0
    start_time = time.time()

    for idx, (src_path, rel_dir, filename) in enumerate(heic_files, 1):
        base_name = os.path.splitext(filename)[0]
        out_name = base_name + ".jpg"

        dest_dir = os.path.join(output_dir, rel_dir) if rel_dir and rel_dir != '.' else output_dir
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, out_name)

        if os.path.exists(dest_path) and not overwrite:
            skipped += 1
            print(f"ITEM:{idx}:{total}:SKIPPED:{filename}:{out_name}", flush=True)
            continue

        try:
            with Image.open(src_path) as img:
                save_kwargs = {'quality': quality}
                
                # Conservar metadatos EXIF (GPS, fecha, cámara)
                if 'exif' in img.info and img.info['exif']:
                    save_kwargs['exif'] = img.info['exif']
                
                # Conservar perfil de color ICC
                if 'icc_profile' in img.info and img.info['icc_profile']:
                    save_kwargs['icc_profile'] = img.info['icc_profile']

                # Asegurar modo compatible con JPEG (RGB / L)
                if img.mode not in ('RGB', 'L'):
                    rgb_img = img.convert('RGB')
                    rgb_img.save(dest_path, 'JPEG', **save_kwargs)
                else:
                    img.save(dest_path, 'JPEG', **save_kwargs)

            converted += 1
            print(f"ITEM:{idx}:{total}:OK:{filename}:{out_name}", flush=True)
        except Exception as err:
            errors += 1
            print(f"ITEM:{idx}:{total}:ERROR:{filename}:{err}", flush=True)

    elapsed = time.time() - start_time
    print(f"SUMMARY:{total}:{converted}:{skipped}:{errors}:{elapsed:.2f}", flush=True)

if __name__ == '__main__':
    main()
'@

# -------------------------------------------------------------------------
# 4. Ejecución del proceso y monitorización de progreso
# -------------------------------------------------------------------------
$ovwStr = if ($Overwrite) { "true" } else { "false" }
$recStr = if ($Recursive) { "true" } else { "false" }

Write-Host "Escaneando imágenes HEIC..." -ForegroundColor DarkGray

$totalFound = 0
$convertedCount = 0
$skippedCount = 0
$errorCount = 0
$elapsedTime = 0

$pyWorker | & $pythonCmd - "$InputFolder" "$OutputFolder" "$Quality" "$ovwStr" "$recStr" | ForEach-Object {
    $line = $_
    if ($line -match '^COUNT:(\d+)$') {
        $totalFound = [int]$Matches[1]
        if ($totalFound -eq 0) {
            Write-Host "[!] No se encontraron archivos .heic o .heif en la carpeta indicada." -ForegroundColor Yellow
        } else {
            Write-Host "Se encontraron $totalFound imagen(es) para procesar.`n" -ForegroundColor Green
        }
    }
    elseif ($line -match '^ITEM:(\d+):(\d+):(\w+):([^:]+):?(.*)$') {
        $idx   = [int]$Matches[1]
        $tot   = [int]$Matches[2]
        $stat  = $Matches[3]
        $src   = $Matches[4]
        $extra = $Matches[5]

        $percent = [math]::Round(($idx / $tot) * 100)
        Write-Progress -Activity "Convirtiendo HEIC a JPG" -Status "[$idx/$tot] $src" -PercentComplete $percent

        switch ($stat) {
            "OK" {
                Write-Host " [$idx/$tot] " -NoNewline -ForegroundColor DarkGray
                Write-Host "$src " -NoNewline -ForegroundColor White
                Write-Host "-> " -NoNewline -ForegroundColor DarkGray
                Write-Host "$extra " -NoNewline -ForegroundColor Gray
                Write-Host "[OK]" -ForegroundColor Green
            }
            "SKIPPED" {
                Write-Host " [$idx/$tot] " -NoNewline -ForegroundColor DarkGray
                Write-Host "$src " -NoNewline -ForegroundColor White
                Write-Host "[OMITIDO - Ya existe en destino]" -ForegroundColor Yellow
            }
            "ERROR" {
                Write-Host " [$idx/$tot] " -NoNewline -ForegroundColor DarkGray
                Write-Host "$src " -NoNewline -ForegroundColor Red
                Write-Host "[ERROR: $extra]" -ForegroundColor Red
            }
        }
    }
    elseif ($line -match '^SUMMARY:(\d+):(\d+):(\d+):(\d+):([\d\.]+)$') {
        $totalFound     = [int]$Matches[1]
        $convertedCount = [int]$Matches[2]
        $skippedCount   = [int]$Matches[3]
        $errorCount     = [int]$Matches[4]
        $elapsedTime    = [double]$Matches[5]
    }
    else {
        if (-not [string]::IsNullOrWhiteSpace($line)) {
            Write-Host $line
        }
    }
}

Write-Progress -Activity "Convirtiendo HEIC a JPG" -Completed

# -------------------------------------------------------------------------
# 5. Resumen final
# -------------------------------------------------------------------------
Write-Host "`n----------------------------------------------------------" -ForegroundColor Cyan
Write-Host "RESUMEN DE TRANSFORMACIÓN:" -ForegroundColor Cyan
Write-Host " - Total encontrados : $totalFound" -ForegroundColor White
Write-Host " - Convertidos       : $convertedCount" -ForegroundColor $(if ($convertedCount -gt 0) { "Green" } else { "Gray" })
Write-Host " - Omitidos          : $skippedCount" -ForegroundColor $(if ($skippedCount -gt 0) { "Yellow" } else { "Gray" })
Write-Host " - Errores           : $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { "Red" } else { "Gray" })
Write-Host " - Tiempo total      : $elapsedTime segundos" -ForegroundColor White
Write-Host " - Carpeta resultado : $OutputFolder" -ForegroundColor Cyan
Write-Host "----------------------------------------------------------`n" -ForegroundColor Cyan
