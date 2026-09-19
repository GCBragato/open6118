"""Testes do P29 -- Pilar-parede (NBR 6118:2026, 15.9.2, 15.9.3, 18.5).

Valores esperados tirados das imagens das páginas do PDF (SCRATCH/nbr_png):
p132 (15.9.2, Figura 15.4), p133 (15.9.3, Figura 15.5), p174 (18.5).
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import pilares_nbr6118 as PIL  # noqa: E402
import pilares_parede_nbr6118 as PP  # noqa: E402


# ---------------------------------------------------------------------------
# 15.9.2 -- le_lamina_cm, os 4 casos da Figura 15.4 (p. 132)
# ---------------------------------------------------------------------------
def test_le_lamina_caso_a():
    """Caso A: topo livre, base engastada -> le = l, qualquer beta."""
    assert PP.le_lamina_cm(l_cm=300.0, b_cm=100.0, vinculacao="A") == pytest.approx(300.0)
    assert PP.le_lamina_cm(l_cm=300.0, b_cm=300.0, vinculacao="a") == pytest.approx(300.0)


def test_le_lamina_caso_b_beta_1():
    """Caso B em beta=1: le = l/(1+(1/3)^2) = l/(10/9) = 0,9*l."""
    l = 300.0
    le = PP.le_lamina_cm(l_cm=l, b_cm=l, vinculacao="B")  # beta = l/b = 1
    esperado = l / (1.0 + (1.0 / 3.0) ** 2)
    assert le == pytest.approx(esperado)
    assert le == pytest.approx(0.9 * l)


def test_le_lamina_caso_b_piso_03l():
    """Caso B: le >= 0,3*l mesmo com beta muito grande (b muito pequeno)."""
    l = 300.0
    b = 1.0  # beta = 300 -> formula bruta daria valor bem menor que 0,3l
    le = PP.le_lamina_cm(l_cm=l, b_cm=b, vinculacao="B")
    assert le == pytest.approx(0.3 * l)


def test_le_lamina_caso_c_beta_1_continuidade():
    """Caso C em beta=1: os dois ramos (beta<=1 e beta>1) dao le = l/2."""
    l = 300.0
    le = PP.le_lamina_cm(l_cm=l, b_cm=l, vinculacao="C")  # beta = 1
    assert le == pytest.approx(l / 2.0)
    # ramo beta<=1: l/(1+beta^2) = l/2 em beta=1
    assert le == pytest.approx(l / (1.0 + 1.0 ** 2))
    # ramo beta>1: l/(2*beta) tambem daria l/2 em beta=1 (continuidade)
    assert le == pytest.approx(l / (2.0 * 1.0))


def test_le_lamina_caso_c_beta_menor_que_1():
    """Caso C, beta=0,5: le = l/(1+0,25) = l/1,25."""
    l = 300.0
    b = 600.0  # beta = 0,5
    le = PP.le_lamina_cm(l_cm=l, b_cm=b, vinculacao="C")
    assert le == pytest.approx(l / 1.25)


def test_le_lamina_caso_c_beta_maior_que_1():
    """Caso C, beta=2: le = l/(2*2) = l/4."""
    l = 400.0
    b = 200.0  # beta = 2
    le = PP.le_lamina_cm(l_cm=l, b_cm=b, vinculacao="C")
    assert le == pytest.approx(l / 4.0)


def test_le_lamina_caso_d_beta_igual_7():
    """Caso D, beta=7,0 exato: le = 2b (<= l)."""
    b = 100.0
    l = 700.0  # beta = l/b = 7,0
    le = PP.le_lamina_cm(l_cm=l, b_cm=b, vinculacao="D")
    assert le == pytest.approx(2.0 * b)


def test_le_lamina_caso_d_beta_menor_que_7_adota_caso_b():
    """Caso D, beta<7,0: adota-se o caso B com a mesma beta."""
    b = 100.0
    l = 500.0  # beta = 5,0 < 7,0
    le_d = PP.le_lamina_cm(l_cm=l, b_cm=b, vinculacao="D")
    le_b = PP.le_lamina_cm(l_cm=l, b_cm=b, vinculacao="B")
    assert le_d == pytest.approx(le_b)


def test_le_lamina_casos_b_e_d_nao_coincidem_em_beta_7():
    """Descontinuidade da propria norma: em beta=7,0 exato, o caso D (le=2b)
    e o caso B (mesma beta) NAO coincidem -- documentado na docstring de
    le_lamina_cm e na secao 8 (riscos) do plano."""
    b = 100.0
    l = 700.0  # beta = 7,0
    le_d = PP.le_lamina_cm(l_cm=l, b_cm=b, vinculacao="D")
    le_b_mesma_beta = l / (1.0 + (7.0 / 3.0) ** 2)
    assert le_d == pytest.approx(2.0 * b)
    assert le_b_mesma_beta == pytest.approx(l / (1.0 + (7.0 / 3.0) ** 2))
    assert le_d != pytest.approx(le_b_mesma_beta)


def test_le_lamina_vinculacao_invalida():
    with pytest.raises(ValueError):
        PP.le_lamina_cm(l_cm=300.0, b_cm=100.0, vinculacao="E")


def test_le_lamina_dimensoes_nao_positivas():
    with pytest.raises(nbr.FaixaNormativaError):
        PP.le_lamina_cm(l_cm=0.0, b_cm=100.0, vinculacao="A")
    with pytest.raises(nbr.FaixaNormativaError):
        PP.le_lamina_cm(l_cm=300.0, b_cm=-10.0, vinculacao="A")


# ---------------------------------------------------------------------------
# 15.9.2 -- esbeltez_lamina e o fator 0,85
# ---------------------------------------------------------------------------
def test_esbeltez_lamina_formula():
    """lambda_i = 3,46 * le / h."""
    lam = PP.esbeltez_lamina(le_cm=300.0, h_cm=20.0)
    assert lam == pytest.approx(3.46 * 300.0 / 20.0)


def test_esbeltez_lamina_fator_085_reduz_15_por_cento():
    """Engastado topo e base, beta<=1: lambda_i * 0,85 reduz exatamente 15%."""
    le, h = 300.0, 20.0
    sem_reducao = PP.esbeltez_lamina(le_cm=le, h_cm=h)
    com_reducao = PP.esbeltez_lamina(
        le_cm=le, h_cm=h, engastado_topo_e_base=True, beta=1.0
    )
    assert com_reducao == pytest.approx(sem_reducao * 0.85)
    assert com_reducao == pytest.approx(sem_reducao * (1.0 - 0.15))


def test_esbeltez_lamina_fator_085_nao_aplica_beta_maior_que_1():
    """Beta > 1: o fator 0,85 NAO se aplica, mesmo engastado nos dois topos."""
    le, h = 300.0, 20.0
    sem_reducao = PP.esbeltez_lamina(le_cm=le, h_cm=h)
    com_beta_alto = PP.esbeltez_lamina(
        le_cm=le, h_cm=h, engastado_topo_e_base=True, beta=1.01
    )
    assert com_beta_alto == pytest.approx(sem_reducao)


def test_esbeltez_lamina_h_nao_positivo():
    with pytest.raises(nbr.FaixaNormativaError):
        PP.esbeltez_lamina(le_cm=300.0, h_cm=0.0)


# ---------------------------------------------------------------------------
# 15.9.2 -- dispensa_efeito_localizado, limite lambda_i < 35
# ---------------------------------------------------------------------------
def test_dispensa_lambda_igual_35_aceito():
    """lambda_i = 35,00 exato: aceito (tolerância de 1e-9), dispensa a análise."""
    res = PP.dispensa_efeito_localizado([35.0, 20.0], fixado_as_lajes=True)
    assert res.ok is True


def test_dispensa_lambda_35_01_recusado():
    """lambda_i = 35,01: recusado, não dispensa a análise dos efeitos localizados."""
    res = PP.dispensa_efeito_localizado([35.01, 10.0], fixado_as_lajes=True)
    assert res.ok is False
    assert "35.01" in res.governante


def test_dispensa_todas_laminas_devem_atender():
    """Uma única lâmina com lambda_i >= 35 já impede a dispensa geral."""
    res = PP.dispensa_efeito_localizado([10.0, 20.0, 40.0], fixado_as_lajes=True)
    assert res.ok is False


def test_dispensa_exige_fixacao_as_lajes():
    """Mesmo com todas as lâminas dentro do limite, sem fixação às lajes não dispensa."""
    res = PP.dispensa_efeito_localizado([10.0, 20.0], fixado_as_lajes=False)
    assert res.ok is False


def test_dispensa_lista_vazia_erro():
    with pytest.raises(ValueError):
        PP.dispensa_efeito_localizado([])


def test_dispensa_fixacao_por_lamina_uma_nao_fixada_recusa():
    """15.9.2 a) e por lamina: mesmo com ambas lambda_i < 35, uma lamina nao
    fixada as lajes (a segunda) ja impede a dispensa geral -- ver PDF p. 132,
    'a base e o topo de CADA lamina devem ser convenientemente fixados'."""
    res = PP.dispensa_efeito_localizado([10.0, 15.0], fixado_as_lajes=[True, False])
    assert res.ok is False
    assert res.fixado_as_lajes == (True, False)


def test_dispensa_fixacao_por_lamina_todas_fixadas_aceita():
    """Mesmas lambda_i do teste anterior, mas as duas lâminas fixadas: dispensa."""
    res = PP.dispensa_efeito_localizado([10.0, 15.0], fixado_as_lajes=[True, True])
    assert res.ok is True


def test_dispensa_fixacao_por_lamina_tamanho_diferente_erro():
    """fixado_as_lajes por lâmina deve ter o mesmo tamanho de lambda_i."""
    with pytest.raises(ValueError):
        PP.dispensa_efeito_localizado([10.0, 15.0], fixado_as_lajes=[True])


def test_esbeltez_e_dispensa_encadeadas_engastado_beta_1():
    """Cadeia completa: le_lamina -> esbeltez_lamina (com 0,85) -> dispensa,
    caso C em beta=1, engastado nos dois topos."""
    l, b, h = 300.0, 300.0, 20.0  # beta = 1
    le = PP.le_lamina_cm(l_cm=l, b_cm=b, vinculacao="C")  # l/2 = 150
    lam = PP.esbeltez_lamina(
        le_cm=le, h_cm=h, engastado_topo_e_base=True, beta=l / b
    )
    esperado = 3.46 * 150.0 / 20.0 * 0.85
    assert lam == pytest.approx(esperado)
    res = PP.dispensa_efeito_localizado([lam], fixado_as_lajes=True)
    assert res.ok is True  # 25,97*0,85 = 22,08 < 35


# ---------------------------------------------------------------------------
# 15.9.3 -- decompor_em_faixas (Figura 15.5, p. 133)
# ---------------------------------------------------------------------------
def test_largura_faixa_regra_3h():
    """ai = 3h, sem atingir o teto de 100 cm."""
    assert PP.largura_faixa_cm(h_cm=20.0) == pytest.approx(60.0)


def test_largura_faixa_teto_100cm():
    """ai = 3h limitado a 100 cm: h=40 -> 3h=120 > 100 -> ai=100."""
    assert PP.largura_faixa_cm(h_cm=40.0) == pytest.approx(100.0)


def test_largura_faixa_h_nao_positivo():
    with pytest.raises(nbr.FaixaNormativaError):
        PP.largura_faixa_cm(h_cm=0.0)


def test_nd_x_recupera_Nd_e_M1xd_por_integracao():
    """Integrando nd(x) e x*nd(x) numericamente em b, recupera-se Nd e M1xd."""
    Nd, M1xd, b = 1000.0, 5000.0, 300.0
    n = 200000
    dx = b / n
    soma_n = 0.0
    soma_xn = 0.0
    for i in range(n):
        x = -b / 2.0 + (i + 0.5) * dx
        nd = PP.nd_x_kn_por_cm(x_cm=x, Nd_kn=Nd, M1xd_kncm=M1xd, b_cm=b)
        soma_n += nd * dx
        soma_xn += x * nd * dx
    assert soma_n == pytest.approx(Nd, rel=1e-6)
    assert soma_xn == pytest.approx(M1xd, rel=1e-6)


def test_nd_x_constante_com_M1xd_zero():
    """M1xd=0: nd(x) constante e igual a Nd/b em qualquer x."""
    Nd, b = 900.0, 300.0
    for x in (-100.0, 0.0, 100.0):
        nd = PP.nd_x_kn_por_cm(x_cm=x, Nd_kn=Nd, M1xd_kncm=0.0, b_cm=b)
        assert nd == pytest.approx(Nd / b)


def test_decompor_em_faixas_soma_Ni_igual_Nd():
    """Soma das Ni de todas as faixas = Nd, com M1xd != 0 (b nao multiplo de ai)."""
    Nd, M1xd = 2400.0, 30000.0
    b, h = 370.0, 20.0  # ai = 60 cm -> faixas de 60,60,60,60,60,10
    faixas = PP.decompor_em_faixas(b_cm=b, h_cm=h, Nd_kn=Nd, M1xd_kncm=M1xd)
    soma_Ni = sum(f.Ni_kn for f in faixas)
    assert soma_Ni == pytest.approx(Nd, rel=1e-9)


def test_decompor_em_faixas_carga_centrada_Ni_igual_em_todas():
    """M1xd=0 (carga centrada): nd(x) constante e Ni = Nd*ai/b, igual em
    todas as faixas de largura completa ai (teste sugerido do brief P29)."""
    Nd = 1800.0
    b, h = 300.0, 20.0  # ai = 60 cm -> exatamente 5 faixas iguais
    faixas = PP.decompor_em_faixas(b_cm=b, h_cm=h, Nd_kn=Nd, M1xd_kncm=0.0)
    assert len(faixas) == 5
    ai = PP.largura_faixa_cm(h_cm=h)
    esperado = Nd * ai / b
    for f in faixas:
        assert f.ai_cm == pytest.approx(ai)
        assert f.Ni_kn == pytest.approx(esperado)


def test_decompor_em_faixas_lambda_igual_90_aceito():
    """O processo aproximado so vale para lambda_i de cada lamina < 90
    (paragrafo antes de 15.9.3, PDF p. 133). Igual ao limite de 35 lâminas de
    15.9.2, o limite e comparado com tolerância relativa de 1e-9 (mesma
    convenção do módulo): lambda_i = 90,00 exato e aceito."""
    faixas = PP.decompor_em_faixas(
        b_cm=300.0, h_cm=20.0, Nd_kn=1800.0, M1xd_kncm=0.0,
        lambda_i_laminas=[90.0, 50.0],
    )
    assert len(faixas) == 5


def test_decompor_em_faixas_lambda_90_01_recusado():
    """lambda_i = 90,01 excede o limite e recusa a decomposicao aproximada."""
    with pytest.raises(nbr.FaixaNormativaError):
        PP.decompor_em_faixas(
            b_cm=300.0, h_cm=20.0, Nd_kn=1800.0, M1xd_kncm=0.0,
            lambda_i_laminas=[90.01],
        )


def test_decompor_em_faixas_sem_lambda_i_nao_verifica():
    """lambda_i_laminas e opcional (padrao None): sem informa-lo, nao ha
    checagem e o comportamento anterior e reproduzido (retrocompatibilidade)."""
    faixas = PP.decompor_em_faixas(b_cm=300.0, h_cm=20.0, Nd_kn=1800.0, M1xd_kncm=0.0)
    assert len(faixas) == 5


def test_decompor_em_faixas_largura_total_igual_b():
    """A soma das larguras das faixas recompõe b, mesmo quando não é múltiplo de ai."""
    b, h = 250.0, 20.0  # ai = 60 -> faixas 60,60,60,60,10
    faixas = PP.decompor_em_faixas(b_cm=b, h_cm=h, Nd_kn=1000.0, M1xd_kncm=0.0)
    assert sum(f.ai_cm for f in faixas) == pytest.approx(b)
    assert faixas[-1].ai_cm == pytest.approx(10.0)


def test_decompor_em_faixas_myid_m1yd_vezes_ai():
    """Myid = m1yd * ai, sem piso de M1d,min quando este não é informado."""
    b, h = 300.0, 20.0
    m1yd = 2.0  # kN.cm/cm
    faixas = PP.decompor_em_faixas(
        b_cm=b, h_cm=h, Nd_kn=1000.0, M1xd_kncm=0.0, m1yd_kncm_por_cm=m1yd
    )
    ai = PP.largura_faixa_cm(h_cm=h)
    for f in faixas:
        assert f.Myid_kncm == pytest.approx(m1yd * f.ai_cm)


def test_decompor_em_faixas_myid_piso_M1d_min():
    """Myid >= M1d,min quando M1d,min é informado (imperfeições geométricas, 11.3.3.4.3)."""
    b, h = 300.0, 20.0
    m1yd = 0.1  # bem pequeno -> m1yd*ai fica abaixo do M1d,min
    M1d_min = nbr.M1d_min_kncm(Nd_kn=1000.0, h_cm=h)  # >0
    faixas = PP.decompor_em_faixas(
        b_cm=b, h_cm=h, Nd_kn=1000.0, M1xd_kncm=0.0,
        m1yd_kncm_por_cm=m1yd, M1d_min_kncm=M1d_min,
    )
    for f in faixas:
        assert f.Myid_kncm >= M1d_min - 1e-9
        assert f.Myid_kncm == pytest.approx(M1d_min)  # m1yd*ai < M1d_min em todas


def test_decompor_em_faixas_b_nao_positivo():
    with pytest.raises(nbr.FaixaNormativaError):
        PP.decompor_em_faixas(b_cm=0.0, h_cm=20.0, Nd_kn=1000.0, M1xd_kncm=0.0)


def test_faixa_encadeada_com_pilares_nbr6118():
    """Uso encadeado: a Faixa (Ni, Myid) decomposta aqui alimenta o método do
    pilar-padrão de pilares_nbr6118 (P25), como pilar isolado equivalente
    (15.9.3, último parágrafo) -- a norma dispensa alfa_b > 0,6 quando
    Myid < M1d,min."""
    b, h = 300.0, 20.0
    Nd, M1xd = 1500.0, 0.0
    faixas = PP.decompor_em_faixas(b_cm=b, h_cm=h, Nd_kn=Nd, M1xd_kncm=M1xd)
    f = faixas[0]
    le_faixa_cm = 280.0  # geometria fora do plano da faixa (fora do escopo deste módulo)
    fck = 30.0
    Ac = f.ai_cm * h
    M1d_min = nbr.M1d_min_kncm(Nd_kn=f.Ni_kn, h_cm=h)
    alpha_b_usado = 0.6 if f.Myid_kncm < M1d_min else 1.0
    resultado = PIL.Mdtot_curvatura_aprox(
        Nd_kn=f.Ni_kn, le_cm=le_faixa_cm, h_cm=h, fck_mpa=fck,
        M1d_A_kncm=f.Myid_kncm, alpha_b_val=alpha_b_usado, Ac_cm2=Ac,
    )
    assert resultado["Md_tot_kncm"] >= resultado["M1d_A_ef_kncm"] - 1e-9


# ---------------------------------------------------------------------------
# 18.5 -- Armadura transversal mínima do pilar-parede (p. 174)
# ---------------------------------------------------------------------------
def test_As_transversal_25_por_cento():
    """As,longitudinal=10cm2/m na maior face -> As,transversal_min=2,5cm2/m
    (teste sugerido do brief P29)."""
    As_t = PP.As_transversal_pilar_parede_cm2_por_m(As_longitudinal_cm2_por_m=10.0)
    assert As_t == pytest.approx(2.5)


def test_As_transversal_proporcional():
    assert PP.As_transversal_pilar_parede_cm2_por_m(4.0) == pytest.approx(1.0)
    assert PP.As_transversal_pilar_parede_cm2_por_m(0.0) == pytest.approx(0.0)


def test_As_transversal_negativo_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        PP.As_transversal_pilar_parede_cm2_por_m(-1.0)
