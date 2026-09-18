"""Testes das correcoes de vigas_bastos.py e viga_servico_bastos.py contra a
ABNT NBR 6118:2026 (auditoria de 18/09/2026 - AUDITORIA_NBR6118_2026.md).

Cobre os achados VIG-01 a VIG-08, VIG-10 (obrigatorios) e VIG-09 (melhoria
opcional). Os valores esperados saem de duas fontes:

  - a reproducao numerica de cada achado em SCRATCH/achados_brutos.md e
    SCRATCH/verificacao_resultados.md (valores literais, comentados);
  - um "oraculo" independente, escrito neste arquivo, que recombina as
    primitivas ja testadas do nucleo normativo (nucleo_nbr6118.py, ver
    tests/test_nucleo_nbr6118.py) pela mesma formula da norma - sem chamar
    as funcoes de vigas_bastos.py/viga_servico_bastos.py que estao sob
    teste, para nao validar o codigo contra si mesmo.

Classes cobertas onde fck entra na formula: C45, C50, C55, C70 e C90
(pedido do brief de correcao).
"""

from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import vigas_bastos as vig  # noqa: E402
import viga_servico_bastos as vser  # noqa: E402


FCKS_COBERTURA = [45.0, 50.0, 55.0, 70.0, 90.0]


# ---------------------------------------------------------------------------
# Oraculos independentes (nucleo normativo, sem chamar o codigo sob teste)
# ---------------------------------------------------------------------------
def _oraculo_retangular(Md_kncm, bw_cm, d_cm, fck_mpa, fyk_mpa=500.0):
    """Bloco retangular da NBR 6118:2026 17.2.2 e), formula fechada em x."""
    lam = nbr.lambda_retangulo(fck_mpa)
    sigma_ret = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck_mpa))
    fyd = nbr.mpa_para_kncm2(nbr.fyd(fyk_mpa))
    a = 0.5 * lam * lam * sigma_ret * bw_cm
    b = -lam * sigma_ret * bw_cm * d_cm
    disc = b * b - 4.0 * a * Md_kncm
    x = (-b - math.sqrt(disc)) / (2.0 * a)
    As = Md_kncm / (fyd * (d_cm - 0.5 * lam * x))
    return x, As


# ---------------------------------------------------------------------------
# VIG-01 / VIG-02 / VIG-03 - bloco retangular com eta_c (17.2.2 e), 8.2.10.1)
# ---------------------------------------------------------------------------
def test_vig01_dupla_C50_As_linha():
    """Achado VIG-01 (ALTA): bw=20, d=45, d'=4, h=50, C50, Md=40000 kN.cm.
    Sem eta_c (bug antigo) A's saia 2.08 cm2; a norma (com eta_c(50) =
    0,9283) da A's ~= 3.54 cm2 (-41% no valor antigo)."""
    r = vig.secao_retangular_dupla(
        Md_kncm=40000.0, bw_cm=20, d_cm=45, d_linha_cm=4, h_cm=50, fck_mpa=50.0,
    )
    assert r.As_linha == pytest.approx(3.5385, abs=0.01)
    assert r.As_linha > 3.0, "nao pode voltar ao valor antigo (2.08)"
    assert not r.minimo_governou


@pytest.mark.parametrize("fck", FCKS_COBERTURA)
def test_vig01_dupla_M1d_bate_com_nucleo(fck):
    """secao_retangular_dupla usa nbr.tensao_retangulo/lambda_retangulo:
    M1d (x fixo em beta_x_lim*d) bate com o oraculo em C45..C90."""
    bw, d, dl, h = 20.0, 45.0, 4.0, 50.0
    beta_lim = nbr.xd_limite_dutilidade(fck)
    x = beta_lim * d
    lam = nbr.lambda_retangulo(fck)
    sigma_ret = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck))
    M1d_esperado = lam * bw * x * sigma_ret * (d - 0.5 * lam * x)

    r = vig.secao_retangular_dupla(
        Md_kncm=M1d_esperado * 2.0, bw_cm=bw, d_cm=d, d_linha_cm=dl, h_cm=h,
        fck_mpa=fck, beta_x_lim=None,
    )
    assert r.M1d == pytest.approx(M1d_esperado, rel=1e-9)
    assert r.beta_x == pytest.approx(beta_lim, rel=1e-9)


