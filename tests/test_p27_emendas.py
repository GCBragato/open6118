"""Testes do P27 -- Emendas, feixes, telas e dispositivos mecânicos
(NBR 6118:2026, 9.4.3, 9.4.4, 9.4.7, 9.4.7.1, 9.5.2 a 9.5.4).

Valores esperados tirados das imagens das páginas do PDF (SCRATCH/nbr_png):
p057 (9.4.2.4 a 9.4.2.6.1), p058 (9.4.3, 9.4.4), p061 (9.4.7, 9.4.7.1),
p062 (9.5.2, 9.5.2.1, Figura 9.4), p063 (Tabela 9.3, 9.5.2.2), p064
(9.5.2.4, Figura 9.5, 9.5.2.5), p065-p066 (9.5.3, 9.5.4, Figura 9.6).

Conta de referência usada em vários testes (CA-50, C25, boa aderência,
γc = 1,4, γs = 1,15):
    fctd = 0,7·0,3·25^(2/3)/1,4 = 1,28249 MPa
    fbd  = 2,25·1,0·1,0·1,28249 = 2,88561 MPa
    fyd  = 500/1,15 = 434,783 MPa
    lb   = φ/4·fyd/fbd = φ·37,6684 (mm, com φ em mm)
"""

import math
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import ancoragem_nbr6118 as A  # noqa: E402
import emendas_nbr6118 as E  # noqa: E402

FCTD_C25 = 0.7 * 0.3 * 25.0 ** (2.0 / 3.0) / 1.4
FBD_C25 = 2.25 * FCTD_C25
FYD_50 = 500.0 / 1.15


def lb_c25_cm(phi_mm, eta3=1.0):
    """lb = φ/4·fyd/fbd, em cm (9.4.2.4, p. 57)."""
    return phi_mm / 4.0 * FYD_50 / (FBD_C25 * eta3) / 10.0


def area_cm2(phi_mm):
    return math.pi * (phi_mm / 10.0) ** 2 / 4.0


# ===========================================================================
# 9.4.3 -- Feixes (PDF p. 58)
# ===========================================================================
def test_943_phi_n_formula():
    """φn = φf·√n: n = 4, φf = 20 mm -> 40 mm; n = 3, φf = 16 -> 27,71."""
    assert E.phi_n_feixe_mm(20.0, 4) == pytest.approx(40.0)
    assert E.phi_n_feixe_mm(16.0, 3) == pytest.approx(16.0 * math.sqrt(3.0))
    with pytest.raises(ValueError):
        E.phi_n_feixe_mm(16.0, 1)


def test_943_a_fronteira_25mm_exato_barra_unica():
    """φf = 12,5 mm, n = 4 -> φn = 25,0 mm exato: caso a) (<= 25 mm),
    barra única de diâmetro 25 mm. lb = 25·37,6684 = 941,7 mm = 94,17 cm."""
    r = E.ancoragem_feixe(12.5, 4, 25.0)
    assert r.phi_n_mm == pytest.approx(25.0)
    assert r.caso == "a"
    assert r.phi_calculo_mm == pytest.approx(25.0)
    assert r.lb_cm == pytest.approx(lb_c25_cm(25.0), rel=1e-9)
    assert r.afastamento_min_extremidades_cm is None
    assert r.armadura_transversal is None


def test_943_b_acima_de_25mm_barra_isolada_afastamento_1_2_lb():
    """φf = 16 mm, n = 3 -> φn = 27,7 mm > 25: caso b), cada barra ancorada
    isoladamente; lb,nec(16) = 16·37,6684 = 602,7 mm = 60,27 cm;
    afastamento >= 1,2·60,27 = 72,32 cm."""
    r = E.ancoragem_feixe(16.0, 3, 25.0)
    assert r.caso == "b"
    assert r.phi_calculo_mm == 16.0
    lb16 = lb_c25_cm(16.0)
    assert r.lb_nec_cm == pytest.approx(lb16, rel=1e-9)
    assert r.afastamento_min_extremidades_cm == pytest.approx(1.2 * lb16, rel=1e-9)


