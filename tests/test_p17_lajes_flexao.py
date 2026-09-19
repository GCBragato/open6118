"""Testes do P17 - Lajes: flexao, armaduras minimas e momentos.

Cobre dimensionamento/lajes_nbr6118.py (bloco "=== P17 ===") contra a
ABNT NBR 6118:2026:

  - 19.2       Principios do ELU de lajes (desvio > 15 graus), p. 179
  - 19.3.3.2   Tabela 19.1 - armaduras minimas de laje, p. 179-180
  - 19.3.3.2   As minima de laje lisa/cogumelo nao aderente, p. 180
  - 19.3.3.2   Extensao da armadura negativa de borda sem continuidade, p. 179
  - 14.7.6.1   Reacoes de apoio por charneiras plasticas, p. 117
  - 14.7.6.2   Compatibilizacao de momentos negativos, p. 117
  - 14.7.8     Faixas de laje para porticos multiplos (Figura 14.9), p. 118

Os valores esperados vem da imagem de cada pagina (SCRATCH\\nbr_png\\pNNN.png).
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import lajes_nbr6118 as laj                # noqa: E402
import nucleo_nbr6118 as nbr               # noqa: E402


def _aprox(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# 19.3.3.2 / Tabela 19.1 - armaduras minimas (p. 179-180)
# ---------------------------------------------------------------------------
# fck = 25 MPa -> rho_min = 0,0015 (Tabela 17.3, ja na faixa C20-C30).
FCK = 25.0
RM = 0.0015          # rho_min(25) esperado
RP = 0.001           # rho_p sintetico


def test_rho_min_flexao_25_e_0015():
    assert _aprox(nbr.rho_min_flexao(FCK), RM)


# --- linha 1: armaduras negativas -------------------------------------------
def test_tab191_negativa_sem_ativa():
    assert _aprox(laj.rho_min_laje("negativa", "sem", FCK), RM)


def test_tab191_negativa_aderente():
    # max(RM - RP, 0.67 RM) = max(0.0005, 0.001005) = 0.001005
    assert _aprox(laj.rho_min_laje("negativa", "aderente", FCK, rho_p=RP), 0.67 * RM)


def test_tab191_negativa_nao_aderente():
    # max(RM - 0.5 RP, 0.67 RM) = max(0.001, 0.001005) = 0.001005
    assert _aprox(laj.rho_min_laje("negativa", "nao_aderente", FCK, rho_p=RP), 0.67 * RM)


def test_tab191_negativa_colapsa_com_rho_p_zero():
    assert _aprox(laj.rho_min_laje("negativa", "aderente", FCK, rho_p=0.0),
                  laj.rho_min_laje("negativa", "sem", FCK))
    assert _aprox(laj.rho_min_laje("negativa", "nao_aderente", FCK, rho_p=0.0),
                  laj.rho_min_laje("negativa", "sem", FCK))


# --- linha 2: armaduras negativas de bordas sem continuidade ----------------
def test_tab191_negativa_borda_sem_continuidade_independe_de_ativa():
    esperado = 0.67 * RM
    for situacao in laj.SITUACOES_ATIVA_LAJE:
        assert _aprox(
            laj.rho_min_laje("negativa_borda_sem_continuidade", situacao, FCK, rho_p=RP),
            esperado,
        )


# --- linha 3: armaduras positivas de lajes armadas nas duas direcoes -------
def test_tab191_positiva_duas_direcoes_sem_ativa():
    assert _aprox(laj.rho_min_laje("positiva_duas_direcoes", "sem", FCK), 0.67 * RM)


def test_tab191_positiva_duas_direcoes_aderente():
    # max(0.67 RM - RP, 0.5 RM) = max(0.000005, 0.00075) = 0.00075
    assert _aprox(laj.rho_min_laje("positiva_duas_direcoes", "aderente", FCK, rho_p=RP),
                  0.5 * RM)


def test_tab191_positiva_duas_direcoes_nao_aderente():
    # max(RM - 0.5 RP, 0.5 RM) = max(0.001, 0.00075) = 0.001
    assert _aprox(laj.rho_min_laje("positiva_duas_direcoes", "nao_aderente", FCK, rho_p=RP),
                  RM - 0.5 * RP)


def test_tab191_positiva_duas_direcoes_aderente_colapsa_com_rho_p_zero():
    # A coluna 'aderente' parte do mesmo piso 0.67 rho_min da coluna 'sem'
    # (ver Tabela 19.1, p. 180), entao colapsa quando rho_p = 0.
    assert _aprox(laj.rho_min_laje("positiva_duas_direcoes", "aderente", FCK, rho_p=0.0),
                  laj.rho_min_laje("positiva_duas_direcoes", "sem", FCK))


def test_tab191_positiva_duas_direcoes_nao_aderente_nao_colapsa_para_0():
    # A coluna 'nao_aderente' parte do piso rho_min (nao 0.67 rho_min como a
    # coluna 'sem'): com rho_p = 0 o resultado e rho_min, nao 0.67 rho_min -
    # e a propria Tabela 19.1 que define os dois pisos diferentes (p. 180).
    assert _aprox(laj.rho_min_laje("positiva_duas_direcoes", "nao_aderente", FCK, rho_p=0.0),
                  RM)


# --- linha 4: armadura positiva principal de lajes em uma direcao ----------
def test_tab191_positiva_principal_sem_ativa():
    assert _aprox(laj.rho_min_laje("positiva_principal_uma_direcao", "sem", FCK), RM)


def test_tab191_positiva_principal_aderente():
    # max(RM - RP, 0.5 RM) = max(0.0005, 0.00075) = 0.00075
    assert _aprox(
        laj.rho_min_laje("positiva_principal_uma_direcao", "aderente", FCK, rho_p=RP),
        0.5 * RM,
    )


def test_tab191_positiva_principal_nao_aderente():
    # max(RM - 0.5 RP, 0.5 RM) = max(0.001, 0.00075) = 0.001
    assert _aprox(
        laj.rho_min_laje("positiva_principal_uma_direcao", "nao_aderente", FCK, rho_p=RP),
        RM - 0.5 * RP,
    )


def test_tab191_positiva_principal_colapsa_com_rho_p_zero():
    assert _aprox(
        laj.rho_min_laje("positiva_principal_uma_direcao", "aderente", FCK, rho_p=0.0),
        laj.rho_min_laje("positiva_principal_uma_direcao", "sem", FCK),
    )
    assert _aprox(
        laj.rho_min_laje("positiva_principal_uma_direcao", "nao_aderente", FCK, rho_p=0.0),
        laj.rho_min_laje("positiva_principal_uma_direcao", "sem", FCK),
    )


# --- linha 5: armadura positiva secundaria de lajes em uma direcao ---------
def test_tab191_positiva_secundaria_rho_sem_e_aderente_e_0_5_rho_min():
    assert _aprox(laj.rho_min_laje("positiva_secundaria_uma_direcao", "sem", FCK), 0.5 * RM)
    assert _aprox(laj.rho_min_laje("positiva_secundaria_uma_direcao", "aderente", FCK),
                  0.5 * RM)


def test_tab191_positiva_secundaria_nao_aderente_e_indefinida():
    """Celula "-" da Tabela 19.1: a norma nao define este caso."""
    with pytest.raises(nbr.FaixaNormativaError):
        laj.rho_min_laje("positiva_secundaria_uma_direcao", "nao_aderente", FCK)


def test_tab191_tipo_e_situacao_invalidos_levantam_valueerror():
    with pytest.raises(ValueError):
        laj.rho_min_laje("tipo_inexistente", "sem", FCK)
    with pytest.raises(ValueError):
        laj.rho_min_laje("negativa", "situacao_inexistente", FCK)


# --- As/s da armadura secundaria (criterio inteiro, com As/s e cm2/m) ------
def test_as_min_secundaria_governa_pelo_rho():
    # As_principal=3 cm2/m -> 20% = 0.6; 0.9 cm2/m; rho_s_min*bw*h = 0.00075*100*15 = 1.125
    As = laj.as_min_secundaria_uma_direcao_cm2_por_m(
        As_principal_cm2_por_m=3.0, bw_cm=100.0, h_cm=15.0, fck_mpa=FCK,
    )
    assert _aprox(As, 1.125)


def test_as_min_secundaria_governa_pelos_20_por_cento():
    # As_principal=6 cm2/m -> 20% = 1.2 > 1.125 (rho) e > 0.9
    As = laj.as_min_secundaria_uma_direcao_cm2_por_m(
        As_principal_cm2_por_m=6.0, bw_cm=100.0, h_cm=15.0, fck_mpa=FCK,
    )
    assert _aprox(As, 1.2)


def test_as_min_secundaria_governa_pelo_piso_09():
    # As_principal=1 cm2/m -> 20% = 0.2; rho_s_min*bw*h = 0.00075*100*5 = 0.375 -> governa 0.9
    As = laj.as_min_secundaria_uma_direcao_cm2_por_m(
        As_principal_cm2_por_m=1.0, bw_cm=100.0, h_cm=5.0, fck_mpa=FCK,
    )
    assert _aprox(As, 0.9)


def test_as_min_secundaria_nao_aderente_levanta_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        laj.as_min_secundaria_uma_direcao_cm2_por_m(
            As_principal_cm2_por_m=3.0, bw_cm=100.0, h_cm=15.0, fck_mpa=FCK,
            situacao_ativa="nao_aderente",
        )


# ---------------------------------------------------------------------------
# 19.3.3.2 - As minima de laje lisa/cogumelo com armadura ativa nao aderente
# (p. 180): As >= 0,00075 h l
# ---------------------------------------------------------------------------
def test_as_min_laje_lisa_nao_aderente_h20_l600():
    # 0.00075 * 20 * 600 = 9.0 cm2 (teste sugerido no plano)
    assert _aprox(laj.as_min_laje_lisa_nao_aderente_cm2(h_cm=20.0, l_cm=600.0), 9.0)


def test_as_min_laje_lisa_nao_aderente_h15_l500():
    assert _aprox(laj.as_min_laje_lisa_nao_aderente_cm2(h_cm=15.0, l_cm=500.0), 5.625)


def test_largura_cobertura_negativa_lisa():
    # apoio de 40 cm + 1.5*20 de cada lado = 40 + 30 + 30 = 100 cm
    assert _aprox(laj.largura_cobertura_negativa_lisa_cm(dimensao_apoio_cm=40.0, h_cm=20.0),
                  100.0)


# ---------------------------------------------------------------------------
# 19.3.3.2 - extensao da armadura negativa de borda sem continuidade (p. 179)
# extensao >= 0,15 * vao_menor
# ---------------------------------------------------------------------------
def test_extensao_negativa_borda_lx500():
    # teste sugerido no plano: lx=500cm -> extensao=75cm
    assert _aprox(laj.extensao_negativa_borda_cm(500.0), 75.0)


def test_extensao_negativa_borda_lx300():
    assert _aprox(laj.extensao_negativa_borda_cm(300.0), 45.0)


# ---------------------------------------------------------------------------
# 19.2 - desvio > 15 graus entre armadura e tensoes principais (p. 179)
# ---------------------------------------------------------------------------
def test_desvio_ate_15_graus_nao_avisa():
    with warnings.catch_warnings():
        warnings.simplefilter("error", nbr.AvisoNBR6118)
        laj.verificar_desvio_armadura_tensoes_principais(15.0)
        laj.verificar_desvio_armadura_tensoes_principais(10.0)
        laj.verificar_desvio_armadura_tensoes_principais(-15.0)


def test_desvio_acima_de_15_graus_avisa():
    with pytest.warns(nbr.AvisoNBR6118):
        laj.verificar_desvio_armadura_tensoes_principais(16.0)


def test_desvio_negativo_acima_de_15_graus_avisa():
    with pytest.warns(nbr.AvisoNBR6118):
        laj.verificar_desvio_armadura_tensoes_principais(-20.0)


# ---------------------------------------------------------------------------
# 14.7.6.2 - compatibilizacao de momentos negativos (p. 117)
# ---------------------------------------------------------------------------
def test_compat_momento_default_media_08_inalterado():
    # Apostila 3.17.5 (ja no modulo): M1=1425, M2=1663 -> X = max(1330.4, 1544) = 1544
    assert _aprox(laj.compat_momento_negativo(1425, 1663), 1544, tol=1.0)


def test_compat_momento_regra_maior():
    assert _aprox(laj.compat_momento_negativo(1425, 1663, regra="maior"), 1663)
    assert _aprox(laj.compat_momento_negativo(-1425, 1663, regra="maior"), 1663)


def test_compat_momento_regra_invalida():
    with pytest.raises(ValueError):
        laj.compat_momento_negativo(100, 200, regra="media")


# ---------------------------------------------------------------------------
# 14.7.8 - faixas de laje para porticos multiplos, Figura 14.9 (p. 118)
# ---------------------------------------------------------------------------
def test_faixas_positivo():
    r = laj.repartir_momentos_faixas(100.0, "positivo")
    assert _aprox(r["faixas_internas"], 45.0)
    assert _aprox(r["faixa_externa"], 27.5)
    assert _aprox(r["faixas_internas"] + 2 * r["faixa_externa"], 100.0)


def test_faixas_negativo():
    r = laj.repartir_momentos_faixas(100.0, "negativo")
    assert _aprox(r["faixas_internas"], 25.0)
    assert _aprox(r["faixa_externa"], 37.5)
    assert _aprox(r["faixas_internas"] + 2 * r["faixa_externa"], 100.0)


def test_faixas_tipo_invalido():
    with pytest.raises(ValueError):
        laj.repartir_momentos_faixas(100.0, "invalido")


# ---------------------------------------------------------------------------
# 14.7.6.1 - reacoes de apoio por charneiras plasticas (p. 117)
# ---------------------------------------------------------------------------
def test_charneiras_quadrado_apoiada_bate_com_bares_tipo1():
    lx = ly = 400.0   # cm, lambda = 1.00 exato
    p = 5.0
    vinc = {"x0": "apoiada", "x1": "apoiada", "y0": "apoiada", "y1": "apoiada"}
    r = laj.reacoes_charneiras(lx, ly, p, vinc)
    bares = laj.reacoes_duas_direcoes("1", lx, ly, p)
    assert _aprox(r["x0"], bares.Vx, tol=1e-6)
    assert _aprox(r["x1"], bares.Vx, tol=1e-6)
    assert _aprox(r["y0"], bares.Vy, tol=1e-6)
    assert _aprox(r["y1"], bares.Vy, tol=1e-6)
    # valor direto do triangulo a 45 graus: V = p*lx/4 = 5*4/4 = 5.0 kN/m
    assert _aprox(r["y0"], 5.0, tol=1e-6)


def test_charneiras_quadrado_engastada_bate_com_bares_tipo6():
    lx = ly = 486.0
    p = 6.9
    vinc = {"x0": "engastada", "x1": "engastada", "y0": "engastada", "y1": "engastada"}
    r = laj.reacoes_charneiras(lx, ly, p, vinc)
    bares = laj.reacoes_duas_direcoes("6", lx, ly, p)
    assert _aprox(r["x0"], bares.Vx_eng, tol=1e-6)
    assert _aprox(r["y0"], bares.Vy_eng, tol=1e-6)


def test_charneiras_retangular_apoiada_lambda2_bate_com_bares_tipo1():
    lx, ly = 200.0, 400.0   # lambda = 2.00, no fim da Tabela de Bares
    p = 5.0
    vinc = {"x0": "apoiada", "x1": "apoiada", "y0": "apoiada", "y1": "apoiada"}
    r = laj.reacoes_charneiras(lx, ly, p, vinc)
    bares = laj.reacoes_duas_direcoes("1", lx, ly, p)
    assert _aprox(r["x0"], bares.Vx, tol=1e-6)
    assert _aprox(r["y0"], bares.Vy, tol=1e-6)


@pytest.mark.parametrize("vinc", [
    {"x0": "apoiada", "x1": "apoiada", "y0": "apoiada", "y1": "apoiada"},
    {"x0": "engastada", "x1": "apoiada", "y0": "apoiada", "y1": "engastada"},
    {"x0": "engastada", "x1": "engastada", "y0": "engastada", "y1": "apoiada"},
    {"x0": "apoiada", "x1": "apoiada", "y0": "apoiada", "y1": "livre"},
])
def test_charneiras_conserva_a_carga_total(vinc):
    """A soma das reacoes vezes o comprimento de cada borda tem de fechar a
    carga total da laje (equilibrio), qualquer que seja a combinacao de
    vinculos - nao depende de estar tabelado em Bares."""
    lx_cm, ly_cm, p = 250.0, 380.0, 4.2
    r = laj.reacoes_charneiras(lx_cm, ly_cm, p, vinc)
    lx_m, ly_m = lx_cm / 100.0, ly_cm / 100.0
    carga_total = p * lx_m * ly_m
    carga_nas_bordas = (
        r["x0"] * ly_m + r["x1"] * ly_m + r["y0"] * lx_m + r["y1"] * lx_m
    )
    assert _aprox(carga_nas_bordas, carga_total, tol=1e-6)


def test_charneiras_borda_livre_nao_recebe_reacao():
    vinc = {"x0": "apoiada", "x1": "apoiada", "y0": "apoiada", "y1": "livre"}
    r = laj.reacoes_charneiras(300.0, 500.0, 5.0, vinc)
    assert r["y1"] == 0.0
    assert r["x0"] > 0.0 and r["x1"] > 0.0 and r["y0"] > 0.0


def test_charneiras_engastada_atrai_mais_area_que_apoiada_oposta():
    """Borda engastada tem peso maior (tan 60 > 1): num quadrado com so uma
    borda engastada e as outras 3 apoiadas, a engastada recebe reacao maior
    que a apoiada oposta a ela."""
    vinc = {"x0": "engastada", "x1": "apoiada", "y0": "apoiada", "y1": "apoiada"}
    r = laj.reacoes_charneiras(400.0, 400.0, 5.0, vinc)
    assert r["x0"] > r["x1"]


def test_charneiras_vinculo_desconhecido_levanta_erro():
    vinc = {"x0": "apoiada", "x1": "apoiada", "y0": "apoiada", "y1": "flutuante"}
    with pytest.raises(ValueError):
        laj.reacoes_charneiras(300.0, 400.0, 5.0, vinc)


def test_charneiras_faltando_chave_levanta_erro():
    vinc = {"x0": "apoiada", "x1": "apoiada", "y0": "apoiada"}
    with pytest.raises(ValueError):
        laj.reacoes_charneiras(300.0, 400.0, 5.0, vinc)


def test_charneiras_menos_de_2_apoios_levanta_erro():
    vinc = {"x0": "apoiada", "x1": "livre", "y0": "livre", "y1": "livre"}
    with pytest.raises(ValueError):
        laj.reacoes_charneiras(300.0, 400.0, 5.0, vinc)


# ---------------------------------------------------------------------------
# Correcoes da verificacao (volta 1) - citacao de pagina do PDF nos itens
# 19.2 e 19.3.3.2. "Pagina do PDF = impressa + 18" (convencao do brief); os
# itens 19.x tinham citado a pagina IMPRESSA (161/162) como se fosse a
# pagina do PDF. Pagina real do PDF: 179 (19.2 e a extensao da armadura
# negativa de borda) e 180 (Tabela 19.1 e As minimo de laje lisa nao
# aderente) - conferido em SCRATCH\nbr_png\p179.png e p180.png.
# ---------------------------------------------------------------------------
def _sem_quebras(texto: str) -> str:
    """Normaliza espacos/quebras de linha do docstring para comparar como
    texto corrido (docstring de varias linhas quebra 'PDF' e 'p. NNN' em
    linhas diferentes, com a indentacao do codigo entre eles)."""
    return " ".join(texto.split())


def test_citacoes_de_pagina_pdf_179_180_nos_itens_19x():
    # 19.2 - desvio > 15 graus (docstring e mensagem de aviso)
    doc_desvio = _sem_quebras(laj.verificar_desvio_armadura_tensoes_principais.__doc__)
    assert "PDF p. 179" in doc_desvio
    assert "PDF p. 161" not in doc_desvio

    # 19.3.3.2 - extensao da armadura negativa de borda
    doc_extensao = _sem_quebras(laj.extensao_negativa_borda_cm.__doc__)
    assert "PDF p. 179" in doc_extensao
    assert "PDF p. 161" not in doc_extensao

    # 19.3.3.2 / Tabela 19.1 - rho minimo e As minimo secundaria
    doc_rho = _sem_quebras(laj.rho_min_laje.__doc__)
    assert "PDF p. 180" in doc_rho
    assert "PDF p. 162" not in doc_rho

    doc_as_sec = _sem_quebras(laj.as_min_secundaria_uma_direcao_cm2_por_m.__doc__)
    assert "PDF p. 180" in doc_as_sec
    assert "PDF p. 162" not in doc_as_sec

    # 19.3.3.2 - As minimo de laje lisa/cogumelo nao aderente e cobertura
    doc_as_lisa = _sem_quebras(laj.as_min_laje_lisa_nao_aderente_cm2.__doc__)
    assert "PDF p. 180" in doc_as_lisa
    assert "PDF p. 162" not in doc_as_lisa

    doc_cobertura = _sem_quebras(laj.largura_cobertura_negativa_lisa_cm.__doc__)
    assert "PDF p. 180" in doc_cobertura
    assert "PDF p. 162" not in doc_cobertura


def test_mensagem_aviso_desvio_15_graus_tem_acentuacao():
    """Mensagem exibida ao usuario final (warnings.warn) tem de sair em
    portugues com acento (regra obrigatoria de texto para usuario final).
    Falharia antes da correcao, quando a mensagem estava 100% em ASCII
    ('direcao', 'tensoes', 'calculo')."""
    with pytest.warns(nbr.AvisoNBR6118) as registro:
        laj.verificar_desvio_armadura_tensoes_principais(20.0)
    texto = str(registro[0].message)
    assert "direção" in texto
    assert "tensões" in texto
    assert "cálculo" in texto
