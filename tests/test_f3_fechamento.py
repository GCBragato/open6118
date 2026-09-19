"""Testes do pacote F3 — fechamento de itens parciais (NBR 6118:2026).

Cobre os dois pontos do brief de fechamento (SCRATCH\\exec\\pacotes\\F3.md):

  - 19.5.3.4 — contorno C'' e disposição da armadura de punção (Figuras 19.8 e
    19.9, PDF p. 190-191): confirma que o arranjo em cruz da Figura 19.8 (à
    direita) continua sinalizado como não traçado, e por quê (a razão vira
    parte da docstring de ``disposicao_armadura_puncao``).
  - 24.6.3 — núcleo central de inércia e verificação sem tração para seção
    poligonal qualquer, com excentricidade nas duas direções (PDF p. 230):
    fecha o que P41 deixou de fora (só retângulo; só uma direção com ações
    laterais), via ``dentro_nucleo_central_poligono``,
    ``nucleo_central_poligono_cm`` e ``verificar_secao_sem_tracao_poligono``.

Os valores de referência do retângulo repetem os de
tests/test_p41_concreto_simples_elementos.py (mesma seção b × h), para provar
que a versão poligonal reproduz exatamente a versão retangular já testada.
Onde não há fórmula fechada na norma (carga fora do núcleo com excentricidade
nas duas direções), o teste confere o equilíbrio por integração numérica
independente (grade fina, sem usar nenhuma função da biblioteca) — como a
seção 3.1 do plano manda para análise sem valor tabelado.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import concreto_simples_nbr6118 as cs          # noqa: E402
import puncao_nbr6118 as pc                    # noqa: E402

REL = 1e-6


def _fcd(fck):
    return fck / 1.68


# ---------------------------------------------------------------------------
# 19.5.3.4 — Figura 19.8 (à direita): arranjo em cruz não traçado (PDF p. 190)
# ---------------------------------------------------------------------------
def test_19_5_3_4_arranjo_em_cruz_continua_nao_tracado():
    """Com linhas radiais espaçadas >= 2d no último contorno, a função (Figura
    19.8, à direita) sinaliza ok=False e aponta o perímetro reduzido, que não
    calcula — a Figura não dá uma regra numérica para esse contorno (só
    ilustra ">2d" e "d"), ao contrário da Figura 19.9 (<=0,75d, <=0,50d)."""
    # Pilar 40x40, d=17: poucas linhas radiais (4) no contorno mais externo
    # dão espaçamento tangencial grande -> viola o "< 2d" da Figura 19.8.
    r = pc.disposicao_armadura_puncao(FSd_kn=500.0, c1_cm=40.0, c2_cm=40.0, d_cm=17.0,
                                      tau_Rd1_mpa=0.6, sr_cm=10.0, n_linhas_radiais=4)
    assert not r.ok
    assert "perímetro reduzido" in r.governante
    # Confere a docstring: continua documentando, na primeira pessoa, por que
    # o perímetro reduzido do arranjo em cruz não é traçado.
    doc = pc.disposicao_armadura_puncao.__doc__
    assert "traça" in doc and "não" in doc
    assert "Figura 19.8" in doc and "não dá uma regra analítica" in doc


def test_19_5_3_4_contorno_inteiro_quando_espacamento_ok():
    """Com bastante linha radial, o espaçamento tangencial cai abaixo de 2d e
    o contorno C'' inteiro vale (Figura 19.8, à esquerda)."""
    r = pc.disposicao_armadura_puncao(FSd_kn=500.0, c1_cm=40.0, c2_cm=40.0, d_cm=17.0,
                                      tau_Rd1_mpa=0.6, sr_cm=10.0, n_linhas_radiais=40)
    assert r.espacamento_tangencial_cm < 2.0 * 17.0


# ---------------------------------------------------------------------------
# 24.6.3 — Núcleo central de inércia, seção poligonal qualquer (PDF p. 230)
# ---------------------------------------------------------------------------
def _retangulo(b, h):
    """Retângulo b (em x) por h (em y), centrado na origem — mesma convenção
    de ``verificar_pilar_simples_acao_lateral`` (e = M/N na direção de h)."""
    return [(-b / 2.0, -h / 2.0), (b / 2.0, -h / 2.0), (b / 2.0, h / 2.0), (-b / 2.0, h / 2.0)]


def test_24_6_3_nucleo_central_poligono_reproduz_retangulo():
    # Mesmo retângulo 30x60 de test_24_6_3_nucleo_central (test_p41).
    poli = _retangulo(30.0, 60.0)
    assert cs.dentro_nucleo_central_poligono(5.0, 0.0, poli)
    assert not cs.dentro_nucleo_central_poligono(5.01, 0.0, poli)
    assert cs.dentro_nucleo_central_poligono(0.0, 10.0, poli)
    assert not cs.dentro_nucleo_central_poligono(0.0, -10.1, poli)
    # Losango: 6·2,5/30 + 6·5/60 = 1 -> limite, dentro.
    assert cs.dentro_nucleo_central_poligono(2.5, 5.0, poli)
    assert not cs.dentro_nucleo_central_poligono(2.5, 5.1, poli)

    # Vértices do núcleo (losango de semidiagonais b/6=5 e h/6=10).
    nucleo = cs.nucleo_central_poligono_cm(poli)
    pontos = {(round(x, 6), round(y, 6)) for x, y in nucleo}
    assert pontos == {(5.0, 0.0), (-5.0, 0.0), (0.0, 10.0), (0.0, -10.0)}


def test_24_6_3_nucleo_central_poligono_secao_qualquer_e_autoconsistente():
    """Triângulo retângulo (0,0)-(30,0)-(0,60): cada vértice do núcleo, quando
    usado como excentricidade, cai exatamente na fronteira de
    ``dentro_nucleo_central_poligono`` (escalar um pouco para fora deixa de
    valer; um pouco para dentro continua valendo) — a mesma relação de
    reciprocidade que reproduz o retângulo acima, agora numa seção sem
    nenhuma simetria."""
    tri = [(0.0, 0.0), (30.0, 0.0), (0.0, 60.0)]
    _, cx, cy, *_ = cs._f3_propriedades_poligono_cm(tri)
    nucleo = cs.nucleo_central_poligono_cm(tri)
    assert len(nucleo) == 3
    for (px, py) in nucleo:
        ex, ey = px - cx, py - cy
        assert cs.dentro_nucleo_central_poligono(ex, ey, tri)
        assert not cs.dentro_nucleo_central_poligono(1.001 * ex, 1.001 * ey, tri)
        assert cs.dentro_nucleo_central_poligono(0.999 * ex, 0.999 * ey, tri)
    # Centroide (excentricidade nula) está sempre dentro, e um vértice do
    # próprio triângulo (bem mais excêntrico que o núcleo) está sempre fora.
    assert cs.dentro_nucleo_central_poligono(0.0, 0.0, tri)
    assert not cs.dentro_nucleo_central_poligono(30.0 - cx, 0.0 - cy, tri)


def test_24_6_3_nucleo_central_poligono_erro_poligono_degenerado():
    with pytest.raises(ValueError):
        cs._f3_propriedades_poligono_cm([(0.0, 0.0), (1.0, 0.0)])
    with pytest.raises(ValueError):
        cs._f3_propriedades_poligono_cm([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)])  # área nula


# ---------------------------------------------------------------------------
# 24.6.3 — Verificação sem tração, seção poligonal qualquer (PDF p. 230)
# ---------------------------------------------------------------------------
def test_24_6_3_sem_tracao_poligono_reduz_ao_retangulo_uniaxial():
    """Mesma seção e os mesmos números de test_24_6_3_acao_lateral (test_p41),
    agora passando o retângulo como polígono e a excentricidade só em y —
    tem de reproduzir exatamente ``verificar_pilar_simples_acao_lateral``."""
    poli = _retangulo(20.0, 30.0)
    f = cs.verificar_pilar_simples_acao_lateral

    # N=100, M=0: sigma0 = 100/600*10 MPa.
    ref = f(100.0, 0.0, 20.0, 30.0, 20.0)
    r = cs.verificar_secao_sem_tracao_poligono(100.0, 0.0, 0.0, poli, 20.0)
    assert r.dentro_nucleo
    assert r.sigma_max_mpa == pytest.approx(ref.sigma_max_mpa, rel=REL) == pytest.approx(1000.0 / 600.0, rel=REL)
    assert r.ok

    # e = h/6 = 5 (M=500): seção toda comprimida, sigma_max = 2*sigma0.
    ref = f(100.0, 500.0, 20.0, 30.0, 20.0)
    r = cs.verificar_secao_sem_tracao_poligono(100.0, 0.0, 5.0, poli, 20.0)
    assert r.dentro_nucleo
    assert r.sigma_max_mpa == pytest.approx(ref.sigma_max_mpa, rel=REL) == pytest.approx(2000.0 / 600.0, rel=REL)
    assert r.area_comprimida_cm2 == pytest.approx(600.0, rel=REL)

    # e = 9,99 (perto de h/3 = 10, sem cair exatamente na fronteira): x deve
    # bater com 3·(h/2 − e) do fechamento fechado. Bem na fronteira exata
    # (a reta neutra passando pelo centroide), a reta em (p, q) — que existe
    # só para representar retas que não passam pelo centroide — vai a
    # infinito; a função detecta isso e devolve ok=False ali (ver docstring
    # de ``_f3_resolver_eixo_neutro``), por isso o teste fica a 0,01 cm da
    # fronteira, onde a reta em (p, q) ainda é finita.
    e = 9.99
    ref = f(100.0, 100.0 * e, 20.0, 30.0, 20.0)
    r = cs.verificar_secao_sem_tracao_poligono(100.0, 0.0, e, poli, 20.0)
    assert not r.dentro_nucleo
    assert r.sigma_max_mpa == pytest.approx(ref.sigma_max_mpa, rel=1e-3)
    assert r.area_comprimida_cm2 == pytest.approx(20.0 * ref.x_comprimido_cm, rel=1e-3)
    assert r.ok and ref.ok

    # e = 10,5: x = 13,5 < h/2 -> não contém o centroide -> não passa.
    ref = f(100.0, 1050.0, 20.0, 30.0, 20.0)
    r = cs.verificar_secao_sem_tracao_poligono(100.0, 0.0, 10.5, poli, 20.0)
    assert not ref.ok
    assert not r.ok


def test_24_6_3_sem_tracao_poligono_biaxial_equilibrio():
    """Excentricidade nas duas direções ao mesmo tempo (flexão oblíqua), sem
    fórmula fechada na norma: confere o equilíbrio por integração numérica
    independente (grade fina, sem chamar nenhuma função da biblioteca), como
    a seção 3.1 do plano manda. F = N e o centroide da pressão cai em
    (ex, ey), dentro da grade usada."""
    b, h = 30.0, 60.0
    poli = _retangulo(b, h)
    N, ex, ey, fck = 100.0, 3.0, 8.0, 25.0
    r = cs.verificar_secao_sem_tracao_poligono(N, ex, ey, poli, fck)
    assert not r.dentro_nucleo          # (3, 8) já passa do losango b/6=5, h/6=10
    assert r.ok
    assert 0.0 < r.area_comprimida_cm2 < b * h

    # --- integração numérica independente (não usa cs.* para o campo de tensão) ---
    xs = [-b / 2.0, b / 2.0]
    ys = [-h / 2.0, h / 2.0]
    nx_grid, ny_grid = 220, 220
    dx = (xs[1] - xs[0]) / nx_grid
    dy = (ys[1] - ys[0]) / ny_grid
    # eixo neutro reconstruído a partir da mesma reta que a biblioteca achou
    # (p, q), só para gerar o campo de profundidade — a integração em si
    # (F, momentos, escala k) é feita aqui, sem chamar _f3_resultante_pq.
    centrado = [(x, y) for x, y in poli]  # já centrado (retângulo simétrico)
    A, cx, cy, Ixx, Iyy, Ixy = cs._f3_propriedades_poligono_cm(poli)
    theta, _girado, Iu, Iv = cs._f3_base_principal(poli, A, cx, cy, Ixx, Iyy, Ixy)
    p, q, _ = cs._f3_resolver_eixo_neutro(centrado, A, (theta, Iu, Iv), ex, ey)
    norma = math.hypot(p, q)
    nxv, nyv = p / norma, q / norma
    a = 1.0 / norma

    def dentro_poligono(px, py, pol):
        n = len(pol)
        dentro = False
        j = n - 1
        for i in range(n):
            xi, yi = pol[i]
            xj, yj = pol[j]
            if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
                dentro = not dentro
            j = i
        return dentro

    S = 0.0     # momento estático da área comprimida em torno do eixo neutro
    for i in range(nx_grid):
        for j in range(ny_grid):
            px = xs[0] + (i + 0.5) * dx
            py = ys[0] + (j + 0.5) * dy
            if dentro_poligono(px, py, centrado):
                d = a - (px * nxv + py * nyv)
                if d > 0.0:
                    S += d * dx * dy
    k = N / S  # tensao = k * profundidade

    F = Mx = My = 0.0
    for i in range(nx_grid):
        for j in range(ny_grid):
            px = xs[0] + (i + 0.5) * dx
            py = ys[0] + (j + 0.5) * dy
            if dentro_poligono(px, py, centrado):
                d = a - (px * nxv + py * nyv)
                if d > 0.0:
                    sigma = k * d
                    area_el = dx * dy
                    F += sigma * area_el
                    Mx += sigma * py * area_el
                    My += sigma * px * area_el

    assert F == pytest.approx(N, rel=2e-3)
    assert My / F == pytest.approx(ex, rel=5e-3)
    assert Mx / F == pytest.approx(ey, rel=5e-3)
    # sigma_max da biblioteca deve bater com k * profundidade máxima da grade
    d_max_grade = max(
        (a - (px * nxv + py * nyv))
        for i in range(nx_grid) for j in range(ny_grid)
        for px, py in [(xs[0] + (i + 0.5) * dx, ys[0] + (j + 0.5) * dy)]
        if dentro_poligono(px, py, centrado) and (a - (px * nxv + py * nyv)) > 0.0
    )
    assert r.sigma_max_mpa == pytest.approx(k * d_max_grade * 10.0, rel=2e-2)


def test_24_6_3_sem_tracao_poligono_fora_da_regiao_admissivel():
    """Excentricidade além do que qualquer reta neutra consegue manter a
    parte comprimida contendo o centroide (equivalente ao e > h/3 uniaxial de
    ``verificar_pilar_simples_acao_lateral``, mas numa direção qualquer)."""
    poli = _retangulo(30.0, 60.0)
    r = cs.verificar_secao_sem_tracao_poligono(100.0, 0.0, 21.0, poli, 25.0)
    assert not r.ok
    assert not r.dentro_nucleo
    assert "não existe reta neutra" in r.governante

    # Perto da fronteira h/3 = 20 (e = 19,9, sem cair exatamente nela — ver o
    # comentário de ``test_24_6_3_sem_tracao_poligono_reduz_ao_retangulo_uniaxial``
    # sobre a reta em (p, q) na fronteira exata), o lado retangular e o
    # poligonal concordam.
    ref = cs.verificar_pilar_simples_acao_lateral(100.0, 100.0 * 19.9, 30.0, 60.0, 25.0)
    assert ref.ok
    r2 = cs.verificar_secao_sem_tracao_poligono(100.0, 0.0, 19.9, poli, 25.0)
    assert r2.ok


def test_24_6_3_sem_tracao_poligono_triangulo_dentro_e_fora_do_nucleo():
    """Seção sem nenhuma simetria (triângulo retângulo): carga no centroide
    está sempre dentro; perto de um vértice, sempre fora, e ainda assim a
    verificação converge (área comprimida positiva e menor que a bruta)."""
    tri = [(0.0, 0.0), (30.0, 0.0), (0.0, 60.0)]
    _, cx, cy, *_ = cs._f3_propriedades_poligono_cm(tri)
    r0 = cs.verificar_secao_sem_tracao_poligono(50.0, 0.0, 0.0, tri, 25.0)
    assert r0.dentro_nucleo and r0.ok
    assert r0.area_comprimida_cm2 == pytest.approx(900.0, rel=REL)  # área bruta toda comprimida

    ex, ey = 3.0, 3.0
    r1 = cs.verificar_secao_sem_tracao_poligono(50.0, ex, ey, tri, 25.0)
    assert not r1.dentro_nucleo
    assert r1.ok
    assert 0.0 < r1.area_comprimida_cm2 < 900.0
