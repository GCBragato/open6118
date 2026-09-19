"""Testes do P15 -- Força cortante completa, vigas e lajes (NBR 6118:2026,
17.4.1.1.2, 17.4.1.1.3, 17.4.1.2.1 a 17.4.1.2.3, 17.4.2.1, 17.4.2.2 b e c,
17.4.2.3 b, 17.6, 19.4.1 e 19.4.2).

Valores esperados tirados das imagens das páginas do PDF (SCRATCH/nbr_png):
p154 (17.4.1.1.2), p155 (17.4.1.1.3, 17.4.1.2.1 a 17.4.1.2.3), p156
(17.4.1.2.3, 17.4.2.1), p157-p158 (17.4.2.2 b, M0 e c), p159 (17.4.2.3 b),
p164 (17.6), p181 (19.4.1), p182 (19.4.1 aℓ e 19.4.2).

Viga de referência: C25, bw = 14 cm, d = 46 cm, CA-50, estribos a 90°.
    fct,m = 0,3·25^(2/3) = 2,5650 MPa; fctd = 0,7·2,5650/1,4 = 1,2825 MPa
    Vc0 = 0,6·0,12825·14·46 = 49,555 kN
    fcd = 25/1,4 = 17,857 MPa; αv2 = 0,9
    VRd2 (I) = 0,27·0,9·1,7857·14·46 = 279,45 kN
    VRd2 (II, θ = 30°) = 0,54·0,9·1,7857·644·sen²30°·cotg 30° = 242,011 kN
    fywd = 500/1,15 = 434,78 MPa = 43,478 kN/cm²
"""

import math
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import cortante_nbr6118 as C  # noqa: E402
import lajes_nbr6118 as L  # noqa: E402

VC0 = 49.55510
VRD2_I = 279.45
VRD2_II = 242.01080
BW, D, FCK = 14.0, 46.0, 25.0


# ===========================================================================
# 17.4.2.2 b) -- M0 (PDF p. 157-158)
# ===========================================================================
def test_M0_formula_com_gamas_locais():
    """M0 = Pd·(W1/Ac + ep) + NSd·(W1/Ac), com γp = 0,9 e γf = 1,0.
    P = 1000, ep = 20, N = 200, W1 = 10 000, Ac = 1 200:
    W1/Ac = 8,3333; M0 = 0,9·1000·28,3333 + 1,0·200·8,3333 = 27 166,67 kN·cm."""
    assert C.GAMA_P_M0 == 0.9 and C.GAMA_F_M0 == 1.0
    m0 = C.M0_kncm(1000.0, 20.0, 200.0, 10000.0, 1200.0)
    assert m0 == pytest.approx(900.0 * (10000 / 1200 + 20.0) + 200.0 * 10000 / 1200)
    assert m0 == pytest.approx(27166.667, abs=1e-3)


def test_M0_nulo_recai_em_flexao_simples():
    """Sem protensão e com Nsd = 0 -> M0 = 0 -> Vc = Vc0."""
    m0 = C.M0_kncm(0.0, 0.0, 0.0, 10000.0, 1200.0)
    assert m0 == 0.0
    r = C.modelo_calculo_I(153.0, BW, D, FCK, M0_kncm=m0, MSd_max_kncm=10000.0)
    assert r.Vc == pytest.approx(VC0, rel=1e-6)


def test_M0_entradas_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        C.M0_kncm(100.0, 10.0, 0.0, 0.0, 1200.0)
    with pytest.raises(nbr.FaixaNormativaError):
        C.M0_kncm(-100.0, 10.0, 0.0, 1000.0, 1200.0)


# ===========================================================================
# 17.4.2.2 b) -- os três ramos de Vc no modelo I (PDF p. 157)
# ===========================================================================
def test_modelo_I_padrao_inalterado_flexao_simples():
    """Sem os parâmetros novos: Vc = Vc0 (comportamento anterior)."""
    r = C.modelo_calculo_I(153.0, BW, D, FCK)
    assert r.Vc == pytest.approx(VC0, rel=1e-6)
    assert r.regime_vc == "flexao_simples"
    assert r.VRd2 == pytest.approx(VRD2_I, rel=1e-9)


