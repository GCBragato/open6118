"""Testes do P39 -- Fadiga: combinação, cortante, concreto e protensão
(NBR 6118:2026, Seção 23: 23.5.2, 23.5.3, 23.5.4, 23.5.5).

Valores esperados tirados das imagens das páginas do PDF (SCRATCH/nbr_png):
p217 (23.5.2, psi1 de fadiga e a combinação Fd,ser); p218-p219 (23.5.3,
correção do Modelo I/II, eta_s, phi_eq, Tabela de xi); p219-p220 (23.5.4.1
e 23.5.4.2, fadiga do concreto). As contas à mão estão nos comentários.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import acoes_nbr6118 as ac  # noqa: E402
import cortante_nbr6118 as cort  # noqa: E402
import fadiga_nbr6118 as F  # noqa: E402
import nucleo_nbr6118 as nbr  # noqa: E402


# ===========================================================================
# 23.5.2 -- psi1 da fadiga (Tabela, PDF p. 217) e combinacao_fadiga
# ===========================================================================
def test_2352_psi1_fadiga_todos_os_5_valores():
    """Os 5 valores de psi1 por tipo de obra/peça (PDF p. 217)."""
    assert F.psi1_fadiga("ponte_rodoviaria_viga") == 0.5
    assert F.psi1_fadiga("ponte_rodoviaria_transversina") == 0.7
    assert F.psi1_fadiga("ponte_rodoviaria_laje_tabuleiro") == 0.8
    assert F.psi1_fadiga("ponte_ferroviaria") == 1.0
    assert F.psi1_fadiga("viga_rolamento_ponte_rolante") == 1.0


def test_2352_tipo_obra_desconhecido_leva_a_valueerror():
    with pytest.raises(ValueError):
        F.psi1_fadiga("ponte_pedestres")


def _acoes_exemplo():
    """Permanente 1000, variável principal (trem-tipo) 500 com categoria de
    edificação 'com_predominancia' (psi1 = 0,6 na Tabela 11.2 -- será
    substituído pelo psi1 de fadiga dentro de combinacao_fadiga), e uma
    segunda variável (vento) 100, que continua com psi2 = 0 (Tabela 11.2)."""
    g = ac.Acao("peso proprio", "permanente_direta", "permanente", 1000.0)
    q1 = ac.Acao("trem tipo", "variavel_direta", "variavel", 500.0,
                categoria_psi="com_predominancia")
    q2 = ac.Acao("vento", "variavel_direta", "variavel", 100.0,
                categoria_psi="vento")
    return g, q1, q2


def test_2352_combinacao_fadiga_usa_psi1_da_tabela_de_fadiga_nao_da_11_2():
    """Fd,ser = Fgk + psi1_fadiga*Fq1k + psi2*Fq2k (23.5.2).

    Ponte rodoviária, viga: psi1 = 0,5 (não o 0,6 de 'com_predominancia',
    Tabela 11.2). Fd,ser = 1000 + 0,5*500 + 0,0*100 = 1250.
    """
    g, q1, q2 = _acoes_exemplo()
    r = F.combinacao_fadiga([g, q1, q2], "ponte_rodoviaria_viga")
    assert r.principal == "trem tipo"
    assert r.Fd == pytest.approx(1250.0)
    parcela_q1 = next(p for p in r.parcelas if p.nome == "trem tipo")
    assert parcela_q1.psi == pytest.approx(0.5)


def test_2352_combinacao_fadiga_ponte_ferroviaria_psi1_igual_a_1():
    """Ponte ferroviária: psi1 = 1,0 -> Fd,ser = 1000 + 1,0*500 + 0,0*100 = 1500."""
    g, q1, q2 = _acoes_exemplo()
    r = F.combinacao_fadiga([g, q1, q2], "ponte_ferroviaria")
    assert r.Fd == pytest.approx(1500.0)


def test_2352_combinacao_fadiga_reproduz_combinacao_frequente_com_psi1_trocado():
    """Reaproveita combinacao_servico(tipo='frequente') -- com psi1 = 1,0
    (viga de rolamento de ponte rolante), o resultado bate com a
    combinação frequente comum onde a categoria já desse psi1 = 1,0."""
    g, q1, q2 = _acoes_exemplo()
    r_fad = F.combinacao_fadiga([g, q1, q2], "viga_rolamento_ponte_rolante")
    q1_psi1_1 = ac.Acao("trem tipo", "variavel_direta", "variavel", 500.0,
                        categoria_psi=(0.7, 1.0, 0.4))
    r_freq = ac.combinacao_servico([g, q1_psi1_1, q2], tipo="frequente")
    assert r_fad.Fd == pytest.approx(r_freq.Fd)


def test_2352_combinacao_fadiga_tipo_obra_invalido_leva_a_valueerror():
    g, q1, q2 = _acoes_exemplo()
    with pytest.raises(ValueError):
        F.combinacao_fadiga([g, q1, q2], "predio_residencial")


# ===========================================================================
# 23.5.5 -- remissão do "número de ciclos muito menor que 2e6" (PDF p. 217):
# a curva S-N (P38) já cobre o efeito (N menor -> Delta_fsd,fad maior)
# ===========================================================================
def test_2355_ciclos_bem_menores_que_2e6_aumenta_a_resistencia_a_fadiga():
    """23.5.5 (remissão, PDF p. 217): 'em casos especiais de pontes rolantes
    de operação menos frequente, onde o número de ciclos é significativamente
    menor que 2x10^6, a resistência à fadiga pode ser aumentada conforme
    23.5.5' -- é exatamente o que `curva_SN` (P38) já devolve: para N bem
    menor que 2x10^6, Delta_fsd,fad > Delta_fsd,fad,min (tabelado)."""
    delta_min = F.TABELA_23_2_PASSIVA_MPA["barra_reta"][20.0]  # 185 MPa
    delta_n_pequeno = F.curva_SN(delta_min, "T1", 2.0e4)  # piso de 23.5.1
    assert delta_n_pequeno > delta_min


# ===========================================================================
# 23.5.3 -- Modelo I: Vc,fad = 0,5 x Vc (PDF p. 218)
# ===========================================================================
def test_2353_modelo_I_vc_fadiga_e_metade_do_vc_padrao():
    r = cort.modelo_calculo_I(VSd_kn=50.0, bw_cm=20.0, d_cm=45.0, fck_mpa=30.0)
    r_fad = cort.modelo_calculo_I(VSd_kn=50.0, bw_cm=20.0, d_cm=45.0, fck_mpa=30.0,
                                  fadiga=True)
    assert r_fad.Vc == pytest.approx(0.5 * r.Vc)
    assert r_fad.fadiga is True
    assert r.fadiga is False


def test_2353_modelo_I_vc_fadiga_muda_vsw_e_asw():
    """Com Vc menor, sobra mais VSd para o aço: Vsw,fad > Vsw padrão."""
    r = cort.modelo_calculo_I(VSd_kn=50.0, bw_cm=20.0, d_cm=45.0, fck_mpa=30.0)
    r_fad = cort.modelo_calculo_I(VSd_kn=50.0, bw_cm=20.0, d_cm=45.0, fck_mpa=30.0,
                                  fadiga=True)
    assert r_fad.Vsw > r.Vsw
    assert r_fad.Asw_m > r.Asw_m


# ===========================================================================
# 23.5.3 -- Modelo II: tg(theta_cor) = raiz(tg(theta)) <= 1 (PDF p. 218)
# ===========================================================================
def test_2353_theta_corrigido_fadiga_theta_45_e_caso_limite():
    """theta=45 -> tg(theta)=1 -> raiz(1)=1 -> theta_cor=45 (tg_cor<=1 exato)."""
    assert cort.theta_corrigido_fadiga_deg(45.0) == pytest.approx(45.0)


def test_2353_theta_corrigido_fadiga_theta_30():
    """theta=30 -> tg(theta)=0,57735; raiz=0,75984 -> theta_cor=atan(0,75984)
    = 37,2289 graus (mais conservador que os 30 graus de entrada)."""
    theta_cor = cort.theta_corrigido_fadiga_deg(30.0)
    tg_theta = math.tan(math.radians(30.0))
    esperado = math.degrees(math.atan(math.sqrt(tg_theta)))
    assert theta_cor == pytest.approx(esperado)
    assert theta_cor == pytest.approx(37.2289, abs=1e-3)
    assert theta_cor > 30.0
    assert theta_cor < 45.0


def test_2353_modelo_II_fadiga_usa_theta_corrigido_e_preserva_theta_de_entrada():
    r = cort.modelo_calculo_II(VSd_kn=50.0, bw_cm=20.0, d_cm=45.0, fck_mpa=30.0,
                               theta_deg=30.0, fadiga=True)
    assert r.theta_deg == 30.0  # entrada preservada
    assert r.theta_cor_deg == pytest.approx(37.2289, abs=1e-3)
    assert r.fadiga is True


def test_2353_modelo_II_sem_fadiga_nao_tem_theta_cor():
    r = cort.modelo_calculo_II(VSd_kn=50.0, bw_cm=20.0, d_cm=45.0, fck_mpa=30.0,
                               theta_deg=30.0)
    assert r.theta_cor_deg is None
    assert r.fadiga is False


def test_2353_modelo_II_fadiga_nao_reduz_vc0():
    """'Para o Modelo II não há necessidade dessa redução [de Vc], sendo
    suficiente a correção do ângulo das bielas' (PDF p. 219): o Vc de
    fadiga bate com o Vc padrão quando VSd <= Vc0 (mesmo ramo, sem a
    correção de theta afetar Vc1)."""
    r = cort.modelo_calculo_II(VSd_kn=1.0, bw_cm=20.0, d_cm=45.0, fck_mpa=30.0,
                               theta_deg=30.0)
    r_fad = cort.modelo_calculo_II(VSd_kn=1.0, bw_cm=20.0, d_cm=45.0, fck_mpa=30.0,
                                   theta_deg=30.0, fadiga=True)
    assert r_fad.Vc == pytest.approx(r.Vc)


def test_2353_theta_corrigido_fadiga_theta_nao_positivo_leva_a_valueerror():
    with pytest.raises(ValueError):
        cort.theta_corrigido_fadiga_deg(0.0)


# ===========================================================================
# 23.5.3 -- Tabela de xi (PDF p. 219), os 6 valores
# ===========================================================================
def test_2353_tabela_xi_pos_tracao_4_valores():
    assert F.xi_aderencia("pos_tracao", "liso") == 0.2
    assert F.xi_aderencia("pos_tracao", "cordoalhas") == 0.4
    assert F.xi_aderencia("pos_tracao", "fios_entalhados") == 0.6
    assert F.xi_aderencia("pos_tracao", "barras_nervuradas") == 1.0


def test_2353_tabela_xi_pre_tracao_2_valores():
    assert F.xi_aderencia("pre_tracao", "cordoalhas") == 0.6
    assert F.xi_aderencia("pre_tracao", "acos_entalhados") == 0.8


def test_2353_tabela_xi_combinacao_nao_definida_leva_a_faixanormativaerror():
    """A pré-tração só lista cordoalhas e aços entalhados; 'liso' não existe
    nessa linha (célula que a norma não define para esse processo)."""
    with pytest.raises(nbr.FaixaNormativaError):
        F.xi_aderencia("pre_tracao", "liso")


def test_2353_tabela_xi_processo_desconhecido_leva_a_valueerror():
    with pytest.raises(ValueError):
        F.xi_aderencia("tracao_direta", "cordoalhas")


# ===========================================================================
# 23.5.3 -- phi_eq de feixe (PDF p. 218)
# ===========================================================================
def test_2353_phi_eq_feixe_cordoalha_12_7mm():
    """Ap = 98,7 mm² (0,987 cm², cordoalha CP190-RB de 12,7 mm) ->
    phi_eq = 1,6 x raiz(98,7) = 15,896 mm."""
    phi_eq = F.phi_eq_feixe(Ap_cm2=0.987)
    assert phi_eq == pytest.approx(1.6 * math.sqrt(98.7), rel=1e-4)
    assert phi_eq == pytest.approx(15.896, abs=1e-3)


def test_2353_phi_eq_feixe_area_nao_positiva_leva_a_valueerror():
    with pytest.raises(ValueError):
        F.phi_eq_feixe(0.0)


# ===========================================================================
# 23.5.3 -- eta_s (PDF p. 218-219)
# ===========================================================================
def test_2353_eta_s_sem_protensao_e_1():
    """Ap = 0 (sem protensão) -> eta_s = 1 (não há aço ativo a corrigir)."""
    assert F.eta_s(As_cm2=10.0, Ap_cm2=0.0, phi_s_mm=16.0, phi_p_mm=12.7, xi=0.4) == 1.0


def test_2353_eta_s_ap_igual_as_mesmo_phi_e_xi_1_da_1():
    """Ap=As, phi_s=phi_p, xi=1 -> eta_s = (1+1)/(1+1*raiz(1*1)) = 2/2 = 1."""
    r = F.eta_s(As_cm2=10.0, Ap_cm2=10.0, phi_s_mm=16.0, phi_p_mm=16.0, xi=1.0)
    assert r == pytest.approx(1.0)


def test_2353_eta_s_maior_que_1_quando_phi_p_menor_que_phi_s():
    """Ap=As, xi=0,4 (cordoalha pós-tração), phi_p < phi_s -> denominador
    menor que o numerador -> eta_s > 1."""
    r = F.eta_s(As_cm2=10.0, Ap_cm2=10.0, phi_s_mm=20.0, phi_p_mm=12.7, xi=0.4)
    numerador = 1.0 + 1.0
    denominador = 1.0 + 1.0 * math.sqrt(0.4 * 20.0 / 12.7)
    assert r == pytest.approx(numerador / denominador)
    assert r > 1.0


def test_2353_eta_s_piso_1_quando_formula_bruta_cai_abaixo():
    """phi_s bem maior que phi_p (fio/cordoalha fino) empurra a fórmula
    bruta abaixo de 1; o piso >= 1 da norma corta nesse caso."""
    bruto_num = 1.0 + 5.0
    bruto_den = 1.0 + 5.0 * math.sqrt(1.0 * 200.0 / 10.0)
    bruto = bruto_num / bruto_den
    assert bruto < 1.0  # a fórmula bruta, sem o piso, cairia abaixo de 1
    r = F.eta_s(As_cm2=2.0, Ap_cm2=10.0, phi_s_mm=200.0, phi_p_mm=10.0, xi=1.0)
    assert r == pytest.approx(1.0)


def test_2353_eta_s_as_nao_positivo_leva_a_valueerror():
    with pytest.raises(ValueError):
        F.eta_s(As_cm2=0.0, Ap_cm2=5.0, phi_s_mm=16.0, phi_p_mm=12.7, xi=0.4)


# ===========================================================================
# 23.5.4.1 -- eta_c,grad e fadiga do concreto em compressão (PDF p. 219)
# ===========================================================================
def test_23541_eta_c_grad_tensoes_iguais_da_1():
    """sigma_c1 = sigma_c2 -> eta_c,grad = 1/(1,5-0,5) = 1,0."""
    assert F.eta_c_grad(5.0, 5.0) == pytest.approx(1.0)


def test_23541_eta_c_grad_sigma_c1_zero_da_0_667():
    """sigma_c1 = 0 -> eta_c,grad = 1/1,5 = 0,6667 (flexão pura)."""
    assert F.eta_c_grad(0.0, 10.0) == pytest.approx(1.0 / 1.5)


def test_23541_eta_c_grad_meio_termo():
    """sigma_c1 = 0,5*sigma_c2 -> eta_c,grad = 1/(1,5-0,25) = 0,8."""
    assert F.eta_c_grad(5.0, 10.0) == pytest.approx(0.8)


def test_23541_eta_c_grad_sigma_c2_zero_leva_a_faixanormativaerror():
    with pytest.raises(nbr.FaixaNormativaError):
        F.eta_c_grad(0.0, 0.0)


def test_23541_eta_c_grad_c1_maior_que_c2_leva_a_faixanormativaerror():
    """sigma_c1 é, por definição, o MENOR valor em módulo; c1 > c2 contraria
    a definição da Figura 23.1."""
    with pytest.raises(nbr.FaixaNormativaError):
        F.eta_c_grad(10.0, 5.0)


def test_23541_verificar_fadiga_concreto_compressao_fcd_fad_e_045_fcd():
    """fcd,fad = 0,45 x fcd; C30, gama_c=1,4 -> fcd = 30/1,4 = 21,4286 MPa
    -> fcd,fad = 9,6429 MPa. sigma_c1=sigma_c2 -> eta_c,grad=1.
    Solicitante = 1 x 1 x 9,0 = 9,0 <= 9,6429 -> ok."""
    r = F.verificar_fadiga_concreto_compressao(
        sigma_c_max_mpa=9.0, sigma_c1_mpa=8.0, sigma_c2_mpa=8.0, fck_mpa=30.0,
    )
    assert r.fcd_fad_mpa == pytest.approx(0.45 * (30.0 / 1.4))
    assert r.ok is True


def test_23541_verificar_fadiga_concreto_compressao_reprova_acima_do_limite():
    r = F.verificar_fadiga_concreto_compressao(
        sigma_c_max_mpa=10.0, sigma_c1_mpa=8.0, sigma_c2_mpa=8.0, fck_mpa=30.0,
    )
    assert r.ok is False


# ===========================================================================
# 23.5.4.2 -- fadiga do concreto em tração (PDF p. 220)
# ===========================================================================
def test_23542_fctd_fad_e_03_fctd_inf_c30():
    """fctd,fad = 0,3 x fctd,inf; fctd,inf = nucleo.fctd (fctk,inf/gama_c)."""
    fctd_inf = nbr.fctd(30.0)
    r = F.verificar_fadiga_concreto_tracao(sigma_ct_max_mpa=0.1, fck_mpa=30.0)
    assert r.fctd_fad_mpa == pytest.approx(0.3 * fctd_inf)


def test_23542_verificar_fadiga_concreto_tracao_passa_e_reprova():
    limite = F.FCTD_FAD_FATOR * nbr.fctd(30.0)
    ok = F.verificar_fadiga_concreto_tracao(sigma_ct_max_mpa=limite - 0.01, fck_mpa=30.0)
    nao_ok = F.verificar_fadiga_concreto_tracao(sigma_ct_max_mpa=limite + 0.01, fck_mpa=30.0)
    assert ok.ok is True
    assert nao_ok.ok is False
