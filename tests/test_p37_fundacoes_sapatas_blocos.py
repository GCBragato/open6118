"""Testes do P37 -- fundacoes: sapatas e blocos (22.6 e 22.7).

Valores esperados tirados da NBR 6118:2026 (imagens das paginas 211 a 215 do
PDF) e das contas escritas no comentario de cada teste. Os itens cobertos:

    22.6.1       hipotese de distribuicao plana de tensoes (p. 211)
    22.6.4.1.1   detalhamento da armadura de flexao e fendilhamento (p. 212-213)
    22.6.4.1.2   altura da sapata para o arranque do pilar (p. 213)
    22.7.1       bloco rigido x flexivel (p. 213)
    22.7.2.1 a   faixa de 1,2*phi sobre o eixo da estaca (p. 213)
    22.7.4.1.1   mais de 85 % nas faixas; estacas tracionadas (p. 214)
    22.7.4.1.2   armadura de distribuicao, 20 % das forcas de tracao (p. 214)
    22.7.4.1.3   condicoes de exigencia da armadura de suspensao (p. 215)
    22.7.4.1.4   altura do bloco para o arranque do pilar (p. 215)
    22.7.4.1.5   armadura lateral e superior em estacas em linha unica (p. 215)
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import ancoragem_nbr6118 as anc  # noqa: E402
import blocos_nbr6118 as BLO  # noqa: E402
import nucleo_nbr6118 as nbr  # noqa: E402
import sapatas_nbr6118 as SAP  # noqa: E402


FYD_KNCM2 = 500.0 / 1.15 / 10.0  # 43,478 kN/cm2 (CA-50, gama_s = 1,15)


# ---------------------------------------------------------------------------
# 22.6.1 -- hipotese de distribuicao plana de tensoes (PDF p. 211)
# ---------------------------------------------------------------------------
def test_hipotese_plana_fronteira_da_rigidez_h_igual_a_um_terco():
    # 22.6.1: h >= (a - ap)/3. A = 200, ap = 50 -> (200 - 50)/3 = 50,0 cm.
    # A fronteira pertence ao lado rigido (a norma escreve ">=").
    r = SAP.verificar_hipotese_distribuicao_plana(50.0, 200.0, 50.0)
    assert r.h_min_rigidez_cm == pytest.approx(50.0)
    assert r.rigida is True
    assert r.hipotese_valida is True
    assert r.ok is True


def test_hipotese_plana_logo_abaixo_da_fronteira_e_flexivel_e_avisa():
    # h = 49,9 cm < 50,0 cm -> sapata flexivel; a hipotese deve ser revista.
    with pytest.warns(nbr.AvisoNBR6118):
        r = SAP.verificar_hipotese_distribuicao_plana(49.9, 200.0, 50.0)
    assert r.rigida is False
    assert r.hipotese_valida is False
    assert "flexivel" in r.governante.replace("í", "i")


def test_hipotese_plana_confere_as_duas_direcoes():
    # 22.6.1: "nas duas direcoes". A = 200, ap = 50 -> 50,0 cm;
    # B = 400, bp = 40 -> (400 - 40)/3 = 120,0 cm. h = 60 passa em A e nao em B.
    with pytest.warns(nbr.AvisoNBR6118):
        r = SAP.verificar_hipotese_distribuicao_plana(60.0, 200.0, 50.0,
                                                      400.0, 40.0)
    assert r.h_min_rigidez_cm == pytest.approx(120.0)
    assert r.rigida is False


def test_hipotese_plana_rocha_invalida_mesmo_com_sapata_rigida():
    # 22.6.1: "Para sapatas flexiveis ou em casos extremos de fundacao em
    # rocha, mesmo com sapata rigida, essa hipotese deve ser revista."
    with pytest.warns(nbr.AvisoNBR6118):
        r = SAP.verificar_hipotese_distribuicao_plana(50.0, 200.0, 50.0,
                                                      fundacao_em_rocha=True)
    assert r.rigida is True
    assert r.hipotese_valida is False
    assert "rocha" in r.governante


def test_hipotese_plana_sem_h_nao_avalia_rigidez():
    r = SAP.verificar_hipotese_distribuicao_plana(None, 200.0)
    assert r.rigida is None
    assert r.hipotese_valida is True


def test_hipotese_plana_dimensoes_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        SAP.verificar_hipotese_distribuicao_plana(50.0, 0.0, 50.0)
    with pytest.raises(nbr.FaixaNormativaError):
        # pilar maior que a sapata
        SAP.verificar_hipotese_distribuicao_plana(50.0, 200.0, 250.0)


def test_tensoes_excentrica_1d_avisa_para_sapata_flexivel():
    # N = 1000 kN, M = 20000 kN.cm, A = B = 200 cm; h = 40 cm, ap = 50 cm:
    # (200 - 50)/3 = 50 > 40 -> flexivel -> aviso e hipotese_plana_valida False.
    with pytest.warns(nbr.AvisoNBR6118):
        r = SAP.tensoes_sapata_excentrica_1d(1000.0, 20000.0, 200.0, 200.0,
                                             h_cm=40.0, ap_cm=50.0)
    assert r["hipotese_plana_valida"] is False
    # as tensoes nao mudam: 0,025*(1 +/- 0,6) = 0,04 e 0,01 kN/cm2
    assert r["sigma_max_kncm2"] == pytest.approx(0.04, abs=1e-9)
    assert r["sigma_min_kncm2"] == pytest.approx(0.01, abs=1e-9)


def test_tensoes_excentrica_1d_sem_dados_de_rigidez_nao_avisa():
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        r = SAP.tensoes_sapata_excentrica_1d(1000.0, 20000.0, 200.0, 200.0)
    assert r["hipotese_plana_valida"] is None


def test_tensoes_excentrica_2d_avisa_e_mantem_a_tupla():
    # N = 1000, eA = 10, eB = 5, A = B = 200: sigma_++ = 0,025*1,45 = 0,03625.
    with pytest.warns(nbr.AvisoNBR6118):
        s = SAP.tensoes_sapata_excentrica_2d(1000.0, 10.0, 5.0, 200.0, 200.0,
                                             h_cm=40.0, ap_cm=50.0)
    assert len(s) == 4
    assert s[0] == pytest.approx(0.03625, abs=1e-9)
    assert s[3] == pytest.approx(0.01375, abs=1e-9)


# ---------------------------------------------------------------------------
# 22.6.4.1.1 -- detalhamento da armadura de flexao da sapata (PDF p. 212)
# ---------------------------------------------------------------------------
def test_detalhamento_flexao_sapata_distribuicao_e_gancho():
    # As = 15,01 cm2 (exemplo do modulo), phi = 12,5 mm, sapata 265 x 205,
    # barras ao longo de 265 cm distribuidas na largura de 205 cm, c = 4 cm.
    # As,barra = pi*1,25^2/4 = 1,22718 cm2 -> n = teto(15,01/1,22718) = 13.
    # largura util = 205 - 2*4 - 1,25 = 195,75 cm; s = 195,75/12 = 16,3125 cm.
    # comprimento reto = 265 - 2*4 = 257 cm; gancho reto = 8*phi = 10 cm
    # (9.4.2.3) -> comprimento total = 257 + 2*10 = 277 cm.
    r = SAP.detalhamento_flexao_sapata(15.01, 12.5, 205.0, 265.0,
                                       cobrimento_cm=4.0)
    assert r.n_barras == 13
    assert r.As_efetiva_cm2 == pytest.approx(13.0 * math.pi * 1.25 ** 2 / 4.0)
    assert r.largura_util_cm == pytest.approx(195.75)
    assert r.espacamento_cm == pytest.approx(16.3125)
    assert r.comprimento_reto_cm == pytest.approx(257.0)
    assert r.gancho_ponta_reta_cm == pytest.approx(10.0)
    assert r.pino_dobramento_phi == pytest.approx(5.0)  # Tabela 9.1, CA-50, phi < 20
    assert r.comprimento_total_barra_cm == pytest.approx(277.0)
    assert r.de_face_a_face is True
    assert r.exige_fendilhamento_horizontal is False
    assert r.ok is True


def test_detalhamento_flexao_sapata_sem_gancho_nao_passa():
    r = SAP.detalhamento_flexao_sapata(15.01, 12.5, 205.0, 265.0,
                                       com_gancho_nas_duas_extremidades=False)
    assert r.ok is False
    assert "gancho" in r.governante


def test_detalhamento_flexao_sapata_minimo_de_duas_barras():
    # As minusculo: a distribuicao de face a face ainda precisa de 2 barras.
    r = SAP.detalhamento_flexao_sapata(0.1, 10.0, 100.0, 100.0)
    assert r.n_barras == 2
    assert r.espacamento_cm == pytest.approx(100.0 - 8.0 - 1.0)


def test_detalhamento_flexao_sapata_espacamento_maximo_do_usuario():
    # A 22.6.4.1.1 nao fixa espacamento maximo; quando o usuario impoe um,
    # ele entra no ok. s = 16,3125 cm > 15 cm -> nao passa.
    r = SAP.detalhamento_flexao_sapata(15.01, 12.5, 205.0, 265.0,
                                       espacamento_max_cm=15.0)
    assert r.ok is False
    r_ok = SAP.detalhamento_flexao_sapata(15.01, 12.5, 205.0, 265.0,
                                          espacamento_max_cm=20.0)
    assert r_ok.ok is True


def test_detalhamento_flexao_sapata_phi_25_exige_fendilhamento():
    # phi = 25 mm: 22.6.4.1.1 (p. 213) exige verificar o fendilhamento
    # horizontal; sem declarar a verificacao, o detalhamento nao passa.
    r = SAP.detalhamento_flexao_sapata(20.0, 25.0, 205.0, 265.0)
    assert r.exige_fendilhamento_horizontal is True
    assert r.ok is False
    r2 = SAP.detalhamento_flexao_sapata(20.0, 25.0, 205.0, 265.0,
                                        fendilhamento_verificado=True)
    assert r2.ok is True


def test_detalhamento_flexao_sapata_geometria_invalida():
    with pytest.raises(nbr.FaixaNormativaError):
        # largura menor que dois cobrimentos mais a bitola
        SAP.detalhamento_flexao_sapata(10.0, 12.5, 8.0, 265.0,
                                       cobrimento_cm=4.0)
    with pytest.raises(nbr.FaixaNormativaError):
        SAP.detalhamento_flexao_sapata(10.0, 12.5, 205.0, 8.0,
                                       cobrimento_cm=4.0)
    with pytest.raises(nbr.FaixaNormativaError):
        SAP.detalhamento_flexao_sapata(0.0, 12.5, 205.0, 265.0)


# ---------------------------------------------------------------------------
# 22.6.4.1.1 -- fendilhamento em plano horizontal, phi >= 25 mm (PDF p. 213)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("phi, exige", [
    (10.0, False),    # bem abaixo do degrau
    (24.9, False),    # logo abaixo
    (25.0, True),     # o degrau pertence a faixa que exige (">= 25 mm")
    (25.1, True),     # logo acima
    (40.0, True),     # bem acima
])
def test_fendilhamento_horizontal_degrau_em_25_mm(phi, exige):
    r = SAP.verificar_fendilhamento_horizontal(phi, avisar=False)
    assert r.exige_verificacao is exige
    assert r.phi_limite_mm == pytest.approx(25.0)
    # sem declarar a verificacao, ok e o contrario da exigencia
    assert r.ok is (not exige)


def test_fendilhamento_horizontal_avisa_e_aceita_declaracao():
    with pytest.warns(nbr.AvisoNBR6118):
        r = SAP.verificar_fendilhamento_horizontal(32.0)
    assert r.ok is False
    r2 = SAP.verificar_fendilhamento_horizontal(32.0,
                                                fendilhamento_verificado=True)
    assert r2.ok is True
    assert r2.exige_verificacao is True


def test_fendilhamento_horizontal_bitola_invalida():
    with pytest.raises(nbr.FaixaNormativaError):
        SAP.verificar_fendilhamento_horizontal(0.0)


# ---------------------------------------------------------------------------
# 22.6.4.1.2 -- altura da sapata para a ancoragem do arranque (PDF p. 213)
# ---------------------------------------------------------------------------
def test_altura_arranque_sapata_passa_e_traz_h_minimo():
    # h = 100, c = 4, dobra = 0 -> l,disponivel = 96 cm; lb,nec = 60 cm.
    # h,minimo = 60 + 4 = 64 cm.
    r = SAP.altura_arranque_suficiente(100.0, 60.0, 4.0)
    assert r.comprimento_disponivel_cm == pytest.approx(96.0)
    assert r.h_minima_cm == pytest.approx(64.0)
    assert r.ok is True
    assert r.item == "22.6.4.1.2"


def test_altura_arranque_sapata_fronteira_l_disponivel_igual_lb_nec():
    # A igualdade e o limite e passa (Rd >= Sd, 12.5.2).
    r = SAP.altura_arranque_suficiente(100.0, 96.0, 4.0)
    assert r.ok is True
    r2 = SAP.altura_arranque_suficiente(100.0, 96.1, 4.0)
    assert r2.ok is False
    assert r2.h_minima_cm == pytest.approx(100.1)


def test_altura_arranque_sapata_desconta_a_dobra():
    # l,disponivel = 100 - 4 - 10 = 86 cm < lb,nec = 90 cm.
    r = SAP.altura_arranque_suficiente(100.0, 90.0, 4.0, desconto_dobra_cm=10.0)
    assert r.comprimento_disponivel_cm == pytest.approx(86.0)
    assert r.ok is False


def test_altura_arranque_sapata_entradas_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        SAP.altura_arranque_suficiente(0.0, 60.0, 4.0)
    with pytest.raises(nbr.FaixaNormativaError):
        SAP.altura_arranque_suficiente(100.0, 0.0, 4.0)
    with pytest.raises(nbr.FaixaNormativaError):
        SAP.altura_arranque_suficiente(100.0, 60.0, -1.0)


# ---------------------------------------------------------------------------
# 22.7.1 -- bloco rigido x flexivel (PDF p. 213)
# ---------------------------------------------------------------------------
def test_bloco_rigido_fronteira_h_igual_a_um_terco():
    # Criterio analogo ao de sapatas (22.6.1): h >= (a - ap)/3.
    # a = 350, ap = 50 -> (350 - 50)/3 = 100,0 cm exatos.
    assert BLO.eh_rigido_bloco(100.0, 350.0, 50.0) is True
    assert BLO.eh_rigido_bloco(99.9, 350.0, 50.0) is False


def test_classificar_bloco_duas_direcoes_e_memoria():
    # a = 250, ap = 50 -> 66,667 cm; b = 400, bp = 40 -> 120,0 cm.
    r = BLO.classificar_bloco(100.0, 250.0, 50.0, 400.0, 40.0)
    assert r.h_min_rigidez_cm == pytest.approx(120.0)
    assert r.rigido is False
    assert r.classificacao == "flexivel"
    assert r.ok is False
    assert any("22.7.1" in linha for linha in r.memoria)


def test_classificar_bloco_rigido():
    r = BLO.classificar_bloco(100.0, 250.0, 50.0)
    assert r.h_min_rigidez_cm == pytest.approx(200.0 / 3.0)
    assert r.rigido is True
    assert r.classificacao == "rigido"


def test_classificar_bloco_geometria_invalida():
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.classificar_bloco(100.0, 250.0, 300.0)   # pilar maior que o bloco
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.classificar_bloco(0.0, 250.0, 50.0)


# ---------------------------------------------------------------------------
# 22.7.2.1 a -- faixa de 1,2*phi sobre o eixo da estaca (PDF p. 213)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("phi_cm, faixa_cm", [
    (20.0, 24.0),    # 1,2 * 20
    (30.0, 36.0),    # 1,2 * 30
    (50.0, 60.0),    # 1,2 * 50
])
def test_faixa_armadura_estaca(phi_cm, faixa_cm):
    assert BLO.faixa_armadura_estaca_cm(phi_cm) == pytest.approx(faixa_cm)


def test_faixa_armadura_estaca_diametro_invalido():
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.faixa_armadura_estaca_cm(0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.faixa_armadura_estaca_cm(-30.0)


# ---------------------------------------------------------------------------
# 22.7.4.1.1 -- mais de 85 % da armadura nas faixas (PDF p. 214)
# ---------------------------------------------------------------------------
def test_85pct_nas_faixas_desigualdade_estrita():
    # "mais de 85 %": 85 % exatos NAO atendem.
    exato = BLO.verificar_85pct_nas_faixas(85.0, 100.0)
    assert exato.fracao == pytest.approx(0.85)
    assert exato.As_minima_nas_faixas_cm2 == pytest.approx(85.0)
    assert exato.ok is False
    acima = BLO.verificar_85pct_nas_faixas(85.01, 100.0)
    assert acima.ok is True
    abaixo = BLO.verificar_85pct_nas_faixas(84.99, 100.0)
    assert abaixo.ok is False


def test_85pct_nas_faixas_toda_a_armadura_nas_faixas():
    r = BLO.verificar_85pct_nas_faixas(12.0, 12.0)
    assert r.fracao == pytest.approx(1.0)
    assert r.ok is True


def test_85pct_nas_faixas_entradas_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.verificar_85pct_nas_faixas(10.0, 0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.verificar_85pct_nas_faixas(-1.0, 10.0)
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.verificar_85pct_nas_faixas(11.0, 10.0)   # faixas > total


def test_detalhamento_flexao_bloco_completo():
    # phi,estaca = 30 cm -> faixa = 36 cm (22.7.2.1 a).
    # 90 % nas faixas, de face a face, com gancho, lb,nec = 40 <= 50 cm
    # disponiveis a partir da face interna da estaca.
    r = BLO.detalhamento_flexao_bloco(9.0, 10.0, 30.0, lb_nec_cm=40.0,
                                      comprimento_ancoragem_disponivel_cm=50.0)
    assert r.faixa_cm == pytest.approx(36.0)
    assert r.fracao == pytest.approx(0.9)
    assert r.ok_85pct is True
    assert r.ok_ancoragem is True
    assert r.ok is True


def test_detalhamento_flexao_bloco_reprova_por_ancoragem_e_por_gancho():
    r = BLO.detalhamento_flexao_bloco(9.0, 10.0, 30.0, lb_nec_cm=60.0,
                                      comprimento_ancoragem_disponivel_cm=50.0)
    assert r.ok_ancoragem is False
    assert r.ok is False
    r2 = BLO.detalhamento_flexao_bloco(9.0, 10.0, 30.0,
                                       com_gancho_nas_duas_extremidades=False)
    assert r2.ok is False
    r3 = BLO.detalhamento_flexao_bloco(9.0, 10.0, 30.0, de_face_a_face=False)
    assert r3.ok is False


def test_detalhamento_flexao_bloco_sem_dados_de_ancoragem_nao_confere():
    r = BLO.detalhamento_flexao_bloco(9.0, 10.0, 30.0)
    assert r.ok_ancoragem is True
    assert r.lb_nec_cm is None
    assert any("não foi conferida" in linha for linha in r.memoria)


# ---------------------------------------------------------------------------
# 22.7.4.1.1 -- estacas tracionadas (PDF p. 214, Figura 22.7)
# ---------------------------------------------------------------------------
def test_estaca_tracionada_ancora_no_topo_do_bloco():
    # Rd,tracao = 300 kN, CA-50, gama_s = 1,15 -> fyd = 43,478 kN/cm2;
    # As,estaca = 300/43,478 = 6,90 cm2.
    # phi = 20 mm, C25, boa aderencia, sem gancho:
    #   fctm = 0,3*25^(2/3) = 2,5650 MPa; fctk,inf = 0,7*fctm = 1,7955;
    #   fctd = 1,7955/1,4 = 1,2825 MPa; fbd = 2,25*1,0*1,0*1,2825 = 2,8856 MPa;
    #   lb = (phi/4)*(fyd/fbd) = (2,0/4)*(434,78/2,8856) = 75,34 cm.
    # h = 100, c = 3 -> l,disponivel = 97 cm >= 75,34 cm.
    r = BLO.ancoragem_estaca_tracionada(300.0, 100.0, 20.0, 25.0,
                                        cobrimento_cm=3.0)
    assert r.tracionada is True
    assert r.As_estaca_nec_cm2 == pytest.approx(300.0 / FYD_KNCM2, rel=1e-9)
    assert r.lb_nec_cm == pytest.approx(75.34, abs=0.05)
    assert r.comprimento_disponivel_cm == pytest.approx(97.0)
    assert r.ok is True


def test_estaca_tracionada_bloco_baixo_nao_ancora_mas_estribos_resolvem():
    # h = 70, c = 3 -> l,disponivel = 67 cm < lb,nec = 75,34 cm.
    r = BLO.ancoragem_estaca_tracionada(300.0, 70.0, 20.0, 25.0,
                                        cobrimento_cm=3.0)
    assert r.ok is False
    # 22.7.4.1.1: "Alternativamente, podem ser utilizados estribos que
    # garantam a transferencia da forca de tracao ate o topo do bloco."
    r2 = BLO.ancoragem_estaca_tracionada(300.0, 70.0, 20.0, 25.0,
                                         cobrimento_cm=3.0,
                                         estribos_de_transferencia=True)
    assert r2.ok is True
    assert "estribos" in r2.governante


def test_estaca_comprimida_nao_aciona_a_regra():
    r = BLO.ancoragem_estaca_tracionada(-500.0, 70.0, 20.0, 25.0)
    assert r.tracionada is False
    assert r.ok is True
    r0 = BLO.ancoragem_estaca_tracionada(0.0, 70.0, 20.0, 25.0)
    assert r0.tracionada is False
    assert r0.ok is True


def test_estaca_tracionada_lb_nec_confere_com_a_ancoragem_do_p21():
    esperado = anc.comprimento_ancoragem(phi_mm=20.0, fck_mpa=25.0).lb_nec_cm
    r = BLO.ancoragem_estaca_tracionada(300.0, 100.0, 20.0, 25.0)
    assert r.lb_nec_cm == pytest.approx(esperado, rel=1e-12)


def test_estaca_tracionada_entradas_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.ancoragem_estaca_tracionada(300.0, 0.0, 20.0, 25.0)
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.ancoragem_estaca_tracionada(300.0, 100.0, 20.0, 25.0,
                                        cobrimento_cm=-1.0)


# ---------------------------------------------------------------------------
# 22.7.4.1.2 -- armadura de distribuicao, 20 % das forcas de tracao (p. 214)
# ---------------------------------------------------------------------------
def test_As_distribuicao_bloco_20pct_das_forcas_de_tracao():
    # F,tracao,total = 1000 kN; fyd = 43,478 kN/cm2.
    # As,distribuicao = 0,20*1000/43,478 = 4,60 cm2.
    As = BLO.As_distribuicao_bloco_cm2(1000.0)
    assert As == pytest.approx(4.6, abs=1e-9)


def test_As_distribuicao_bloco_coincide_com_As_superior_dir():
    # A base pedida por 22.7.4.1.2 e "o total das forcas de tracao em cada
    # direcao". Quando a armadura principal foi dimensionada a fyd, vale
    # F = As,principal*fyd, e entao 0,20*F/fyd = 0,20*As,principal.
    As_p = 12.34
    F = As_p * FYD_KNCM2
    assert BLO.As_distribuicao_bloco_cm2(F) == pytest.approx(
        BLO.As_superior_dir(As_p), rel=1e-12)


def test_As_distribuicao_bloco_forca_nula_e_fracao_invalida():
    assert BLO.As_distribuicao_bloco_cm2(0.0) == pytest.approx(0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.As_distribuicao_bloco_cm2(-10.0)
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.As_distribuicao_bloco_cm2(1000.0, fracao=0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.As_distribuicao_bloco_cm2(1000.0, fracao=1.5)


# ---------------------------------------------------------------------------
# 22.7.4.1.3 -- condicoes de exigencia da armadura de suspensao (p. 215)
# ---------------------------------------------------------------------------
def test_suspensao_nao_exigida_com_os_20pct_da_22_7_4_1_2():
    # fracao = 0,20 <= 0,25 e espacamento 100 cm <= 3*50 = 150 cm.
    r = BLO.exigir_armadura_suspensao_bloco(0.20, 100.0, 50.0)
    assert r.espacamento_limite_cm == pytest.approx(150.0)
    assert r.por_distribuicao is False
    assert r.por_espacamento is False
    assert r.exige is False
    assert r.ok is True


@pytest.mark.parametrize("fracao, dispara", [
    (0.20, False),     # o valor de 22.7.4.1.2
    (0.25, False),     # 25 % exatos: "mais de 25 %" nao inclui o limite
    (0.2501, True),    # logo acima do degrau
    (0.40, True),      # bem acima
])
def test_suspensao_degrau_dos_25pct(fracao, dispara):
    r = BLO.exigir_armadura_suspensao_bloco(fracao, 100.0, 50.0,
                                            suspensao_prevista=True)
    assert r.por_distribuicao is dispara
    assert r.exige is dispara


@pytest.mark.parametrize("espacamento, dispara", [
    (100.0, False),    # bem abaixo de 3*h
    (150.0, False),    # 3*h exatos: "maior que tres vezes" nao inclui o limite
    (150.1, True),     # logo acima
    (300.0, True),     # bem acima
])
def test_suspensao_degrau_do_espacamento_3h(espacamento, dispara):
    # h,bloco = 50 cm -> 3*h = 150 cm (22.7.4.1.3: "espacamento entre estacas
    # maior que tres vezes a altura do bloco").
    r = BLO.exigir_armadura_suspensao_bloco(0.20, espacamento, 50.0,
                                            suspensao_prevista=True)
    assert r.por_espacamento is dispara
    assert r.exige is dispara


def test_suspensao_as_duas_condicoes_juntas_e_o_aviso():
    with pytest.warns(nbr.AvisoNBR6118):
        r = BLO.exigir_armadura_suspensao_bloco(0.30, 200.0, 50.0)
    assert r.por_distribuicao is True
    assert r.por_espacamento is True
    assert r.exige is True
    assert r.ok is False
    assert "25 %" in r.motivo and "3·h" in r.motivo
    r2 = BLO.exigir_armadura_suspensao_bloco(0.30, 200.0, 50.0,
                                             suspensao_prevista=True)
    assert r2.exige is True
    assert r2.ok is True


def test_suspensao_entradas_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.exigir_armadura_suspensao_bloco(-0.1, 100.0, 50.0)
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.exigir_armadura_suspensao_bloco(0.20, 0.0, 50.0)
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.exigir_armadura_suspensao_bloco(0.20, 100.0, 0.0)


# ---------------------------------------------------------------------------
# 22.7.4.1.4 -- altura do bloco para o arranque do pilar (PDF p. 215)
# ---------------------------------------------------------------------------
def test_altura_arranque_bloco_cita_o_item_do_bloco():
    # h = 90, c = 3 -> l,disponivel = 87 cm; lb,nec = 75,34 cm -> passa.
    r = BLO.altura_arranque_pilar_bloco(90.0, 75.34)
    assert r.item == "22.7.4.1.4"
    assert r.elemento == "bloco"
    assert r.comprimento_disponivel_cm == pytest.approx(87.0)
    assert r.ok is True


def test_altura_arranque_bloco_insuficiente_da_h_minimo():
    # h = 60, c = 3 -> l,disponivel = 57 cm < 75,34 cm; h,minimo = 78,34 cm.
    r = BLO.altura_arranque_pilar_bloco(60.0, 75.34)
    assert r.ok is False
    assert r.h_minima_cm == pytest.approx(78.34)


# ---------------------------------------------------------------------------
# 22.7.4.1.5 -- armadura lateral e superior (PDF p. 215)
# ---------------------------------------------------------------------------
def test_bloco_de_duas_estacas_exige_armadura_lateral_e_superior():
    # Duas estacas estao sempre em uma unica linha.
    r = BLO.armaduras_lateral_e_superior_bloco(2, 10.0)
    assert r.em_linha_unica is True
    assert r.obrigatoria is True
    assert r.As_superior_dir_cm2 == pytest.approx(2.0)     # 0,20*10
    assert r.Asp_pele_face_cm2 == pytest.approx(10.0 / 8.0)
    assert r.ok is True


def test_bloco_de_quatro_estacas_em_quadrado_nao_e_linha_unica():
    r = BLO.armaduras_lateral_e_superior_bloco(4, 10.0)
    assert r.em_linha_unica is False
    assert r.obrigatoria is False
    assert r.ok is True


def test_bloco_de_tres_estacas_alinhadas_exige_as_armaduras():
    # 22.7.4.1.5 fala em "duas ou mais estacas em uma unica linha".
    r = BLO.armaduras_lateral_e_superior_bloco(3, 10.0, em_linha_unica=True)
    assert r.obrigatoria is True


def test_bloco_de_uma_estaca_nao_dispara_a_obrigatoriedade():
    r = BLO.armaduras_lateral_e_superior_bloco(1, 10.0, em_linha_unica=True)
    assert r.obrigatoria is False


def test_armadura_lateral_obrigatoria_e_nao_prevista_avisa():
    with pytest.warns(nbr.AvisoNBR6118):
        r = BLO.armaduras_lateral_e_superior_bloco(2, 10.0,
                                                   armaduras_previstas=False)
    assert r.obrigatoria is True
    assert r.ok is False


def test_bloco_de_grande_volume_registra_armaduras_complementares():
    r = BLO.armaduras_lateral_e_superior_bloco(4, 10.0, grande_volume=True)
    assert r.grande_volume is True
    assert any("complementares" in linha for linha in r.memoria)


def test_armaduras_lateral_e_superior_entradas_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.armaduras_lateral_e_superior_bloco(0, 10.0)
    with pytest.raises(nbr.FaixaNormativaError):
        BLO.armaduras_lateral_e_superior_bloco(2, -1.0)


# ---------------------------------------------------------------------------
# projetar_bloco -- o detalhamento de 22.7 ligado ao resultado
# ---------------------------------------------------------------------------
def test_projetar_bloco_traz_o_detalhamento_de_22_7():
    # Exemplo 1 da apostila (2 estacas): Nk = 657,4 kN, e = 80 cm, pilar
    # 30 x 20, phi,estaca = 30 cm, h = 50 cm, C25.
    r = BLO.projetar_bloco(
        n_estacas=2, Nk_kn=657.4, e_cm=80.0, ap_cm=30.0, bp_cm=20.0,
        phi_e_cm=30.0, h_cm=50.0, fck_mpa=25.0, KR=0.95, cobrimento_cm=3.0,
    )
    # 22.7.2.1 a: faixa = 1,2*30 = 36 cm.
    assert r.faixa_armadura_estaca_cm == pytest.approx(36.0)
    # 22.7.4.1.2: F,tracao = As,principal*fyd e As,distribuicao = 20 % disso
    # sobre fyd -- ou seja, 0,20*As,principal.
    assert r.F_tracao_dir_kn == pytest.approx(r.As_principal_cm2 * FYD_KNCM2)
    assert r.As_distribuicao_dir_cm2 == pytest.approx(0.20 * r.As_principal_cm2)
    # 22.7.4.1.5: duas estacas -> linha unica -> obrigatoria.
    assert r.em_linha_unica is True
    assert r.armadura_lateral_superior_obrigatoria is True
    assert r.Asp_pele_face_cm2 == pytest.approx(r.As_principal_cm2 / 8.0)
    # 22.7.4.1.3: 0,20 <= 0,25 e e = 80 cm <= 3*50 = 150 cm -> nao exige.
    assert r.exige_suspensao is False
    assert r.motivo_suspensao == ""
    # 22.7.1: sem as dimensoes em planta do bloco, a rigidez fica indefinida.
    assert r.rigido_22_7_1 is None
    # o que ja existia nao muda (Blevot continua sendo o criterio).
    assert r.As_suspensao_cm2 == pytest.approx(
        BLO.As_suspensao_total(1.4 * 657.4, 2))


def test_projetar_bloco_dispara_a_suspensao_por_espacamento():
    # e = 200 cm > 3*h = 3*60 = 180 cm -> 22.7.4.1.3 exige suspensao.
    r = BLO.projetar_bloco(
        n_estacas=2, Nk_kn=657.4, e_cm=200.0, ap_cm=30.0, bp_cm=20.0,
        phi_e_cm=30.0, h_cm=60.0, fck_mpa=25.0,
    )
    assert r.exige_suspensao is True
    assert "3·h" in r.motivo_suspensao


def test_projetar_bloco_classifica_a_rigidez_quando_recebe_a_planta():
    # Bloco 200 x 90 cm, pilar 30 x 20, h = 50: (200 - 30)/3 = 56,67 > 50
    # -> flexivel (22.7.1).
    r = BLO.projetar_bloco(
        n_estacas=2, Nk_kn=657.4, e_cm=80.0, ap_cm=30.0, bp_cm=20.0,
        phi_e_cm=30.0, h_cm=50.0, fck_mpa=25.0,
        a_bloco_cm=200.0, b_bloco_cm=90.0,
    )
    assert r.rigido_22_7_1 is False
    r2 = BLO.projetar_bloco(
        n_estacas=2, Nk_kn=657.4, e_cm=80.0, ap_cm=30.0, bp_cm=20.0,
        phi_e_cm=30.0, h_cm=80.0, fck_mpa=25.0,
        a_bloco_cm=200.0, b_bloco_cm=90.0,
    )
    assert r2.rigido_22_7_1 is True


def test_projetar_bloco_quatro_estacas_nao_e_linha_unica():
    r = BLO.projetar_bloco(
        n_estacas=4, Nk_kn=3000.0, e_cm=200.0, ap_cm=40.0, bp_cm=40.0,
        phi_e_cm=40.0, h_cm=150.0, fck_mpa=30.0,
    )
    assert r.em_linha_unica is False
    assert r.armadura_lateral_superior_obrigatoria is False
    assert r.faixa_armadura_estaca_cm == pytest.approx(48.0)   # 1,2*40


# ---------------------------------------------------------------------------
# Texto ao usuario: memoria de calculo em portugues acentuado
# ---------------------------------------------------------------------------
def test_memorias_de_calculo_saem_acentuadas():
    textos = []
    textos.extend(SAP.verificar_hipotese_distribuicao_plana(
        50.0, 200.0, 50.0).memoria)
    textos.extend(SAP.detalhamento_flexao_sapata(15.01, 12.5, 205.0,
                                                 265.0).memoria)
    textos.extend(SAP.altura_arranque_suficiente(100.0, 60.0).memoria)
    textos.extend(BLO.classificar_bloco(100.0, 250.0, 50.0).memoria)
    textos.extend(BLO.verificar_85pct_nas_faixas(9.0, 10.0).memoria)
    textos.extend(BLO.exigir_armadura_suspensao_bloco(0.20, 100.0,
                                                      50.0).memoria)
    textos.extend(BLO.armaduras_lateral_e_superior_bloco(2, 10.0).memoria)
    junto = " ".join(textos)
    assert any(ch in junto for ch in "áâãéêíóôõúçÁÉÍÓÚ")
    for linha in textos:
        assert linha.strip().endswith((".", ":", "%")), linha