def test_modelo_I_tracao_ln_fora_vc_zero():
    """Vc = 0 no elemento tracionado com LN fora da seção.
    Asw = 153/(0,9·46·43,478)·100 = 8,50 cm²/m."""
    r = C.modelo_calculo_I(153.0, BW, D, FCK, Nsd_kn=-50.0, linha_neutra_fora=True)
    assert r.Vc == 0.0 and r.regime_vc == "tracao_ln_fora"
    assert r.Vsw == pytest.approx(153.0)
    assert r.Asw_m == pytest.approx(8.50, abs=1e-6)


def test_modelo_I_flexo_tracao_ln_cortando_vc0():
    r = C.modelo_calculo_I(153.0, BW, D, FCK, Nsd_kn=-50.0)
    assert r.Vc == pytest.approx(VC0, rel=1e-6)
    assert r.regime_vc == "flexo_tracao"


@pytest.mark.parametrize("razao, fator", [
    (0.0, 1.0),     # M0 = 0: fronteira com a flexão simples
    (0.5, 1.5),     # ponto interior
    (1.0, 2.0),     # M0 = MSd,máx: exatamente o teto 2·Vc0
    (2.0, 2.0),     # além do teto: limitado a 2·Vc0
])
def test_modelo_I_flexo_compressao(razao, fator):
    """Vc = Vc0·(1 + M0/MSd,máx) <= 2·Vc0."""
    msd = 20000.0
    r = C.modelo_calculo_I(153.0, BW, D, FCK, Nsd_kn=300.0,
                           M0_kncm=razao * msd, MSd_max_kncm=msd)
    assert r.Vc == pytest.approx(fator * VC0, rel=1e-6)
    assert r.regime_vc == "flexo_compressao"


def test_modelo_I_varredura_de_tracao_a_compressao():
    """Teste sugerido: MSd,máx fixo, Nd de tração pura a compressão forte."""
    msd = 20000.0
    vc_t = C.modelo_calculo_I(100.0, BW, D, FCK, Nsd_kn=-300.0,
                              linha_neutra_fora=True).Vc
    vc_ft = C.modelo_calculo_I(100.0, BW, D, FCK, Nsd_kn=-30.0).Vc
    vc_fs = C.modelo_calculo_I(100.0, BW, D, FCK).Vc
    m0 = C.M0_kncm(0.0, 0.0, 3000.0, 3000.0, 700.0)  # 3000·4,2857 = 12 857
    vc_fc = C.modelo_calculo_I(100.0, BW, D, FCK, Nsd_kn=3000.0, M0_kncm=m0,
                               MSd_max_kncm=msd).Vc
    m0_forte = C.M0_kncm(0.0, 0.0, 6000.0, 3000.0, 700.0)  # 25 714 > MSd
    vc_fc2 = C.modelo_calculo_I(100.0, BW, D, FCK, Nsd_kn=6000.0,
                                M0_kncm=m0_forte, MSd_max_kncm=msd).Vc
    assert vc_t == 0.0
    assert vc_ft == pytest.approx(VC0, rel=1e-6)
    assert vc_fs == pytest.approx(VC0, rel=1e-6)
    assert vc_fc == pytest.approx(VC0 * (1.0 + 3000.0 * 3000.0 / 700.0 / msd), rel=1e-6)
    assert vc_fc2 == pytest.approx(2.0 * VC0, rel=1e-6)


def test_compressao_sem_M0_avisa_e_usa_vc0():
    with pytest.warns(nbr.AvisoNBR6118):
        r = C.modelo_calculo_I(153.0, BW, D, FCK, Nsd_kn=200.0)
    assert r.Vc == pytest.approx(VC0, rel=1e-6)
    assert r.regime_vc == "flexo_compressao_sem_M0"