def test_vig02_simples_C50_As_no_limite_de_dutilidade():
    """Achado VIG-02 (MEDIA): bw=20, d=45, h=50, C50, Md no x/d=0.45 da
    formula ANTIGA (sem eta_c) = 36293.79 kN.cm. Repro: As 22.62 (formula
    antiga) x 23.14 (norma, com eta_c) cm2 (-2.24% no valor antigo).
    Bonus: com eta_c o bloco fica mais fraco, entao esse mesmo Md agora
    ultrapassa o limite de dutilidade (beta_x ~ 0.496 > 0.45) - o codigo
    antigo aceitava silenciosamente."""
    Md_no_limite_antigo = 36293.79
    r = vig.secao_retangular_simples(
        Md_kncm=Md_no_limite_antigo, bw_cm=20, d_cm=45, h_cm=50, fck_mpa=50.0,
    )
    assert r.As == pytest.approx(23.14, abs=0.02)
    assert r.As > 22.7, "nao pode voltar ao valor antigo (22.62)"
    assert r.erro, "com eta_c o bloco e mais fraco: deveria estourar x/d <= 0.45"


@pytest.mark.parametrize("fck", FCKS_COBERTURA)
def test_vig02_simples_bate_com_nucleo(fck):
    """secao_retangular_simples bate com o oraculo (bloco do nucleo) em
    C45..C90, com folga da dutilidade e do As,min (x/d alvo = 0.30)."""
    bw, d, h = 20.0, 45.0, 50.0
    lam = nbr.lambda_retangulo(fck)
    sigma_ret = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck))
    x_alvo = 0.30 * d
    Md = lam * bw * x_alvo * sigma_ret * (d - 0.5 * lam * x_alvo)

    x_o, As_o = _oraculo_retangular(Md, bw, d, fck)
    r = vig.secao_retangular_simples(Md_kncm=Md, bw_cm=bw, d_cm=d, h_cm=h, fck_mpa=fck)
    assert r.x == pytest.approx(x_o, rel=1e-9)
    assert r.As == pytest.approx(As_o, rel=1e-9)
    assert not r.erro
    assert not r.minimo_governou


@pytest.mark.parametrize("fck", FCKS_COBERTURA)
def test_vig02_momento_resistente_bate_com_nucleo(fck):
    """momento_resistente_simples (problema inverso) usa o mesmo bloco do
    nucleo; round-trip com secao_retangular_simples deve devolver o Md de
    entrada em C45..C90."""
    bw, d, h = 20.0, 45.0, 50.0
    Md = 20000.0
    r = vig.secao_retangular_simples(Md_kncm=Md, bw_cm=bw, d_cm=d, h_cm=h, fck_mpa=fck)
    MRd, x, dom = vig.momento_resistente_simples(
        As_cm2=r.As, bw_cm=bw, d_cm=d, fck_mpa=fck,
    )
    assert MRd == pytest.approx(Md, rel=1e-6)
    assert x == pytest.approx(r.x, rel=1e-6)
    assert dom == r.dominio


