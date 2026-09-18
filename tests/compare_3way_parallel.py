"""Comparacao 3-way paralela: Python vs C++ vs TQS, multiprocessing.

Pre-extrai todos os casos do XML, depois distribui em workers.
Cada worker calcula razao_dc_radial em ambos backends para seus
casos atribuidos. Reduce coleta resultados.

Uso:
    python tests/compare_3way_parallel.py <Pilar.xml> [--out csv] [--max N]
                                                       [--workers W]
                                                       [--backend py|cpp|both]
"""

from __future__ import annotations

import argparse
import csv
import math
import multiprocessing as mp
import os
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.compare_tqs_pilar import (
    split_top_columns, parse_pillar_geom, iter_case_blocks_with_sdrd,
    grab, grab_float,
)


def _worker_init(_gama_c, _gama_s):
    """Init de cada worker: importa modulos uma vez."""
    global _Aco_g, _Concreto_g, _SecaoRetangular_g, _Barra_g, _fco_g
    from dimensionamento.rotinas.flexao_composta_obliqua import (
        Aco, Barra, Concreto, SecaoRetangular,
    )
    from dimensionamento.rotinas import fco_dispatch as fco
    _Aco_g = Aco; _Concreto_g = Concreto
    _SecaoRetangular_g = SecaoRetangular; _Barra_g = Barra
    _fco_g = fco
    # Cache gammas por worker
    global _GAMA_C, _GAMA_S
    _GAMA_C, _GAMA_S = _gama_c, _gama_s


def _process_pillar(args):
    """Roda todos os cases de 1 pilar em ambos backends (ou um, conforme flag).

    args = (cid, geom_dict, cases_list, backend)
    cases_list: lista de dicts com keys: caso, secao, nd_kn, mxd, myd, sdrd, caso_nome
    backend: 'py' | 'cpp' | 'both'
    Retorna: list[dict] (rows)
    """
    cid, g, cases, backend = args
    barras = tuple(_Barra_g(b['x_cm'], b['y_cm'], b['area_cm2']) for b in g['barras'])
    secao = _SecaoRetangular_g(g['b_cm'], g['h_cm'], g['cobr_cm'], barras)
    concreto = _Concreto_g(g['fck_mpa'], _GAMA_C)
    aco = _Aco_g(500.0, 21000.0, _GAMA_S)

    rows = []
    for c in cases:
        r_py = r_cpp = None
        t_py = t_cpp = 0.0
        if backend in ('py', 'both'):
            t1 = time.perf_counter()
            try:
                r_py = _fco_g.razao_dc_radial(secao, concreto, aco,
                                              c['nd_kn'], c['mxd'], c['myd'],
                                              n_grid=60, use_cpp=False)
            except Exception as e:
                r_py = {'status': f'EXC:{type(e).__name__}',
                        'razao_dc': float('nan'), 'lambda': float('nan')}
            t_py = time.perf_counter() - t1
        if backend in ('cpp', 'both'):
            t1 = time.perf_counter()
            try:
                r_cpp = _fco_g.razao_dc_radial(secao, concreto, aco,
                                                c['nd_kn'], c['mxd'], c['myd'],
                                                n_grid=60, use_cpp=True)
            except Exception as e:
                r_cpp = {'status': f'EXC:{type(e).__name__}',
                         'razao_dc': float('nan'), 'lambda': float('nan')}
            t_cpp = time.perf_counter() - t1

        dc_py = r_py.get('razao_dc', float('nan')) if r_py else float('nan')
        dc_cpp = r_cpp.get('razao_dc', float('nan')) if r_cpp else float('nan')
        rows.append({
            'pilar_id': cid, 'pilar_nome': g['name'],
            'caso': c['caso'], 'caso_nome': c['caso_nome'], 'secao': c['secao'],
            'b_cm': g['b_cm'], 'h_cm': g['h_cm'], 'fck_mpa': g['fck_mpa'],
            'as_total_cm2': sum(b.area_cm2 for b in barras),
            'nd_kn': c['nd_kn'], 'mxd_kncm': c['mxd'], 'myd_kncm': c['myd'],
            'sdrd_tqs': c['sdrd'],
            'dc_py': dc_py, 'dc_cpp': dc_cpp,
            'lambda_py': r_py.get('lambda', float('nan')) if r_py else float('nan'),
            'lambda_cpp': r_cpp.get('lambda', float('nan')) if r_cpp else float('nan'),
            'status_py': r_py.get('status', '?') if r_py else '?',
            'status_cpp': r_cpp.get('status', '?') if r_cpp else '?',
            'diff_py_tqs': dc_py - c['sdrd'] if math.isfinite(dc_py) else float('nan'),
            'diff_cpp_tqs': dc_cpp - c['sdrd'] if math.isfinite(dc_cpp) else float('nan'),
            'diff_py_cpp': dc_py - dc_cpp if (math.isfinite(dc_py) and math.isfinite(dc_cpp)) else float('nan'),
            't_py_s': t_py, 't_cpp_s': t_cpp,
        })
    return rows


