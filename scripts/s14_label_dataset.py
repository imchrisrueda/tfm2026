#!/usr/bin/env python3
"""
s14_label_dataset.py
================
Script de etiquetado, catalogación e inventario de imágenes para el TFM según:
- 03_PLANIFICACION_TFM.md (P0: Inventario, etiquetado y agrupación)
- 02_FLUJO_IMAGENES_TFM.md
- 04_PROTOCOLO_ESCALA_MACETAS.md (10 cm para 2025, 20 cm para 2026)

Diseño experimental:
-------------------
Año 2025 (exp_design/01_2025.csv):
  * Rejilla de 10 filas (F1 a F10) x 8 columnas (C1 a C8).
  * 70 macetas por sesión (20 Palmeri, 20 Hybridus, 20 Retroflexus, 10 Maíz).
  * Diámetro exterior de maceta: 10.0 cm.
  * Tarjetas de referencia amarilla: únicamente presentes en la sesión 2025-05-13.
  * Recorrido en serpentina:
      C1: F10 -> F1  (sube, 10 fotos)
      C2: F1  -> F10 (baja, 10 fotos)
      C3: F10 -> F1  (sube, 10 fotos)
      C4: F1  -> F10 (baja, 10 fotos)
      C5: F10 -> F1  (sube, 10 fotos)
      C6: F1  -> F10 (baja, 10 fotos)
      C7: F10 -> F6  (sube, 5 fotos maíz)
      C8: F6  -> F10 (baja, 5 fotos maíz)

Año 2026 (exp_design/03_2026.csv):
  * Rejilla de 26 filas (F1 a F26) x 5 columnas (C1 a C5).
  * 130 macetas por sesión (40 Palmeri, 40 Hybridus, 40 Retroflexus, 10 Maíz).
  * Diámetro exterior de maceta: 20.0 cm.
  * Tarjetas de referencia amarilla: ninguna (has_reference_card = False).
  * Recorrido en serpentina:
      C1: F26 -> F1  (sube, 26 fotos)
      C2: F1  -> F26 (baja, 26 fotos)
      C3: F26 -> F1  (sube, 26 fotos)
      C4: F1  -> F26 (baja, 26 fotos)
      C5: F26 -> F1  (sube, 26 fotos)

Convención de directorios:
-------------------------
{fecha}_{campana}_{repeticion} (ej. 2025-05-13_c1_r1, 2026-06-10_c2_r2).
"""

import os
import sys
import json
import hashlib
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
from PIL import Image, ExifTags
from tqdm import tqdm


# Mapeo de códigos de especie a nombres científicos y atributos taxonómicos
SPECIES_MAP: Dict[str, Dict[str, Any]] = {
    "P": {
        "species_scientific": "Amaranthus palmeri",
        "genus": "Amaranthus",
        "is_target_species": True,
        "is_auxiliary": False,
        "class_label": "palmeri",
    },
    "H": {
        "species_scientific": "Amaranthus hybridus",
        "genus": "Amaranthus",
        "is_target_species": False,
        "is_auxiliary": False,
        "class_label": "hybridus",
    },
    "R": {
        "species_scientific": "Amaranthus retroflexus",
        "genus": "Amaranthus",
        "is_target_species": False,
        "is_auxiliary": False,
        "class_label": "retroflexus",
    },
    "M": {
        "species_scientific": "Zea mays",
        "genus": "Zea",
        "is_target_species": False,
        "is_auxiliary": True,
        "class_label": "maize",
    },
}


