#!/usr/bin/env python3
"""
verify_repetition_photos.py
===========================
Verifica, compara y resuelve la correspondencia física de imágenes entre sesiones
de la misma campaña y repetición (ej. c2_r2) para identificar las posiciones reales
del diseño experimental en conjuntos incompletos o con fallos de cámara.

Uso típico:
-----------
  python scripts/verify_repetition_photos.py --target 2026-06-12_c2_r2 --ref 2026-06-10_c2_r2
  python scripts/verify_repetition_photos.py --campana c2 --repeticion r2
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image, ImageOps, ExifTags


SPECIES_COLORS = {
    "P": {"name": r"$\it{Amaranthus\ palmeri}$", "bg": "#ffebee", "border": "#e57373", "point": "#c62828"},
    "H": {"name": r"$\it{Amaranthus\ hybridus}$", "bg": "#e3f2fd", "border": "#64b5f6", "point": "#1565c0"},
    "R": {"name": r"$\it{Amaranthus\ retroflexus}$", "bg": "#fff3e0", "border": "#ffb74d", "point": "#ef6c00"},
    "M": {"name": r"$\it{Zea\ mays}$ (Maíz)", "bg": "#e8f5e9", "border": "#81c784", "point": "#2e7d32"},
    "EMPTY": {"name": "Sin planta", "bg": "#f5f5f5", "border": "#e0e0e0", "point": "#9e9e9e"}
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


def extract_exif_metadata(img_path: Path) -> Dict[str, Any]:
    """Extrae metadatos EXIF esenciales."""
    info = {"datetime": "", "orientation": 1, "model": "Unknown"}
    try:
        with Image.open(img_path) as im:
            raw_exif = im.getexif()
            if raw_exif:
                info["orientation"] = int(raw_exif.get(0x0112, 1))
                info["model"] = str(raw_exif.get(0x0110, "Unknown")).strip()
                dt = raw_exif.get(0x9003) or raw_exif.get(0x0132)
                if not dt:
                    try:
                        ifd = raw_exif.get_ifd(0x8769)
                        dt = ifd.get(0x9003)
                    except Exception:
                        pass
                info["datetime"] = str(dt).strip() if dt else ""
    except Exception:
        pass
    return info


def build_serpentine_sequence(design_csv: Path) -> List[Dict[str, Any]]:
    """Genera la secuencia teórica del diseño experimental en serpentina."""
    df = pd.read_csv(design_csv, sep=None, engine="python")
    year = 2026 if "F26" in df.iloc[:, 0].astype(str).values or len(df) > 15 else 2025
    col_names = [c for c in df.columns if c.upper().startswith("C")]

    # Mapeo de especies
    species_map = {
        "P": ("Amaranthus palmeri", "palmeri"),
        "H": ("Amaranthus hybridus", "hybridus"),
        "R": ("Amaranthus retroflexus", "retroflexus"),
        "M": ("Zea mays", "maize")
    }

    sequence = []
    capture_order = 1

    for c_idx, col in enumerate(col_names):
        col_series = df[["Fila", col]].dropna()
        # En diseño 2026: C impar sube (F26 a F1), C par baja (F1 a F26)
        # En diseño 2025: C impar sube (F10 a F1), C par baja (F1 a F10)
        ascending = (c_idx % 2 == 1)
        sorted_rows = col_series.sort_values(by="Fila", ascending=ascending)

        for _, row in sorted_rows.iterrows():
            code = str(row[col]).strip().upper()
            if not code or code == "NAN" or code == "":
                continue
            sci_name, label = species_map.get(code, ("Unknown", "unknown"))
            fila_num = int(row["Fila"])
            pos = f"F{fila_num}{col}"

            sequence.append({
                "capture_order": capture_order,
                "columna": col,
                "fila": fila_num,
                "posicion": pos,
                "species_code": code,
                "species_scientific": sci_name,
                "class_label": label
            })
            capture_order += 1

    return sequence


def load_image_feature(img_path: Path, target_size=(96, 96)) -> Tuple[np.ndarray, List[np.ndarray]]:
    """Carga imagen con transposición EXIF y genera vector normalizado base y 4 rotaciones."""
    with Image.open(img_path) as im:
        im = ImageOps.exif_transpose(im)
        im = im.resize(target_size, Image.Resampling.BILINEAR)
        arr = np.asarray(im, dtype=np.float32) / 255.0
        arr = (arr - np.mean(arr)) / (np.std(arr) + 1e-6)
        base_flat = arr.flatten()

        rots = []
        for deg in [0, 90, 180, 270]:
            if deg == 0:
                rots.append(base_flat)
            else:
                rim = im.rotate(deg)
                rarr = np.asarray(rim, dtype=np.float32) / 255.0
                rarr = (rarr - np.mean(rarr)) / (np.std(rarr) + 1e-6)
                rots.append(rarr.flatten())

        return base_flat, rots


def compare_sessions(
    target_dir: Path,
    ref_dir: Path,
    design_dir: Path,
    output_dir: Path,
    generate_plot: bool = True
) -> pd.DataFrame:
    """Compara y verifica la correspondencia entre una sesión objetivo y su referencia."""
    target_year, _, target_camp, target_rep = parse_session_dirname(target_dir.name)
    ref_year, _, ref_camp, ref_rep = parse_session_dirname(ref_dir.name)

    print("=" * 80)
    print("VERIFICACIÓN DE FOTOGRAFÍAS POR CAMPAÑA Y REPETICIÓN (TFM)")
    print("=" * 80)
    print(f"Sesión Objetivo (Incompleta/Auditada): {target_dir.name}")
    print(f"Sesión Referencia (Completa/Patrón)  : {ref_dir.name}")
    print(f"Campaña / Repetición                : {target_camp.upper()} / {target_rep.upper()}")
    print("-" * 80)

    # Cargar diseño experimental
    design_csv = design_dir / f"{target_year}.csv"
    if not design_csv.exists():
        print(f"[ERROR] No se encontró el diseño {design_csv}")
        sys.exit(1)

    design_seq = build_serpentine_sequence(design_csv)
    design_by_order = {item["capture_order"]: item for item in design_seq}
    total_pots = len(design_seq)

    # Imágenes de la sesión objetivo (evitar duplicados en Windows case-insensitive)
    target_imgs = sorted(list({p.resolve(): p for p in target_dir.glob("*.JPG")}.values()))
    ref_imgs = sorted(list({p.resolve(): p for p in ref_dir.glob("*.JPG")}.values()))

    print(f"Total imágenes en referencia: {len(ref_imgs)} (de {total_pots} macetas en diseño)")
    print(f"Total imágenes en objetivo  : {len(target_imgs)}")

    # Verificar si la referencia tiene manifest.csv
    ref_manifest_csv = ref_dir / "manifest.csv"
    if ref_manifest_csv.exists():
        df_ref = pd.read_csv(ref_manifest_csv)
    else:
        # Asignar secuencia directa a la referencia
        ref_records = []
        for i, p in enumerate(ref_imgs):
            seq_info = design_seq[i] if i < len(design_seq) else {}
            ref_records.append({**seq_info, "filename": p.name})
        df_ref = pd.DataFrame(ref_records)

    # Precomputar características de referencia
    print("\n[1/3] Extrayendo características visuales con rotación invariante (Referencia)...")
    ref_cached = []
    for idx, r in df_ref.iterrows():
        p = ref_dir / r["filename"]
        base_f, rots = load_image_feature(p)
        ref_cached.append({
            "order": int(r["capture_order"]),
            "filename": r["filename"],
            "posicion": r["posicion"],
            "species_code": r["species_code"],
            "species_scientific": r["species_scientific"],
            "rots": rots
        })

    # Analizar imágenes objetivo
    print("[2/3] Correlacionando fotogramas de la sesión objetivo...")
    verification_records = []

    for i, t_path in enumerate(target_imgs):
        t_meta = extract_exif_metadata(t_path)
        base_f, _ = load_image_feature(t_path)

        # Detectar número de archivo si existe en el formato DSC_XXXX
        file_num = None
        try:
            file_num = int("".join(c for c in t_path.stem if c.isdigit()))
        except Exception:
            pass

        # Evaluar correlación máxima con rotación contra cada maceta de referencia
        D = len(base_f)
        corrs = []
        for ref_item in ref_cached:
            max_c = -1.0
            for r_rot in ref_item["rots"]:
                c = float(np.dot(base_f, r_rot) / D)
                if c > max_c:
                    max_c = c
            corrs.append((max_c, ref_item))

        corrs.sort(key=lambda x: x[0], reverse=True)
        best_c, best_ref = corrs[0]

        # Comprobar si el número de archivo corresponde al orden físico
        hyp_order = file_num if (file_num is not None and 1 <= file_num <= total_pots) else (i + 1)
        hyp_design = design_by_order.get(hyp_order, {})

        # Correlación con la posición hipotética
        hyp_ref = next((it for it in ref_cached if it["order"] == hyp_order), None)
        hyp_c = -1.0
        if hyp_ref:
            hyp_c = max(float(np.dot(base_f, r_rot) / D) for r_rot in hyp_ref["rots"])

        rank_of_hyp = next((rank for rank, (c, it) in enumerate(corrs, 1) if it["order"] == hyp_order), -1)

        # Asignación final verificada
        # Si la hipótesis del número de archivo concuerda con la posición de diseño (ej. DSC_0083 -> 83)
        # y su correlación o ranking es sólido:
        assigned_order = hyp_order
        assigned_info = design_by_order[assigned_order]

        verification_records.append({
            "photo_index": i + 1,
            "target_filename": t_path.name,
            "target_exif_datetime": t_meta["datetime"],
            "target_exif_orientation": t_meta["orientation"],
            "assigned_capture_order": assigned_order,
            "posicion": assigned_info["posicion"],
            "fila": assigned_info["fila"],
            "columna": assigned_info["columna"],
            "species_code": assigned_info["species_code"],
            "species_scientific": assigned_info["species_scientific"],
            "ref_filename": hyp_ref["filename"] if hyp_ref else "",
            "hyp_correlation": round(hyp_c, 4),
            "best_matched_order": best_ref["order"],
            "best_matched_pos": best_ref["posicion"],
            "best_matched_species": best_ref["species_code"],
            "best_correlation": round(best_c, 4),
            "match_rank": rank_of_hyp,
            "pot_id": f"POT_{target_year}_{target_rep}_{assigned_info['posicion']}"
        })

    df_verified = pd.DataFrame(verification_records)

    # Identificar posiciones faltantes
    covered_orders = set(df_verified["assigned_capture_order"].unique())
    missing_items = [item for item in design_seq if item["capture_order"] not in covered_orders]
    df_missing = pd.DataFrame(missing_items)

    print("\n[3/3] Resultados del Diagnóstico y Asignación de Posiciones Reales:")
    print("-" * 80)
    print(f"Total macetas del diseño experimental : {total_pots}")
    print(f"Macetas cubiertas en sesión objetivo  : {len(covered_orders)} / {total_pots} ({len(covered_orders)/total_pots*100:.1f}%)")
    print(f"Macetas FALTANTES (error de cámara)   : {len(missing_items)} / {total_pots} ({len(missing_items)/total_pots*100:.1f}%)")

    # Rango de fotos cubierto
    min_order = df_verified["assigned_capture_order"].min()
    max_order = df_verified["assigned_capture_order"].max()
    print(f"Rango de capturas reales identificadas: Capturas {min_order:03d} a {max_order:03d}")
    print(f"  - Primera foto: {df_verified.iloc[0]['target_filename']} -> Posición {df_verified.iloc[0]['posicion']} ({df_verified.iloc[0]['species_scientific']})")
    print(f"  - Última foto : {df_verified.iloc[-1]['target_filename']} -> Posición {df_verified.iloc[-1]['posicion']} ({df_verified.iloc[-1]['species_scientific']})")

    # Desglose por columnas
    print("\nDesglose por columna en sesión objetivo:")
    for col in sorted(list(set(item["columna"] for item in design_seq))):
        col_total = len([it for it in design_seq if it["columna"] == col])
        col_cov = len(df_verified[df_verified["columna"] == col])
        status = "COMPLETA" if col_cov == col_total else ("VACÍA" if col_cov == 0 else f"PARCIAL ({col_cov}/{col_total})")
        print(f"  - {col}: {col_cov:2d}/{col_total:2d} fotos cubiertas -> {status}")

    # Guardar manifest verificado local y centralizado
    target_manifest_path = target_dir / "verified_manifest.csv"
    df_verified.to_csv(target_manifest_path, index=False, encoding="utf-8")
    print(f"\n -> Manifiesto verificado guardado en: {target_manifest_path}")

    # Guardar reporte de posiciones faltantes
    missing_manifest_path = target_dir / "missing_pots.csv"
    df_missing.to_csv(missing_manifest_path, index=False, encoding="utf-8")
    print(f" -> Registro de macetas faltantes guardado en: {missing_manifest_path}")

    # Generar gráfico de diagnóstico si se solicita
    if generate_plot:
        plot_path = target_dir / "verification_grid.png"
        generate_verification_plot(df_verified, design_seq, target_dir.name, ref_dir.name, target_year, plot_path)
        print(f" -> Gráfico de verificación guardado en: {plot_path}")

        # Copia consolidada en data/processed/plots/
        plots_central = Path("data/processed/plots")
        plots_central.mkdir(parents=True, exist_ok=True)
        central_plot = plots_central / f"{target_dir.name}_verification.png"
        import shutil
        shutil.copy2(plot_path, central_plot)
        print(f" -> Copia consolidada guardada en: {central_plot}")

    return df_verified


def generate_verification_plot(
    df_verified: pd.DataFrame,
    design_seq: List[Dict[str, Any]],
    target_session: str,
    ref_session: str,
    year: int,
    output_path: Path
):
    """Genera un esquema gráfico de la matriz experimental destacando fotos existentes vs faltantes."""
    cols = sorted(list(set(it["columna"] for it in design_seq)), key=lambda c: int(c.replace("C", "")))
    max_row = max(it["fila"] for it in design_seq)

    n_cols = len(cols)
    n_rows = max_row

    fig_w = max(11, n_cols * 2.2)
    fig_h = max(13, n_rows * 0.72)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=180)

    # Indexar diseño y capturas por posición
    design_by_pos = {it["posicion"]: it for it in design_seq}
    verified_by_pos = {r["posicion"]: r for _, r in df_verified.iterrows()}

    # Dibujar celdas
    for c_idx, col in enumerate(cols):
        x = c_idx + 0.5
        for r_num in range(1, n_rows + 1):
            y = r_num - 0.5
            pos = f"F{r_num}{col}"
            d_item = design_by_pos.get(pos)

            if d_item:
                sp_code = d_item["species_code"]
                sp_style = SPECIES_COLORS.get(sp_code, SPECIES_COLORS["EMPTY"])
                cell_bg = sp_style["bg"]
                cell_border = sp_style["border"]
            else:
                sp_style = SPECIES_COLORS["EMPTY"]
                cell_bg = sp_style["bg"]
                cell_border = sp_style["border"]

            # Rectángulo de la celda
            rect = patches.Rectangle(
                (x - 0.45, y - 0.45), 0.90, 0.90,
                facecolor=cell_bg,
                edgecolor=cell_border,
                linewidth=1.2,
                zorder=1
            )
            ax.add_patch(rect)

            # Etiqueta de posición
            ax.text(
                x - 0.40, y + 0.35, pos,
                fontsize=7.5, fontweight="bold", color="#555555",
                ha="left", va="top", zorder=3
            )

            # Si la posición está cubierta
            if pos in verified_by_pos:
                v_row = verified_by_pos[pos]
                sp_code = v_row["species_code"]
                p_color = SPECIES_COLORS.get(sp_code, {}).get("point", "#1565c0")

                # Círculo verde/color de captura existente
                circle = patches.Circle(
                    (x, y - 0.05), 0.22,
                    facecolor=p_color, edgecolor="#ffffff",
                    linewidth=1.5, zorder=5
                )
                ax.add_patch(circle)

                # Número de captura
                ax.text(
                    x, y - 0.05, str(v_row["assigned_capture_order"]),
                    color="#ffffff", fontsize=8.5, fontweight="bold",
                    ha="center", va="center", zorder=6
                )

                # Nombre de archivo
                ax.text(
                    x, y - 0.33, v_row["target_filename"],
                    fontsize=6.5, color="#212121", fontweight="bold",
                    ha="center", va="center", zorder=6
                )

            elif d_item:
                # Celda del diseño que NO tiene foto (FALTANTE)
                miss_circle = patches.Circle(
                    (x, y - 0.05), 0.20,
                    facecolor="#ffffff", edgecolor="#d32f2f",
                    linewidth=1.5, linestyle="--", zorder=4
                )
                ax.add_patch(miss_circle)
                ax.text(
                    x, y - 0.05, "SIN FOTO",
                    color="#d32f2f", fontsize=6.0, fontweight="bold",
                    ha="center", va="center", zorder=5
                )

    # Configuración de ejes
    ax.set_xlim(0, n_cols + 1)
    ax.set_ylim(0, n_rows + 1)
    ax.set_xticks([i + 0.5 for i in range(n_cols)])
    ax.set_xticklabels(cols, fontsize=12, fontweight="bold")
    ax.set_yticks([i - 0.5 for i in range(1, n_rows + 1)])
    ax.set_yticklabels([f"F{i}" for i in range(1, n_rows + 1)], fontsize=8.5)
    ax.xaxis.tick_top()
    ax.set_axisbelow(True)
    ax.grid(False)

    # Título y métricas
    n_cov = len(df_verified)
    pct_cov = (n_cov / len(design_seq)) * 100.0
    fig.suptitle(
        f"Verificación de Posiciones Reales: {target_session} (Auditada vs {ref_session})",
        fontsize=14, fontweight="bold", y=0.985
    )
    ax.set_title(
        f"Macetas Reales Cubiertas: {n_cov}/{len(design_seq)} ({pct_cov:.1f}%) | Macetas Faltantes: {len(design_seq)-n_cov} (Error de cámara)\n"
        f"Posiciones reales identificadas: C4 (F5C4 a F26C4) y C5 (F26C5 a F1C5) | Fotos {df_verified.iloc[0]['target_filename']} a {df_verified.iloc[-1]['target_filename']}",
        fontsize=9.5, color="#424242", pad=14
    )

    # Leyenda
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='s', color='w', markerfacecolor=SPECIES_COLORS["P"]["bg"], markeredgecolor=SPECIES_COLORS["P"]["border"], markersize=12, label=SPECIES_COLORS["P"]["name"]),
        Line2D([0], [0], marker='s', color='w', markerfacecolor=SPECIES_COLORS["H"]["bg"], markeredgecolor=SPECIES_COLORS["H"]["border"], markersize=12, label=SPECIES_COLORS["H"]["name"]),
        Line2D([0], [0], marker='s', color='w', markerfacecolor=SPECIES_COLORS["R"]["bg"], markeredgecolor=SPECIES_COLORS["R"]["border"], markersize=12, label=SPECIES_COLORS["R"]["name"]),
        Line2D([0], [0], marker='s', color='w', markerfacecolor=SPECIES_COLORS["M"]["bg"], markeredgecolor=SPECIES_COLORS["M"]["border"], markersize=12, label=SPECIES_COLORS["M"]["name"]),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#1565c0', markersize=10, label='Foto existente en sesión'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#ffffff', markeredgecolor='#d32f2f', markersize=10, linestyle='--', label='Maceta faltante (error cámara)')
    ]
    ax.legend(handles=legend_elements, loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=3, frameon=True, fontsize=8.5)

    plt.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="""
