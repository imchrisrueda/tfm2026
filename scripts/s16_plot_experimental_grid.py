#!/usr/bin/env python3
"""
s16_plot_experimental_grid.py
=========================
Genera un esquema gráfico de la matriz del diseño experimental (2025 o 2026),
mostrando la posición de cada planta en la cuadrícula y superponiendo, a modo
de puntos con información EXIF y número de captura, las imágenes existentes
en una sesión dada. Soporta múltiples fotos por planta/maceta.

Uso:
----
  python scripts/s16_plot_experimental_grid.py --session_dir "data/raw/2025-05-13_c1_r1"
  python scripts/s16_plot_experimental_grid.py --session_dir "data/raw/2026-06-10_c2_r2"
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Backend no interactivo
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D
from PIL import Image, ExifTags

# Paleta de colores consistente con el TFM
SPECIES_COLORS = {
    "P": {
        "name": r"$\it{Amaranthus\ palmeri}$",
        "bg": "#ffebee",       # Rojo coral suave para celda
        "border": "#e57373",   # Borde de celda
        "point": "#c62828",    # Punto sólido rojo intenso
        "text": "#b71c1c"
    },
    "H": {
        "name": r"$\it{Amaranthus\ hybridus}$",
        "bg": "#e3f2fd",       # Azul suave para celda
        "border": "#64b5f6",   # Borde de celda
        "point": "#1565c0",    # Punto sólido azul intenso
        "text": "#0d47a1"
    },
    "R": {
        "name": r"$\it{Amaranthus\ retroflexus}$",
        "bg": "#fff3e0",       # Ámbar suave para celda
        "border": "#ffb74d",   # Borde de celda
        "point": "#ef6c00",    # Punto sólido naranja intenso
        "text": "#e65100"
    },
    "M": {
        "name": r"$\it{Zea\ mays}$ (Maíz)",
        "bg": "#e8f5e9",       # Verde suave para celda
        "border": "#81c784",   # Borde de celda
        "point": "#2e7d32",    # Punto sólido verde intenso
        "text": "#1b5e20"
    },
    "EMPTY": {
        "name": "Sin planta (Vacío)",
        "bg": "#f5f5f5",
        "border": "#e0e0e0",
        "point": "#9e9e9e",
        "text": "#9e9e9e"
    }
}


def parse_session_dirname(dir_name: str) -> Tuple[Optional[int], Optional[str], Optional[str], Optional[str]]:
    """Extrae año, fecha, campaña y repetición del nombre de la carpeta."""
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


def extract_exif(img_path: Path) -> Dict[str, Any]:
    """Extrae metadatos EXIF esenciales."""
    info = {
        "datetime_original": None,
        "time_str": "",
        "orientation": 1,
        "camera": "Unknown"
    }
    try:
        with Image.open(img_path) as im:
            raw_exif = im.getexif()
            if raw_exif:
                for tag_id, value in raw_exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    if tag_name == "Model":
                        info["camera"] = str(value).strip()
                    elif tag_name in ("DateTimeOriginal", "DateTime"):
                        if not info["datetime_original"]:
                            info["datetime_original"] = str(value).strip()
                    elif tag_name == "Orientation":
                        try:
                            info["orientation"] = int(value)
                        except Exception:
                            info["orientation"] = 1
                if not info["datetime_original"]:
                    try:
                        exif_ifd = raw_exif.get_ifd(0x8769)
                        for tag_id, value in exif_ifd.items():
                            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                            if tag_name in ("DateTimeOriginal", "DateTime"):
                                info["datetime_original"] = str(value).strip()
                                break
                    except Exception:
                        pass
    except Exception:
        pass

    if info["datetime_original"] and " " in info["datetime_original"]:
        info["time_str"] = info["datetime_original"].split(" ")[1]
    return info


def build_serpentine_sequence(design_csv_path: Path) -> List[Dict[str, Any]]:
    """Construye la lista ordenada de posiciones en serpentina."""
    df_grid = pd.read_csv(design_csv_path, index_col="Fila")
    cols = [c for c in df_grid.columns if c.startswith("C")]
    sequence: List[Dict[str, Any]] = []

    for c_idx, col_name in enumerate(cols, start=1):
        valid_rows = [
            r for r in df_grid.index
            if pd.notna(df_grid.loc[r, col_name]) and str(df_grid.loc[r, col_name]).strip() != ""
        ]
        is_odd = (c_idx % 2 == 1)
        ordered_rows = sorted(valid_rows, reverse=True) if is_odd else sorted(valid_rows, reverse=False)

        for r in ordered_rows:
            val = df_grid.loc[r, col_name]
            sequence.append({
                "columna": col_name,
                "col_index": c_idx,
                "fila": int(r),
                "posicion": f"F{r}{col_name}",
                "species_code": str(val).strip(),
            })
    return sequence


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
        for idx in range(26):
            mapping.append(design_sequence[idx])
        for idx in range(26, 52):
            mapping.append(design_sequence[idx])
        for idx in range(52, 78):
            mapping.append(design_sequence[idx])
        for idx in range(78, 104):
            mapping.append(design_sequence[idx])
        c5_seq = design_sequence[104:130]
        for idx in range(104, 127):
            k = idx - 104
            mapping.append(c5_seq[k])
        for idx in range(127, 150):
            k = idx - 127
            mapping.append(c5_seq[k])
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


def load_session_data(session_dir: Path, design_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame, int, Dict[str, Any]]:
    """
    Carga el diseño experimental del año correspondiente y los datos de las imágenes
    (desde manifest.csv si existe, o extrayendo EXIF directamente de los archivos).
    """
    session_name = session_dir.name
    year, date_str, campana, repeticion = parse_session_dirname(session_name)
    if year is None:
        raise ValueError(f"No se pudo inferir el año del nombre de la carpeta: {session_name}")

    design_csv = design_dir / {2025: "01_2025.csv", 2026: "03_2026.csv"}[year]
    if not design_csv.exists():
        raise FileNotFoundError(f"No se encontró el archivo de diseño: {design_csv}")

    df_grid = pd.read_csv(design_csv, index_col="Fila")

    manifest_csv = session_dir / "manifest.csv"
    if manifest_csv.exists():
        print(f"Cargando metadatos desde manifest.csv en {session_dir.name}...")
        df_images = pd.read_csv(manifest_csv)
    else:
        print(f"Analizando imágenes y EXIF directamente en {session_dir.name}...")
        valid_exts = (".jpg", ".jpeg", ".JPG", ".JPEG")
        image_files = sorted([f for f in session_dir.iterdir() if f.is_file() and f.suffix in valid_exts])
        sequence = build_serpentine_sequence(design_csv)
        pot_mapping = get_session_pot_mapping(session_name, image_files, sequence)

        records = []
        for idx, img_path in enumerate(image_files):
            exif_info = extract_exif(img_path)
            pos_info = pot_mapping[idx]
            col_name = pos_info["columna"]
            col_idx = pos_info["col_index"]
            row_num = pos_info["fila"]
            pos_code = pos_info["posicion"]
            sp_code = pos_info["species_code"]

            records.append({
                "image_id": f"{session_name}_{img_path.stem}",
                "filename": img_path.name,
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
                "species_code": sp_code,
                "exif_orientation": exif_info["orientation"],
                "exif_datetime_original": exif_info["datetime_original"],
                "exif_camera_model": exif_info["camera"],
                "has_reference_card": (date_str == "2025-05-13"),
                "pot_diameter_exterior_cm": 10.0 if year == 2025 else 20.0
            })
        df_images = pd.DataFrame(records)

    meta = {
        "session_name": session_name,
        "year": year,
        "date_str": date_str,
        "campana": campana,
        "repeticion": repeticion,
        "total_images": len(df_images),
        "camera": df_images["exif_camera_model"].dropna().iloc[0] if "exif_camera_model" in df_images.columns and len(df_images) > 0 else "Nikon",
        "has_card": df_images["has_reference_card"].any() if "has_reference_card" in df_images.columns else False,
        "pot_diameter": df_images["pot_diameter_exterior_cm"].iloc[0] if "pot_diameter_exterior_cm" in df_images.columns else (10.0 if year == 2025 else 20.0)
    }

    return df_grid, df_images, year, meta


def draw_orientation_arrow(ax, cx: float, cy: float, orientation: int = 1, length: float = 0.16, color: str = "#0277bd", zorder: int = 6):
    """
    Dibuja una flecha indicadora de la dirección de la cámara según la orientación EXIF:
    - Orientación 1: Arriba (apaisado normal)
    - Orientación 6: Derecha (rotada 90° horario / vertical)
    - Orientación 8: Izquierda (rotada 90° antihorario / vertical)
    - Orientación 3: Abajo (180° invertido)
    """
    if orientation == 1:
        dx, dy = 0, -length
    elif orientation == 6:
        dx, dy = length, 0
    elif orientation == 8:
        dx, dy = -length, 0
    elif orientation == 3:
        dx, dy = 0, length
    else:
        dx, dy = 0, -length

    ax.annotate(
        "",
        xy=(cx + dx / 2, cy + dy / 2),
        xytext=(cx - dx / 2, cy - dy / 2),
        arrowprops=dict(
            facecolor=color,
            edgecolor="#01579b",
            width=2.4,
            headwidth=6.5,
            headlength=6.0,
            shrink=0
        ),
        zorder=zorder
    )


def plot_grid(df_grid: pd.DataFrame, df_images: pd.DataFrame, year: int, meta: Dict[str, Any], output_path: Path):
    """
    Dibuja la matriz del diseño experimental con celdas por especie y superpone las imágenes como puntos,
    manejando correctamente plantas con 1 o más imágenes.
    """
    cols = [c for c in df_grid.columns if c.startswith("C")]
    rows = list(df_grid.index)
    n_cols = len(cols)
    n_rows = len(rows)

    # Configuración de dimensiones según año
    if year == 2025:
        fig_w, fig_h = 16, 12
        cell_w, cell_h = 0.88, 0.85
        base_point_size = 380
        font_num = 9
        font_sub = 6.5
        cam_scale = 0.08
    else:  # 2026 (26 filas)
        fig_w, fig_h = 15, 25
        cell_w, cell_h = 0.88, 0.88
        base_point_size = 280
        font_num = 7.5
        font_sub = 5.2
        cam_scale = 0.065

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=180)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#fafafa")

    col_to_x = {col: i + 1 for i, col in enumerate(cols)}

    # Agrupar imágenes por posición para soportar múltiples fotos por planta
    img_by_pos = defaultdict(list)
    if not df_images.empty and "posicion" in df_images.columns:
        for _, row in df_images.iterrows():
            img_by_pos[str(row["posicion"])].append(row)

    # 1. Dibujar celdas de la cuadrícula del diseño experimental
    total_planned_pots = 0
    for r in rows:
        for c in cols:
            val = df_grid.loc[r, c]
            x_center = col_to_x[c]
            y_center = r

            is_valid = pd.notna(val) and str(val).strip() != ""
            sp_code = str(val).strip() if is_valid else "EMPTY"
            color_info = SPECIES_COLORS.get(sp_code, SPECIES_COLORS["EMPTY"])

            if is_valid:
                total_planned_pots += 1

            # Rectángulo de fondo de la celda
            rect = patches.FancyBboxPatch(
                (x_center - cell_w / 2, y_center - cell_h / 2),
                cell_w, cell_h,
                boxstyle="round,pad=0.02,rounding_size=0.08",
                facecolor=color_info["bg"],
                edgecolor=color_info["border"],
                linewidth=1.2,
                linestyle="--" if not is_valid else "-",
                hatch="///" if not is_valid else None,
                alpha=0.9,
                zorder=1
            )
            ax.add_patch(rect)

            # Rótulo de la posición en la esquina superior izquierda
            pos_label = f"F{r}{c}"
            if is_valid:
                ax.text(
                    x_center - cell_w / 2 + 0.05,
                    y_center - cell_h / 2 + 0.14,
                    f"{pos_label} [{sp_code}]",
                    fontsize=font_sub + 1.2,
                    fontweight="bold",
                    color=color_info["text"],
                    ha="left",
                    va="top",
                    zorder=2
                )
            else:
                ax.text(
                    x_center, y_center,
                    f"{pos_label}\n(vacío)",
                    fontsize=font_sub,
                    color="#bdbdbd",
                    ha="center",
                    va="center",
                    style="italic",
                    zorder=2
                )

    # 2. Dibujar trayectoria en serpentina (ordenada cronológicamente por capture_order)
    if not df_images.empty and "capture_order" in df_images.columns:
        df_sorted = df_images.sort_values("capture_order")
        traj_x = []
        traj_y = []

        # Para posicionar la línea exactamente sobre cada foto (incluso múltiples fotos en una misma celda)
        for _, row in df_sorted.iterrows():
            pos = str(row["posicion"])
            col_name = str(row.get("columna", ""))
            row_num = row.get("fila")
            if col_name in col_to_x and pd.notna(row_num):
                x_base = col_to_x[col_name]
                y_base = float(row_num)

                # Calcular offset si hay múltiples fotos en esta posición
                photos_at_pos = img_by_pos.get(pos, [])
                k = len(photos_at_pos)
                if k > 1:
                    photo_idx = next((i for i, p in enumerate(photos_at_pos) if int(p["capture_order"]) == int(row["capture_order"])), 0)
                    offsets = np.linspace(-0.20, 0.20, k)
                    x_pt = x_base + offsets[photo_idx]
                else:
                    x_pt = x_base

                traj_x.append(x_pt)
                traj_y.append(y_base)

        if len(traj_x) > 1:
            ax.plot(
                traj_x, traj_y,
                color="#78909c",
                linestyle=":",
                linewidth=1.8,
                alpha=0.7,
                zorder=3
            )

    # 3. Superponer las imágenes existentes a manera de puntos con datos EXIF
    images_plotted_count = 0
    multi_photo_pots_count = 0

    for r in rows:
        for c in cols:
            val = df_grid.loc[r, c]
            is_valid = pd.notna(val) and str(val).strip() != ""
            pos_code = f"F{r}{c}"
            x_center = col_to_x[c]
            y_center = r

            photos = img_by_pos.get(pos_code, [])
            k = len(photos)

            if k > 0:
                images_plotted_count += k
                if k > 1:
                    multi_photo_pots_count += 1
                    # Insignia de múltiples fotos en la esquina superior derecha de la celda
                    ax.text(
                        x_center + cell_w / 2 - 0.04,
                        y_center - cell_h / 2 + 0.14,
                        f"{k} fotos",
                        fontsize=font_sub + 0.5,
                        fontweight="bold",
                        color="#ffffff",
                        ha="right",
                        va="top",
                        bbox=dict(boxstyle="round,pad=0.18", fc="#6a1b9a", ec="none"),
                        zorder=3
                    )

                # Calcular separación horizontal si hay 1 o más fotos
                if k == 1:
                    offsets = [0.0]
                    p_size = base_point_size
                    f_num = font_num
                    c_scale = cam_scale
                elif k == 2:
                    offsets = [-0.19, 0.19]
                    p_size = base_point_size * 0.75
                    f_num = font_num - 1.5
                    c_scale = cam_scale * 0.85
                else:
                    offsets = np.linspace(-0.25, 0.25, k).tolist()
                    p_size = base_point_size * 0.58
                    f_num = font_num - 2.5
                    c_scale = cam_scale * 0.72

                for i, img_row in enumerate(photos):
                    x_pt = x_center + offsets[i]
                    sp_code = str(img_row.get("species_code", val if is_valid else "UNKNOWN"))
                    color_info = SPECIES_COLORS.get(sp_code, SPECIES_COLORS["EMPTY"])

                    order_num = int(img_row["capture_order"])
                    filename = str(img_row.get("filename", ""))
                    exif_time = ""
                    raw_time = str(img_row.get("exif_datetime_original", ""))
                    if " " in raw_time:
                        exif_time = raw_time.split(" ")[1]
                    exif_orient = int(img_row.get("exif_orientation", 1))

                    # Punto marcador principal
                    ax.scatter(
                        x_pt, y_center,
                        s=p_size,
                        color=color_info["point"],
                        edgecolors="#ffffff",
                        linewidths=1.8,
                        zorder=4
                    )

                    # Número de orden de captura dentro del punto
                    ax.text(
                        x_pt, y_center,
                        f"{order_num}",
                        fontsize=f_num,
                        fontweight="heavy",
                        color="#ffffff",
                        ha="center",
                        va="center",
                        zorder=5
                    )

                    # Flecha direccional de orientación EXIF de la cámara
                    arrow_len = 0.16 if k == 1 else 0.13
                    draw_orientation_arrow(ax, x_pt, y_center + 0.20, orientation=exif_orient, length=arrow_len, zorder=6)

                    # Texto descriptivo (nombre y hora) debajo de la flecha
                    time_label = f"\n{exif_time}" if exif_time else ""
                    orient_name = f"O:{exif_orient}"
                    info_text = f"{filename}{time_label} ({orient_name})"
                    ax.text(
                        x_pt, y_center + 0.32,
                        info_text,
                        fontsize=font_sub if k == 1 else font_sub - 0.8,
                        fontweight="medium",
                        color="#263238",
                        ha="center",
                        va="top",
                        bbox=dict(boxstyle="square,pad=0.1", fc="#ffffff", ec="#cfd8dc", lw=0.5, alpha=0.88),
                        zorder=5
                    )

            elif is_valid:
                # Posición planificada pero ausente
                ax.scatter(
                    x_center, y_center,
                    s=base_point_size * 0.7,
                    facecolors="none",
                    edgecolors="#d32f2f",
                    linewidths=2.0,
                    linestyle="--",
                    zorder=4
                )
                ax.text(
                    x_center, y_center,
                    "X",
                    fontsize=font_num + 2,
                    fontweight="bold",
                    color="#d32f2f",
                    ha="center",
                    va="center",
                    zorder=5
                )
                ax.text(
                    x_center, y_center + 0.26,
                    "FALTANTE",
                    fontsize=font_sub,
                    fontweight="bold",
                    color="#d32f2f",
                    ha="center",
                    va="top",
                    zorder=5
                )

    # Invertir eje Y para que Fila 1 aparezca arriba
    ax.set_ylim(n_rows + 0.6, 0.4)
    ax.set_xlim(0.4, n_cols + 0.6)

    # Configuración de ejes (sin etiquetas de texto en los ejes X e Y según solicitud del usuario)
    ax.set_xticks([col_to_x[c] for c in cols])
    ax.set_xticklabels(cols, fontsize=12, fontweight="bold", color="#1a237e")
    ax.set_yticks(rows)
    ax.set_yticklabels([f"F{r}" for r in rows], fontsize=11 if year == 2025 else 8.5, fontweight="bold", color="#37474f")

    ax.set_xlabel("")
    ax.set_ylabel("")

    # Título principal y subtítulo
    unique_covered_pots = len([p for p in img_by_pos.keys() if p in [f"F{r}{c}" for r in rows for c in cols if pd.notna(df_grid.loc[r, c])]])
    pct = (unique_covered_pots / total_planned_pots * 100) if total_planned_pots > 0 else 0

    title_main = f"Esquema de Imágenes y Matriz Experimental: {meta['session_name']}"
    sub_title = (
        f"Año: {year} | Campaña: {meta['campana'].upper()} | Repetición: {meta['repeticion'].upper()} | "
        f"Maceta: {meta['pot_diameter']} cm | Tarjeta: {'Sí' if meta['has_card'] else 'No'} | "
        f"Macetas cubiertas: {unique_covered_pots}/{total_planned_pots} ({pct:.1f}%) | "
        f"Total fotos: {images_plotted_count}" + (f" ({multi_photo_pots_count} macetas con >1 foto)" if multi_photo_pots_count > 0 else "")
    )
    plt.suptitle(title_main, fontsize=15, fontweight="heavy", y=0.98 if year == 2025 else 0.99, color="#0d47a1")
    ax.set_title(sub_title, fontsize=10, pad=12, color="#455a64")

    # Leyenda con nombres científicos en cursiva mediante mathtext
    legend_elements = [
        patches.Patch(facecolor=SPECIES_COLORS["P"]["bg"], edgecolor=SPECIES_COLORS["P"]["point"], label=r"$\it{Amaranthus\ palmeri}$ (P)"),
        patches.Patch(facecolor=SPECIES_COLORS["H"]["bg"], edgecolor=SPECIES_COLORS["H"]["point"], label=r"$\it{Amaranthus\ hybridus}$ (H)"),
        patches.Patch(facecolor=SPECIES_COLORS["R"]["bg"], edgecolor=SPECIES_COLORS["R"]["point"], label=r"$\it{Amaranthus\ retroflexus}$ (R)"),
        patches.Patch(facecolor=SPECIES_COLORS["M"]["bg"], edgecolor=SPECIES_COLORS["M"]["point"], label=r"$\it{Zea\ mays}$ / Maíz (M)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#263238", markersize=9, label="Imagen (# Orden)"),
        Line2D([0], [0], color="#78909c", linestyle=":", linewidth=2, label="Trayectoria serpentina"),
        patches.Patch(facecolor="#6a1b9a", edgecolor="none", label="Múltiples fotos/planta"),
        Line2D([0], [0], marker=r"$\uparrow$", color="#0277bd", markersize=11, linestyle="none", label="Dirección cámara EXIF"),
    ]

    leg = ax.legend(
        handles=legend_elements,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.045 if year == 2025 else -0.025),
        ncol=4,
        fontsize=9.5,
        frameon=True,
        facecolor="#ffffff",
        edgecolor="#b0bec5"
    )

    # Mini-guía de flechas de orientación EXIF en el pie de figura
    fig.text(
        0.05, 0.015,
        "Dirección cámara (flecha EXIF):   [ ↑ ] O:1 Normal (apaisado)   |   [ → ] O:6 Vertical 90° horario (CW)   |   [ ← ] O:8 Vertical 90° antihorario (CCW)   |   [ ↓ ] O:3 Invertido 180°",
        fontsize=8.5,
        color="#37474f",
        fontweight="medium"
    )

    plt.tight_layout(rect=[0, 0.035, 1, 0.96])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close()
    print(f" -> Gráfico guardado exitosamente en: {output_path}")


def main():
    description_text = """
