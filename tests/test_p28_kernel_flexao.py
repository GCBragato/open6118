"""Testes do P28 — Kernel de flexão: domínios, momento-curvatura e método geral (NBR 6118:2026).

Cobre:
  - 17.2.2 g) e Figura 17.1, rótulo do domínio de deformação, PDF p. 142;
  - 15.3.1 e Figura 15.1, diagrama M, N, 1/r (curva AB com 1,10·fcd e
    NRd/γf3; ponto B = MRd/γf3; (EI)sec), PDF p. 121;
  - 15.8.3.3.4, pilar-padrão acoplado a diagramas M, N, 1/r (λ <= 140), PDF p. 130;
  - 15.8.3.2, método geral (discretização da barra), PDF p. 129;
  - 15.8.1 (γn1 e λ <= 200, PDF p. 127) e 15.8.4 (fluência obrigatória
    para λ > 90, PDF p. 131) nos dois métodos.

Os valores esperados vêm das imagens das páginas (SCRATCH/nbr_png) e as
contas à mão estão nos comentários.
"""

import math
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import pilares_nbr6118 as P  # noqa: E402
from dimensionamento.rotinas import flexao_composta_obliqua as F  # noqa: E402
from dimensionamento.rotinas import momento_curvatura as MC  # noqa: E402
from dimensionamento.rotinas import verificacao_pilar as VP  # noqa: E402

# A mesma exceção pode vir de duas cópias do núcleo (import por pacote e por sys.path).
Erro = (F.nbr.FaixaNormativaError, P.nbr.FaixaNormativaError)

C30 = F.Concreto(fck_mpa=30.0)
ACO = F.Aco()


def secao_20x50(fi_mm: float = 16.0) -> F.SecaoRetangular:
    """Pilar 20x50 (base x altura), 8 barras no perímetro (2 por face de 20, 4 linhas)."""
    return F.SecaoRetangular(20.0, 50.0, 3.0,
                             F.armadura_perimetral_retangular(20, 50, 3.0, 2, 4, fi_mm))


S = secao_20x50()


# ===========================================================================
# 17.2.2 g) — domínios da Figura 17.1 (PDF p. 142)
# ===========================================================================
# C30: εcu = 3,5 ‰, εc2 = 2,0 ‰, pivô C a 3/7·h. CA-50: εyd = 500/1,15/210000 = 2,0704 ‰.
H, D = 50.0, 45.0
X23 = 3.5 / 13.5 * D                     # = 11,6667 cm
EYD = 500.0 / 1.15 / 210000.0 * 1000.0   # = 2,07039 ‰
X34 = 3.5 / (3.5 + EYD) * D              # = 157,5/5,57039 = 28,2745 cm


def plano_ultimo(x, fck=30.0, h=H, d=D):
    """(εtopo, εbase) da deformada última com LN em x (pivôs A, B e C da Figura 17.1)."""
    from dimensionamento import nucleo_nbr6118 as n
    ecu, ec2 = n.eps_cu(fck), min(n.eps_c2(fck), n.eps_cu(fck))
    rho = n.pivo_C_distancia_relativa(fck)
    x23 = ecu / (ecu + 10.0) * d
    if x <= x23:                       # pivô A: −10 ‰ em d
        return 10.0 * x / (d - x), 10.0 * (x - h) / (d - x)
    if x <= h:                         # pivô B: εcu na face
        return ecu, ecu * (x - h) / x
    k = ec2 / (x - rho * h)            # pivô C: εc2 a ρ·h da face
    return k * x, k * (x - h)


def test_1722g_limites_conta_a_mao():
    assert X23 == pytest.approx(11.6666667, rel=1e-7)
    assert X34 == pytest.approx(28.27448, rel=1e-6)
    assert F.nbr.x_lim_dominio_3_4(D, 30.0) == pytest.approx(X34, rel=1e-12)


