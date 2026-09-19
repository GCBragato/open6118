"""Testes do P45 — Lajes por grelha e pórtico equivalente.

Cobre dimensionamento/analise_lajes_nbr6118.py contra a ABNT NBR 6118:2026:

  - 14.7.3.1 Rigidez do estádio I em placas (M < Mr), p. 116
  - 14.7.7   Laje nervurada como grelha de vigas, p. 118
  - 14.7.7   Laje nervurada unidirecional (sem rigidez transversal e à torção), p. 118
  - 14.7.8   Laje lisa por procedimento numérico (grelha equivalente), p. 118
  - 14.7.8   Pórtico equivalente (pórticos múltiplos, Figura 14.9), p. 118

A análise não tem valor esperado na norma: os valores vêm de soluções
fechadas (placa de Timoshenko pela série de Navier, viga contínua pela
equação dos três momentos, pórtico simétrico pela distribuição de momentos,
grelha de duas vigas cruzadas), com a conta no comentário, e todo resultado
confere o equilíbrio (o P44 levanta erro se não fechar).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import analise_lajes_nbr6118 as an        # noqa: E402
import analise_linear_nbr6118 as al       # noqa: E402
import els_deformacao_nbr6118 as ed       # noqa: E402
import nucleo_nbr6118 as nbr              # noqa: E402

FCK = 30.0
E_KNCM2 = nbr.Ecs(FCK) / 10.0
G_KNCM2 = nbr.Gc(FCK) / 10.0
NU = 0.2


def _rel(a: float, b: float) -> float:
    return abs(a - b) / abs(b)


# =============================================================================
# 14.7.3.1 — rigidez do estádio I (p. 116)
# =============================================================================
def test_estadio_I_abaixo_de_Mr_autoriza_rigidez_bruta():
    # 14.7.3.1: M < Mr → estádio I (Ecs·Ic)
    r = an.verificar_rigidez_estadio_I(249.9, 250.0)
    assert r.ok and r.usar_estadio_I
    assert r.governante.startswith("estádio I")
    assert math.isclose(r.razao, 249.9 / 250.0)
    assert "14.7.3.1" in r.memoria[0]


def test_estadio_I_igual_a_Mr_nao_autoriza():
    # "desde que os momentos fletores sejam menores que o de fissuração":
    # desigualdade estrita; M = Mr já exige a Seção 17
    r = an.verificar_rigidez_estadio_I(250.0, 250.0)
    assert not r.ok and not r.usar_estadio_I
    assert "Seção 17" in r.governante


def test_estadio_I_sequencia_usa_maior_modulo_e_Mr_do_P8():
    # Mr de placa de 12 cm, faixa de 1 cm, fct,m (17.3.1, P8):
    # Mr = 1,5·fct,m·(1·12³/12)/6; momentos da grelha em kN·cm/cm
    Mr = ed.momento_fissuracao_kncm(12.0 ** 3 / 12.0, 6.0, FCK)
    fctm = nbr.fct_m(FCK) / 10.0
    assert math.isclose(Mr, 1.5 * fctm * 144.0 / 6.0)
    r = an.verificar_rigidez_estadio_I([0.5 * Mr, -1.01 * Mr, 0.2 * Mr], Mr)
    assert math.isclose(r.M_max_kncm, 1.01 * Mr)
    assert not r.ok
    r2 = an.verificar_rigidez_estadio_I(np.array([0.3 * Mr, -0.99 * Mr]), Mr)
    assert r2.ok


def test_estadio_I_Mr_invalido():
    with pytest.raises(nbr.FaixaNormativaError):
        an.verificar_rigidez_estadio_I(10.0, 0.0)
    with pytest.raises(ValueError):
        an.verificar_rigidez_estadio_I([], 10.0)


# =============================================================================
# Seção T e largura colaborante da nervura (14.6.2.2 via P14; 14.7.7)
# =============================================================================
def test_secao_T_nervura_propriedades():
    # bw = 10, h = 30, hf = 5, bf = 60:
    # A = 60·5 + 10·25 = 550 cm²; ys = (300·2,5 + 250·17,5)/550 = 9,31818 cm
    # I = 60·5³/12 + 300·(ys − 2,5)² + 10·25³/12 + 250·(ys − 17,5)²
    s = an.secao_T_nervura(10, 30, 5, 60)
    ys = (300 * 2.5 + 250 * 17.5) / 550
    I = 60 * 125 / 12 + 300 * (ys - 2.5) ** 2 + 10 * 25 ** 3 / 12 + 250 * (ys - 17.5) ** 2
    assert math.isclose(s.A_cm2, 550.0)
    assert math.isclose(s.ys_cm, ys)
    assert math.isclose(s.yt_cm, 30 - ys)
    assert math.isclose(s.I_cm4, I)
    assert math.isclose(s.secao.I_cm4, I)
    # J = retângulo 10×30 + aba 50×5, cada um β·a·b³
    def J(a, b):
        a, b = max(a, b), min(a, b)
        r = b / a
        return (1 / 3 - 0.21 * r * (1 - r ** 4 / 12)) * a * b ** 3
    assert math.isclose(s.J_cm4, J(10, 30) + J(50, 5))


def test_secao_T_nervura_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        an.secao_T_nervura(10, 30, 30, 60)       # hf = h
    with pytest.raises(nbr.FaixaNormativaError):
        an.secao_T_nervura(10, 30, 5, 8)         # bf < bw
    with pytest.raises(nbr.FaixaNormativaError):
        an.secao_T_nervura(0, 30, 5, 60)


def test_largura_colaborante_nervura_usa_P14():
    # e = 60, bw = 10 → b2 = 50; b1 = b3 = min(0,5·50; 0,1·a)
    # a = 600: min(25; 60) = 25 → bf = 60 (o espaçamento governa)
    assert math.isclose(an.largura_colaborante_nervura_cm(10, 60, 600), 60.0)
    # a = 150: min(25; 15) = 15 → bf = 40 (0,1·a governa)
    assert math.isclose(an.largura_colaborante_nervura_cm(10, 60, 150), 40.0)
    assert math.isclose(an.largura_colaborante_nervura_cm(10, 60, 150),
                        al.largura_colaborante_cm(10, 50, 50, 150))
    # borda livre: seção L, b3 = 0
    assert math.isclose(an.largura_colaborante_nervura_cm(10, 60, 600, borda=True), 35.0)
    with pytest.raises(nbr.FaixaNormativaError):
        an.largura_colaborante_nervura_cm(10, 10, 600)


# =============================================================================
# 14.7.7 — nervurada unidirecional (p. 118): igual à viga contínua
# =============================================================================
def test_unidirecional_dois_vaos_igual_viga_continua():
    # q = 6 kN/m², e = 50 cm → q·e = 3 kN/m por nervura; L = 400 cm.
    # Viga contínua de dois vãos iguais, EI constante (bf = 50 nos dois vãos
    # extremos, a = 0,75·L): M apoio = −q·L²/8 = −3·4²/8 = −6 kN·m = −600 kN·cm;
    # M+ máx = 9/128·q·L² = 337,5 kN·cm; reações 3/8·qL, 10/8·qL, 3/8·qL.
    r = an.nervurada_unidirecional([400, 400], 50, 10, 25, 5, FCK, 6.0)
    q, L = 3.0, 4.0
    assert math.isclose(r.carga_nervura_kn_m, q)
    assert math.isclose(r.M_apoios_kncm[1], -q * L ** 2 / 8 * 100, rel_tol=1e-9)
    assert abs(r.M_apoios_kncm[0]) < 1e-9 and abs(r.M_apoios_kncm[2]) < 1e-9
    for m in r.M_vao_max_kncm:
        assert math.isclose(m, 9 / 128 * q * L ** 2 * 100, rel_tol=1e-9)
    esp = (3 / 8 * q * L, 10 / 8 * q * L, 3 / 8 * q * L)
    for a, b in zip(r.reacoes_kn, esp):
        assert math.isclose(a, b, rel_tol=1e-9)
    # por metro: M/e = −6 kN·m / 0,5 m = −12 kN·m/m
    assert math.isclose(r.m_apoios_knm_por_m[1], -12.0, rel_tol=1e-9)
    # a = 0,75·400 = 300 → b1 = min(20; 30) = 20 → bf = 50
    assert all(math.isclose(s.bf_cm, 50.0) for s in r.secoes)
    assert "14.7.7" in r.memoria[0]


def test_unidirecional_tres_vaos_e_engastes():
    # três vãos iguais, EI constante (bf = e em todos): M apoios internos
    # = −q·L²/10 (três momentos)
    r = an.nervurada_unidirecional([500, 500, 500], 50, 10, 25, 5, FCK, 4.0)
    q, L = 2.0, 5.0
    assert all(math.isclose(s.bf_cm, 50.0) for s in r.secoes)
    assert math.isclose(r.M_apoios_kncm[1], -q * L ** 2 / 10 * 100, rel_tol=1e-9)
    assert math.isclose(r.M_apoios_kncm[2], -q * L ** 2 / 10 * 100, rel_tol=1e-9)
    # vão biengastado: −q·L²/12 nos apoios e +q·L²/24 no meio
    r2 = an.nervurada_unidirecional([500], 50, 10, 25, 5, FCK, 4.0,
                                    engaste_inicio=True, engaste_fim=True)
    assert math.isclose(r2.M_apoios_kncm[0], -q * L ** 2 / 12 * 100, rel_tol=1e-9)
    assert math.isclose(r2.M_apoios_kncm[1], -q * L ** 2 / 12 * 100, rel_tol=1e-9)
    assert math.isclose(r2.M_vao_max_kncm[0], q * L ** 2 / 24 * 100, rel_tol=1e-9)


def test_unidirecional_sem_ligacao_transversal_nem_torcao():
    # o modelo é pórtico plano (sem grau de torção nem barras transversais)
    r = an.nervurada_unidirecional([400, 400], 50, 10, 25, 5, FCK, 6.0)
    assert r.modelo.tipo == "portico_plano"
    assert len(r.modelo.barras) == 2


def test_unidirecional_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        an.nervurada_unidirecional([], 50, 10, 25, 5, FCK, 6.0)
    with pytest.raises(nbr.FaixaNormativaError):
        an.nervurada_unidirecional([400, -1], 50, 10, 25, 5, FCK, 6.0)
    with pytest.raises(nbr.FaixaNormativaError):
        an.nervurada_unidirecional([400], 50, 10, 25, 5, FCK, -1.0)


# =============================================================================
# 14.7.7 — nervurada como grelha de vigas (p. 118)
# =============================================================================
def test_grelha_nervurada_duas_nervuras_cruzadas_solucao_fechada():
    # ex = ey = L/2 → uma nervura em cada direção, cruzando no centro.
    # Carga no nó central: P = q·(L/2)² (área de influência); os nós de
    # borda vão direto aos apoios. Sem torção (fator 0) e painel quadrado:
    # cada nervura leva P/2 → w = (P/2)·L³/(48·E·I); M = (P/2)·L/4.
    L, q = 600.0, 8.0
    r = an.grelha_nervurada(L, L, L / 2, L / 2, 12, 30, 5, FCK, q, fator_torcao=0.0)
    P = q / 1e4 * (L / 2) ** 2
    bf = an.largura_colaborante_nervura_cm(12, L / 2, L)       # b1 = min(144; 60) → bf = 132
    assert math.isclose(bf, 132.0)
    I = an.secao_T_nervura(12, 30, 5, bf).I_cm4
    assert math.isclose(r.deslocamento_cm(L / 2, L / 2), -(P / 2) * L ** 3 / (48 * E_KNCM2 * I),
                        rel_tol=1e-9)
    assert math.isclose(r.M_x_pos_kncm, (P / 2) * L / 4, rel_tol=1e-9)
    assert math.isclose(r.M_y_pos_kncm, (P / 2) * L / 4, rel_tol=1e-9)
    assert math.isclose(r.carga_total_kn, q * (L / 100) ** 2, rel_tol=1e-12)


def test_grelha_nervurada_equilibrio_e_classificacao():
    # 13.2.4.2 (P10): e = 60 → categoria a; e = 120 → categoria c, capa como
    # laje maciça apoiada na grelha
    r = an.grelha_nervurada(600, 480, 60, 60, 10, 30, 5, FCK, 8.0)
    soma = sum(v["uz"] for v in r.analise.reacoes.values())
    assert math.isclose(soma, r.carga_total_kn, rel_tol=1e-9)
    assert math.isclose(r.carga_total_kn, 8.0 * 6.0 * 4.8, rel_tol=1e-12)
    assert "categoria a" in r.governante
    assert r.M_x_pos_kncm > 0 and r.M_y_pos_kncm > 0
    # painel 6 × 4,8 m: a direção curta (Y) é mais rígida e leva mais momento por nervura
    assert r.M_y_pos_kncm > r.M_x_pos_kncm
    r2 = an.grelha_nervurada(600, 600, 120, 120, 12, 35, 6, FCK, 8.0)
    assert "categoria c" in r2.governante
    assert any("laje maciça apoiada" in m for m in r2.memoria)


def test_grelha_nervurada_torcao_padrao_14_6_6_2():
    # o padrão é 0,15·GJ (14.6.6.2); com torção, a flecha diminui
    r15 = an.grelha_nervurada(600, 600, 60, 60, 10, 30, 5, FCK, 8.0)
    r0 = an.grelha_nervurada(600, 600, 60, 60, 10, 30, 5, FCK, 8.0, fator_torcao=0.0)
    r100 = an.grelha_nervurada(600, 600, 60, 60, 10, 30, 5, FCK, 8.0, fator_torcao=1.0)
    b = next(iter(r15.modelo.barras.values()))
    assert math.isclose(b.fator_GJ, 0.15)
    assert r100.w_max_cm < r15.w_max_cm < r0.w_max_cm


def test_grelha_nervurada_bordas_engaste_e_livre():
    # engaste em x0 gera momento negativo nas nervuras paralelas a X
    r = an.grelha_nervurada(600, 600, 60, 60, 10, 30, 5, FCK, 8.0, bordas={"x0": "engaste"})
    assert r.M_x_neg_kncm < -1.0
    # borda livre em y1: nervura de borda com seção L (bf = bw + 25)
    r2 = an.grelha_nervurada(600, 600, 60, 60, 10, 30, 5, FCK, 8.0, bordas={"y1": "livre"})
    assert ("x", 0, 10) in r2.modelo.barras
    bL = r2.modelo.barras[("x", 0, 10)]
    assert math.isclose(bL.secao.A_cm2, an.secao_T_nervura(10, 30, 5, 35).A_cm2)
    soma = sum(v["uz"] for v in r2.analise.reacoes.values())
    assert math.isclose(soma, r2.carga_total_kn, rel_tol=1e-9)
    with pytest.raises(nbr.FaixaNormativaError):
        an.grelha_nervurada(600, 600, 60, 60, 10, 30, 5, FCK, 8.0,
                            bordas={k: "livre" for k in an.BORDAS})
    with pytest.raises(ValueError):
        an.grelha_nervurada(600, 600, 60, 60, 10, 30, 5, FCK, 8.0, bordas={"z0": "apoio"})


# =============================================================================
# 14.7.8 — grelha equivalente contra a placa de Timoshenko (p. 118)
# =============================================================================
def _navier_placa_apoiada(a, b, q_kncm2, D, x, y, nu, termos=199):
    """Solução de Navier (Timoshenko & Woinowsky-Krieger, placa retangular
    simplesmente apoiada com carga uniforme):
      w  = 16q/(π⁶D)·ΣΣ sen(mπx/a)·sen(nπy/b) / [m·n·((m/a)² + (n/b)²)²]
      mx = 16q/π⁴ ·ΣΣ [(m/a)² + ν(n/b)²]·sen·sen / [m·n·((m/a)² + (n/b)²)²]
    com m, n ímpares."""
    w = mx = 0.0
    for m in range(1, termos + 1, 2):
        for n in range(1, termos + 1, 2):
            s = math.sin(m * math.pi * x / a) * math.sin(n * math.pi * y / b)
            den = m * n * ((m / a) ** 2 + (n / b) ** 2) ** 2
            w += s / den
            mx += ((m / a) ** 2 + nu * (n / b) ** 2) * s / den
    return 16 * q_kncm2 / (math.pi ** 6 * D) * w, 16 * q_kncm2 / math.pi ** 4 * mx


A_PLACA, H_PLACA, Q_PLACA = 600.0, 15.0, 10.0
D_PLACA = E_KNCM2 * H_PLACA ** 3 / (12 * (1 - NU ** 2))
W_NAVIER, M_NAVIER = _navier_placa_apoiada(A_PLACA, A_PLACA, Q_PLACA / 1e4, D_PLACA,
                                           A_PLACA / 2, A_PLACA / 2, NU)


def test_navier_confere_coeficientes_de_timoshenko():
    # conferência da referência: w = 0,00406·q·a⁴/D (tabela de Timoshenko) e
    # mx = (0,0479/1,3)·(1 + ν)·q·a² no centro do quadrado (0,0479 é o de ν = 0,3)
    q = Q_PLACA / 1e4
    assert math.isclose(W_NAVIER, 0.00406 * q * A_PLACA ** 4 / D_PLACA, rel_tol=2e-3)
    assert math.isclose(M_NAVIER, 0.0479 / 1.3 * 1.2 * q * A_PLACA ** 2, rel_tol=3e-3)


def _placa(n, torcao="isotropica"):
    return an.grelha_equivalente_laje_lisa(A_PLACA, A_PLACA, H_PLACA, FCK, Q_PLACA, n_div_x=n,
                                           bordas={k: "apoio" for k in an.BORDAS}, torcao=torcao)


def test_grelha_equivalente_converge_para_timoshenko():
    # Tolerância declarada: flecha no centro a 2,5 % com 8 divisões e a 1 %
    # com 32; momento no centro (nodal, com correção de Poisson) a 6 % com 8
    # e a 1,5 % com 32. O erro diminui com o refinamento da malha.
    erros_w, erros_m = [], []
    for n in (8, 16, 32):
        r = _placa(n)
        w = -r.deslocamento_cm(A_PLACA / 2, A_PLACA / 2)
        mx, my = r.momentos_nodais[(n // 2, n // 2)]
        erros_w.append(_rel(w, W_NAVIER))
        erros_m.append(_rel(mx, M_NAVIER))
        assert math.isclose(mx, my, rel_tol=1e-9)        # simetria
        soma = sum(v["uz"] for v in r.analise.reacoes.values())
        assert math.isclose(soma, Q_PLACA * (A_PLACA / 100) ** 2, rel_tol=1e-9)
    assert erros_w[0] < 0.025 and erros_w[-1] < 0.01
    assert erros_m[0] < 0.06 and erros_m[-1] < 0.015
    assert erros_w[0] > erros_w[1] > erros_w[2]
    assert erros_m[0] > erros_m[1] > erros_m[2]


def test_grelha_equivalente_torcao_da_placa_mais_flexivel():
    # com a rigidez à torção D·(1 − ν) (sem o termo de Poisson do 2H da
    # placa), a grelha fica cerca de 12 % mais flexível que a placa
    r = _placa(16, torcao="placa")
    w = -r.deslocamento_cm(A_PLACA / 2, A_PLACA / 2)
    assert 0.08 < w / W_NAVIER - 1 < 0.16
    b = next(iter(r.modelo.barras.values()))
    assert math.isclose(b.fator_GJ, 1.0)
    b_iso = next(iter(_placa(4).modelo.barras.values()))
    assert math.isclose(b_iso.fator_GJ, 1 / (1 - NU))
    assert math.isclose(b_iso.fator_EI, 1 / (1 - NU ** 2))


def test_grelha_equivalente_laje_lisa_sobre_pilares():
    # 3 × 3 pilares; equilíbrio e simetria das reações; pilar central leva mais
    pts = [(x, y) for x in (0, 600, 1200) for y in (0, 500, 1000)]
    pil = [an.PilarLajeLisa(x, y, 40, 40) for x, y in pts]
    r = an.grelha_equivalente_laje_lisa(1200, 1000, 20, FCK, 10.0, pil, n_div_x=12)
    total = 10.0 * 12.0 * 10.0
    assert math.isclose(sum(r.reacoes_pilares.values()), total, rel_tol=1e-9)
    R = r.reacoes_pilares
    assert math.isclose(R[0], R[8], rel_tol=1e-6) and math.isclose(R[0], R[2], rel_tol=1e-6)
    assert R[4] == max(R.values())
    assert r.m_x_neg_knm_por_m < 0 < r.m_x_pos_knm_por_m
    # molas de rotação 4·E·I/h do pilar (h = 280 cm, I = 40⁴/12)
    k = 4 * E_KNCM2 * 40 ** 4 / 12 / 280
    assert math.isclose(an.rigidez_rotacao_pilar_kncm_rad(nbr.Ecs(FCK), 40 ** 4 / 12, 280), k)
    no = (0, 0)
    assert math.isclose(r.modelo.molas[no][3], k) and math.isclose(r.modelo.molas[no][4], k)
    assert any("14.7.8" in m for m in r.memoria)


def test_grelha_equivalente_pilar_elastico_e_articulado():
    # mola axial E·A/h e 3·E·I/h com extremo articulado
    pil = [an.PilarLajeLisa(x, y, 30, 50, h_inf_cm=300, h_sup_cm=300, extremo_engastado=False,
                            rigido_vertical=False)
           for x in (0, 500) for y in (0, 500)]
    r = an.grelha_equivalente_laje_lisa(500, 500, 18, FCK, 8.0, pil, n_div_x=6)
    molas = r.modelo.molas[(0, 0)]
    assert math.isclose(molas[2], E_KNCM2 * 30 * 50 / 300)
    assert math.isclose(molas[3], 2 * 3 * E_KNCM2 * (30 * 50 ** 3 / 12) / 300)   # giro em X: I = bx·by³/12
    assert math.isclose(molas[4], 2 * 3 * E_KNCM2 * (50 * 30 ** 3 / 12) / 300)
    assert math.isclose(sum(r.reacoes_pilares.values()), 8.0 * 25.0, rel_tol=1e-9)


def test_grelha_equivalente_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        an.grelha_equivalente_laje_lisa(500, 500, 18, FCK, 8.0)        # nada apoia
    with pytest.raises(nbr.FaixaNormativaError):
        an.grelha_equivalente_laje_lisa(500, 500, 18, FCK, 8.0, [an.PilarLajeLisa(600, 0, 30, 30)])
    with pytest.raises(nbr.FaixaNormativaError):
        an.PilarLajeLisa(0, 0, 0, 30)
    with pytest.raises(ValueError):
        an.grelha_equivalente_laje_lisa(500, 500, 18, FCK, 8.0, bordas={"x0": "apoio"},
                                        torcao="viga")


# =============================================================================
# 14.7.8 — pórtico equivalente (p. 118)
# =============================================================================
PILARES_3X3 = [(x, y) for x in (0, 600, 1200) for y in (0, 500, 1000)]


def test_condicoes_portico_ok_e_falhas():
    c = an.verificar_condicoes_portico_equivalente(PILARES_3X3)
    assert c.ok and c.filas_ortogonais and c.vaos_pouco_diferentes
    assert c.vaos_x_cm == (600.0, 600.0) and c.vaos_y_cm == (500.0, 500.0)
    # pilar desalinhado (5 cm fora da fila)
    p = list(PILARES_3X3)
    p[4] = (605.0, 500.0)
    c2 = an.verificar_condicoes_portico_equivalente(p)
    assert not c2.ok and not c2.filas_ortogonais
    # fila incompleta (falta um pilar)
    c3 = an.verificar_condicoes_portico_equivalente(PILARES_3X3[:-1])
    assert not c3.filas_ortogonais
    # vãos: 600 e 400 → 0,667 ≥ 2/3 (limite inclusivo); 600 e 390 → 0,65 < 2/3
    ok = [(x, y) for x in (0, 600, 1000) for y in (0, 500)]
    assert an.verificar_condicoes_portico_equivalente(ok).vaos_pouco_diferentes
    nok = [(x, y) for x in (0, 600, 990) for y in (0, 500)]
    c4 = an.verificar_condicoes_portico_equivalente(nok)
    assert not c4.vaos_pouco_diferentes and not c4.ok
    # só concreto armado
    assert not an.verificar_condicoes_portico_equivalente(PILARES_3X3, concreto_armado=False).ok
    with pytest.raises(nbr.FaixaNormativaError):
        an.portico_equivalente(nok, 20, FCK, 10.0, 40, 40)
    with pytest.raises(nbr.FaixaNormativaError):
        an.verificar_condicoes_portico_equivalente([(0, 0), (1, 1)])


def test_portico_equivalente_painel_unico_solucao_fechada():
    # 2 × 2 pilares, um vão em cada direção, só lance inferior engastado na
    # base: pórtico simétrico sem deslocamento lateral. Distribuição de
    # momentos no nó: viga simétrica 2EIv/L, pilar 4EIp/h;
    # M− = (q·L²/12)·(4EIp/h)/(4EIp/h + 2EIv/L); M+ = q·L²/8 − M−.
    L, B, h, hp, q = 600.0, 500.0, 20.0, 300.0, 10.0
    pil = [(0, 0), (L, 0), (0, B), (L, B)]
    r = an.portico_equivalente(pil, h, FCK, q, 40, 30, h_inf_cm=hp, direcao="x")
    assert len(r.porticos) == 2
    p = r.porticos[0]
    l2 = B / 2                                 # fila de borda: metade do vão transversal
    assert math.isclose(p.largura_a_cm + p.largura_b_cm, l2)
    qlin = q * l2 / 1e4                        # kN/cm
    Iv = l2 * h ** 3 / 12
    Ip = 30 * 40 ** 3 / 12                     # direção X: dimensão 40 no plano
    kp, kv = 4 * Ip / hp, 2 * Iv / L
    Mneg = qlin * L ** 2 / 12 * kp / (kp + kv)
    # Tolerância 2e-3: a solução fechada despreza a deformação axial da laje e
    # dos pilares, que o pórtico do P44 considera (EA finito); o efeito aqui
    # é de 0,07 %.
    v = p.vaos[0]
    assert math.isclose(v.M_neg_i_kncm, -Mneg, rel_tol=2e-3)
    assert math.isclose(v.M_neg_j_kncm, v.M_neg_i_kncm, rel_tol=1e-9)
    assert math.isclose(v.M_pos_kncm, qlin * L ** 2 / 8 - Mneg, rel_tol=2e-3)
    # M+ + |M−| = q·L²/8 vale exatamente (estática do vão)
    assert math.isclose(v.M_pos_kncm - v.M_neg_i_kncm, qlin * L ** 2 / 8, rel_tol=1e-9)
    # momento de ligação laje-pilar extremo (14.7.8): equilíbrio do nó
    assert math.isclose(abs(p.momentos_pilares_kncm[0]["inferior"]), abs(v.M_neg_i_kncm),
                        rel_tol=1e-9)
    assert math.isclose(sum(p.reacoes_kn.values()), qlin * L, rel_tol=1e-9)


def test_portico_equivalente_faixas_somam_o_total_e_figura_14_9():
    # pórtico interno de painel regular: lados iguais → faixa externa 27,5 %
    # (positivo) e 37,5 % (negativo) do momento do pórtico; internas 45 % e
    # 25 % (14.7.8 a a d); a soma das faixas é o momento do pórtico
    r = an.portico_equivalente(PILARES_3X3, 20, FCK, 10.0, 40, 40, h_inf_cm=280, h_sup_cm=280)
    assert len(r.porticos) == 6
    for p in r.porticos:
        for v in p.vaos:
            for chave, M in (("M_neg_i", v.M_neg_i_kncm), ("M_neg_j", v.M_neg_j_kncm),
                             ("M_pos", v.M_pos_kncm)):
                assert math.isclose(sum(v.faixas[chave].values()), M, rel_tol=1e-12)
    interno = [p for p in r.porticos if p.direcao == "x" and p.coordenada_cm == 500.0][0]
    assert math.isclose(interno.largura_a_cm, 250.0) and math.isclose(interno.largura_b_cm, 250.0)
    v = interno.vaos[0]
    f = v.faixas
    assert math.isclose(f["M_pos"]["faixa_externa_a"], 0.275 * v.M_pos_kncm)
    assert math.isclose(f["M_pos"]["faixa_externa_b"], 0.275 * v.M_pos_kncm)
    assert math.isclose(f["M_pos"]["faixa_interna_a"] + f["M_pos"]["faixa_interna_b"],
                        0.45 * v.M_pos_kncm)
    assert math.isclose(f["M_neg_j"]["faixa_externa_a"], 0.375 * v.M_neg_j_kncm)
    assert math.isclose(f["M_neg_j"]["faixa_interna_a"] + f["M_neg_j"]["faixa_interna_b"],
                        0.25 * v.M_neg_j_kncm)
    # pórtico de borda (um lado só): faixa externa 55 % / 75 %, meia interna 45 % / 25 %
    borda = [p for p in r.porticos if p.direcao == "x" and p.coordenada_cm == 0.0][0]
    vb = borda.vaos[0]
    assert math.isclose(vb.faixas["M_pos"]["faixa_externa_b"], 0.55 * vb.M_pos_kncm)
    assert math.isclose(vb.faixas["M_neg_j"]["faixa_externa_b"], 0.75 * vb.M_neg_j_kncm)
    assert "faixa_externa_a" not in vb.faixas["M_pos"]


def test_portico_equivalente_carga_total_em_cada_direcao():
    # "para cada pórtico deve ser considerada a carga total": a soma das
    # reações dos pórticos de cada direção é a carga total da laje
    r = an.portico_equivalente(PILARES_3X3, 20, FCK, 10.0, 40, 40)
    total = 10.0 * 12.0 * 10.0
    for d in ("x", "y"):
        soma = sum(sum(p.reacoes_kn.values()) for p in r.porticos if p.direcao == d)
        assert math.isclose(soma, total, rel_tol=1e-9)
    # vão simétrico: momentos negativos simétricos nos pórticos de 2 vãos iguais
    p = r.porticos[1]
    assert math.isclose(p.vaos[0].M_neg_j_kncm, p.vaos[1].M_neg_i_kncm, rel_tol=1e-9)
    assert math.isclose(p.vaos[0].M_pos_kncm, p.vaos[1].M_pos_kncm, rel_tol=1e-9)


def test_portico_equivalente_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        an.portico_equivalente(PILARES_3X3, 20, FCK, 10.0, 40, 40, h_inf_cm=None)
    with pytest.raises(ValueError):
        an.portico_equivalente(PILARES_3X3, 20, FCK, 10.0, 40, 40, direcao="z")
    with pytest.raises(nbr.FaixaNormativaError):
        an.portico_equivalente(PILARES_3X3, 20, FCK, -1.0, 40, 40)