@pytest.mark.parametrize("fck", FCKS_COBERTURA)
def test_vig02_secao_T_bate_com_nucleo_casoA_e_casoB(fck):
    """secao_T_simples usa o bloco do nucleo tanto no Caso A (mesa) quanto
    no Caso B (mesa + alma); com esta geometria, C45/C50/C55 caem no Caso B
    e C70/C90 caem no Caso A (eta_c encolhe o bloco, LN sobe) - o teste
    aceita qualquer um dos dois e monta o oraculo correspondente."""
    bw, bf, hf, d, h = 20.0, 45.0, 7.0, 45.0, 50.0
    Md = 39200.0
    lam = nbr.lambda_retangulo(fck)
    sigma_ret = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck))
    fyd = nbr.mpa_para_kncm2(nbr.fyd(500.0))

    r = vig.secao_T_simples(Md_kncm=Md, bw_cm=bw, bf_cm=bf, hf_cm=hf,
                            d_cm=d, h_cm=h, fck_mpa=fck)

    if lam * r.x <= hf + 1e-9:
        # Caso A: equivalente a retangular bf x h; As,min com bw da nervura.
        x_o, As_o = _oraculo_retangular(Md, bf, d, fck)
        As_min_o = nbr.rho_min_flexao(fck) * bw * h
        As_esperado = max(As_o, As_min_o)
        assert r.tipo.startswith("T (mesa")
    else:
        # Caso B: mesa colaborante (hf) + alma (bw).
        M1d_o = (bf - bw) * hf * sigma_ret * (d - 0.5 * hf)
        M2d_o = Md - M1d_o
        x_o, As2_o = _oraculo_retangular(M2d_o, bw, d, fck)
        As1_o = M1d_o / (fyd * (d - 0.5 * hf))
        As_min_o = nbr.rho_min_flexao(fck) * bw * h
        As_esperado = max(As1_o + As2_o, As_min_o)
        assert r.tipo == "T (alma + mesa)"

    assert r.As == pytest.approx(As_esperado, rel=1e-6)


def test_vig03_C70_limite_de_dutilidade_correto():
    """Achado VIG-03 (ALTA): bw=20, d=45, h=50, C70. A norma limita x/d a
    0,35 (14.6.4.3 b), atingido em Md ~ 29316 kN.cm; o codigo antigo so
    acusava erro em Md >= 50811 (73% acima). Verifica que o limite correto
    (~0,35) e aplicado, nao o de C50 (0,45)."""
    bw, d, h, fck = 20.0, 45.0, 50.0, 70.0
    assert nbr.xd_limite_dutilidade(fck) == 0.35

    r_abaixo = vig.secao_retangular_simples(Md_kncm=20000.0, bw_cm=bw, d_cm=d, h_cm=h, fck_mpa=fck)
    assert not r_abaixo.erro

    r_no_limite = vig.secao_retangular_simples(Md_kncm=29316.0, bw_cm=bw, d_cm=d, h_cm=h, fck_mpa=fck)
    assert r_no_limite.beta_x == pytest.approx(0.35, abs=0.001)

    # Regressao central do achado: Md=45000 fica ABAIXO do limiar antigo
    # (50811), que o deixava passar batido; a norma tem que barrar aqui.
    r_45000 = vig.secao_retangular_simples(Md_kncm=45000.0, bw_cm=bw, d_cm=d, h_cm=h, fck_mpa=fck)
    assert r_45000.erro, "Md=45000 excede x/d<=0.35 em C70 e tem que ser sinalizado"


@pytest.mark.parametrize("fck,rho_esperado", [
    (45.0, 0.00194), (50.0, 0.00208), (55.0, 0.00211), (70.0, 0.00233), (90.0, 0.00256),
])
def test_vig03_as_min_usa_rho_da_classe_correta(fck, rho_esperado):
    """VIG-03 tambem cobre as_min: antes, fck > 50 caia no rho do C50
    (0,00208); a Tabela 17.3 tem valores proprios ate C90 (nbr.rho_min_flexao)."""
    bw, h = 20.0, 50.0
    esperado = rho_esperado * bw * h
    assert vig.as_min(bw, h, fck) == pytest.approx(esperado, abs=0.01)
    if fck > 50.0:
        valor_c50 = 0.00208 * bw * h
        assert vig.as_min(bw, h, fck) != pytest.approx(valor_c50, abs=1e-6)