@pytest.mark.parametrize("x, esperado", [
    (-20.0, "1"),            # tração não uniforme, sem compressão
    (0.0, "1"),              # x = 0: face de topo com ε = 0, ainda sem compressão
    (1e-4, "2"),             # logo depois de x = 0
    (X23 - 1e-4, "2"),       # εc < εcu
    (X23, "3"),              # εc = εcu e εs = 10 ‰ >= εyd
    (20.0, "3"),
    (X34, "3"),              # εs = εyd (εs >= εyd ainda é 3)
    (X34 + 1e-4, "4"),       # εs < εyd
    (D - 1e-4, "4"),
    (D, "4a"),               # εs = 0: armadura deixa de ser tracionada
    (H - 1e-4, "4a"),        # armadura comprimida, base ainda tracionada
    (H, "5"),                # sem tração
    (80.0, "5"),
    (1e6, "5"),
])
def test_1722g_dominios_nas_fronteiras(x, esperado):
    et, eb = plano_ultimo(x)
    assert F.dominio_deformacao(et, eb, 30.0, H, D) == esperado


@pytest.mark.parametrize("eps, esperado", [(-10.0, "reta a"), (-3.0, "reta a"),
                                           (2.0, "reta b"), (0.5, "reta b")])
def test_1722g_retas_a_e_b(eps, esperado):
    assert F.dominio_deformacao(eps, eps, 30.0, H, D) == esperado


def test_1722g_deformada_interior_recebe_rotulo_pela_ln():
    # Estado não último com x = 20 cm (entre x23 e x34): εtopo = 1 ‰, εbase = −1,5 ‰
    # -> x = 50·1/2,5 = 20 cm -> domínio 3.
    assert F.dominio_deformacao(1.0, -1.5, 30.0, H, D) == "3"


def test_1722g_ca60_desloca_x34():
    # CA-60: εyd = 600/1,15/210000 = 2,48447 ‰; x34 = 3,5/5,98447·45 = 26,318 cm.
    # x = 27 cm: domínio 4 com CA-60 e 3 com CA-50.
    et, eb = plano_ultimo(27.0)
    assert F.dominio_deformacao(et, eb, 30.0, H, D, fyk_mpa=600.0) == "4"
    assert F.dominio_deformacao(et, eb, 30.0, H, D) == "3"


def test_1722g_c90_pivo_c_na_face():
    # C90: εcu = 2,6 ‰ e εc2 = 2,6006 ‰ -> εc2 efetivo 2,6 e pivô C na face (ρ = 0).
    assert F.dominio_deformacao(2.6, 2.6, 90.0, H, D) == "reta b"
    assert F.dominio_deformacao(2.6, 0.0, 90.0, H, D) == "5"
    x23 = 2.6 / 12.6 * D
    et, eb = plano_ultimo(x23, fck=90.0)
    assert F.dominio_deformacao(et, eb, 90.0, H, D) == "3"
    with pytest.raises(Erro):
        F.dominio_deformacao(2.6006, 2.6006, 90.0, H, D)


def test_1722g_c60_pivo_c():
    # C60: εcu = 2,6 + 35·0,3⁴ = 2,88350 ‰; εc2 = 2 + 0,085·10^0,53 = 2,28782 ‰;
    # ρ = (εcu − εc2)/εcu = 0,20658. Plano pelo pivô C com x = 2h passa; 1 % acima, não.
    et, eb = plano_ultimo(100.0, fck=60.0)
    assert F.dominio_deformacao(et, eb, 60.0, H, D) == "5"
    with pytest.raises(Erro):
        F.dominio_deformacao(1.01 * et, 1.01 * eb, 60.0, H, D)


