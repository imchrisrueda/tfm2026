"""Generate Markdown/HTML reports and anonymous side-by-side comparison figures."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from common import (
    DEFAULT_BENCHMARK_DIR,
    read_json,
    sha256_text,
    utc_now_iso,
)


def build_anonymous_comparison_sheets(benchmark_dir: Path, split: str, size: int = 384) -> list[str]:
    """Create anonymous side-by-side comparison sheets across available views."""
    sample_rows = read_json(benchmark_dir / "samples" / f"{split}.json")
    cfg = read_json(benchmark_dir / "config_draft.json")
    views = list(cfg["views"]["definitions"])
    seed = cfg["seed"]
    fig_dir = benchmark_dir / "figures" / split
    fig_dir.mkdir(parents=True, exist_ok=True)

    generated: list[str] = []
    for row in sample_rows:
        iid = row["image_id"]
        blind_id = row["blind_id"]
        # Deterministic anonymous permutation of view order per image
        ordered_views = sorted(views, key=lambda v: sha256_text(f"{seed}|blind_view|{iid}|{v}"))
        available = []
        for idx, v in enumerate(ordered_views, 1):
            p = benchmark_dir / "views" / v / str(size) / split / f"{iid}.png"
            if p.exists():
                available.append((f"M{idx}", v, p))
        if not available:
            continue

        pad = 8
        tile_w = len(available) * (size + pad) + pad
        tile_h = size + 36
        sheet = Image.new("RGB", (tile_w, tile_h), "white")
        draw = ImageDraw.Draw(sheet)
        for col, (anon_code, _, img_path) in enumerate(available):
            with Image.open(img_path) as im:
                sheet.paste(im.convert("RGB"), (pad + col * (size + pad), 4))
            draw.text((pad + col * (size + pad) + 4, size + 10), f"{blind_id} | {anon_code}", fill="black")

        out_path = fig_dir / f"{blind_id}_anon_{size}.png"
        sheet.save(out_path, format="PNG")
        generated.append(str(out_path.relative_to(benchmark_dir).as_posix()))

    return generated


def generate_report(benchmark_dir: Path, split: str) -> Path:
    sampling = read_json(benchmark_dir / "sampling.json")
    env = read_json(benchmark_dir / "environment.json")
    stats_path = benchmark_dir / f"statistics_{split}.json"
    stats = read_json(stats_path) if stats_path.exists() else None
    timings_path = benchmark_dir / f"timings_{split}.csv"

    lines = [
        f"# Informe de benchmark de segmentación y preprocesado (`{split}`)",
        "",
        f"Generado: `{utc_now_iso()}`.",
        "",
        "## 1. Entorno y dependencias",
        f"- Python: `{env.get('python_version')}` (`{env.get('python_executable')}`)",
        f"- Pillow: `{env.get('pillow_version')}`, NumPy: `{env.get('numpy_version')}`",
        f"- OpenCV: `{env.get('cv2', {}).get('available')}` (`{env.get('cv2', {}).get('version')}`)",
        f"- PyTorch: `{env.get('torch', {}).get('available')}` (CUDA: `{env.get('torch', {}).get('cuda_available')}`)",
        f"- SAM3: `{env.get('sam3', {}).get('available')}`",
        "",
        "## 2. Resumen de muestreo",
        f"- Semilla: `{sampling['seed']}`",
        f"- Disjunción de grupos verificada: `{sampling['disjointness_verified']}`",
        f"- Cobertura `{split}`: `{sampling.get(split, {}).get('coverage', {}).get('by_year_species', {})}`",
        "",
    ]

    if timings_path.exists():
        import csv

        with timings_path.open(encoding="utf-8-sig", newline="") as stream:
            t_rows = list(csv.DictReader(stream))
        lines.append("## 3. Ejecución y tiempos observados")
        lines.append(f"- Registros en `timings_{split}.csv`: `{len(t_rows)}`")
        by_m: dict[str, dict[str, int]] = {}
        for r in t_rows:
            m = r["method_id"]
            by_m.setdefault(m, {})
            by_m[m][r["status"]] = by_m[m].get(r["status"], 0) + 1
        for m, counts in sorted(by_m.items()):
            lines.append(f"  - `{m}`: `{counts}`")
        lines.append("")

    if stats is not None:
        lines.append("## 4. Métricas frente a referencia humana")
        lines.append(f"- Imágenes en muestra: `{stats['n_sample_images']}`; sin GT: `{stats['n_missing_gt']}`")
        for eid, val in sorted(stats.get("summary_by_entity", {}).items()):
            lines.append(f"- **{eid}**: `{val}`")
        lines.append("")
    else:
        lines.append("## 4. Métricas frente a referencia humana")
        lines.append("- Pendiente: no existen todavía anotaciones humanas adjudicadas (`annotations/consensus/`).")
        lines.append("")

    out_md = benchmark_dir / f"report_{split}.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_md


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, default=DEFAULT_BENCHMARK_DIR)
    parser.add_argument("--split", choices=["tuning", "evaluation", "stress"], default="tuning")
    parser.add_argument("--sheets", action="store_true")
    args = parser.parse_args()

    out_md = generate_report(args.benchmark_dir, args.split)
    sheets = build_anonymous_comparison_sheets(args.benchmark_dir, args.split) if args.sheets else []
    import json

    print(json.dumps({"report": str(out_md), "anonymous_sheets": len(sheets)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
