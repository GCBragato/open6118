"""Testes do P32 -- Protensão: ato da protensão e ELS de tensões
(NBR 6118:2026, 17.2.2 c, 17.2.4.3, 17.2.4.4, 17.3.2.1.3 e 17.3.4).

Valores esperados tirados das imagens das páginas do PDF (SCRATCH/nbr_png):
p140-141 (17.2.2 c), p143 (17.2.4.3.1-b), p144 (17.2.4.3.2 e 17.2.4.4),
p148 (17.3.2.1.3) e p150-151 (17.3.4). As contas à mão estão nos
comentários de cada teste.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import els_deformacao_nbr6118 as ELS8  # noqa: E402
import protendido_nbr6118 as PT  # noqa: E402


def _fctm(fck_mpa: float) -> float:
    """fct,m manual (8.2.5), independente do núcleo, só para montar o
    esperado dos testes deste arquivo."""
    if fck_mpa <= 50.0:
        return 0.3 * fck_mpa ** (2.0 / 3.0)
    return 2.12 * math.log(1.0 + 0.1 * (fck_mpa + 8.0))


# ===========================================================================
# 17.2.4.3.1-b -- Coeficientes de ponderação no ato da protensão (PDF p. 143)
# ===========================================================================
def test_17_2_4_3_1_b_tabela_coeficientes():
    assert PT.GAMAS_ATO_PROTENSAO == {
        "gama_c": 1.2,
        "gama_s": 1.15,
        "gama_p_pre_tracao": 1.0,
        "gama_p_pos_tracao": 1.1,
        "gama_f_desfavoravel": 1.0,
        "gama_f_favoravel": 0.9,
    }


@pytest.mark.parametrize("sistema, esperado", [
    ("pre_tracao", 1.0), ("pre", 1.0), ("PRÉ-TRAÇÃO", 1.0),
    ("pos_tracao", 1.1), ("pos", 1.1), ("pós-tração", 1.1),
])
def test_gama_p_ato_protensao(sistema, esperado):
    assert PT.gama_p_ato_protensao(sistema) == pytest.approx(esperado)


def test_gama_p_ato_protensao_invalido():
    with pytest.raises(ValueError):
        PT.gama_p_ato_protensao("misto")


# ===========================================================================
# 17.2.4.3.2-a -- Tensão máxima de compressão no ato (PDF p. 144)
# ===========================================================================
def test_tensao_max_compressao_ato_fck20():
    # fckj = 20 <= 50: limite = 0,7*20 = 14 MPa.
    assert PT.tensao_max_compressao_ato_kncm2(20.0) * 10.0 == pytest.approx(14.0)


def test_tensao_max_compressao_ato_continuidade_fck50():
    # Os dois ramos devem coincidir em fckj = 50: 0,7*50 = 35 MPa.
    ramo_baixo = 0.7 * 50.0
    ramo_alto = 0.7 * (1.0 - (50.0 - 50.0) / 200.0) * 50.0
    assert ramo_baixo == pytest.approx(ramo_alto)
    assert PT.tensao_max_compressao_ato_kncm2(50.0) * 10.0 == pytest.approx(35.0)


def test_tensao_max_compressao_ato_fck90():
    # fckj = 90: limite = 0,7*(1 - 40/200)*90 = 0,7*0,8*90 = 50,4 MPa.
    assert PT.tensao_max_compressao_ato_kncm2(90.0) * 10.0 == pytest.approx(50.4)


@pytest.mark.parametrize("fckj", [6.999, 90.001, 0.0, -5.0])
def test_tensao_max_compressao_ato_fora_da_faixa(fckj):
    with pytest.raises(nbr.FaixaNormativaError):
        PT.tensao_max_compressao_ato_kncm2(fckj)


# ===========================================================================
# 17.2.4.3.2-b -- Tensão máxima de tração no ato (PDF p. 144)
# ===========================================================================
def test_tensao_max_tracao_ato_fckj20():
    # sigma_ct,max = 1,2*fctm(20) = 1,2*0,3*20^(2/3).
    esperado = 1.2 * _fctm(20.0)
    assert PT.tensao_max_tracao_ato_kncm2(20.0) * 10.0 == pytest.approx(esperado)


def test_tensao_max_tracao_ato_fckj_acima_de_50():
    # fckj = 60 > 50: fctm = 2,12*ln(1 + 0,1*(60+8)).
    esperado = 1.2 * _fctm(60.0)
    assert PT.tensao_max_tracao_ato_kncm2(60.0) * 10.0 == pytest.approx(esperado)


def test_tensao_max_tracao_ato_fora_da_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        PT.tensao_max_tracao_ato_kncm2(6.9)


# ===========================================================================
# 17.2.4.3.2 -- verificar_ato_protensao (compressão, tração e armadura)
# ===========================================================================
def test_ato_protensao_secao_toda_comprimida_sem_tracao():
    # bw=20, h=50 -> Ac=1000, W=bh^2/6=8333,33. P=2000 kN, ep=0, M=0:
    # sigma = -P/Ac = -2 kN/cm2 = -20 MPa (compressao pura, sem tracao).
    r = PT.verificar_ato_protensao(
        bw_cm=20.0, h_cm=50.0, P_kn=2000.0, ep_cm=0.0, M_kncm=0.0,
        fckj_mpa=30.0)
    assert r.sigma_base_kncm2 == pytest.approx(-2.0)
    assert r.sigma_topo_kncm2 == pytest.approx(-2.0)
    assert r.Fs_tracao_kn == pytest.approx(0.0)
    assert r.delta_sigma_s_mpa is None
    assert r.ok_armadura_tracao is True
    assert r.sigma_compressao_max_kncm2 == pytest.approx(2.0)
    # limite (fckj=30) = 0,7*30 = 21 MPa = 2,1 kN/cm2 > 2,0 -> ok.
    assert r.ok_compressao is True
    assert r.ok is True


def test_ato_protensao_compressao_excede_limite():
    # Mesma seção, P bem maior -> sigma_c = -P/Ac excede 0,7*fckj.
    r = PT.verificar_ato_protensao(
        bw_cm=20.0, h_cm=50.0, P_kn=25000.0, ep_cm=0.0, M_kncm=0.0,
        fckj_mpa=30.0)
    # sigma_c = 25000/1000 = 25 kN/cm2 = 250 MPa >> 21 MPa.
    assert r.ok_compressao is False
    assert r.ok is False
    assert "17.2.4.3.2-a" in r.governante


def test_ato_protensao_com_tracao_e_armadura_ok():
    # bw=100,h=50: Ac=5000, Wb=Wt=41666,667. P=500 kN, ep=2 cm, M=6000 kN.cm:
    # sigma_b = -P/Ac - P*ep/Wb + M/Wb = -0,1 - 0,024 + 0,144 = 0,020 kN/cm2
    #         (tracao pequena na base -- dentro do limite b)
    # sigma_t = -P/Ac + P*ep/Wt - M/Wt = -0,1 + 0,024 - 0,144 = -0,220 kN/cm2
    r = PT.verificar_ato_protensao(
        bw_cm=100.0, h_cm=50.0, P_kn=500.0, ep_cm=2.0, M_kncm=6000.0,
        fckj_mpa=30.0, As_tracao_cm2=10.0)
    assert r.sigma_base_kncm2 == pytest.approx(0.02)
    assert r.sigma_topo_kncm2 == pytest.approx(-0.22)
    assert r.sigma_tracao_max_kncm2 == pytest.approx(0.02)
    # Fs = triangulo: y_tr = h*sb/(sb-st) = 50*0,02/(0,02+0,22) = 4,16667 cm
    y_tr = 50.0 * 0.02 / (0.02 - (-0.22))
    Fs_esperado = 100.0 * 0.5 * 0.02 * y_tr
    assert r.Fs_tracao_kn == pytest.approx(Fs_esperado)
    delta_esperado = Fs_esperado / 10.0 * 10.0  # kN/cm2 -> MPa
    assert r.delta_sigma_s_mpa == pytest.approx(delta_esperado)
    # limite b) = 1,2*fctm(30) = 3,48 MPa >> 0,2 MPa da tração -> ok.
    assert r.ok_tracao_concreto is True
    assert r.ok_armadura_tracao is True  # bem abaixo de 250 MPa
    assert r.ok is True


def test_ato_protensao_tracao_sem_As_informado_levanta_erro():
    with pytest.raises(ValueError):
        PT.verificar_ato_protensao(
            bw_cm=20.0, h_cm=50.0, P_kn=500.0, ep_cm=20.0, M_kncm=0.0,
            fckj_mpa=30.0)  # tem tracao (sigma_t=0,7) mas As nao informado


def test_ato_protensao_armadura_lisa_x_nervurada():
    # Mesmo caso do teste anterior, mas com As pequeno o bastante para que
    # Δσs fique entre 150 e 250 MPa: falha para 'lisa', passa para 'nervurada'.
    y_tr = 50.0 * 0.7 / (0.7 - (-1.7))
    Fs = 20.0 * 0.5 * 0.7 * y_tr
    As = Fs * 10.0 / 200.0  # Δσs = 200 MPa com este As
    r_nerv = PT.verificar_ato_protensao(
        bw_cm=20.0, h_cm=50.0, P_kn=500.0, ep_cm=20.0, M_kncm=0.0,
        fckj_mpa=30.0, As_tracao_cm2=As, tipo_barra="nervurada")
    r_lisa = PT.verificar_ato_protensao(
        bw_cm=20.0, h_cm=50.0, P_kn=500.0, ep_cm=20.0, M_kncm=0.0,
        fckj_mpa=30.0, As_tracao_cm2=As, tipo_barra="lisa")
    assert r_nerv.delta_sigma_s_mpa == pytest.approx(200.0)
    assert r_nerv.ok_armadura_tracao is True
    assert r_lisa.ok_armadura_tracao is False
    assert r_lisa.ok is False


def test_ato_protensao_tipo_barra_invalido():
    with pytest.raises(ValueError):
        PT.verificar_ato_protensao(
            bw_cm=20.0, h_cm=50.0, P_kn=2000.0, ep_cm=0.0, M_kncm=0.0,
            fckj_mpa=30.0, tipo_barra="chata")


# ===========================================================================
# 17.2.4.4.1 -- Limites de compressão em serviço (PDF p. 144)
# ===========================================================================
def test_17_2_4_4_1_c30_quase_permanente():
    # C30, quase permanente: 0,45*30 = 13,5 MPa.
    assert PT.limite_compressao_servico_mpa(30.0, "quase_permanente", "completa") \
        == pytest.approx(13.5)


def test_17_2_4_4_1_c30_frequente_e_rara():
    assert PT.limite_compressao_servico_mpa(30.0, "frequente", "completa") \
        == pytest.approx(18.0)
    assert PT.limite_compressao_servico_mpa(30.0, "rara", "completa") \
        == pytest.approx(18.0)


def test_17_2_4_4_1_limitada_aceita_quase_permanente_e_frequente():
    assert PT.limite_compressao_servico_mpa(30.0, "quase_permanente", "limitada") \
        == pytest.approx(13.5)
    assert PT.limite_compressao_servico_mpa(30.0, "frequente", "limitada") \
        == pytest.approx(18.0)


def test_17_2_4_4_1_rara_so_vale_para_completa():
    with pytest.raises(nbr.FaixaNormativaError):
        PT.limite_compressao_servico_mpa(30.0, "rara", "limitada")


def test_17_2_4_4_1_nivel_parcial_nao_tem_limite():
    with pytest.raises(nbr.FaixaNormativaError):
        PT.limite_compressao_servico_mpa(30.0, "quase_permanente", "parcial")


def test_17_2_4_4_1_combinacao_desconhecida():
    with pytest.raises(ValueError):
        PT.limite_compressao_servico_mpa(30.0, "excepcional", "completa")


# ===========================================================================
# 17.2.4.4.2 -- Limites de tração em serviço (PDF p. 144)
# ===========================================================================
def test_17_2_4_4_2_els_d_tensao_nula():
    assert PT.limite_tracao_servico_mpa(30.0, "ELS-D") == pytest.approx(0.0)
    assert PT.limite_tracao_servico_mpa(90.0, "els_d") == pytest.approx(0.0)


def test_17_2_4_4_2_els_f_retangular():
    # 0,7*alpha*fctm, alpha=1,5 (retangular).
    esperado = 0.7 * 1.5 * _fctm(30.0)
    assert PT.limite_tracao_servico_mpa(30.0, "ELS-F", "retangular") \
        == pytest.approx(esperado)
    # Mesma fórmula de fct_admissivel_traçao_kncm2 (sem divergência real).
    assert PT.limite_tracao_servico_mpa(30.0, "ELS-F", "retangular") == pytest.approx(
        PT.fct_admissivel_traçao_kncm2(30.0, "retangular") * 10.0)


def test_17_2_4_4_2_els_f_secao_T():
    esperado = 0.7 * 1.2 * _fctm(30.0)
    assert PT.limite_tracao_servico_mpa(30.0, "ELS-F", "T") == pytest.approx(esperado)


def test_17_2_4_4_2_estado_invalido():
    with pytest.raises(ValueError):
        PT.limite_tracao_servico_mpa(30.0, "ELS-X")


def test_limites_tensao_servico_dispatcher():
    r_c = PT.limites_tensao_servico(30.0, "quase_permanente", nivel="completa")
    assert r_c.tipo == "compressao"
    assert r_c.limite_mpa == pytest.approx(13.5)
    r_t = PT.limites_tensao_servico(30.0, "ELS-D")
    assert r_t.tipo == "tracao"
    assert r_t.limite_mpa == pytest.approx(0.0)


# ===========================================================================
# 17.3.4 -- Descompressão e formação de fissuras (PDF p. 150-151)
# ===========================================================================
def test_descompressao_sigma_zero_exato():
    # Ac=900, Wb=Wt=4500, ep=0, P=1125 kN -> M para sigma_base=0 exato:
    # sigma_b = -P/Ac + M/Wb = 0 -> M = P/Ac*Wb = 1125/900*4500 = 5625.
    r = PT.verificar_descompressao_fissuracao(
        P_kn=1125.0, ep_cm=0.0, M_kncm=5625.0,
        Ac_cm2=900.0, Wb_cm3=4500.0, Wt_cm3=4500.0, estado="ELS-D")
    assert r.sigma_tracao_max_kncm2 == pytest.approx(0.0, abs=1e-9)
    assert r.ok is True


def test_descompressao_els_d_falha_com_tracao():
    r = PT.verificar_descompressao_fissuracao(
        P_kn=1125.0, ep_cm=0.0, M_kncm=5626.0,
        Ac_cm2=900.0, Wb_cm3=4500.0, Wt_cm3=4500.0, estado="ELS-D")
    assert r.sigma_tracao_max_kncm2 > 0.0
    assert r.ok is False


def test_descompressao_els_f_usa_limite_de_tracao_servico():
    limite_mpa = PT.limite_tracao_servico_mpa(30.0, "ELS-F", "retangular")
    r_ok = PT.verificar_descompressao_fissuracao(
        P_kn=1125.0, ep_cm=0.0, M_kncm=5625.0 + 1.0,
        Ac_cm2=900.0, Wb_cm3=4500.0, Wt_cm3=4500.0,
        estado="ELS-F", fck_mpa=30.0)
    assert r_ok.limite_kncm2 * 10.0 == pytest.approx(limite_mpa)


def test_descompressao_els_f_sem_fck_levanta_erro():
    with pytest.raises(ValueError):
        PT.verificar_descompressao_fissuracao(
            P_kn=1125.0, ep_cm=0.0, M_kncm=5625.0,
            Ac_cm2=900.0, Wb_cm3=4500.0, Wt_cm3=4500.0, estado="ELS-F")


def test_descompressao_estado_invalido():
    with pytest.raises(ValueError):
        PT.verificar_descompressao_fissuracao(
            P_kn=1125.0, ep_cm=0.0, M_kncm=5625.0,
            Ac_cm2=900.0, Wb_cm3=4500.0, Wt_cm3=4500.0, estado="ELS-X")


# ===========================================================================
# 17.2.2 c) -- Δσp da armadura ativa não aderente (PDF p. 140-141)
# ===========================================================================
def test_rho_p_armadura_ativa():
    assert PT.rho_p_armadura_ativa(5.0, 100.0, 40.0) == pytest.approx(5.0 / 4000.0)


def test_rho_p_armadura_ativa_invalida():
    with pytest.raises(ValueError):
        PT.rho_p_armadura_ativa(5.0, 0.0, 40.0)


def test_delta_sigma_p_nao_aderente_vao_curto():
    # vao/dp = 30 <= 35: Dsp = 70 + 30/(100*0,01) = 70 + 30 = 100 MPa.
    assert PT.delta_sigma_p_nao_aderente(30.0, 0.01, 30.0) == pytest.approx(100.0)


def test_delta_sigma_p_nao_aderente_vao_longo():
    # vao/dp = 40 > 35: Dsp = 70 + 30/(300*0,01) = 70 + 10 = 80 MPa.
    assert PT.delta_sigma_p_nao_aderente(30.0, 0.01, 40.0) == pytest.approx(80.0)


def test_delta_sigma_p_nao_aderente_fronteira_35_usa_ramo_curto():
    # Exatamente 35 usa o primeiro ramo ("igual ou menor que 35").
    esperado_curto = 70.0 + 30.0 / (100.0 * 0.01)
    assert PT.delta_sigma_p_nao_aderente(30.0, 0.01, 35.0) == pytest.approx(esperado_curto)
    # Logo acima de 35 muda para o segundo ramo (denominador 300).
    esperado_longo = 70.0 + 30.0 / (300.0 * 0.01)
    assert PT.delta_sigma_p_nao_aderente(30.0, 0.01, 35.0001) == pytest.approx(
        esperado_longo, rel=1e-3)
    assert esperado_curto != pytest.approx(esperado_longo)


def test_delta_sigma_p_nao_aderente_saturacao_teto():
    # rho_p muito pequeno -> satura no teto de cada ramo.
    assert PT.delta_sigma_p_nao_aderente(50.0, 1e-4, 30.0) == pytest.approx(420.0)
    assert PT.delta_sigma_p_nao_aderente(50.0, 1e-4, 40.0) == pytest.approx(210.0)


def test_delta_sigma_p_nao_aderente_rho_grande_aproxima_70():
    # rho_p grande -> segunda parcela desprezível, Dsp ~= 70 MPa.
    valor = PT.delta_sigma_p_nao_aderente(30.0, 5.0, 30.0)
    assert valor == pytest.approx(70.0, abs=1.0)
    assert valor > 70.0


def test_delta_sigma_p_nao_aderente_rho_invalido():
    with pytest.raises(ValueError):
        PT.delta_sigma_p_nao_aderente(30.0, 0.0, 30.0)


def test_delta_sigma_p_nao_aderente_docstring_cita_divisao_por_ponderacao():
    # 17.2.2 c) (PDF p. 140): "...devendo ainda ser divididos pelos devidos
    # coeficientes de ponderação" -- a docstring precisa avisar que o
    # retorno é o valor característico, não o valor já dividido.
    doc = (PT.delta_sigma_p_nao_aderente.__doc__ or "")
    assert "coeficientes de ponderação" in doc
    assert "característico" in doc


def test_delta_sigma_p_nao_aderente_gama_s_divide_o_resultado():
    # Mesmo caso de test_delta_sigma_p_nao_aderente_vao_curto (Dsp = 100
    # MPa característico); com gama_s = 1,15, o valor de projeto é
    # 100 / 1,15 = 86,9565... MPa.
    caracteristico = PT.delta_sigma_p_nao_aderente(30.0, 0.01, 30.0)
    assert caracteristico == pytest.approx(100.0)
    dividido = PT.delta_sigma_p_nao_aderente(30.0, 0.01, 30.0, gama_s=1.15)
    assert dividido == pytest.approx(100.0 / 1.15)
    assert dividido < caracteristico


def test_delta_sigma_p_nao_aderente_gama_s_invalido():
    with pytest.raises(ValueError):
        PT.delta_sigma_p_nao_aderente(30.0, 0.01, 30.0, gama_s=0.0)


# ===========================================================================
# 17.3.2.1.3 -- Flecha em elementos com armaduras ativas (PDF p. 148)
# ===========================================================================
def test_momento_fissuracao_protendido():
    # Mr,sem_P=1000, P=500, ep=5, Ac=900, W=4500 -> W/Ac=5.
    # Mr,p = 1000 + 500*(5+5) = 1000 + 5000 = 6000 kN.cm.
    assert PT.momento_fissuracao_protendido_kncm(1000.0, 500.0, 5.0, 900.0, 4500.0) \
        == pytest.approx(6000.0)


def test_momento_fissuracao_protendido_geometria_invalida():
    with pytest.raises(ValueError):
        PT.momento_fissuracao_protendido_kncm(1000.0, 500.0, 5.0, 0.0, 4500.0)


def test_flecha_protendido_nao_fissurado():
    # Ma = Mr,p exatamente (6000) -> nao ultrapassa a formacao de fissuras
    # (a condicao e' "> Mr,p" para fissurar): (EI)eq = Ecs*Ic.
    r = PT.flecha_protendido(
        Ecs_kncm2=2500.0, Ic_cm4=67500.0, III_cm4=30000.0,
        Mr_sem_protensao_kncm=1000.0, Ma_kncm=6000.0,
        P_kn=500.0, ep_cm=5.0, Ac_cm2=900.0, W_cm3=4500.0)
    assert r.fissurado is False
    assert r.Mr_protendido_kncm == pytest.approx(6000.0)
    assert r.EI_eq_kncm2 == pytest.approx(2500.0 * 67500.0)


def test_flecha_protendido_fissurado_delega_p8():
    Mr_p = 6000.0
    Ma = 9000.0  # > Mr_p -> fissura
    r = PT.flecha_protendido(
        Ecs_kncm2=2500.0, Ic_cm4=67500.0, III_cm4=30000.0,
        Mr_sem_protensao_kncm=1000.0, Ma_kncm=Ma,
        P_kn=500.0, ep_cm=5.0, Ac_cm2=900.0, W_cm3=4500.0)
    esperado = ELS8.rigidez_equivalente_kncm2(2500.0, 67500.0, 30000.0, Mr_p, Ma, False)
    assert r.fissurado is True
    assert r.EI_eq_kncm2 == pytest.approx(esperado)


def test_flecha_protendido_docstring_nao_cita_alfa_f_para_flecha_diferida():
    # 17.3.2.1.3 (PDF p. 148) manda multiplicar a parcela permanente da
    # flecha imediata por (1 + phi) -- phi é o coeficiente de fluência de
    # 8.2.11, uma fórmula diferente do alfa_f de 17.3.2.1.2/13.3 Nota 5
    # (que depende de rho' e é pensada para armadura passiva). A docstring
    # não pode mais apontar para "(1 + alfa_f)" como se fosse a mesma coisa.
    doc = (PT.flecha_protendido.__doc__ or "")
    assert "flecha_total_protendido" in doc
    assert "(1 + phi)" in doc
    assert "1 + alfa_f" not in doc


def test_flecha_total_protendido_so_parcela_permanente():
    # phi = 2,0: f_total = 0 + 3,0*(1+2,0) = 9,0 cm.
    assert PT.flecha_total_protendido(3.0, 2.0) == pytest.approx(9.0)


def test_flecha_total_protendido_com_parcela_variavel():
    # f_imediata,variável = 1,0 cm (não entra no fator de fluência);
    # f_imediata,permanente = 3,0 cm; phi = 1,5.
    # f_total = 1,0 + 3,0*(1+1,5) = 1,0 + 7,5 = 8,5 cm.
    assert PT.flecha_total_protendido(3.0, 1.5, 1.0) == pytest.approx(8.5)


def test_flecha_total_protendido_phi_zero_nao_altera_flecha_imediata():
    assert PT.flecha_total_protendido(4.0, 0.0, 2.0) == pytest.approx(6.0)


def test_flecha_total_protendido_phi_negativo_levanta_erro():
    with pytest.raises(ValueError):
        PT.flecha_total_protendido(3.0, -0.1)
