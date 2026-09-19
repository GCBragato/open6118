"""Testes do P26 — estabilidade global e imperfeições globais (NBR 6118:2026).

Itens cobertos: 15.4.2 (classificação nós fixos/móveis), 15.5.1 (majoração do
Ecs), 15.5.2 (parâmetro alfa, alfa1, rigidez do pilar equivalente), 15.5.3
(gama_z), 15.7.2 (processo aproximado 0,95*gama_z), 15.7.3 (rigidezes
aproximadas), 11.3.3.4.1 (desaprumo global e combinação vento/desaprumo).

Casos-limite citados no pacote: gama_z = 1,1 exato; alfa1 nos dois tipos de
contraventamento (pórticos puros e pilar-parede exclusivo); os três casos de
vento contra desaprumo na fronteira de 30%. As contas de apoio (quando não
são só a fórmula da norma com números redondos) estão nos comentários.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import estabilidade_global_nbr6118 as eg  # noqa: E402
import nucleo_nbr6118 as nbr  # noqa: E402


# --- 15.5.1 — majoração do Ecs (PDF p. 124) ---------------------------------
def test_ecs_estabilidade_majora_10_por_cento():
    fck = 30.0
    ecs_padrao = nbr.Ecs(fck)
    ecs_majorado = eg.Ecs_estabilidade_mpa(fck)
    assert ecs_majorado == pytest.approx(1.10 * ecs_padrao)


def test_ecs_estabilidade_sem_majorar_reproduz_ecs_padrao():
    fck = 25.0
    assert eg.Ecs_estabilidade_mpa(fck, majorar=False) == pytest.approx(nbr.Ecs(fck))


# --- 15.5.2 — parâmetro de instabilidade alfa (PDF p. 124-125) --------------
def test_parametro_alfa_formula():
    # Nk/EcsIc = 50000/31250000 = 0,0016 = 0,04^2 -> sqrt = 0,04
    # alfa = 30 * 0,04 = 1,2
    a = eg.parametro_alfa(Htot_m=30.0, Nk_kn=50000.0, EcsIc_knm2=31250000.0)
    assert a == pytest.approx(1.2)


def test_parametro_alfa_exige_grandezas_positivas():
    with pytest.raises(ValueError):
        eg.parametro_alfa(Htot_m=0.0, Nk_kn=50000.0, EcsIc_knm2=31250000.0)
    with pytest.raises(ValueError):
        eg.parametro_alfa(Htot_m=30.0, Nk_kn=-1.0, EcsIc_knm2=31250000.0)
    with pytest.raises(ValueError):
        eg.parametro_alfa(Htot_m=30.0, Nk_kn=50000.0, EcsIc_knm2=0.0)


# --- 15.5.2 — alfa1 (PDF p. 124-125) ----------------------------------------
def test_alfa1_tabela_n_ate_3():
    assert eg.alfa1(1) == pytest.approx(0.3)
    assert eg.alfa1(2) == pytest.approx(0.4)
    assert eg.alfa1(3) == pytest.approx(0.5)


def test_alfa1_usual_n_maior_igual_4():
    assert eg.alfa1(4) == pytest.approx(0.6)
    assert eg.alfa1(20) == pytest.approx(0.6)


def test_alfa1_contraventamento_pilar_parede_exclusivo():
    assert eg.alfa1(10, contraventamento="pilar_parede") == pytest.approx(0.7)
    assert eg.alfa1(10, contraventamento="parede") == pytest.approx(0.7)


def test_alfa1_contraventamento_so_porticos():
    assert eg.alfa1(10, contraventamento="porticos") == pytest.approx(0.5)


def test_alfa1_n_invalido_levanta():
    with pytest.raises(ValueError):
        eg.alfa1(0)


def test_alfa1_contraventamento_desconhecido_levanta():
    with pytest.raises(ValueError):
        eg.alfa1(10, contraventamento="treliça-mista-desconhecida")


# --- 15.5.2 — rigidez do pilar equivalente (PDF p. 125) ---------------------
def test_rigidez_pilar_equivalente_caso_trivial_pilar_isolado():
    # Pilar unico de EI0 = 1000 kN.m2, H=3m, F=10kN:
    # delta = F*H^3/(3*EI0) = 10*27/3000 = 0,09 m
    # a rigidez equivalente recuperada deve ser o proprio EI0 (sem porticos
    # associados, o pilar equivalente do pilar isolado e ele mesmo).
    EI0 = 1000.0
    delta = 10.0 * 3.0 ** 3 / (3.0 * EI0)
    assert delta == pytest.approx(0.09)
    EI_equiv = eg.rigidez_pilar_equivalente(Htot_m=3.0, F_kn=10.0, delta_topo_m=delta)
    assert EI_equiv == pytest.approx(EI0)


def test_rigidez_pilar_equivalente_segundo_caso():
    # H=6m, F=20kN, EI0=5000 kN.m2 -> delta = 20*216/(3*5000) = 4320/15000 = 0,288 m
    EI0 = 5000.0
    delta = 20.0 * 6.0 ** 3 / (3.0 * EI0)
    assert delta == pytest.approx(0.288)
    EI_equiv = eg.rigidez_pilar_equivalente(Htot_m=6.0, F_kn=20.0, delta_topo_m=delta)
    assert EI_equiv == pytest.approx(EI0)


def test_rigidez_pilar_equivalente_exige_grandezas_positivas():
    with pytest.raises(ValueError):
        eg.rigidez_pilar_equivalente(Htot_m=0.0, F_kn=10.0, delta_topo_m=0.09)
    with pytest.raises(ValueError):
        eg.rigidez_pilar_equivalente(Htot_m=3.0, F_kn=10.0, delta_topo_m=0.0)


# --- 15.5.3 — coeficiente gama_z (PDF p. 125) -------------------------------
def test_gama_z_fronteira_1_1():
    # M1=1100, dM=100 -> dM/M1 = 1/11; gama_z = 1/(10/11) = 1,1 exato
    gz = eg.gama_z(M1tot_d_knm=1100.0, delta_Mtot_d_knm=100.0)
    assert gz == pytest.approx(1.1)


def test_gama_z_delta_zero_da_1_0():
    gz = eg.gama_z(M1tot_d_knm=1000.0, delta_Mtot_d_knm=0.0)
    assert gz == pytest.approx(1.0)


def test_gama_z_ponto_interior():
    gz = eg.gama_z(M1tot_d_knm=1000.0, delta_Mtot_d_knm=200.0)
    assert gz == pytest.approx(1.25)


def test_gama_z_m1_nao_positivo_levanta():
    with pytest.raises(ValueError):
        eg.gama_z(M1tot_d_knm=0.0, delta_Mtot_d_knm=10.0)
    with pytest.raises(ValueError):
        eg.gama_z(M1tot_d_knm=-100.0, delta_Mtot_d_knm=10.0)


# --- 15.4.2 — classificação de nós (PDF p. 123) -----------------------------
def test_classificar_nos_por_alfa_fixos_e_moveis():
    r_fixos = eg.classificar_nos(alfa=0.5, alfa1_valor=0.6)
    assert r_fixos.nos_fixos is True

    r_moveis = eg.classificar_nos(alfa=0.7, alfa1_valor=0.6)
    assert r_moveis.nos_fixos is False


def test_classificar_nos_por_alfa_caso_limite_igual_cai_em_nos_moveis():
    # 15.5.2 (PDF p. 124): "menor que o valor alfa1" -> desigualdade
    # estrita; alfa == alfa1 nao satisfaz o criterio, logo nos moveis.
    r = eg.classificar_nos(alfa=0.6, alfa1_valor=0.6)
    assert r.nos_fixos is False


def test_classificar_nos_por_alfa_abaixo_do_limite_e_nos_fixos():
    r = eg.classificar_nos(alfa=0.599, alfa1_valor=0.6)
    assert r.nos_fixos is True


def test_classificar_nos_por_gama_z_fronteira_1_1_e_nos_fixos():
    r = eg.classificar_nos(gama_z=1.1)
    assert r.nos_fixos is True


def test_classificar_nos_por_gama_z_acima_de_1_1_e_nos_moveis():
    r = eg.classificar_nos(gama_z=1.11)
    assert r.nos_fixos is False


def test_classificar_nos_dois_criterios_concordando():
    r = eg.classificar_nos(alfa=0.5, alfa1_valor=0.6, gama_z=1.05)
    assert r.nos_fixos is True


def test_classificar_nos_dois_criterios_discordando_prevalece_nos_moveis():
    # alfa indica nos fixos, gama_z indica nos moveis -> a favor da seguranca
    r = eg.classificar_nos(alfa=0.5, alfa1_valor=0.6, gama_z=1.5)
    assert r.nos_fixos is False
    assert any("discordam" in linha for linha in r.memoria)


def test_classificar_nos_sem_nenhum_criterio_levanta():
    with pytest.raises(ValueError):
        eg.classificar_nos()


def test_classificar_nos_alfa_sem_alfa1_levanta():
    with pytest.raises(ValueError):
        eg.classificar_nos(alfa=0.5)


# --- 15.7.2 — processo aproximado 0,95*gama_z (PDF p. 126) ------------------
def test_majoracao_horizontal_no_limite_1_3_e_aceito():
    fator = eg.majoracao_horizontal(1.3)
    assert fator == pytest.approx(0.95 * 1.3)
    assert fator == pytest.approx(1.235)


def test_majoracao_horizontal_ponto_interior():
    assert eg.majoracao_horizontal(1.0) == pytest.approx(0.95)


def test_majoracao_horizontal_acima_do_limite_levanta():
    with pytest.raises(eg.FaixaNormativaError):
        eg.majoracao_horizontal(1.31)


# --- 15.7.3 — rigidezes aproximadas (PDF p. 126-127) ------------------------
def test_rigidezes_aproximadas_laje():
    # Ec=10000 MPa = 1000 kN/cm2; Ic=1000 cm4 -> 0,3*1000*1000 = 300000
    ei = eg.rigidezes_aproximadas("laje", Ec_mpa=10000.0, Ic_cm4=1000.0)
    assert ei == pytest.approx(300000.0)


def test_rigidezes_aproximadas_viga_as_diferente():
    ei = eg.rigidezes_aproximadas("viga", Ec_mpa=10000.0, Ic_cm4=1000.0, As_igual=False)
    assert ei == pytest.approx(400000.0)


def test_rigidezes_aproximadas_viga_as_igual():
    ei = eg.rigidezes_aproximadas("viga", Ec_mpa=10000.0, Ic_cm4=1000.0, As_igual=True)
    assert ei == pytest.approx(500000.0)


def test_rigidezes_aproximadas_pilar():
    ei = eg.rigidezes_aproximadas("pilar", Ec_mpa=10000.0, Ic_cm4=1000.0)
    assert ei == pytest.approx(800000.0)


def test_rigidezes_aproximadas_viga_sem_as_igual_levanta():
    with pytest.raises(ValueError):
        eg.rigidezes_aproximadas("viga", Ec_mpa=10000.0, Ic_cm4=1000.0)


def test_rigidezes_aproximadas_elemento_desconhecido_levanta():
    with pytest.raises(ValueError):
        eg.rigidezes_aproximadas("fundacao", Ec_mpa=10000.0, Ic_cm4=1000.0)


# --- 11.3.3.4.1 — desaprumo global (PDF p. 79) ------------------------------
def test_desaprumo_theta1_ponto_interior_sem_clamp():
    # H = 6,25 -> theta1 = 1/(100*sqrt(6,25)) = 1/(100*2,5) = 1/250 = 0,004
    # (dentro de [1/300, 1/200], sem entrar no clamp)
    r = eg.desaprumo_global(H_m=6.25, n_pilares=1)
    assert r.theta1 == pytest.approx(0.004)


def test_desaprumo_theta1_fronteira_theta1_max_H_igual_4():
    # H = 4 -> theta1 = 1/(100*sqrt(4)) = 1/200 = 0,005 (fronteira do maximo)
    r = eg.desaprumo_global(H_m=4.0, n_pilares=1)
    assert r.theta1 == pytest.approx(1.0 / 200.0)


def test_desaprumo_theta1_fronteira_theta1_min_H_igual_9():
    # H = 9 -> theta1 = 1/(100*sqrt(9)) = 1/300 (fronteira do minimo)
    r = eg.desaprumo_global(H_m=9.0, n_pilares=1)
    assert r.theta1 == pytest.approx(1.0 / 300.0)


def test_desaprumo_theta1_clampado_no_maximo_predio_baixo():
    # H = 1 -> theta1_bruto = 1/(100*1) = 0,01 > 1/200 -> clamp em 1/200
    r = eg.desaprumo_global(H_m=1.0, n_pilares=1)
    assert r.theta1 == pytest.approx(1.0 / 200.0)


def test_desaprumo_theta1_clampado_no_minimo_predio_alto():
    # H = 100 -> theta1_bruto = 1/(100*10) = 0,001 < 1/300 -> clamp em 1/300
    r = eg.desaprumo_global(H_m=100.0, n_pilares=1)
    assert r.theta1 == pytest.approx(1.0 / 300.0)


def test_desaprumo_theta_a_com_n_igual_1_reproduz_theta1():
    # n=1 -> sqrt((1+1)/2) = sqrt(1) = 1 -> theta_a = theta1
    r = eg.desaprumo_global(H_m=6.25, n_pilares=1)
    assert r.theta_a == pytest.approx(r.theta1)


def test_desaprumo_theta_a_geral_n_maior_que_1():
    # H=9 -> theta1=1/300; n=10 -> fator = sqrt((1+0,1)/2) = sqrt(0,55) = 0,74161985
    r = eg.desaprumo_global(H_m=9.0, n_pilares=10)
    assert r.theta1 == pytest.approx(1.0 / 300.0)
    assert r.theta_a == pytest.approx((1.0 / 300.0) * math.sqrt(1.1 / 2.0))


def test_desaprumo_lajes_lisas_theta_a_igual_theta1_mesmo_com_n_grande():
    r = eg.desaprumo_global(H_m=9.0, n_pilares=10, lajes_lisas_ou_cogumelo=True)
    assert r.theta_a == pytest.approx(r.theta1)
    assert r.caso == "lajes_lisas_ou_cogumelo"


def test_desaprumo_pilar_isolado_em_balanco_fixa_theta1_em_1_200():
    # Mesmo com H muito grande (que sozinho daria theta1 bem menor), o pilar
    # isolado em balanco fixa theta1 = 1/200.
    r = eg.desaprumo_global(H_m=100.0, n_pilares=1, pilar_isolado_em_balanco=True)
    assert r.theta1 == pytest.approx(1.0 / 200.0)
    assert r.theta_a == pytest.approx(1.0 / 200.0)
    assert r.caso == "pilar_isolado_em_balanco"


def test_desaprumo_n_pilares_invalido_levanta():
    with pytest.raises(ValueError):
        eg.desaprumo_global(H_m=10.0, n_pilares=0)


# --- 11.3.3.4.1 — combinação vento x desaprumo (PDF p. 79) ------------------
def test_combinar_vento_desaprumo_caso_a_somente_vento():
    # 0,3*100 = 30 > 20 -> caso a
    r = eg.combinar_vento_desaprumo(M_vento=100.0, M_desaprumo=20.0)
    assert r.caso == "a"
    assert r.M_calculo == pytest.approx(100.0)
    assert r.considerar_theta1min is False


def test_combinar_vento_desaprumo_fronteira_caso_a_cai_em_c():
    # 0,3*100 = 30 = M_desaprumo -> igualdade nao satisfaz "maior que" -> caso c
    r = eg.combinar_vento_desaprumo(M_vento=100.0, M_desaprumo=30.0)
    assert r.caso == "c"
    assert r.M_calculo == pytest.approx(130.0)


def test_combinar_vento_desaprumo_caso_b_somente_desaprumo():
    # 0,3*100 (desaprumo) = 30; M_vento = 5 < 30 -> caso b
    r = eg.combinar_vento_desaprumo(M_vento=5.0, M_desaprumo=100.0)
    assert r.caso == "b"
    assert r.M_calculo == pytest.approx(100.0)
    assert r.considerar_theta1min is True


def test_combinar_vento_desaprumo_fronteira_caso_b_cai_em_c():
    # M_vento = 30 = 0,3*100 -> igualdade nao satisfaz "inferior a" -> caso c
    r = eg.combinar_vento_desaprumo(M_vento=30.0, M_desaprumo=100.0)
    assert r.caso == "c"
    assert r.M_calculo == pytest.approx(130.0)


def test_combinar_vento_desaprumo_caso_c_combina_as_duas():
    r = eg.combinar_vento_desaprumo(M_vento=50.0, M_desaprumo=100.0)
    assert r.caso == "c"
    assert r.M_calculo == pytest.approx(150.0)
    assert r.considerar_theta1min is False


def test_combinar_vento_desaprumo_negativo_levanta():
    with pytest.raises(ValueError):
        eg.combinar_vento_desaprumo(M_vento=-1.0, M_desaprumo=10.0)
    with pytest.raises(ValueError):
        eg.combinar_vento_desaprumo(M_vento=10.0, M_desaprumo=-1.0)