def build_serpentine_sequence(design_csv_path: Path) -> List[Dict[str, Any]]:
    """
    Construye la lista ordenada de posiciones en serpentina a partir del archivo CSV del diseño experimental:
    Para cada columna (C1, C2, ...):
      - Si la columna es impar (C1, C3, C5, C7): se recorre de abajo a arriba (fila max a fila min, SUBE).
      - Si la columna es par (C2, C4, C6, C8): se recorre de arriba a abajo (fila min a fila max, BAJA).
    Celdas vacías (como filas 1-5 en C7 y C8 de 2025) se omiten automáticamente.
    """
    if not design_csv_path.exists():
        raise FileNotFoundError(f"No se encontró el diseño experimental en: {design_csv_path}")

    df_grid = pd.read_csv(design_csv_path, index_col="Fila")
    cols = [c for c in df_grid.columns if c.startswith("C")]
    sequence: List[Dict[str, Any]] = []

    for c_idx, col_name in enumerate(cols, start=1):
        # Obtener las filas válidas no vacías en esta columna
        valid_rows = [
            r for r in df_grid.index
            if pd.notna(df_grid.loc[r, col_name]) and str(df_grid.loc[r, col_name]).strip() != ""
        ]

        # Serpentina: impares suben (descendente), pares bajan (ascendente)
        is_odd = (c_idx % 2 == 1)
        ordered_rows = sorted(valid_rows, reverse=True) if is_odd else sorted(valid_rows, reverse=False)

        for r in ordered_rows:
            val = df_grid.loc[r, col_name]
            species_code = str(val).strip() if pd.notna(val) else "UNKNOWN"
            sequence.append({
                "columna": col_name,
                "col_index": c_idx,
                "fila": int(r),
                "posicion": f"F{r}{col_name}",
                "species_code": species_code,
            })

    return sequence