def pre_extract(xml_path: Path, max_pillars: int | None):
    """Le XML e extrai (geom, cases) por pilar, sem chamar FCO ainda."""
    print(f'[INFO] Lendo {xml_path}')
    xml = xml_path.read_text(encoding='utf-8', errors='ignore')
    cols = split_top_columns(xml)

    pillar_jobs = []
    for cid in sorted(cols):
        g = parse_pillar_geom(cols[cid])
        if g is None or not g['barras']:
            continue
        # Geometria serializavel: convert Barra obj para dict (pickle-friendly)
        g_dict = {
            'name': g['name'], 'floor': g['floor'],
            'fck_mpa': g['fck_mpa'], 'b_cm': g['b_cm'], 'h_cm': g['h_cm'],
            'cobr_cm': g['cobr_cm'],
            'barras': [{'x_cm': b.x_cm, 'y_cm': b.y_cm, 'area_cm2': b.area_cm2}
                       for b in g['barras']],
        }
        cases = []
        for case_idx, c_chunk in iter_case_blocks_with_sdrd(cols[cid]):
            nsd = grab_float(c_chunk, 'TOP_NSD')
            if nsd is None:
                continue
            nd_kn = nsd / 1000.0
            case_name = grab(c_chunk, 'CASE_NAME')
            for label in ('TOP', 'BOTTOM'):
                msdx = grab_float(c_chunk, f'{label}_MSDX')
                msdy = grab_float(c_chunk, f'{label}_MSDY')
                sdrd = grab_float(c_chunk, f'{label}_SDRD')
                if msdx is None or msdy is None or sdrd is None:
                    continue
                cases.append({
                    'caso': case_idx, 'caso_nome': case_name, 'secao': label,
                    'nd_kn': nd_kn,
                    'mxd': msdy * 0.1, 'myd': msdx * 0.1,
                    'sdrd': sdrd,
                })
        pillar_jobs.append((cid, g_dict, cases))
        if max_pillars and len(pillar_jobs) >= max_pillars:
            break

    gama_c = grab_float(xml, 'GMAC_EXC') or 1.4
    gama_s = grab_float(xml, 'GMAS_EXC') or 1.15
    return pillar_jobs, gama_c, gama_s


