"""Testes do P20 -- Punção: casos especiais, robustez e detalhamento (NBR 6118:2026).

Valores esperados tirados das imagens das páginas do PDF (SCRATCH/nbr_png):
p184 (19.5.2.2, Wp = ∫|e|dℓ), p186-187 (19.5.2.5, Figura 19.5), p187-188
(19.5.2.6, Figuras 19.6 e 19.7), p190-191 (19.5.3.4, Figuras 19.8 e 19.9;
19.5.3.5; 19.5.4), p191-192 (19.5.5, Figura 19.11), p196 (20.4), p201
(21.3.4 c) e p212 (22.6.2.3).

As integrais de contorno são conferidas contra as fórmulas fechadas do P19 e
contra uma integração numérica independente (amostragem densa do contorno
paralelo, sem usar a geometria da biblioteca).
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import puncao_nbr6118 as P  # noqa: E402
import sapatas_nbr6118 as S  # noqa: E402

FE = nbr.FaixaNormativaError


def ret(c1, c2, x0=0.0, y0=0.0):
    return [(x0 - c1 / 2, y0 - c2 / 2), (x0 + c1 / 2, y0 - c2 / 2),
            (x0 + c1 / 2, y0 + c2 / 2), (x0 - c1 / 2, y0 + c2 / 2)]


# ---------------------------------------------------------------------------
# Integração independente: contorno paralelo = fronteira da soma de Minkowski
# do polígono convexo com o disco de raio r. Para cada direção n(φ), o ponto
# do contorno é o vértice de suporte + r·n(φ). Amostragem densa em φ e nos
# lados (entre dois φ com o mesmo vértice de suporte a curva é arco; a troca
# de vértice gera o trecho reto).
# ---------------------------------------------------------------------------
def _contorno_amostrado(verts, r, n=200000):
    pts = []
    for i in range(n):
        f = 2 * math.pi * i / n
        nx, ny = math.cos(f), math.sin(f)
        v = max(verts, key=lambda p: p[0] * nx + p[1] * ny)
        pts.append((v[0] + r * nx, v[1] + r * ny))
    return pts


def _integrais_amostra(pts, centro, dir_graus, excluir=None):
    a = math.radians(dir_graus)
    nx, ny = math.cos(a), math.sin(a)
    L = W = 0.0
    for i in range(len(pts)):
        q0, q1 = pts[i], pts[(i + 1) % len(pts)]
        k = max(1, math.ceil(math.hypot(q1[0] - q0[0], q1[1] - q0[1]) / 0.01))
        for j in range(k):  # trechos retos longos: subdividir (e pode trocar de sinal)
            p0 = (q0[0] + (q1[0] - q0[0]) * j / k, q0[1] + (q1[1] - q0[1]) * j / k)
            p1 = (q0[0] + (q1[0] - q0[0]) * (j + 1) / k, q0[1] + (q1[1] - q0[1]) * (j + 1) / k)
            pm = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
            if excluir is not None and excluir(pm):
                continue
            dl = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            L += dl
            W += abs((pm[0] - centro[0]) * nx + (pm[1] - centro[1]) * ny) * dl
    return L, W


# ---------------------------------------------------------------------------
# 19.5.2.2 — Wp genérico por integração (PDF p. 184)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("c1,c2,d", [(40, 60, 15), (40, 60, 20), (20, 80, 18), (100, 25, 30)])
def test_wp_generico_reproduz_retangular(c1, c2, d):
    # 19.5.2.2: Wp = C1²/2 + C1·C2 + 4·C2·d + 16·d² + 2·π·d·C1 (C1 na direção x)
    assert P.Wp_generico_cm2(ret(c1, c2), d, 0.0) == pytest.approx(
        P.Wp_retangular_cm2(c1, c2, d), rel=1e-12)
    # excentricidade em y: C1 e C2 trocam de papel
    assert P.Wp_generico_cm2(ret(c1, c2), d, 90.0) == pytest.approx(
        P.Wp_retangular_cm2(c2, c1, d), rel=1e-12)
    # sentido do polígono e excentricidade de sentido oposto não mudam Wp
    assert P.Wp_generico_cm2(list(reversed(ret(c1, c2))), d, 180.0) == pytest.approx(
        P.Wp_retangular_cm2(c1, c2, d), rel=1e-12)


def test_wp_generico_contorno_C():
    # Integral sobre u0 do retângulo: Wp0 = C1²/2 + C1·C2 = 800 + 2400 = 3200
    assert P.Wp_generico_cm2(ret(40, 60), 20, 0.0, "C") == pytest.approx(3200.0, rel=1e-12)


def test_wp_generico_retangulo_girado():
    # Pilar 40x60 girado de 30°, excentricidade girada de 30°: mesmo Wp do alinhado
    c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
    pol = [(x * c - y * s + 7.0, x * s + y * c - 3.0) for x, y in ret(40, 60)]
    assert P.Wp_generico_cm2(pol, 20, 30.0) == pytest.approx(P.Wp_retangular_cm2(40, 60, 20), rel=1e-12)


def test_wp_generico_reproduz_circular():
    # Pilar circular D = 50 como polígono regular inscrito de 720 lados:
    # Wp -> (D + 4d)² = 130² = 16 900; u -> π·(D + 4d); Wp0 -> D² = 2 500.
    N, D, d = 720, 50.0, 20.0
    circ = [(D / 2 * math.cos(2 * math.pi * i / N), D / 2 * math.sin(2 * math.pi * i / N)) for i in range(N)]
    assert P.Wp_generico_cm2(circ, d, 0.0) == pytest.approx(P.Wp_circular_cm2(D, d), rel=1e-5)
    assert P.Wp_generico_cm2(circ, d, 57.0) == pytest.approx(P.Wp_circular_cm2(D, d), rel=1e-5)
    assert P.perimetro_com_reentrancia_cm(circ, d) == pytest.approx(
        P.perimetro_critico_circular_cm(D, d), rel=1e-5)
    assert P.Wp_generico_cm2(circ, d, 0.0, "C") == pytest.approx(D * D, rel=1e-4)


def test_wp_generico_cantos_retos():
    # "Wp pode ser calculado desprezando a curvatura dos cantos": contorno
    # retangular (C1 + 4d) x (C2 + 4d). À mão, com e medido na direção de C1:
    #   lados paralelos ao eixo: 2·(C2 + 4d)·(C1/2 + 2d)
    #   lados perpendiculares:   2·(C1 + 4d)²/4
    # = C1²/2 + C1·C2 + 4·C2·d + 8·d·C1 + 24·d²; C1=40, C2=60, d=20:
    # 800 + 2400 + 4800 + 6400 + 9600 = 24 000
    assert P.Wp_generico_cm2(ret(40, 60), 20, 0.0, cantos="retos") == pytest.approx(24000.0, rel=1e-12)
    cont = P.contorno_critico(ret(40, 60), 20, cantos="retos")
    assert cont.u_cm == pytest.approx(2 * (120 + 140), rel=1e-12)


def test_wp_generico_forma_qualquer_contra_amostragem():
    # Pilar em L: Wp contra integração independente sobre a envoltória convexa
    L_pol = [(0, 0), (60, 0), (60, 30), (30, 30), (30, 60), (0, 60)]
    hull = [(0, 0), (60, 0), (60, 30), (30, 60), (0, 60)]
    d = 15.0
    cg = P.centroide_cm(L_pol)
    # CG do L: área 2700; x = (1800·30 + 900·15)/2700 = 25
    assert cg[0] == pytest.approx(25.0) and cg[1] == pytest.approx(25.0)
    pts = _contorno_amostrado(hull, 2 * d)
    for ang in (0.0, 45.0, 90.0, 120.0):
        Lr, Wr = _integrais_amostra(pts, cg, ang)
        assert P.Wp_generico_cm2(L_pol, d, ang) == pytest.approx(Wr, rel=2e-5)
    assert P.perimetro_com_reentrancia_cm(L_pol, d) == pytest.approx(Lr, rel=2e-6)


def test_wp_generico_erros():
    with pytest.raises(ValueError):
        P.Wp_generico_cm2([(0, 0), (1, 0)], 10)
    with pytest.raises(ValueError):
        P.Wp_generico_cm2([(0, 0), (1, 0), (2, 0)], 10)
    with pytest.raises(FE):
        P.Wp_generico_cm2(ret(40, 40), 0.0)
    with pytest.raises(ValueError):
        P.Wp_generico_cm2(ret(40, 40), 20, cantos="chanfrado")


# ---------------------------------------------------------------------------
# 19.5.2.6 — Contorno com reentrância (Figura 19.6, PDF p. 187)
# ---------------------------------------------------------------------------
def test_reentrancia_poligono_convexo_circunscrito():
    L_pol = [(0, 0), (60, 0), (60, 30), (30, 30), (30, 60), (0, 60)]
    hull = P.poligono_convexo_circunscrito(L_pol)
    assert set(hull) == {(0.0, 0.0), (60.0, 0.0), (60.0, 30.0), (30.0, 60.0), (0.0, 60.0)}
    d = 20.0
    # Figura 19.6: C′ paralelo ao polígono circunscrito (a reentrância é
    # fechada pela reta tracejada, não pelo retângulo envolvente).
    # u = 60 + 30 + 30·√2 + 30 + 60 + 2·π·2d
    u = 180.0 + 30.0 * math.sqrt(2.0) + 4.0 * math.pi * d
    assert P.perimetro_com_reentrancia_cm(L_pol, d) == pytest.approx(u, rel=1e-12)
    assert P.perimetro_com_reentrancia_cm(L_pol, d) < 240.0 + 4.0 * math.pi * d
    # contorno C: perímetro real do L = 240
    assert P.perimetro_com_reentrancia_cm(L_pol, d, "C") == pytest.approx(240.0, rel=1e-12)
    cont = P.contorno_critico(L_pol, d)
    assert cont.reentrancia is True
    assert any("Figura 19.6" in m for m in cont.memoria)


@pytest.mark.parametrize("tipo_c", ["C", "Cl"])
def test_sem_reentrancia_reproduz_perimetro_p19(tipo_c):
    assert P.perimetro_com_reentrancia_cm(ret(30, 70), 18, tipo_c) == pytest.approx(
        P.perimetro_critico_cm(30, 70, 18, "interno", tipo_c), rel=1e-12)
    assert P.contorno_critico(ret(30, 70), 18).reentrancia is False


# ---------------------------------------------------------------------------
# 19.5.2.6 — Abertura a menos de 8d (Figura 19.7, PDF p. 187-188)
# ---------------------------------------------------------------------------
def test_abertura_trecho_reto_mao():
    # Pilar 40x40 na origem, d = 20: C′ tem o lado x = 20 + 40 = 60, y em [-20, 20].
    # Abertura 40x40 com a face mais próxima em x = 120 (100 cm de C < 8d = 160).
    # Retas tangentes pelo CG passam pelos vértices (120, ±20): tg θ = 20/120.
    # Trecho excluído em x = 60: 2·60·(20/120) = 20 cm.
    # u = 4·40 + 2·π·40 = 411,327; u efetivo = 391,327.
    ab = [(120, -20), (160, -20), (160, 20), (120, 20)]
    c = P.perimetro_com_abertura(ret(40, 40), 20, [ab])
    assert c.u_total_cm == pytest.approx(160 + 80 * math.pi, rel=1e-12)
    assert c.u_excluido_cm == pytest.approx(20.0, rel=1e-12)
    assert c.u_cm == pytest.approx(160 + 80 * math.pi - 20.0, rel=1e-12)
    assert c.aberturas_consideradas == (0,)
    assert c.distancias_aberturas_cm[0] == pytest.approx(100.0)


def test_abertura_a_8d_exatos_nao_reduz():
    # "a menos de 8d": a 8d exatos (160 cm) a abertura não conta
    d = 20.0
    ab = [(180, -20), (220, -20), (220, 20), (180, 20)]
    c = P.perimetro_com_abertura(ret(40, 40), d, [ab])
    assert c.distancias_aberturas_cm[0] == pytest.approx(8 * d)
    assert c.aberturas_consideradas == ()
    assert c.u_cm == pytest.approx(P.perimetro_critico_cm(40, 40, d), rel=1e-12)
    # um pouco mais perto (159,9 cm) já conta: as tangentes passam pelos
    # vértices (179,9; ±20), tg θ = 20/179,9; excluído = 2·60·20/179,9
    ab2 = [(179.9, -20), (220, -20), (220, 20), (179.9, 20)]
    c2 = P.perimetro_com_abertura(ret(40, 40), d, [ab2])
    assert c2.aberturas_consideradas == (0,)
    assert c2.u_excluido_cm == pytest.approx(2 * 60 * 20 / 179.9, rel=1e-12)


def test_abertura_em_diagonal_contra_amostragem():
    # Abertura na diagonal: as retas tangentes cortam o arco de canto e os lados.
    d = 20.0
    ab = [(60, 50), (110, 50), (110, 90), (60, 90)]
    c = P.perimetro_com_abertura(ret(40, 30), d, [ab])
    hull = ret(40, 30)
    angs = [math.atan2(y, x) for x, y in ab]
    lo, hi = min(angs), max(angs)

    def excl(pm):
        return lo <= math.atan2(pm[1], pm[0]) <= hi

    pts = _contorno_amostrado(hull, 2 * d)
    L_ef, W_ef = _integrais_amostra(pts, (0, 0), 0.0, excl)
    assert c.u_cm == pytest.approx(L_ef, rel=1e-5)
    assert P.Wp_generico_cm2(ret(40, 30), d, 0.0, aberturas=[ab]) == pytest.approx(W_ef, rel=1e-4)
    # C (u0) não é descontado
    assert P.perimetro_com_abertura(ret(40, 30), d, [ab], "C").u_cm == pytest.approx(140.0)


def test_duas_aberturas_sobrepostas_contam_uma_vez():
    ab = [(120, -20), (160, -20), (160, 20), (120, 20)]
    c1 = P.perimetro_com_abertura(ret(40, 40), 20, [ab])
    c2 = P.perimetro_com_abertura(ret(40, 40), 20, [ab, ab])
    assert c2.u_excluido_cm == pytest.approx(c1.u_excluido_cm, rel=1e-12)
    assert c2.aberturas_consideradas == (0, 1)


def test_distancia_poligonos():
    assert P.distancia_poligonos_cm(ret(40, 40), ret(10, 10, 50, 0)) == pytest.approx(25.0)
    assert P.distancia_poligonos_cm(ret(40, 40), ret(10, 10, 20, 0)) == 0.0
    assert P.distancia_poligonos_cm(ret(40, 40), ret(10, 10, 50, 50)) == pytest.approx(
        math.hypot(25, 25))


# ---------------------------------------------------------------------------
# 19.5.2.5 — Capitel (Figura 19.5, PDF p. 186-187)
# ---------------------------------------------------------------------------
def test_capitel_lc_zero_recai_no_caso_sem_capitel():
    r = P.contornos_capitel(0.0, 20.0, 20.0, c1_cm=40, c2_cm=60)
    assert (r.verificar_C1l, r.verificar_C2l) == (False, True)
    assert r.afastamento_C2l_cm == pytest.approx(40.0)
    assert r.u_C2l_cm == pytest.approx(P.perimetro_critico_cm(40, 60, 20), rel=1e-12)
    assert r.u_C1l_cm is None


def test_capitel_tres_faixas_e_fronteiras():
    d, dc = 20.0, 35.0      # 2(dc − d) = 30; 2dc = 70
    r = P.contornos_capitel(30.0, d, dc, c1_cm=40, c2_cm=40)          # fronteira: só C2′
    assert (r.verificar_C1l, r.verificar_C2l) == (False, True)
    # u(C2′) = 2·(40 + 40 + 4·30) + 2·π·40 = 400 + 80π
    assert r.u_C2l_cm == pytest.approx(400 + 80 * math.pi, rel=1e-12)
    assert r.afastamento_C2l_cm == pytest.approx(70.0)
    r = P.contornos_capitel(30.01, d, dc, da_cm=30.0, c1_cm=40, c2_cm=40)   # só C1′
    assert (r.verificar_C1l, r.verificar_C2l) == (True, False)
    # u(C1′) = 2·(40 + 40) + 2·π·(2·35) = 160 + 140π
    assert r.u_C1l_cm == pytest.approx(160 + 140 * math.pi, rel=1e-12)
    assert r.afastamento_C1l_cm == pytest.approx(70.0)
    assert r.d_C1l_cm == 30.0
    r = P.contornos_capitel(70.0, d, dc, da_cm=30.0)                    # fronteira: só C1′
    assert (r.verificar_C1l, r.verificar_C2l) == (True, False)
    r = P.contornos_capitel(70.01, d, dc, da_cm=30.0)                   # C1′ e C2′
    assert (r.verificar_C1l, r.verificar_C2l) == (True, True)
    assert r.afastamento_C2l_cm == pytest.approx(110.01)


def test_capitel_erros():
    with pytest.raises(ValueError):
        P.contornos_capitel(50.0, 20.0, 35.0)             # C1′ sem da
    with pytest.raises(FE):
        P.contornos_capitel(10.0, 20.0, 15.0)             # dc < d
    with pytest.raises(FE):
        P.contornos_capitel(-1.0, 20.0, 35.0)


# ---------------------------------------------------------------------------
# 19.5.3.4 — Disposição da armadura até C″ (Figuras 19.8 e 19.9, PDF p. 190)
# ---------------------------------------------------------------------------
def _n_contornos_mao(F, c1, c2, d, rd1, s0, sr):
    n = 1
    while True:
        r2 = s0 + (n - 1) * sr + 2 * d
        u2 = 2 * (c1 + c2) + 2 * math.pi * r2
        tau = F / (u2 * d) * 10
        if tau <= rd1:
            return n, r2, u2, tau
        n += 1


def test_disposicao_ultimo_contorno_a_2d_de_c2l():
    F, c1, c2, d, rd1 = 1500.0, 40.0, 40.0, 20.0, 0.6
    r = P.disposicao_armadura_puncao(F, c1, c2, d, rd1, sr_cm=15.0, s0_cm=10.0)
    n, r2, u2, tau = _n_contornos_mao(F, c1, c2, d, rd1, 10.0, 15.0)
    assert r.n_contornos == n
    assert r.afastamento_C2l_cm == pytest.approx(r2)
    assert r.afastamento_C2l_cm == pytest.approx(r.raios_contornos_cm[-1] + 2 * d)
    assert r.u_C2l_cm == pytest.approx(u2)
    assert r.tau_Sd_C2l_mpa == pytest.approx(tau)
    assert r.ok
    # com um contorno a menos, C″ não passaria
    r2m = 10.0 + (n - 2) * 15.0 + 2 * d
    assert F / ((2 * (c1 + c2) + 2 * math.pi * r2m) * d) * 10 > rd1
    assert r.raios_contornos_cm[0] == 10.0 and r.raios_contornos_cm[1] - r.raios_contornos_cm[0] == 15.0


def test_disposicao_limites_s0_sr():
    # s0 <= 0,50d e sr <= 0,75d (Figura 19.9), igualdade passa
    P.disposicao_armadura_puncao(800, 40, 40, 20, 0.6, sr_cm=15.0, s0_cm=10.0)
    assert P.disposicao_armadura_puncao(800, 40, 40, 20, 0.6, sr_cm=15.0).s0_cm == 10.0
    with pytest.raises(FE):
        P.disposicao_armadura_puncao(800, 40, 40, 20, 0.6, sr_cm=15.0001, s0_cm=10.0)
    with pytest.raises(FE):
        P.disposicao_armadura_puncao(800, 40, 40, 20, 0.6, sr_cm=15.0, s0_cm=10.0001)


def test_disposicao_com_momento_wp_de_c2l():
    F, M1, c1, c2, d, rd1 = 1200.0, 6000.0, 40.0, 60.0, 20.0, 0.55
    r = P.disposicao_armadura_puncao(F, c1, c2, d, rd1, sr_cm=15.0, s0_cm=10.0, MSd1_kncm=M1)
    rr = r.afastamento_C2l_cm
    # Wp com afastamento r: C1²/2 + C1·C2 + 2·C2·r + 4·r² + π·r·C1
    W = c1 ** 2 / 2 + c1 * c2 + 2 * c2 * rr + 4 * rr ** 2 + math.pi * rr * c1
    assert r.Wp_C2l_cm2[0] == pytest.approx(W, rel=1e-12)
    k = P.K(c1 / c2)
    tau = (F / (r.u_C2l_cm * d) + k * M1 / (W * d)) * 10
    assert r.tau_Sd_C2l_mpa == pytest.approx(tau, rel=1e-12)
    assert tau <= rd1


def test_disposicao_espacamento_tangencial():
    F, d = 1500.0, 20.0
    r = P.disposicao_armadura_puncao(F, 40, 40, d, 0.6, sr_cm=15.0, s0_cm=10.0, n_linhas_radiais=16)
    st = (160 + 2 * math.pi * r.raios_contornos_cm[-1]) / 16
    assert r.espacamento_tangencial_cm == pytest.approx(st)
    assert r.ok == (st < 2 * d)
    r8 = P.disposicao_armadura_puncao(F, 40, 40, d, 0.6, sr_cm=15.0, s0_cm=10.0, n_linhas_radiais=4)
    assert r8.espacamento_tangencial_cm >= 2 * d and not r8.ok
    assert "Figura 19.8" in r8.governante


# ---------------------------------------------------------------------------
# 19.5.3.5 — Armadura de punção obrigatória (PDF p. 191)
# ---------------------------------------------------------------------------
def test_armadura_obrigatoria_50pct():
    # FSd = 800 kN -> 0,50·FSd = 400 kN; fywd = 300 MPa = 30 kN/cm²: Asw,min = 13,333 cm²
    r = P.armadura_puncao_obrigatoria(800.0, 300.0)
    assert r.F_min_kn == pytest.approx(400.0)
    assert r.Asw_min_cm2 == pytest.approx(400.0 / 30.0)
    assert r.exigida and not r.ok
    assert P.armadura_puncao_obrigatoria(800.0, 300.0, Asw_cm2=400.0 / 30.0).ok
    assert not P.armadura_puncao_obrigatoria(800.0, 300.0, Asw_cm2=13.3).ok
    # fywd acima do teto de 19.5.3.3 (estribos: 250 MPa) é limitado
    r = P.armadura_puncao_obrigatoria(800.0, 435.0, tipo_armadura="estribos")
    assert r.fywd_mpa == 250.0 and r.Asw_min_cm2 == pytest.approx(16.0)
    # α = 60°: Asw,min = 400/(30·sen 60°)
    assert P.armadura_puncao_obrigatoria(800.0, 300.0, alpha_graus=60.0).Asw_min_cm2 == pytest.approx(
        400.0 / (30.0 * math.sin(math.radians(60))))


def test_armadura_obrigatoria_nao_exigida_e_erros():
    r = P.armadura_puncao_obrigatoria(800.0, 300.0, estabilidade_depende=False)
    assert not r.exigida and r.ok
    with pytest.raises(FE):
        P.armadura_puncao_obrigatoria(800.0, 300.0, alpha_graus=0.0)
    with pytest.raises(FE):
        P.armadura_puncao_obrigatoria(-1.0, 300.0)


# ---------------------------------------------------------------------------
# 19.5.4 — Colapso progressivo (PDF p. 191)
# ---------------------------------------------------------------------------
def test_colapso_progressivo():
    # FSd = 600 kN, fyd = 500/1,15 = 434,78 MPa = 43,478 kN/cm²:
    # As,ccp = 1,5·600/43,478 = 20,70 cm²
    A = P.As_colapso_progressivo_cm2(600.0)
    assert A == pytest.approx(900.0 / (500.0 / 1.15 / 10.0), rel=1e-12)
    assert A == pytest.approx(20.70, abs=0.005)
    assert P.verificar_colapso_progressivo(600.0, A).ok
    assert not P.verificar_colapso_progressivo(600.0, A * (1 - 1e-6)).ok
    # FSd com γf = 1,2
    assert P.FSd_colapso_progressivo_kn(500.0) == pytest.approx(600.0)
    assert P.FSd_colapso_progressivo_kn(500.0, 1.4) == pytest.approx(700.0)
    with pytest.raises(FE):
        P.As_colapso_progressivo_cm2(-1.0)


# ---------------------------------------------------------------------------
# 19.5.5 — Laje protendida (PDF p. 191-192)
# ---------------------------------------------------------------------------
def test_tau_Pd_e_tau_Sd_efetivo():
    # Pk,inf = 500 kN, α = 10°, u = 300 cm, d = 20 cm:
    # τPd = 500·sen 10°/(300·20) = 0,014470 kN/cm² = 0,14470 MPa
    t = P.tau_Pd_mpa([(500.0, 10.0)], 300.0, 20.0)
    assert t == pytest.approx(500 * math.sin(math.radians(10)) / 6000 * 10, rel=1e-12)
    assert t == pytest.approx(0.1447, abs=5e-5)
    assert P.tau_Sd_efetivo_protendido_mpa(1.0, [(500.0, 10.0)], 300.0, 20.0) == pytest.approx(1.0 - t)
    # dois cabos somam
    assert P.tau_Pd_mpa([(500.0, 10.0), (500.0, 10.0)], 300.0, 20.0) == pytest.approx(2 * t)
    # bordas de α: 0° não contribui; 90° dá P/(u·d)
    assert P.tau_Pd_mpa([(500.0, 0.0)], 300.0, 20.0) == 0.0
    assert P.tau_Pd_mpa([(600.0, 90.0)], 300.0, 20.0) == pytest.approx(1.0)


def test_tau_Pd_cabo_a_menos_de_d_sobre_2():
    # d = 20: só cabos a menos de d/2 = 10 cm da face do pilar
    assert P.tau_Pd_mpa([(500.0, 10.0, 10.0)], 300.0, 20.0) == 0.0
    assert P.tau_Pd_mpa([(500.0, 10.0, 9.99)], 300.0, 20.0) > 0.0
    with pytest.raises(FE):
        P.tau_Pd_mpa([(500.0, -1.0)], 300.0, 20.0)
    with pytest.raises(FE):
        P.tau_Pd_mpa([(500.0, 91.0)], 300.0, 20.0)


# ---------------------------------------------------------------------------
# 20.4 — Estribos de punção (PDF p. 196)
# ---------------------------------------------------------------------------
def test_phi_max_estribo_puncao():
    # φ <= h/20: h = 20 cm -> 1 cm = 10 mm; h = 16 cm -> 8 mm
    assert P.phi_max_estribo_puncao_mm(20.0) == pytest.approx(10.0)
    assert P.phi_max_estribo_puncao_mm(16.0) == pytest.approx(8.0)
    with pytest.raises(FE):
        P.phi_max_estribo_puncao_mm(0.0)


def test_contato_canto_estribo():
    assert P.verificar_contato_canto(10.0, 10.0).ok                    # igual passa
    assert not P.verificar_contato_canto(10.0, 8.0).ok                 # longitudinal menor
    r = P.verificar_contato_canto(8.0, 10.0, contato_mecanico=False)
    assert not r.ok and "contato" in r.governante
    assert P.verificar_contato_canto(10.0, 12.5, h_cm=20.0).ok         # 10 <= 20/20 cm
    r = P.verificar_contato_canto(10.5, 12.5, h_cm=20.0)
    assert not r.ok and not r.ok_diametro and r.phi_max_mm == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# 21.3.4 c — Abertura próxima a pilar (PDF p. 201)
# ---------------------------------------------------------------------------
def test_abertura_proxima_sem_abertura_efetiva_reproduz_verificar_puncao():
    kw = dict(rho_x=0.01, rho_y=0.01)
    ab_longe = [(500, -20), (540, -20), (540, 20), (500, 20)]
    r = P.puncao_abertura_proxima_pilar(30.0, 20.0, 900.0, 40.0, 60.0, [ab_longe],
                                        MSd1_kncm=5000.0, MSd2_kncm=3000.0, **kw)
    ref = P.verificar_puncao(30.0, 20.0, 900.0, 40.0, 60.0, "interno", 5000.0, 3000.0, **kw)
    assert r.aberturas_consideradas == ()
    assert r.tau_Sd_Cl_mpa == pytest.approx(ref.tau_Sd_Cl_mpa, rel=1e-12)
    assert r.tau_Sd_C_mpa == pytest.approx(ref.tau_Sd_C_mpa, rel=1e-12)
    assert r.tau_Rd1_mpa == pytest.approx(ref.tau_Rd1_mpa, rel=1e-12)
    assert r.ok == ref.ok


def test_abertura_proxima_reduz_perimetro():
    # mesmo caso da Figura 19.7 montado à mão: excluídos 20 cm de u
    ab = [(120, -20), (160, -20), (160, 20), (120, 20)]
    F, d = 700.0, 20.0
    r = P.puncao_abertura_proxima_pilar(30.0, d, F, 40.0, 40.0, [ab], rho_x=0.01, rho_y=0.01)
    u = 160 + 80 * math.pi - 20.0
    assert r.u_cm == pytest.approx(u, rel=1e-12)
    assert r.tau_Sd_Cl_mpa == pytest.approx(F / (u * d) * 10, rel=1e-12)
    # sem a ampliação de 20 % de τRd2 (19.5.3.1: só sem aberturas junto ao pilar)
    assert r.tau_Rd2_mpa == pytest.approx(P.tau_Rd2_mpa(30.0), rel=1e-12)
    assert any("21.3.4 c" in m for m in r.memoria)


def test_abertura_proxima_com_armadura():
    ab = [(60, -30), (100, -30), (100, 30), (60, 30)]
    r = P.puncao_abertura_proxima_pilar(30.0, 20.0, 1300.0, 40.0, 40.0, [ab], rho_x=0.01, rho_y=0.01)
    assert r.armadura_necessaria and not r.ok
    r = P.puncao_abertura_proxima_pilar(30.0, 20.0, 1300.0, 40.0, 40.0, [ab], rho_x=0.01, rho_y=0.01,
                                        Asw_cm2=20.0, sr_cm=15.0, fywd_mpa=300.0)
    rd3 = P.tau_Rd3_mpa(30.0, 0.01, 20.0, 20.0, 15.0, 300.0, r.u_cm)
    assert r.tau_Rd3_mpa == pytest.approx(rd3, rel=1e-12)
    assert r.ok == (r.tau_Sd_Cl_mpa <= rd3 and r.tau_Sd_C_mpa <= r.tau_Rd2_mpa)


# ---------------------------------------------------------------------------
# 22.6.2.3 — Sapata flexível: punção (PDF p. 212)
# ---------------------------------------------------------------------------
def test_sapata_flexivel_caso_mao():
    # Sapata 300 x 300, pilar 40 x 40, d = 35, FSd = 1500 kN, C25, ρ = 0,005.
    # p = 1500/90 000 = 0,016667 kN/cm²
    # C:  FSd,C = 1500 − p·1600 = 1473,33 kN; u0 = 160; τSd = 1473,33/(160·35)·10 = 2,6310 MPa
    # C′: r = 70; área = 1600 + 2·70·80 + π·70² = 28 193,8 cm²; FSd,C′ = 1500 − 469,90 = 1030,10 kN
    #     u = 160 + 140·π = 599,82 cm; τSd = 1030,10/(599,82·35)·10 = 0,49066 MPa
    #     τRd1 = 0,13·(1 + √(20/35))·(100·0,005·25)^(1/3) = 0,52976 MPa
    #     τRd2 = 0,27·(1 − 25/250)·25/1,4 = 4,3393 MPa
    r = S.verificar_puncao_sapata_flexivel(1500.0, 300.0, 300.0, 40.0, 40.0, 35.0, 25.0,
                                           rho_x=0.005, rho_y=0.005, h_cm=40.0)
    p = 1500.0 / 90000.0
    assert r.p_solo_kncm2 == pytest.approx(p)
    assert r.FSd_C_kn == pytest.approx(1500 - p * 1600)
    assert r.tau_Sd_C_mpa == pytest.approx((1500 - p * 1600) / (160 * 35) * 10, rel=1e-12)
    area = 1600 + 2 * 70 * 80 + math.pi * 70 ** 2
    assert r.area_Cl_cm2 == pytest.approx(area)
    Fl = 1500 - p * area
    assert r.FSd_Cl_kn == pytest.approx(Fl)
    u = 160 + 140 * math.pi
    assert r.u_cm == pytest.approx(u)
    assert r.tau_Sd_Cl_mpa == pytest.approx(Fl / (u * 35) * 10, rel=1e-12)
    assert r.tau_Sd_Cl_mpa == pytest.approx(0.49066, abs=5e-5)
    rd1 = 0.13 * (1 + math.sqrt(20 / 35)) * (100 * 0.005 * 25) ** (1 / 3)
    assert r.tau_Rd1_mpa == pytest.approx(rd1, rel=1e-12)
    assert r.tau_Rd2_mpa == pytest.approx(0.27 * 0.9 * 25 / 1.4, rel=1e-12)
    assert r.ok and r.Cl_dentro_da_sapata
    assert r.rigida is False           # h = 40 < (300 − 40)/3 = 86,7
    # ρ menor: τRd1 = 0,13·1,7559·5^(1/3) = 0,39034 < 0,49066 -> não passa
    r2 = S.verificar_puncao_sapata_flexivel(1500.0, 300.0, 300.0, 40.0, 40.0, 35.0, 25.0,
                                            rho_x=0.002, rho_y=0.002)
    assert not r2.ok and "C′" in r2.governante


def test_sapata_flexivel_reacao_informada_e_momento():
    # p informado (por exemplo, descontado o peso próprio); momento em A com K(ap/bp)
    r = S.verificar_puncao_sapata_flexivel(1500.0, 300.0, 300.0, 40.0, 40.0, 35.0, 25.0,
                                           rho_x=0.005, rho_y=0.005, p_solo_kncm2=0.015,
                                           MSd_A_kncm=10000.0)
    area = 1600 + 2 * 70 * 80 + math.pi * 70 ** 2
    Fl = 1500 - 0.015 * area
    W = P.Wp_retangular_cm2(40, 40, 35)
    tau = (Fl / ((160 + 140 * math.pi) * 35) + 0.6 * 10000.0 / (W * 35)) * 10
    assert r.tau_Sd_Cl_mpa == pytest.approx(tau, rel=1e-12)


def test_sapata_flexivel_Cl_fora_da_sapata():
    # A = 150, ap = 40, d = 35: ap + 4d = 180 > 150 -> só C (22.6.2.2 b)
    r = S.verificar_puncao_sapata_flexivel(1000.0, 150.0, 150.0, 40.0, 40.0, 35.0, 25.0)
    assert not r.Cl_dentro_da_sapata
    assert r.tau_Sd_Cl_mpa is None and r.tau_Rd1_mpa is None
    assert r.ok == (r.tau_Sd_C_mpa <= r.tau_Rd2_mpa)
    # fronteira: ap + 4d = A exato ainda cabe
    r = S.verificar_puncao_sapata_flexivel(1000.0, 180.0, 180.0, 40.0, 40.0, 35.0, 25.0)
    assert r.Cl_dentro_da_sapata


def test_sapata_flexivel_erros():
    with pytest.raises(FE):
        S.verificar_puncao_sapata_flexivel(1000.0, 30.0, 150.0, 40.0, 40.0, 35.0, 25.0)
    with pytest.raises(FE):
        S.verificar_puncao_sapata_flexivel(-1.0, 300.0, 300.0, 40.0, 40.0, 35.0, 25.0)
