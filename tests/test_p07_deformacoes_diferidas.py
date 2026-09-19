"""P7 — Deformações diferidas do concreto e da armadura (tempo_concreto_nbr6118.py).

Valores esperados tirados das imagens da NBR 6118:2026 (PDF p. 232, 234, 240,
241, 77 e 78, Anexo A e 11.3.3). Quando o esperado depende de conta, a conta
está no comentário do teste.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import tempo_concreto_nbr6118 as tc  # noqa: E402

Erro = nbr.FaixaNormativaError
Aviso = nbr.AvisoNBR6118


# ---------------------------------------------------------------------------
# A.2.1 (PDF p. 232) — εc(t0) = σc(t0) / Eci(t0)
# ---------------------------------------------------------------------------
def test_eps_c_imediata_divisao_direta():
    # sigma_c(t0) = -12 MPa; Eci(t0) = 24000 MPa -> -12/24000 = -0,0005 = -0,5 permil
    assert tc.eps_c_imediata_pmil(-12.0, 24000.0) == pytest.approx(-0.5)


def test_eps_c_imediata_bate_com_o_nucleo():
    # sigma_c(t0)/Eci(t0), com Eci(t0) tirado do próprio núcleo (8.2.8).
    fck = 30.0
    Eci_t0 = nbr.Eci_idade(fck, fckj_mpa=20.0)
    sigma = -10.0
    esperado = sigma / Eci_t0 * 1000.0
    assert tc.eps_c_imediata_pmil(sigma, Eci_t0) == pytest.approx(esperado)


def test_eps_c_imediata_Eci_nao_positivo_levanta():
    with pytest.raises(Erro):
        tc.eps_c_imediata_pmil(-10.0, 0.0)
    with pytest.raises(Erro):
        tc.eps_c_imediata_pmil(-10.0, -100.0)


# ---------------------------------------------------------------------------
# A.2.2.3 (PDF p. 234) — εcc(t,t0) = (σc/Eci)·φ(t,t0)
# ---------------------------------------------------------------------------
def test_eps_cc_phi_zero_da_zero():
    assert tc.eps_cc_pmil(-15.0, 26000.0, 0.0) == pytest.approx(0.0)


def test_eps_cc_cresce_linear_com_sigma_c_para_phi_fixo():
    # phi fixo: eps_cc proporcional a sigma_c.
    Eci = 26000.0
    phi = 2.0
    e1 = tc.eps_cc_pmil(-5.0, Eci, phi)
    e2 = tc.eps_cc_pmil(-10.0, Eci, phi)
    assert e2 == pytest.approx(2.0 * e1)
    # -10/26000*2*1000 = -0,769230...
    assert e2 == pytest.approx(-10.0 / 26000.0 * 2.0 * 1000.0)


def test_eps_cc_Eci_nao_positivo_levanta():
    with pytest.raises(Erro):
        tc.eps_cc_pmil(-10.0, 0.0, 1.0)


# ---------------------------------------------------------------------------
# A.2.5 (PDF p. 240) — escolha de α
# ---------------------------------------------------------------------------
def test_alfa_envelhecimento_caso_unico_e_geral():
    assert tc.alfa_envelhecimento("unico") == pytest.approx(0.5)
    assert tc.alfa_envelhecimento("geral") == pytest.approx(0.8)


def test_alfa_envelhecimento_caso_desconhecido():
    with pytest.raises(ValueError):
        tc.alfa_envelhecimento("nenhum-dos-dois")


# ---------------------------------------------------------------------------
# A.2.5 (PDF p. 240) — εc(t), forma prática simplificada
# ---------------------------------------------------------------------------
def test_eps_c_total_simplificada_com_delta_zero_reduz_a_A21_mais_A223():
    sigma_c_t0 = -12.0
    phi = 1.8
    eps_cs = -0.3
    Ec_t0 = 25000.0
    Eci = 30000.0
    total = tc.eps_c_total_simplificada_pmil(
        sigma_c_t0, 0.0, phi, eps_cs, Ec_t0, Eci, alfa=0.8
    )
    esperado = (
        tc.eps_c_imediata_pmil(sigma_c_t0, Ec_t0)
        + tc.eps_cc_pmil(sigma_c_t0, Eci, phi)
        + eps_cs
    )
    assert total == pytest.approx(esperado)


def test_eps_c_total_simplificada_alfa_padrao_e_08():
    sigma_c_t0 = -10.0
    delta = -2.0
    phi = 1.5
    eps_cs = -0.2
    Ec_t0 = 24000.0
    Eci = 28000.0
    com_default = tc.eps_c_total_simplificada_pmil(
        sigma_c_t0, delta, phi, eps_cs, Ec_t0, Eci
    )
    com_08 = tc.eps_c_total_simplificada_pmil(
        sigma_c_t0, delta, phi, eps_cs, Ec_t0, Eci, alfa=0.8
    )
    assert com_default == pytest.approx(com_08)


def test_eps_c_total_simplificada_conta_completa():
    # sigma_c(t0) = -8 MPa; delta_sigma_c = -1 MPa; phi = 2,0; eps_cs = -0,4 permil;
    # Ec(t0) = 20000 MPa; Eci = 32000 MPa; alfa = 0,5.
    # termo1 = -8*(1/20000 + 2,0/32000)*1000 = -8*(0,00005+0,0000625)*1000
    #        = -8*0,0001125*1000 = -0,9
    # termo_delta = -1*(1/20000 + 0,5*2,0/32000)*1000
    #             = -1*(0,00005+0,00003125)*1000 = -0,08125
    # total = -0,9 + (-0,4) + (-0,08125) = -1,38125
    total = tc.eps_c_total_simplificada_pmil(
        -8.0, -1.0, 2.0, -0.4, 20000.0, 32000.0, alfa=0.5
    )
    assert total == pytest.approx(-1.38125)


def test_eps_c_total_simplificada_Ec_ou_Eci_nao_positivo_levanta():
    with pytest.raises(Erro):
        tc.eps_c_total_simplificada_pmil(-8.0, -1.0, 1.0, 0.0, 0.0, 30000.0)
    with pytest.raises(Erro):
        tc.eps_c_total_simplificada_pmil(-8.0, -1.0, 1.0, 0.0, 20000.0, 0.0)


# ---------------------------------------------------------------------------
# 11.3.3.2 (PDF p. 78) — εc(t∞,t0), processo simplificado
# ---------------------------------------------------------------------------
def test_deformacao_total_fluencia_simplificada_phi_zero_reduz_a_elastica():
    sigma_c_t0 = -9.0
    Ec_t0 = 22000.0
    Ec_28 = 30000.0
    esperado = sigma_c_t0 / Ec_t0 * 1000.0
    assert tc.deformacao_total_fluencia_simplificada_pmil(
        sigma_c_t0, Ec_t0, Ec_28, 0.0
    ) == pytest.approx(esperado)


def test_deformacao_total_fluencia_simplificada_cresce_com_phi():
    sigma_c_t0 = -9.0
    Ec_t0 = 22000.0
    Ec_28 = 30000.0
    e_baixo = tc.deformacao_total_fluencia_simplificada_pmil(sigma_c_t0, Ec_t0, Ec_28, 1.0)
    e_alto = tc.deformacao_total_fluencia_simplificada_pmil(sigma_c_t0, Ec_t0, Ec_28, 3.0)
    # sigma_c(t0) < 0: mais fluência -> mais encurtamento -> mais negativo.
    assert e_alto < e_baixo


def test_deformacao_total_fluencia_simplificada_conta_completa():
    # sigma_c(t0) = -10 MPa; Ec(t0) = 25000; Ec(28) = 30000; phi = 2,4.
    # eps = -10*(1/25000 + 2,4/30000)*1000 = -10*(0,00004+0,00008)*1000 = -1,2
    v = tc.deformacao_total_fluencia_simplificada_pmil(-10.0, 25000.0, 30000.0, 2.4)
    assert v == pytest.approx(-1.2)


def test_deformacao_total_fluencia_simplificada_Ec_nao_positivo_levanta():
    with pytest.raises(Erro):
        tc.deformacao_total_fluencia_simplificada_pmil(-10.0, 0.0, 30000.0, 1.0)
    with pytest.raises(Erro):
        tc.deformacao_total_fluencia_simplificada_pmil(-10.0, 25000.0, 0.0, 1.0)


# ---------------------------------------------------------------------------
# 11.3.3.1 (PDF p. 77) — retração simplificada, valor único e faixa de validade
# ---------------------------------------------------------------------------
def test_retracao_simplificada_valor_fixo():
    assert tc.retracao_simplificada_pmil() == pytest.approx(-0.15)


def test_retracao_simplificada_caracteristico_inferior_e_nulo():
    assert tc.retracao_simplificada_pmil(caracteristico="inferior") == pytest.approx(0.0)


def test_retracao_simplificada_caracteristico_desconhecido():
    with pytest.raises(ValueError):
        tc.retracao_simplificada_pmil(caracteristico="media")


@pytest.mark.parametrize("dimensao_cm", [10.0, 55.0, 100.0])
def test_retracao_simplificada_dimensao_dentro_da_faixa_sem_aviso(dimensao_cm, recwarn):
    v = tc.retracao_simplificada_pmil(dimensao_cm=dimensao_cm, UR_pct=80.0)
    assert v == pytest.approx(-0.15)
    assert len(recwarn) == 0


@pytest.mark.parametrize("dimensao_cm", [9.9, 100.1, 5.0, 150.0])
def test_retracao_simplificada_dimensao_fora_da_faixa_avisa(dimensao_cm):
    with pytest.warns(Aviso):
        v = tc.retracao_simplificada_pmil(dimensao_cm=dimensao_cm, UR_pct=80.0)
    assert v == pytest.approx(-0.15)  # o valor não muda, só o aviso


def test_retracao_simplificada_UR_no_limite_75_sem_aviso(recwarn):
    v = tc.retracao_simplificada_pmil(dimensao_cm=50.0, UR_pct=75.0)
    assert v == pytest.approx(-0.15)
    assert len(recwarn) == 0


@pytest.mark.parametrize("UR_pct", [74.9, 50.0, 0.0])
def test_retracao_simplificada_UR_abaixo_de_75_avisa(UR_pct):
    with pytest.warns(Aviso):
        v = tc.retracao_simplificada_pmil(dimensao_cm=50.0, UR_pct=UR_pct)
    assert v == pytest.approx(-0.15)


def test_retracao_simplificada_sem_informar_dimensao_ou_UR_nao_avisa(recwarn):
    v = tc.retracao_simplificada_pmil()
    assert v == pytest.approx(-0.15)
    assert len(recwarn) == 0


# ---------------------------------------------------------------------------
# A.3.1 (PDF p. 241) — εs(t) da armadura, fluência/relaxação do aço
# ---------------------------------------------------------------------------
def test_eps_s_fluencia_chi_zero_reduz_a_hooke():
    # chi=0 -> eps_s(t) = sigma_s(t0)/Es (Hooke puro).
    sigma_s_t0 = 1200.0
    Es = 200000.0
    assert tc.eps_s_fluencia_pmil(sigma_s_t0, Es, 0.0) == pytest.approx(
        sigma_s_t0 / Es * 1000.0
    )


def test_eps_s_fluencia_conta_completa_sem_criterio_fptk():
    # sigma_s(t0) = 1000 MPa; Es = 200000 MPa; chi = 0,1.
    # eps_s = 1000/200000*(1+0,1)*1000 = 5*1,1 = 5,5 permil
    v = tc.eps_s_fluencia_pmil(1000.0, 200000.0, 0.1)
    assert v == pytest.approx(5.5)


def test_eps_s_fluencia_criterio_05_fptk_acima_considera_chi():
    # fptk = 1900 MPa; 0,5*fptk = 950; sigma_s(t0) = 1000 > 950 -> chi contado.
    v = tc.eps_s_fluencia_pmil(1000.0, 200000.0, 0.1, fptk_mpa=1900.0)
    assert v == pytest.approx(1000.0 / 200000.0 * 1.1 * 1000.0)


def test_eps_s_fluencia_criterio_05_fptk_abaixo_descarta_chi():
    # sigma_s(t0) = 900 <= 0,5*1900 = 950 -> chi descartado (eps_s vira Hooke puro).
    v = tc.eps_s_fluencia_pmil(900.0, 200000.0, 0.5, fptk_mpa=1900.0)
    assert v == pytest.approx(900.0 / 200000.0 * 1000.0)


def test_eps_s_fluencia_criterio_05_fptk_no_limite_exato_descarta_chi():
    # sigma_s(t0) = 950 = 0,5*1900 exatamente -> ">" estrito, não conta chi.
    v = tc.eps_s_fluencia_pmil(950.0, 200000.0, 0.5, fptk_mpa=1900.0)
    assert v == pytest.approx(950.0 / 200000.0 * 1000.0)


def test_eps_s_fluencia_Es_nao_positivo_levanta():
    with pytest.raises(Erro):
        tc.eps_s_fluencia_pmil(1000.0, 0.0, 0.1)


# ---------------------------------------------------------------------------
# A.3.2 (PDF p. 241) — εs(t) com fluência livre impedida
# ---------------------------------------------------------------------------
def test_eps_s_impedida_com_delta_zero_reduz_a_A31():
    sigma_s_t0 = 1100.0
    Es = 200000.0
    chi = 0.15
    assert tc.eps_s_impedida_pmil(sigma_s_t0, Es, chi, 0.0) == pytest.approx(
        tc.eps_s_fluencia_pmil(sigma_s_t0, Es, chi)
    )


def test_eps_s_impedida_conta_completa():
    # sigma_s(t0) = 1000; Es = 200000; chi = 0,2; delta_sigma_s = -50.
    # eps_s = 1000/200000 + 1000/200000*0,2 + (-50/200000)*(1+0,2)
    #       = 0,005 + 0,001 + (-0,00025*1,2) = 0,005+0,001-0,0003 = 0,0057
    #       = 5,7 permil
    v = tc.eps_s_impedida_pmil(1000.0, 200000.0, 0.2, -50.0)
    assert v == pytest.approx(5.7)


def test_eps_s_impedida_criterio_fptk_aplica_as_duas_parcelas_de_chi():
    # sigma_s(t0) = 900 <= 0,5*1900 -> chi descartado nas duas parcelas.
    v = tc.eps_s_impedida_pmil(900.0, 200000.0, 0.3, -40.0, fptk_mpa=1900.0)
    esperado = (900.0 + (-40.0)) / 200000.0 * 1000.0  # chi=0 -> 1+chi=1 nas duas parcelas
    assert v == pytest.approx(esperado)


def test_eps_s_impedida_Es_nao_positivo_levanta():
    with pytest.raises(Erro):
        tc.eps_s_impedida_pmil(1000.0, 0.0, 0.1, -10.0)