def run_parallel(xml_path: Path, out_csv: Path | None,
                 max_pillars: int | None,
                 workers: int, backend: str):
    pillar_jobs, gama_c, gama_s = pre_extract(xml_path, max_pillars)
    n_pillars = len(pillar_jobs)
    n_cases = sum(len(j[2]) for j in pillar_jobs)
    print(f'[INFO] {n_pillars} pilares, {n_cases} cases totais')
    print(f'[INFO] gama_c={gama_c}, gama_s={gama_s}')
    print(f'[INFO] workers={workers}, backend={backend}')

    args_list = [(cid, g, cases, backend) for cid, g, cases in pillar_jobs]

    t_total = time.perf_counter()
    rows = []
    with mp.Pool(processes=workers,
                 initializer=_worker_init, initargs=(gama_c, gama_s)) as pool:
        # imap_unordered para print de progresso conforme termina
        done = 0
        for r in pool.imap_unordered(_process_pillar, args_list):
            rows.extend(r)
            done += 1
            if done % max(1, n_pillars // 10) == 0:
                el = time.perf_counter() - t_total
                print(f'  ... {done}/{n_pillars} pilares ({el:.0f}s)')

    el = time.perf_counter() - t_total
    n_eval = len(rows)
    print(f'\n[INFO] {n_eval} avaliacoes em {el:.1f}s ({n_eval/el:.1f}/s)')
    if backend == 'both':
        t_py = sum(r['t_py_s'] for r in rows)
        t_cpp = sum(r['t_cpp_s'] for r in rows)
        print(f'[INFO] tempo CPU Python: {t_py:.1f}s')
        print(f'[INFO] tempo CPU C++:    {t_cpp:.1f}s')
        if t_cpp > 0:
            print(f'[INFO] speedup C++/Python (CPU): {t_py/t_cpp:.1f}x')
        print(f'[INFO] speedup vs single-thread: ~{(t_py+t_cpp)/el:.1f}x (incluindo ambos backends)')

    # Estatisticas
    print('\n=== Estatisticas ===')
    valid_py = [r for r in rows if math.isfinite(r['diff_py_tqs'])]
    valid_cpp = [r for r in rows if math.isfinite(r['diff_cpp_tqs'])]
    valid_pc = [r for r in rows if math.isfinite(r['diff_py_cpp'])]

    def stats(label, key, src):
        if not src: return
        vs = [r[key] for r in src]
        print(f'{label}: n={len(src)}, mean={statistics.mean(vs):+.4f}, '
              f'median={statistics.median(vs):+.4f}, '
              f'max|.|={max(map(abs,vs)):.4f}, stdev={statistics.pstdev(vs):.4f}')

    if backend in ('py', 'both'): stats('Python vs TQS  ', 'diff_py_tqs', valid_py)
    if backend in ('cpp', 'both'): stats('C++    vs TQS  ', 'diff_cpp_tqs', valid_cpp)
    if backend == 'both': stats('Python vs C++  ', 'diff_py_cpp', valid_pc)

    def agree(src, key_dc):
        if not src: return 0
        return sum(1 for r in src if (r['sdrd_tqs'] <= 1.0) == (r[key_dc] <= 1.0)) / len(src)
    if backend in ('py', 'both'):
        print(f'\nConcordancia binaria Py vs TQS: {agree(valid_py,"dc_py")*100:.2f}%')
    if backend in ('cpp', 'both'):
        print(f'Concordancia binaria C++ vs TQS: {agree(valid_cpp,"dc_cpp")*100:.2f}%')

    print(f'\nStatus Python: {dict(Counter(r["status_py"] for r in rows))}')
    print(f'Status C++:    {dict(Counter(r["status_cpp"] for r in rows))}')

    if out_csv and rows:
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f'\n[INFO] CSV salvo: {out_csv} ({out_csv.stat().st_size/1024:.1f} KB)')


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('xml', type=Path)
    p.add_argument('--out', type=Path, default=Path('/tmp/pilar_rep/comparacao_3way_par.csv'))
    p.add_argument('--max', type=int, default=None)
    p.add_argument('--workers', type=int, default=os.cpu_count() or 4)
    p.add_argument('--backend', choices=['py', 'cpp', 'both'], default='both')
    args = p.parse_args(argv)
    run_parallel(args.xml, args.out, args.max, args.workers, args.backend)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