@pytest.mark.parametrize("et, eb", [
    (3.6, -1.0),          # passa do pivô B (εtopo > εcu)
    (1.0, -20.0),         # εs em d = 1 − 21·0,9 = −17,9 ‰ < −10 ‰ (pivô A)
    (3.0, 1.5),           # εC = 3 − 1,5·3/7 = 2,357 > 2 ‰ (pivô C)
    (2.1, 2.1),           # reta b além de εc2
    (-10.5, -10.5),       # reta a além de 10 ‰
    (-1.0, 1.0),          # topo menos comprimido que a base
    (0.0, 0.0),           # sem deformação
    (float("nan"), 0.0),
])
def test_1722g_fora_da_figura_17_1(et, eb):
    with pytest.raises(Erro):
        F.dominio_deformacao(et, eb, 30.0, H, D)


@pytest.mark.parametrize("h, d", [(50.0, 0.0), (50.0, 55.0), (0.0, 0.0)])
def test_1722g_geometria_invalida(h, d):
    with pytest.raises(Erro):
        F.dominio_deformacao(3.5, -1.0, 30.0, h, d)


def test_1722g_fck_fora_da_faixa():
    with pytest.raises(Erro):
        F.dominio_deformacao(3.5, -1.0, 95.0, H, D)


# Seção 20x50 do kernel: d_linha = 3 + (5 + 16/2)/10 = 4,3 cm -> d = 50 − 4,3 = 45,7 cm (α = 0).
D_S = 50.0 - 4.3


@pytest.mark.parametrize("x, esperado", [
    (-3.0, "1"), (5.0, "2"), (20.0, "3"), (35.0, "4"), (47.0, "4a"), (60.0, "5"),
])
def test_1722g_dominio_elu_do_kernel(x, esperado):
    assert F.dominio_elu(S, C30, ACO, 0.0, x) == esperado
    sp = F.Secao.retangular(20.0, 50.0, C30, S.barras)
    assert F.dominio_elu(sp, None, ACO, 0.0, x) == esperado


def test_1722g_dominio_elu_flexao_simples_do_kernel():
    """Resultado de verificar_fco com Nd pequeno: rótulo coerente com x/d."""
    r = F.verificar_fco(S, C30, ACO, 50.0, 8000.0, 0.0)
    x = r["x_LN_cm"]
    dom = F.dominio_elu(S, C30, ACO, r["alpha_rad"], x)
    x23 = 3.5 / 13.5 * D_S
    x34 = 3.5 / (3.5 + EYD) * D_S
    assert dom == ("2" if x < x23 else "3" if x <= x34 else "4")
    assert dom in ("2", "3")


def test_1722g_dominio_elu_sem_armadura():
    s0 = F.SecaoRetangular(20.0, 50.0, 3.0, ())
    with pytest.raises(Erro):
        F.dominio_elu(s0, C30, ACO, 0.0, 20.0)


# ===========================================================================
# 15.3.1 e Figura 15.1 — diagrama M, N, 1/r (PDF p. 121)
# ===========================================================================
@pytest.fixture(scope="module")
def diag_x():
    return MC.diagrama_M_N_curvatura(S, C30, ACO, 1400.0, eixo="x")


def test_1531_diagrama_cruza_ei_secante_no_ponto_B(diag_x):
    """A reta AB do diagrama é a (EI)sec de ei_secante (mesma curva AB, mesmo ponto B)."""
    EI = F.ei_secante(S, C30, ACO, 1400.0, 5000.0, "x")
    assert diag_x.EI_sec_kncm2 == pytest.approx(EI, rel=1e-9)
    # o ponto B é ponto da curva: M(1/r_B) = MRd/γf3
    assert diag_x.momento(diag_x.curvatura_B_1_cm) == pytest.approx(diag_x.M_B_kncm, rel=1e-12)
    assert diag_x.curvatura(diag_x.M_B_kncm) == pytest.approx(diag_x.curvatura_B_1_cm, rel=1e-12)


