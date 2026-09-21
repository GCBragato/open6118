"""Testes do pacote T2 — contorno C″ com armadura de punção em cruz (NBR 6118:2026).

19.5.3.4, Figura 19.8 (à direita), PDF p. 190. A Figura não dá a regra
numérica do contorno reduzido entre os braços da cruz; a construção adotada é
a do programa de punção do escritório (BRGTools, ``Perimetros.Cruz``, porte do
LPUNC), por decisão do engenheiro em 21/09/2026.

Os valores esperados saem de conta independente, feita aqui à mão:
    arco = raio × ângulo; reta = distância entre as pontas;
    r6 = (0,5·nb + 2d·cos 45°)/cos 45° = nb/√2 + 2d (arcos acima e abaixo);
    r8 = nh/√2 + 2d (arcos à direita e à esquerda);
    pilar interno: quatro arcos de 90° (π/2) e, com rn > 2d, oito retas de d;
    borda: dois arcos de 45° (π/4) e um de 90° e, com rn > 2d, quatro retas;
    canto: dois arcos de 45° e, com rn > 2d, duas retas;
    pilar circular: nb = nh = D·cos 45° e rn acrescido de (D − nb)/2.
Os testes do BRGTools (tests/BRGTools.PuncaoLaje.Tests) não têm valor esperado
de u″ na cruz (só o SmokeTests confere que o caminho roda), então não há valor
de lá para reproduzir.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr                   # noqa: E402
import puncao_nbr6118 as P                     # noqa: E402

FE = nbr.FaixaNormativaError
S2 = math.sqrt(2.0)


def _u_mao(tipo, nb, nh, d, rn):
    """u″ à mão: soma de raio × ângulo dos arcos e d por reta (PDF p. 190, construção do BRGTools)."""
    r6 = nb / S2 + 2 * d
    r8 = nh / S2 + 2 * d
    retas = rn > 2 * d
    if tipo == "interno":
        return 2 * r6 * (math.pi / 2) + 2 * r8 * (math.pi / 2) + (8 * d if retas else 0.0)
    if tipo == "borda":
        # esq/dir: dois arcos r6 de π/4 e um r8 de π/2 (sup/inf: papéis trocados; o total é o mesmo)
        return 2 * r6 * (math.pi / 4) + r8 * (math.pi / 2) + (4 * d if retas else 0.0)
    return r6 * math.pi / 4 + r8 * math.pi / 4 + (2 * d if retas else 0.0)


# ---------------------------------------------------------------------------
# 19.5.3.4 — u″ do pilar retangular, interno, borda e canto (PDF p. 190)
# ---------------------------------------------------------------------------
def test_u_cruz_interno_retangular_com_trechos_retos():
    # b = 40, h = 60, d = 15, C″ a 70 cm da face -> rn = 70 − 30 = 40 cm > 2d = 30.
    # r6 = 40/√2 + 30 = 58,284 cm; r8 = 60/√2 + 30 = 72,426 cm
    # u″ = π·(58,284 + 72,426) + 8·15 = 410,640 + 120 = 530,640 cm
    u = P.u_C2l_cruz_cm(40, 60, 15, 70, "interno")
    assert u == pytest.approx(math.pi * (40 / S2 + 30 + 60 / S2 + 30) + 120, rel=1e-12)
    assert u == pytest.approx(530.6397, abs=1e-3)


def test_u_cruz_interno_retangular_sem_trechos_retos():
    # rn = 50 − 30 = 20 cm <= 2d: só os quatro arcos. u″ = π·(r6 + r8) = 410,640 cm
    u = P.u_C2l_cruz_cm(40, 60, 15, 50, "interno")
    assert u == pytest.approx(math.pi * (40 / S2 + 60 / S2 + 60), rel=1e-12)


def test_u_cruz_degrau_dos_trechos_retos_em_rn_igual_a_2d():
    # rn = 2d exato: ainda sem retas (o programa usa rn > 2d); logo acima, + 8d.
    d = 15.0
    sem = P.u_C2l_cruz_cm(40, 60, d, 4 * d, "interno")
    com = P.u_C2l_cruz_cm(40, 60, d, 4 * d + 1e-6, "interno")
    assert sem == pytest.approx(_u_mao("interno", 40, 60, d, 2 * d), rel=1e-12)
    assert com - sem == pytest.approx(8 * d, rel=1e-9)


def test_u_cruz_nao_depende_do_afastamento_alem_de_2d():
    # Na cruz, u″ não cresce com a armadura: só os centros dos arcos se deslocam.
    u1 = P.u_C2l_cruz_cm(40, 60, 15, 70, "interno")
    u2 = P.u_C2l_cruz_cm(40, 60, 15, 170, "interno")
    assert u1 == pytest.approx(u2, rel=1e-12)


@pytest.mark.parametrize("pos", ["esq", "dir", "sup", "inf"])
@pytest.mark.parametrize("af", [50.0, 70.0])   # rn = 20 (sem retas) e 40 (com retas)
def test_u_cruz_borda_todas_as_posicoes(pos, af):
    # borda: (π/2)·(r6 + r8) + 4d·δ. b = 40, h = 60, d = 15.
    # af = 70: (π/2)·(58,284 + 72,426) + 60 = 265,320 cm
    u = P.u_C2l_cruz_cm(40, 60, 15, af, "borda", pos)
    assert u == pytest.approx(_u_mao("borda", 40, 60, 15, af - 30), rel=1e-12)


@pytest.mark.parametrize("pos", ["inf_esq", "inf_dir", "sup_esq", "sup_dir"])
@pytest.mark.parametrize("af", [50.0, 70.0])
def test_u_cruz_canto_todas_as_posicoes(pos, af):
    # canto: (π/4)·(r6 + r8) + 2d·δ. af = 70: (π/4)·130,710 + 30 = 132,660 cm
    u = P.u_C2l_cruz_cm(40, 60, 15, af, "canto", pos)
    assert u == pytest.approx(_u_mao("canto", 40, 60, 15, af - 30), rel=1e-12)


def test_u_cruz_borda_arco_a_arco():
    # pb_esq, conferido trecho a trecho: arco superior r6 de 45° a 90° (π/4),
    # arco direito r8 de 315° a 45° (cruza 0: π/2), arco inferior r6 de 270° a
    # 315° (π/4), e 4 retas de d.
    b, h, d, af = 40.0, 60.0, 15.0, 70.0
    tr = P.contorno_C2l_cruz(b, h, d, af, "borda", "esq")
    arcos = [t for t in tr if t[0] == "arco"]
    retas = [t for t in tr if t[0] == "reta"]
    assert len(arcos) == 3 and len(retas) == 4
    r6, r8 = b / S2 + 2 * d, h / S2 + 2 * d
    assert [a[2] for a in arcos] == pytest.approx([r6, r8, r6])
    assert [a[4] - a[3] for a in arcos] == pytest.approx([math.pi / 4, math.pi / 2, math.pi / 4])
    for rt in retas:
        assert math.dist(rt[1], rt[2]) == pytest.approx(d)


def test_u_cruz_simetria_das_posicoes():
    # Borda "sup" com b e h trocados é a borda "esq" girada de 90°.
    assert P.u_C2l_cruz_cm(60, 40, 15, 70, "borda", "sup") == \
        pytest.approx(P.u_C2l_cruz_cm(40, 60, 15, 70, "borda", "esq"), rel=1e-12)
    # Padrões: borda "esq", canto "inf_esq".
    assert P.u_C2l_cruz_cm(40, 60, 15, 70, "borda") == \
        P.u_C2l_cruz_cm(40, 60, 15, 70, "borda", "esq")
    assert P.u_C2l_cruz_cm(40, 60, 15, 70, "canto") == \
        P.u_C2l_cruz_cm(40, 60, 15, 70, "canto", "inf_esq")


# ---------------------------------------------------------------------------
# Pilar circular (PDF p. 190; construção do BRGTools)
# ---------------------------------------------------------------------------
def test_u_cruz_interno_circular():
    # D = 40, d = 15. nb = nh = 40·cos 45° = 28,284 cm; r6 = r8 = 20 + 30 = 50 cm.
    # C″ a 50 cm da face: rn = 20; rn efetivo = 20 + (40 − 28,284)/2 = 25,858 <= 30 -> sem retas.
    # u″ = π·(50 + 50) = 314,159 cm
    assert P.u_C2l_cruz_cm(None, None, 15, 50, "interno", D_cm=40) == \
        pytest.approx(100 * math.pi, rel=1e-12)
    # C″ a 60 cm: rn efetivo = 30 + 5,858 = 35,858 > 30 -> + 8·15 = 434,159 cm
    assert P.u_C2l_cruz_cm(None, None, 15, 60, "interno", D_cm=40) == \
        pytest.approx(100 * math.pi + 120, rel=1e-12)


def test_u_cruz_circular_degrau_com_o_acrescimo_do_programa():
    # O trecho reto entra quando rn + (D − D·cos45°)/2 > 2d, isto é,
    # afastamento > 4d − (D − D/√2)/2 = 60 − 5,858 = 54,142 cm.
    lim = 60 - (40 - 40 / S2) / 2
    abaixo = P.u_C2l_cruz_cm(None, None, 15, lim - 1e-6, "interno", D_cm=40)
    acima = P.u_C2l_cruz_cm(None, None, 15, lim + 1e-6, "interno", D_cm=40)
    assert abaixo == pytest.approx(100 * math.pi, rel=1e-12)
    assert acima == pytest.approx(100 * math.pi + 120, rel=1e-12)


@pytest.mark.parametrize("tipo,pos,frac,nretas", [
    ("borda", "esq", 0.5, 4), ("borda", "sup", 0.5, 4),
    ("canto", "inf_esq", 0.25, 2), ("canto", "sup_dir", 0.25, 2)])
def test_u_cruz_circular_borda_e_canto(tipo, pos, frac, nretas):
    # r6 = r8 = D/2 + 2d = 50; borda: (π/2)·100 + 4d; canto: (π/4)·100 + 2d (C″ a 60 cm).
    u = P.u_C2l_cruz_cm(None, None, 15, 60, tipo, pos, D_cm=40)
    assert u == pytest.approx(frac * 2 * math.pi * 50 + nretas * 15, rel=1e-12)


# ---------------------------------------------------------------------------
# Geometria da construção: pontas dos arcos, continuidade das retas
# ---------------------------------------------------------------------------
def test_contorno_cruz_interno_pontas_a_2d_do_canto_do_braco():
    # Arco superior: pontas a 2d, na diagonal de 45°, do canto externo do braço
    # superior do último contorno, (±b/2, h/2 + rn). b = 40, h = 60, d = 15, rn = 40.
    b, h, d, rn = 40.0, 60.0, 15.0, 40.0
    tr = P.contorno_C2l_cruz(b, h, d, rn + 2 * d, "interno")
    sup = tr[0]
    assert sup[0] == "arco"
    c, r, t0, t1 = sup[1], sup[2], sup[3], sup[4]
    p1 = (c[0] + r * math.cos(t0), c[1] + r * math.sin(t0))
    p2 = (c[0] + r * math.cos(t1), c[1] + r * math.sin(t1))
    assert math.dist(p1, (b / 2, h / 2 + rn)) == pytest.approx(2 * d)
    assert math.dist(p2, (-b / 2, h / 2 + rn)) == pytest.approx(2 * d)
    assert (p1[0] - b / 2) == pytest.approx(p1[1] - h / 2 - rn)   # 45°
    # As retas começam nas pontas do arco e têm comprimento d.
    reta_d, reta_e = tr[1], tr[2]
    assert reta_d[1] == pytest.approx(p1) and reta_e[1] == pytest.approx(p2)
    assert math.dist(*reta_d[1:]) == pytest.approx(d)


def test_contorno_cruz_interno_simetrico():
    # 4 arcos e 8 retas; soma dos ângulos = 2π; centróide na origem.
    tr = P.contorno_C2l_cruz(40, 60, 15, 70, "interno")
    arcos = [t for t in tr if t[0] == "arco"]
    assert len(arcos) == 4 and len(tr) == 12
    assert sum(a[4] - a[3] for a in arcos) == pytest.approx(2 * math.pi)
    assert all(a[4] > a[3] for a in arcos)


# ---------------------------------------------------------------------------
# Wp″ do contorno em cruz (19.5.2.2 aplicado a C″, PDF p. 184 e 190)
# ---------------------------------------------------------------------------
def _pontos(tr, n=4000):
    """Discretiza o contorno em segmentos curtos (integração independente da forma fechada)."""
    for t in tr:
        for i in range(n):
            s0, s1 = i / n, (i + 1) / n
            if t[0] == "reta":
                a = (t[1][0] + s0 * (t[2][0] - t[1][0]), t[1][1] + s0 * (t[2][1] - t[1][1]))
                b = (t[1][0] + s1 * (t[2][0] - t[1][0]), t[1][1] + s1 * (t[2][1] - t[1][1]))
            else:
                c, r, u0, u1 = t[1], t[2], t[3], t[4]
                a0, a1 = u0 + s0 * (u1 - u0), u0 + s1 * (u1 - u0)
                a = (c[0] + r * math.cos(a0), c[1] + r * math.sin(a0))
                b = (c[0] + r * math.cos(a1), c[1] + r * math.sin(a1))
            yield a, b


def _wp_numerico(tr, eixo, polo=None):
    segs = list(_pontos(tr))
    if polo is None:
        L = sum(math.dist(a, b) for a, b in segs)
        polo = (sum(math.dist(a, b) * (a[0] + b[0]) / 2 for a, b in segs) / L,
                sum(math.dist(a, b) * (a[1] + b[1]) / 2 for a, b in segs) / L)
    return sum(math.dist(a, b) * abs((a[eixo] + b[eixo]) / 2 - polo[eixo]) for a, b in segs)


@pytest.mark.parametrize("tipo,pos", [("interno", None), ("borda", "esq"), ("borda", "sup"),
                                      ("canto", "inf_esq")])
@pytest.mark.parametrize("direcao,eixo", [(0.0, 0), (90.0, 1)])
def test_wp_cruz_contra_integracao_numerica(tipo, pos, direcao, eixo):
    tr = P.contorno_C2l_cruz(40, 60, 15, 70, tipo, pos)
    W = P.Wp_C2l_cruz_cm2(40, 60, 15, 70, tipo, pos, None, direcao)
    assert W == pytest.approx(_wp_numerico(tr, eixo), rel=1e-5)
    Wpil = P.Wp_C2l_cruz_cm2(40, 60, 15, 70, tipo, pos, None, direcao, polo="pilar")
    assert Wpil == pytest.approx(_wp_numerico(tr, eixo, (0.0, 0.0)), rel=1e-5)


def test_wp_cruz_interno_polo_do_perimetro_e_do_pilar_coincidem():
    a = P.Wp_C2l_cruz_cm2(40, 60, 15, 70, "interno", direcao_excentricidade_graus=0.0)
    b = P.Wp_C2l_cruz_cm2(40, 60, 15, 70, "interno", direcao_excentricidade_graus=0.0, polo="pilar")
    assert a == pytest.approx(b, rel=1e-12)
    with pytest.raises(ValueError):
        P.Wp_C2l_cruz_cm2(40, 60, 15, 70, "interno", polo="centro")


# ---------------------------------------------------------------------------
# Erros e faixa
# ---------------------------------------------------------------------------
def test_cruz_erros():
    # C″ a 2d ou menos da face: não há contorno de armadura fora da face.
    with pytest.raises(FE):
        P.u_C2l_cruz_cm(40, 60, 15, 30, "interno")
    P.u_C2l_cruz_cm(40, 60, 15, 30.001, "interno")
    with pytest.raises(ValueError):
        P.u_C2l_cruz_cm(40, 60, 15, 70, "borda", "inf_esq")
    with pytest.raises(ValueError):
        P.u_C2l_cruz_cm(40, 60, 15, 70, "canto", "esq")
    with pytest.raises(ValueError):
        P.u_C2l_cruz_cm(40, 60, 15, 70, "interno", "esq")
    with pytest.raises(ValueError):
        P.u_C2l_cruz_cm(None, 60, 15, 70, "interno")
    with pytest.raises(FE):
        P.u_C2l_cruz_cm(40, 60, 0.0, 70, "interno")


def test_fonte_declarada_nas_docstrings():
    for f in (P.contorno_C2l_cruz, P.u_C2l_cruz_cm, P.Wp_C2l_cruz_cm2):
        doc = " ".join(f.__doc__.split())
        assert "BRGTools" in doc and "21/09/2026" in doc
        assert "não dá a regra numérica" in doc
    assert "BRGTools" in P.FONTE_C2L_CRUZ and "21/09/2026" in P.FONTE_C2L_CRUZ


# ---------------------------------------------------------------------------
# Ligação: disposicao_armadura_puncao e verificar_puncao (19.5.3.4)
# ---------------------------------------------------------------------------
def test_disposicao_arranjo_cruz():
    # Pilar 40×40, d = 17, s0 = 8,5, sr = 10, FSd = 500 kN, τRd1 = 0,6 MPa.
    # n = 1: rn = 8,5 <= 34 -> u″ = π·2·(40/√2 + 34) = 391,34 cm; τ = 500/(391,34·17)·10 = 0,7516 > 0,6
    # n = 4: rn = 38,5 > 34 -> u″ = 391,34 + 136 = 527,34 cm; τ = 0,5577 <= 0,6 (n = 2, 3 não têm as retas)
    r = P.disposicao_armadura_puncao(500.0, 40.0, 40.0, 17.0, 0.6, sr_cm=10.0, arranjo="cruz")
    u = math.pi * 2 * (40 / S2 + 34) + 136
    assert r.arranjo_C2l == "cruz" and r.ok
    assert r.n_contornos == 4
    assert r.u_C2l_cm == pytest.approx(u, rel=1e-12)
    assert r.tau_Sd_C2l_mpa == pytest.approx(500 / (u * 17) * 10, rel=1e-12)
    assert r.espacamento_tangencial_cm is None
    assert any("BRGTools" in m for m in r.memoria)


def test_disposicao_cruz_sem_saida_para_antes_do_limite():
    # FSd/(u″·d) > τRd1 com rn > 2d: u″ não cresce, a busca para (como no BRGTools).
    r = P.disposicao_armadura_puncao(1500.0, 40.0, 40.0, 20.0, 0.6, sr_cm=15.0, s0_cm=10.0,
                                     arranjo="cruz")
    assert not r.ok
    assert r.n_contornos < 200
    assert "não cresce" in r.governante
    # rn = 10 + (n − 1)·15 > 40 na parada: n = 4 (rn = 55)
    assert r.n_contornos == 4


def test_disposicao_cruz_com_momento_usa_wp_da_cruz():
    r = P.disposicao_armadura_puncao(500.0, 40.0, 60.0, 17.0, 0.9, sr_cm=10.0,
                                     MSd1_kncm=3000.0, arranjo="cruz")
    W1 = P.Wp_C2l_cruz_cm2(40.0, 60.0, 17.0, r.afastamento_C2l_cm, "interno",
                           direcao_excentricidade_graus=0.0)
    assert r.Wp_C2l_cm2[0] == pytest.approx(W1, rel=1e-12)
    tau = (500 / (r.u_C2l_cm * 17) + P.K(40 / 60) * 3000 / (W1 * 17)) * 10
    assert r.tau_Sd_C2l_mpa == pytest.approx(tau, rel=1e-12)


def test_disposicao_radial_sem_n_linhas_continua_inteiro():
    r = P.disposicao_armadura_puncao(500.0, 40.0, 40.0, 17.0, 0.6, sr_cm=10.0)
    assert r.arranjo_C2l == "inteiro"
    with pytest.raises(ValueError):
        P.disposicao_armadura_puncao(500.0, 40.0, 40.0, 17.0, 0.6, sr_cm=10.0, arranjo="anel")


def _verif(**kw):
    base = dict(fck_mpa=30.0, d_cm=15.0, FSd_kn=600.0, c1_cm=40.0, c2_cm=60.0,
                rho_x=0.01, rho_y=0.01, Asw_cm2=6.0, sr_cm=10.0, fywd_mpa=300.0)
    base.update(kw)
    return P.verificar_puncao(**base)


def test_verificar_puncao_calcula_u_cruz():
    r = _verif(afastamento_C2l_cruz_cm=70.0)
    assert r.armadura_necessaria
    u = math.pi * (40 / S2 + 60 / S2 + 60) + 120
    assert r.tau_Sd_C2l_mpa == pytest.approx(600 / (u * 15) * 10, rel=1e-12)
    assert r.status_C2l != "não verificado: informe u_C2l_cm (19.5.3.4)"
    assert any("BRGTools" in m for m in r.memoria)
    # Sem o afastamento e sem u″: continua "não verificado".
    assert "não verificado" in _verif().status_C2l
    # u″ informado prevalece.
    assert _verif(afastamento_C2l_cruz_cm=70.0, u_C2l_cm=900.0).tau_Sd_C2l_mpa == \
        pytest.approx(600 / (900 * 15) * 10, rel=1e-12)


def test_verificar_puncao_cruz_borda_com_momento():
    r = _verif(tipo="borda", posicao="esq", MSd1_kncm=2000.0, afastamento_C2l_cruz_cm=70.0)
    u = (math.pi / 2) * (40 / S2 + 60 / S2 + 60) + 60
    W1 = P.Wp_C2l_cruz_cm2(40, 60, 15, 70, "borda", "esq", None, 0.0)
    tau = (600 / (u * 15) + P.K(40 / 60) * 2000 / (W1 * 15)) * 10
    assert r.tau_Sd_C2l_mpa == pytest.approx(tau, rel=1e-12)


def test_verificar_puncao_cruz_circular():
    r = _verif(c1_cm=40.0, c2_cm=None, circular=True, afastamento_C2l_cruz_cm=60.0)
    assert r.tau_Sd_C2l_mpa == pytest.approx(600 / ((100 * math.pi + 120) * 15) * 10, rel=1e-12)
