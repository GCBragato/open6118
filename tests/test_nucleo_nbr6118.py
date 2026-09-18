"""Testes do núcleo normativo contra valores da NBR 6118:2026.

Os valores esperados saem das fórmulas e tabelas da norma (página do PDF
indicada em cada teste), não de apostilas.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402


# --- 8.2.1 faixa de validade (p. 41-42) -------------------------------------
@pytest.mark.parametrize("fck", [15.0, 19.9, 90.1, 120.0])
def test_fck_fora_da_faixa_levanta(fck):
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.validar_fck(fck)


def test_protendido_exige_c25():
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.validar_fck(22.0, protendido=True)
    assert nbr.validar_fck(25.0, protendido=True) == 25.0


def test_grupo_resistencia():
    assert nbr.grupo_resistencia(50) == "I"
    assert nbr.grupo_resistencia(55) == "II"


# --- Tabela 7.2 cobrimento nominal (p. 39) ----------------------------------
@pytest.mark.parametrize("elemento, protendido, esperado", [
    ("laje", False, (20, 25, 35, 45)),
    ("viga", False, (25, 30, 40, 50)),       # LEG-01: CAA I = 25 mm
    ("pilar", False, (25, 30, 40, 50)),
    ("solo", False, (30, 30, 40, 50)),
    ("laje", True, (25, 30, 40, 50)),
    ("viga/pilar", True, (30, 35, 45, 55)),
])
def test_cobrimento_tabela_7_2(elemento, protendido, esperado):
    for caa, valor in zip(("I", "CAA II", "CAIII", "4"), esperado):
        assert nbr.cobrimento_nominal(caa, elemento, protendido) == valor


def test_cobrimento_pilar_em_contato_com_solo_nota_d():
    assert nbr.cobrimento_nominal("I", "pilar solo") == 45
    assert nbr.cobrimento_nominal("IV", "pilar solo") == 50


def test_cobrimento_entradas_invalidas():
    with pytest.raises(ValueError):
        nbr.cobrimento_nominal("V", "laje")
    with pytest.raises(ValueError):
        nbr.cobrimento_nominal("I", "solo", protendido=True)
    with pytest.raises(ValueError):
        nbr.cobrimento_nominal("I", "parede")


# --- 8.2.5 resistência à tração (p. 42-43) ----------------------------------
@pytest.mark.parametrize("fck, esperado", [
    (30.0, 0.3 * 30 ** (2 / 3)),                   # 2,8965
    (50.0, 0.3 * 50 ** (2 / 3)),                   # 4,0716
    (55.0, 2.12 * math.log(1 + 0.1 * 63)),         # 4,2143
    (70.0, 2.12 * math.log(1 + 0.1 * 78)),         # 4,6105
    (90.0, 2.12 * math.log(1 + 0.1 * 98)),         # 5,0446
])
def test_fct_m(fck, esperado):
    assert nbr.fct_m(fck) == pytest.approx(esperado, rel=1e-12)


def test_fct_m_valores_numericos():
    assert nbr.fct_m(70.0) == pytest.approx(4.6105, abs=1e-4)
    assert nbr.fct_m(90.0) == pytest.approx(5.0446, abs=1e-4)


def test_fctk_e_fctd():
    assert nbr.fctk_inf(30) == pytest.approx(0.7 * nbr.fct_m(30))
    assert nbr.fctk_sup(30) == pytest.approx(1.3 * nbr.fct_m(30))
    assert nbr.fctd(25) == pytest.approx(0.7 * 0.3 * 25 ** (2 / 3) / 1.4)   # 1,2825


def test_fct_m_idade_aceita_fckj_baixo():
    assert nbr.fct_m_idade(15.0) == pytest.approx(0.3 * 15 ** (2 / 3))
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.fct_m_idade(6.0)


# --- 8.2.8 módulo de elasticidade (p. 44) -----------------------------------
def test_Eci_dois_ramos():
    assert nbr.Eci(30) == pytest.approx(5600 * math.sqrt(30))                  # 30 672
    assert nbr.Eci(70) == pytest.approx(21.5e3 * (7.0 + 1.25) ** (1 / 3))      # 43 443
    assert nbr.Eci(30, nbr.alpha_E("basalto")) == pytest.approx(1.2 * 5600 * math.sqrt(30))


def test_Ecs_e_alpha_i():
    assert nbr.alpha_i(30) == pytest.approx(0.875)
    assert nbr.alpha_i(90) == 1.0
    assert nbr.Ecs(70) == pytest.approx(42357.2, abs=0.5)     # LAJ-04 (esperado verificado)
    assert nbr.Ecs(90) == pytest.approx(46703.0, abs=1.0)


def test_alpha_E_aceita_acento():
    assert nbr.alpha_E("calcário") == 0.9
    assert nbr.alpha_E("Diabásio") == 1.2
    with pytest.raises(ValueError):
        nbr.alpha_E("seixo")


def test_Eci_idade_usa_fck_na_base():
    # LEG-05: Eci(t) = (fckj/fck)^0,5 · Eci(fck), não Eci(fckj)
    fckj = nbr.fckj(30, 7, "CPIII")
    assert nbr.Eci_idade(30, fckj) == pytest.approx((fckj / 30) ** 0.5 * nbr.Eci(30))
    assert nbr.Eci_idade(30, fckj) == pytest.approx(25364.9, abs=1.0)


# --- 12.3.3 resistência de cálculo e idade (p. 90-91) -----------------------
def test_beta1_cimentos():
    assert nbr.beta1(7, "CPIII") == pytest.approx(math.exp(-0.38))
    assert nbr.beta1(7, "CP II") == pytest.approx(math.exp(-0.25))
    assert nbr.beta1(7, "CPV-ARI") == pytest.approx(math.exp(-0.20))


def test_s_020_para_c60_ou_mais():
    # LEG-02: s = 0,20 para todo concreto C60 ou superior, qualquer cimento
    assert nbr.s_cimento("CPIV", 60) == 0.20
    assert nbr.fckj(70, 7, "CPIV") == pytest.approx(57.31, abs=0.01)


def test_fcd_antes_de_28_dias_usa_fckj():
    # LEG-03: fcd = fckj/γc para t < 28 dias
    assert nbr.fcd(30, t_dias=7, cimento="CPIII") == pytest.approx(14.65, abs=0.01)
    assert nbr.fcd(30) == pytest.approx(30 / 1.4)
    assert nbr.fckj(30, 90, "CPIII") == 30.0


# --- 8.2.10.1 diagrama parábola-retângulo (p. 45) ---------------------------
@pytest.mark.parametrize("fck, esperado", [
    (40, 1.0), (45, (40 / 45) ** (1 / 3)), (50, (40 / 50) ** (1 / 3)), (90, (40 / 90) ** (1 / 3)),
])
def test_eta_c(fck, esperado):
    assert nbr.eta_c(fck) == pytest.approx(esperado)


def test_parametros_grupo_II():
    assert nbr.eps_c2(50) == 2.0 and nbr.eps_cu(50) == 3.5 and nbr.n_parabola(50) == 2.0
    assert nbr.eps_c2(70) == pytest.approx(2.0 + 0.085 * 20 ** 0.53)
    assert nbr.eps_cu(70) == pytest.approx(2.656)
    assert nbr.n_parabola(70) == pytest.approx(1.4 + 23.4 * 0.2 ** 4)


def test_sigma_c_com_eta_c():
    # LEG-07: C60, εc = 1,0 ‰ -> 19,056 MPa
    assert nbr.sigma_c(1.0, 60) == pytest.approx(19.056, abs=1e-3)


def test_sigma_c_patamar_com_085():
    # LEG-07b: o patamar vale 0,85·ηc·fcd, contínuo em εc2
    pico = 0.85 * 30 / 1.4
    assert nbr.sigma_c(2.0, 30) == pytest.approx(pico)
    assert nbr.sigma_c(3.5, 30) == pytest.approx(pico)
    assert nbr.sigma_c(1.99999, 30) == pytest.approx(pico, rel=1e-6)
    assert nbr.sigma_c(-1.0, 30) == 0.0


# --- 17.2.2 e) diagrama retangular (p. 141) ---------------------------------
def test_retangulo_grupo_I_e_II():
    assert nbr.lambda_retangulo(50) == 0.8 and nbr.alpha_c(50) == 0.85
    assert nbr.lambda_retangulo(70) == pytest.approx(0.75)
    assert nbr.alpha_c(70) == pytest.approx(0.765)
    assert nbr.tensao_retangulo(30) == pytest.approx(0.85 * 30 / 1.4)
    assert nbr.tensao_retangulo(50) == pytest.approx(0.85 * (0.8 ** (1 / 3)) * 50 / 1.4)
    assert nbr.tensao_retangulo(30, largura_diminui=True) == pytest.approx(0.9 * 0.85 * 30 / 1.4)


# --- Figura 17.1 domínios (p. 142) ------------------------------------------
def test_pivo_C():
    assert nbr.pivo_C_distancia_relativa(30) == pytest.approx(3 / 7)
    assert nbr.pivo_C_distancia_relativa(70) == pytest.approx((2.656 - nbr.eps_c2(70)) / 2.656)
    assert nbr.pivo_C_distancia_relativa(90) == 0.0


def test_limites_de_dominio():
    assert nbr.x_lim_dominio_2_3(100, 30) == pytest.approx(3.5 / 13.5 * 100)
    eyd = 500 / 1.15 / 210000 * 1000
    assert nbr.x_lim_dominio_3_4(100, 30) == pytest.approx(3.5 / (3.5 + eyd) * 100)


def test_eps_compressao_uniforme():
    assert nbr.eps_compressao_uniforme(30) == 2.0
    assert nbr.eps_compressao_uniforme(70) == pytest.approx(nbr.eps_c2(70))
    assert nbr.eps_compressao_uniforme(90) == pytest.approx(2.6)     # εc2(90) > εcu(90)


# --- Pilares: 11.3.3.4.3, 15.3.1, 17.3.5.3 (p. 80, 121, 153) ----------------
def test_M1d_min():
    assert nbr.M1d_min_kncm(1400.0, 20.0) == pytest.approx(2940.0)   # exemplo da apostila
    assert nbr.M1d_min_kncm(1400.0, 50.0) == pytest.approx(4200.0)
    assert nbr.M1d_min_kncm(-100.0, 20.0) == 0.0


def test_armadura_de_pilar():
    # FCO-09: 30x60, C30, Nd = 300 kN -> 0,004·Ac = 7,20 cm² governa
    assert nbr.As_min_pilar_cm2(300.0, 1800.0) == pytest.approx(7.20)
    # Nd alto: 0,15·Nd/fyd governa (Nd = 4000 kN -> 13,80 cm²)
    assert nbr.As_min_pilar_cm2(4000.0, 1800.0) == pytest.approx(0.15 * 4000 / (50 / 1.15))
    assert nbr.As_max_pilar_cm2(1800.0) == pytest.approx(144.0)
    assert nbr.GAMA_F3 == 1.1


# --- 14.6.4.3 dutilidade (p. 112) -------------------------------------------
def test_xd_limite():
    assert nbr.xd_limite_dutilidade(50) == 0.45
    assert nbr.xd_limite_dutilidade(55) == 0.35
    assert nbr.xd_limite_dutilidade(90) == 0.35


# --- Tabela 17.3 (p. 151) ---------------------------------------------------
def test_rho_min_tabela_e_interpolacao():
    assert nbr.rho_min_flexao(30) == pytest.approx(0.00150)
    assert nbr.rho_min_flexao(22) == pytest.approx(0.00150)         # VIG-08
    assert nbr.rho_min_flexao(37.5) == pytest.approx((0.164 + 0.179) / 2 / 100)
    assert nbr.rho_min_flexao(60) == pytest.approx(0.00219)          # LAJ-06
    assert nbr.rho_min_flexao(90) == pytest.approx(0.00256)


@pytest.mark.parametrize("fck", sorted(nbr.RHO_MIN_TABELA_17_3))
def test_definicao_17_3_5_2_1_reproduz_tabela_17_3(fck):
    # Premissas da nota da Tabela 17.3: CA-50, d/h = 0,8, γc = 1,4, γs = 1,15.
    # De C55 a C90 a tabela foi calculada com o fct,m de 2014, 2,12·ln(1 + 0,11·fck):
    # com a fórmula de 2023/2026 a definição dá até +1,6 % (C55). Por isso a
    # tolerância de 2 %. Com o fct de 2014 a definição bate com a tabela em ±0,7 %.
    bw, h = 20.0, 50.0
    As = nbr.As_min_flexao_retangular(bw, h, 0.8 * h, fck)
    rho = As / (bw * h) * 100.0
    assert rho == pytest.approx(nbr.RHO_MIN_TABELA_17_3[fck], rel=0.02)


# --- Tabela 8.2 e 9.3.2 aderência (p. 48 e 54) ------------------------------
def test_eta1_por_categoria():
    assert nbr.eta1("CA-25") == 1.0
    assert nbr.eta1("CA50") == 2.25
    assert nbr.eta1("ca-60") == 1.0      # ANC-01: CA-60 é 1,00 na 2026


def test_eta2_eta3_fbd():
    assert nbr.eta2(False) == 0.7
    assert nbr.eta3(25) == 1.0
    assert nbr.eta3(40) == pytest.approx(0.92)
    assert nbr.fbd(25, "CA-50", True, 10) == pytest.approx(2.25 * nbr.fctd(25))   # 2,8856
    assert nbr.fbd(25, "CA-60", True, 8) == pytest.approx(nbr.fctd(25))


def test_fbpd():
    assert nbr.fbpd(30, "cordoalha", True) == pytest.approx(1.2 * nbr.fctd(30))
    assert nbr.fbpd(30, "fio dentado", False) == pytest.approx(1.4 * 0.7 * nbr.fctd(30))


# --- αv2 (17.4.2.2, 19.5.3.1, 22.3.2) ---------------------------------------
def test_alpha_v2():
    assert nbr.alpha_v2(25) == pytest.approx(0.9)
    assert nbr.alpha_v2(90) == pytest.approx(0.64)
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.alpha_v2(100)


# --- 19.4.1 τRd com teto de fck = 60 MPa (p. 181) ---------------------------
def test_tau_Rd_teto_60():
    assert nbr.tau_Rd(30) == pytest.approx(0.25 * nbr.fctd(30))
    assert nbr.tau_Rd(90) == pytest.approx(nbr.tau_Rd(60))       # CRT-02 / LAJ-05
    assert nbr.tau_Rd(70) < 0.25 * nbr.fctd(70)


# --- 8.3 aço passivo (p. 47-49) ---------------------------------------------
def test_aco():
    assert nbr.fyk_categoria("CA-60") == 600.0
    assert nbr.fyd(500) == pytest.approx(434.78, abs=0.01)
    assert nbr.eps_yd(500) == pytest.approx(2.0704, abs=1e-4)
    assert nbr.sigma_s(2.0, 500) == pytest.approx(420.0)
    assert nbr.sigma_s(5.0, 500) == pytest.approx(434.78, abs=0.01)
    assert nbr.sigma_s(-5.0, 500) == pytest.approx(-434.78, abs=0.01)
