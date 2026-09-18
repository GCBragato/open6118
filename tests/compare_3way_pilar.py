"""Comparacao 3-way: Python vs C++ vs TQS para Pilar.rep.

Para cada pilar/caso/secao, roda razao_dc_radial em ambos backends
(Python e C++) e compara contra TQS_SDRD. Mede tempo de cada backend.

Uso:
    python tests/compare_3way_pilar.py <Pilar.xml> [--out csv] [--max N]
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dimensionamento.rotinas import fco_dispatch as fco
from dimensionamento.rotinas.flexao_composta_obliqua import (
    Aco, Barra, Concreto, SecaoRetangular, armadura_perimetral_retangular,
)

# Reusa parser do compare_tqs_pilar
from tests.compare_tqs_pilar import (
    split_top_columns, parse_pillar_geom, iter_case_blocks_with_sdrd,
    grab, grab_float,
)


def run_compare_3way(xml_path: Path, out_csv: Path | None,
                     max_pillars: int | None = None):
    print(f'[INFO] CPP_AVAILABLE: {fco.CPP_AVAILABLE}')
    if not fco.CPP_AVAILABLE:
        raise RuntimeError("Backend C++ nao disponivel. Rode build.bat antes.")

    print(f'[INFO] Lendo {xml_path}')
    xml = xml_path.read_text(encoding='utf-8', errors='ignore')
    cols = split_top_columns(xml)

    pillars: list[tuple[int, dict, str]] = []
    for cid in sorted(cols):
        g = parse_pillar_geom(cols[cid])
        if g is None or not g['barras']:
            continue
        pillars.append((cid, g, cols[cid]))
        if max_pillars and len(pillars) >= max_pillars:
            break
    print(f'[INFO] {len(pillars)} pilares')

    gama_c = grab_float(xml, 'GMAC_EXC') or 1.4
    gama_s = grab_float(xml, 'GMAS_EXC') or 1.15
    print(f'[INFO] gama_c={gama_c}, gama_s={gama_s}')

    aco = Aco(fyk_mpa=500.0, gama_s=gama_s)
    rows = []
    t_total = time.perf_counter()
    n_eval = 0
    t_py_acc = 0.0
    t_cpp_acc = 0.0

    for cid, g, chunk in pillars:
        concreto = Concreto(fck_mpa=g['fck_mpa'], gama_c=gama_c)
        secao = SecaoRetangular(
            base_cm=g['b_cm'], altura_cm=g['h_cm'],
            cobrimento_cm=g['cobr_cm'], barras=tuple(g['barras']),
        )
        for case_idx, c_chunk in iter_case_blocks_with_sdrd(chunk):
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
                mxd = msdy * 0.1
                myd = msdx * 0.1

                # Python
                t1 = time.perf_counter()
                try:
                    r_py = fco.razao_dc_radial(secao, concreto, aco,
                                                nd_kn, mxd, myd, n_grid=60,
                                                use_cpp=False)
                except Exception as e:
                    r_py = {'status': f'EXC:{type(e).__name__}',
                            'razao_dc': float('nan'), 'lambda': float('nan')}
                t_py = time.perf_counter() - t1
                t_py_acc += t_py

                # C++
                t1 = time.perf_counter()
                try:
                    r_cpp = fco.razao_dc_radial(secao, concreto, aco,
                                                 nd_kn, mxd, myd, n_grid=60,
                                                 use_cpp=True)
                except Exception as e:
                    r_cpp = {'status': f'EXC:{type(e).__name__}',
                             'razao_dc': float('nan'), 'lambda': float('nan')}
                t_cpp = time.perf_counter() - t1
                t_cpp_acc += t_cpp

                n_eval += 1
                dc_py = r_py.get('razao_dc', float('nan'))
                dc_cpp = r_cpp.get('razao_dc', float('nan'))

                rows.append({
                    'pilar_id': cid,
                    'pilar_nome': g['name'],
                    'caso': case_idx,
                    'caso_nome': case_name,
                    'secao': label,
                    'b_cm': g['b_cm'], 'h_cm': g['h_cm'],
                    'fck_mpa': g['fck_mpa'],
                    'as_total_cm2': sum(b.area_cm2 for b in g['barras']),
                    'nd_kn': nd_kn,
                    'mxd_kncm': mxd, 'myd_kncm': myd,
                    'sdrd_tqs': sdrd,
                    'dc_py': dc_py,
                    'dc_cpp': dc_cpp,
                    'lambda_py': r_py.get('lambda', float('nan')),
                    'lambda_cpp': r_cpp.get('lambda', float('nan')),
                    'status_py': r_py.get('status', '?'),
                    'status_cpp': r_cpp.get('status', '?'),
                    'diff_py_tqs': dc_py - sdrd if math.isfinite(dc_py) else float('nan'),
                    'diff_cpp_tqs': dc_cpp - sdrd if math.isfinite(dc_cpp) else float('nan'),
                    'diff_py_cpp': dc_py - dc_cpp if (math.isfinite(dc_py) and math.isfinite(dc_cpp)) else float('nan'),
                    't_py_s': t_py,
                    't_cpp_s': t_cpp,
                })
                if n_eval % 500 == 0:
                    el = time.perf_counter() - t_total
                    print(f'  ... {n_eval} avals (P{cid}, {el:.0f}s, '
                          f'py={t_py_acc:.0f}s cpp={t_cpp_acc:.0f}s)')

    el = time.perf_counter() - t_total
    print(f'\n[INFO] {n_eval} avaliacoes em {el:.1f}s')
    print(f'[INFO] tempo Python total: {t_py_acc:.1f}s ({n_eval/t_py_acc:.1f}/s)')
    print(f'[INFO] tempo C++    total: {t_cpp_acc:.1f}s ({n_eval/t_cpp_acc:.1f}/s)')
    print(f'[INFO] speedup C++ / Python: {t_py_acc/t_cpp_acc:.1f}x')

    # Estatisticas
    print('\n=== Estatisticas ===')
    valid_py = [r for r in rows if math.isfinite(r['diff_py_tqs'])]
    valid_cpp = [r for r in rows if math.isfinite(r['diff_cpp_tqs'])]
    valid_pc = [r for r in rows if math.isfinite(r['diff_py_cpp'])]

    def stats(label, key, src):
        if not src: print(f'{label}: sem dados'); return
        vs = [r[key] for r in src]
        print(f'{label}: n={len(src)}, mean={statistics.mean(vs):+.4f}, '
              f'median={statistics.median(vs):+.4f}, '
              f'max|.|={max(map(abs,vs)):.4f}, stdev={statistics.pstdev(vs):.4f}')

    stats('Python vs TQS  ', 'diff_py_tqs', valid_py)
    stats('C++    vs TQS  ', 'diff_cpp_tqs', valid_cpp)
    stats('Python vs C++  ', 'diff_py_cpp', valid_pc)

    # Concordancia binaria
    def agree(src, key_dc):
        if not src: return 0
        return sum(1 for r in src if (r['sdrd_tqs'] <= 1.0) == (r[key_dc] <= 1.0)) / len(src)
    print(f'\nConcordancia binaria Py vs TQS: {agree(valid_py,"dc_py")*100:.2f}%')
    print(f'Concordancia binaria C++ vs TQS: {agree(valid_cpp,"dc_cpp")*100:.2f}%')

    # Status counters
    print(f'\nStatus Python: {dict(Counter(r["status_py"] for r in rows))}')
    print(f'Status C++:    {dict(Counter(r["status_cpp"] for r in rows))}')

    # Top 5 maior |Py-Cpp| (sanidade)
    if valid_pc:
        print('\nTop 5 maior |dc_py - dc_cpp| (sanidade backend):')
        outs = sorted(valid_pc, key=lambda r: abs(r['diff_py_cpp']), reverse=True)[:5]
        for r in outs:
            print(f"  P{r['pilar_nome']:<4} c{r['caso']:>2} {r['secao']:<6} "
                  f"py={r['dc_py']:>7.4f} cpp={r['dc_cpp']:>7.4f} "
                  f"diff={r['diff_py_cpp']:+.4f}")

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
    p.add_argument('--out', type=Path, default=Path('/tmp/pilar_rep/comparacao_3way.csv'))
    p.add_argument('--max', type=int, default=None)
    args = p.parse_args(argv)
    run_compare_3way(args.xml, args.out, max_pillars=args.max)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
