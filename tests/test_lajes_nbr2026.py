"""Testes de lajes_bastos.py contra a ABNT NBR 6118:2026.

Cobre os achados LAJ-01 a LAJ-07 da auditoria (AUDITORIA_NBR6118_2026.md).
Os valores esperados vem das formulas do nucleo normativo (nucleo_nbr6118.py,
ja testado contra a norma em test_nucleo_nbr6118.py) e, quando citados, dos
numeros de reproducao do achado (achados_brutos.md / verificacao_resultados.md).
"""

from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import lajes_bastos as laj  # noqa: E402
import nucleo_nbr6118 as nbr  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers de oraculo (formula antiga, so para medir a regressao) e formula
# generica de referencia (independente da implementacao, usada como oraculo).
# ---------------------------------------------------------------------------
def _dimensionar_antigo(Md_kncm: float, d_cm: float, fck_mpa: float,
                        fyk_mpa: float = 500.0, bw_cm: float = 100.0) -> tuple[float, float, float]:
    """Reproduz a formula de antes da correcao: alpha_c*eta_c = 0.85 e
    lambda = 0.8 fixos, qualquer que seja o fck (bug de LAJ-01/LAJ-02)."""
    fcd = (fck_mpa / 1.4) * 0.1
    fyd = (fyk_mpa / 1.15) * 0.1
    a = 0.272 * fcd * bw_cm
    b = -0.68 * fcd * bw_cm * d_cm
    c = abs(Md_kncm)
    disc = b * b - 4.0 * a * c
    x = (-b - math.sqrt(disc)) / (2.0 * a)
    beta_x = x / d_cm
    As = c / (fyd * (d_cm - 0.4 * x))
    return x, beta_x, As


def _dimensionar_oraculo(Md_kncm: float, d_cm: float, fck_mpa: float,
                         fyk_mpa: float = 500.0, bw_cm: float = 100.0) -> tuple[float, float]:
    """Oraculo independente: mesma fisica (bloco retangular, 17.2.2 e), mas
    escrito direto a partir do nucleo, sem chamar lajes_bastos."""
    tensao = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck_mpa))
    lam = nbr.lambda_retangulo(fck_mpa)
    fyd = nbr.mpa_para_kncm2(nbr.fyd(fyk_mpa))
    a = tensao * bw_cm * lam * lam / 2.0
    b = -tensao * bw_cm * lam * d_cm
    c = abs(Md_kncm)
    x = (-b - math.sqrt(b * b - 4.0 * a * c)) / (2.0 * a)
    As = c / (fyd * (d_cm - 0.5 * lam * x))
    return x, As


# ---------------------------------------------------------------------------
# LAJ-01 - bloco retangular sem eta_c (17.2.2 e, 8.2.10.1)
# ---------------------------------------------------------------------------
def test_LAJ01_dimensionar_flexao_usa_eta_c_e_lambda_do_nucleo():
    # Achado: fck=50, d=12, h=15, Md=6020 kN.cm/m -> obtido (bug) 12.466,
    # esperado (norma) 12.551 cm2/m (-0.7 % no bug).
    r = laj.dimensionar_flexao(Md_kncm=6020, d_cm=12.0, h_cm=15.0, fck_mpa=50.0)
    _, _, As_antigo = _dimensionar_antigo(6020, 12.0, 50.0)

    assert As_antigo == pytest.approx(12.4657, abs=1e-3)   # comportamento antigo (bug)
    assert r.As == pytest.approx(12.551, abs=1e-3)          # comportamento corrigido
    assert r.As > As_antigo                                 # a correcao pede mais aco, nao menos
    assert not r.erro


@pytest.mark.parametrize("fck", [45.0, 50.0, 55.0, 70.0, 90.0])
def test_LAJ01_bloco_retangular_bate_com_oraculo_do_nucleo(fck):
    # Md pequeno o bastante para nao esbarrar no limite de x/d em nenhuma classe.
    Md = 3000.0
    r = laj.dimensionar_flexao(Md_kncm=Md, d_cm=12.0, h_cm=15.0, fck_mpa=fck)
    x_ref, As_ref = _dimensionar_oraculo(Md, 12.0, fck)
    assert r.x == pytest.approx(x_ref, rel=1e-9)
    assert r.As == pytest.approx(max(As_ref, r.As_min), rel=1e-6)
    assert not r.erro


