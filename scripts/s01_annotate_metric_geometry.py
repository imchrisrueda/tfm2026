"""Local manual annotation of EXIF-oriented development images; no automatic acceptance."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np
from PIL import Image, ImageTk

from s18_prepare_metric_masters import oriented_srgb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "data/processed/preprocessing/development_v1"


def fit_circle(points):
    """Algebraic circle fit; RMS is radial error, not calibration uncertainty."""
    if len(points) < 6:
        raise ValueError("Se necesitan al menos seis puntos del borde exterior.")
    xy = np.asarray(points, dtype=float)
    if xy.ndim != 2 or xy.shape[1] != 2 or not np.isfinite(xy).all():
        raise ValueError("Puntos no válidos.")
    origin = xy.mean(axis=0)
    local = xy - origin
    matrix = np.column_stack((2 * local, np.ones(len(local))))
    result, _, rank, _ = np.linalg.lstsq(matrix, (local * local).sum(axis=1), rcond=None)
    if rank < 3:
        raise ValueError("Los puntos no permiten ajustar un círculo.")
    radius_squared = result[2] + result[0] ** 2 + result[1] ** 2
    if radius_squared <= 0:
        raise ValueError("Radio no válido.")
    radius = math.sqrt(radius_squared)
    center = result[:2] + origin
    rms = float(np.sqrt(np.mean((np.linalg.norm(xy - center, axis=1) - radius) ** 2)))
    return float(center[0]), float(center[1]), 2 * radius, rms


def read_list(path):
    rows = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list) or len({row['image_id'] for row in rows}) != len(rows):
        raise ValueError("Se requiere lista JSON con image_id únicos.")
    return rows


class Annotator:
    def __init__(self, window, selection, output):
        self.window, self.output = window, output
        self.rows = read_list(selection)
        if not self.rows or any(row.get("split_assignment") != "C_fit" or
                                row.get("use_in_assigned_partition") is not True for row in self.rows):
            raise ValueError("El lote debe contener sólo C_fit activo.")
        saved = read_list(output) if output.exists() else []
        selected = {row['image_id']: row for row in self.rows}
        if any(row['image_id'] not in selected or row.get('source_sha256') !=
               selected[row['image_id']]['sha256'] for row in saved):
            raise ValueError("Anotaciones existentes incompatibles con lote/hash.")
        self.saved = {row['image_id']: row for row in saved}
        self.index, self.dirty = 0, False
        self.mode = tk.StringVar(value="rim")
        self.reviewer, self.quality, self.truncated = (tk.StringVar() for _ in range(3))
        self.review_date = tk.StringVar(value=date.today().isoformat())
        self.status = tk.StringVar()
        window.title("Medición manual de macetas · desarrollo C_fit")
        window.geometry("1200x920")
        top = ttk.Frame(window); top.pack(fill="x")
        ttk.Button(top, text="Anterior", command=lambda: self.navigate(-1)).pack(side="left")
        ttk.Button(top, text="Siguiente", command=lambda: self.navigate(1)).pack(side="left")
        ttk.Button(top, text="Guardar revisión", command=self.save).pack(side="left")
        ttk.Button(top, text="Deshacer punto", command=self.undo).pack(side="left")
        ttk.Button(top, text="Borrar geometría", command=self.clear).pack(side="left")
        ttk.Label(window, textvariable=self.status, wraplength=1150).pack(fill="x")
        form = ttk.Frame(window); form.pack(fill="x")
        for label, variable, width in (("Revisor", self.reviewer, 28), ("Fecha ISO", self.review_date, 12)):
            ttk.Label(form, text=label).pack(side="left")
            ttk.Entry(form, textvariable=variable, width=width).pack(side="left")
        ttk.Label(form, text="Referencia").pack(side="left")
        ttk.Combobox(form, textvariable=self.quality, values=("usable", "unusable"),
                     state="readonly", width=10).pack(side="left")
        ttk.Label(form, text="Vegetación cortada en origen").pack(side="left")
        ttk.Combobox(form, textvariable=self.truncated, values=("true", "false"),
                     state="readonly", width=8).pack(side="left")
        controls = ttk.Frame(window); controls.pack(fill="x")
        ttk.Radiobutton(controls, text="Puntos del borde exterior (mínimo 6)",
                        variable=self.mode, value="rim").pack(side="left")
        ttk.Radiobutton(controls, text="Envolvente vegetal (2 esquinas opuestas)",
                        variable=self.mode, value="bbox").pack(side="left")
        ttk.Label(window, text="Notas: oclusión, inclinación, incertidumbre y motivo si no es usable.").pack(anchor="w")
        self.notes = tk.Text(window, height=3); self.notes.pack(fill="x")
        self.canvas = tk.Canvas(window, background="#222", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<Configure>", lambda event: self.draw())
        for variable in (self.reviewer, self.review_date, self.quality, self.truncated):
            variable.trace_add("write", lambda *_: setattr(self, 'dirty', True))
        self.notes.bind("<KeyRelease>", lambda event: setattr(self, 'dirty', True))
        window.protocol("WM_DELETE_WINDOW", self.close)
        self.load()

    def load(self):
        row = self.rows[self.index]
        source = (ROOT / row['source_path']).resolve(); source.relative_to(ROOT)
        if hashlib.sha256(source.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError("El original ya no coincide con el hash del lote.")
        with Image.open(source) as image:
            self.image, self.color_status, _ = oriented_srgb(image)
        if self.image.size != (row['oriented_width'], row['oriented_height']):
            raise ValueError("Dimensiones orientadas incoherentes.")
        annotation = self.saved.get(row['image_id'], {})
        self.points = [list(point) for point in annotation.get('outer_rim_points_px', [])]
        bbox = annotation.get('vegetation_bbox')
        self.bbox_points = [[bbox[0], bbox[1]], [bbox[2], bbox[3]]] if bbox else []
        self.quality.set(annotation.get('reference_quality', ''))
        truncated = annotation.get('vegetation_truncated')
        self.truncated.set(str(truncated).lower() if isinstance(truncated, bool) else '')
        if annotation.get('reviewer'): self.reviewer.set(annotation['reviewer'])
        self.review_date.set(annotation.get('review_date', date.today().isoformat()))
        self.notes.delete('1.0', 'end'); self.notes.insert('1.0', annotation.get('notes', ''))
        self.dirty = False
        self.draw()

    def draw(self):
        if not hasattr(self, 'image'): return
        w, h = self.image.size
        available_w, available_h = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        self.scale = min(available_w / w, available_h / h)
        display_w, display_h = max(1, round(w * self.scale)), max(1, round(h * self.scale))
        self.sx, self.sy = display_w / w, display_h / h
        self.ox, self.oy = (available_w - display_w) / 2, (available_h - display_h) / 2
        self.photo = ImageTk.PhotoImage(self.image.resize((display_w, display_h), Image.Resampling.LANCZOS))
        self.canvas.delete('all')
        self.canvas.create_image(self.ox, self.oy, anchor='nw', image=self.photo)
        def xy(x, y): return self.ox + x * self.sx, self.oy + y * self.sy
        for index, point in enumerate(self.points):
            x, y = xy(*point)
            self.canvas.create_oval(x-3, y-3, x+3, y+3, fill='cyan')
            self.canvas.create_text(x+8, y, text=str(index+1), fill='cyan', anchor='w')
        fit_text = 'sin ajuste'
        try:
            cx, cy, diameter, rms = fit_circle(self.points)
            self.canvas.create_oval(*xy(cx-diameter/2, cy-diameter/2),
                                    *xy(cx+diameter/2, cy+diameter/2), outline='cyan', width=2)
            x, y = xy(cx, cy)
            self.canvas.create_line(x-8, y, x+8, y, fill='cyan')
            self.canvas.create_line(x, y-8, x, y+8, fill='cyan')
            fit_text = f'd={diameter:.2f}px RMS={rms:.2f}px'
        except ValueError: pass
        if len(self.bbox_points) == 2:
            self.canvas.create_rectangle(*xy(*self.bbox_points[0]), *xy(*self.bbox_points[1]), outline='magenta', width=2)
        elif self.bbox_points:
            x, y = xy(*self.bbox_points[0]); self.canvas.create_oval(x-4, y-4, x+4, y+4, outline='magenta')
        row = self.rows[self.index]
        self.status.set(f"{self.index+1}/{len(self.rows)} · {row['image_id']} · {row['species_scientific']} · "
                        f"maceta nominal {row['pot_diameter_exterior_cm']}cm · {fit_text} · "
                        f"{'guardada' if row['image_id'] in self.saved else 'pendiente'}")

    def click(self, event):
        x, y = (event.x - self.ox) / self.sx, (event.y - self.oy) / self.sy
        if not (0 <= x <= self.image.width and 0 <= y <= self.image.height): return
        if self.mode.get() == 'rim': self.points.append([x, y])
        else:
            if len(self.bbox_points) == 2: self.bbox_points = []
            self.bbox_points.append([x, y])
        self.dirty = True; self.draw()

    def undo(self):
        target = self.points if self.mode.get() == 'rim' else self.bbox_points
        if target: target.pop(); self.dirty = True; self.draw()

    def clear(self):
        if messagebox.askyesno('Borrar', '¿Borrar puntos y envolvente de esta imagen?'):
            self.points, self.bbox_points = [], []; self.dirty = True; self.draw()

    def save(self):
        try:
            if not self.reviewer.get().strip(): raise ValueError('Indicar revisor.')
            date.fromisoformat(self.review_date.get())
            if self.quality.get() not in {'usable', 'unusable'}: raise ValueError('Elegir calidad explícitamente.')
            if self.truncated.get() not in {'true', 'false'}: raise ValueError('Indicar explícitamente si la vegetación está cortada.')
            notes = self.notes.get('1.0', 'end').strip()
            if self.quality.get() == 'unusable' and not notes: raise ValueError('Anotar el motivo de referencia no usable.')
            circle = None
            if len(self.points) >= 6: circle = fit_circle(self.points)
            if self.quality.get() == 'usable' and (circle is None or len(self.bbox_points) != 2):
                raise ValueError('Referencia usable requiere mínimo 6 puntos y envolvente vegetal.')
            bbox = None
            if len(self.bbox_points) == 2:
                (x0, y0), (x1, y1) = self.bbox_points
                bbox = [min(x0,x1), min(y0,y1), max(x0,x1), max(y0,y1)]
                if bbox[0] == bbox[2] or bbox[1] == bbox[3]: raise ValueError('Envolvente sin área.')
            row = self.rows[self.index]
            annotation = dict(image_id=row['image_id'], source_sha256=row['sha256'], coordinate_space='exif_oriented',
                review_status='accepted' if self.quality.get() == 'usable' else 'rejected',
                reference_quality=self.quality.get(), reviewer=self.reviewer.get().strip(), review_date=self.review_date.get(),
                reviewed_utc=datetime.now(timezone.utc).isoformat(), outer_rim_points_px=self.points,
                pot_center_x_px=circle[0] if circle else None, pot_center_y_px=circle[1] if circle else None,
                pot_diameter_px=circle[2] if circle else None, rim_fit_rms_px=circle[3] if circle else None,
                pot_diameter_nominal_cm=row['pot_diameter_exterior_cm'], vegetation_bbox=bbox,
                vegetation_truncated=self.truncated.get() == 'true', notes=notes,
                measurement_method='manual_points_algebraic_circle_fit_Tkinter', measurement_scope='investigator_review',
                measurement_repeatability_status='not_estimated', display_color_processing=self.color_status)
            updated = dict(self.saved)
            # Keep committed records independent from mutable on-screen point lists.
            updated[row['image_id']] = json.loads(json.dumps(annotation))
            data = [updated[item['image_id']] for item in self.rows if item['image_id'] in updated]
            self.output.parent.mkdir(parents=True, exist_ok=True)
            if self.output.exists():
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                shutil.copy2(self.output, self.output.with_name(self.output.stem + '.' + stamp + '.bak.json'))
            temporary = self.output.with_suffix('.tmp')
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(self.output)
            self.saved = updated; self.dirty = False; self.draw()
            return True
        except (ValueError, OSError) as error:
            messagebox.showerror('No guardado', str(error)); return False

    def may_leave(self):
        if not self.dirty: return True
        answer = messagebox.askyesnocancel('Cambios pendientes', '¿Guardar la revisión antes de continuar?')
        return False if answer is None else self.save() if answer else True

    def navigate(self, step):
        new_index = self.index + step
        if 0 <= new_index < len(self.rows) and self.may_leave():
            previous = self.index
            self.index = new_index
            try:
                self.load()
            except (ValueError, OSError) as error:
                self.index = previous
                # Never allow saving measurements against a different failed source.
                self.load()
                messagebox.showerror('Imagen no cargada', str(error))

    def close(self):
        if self.may_leave(): self.window.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, default=DEFAULT / 'selection.json')
    parser.add_argument('--output', type=Path, default=DEFAULT / 'annotations_reviewed.json')
    args = parser.parse_args()
    args.output = args.output.resolve(); args.output.relative_to(ROOT)
    if args.output.name != 'annotations_reviewed.json':
        raise ValueError('Usar annotations_reviewed.json; no sobrescribir piloto ni plantilla.')
    window = tk.Tk()
    try: Annotator(window, args.selection, args.output)
    except Exception:
        window.destroy(); raise
    window.mainloop()


if __name__ == '__main__':
    main()