s16_plot_experimental_grid.py
=========================
Genera un esquema visual en alta resolución de la matriz del diseño experimental (2025 o 2026),
superponiendo cada imagen capturada como un punto en su celda correspondiente y trazando el
recorrido secuencial en serpentina.

Capacidades y características principales:
  1. Matriz experimental:
     - Dibuja la cuadrícula completa según el diseño oficial (2025: 10 filas x 8 cols; 2026: 26 filas x 5 cols).
     - Colorea cada celda según la especie planificada:
         * Amaranthus palmeri (P): Coral suave
         * Amaranthus hybridus (H): Azul suave
         * Amaranthus retroflexus (R): Ámbar suave
         * Zea mays / Maíz (M): Verde suave
         * Celdas vacías (sin planta): Gris con trama diagonal
     - Eje vertical simplificado (F1, F2, ..., F26) y columnas (C1 a C8).
     - Nombres científicos en cursiva matemática en la leyenda oficial.

  2. Soporte nativo de fotos múltiples por maceta:
     - Permite múltiples tomas en una misma posición (ej. re-tomas o tomas adicionales).
     - Resuelve mapeos específicos como 2026-05-14_c2_r1 (153 fotos / 130 macetas, donde F26C5..F4C5 tienen 2 tomas).
     - Si una maceta tiene >1 foto, muestra una insignia morada ('k fotos') y distribuye los puntos
       horizontalmente dentro de la celda, cada uno con su propio orden, hora y flecha de orientación.

  3. Flechas de orientación de cámara (EXIF):
     - Muestra una flecha direccional azul en cada toma según su rotación física en la captura:
         * [ ↑ ] O:1 -> Horizontal normal (Landscape)
         * [ → ] O:6 -> Vertical rotada 90° horario (CW / Portrait derecha)
         * [ ← ] O:8 -> Vertical rotada 90° antihorario (CCW / Portrait izquierda)
         * [ ↓ ] O:3 -> Invertida 180°

  4. Información por captura:
     - Cada punto indica el número de orden secuencial cronológico en su centro.
     - Etiqueta el nombre del archivo (ej. DSC_0062.JPG) y la hora exacta de disparo (hh:mm:ss).

  5. Trazado en serpentina y diagnóstico:
     - Línea punteada que conecta las tomas en su orden cronológico de captura.
     - Detección de macetas faltantes: si una posición planificada carece de imagen, se resalta
       con borde discontinuo rojo y la marca 'FALTANTE'.
     - Subtítulo con métricas precisas de cobertura (macetas cubiertas, porcentaje, fotos totales
       y número de macetas con fotos múltiples).

  6. Compatibilidad y fuentes de datos:
     - Funciona tanto con carpetas crudas directas (extrayendo metadatos EXIF al vuelo de los .JPG)
       como reutilizando el manifest.csv generado previamente por s14_label_dataset.py si existe.