def test_943_b_logo_acima_de_25():
    """φf = 12,51 mm, n = 4 -> φn = 25,02 mm > 25: já é caso b)."""
    r = E.ancoragem_feixe(12.51, 4, 25.0)
    assert r.caso == "b"


def test_943_c_construtivo_phi_n_menor_32():
    """Caso c) com φn = 27,7 mm < 32: barra única φn e armadura transversal
    de 9.4.2.6.1: Ast = 0,25·As,feixe = 0,25·3·π·1,6²/4 = 1,508 cm²."""
    r = E.ancoragem_feixe(16.0, 3, 25.0, afastamento_possivel=False)
    assert r.caso == "c"
    phi_n = 16.0 * math.sqrt(3.0)
    assert r.lb_cm == pytest.approx(lb_c25_cm(phi_n), rel=1e-9)
    ast = r.armadura_transversal
    assert ast.governante.startswith("9.4.2.6.1")
    assert ast.Ast_min_cm2 == pytest.approx(0.25 * 3 * area_cm2(16.0), rel=1e-9)


def test_943_c_construtivo_phi_n_maior_32():
    """Caso c) com φf = 20, n = 3 -> φn = 34,64 >= 32: 9.4.2.6.2 (duas
    direções, s <= 5·φn); η3 = (132 − 34,64)/100 = 0,9736; comprimida:
    barra a 4·φn = 13,86 cm além da extremidade."""
    r = E.ancoragem_feixe(20.0, 3, 25.0, afastamento_possivel=False,
                          barra_comprimida=True)
    phi_n = 20.0 * math.sqrt(3.0)
    assert r.caso == "c"
    eta3 = (132.0 - phi_n) / 100.0
    assert r.lb_cm == pytest.approx(lb_c25_cm(phi_n, eta3), rel=1e-9)
    ast = r.armadura_transversal
    assert ast.duas_direcoes is True
    assert ast.Ast_min_cm2 is None
    assert ast.espacamento_max_cm == pytest.approx(5.0 * phi_n / 10.0)
    assert ast.barra_adicional_alem_extremidade_cm == pytest.approx(4.0 * phi_n / 10.0)


def test_943_afastamento_irrelevante_ate_25():
    """Com φn <= 25 mm, afastamento_possivel não muda nada (caso a)."""
    r = E.ancoragem_feixe(12.5, 4, 25.0, afastamento_possivel=False)
    assert r.caso == "a"


# ===========================================================================
# 9.4.4 -- Telas soldadas (PDF p. 58)
# ===========================================================================
def test_944_n_fios():
    """n >= 4·As,calc/As,ef: 0,8 -> 3,2 -> 4 fios; 0,75 -> 3,0 -> 3 (borda);
    0,76 -> 3,04 -> 4; 1,0 -> 4."""
    assert E.n_fios_transversais_tela_min(0.8, 1.0) == pytest.approx(3.2)
    assert E.n_fios_transversais_tela(0.8, 1.0) == 4
    assert E.n_fios_transversais_tela(3.0, 4.0) == 3
    assert E.n_fios_transversais_tela(0.76, 1.0) == 4
    assert E.n_fios_transversais_tela(2.0, 2.0) == 4
    assert E.n_fios_transversais_tela(0.0, 2.0) == 0


def test_944_fora_da_faixa():
    """As,calc > As,ef: fora da faixa."""
    with pytest.raises(nbr.FaixaNormativaError):
        E.n_fios_transversais_tela(1.01, 1.0)
    with pytest.raises(ValueError):
        E.n_fios_transversais_tela(1.0, 0.0)


# ===========================================================================
# 9.4.7 -- Dispositivos mecânicos (PDF p. 61)
# ===========================================================================
def test_947_limites_exatos_passam():
    """Fu = 100 kN: 0,1 mm a 70 %, 0,5 mm a 95 % e Rd = 50 kN (0,5·Fu)."""
    r = E.verificar_dispositivo_mecanico(100.0, 0.1, 0.5, 50.0)
    assert r.ok and r.Rd_max_kn == pytest.approx(50.0)


