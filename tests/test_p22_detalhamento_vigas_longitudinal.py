"""Testes do P22 -- Detalhamento de vigas: armadura longitudinal (NBR 6118:2026).

Valores esperados tirados da imagem das páginas do PDF (SCRATCH/nbr_png):
p166 (18.2.2 barras curvadas), p168 (18.3.2.2 distribuição transversal;
18.3.2.3.1 armadura de tração ancorada por aderência), p169 (Figura 18.3,
ponto A na face do apoio, 18.3.2.3.2 barras nas mesas, 18.3.2.4 b), p170
(18.3.2.4 c) e 18.3.2.4.1 ancoragem no apoio), p175 (18.6.1.1 apoio
intermediário). As contas à mão estão nos comentários de cada teste.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import ancoragem_nbr6118 as anc  # noqa: E402
import detalhamento_vigas_nbr6118 as DV  # noqa: E402

Erro = nbr.FaixaNormativaError


# ===========================================================================
# 18.3.2.2 -- espaçamento mínimo livre ah e av (PDF p. 168)
# ===========================================================================
def test_ah_phi20_brita19_governa_agregado():
    # ah = máx(20; 20; 1,2·19 = 22,8) = 22,8 mm = 2,28 cm
    assert DV.ah_min_cm(20.0, 19.0) == pytest.approx(2.28)


def test_av_phi20_brita19_governa_20mm_e_diametro():
    # av = máx(20; 20; 0,5·19 = 9,5) = 20 mm = 2,0 cm
    assert DV.av_min_cm(20.0, 19.0) == pytest.approx(2.0)


def test_ah_governa_20mm_absoluto():
    # φ10, dmáx 9,5: máx(20; 10; 11,4) = 20 mm
    assert DV.ah_min_cm(10.0, 9.5) == pytest.approx(2.0)


def test_ah_governa_diametro_da_barra():
    # φ25, dmáx 19: máx(20; 25; 22,8) = 25 mm
    assert DV.ah_min_cm(25.0, 19.0) == pytest.approx(2.5)
    assert DV.av_min_cm(25.0, 19.0) == pytest.approx(2.5)


def test_av_governa_agregado():
    # φ16, dmáx 50: av = máx(20; 16; 25) = 25 mm; ah = máx(20; 16; 60) = 60 mm
    assert DV.av_min_cm(16.0, 50.0) == pytest.approx(2.5)
    assert DV.ah_min_cm(16.0, 50.0) == pytest.approx(6.0)


def test_av_degrau_agregado_40mm():
    # 0,5·40 = 20 = 20 mm (empate); 0,5·40,2 = 20,1 mm
    assert DV.av_min_cm(10.0, 40.0) == pytest.approx(2.0)
    assert DV.av_min_cm(10.0, 40.2) == pytest.approx(2.01)


def test_feixe_3_phi16_usa_phi_n():
    # φn = 16·√3 = 27,71 mm; ah = máx(20; 27,71; 22,8) = 27,71 mm
    assert DV.ah_min_cm(16.0, 19.0, n_barras_feixe=3) == pytest.approx(
        16.0 * math.sqrt(3) / 10.0)
    assert DV.av_min_cm(16.0, 19.0, n_barras_feixe=3) == pytest.approx(
        16.0 * math.sqrt(3) / 10.0)


def test_luva_entra_no_maximo():
    # luva de 35 mm: máx(20; 20; 35; 22,8) = 35 mm
    assert DV.ah_min_cm(20.0, 19.0, phi_luva_mm=35.0) == pytest.approx(3.5)


@pytest.mark.parametrize("kw", [
    dict(phi_mm=0.0, dmax_agregado_mm=19.0),
    dict(phi_mm=16.0, dmax_agregado_mm=0.0),
    dict(phi_mm=16.0, dmax_agregado_mm=19.0, n_barras_feixe=0),
])
def test_espacamento_fora_da_faixa(kw):
    with pytest.raises(Erro):
        DV.ah_min_cm(**kw)
    with pytest.raises(Erro):
        DV.av_min_cm(**kw)


# ===========================================================================
# 18.2.2 -- diâmetro de curvatura de barra longitudinal dobrada (PDF p. 166)
# ===========================================================================
@pytest.mark.parametrize("aco,phi,esperado", [
    ("CA-25", 10.0, 100.0),   # 10φ
    ("CA-50", 20.0, 300.0),   # 15φ
    ("CA-60", 8.0, 144.0),    # 18φ
    ("CA60", 20.0, 360.0),    # 18φ, sem redução não consulta a Tabela 9.1
])
def test_curvatura_por_categoria(aco, phi, esperado):
    assert DV.diametro_curvatura_barra_dobrada_mm(phi, aco) == pytest.approx(esperado)


def test_curvatura_sigma_igual_fyd_nao_reduz():
    assert DV.diametro_curvatura_barra_dobrada_mm(16.0, "CA-50", 1.0) == pytest.approx(240.0)


def test_curvatura_reducao_proporcional():
    # 15·16·0,5 = 120 mm > gancho 5·16 = 80 mm
    assert DV.diametro_curvatura_barra_dobrada_mm(16.0, "CA-50", 0.5) == pytest.approx(120.0)


def test_curvatura_reducao_limitada_ao_gancho():
    # σs = 0: 0 -> gancho da Tabela 9.1, 5φ = 80 mm (φ < 20, CA-50)
    assert DV.diametro_curvatura_barra_dobrada_mm(16.0, "CA-50", 0.0) == pytest.approx(80.0)
    # 15·16·0,3 = 72 < 80 -> 80
    assert DV.diametro_curvatura_barra_dobrada_mm(16.0, "CA-50", 0.3) == pytest.approx(80.0)
    # φ20 CA-50: 15·20·0,5 = 150 < gancho 8·20 = 160 -> 160
    assert DV.diametro_curvatura_barra_dobrada_mm(20.0, "CA-50", 0.5) == pytest.approx(160.0)


def test_curvatura_reducao_ca60_phi20_sem_gancho_definido():
    # Tabela 9.1 tem "-" para CA-60 com φ >= 20 mm
    with pytest.raises(Erro):
        DV.diametro_curvatura_barra_dobrada_mm(20.0, "CA-60", 0.9)


def test_curvatura_multiplica_pelo_numero_de_barras():
    # 3 barras no mesmo plano, espaçamento desconhecido: 3·300 = 900 mm
    assert DV.diametro_curvatura_barra_dobrada_mm(20.0, "CA-50", n_barras_plano=3) == pytest.approx(900.0)


def test_curvatura_multiplicacao_dos_dois_lados_do_limite():
    ah = DV.ah_min_cm(20.0, 19.0)   # 2,28 cm; dobro = 4,56 cm
    f = DV.diametro_curvatura_barra_dobrada_mm
    assert f(20.0, "CA-50", n_barras_plano=3, espacamento_livre_cm=4.0,
             espacamento_min_cm=ah) == pytest.approx(900.0)
    # exatamente o dobro: não é "inferior ao dobro"
    assert f(20.0, "CA-50", n_barras_plano=3, espacamento_livre_cm=2 * ah,
             espacamento_min_cm=ah) == pytest.approx(300.0)
    assert f(20.0, "CA-50", n_barras_plano=3, espacamento_livre_cm=5.0,
             espacamento_min_cm=ah) == pytest.approx(300.0)


@pytest.mark.parametrize("kw", [
    dict(phi_mm=16.0, sigma_s_fyd=1.1),
    dict(phi_mm=16.0, sigma_s_fyd=-0.1),
    dict(phi_mm=0.0),
    dict(phi_mm=16.0, n_barras_plano=0),
    dict(phi_mm=16.0, aco="CA-40"),
    dict(phi_mm=20.0, n_barras_plano=2, espacamento_livre_cm=-5.0,
         espacamento_min_cm=2.0),
    dict(phi_mm=20.0, n_barras_plano=2, espacamento_livre_cm=3.0,
         espacamento_min_cm=0.0),
    dict(phi_mm=20.0, n_barras_plano=2, espacamento_livre_cm=3.0,
         espacamento_min_cm=-2.0),
])
def test_curvatura_fora_da_faixa(kw):
    with pytest.raises(Erro):
        DV.diametro_curvatura_barra_dobrada_mm(**kw)


# ===========================================================================
# 18.3.2.3.2 -- barras nas mesas (PDF p. 169)
# ===========================================================================
def test_comprimento_adicional_mesa():
    assert DV.comprimento_adicional_mesa_cm(15.0) == 15.0
    assert DV.comprimento_adicional_mesa_cm(0.0) == 0.0
    with pytest.raises(Erro):
        DV.comprimento_adicional_mesa_cm(-1.0)


# ===========================================================================
# 18.3.2.4 b) -- força no apoio extremo (PDF p. 169)
# ===========================================================================
def test_FSd_extremo_sem_momento():
    # (aℓ/d)·VSd = 40/50·100 = 80 kN
    assert DV.FSd_apoio_extremo_kn(100.0, 40.0, 50.0) == pytest.approx(80.0)


def test_FSd_extremo_com_tracao_normal():
    # 80 + 10 = 90 kN
    assert DV.FSd_apoio_extremo_kn(100.0, 40.0, 50.0, NSd_kn=10.0) == pytest.approx(90.0)


def test_FSd_extremo_com_momento_positivo():
    # 900/45 + 80 = 100 kN
    assert DV.FSd_apoio_extremo_kn(100.0, 40.0, 50.0, 900.0, 45.0) == pytest.approx(100.0)


def test_FSd_extremo_momento_negativo_fica_no_piso():
    # MSd/z negativo: FSd >= (aℓ/d)·VSd + NSd = 80 kN
    assert DV.FSd_apoio_extremo_kn(-100.0, 40.0, 50.0, -900.0, 45.0) == pytest.approx(80.0)


@pytest.mark.parametrize("args,kw", [
    ((100.0, 40.0, 50.0), dict(NSd_kn=-5.0)),
    ((100.0, 40.0, 0.0), {}),
    ((100.0, -1.0, 50.0), {}),
    ((100.0, 40.0, 50.0, 900.0), {}),   # MSd sem z
])
def test_FSd_extremo_fora_da_faixa(args, kw):
    with pytest.raises(Erro):
        DV.FSd_apoio_extremo_kn(*args, **kw)


# ===========================================================================
# 18.6.1.1 -- força no apoio intermediário (PDF p. 175)
# ===========================================================================
def test_FSd_intermediario_formula():
    # (25/50)·150 = 75 > 0,2·100 = 20
    assert DV.FSd_apoio_intermediario_kn(150.0, 100.0, 25.0, 50.0) == pytest.approx(75.0)
    # com Nd = 5: 80
    assert DV.FSd_apoio_intermediario_kn(150.0, 100.0, 25.0, 50.0, 5.0) == pytest.approx(80.0)


def test_FSd_intermediario_minimo_dos_dois_lados():
    f = DV.FSd_apoio_intermediario_kn
    # (25/50)·20 = 10 < 0,2·100 = 20 -> 20
    assert f(20.0, 100.0, 25.0, 50.0) == pytest.approx(20.0)
    # (25/50)·40 = 20 = 0,2·100 (empate)
    assert f(40.0, 100.0, 25.0, 50.0) == pytest.approx(20.0)
    # (25/50)·42 = 21 > 20
    assert f(42.0, 100.0, 25.0, 50.0) == pytest.approx(21.0)


def test_FSd_intermediario_maior_dos_lados():
    # ΔVd = 20: lado 1 máx(10; 20) = 20; lado 2 máx((50/50)·20 = 20; 0,2·120 = 24) = 24
    assert DV.FSd_apoio_intermediario_max_kn(
        20.0, [(100.0, 25.0, 50.0), (120.0, 50.0, 50.0)]) == pytest.approx(24.0)


def test_FSd_intermediario_fora_da_faixa():
    with pytest.raises(Erro):
        DV.FSd_apoio_intermediario_kn(10.0, 10.0, 25.0, 50.0, -1.0)
    with pytest.raises(Erro):
        DV.FSd_apoio_intermediario_kn(10.0, 10.0, 25.0, 0.0)
    with pytest.raises(Erro):
        DV.FSd_apoio_intermediario_max_kn(10.0, [])


# ===========================================================================
# 18.3.2.4 c) -- fração de As,vão no apoio (PDF p. 170)
# ===========================================================================
def test_fracao_momento_nulo():
    assert DV.fracao_As_vao_no_apoio(0.0, 10000.0) == pytest.approx(1 / 3)


def test_fracao_limite_exato_meio_mvao_da_um_terco():
    # |Mapoio| = 0,5·Mvão -> ramo de 1/3 (<=)
    assert DV.fracao_As_vao_no_apoio(-5000.0, 10000.0) == pytest.approx(1 / 3)


def test_fracao_logo_acima_do_limite_da_um_quarto():
    assert DV.fracao_As_vao_no_apoio(-5000.001, 10000.0) == pytest.approx(1 / 4)
    assert DV.fracao_As_vao_no_apoio(-8000.0, 10000.0) == pytest.approx(1 / 4)


def test_fracao_ponto_interior_um_terco():
    assert DV.fracao_As_vao_no_apoio(-2000.0, 10000.0) == pytest.approx(1 / 3)


def test_fracao_fora_da_faixa():
    with pytest.raises(Erro):
        DV.fracao_As_vao_no_apoio(100.0, 10000.0)   # momento positivo: 18.3.2.4 a)
    with pytest.raises(Erro):
        DV.fracao_As_vao_no_apoio(0.0, 0.0)


def test_armadura_apoio_governa_fracao():
    # As,vão = 6 cm², Mapoio = 0 -> 2 cm²; FSd = 80 kN, fyd = 500/1,15 = 434,78 MPa
    # FSd/fyd = 80/43,478 = 1,84 cm² < 2 -> governa c)
    r = DV.armadura_tracao_apoio(6.0, 0.0, 10000.0, FSd_kn=80.0, gama_s=1.15)
    assert r.As_min_fracao_cm2 == pytest.approx(2.0)
    assert r.As_min_forca_cm2 == pytest.approx(80.0 / (500 / 1.15 / 10))
    assert r.As_necessaria_cm2 == pytest.approx(2.0)
    assert "c)" in r.governante
    assert r.ok


def test_armadura_apoio_governa_forca_e_reprova():
    # FSd = 100 kN -> 100/43,478 = 2,30 cm² > 2; As,apoio = 2,0 não atende
    r = DV.armadura_tracao_apoio(6.0, 0.0, 10000.0, FSd_kn=100.0,
                                 gama_s=1.15, As_apoio_cm2=2.0)
    assert r.As_necessaria_cm2 == pytest.approx(2.3)
    assert "b)" in r.governante
    assert not r.ok
    assert any("18.3.2.4 b)" in m for m in r.memoria)


def test_armadura_apoio_um_quarto():
    # |Mapoio| = 0,6·Mvão: As,vão = 8 -> 2 cm²
    r = DV.armadura_tracao_apoio(8.0, -6000.0, 10000.0, As_apoio_cm2=2.0)
    assert r.fracao == pytest.approx(0.25)
    assert r.As_necessaria_cm2 == pytest.approx(2.0)
    assert r.ok


# ===========================================================================
# 18.3.2.4.1 -- ancoragem a partir da face do apoio (PDF p. 170)
# ===========================================================================
def test_ancoragem_apoio_governa_lb_nec_C25_phi16():
    # lb = φ/4·fyd/fbd; fctd = 0,21·25^(2/3)/1,4 = 1,2825; fbd = 2,25·1,2825 = 2,8856
    # lb = 1,6/4·434,78/2,8856 = 60,27 cm; r = 5·16/2 = 40 mm;
    # r + 5,5φ = 40 + 88 = 128 mm = 12,8 cm; 60 mm = 6 cm -> governa ℓb,nec
    lb_nec = anc.comprimento_ancoragem(16.0, 25.0).lb_nec_cm
    assert lb_nec == pytest.approx(60.27, abs=0.01)
    r = DV.ancoragem_no_apoio_cm(16.0, lb_nec, "CA-50")
    assert r.r_mm == pytest.approx(40.0)
    assert r.r_mais_5_5phi_cm == pytest.approx(12.8)
    assert r.comprimento_cm == pytest.approx(lb_nec)
    assert "ℓb,nec" in r.governante


def test_ancoragem_apoio_governa_r_mais_5_5phi():
    r = DV.ancoragem_no_apoio_cm(16.0, 10.0, "CA-50")
    assert r.comprimento_cm == pytest.approx(12.8)
    # φ20 CA-50: D = 8φ -> r = 80 mm; 80 + 110 = 190 mm
    r20 = DV.ancoragem_no_apoio_cm(20.0, 10.0, "CA-50")
    assert r20.comprimento_cm == pytest.approx(19.0)


def test_ancoragem_apoio_governa_60mm():
    # φ6,3 CA-50: r = 2,5·6,3 = 15,75; + 34,65 = 50,4 mm < 60 mm
    r = DV.ancoragem_no_apoio_cm(6.3, 3.0, "CA-50")
    assert r.r_mais_5_5phi_cm == pytest.approx(5.04)
    assert r.comprimento_cm == pytest.approx(6.0)
    assert r.governante == "60 mm"


def test_ancoragem_apoio_dispensa_lb_nec_dos_dois_lados():
    f = DV.ancoragem_no_apoio_cm
    # cobrimento 70 mm e ações variáveis pouco frequentes: ℓb,nec desprezado
    r = f(16.0, 60.27, cobrimento_gancho_mm=70.0, acoes_variaveis_frequentes=False)
    assert r.lb_nec_dispensado and r.comprimento_cm == pytest.approx(12.8)
    # 69,9 mm: não dispensa
    r = f(16.0, 60.27, cobrimento_gancho_mm=69.9, acoes_variaveis_frequentes=False)
    assert not r.lb_nec_dispensado and r.comprimento_cm == pytest.approx(60.27)
    # ações frequentes: não dispensa
    r = f(16.0, 60.27, cobrimento_gancho_mm=80.0, acoes_variaveis_frequentes=True)
    assert r.comprimento_cm == pytest.approx(60.27)


def test_ancoragem_apoio_intermediario_caso_c_10phi():
    r = DV.ancoragem_no_apoio_cm(16.0, 60.27, intermediario_caso_c=True,
                                 risco_momento_positivo=False)
    assert r.comprimento_cm == pytest.approx(16.0)   # 10·16 mm


def test_ancoragem_apoio_intermediario_caso_c_com_risco_exige_continuidade():
    with pytest.raises(Erro, match="contínuas ou emendadas"):
        DV.ancoragem_no_apoio_cm(16.0, 60.27, intermediario_caso_c=True)


def test_ancoragem_apoio_verificacao_disponivel():
    assert DV.ancoragem_no_apoio_cm(16.0, 10.0, comprimento_disponivel_cm=12.8).ok
    assert not DV.ancoragem_no_apoio_cm(16.0, 10.0, comprimento_disponivel_cm=12.7).ok


def test_ancoragem_apoio_ca60_phi20_tabela_9_1_nao_define():
    with pytest.raises(Erro):
        DV.ancoragem_no_apoio_cm(20.0, 50.0, "CA-60")


# ===========================================================================
# 18.3.2.3.1 -- cobertura do diagrama decalado (Figura 18.3, PDF p. 168-169)
# ===========================================================================
# Viga biapoiada, carga uniforme: L = 600 cm, M(x) = 4·Mmáx·x(L − x)/L²,
# Mmáx = 9000 kN·cm, z = 45 cm -> Rsd,máx = 200 kN; aℓ = 30 cm.
# Rsd(ξ) = R  <=>  ξ = L/2·(1 − √(1 − R/200)); no lado esquerdo, o diagrama
# decalado vale Rsd(x + aℓ), então o cruzamento é x = ξ − aℓ.
# 4 barras φ16 de 55 kN cada (Σ = 220 kN), ℓb,nec = 50 cm, 10φ = 16 cm.
L, Z, MMAX, AL = 600.0, 45.0, 9000.0, 30.0
XS = [float(i) for i in range(601)]
MS = [4 * MMAX * x * (L - x) / L ** 2 for x in XS]


def _x_esq(R):
    return L / 2 * (1 - math.sqrt(1 - R / 200.0)) - AL


def _barras(**kw1):
    b = [DV.BarraCorte(f"N{i}", 16.0, 55.0, 50.0) for i in range(1, 5)]
    if kw1:
        b[0] = DV.BarraCorte("N1", 16.0, 55.0, 50.0, **kw1)
    return b


def _cortes(res, nome):
    return {c.lado: c for c in res.cortes if c.nome == nome}


@pytest.fixture(scope="module")
def biapoiada():
    return DV.cobertura_diagrama(XS, MS, Z, AL, _barras(),
                                 x_face_esquerda_cm=20.0, x_face_direita_cm=580.0)


def test_cobertura_decalagem_e_totais(biapoiada):
    assert biapoiada.Fsd_cor_max_kn == pytest.approx(200.0)
    assert biapoiada.R_total_kn == pytest.approx(220.0)
    assert biapoiada.ok
    # patamar do diagrama decalado: [300 − 30; 300 + 30]
    assert biapoiada.Fsd_cor_kn[270] == pytest.approx(200.0)
    assert biapoiada.Fsd_cor_kn[330] == pytest.approx(200.0)
    # Fsd,cor(0) = Rsd(30) = 200·(1 − (270/300)²) = 38 kN
    assert biapoiada.Fsd_cor_kn[0] == pytest.approx(38.0, abs=1e-6)


def test_cobertura_barra_1_a_mao(biapoiada):
    c = _cortes(biapoiada, "N1")
    # R_rest = 165: B = 300·(1 − √0,175) − 30 = 144,50 cm
    # R_cheio = 220 > 200: A no início do patamar, 270 cm
    # ponta = mín(270 − 50 = 220; 144,50 − 16 = 128,50) = 128,50 (10φ além de B)
    assert c["esquerdo"].x_B_cm == pytest.approx(_x_esq(165.0), abs=0.02)
    assert c["esquerdo"].x_A_cm == pytest.approx(270.0, abs=0.02)
    assert c["esquerdo"].x_fim_cm == pytest.approx(_x_esq(165.0) - 16.0, abs=0.02)
    assert "10φ" in c["esquerdo"].governante
    # simetria: lado direito
    assert c["direito"].x_A_cm == pytest.approx(330.0, abs=0.02)
    assert c["direito"].x_fim_cm == pytest.approx(L - (_x_esq(165.0) - 16.0), abs=0.02)
    assert not c["esquerdo"].ate_apoio


def test_cobertura_barra_2_a_mao(biapoiada):
    c = _cortes(biapoiada, "N2")["esquerdo"]
    # B (110 kN) = 300·(1 − √0,45) − 30 = 68,75; A (165 kN) = 144,50
    # ponta = mín(144,50 − 50 = 94,50; 68,75 − 16 = 52,75) = 52,75
    assert c.x_B_cm == pytest.approx(68.754, abs=0.02)
    assert c.x_A_cm == pytest.approx(144.50, abs=0.02)
    assert c.x_fim_cm == pytest.approx(52.754, abs=0.02)


def test_cobertura_barra_3_chega_ao_apoio(biapoiada):
    c = _cortes(biapoiada, "N3")["esquerdo"]
    # B (55 kN) = 300·(1 − √0,725) − 30 = 14,56; ponta = 14,56 − 16 = −1,44 < face (20)
    assert c.x_B_cm == pytest.approx(14.559, abs=0.02)
    assert c.x_fim_cm == pytest.approx(-1.441, abs=0.02)
    assert c.ate_apoio and not c.ponto_A_na_face
    # força na face: Fsd,cor(20) = Rsd(50) = 200·(1 − (250/300)²) = 61,11 kN
    assert c.Fsd_face_kn == pytest.approx(61.111, abs=1e-3)


def test_cobertura_ponto_A_na_face_do_apoio(biapoiada):
    # barra 4 (a última): A em Fsd,cor = 55 kN -> x = 14,56 < face em 20 cm:
    # ancoragem medida a partir da face (18.3.2.3.1, remete a 18.3.2.4 b)
    for lado, c in _cortes(biapoiada, "N4").items():
        assert c.ponto_A_na_face and c.ate_apoio
        assert "face" in c.governante
    # e a força a ancorar na face é a do apoio extremo
    assert _cortes(biapoiada, "N4")["esquerdo"].Fsd_face_kn == pytest.approx(61.111, abs=1e-3)


def test_cobertura_ponto_A_dentro_do_vao_nao_marca_face():
    # mesma viga com a face em 10 cm: A da barra 4 (14,56) fica dentro do vão
    r = DV.cobertura_diagrama(XS, MS, Z, AL, _barras(),
                              x_face_esquerda_cm=10.0, x_face_direita_cm=590.0)
    c = _cortes(r, "N4")["esquerdo"]
    assert not c.ponto_A_na_face and c.ate_apoio


def test_cobertura_ponto_A_alem_da_face_com_forca_crescendo_para_o_apoio():
    # 18.3.2.3.1 (p. 169): A na face ou além E Fsd diminuindo rumo ao centro
    # do apoio. Aqui, entre o centro (x = 0) e a face (x = 20), M cresce
    # rumo ao apoio: Rsd(0) = 5160/45 = 114,7 kN > Rsd(20) = 25,8 kN. A da
    # barra 4 (55 kN) fica em x = 0, além da face, mas a condição de Fsd
    # decrescente falha: não se mede a ancoragem a partir da face.
    ms = [m if x >= 20.0 else MS[20] + (20.0 - x) * 200.0
          for x, m in zip(XS, MS)]
    r = DV.cobertura_diagrama(XS, ms, Z, 0.0, _barras(),
                              x_face_esquerda_cm=20.0, x_face_direita_cm=580.0)
    c = _cortes(r, "N4")["esquerdo"]
    assert c.x_A_cm <= 20.0
    assert not c.ponto_A_na_face
    assert "face do apoio" not in c.governante
    assert c.ate_apoio   # ancora-se no apoio por 18.3.2.4.1


def test_cobertura_barra_dobrada_comeca_em_B():
    r = DV.cobertura_diagrama(XS, MS, Z, AL, _barras(dobrada=True))
    c = _cortes(r, "N1")["esquerdo"]
    assert c.dobrada
    assert c.x_fim_cm == pytest.approx(_x_esq(165.0), abs=0.02)


def test_cobertura_barra_na_mesa_soma_distancia_a_alma():
    # 18.3.2.3.2: barra a 15 cm da alma -> ponta = 128,50 − 15 = 113,50
    r = DV.cobertura_diagrama(XS, MS, Z, AL, _barras(distancia_alma_cm=15.0))
    c = _cortes(r, "N1")
    assert c["esquerdo"].x_fim_cm == pytest.approx(_x_esq(165.0) - 16.0 - 15.0, abs=0.02)
    assert c["direito"].x_fim_cm == pytest.approx(L - (_x_esq(165.0) - 16.0 - 15.0), abs=0.02)


def test_cobertura_lb_nec_governa():
    # barra 2 com ℓb,nec = 100: 144,50 − 100 = 44,50 < 52,75 -> governa ℓb,nec
    b = _barras()
    b[1] = DV.BarraCorte("N2", 16.0, 55.0, 100.0)
    r = DV.cobertura_diagrama(XS, MS, Z, AL, b)
    c = _cortes(r, "N2")["esquerdo"]
    assert c.x_fim_cm == pytest.approx(144.50 - 100.0, abs=0.02)
    assert "ℓb,nec" in c.governante


def test_cobertura_diagrama_linearizado_governa():
    # Rsd: 100 kN até x = 10, cai linearmente a 90 em x = 60 e a 0 em x = 70
    # (aℓ = 0, z = 1). Uma barra de 100 kN, ℓb,nec = 40, φ10:
    # A = 10, B = 70; ℓb,nec de A: 50; 10φ além de B: 80;
    # cobertura em x = 60: 60 + 40·90/100 = 96 -> governa (ponta em 96)
    xs = [0.0, 10.0, 60.0, 70.0, 100.0]
    ms = [100.0, 100.0, 90.0, 0.0, 0.0]
    r = DV.cobertura_diagrama(xs, ms, 1.0, 0.0,
                              [DV.BarraCorte("N1", 10.0, 100.0, 40.0)])
    c = _cortes(r, "N1")["direito"]
    assert c.x_A_cm == pytest.approx(10.0, abs=1e-6)
    assert c.x_B_cm == pytest.approx(70.0, abs=1e-6)
    assert c.x_fim_cm == pytest.approx(96.0, abs=1e-6)
    assert "linearizado" in c.governante


def test_cobertura_armadura_insuficiente():
    b = [DV.BarraCorte(f"N{i}", 16.0, 45.0, 50.0) for i in range(4)]   # 180 < 200
    r = DV.cobertura_diagrama(XS, MS, Z, AL, b)
    assert not r.ok
    assert "NÃO cobre" in r.memoria[0]


def test_cobertura_memoria_cita_item():
    r = DV.cobertura_diagrama(XS, MS, Z, AL, _barras())
    assert all(m.startswith("18.3.2.3.1") for m in r.memoria)
    assert len(r.cortes) == 8


@pytest.mark.parametrize("args", [
    ([0.0], [0.0], 45.0, 30.0),
    ([0.0, 1.0], [0.0, 1.0], 45.0, -1.0),
    ([1.0, 0.0], [0.0, 1.0], 45.0, 30.0),
    ([0.0, 1.0], [0.0, 1.0], 0.0, 30.0),
])
def test_cobertura_fora_da_faixa(args):
    with pytest.raises(Erro):
        DV.cobertura_diagrama(*args, [DV.BarraCorte("N1", 16.0, 55.0, 50.0)])
    with pytest.raises(Erro):
        DV.cobertura_diagrama([0.0, 1.0], [0.0, 1.0], 45.0, 30.0, [])