def test_1531_ponto_B_e_MRd_sobre_gama_f3(diag_x):
    MR = F.momento_resistente_fco(S, C30, ACO, 1400.0, 0.0, 60)["MR_kncm"]
    assert diag_x.MRd_kncm == pytest.approx(MR, rel=1e-12)
    assert diag_x.M_B_kncm == pytest.approx(MR / 1.1, rel=1e-12)
    assert diag_x.N_curva_kn == pytest.approx(1400.0 / 1.1, rel=1e-12)
    # a curva AB (1,10·fcd) passa de MRd/γf3 (Figura 15.1: B abaixo do topo da curva cheia)
    assert diag_x.M_max_curva_kncm > diag_x.M_B_kncm


def test_1531_diagrama_comeca_em_zero_e_sobe(diag_x):
    k, m = diag_x.curvaturas_1_cm, diag_x.momentos_kncm
    assert k[0] == 0.0 and m[0] == 0.0
    assert all(k[i + 1] > k[i] for i in range(len(k) - 1))
    assert all(m[i + 1] > m[i] for i in range(len(m) - 1))   # ramo ascendente até o limite


def test_1531_ultimo_ponto_no_limite_da_figura_17_1(diag_x):
    """A curva vai até a deformada que atinge o primeiro limite da Figura 17.1."""
    conc_ab = F._concreto_curva_15_3_1(C30)
    k_ult = diag_x.curvaturas_1_cm[-1] * 1e3     # 1/cm -> ‰/cm
    e0, _, _ = MC._estado(S, conc_ab, ACO, 1400.0 / 1.1, k_ult, "x", 60)
    assert MC._razao_limite(S, C30, e0, k_ult, "x") == pytest.approx(1.0, abs=1e-8)


def test_1531_inversa_curvatura_momento(diag_x):
    k_meio = 0.5 * diag_x.curvaturas_1_cm[-1]
    assert diag_x.curvatura(diag_x.momento(k_meio)) == pytest.approx(k_meio, rel=1e-9)
    with pytest.raises(Erro):
        diag_x.curvatura(1.01 * diag_x.M_max_curva_kncm)
    with pytest.raises(Erro):
        diag_x.momento(1.01 * diag_x.curvaturas_1_cm[-1])


def test_1531_secao_simetrica_sentidos_iguais(diag_x):
    neg = MC.diagrama_M_N_curvatura(S, C30, ACO, 1400.0, eixo="x", sentido=-1)
    assert neg.EI_sec_kncm2 == pytest.approx(diag_x.EI_sec_kncm2, rel=1e-9)
    assert neg.M_max_curva_kncm == pytest.approx(diag_x.M_max_curva_kncm, rel=1e-9)


def test_1531_eixo_y_menos_rigido(diag_x):
    dy = MC.diagrama_M_N_curvatura(S, C30, ACO, 1400.0, eixo="y")
    assert dy.EI_sec_kncm2 == pytest.approx(F.ei_secante(S, C30, ACO, 1400.0, 1.0, "y"), rel=1e-9)
    assert dy.EI_sec_kncm2 < diag_x.EI_sec_kncm2


def test_1531_memoria_cita_itens(diag_x):
    texto = " ".join(diag_x.memoria)
    assert "15.3.1" in texto and "1,10·fcd" in texto and "γf3" in texto


def test_1531_secao_assimetrica_avisa():
    barras = (F.Barra(7.0, 20.0, 2.0), F.Barra(7.0, -20.0, 2.0))
    s = F.SecaoRetangular(20.0, 50.0, 3.0, barras)
    with pytest.warns(F.nbr.AvisoNBR6118):
        MC.diagrama_M_N_curvatura(s, C30, ACO, 800.0, eixo="x")


def test_1531_secao_simetrica_nao_avisa():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        MC.diagrama_M_N_curvatura(S, C30, ACO, 1000.0, eixo="y", n_pontos=10)


@pytest.mark.parametrize("kw", [dict(eixo="z"), dict(sentido=2), dict(n_pontos=3)])
def test_1531_parametros_invalidos(kw):
    with pytest.raises(ValueError):
        MC.diagrama_M_N_curvatura(S, C30, ACO, 1000.0, **kw)


