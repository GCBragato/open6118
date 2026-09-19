# -*- coding: utf-8 -*-
"""Testes do P33 — Lajes protendidas: detalhamento (ABNT NBR 6118:2026, 20.3.2).

Cada teste cita o item da norma e a página do PDF (a impressa é PDF - 18).
Fonte das fórmulas: SCRATCH\\nbr_png\\p194.png, p195.png, p196.png.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dimensionamento"))

import pytest

import detalhamento_lajes_nbr6118 as dl


TOL = 1e-9


# ---------------------------------------------------------------------------
# 20.3.2.1 — espacamento_max_cabos_cm (PDF p. 194): s_max = min(6h, 120cm)
# ---------------------------------------------------------------------------
def test_espacamento_max_cabos_h25_governa_120cm():
    # h=25cm -> 6h=150cm > 120cm, logo s_max=120cm (teste sugerido do plano)
    assert dl.espacamento_max_cabos_cm(25.0) == pytest.approx(120.0, abs=TOL)


def test_espacamento_max_cabos_h15_governa_6h():
    # h=15cm -> 6h=90cm < 120cm, logo s_max=90cm (teste sugerido do plano)
    assert dl.espacamento_max_cabos_cm(15.0) == pytest.approx(90.0, abs=TOL)


def test_espacamento_max_cabos_fronteira_120cm():
    # h=20cm -> 6h=120cm exatamente: as duas bordas do min() coincidem
    assert dl.espacamento_max_cabos_cm(20.0) == pytest.approx(120.0, abs=TOL)


def test_espacamento_max_cabos_ponto_interior():
    # h=18cm -> 6h=108cm < 120cm
    assert dl.espacamento_max_cabos_cm(18.0) == pytest.approx(108.0, abs=TOL)


def test_espacamento_max_cabos_h_invalido():
    with pytest.raises(ValueError):
        dl.espacamento_max_cabos_cm(0.0)
    with pytest.raises(ValueError):
        dl.espacamento_max_cabos_cm(-1.0)


# ---------------------------------------------------------------------------
# 20.3.2.1 — verificar_compressao_media (PDF p. 194):
# sigma_cp,media = P/Ac (x10 para MPa) >= 1,0 MPa, apos todas as perdas
# ---------------------------------------------------------------------------
def test_compressao_media_no_limite_1mpa_ok():
    # sigma_cp = P/Ac * 10 = 1,0 MPa -> P/Ac = 0,1 kN/cm2 -> P=100kN, Ac=1000cm2
    r = dl.verificar_compressao_media(P_kn=100.0, Ac_cm2=1000.0)
    assert r.sigma_cp_media_mpa == pytest.approx(1.0, abs=1e-6)
    assert r.ok is True


def test_compressao_media_abaixo_0_99mpa_reprovado():
    # sigma_cp = 99 kN / 1000 cm2 * 10 = 0,99 MPa < 1,0 MPa
    r = dl.verificar_compressao_media(P_kn=99.0, Ac_cm2=1000.0)
    assert r.sigma_cp_media_mpa == pytest.approx(0.99, abs=1e-6)
    assert r.ok is False


def test_compressao_media_ponto_interior_acima_do_minimo():
    # P=200kN, Ac=1000cm2 -> sigma_cp = 2,0 MPa >= 1,0 MPa
    r = dl.verificar_compressao_media(P_kn=200.0, Ac_cm2=1000.0)
    assert r.sigma_cp_media_mpa == pytest.approx(2.0, abs=1e-6)
    assert r.ok is True


def test_compressao_media_Ac_invalido():
    with pytest.raises(ValueError):
        dl.verificar_compressao_media(P_kn=100.0, Ac_cm2=0.0)


def test_compressao_media_P_negativo_invalido():
    with pytest.raises(ValueError):
        dl.verificar_compressao_media(P_kn=-1.0, Ac_cm2=1000.0)


# ---------------------------------------------------------------------------
# 20.3.2.2 — largura_max_faixa_externa_cm (PDF p. 195, Figura 20.3):
# largura_max = a + lados*3,5h
# ---------------------------------------------------------------------------
def test_largura_max_faixa_externa_pilar_interno_teste_do_plano():
    # pilar 40cm, h=20cm, lados=2 (padrão) -> 40+2*3,5*20=180cm
    assert dl.largura_max_faixa_externa_cm(40.0, 20.0) == pytest.approx(180.0, abs=TOL)


def test_largura_max_faixa_externa_pilar_borda_um_lado():
    # Figura 20.3: pilar de borda, só um lado recebe o acrescimo -> a+3,5h
    # a=40cm, h=20cm -> 40+3,5*20=110cm
    assert dl.largura_max_faixa_externa_cm(40.0, 20.0, lados=1) == pytest.approx(110.0, abs=TOL)


def test_largura_max_faixa_externa_ponto_interior():
    # a=60cm, h=25cm, lados=2 -> 60+2*3,5*25=235cm
    assert dl.largura_max_faixa_externa_cm(60.0, 25.0) == pytest.approx(235.0, abs=TOL)


def test_largura_max_faixa_externa_lados_invalido():
    with pytest.raises(ValueError):
        dl.largura_max_faixa_externa_cm(40.0, 20.0, lados=3)
    with pytest.raises(ValueError):
        dl.largura_max_faixa_externa_cm(40.0, 20.0, lados=0)


def test_largura_max_faixa_externa_dimensoes_invalidas():
    with pytest.raises(ValueError):
        dl.largura_max_faixa_externa_cm(0.0, 20.0)
    with pytest.raises(ValueError):
        dl.largura_max_faixa_externa_cm(40.0, -1.0)


# ---------------------------------------------------------------------------
# 20.3.2.3 — espacamento_min_cabos_cm (PDF p. 195): 5 cm
# ---------------------------------------------------------------------------
def test_espacamento_min_cabos_cm():
    assert dl.espacamento_min_cabos_cm() == pytest.approx(5.0, abs=TOL)


# ---------------------------------------------------------------------------
# 20.3.2.4 — cobrimento_cabo_abertura_min_cm (PDF p. 195): 7,5 cm
# ---------------------------------------------------------------------------
def test_cobrimento_cabo_abertura_min_cm():
    assert dl.cobrimento_cabo_abertura_min_cm() == pytest.approx(7.5, abs=TOL)


# ---------------------------------------------------------------------------
# 20.3.2.5 — desvio_max_planta (PDF p. 195): inclinacao = delta_y/delta_x <= 1/10
# ---------------------------------------------------------------------------
def test_desvio_max_planta_no_limite_ok():
    # delta_y/delta_x = 1/10 exatamente -> ok (fronteira)
    r = dl.desvio_max_planta(delta_x_cm=100.0, delta_y_cm=10.0)
    assert r.inclinacao == pytest.approx(0.10, abs=TOL)
    assert r.ok is True


def test_desvio_max_planta_acima_do_limite_reprovado():
    # delta_y/delta_x = 11/100 = 0,11 > 0,10
    r = dl.desvio_max_planta(delta_x_cm=100.0, delta_y_cm=11.0)
    assert r.inclinacao == pytest.approx(0.11, abs=TOL)
    assert r.ok is False


def test_desvio_max_planta_abaixo_do_limite_ok():
    # delta_y/delta_x = 5/100 = 0,05 < 0,10
    r = dl.desvio_max_planta(delta_x_cm=100.0, delta_y_cm=5.0)
    assert r.inclinacao == pytest.approx(0.05, abs=TOL)
    assert r.ok is True


def test_desvio_max_planta_nao_levanta_erro_quando_excede():
    # excede o limite mas a norma não veda: exige armadura extra, não erro
    r = dl.desvio_max_planta(delta_x_cm=50.0, delta_y_cm=10.0)
    assert r.ok is False
    assert "armadura" in r.governante.lower()


def test_desvio_max_planta_delta_x_invalido():
    with pytest.raises(ValueError):
        dl.desvio_max_planta(delta_x_cm=0.0, delta_y_cm=1.0)


# ---------------------------------------------------------------------------
# 20.3.2.5 — distancia_min_cabos_curva_cm (PDF p. 195): 5 cm
# ---------------------------------------------------------------------------
def test_distancia_min_cabos_curva_cm():
    assert dl.distancia_min_cabos_curva_cm() == pytest.approx(5.0, abs=TOL)


# ---------------------------------------------------------------------------
# 20.3.2.6 — cabos_min_sobre_pilar (PDF p. 196): 2 por direcao ortogonal
# ---------------------------------------------------------------------------
def test_cabos_min_sobre_pilar():
    assert dl.cabos_min_sobre_pilar() == 2


# ---------------------------------------------------------------------------
# 20.3.2.6 — armadura_apoio_laje_protendida (PDF p. 196):
# n_barras>=4; largura_faixa<=largura_apoio+2*1,5h; s_max=30cm;
# extensao_min=vao_livre/6
# ---------------------------------------------------------------------------
def test_armadura_apoio_teste_do_plano_apenas_n_barras():
    # apoio 40cm, h=20cm -> largura_faixa_max=40+2*1,5*20=100cm;
    # vao_livre=500cm -> extensao_min=500/6=83,333...cm
    r = dl.armadura_apoio_laje_protendida(
        n_barras=4, largura_apoio_cm=40.0, h_cm=20.0, vao_livre_cm=500.0,
    )
    assert r.largura_faixa_max_cm == pytest.approx(100.0, abs=TOL)
    assert r.extensao_min_cm == pytest.approx(500.0 / 6.0, abs=TOL)
    assert r.ok is True


def test_armadura_apoio_n_barras_abaixo_do_minimo_reprovado():
    r = dl.armadura_apoio_laje_protendida(
        n_barras=3, largura_apoio_cm=40.0, h_cm=20.0, vao_livre_cm=500.0,
    )
    assert r.ok is False
    assert "número mínimo" in r.governante


def test_armadura_apoio_n_barras_no_minimo_ok():
    r = dl.armadura_apoio_laje_protendida(
        n_barras=4, largura_apoio_cm=40.0, h_cm=20.0, vao_livre_cm=500.0,
    )
    assert r.ok is True


def test_armadura_apoio_largura_faixa_adotada_no_limite_ok():
    r = dl.armadura_apoio_laje_protendida(
        n_barras=4, largura_apoio_cm=40.0, h_cm=20.0, vao_livre_cm=500.0,
        largura_faixa_adotada_cm=100.0,
    )
    assert r.ok is True


def test_armadura_apoio_largura_faixa_adotada_acima_reprovado():
    r = dl.armadura_apoio_laje_protendida(
        n_barras=4, largura_apoio_cm=40.0, h_cm=20.0, vao_livre_cm=500.0,
        largura_faixa_adotada_cm=100.01,
    )
    assert r.ok is False
    assert "largura" in r.governante


def test_armadura_apoio_espacamento_adotado_no_limite_ok():
    r = dl.armadura_apoio_laje_protendida(
        n_barras=4, largura_apoio_cm=40.0, h_cm=20.0, vao_livre_cm=500.0,
        s_adotado_cm=30.0,
    )
    assert r.ok is True


def test_armadura_apoio_espacamento_adotado_acima_reprovado():
    r = dl.armadura_apoio_laje_protendida(
        n_barras=4, largura_apoio_cm=40.0, h_cm=20.0, vao_livre_cm=500.0,
        s_adotado_cm=30.01,
    )
    assert r.ok is False
    assert "espaçamento" in r.governante


def test_armadura_apoio_extensao_adotada_no_limite_ok():
    r = dl.armadura_apoio_laje_protendida(
        n_barras=4, largura_apoio_cm=40.0, h_cm=20.0, vao_livre_cm=500.0,
        extensao_adotada_cm=500.0 / 6.0,
    )
    assert r.ok is True


def test_armadura_apoio_extensao_adotada_abaixo_reprovado():
    r = dl.armadura_apoio_laje_protendida(
        n_barras=4, largura_apoio_cm=40.0, h_cm=20.0, vao_livre_cm=500.0,
        extensao_adotada_cm=80.0,
    )
    assert r.ok is False
    assert "extensão" in r.governante


def test_armadura_apoio_dimensoes_invalidas():
    with pytest.raises(ValueError):
        dl.armadura_apoio_laje_protendida(
            n_barras=4, largura_apoio_cm=0.0, h_cm=20.0, vao_livre_cm=500.0,
        )
    with pytest.raises(ValueError):
        dl.armadura_apoio_laje_protendida(
            n_barras=4, largura_apoio_cm=40.0, h_cm=20.0, vao_livre_cm=0.0,
        )


# ---------------------------------------------------------------------------
# 20.3.2.6 — max_monocordoalhas_feixe (PDF p. 196): 4
# ---------------------------------------------------------------------------
def test_max_monocordoalhas_feixe():
    assert dl.max_monocordoalhas_feixe() == 4