@pytest.mark.parametrize("s70,s95,rd,campo", [
    (0.1001, 0.5, 50.0, "ok_escorregamento_70"),
    (0.1, 0.5001, 50.0, "ok_escorregamento_95"),
    (0.1, 0.5, 50.01, "ok_resistencia"),
])
def test_947_acima_do_limite_reprova(s70, s95, rd, campo):
    r = E.verificar_dispositivo_mecanico(100.0, s70, s95, rd)
    assert r.ok is False and getattr(r, campo) is False


def test_947_fadiga_70pct():
    """Com fadiga: Rd <= 0,7·Fu (Fu do ensaio de fadiga) = 70 kN."""
    assert E.verificar_dispositivo_mecanico(100.0, 0.0, 0.0, 70.0, fadiga=True).ok
    assert not E.verificar_dispositivo_mecanico(100.0, 0.0, 0.0, 70.1, fadiga=True).ok


# ===========================================================================
# 9.4.7.1 -- Barra transversal única (PDF p. 61)
# ===========================================================================
def test_9471_phi_limitado_por_dimensao():
    """Menor dimensão 12 cm -> 120/6 = 20 mm < 25: φ = 20 ok, 20,5 não;
    espaçamento <= 20·φ = 40 cm."""
    r = E.barra_transversal_unica(20.0, 20.0, 12.0, 40.0)
    assert r.ok and r.phi_max_mm == pytest.approx(20.0)
    assert r.espacamento_max_cm == pytest.approx(40.0)
    assert not E.barra_transversal_unica(20.5, 20.5, 12.0, 40.0).ok_phi
    assert not E.barra_transversal_unica(20.0, 20.0, 12.0, 40.1).ok_espacamento


def test_9471_phi_limitado_a_25mm():
    """Menor dimensão 30 cm -> 50 mm, mas o limite é 25 mm."""
    assert E.barra_transversal_unica(25.0, 25.0, 30.0, 50.0).ok
    r = E.barra_transversal_unica(25.5, 25.5, 30.0, 50.0)
    assert r.phi_max_mm == pytest.approx(25.0) and not r.ok_phi


def test_9471_phi_t_e_solda():
    assert not E.barra_transversal_unica(20.0, 16.0, 30.0, 20.0).ok_phi_t
    assert not E.barra_transversal_unica(20.0, 20.0, 30.0, 20.0,
                                         solda_contorno_completo=False).ok
    assert not E.barra_transversal_unica(20.0, 20.0, 30.0, 20.0,
                                         solda_conforme_954=False).ok


# ===========================================================================
# 9.5.2 -- Limites de bitola do traspasse (PDF p. 62)
# ===========================================================================
def test_952_barra_32mm():
    assert E.verificar_bitola_traspasse(32.0).ok
    r = E.verificar_bitola_traspasse(32.5)
    assert not r.ok and not r.ok_barra


def test_952_feixe_45mm_exato():
    """√(4·22,5²) = 45 mm exato e √(27² + 36²) = 45 mm exato: passam."""
    r = E.verificar_bitola_traspasse((22.5,) * 4)
    assert r.feixe and r.diametro_equivalente_mm == pytest.approx(45.0) and r.ok
    assert E.verificar_bitola_traspasse((27.0, 36.0)).ok_feixe


def test_952_feixe_acima_de_45mm():
    """√(4·25²) = 50 mm > 45: reprova."""
    r = E.verificar_bitola_traspasse((25.0,) * 4)
    assert r.diametro_equivalente_mm == pytest.approx(50.0)
    assert not r.ok and not r.ok_feixe and r.ok_barra
    assert not E.verificar_bitola_traspasse((22.6,) * 4).ok