def test_1531_entradas_fora_da_faixa():
    Nmax = F.Nd_max_kn(S, C30, ACO)
    with pytest.raises(Erro):
        MC.diagrama_M_N_curvatura(S, C30, ACO, 1.01 * Nmax)
    with pytest.raises(Erro):
        MC.diagrama_M_N_curvatura(S, C30, ACO, 1000.0, gama_f3=0.9)
    with pytest.raises(TypeError):
        MC.diagrama_M_N_curvatura(F.Secao.retangular(20, 50, C30, S.barras), C30, ACO, 1000.0)


# ===========================================================================
# 15.8.3.3.4 — pilar-padrão acoplado a diagramas M, N, 1/r (PDF p. 130)
# ===========================================================================
def test_158334_forma_linearizada_conta_a_mao():
    # Reta AB: 1/r = M/(γf3·EI) -> Md,tot = αb·M1d,A/[1 − Nd·ℓe²/(10·γf3·EI)].
    r = VP.pilar_padrao_MN1r(S, C30, ACO, 1000.0, 400.0, 3000.0, 3000.0, eixo="y",
                             verificar_dispensa=False, linearizar=True)
    EI = r.diagrama.EI_sec_kncm2
    esperado = 3000.0 / (1.0 - 1000.0 * 400.0 ** 2 / (10.0 * 1.1 * EI))
    assert r.Md_tot_kncm == pytest.approx(esperado, rel=1e-12)
    assert r.curvatura_1_cm == pytest.approx(esperado / (1.1 * EI), rel=1e-12)


def test_158334_equacao_de_equilibrio():
    """Md,tot = αb·M1d,A + Nd·ℓe²/10·(1/r)(Md,tot/γf3) no resultado."""
    r = VP.pilar_padrao_MN1r(S, C30, ACO, 1000.0, 450.0, 3000.0, 1500.0, eixo="y",
                             verificar_dispensa=False)
    # αb = 0,6 + 0,4·1500/3000 = 0,8
    assert r.alpha_b == pytest.approx(0.8, rel=1e-12)
    k = r.diagrama.curvatura(r.Md_tot_kncm / 1.1)
    assert r.Md_tot_kncm == pytest.approx(0.8 * 3000.0 + 1000.0 * 450.0 ** 2 / 10.0 * k, rel=1e-9)
    assert r.Md_tot_kncm >= r.M1d_A_ef_kncm
    assert r.estavel and r.ok
    assert r.gama_n1 == 1.0


def test_158334_mais_leve_que_curvatura_aproximada():
    """ν = 1000/(1000·30/1,4/10) = 0,467: a curvatura aproximada 0,005/[h(ν+0,5)]
    é uma estimativa de ELU e fica entre a curvatura do ponto B e a do limite
    de deformação do diagrama; com M abaixo de MRd, o diagrama dá Md,tot menor."""
    le = 450.0
    r = VP.pilar_padrao_MN1r(S, C30, ACO, 1000.0, le, 3000.0, 3000.0, eixo="y",
                             verificar_dispensa=False)
    pp = P.pilar_padrao_direcao(1000.0, le, 20.0, 1000.0, 30.0, 3000.0, 3000.0,
                                verificar_dispensa=False)
    assert r.Md_tot_kncm < pp.Md_tot_kncm
    ap = P.curvatura_aproximada(20.0, pp.nu)
    assert r.diagrama.curvatura_B_1_cm < ap < r.diagrama.curvaturas_1_cm[-1]


@pytest.mark.parametrize("nu", [0.5, 0.55, 0.6])
def test_158334_curvatura_aproximada_entre_B_e_elu(nu):
    Nd = nu * 1000.0 * 30.0 / 1.4 / 10.0
    d = MC.diagrama_M_N_curvatura(S, C30, ACO, Nd, eixo="y", n_pontos=20)
    ap = P.curvatura_aproximada(20.0, nu)
    assert d.curvatura_B_1_cm < ap < d.curvaturas_1_cm[-1]