def calculate_sha256(file_path: Path, block_size: int = 65536) -> str:
    """Calcula el hash SHA-256 de un archivo de imagen original."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            sha256.update(block)
    return sha256.hexdigest()


def extract_exif(img: Image.Image) -> Dict[str, Any]:
    """Extrae metadatos relevantes de los tags EXIF."""
    info: Dict[str, Any] = {
        "camera_make": None,
        "camera_model": None,
        "datetime_original": None,
        "focal_length_mm": None,
        "orientation": 1,
    }
    raw_exif = img.getexif()
    if not raw_exif:
        return info

    for tag_id, value in raw_exif.items():
        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
        if tag_name == "Make":
            info["camera_make"] = str(value).strip()
        elif tag_name == "Model":
            info["camera_model"] = str(value).strip()
        elif tag_name in ("DateTimeOriginal", "DateTime"):
            if not info["datetime_original"]:
                info["datetime_original"] = str(value).strip()
        elif tag_name == "FocalLength":
            try:
                info["focal_length_mm"] = float(value)
            except Exception:
                info["focal_length_mm"] = str(value)
        elif tag_name == "Orientation":
            try:
                info["orientation"] = int(value)
            except Exception:
                info["orientation"] = 1

    return info


def parse_session_dirname(dir_name: str) -> Tuple[Optional[int], Optional[str], Optional[str], Optional[str]]:
    """
    Extrae año, fecha, campaña y repetición del nombre de la carpeta (ej. 2025-05-13_c1_r1, 2026-06-10_c2_r2).
    c1 = Campaña 1, c2 = Campaña 2
    r1 = Repetición 1, r2 = Repetición 2
    """
    parts = dir_name.split("_")
    if len(parts) >= 3:
        date_str = parts[0]
        campana = parts[1].lower()
        repeticion = parts[2].lower()
        try:
            year = int(date_str.split("-")[0])
        except Exception:
            year = None
        return year, date_str, campana, repeticion
    return None, None, None, None


def get_session_pot_mapping(session_name: str, image_files: List[Path], design_sequence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Determina la posición en el diseño experimental para cada foto de una sesión.
    Soporta casos de múltiples tomas por planta/maceta:
      - Sesiones 1-a-1 estándar: len(image_files) == len(design_sequence).
      - Sesión 2026-05-14_c2_r1 (153 imágenes en cuadrícula de 130 macetas):
          * C1 (26 fotos): DSC_0665 a DSC_0690 -> 26 macetas de C1 (F26C1 a F1C1)
          * C2 (26 fotos): DSC_0694 a DSC_0719 -> 26 macetas de C2 (F1C2 a F26C2)
          * C3 (26 fotos): DSC_0720 a DSC_0745 -> 26 macetas de C3 (F26C3 a F1C3)
          * C4 (26 fotos): DSC_0746 a DSC_0771 -> 26 macetas de C4 (F1C4 a F26C4)
          * C5 (49 fotos para 26 macetas):
              - Toma 1 macetas 1..23 (F26C5..F4C5): fotos 104 a 126 (DSC_0772 a DSC_0795)
              - Toma 2 macetas 1..23 (F26C5..F4C5): fotos 127 a 149 (DSC_0797 a DSC_0819)
              - Macetas 24..26 (F3C5..F1C5): fotos 150 a 152 (DSC_0820 a DSC_0822)
      - Sesión 2025-06-16_c1_r2 (120 imágenes, 60 plantas x 2 tomas/planta sin maíz).
      - Fallback con celdas EXTRA si el número excede la secuencia.
    """
    n_images = len(image_files)
    n_seq = len(design_sequence)

    # Caso específico: 2026-05-14_c2_r1 (153 imágenes)
    if ("2026-05-14_c2_r1" in session_name or "2026-05-14" in session_name) and n_images == 153:
        mapping = []
        # C1 (26 macetas: 0..25)
        for idx in range(26):
            mapping.append(design_sequence[idx])
        # C2 (26 macetas: 26..51)
        for idx in range(26, 52):
            mapping.append(design_sequence[idx])
        # C3 (26 macetas: 52..77)
        for idx in range(52, 78):
            mapping.append(design_sequence[idx])
        # C4 (26 macetas: 78..103)
        for idx in range(78, 104):
            mapping.append(design_sequence[idx])
        # C5: 26 macetas (F26C5..F1C5) = design_sequence[104..129]
        c5_seq = design_sequence[104:130]
        # Batch 1 de C5: fotos 104 a 126 -> macetas 0..22 (F26C5 a F4C5)
        for idx in range(104, 127):
            k = idx - 104
            mapping.append(c5_seq[k])
        # Batch 2 de C5: fotos 127 a 149 -> macetas 0..22 (F26C5 a F4C5)
        for idx in range(127, 150):
            k = idx - 127
            mapping.append(c5_seq[k])
        # Batch final de C5: fotos 150 a 152 -> macetas 23..25 (F3C5, F2C5, F1C5)
        for idx in range(150, 153):
            k = idx - 150
            mapping.append(c5_seq[23 + k])
        return mapping

    # Caso específico: 2025-06-16_c1_r2 (120 fotos = 60 macetas x 2 fotos/maceta sin maíz)
    if "2025-06-16_c1_r2" in session_name and n_images == 120:
        mapping = []
        weed_seq = design_sequence[:60]
        for idx in range(n_images):
            pot_idx = idx // 2
            if pot_idx < len(weed_seq):
                mapping.append(weed_seq[pot_idx])
            else:
                mapping.append({
                    "columna": "C_extra",
                    "col_index": 99,
                    "fila": idx + 1,
                    "posicion": f"EXTRA_{idx+1}",
                    "species_code": "UNKNOWN",
                })
        return mapping

    # Caso estándar 1 a 1 (o fallback si no hay caso especial)
    mapping = []
    for idx in range(n_images):
        if idx < n_seq:
            mapping.append(design_sequence[idx])
        else:
            mapping.append({
                "columna": "C_extra",
                "col_index": 99,
                "fila": idx + 1,
                "posicion": f"EXTRA_{idx+1}",
                "species_code": "UNKNOWN",
            })
    return mapping


