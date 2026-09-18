"""Testes do legado (secoes_norma/sec7,sec8,sec17; flexao_simples.py;
conv_unidades.py) contra a ABNT NBR 6118:2026.

Reproduções de REPO\\AUDITORIA_NBR6118_2026.md (achados LEG-01 a LEG-13,
com os ajustes de SCRATCH\\verificacao_resultados.md). Os valores esperados
vêm da fórmula/tabela da norma ou do núcleo (dimensionamento/nucleo_nbr6118.py,
já testado em tests/test_nucleo_nbr6118.py contra a própria norma), nunca de
apostilas.
"""

import math
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _p in (
    _REPO / "dimensionamento",
    _REPO / "dimensionamento" / "rotinas",
    _REPO / "secoes_norma",
    _REPO / "utilitarios",
):
    sp = str(_p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

import nucleo_nbr6118 as nbr   # noqa: E402
import sec7                     # noqa: E402
import sec8                     # noqa: E402
import sec17                    # noqa: E402
import flexao_simples as fs     # noqa: E402
import conv_unidades as cv      # noqa: E402


# --- LEG-01: Tabela 7.2 (PDF p. 39) - cobrimento CA viga/pilar CAA I = 25mm
def test_leg01_cobrimento_viga_pilar_caa1_25mm():
    resultado = sec7.CAAPropriedades("CAI", "CA")
    assert resultado[3] == 25          # antes da correcao: 22


def test_leg01_tabela_7_2_completa_concreto_armado():
    # Tabela 7.2 inteira (conferida na imagem p. 39) - nao regredir o resto
    esperado_laje = {"CAI": 20, "CAII": 25, "CAIII": 35, "CAIV": 45}
    esperado_vigpil = {"CAI": 25, "CAII": 30, "CAIII": 40, "CAIV": 50}
    esperado_solo = {"CAI": 30, "CAII": 30, "CAIII": 40, "CAIV": 50}
    for caa, esperado in esperado_laje.items():
        assert sec7.CAAPropriedades(caa, "CA")[2] == esperado
    for caa, esperado in esperado_vigpil.items():
        assert sec7.CAAPropriedades(caa, "CA")[3] == esperado
    for caa, esperado in esperado_solo.items():
        assert sec7.CAAPropriedades(caa, "CA")[4] == esperado


def test_leg01_tabela_7_2_concreto_protendido_nao_regrediu():
    esperado_vigpil_cp = {"CAI": 30, "CAII": 35, "CAIII": 45, "CAIV": 55}
    for caa, esperado in esperado_vigpil_cp.items():
        assert sec7.CAAPropriedades(caa, "CP")[3] == esperado


# --- LEG-02: fckj usa s = 0,20 para C60 ou mais, qualquer cimento ----------
def test_leg02_fckj_c60_ou_mais_usa_s_020():
    C = sec8.Concreto(70, t=7, cimento="CPIV")
    assert C.fck_j == pytest.approx(nbr.fckj(70, 7, "CPIV"))
    assert C.fck_j == pytest.approx(57.31, abs=0.01)   # achados_brutos LEG-02


def test_leg02_fckj_abaixo_de_c60_usa_s_do_cimento():
    # controle: para fck < 60 o comportamento antigo (s pelo cimento) segue valendo
    C = sec8.Concreto(30, t=7, cimento="CPIII")
    assert C.fck_j == pytest.approx(30.0 * math.exp(0.38 * (1 - math.sqrt(28/7))))


# --- LEG-03: fcd usa fckj (nao fck) para t < 28 dias -----------------------
def test_leg03_fcd_usa_fckj_antes_de_28_dias():
    C = sec8.Concreto(30, t=7, cimento="CPIII")
    assert C.fcd == pytest.approx(14.65, abs=0.01)     # achados_brutos LEG-03
    assert C.fcd == pytest.approx(C.fck_j / C.y_c)


def test_leg03_fcd_em_28_dias_nao_regrediu():
    C = sec8.Concreto(30)   # t=28 (padrao)
    assert C.fcd == pytest.approx(30 / 1.4)


# --- LEG-04 = ANC-09: fct,m com a formula de 2023/2026 (fck > 50) ----------
@pytest.mark.parametrize("fck, esperado", [(55.0, 4.2143), (90.0, 5.0446)])
def test_leg04_fct_m_formula_2026_para_fck_acima_de_50(fck, esperado):
    C = sec8.Concreto(fck)
    assert C.fct_m == pytest.approx(esperado, abs=1e-3)
    assert C.fct_m == pytest.approx(nbr.fct_m(fck))


def test_leg04_fct_m_ate_50_nao_mudou():
    # ate C50 a formula sempre foi 0,3*fck^(2/3); nao deve mudar
    C = sec8.Concreto(30.0)
    assert C.fct_m == pytest.approx(0.3 * 30.0 ** (2/3))


# --- LEG-05: Eci(t) nao aplica o efeito da idade em dobro ------------------
def test_leg05_Eci_idade_nao_duplica_efeito():
    C = sec8.Concreto(30, t=7, cimento="CPIII")
    assert C.E_ci == pytest.approx(25364.9, abs=1.0)   # achados_brutos LEG-05
    assert C.E_ci == pytest.approx(nbr.Eci_idade(30, C.fck_j))


# --- LEG-06: alpha_i usa fck (idade de projeto), nao fckj ------------------
def test_leg06_alpha_i_usa_fck_nao_fckj():
    C = sec8.Concreto(30, t=7, cimento="CPIII")
    assert C.E_cs == pytest.approx(nbr.alpha_i(30) * C.E_ci)
    assert nbr.alpha_i(30) != pytest.approx(nbr.alpha_i(C.fck_j))  # eram diferentes


# --- Varredura de classes: Concreto bate com o nucleo em t = 28 dias -------
@pytest.mark.parametrize("fck", [45.0, 50.0, 55.0, 70.0, 90.0])
def test_concreto_bate_com_nucleo_c45_a_c90(fck):
    C = sec8.Concreto(fck)
    assert C.fck_j == pytest.approx(fck)
    assert C.fct_m == pytest.approx(nbr.fct_m(fck))
    assert C.E_ci == pytest.approx(nbr.Eci(fck, C.a_E))
    assert C.E_cs == pytest.approx(nbr.alpha_i(fck) * nbr.Eci(fck, C.a_E))
    assert C.fcd == pytest.approx(fck / 1.4)


def test_validacao_faixa_fck_acima_de_90_nao_da_mais_unboundlocalerror():
    with pytest.raises(nbr.FaixaNormativaError):
        sec8.Concreto(120.0)


# --- LEG-07 / LEG-07b: sigma_c (tipo 'b') com etac e patamar em 0,85 -------
def test_leg07_sigma_c_com_eta_c():
    C = sec8.Concreto(60.0)
    assert C.o_c_de_Eps_c(1.0, 'b') == pytest.approx(19.056, abs=1e-3)  # achados LEG-07


def test_leg07b_patamar_com_085_e_continuo_em_eps_c2():
    C = sec8.Concreto(30.0)
    pico = 0.85 * (30.0 / 1.4)
    assert C.o_c_de_Eps_c(2.0, 'b') == pytest.approx(pico)
    assert C.o_c_de_Eps_c(3.5, 'b') == pytest.approx(pico)          # ate Eps_cu
    assert C.o_c_de_Eps_c(1.99999, 'b') == pytest.approx(pico, rel=1e-4)
    assert C.o_c_de_Eps_c(3.500001, 'b') == 0.0                      # alem de Eps_cu


@pytest.mark.parametrize("fck", [45.0, 50.0, 55.0, 70.0, 90.0])
def test_leg07_sigma_c_bate_com_nucleo_c45_a_c90(fck):
    C = sec8.Concreto(fck)
    assert C.o_c_de_Eps_c(1.0, 'b') == pytest.approx(nbr.sigma_c(1.0, fck, C.y_c))


def test_leg07b_patamar_bate_com_nucleo_c70():
    # C90 fica de fora deste ponto: a propria norma da Eps_c2(90)=2,6005 >
    # Eps_cu(90)=2,6 (nucleo.pivo_C_distancia_relativa ja documenta isso),
    # entao "no patamar" nao existe estritamente para C90.
    C = sec8.Concreto(70.0)
    assert C.Eps_c2 < C.Eps_cu
    assert C.o_c_de_Eps_c(C.Eps_c2, 'b') == pytest.approx(0.85 * nbr.eta_c(70.0) * C.fcd)


# --- LEG-08: eta1 por categoria do aco (Tabela 8.2), nao pela superficie ---
def test_leg08_eta1_por_categoria_nao_por_superficie():
    A_ca60 = sec8.Aco_Passivo('CA60', 'nervurada')
    assert A_ca60.n_1 == pytest.approx(1.00)     # antes: 2,25 (regra de superficie)
    A_ca50 = sec8.Aco_Passivo('CA50', 'lisa')
    assert A_ca50.n_1 == pytest.approx(2.25)     # antes: 1,00
    A_ca25 = sec8.Aco_Passivo('CA25', 'entalhada')
    assert A_ca25.n_1 == pytest.approx(1.00)


# --- LEG-09: t0 vira parametro, com padrao de 1 mes ------------------------
def test_leg09_t0_e_parametro_com_padrao_1_mes():
    af_padrao = sec17.multiplicador_flecha_diferida(0, 10)
    af_t0_1 = sec17.multiplicador_flecha_diferida(0, 10, t0_meses=1)
    assert af_padrao == pytest.approx(af_t0_1)
    xi_1 = 0.68 * (0.996 ** 1) * 1 ** 0.32       # Tabela 17.1: xi(1) = 0,68 (arred.)
    xi_10 = 0.68 * (0.996 ** 10) * 10 ** 0.32    # Tabela 17.1: xi(10) = 1,36 (arred.)
    assert xi_10 == pytest.approx(1.36, abs=0.01)
    assert af_padrao == pytest.approx(xi_10 - xi_1)


def test_leg09_t0_diferente_muda_o_resultado():
    af_t0_1 = sec17.multiplicador_flecha_diferida(0, 70, t0_meses=1)
    af_t0_2 = sec17.multiplicador_flecha_diferida(0, 70, t0_meses=2)
    # carga de longa duracao aplicada mais tarde -> menos fluencia acumulada
    assert af_t0_2 < af_t0_1


def test_leg09_tabela_17_1_extremos():
    # Tabela 17.1 (PDF p. 129): xi(0) = 0; xi(t) = 2 para t > 70 meses
    assert sec17.multiplicador_flecha_diferida(0, 0, t0_meses=0) == pytest.approx(0.0)
    af_75 = sec17.multiplicador_flecha_diferida(0, 75, t0_meses=1)
    af_70 = sec17.multiplicador_flecha_diferida(0, 70, t0_meses=1)
    assert af_75 == pytest.approx(af_70, abs=1e-2)   # continuo no limite de 70 meses


# --- LEG-10: VRd2 ganha "return" e o modelo de calculo II ------------------
def test_leg10_modelo_1_agora_retorna_valor():
    # achados_brutos LEG-10: VRd2(30, 21,43, 0,20, 0,54, 1, ...) = 549,9 kN
    fcd = nbr.fcd(30.0)
    resultado = sec17.VRd2(30.0, fcd, 0.20, 0.54, 1, "flsimples_fltracao")
    assert resultado is not None
    assert resultado == pytest.approx(549.9, abs=0.2)


@pytest.mark.parametrize("fck", [30.0, 45.0, 50.0, 55.0, 70.0, 90.0])
def test_leg10_modelo_1_varias_classes(fck):
    fcd = nbr.fcd(fck)
    resultado = sec17.VRd2(fck, fcd, 0.20, 0.50, 1, "x")
    esperado = 0.27 * (1 - fck/250.0) * fcd * 0.20 * 0.50 * 1000.0
    assert resultado == pytest.approx(esperado, rel=1e-9)


def test_leg10_modelo_2_bate_com_formula_da_norma_p140():
    # 17.4.2.3: VRd2 = 0,54*alfa_v2*fcd*bw*d*sen^2(theta)*(cotg(alfa)+cotg(theta))
    fck, bw, d, theta_graus = 30.0, 0.20, 0.54, 30.0
    fcd = nbr.fcd(fck)
    resultado = sec17.VRd2(fck, fcd, bw, d, 2, "flsimples_fltracao", theta_graus=theta_graus)

    alfa_v2 = 1 - fck/250.0
    theta = math.radians(theta_graus)
    cotg_theta = math.cos(theta) / math.sin(theta)     # via cos/sen, independente da implementacao
    cotg_alfa_90 = 0.0                                  # alfa = 90 graus (padrao)
    esperado = 0.54*alfa_v2*fcd*bw*d*math.sin(theta)**2*(cotg_alfa_90 + cotg_theta)*1000.0
    assert resultado == pytest.approx(esperado, rel=1e-6)


def test_leg10_modelo_2_theta_fora_da_faixa_leva_erro():
    fcd = nbr.fcd(30.0)
    with pytest.raises(ValueError):
        sec17.VRd2(30.0, fcd, 0.20, 0.54, 2, "x", theta_graus=15.0)
    with pytest.raises(ValueError):
        sec17.VRd2(30.0, fcd, 0.20, 0.54, 2, "x", theta_graus=50.0)


def test_leg10_modelo_invalido_leva_erro():
    fcd = nbr.fcd(30.0)
    with pytest.raises(ValueError):
        sec17.VRd2(30.0, fcd, 0.20, 0.54, 3, "x")


# --- LEG-11: calc_a_c_coef_lambda devolve alpha_c*etac e lambda do nucleo --
@pytest.mark.parametrize("fck", [30.0, 45.0, 50.0, 55.0, 70.0, 90.0])
def test_leg11_calc_a_c_coef_lambda_bate_com_nucleo(fck):
    a_c, coef_lambda = fs.calc_a_c_coef_lambda(fck)
    assert a_c == pytest.approx(nbr.alpha_c(fck) * nbr.eta_c(fck))
    assert coef_lambda == pytest.approx(nbr.lambda_retangulo(fck))


def test_leg11_reproducao_achado_fck_30():
    # achados_brutos LEG-11: bw=14, d=45 cm, Md=180 kN.m, CA-50 -> As = 11,87 cm2
    bw_m, d_m, Md_kNm = 0.14, 0.45, 180.0
    fyd_mpa = 500.0 / 1.15
    a_c, coef_lambda = fs.calc_a_c_coef_lambda(30.0)
    fcd_mpa = nbr.fcd(30.0)
    x = fs.calc_x(d_m, fcd_mpa, Md_kNm, bw_m, a_c, coef_lambda)
    As_cm2 = fs.calc_As(fyd_mpa, Md_kNm, d_m, coef_lambda, x) * cv.convArea('m2', 'cm2')
    assert As_cm2 == pytest.approx(11.87, abs=0.02)


@pytest.mark.parametrize("fck", [50.0, 70.0])
def test_leg11_reproducao_fck_50_e_70_bate_com_equilibrio_da_norma(fck):
    # pedido explicito: reproduzir o LEG-11 com fck = 50 e fck = 70
    bw_m, d_m, Md_kNm = 0.14, 0.45, 180.0
    fyd_mpa = 500.0 / 1.15

    a_c, coef_lambda = fs.calc_a_c_coef_lambda(fck)
    fcd_mpa = nbr.fcd(fck)

    x = fs.calc_x(d_m, fcd_mpa, Md_kNm, bw_m, a_c, coef_lambda)
    As = fs.calc_As(fyd_mpa, Md_kNm, d_m, coef_lambda, x)

    # equilibrio re-derivado a parte (nao usa calc_a_c_coef_lambda em si)
    tensao_kpa = nbr.alpha_c(fck) * nbr.eta_c(fck) * fcd_mpa * 1000.0
    lam = nbr.lambda_retangulo(fck)
    x_esperado = (d_m - math.sqrt(d_m**2 - 2*Md_kNm/(bw_m*tensao_kpa))) / lam
    As_esperado = Md_kNm / ((d_m - 0.5*lam*x_esperado) * fyd_mpa * 1000.0)

    assert x == pytest.approx(x_esperado, rel=1e-9)
    assert As == pytest.approx(As_esperado, rel=1e-9)

    # tem que pedir mais aco que a regressao local (a_c = 1), que era contra
    # a seguranca (achados_brutos: -5,4% a -7,9% no As)
    x_regressao = fs.calc_x(d_m, fcd_mpa, Md_kNm, bw_m, 1.0, coef_lambda)
    As_regressao = fs.calc_As(fyd_mpa, Md_kNm, d_m, coef_lambda, x_regressao)
    assert As > As_regressao


def test_leg11_vigas_py_ainda_roda():
    # dimensionamento/vigas.py e' script de estudo do Gustavo (nao editado);
    # confere so' que continua rodando e devolvendo um As positivo e finito
    # depois da correcao de calc_a_c_coef_lambda.
    import vigas
    As = vigas.dim_flexao_simples(203.4, 60)
    assert As > 0
    assert math.isfinite(As)


# --- LEG-12: g = 10 (1 tf = 10 kN) e' convencao documentada, nao corrigida -
def test_leg12_conversao_tf_kn_usa_g_10_documentado():
    assert cv.convForca('tf', 'kN') == pytest.approx(10.0)
    assert cv.convForca('tf', 'kN') != pytest.approx(9.80665, rel=1e-3)


# --- LEG-13: o print ativo no fim do modulo foi comentado ------------------
def test_leg13_import_nao_imprime_mais_nada(capsys):
    import importlib
    importlib.reload(cv)
    capturado = capsys.readouterr()
    assert capturado.out == ""