def test_vc_regime_entradas_incoerentes():
    with pytest.raises(nbr.FaixaNormativaError):  # LN fora sem tração
        C.modelo_calculo_I(153.0, BW, D, FCK, linha_neutra_fora=True)
    with pytest.raises(nbr.FaixaNormativaError):  # M0 sem MSd,máx
        C.modelo_calculo_I(153.0, BW, D, FCK, M0_kncm=1000.0)
    with pytest.raises(nbr.FaixaNormativaError):  # M0 negativo
        C.modelo_calculo_I(153.0, BW, D, FCK, M0_kncm=-1.0, MSd_max_kncm=1000.0)
    with pytest.raises(nbr.FaixaNormativaError):  # tração com LN fora e M0
        C.modelo_calculo_I(153.0, BW, D, FCK, Nsd_kn=-1.0, linha_neutra_fora=True,
                           M0_kncm=10.0, MSd_max_kncm=1000.0)


# ===========================================================================
# 17.4.2.3 b) -- os mesmos ramos no modelo II, sobre Vc1 (PDF p. 159)
# ===========================================================================
# Vc1 = Vc0·(VRd2 − VSd)/(VRd2 − Vc0) = 49,555·(242,011 − 153)/(242,011 − 49,555)
#     = 22,9192 kN (VSd = 153, θ = 30°)
VC1_153 = 22.91925


def test_modelo_II_padrao_inalterado():
    r = C.modelo_calculo_II(153.0, BW, D, FCK, 30.0)
    assert r.Vc == pytest.approx(VC1_153, rel=1e-5)
    assert r.regime_vc == "flexao_simples"


def test_modelo_II_tracao_ln_fora():
    r = C.modelo_calculo_II(153.0, BW, D, FCK, 30.0, Nsd_kn=-10.0,
                            linha_neutra_fora=True)
    assert r.Vc == 0.0


def test_modelo_II_flexo_tracao():
    r = C.modelo_calculo_II(153.0, BW, D, FCK, 30.0, Nsd_kn=-10.0)
    assert r.Vc == pytest.approx(VC1_153, rel=1e-5)


@pytest.mark.parametrize("razao, fator", [(0.0, 1.0), (0.5, 1.5), (1.0, 2.0), (3.0, 2.0)])
def test_modelo_II_flexo_compressao(razao, fator):
    """Vc = Vc1·(1 + M0/MSd,máx), limitado a 2·Vc1.
    Razão 0,5: Vc = 34,3789 kN; Asw = (153 − 34,3789)/(0,9·46·43,478·cotg 30°)·100
    = 3,8048 cm²/m."""
    msd = 15000.0
    r = C.modelo_calculo_II(153.0, BW, D, FCK, 30.0, Nsd_kn=100.0,
                            M0_kncm=razao * msd, MSd_max_kncm=msd)
    assert r.Vc == pytest.approx(fator * VC1_153, rel=1e-5)
    if razao == 0.5:
        assert r.Asw_m == pytest.approx(3.80477, abs=1e-4)


def test_modelo_II_vc1_nas_bordas_da_interpolacao():
    """VSd <= Vc0 -> Vc1 = Vc0; VSd = VRd2 -> Vc1 = 0 (o dobro de 0 é 0)."""
    r = C.modelo_calculo_II(40.0, BW, D, FCK, 30.0, M0_kncm=5000.0, MSd_max_kncm=5000.0)
    assert r.Vc == pytest.approx(2.0 * VC0, rel=1e-6)
    r = C.modelo_calculo_II(VRD2_II, BW, D, FCK, 30.0, M0_kncm=5000.0,
                            MSd_max_kncm=5000.0)
    assert r.Vc == pytest.approx(0.0, abs=1e-6)


