"""Testes do P30 -- Protensão: força, limites e perdas (NBR 6118:2026,
9.6.1.1 a 9.6.1.4 e 9.6.3.3.2.1, 9.6.3.3.2.2, 9.6.3.4.2, 9.6.3.4.3, 9.6.3.4.5).

Valores esperados tirados das imagens das páginas do PDF (SCRATCH/nbr_png):
p067 (9.6.1.1, 9.6.1.2.1 a 9.6.1.2.3), p068 (9.6.1.3, 9.6.1.4), p070
(9.6.3.3.2.1), p071 (9.6.3.3.2.2), p072 (9.6.3.4.2), p073 (9.6.3.4.3) e p074
(9.6.3.4.5). As contas à mão estão nos comentários; Eci de granito
(αE = 1,0) é 5600·√fck para fck <= 50 MPa (8.2.8).
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import protendido_nbr6118 as PT  # noqa: E402

EP = 200000.0


def _eci_granito(fck):
    return 5600.0 * math.sqrt(fck)


# ===========================================================================
# 9.6.1.1 -- Força média Pt(x) (PDF p. 67)
# ===========================================================================
def test_9611_sem_perdas_Pt_igual_Pi():
    assert PT.forca_media_kn(1000.0) == pytest.approx(1000.0)
    assert PT.forca_media_kn(1000.0, 0.0, 0.0) == pytest.approx(1000.0)


def test_9611_com_perda_por_atrito_conhecida():
    # ΔP = 1000·[1 − e^−(0,20·0,30 + 0,002·10)] = 1000·(1 − e^−0,08) = 76,884 kN
    dP = PT.perda_atrito_kn(1000.0, 0.20, 0.30, 0.002, 10.0)
    assert dP == pytest.approx(1000.0 * (1.0 - math.exp(-0.08)))
    assert PT.forca_media_kn(1000.0, dP) == pytest.approx(1000.0 - dP)


def test_9611_P0_e_Pt_com_parcelas():
    # P0 = 1000 − (60 + 20) = 920; Pt = 920 − (50 + 30 + 20) = 820 kN
    assert PT.forca_media_kn(1000.0, [60.0, 20.0]) == pytest.approx(920.0)
    assert PT.forca_media_kn(1000.0, [60.0, 20.0], [50.0, 30.0, 20.0]) == pytest.approx(820.0)


@pytest.mark.parametrize("Pi, dp0, dpt", [
    (1000.0, 600.0, 400.0),   # Pt = 0
    (1000.0, 800.0, 400.0),   # Pt < 0
    (0.0, 0.0, 0.0),          # Pi nulo
    (1000.0, -10.0, 0.0),     # perda negativa
])
def test_9611_fora_da_faixa(Pi, dp0, dpt):
    with pytest.raises(nbr.FaixaNormativaError):
        PT.forca_media_kn(Pi, dp0, dpt)


# ===========================================================================
# 9.6.1.2.1 -- Limites de σpi (PDF p. 67)
# ===========================================================================
@pytest.mark.parametrize("sistema, aco, fptk, esperado", [
    ("pre_tracionada", "fio_cordoalha", 1900.0, 0.77 * 1900.0),              # 1463
    ("pos_tracionada_aderente", "fio_cordoalha", 1900.0, 0.74 * 1900.0),     # 1406
    ("pos_tracionada_nao_aderente", "fio_cordoalha", 1900.0, 0.80 * 1900.0),  # 1520
    ("pos_tracionada_aderente", "barra", 1050.0, 0.72 * 1050.0),             # 756
    ("pre_tracionada", "barra", 1050.0, 0.72 * 1050.0),                      # d) vale sempre
])
def test_96121_quatro_limites(sistema, aco, fptk, esperado):
    assert PT.sigma_pi_limite_mpa(fptk, sistema, aco) == pytest.approx(esperado)


def test_96121_valores_do_teste_sugerido_CP190():
    assert PT.sigma_pi_limite_mpa(1900.0, "pre") == pytest.approx(1463.0)
    assert PT.sigma_pi_limite_mpa(1900.0, "pos_aderente") == pytest.approx(1406.0)
    assert PT.sigma_pi_limite_mpa(1900.0, "pós-tracionada não aderente") == pytest.approx(1520.0)


def test_96121_tabela_como_dado():
    assert PT.TABELA_9_6_1_2_1_SIGMA_PI == {
        "pre_tracionada": 0.77, "pos_tracionada_aderente": 0.74,
        "pos_tracionada_nao_aderente": 0.80, "barra_cp85_105": 0.72,
    }


def test_96121_verificacao_dos_dois_lados_do_limite():
    ok = PT.verificar_sigma_pi(1463.0, 1900.0, "pre")
    assert ok.ok and ok.limite_mpa == pytest.approx(1463.0)
    assert "9.6.1.2.1-a)" in ok.memoria[0]
    nao = PT.verificar_sigma_pi(1463.1, 1900.0, "pre")
    assert not nao.ok
    assert PT.verificar_sigma_pi(756.0, 1050.0, "pos_aderente", aco="barra").ok
    assert not PT.verificar_sigma_pi(756.1, 1050.0, "pos_aderente", aco="barra").ok


def test_96121_entradas_invalidas():
    with pytest.raises(ValueError):
        PT.sigma_pi_limite_mpa(1900.0, "protendido")
    with pytest.raises(ValueError):
        PT.sigma_pi_limite_mpa(1900.0, "pre", aco="vergalhao")
    with pytest.raises(nbr.FaixaNormativaError):
        PT.sigma_pi_limite_mpa(0.0, "pre")


# ===========================================================================
# 9.6.1.2.2 -- σp0(x) ao término da protensão <= 0,74·fptk (PDF p. 67)
# ===========================================================================
def test_96122_sigma_p0_limite_b():
    r = PT.verificar_sigma_p0(1406.0, 1900.0)   # 0,74·1900 = 1406 (igualdade passa)
    assert r.ok and r.limite_mpa == pytest.approx(1406.0)
    assert not PT.verificar_sigma_p0(1406.1, 1900.0).ok
    assert PT.verificar_sigma_p0(1300.0, 1900.0).ok


# ===========================================================================
# 9.6.1.2.3 -- Tolerância de execução (PDF p. 67)
# ===========================================================================
def test_96123_tolerancia_dentro():
    # base = 0,74·1900 = 1406; majorado = 1,10·1406 = 1546,6 MPa.
    # 2 de 4 cabos acima de 1406 -> 2 <= 0,5·4 = 2 (fronteira) -> ok.
    r = PT.tolerancia_execucao([1546.6, 1500.0, 1406.0, 1400.0], 1900.0)
    assert r.limite_base_mpa == pytest.approx(1406.0)
    assert r.limite_majorado_mpa == pytest.approx(1546.6)
    assert r.n_cabos_majorados == 2 and r.n_max_majorados == pytest.approx(2.0)
    assert r.ok


def test_96123_tensao_acima_de_110_por_cento():
    r = PT.tolerancia_execucao([1546.7, 1400.0, 1400.0, 1400.0], 1900.0)
    assert not r.ok and "1,10" in r.governante


def test_96123_mais_de_50_por_cento_dos_cabos():
    r = PT.tolerancia_execucao([1500.0, 1500.0, 1500.0, 1400.0], 1900.0)
    assert r.n_cabos_majorados == 3 and not r.ok and "50 %" in r.governante


def test_96123_lista_vazia():
    with pytest.raises(ValueError):
        PT.tolerancia_execucao([], 1900.0)


# ===========================================================================
# 9.6.1.3 -- Pk,t sup e inf (PDF p. 68)
# ===========================================================================
def test_9613_perda_acima_de_035_Pi():
    # Pt = 1000; perda máx = 400 > 0,35·1000 = 350 -> sup = 1050, inf = 950 kN.
    r = PT.Pk_sup_inf_kn(1000.0, 400.0, 1000.0)
    assert r.usa_sup_inf
    assert r.Pk_sup_kn == pytest.approx(1050.0)
    assert r.Pk_inf_kn == pytest.approx(950.0)


def test_9613_perda_igual_035_Pi_fica_valor_medio():
    # "maior que 0,35 Pi": igualdade não aciona.
    r = PT.Pk_sup_inf_kn(1000.0, 350.0, 1000.0)
    assert not r.usa_sup_inf
    assert r.Pk_sup_kn == pytest.approx(1000.0) and r.Pk_inf_kn == pytest.approx(1000.0)
    r2 = PT.Pk_sup_inf_kn(1000.0, 350.001, 1000.0)
    assert r2.usa_sup_inf


def test_9613_obra_especial():
    r = PT.Pk_sup_inf_kn(800.0, 100.0, 1000.0, obra_especial=True)
    assert r.Pk_sup_kn == pytest.approx(840.0) and r.Pk_inf_kn == pytest.approx(760.0)


# ===========================================================================
# 9.6.1.4 -- Pd,t = γp·Pt (PDF p. 68; γp da Tabela 11.1, p. 85)
# ===========================================================================
def test_9614_Pd():
    assert PT.Pd_kn(1000.0) == pytest.approx(1200.0)                   # γp = 1,2 (D)
    assert PT.Pd_kn(1000.0, favoravel=True) == pytest.approx(900.0)   # γp = 0,9 (F)
    assert PT.Pd_kn(1000.0, combinacao="excepcional") == pytest.approx(1200.0)
    assert PT.Pd_kn(1000.0, gama_p=1.1) == pytest.approx(1100.0)
    with pytest.raises(nbr.FaixaNormativaError):
        PT.Pd_kn(1000.0, gama_p=0.0)


# ===========================================================================
# 9.6.3.3.2.1 -- Encurtamento entre grupos de cabos com αp(t) (PDF p. 70 e 72)
# ===========================================================================
def test_963321_padrao_mantem_alpha_p_28_dias():
    # Sem t0: αp = 200000/(5600·√40) = 5,6470; Δσp = αp·3/8·1,0 kN/cm²
    esperado = EP / _eci_granito(40.0) * 3.0 / 8.0 * 1.0
    assert PT.perda_encurtamento_cabos_restantes_kncm2(4, 1.0, 40.0) == pytest.approx(esperado)
    assert PT.perda_encurtamento_cabos_restantes_kncm2(4, 1.0, 40.0, t0_dias=28.0) \
        == pytest.approx(esperado)


def test_963321_alpha_p_t_aos_7_dias():
    # CPII, s = 0,25; β1(7) = exp[0,25·(1 − √(28/7))] = e^−0,25 = 0,77880
    # Eci(7) = √0,77880·Eci = 0,88250·35417,5 = 31256 MPa; αp(7) = 6,3988
    beta1 = math.exp(0.25 * (1.0 - math.sqrt(28.0 / 7.0)))
    eci7 = math.sqrt(beta1) * _eci_granito(40.0)
    assert PT.alpha_p_t(40.0, 7.0) == pytest.approx(EP / eci7)
    esperado = EP / eci7 * 3.0 / 8.0 * 1.0
    assert PT.perda_encurtamento_cabos_restantes_kncm2(4, 1.0, 40.0, t0_dias=7.0) \
        == pytest.approx(esperado)


def test_963321_alpha_p_t_interior_e_ensaio():
    # t0 = 14 dias: β1 = exp[0,25·(1 − √2)] = 0,90163
    beta1 = math.exp(0.25 * (1.0 - math.sqrt(2.0)))
    assert PT.alpha_p_t(30.0, 14.0) == pytest.approx(EP / (math.sqrt(beta1) * _eci_granito(30.0)))
    assert PT.alpha_p_t(30.0, 3.0, Eci_t0_mpa=25000.0) == pytest.approx(8.0)
    # n = 2: (n−1)/(2n) = 1/4; αp = 8 -> 8·0,25·1,2 = 2,4 kN/cm²
    assert PT.perda_encurtamento_cabos_restantes_kncm2(2, 1.2, 30.0, Eci_t0_mpa=25000.0) \
        == pytest.approx(2.4)


def test_963321_abaixo_de_7_dias_sem_ensaio_levanta():
    with pytest.raises(nbr.FaixaNormativaError):
        PT.alpha_p_t(40.0, 6.99)
    with pytest.raises(nbr.FaixaNormativaError):
        PT.perda_encurtamento_cabos_restantes_kncm2(4, 1.0, 40.0, t0_dias=5.0)


# ===========================================================================
# 9.6.3.3.2.2 -- μ e k (PDF p. 71)
# ===========================================================================
@pytest.mark.parametrize("contato, mu, k", [
    ("cabo_concreto_sem_bainha", 0.50, 0.0050),
    ("barra_ou_fio_com_mossas_bainha_metalica", 0.30, 0.0030),
    ("fio_liso_ou_cordoalha_bainha_metalica", 0.20, 0.0020),
    ("fio_liso_ou_cordoalha_bainha_metalica_lubrificada", 0.10, 0.0010),
    ("cordoalha_bainha_polipropileno_lubrificada", 0.07, 0.065 * 0.07),  # 0,00455
])
def test_963322_tabela_mu_k(contato, mu, k):
    m, kk = PT.coeficientes_atrito(contato)
    assert m == pytest.approx(mu)
    assert kk == pytest.approx(k)


def test_963322_contato_desconhecido():
    with pytest.raises(ValueError):
        PT.coeficientes_atrito("bainha_plastica")


# ===========================================================================
# 9.6.3.4.2 -- Δεpt e Δεct (PDF p. 72)
# ===========================================================================
def test_96342_deformacoes_valor_a_mao():
    # σp0 = 1300, Δσp = 200, σc,p0g = 10, Δσc = 1 MPa; φ = 2; ψ = 5 %; εcs = −0,3 ‰;
    # Eci = 30000 MPa. χ = −ln 0,95 = 0,051293; χp = 1,051293; χc = 2.
    # Δεpt = (1300/200000·0,051293 − 200/200000·1,051293)·1000 = −0,717886 ‰
    # Δεct = (10/30000·2 − 1/30000·2)·1000 + 0,3 = 0,9 ‰
    r = PT.deformacoes_aco_concreto(1300.0, 200.0, 10.0, 1.0, 2.0, 5.0, -0.3,
                                    fck_mpa=40.0, Eci_28_mpa=30000.0)
    chi = -math.log(0.95)
    assert r.chi == pytest.approx(chi)
    assert r.chi_p == pytest.approx(1.0 + chi) and r.chi_c == pytest.approx(2.0)
    assert r.deps_pt_pmil == pytest.approx((1300.0 / EP * chi - 200.0 / EP * (1.0 + chi)) * 1000.0)
    assert r.deps_pt_pmil == pytest.approx(-0.717886, abs=1e-6)
    assert r.deps_ct_pmil == pytest.approx(0.9)


def test_96342_compatibilidade_com_processo_simplificado():
    # Com Δσp de perda_progressiva_simplificada (t0 = 28 d, αp(t) = αp) e
    # Δσc = η·ρp·Δσp, a dedução do processo dá Δεpt + Δεct = 0.
    Ap, Ac, Ic, ep = 10.0, 3000.0, 900000.0, 30.0
    dados = dict(eps_cs_permil=-0.25, psi_percent=6.0, phi_inf=2.2,
                 sigma_c_p0g_mpa=8.0, sigma_p0_mpa=1250.0)
    dsp = PT.perda_progressiva_simplificada(Ap_cm2=Ap, Ac_cm2=Ac, Ic_cm4=Ic, ep_cm=ep,
                                            fck_mpa=35.0, **dados)
    eta = 1.0 + ep ** 2 * Ac / Ic
    dsc = eta * (Ap / Ac) * dsp
    r = PT.deformacoes_aco_concreto(1250.0, dsp, 8.0, dsc, 2.2, 6.0, -0.25, fck_mpa=35.0)
    assert r.deps_pt_pmil + r.deps_ct_pmil == pytest.approx(0.0, abs=1e-12)


def test_96342_fora_da_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        PT.deformacoes_aco_concreto(1300.0, 200.0, 10.0, 1.0, 2.0, 100.0, -0.3, fck_mpa=40.0)
    with pytest.raises(nbr.FaixaNormativaError):
        PT.deformacoes_aco_concreto(1300.0, 200.0, 10.0, 1.0, -0.1, 5.0, -0.3, fck_mpa=40.0)


# ===========================================================================
# 9.6.3.4.3 -- Processo aproximado RN e RB (PDF p. 73)
# ===========================================================================
def test_96343_RN_e_RB_ponto_interior():
    # C40 granito: αp = 200000/35417,5 = 5,64693; φ = 2; σc,p0g = 10 MPa
    # RN: 18,1 + 5,64693/47·2^1,57·13 = 18,1 + 0,120147·2,96905·13 = 22,737 %
    # RB: 7,4 + 5,64693/18,7·2^1,07·13 = 7,4 + 0,301975·2,09940·13 = 15,642 %
    ap = EP / _eci_granito(40.0)
    rn = PT.perda_progressiva_aproximada_pct("RN", 2.0, 10.0, -0.16, 40.0)
    rb = PT.perda_progressiva_aproximada_pct("RB", 2.0, 10.0, -0.16, 40.0)
    assert rn == pytest.approx(18.1 + ap / 47.0 * 2.0 ** 1.57 * 13.0)
    assert rb == pytest.approx(7.4 + ap / 18.7 * 2.0 ** 1.07 * 13.0)
    assert rn == pytest.approx(22.737, abs=1e-3)
    assert rb == pytest.approx(15.642, abs=1e-3)


def test_96343_phi_nulo_da_termo_constante():
    # φ = 0 e εcs = 0 (referência 0): sobra a parcela constante 18,1 % e 7,4 %.
    assert PT.perda_progressiva_aproximada_pct("RN", 0.0, 10.0, 0.0, 40.0) == pytest.approx(18.1)
    assert PT.perda_progressiva_aproximada_pct("RB", 0.0, 10.0, 0.0, 40.0) == pytest.approx(7.4)


@pytest.mark.parametrize("eps_pmil", [-0.2, -0.12, 0.2, -0.16])
def test_96343_condicao_retracao_25_por_cento_passa(eps_pmil):
    # φ = 2: referência = 8·10^−5·2 = 0,16 ‰; faixa de ±25 %: 0,12 a 0,20 ‰
    PT.perda_progressiva_aproximada_pct("RB", 2.0, 10.0, eps_pmil, 40.0)


@pytest.mark.parametrize("eps_pmil", [-0.2001, -0.1199, -0.3])
def test_96343_condicao_retracao_25_por_cento_falha(eps_pmil):
    with pytest.raises(nbr.FaixaNormativaError):
        PT.perda_progressiva_aproximada_pct("RN", 2.0, 10.0, eps_pmil, 40.0)


def test_96343_aco_desconhecido():
    with pytest.raises(ValueError):
        PT.perda_progressiva_aproximada_pct("RX", 2.0, 10.0, -0.16, 40.0)


# ===========================================================================
# 9.6.3.4.5 -- Sem relaxação abaixo de 0,5·fptk (PDF p. 74)
# ===========================================================================
@pytest.mark.parametrize("tipo, relax", [
    ("cordoalha", "RN"), ("cordoalha", "RB"), ("fio", "RN"), ("fio", "RB"), ("barra", None),
])
def test_96345_abaixo_de_05_fptk_devolve_zero(tipo, relax):
    assert PT.psi_1000(tipo, relax, 0.49) == 0.0
    assert PT.psi_1000(tipo, relax, 0.0) == 0.0
    assert PT.psi_1000(tipo, relax, 0.5) == pytest.approx(0.0)   # σpi = 0,5·fptk exato


def test_96345_acima_de_05_continua_tabela_8_3():
    # Cordoalha RN: 0 em 0,5 e 3,5 em 0,6 -> 0,55 dá 1,75 (interpolação de 9.6.3.4.5)
    assert PT.psi_1000("cordoalha", "RN", 0.55) == pytest.approx(1.75)


@pytest.mark.parametrize("razao", [0.81, 1.0, -0.1])
def test_96345_fora_da_tabela_levanta(razao):
    with pytest.raises(ValueError):
        PT.psi_1000("cordoalha", "RN", razao)