# ---------------------------------------------------------------------------
# VIG-04 - As = max(As, As_min), com sinalizacao de que o minimo governou
# ---------------------------------------------------------------------------
def test_vig04_as_min_governa_secao_simples():
    """Achado VIG-04 (ALTA): bw=20, d=50, h=55, C20, Md=1500 kN.cm.
    As de equilibrio = 0,699 cm2; As,min (17.3.5.2.1) = 1,65 cm2. O codigo
    antigo devolvia 0,699 sem avisar (-57,6%); agora devolve o minimo e
    sinaliza minimo_governou=True."""
    r = vig.secao_retangular_simples(Md_kncm=1500.0, bw_cm=20, d_cm=50, h_cm=55, fck_mpa=20.0)
    assert r.As == pytest.approx(1.65, abs=0.01)
    assert r.As_min == pytest.approx(1.65, abs=0.01)
    assert r.minimo_governou is True


def test_vig04_as_min_nao_governa_quando_As_e_maior():
    """Contraprova: com momento grande, As de equilibrio supera As,min e a
    flag continua False (nao pode sempre disparar)."""
    r = vig.secao_retangular_simples(Md_kncm=30000.0, bw_cm=20, d_cm=45, h_cm=50, fck_mpa=30.0)
    assert r.As > r.As_min
    assert r.minimo_governou is False


def test_vig04_as_min_governa_secao_T_com_largura_da_nervura():
    """secao_T_simples aplica o mesmo piso (bw da nervura, nao bf) - mesmo
    padrao do achado, agora tambem sinalizado por minimo_governou."""
    r = vig.secao_T_simples(
        Md_kncm=200.0, bw_cm=15, bf_cm=90, hf_cm=6, d_cm=25, h_cm=30, fck_mpa=20.0,
    )
    as_min_bw = vig.as_min(15, 30, 20.0)
    assert r.As_min == pytest.approx(as_min_bw, rel=1e-9)
    if r.As == pytest.approx(as_min_bw, rel=1e-6):
        assert r.minimo_governou is True


# ---------------------------------------------------------------------------
# VIG-05 / VIG-06 / VIG-07 - decalagem do diagrama (17.4.2.2 c, 17.4.2.3 c)
# ---------------------------------------------------------------------------
def test_vig05_decalagem_modelo_I_vsd_menor_que_vc():
    """Achado VIG-05 (ALTA): d=46, VSd=45, Vc=49.6 -> |VSd| <= |Vc|, logo
    a_l = d = 46,0 cm. O codigo antigo devolvia 0,5d = 23,0 cm (-50%)."""
    a = vser.decalagem_modelo_I(d_cm=46.0, VSd_kn=45.0, Vc_kn=49.6)
    assert a == pytest.approx(46.0, abs=0.01)


def test_vig06_decalagem_modelo_I_usa_cotg_alfa():
    """Achado VIG-06 (MEDIA): d=46, VSd=153, Vc=49.6, alfa=45 graus ->
    a_l = 22,07 cm pela formula completa (17.4.2.2 c). O codigo antigo
    ignorava alfa_deg e devolvia 34,03 cm (o valor de alfa=90)."""
    a_90 = vser.decalagem_modelo_I(d_cm=46.0, VSd_kn=153.0, Vc_kn=49.6, alfa_deg=90.0)
    a_45 = vser.decalagem_modelo_I(d_cm=46.0, VSd_kn=153.0, Vc_kn=49.6, alfa_deg=45.0)
    assert a_90 == pytest.approx(34.03, abs=0.05)
    assert a_45 == pytest.approx(22.07, abs=0.05)
    assert a_45 != pytest.approx(a_90, abs=0.5), "alfa_deg nao pode ser ignorado"


def test_vig07_decalagem_modelo_II_sem_dados_avisa_e_usa_limite_d():
    """Achado VIG-07 (ALTA): sem VSd_kn/Vc_kn a formula com Vc=0 da
    apostila subestima a_l sempre (contra a seguranca). A funcao agora
    avisa (warnings.warn) e devolve o limite conservador a_l = d, em vez
    de repetir o atalho antigo (que dava 0,5*cotg(theta)*d = 39,84 cm)."""
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        a = vser.decalagem_modelo_II(d_cm=46.0, theta_deg=30.0)
    assert a == pytest.approx(46.0, abs=0.01)
    assert len(avisos) == 1
    assert issubclass(avisos[0].category, UserWarning)
    assert "VSd_kn" in str(avisos[0].message)