# ===========================================================================
# 17.4.2.1 -- condição dupla VRd2 e VRd3 no modo verificação (PDF p. 156)
# ===========================================================================
# Asw necessária (modelo I, VSd = 153): (153 − 49,555)/(0,9·46·43,478)·100 = 5,74694 cm²/m
ASW_NEC_I = 5.746939


def test_verificar_cortante_limite_VRd3():
    r = C.verificar_cortante(ASW_NEC_I, 153.0, BW, D, FCK)
    assert r.VRd3_kn == pytest.approx(153.0, rel=1e-6)
    assert r.ok and r.ok_VRd2 and r.ok_VRd3
    r = C.verificar_cortante(ASW_NEC_I * 0.999, 153.0, BW, D, FCK)
    assert not r.ok and not r.ok_VRd3 and r.ok_VRd2
    assert "VRd3" in r.governante
    assert any("17.4.2.1" in linha for linha in r.memoria)


def test_verificar_cortante_bate_com_dimensionamento():
    """Dimensionar e verificar com a Asw calculada fecha VRd3 = VSd."""
    d = C.modelo_calculo_I(200.0, 20.0, 50.0, 30.0)
    v = C.verificar_cortante(d.Asw_m, 200.0, 20.0, 50.0, 30.0)
    assert v.VRd3_kn == pytest.approx(200.0, rel=1e-9)
    d2 = C.modelo_calculo_II(200.0, 20.0, 50.0, 30.0, 35.0)
    v2 = C.verificar_cortante(d2.Asw_m, 200.0, 20.0, 50.0, 30.0, modelo="II",
                              theta_deg=35.0)
    assert v2.VRd3_kn == pytest.approx(200.0, rel=1e-9)


def test_verificar_cortante_biela():
    """VSd = 279,45 = VRd2 passa na biela; 280 não passa."""
    r = C.verificar_cortante(20.0, VRD2_I, BW, D, FCK)
    assert r.ok_VRd2
    r = C.verificar_cortante(20.0, 280.0, BW, D, FCK)
    assert not r.ok_VRd2 and not r.ok and "VRd2" in r.governante


def test_verificar_cortante_asw_min():
    """Asw,min = 20·0,2565·14/50 = 1,43638 cm²/m (17.4.1.1.1)."""
    r = C.verificar_cortante(1.43638, 40.0, BW, D, FCK)
    assert r.ok_asw_min and r.ok
    r = C.verificar_cortante(1.43, 40.0, BW, D, FCK)
    assert not r.ok_asw_min and not r.ok
    r = C.verificar_cortante(1.43, 40.0, BW, D, FCK, verificar_asw_min=False)
    assert r.ok


def test_verificar_cortante_modelo_I_so_theta_45():
    with pytest.raises(nbr.FaixaNormativaError):
        C.verificar_cortante(5.0, 100.0, BW, D, FCK, theta_deg=30.0)
    with pytest.raises(ValueError):
        C.verificar_cortante(5.0, 100.0, BW, D, FCK, modelo="III")


# ===========================================================================
# 17.4.2.2 c) -- FSd,cor (PDF p. 158)
# ===========================================================================
def test_FSd_cor():
    """M = 10 000, z = 40, V = 100, aℓ = 23, d = 46:
    FSd,cor = 250 + 100·0,5 = 300 kN <= 20 000/40 = 500."""
    assert C.FSd_cor_kn(10000.0, 40.0, 100.0, 23.0, 46.0, 20000.0, 40.0) == pytest.approx(300.0)
    # teto MSd,máx/z_máx = 11 000/40 = 275
    assert C.FSd_cor_kn(10000.0, 40.0, 100.0, 23.0, 46.0, 11000.0, 40.0) == pytest.approx(275.0)


def test_FSd_cor_igual_a_decalar_M_quando_z_igual_d():
    """M linear com inclinação V: M(x + aℓ) = M + V·aℓ; com z = d,
    M(x + aℓ)/z = M/z + V·aℓ/d = FSd,cor."""
    M, V, al, d = 8000.0, 120.0, 30.0, 45.0
    assert C.FSd_cor_kn(M, d, V, al, d, 1e9, d) == pytest.approx((M + V * al) / d)