def test_158334_momento_minimo_e_dispensa():
    # M1d,mín = 1000·(1,5 + 0,03·20) = 2100 kN·cm; MA = 500 < mínimo -> M1d,A = 2100, αb = 1.
    r = VP.pilar_padrao_MN1r(S, C30, ACO, 1000.0, 400.0, 500.0, 500.0, eixo="y",
                             verificar_dispensa=False)
    assert r.M1d_min_kncm == pytest.approx(2100.0, rel=1e-12)
    assert r.M1d_A_ef_kncm == pytest.approx(2100.0, rel=1e-12)
    assert r.alpha_b == 1.0
    # λ = √12·100/20 = 17,32 < λ1 = 35: 2ª ordem desprezada (15.8.2).
    r2 = VP.pilar_padrao_MN1r(S, C30, ACO, 1000.0, 100.0, 3000.0, 3000.0, eixo="y")
    assert r2.dispensa_2a_ordem and r2.M2d_kncm == 0.0
    assert r2.Md_tot_kncm == pytest.approx(3000.0, rel=1e-12)


def test_158334_limite_140_e_fluencia():
    # eixo y, h = 20: λ = √12·ℓe/20. ℓe = 850 -> λ = 147,2 > 140.
    with pytest.raises(Erro):
        VP.pilar_padrao_MN1r(S, C30, ACO, 200.0, 850.0, 1000.0, 1000.0, eixo="y", ecc_cm=0.0)
    # ℓe = 808 -> λ = 139,95 <= 140: aceito com ecc; sem ecc, erro (λ > 90, 15.8.4).
    with pytest.raises(Erro):
        VP.pilar_padrao_MN1r(S, C30, ACO, 200.0, 808.0, 1000.0, 1000.0, eixo="y")
    r = VP.pilar_padrao_MN1r(S, C30, ACO, 200.0, 808.0, 1000.0, 1000.0, eixo="y", ecc_cm=0.5)
    # M1d,mín = 200·2,1 = 420 < 1000; M1d,A = 1000 + 200·0,5 = 1100 kN·cm
    assert r.lambda_ == pytest.approx(math.sqrt(12.0) * 808.0 / 20.0, rel=1e-12)
    assert r.M1d_A_ef_kncm == pytest.approx(1100.0, rel=1e-12)
    with pytest.raises(Erro):
        VP.pilar_padrao_MN1r(S, C30, ACO, 200.0, 808.0, 1000.0, 1000.0, eixo="y", ecc_cm=-1.0)


def test_158334_fluencia_dispensada_ate_90():
    # ℓe = 519 -> λ = 89,9: sem ecc, passa.
    r = VP.pilar_padrao_MN1r(S, C30, ACO, 500.0, 519.0, 2000.0, 2000.0, eixo="y",
                             verificar_dispensa=False)
    assert r.ecc_cm == 0.0 and r.estavel


def test_158334_instavel():
    # Nd = 1000 kN com ℓe = 600 cm (λ = 103,9) na direção de 20 cm: sem equilíbrio.
    r = VP.pilar_padrao_MN1r(S, C30, ACO, 1000.0, 600.0, 3000.0, 3000.0, eixo="y",
                             ecc_cm=0.0, verificar_dispensa=False)
    assert not r.estavel and not r.ok
    assert math.isnan(r.Md_tot_kncm)
    assert "instabilidade" in r.governante


def test_158334_elu_nao_passa():
    # MA perto de MRd: Md,tot > MRd na seção crítica.
    MRd = F.momento_resistente_fco(S, C30, ACO, 1000.0, math.pi / 2, 60)["MR_kncm"]
    r = VP.pilar_padrao_MN1r(S, C30, ACO, 1000.0, 150.0, 0.97 * MRd, 0.97 * MRd, eixo="y",
                             verificar_dispensa=False)
    assert r.estavel and not r.ok
    assert r.Md_tot_kncm > r.MRd_kncm