def test_952_feixe_com_barra_acima_de_32():
    r = E.verificar_bitola_traspasse((33.0, 10.0))
    assert not r.ok_barra and r.ok_feixe


# ===========================================================================
# 9.5.2.1 -- Mesma seção, diâmetros diferentes e Tabela 9.3 (PDF p. 62-63)
# ===========================================================================
def test_9521_mesma_secao_20pct():
    """ℓ0 = 100 cm: afastamento < 20 cm é mesma seção; 20 cm exato não."""
    assert E.mesma_secao(19.99, 100.0) is True
    assert E.mesma_secao(20.0, 100.0) is False
    assert E.mesma_secao(0.0, 100.0) is True
    assert E.mesma_secao(-10.0, 100.0) is True   # superpostas


def test_9521_mesma_secao_usa_maior_l0():
    """Figura 9.4: ℓ01 > ℓ02, cota < 0,2·ℓ01. ℓ01 = 120: 0,2·120 = 24 cm."""
    assert E.mesma_secao(22.0, 100.0, 120.0) is True
    assert E.mesma_secao(24.0, 100.0, 120.0) is False


def test_9521_diametros_diferentes():
    assert E.phi_traspasse_diametros_diferentes((16.0, 20.0)) == 16.0
    with pytest.raises(nbr.FaixaNormativaError):
        E.phi_traspasse_diametros_diferentes((12.5, 16.0, 20.0))


@pytest.mark.parametrize("tipo,carr,camadas,phi,esperado", [
    ("alta_aderencia", "estatico", 1, None, 100.0),
    ("alta_aderencia", "dinamico", 1, None, 100.0),
    ("alta_aderencia", "estatico", 2, None, 50.0),
    ("alta_aderencia", "dinamico", 3, None, 50.0),
    ("lisa", "estatico", 1, 12.5, 50.0),
    ("lisa", "dinamico", 1, 12.5, 25.0),
    ("lisa", "estatico", 1, 16.0, 25.0),
    ("lisa", "dinamico", 1, 16.0, 25.0),
    ("lisa", "estatico", 1, 15.9, 50.0),   # degrau: φ < 16
    ("nervurada", "estático", 1, None, 100.0),
])
def test_tabela_9_3_todas_as_celulas(tipo, carr, camadas, phi, esperado):
    """Tabela 9.3 (p. 63), as oito células e o degrau φ = 16 mm."""
    assert E.proporcao_maxima_emendas_pct(tipo, carr, camadas, phi) == esperado


def test_tabela_9_3_dado():
    assert E.TABELA_9_3 == {
        ("alta_aderencia", "uma_camada"): {"estatico": 100.0, "dinamico": 100.0},
        ("alta_aderencia", "mais_de_uma_camada"): {"estatico": 50.0, "dinamico": 50.0},
        ("lisa", "phi_menor_16"): {"estatico": 50.0, "dinamico": 25.0},
        ("lisa", "phi_maior_igual_16"): {"estatico": 25.0, "dinamico": 25.0},
    }


def test_tabela_9_3_casos_nao_definidos():
    with pytest.raises(nbr.FaixaNormativaError):
        E.proporcao_maxima_emendas_pct("entalhada", "estatico")
    with pytest.raises(ValueError):
        E.proporcao_maxima_emendas_pct("lisa", "estatico")  # falta φ
    with pytest.raises(ValueError):
        E.proporcao_maxima_emendas_pct("lisa", "ciclico", phi_mm=10.0)


def test_9521_verificar_proporcao():
    assert E.verificar_proporcao_emendas(100.0, "alta_aderencia", "estatico").ok
    r = E.verificar_proporcao_emendas(50.1, "alta_aderencia", "estatico", n_camadas=2)
    assert not r.ok and r.pct_maxima == 50.0
    assert E.verificar_proporcao_emendas(50.0, "alta_aderencia", "dinamico", n_camadas=2).ok
    assert not E.verificar_proporcao_emendas(26.0, "lisa", "dinamico", phi_mm=10.0).ok
    # armadura comprimida ou de distribuição: todas podem ser emendadas
    assert E.verificar_proporcao_emendas(100.0, "lisa", "dinamico", phi_mm=20.0,
                                         comprimida_ou_distribuicao=True).ok