def test_LAJ01_eta_c_ja_reduz_tensao_em_c45_e_c50():
    # Nota da verificacao (lente NORMA-A2): eta_c muda em fck > 40, nao > 50.
    assert nbr.eta_c(45.0) < 1.0
    assert nbr.eta_c(50.0) < 1.0
    r45 = laj.dimensionar_flexao(Md_kncm=3000, d_cm=12.0, h_cm=15.0, fck_mpa=45.0)
    x_antigo, _, _ = _dimensionar_antigo(3000, 12.0, 45.0)
    assert r45.x > x_antigo   # tensao de bloco menor -> x maior para o mesmo Md


# ---------------------------------------------------------------------------
# LAJ-02 - limite de x/d do Grupo II (14.6.4.3)
# ---------------------------------------------------------------------------
def test_LAJ02_limite_xd_035_acima_de_c50_agora_e_acusado():
    # Achado: fck=70, d=12, h=15, Md=16800 -> bug: x/d=0.4106 sem aviso
    # (limite antigo fixo 0.45). Corrigido: limite vira 0.35 (norma) e o
    # x/d real tambem sobe (a tensao do bloco caiu com eta_c e lambda(70)).
    x_antigo, beta_x_antigo, _ = _dimensionar_antigo(16800, 12.0, 70.0)
    assert beta_x_antigo == pytest.approx(0.4106, abs=1e-3)
    assert beta_x_antigo < laj.LIMITE_BETA_X   # bug: passava batido no limite antigo

    r = laj.dimensionar_flexao(Md_kncm=16800, d_cm=12.0, h_cm=15.0, fck_mpa=70.0)
    assert r.beta_x == pytest.approx(0.6471, abs=1e-3)
    assert r.beta_x > nbr.xd_limite_dutilidade(70.0)
    assert r.erro != ""
    assert "14.6.4.3" in r.erro


def test_LAJ02_limite_vem_de_xd_limite_dutilidade_por_fck():
    r50 = laj.dimensionar_flexao(Md_kncm=15000, d_cm=12.0, h_cm=15.0, fck_mpa=50.0)
    r70 = laj.dimensionar_flexao(Md_kncm=8200, d_cm=12.0, h_cm=15.0, fck_mpa=70.0)
    # fck=50: ainda usa 0.45; fck=70 com x/d ~ mesma ordem de grandeza ja
    # deve poder violar 0.35 (limite mais apertado do Grupo II).
    assert nbr.xd_limite_dutilidade(50.0) == 0.45
    assert nbr.xd_limite_dutilidade(70.0) == 0.35
    for r, fck in ((r50, 50.0), (r70, 70.0)):
        limite = nbr.xd_limite_dutilidade(fck)
        if r.beta_x > limite:
            assert r.erro != ""
        else:
            assert r.erro == ""


def test_LAJ02_sem_violacao_nao_acusa_erro():
    r = laj.dimensionar_flexao(Md_kncm=3000, d_cm=12.0, h_cm=15.0, fck_mpa=90.0)
    assert r.beta_x < nbr.xd_limite_dutilidade(90.0)
    assert r.erro == ""


# ---------------------------------------------------------------------------
# LAJ-03 - fct_m_kncm2 sem o ramo de fck > 50 (8.2.5)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fck, fct_m_mpa_esperado", [
    (45.0, 0.3 * 45.0 ** (2 / 3)),
    (50.0, 0.3 * 50.0 ** (2 / 3)),
    (55.0, 2.12 * math.log(1 + 0.1 * 63)),
    (70.0, 2.12 * math.log(1 + 0.1 * 78)),
    (90.0, 2.12 * math.log(1 + 0.1 * 98)),
])
def test_LAJ03_fct_m_kncm2_delega_ao_nucleo(fck, fct_m_mpa_esperado):
    assert laj.fct_m_kncm2(fck) == pytest.approx(fct_m_mpa_esperado * 0.1, rel=1e-9)


def test_LAJ03_fct_m_kncm2_valores_do_achado():
    # Achado: fck=70 -> 5.0955 (bug, formula do Grupo I) x 4.6105 MPa (norma).
    assert laj.fct_m_kncm2(70.0) * 10.0 == pytest.approx(4.6105, abs=1e-4)
    assert 0.3 * 70.0 ** (2 / 3) == pytest.approx(5.0955, abs=1e-4)   # o valor do bug, p/ registro
    assert laj.fct_m_kncm2(90.0) * 10.0 == pytest.approx(5.0446, abs=1e-4)