# ===========================================================================
# 17.4.1.1.2 -- exceções à Asw,min (PDF p. 154)
# ===========================================================================
def test_regime_asw_min_bw_5d():
    assert C.regime_asw_minima(5.1 * 20.0, 20.0).regime == "laje_19_4"
    r = C.regime_asw_minima(5.0 * 20.0, 20.0)   # bw = 5d: ainda viga (bw > 5d)
    assert r.regime == "asw_min_17_4_1_1_1" and not r.dispensa_asw_min_17


def test_regime_asw_min_nervura():
    r = C.regime_asw_minima(12.0, 20.0, "nervura", VSd_kn=10.0, VRd1_kn=12.0)
    assert r.regime == "nervura_laje_19_4_1" and r.dispensa_asw_min_17
    r = C.regime_asw_minima(12.0, 20.0, "nervura", VSd_kn=13.0, VRd1_kn=12.0)
    assert not r.dispensa_asw_min_17
    assert not C.regime_asw_minima(12.0, 20.0, "nervura").dispensa_asw_min_17


def test_regime_asw_min_pilar_comprimido():
    """fctk,inf(C25) = 0,7·2,5650 = 1,7955 MPa."""
    r = C.regime_asw_minima(30.0, 45.0, "pilar", True, sigma_tracao_max_mpa=1.79,
                            fck_mpa=25.0, VSd_kn=50.0, Vc_kn=60.0)
    assert r.regime == "asw_min_secao_18" and r.dispensa_asw_min_17
    r = C.regime_asw_minima(30.0, 45.0, "pilar", True, sigma_tracao_max_mpa=1.80,
                            fck_mpa=25.0, VSd_kn=50.0, Vc_kn=60.0)
    assert r.regime == "asw_min_17_4_1_1_1"
    r = C.regime_asw_minima(30.0, 45.0, "fundacao", True, sigma_tracao_max_mpa=0.0,
                            fck_mpa=25.0, VSd_kn=61.0, Vc_kn=60.0)
    assert r.regime == "asw_min_17_4_1_1_1"
    with pytest.raises(nbr.FaixaNormativaError):
        C.regime_asw_minima(30.0, 45.0, "pilar", True)
    with pytest.raises(ValueError):
        C.regime_asw_minima(30.0, 45.0, "tirante")


# ===========================================================================
# 17.4.1.1.3 -- barras dobradas <= 60 % (PDF p. 155)
# ===========================================================================
def test_barras_dobradas_60_por_cento():
    assert C.verificar_limite_barras_dobradas(60.0, 100.0).ok
    r = C.verificar_limite_barras_dobradas(61.0, 100.0)
    assert not r.ok and r.limite_kn == pytest.approx(60.0)
    with pytest.raises(nbr.FaixaNormativaError):
        C.verificar_limite_barras_dobradas(101.0, 100.0)


# ===========================================================================
# 17.4.1.2.1 -- cargas próximas aos apoios (PDF p. 155)
# ===========================================================================
@pytest.mark.parametrize("a, fator", [(0.0, 0.0), (40.0, 0.5), (80.0, 1.0), (80.1, 1.0)])
def test_fator_carga_concentrada(a, fator):
    """d = 40: a = d -> 0,5; a = 2d -> 1; a > 2d -> sem redução."""
    assert C.fator_reducao_carga_concentrada(a, 40.0) == pytest.approx(fator)


def test_VSd_reduzido_carga_distribuida():
    """V_face = 100, q = 0,5 kN/cm, d = 40: V(d/2) = 100 − 0,5·20 = 90."""
    r = C.VSd_reduzido_apoio(40.0, 100.0, 0.5, x_cm=0.0)
    assert r.VSd_reduzido_kn == pytest.approx(90.0)
    assert r.VSd_sem_reducao_kn == pytest.approx(100.0)
    r = C.VSd_reduzido_apoio(40.0, 100.0, 0.5, x_cm=30.0)   # x > d/2: sem redução
    assert r.VSd_reduzido_kn == pytest.approx(85.0)