# ===========================================================================
# 9.5.2.1 e 9.5.2.2.2 -- parâmetros novos do traspasse (PDF p. 62-63)
# ===========================================================================
def test_transpasse_sem_parametros_novos_nao_muda():
    """Sem os argumentos do P27, l0t e l0c são os de antes: φ = 16, C25,
    20 % -> α0t = 1,2; l0t = 1,2·60,27 = 72,32 cm; l0c = 60,27 cm."""
    t = A.transpasse_tracionado_cm(16.0, 25.0, 20.0)
    assert t["l0t_cm"] == pytest.approx(1.2 * lb_c25_cm(16.0), rel=1e-9)
    assert t["acrescimo_distancia_livre_cm"] == 0.0
    assert t["justificar_armadura_transversal"] is False
    c = A.transpasse_comprimido_cm(16.0, 25.0)
    assert c["l0c_cm"] == pytest.approx(lb_c25_cm(16.0), rel=1e-9)


def test_transpasse_diametros_diferentes_usa_menor():
    """Barras de 16 e 20 mm emendadas entre si: traspasse pela de 16 mm."""
    base = A.transpasse_tracionado_cm(16.0, 25.0, 20.0)
    r = A.transpasse_tracionado_cm(20.0, 25.0, 20.0, diametros_diferentes=(16.0, 20.0))
    assert r["phi_calculo_mm"] == 16.0
    assert r["l0t_cm"] == pytest.approx(base["l0t_cm"])
    rc = A.transpasse_comprimido_cm(20.0, 25.0, diametros_diferentes=(20.0, 16.0))
    assert rc["l0c_cm"] == pytest.approx(A.transpasse_comprimido_cm(16.0, 25.0)["l0c_cm"])
    assert E.transpasse_tracionado_cm is A.transpasse_tracionado_cm


def test_transpasse_diametros_diferentes_erros():
    with pytest.raises(nbr.FaixaNormativaError):
        A.transpasse_tracionado_cm(16.0, 25.0, 20.0, diametros_diferentes=(12.5, 16.0, 20.0))
    with pytest.raises(ValueError):   # φ não é um dos dois
        A.transpasse_tracionado_cm(10.0, 25.0, 20.0, diametros_diferentes=(16.0, 20.0))
    with pytest.raises(ValueError):   # uma das barras > 32 mm
        A.transpasse_tracionado_cm(25.0, 25.0, 20.0, diametros_diferentes=(25.0, 40.0))


def test_95222_distancia_livre_maior_que_4phi():
    """φ = 16 mm -> 4φ = 6,4 cm. Distância 6,4 cm (= 4φ): nada se soma;
    6,5 cm: soma 6,5; 5φ = 8,0 cm: l0t = l0t,base + 8,0."""
    base = A.transpasse_tracionado_cm(16.0, 25.0, 20.0)["l0t_cm"]
    r = A.transpasse_tracionado_cm(16.0, 25.0, 20.0, distancia_livre_cm=6.4)
    assert r["l0t_cm"] == pytest.approx(base)
    assert r["justificar_armadura_transversal"] is False
    r = A.transpasse_tracionado_cm(16.0, 25.0, 20.0, distancia_livre_cm=6.5)
    assert r["l0t_cm"] == pytest.approx(base + 6.5)
    r = A.transpasse_tracionado_cm(16.0, 25.0, 20.0, distancia_livre_cm=8.0)
    assert r["l0t_cm"] == pytest.approx(base + 8.0)
    assert r["justificar_armadura_transversal"] is True
    with pytest.raises(ValueError):
        A.transpasse_tracionado_cm(16.0, 25.0, 20.0, distancia_livre_cm=-1.0)