def test_LAJ03_momento_fissuracao_usa_fct_m_corrigido():
    # momento_fissuracao (17.3.1) usa fct_m_kncm2; C70 deve refletir o ramo novo.
    Mr70 = laj.momento_fissuracao(100.0, 15.0, 70.0)
    Mr_bug = 1.5 * (0.3 * 70.0 ** (2 / 3) * 0.1) * (100.0 * 15.0 ** 3 / 12.0) / 7.5
    assert Mr70 < Mr_bug   # fct,m correto (Grupo II) e menor que a formula do Grupo I extrapolada


# ---------------------------------------------------------------------------
# LAJ-04 - Ecs_kncm2 sem o ramo de fck > 50 (8.2.8)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fck", [45.0, 50.0, 55.0, 70.0, 90.0])
def test_LAJ04_Ecs_kncm2_delega_ao_nucleo(fck):
    assert laj.Ecs_kncm2(fck) == pytest.approx(nbr.mpa_para_kncm2(nbr.Ecs(fck)), rel=1e-12)


def test_LAJ04_Ecs_valores_do_achado():
    # Achado: Ecs(70) 45681.6 (bug) x 42357.2 MPa (norma); Ecs(90) -> +13.8 % no bug.
    assert laj.Ecs_kncm2(70.0) * 10.0 == pytest.approx(42357.2, abs=0.5)
    assert laj.Ecs_kncm2(90.0) * 10.0 == pytest.approx(46703.0, abs=1.0)
    Eci_bug = 5600.0 * math.sqrt(70.0)
    alpha_i_bug = min(0.8 + 0.2 * 70.0 / 80.0, 1.0)
    Ecs_bug = alpha_i_bug * Eci_bug
    assert Ecs_bug == pytest.approx(45681.6, abs=0.5)   # valor do bug, p/ registro
    assert laj.Ecs_kncm2(70.0) * 10.0 < Ecs_bug


def test_LAJ04_alpha_E_ainda_funciona():
    assert laj.Ecs_kncm2(30.0, alpha_E=1.2) == pytest.approx(
        nbr.mpa_para_kncm2(nbr.Ecs(30.0, 1.2)), rel=1e-12)


# ---------------------------------------------------------------------------
# LAJ-05 - tau_Rd sem o teto de fck = 60 MPa (19.4.1)
# ---------------------------------------------------------------------------
def test_LAJ05_cortante_resistente_laje_aplica_teto_60():
    # Achado: bw=100, d=15, As=8, fck=70 -> VRd1 195.79 (bug) x 167.33 kN/m (norma).
    v70 = laj.cortante_resistente_laje(bw_cm=100.0, d_cm=15.0, As_long_cm2=8.0, fck_mpa=70.0)
    v60 = laj.cortante_resistente_laje(bw_cm=100.0, d_cm=15.0, As_long_cm2=8.0, fck_mpa=60.0)
    v90 = laj.cortante_resistente_laje(bw_cm=100.0, d_cm=15.0, As_long_cm2=8.0, fck_mpa=90.0)

    assert v70 == pytest.approx(167.33, abs=0.02)
    assert v70 == v60 == v90            # capped: mesmo VRd1 de C60 em diante

    def _antigo(fck):
        fctd = (0.7 * 0.3 * fck ** (2 / 3) * 0.1) / 1.4
        tau_rd = 0.25 * fctd
        rho1 = min(8.0 / (100.0 * 15.0), 0.02)
        k = max(1.6 - 15.0 / 100.0, 1.0)
        return tau_rd * k * (1.2 + 40.0 * rho1) * 100.0 * 15.0

    assert _antigo(70.0) == pytest.approx(195.79, abs=0.02)   # valor do bug, p/ registro
    assert v70 < _antigo(70.0)


@pytest.mark.parametrize("fck", [30.0, 45.0, 55.0])
def test_LAJ05_abaixo_de_60_nao_muda(fck):
    # Para fck <= 60 o teto nao entra em jogo: resultado deve bater com a
    # formula direta usando tau_Rd = 0.25 fctd(fck) sem cap.
    v = laj.cortante_resistente_laje(bw_cm=100.0, d_cm=15.0, As_long_cm2=8.0, fck_mpa=fck)
    tau_rd_esperado = nbr.mpa_para_kncm2(0.25 * nbr.fctd(fck))
    rho1 = min(8.0 / (100.0 * 15.0), 0.02)
    k = max(1.6 - 15.0 / 100.0, 1.0)
    esperado = tau_rd_esperado * k * (1.2 + 40.0 * rho1) * 100.0 * 15.0
    assert v == pytest.approx(esperado, rel=1e-9)