def test_VSd_reduzido_concentrada_cabos_e_apoio_indireto():
    """Carga a a = d (fator 0,5) com V = 60, mais 20 kN de cabos inclinados
    (não reduz): 0,5·60 + 20 = 50; sem redução 80. Apoio indireto: 80."""
    r = C.VSd_reduzido_apoio(40.0, cargas_concentradas=((60.0, 40.0),),
                             V_cabos_inclinados_kn=20.0)
    assert r.VSd_reduzido_kn == pytest.approx(50.0)
    assert r.VSd_sem_reducao_kn == pytest.approx(80.0)
    r = C.VSd_reduzido_apoio(40.0, cargas_concentradas=((60.0, 40.0),),
                             V_cabos_inclinados_kn=20.0, apoio_direto=False)
    assert r.VSd_reduzido_kn == pytest.approx(80.0)


# ===========================================================================
# 17.4.1.2.2 -- componente tangencial da protensão (PDF p. 155)
# ===========================================================================
def test_protensao_tangencial_limite():
    """Ap = 1, fpyk = 1710 -> fpyd = 1486,96; As = 2, fyd = 434,78:
    (1486,96 + 869,57)/10 = 235,652 kN."""
    r = C.verificar_protensao_tangencial(235.6521739, 1.0, 2.0, 1710.0)
    assert r.resistencia_kn == pytest.approx(235.6521739, rel=1e-9)
    assert r.ok
    assert not C.verificar_protensao_tangencial(235.66, 1.0, 2.0, 1710.0).ok
    r = C.verificar_protensao_tangencial(999.0, 1.0, 2.0, 1710.0, efeito_favoravel=False)
    assert r.ok and not r.exigida


# ===========================================================================
# 17.4.1.2.3 -- altura variável (PDF p. 155-156)
# ===========================================================================
def test_altura_variavel_banzos_paralelos():
    assert C.VSd_red_altura_variavel(100.0, 10000.0, 40.0, 0.0, 0.0) == pytest.approx(100.0)


def test_altura_variavel_banzo_comprimido_inclinado():
    """θ = 45°, βc = 10°, βt = 0, M/z = 250, VSd = 100:
    VSd,red = (100 − 250·tg 10°)/(1 − 0,5·tg 10°) = 61,3249 kN; confere a
    equação original por substituição."""
    v = C.VSd_red_altura_variavel(100.0, 10000.0, 40.0, 10.0, 0.0, 45.0)
    assert v == pytest.approx(61.32487, abs=1e-4)
    tc, fz = math.tan(math.radians(10.0)), 250.0
    assert 100.0 - v == pytest.approx((fz - v * 0.5) * tc)


def test_altura_variavel_fora_da_faixa():
    with pytest.raises(nbr.FaixaNormativaError):
        C.VSd_red_altura_variavel(100.0, 1000.0, 40.0, 0.0, 0.0, 29.0)
    with pytest.raises(nbr.FaixaNormativaError):  # componentes > VSd
        C.VSd_red_altura_variavel(10.0, 100000.0, 40.0, 20.0, 20.0)


# ===========================================================================
# 17.6 -- fissuração inclinada da alma (PDF p. 164)
# ===========================================================================
def test_espacamento_fissuracao_alma():
    assert C.S_MAX_FISSURACAO_ALMA_CM == 15.0
    assert C.verificar_espacamento_fissuracao_alma(15.0)
    assert not C.verificar_espacamento_fissuracao_alma(15.1)
    assert C.verificar_espacamento_fissuracao_alma(20.0, caso_especial=False)
    r = C.verificar_cortante(ASW_NEC_I, 153.0, BW, D, FCK, s_cm=16.0,
                             controle_fissuracao_alma=True)
    assert not r.ok and not r.ok_espacamento_alma


