"""Pacote P3 -- Aco de protensao: catalogo e diagrama da Figura 8.6.

Itens da NBR 6118:2026 cobertos:
    - 8.4.1 (PDF p. 49) -- classificacao do aco de armadura ativa (fios e
      cordoalhas, RN/RB).
    - 8.4.5, Figura 8.6 (PDF p. 50) -- diagrama tensao-deformacao simplificado
      do aco de armadura ativa, com o segundo trecho ainda ascendente ate
      fptd em eps_pu (decisao 2 de 19/09/2026: vira o padrao).
    - 8.4.6 (PDF p. 50) -- caracteristicas de dutilidade de fios e cordoalhas.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import protendido_nbr6118 as PT  # noqa: E402

from dimensionamento.rotinas.flexao_composta_obliqua import (  # noqa: E402
    Aco,
    Cabo,
    Concreto,
    CurvaApBilinear,
    Secao,
    armadura_perimetral_retangular,
    esforcos_resistentes_pol,
)


# ---------------------------------------------------------------------------
# 8.4.5 (Figura 8.6, p. 50) -- nucleo_nbr6118.sigma_p
# ---------------------------------------------------------------------------
# CP-190 RB: fpyk = 1710 MPa, fptk = 1900 MPa, gama_s = 1.15, Ep = 200000 MPa.
FPYK_CP190 = 1710.0
FPTK_CP190 = 1900.0
FPYD_CP190 = FPYK_CP190 / nbr.GAMA_S            # = 1486.9565... MPa
FPTD_CP190 = FPTK_CP190 / nbr.GAMA_S            # = 1652.1739... MPa
EPS_PYD_CP190 = FPYD_CP190 / nbr.EP_MPA * 1000.0  # = 7.434782... por mil


def test_sigma_p_joelho_exato_cp190_rb():
    """(eps_pyd, fpyd) exato para CP-190 RB, nos dois diagramas (8.4.5, p.50).

    fpyd = fpyk/gama_s = 1710/1,15 = 1486,9565 MPa;
    eps_pyd = fpyd/Ep*1000 = 1486,9565/200000*1000 = 7,4348 por mil.
    """
    s_fig = nbr.sigma_p(EPS_PYD_CP190, FPYK_CP190, FPTK_CP190, diagrama="nbr_fig_8_6")
    s_pat = nbr.sigma_p(EPS_PYD_CP190, FPYK_CP190, FPTK_CP190, diagrama="patamar")
    assert s_fig == pytest.approx(FPYD_CP190, rel=1e-6)
    assert s_pat == pytest.approx(FPYD_CP190, rel=1e-6)


def test_sigma_p_extremo_eps_pu_exato_cp190_rb():
    """(eps_pu, fptd) exato para CP-190 RB no diagrama da Figura 8.6 (8.4.5, p.50).

    fptd = fptk/gama_s = 1900/1,15 = 1652,1739 MPa, em eps_pu = 35 por mil.
    """
    s = nbr.sigma_p(35.0, FPYK_CP190, FPTK_CP190, diagrama="nbr_fig_8_6")
    assert s == pytest.approx(FPTD_CP190, rel=1e-6)
    # sinal de tracao (eps negativo) espelha o mesmo modulo
    s_neg = nbr.sigma_p(-35.0, FPYK_CP190, FPTK_CP190, diagrama="nbr_fig_8_6")
    assert s_neg == pytest.approx(-FPTD_CP190, rel=1e-6)


def test_sigma_p_ponto_interior_segundo_trecho():
    """Ponto interior do segundo trecho (eps=20 por mil) cai na reta
    (eps_pyd, fpyd) -> (eps_pu, fptd), acima do patamar fpyd (8.4.5, Figura 8.6).

    Conta: sigma = fpyd + (fptd - fpyd) * (20 - eps_pyd) / (35 - eps_pyd)
                 = 1486,9565 + 165,2174 * (12,5652 / 27,5652) = 1562,30 MPa.
    """
    esperado = FPYD_CP190 + (FPTD_CP190 - FPYD_CP190) * (
        (20.0 - EPS_PYD_CP190) / (35.0 - EPS_PYD_CP190)
    )
    s = nbr.sigma_p(20.0, FPYK_CP190, FPTK_CP190, diagrama="nbr_fig_8_6")
    assert s == pytest.approx(esperado, rel=1e-6)
    assert s > FPYD_CP190  # segundo trecho ainda ascendente, nao patamar
    assert s < FPTD_CP190


def test_sigma_p_linear_abaixo_do_joelho():
    """Abaixo de eps_pyd, sigma_p = Ep*eps (reta unica, igual nos dois diagramas)."""
    eps = EPS_PYD_CP190 / 2.0
    esperado = nbr.EP_MPA * eps / 1000.0
    assert esperado < FPYD_CP190
    assert nbr.sigma_p(eps, FPYK_CP190, FPTK_CP190, diagrama="nbr_fig_8_6") == pytest.approx(esperado, rel=1e-6)
    assert nbr.sigma_p(eps, FPYK_CP190, FPTK_CP190, diagrama="patamar") == pytest.approx(esperado, rel=1e-6)


def test_sigma_p_patamar_nao_ultrapassa_fpyd():
    """diagrama='patamar' reproduz o comportamento anterior a este pacote:
    tensao nunca ultrapassa fpyd, mesmo bem alem do joelho."""
    s = nbr.sigma_p(30.0, FPYK_CP190, FPTK_CP190, diagrama="patamar")
    assert s == pytest.approx(FPYD_CP190, rel=1e-6)


def test_sigma_p_monotona_ate_eps_pu():
    """sigma_p(eps) e nao-decrescente em |eps| ate eps_pu, no diagrama da Figura 8.6."""
    eps_varredura = [0.0, 2.0, EPS_PYD_CP190, 10.0, 20.0, 30.0, 35.0]
    valores = [nbr.sigma_p(e, FPYK_CP190, FPTK_CP190, diagrama="nbr_fig_8_6") for e in eps_varredura]
    assert all(b >= a - 1e-9 for a, b in zip(valores, valores[1:]))


def test_sigma_p_fora_da_faixa_levanta_erro():
    """Acima de eps_pu a norma nao define tensao (8.4.5, Figura 8.6): erro, nao numero."""
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.sigma_p(35.001, FPYK_CP190, FPTK_CP190, diagrama="nbr_fig_8_6")


def test_sigma_p_patamar_fora_da_faixa_tambem_levanta_erro():
    """O diagrama='patamar' (legado, mantido para comparacao) tambem respeita
    |eps| <= eps_pu -- a norma nao define tensao alem do alongamento ultimo em
    nenhum dos dois diagramas (8.4.5, Figura 8.6). Antes da correcao do
    pacote P3, esse ramo so clipava em fpyd sem checar a faixa e nunca
    levantava erro aqui."""
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.sigma_p(35.001, FPYK_CP190, FPTK_CP190, diagrama="patamar")


def test_sigma_p_diagrama_invalido_levanta_erro():
    with pytest.raises(ValueError):
        nbr.sigma_p(10.0, FPYK_CP190, FPTK_CP190, diagrama="triangular")


# ---------------------------------------------------------------------------
# 8.4.5 -- CurvaApBilinear (kernel) e efeito no MRd de secao protendida
# ---------------------------------------------------------------------------
def test_curva_ap_bilinear_default_e_figura_8_6():
    """O construtor sem argumentos passa a ser a Figura 8.6 completa
    (ramo_inclinado=True), decisao 2 de 19/09/2026 -- nao mais o patamar."""
    curva = CurvaApBilinear()
    assert curva.ramo_inclinado is True
    eps = curva.eps_pu_pmilh
    assert curva.sigma(eps) == pytest.approx(curva.fptd_kncm2, rel=1e-6)
    assert curva.fptd_kncm2 > curva.fpyd_kncm2


def test_mrd_secao_protendida_ramo_inclinado_maior_que_patamar():
    """MRd de secao retangular protendida com ramo inclinado >= MRd com
    patamar, para o mesmo estado de deformacao (aceite do pacote P3).

    Secao 40x60, cabo a y=-25 cm com eps_pre=15 por mil (efetiva > eps_pyd em
    x_LN=20 cm), comparando so a curva do cabo -- concreto e armadura passiva
    identicos nos dois casos.
    """
    barras = armadura_perimetral_retangular(40, 60, 2.5, 3, 3, 16.0)
    concreto = Concreto(fck_mpa=25.0)
    aco = Aco()
    cabo_inclinado = Cabo(x_cm=0.0, y_cm=-25.0, area_cm2=5.0, eps_pre_pmilh=15.0,
                          curva=CurvaApBilinear(ramo_inclinado=True))
    cabo_patamar = Cabo(x_cm=0.0, y_cm=-25.0, area_cm2=5.0, eps_pre_pmilh=15.0,
                        curva=CurvaApBilinear(ramo_inclinado=False))
    s_inclinado = Secao.retangular(40, 60, concreto, barras=barras, cabos=(cabo_inclinado,))
    s_patamar = Secao.retangular(40, 60, concreto, barras=barras, cabos=(cabo_patamar,))
    alpha, x_LN = 0.0, 20.0
    _, Mx_inclinado, _ = esforcos_resistentes_pol(s_inclinado, aco, alpha, x_LN)
    _, Mx_patamar, _ = esforcos_resistentes_pol(s_patamar, aco, alpha, x_LN)
    assert abs(Mx_inclinado) > abs(Mx_patamar)
    razao = abs(Mx_inclinado) / abs(Mx_patamar)
    assert 1.0 < razao < 1.10  # expectativa do pacote: ~2 % a 3 % a mais


# ---------------------------------------------------------------------------
# 8.4.1 (p. 49) -- catalogo de aco ativo (fios e cordoalhas, RN/RB)
# ---------------------------------------------------------------------------
def test_propriedades_fio_nbr7482_bordas_e_interior():
    """Fio de 4,0 mm (borda fina, unica categoria) e 9,0 mm (borda grossa,
    unica categoria) da TABELA_FIOS_NBR7482, reconstruida a partir do
    catalogo real (Belgo/ArcelorMittal, NBR 7482) na correcao da verificacao
    do pacote P3 -- os valores antigos (fptk e categoria por diametro) nao
    batiam com o catalogo."""
    fio_fino = PT.propriedades_fio(4.0)
    assert fio_fino["area_mm2"] == pytest.approx(12.6)
    assert fio_fino["fptk_MPa"] == pytest.approx(1750.0)
    assert fio_fino["categoria"] == "CP-175"

    fio_grosso = PT.propriedades_fio(9.0)
    assert fio_grosso["area_mm2"] == pytest.approx(63.6)
    assert fio_grosso["fptk_MPa"] == pytest.approx(1450.0)
    assert fio_grosso["categoria"] == "CP-145"

    fio_meio = PT.propriedades_fio(8.0)
    assert fio_meio["area_mm2"] == pytest.approx(50.3)
    assert fio_meio["fptk_MPa"] == pytest.approx(1500.0)
    assert fio_meio["categoria"] == "CP-150"


def test_propriedades_fio_diametro_com_duas_categorias_exige_escolha():
    """6,0 mm e 7,0 mm existem em duas categorias no catalogo (mesma area,
    fptk diferente): sem categoria, propriedades_fio deve recusar a
    ambiguidade em vez de escolher uma sozinha (achado da verificacao do
    pacote P3 -- a tabela antiga so guardava uma entrada por diametro)."""
    with pytest.raises(ValueError):
        PT.propriedades_fio(6.0)

    fio_175 = PT.propriedades_fio(6.0, categoria="CP-175")
    fio_190 = PT.propriedades_fio(6.0, categoria="CP-190")
    assert fio_175["area_mm2"] == pytest.approx(28.3)
    assert fio_190["area_mm2"] == pytest.approx(28.3)
    assert fio_175["fptk_MPa"] == pytest.approx(1750.0)
    assert fio_190["fptk_MPa"] == pytest.approx(1900.0)

    with pytest.raises(ValueError):
        PT.propriedades_fio(6.0, categoria="CP-145")  # nao existe para 6,0 mm


def test_propriedades_fio_bitola_nao_tabelada_levanta_erro():
    with pytest.raises(ValueError):
        PT.propriedades_fio(6.5)


def test_tabela_acos_ativos_cobre_fios_e_cordoalhas():
    """TABELA_ACOS_ATIVOS reune fios (NBR 7482) e cordoalhas CP-190/CP-210
    (NBR 7483) num catalogo unico (8.4.1). A tabela de fios agora e chaveada
    por (diametro, categoria)."""
    assert "fios" in PT.TABELA_ACOS_ATIVOS
    assert "cordoalhas" in PT.TABELA_ACOS_ATIVOS
    assert set(PT.TABELA_ACOS_ATIVOS["cordoalhas"]) == {"CP-190", "CP-210"}
    assert (8.0, "CP-150") in PT.TABELA_ACOS_ATIVOS["fios"]
    assert any(d == 8.0 for (d, _c) in PT.TABELA_ACOS_ATIVOS["fios"])
    assert 12.7 in PT.TABELA_ACOS_ATIVOS["cordoalhas"]["CP-190"]


def test_propriedades_cordoalha_rn_mesma_geometria_que_rb():
    """RN e RB da mesma categoria (CP-190) tem a mesma geometria/fptk -- a
    diferenca entre elas esta na relaxacao (PSI_1000_TIPICOS), nao na
    geometria do produto (8.4.1, ressalva do pacote P3). Corrigido na
    verificacao: a versao anterior chamava propriedades_cordoalha duas vezes
    com a MESMA categoria ("CP-190 RB", "CP-190 RB"), nunca exercitando o
    sufixo RN de fato."""
    rb = PT.propriedades_cordoalha(12.7, categoria="CP-190 RB")
    rn = PT.propriedades_cordoalha(12.7, categoria="CP-190 RN")
    assert rb["area_mm2"] == rn["area_mm2"]
    assert rb["fptk_MPa"] == rn["fptk_MPa"]
    # e as duas classes de relaxacao estao na tabela de perdas
    assert ("CP-190", "RN") in PT.PSI_1000_TIPICOS
    assert ("CP-190", "RB") in PT.PSI_1000_TIPICOS


# ---------------------------------------------------------------------------
# 8.4.6 (p. 50) -- dutilidade de fios e cordoalhas
# ---------------------------------------------------------------------------
def test_dutilidade_aco_ativo_acima_do_minimo():
    """eps_uk acima do minimo -> dutilidade normal (8.4.6, p.50)."""
    r = PT.dutilidade_aco_ativo(eps_uk_pmilh=35.0, minimo_pmilh=35.0 - 0.1)
    assert r.ok is True
    assert r.governante == "dutilidade normal"
    assert len(r.memoria) >= 1


def test_dutilidade_aco_ativo_no_minimo_exato_nao_e_normal():
    """No limite exato (eps_uk == minimo) a norma exige *maior que* o minimo,
    nao maior-ou-igual (8.4.6): fica do lado nao caracterizado."""
    r = PT.dutilidade_aco_ativo(eps_uk_pmilh=35.0, minimo_pmilh=35.0)
    assert r.ok is False


def test_dutilidade_aco_ativo_abaixo_do_minimo():
    r = PT.dutilidade_aco_ativo(eps_uk_pmilh=20.0, minimo_pmilh=35.0)
    assert r.ok is False
    assert r.governante == "abaixo do mínimo normativo"