# ---------------------------------------------------------------------------
# LAJ-06 - rho_min so ate C50 (Tabela 17.3)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fck", [45, 50, 55, 60, 70, 90])
def test_LAJ06_as_min_laje_cobre_tabela_17_3_completa(fck):
    esperado = nbr.RHO_MIN_TABELA_17_3[fck] / 100.0 * 100.0 * 15.0  # bw=100, h=15
    assert laj.as_min_laje(bw_cm=100.0, h_cm=15.0, fck_mpa=float(fck)) == pytest.approx(esperado, rel=1e-9)


def test_LAJ06_valores_do_achado():
    # Achado: fck=60, h=15 -> 3.12 (bug, cai no C50) x 3.285 cm2/m (norma); fck=90 -> 3.84.
    as_min_60 = laj.as_min_laje(bw_cm=100.0, h_cm=15.0, fck_mpa=60.0)
    as_min_90 = laj.as_min_laje(bw_cm=100.0, h_cm=15.0, fck_mpa=90.0)
    assert as_min_60 == pytest.approx(3.285, abs=1e-3)
    assert as_min_90 == pytest.approx(3.84, abs=1e-3)
    as_min_bug = 0.00208 * 100.0 * 15.0
    assert as_min_bug == pytest.approx(3.12, abs=1e-3)   # valor do bug (C50), p/ registro
    assert as_min_60 > as_min_bug
    assert as_min_90 > as_min_bug


def test_LAJ06_fator_067_duas_direcoes_continua_no_modulo():
    # O fator da Tabela 19.1 e uma decisao do modulo (nao do nucleo); confere
    # que continua aplicado em cima do rho_min corrigido.
    cheio = laj.as_min_laje(bw_cm=100.0, h_cm=15.0, fck_mpa=70.0,
                            armadura_positiva=False, duas_direcoes=True)
    reduzido = laj.as_min_laje(bw_cm=100.0, h_cm=15.0, fck_mpa=70.0,
                               armadura_positiva=True, duas_direcoes=True)
    assert reduzido == pytest.approx(0.67 * cheio, rel=1e-9)


def test_LAJ06_dimensionar_flexao_aplica_as_min_corrigido():
    # Md muito pequeno: o dimensionamento deve cair no As,min da Tabela 17.3
    # completa, nao no valor truncado do C50.
    r = laj.dimensionar_flexao(Md_kncm=50.0, d_cm=12.0, h_cm=15.0, fck_mpa=90.0)
    assert r.As == pytest.approx(r.As_min)
    assert r.As_min == pytest.approx(3.84, abs=1e-3)


# ---------------------------------------------------------------------------
# LAJ-07 - gama_n de laje em balanco ausente (13.2.4.1, Tabela 13.2)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("h_cm, gama_n_esperado", [
    (10.0, 1.45), (11.0, 1.40), (12.0, 1.35), (15.0, 1.20), (18.0, 1.05),
    (19.0, 1.00), (25.0, 1.00),
])
def test_LAJ07_gama_n_laje_balanco_tabela_13_2(h_cm, gama_n_esperado):
    assert laj.gama_n_laje_balanco(h_cm) == pytest.approx(gama_n_esperado, abs=1e-9)


def test_LAJ07_gama_n_abaixo_do_minimo_normativo_levanta_erro():
    # 13.2.4.1 c): espessura minima de 10 cm para laje em balanco.
    with pytest.raises(nbr.FaixaNormativaError):
        laj.gama_n_laje_balanco(9.0)


def test_LAJ07_momentos_uma_direcao_balanco_sem_h_avisa_e_nao_aplica_gama_n():
    with pytest.warns(UserWarning, match="gama_n"):
        m = laj.momentos_uma_direcao(p_kn_m2=6.83, lef_cm=163.0, vinculacao="balanco")
    assert "gama_n" not in m
    # Reproduz teste_balanco_L1 (apostila): sem gama_n, |M_eng|+gradil ~ 989.
    M_eng_total = abs(m["M_eng"]) + 0.5 * 1.63 * 100.0
    assert M_eng_total == pytest.approx(988.8, abs=1.0)


