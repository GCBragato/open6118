"""Testes do P36 -- consolos e dentes Gerber (22.5).

Valores esperados tirados da NBR 6118:2026 (PDF p. 206-211) e das contas nos
comentarios de cada teste. O modelo quantitativo de dimensionamento (braco
de alavanca z = 0,85*d, Rsd = Fd*a/z + Hd) e a aproximacao classica adotada
por consolos_nbr6118.py -- ver a docstring do modulo -- porque 22.5.1.3 e
22.5.2.3 sao descritivos na norma (nao ha formula fechada na imagem da
pagina).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import bielas_tirantes_nbr6118 as bt  # noqa: E402
import consolos_nbr6118 as cons  # noqa: E402
import limites_geometricos_nbr6118 as lim  # noqa: E402
import nucleo_nbr6118 as nbr  # noqa: E402


# ---------------------------------------------------------------------------
# 22.5.1.1 -- classificacao de consolo (PDF p. 206)
# ---------------------------------------------------------------------------
def test_classificar_consolo_limite_muito_curto_curto_a_igual_0_5d():
    # a = 0,5*d: a norma inclui esse limite em "curto" (0,5d <= a <= d)
    r = cons.classificar_consolo(a_cm=20.0, d_cm=40.0)
    assert r.classificacao == "curto"
    assert r.ok is True
    assert r.razao_a_d == pytest.approx(0.5)


def test_classificar_consolo_abaixo_do_limite_e_muito_curto():
    r = cons.classificar_consolo(a_cm=19.0, d_cm=40.0)
    assert r.classificacao == "muito_curto"
    assert r.ok is True


def test_classificar_consolo_limite_curto_viga_a_igual_d():
    # a = d: ainda consolo curto (0,5d <= a <= d é inclusivo em a = d)
    r = cons.classificar_consolo(a_cm=40.0, d_cm=40.0)
    assert r.classificacao == "curto"
    assert r.ok is True


def test_classificar_consolo_acima_de_d_e_viga_em_balanco():
    # a = 1,01*d -> nao e mais consolo (22.5.1.1: "a > d, tratar como viga em balanco")
    r = cons.classificar_consolo(a_cm=40.4, d_cm=40.0)
    assert r.classificacao == "viga_em_balanco"
    assert r.ok is False


def test_classificar_consolo_a_ou_d_nao_positivos_levantam_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        cons.classificar_consolo(a_cm=0.0, d_cm=40.0)
    with pytest.raises(nbr.FaixaNormativaError):
        cons.classificar_consolo(a_cm=10.0, d_cm=0.0)


# ---------------------------------------------------------------------------
# 22.5.1.2 c) -- abertura de carga, limite 1:2 (PDF p. 207)
# ---------------------------------------------------------------------------
def test_verificar_abertura_carga_largura_maxima():
    # a0 = 20 cm; profundidade = 10 cm -> largura_max = a0 + profundidade = 30 cm
    # (1:2 horizontal:vertical -> 5 cm de cada lado, 10 cm no total)
    r = cons.verificar_abertura_carga(a0_cm=20.0, profundidade_cm=10.0)
    assert r.largura_max_cm == pytest.approx(30.0)
    assert r.ok is True


def test_verificar_abertura_carga_profundidade_zero_nao_altera_largura():
    r = cons.verificar_abertura_carga(a0_cm=20.0, profundidade_cm=0.0)
    assert r.largura_max_cm == pytest.approx(20.0)


def test_verificar_abertura_carga_dentro_do_limite():
    r = cons.verificar_abertura_carga(a0_cm=20.0, profundidade_cm=10.0, largura_considerada_cm=30.0)
    assert r.ok is True


def test_verificar_abertura_carga_acima_do_limite_reprovado():
    # largura considerada (35) > largura maxima (30) -> reprovado
    r = cons.verificar_abertura_carga(a0_cm=20.0, profundidade_cm=10.0, largura_considerada_cm=35.0)
    assert r.ok is False
    assert r.largura_max_cm == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# 22.5.1.3 -- braco de alavanca e forca do tirante (PDF p. 208)
# ---------------------------------------------------------------------------
def test_braco_alavanca_consolo():
    assert cons.braco_alavanca_consolo_cm(40.0) == pytest.approx(34.0)  # 0,85*40


def test_rsd_tirante_consolo_sem_forca_horizontal():
    # Fd=100 kN, a=20 cm, z=34 cm, Hd=0 -> Rsd = 100*20/34 = 58,8235 kN
    Rsd = cons.Rsd_tirante_consolo_kn(Fd_kn=100.0, Hd_kn=0.0, a_cm=20.0, z_cm=34.0)
    assert Rsd == pytest.approx(100.0 * 20.0 / 34.0)


def test_rsd_tirante_consolo_com_forca_horizontal_soma_direto():
    # Hd soma direto (atua no nivel do tirante, sem braco de alavanca)
    Rsd = cons.Rsd_tirante_consolo_kn(Fd_kn=100.0, Hd_kn=15.0, a_cm=20.0, z_cm=34.0)
    assert Rsd == pytest.approx(100.0 * 20.0 / 34.0 + 15.0)


# ---------------------------------------------------------------------------
# 22.5.1.4.1 -- restricao ao gancho vertical (PDF p. 208)
# ---------------------------------------------------------------------------
def test_gancho_vertical_permitido_consolo_continuo_largo_com_cargas_pequenas():
    # b=200 cm; 4*(a+a0) = 4*(25+15) = 160 cm; b > 160 -> largura ok
    r = cons.verificar_gancho_vertical_consolo(
        b_cm=200.0, a_cm=25.0, a0_cm=15.0,
        consolo_continuo=True, cargas_horizontais_verticais_pequenas=True,
    )
    assert r.limite_b_cm == pytest.approx(160.0)
    assert r.permitido is True
    assert r.ok is True


def test_gancho_vertical_proibido_se_b_nao_supera_4_vezes_a_mais_a0():
    # b=100 cm <= 160 cm -> largura reprovada -> gancho proibido mesmo continuo
    r = cons.verificar_gancho_vertical_consolo(
        b_cm=100.0, a_cm=25.0, a0_cm=15.0,
        consolo_continuo=True, cargas_horizontais_verticais_pequenas=True,
    )
    assert r.permitido is False


def test_gancho_vertical_proibido_se_nao_continuo_mesmo_com_b_grande():
    r = cons.verificar_gancho_vertical_consolo(
        b_cm=200.0, a_cm=25.0, a0_cm=15.0,
        consolo_continuo=False, cargas_horizontais_verticais_pequenas=True,
    )
    assert r.permitido is False


def test_gancho_vertical_proibido_se_cargas_nao_forem_pequenas():
    r = cons.verificar_gancho_vertical_consolo(
        b_cm=200.0, a_cm=25.0, a0_cm=15.0,
        consolo_continuo=True, cargas_horizontais_verticais_pequenas=False,
    )
    assert r.permitido is False


def test_gancho_vertical_limite_exato_b_igual_4_a_mais_a0_e_reprovado():
    # b = 4*(a+a0) exatamente -> "b > 4*(a+a0)" nao e satisfeito (desigualdade estrita)
    r = cons.verificar_gancho_vertical_consolo(
        b_cm=160.0, a_cm=25.0, a0_cm=15.0,
        consolo_continuo=True, cargas_horizontais_verticais_pequenas=True,
    )
    assert r.permitido is False


# ---------------------------------------------------------------------------
# 22.5.1.4.3 -- armadura de costura minima (PDF p. 209)
# ---------------------------------------------------------------------------
def test_as_costura_minima_40_por_cento_exato():
    # As,tirante = 6 cm2 -> As,costura,min = 0,40*6 = 2,4 cm2 (teste sugerido do plano)
    assert cons.As_costura_min_cm2(6.0) == pytest.approx(2.4)


def test_as_costura_minima_zero_para_tirante_zero():
    assert cons.As_costura_min_cm2(0.0) == pytest.approx(0.0)


def test_as_costura_minima_negativa_levanta_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        cons.As_costura_min_cm2(-1.0)


# ---------------------------------------------------------------------------
# 22.5.1.4.4 -- armadura de suspensao do consolo, carga indireta (PDF p. 209)
# ---------------------------------------------------------------------------
def test_as_suspensao_consolo_formula():
    # Fd,indireta = 50 kN; fyd = 43,478 kN/cm2 (CA-50) -> As = 50/43,478 = 1,15 cm2
    fyd_kncm2 = nbr.mpa_para_kncm2(nbr.fyd(500.0, nbr.GAMA_S))
    As = cons.As_suspensao_consolo_cm2(50.0, fyd_kncm2)
    assert As == pytest.approx(50.0 / fyd_kncm2)
    assert As == pytest.approx(1.15, abs=1e-2)


def test_as_suspensao_consolo_sem_carga_indireta_e_zero():
    fyd_kncm2 = nbr.mpa_para_kncm2(nbr.fyd(500.0, nbr.GAMA_S))
    assert cons.As_suspensao_consolo_cm2(0.0, fyd_kncm2) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 22.5.2.4.2 -- armadura de suspensao do dente Gerber (PDF p. 211)
# ---------------------------------------------------------------------------
def test_as_suspensao_dente_gerber_formula():
    # Fd = 240 kN (ja com gama_n aplicado); fyd = 43,478 kN/cm2 -> As = 240/43,478 = 5,52 cm2
    fyd_kncm2 = nbr.mpa_para_kncm2(nbr.fyd(500.0, nbr.GAMA_S))
    As = cons.As_suspensao_dente_cm2(240.0, fyd_kncm2)
    assert As == pytest.approx(240.0 / fyd_kncm2)
    assert As == pytest.approx(5.52, abs=1e-2)


# ---------------------------------------------------------------------------
# 22.5.1.3 a 22.5.1.4.4 -- dimensionar_consolo, exemplo a mao (PDF p. 206-209)
# ---------------------------------------------------------------------------
def test_dimensionar_consolo_exemplo_a_mao_modelo_biela_tirante():
    # Consolo curto: Fd=200 kN, Hd=30 kN, a=25 cm, d=40 cm (a/d=0,625 -> curto),
    # b=20 cm, h=45 cm, C30, CA-50.
    #
    # gama_n (22.2, P10) = 1,2 -> Fd,amp = 200*1,2 = 240 kN; Hd,amp = 30*1,2 = 36 kN.
    # z = 0,85*40 = 34 cm.
    # Rsd = 240*25/34 + 36 = 176,4706 + 36 = 212,4706 kN.
    # fyd (CA-50) = 500/1,15 = 434,7826 MPa = 43,4783 kN/cm2.
    # As,tirante = 212,4706/43,4783 = 4,8868 cm2.
    # As,min (17.3.5.2, viga ficticia 20x45 cm, d=40, C30) = 1,35 cm2 (nucleo).
    # As = max(4,8868; 1,35) = 4,8868 cm2 -> governa o tirante.
    # As,costura,min = 0,40*4,8868 = 1,9547 cm2, em (2/3)*40 = 26,6667 cm.
    Fd, Hd, a, d, b, h, fck, fyk = 200.0, 30.0, 25.0, 40.0, 20.0, 45.0, 30.0, 500.0
    r = cons.dimensionar_consolo(Fd, Hd, a, d, b, h, fck, fyk)

    assert r.classificacao == "curto"
    assert r.gama_n == pytest.approx(1.2)
    assert r.Fd_amp_kn == pytest.approx(240.0)
    assert r.Hd_amp_kn == pytest.approx(36.0)
    assert r.z_cm == pytest.approx(34.0)
    assert r.Rsd_kn == pytest.approx(240.0 * 25.0 / 34.0 + 36.0)
    assert r.As_tirante_cm2 == pytest.approx(4.8868, abs=1e-3)
    assert r.As_min_cm2 == pytest.approx(1.35, abs=1e-2)
    assert r.As_cm2 == pytest.approx(r.As_tirante_cm2)  # o tirante governa
    assert r.As_costura_min_cm2 == pytest.approx(0.4 * r.As_cm2)
    assert r.altura_costura_cm == pytest.approx(40.0 * 2.0 / 3.0)
    assert r.ok is True
    assert r.gancho_vertical is None  # a0_cm nao informado


def test_dimensionar_consolo_as_min_governa_quando_tirante_e_pequeno():
    # Consolo com forca pequena: As,tirante fica abaixo de As,min (17.3.5.2)
    r = cons.dimensionar_consolo(
        Fd_kn=5.0, Hd_kn=0.0, a_cm=15.0, d_cm=40.0, b_cm=25.0, h_cm=50.0,
        fck_mpa=25.0, fyk_mpa=500.0,
    )
    assert r.As_tirante_cm2 < r.As_min_cm2
    assert r.As_cm2 == pytest.approx(r.As_min_cm2)


def test_dimensionar_consolo_gama_n_explicito_sobrescreve_padrao():
    r_padrao = cons.dimensionar_consolo(100.0, 0.0, 20.0, 40.0, 25.0, 50.0, 25.0, 500.0)
    r_1 = cons.dimensionar_consolo(100.0, 0.0, 20.0, 40.0, 25.0, 50.0, 25.0, 500.0, gama_n=1.0)
    assert r_padrao.gama_n == pytest.approx(lim.gama_n_consolo_gerber())
    assert r_1.gama_n == pytest.approx(1.0)
    assert r_1.Fd_amp_kn == pytest.approx(100.0)
    assert r_1.Rsd_kn < r_padrao.Rsd_kn


def test_dimensionar_consolo_expoe_fcd1_fcd3_como_referencia():
    r = cons.dimensionar_consolo(100.0, 0.0, 20.0, 40.0, 25.0, 50.0, 25.0, 500.0)
    assert r.fcd1_kncm2 == pytest.approx(bt.fcd1_kncm2(25.0))
    assert r.fcd3_kncm2 == pytest.approx(bt.fcd3_kncm2(25.0))


def test_dimensionar_consolo_a_maior_que_d_levanta_erro_nao_e_consolo():
    with pytest.raises(nbr.FaixaNormativaError):
        cons.dimensionar_consolo(100.0, 0.0, a_cm=41.0, d_cm=40.0, b_cm=25.0,
                                  h_cm=50.0, fck_mpa=25.0, fyk_mpa=500.0)


def test_dimensionar_consolo_modelo_atrito_nao_implementado():
    with pytest.raises(NotImplementedError):
        cons.dimensionar_consolo(100.0, 0.0, 20.0, 40.0, 25.0, 50.0, 25.0, 500.0,
                                  modelo="atrito")


def test_dimensionar_consolo_modelo_desconhecido_levanta_value_error():
    with pytest.raises(ValueError):
        cons.dimensionar_consolo(100.0, 0.0, 20.0, 40.0, 25.0, 50.0, 25.0, 500.0,
                                  modelo="outro")


def test_dimensionar_consolo_com_carga_indireta_dimensiona_suspensao():
    fyd_kncm2 = nbr.mpa_para_kncm2(nbr.fyd(500.0, nbr.GAMA_S))
    r = cons.dimensionar_consolo(
        100.0, 0.0, 20.0, 40.0, 25.0, 50.0, 25.0, 500.0, Fd_indireta_kn=50.0,
    )
    assert r.As_suspensao_cm2 == pytest.approx(50.0 / fyd_kncm2)


def test_dimensionar_consolo_sem_carga_indireta_suspensao_e_zero():
    r = cons.dimensionar_consolo(100.0, 0.0, 20.0, 40.0, 25.0, 50.0, 25.0, 500.0)
    assert r.As_suspensao_cm2 == pytest.approx(0.0)


def test_dimensionar_consolo_com_a0_avalia_gancho_vertical():
    r = cons.dimensionar_consolo(
        100.0, 0.0, 20.0, 40.0, 200.0, 50.0, 25.0, 500.0,
        a0_cm=10.0, consolo_continuo=True,
        cargas_horizontais_verticais_pequenas=True,
    )
    assert r.gancho_vertical is not None
    assert r.gancho_vertical.permitido is True


# ---------------------------------------------------------------------------
# 22.5.2.3 e 22.5.2.4.2 -- dimensionar_dente_gerber (PDF p. 210-211)
# ---------------------------------------------------------------------------
def test_dimensionar_dente_gerber_reaproveita_consolo_e_soma_suspensao():
    Fd, Hd, a, d, b, h, fck, fyk = 200.0, 30.0, 25.0, 40.0, 20.0, 45.0, 30.0, 500.0
    consolo = cons.dimensionar_consolo(Fd, Hd, a, d, b, h, fck, fyk, Fd_indireta_kn=0.0)
    gerber = cons.dimensionar_dente_gerber(Fd, Hd, a, d, b, h, fck, fyk)

    assert gerber.consolo.Rsd_kn == pytest.approx(consolo.Rsd_kn)
    assert gerber.consolo.As_tirante_cm2 == pytest.approx(consolo.As_tirante_cm2)
    assert gerber.consolo.As_suspensao_cm2 == pytest.approx(0.0)  # 22.5.2.4.1: nao se aplica
    # 22.5.2.4.2: As,susp = Fd,amp/fyd, sempre exigida (independe de carga indireta)
    fyd_kncm2 = nbr.mpa_para_kncm2(nbr.fyd(fyk, nbr.GAMA_S))
    assert gerber.As_suspensao_dente_cm2 == pytest.approx(consolo.Fd_amp_kn / fyd_kncm2)
    assert gerber.As_suspensao_dente_cm2 > 0.0
    assert gerber.ok is True
    assert gerber.governante == "22.5.2.3"


def test_dimensionar_dente_gerber_a_maior_que_d_levanta_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        cons.dimensionar_dente_gerber(100.0, 0.0, a_cm=41.0, d_cm=40.0, b_cm=25.0,
                                       h_cm=50.0, fck_mpa=25.0, fyk_mpa=500.0)