def label_session(session_dir: Path, design_sequence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Etiqueta todas las imágenes de una sesión asignando las posiciones en serpentina continua,
    soportando correctamente sesiones con múltiples tomas por maceta.
    """
    session_name = session_dir.name
    year, date_str, campana, repeticion = parse_session_dirname(session_name)
    if year is None:
        raise ValueError(f"No se pudo determinar el año para la sesión: {session_name}")

    # Especificaciones según protocolo por año
    pot_diameter = 10.0 if year == 2025 else 20.0
    # Tarjeta amarilla: solo colocada en la primera fecha de 2025 (2025-05-13)
    has_card = (date_str == "2025-05-13")

    valid_extensions = (".jpg", ".jpeg", ".JPG", ".JPEG")
    image_files = sorted([f for f in session_dir.iterdir() if f.is_file() and f.suffix in valid_extensions])
    total_images = len(image_files)

    pot_mapping = get_session_pot_mapping(session_name, image_files, design_sequence)

    records: List[Dict[str, Any]] = []
    print(f"\nProcesando sesión: {session_name} ({total_images} imágenes, maceta nominal {pot_diameter} cm)...")

    for idx, img_path in enumerate(tqdm(image_files, desc=f"Etiquetando {session_name}")):
        pos_info = pot_mapping[idx]
        col_name = pos_info["columna"]
        col_idx = pos_info["col_index"]
        row_num = pos_info["fila"]
        pos_code = pos_info["posicion"]
        species_code = pos_info["species_code"]

        species_meta = SPECIES_MAP.get(species_code, {
            "species_scientific": "Unknown",
            "genus": "Unknown",
            "is_target_species": False,
            "is_auxiliary": False,
            "class_label": "unknown",
        })

        # Identificador unívoco y persistente de maceta para trazabilidad temporal entre fechas (P0 / P1)
        pot_id = f"POT_{year}_{repeticion}_{pos_code}"
        image_id = f"{session_name}_{img_path.stem}"

        # Hash SHA-256
        file_sha256 = calculate_sha256(img_path)

        # Leer metadatos y EXIF
        try:
            with Image.open(img_path) as im:
                width, height = im.size
                exif_info = extract_exif(im)
        except Exception as e:
            print(f"[ERROR] Error al leer imagen {img_path.name}: {e}")
            width, height = None, None
            exif_info = {
                "camera_make": None,
                "camera_model": None,
                "datetime_original": None,
                "focal_length_mm": None,
                "orientation": 1,
            }

        # Ruta relativa segura
        try:
            rel_path = str(img_path.relative_to(session_dir.parent.parent)).replace("\\", "/")
        except ValueError:
            try:
                rel_path = str(img_path.relative_to(session_dir.parent)).replace("\\", "/")
            except ValueError:
                rel_path = str(img_path).replace("\\", "/")

        record = {
            "image_id": image_id,
            "filename": img_path.name,
            "relative_path": rel_path,
            "session_id": session_name,
            "year": year,
            "date_session": date_str,
            "campana": campana,
            "repeticion": repeticion,
            "capture_order": idx + 1,
            "columna": col_name,
            "col_index": col_idx,
            "fila": row_num,
            "posicion": pos_code,
            "pot_id": pot_id,
            "species_code": species_code,
            "species_scientific": species_meta["species_scientific"],
            "genus": species_meta["genus"],
            "class_label": species_meta["class_label"],
            "is_target_species": species_meta["is_target_species"],
            "is_auxiliary": species_meta["is_auxiliary"],
            "pot_diameter_exterior_cm": pot_diameter,
            "has_reference_card": has_card,
            "sha256": file_sha256,
            "width": width,
            "height": height,
            "exif_orientation": exif_info["orientation"],
            "exif_camera_make": exif_info["camera_make"],
            "exif_camera_model": exif_info["camera_model"],
            "exif_datetime_original": exif_info["datetime_original"],
            "exif_focal_length_mm": exif_info["focal_length_mm"],
            "pipeline_status": "raw_inventory_ok",
        }
        records.append(record)

    return records


def print_column_milestones(session_df: pd.DataFrame):
    """Muestra el inicio y fin de cada columna para verificar la serpentina."""
    col_milestones = []
    current_col = None
    col_start_idx = 0
    records = session_df.to_dict("records")
    for idx, item in enumerate(records):
        if item["columna"] != current_col:
            if current_col is not None:
                col_milestones.append((col_start_idx + 1, idx, current_col))
            current_col = item["columna"]
            col_start_idx = idx
    if current_col is not None:
        col_milestones.append((col_start_idx + 1, len(session_df), current_col))

    print("\n  Desglose de recorrido en serpentina por columna:")
    for start_p, end_p, col_name in col_milestones:
        start_row = session_df.iloc[start_p - 1]
        end_row = session_df.iloc[end_p - 1]
        direction = "sube" if start_row["fila"] > end_row["fila"] else "baja"
        count = end_p - start_p + 1
        print(f"    - {col_name} ({direction:4s}, {count:2d} fotos): Foto {start_p:03d} [{start_row['posicion']}: {start_row['species_code']}] -> Foto {end_p:03d} [{end_row['posicion']}: {end_row['species_code']}]")


def main():
    description_text = """
s14_label_dataset.py
================
Etiquetado, catalogación e inventario de imágenes de Amaranthus palmeri y auxiliares
para el Trabajo de Fin de Máster (TFM 2025/2026).

Capacidades principales:
  1. Asignación botánica en serpentina: Cruza cada captura fotográfica ordenada cronológicamente
     con la posición del diseño experimental (01_2025.csv o 03_2026.csv).
  2. Soporte nativo de sesiones con fotos múltiples por maceta (ej. 2026-05-14_c2_r1 con 153 fotos),
     vinculando tomas repetidas a la misma maceta física (posicion y pot_id) sin descartar datos.
  3. Normalización física: Asigna diámetro exterior nominal (10.0 cm en 2025; 20.0 cm en 2026).
  4. Extracción de metadatos EXIF: Cámara, fecha/hora original, orientación y distancia focal.
  5. Integridad SHA-256: Hash criptográfico por imagen para garantizar trazabilidad estricta.
  6. Generación de manifiestos: Archivos CSV y JSON por sesión y consolidados (anuales y global).
"""

    epilog_text = """
Ejemplos de uso:
----------------
  1. Procesar todas las sesiones disponibles en data/raw (2025 y 2026):
     python scripts/s14_label_dataset.py

  2. Procesar una sesión específica dentro de data/raw:
     python scripts/s14_label_dataset.py --session 2026-06-10_c2_r2

  3. Procesar una sesión con fotos múltiples por maceta (153 fotos, 130 macetas):
     python scripts/s14_label_dataset.py --session 2026-05-14_c2_r1

  4. Procesar una carpeta de sesión situada en una ruta externa:
     python scripts/s14_label_dataset.py --session "D:\\TFM_FOTOS\\2026-06-17_c2_r2"

  5. Leer desde un directorio raíz externo con múltiples sesiones:
     python scripts/s14_label_dataset.py --raw_dir "D:\\TFM_DATASET\\raw"

  6. Filtrar y procesar únicamente sesiones de un año específico:
     python scripts/s14_label_dataset.py --year 2025
     python scripts/s14_label_dataset.py --year 2026

  7. Cambiar la carpeta de salida de los manifiestos consolidados:
     python scripts/s14_label_dataset.py --output_dir "D:\\mis_manifiestos"

Convención de nombres de carpetas de sesión:
-------------------------------------------
  {YYYY-MM-DD}_{campana}_{repeticion}
  Ejemplos: 
    * 2025-05-13_c1_r1 -> Año 2025, Campaña 1, Repetición 1 (70 fotos, maceta 10 cm)
    * 2026-06-10_c2_r2 -> Año 2026, Campaña 2, Repetición 2 (130 fotos, maceta 20 cm)
    * 2026-05-14_c2_r1 -> Año 2026, Campaña 2, Repetición 1 (153 fotos, maceta 20 cm, 23 macetas con doble toma)

Archivos de salida generados:
----------------------------
  - manifest.csv y manifest.json dentro de cada carpeta de sesión procesada.
  - manifest_2025.csv / .json y manifest_2026.csv / .json (consolidados anuales en data/processed).
  - manifest_all.csv / .json (consolidado global de todo el proyecto en data/processed).
"""
    parser = argparse.ArgumentParser(
        description=description_text,
        epilog=epilog_text,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--raw_dir",
        type=str,
        default=r"data\raw",
        help="Directorio raíz que contiene las carpetas de sesiones crudas (por defecto: data/raw).",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=r"data\processed",
        help="Directorio donde se guardarán los manifiestos consolidados (por defecto: data/processed).",
    )
    parser.add_argument(
        "--design_dir",
        type=str,
        default=r"exp_design",
        help="Directorio con los archivos de diseño experimental {year}.csv (por defecto: exp_design).",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Filtrar sesiones por año específico (ej. 2025 o 2026). Si no se indica, procesa todos los años.",
    )
    parser.add_argument(
        "--session",
        type=str,
        default=None,
        help="Nombre o ruta completa de una sesión específica para procesar (ej. 2026-06-10_c2_r2 o 'D:\\fotos\\2026-06-10_c2_r2').",
    )
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    output_dir = Path(args.output_dir)
    design_dir = Path(args.design_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not raw_dir.exists():
        print(f"[ERROR] El directorio {raw_dir} no existe.")
        sys.exit(1)

    # Identificar carpetas de sesión (admite nombre relativo en raw_dir o ruta completa externa)
    if args.session:
        session_candidate = Path(args.session)
        if session_candidate.exists() and session_candidate.is_dir():
            session_dirs = [session_candidate]
        elif (raw_dir / args.session).exists() and (raw_dir / args.session).is_dir():
            session_dirs = [raw_dir / args.session]
        else:
            print(f"[ERROR] No se encontró el directorio de sesión: {args.session}")
            sys.exit(1)
    else:
        all_dirs = sorted([d for d in raw_dir.iterdir() if d.is_dir()])
        if args.year:
            session_dirs = [d for d in all_dirs if d.name.startswith(str(args.year))]
        else:
            session_dirs = [d for d in all_dirs if d.name.startswith(("2025", "2026"))]

    if not session_dirs:
        print(f"[AVISO] No se encontraron directorios de sesión válidos en {raw_dir}.")
        sys.exit(0)

    # Cache de secuencias de diseño por año
    design_sequences: Dict[int, List[Dict[str, Any]]] = {}
    all_records: List[Dict[str, Any]] = []

    for s_dir in session_dirs:
        if not s_dir.exists():
            print(f"[ERROR] Directorio no encontrado: {s_dir}")
            continue

        year, date_str, campana, repeticion = parse_session_dirname(s_dir.name)
        if year not in design_sequences:
            design_csv = design_dir / {2025: "01_2025.csv", 2026: "03_2026.csv"}[year]
            if not design_csv.exists():
                print(f"[ERROR] No se encontró el diseño experimental {design_csv} para el año {year}.")
                continue
            design_sequences[year] = build_serpentine_sequence(design_csv)

        seq = design_sequences[year]
        session_records = label_session(s_dir, seq)
        all_records.extend(session_records)

        # Guardar manifiesto individual por sesión dentro de la propia carpeta
        session_df = pd.DataFrame(session_records)
        session_csv = s_dir / "manifest.csv"
        session_json = s_dir / "manifest.json"
        session_df.to_csv(session_csv, index=False, encoding="utf-8")
        with open(session_json, "w", encoding="utf-8") as f:
            json.dump(session_records, f, indent=2, ensure_ascii=False)
        print(f" -> Guardado manifiesto de sesión en: {session_csv.name}")
        print_column_milestones(session_df)

    if all_records:
        df_all = pd.DataFrame(all_records)

        # Guardar manifiestos por año y consolidado general
        for y in df_all["year"].unique():
            df_year = df_all[df_all["year"] == y]
            year_csv = output_dir / f"manifest_{y}.csv"
            year_json = output_dir / f"manifest_{y}.json"
            df_year.to_csv(year_csv, index=False, encoding="utf-8")
            with open(year_json, "w", encoding="utf-8") as f:
                json.dump(df_year.to_dict("records"), f, indent=2, ensure_ascii=False)
            print(f" -> Guardado manifiesto anual {y}: {year_csv.name}")

        consolidated_csv = output_dir / "manifest_all.csv"
        consolidated_json = output_dir / "manifest_all.json"
        df_all.to_csv(consolidated_csv, index=False, encoding="utf-8")
        with open(consolidated_json, "w", encoding="utf-8") as f:
            json.dump(all_records, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 75)
        print("RESUMEN DE ETIQUETADO Y CATALOGACIÓN CONSOLIDADA (TFM)")
        print("=" * 75)
        print(f"Total global de imágenes procesadas: {len(df_all)}")
        print(f"Sesiones procesadas ({df_all['session_id'].nunique()}): {list(df_all['session_id'].unique())}")
        print("\nDistribución global por especie:")
        print(df_all["species_scientific"].value_counts().to_string())
        print("\nDistribución por sesión y especie:")
        print(pd.crosstab(df_all["session_id"], df_all["species_scientific"], margins=True))
        print("=" * 75)
        print(f"Manifiesto consolidado CSV : {consolidated_csv}")
        print(f"Manifiesto consolidado JSON: {consolidated_json}")
        print("=" * 75)


if __name__ == "__main__":
    main()