def test_158334_entradas_invalidas():
    with pytest.raises(Erro):
        VP.pilar_padrao_MN1r(S, C30, ACO, 0.0, 300.0, 1000.0, 1000.0)
    with pytest.raises(ValueError):
        VP.pilar_padrao_MN1r(S, C30, ACO, 1000.0, 300.0, 1000.0, 1000.0, eixo="z")
    with pytest.raises(TypeError):
        VP.pilar_padrao_MN1r(F.Secao.retangular(20, 50, C30, S.barras), C30, ACO,
                             1000.0, 300.0, 1000.0, 1000.0)


# ===========================================================================
# 15.8.3.2 — método geral (PDF p. 129)
# ===========================================================================
class DiagramaLinear:
    """Relação M-1/r linear, 1/r = M/EI, para conferir a linha elástica contra a solução fechada."""

    def __init__(self, EI):
        self.EI = EI
        self.M_max_curva_kncm = float("inf")
        self.MRd_kncm = 1e12

    def curvatura(self, M):
        return abs(M) / self.EI


def test_1583_2_solucao_fechada_elastica():
    """Barra birrotulada com momentos iguais M0 nas pontas e 1/r = (M/γf3)/EI:
    M,máx = M0·sec(π/2·√(Nd/Pcr)), Pcr = π²·γf3·EI/ℓe² (fórmula da secante)."""
    EI, L, N, M0 = 3.0e8, 600.0, 1000.0, 3000.0
    Pcr = math.pi ** 2 * 1.1 * EI / L ** 2
    esperado = M0 / math.cos(math.pi / 2.0 * math.sqrt(N / Pcr))   # = 3461,38 kN·cm
    g = VP.metodo_geral_pilar(S, C30, ACO, L, N, M0, M0, n_segmentos=20, eixo="x",
                              diagramas=(DiagramaLinear(EI), DiagramaLinear(EI)))
    assert g.convergiu and g.estavel
    assert g.Md_tot_max_kncm == pytest.approx(esperado, rel=1e-4)
    assert g.x_Md_tot_max_cm == pytest.approx(300.0)


def test_1583_2_momentos_opostos_maximo_na_ponta():
    """Curvatura dupla (M1,topo = −M1,base) com Nd pequeno: o maior momento fica na ponta."""
    g = VP.metodo_geral_pilar(S, C30, ACO, 600.0, 1000.0, 3000.0, -3000.0, eixo="x",
                              diagramas=(DiagramaLinear(3e8), DiagramaLinear(3e8)))
    assert g.Md_tot_max_kncm == pytest.approx(3000.0, rel=1e-12)
    assert g.y_cm[10] == pytest.approx(0.0, abs=1e-12)   # antissimetria: y(ℓe/2) = 0


@pytest.mark.parametrize("le", [200.0, 400.0])
def test_1583_2_converge_para_pilar_padrao_com_lambda_pequeno(le):
    """λ = √12·ℓe/50 = 13,9 e 27,7: método geral e pilar-padrão M, N, 1/r a menos de 2 %."""
    g = VP.metodo_geral_pilar(S, C30, ACO, le, 1000.0, 3000.0, 3000.0, eixo="x")
    r = VP.pilar_padrao_MN1r(S, C30, ACO, 1000.0, le, 3000.0, 3000.0, eixo="x",
                             verificar_dispensa=False)
    assert g.Md_tot_max_kncm == pytest.approx(r.Md_tot_kncm, rel=0.02)
    assert g.ok and r.ok


