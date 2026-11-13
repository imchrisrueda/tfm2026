#!/usr/bin/env python3
"""Asignación v1 por maceta, sin leer píxeles ni resultados de modelos (M024)."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd

SEED = 20261112
VERSION = 'v1'
FINGERPRINT_FIELDS = ('source_path', 'sha256', 'species_code', 'split_group_id', 'year', 'campana', 'repeticion',
                      'posicion', 'use_in_initial_partition', 'exclude_from_primary_training',
                      'num_plants_seeded_2025', 'num_plants_nominal_2026')


def snapshot_fingerprint(records):
    selected = [{k: row[k] for k in FINGERPRINT_FIELDS} for row in sorted(records, key=lambda r: r['source_path'])]
    return hashlib.sha256(json.dumps(selected, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def stable_order(group_id, phase):
    return hashlib.sha256(f'{SEED}|{phase}|{group_id}'.encode('utf-8')).hexdigest()


def allocation(n, weights):
    """Mayor resto; empates según el orden de los roles en weights."""
    total = sum(weight for _, weight in weights)
    counts = {role: n * weight // total for role, weight in weights}
    order = sorted(range(len(weights)), key=lambda i: (-(n * weights[i][1] % total), i))
    for i in order[:n - sum(counts.values())]:
        counts[weights[i][0]] += 1
    return counts


def run(root):
    out = root / 'data/processed'
    records = json.loads((out / 'manifest_all.json').read_text(encoding='utf-8'))
    df = pd.DataFrame(records)
    fingerprint = snapshot_fingerprint(records)
    groups = []
    for group_id, images in df.groupby('split_group_id', sort=True):
        for column in ('species_code', 'year', 'campana', 'repeticion', 'posicion'):
            if images[column].nunique(dropna=False) != 1:
                raise ValueError(f'Grupo incoherente: {group_id}, {column}')
        first = images.iloc[0]
        density_column = 'num_plants_seeded_2025' if int(first.year) == 2025 else 'num_plants_nominal_2026'
        if images[density_column].nunique(dropna=False) != 1 or pd.isna(first[density_column]):
            raise ValueError(f'Densidad nominal no unívoca: {group_id}')
        eligible = images.use_in_initial_partition & ~images.exclude_from_primary_training
        if not eligible.any():
            raise ValueError(f'Grupo sin imagen apta para ningún conjunto: {group_id}')
        groups.append(dict(split_group_id=group_id, pot_id=first.pot_id, year=int(first.year), campana=first.campana,
            repeticion=first.repeticion, posicion=first.posicion, species_code=first.species_code,
            density_count=int(first[density_column]), density_source=density_column,
            initial_eligible_images=int(eligible.sum()), split_assignment=None, validation_role=None))
    groups = pd.DataFrame(groups)
    groups.loc[groups.species_code.eq('M'), 'split_assignment'] = 'M_aux'
    strata = ['year', 'campana', 'repeticion', 'species_code', 'density_count']
    # Reserva generativa estratificada; 20 % con redondeo entero al más próximo.
    for _, group in groups[groups.species_code.eq('P')].groupby(strata, sort=True):
        ordered = sorted(group.index, key=lambda i: stable_order(groups.loc[i, 'split_group_id'], 'G_fit'))
        reserve = int(len(ordered) * 0.20 + 0.5)
        if reserve < 1 or len(ordered) - reserve < 3:
            raise ValueError('El estrato no admite reserva generativa y tres funciones de clasificador')
        groups.loc[ordered[:reserve], 'split_assignment'] = 'G_fit'
    for _, group in groups[groups.split_assignment.isna()].groupby(strata, sort=True):
        ordered = sorted(group.index, key=lambda i: stable_order(groups.loc[i, 'split_group_id'], 'classifier'))
        counts = allocation(len(ordered), [('C_fit', 70), ('C_val', 15), ('T_real', 15)])
        if min(counts.values()) < 1:
            raise ValueError('Un estrato quedaría ausente de una función de clasificación')
        cursor = 0
        for role, count in counts.items():
            groups.loc[ordered[cursor:cursor+count], 'split_assignment'] = role
            cursor += count
    # Dos reservas distintas dentro de C_val, equilibradas por clase/año/campaña.
    for _, group in groups[groups.split_assignment.eq('C_val')].groupby(['species_code', 'year', 'campana'], sort=True):
        ordered = sorted(group.index, key=lambda i: stable_order(groups.loc[i, 'split_group_id'], 'C_val_roles'))
        n_model = (len(ordered) + 1) // 2
        if n_model == len(ordered):
            raise ValueError('No caben dos reservas C_val para esa especie/año')
        groups.loc[ordered[:n_model], 'validation_role'] = 'model_selection'
        groups.loc[ordered[n_model:], 'validation_role'] = 'threshold_calibration'
    if groups.split_assignment.isna().any() or groups.split_group_id.duplicated().any():
        raise ValueError('Asignación incompleta o ambigua')
    expected = {'C_fit', 'C_val', 'G_fit', 'T_real', 'M_aux'}
    if set(groups.split_assignment) != expected:
        raise ValueError('Faltan funciones del diseño')
    plan_path = root / 'exp_design/08_partition_plan_v1.json'
    assignments_path = root / 'exp_design/07_partition_assignments_v1.csv'
    if plan_path.exists() or assignments_path.exists():
        raise FileExistsError('v1 ya existe: no se reasigna ni sobrescribe; documentar una migración/versionado si fuera necesario')
    plan = dict(version=VERSION, seed=SEED, created_utc=datetime.now(timezone.utc).isoformat(),
        status='frozen_initial_assignment', methodology_entry='M024', input_manifest_fingerprint=fingerprint,
        fingerprint_fields=list(FINGERPRINT_FIELDS), unit='split_group_id_same_pot_all_dates_and_cameras',
        strata=strata, density_note='2025 sembradas; 2026 nominales; no recuentos observados por foto',
        G_fit_fraction_of_palmeri_groups=0.20, classifier_weights={'C_fit': 70, 'C_val': 15, 'T_real': 15},
        C_val_functions={'model_selection': 0.5, 'threshold_calibration': 0.5},
        algorithm='SHA256(seed|phase|group_id) sort; G_fit nearest integer; classifier largest remainder, ties C_fit/C_val/T_real; C_val halves by class/year/campaign',
        no_outcomes_or_pixels_used=True, excluded_acquisition='2025-06-20_c1_r2/nikon_d70',
        group_counts=groups.split_assignment.value_counts().to_dict(),
        group_counts_by_species=groups.groupby(['split_assignment', 'species_code']).size().reset_index(name='groups').to_dict('records'),
        limitations=['Holdout within represented campaigns/repetitions, not an external campaign evaluation.',
            'Cross-repetition independence relies on available grouping; no undocumented transplant links inferred.',
            'Small validation/calibration samples limit precision; no minimum performance is guaranteed.',
            'Bad images and incomplete Nikon acquisition inherit group role but are not emitted in active sets.'])
    groups.to_csv(assignments_path, index=False, encoding='utf-8-sig')
    plan['assignments_sha256'] = hashlib.sha256(assignments_path.read_bytes()).hexdigest()
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: plan[k] for k in ('version', 'seed', 'group_counts', 'group_counts_by_species')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    run(Path(__file__).resolve().parents[1])