"""

    epilog_text = """
Ejemplos de uso:
----------------
  1. Graficar una sesión específica de 2025:
     python scripts/s16_plot_experimental_grid.py --session_dir "data/raw/2025-05-13_c1_r1"

  2. Graficar una sesión específica de 2026 (sesión estándar de 130 fotos):
     python scripts/s16_plot_experimental_grid.py --session_dir "data/raw/2026-06-10_c2_r2"

  3. Graficar una sesión de 2026 con fotos múltiples (153 fotos, 23 macetas con doble toma):
     python scripts/s16_plot_experimental_grid.py --session_dir "data/raw/2026-05-14_c2_r1"

  4. Graficar automáticamente todas las sesiones disponibles en data/raw:
     python scripts/s16_plot_experimental_grid.py --all

  5. Leer sesiones desde un directorio raíz o disco externo:
     python scripts/s16_plot_experimental_grid.py --all --raw_dir "D:\\TFM_DATASET\\raw"

  6. Guardar la figura en una ruta o nombre de archivo personalizado:
     python scripts/s16_plot_experimental_grid.py --session_dir "data/raw/2025-05-13_c1_r1" --output "grafico_2025_c1_r1.png"

Archivos de salida generados:
----------------------------
  * {session_dir}/grid_plot.png            -> Imagen en alta resolución (180 DPI) dentro de la carpeta de sesión.
  * data/processed/plots/{sesion}_grid.png -> Copia consolidada en el repositorio central de figuras.