def test_vig07_decalagem_modelo_II_formula_completa():
    """Achado VIG-07: d=46, theta=30, VSd=153, Vc=49.6 -> a_l = d = 46,0 cm
    pela formula completa (o valor bruto, 58,94 cm, e limitado a d). O
    codigo antigo (Vc=0) dava 39,84 cm (-13,4%)."""
    a = vser.decalagem_modelo_II(d_cm=46.0, theta_deg=30.0, VSd_kn=153.0, Vc_kn=49.6)
    assert a == pytest.approx(46.0, abs=0.05)

    # Caso nao-limitado (VSd bem maior que Vc): confere a formula bruta.
    d, theta, VSd, Vc = 46.0, 30.0, 2000.0, 49.6
    cot_t = 1.0 / math.tan(math.radians(theta))
    esperado = 0.5 * d * (VSd / (VSd - Vc) * cot_t)
    a2 = vser.decalagem_modelo_II(d_cm=d, theta_deg=theta, VSd_kn=VSd, Vc_kn=Vc)
    assert a2 == pytest.approx(esperado, rel=1e-9)
    assert a2 < d


def test_vig07_decalagem_modelo_II_vsd_menor_que_vc():
    """Mantidas as limitacoes de 17.4.2.2 (17.4.2.3 c): |VSd| <= |Vc| ->
    a_l = d, mesmo com VSd_kn/Vc_kn informados."""
    a = vser.decalagem_modelo_II(d_cm=46.0, theta_deg=30.0, VSd_kn=40.0, Vc_kn=49.6)
    assert a == pytest.approx(46.0, abs=0.01)


# ---------------------------------------------------------------------------
# VIG-08 - As,min interpolado (Tabela 17.3), sem cair no valor do C50
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fck", [22.0, 47.0, 63.0, 77.0, 88.0])
def test_vig08_as_min_interpola_fck_fora_dos_multiplos_de_5(fck):
    """Achado VIG-08 (BAIXA): fck fora dos multiplos de 5 caia no valor do
    C50 (0,208%). Repro: fck=22 -> 0,208% (antigo) x 0,150% (norma,
    interpolado entre C20 e C25, ambos 0,150%)."""
    bw, h = 20.0, 50.0
    esperado = nbr.rho_min_flexao(fck) * bw * h
    assert vig.as_min(bw, h, fck) == pytest.approx(esperado, rel=1e-9)


def test_vig08_as_min_fck22_valor_da_norma():
    """Numero literal do achado: fck=22 -> rho = 0,150% (nao 0,208%)."""
    bw, h = 20.0, 50.0
    assert vig.as_min(bw, h, 22.0) == pytest.approx(1.5, abs=0.01)
    assert vig.as_min(bw, h, 22.0) != pytest.approx(0.00208 * bw * h, abs=1e-6)


# ---------------------------------------------------------------------------
# VIG-10 - fct,m com o ramo de 8.2.5 para fck > 50 (abertura_fissura_wk)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fck,esperado_mpa", [
    (30.0, 0.3 * 30 ** (2 / 3)),
    (50.0, 0.3 * 50 ** (2 / 3)),
    (55.0, 2.12 * math.log(1 + 0.1 * 63)),
    (70.0, 2.12 * math.log(1 + 0.1 * 78)),
    (90.0, 2.12 * math.log(1 + 0.1 * 98)),
])
def test_vig10_fctm_kncm2_delega_ao_nucleo(fck, esperado_mpa):
    """fctm_kncm2 (usada em abertura_fissura_wk) passa a delegar a
    nbr.fct_m: ramo 0,3*fck^(2/3) ate C50 e 2,12*ln[1+0,1(fck+8)] acima."""
    assert vser.fctm_kncm2(fck) == pytest.approx(esperado_mpa / 10.0, rel=1e-9)