def test_95222_distancia_livre_comprimido_por_analogia_com_aviso():
    base = A.transpasse_comprimido_cm(16.0, 25.0)["l0c_cm"]
    with pytest.warns(nbr.AvisoNBR6118):
        r = A.transpasse_comprimido_cm(16.0, 25.0, distancia_livre_cm=8.0)
    assert r["l0c_cm"] == pytest.approx(base + 8.0)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        A.transpasse_comprimido_cm(16.0, 25.0, distancia_livre_cm=6.4)


# ===========================================================================
# 9.5.2.4 -- Armadura transversal nas emendas (PDF p. 64)
# ===========================================================================
def test_95241_phi_menor_16_e_menos_25pct_usa_9426():
    """φ = 12,5 mm, 20 %: vale 9.4.2.6: Ast = 0,25·As = 0,25·1,2272 cm²."""
    As = area_cm2(12.5)
    r = E.Ast_emenda("tracionada", 12.5, As, FYD_50, pct_emendadas=20.0)
    assert r.regra == "9.4.2.6"
    assert r.Ast_min_cm2 == pytest.approx(0.25 * As)
    assert r.fracao_forca_barra == 0.25
    # borda: φ = 15,9 e 24,9 % ainda é 9.4.2.6
    assert E.Ast_emenda("tracionada", 15.9, 2.0, FYD_50, pct_emendadas=24.9).regra == "9.4.2.6"


def test_95241_25pct_ou_phi_16_forca_de_uma_barra():
    """25 % exato (>= 25) ou φ = 16 exato (>= 16): Ast·fyd,t >= As·fyd."""
    As = area_cm2(12.5)
    r = E.Ast_emenda("tracionada", 12.5, As, FYD_50, pct_emendadas=25.0)
    assert r.regra == "9.5.2.4.1" and r.Ast_min_cm2 == pytest.approx(As)
    assert r.Ast_por_terco_extremo_cm2 == pytest.approx(As / 2.0)
    assert r.distancia_max_primeira_barra_cm == 15.0
    r = E.Ast_emenda("tracionada", 16.0, area_cm2(16.0), FYD_50, pct_emendadas=0.0)
    assert r.regra == "9.5.2.4.1"


def test_95241_fyd_transversal_diferente():
    """As = 3,1416 cm² (φ 20), fyd = 434,78; estribo CA-60, fyd,t = 521,74:
    Ast = 3,1416·434,78/521,74 = 2,618 cm²."""
    As = area_cm2(20.0)
    r = E.Ast_emenda("tracionada", 20.0, As, FYD_50, pct_emendadas=30.0,
                     fyd_transversal_mpa=600.0 / 1.15)
    assert r.Ast_min_cm2 == pytest.approx(As * 500.0 / 600.0)


def test_95241_barras_fechadas_10phi():
    """φ = 20 mm -> 10φ = 20 cm: 19,9 cm exige barras fechadas; 20 cm não."""
    As = area_cm2(20.0)
    r = E.Ast_emenda("tracionada", 20.0, As, FYD_50, pct_emendadas=30.0,
                     distancia_entre_emendas_cm=19.9)
    assert r.barras_fechadas is True and r.distancia_limite_fechadas_cm == 20.0
    r = E.Ast_emenda("tracionada", 20.0, As, FYD_50, pct_emendadas=30.0,
                     distancia_entre_emendas_cm=20.0)
    assert r.barras_fechadas is False
    r = E.Ast_emenda("tracionada", 20.0, As, FYD_50, pct_emendadas=30.0)
    assert r.barras_fechadas is None


def test_95242_comprimida_barra_4phi_alem():
    """Comprimida φ = 20: mesmos critérios e barra a 4φ = 8 cm além."""
    As = area_cm2(20.0)
    r = E.Ast_emenda("comprimida", 20.0, As, FYD_50, pct_emendadas=100.0)
    assert r.regra == "9.5.2.4.1" and r.Ast_min_cm2 == pytest.approx(As)
    assert r.barra_alem_extremidade_cm == pytest.approx(8.0)
    r = E.Ast_emenda("comprimida", 10.0, area_cm2(10.0), FYD_50, pct_emendadas=20.0)
    assert r.regra == "9.4.2.6" and r.barra_alem_extremidade_cm == pytest.approx(4.0)