"""
    parser = argparse.ArgumentParser(
        description=description_text,
        epilog=epilog_text,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--session_dir",
        type=str,
        default=None,
        help="Ruta al directorio de la sesión cruda a graficar (ej. data/raw/2025-05-13_c1_r1 o 2026-05-14_c2_r1).",
    )
    parser.add_argument(
        "--raw_dir",
        type=str,
        default=r"data\raw",
        help="Directorio raíz que contiene las carpetas de sesiones crudas (por defecto: data/raw).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Procesa y grafica automáticamente todas las sesiones encontradas en raw_dir (por defecto si no se indica --session_dir).",
    )
    parser.add_argument(
        "--design_dir",
        type=str,
        default=r"exp_design",
        help="Ruta a la carpeta con los diseños experimentales 01_2025.csv y 03_2026.csv (por defecto: exp_design).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Ruta de salida personalizada para la imagen generada (solo al procesar una única sesión).",
    )
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    design_dir = Path(args.design_dir)
    central_plots_dir = Path("data/processed/plots")
    central_plots_dir.mkdir(parents=True, exist_ok=True)

    if args.all:
        session_dirs = sorted([d for d in raw_dir.iterdir() if d.is_dir() and d.name.startswith(("2025", "2026"))])
        if not session_dirs:
            print(f"[ERROR] No se encontraron carpetas de sesión en {raw_dir}")
            sys.exit(1)
    elif args.session_dir:
        candidate = Path(args.session_dir)
        if candidate.exists() and candidate.is_dir():
            session_dirs = [candidate]
        elif (raw_dir / args.session_dir).exists() and (raw_dir / args.session_dir).is_dir():
            session_dirs = [raw_dir / args.session_dir]
        else:
            print(f"[ERROR] No existe el directorio de sesión: {args.session_dir}")
            sys.exit(1)
    else:
        # Por defecto si no se indica argumento, procesar todas las sesiones
        session_dirs = sorted([d for d in raw_dir.iterdir() if d.is_dir() and d.name.startswith(("2025", "2026"))])

    import shutil
    print(f"\nGenerando esquemas gráficos para {len(session_dirs)} sesión(es)...")

    for s_dir in session_dirs:
        print(f"\n--- Procesando: {s_dir.name} ---")
        df_grid, df_images, year, meta = load_session_data(s_dir, design_dir)

        if args.output and len(session_dirs) == 1:
            primary_output = Path(args.output)
        else:
            primary_output = s_dir / "grid_plot.png"

        plot_grid(df_grid, df_images, year, meta, primary_output)

        central_output = central_plots_dir / f"{s_dir.name}_grid.png"
        if primary_output.resolve() != central_output.resolve():
            shutil.copy2(primary_output, central_output)
            print(f" -> Copia consolidada guardada en: {central_output}")


if __name__ == "__main__":
    main()