def test_vig10_wk2_nao_fica_mais_baixo_que_o_devido_C70_C90():
    """Achado VIG-10 (MEDIA): sem o ramo de 8.2.5, fctm saia alto demais
    para fck > 50 e por estar no denominador de wk2, wk2 saia BAIXO demais
    (contra a seguranca): -9,5% (C70) e -16,3% (C90). Caso numerico
    proprio (phi=20, sigma_si=20, Acr=1000, As=20, eta1=2.25)."""
    kwargs = dict(phi_mm=20.0, sigma_si_kncm2=20.0, Acr_cm2=1000.0,
                  As_cm2=20.0, eta1_val=2.25)

    def wk2_com_fctm(fctm_mpa_x10_kncm2):
        base = (20.0 / (12.5 * 2.25)) * (20.0 / vser.E_S_KNCM2)
        return base * (3.0 * 20.0 / fctm_mpa_x10_kncm2)

    r70 = vser.abertura_fissura_wk(fck_mpa=70.0, **kwargs)
    r90 = vser.abertura_fissura_wk(fck_mpa=90.0, **kwargs)

    fctm_errado_70 = nbr.mpa_para_kncm2(0.3 * 70.0 ** (2.0 / 3.0))
    fctm_errado_90 = nbr.mpa_para_kncm2(0.3 * 90.0 ** (2.0 / 3.0))
    wk2_errado_70 = wk2_com_fctm(fctm_errado_70)
    wk2_errado_90 = wk2_com_fctm(fctm_errado_90)

    assert r70.wk2_mm == pytest.approx(0.08814, abs=0.0005)
    assert r90.wk2_mm == pytest.approx(0.08055, abs=0.0005)
    # wk2 corrigido tem que ser MAIOR que o antigo (o antigo subestimava).
    assert r70.wk2_mm > wk2_errado_70
    assert r90.wk2_mm > wk2_errado_90
    # Na direcao do achado: o wk2 antigo (errado) ficava 9,5% (C70) e 16,3%
    # (C90) ABAIXO do valor correto.
    assert wk2_errado_70 / r70.wk2_mm - 1.0 == pytest.approx(-0.095, abs=0.01)
    assert wk2_errado_90 / r90.wk2_mm - 1.0 == pytest.approx(-0.163, abs=0.01)


# ---------------------------------------------------------------------------
# VIG-09 (opcional) - sigma_si no Estadio II, sem mexer em sigma_si_aproximada
# ---------------------------------------------------------------------------
def test_vig09_sigma_si_estadio_II_viga_ponte_apostila():
    """Apostila item 17.1 (viga-ponte, C40): sigma_si_aproximada() da 25,18
    kN/cm2 (a favor da seguranca, +12,3%); com a rigidez fissurada real
    (x_II/I_II ja calculados pelo modulo), a norma da ~22,43 kN/cm2."""
    ae = vser.alpha_e(40.0, "granito")
    x_II = vser.x_II_secao_T(
        bf_cm=325.0, bw_cm=25.0, hf_cm=20.0, d_cm=186.5,
        As_cm2=137.20, As_linha_cm2=16.00, d_linha_cm=5.1, alpha_e_val=ae,
    )
    I_II = vser.I_II_secao_T(
        bf_cm=325.0, bw_cm=25.0, hf_cm=20.0, d_cm=186.5, x_II_cm=x_II,
        As_cm2=137.20, As_linha_cm2=16.00, d_linha_cm=5.1, alpha_e_val=ae,
    )
    sigma = vser.sigma_si_estadio_II(
        Md_ser_kncm=547750.0, d_cm=186.5, x_II_cm=x_II, I_II_cm4=I_II,
        alpha_e_val=ae,
    )
    aproximada = vser.sigma_si_aproximada(547750.0, 186.5, 137.20)

    assert sigma == pytest.approx(22.43, abs=0.05)
    assert aproximada == pytest.approx(25.18, abs=0.05)
    assert sigma < aproximada, "sigma_si_aproximada deve continuar a favor da seguranca"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
