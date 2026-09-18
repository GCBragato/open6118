"""Concreto protendido (protendido_bastos.py) contra a NBR 6118:2026 —
achados PRO-01 a PRO-08 (auditoria de 18/09/2026).

Os valores esperados saem das reproduções verificadas em
achados_brutos.md / verificacao_resultados.md (norma, execução e critério
concordam nos três), não das apostilas.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import protendido_bastos as PT  # noqa: E402


FCKS_VARREDURA = (20.0, 30.0, 40.0, 45.0, 50.0, 55.0, 70.0, 90.0)


# ---------------------------------------------------------------------------
# PRO-01 — fct,m / Eci / Ecs / fct_admissivel_tracao devem vir do núcleo
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fck", FCKS_VARREDURA)
def test_PRO01_fctm_delega_ao_nucleo(fck):
    assert PT.fctm_mpa(fck) == pytest.approx(nbr.fct_m(fck))


def test_PRO01_fctm_C70_valor_da_norma():
    # Achado: fctm(70) antes 5,0955 (sem ramo >50) x correto 4,6105 MPa.
    assert PT.fctm_mpa(70.0) == pytest.approx(4.6105, abs=0.001)
    assert PT.fctm_mpa(70.0) != pytest.approx(5.0955, abs=0.01)


@pytest.mark.parametrize("fck", FCKS_VARREDURA)
def test_PRO01_Eci_Ecs_delegam_ao_nucleo(fck):
    assert PT.Eci_mpa(fck) == pytest.approx(nbr.Eci(fck, nbr.alpha_E("granito")))
    assert PT.Ecs_mpa(fck) == pytest.approx(nbr.Ecs(fck, nbr.alpha_E("granito")))
    # agregado nao-default tambem delega (alpha_E por tipo, nao so 1.0)
    assert PT.Eci_mpa(fck, "basalto") == pytest.approx(nbr.Eci(fck, nbr.alpha_E("basalto")))


def test_PRO01_agregado_desconhecido_levanta():
    # Delegar ao nucleo troca o fallback silencioso (alpha=1.0) por erro
    # explicito (nbr.alpha_E valida a lista de agregados).
    with pytest.raises(ValueError):
        PT.Eci_mpa(30.0, "agregado-inexistente")


@pytest.mark.parametrize("fck", FCKS_VARREDURA)
def test_PRO01_fct_admissivel_usa_fctm_do_nucleo(fck):
    for secao, alpha in (("T", 1.2), ("I", 1.3), ("retangular", 1.5)):
        esperado = alpha * 0.7 * nbr.fct_m(fck) * 0.1
        assert PT.fct_admissivel_traçao_kncm2(fck, secao) == pytest.approx(esperado)


def test_PRO01_fct_admissivel_C70_nao_e_o_valor_antigo():
    # Com fct,m de 2014 (bug antigo), fct_R(70) sairia maior; o correto usa
    # fct,m do nucleo (Grupo II).
    correto = PT.fct_admissivel_traçao_kncm2(70.0, "retangular") * 10.0  # MPa
    assert correto == pytest.approx(4.841, abs=0.01)


# ---------------------------------------------------------------------------
# PRO-02 — Tabela 8.1 (fluência/retração) com eixos t0 e fck
# ---------------------------------------------------------------------------
def test_PRO02_grid_C20_C45_t0_30():
    # Tabela 8.1: t0=30, U=40%, h_fic=20cm, C20-C45 -> phi=3,4
    phi, eps = PT.phi_eps_cs_NBR(umidade_pct=40.0, h_fic_cm=20.0, to_dias=30.0,
                                 fck_mpa=30.0)
    assert phi == pytest.approx(3.4, abs=0.001)
    assert eps == pytest.approx(-0.44, abs=0.001)


def test_PRO02_grid_C50_C90_t0_30():
    # Mesmo ponto, mas C60 (bloco C50-C90) -> phi=2,0 (achado: +120% no bug antigo)
    phi, eps = PT.phi_eps_cs_NBR(umidade_pct=40.0, h_fic_cm=20.0, to_dias=30.0,
                                 fck_mpa=60.0)
    assert phi == pytest.approx(2.0, abs=0.001)


def test_PRO02_eps_cs_comum_as_duas_classes_U90_h60_t0_30():
    # Achado: phi_eps_cs_NBR(90, 60, 30) -> eps_cs correto = -0,15 permil
    _, eps_c20 = PT.phi_eps_cs_NBR(90.0, 60.0, 30.0, fck_mpa=30.0)
    _, eps_c70 = PT.phi_eps_cs_NBR(90.0, 60.0, 30.0, fck_mpa=70.0)
    assert eps_c20 == pytest.approx(-0.15, abs=0.001)
    assert eps_c20 == pytest.approx(eps_c70)  # eps_cs nao separa por classe


@pytest.mark.parametrize("fck, bloco", [(20.0, "C20-C45"), (45.0, "C20-C45"),
                                        (50.0, "C50-C90"), (90.0, "C50-C90")])
def test_PRO02_bloco_de_classe(fck, bloco):
    assert PT._bloco_classe_tabela_8_1(fck) == bloco


def test_PRO02_interpolacao_linear_em_t0():
    # phi(5)=4,6 e phi(30)=3,4 em U=40%,h=20cm,C20-C45 -> em t0=15,
    # interpolacao linear da 4,6 + (3,4-4,6)*(15-5)/(30-5) = 4,12
    phi, _ = PT.phi_eps_cs_NBR(40.0, 20.0, to_dias=15.0, fck_mpa=30.0)
    assert phi == pytest.approx(4.12, abs=0.001)


@pytest.mark.parametrize("to_dias", [1.0, 4.9, 60.1, 200.0])
def test_PRO02_to_dias_fora_da_faixa_levanta(to_dias):
    with pytest.raises(ValueError):
        PT.phi_eps_cs_NBR(75.0, 20.0, to_dias=to_dias)


@pytest.mark.parametrize("umidade,h_fic", [(10.0, 20.0), (95.0, 20.0),
                                           (75.0, 5.0), (75.0, 100.0)])
def test_PRO02_umidade_ou_hfic_fora_da_faixa_levanta(umidade, h_fic):
    with pytest.raises(ValueError):
        PT.phi_eps_cs_NBR(umidade, h_fic, to_dias=30.0)


# ---------------------------------------------------------------------------
# PRO-03 — alpha_p = Ep/Eci (não Ep/Ecs) nas perdas isoladas
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fck", FCKS_VARREDURA)
def test_PRO03_perda_encurtamento_elastico_usa_Eci(fck):
    esperado = (PT.E_P_MPA / nbr.Eci(fck, 1.0)) * 1.0
    assert PT.perda_encurtamento_elastico_kncm2(1.0, fck) == pytest.approx(esperado)


@pytest.mark.parametrize("fck", FCKS_VARREDURA)
def test_PRO03_perda_fluencia_usa_Eci(fck):
    esperado = (PT.E_P_MPA / nbr.Eci(fck, 1.0)) * 2.0 * 1.0
    assert PT.perda_fluencia_kncm2(2.0, 1.0, fck) == pytest.approx(esperado)


@pytest.mark.parametrize("fck", FCKS_VARREDURA)
def test_PRO03_perda_cabos_restantes_usa_Eci(fck):
    esperado = (PT.E_P_MPA / nbr.Eci(fck, 1.0)) * (3.0 / 8.0) * 1.0
    assert PT.perda_encurtamento_cabos_restantes_kncm2(4, 1.0, fck) == pytest.approx(esperado)


def test_PRO03_reproducao_achado_C50_alpha_p():
    # sigma_cp=1,0 kN/cm2 (10 MPa), C50: alpha_p correto ~5,051 (Eci) contra
    # o antigo ~5,460 (Ecs) -> perda antiga +8,1% maior (a favor da seguranca).
    correto = PT.perda_encurtamento_elastico_kncm2(1.0, 50.0)
    antigo_bug = (PT.E_P_MPA / nbr.Ecs(50.0, 1.0)) * 1.0
    assert correto == pytest.approx(5.0508, abs=0.001)
    assert antigo_bug == pytest.approx(5.4603, abs=0.001)
    assert (antigo_bug - correto) / correto * 100.0 == pytest.approx(8.1, abs=0.1)


def test_PRO03_reproducao_achado_C30_alpha_p():
    # C30: perda antiga +14,3% maior que a correta.
    correto = PT.perda_encurtamento_elastico_kncm2(1.0, 30.0)
    antigo_bug = (PT.E_P_MPA / nbr.Ecs(30.0, 1.0)) * 1.0
    assert (antigo_bug - correto) / correto * 100.0 == pytest.approx(14.3, abs=0.1)


# ---------------------------------------------------------------------------
# PRO-04 — Tabela 8.3 (psi_1000) por tipo/relaxação, com interpolação
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("tipo, relax, razao, esperado", [
    ("cordoalha", "RN", 0.5, 0.0), ("cordoalha", "RN", 0.6, 3.5),
    ("cordoalha", "RN", 0.7, 7.0), ("cordoalha", "RN", 0.8, 12.0),
    ("cordoalha", "RB", 0.8, 3.5),
    ("fio", "RN", 0.8, 8.5),
    ("fio", "RB", 0.8, 3.0),
    ("barra", "RN", 0.6, 1.5), ("barra", "RB", 0.7, 4.0), ("barra", None, 0.8, 7.0),
])
def test_PRO04_tabela_8_3_valores(tipo, relax, razao, esperado):
    assert PT.psi_1000(tipo, relax, razao) == pytest.approx(esperado)


def test_PRO04_interpolacao_linear_entre_linhas():
    # cordoalha RN: 3,5 em 0,6 e 7,0 em 0,7 -> 5,25 em 0,65
    assert PT.psi_1000("cordoalha", "RN", 0.65) == pytest.approx(5.25)


@pytest.mark.parametrize("razao", [0.49, 0.0, 0.81, 1.0])
def test_PRO04_fora_da_faixa_0_5_a_0_8_levanta(razao):
    with pytest.raises(ValueError):
        PT.psi_1000("cordoalha", "RN", razao)


def test_PRO04_PSI_1000_TIPICOS_atualizada():
    # CP-175 e fio; CP-190/CP-210 sao cordoalhas (Tabela 8.3 a 0,8 fptk).
    assert PT.PSI_1000_TIPICOS[("CP-175", "RN")] == pytest.approx(8.5)
    assert PT.PSI_1000_TIPICOS[("CP-175", "RB")] == pytest.approx(3.0)
    assert PT.PSI_1000_TIPICOS[("CP-190", "RN")] == pytest.approx(12.0)
    assert PT.PSI_1000_TIPICOS[("CP-190", "RB")] == pytest.approx(3.5)
    assert PT.PSI_1000_TIPICOS[("CP-210", "RN")] == pytest.approx(12.0)
    assert PT.PSI_1000_TIPICOS[("CP-210", "RB")] == pytest.approx(3.5)


def test_PRO04_reproducao_achado_CP190_RN():
    # psi_inf correto = 30,0% (antigo 21,25%); perda a 0,8 fptk = 456,0 MPa
    # (antigo 323,0 MPa), fptk=1900 MPa.
    psi_inf_correto = PT.psi_infinito(PT.psi_1000("cordoalha", "RN", 0.8))
    psi_1000_antigo_cp190_rn = 8.5  # valor pre-correcao (achado PRO-04)
    psi_inf_antigo = PT.psi_infinito(psi_1000_antigo_cp190_rn)
    assert psi_inf_correto == pytest.approx(30.0, abs=0.01)
    assert psi_inf_antigo == pytest.approx(21.25, abs=0.01)

    sigma_pi_kncm2 = 0.8 * 1900.0 * 0.1  # 0,8*fptk em kN/cm2
    perda_correta_mpa = PT.perda_relaxacao_kncm2(psi_inf_correto, sigma_pi_kncm2) * 10.0
    perda_antiga_mpa = PT.perda_relaxacao_kncm2(psi_inf_antigo, sigma_pi_kncm2) * 10.0
    assert perda_correta_mpa == pytest.approx(456.0, abs=0.5)
    assert perda_antiga_mpa == pytest.approx(323.0, abs=0.5)


# ---------------------------------------------------------------------------
# PRO-05 / PRO-06 — MRd protendido com lambda, alpha_c*etac*fcd e x/d-limite
# do núcleo (Grupo II)
# ---------------------------------------------------------------------------
def _MRd_ret(fck, alpha_c=None):
    return PT.MRd_secao_retangular_protendida(
        bw_cm=30.0, dp_cm=70.0, ds_cm=70.0, d_linha_cm=0.0,
        Ap_cm2=15.0, As_cm2=0.0, As_linha_cm2=0.0,
        fck_mpa=fck, sigma_pd_mpa=1400.0, alpha_c=alpha_c,
    )


def test_PRO05_reproducao_achado_C90():
    # bw=30, dp=70, Ap=15, fck=90, sigma_pd=1400 -> MRd correto ~124968 kN.cm
    # (antigo, com lambda/alpha_c/etac fixos: ~133549, +6,9%).
    r = _MRd_ret(90.0)
    assert r["MRd_kncm"] == pytest.approx(124968.0, rel=0.001)


def test_PRO05_reproducao_achado_C70():
    # fck=70 -> MRd correto ~123844 kN.cm (antigo +4,7%).
    r = _MRd_ret(70.0)
    assert r["MRd_kncm"] == pytest.approx(123844.0, rel=0.001)


@pytest.mark.parametrize("fck", FCKS_VARREDURA)
def test_PRO05_usa_lambda_e_tensao_do_nucleo(fck):
    r = _MRd_ret(fck)
    lam = nbr.lambda_retangulo(fck)
    tensao_kncm2 = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck, PT.GAMA_C))
    x_esperado = (140.0 * 15.0) / (tensao_kncm2 * lam * 30.0)
    assert r["x_cm"] == pytest.approx(x_esperado)
    assert r["x_d"] == pytest.approx(x_esperado / 70.0)


def test_PRO06_ductilidade_C70_nao_e_mais_ductil():
    # Achado: fck=70, x/d = 0,420 -> codigo antigo dizia "dutil" (limite 0,45
    # fixo); a norma exige 0,35 acima de C50, entao nao e ductil.
    r = _MRd_ret(70.0)
    assert r["x_d"] == pytest.approx(0.420, abs=0.001)
    assert r["ductil"] is False


@pytest.mark.parametrize("fck, ductil_esperado", [
    # x/d desce devagar com fck (fcd cresce), mas o limite cai de 0,45 para
    # 0,35 exatamente na fronteira C50/C55 (14.6.4.3) - por isso C50 fica
    # dutil e C55, com x/d ainda menor, nao fica.
    (40.0, False), (45.0, False), (50.0, True), (55.0, False),
    (70.0, False), (90.0, False),
])
def test_PRO06_ductilidade_usa_limite_do_nucleo(fck, ductil_esperado):
    r = _MRd_ret(fck)
    assert r["ductil"] == ductil_esperado
    assert r["ductil"] == (r["x_d"] <= nbr.xd_limite_dutilidade(fck))


def test_PRO06_C45_ja_sente_etac_mesmo_sendo_Grupo_I():
    # etac < 1 comeca em fck > 40 (nao 50): em C45 o x/d sobe o suficiente
    # para passar do limite de dutilidade de 0,45 (ainda do Grupo I).
    r = _MRd_ret(45.0)
    assert nbr.eta_c(45.0) < 1.0
    assert r["x_d"] > nbr.xd_limite_dutilidade(45.0)
    assert r["ductil"] is False


def test_PRO05_alpha_c_explicito_mantem_compatibilidade_mas_usa_etac_fcd_do_nucleo():
    # alpha_c=None (padrao) e alpha_c=0.85 explicito devem coincidir ate C50
    # (onde nbr.alpha_c(fck) tambem vale 0,85).
    r_none = _MRd_ret(40.0, alpha_c=None)
    r_085 = _MRd_ret(40.0, alpha_c=0.85)
    assert r_none["MRd_kncm"] == pytest.approx(r_085["MRd_kncm"])
    # Acima de C50, um alpha_c explicito ainda aplica etac(fck) do nucleo
    # (nao reintroduz o bug de etac=1 fixo).
    r_90_explicito = _MRd_ret(90.0, alpha_c=0.85)
    tensao_kncm2 = nbr.mpa_para_kncm2(0.85 * nbr.eta_c(90.0) * nbr.fcd(90.0, PT.GAMA_C))
    lam = nbr.lambda_retangulo(90.0)
    x_esperado = (140.0 * 15.0) / (tensao_kncm2 * lam * 30.0)
    assert r_90_explicito["x_cm"] == pytest.approx(x_esperado)


@pytest.mark.parametrize("fck", (30.0, 45.0, 50.0, 55.0, 70.0, 90.0))
def test_PRO05_secao_T_equilibrio_de_forcas_LN_nervura(fck):
    # Equilibrio Rcc,mesa + Rcc,nervura = Rpt deve valer com lambda e tensao
    # do nucleo em qualquer classe (nao so ate C50).
    r = PT.MRd_secao_T_protendida(
        bf_cm=120.0, bw_cm=20.0, hf_cm=5.0,
        dp_cm=80.0, ds_cm=80.0, d_linha_cm=0.0,
        Ap_cm2=15.0, As_cm2=0.0, As_linha_cm2=0.0,
        fck_mpa=fck, sigma_pd_mpa=1500.0,
    )
    assert r["secao"] == "T-LN-nervura"
    lam = nbr.lambda_retangulo(fck)
    tensao_kncm2 = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck, PT.GAMA_C))
    Rcc_mes = tensao_kncm2 * (120.0 - 20.0) * 5.0   # mesma tensão na mesa (PRO-09)
    Rcc_nerv = tensao_kncm2 * lam * r["x_cm"] * 20.0
    Rpt = 150.0 * 15.0
    assert Rcc_mes + Rcc_nerv == pytest.approx(Rpt, abs=0.5)
    assert r["ductil"] == (r["x_d"] <= nbr.xd_limite_dutilidade(fck))


# ---------------------------------------------------------------------------
# PRO-07 — perda progressiva simplificada (9.6.3.4.2), com interação
# ---------------------------------------------------------------------------
def test_PRO07_reproducao_achado():
    # fck=40, Ac=2000, Ic=800000, ep=30, Ap=15, eps_cs=-0,30 permil,
    # sigma_c,p0g=8 MPa, phi=2,2, cordoalha RB, sigma_p0=1300 MPa ->
    # correto ~201,7 MPa (soma das isoladas dava 284,2 MPa, +41%).
    psi_inf = PT.psi_infinito(PT.psi_1000("cordoalha", "RB", 0.8))
    delta = PT.perda_progressiva_simplificada(
        eps_cs_permil=-0.30, psi_percent=psi_inf, phi_inf=2.2,
        sigma_c_p0g_mpa=8.0, sigma_p0_mpa=1300.0,
        Ap_cm2=15.0, Ac_cm2=2000.0, Ic_cm4=800000.0, ep_cm=30.0,
        fck_mpa=40.0,
    )
    assert delta == pytest.approx(201.7, abs=0.2)


def test_PRO07_nao_e_a_soma_das_parcelas_isoladas():
    # A funcao combinada deve divergir da soma ingenua (que superestimava a
    # perda em ~41% no achado) - e o denominador de interacao deve ser > 1.
    psi_inf = PT.psi_infinito(PT.psi_1000("cordoalha", "RB", 0.8))
    combinado = PT.perda_progressiva_simplificada(
        eps_cs_permil=-0.30, psi_percent=psi_inf, phi_inf=2.2,
        sigma_c_p0g_mpa=8.0, sigma_p0_mpa=1300.0,
        Ap_cm2=15.0, Ac_cm2=2000.0, Ic_cm4=800000.0, ep_cm=30.0,
        fck_mpa=40.0,
    )
    soma_isolada = (
        PT.perda_retracao_kncm2(-0.30) * 10.0
        + PT.perda_fluencia_kncm2(2.2, 8.0 * 0.1, 40.0) * 10.0
        + PT.perda_relaxacao_kncm2(psi_inf, 1300.0 * 0.1) * 10.0
    )
    assert combinado < soma_isolada
    assert combinado / soma_isolada == pytest.approx(0.738, abs=0.01)


@pytest.mark.parametrize("fck", FCKS_VARREDURA)
def test_PRO07_alpha_p_usa_Eci(fck):
    # Denominador/numerador usam alpha_p = Ep/Eci; dobrar phi_inf tem que
    # mudar o resultado de forma consistente com alpha_p(fck) do nucleo.
    psi_inf = 8.75
    kwargs = dict(eps_cs_permil=-0.30, psi_percent=psi_inf,
                  sigma_c_p0g_mpa=8.0, sigma_p0_mpa=1300.0,
                  Ap_cm2=15.0, Ac_cm2=2000.0, Ic_cm4=800000.0, ep_cm=30.0,
                  fck_mpa=fck)
    alpha_p = PT.E_P_MPA / nbr.Eci(fck, 1.0)
    chi = -math.log(1.0 - psi_inf / 100.0)
    chi_c = 1.0 + 0.5 * 2.2
    chi_p = 1.0 + chi
    eta = 1.0 + 30.0 ** 2 * 2000.0 / 800000.0
    rho_p = 15.0 / 2000.0
    numerador = (0.30 / 1000.0) * PT.E_P_MPA + alpha_p * 8.0 * 2.2 + 1300.0 * chi
    denominador = chi_p + chi_c * alpha_p * eta * rho_p
    esperado = numerador / denominador
    assert PT.perda_progressiva_simplificada(phi_inf=2.2, **kwargs) == pytest.approx(esperado)


# ---------------------------------------------------------------------------
# PRO-08 — fuso_limite_excentricidade: sinais das 4 equações
# ---------------------------------------------------------------------------
def test_PRO08_reproducao_achado_e_realimentacao_em_sigma_base_topo():
    Po, Mo, Mtot, R = 800.0, 4000.0, 9000.0, 0.85
    Ac, Wb, Wt = 1800.0, 18000.0, 18000.0
    sigma_tr_o, sigma_c_o = 0.10, -1.6
    sigma_tr_tot, sigma_c_tot = 0.12, -1.5

    fuso = PT.fuso_limite_excentricidade(
        Po_kn=Po, Mo_kncm=Mo, Mtot_kncm=Mtot,
        Ac_cm2=Ac, Wb_cm3=Wb, Wt_cm3=Wt, R=R,
        sigma_tr_o_kncm2=sigma_tr_o, sigma_c_o_kncm2=sigma_c_o,
        sigma_tr_tot_kncm2=sigma_tr_tot, sigma_c_tot_kncm2=sigma_c_tot,
    )
    # Valores esperados (achado PRO-08, re-derivados independentemente):
    assert fuso["ep_77_top_o"] == pytest.approx(17.25, abs=0.005)
    assert fuso["ep_78_base_o"] == pytest.approx(31.00, abs=0.005)
    assert fuso["ep_79_top_tot"] == pytest.approx(-16.47, abs=0.005)
    assert fuso["ep_80_base_tot"] == pytest.approx(0.059, abs=0.005)

    # Realimenta cada ep em sigma_base_topo: tem que reproduzir a tensao-alvo.
    _, st_o = PT.sigma_base_topo(Po, fuso["ep_77_top_o"], Mo, Ac, Wb, Wt)
    sb_o, _ = PT.sigma_base_topo(Po, fuso["ep_78_base_o"], Mo, Ac, Wb, Wt)
    _, st_tot = PT.sigma_base_topo(R * Po, fuso["ep_79_top_tot"], Mtot, Ac, Wb, Wt)
    sb_tot, _ = PT.sigma_base_topo(R * Po, fuso["ep_80_base_tot"], Mtot, Ac, Wb, Wt)
    assert st_o == pytest.approx(sigma_tr_o, abs=1e-6)
    assert sb_o == pytest.approx(sigma_c_o, abs=1e-6)
    assert st_tot == pytest.approx(sigma_c_tot, abs=1e-6)
    assert sb_tot == pytest.approx(sigma_tr_tot, abs=1e-6)


@pytest.mark.parametrize("seed", [
    dict(Po_kn=500.0, Mo_kncm=2000.0, Mtot_kncm=6000.0, Ac_cm2=1200.0,
         Wb_cm3=9000.0, Wt_cm3=9000.0, R=0.80, sigma_tr_o_kncm2=0.15,
         sigma_c_o_kncm2=-1.2, sigma_tr_tot_kncm2=0.10, sigma_c_tot_kncm2=-1.1),
    dict(Po_kn=1200.0, Mo_kncm=3000.0, Mtot_kncm=15000.0, Ac_cm2=2500.0,
         Wb_cm3=25000.0, Wt_cm3=30000.0, R=0.90, sigma_tr_o_kncm2=0.05,
         sigma_c_o_kncm2=-2.0, sigma_tr_tot_kncm2=0.18, sigma_c_tot_kncm2=-1.8),
])
def test_PRO08_generico_realimenta_para_qualquer_secao(seed):
    # Generaliza o round-trip para outra geometria e outras tensoes
    # admissiveis (inclusive Wb != Wt), garantindo que a re-derivacao nao
    # foi ajustada so para o caso do achado.
    fuso = PT.fuso_limite_excentricidade(**seed)
    Po, Mo, Mtot, R = seed["Po_kn"], seed["Mo_kncm"], seed["Mtot_kncm"], seed["R"]
    Ac, Wb, Wt = seed["Ac_cm2"], seed["Wb_cm3"], seed["Wt_cm3"]

    _, st_o = PT.sigma_base_topo(Po, fuso["ep_77_top_o"], Mo, Ac, Wb, Wt)
    sb_o, _ = PT.sigma_base_topo(Po, fuso["ep_78_base_o"], Mo, Ac, Wb, Wt)
    _, st_tot = PT.sigma_base_topo(R * Po, fuso["ep_79_top_tot"], Mtot, Ac, Wb, Wt)
    sb_tot, _ = PT.sigma_base_topo(R * Po, fuso["ep_80_base_tot"], Mtot, Ac, Wb, Wt)
    assert st_o == pytest.approx(seed["sigma_tr_o_kncm2"], abs=1e-6)
    assert sb_o == pytest.approx(seed["sigma_c_o_kncm2"], abs=1e-6)
    assert st_tot == pytest.approx(seed["sigma_c_tot_kncm2"], abs=1e-6)
    assert sb_tot == pytest.approx(seed["sigma_tr_tot_kncm2"], abs=1e-6)


# ---------------------------------------------------------------------------
# PRO-09 (consolidação) — mesa da seção T com a mesma tensão da nervura
# ---------------------------------------------------------------------------
def test_PRO09_secao_T_mesa_com_tensao_do_bloco_sem_085_extra():
    # 17.2.2 e): com a mesa comprimida a largura não diminui em direção à borda
    # comprimida -> tensão αc·ηc·fcd em toda a zona comprimida (mesa e nervura).
    # C30, bf=120, bw=20, hf=5, dp=80, Ap=15, σpd=1500 MPa (cálculo à mão):
    sigma = 0.85 * 30.0 / 1.4 / 10.0          # kN/cm²
    Rpt = 150.0 * 15.0
    Rmesa = sigma * (120.0 - 20.0) * 5.0
    x = (Rpt - Rmesa) / (sigma * 0.8 * 20.0)
    MRd = Rmesa * (0.4 * x - 2.5) + Rpt * (80.0 - 0.4 * x)
    r = PT.MRd_secao_T_protendida(
        bf_cm=120.0, bw_cm=20.0, hf_cm=5.0, dp_cm=80.0, ds_cm=80.0, d_linha_cm=0.0,
        Ap_cm2=15.0, As_cm2=0.0, As_linha_cm2=0.0, fck_mpa=30.0, sigma_pd_mpa=1500.0,
    )
    assert r["x_cm"] == pytest.approx(x, rel=1e-9)            # 45,96 cm
    assert r["MRd_kncm"] == pytest.approx(MRd, rel=1e-9)      # ≈ 153 100 kN·cm
    assert r["MRd_kncm"] == pytest.approx(153103.0, abs=5.0)


# ---------------------------------------------------------------------------
# 9.6.3.4.2: alpha_p(t) = Ep/Eci(t0) no numerador quando t0 < 28 dias
# (achado da verificação das correções; PDF p. 71-72)
# ---------------------------------------------------------------------------
_DADOS_PRO07 = dict(eps_cs_permil=-0.30, psi_percent=None, phi_inf=2.2,
                    sigma_c_p0g_mpa=8.0, sigma_p0_mpa=1300.0, Ap_cm2=15.0,
                    Ac_cm2=2000.0, Ic_cm4=800000.0, ep_cm=30.0, fck_mpa=40.0)


def _dados_pro07():
    d = dict(_DADOS_PRO07)
    d["psi_percent"] = PT.psi_infinito(PT.psi_1000("cordoalha", "RB", 1300.0 / 1900.0))
    return d


def test_alpha_p_t_igual_a_alpha_p_a_partir_de_28_dias():
    d = _dados_pro07()
    assert PT.perda_progressiva_simplificada(**d, t0_dias=28.0) == pytest.approx(
        PT.perda_progressiva_simplificada(**d))
    assert PT.perda_progressiva_simplificada(**d, t0_dias=90.0) == pytest.approx(
        PT.perda_progressiva_simplificada(**d))


def test_alpha_p_t_aos_7_dias_usa_Eci_t0():
    d = _dados_pro07()
    Ep = PT.E_P_MPA
    Eci28 = 5600.0 * math.sqrt(40.0)
    fckj = math.exp(0.25 * (1.0 - math.sqrt(28.0 / 7.0))) * 40.0       # CP II
    Eci7 = (fckj / 40.0) ** 0.5 * Eci28
    chi = -math.log(1.0 - d["psi_percent"] / 100.0)
    num = 0.30 / 1000.0 * Ep + (Ep / Eci7) * 8.0 * 2.2 + 1300.0 * chi
    den = (1.0 + chi) + (1.0 + 0.5 * 2.2) * (Ep / Eci28) * (1.0 + 30.0 ** 2 * 2000.0 / 800000.0) * (15.0 / 2000.0)
    assert PT.perda_progressiva_simplificada(**d, t0_dias=7.0, cimento="CPII") == pytest.approx(num / den)
    assert num / den > PT.perda_progressiva_simplificada(**d)   # concreto jovem: perda maior


def test_alpha_p_t_abaixo_de_7_dias_exige_Eci_de_ensaio():
    d = _dados_pro07()
    with pytest.raises(nbr.FaixaNormativaError):
        PT.perda_progressiva_simplificada(**d, t0_dias=3.0)
    v = PT.perda_progressiva_simplificada(**d, t0_dias=3.0, Eci_t0_mpa=25000.0)
    assert v > PT.perda_progressiva_simplificada(**d)
