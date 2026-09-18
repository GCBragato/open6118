"""Compara nosso FCO contra relatorio TQS Pilar.rep.

Le `Pilar.xml` (gzip ja descomprimido), itera todos os pilares e cada
INTERNALFORCES_CASE com SDRD presente, roda `verificar_fco` e compara
D/C contra TQS_SDRD.

Uso:
    python tests/compare_tqs_pilar.py <Pilar.xml> [--out csv] [--max N]
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

from dimensionamento.rotinas.flexao_composta_obliqua import (
    Aco,
    Barra,
    Concreto,
    SecaoRetangular,
    armadura_perimetral_retangular,
    razao_dc_radial,
    verificar_fco,
)


def split_top_columns(xml: str) -> dict[int, str]:
    """Divide o XML em chunks por COLUMN[i].

    Como nao ha aninhamento entre COLUMNs, cada chunk corresponde a 1 pilar.
    """
    parts = re.split(r'(<a:Key>COLUMN\[\d+\]</a:Key>)', xml)
    out: dict[int, str] = {}
    for i in range(1, len(parts), 2):
        cid = int(re.search(r'COLUMN\[(\d+)\]', parts[i]).group(1))
        body = parts[i + 1] if i + 1 < len(parts) else ''
        out[cid] = body
    return out


def grab(chunk: str, key: str) -> str | None:
    m = re.search(
        r'<a:Key>' + re.escape(key) + r'</a:Key><a:Value[^>]*>([^<]*)</a:Value>',
        chunk,
    )
    return m.group(1) if m else None


def grab_float(chunk: str, key: str) -> float | None:
    v = grab(chunk, key)
    if v is None or v == '':
        return None
    try:
        return float(v)
    except ValueError:
        return None


def grab_all_floats(chunk: str, key: str) -> list[float]:
    vs = re.findall(
        r'<a:Key>' + re.escape(key) + r'</a:Key><a:Value[^>]*>([^<]*)</a:Value>',
        chunk,
    )
    out: list[float] = []
    for v in vs:
        try:
            out.append(float(v))
        except ValueError:
            pass
    return out


def parse_pillar_geom(chunk: str) -> dict | None:
    """Extrai geometria + barras (deduplicadas) do pilar."""
    name = grab(chunk, 'NAME')
    floor = grab(chunk, 'FLOOR_NAME')
    fck = grab_float(chunk, 'FCK')
    sec_b = grab_float(chunk, 'SEC_B')
    sec_h = grab_float(chunk, 'SEC_H')
    cobr = grab_float(chunk, 'COBR')
    n_as = grab_float(chunk, 'N_AS')
    fi_as = grab_float(chunk, 'FI_AS')  # m
    if None in (fck, sec_b, sec_h, cobr):
        return None

    b_cm = sec_b * 100
    h_cm = sec_h * 100
    cobr_cm = cobr * 100

    # ARMD do TQS guarda multiplos layouts alternativos (nao confiavel
    # pra extrair barras 1:1). Reconstroi armadura PERIMETRAL via N_AS
    # e FI_AS reportados (que correspondem ao layout efetivo do pilar).
    barras: list[Barra] = []
    if n_as is not None and fi_as is not None and n_as >= 4 and n_as % 2 == 0:
        # heuristica: nx=2 (face curta), ny = N_AS/2 (face longa).
        # Funciona para 2*(nx+ny)-4 == N_AS quando nx=2.
        n_int = int(round(n_as))
        if h_cm >= b_cm:
            nx, ny = 2, n_int // 2
        else:
            nx, ny = n_int // 2, 2
        if nx >= 2 and ny >= 2:
            try:
                barras = list(armadura_perimetral_retangular(
                    base_cm=b_cm, altura_cm=h_cm, cobrimento_cm=cobr_cm,
                    nx=nx, ny=ny, fi_l_mm=fi_as * 1000.0,
                ))
            except Exception:
                barras = []

    return {
        'name': name,
        'floor': floor,
        'fck_mpa': fck / 1e6,
        'b_cm': b_cm,
        'h_cm': h_cm,
        'cobr_cm': cobr * 100,
        'n_as_tqs': int(n_as) if n_as is not None else None,
        'fi_as_mm': fi_as * 1000 if fi_as is not None else None,
        'as_total_cm2_tqs': grab_float(chunk, 'AS') and grab_float(chunk, 'AS') * 1e4,
        'barras': barras,
    }


def iter_case_blocks_with_sdrd(chunk: str):
    """Itera blocos INTERNALFORCES_CASE[i] que contem TOP_SDRD ou BOTTOM_SDRD.

    Yield: (case_idx, block_str)
    """
    matches = list(re.finditer(
        r'<a:Key>INTERNALFORCES_CASE\[(\d+)\]</a:Key>', chunk
    ))
    for i, m in enumerate(matches):
        idx = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(chunk)
        body = chunk[start:end]
        if 'TOP_SDRD' in body or 'BOTTOM_SDRD' in body:
            yield idx, body


def run_compare(xml_path: Path, out_csv: Path | None, max_pillars: int | None = None):
    print(f'[INFO] Lendo XML: {xml_path}')
    xml = xml_path.read_text(encoding='utf-8', errors='ignore')
    print(f'[INFO] XML em texto: {len(xml)/1e6:.1f} MB')

    cols = split_top_columns(xml)
    pillars: list[tuple[int, dict, str]] = []
    for cid in sorted(cols):
        g = parse_pillar_geom(cols[cid])
        if g is None or not g['barras']:
            continue
        pillars.append((cid, g, cols[cid]))
        if max_pillars and len(pillars) >= max_pillars:
            break
    print(f'[INFO] {len(pillars)} pilares parseados')

    # Coeficientes parciais do TQS no header (GMAC_EXC, GMAS_EXC)
    gama_c_tqs = grab_float(xml, 'GMAC_EXC') or 1.4
    gama_s_tqs = grab_float(xml, 'GMAS_EXC') or 1.15
    print(f'[INFO] gama_c={gama_c_tqs}, gama_s={gama_s_tqs}')

    rows: list[dict] = []
    aco = Aco(fyk_mpa=500.0, gama_s=gama_s_tqs)
    t0 = time.perf_counter()
    n_eval = 0

    for cid, g, chunk in pillars:
        concreto = Concreto(fck_mpa=g['fck_mpa'], gama_c=gama_c_tqs)
        secao = SecaoRetangular(
            base_cm=g['b_cm'],
            altura_cm=g['h_cm'],
            cobrimento_cm=g['cobr_cm'],
            barras=tuple(g['barras']),
        )
        as_calc = sum(b.area_cm2 for b in g['barras'])

        for case_idx, c_chunk in iter_case_blocks_with_sdrd(chunk):
            nsd = grab_float(c_chunk, 'TOP_NSD')  # N
            case_name = grab(c_chunk, 'CASE_NAME')
            if nsd is None:
                continue
            nsd_kn = nsd / 1000.0

            for label in ('TOP', 'BOTTOM'):
                msdx = grab_float(c_chunk, f'{label}_MSDX')  # N.m
                msdy = grab_float(c_chunk, f'{label}_MSDY')
                sdrd_tqs = grab_float(c_chunk, f'{label}_SDRD')
                if sdrd_tqs is None or msdx is None or msdy is None:
                    continue

                # Trocar convencao TQS->nossa:
                # TQS MSDX = momento em torno do eixo X (longitudinal/H)
                #         = causa flexao na direcao transversal (B)
                #         = nosso Myd (em torno do eixo y/altura)
                # TQS MSDY = momento em torno do eixo Y (transversal/B)
                #         = causa flexao na direcao longitudinal (H)
                #         = nosso Mxd (em torno do eixo x/base)
                # N.m -> kN.cm: *0.1
                mxd_kncm = msdy * 0.1
                myd_kncm = msdx * 0.1

                t1 = time.perf_counter()
                try:
                    res = razao_dc_radial(
                        secao, concreto, aco, nsd_kn, mxd_kncm, myd_kncm,
                        n_grid=60,
                    )
                except Exception as e:
                    res = {
                        'status': f'EXC:{type(e).__name__}',
                        'razao_dc': float('nan'),
                        'lambda': float('nan'),
                    }
                dt = time.perf_counter() - t1
                n_eval += 1

                dc_ours = res.get('razao_dc', float('nan'))
                lam = res.get('lambda', float('nan'))
                status = res.get('status', '?')
                # razao "tipo verificar_fco" inverso pra concordancia binaria:
                razao = 1.0 / dc_ours if (
                    isinstance(dc_ours, float) and math.isfinite(dc_ours)
                    and dc_ours > 0
                ) else float('nan')

                if math.isfinite(dc_ours):
                    diff = dc_ours - sdrd_tqs
                    rel = (
                        diff / sdrd_tqs if abs(sdrd_tqs) > 1e-6 else float('nan')
                    )
                else:
                    diff = float('nan')
                    rel = float('nan')

                rows.append({
                    'pilar_id': cid,
                    'pilar_nome': g['name'],
                    'pavto': g['floor'],
                    'b_cm': g['b_cm'],
                    'h_cm': g['h_cm'],
                    'fck_mpa': g['fck_mpa'],
                    'as_total_cm2': as_calc,
                    'as_tqs_cm2': g['as_total_cm2_tqs'],
                    'n_barras': len(g['barras']),
                    'caso': case_idx,
                    'caso_nome': case_name,
                    'secao': label,
                    'nd_kn': nsd_kn,
                    'mxd_kncm': mxd_kncm,
                    'myd_kncm': myd_kncm,
                    'sdrd_tqs': sdrd_tqs,
                    'dc_ours': dc_ours,
                    'lambda_ours': lam,
                    'diff_abs': diff,
                    'diff_rel': rel,
                    'status_ours': status,
                    'razao_ours': razao,
                    'tempo_s': dt,
                })

            if n_eval and n_eval % 500 == 0:
                el = time.perf_counter() - t0
                print(
                    f'  ... {n_eval} avals (P{cid}, {el:.0f}s, '
                    f'{n_eval/el:.1f}/s)'
                )

    el = time.perf_counter() - t0
    print(
        f'\n[INFO] {n_eval} avaliacoes em {el:.1f}s '
        f'({n_eval/el:.1f}/s) -> total {len(rows)} linhas'
    )

    valid = [r for r in rows if math.isfinite(r['diff_abs'])]
    print('\n=== Resumo ===')
    print(f'Total linhas:       {len(rows)}')
    print(f'Validas (numerico): {len(valid)} ({len(valid)/len(rows)*100:.1f}%)')

    st = Counter(r['status_ours'] for r in rows)
    print(f'Status nosso: {dict(st)}')

    if valid:
        diffs = [r['diff_abs'] for r in valid]
        rels = [r['diff_rel'] for r in valid if math.isfinite(r['diff_rel'])]
        print(f'\ndiff_abs (dc_ours - sdrd_tqs):')
        print(f'  mean   = {statistics.mean(diffs):+.4f}')
        print(f'  median = {statistics.median(diffs):+.4f}')
        print(f'  stdev  = {statistics.pstdev(diffs):.4f}')
        print(f'  max|.| = {max(map(abs,diffs)):.4f}')
        if rels:
            print(f'\ndiff_rel:')
            print(f'  mean   = {statistics.mean(rels)*100:+.2f}%')
            print(f'  median = {statistics.median(rels)*100:+.2f}%')
            print(f'  max|.| = {max(map(abs,rels))*100:.2f}%')

        agree = sum(
            1 for r in valid
            if (r['sdrd_tqs'] <= 1.0) == (r['razao_ours'] >= 1.0)
        )
        print(f'\nConcordancia binaria (passa?): {agree}/{len(valid)} '
              f'= {agree/len(valid)*100:.1f}%')

        outliers = sorted(valid, key=lambda r: abs(r['diff_abs']), reverse=True)[:15]
        print('\nTop 15 outliers (|diff_abs|):')
        print(f'{"pil":<5}{"caso":>5}{"sec":>7}'
              f'{"Nd_kN":>9}{"Mxd_kNcm":>11}{"Myd_kNcm":>11}'
              f'{"sdrd_tqs":>10}{"dc_ours":>10}{"diff":>10}')
        for r in outliers:
            print(f'{r["pilar_nome"]:<5}{r["caso"]:>5}{r["secao"]:>7}'
                  f'{r["nd_kn"]:>9.1f}{r["mxd_kncm"]:>11.1f}{r["myd_kncm"]:>11.1f}'
                  f'{r["sdrd_tqs"]:>10.4f}{r["dc_ours"]:>10.4f}{r["diff_abs"]:>+10.4f}')

    if out_csv and rows:
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f'\n[INFO] CSV salvo: {out_csv} ({out_csv.stat().st_size/1024:.1f} KB)')


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('xml', type=Path)
    p.add_argument('--out', type=Path, default=Path('/tmp/pilar_rep/comparacao.csv'))
    p.add_argument('--max', type=int, default=None)
    args = p.parse_args(argv)
    run_compare(args.xml, args.out, max_pillars=args.max)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