# ===========================================================================
# 19.4.2 -- fywd máximo em laje (PDF p. 182)
# ===========================================================================
@pytest.mark.parametrize("h, esperado", [
    (10.0, 250.0), (15.0, 250.0), (25.0, 342.5), (35.0, 435.0), (40.0, 435.0),
    (20.0, 296.25),   # 250 + 185·5/20
])
def test_fywd_max_laje(h, esperado):
    assert C.fywd_max_laje_mpa(h) == pytest.approx(esperado)


def test_fywd_laje_kncm2_e_modelos():
    assert C.fywd_laje_kncm2(500.0, 20.0) == pytest.approx(29.625)
    assert C.fywd_laje_kncm2(250.0, 15.0) == pytest.approx(250.0 / 1.15 / 10.0)  # fyd < 250
    with pytest.raises(nbr.FaixaNormativaError):
        C.fywd_max_laje_mpa(0.0)
    # Modelo I com h = 15 cm: Asw cresce na razão 43,478/25
    r0 = C.modelo_calculo_I(300.0, 100.0, 12.0, 30.0)
    r1 = C.modelo_calculo_I(300.0, 100.0, 12.0, 30.0, h_laje_cm=15.0)
    assert r1.Asw_m == pytest.approx(r0.Asw_m * (500.0 / 1.15 / 10.0) / 25.0, rel=1e-9)
    v = C.verificar_cortante(10.0, 100.0, 100.0, 12.0, 30.0, h_laje_cm=15.0)
    assert v.fywd_kncm2 == pytest.approx(25.0)


# ===========================================================================
# 19.4.1 -- VRd1 e aℓ = 1,5d em lajes (PDF p. 181-182)
# ===========================================================================
def test_a_l_laje():
    assert C.AL_LAJE_FATOR_D == 1.5
    assert C.a_l_laje_cm(15.0) == pytest.approx(22.5)


def test_sigma_cp():
    assert C.sigma_cp_mpa(100.0, 1000.0) == pytest.approx(1.0)


def test_cortante_resistente_laje_delegada_sem_normal_igual_antes():
    """bw = 100, d = 15, As = 8, C25: τRd = 0,25·1,2825 = 0,32063 MPa;
    k = 1,6 − 0,15 = 1,45; ρ1 = 8/1500 = 0,005333;
    VRd1 = 0,032063·1,45·(1,2 + 0,21333)·1500 = 98,559 kN (fórmula antiga)."""
    v = L.cortante_resistente_laje(100.0, 15.0, 8.0, 25.0)
    assert v == pytest.approx(98.5587, abs=1e-3)
    ref = C.laje_sem_armadura(0.0, 100.0, 15.0, 25.0, rho_l=8.0 / 1500.0)["VRd1_kN"]
    assert v == pytest.approx(ref, rel=1e-12)


def test_cortante_resistente_laje_com_sigma_cp():
    """Tração σcp = −1 MPa reduz VRd1 em 0,15·0,1·100·15 = 22,5 kN;
    compressão +1 MPa aumenta o mesmo tanto."""
    v0 = L.cortante_resistente_laje(100.0, 15.0, 8.0, 25.0)
    vt = L.cortante_resistente_laje(100.0, 15.0, 8.0, 25.0, sigma_cp_mpa=-1.0)
    vc = L.cortante_resistente_laje(100.0, 15.0, 8.0, 25.0, sigma_cp_mpa=1.0)
    assert vt < v0
    assert v0 - vt == pytest.approx(22.5)
    assert vc - v0 == pytest.approx(22.5)
    k1 = L.cortante_resistente_laje(100.0, 15.0, 8.0, 25.0,
                                    metade_armadura_chega_apoio=False)
    assert k1 == pytest.approx(v0 / 1.45)