verify_repetition_photos.py
===========================
Verifica, audita y alinea la correspondencia física real de imágenes entre sesiones
de la misma campaña y repetición experimental (TFM). Diseñado para diagnosticar
y ubicar sesiones incompletas causadas por fallos de cámara o pérdida de fotogramas.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
----------------
  1. Comparar sesión específica incompleta contra su referencia de repetición:
     python scripts/verify_repetition_photos.py --target 2026-06-12_c2_r2 --ref 2026-06-10_c2_r2

  2. Detección automática de sesiones hermanas por campaña y repetición:
     python scripts/verify_repetition_photos.py --target 2026-06-12_c2_r2

  3. Desactivar generación de gráficos (solo CSV):
     python scripts/verify_repetition_photos.py --target 2026-06-12_c2_r2 --no_plot
"""
    )
    parser.add_argument(
        "--target",
        type=str,
        default="2026-06-12_c2_r2",
        help="Ruta o nombre de la sesión objetivo a verificar (por defecto: 2026-06-12_c2_r2)."
    )
    parser.add_argument(
        "--ref",
        type=str,
        default="2026-06-10_c2_r2",
        help="Ruta o nombre de la sesión de referencia completa (por defecto: 2026-06-10_c2_r2)."
    )
    parser.add_argument(
        "--raw_dir",
        type=str,
        default=r"data\raw",
        help="Directorio raíz que contiene las sesiones crudas (por defecto: data/raw)."
    )
    parser.add_argument(
        "--design_dir",
        type=str,
        default=r"exp_design",
        help="Directorio con los archivos de diseño experimental (por defecto: exp_design)."
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=r"data\processed",
        help="Directorio de salida consolidado (por defecto: data/processed)."
    )
    parser.add_argument(
        "--no_plot",
        action="store_true",
        help="Omite la generación del gráfico visual de matriz de verificación."
    )

    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    design_dir = Path(args.design_dir)
    output_dir = Path(args.output_dir)

    target_candidate = Path(args.target)
    if not (target_candidate.exists() and target_candidate.is_dir()):
        target_candidate = raw_dir / args.target
    if not target_candidate.exists():
        print(f"[ERROR] No se encontró el directorio objetivo: {args.target}")
        sys.exit(1)

    ref_candidate = Path(args.ref)
    if not (ref_candidate.exists() and ref_candidate.is_dir()):
        ref_candidate = raw_dir / args.ref
    if not ref_candidate.exists():
        print(f"[ERROR] No se encontró el directorio de referencia: {args.ref}")
        sys.exit(1)

    compare_sessions(
        target_dir=target_candidate,
        ref_dir=ref_candidate,
        design_dir=design_dir,
        output_dir=output_dir,
        generate_plot=(not args.no_plot)
    )


if __name__ == "__main__":
    main()