def test_LAJ07_momentos_uma_direcao_balanco_com_h_aplica_gama_n():
    # Achado LAJ-07: teste_balanco_L1 com h=12 cm -> momento x 1.35 (gama_n
    # da Tabela 13.2); h=10 cm -> x 1.45 (-31 % era o efeito do bug).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")   # so p/ obter o valor sem gama_n, sem falhar no aviso
        m_sem = laj.momentos_uma_direcao(p_kn_m2=6.83, lef_cm=163.0, vinculacao="balanco")

    with warnings.catch_warnings():
        warnings.simplefilter("error")   # nao pode emitir aviso quando h_cm e dado
        m12 = laj.momentos_uma_direcao(p_kn_m2=6.83, lef_cm=163.0, vinculacao="balanco", h_cm=12.0)
        m10 = laj.momentos_uma_direcao(p_kn_m2=6.83, lef_cm=163.0, vinculacao="balanco", h_cm=10.0)

    assert m12["gama_n"] == pytest.approx(1.35, abs=1e-9)
    assert m10["gama_n"] == pytest.approx(1.45, abs=1e-9)
    assert m12["M_eng"] == pytest.approx(m_sem["M_eng"] * 1.35, rel=1e-9)
    assert m10["M_eng"] == pytest.approx(m_sem["M_eng"] * 1.45, rel=1e-9)


def test_LAJ07_reproduz_teste_balanco_L1_h12_multiplica_por_135():
    # Brief: "com a entrada do teste_balanco_L1, h = 12 cm da M x 1,35."
    # teste_balanco_L1: p=6.83 kN/m2, lef=163 cm, + gradil 0.5 kN/m (momento
    # concentrado somado ao engaste fora desta funcao). Sem gama_n (bug):
    # M_eng_total ~ 988.8 kN.cm/m. A NBR 13.2.4.1 manda multiplicar TODOS os
    # esforcos solicitantes do balanco por gama_n, inclusive o do gradil; por
    # isso o teste aplica o gama_n devolvido tambem a parcela do gradil.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m_sem = laj.momentos_uma_direcao(p_kn_m2=6.83, lef_cm=163.0, vinculacao="balanco")
    M_sem_total = abs(m_sem["M_eng"]) + 0.5 * 1.63 * 100.0
    assert M_sem_total == pytest.approx(988.8, abs=0.1)

    m12 = laj.momentos_uma_direcao(p_kn_m2=6.83, lef_cm=163.0, vinculacao="balanco", h_cm=12.0)
    gn = m12["gama_n"]
    assert gn == pytest.approx(1.35, abs=1e-9)
    M_com_total = abs(m12["M_eng"]) + 0.5 * 1.63 * 100.0 * gn
    assert M_com_total == pytest.approx(M_sem_total * 1.35, rel=1e-9)
    assert M_com_total == pytest.approx(1334.9, abs=0.2)   # achado LAJ-07 (norma)


def test_LAJ07_outras_vinculacoes_ignoram_h_cm_sem_aviso():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        m = laj.momentos_uma_direcao(p_kn_m2=6.83, lef_cm=163.0, vinculacao="apoio_simples", h_cm=12.0)
    assert "gama_n" not in m


def test_LAJ07_dimensionar_flexao_aceita_gama_n():
    # "quem chama aplica o gama_n no dimensionamento": parametro no fim, com
    # padrao neutro (1.0), compatibilidade preservada.
    r_sem = laj.dimensionar_flexao(Md_kncm=907.33, d_cm=8.0, h_cm=12.0, fck_mpa=25.0)
    r_com = laj.dimensionar_flexao(Md_kncm=907.33, d_cm=8.0, h_cm=12.0, fck_mpa=25.0, gama_n=1.35)
    assert r_sem.Md == pytest.approx(907.33)
    assert r_com.Md == pytest.approx(907.33 * 1.35)
    assert r_com.As > r_sem.As


# ---------------------------------------------------------------------------
# Compatibilidade: nomes legados continuam exportados (LAJ-01/02/06)
# ---------------------------------------------------------------------------
def test_nomes_legados_continuam_exportados():
    assert laj.LIMITE_BETA_X == 0.45
    assert laj.RHO_MIN_TABELA[50] == pytest.approx(0.00208)
    assert laj.EPS_CU == 3.5


# ---------------------------------------------------------------------------
# Decisao 1: fora de 20-90 MPa, a FaixaNormativaError do nucleo deve subir
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fn, kwargs", [
    (laj.dimensionar_flexao, dict(Md_kncm=1000.0, d_cm=12.0, h_cm=15.0, fck_mpa=15.0)),
    (laj.fct_m_kncm2, dict(fck_mpa=95.0)),
    (laj.Ecs_kncm2, dict(fck_mpa=15.0)),
    (laj.cortante_resistente_laje, dict(bw_cm=100.0, d_cm=15.0, As_long_cm2=8.0, fck_mpa=95.0)),
    (laj.as_min_laje, dict(bw_cm=100.0, h_cm=15.0, fck_mpa=95.0)),
])
def test_fck_fora_da_faixa_propaga_erro_do_nucleo(fn, kwargs):
    with pytest.raises(nbr.FaixaNormativaError):
        fn(**kwargs)