def test_95243_secundaria_usa_9426():
    As = area_cm2(20.0)
    r = E.Ast_emenda("secundaria", 20.0, As, FYD_50)
    assert r.regra == "9.4.2.6" and r.Ast_min_cm2 == pytest.approx(0.25 * As)
    r = E.Ast_emenda("secundaria", 32.0, area_cm2(32.0), FYD_50)
    assert r.Ast_min_cm2 is None and r.ok is None   # 9.4.2.6.2 não dá área


def test_9524_verificacao_e_erros():
    As = area_cm2(20.0)
    assert E.Ast_emenda("tracionada", 20.0, As, FYD_50, pct_emendadas=30.0,
                        Ast_adotada_cm2=As).ok is True
    assert E.Ast_emenda("tracionada", 20.0, As, FYD_50, pct_emendadas=30.0,
                        Ast_adotada_cm2=0.99 * As).ok is False
    with pytest.raises(nbr.FaixaNormativaError):
        E.Ast_emenda("tracionada", 32.5, 8.3, FYD_50, pct_emendadas=30.0)
    with pytest.raises(ValueError):
        E.Ast_emenda("tracionada", 20.0, As, FYD_50)   # falta pct
    with pytest.raises(ValueError):
        E.Ast_emenda("torcida", 20.0, As, FYD_50, pct_emendadas=30.0)


# ===========================================================================
# 9.5.2.5 -- Traspasse em feixes (PDF p. 64)
# ===========================================================================
def test_9525_feixe_3_barras():
    """n = 3, φ = 20, ℓ0 = 100 cm: 3 + 1 = 4 barras na seção (ok);
    separação >= 1,3·100 = 130 cm; inícios 0, 130, 260; zona 2·130 + 100 =
    360 cm; círculo de mesma área = 20·√3 = 34,64 mm <= 45."""
    r = E.escalonamento_emenda_feixe(3, 20.0, 100.0)
    assert r.ok and r.n_max_barras_secao == 4
    assert r.separacao_min_cm == pytest.approx(130.0)
    assert r.inicios_emendas_cm == pytest.approx((0.0, 130.0, 260.0))
    assert r.comprimento_zona_emendas_cm == pytest.approx(360.0)
    assert r.diametro_equivalente_mm == pytest.approx(20.0 * math.sqrt(3.0))


def test_9525_feixe_4_barras_passa_de_4_na_secao():
    r = E.escalonamento_emenda_feixe(4, 16.0, 80.0)
    assert r.n_max_barras_secao == 5 and not r.ok_n_barras and not r.ok


def test_9525_separacao_adotada_e_45mm():
    assert E.escalonamento_emenda_feixe(3, 20.0, 100.0, separacao_adotada_cm=130.0).ok
    assert not E.escalonamento_emenda_feixe(3, 20.0, 100.0, separacao_adotada_cm=129.9).ok
    # φ = 26, n = 3: 26·√3 = 45,03 mm > 45
    assert not E.escalonamento_emenda_feixe(3, 26.0, 100.0).ok_diametro


# ===========================================================================
# 9.5.3 -- Luvas (PDF p. 65)
# ===========================================================================
def test_953_luva_115_fy():
    """φ 20: As = 3,1416 cm²; fy = 500 MPa -> As·fy = 157,08 kN;
    F,mín = 1,15·157,08 = 180,64 kN."""
    As = area_cm2(20.0)
    Fmin = 1.15 * As * 500.0 / 10.0
    r = E.verificar_luva(Fmin, 500.0, As)
    assert r.ok and r.F_min_kn == pytest.approx(180.642, rel=1e-4)
    assert not E.verificar_luva(180.0, 500.0, As).ok


