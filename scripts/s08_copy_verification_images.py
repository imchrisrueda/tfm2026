#!/usr/bin/env python3
"""
s08_copy_verification_images.py
===========================
Copia las imágenes de la última toma de cada campaña y repetición en un nuevo
directorio dentro de 'data' (data/verificacion_siembra), renombrándolas con el
sufijo '_<especie>' según el diseño experimental y el recorrido en serpentina.

Sesiones procesadas:
- 2025-05-28 (c1_r1) -> 70 imágenes
- 2025-06-20 (c1_r2) -> 60 imágenes (excluyendo la subcarpeta nikon_d70)
- 2026-05-14 (c2_r1) -> 153 imágenes
- 2026-06-12 (c2_r2) -> 48 imágenes (órdenes 83 a 130 del diseño)

Total imágenes copiadas: 331
"""

import os
import shutil
from pathlib import Path
import pandas as pd

def main():
    root = Path(__file__).resolve().parents[1]
    inventory_path = root / 'data/processed/audit_raw_2026-11-12/inventory.csv'
    
    if not inventory_path.exists():
        raise FileNotFoundError(f"No se encontró el inventario auditado en {inventory_path}")
        
    df = pd.read_csv(inventory_path)
    
    target_sessions = [
        ('2025-05-28', '2025-05-28_c1_r1'),
        ('2025-06-20', '2025-06-20_c1_r2'),
        ('2026-05-14', '2026-05-14_c2_r1'),
        ('2026-06-12', '2026-06-12_c2_r2'),
    ]
    
    species_map = {
        'P': 'palmeri',
        'H': 'hybridus',
        'R': 'retroflexus',
        'M': 'maiz',
    }
    
    dest_base = root / 'data/verificacion_siembra'
    dest_base.mkdir(parents=True, exist_ok=True)
    
    manifest_records = []
    
    print(f"Iniciando copia de verificación en: {dest_base}")
    
    for date_str, session_id in target_sessions:
        # Filtrar solo archivos directos en la raíz de la sesión (excluyendo subcarpetas como nikon_d70)
        sub = df[(df['session_id'] == session_id) & (df['source_subdir'] == '.')]
        
        session_dest_dir = dest_base / session_id
        session_dest_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\nProcesando {session_id} (Fecha: {date_str}) -> {len(sub)} imágenes")
        
        for _, row in sub.iterrows():
            orig_rel_path = row['relative_path']
            src_file = root / orig_rel_path
            
            if not src_file.exists():
                raise FileNotFoundError(f"Archivo de origen no encontrado: {src_file}")
                
            orig_filename = row['filename']
            base_name, ext = os.path.splitext(orig_filename)
            
            species_code = str(row['species_code']).strip()
            species_name = species_map.get(species_code, 'desconocida')
            
            # Nombre con sufijo _especie
            new_filename = f"{base_name}_{species_name}{ext}"
            dest_file = session_dest_dir / new_filename
            
            # Copiar preservando metadatos (EXIF, fecha de modificación, etc.)
            shutil.copy2(src_file, dest_file)
            
            manifest_records.append({
                'session_id': session_id,
                'fecha': date_str,
                'campana': row['campana'],
                'repeticion': row['repeticion'],
                'posicion': row['posicion'],
                'fila': row['fila'],
                'columna': row['columna'],
                'species_code': species_code,
                'especie': species_name,
                'species_scientific': row['species_scientific'],
                'filename_original': orig_filename,
                'filename_nuevo': new_filename,
                'ruta_origen': orig_rel_path,
                'ruta_destino': dest_file.relative_to(root).as_posix(),
                'bytes': src_file.stat().st_size,
            })
            
        print(f"  -> {len(sub)} imágenes copiadas a {session_dest_dir.name}")
        
    df_manifest = pd.DataFrame(manifest_records)
    manifest_csv_path = dest_base / 'manifest_verificacion.csv'
    df_manifest.to_csv(manifest_csv_path, index=False, encoding='utf-8-sig')
    print(f"\nManifiesto generado en: {manifest_csv_path}")
    print(f"Total imágenes copiadas: {len(df_manifest)}")

if __name__ == '__main__':
    main()