def test_1583_2_equilibrio_nos_nos():
    """Md = M1d + Nd·y e (y[i−1] − 2y[i] + y[i+1])/Δ² = −1/r(Md/γf3) em cada nó interno."""
    g = VP.metodo_geral_pilar(S, C30, ACO, 500.0, 1000.0, 3000.0, 1000.0, eixo="y",
                              n_segmentos=10)
    d = MC.diagrama_M_N_curvatura(S, C30, ACO, 1000.0, eixo="y")
    dx = 50.0
    for i in range(1, 10):
        M = g.M1d_kncm[i] + 1000.0 * g.y_cm[i]
        assert g.Md_tot_kncm[i] == pytest.approx(M, rel=1e-12)
        fd = (g.y_cm[i - 1] - 2 * g.y_cm[i] + g.y_cm[i + 1]) / dx ** 2
        assert fd == pytest.approx(-d.curvatura(M / 1.1), rel=1e-5)


def test_1583_2_momento_minimo_e_fluencia():
    # M1 nulo -> M1d,mín = 1000·(1,5 + 0,03·20) = 2100 kN·cm uniforme; ecc = 0,4 cm soma 400.
    g = VP.metodo_geral_pilar(S, C30, ACO, 300.0, 1000.0, 0.0, 0.0, eixo="y", ecc_cm=0.4)
    assert all(m == pytest.approx(2500.0, rel=1e-12) for m in g.M1d_kncm)
    assert g.ecc_cm == 0.4


def test_1583_2_gama_n1_acima_de_140():
    # eixo y, h = 20: ℓe = 866 -> λ = √12·866/20 = 150,0; γn1 = 1 + (λ − 140)/140.
    le = 866.0
    lam = math.sqrt(12.0) * le / 20.0
    g = VP.metodo_geral_pilar(S, C30, ACO, le, 150.0, 1000.0, 1000.0, eixo="y", ecc_cm=0.5)
    assert g.lambda_ == pytest.approx(lam, rel=1e-12)
    assert g.gama_n1 == pytest.approx(1.0 + (lam - 140.0) / 140.0, rel=1e-12)
    i = len(g.x_cm) // 2
    assert g.Md_tot_kncm[i] == pytest.approx(g.M1d_kncm[i] + g.gama_n1 * 150.0 * g.y_cm[i], rel=1e-12)
    assert g.estavel


def test_1583_2_lambda_acima_de_200():
    # ℓe = 1200 -> λ = 207,8 > 200 com Nd = 500 kN >= 0,10·fcd·Ac = 0,1·2,142857·1000 = 214,3 kN.
    with pytest.raises(Erro):
        VP.metodo_geral_pilar(S, C30, ACO, 1200.0, 500.0, 1000.0, 1000.0, eixo="y", ecc_cm=0.5)


def test_1583_2_fluencia_obrigatoria():
    with pytest.raises(Erro):
        VP.metodo_geral_pilar(S, C30, ACO, 600.0, 300.0, 1000.0, 1000.0, eixo="y")


def test_1583_2_instavel():
    g = VP.metodo_geral_pilar(S, C30, ACO, 600.0, 1000.0, 3000.0, 3000.0, eixo="y", ecc_cm=0.0)
    assert not g.estavel and not g.ok
    assert "instabilidade" in g.governante


def test_1583_2_entradas_invalidas():
    with pytest.raises(ValueError):
        VP.metodo_geral_pilar(S, C30, ACO, 300.0, 1000.0, 1000.0, 1000.0, n_segmentos=3)
    with pytest.raises(Erro):
        VP.metodo_geral_pilar(S, C30, ACO, 300.0, -10.0, 1000.0, 1000.0)
    with pytest.raises(Erro):
        VP.metodo_geral_pilar(S, C30, ACO, 300.0, 1000.0, 1000.0, 1000.0, ecc_cm=-1.0)


def test_1583_2_memoria():
    g = VP.metodo_geral_pilar(S, C30, ACO, 300.0, 1000.0, 3000.0, 3000.0, eixo="y")
    texto = " ".join(g.memoria)
    assert "15.8.3.2" in texto and "15.8.1" in texto and "Rd >= Sd" in texto