# ===========================================================================
# 9.5.4 -- Solda (PDF p. 65-66)
# ===========================================================================
def test_954_topo():
    assert E.verificar_emenda_solda("topo_caldeamento", 10.0).ok
    assert not E.verificar_emenda_solda("topo_caldeamento", 8.0).ok
    assert E.verificar_emenda_solda("topo_eletrodo", 20.0).ok
    assert not E.verificar_emenda_solda("topo_eletrodo", 16.0).ok


def test_954_traspasse_5phi():
    """φ = 20: cordões >= 100 mm, afastados >= 100 mm, >= 2 cordões,
    espessura >= 0,3·20 = 6 mm (Figura 9.6)."""
    ok = E.verificar_emenda_solda("traspasse", 20.0, n_cordoes=2,
                                  comprimento_cordao_mm=100.0,
                                  afastamento_cordoes_mm=100.0,
                                  espessura_cordao_mm=6.0)
    assert ok.ok
    for kw in (dict(n_cordoes=1), dict(comprimento_cordao_mm=99.0),
               dict(afastamento_cordoes_mm=99.0), dict(espessura_cordao_mm=5.9)):
        args = dict(n_cordoes=2, comprimento_cordao_mm=100.0,
                    afastamento_cordoes_mm=100.0, espessura_cordao_mm=6.0)
        args.update(kw)
        assert not E.verificar_emenda_solda("traspasse", 20.0, **args).ok
    with pytest.raises(ValueError):
        E.verificar_emenda_solda("traspasse", 20.0, n_cordoes=2)


def test_954_cobrejuntas():
    """φ1 = 20: cordões >= 100 mm; cobrejunta φ2 = 16 -> espessura >= 4,8 mm."""
    assert E.verificar_emenda_solda("cobrejuntas", 20.0, comprimento_cordao_mm=100.0,
                                    espessura_cordao_mm=4.8, phi_cobrejunta_mm=16.0).ok
    assert not E.verificar_emenda_solda("cobrejuntas", 20.0, comprimento_cordao_mm=100.0,
                                        espessura_cordao_mm=4.7, phi_cobrejunta_mm=16.0).ok
    assert not E.verificar_emenda_solda("cobrejuntas", 20.0, comprimento_cordao_mm=99.0).ok


def test_954_resistencia_115():
    As = area_cm2(20.0)
    Fmin = 1.15 * As * 500.0 / 10.0
    r = E.verificar_emenda_solda("topo_eletrodo", 20.0, F_ensaio_kn=Fmin,
                                 fy_barra_mpa=500.0, As_cm2=As)
    assert r.ok and r.resistencia.F_min_kn == pytest.approx(Fmin)
    assert not E.verificar_emenda_solda("topo_eletrodo", 20.0, F_ensaio_kn=0.99 * Fmin,
                                        fy_barra_mpa=500.0, As_cm2=As).ok


def test_954_mesma_secao_15phi():
    """φ = 20 -> 15φ = 30 cm: 12φ = 24 cm é mesma seção; 30 cm exato não."""
    assert E.mesma_secao_solda(24.0, 20.0) is True
    assert E.mesma_secao_solda(29.9, 20.0) is True
    assert E.mesma_secao_solda(30.0, 20.0) is False


def test_954_reducao_20pct():
    """Tracionada com variável preponderante: 0,8·As·fyd.
    φ 20: 0,8·3,1416·434,78/10 = 109,27 kN; sem redução, 136,59 kN."""
    As = area_cm2(20.0)
    assert E.fator_resistencia_emenda_solda(True, True) == 0.8
    assert E.fator_resistencia_emenda_solda(True, False) == 1.0
    assert E.fator_resistencia_emenda_solda(False, True) == 1.0
    assert E.resistencia_emenda_solda_kn(As, FYD_50, True, True) == pytest.approx(
        0.8 * As * FYD_50 / 10.0)
    assert E.resistencia_emenda_solda_kn(As, FYD_50, False, False) == pytest.approx(136.591, rel=1e-4)
