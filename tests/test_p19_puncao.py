"""Testes do P19 -- Punção: solicitação e resistência (NBR 6118:2026, 19.5.1 a 19.5.3.3).

Valores esperados tirados das imagens das páginas do PDF (SCRATCH/nbr_png):
p182 (19.5.1), p183 (19.5.2.1, Figura 19.2), p184 (19.5.2.2, Tabela 19.2, Wp),
p185 (19.5.2.3, Figura 19.3), p186 (19.5.2.3 b e 19.5.2.4, Figura 19.4),
p188 (19.5.3.1 e 19.5.3.2), p189 (19.5.3.2 e 19.5.3.3), p190 (19.5.3.3, fywd).

Wp e e* de borda e canto não têm expressão fechada na norma (só a integral
Wp = ∫|e|·dℓ de 19.5.2.2): os testes conferem as expressões da biblioteca
contra integração numérica independente do perímetro das Figuras 19.3 e 19.4.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import puncao_nbr6118 as P  # noqa: E402


# ---------------------------------------------------------------------------
# Integração numérica independente do perímetro (sem a biblioteca)
# ---------------------------------------------------------------------------
def _reta(p0, p1, n=2000):
    return [(p0[0] + (p1[0] - p0[0]) * i / n, p0[1] + (p1[1] - p0[1]) * i / n)
            for i in range(n + 1)]


def _arco(cx, cy, r, a0, a1, n=4000):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n))
            for i in range(n + 1)]


def _integrais(trechos, eixo, x_eixo):
    """Devolve (comprimento, ∫|e|dℓ, ∫e dℓ) com e = coordenada[eixo] − x_eixo."""
    L = W = S = 0.0
    for pts in trechos:
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            dl = math.hypot(xb - xa, yb - ya)
            e = ((xa + xb) / 2.0 if eixo == 0 else (ya + yb) / 2.0) - x_eixo
            L += dl
            W += abs(e) * dl
            S += e * dl
    return L, W, S


def _perimetro_borda(c1, c2, r, a=None):
    """Borda livre em x = 0; pilar em [0, c1] × [−c2/2, c2/2]; C′ afastado r (Figura 19.3).

    Com a = None, perímetro u completo; com a, u* (trechos retos de comprimento a
    junto à face interna do pilar, x de c1 − a a c1).
    """
    x0 = 0.0 if a is None else c1 - a
    y = c2 / 2.0 + r
    tr = [_reta((x0, y), (c1, y)), _reta((x0, -y), (c1, -y)),
          _reta((c1 + r, -c2 / 2.0), (c1 + r, c2 / 2.0))]
    if r > 0:
        tr += [_arco(c1, c2 / 2.0, r, 0.0, math.pi / 2), _arco(c1, -c2 / 2.0, r, -math.pi / 2, 0.0)]
    return tr


def _perimetro_canto(c1, c2, r, a1=None, a2=None):
    """Bordas livres em x = 0 e y = 0; pilar em [0, c1] × [0, c2] (Figura 19.4)."""
    x0 = 0.0 if a1 is None else c1 - a1
    y0 = 0.0 if a2 is None else c2 - a2
    tr = [_reta((x0, c2 + r), (c1, c2 + r)), _reta((c1 + r, y0), (c1 + r, c2))]
    if r > 0:
        tr.append(_arco(c1, c2, r, 0.0, math.pi / 2))
    return tr


def _perimetro_interno(c1, c2, r):
    h1, h2 = c1 / 2.0, c2 / 2.0
    tr = [_reta((-h1, h2 + r), (h1, h2 + r)), _reta((-h1, -h2 - r), (h1, -h2 - r)),
          _reta((h1 + r, -h2), (h1 + r, h2)), _reta((-h1 - r, -h2), (-h1 - r, h2))]
    for cx, cy, a0 in ((h1, h2, 0.0), (-h1, h2, math.pi / 2), (-h1, -h2, math.pi),
                       (h1, -h2, 3 * math.pi / 2)):
        tr.append(_arco(cx, cy, r, a0, a0 + math.pi / 2))
    return tr


# ===========================================================================
# 19.5.1 -- modelo de cálculo (PDF p. 182)
# ===========================================================================
def test_19_5_1_modelo_tres_contornos():
    """19.5.1 (p. 182): C com τRd2, C′ com τRd1/τRd3 e C″ só quando há armadura."""
    r = P.verificar_puncao(25.0, 20.0, 100.0, 40.0, 40.0, rho_x=0.01, rho_y=0.01)
    assert r.ok and not r.armadura_necessaria
    assert r.status_C2l == "não necessário"
    assert r.tau_Rd3_mpa is None and r.tau_Sd_C2l_mpa is None
    assert any("19.5.3.1" in m for m in r.memoria)
    assert any("19.5.3.2" in m for m in r.memoria)


# ===========================================================================
# 19.5.2.1 -- pilar interno, carregamento simétrico (PDF p. 183)
# ===========================================================================
def test_19_5_2_1_tau_sd_simetrico():
    """τSd = FSd/(u·d): 500/(200·20) = 0,125 kN/cm² = 1,25 MPa (19.5.2.1, p. 183)."""
    assert P.tau_Sd_mpa(500.0, 200.0, 20.0) == pytest.approx(1.25, rel=1e-12)


def test_19_5_2_1_d_medio():
    """d = (dx + dy)/2 (19.5.2.1, p. 183): (14 + 16)/2 = 15."""
    assert P.d_medio_cm(14.0, 16.0) == pytest.approx(15.0)
    with pytest.raises(nbr.FaixaNormativaError):
        P.d_medio_cm(0.0, 16.0)


def test_19_5_2_1_perimetros_interno():
    """Figura 19.2 (p. 183): u0 = 2(C1+C2); u = 2(C1+C2) + 4πd (C′ a 2d, cantos em arco)."""
    assert P.perimetro_critico_cm(40, 20, 15, "interno", "C") == pytest.approx(120.0)
    assert P.perimetro_critico_cm(40, 20, 15, "interno", "Cl") == pytest.approx(120 + 60 * math.pi)
    L, _, _ = _integrais(_perimetro_interno(40, 20, 30), 0, 0.0)
    assert P.perimetro_critico_cm(40, 20, 15) == pytest.approx(L, rel=1e-6)
    # pilar circular: u0 = πD; u = π(D + 4d)
    assert P.perimetro_critico_circular_cm(40, 15, "C") == pytest.approx(40 * math.pi)
    assert P.perimetro_critico_circular_cm(40, 15) == pytest.approx(100 * math.pi)


def test_19_5_2_1_entradas_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        P.tau_Sd_mpa(100.0, 0.0, 15.0)
    with pytest.raises(nbr.FaixaNormativaError):
        P.tau_Sd_mpa(-1.0, 100.0, 15.0)
    with pytest.raises(ValueError):
        P.perimetro_critico_cm(40, 40, 15, "meio")
    with pytest.raises(ValueError):
        P.perimetro_critico_cm(40, 40, 15, "interno", "C3")


# ===========================================================================
# Tabela 19.2 -- K (PDF p. 184)
# ===========================================================================
@pytest.mark.parametrize("c1c2, k", [(0.5, 0.45), (1.0, 0.60), (2.0, 0.70), (3.0, 0.80)])
def test_tabela_19_2_todas_as_celulas(c1c2, k):
    """Tabela 19.2 (p. 184): as quatro colunas, com e sem interpolação."""
    assert P.K(c1c2) == pytest.approx(k)
    assert P.K(c1c2, interpolar=False) == pytest.approx(k)
    assert P.TABELA_19_2_K[c1c2] == k


@pytest.mark.parametrize("c1c2, k_interp, k_degrau", [
    (0.75, 0.525, 0.60),   # 0,45 + 0,15·0,5
    (1.5, 0.65, 0.70),     # 0,60 + 0,10·0,5
    (2.5, 0.75, 0.80),     # 0,70 + 0,10·0,5
    (1.25, 0.625, 0.70),   # 0,60 + 0,10·0,25
])
def test_tabela_19_2_intermediarios(c1c2, k_interp, k_degrau):
    """Valores intermediários: a norma não diz; interpolação linear ou degrau superior."""
    assert P.K(c1c2) == pytest.approx(k_interp)
    assert P.K(c1c2, interpolar=False) == pytest.approx(k_degrau)


@pytest.mark.parametrize("c1c2", [0.49, 0.2, 3.01, 4.0])
def test_tabela_19_2_fora_da_faixa(c1c2):
    """Fora de 0,5 <= C1/C2 <= 3,0 a Tabela 19.2 não define K."""
    with pytest.raises(nbr.FaixaNormativaError):
        P.K(c1c2)


def test_tabela_19_2_circular():
    """Pilares circulares internos: K = 0,6 (p. 184)."""
    assert P.K_CIRCULAR == 0.6


# ===========================================================================
# 19.5.2.2 -- Wp (PDF p. 184)
# ===========================================================================
def test_19_5_2_2_wp_retangular_40_40_15():
    """Wp = C1²/2 + C1C2 + 4C2d + 16d² + 2πdC1 (p. 184).

    C1 = C2 = 40, d = 15: 800 + 1600 + 2400 + 3600 + 1200π = 8400 + 3769,911 = 12169,911.
    """
    assert P.Wp_retangular_cm2(40, 40, 15) == pytest.approx(8400 + 1200 * math.pi, rel=1e-12)


@pytest.mark.parametrize("c1, c2, d", [(40, 40, 15), (60, 20, 18), (20, 50, 12)])
def test_19_5_2_2_wp_retangular_igual_integral(c1, c2, d):
    """Wp da norma = ∫|e|dℓ sobre u (Figura 19.2) e, em C, sobre u0 (19.5.3.1)."""
    _, W, _ = _integrais(_perimetro_interno(c1, c2, 2 * d), 0, 0.0)
    assert P.Wp_retangular_cm2(c1, c2, d) == pytest.approx(W, rel=1e-6)
    _, W0, _ = _integrais(_perimetro_interno(c1, c2, 0.0), 0, 0.0)
    assert P.Wp_retangular_cm2(c1, c2, d, "C") == pytest.approx(W0, rel=1e-6)
    assert P.Wp_retangular_cm2(c1, c2, d, "C") == pytest.approx(c1 ** 2 / 2 + c1 * c2)


def test_19_5_2_2_wp_circular():
    """Wp = (D + 4d)²: D = 40, d = 15 -> 100² = 10000 (p. 184); em C, D² = 1600."""
    assert P.Wp_circular_cm2(40, 15) == pytest.approx(10000.0)
    assert P.Wp_circular_cm2(40, 15, "C") == pytest.approx(1600.0)
    # ∫|R cos θ|·R dθ = 4R² = (2R)²
    R = 50.0
    n = 100000
    W = sum(abs(R * math.cos(2 * math.pi * (i + 0.5) / n)) * R * 2 * math.pi / n for i in range(n))
    assert W == pytest.approx(10000.0, rel=1e-6)


def test_19_5_2_2_tau_sd_com_momento():
    """τSd = FSd/(ud) + K·MSd/(Wp·d) (p. 184). C1 = C2 = 40, d = 15, FSd = 600 kN, MSd = 3000 kN·cm.

    u = 160 + 60π = 348,4956; FSd/(ud) = 600/5227,43 = 0,114779 kN/cm²;
    K = 0,60; Wp = 12169,911; K·MSd/(Wp·d) = 1800/182548,67 = 0,0098604 kN/cm²;
    τSd = 0,1246395 kN/cm² = 1,246395 MPa.
    """
    u = 160 + 60 * math.pi
    Wp = 8400 + 1200 * math.pi
    esperado = (600 / (u * 15) + 0.6 * 3000 / (Wp * 15)) * 10
    assert P.tau_Sd_interno_mpa(600, 40, 40, 15, 3000) == pytest.approx(esperado, rel=1e-12)
    assert esperado == pytest.approx(1.246395, rel=1e-5)


def test_19_5_2_2_momento_nulo_reduz_ao_simetrico():
    """MSd = 0 reduz 19.5.2.2 a 19.5.2.1, mesmo com C1/C2 fora da Tabela 19.2."""
    u = 2 * (80 + 20) + 60 * math.pi
    assert P.tau_Sd_interno_mpa(600, 80, 20, 15) == pytest.approx(600 / (u * 15) * 10)
    assert P.tau_Sd_mpa(600, u, 15, 0.0, 0.6, 1000.0) == pytest.approx(600 / (u * 15) * 10)


def test_19_5_2_2_momento_sem_k_ou_wp():
    with pytest.raises(ValueError):
        P.tau_Sd_mpa(600, 300, 15, 1000.0)


def test_19_5_2_2_circular():
    """Pilar circular: K = 0,6, Wp = (D + 4d)², u = π(D + 4d). D = 40, d = 15, FSd = 500, MSd = 2000."""
    u = 100 * math.pi
    esperado = (500 / (u * 15) + 0.6 * 2000 / (10000 * 15)) * 10
    assert P.tau_Sd_interno_circular_mpa(500, 40, 15, 2000) == pytest.approx(esperado)


# ===========================================================================
# 19.5.2.3 -- pilares de borda (PDF p. 185-186)
# ===========================================================================
def test_19_5_2_3_u_estrela_borda():
    """u* = 2a + C2 + 2πd, a = min(1,5d; 0,5C1) (Figura 19.3, p. 185).

    C1 = 40, C2 = 20, d = 15: a = min(22,5; 20) = 20; u* = 40 + 20 + 30π = 154,248.
    C1 = 60: a = min(22,5; 30) = 22,5 (os dois lados do min).
    """
    assert P.a_estrela_cm(40, 15) == pytest.approx(20.0)
    assert P.a_estrela_cm(60, 15) == pytest.approx(22.5)
    assert P.a_estrela_cm(45, 15) == pytest.approx(22.5)   # empate: 1,5d = 0,5C1
    assert P.u_estrela_cm(40, 20, 15, "borda") == pytest.approx(60 + 30 * math.pi)
    L, _, _ = _integrais(_perimetro_borda(40, 20, 30, a=20), 0, 20.0)
    assert P.u_estrela_cm(40, 20, 15, "borda") == pytest.approx(L, rel=1e-6)
    with pytest.raises(ValueError):
        P.u_estrela_cm(40, 20, 15, "interno")


def test_19_5_2_3_perimetro_borda():
    """u = 2C1 + C2 + 2πd (Figura 19.3); u0 = 2C1 + C2."""
    L, _, _ = _integrais(_perimetro_borda(40, 20, 30), 0, 20.0)
    assert P.perimetro_critico_cm(40, 20, 15, "borda") == pytest.approx(L, rel=1e-6)
    assert P.perimetro_critico_cm(40, 20, 15, "borda", "C") == pytest.approx(100.0)


@pytest.mark.parametrize("c1, c2, d", [(40, 20, 15), (60, 30, 12), (20, 60, 16)])
def test_19_5_2_3_wp1_wp2_e_excentricidade_por_integracao(c1, c2, d):
    """Wp1, Wp2 (calculados para u) e e* de u* conferidos por integração numérica."""
    r = 2 * d
    _, W1, _ = _integrais(_perimetro_borda(c1, c2, r), 0, c1 / 2)
    _, W2, _ = _integrais(_perimetro_borda(c1, c2, r), 1, 0.0)
    assert P.Wp1_borda_cm2(c1, c2, d) == pytest.approx(W1, rel=1e-6)
    assert P.Wp2_borda_cm2(c1, c2, d) == pytest.approx(W2, rel=1e-6)
    a = min(1.5 * d, 0.5 * c1)
    L, _, S = _integrais(_perimetro_borda(c1, c2, r, a=a), 0, c1 / 2)
    assert P.excentricidade_u_estrela_cm(c1, c2, d, "borda") == pytest.approx(S / L, rel=1e-6)
    # contorno C: integral sobre u0 = 2C1 + C2
    _, W10, _ = _integrais(_perimetro_borda(c1, c2, 0.0), 0, c1 / 2)
    assert P.Wp1_borda_cm2(c1, c2, d, "C") == pytest.approx(W10, rel=1e-6)


def test_19_5_2_3a_msd_igual_msd_estrela():
    """MSd = MSd* -> MSd1 = 0 e τSd = FSd/(u*·d) (19.5.2.3 a, p. 185)."""
    F, c1, c2, d = 400.0, 40.0, 20.0, 15.0
    e = P.excentricidade_u_estrela_cm(c1, c2, d)
    assert P.MSd1_borda_kncm(F, F * e, c1, c2, d) == pytest.approx(0.0, abs=1e-9)
    assert P.MSd1_borda_kncm(F, 0.5 * F * e, c1, c2, d) == 0.0   # (MSd − MSd*) >= 0
    us = 60 + 30 * math.pi
    assert P.tau_Sd_borda_mpa(F, c1, c2, d, F * e) == pytest.approx(F / (us * d) * 10, rel=1e-9)


def test_19_5_2_3a_caso_montado_a_mao():
    """Borda: C1 = 40 (perp.), C2 = 20, d = 15, FSd = 400 kN, MSd = 10000 kN·cm.

    a = 20; u* = 60 + 30π = 154,2478.
    e* = [20·40 − 400 + 400 + 600 + 600π + 1800]/u* = (3200 + 1884,956)/154,2478 = 32,9662 cm.
    MSd* = 400·32,9662 = 13186,5 > 10000 -> MSd1 = 0; τSd = 400/(154,2478·15)·10 = 1,72882 MPa.
    Com MSd = 20000: MSd1 = 6813,54; K1 = K(40/20 = 2) = 0,70;
    Wp1 = 800 + 400 + 600 + 1800 + 600π = 5484,956;
    τSd = [400/(154,2478·15) + 0,7·6294,92/(5484,956·15)]·10.
    """
    us = 60 + 30 * math.pi
    e = (3200 + 600 * math.pi) / us
    assert P.excentricidade_u_estrela_cm(40, 20, 15) == pytest.approx(e, rel=1e-12)
    assert e == pytest.approx(32.9662, rel=1e-5)
    assert P.tau_Sd_borda_mpa(400, 40, 20, 15, 10000) == pytest.approx(400 / (us * 15) * 10)
    M1 = 20000 - 400 * e
    Wp1 = 3600 + 600 * math.pi
    esperado = (400 / (us * 15) + 0.7 * M1 / (Wp1 * 15)) * 10
    assert P.tau_Sd_borda_mpa(400, 40, 20, 15, 20000) == pytest.approx(esperado, rel=1e-12)


def test_19_5_2_3b_msd2_nulo_reduz_ao_caso_a():
    """19.5.2.3 b com MSd2 = 0 é o caso a (p. 185)."""
    a = P.tau_Sd_borda_mpa(400, 40, 20, 15, 20000)
    b = P.tau_Sd_borda_mpa(400, 40, 20, 15, 20000, 0.0)
    assert a == b


def test_19_5_2_3b_com_momento_paralelo():
    """K2 com C2/(2C1) na Tabela 19.2 (p. 186); Wp2 para u.

    C1 = 20 (perp.), C2 = 40, d = 15, FSd = 400, MSd = 0, MSd2 = 5000:
    C2/(2C1) = 1,0 -> K2 = 0,60; Wp2 = 1600/4 + 800 + 4·20·15 + 8·225 + 40·15π
    = 400 + 800 + 1200 + 1800 + 600π = 4200 + 1884,956.
    a = min(22,5; 10) = 10; u* = 20 + 40 + 30π.
    """
    us = 60 + 30 * math.pi
    Wp2 = 4200 + 600 * math.pi
    assert P.Wp2_borda_cm2(20, 40, 15) == pytest.approx(Wp2)
    esperado = (400 / (us * 15) + 0.6 * 5000 / (Wp2 * 15)) * 10
    assert P.tau_Sd_borda_mpa(400, 20, 40, 15, 0.0, 5000) == pytest.approx(esperado, rel=1e-12)


def test_19_5_2_3b_k2_fora_da_tabela():
    """C2/(2C1) = 20/80 = 0,25 < 0,5: K2 não definido."""
    with pytest.raises(nbr.FaixaNormativaError):
        P.tau_Sd_borda_mpa(400, 40, 20, 15, 0.0, 5000)


# ===========================================================================
# 19.5.2.4 -- pilares de canto (PDF p. 186)
# ===========================================================================
def test_19_5_2_4_u_estrela_e_wp_canto():
    """u* = a1 + a2 + πd (Figura 19.4); Wp1 e e* por integração numérica."""
    c1, c2, d = 40.0, 25.0, 15.0
    a1, a2 = min(22.5, 20.0), min(22.5, 12.5)
    assert P.u_estrela_cm(c1, c2, d, "canto") == pytest.approx(a1 + a2 + 15 * math.pi)
    assert P.perimetro_critico_cm(c1, c2, d, "canto") == pytest.approx(65 + 15 * math.pi)
    assert P.perimetro_critico_cm(c1, c2, d, "canto", "C") == pytest.approx(65.0)
    _, W1, _ = _integrais(_perimetro_canto(c1, c2, 2 * d), 0, c1 / 2)
    assert P.Wp1_canto_cm2(c1, c2, d) == pytest.approx(W1, rel=1e-6)
    L, _, S = _integrais(_perimetro_canto(c1, c2, 2 * d, a1, a2), 0, c1 / 2)
    assert L == pytest.approx(P.u_estrela_cm(c1, c2, d, "canto"), rel=1e-6)
    assert P.excentricidade_u_estrela_cm(c1, c2, d, "canto") == pytest.approx(S / L, rel=1e-6)


def test_19_5_2_4_canto_simetrico():
    """Pilar de canto quadrado com momentos iguais: as duas verificações coincidem."""
    t1 = P.tau_Sd_canto_mpa(250, 30, 30, 12, 15000)
    t2 = P.tau_Sd_canto_mpa(250, 30, 30, 12, 15000)
    assert t1 == t2
    r = P.verificar_puncao(30, 12, 250, 30, 30, "canto", 15000, 15000, 0.01, 0.01)
    assert r.tau_Sd_Cl_mpa == pytest.approx(t1)


def test_19_5_2_4_canto_montado_a_mao():
    """Canto: C1 = 30, C2 = 30, d = 12, FSd = 250 kN, MSd = 15000 kN·cm.

    a1 = a2 = min(18, 15) = 15; u* = 30 + 12π = 67,6991.
    e* = [(15·30 − 225)/2 + π·12·30/2 + 4·144 + 15·(15 + 24)]/u*
       = (112,5 + 180π + 576 + 585)/67,6991 = 1839,996/67,6991 = 27,1791 cm.
    MSd1 = 15000 − 250·27,1791 = 8205,23 kN·cm; K = K(1) = 0,60;
    Wp1 = 900/4 + 450 + 2·30·12 + 4·144 + π·12·30/2 = 225 + 450 + 720 + 576 + 180π.
    """
    us = 30 + 12 * math.pi
    e = (112.5 + 180 * math.pi + 576 + 585) / us
    assert P.excentricidade_u_estrela_cm(30, 30, 12, "canto") == pytest.approx(e, rel=1e-12)
    M1 = 15000 - 250 * e
    Wp1 = 1971 + 180 * math.pi
    esperado = (250 / (us * 12) + 0.6 * M1 / (Wp1 * 12)) * 10
    assert P.tau_Sd_canto_mpa(250, 30, 30, 12, 15000) == pytest.approx(esperado, rel=1e-12)


def test_19_5_2_4_canto_retangular_duas_bordas():
    """Pilar de canto 40 × 25: cada borda com C1 perpendicular a ela; vale a maior τSd."""
    ta = P.tau_Sd_canto_mpa(250, 40, 25, 12, 12000)
    tb = P.tau_Sd_canto_mpa(250, 25, 40, 12, 9000)
    r = P.verificar_puncao(30, 12, 250, 40, 25, "canto", 12000, 9000, 0.01, 0.01)
    assert r.tau_Sd_Cl_mpa == pytest.approx(max(ta, tb))


# ===========================================================================
# 19.5.3.1 -- τRd2 (PDF p. 188)
# ===========================================================================
def test_19_5_3_1_tau_rd2_c25():
    """τRd2 = 0,27·αv·fcd: C25 -> 0,27·0,9·25/1,4 = 4,33929 MPa; ampliado 20 % = 5,20714."""
    assert P.tau_Rd2_mpa(25) == pytest.approx(0.27 * 0.9 * 25 / 1.4, rel=1e-12)
    assert P.tau_Rd2_mpa(25) == pytest.approx(4.33929, rel=1e-5)
    assert P.tau_Rd2_mpa(25, ampliar_20pct=True) == pytest.approx(1.2 * 0.27 * 0.9 * 25 / 1.4)


@pytest.mark.parametrize("fck", [20.0, 50.0, 90.0])
def test_19_5_3_1_tau_rd2_faixa(fck):
    """Bordas da faixa de fck (8.2.1): αv = 1 − fck/250."""
    assert P.tau_Rd2_mpa(fck) == pytest.approx(0.27 * (1 - fck / 250) * fck / 1.4)


def test_19_5_3_1_fora_da_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        P.tau_Rd2_mpa(95)
    with pytest.raises(ValueError):
        P.verificar_puncao(25, 15, 100, 20, 40, "borda", ampliar_tau_Rd2=True)


# ===========================================================================
# 19.5.3.2 -- τRd1 sem armadura (PDF p. 188-189)
# ===========================================================================
def test_19_5_3_2_tau_rd1_c25():
    """C25, ρ = 0,01, d = 20, σcp = 0: ke = 1 + √1 = 2; τRd1 = 0,13·2·25^(1/3) = 0,760245 MPa."""
    assert P.tau_Rd1_mpa(25, 0.01, 20) == pytest.approx(0.26 * 25 ** (1 / 3), rel=1e-12)
    assert P.tau_Rd1_mpa(25, 0.01, 20) == pytest.approx(0.760245, rel=1e-5)


@pytest.mark.parametrize("d, ke", [(10.0, 2.0), (20.0, 2.0), (19.0, 2.0), (21.0, 1 + math.sqrt(20 / 21)),
                                   (80.0, 1.5)])
def test_19_5_3_2_ke_teto(d, ke):
    """ke = 1 + √(20/d) <= 2, d em cm: teto até d = 20 cm."""
    assert P.ke_puncao(d) == pytest.approx(ke)


def test_19_5_3_2_rho():
    """ρ = √(ρx·ρy) <= 0,02."""
    assert P.rho_puncao(0.01, 0.016) == pytest.approx(math.sqrt(0.016e-2))
    assert P.rho_puncao(0.02, 0.02) == pytest.approx(0.02)
    assert P.rho_puncao(0.03, 0.025) == pytest.approx(0.02)
    assert P.tau_Rd1_mpa(25, 0.03, 20) == pytest.approx(P.tau_Rd1_mpa(25, 0.02, 20))


@pytest.mark.parametrize("sx, sy, esperado", [
    (1.0, 5.0, 0.0),       # σcp,x <= 1 MPa: despreza
    (5.0, 1.0, 0.0),
    (1.01, 5.0, 3.005),
    (2.0, 3.0, 2.5),
    (3.5, 3.5, 3.5),
    (4.0, 6.0, 3.5),       # média 5 > 3,5: teto
    (0.0, 0.0, 0.0),
])
def test_19_5_3_2_sigma_cp(sx, sy, esperado):
    """σcp = (σcp,x + σcp,y)/2 <= 3,5 MPa; zero se σcp,x ou σcp,y <= 1 MPa (p. 189)."""
    assert P.sigma_cp_puncao_mpa(sx, sy) == pytest.approx(esperado)


def test_19_5_3_2_tau_rd1_com_sigma_cp():
    """+0,10·σcp: σcp = 2,5 -> +0,25 MPa."""
    assert P.tau_Rd1_mpa(25, 0.01, 20, 2.5) == pytest.approx(0.26 * 25 ** (1 / 3) + 0.25)
    with pytest.raises(nbr.FaixaNormativaError):
        P.tau_Rd1_mpa(25, 0.01, 20, 3.6)


# ===========================================================================
# 19.5.3.3 -- τRd3 com armadura (PDF p. 189-190)
# ===========================================================================
def test_19_5_3_3_tau_rd3_caso_a_mao():
    """C25, ρ = 0,01, d = 20, Asw = 10 cm², sr = 15 cm, fywd = 300 MPa (studs), u = 300 cm, α = 90°.

    Concreto: 0,10·2·25^(1/3) = 0,584804 MPa.
    Armadura: 1,5·(20/15)·10·300·1/(300·20) = 1,0 MPa. τRd3 = 1,584804 MPa.
    """
    esperado = 0.2 * 25 ** (1 / 3) + 1.0
    assert P.tau_Rd3_mpa(25, 0.01, 20, 10, 15, 300, 300) == pytest.approx(esperado, rel=1e-12)


def test_19_5_3_3_asw_nulo_nao_reduz_a_tau_rd1():
    """Descontinuidade da norma: com Asw = 0, τRd3 = 0,10/0,13 da parcela de τRd1 (não é igual)."""
    rd3 = P.tau_Rd3_mpa(25, 0.01, 20, 0.0, 15, 300, 300)
    rd1 = P.tau_Rd1_mpa(25, 0.01, 20)
    assert rd3 == pytest.approx(rd1 * 0.10 / 0.13, rel=1e-12)
    assert rd3 < rd1


def test_19_5_3_3_sr_limite():
    """sr <= 0,75·d: 15 cm passa com d = 20; 15,01 cm não."""
    P.tau_Rd3_mpa(25, 0.01, 20, 10, 15.0, 300, 300)
    with pytest.raises(nbr.FaixaNormativaError):
        P.tau_Rd3_mpa(25, 0.01, 20, 10, 15.01, 300, 300)


def test_19_5_3_3_alfa():
    """sen α: α = 45° multiplica a parcela da armadura por √2/2."""
    base = 0.2 * 25 ** (1 / 3)
    assert P.tau_Rd3_mpa(25, 0.01, 20, 10, 15, 300, 300, 45.0) == pytest.approx(
        base + math.sqrt(2) / 2)
    with pytest.raises(nbr.FaixaNormativaError):
        P.tau_Rd3_mpa(25, 0.01, 20, 10, 15, 300, 300, 95.0)


@pytest.mark.parametrize("tipo, h, teto", [
    ("studs", None, 300.0),
    ("estribos", None, 250.0),
    ("studs", 15.0, 300.0),
    ("estribos", 15.0, 250.0),
    ("estribos", 18.0, 250 + 185 * 3 / 20),      # 277,75 (reta de 19.4.2)
    ("studs", 18.0, 300.0),                      # reta < 300: fica 300
    ("studs", 25.0, 342.5),                      # 250 + 185·0,5
    ("estribos", 25.0, 342.5),
    ("studs", 40.0, 435.0),
    ("estribos", 35.0, 435.0),
])
def test_19_5_3_3_teto_fywd(tipo, h, teto):
    """fywd <= 300 MPa (studs) ou 250 MPa (estribos); h > 15 cm: aumento de 19.4.2 (p. 182 e 190)."""
    assert P.fywd_max_puncao_mpa(tipo, h) == pytest.approx(teto)


def test_19_5_3_3_fywd_limitado():
    """fywd = 435 com estribos e sem h: usa 250 MPa. Armadura: 1,5·(20/15)·10·250/(300·20) = 0,8333."""
    esperado = 0.2 * 25 ** (1 / 3) + 1.5 * (20 / 15) * 10 * 250 / 6000
    assert P.tau_Rd3_mpa(25, 0.01, 20, 10, 15, 435, 300, tipo_armadura="estribos") == pytest.approx(
        esperado)


# ===========================================================================
# verificar_puncao -- C, C′ e C″
# ===========================================================================
# Caso interno montado à mão: C30, C1 = C2 = 40 cm, d = 15 cm, FSd = 600 kN, ρx = ρy = 0,012.
#   u0 = 160; τSd,C = 600/(160·15)·10 = 2,5 MPa
#   τRd2 = 0,27·(1 − 30/250)·30/1,4 = 0,27·0,88·21,428571 = 5,091429 MPa
#   u = 160 + 60π = 348,4956; τSd,C′ = 600/(348,4956·15)·10 = 1,147790 MPa
#   ke = 1 + √(20/15) = 2,1547 -> 2; (100·0,012·30)^(1/3) = 36^(1/3) = 3,301927
#   τRd1 = 0,26·3,301927 = 0,858501 MPa < τSd -> armadura necessária
#   studs, h = 18 cm (teto 300), Asw = 5 cm², sr = 11,25 cm = 0,75d, fywd = 300:
#   τRd3 = 0,2·3,301927 + 1,5·(15/11,25)·5·300/(348,4956·15) = 0,660385 + 0,573890 = 1,234275 MPa
#   C″ com u″ = 600 cm: τSd = 600/(600·15)·10 = 0,666667 <= 0,858501
U_INT = 160 + 60 * math.pi
RD1_INT = 0.26 * 36 ** (1 / 3)


def test_verificar_interno_sem_armadura_nao_passa():
    r = P.verificar_puncao(30, 15, 600, 40, 40, rho_x=0.012, rho_y=0.012)
    assert r.tau_Sd_C_mpa == pytest.approx(2.5)
    assert r.tau_Rd2_mpa == pytest.approx(0.27 * 0.88 * 30 / 1.4)
    assert r.tau_Sd_Cl_mpa == pytest.approx(600 / (U_INT * 15) * 10)
    assert r.tau_Rd1_mpa == pytest.approx(RD1_INT)
    assert r.armadura_necessaria and not r.ok
    assert "C′" in r.governante
    assert r.status_C == "ok"


def test_verificar_interno_com_armadura_e_c2linha():
    r = P.verificar_puncao(30, 15, 600, 40, 40, rho_x=0.012, rho_y=0.012,
                           Asw_cm2=5, sr_cm=11.25, fywd_mpa=300, h_cm=18, u_C2l_cm=600)
    rd3 = 0.2 * 36 ** (1 / 3) + 1.5 * (15 / 11.25) * 5 * 300 / (U_INT * 15)
    assert r.tau_Rd3_mpa == pytest.approx(rd3)
    assert r.tau_Rd3_mpa == pytest.approx(1.234275, rel=1e-5)
    assert r.tau_Sd_C2l_mpa == pytest.approx(600 / (600 * 15) * 10)
    assert r.tau_Rd1_C2l_mpa == pytest.approx(RD1_INT)
    assert r.ok
    assert r.status_Cl == "ok com armadura de punção"
    assert r.status_C2l == "ok"


def test_verificar_interno_sem_c2linha_nao_fecha():
    """Com armadura necessária, C″ é obrigatório (19.5.3.4): sem u″, ok é falso."""
    r = P.verificar_puncao(30, 15, 600, 40, 40, rho_x=0.012, rho_y=0.012,
                           Asw_cm2=5, sr_cm=11.25, fywd_mpa=300, h_cm=18)
    assert not r.ok
    assert "C″" in r.governante


def test_verificar_c2linha_nao_passa():
    """u″ = 400: τSd = 600/(400·15)·10 = 1,0 > 0,8585 -> estender a armadura."""
    r = P.verificar_puncao(30, 15, 600, 40, 40, rho_x=0.012, rho_y=0.012,
                           Asw_cm2=5, sr_cm=11.25, fywd_mpa=300, h_cm=18, u_C2l_cm=400)
    assert r.tau_Sd_C2l_mpa == pytest.approx(1.0)
    assert not r.ok and "C″" in r.governante


def test_verificar_contorno_c_governa():
    """FSd = 1300 kN: τSd,C = 1300/2400·10 = 5,4167 > 5,0914 (C); com +20 %, 6,1097 passa."""
    r = P.verificar_puncao(30, 15, 1300, 40, 40, rho_x=0.012, rho_y=0.012)
    assert not r.ok and r.status_C == "não passa"
    assert "Contorno C:" in r.governante
    r2 = P.verificar_puncao(30, 15, 1300, 40, 40, rho_x=0.012, rho_y=0.012, ampliar_tau_Rd2=True)
    assert r2.status_C == "ok"


def test_verificar_interno_com_momento_nos_dois_planos():
    """Momentos nos dois planos: soma das parcelas, K(C1/C2) com Wp(C1, C2) e K(C2/C1) com Wp(C2, C1)."""
    c1, c2, d = 60.0, 30.0, 15.0
    u = 180 + 60 * math.pi
    W1 = 1800 + 1800 + 4 * 30 * 15 + 16 * 225 + 2 * math.pi * 15 * 60
    W2 = 450 + 1800 + 4 * 60 * 15 + 16 * 225 + 2 * math.pi * 15 * 30
    esperado = (500 / (u * d) + 0.70 * 4000 / (W1 * d) + 0.45 * 3000 / (W2 * d)) * 10
    r = P.verificar_puncao(30, d, 500, c1, c2, "interno", 4000, 3000, 0.012, 0.012)
    assert r.tau_Sd_Cl_mpa == pytest.approx(esperado, rel=1e-12)


def test_verificar_borda_usa_u_estrela():
    """Borda: τSd em C′ com u* e MSd1 = MSd − MSd*; τRd1 igual ao interno."""
    r = P.verificar_puncao(25, 15, 400, 40, 20, "borda", 20000, 0.0, 0.01, 0.01)
    assert r.u_cm == pytest.approx(60 + 30 * math.pi)
    assert r.u0_cm == pytest.approx(100.0)
    assert r.tau_Sd_Cl_mpa == pytest.approx(P.tau_Sd_borda_mpa(400, 40, 20, 15, 20000))
    # contorno C: u0 = 2C1 + C2 = 100, momento inteiro, Wp1 sobre u0 = 800 + 400 = 1200
    esperado_C = (400 / (100 * 15) + 0.7 * 20000 / (1200 * 15)) * 10
    assert r.tau_Sd_C_mpa == pytest.approx(esperado_C)


def test_verificar_circular():
    r = P.verificar_puncao(25, 15, 500, 40, tipo="interno", MSd1_kncm=2000, circular=True,
                           rho_x=0.01, rho_y=0.01)
    assert r.tau_Sd_Cl_mpa == pytest.approx(P.tau_Sd_interno_circular_mpa(500, 40, 15, 2000))
    assert r.u0_cm == pytest.approx(40 * math.pi)
    with pytest.raises(ValueError):
        P.verificar_puncao(25, 15, 500, 40, tipo="borda", circular=True)


def test_memoria_em_portugues():
    r = P.verificar_puncao(30, 15, 600, 40, 40, "interno", 3000, 0, 0.012, 0.012)
    texto = "\n".join(r.memoria)
    assert "Tabela 19.2" in texto and "interpolado" in texto
    assert "τRd1" in texto and "τRd2" in texto
