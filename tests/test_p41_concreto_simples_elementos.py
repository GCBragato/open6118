"""Testes do P41 — Concreto simples: elementos (NBR 6118:2026, 24.5.7 e 24.6).

Cobre o bloco P41 de dimensionamento/concreto_simples_nbr6118.py:

  - 24.5.7.2 (G1, exa/eya, área eficaz triangular), p. 228
  - 24.5.7.3 (compressão com força cortante), p. 229
  - 24.6.1 (pilar-parede: NRd, comprimento horizontal, espessura, aberturas), p. 229-230
  - 24.6.2 (blocos de fundação), p. 230
  - 24.6.3 (pilares: remissão, núcleo central, ações laterais, dimensão mínima), p. 230
  - 24.6.4 (arcos: sem tração, 2ª ordem até 10 %), p. 230

Os valores esperados vêm da imagem das páginas (SCRATCH\\nbr_png\\p228 a p230).
Contas à mão nos comentários, só com a norma: fcd = fck/1,68 (24.5.2.1);
σcRd = 0,85·fcd; fctd = 0,7·0,3·fck^(2/3)/1,68 (8.2.5 e 24.5.2.1);
σctRd = 0,85·fctd (24.5.2.2); τwRd = 0,30·fctd (24.5.2.3).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import concreto_simples_nbr6118 as cs          # noqa: E402

FNE = cs.FaixaNormativaError
REL = 1e-9


def _fcd(fck):
    return fck / 1.68


def _fctd(fck):
    return 0.7 * 0.3 * fck ** (2.0 / 3.0) / 1.68


# ---------------------------------------------------------------------------
# 24.5.7.2 — exa, eya (p. 228)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("h, esperado", [
    (30.0, 2.0),    # 0,05·30 = 1,5 < 2 cm -> governa 2 cm
    (40.0, 2.0),    # 0,05·40 = 2,0 = 2 cm (fronteira)
    (60.0, 3.0),    # 0,05·60 = 3,0 > 2 cm
])
def test_24_5_7_2_excentricidade_adicional(h, esperado):
    assert cs.excentricidade_adicional_cm(h) == pytest.approx(esperado, rel=REL)


def test_24_5_7_2_excentricidade_adicional_h_invalido():
    with pytest.raises(FNE):
        cs.excentricidade_adicional_cm(0.0)


# ---------------------------------------------------------------------------
# 24.5.7.2 — G1 e Ae, Figura 24.2 (p. 228)
# ---------------------------------------------------------------------------
def test_24_5_7_2_triangulo_dentro_da_secao():
    # hx = 40, hy = 60; ex = 15, ey = 20; exa = 2, eya = 0,05·60 = 3.
    # G1x = (17; 20): ax = 20 − 17 = 3, ay = 30 − 20 = 10; Ae = (3·3)·(3·10)/2 = 135 cm².
    # G1y = (15; 23): ax = 5, ay = 7; Ae = 15·21/2 = 157,5 cm².
    # Mais desfavorável: G1x (menor Ae). 3ax = 9 <= 40 e 3ay = 30 <= 60 -> sem recorte.
    r = cs.secao_comprimida_excentrica(100.0, 15.0, 20.0, 40.0, 60.0, 20.0)
    assert r.G1x.Ae_cm2 == pytest.approx(135.0, rel=REL)
    assert r.G1y.Ae_cm2 == pytest.approx(157.5, rel=REL)
    assert r.G1.nome == "G1x"
    assert (r.G1.e1x_cm, r.G1.e1y_cm) == (pytest.approx(17.0), pytest.approx(20.0))
    assert (r.G1.ax_cm, r.G1.ay_cm) == (pytest.approx(3.0), pytest.approx(10.0))
    assert not r.G1.recortado
    assert r.Ae_cm2 == pytest.approx(3 * 3.0 * 3 * 10.0 / 2, rel=REL)
    # σSd = 100/135 × 10 = 7,407 MPa; σcRd = 0,85·20/1,68 = 10,119 MPa -> ok.
    assert r.sigma_Sd_mpa == pytest.approx(1000.0 / 135.0, rel=REL)
    assert r.sigma_cRd_mpa == pytest.approx(0.85 * _fcd(20.0), rel=REL)
    assert r.ok
    assert any("24.5.7.2" in m for m in r.memoria)


def test_24_5_7_2_excentricidade_negativa_simetrica():
    # Mesmo caso espelhado: exa soma-se no sentido de ex (e1x = −17).
    r = cs.secao_comprimida_excentrica(100.0, -15.0, -20.0, 40.0, 60.0, 20.0)
    assert r.Ae_cm2 == pytest.approx(135.0, rel=REL)
    assert r.G1.e1x_cm == pytest.approx(-17.0, rel=REL)


def test_24_5_7_2_triangulo_recortado():
    # hx = 40, hy = 60; ex = 10, ey = 5; exa = 2, eya = 3.
    # G1x = (12; 5): ax = 8, ay = 25; catetos 24 e 75; triângulo 900 cm²;
    #   75 > 60: ponta fora = (75 − 60)²·(24/75)/2 = 225·0,32/2 = 36 -> Ae = 864 cm².
    # G1y = (10; 8): ax = 10, ay = 22; catetos 30 e 66; triângulo 990 cm²;
    #   ponta fora = (66 − 60)²·(30/66)/2 = 36·0,4545/2 = 8,1818 -> 981,818 cm².
    r = cs.secao_comprimida_excentrica(500.0, 10.0, 5.0, 40.0, 60.0, 25.0)
    assert r.G1x.Ae_triangulo_cm2 == pytest.approx(900.0, rel=REL)
    assert r.G1x.Ae_cm2 == pytest.approx(864.0, rel=REL)
    assert r.G1y.Ae_cm2 == pytest.approx(990.0 - 36.0 * 30.0 / 66.0 / 2.0, rel=REL)
    assert r.G1.nome == "G1x" and r.G1.recortado
    assert r.sigma_Sd_mpa == pytest.approx(5000.0 / 864.0, rel=REL)


def test_24_5_7_2_carga_centrada_nao_excede_secao():
    # ex = ey = 0, 40 × 40: exa = eya = 2. G1x = (2; 0): ax = 18, ay = 20;
    # catetos 54 e 60, triângulo 1620 cm² (> 1600 da seção);
    # recorte: 14²·(60/54)/2 + 20²·(54/60)/2 = 108,889 + 180 = 288,889 -> Ae = 1331,11 cm².
    r = cs.secao_comprimida_excentrica(100.0, 0.0, 0.0, 40.0, 40.0, 20.0)
    esperado = 1620.0 - 196.0 * (60.0 / 54.0) / 2.0 - 400.0 * 0.9 / 2.0
    assert r.Ae_cm2 == pytest.approx(esperado, rel=REL)
    assert r.Ae_cm2 < 40.0 * 40.0
    assert r.G1x.Ae_cm2 == pytest.approx(r.G1y.Ae_cm2, rel=REL)


def test_24_5_7_2_fronteira_sigma_igual_sigma_cRd():
    # N tal que σSd = σcRd exatamente: N = σcRd·Ae/10 -> passa; 1 % a mais -> não passa.
    s = 0.85 * _fcd(20.0)
    N = s * 135.0 / 10.0
    assert cs.secao_comprimida_excentrica(N, 15.0, 20.0, 40.0, 60.0, 20.0).ok
    assert not cs.secao_comprimida_excentrica(N * 1.01, 15.0, 20.0, 40.0, 60.0, 20.0).ok


def test_24_5_7_2_G1_fora_da_secao():
    # ex = 19, hx = 40: e1x = 21 > hx/2 = 20 -> sem área eficaz.
    with pytest.raises(FNE):
        cs.secao_comprimida_excentrica(100.0, 19.0, 0.0, 40.0, 60.0, 20.0)


def test_24_5_7_2_fck_fora_da_faixa():
    with pytest.raises(FNE):
        cs.secao_comprimida_excentrica(100.0, 0.0, 0.0, 40.0, 60.0, 45.0)


# ---------------------------------------------------------------------------
# 24.5.7.3 — Compressão e força cortante (p. 229)
# ---------------------------------------------------------------------------
def test_24_5_7_3_V_nulo_recai_em_24_5_7_2():
    a = cs.secao_comprimida_excentrica(100.0, 15.0, 20.0, 40.0, 60.0, 20.0)
    b = cs.secao_comprimida_com_cortante(100.0, 0.0, 15.0, 20.0, 40.0, 60.0, 20.0)
    assert b.secao.Ae_cm2 == a.Ae_cm2 and b.secao.sigma_Sd_mpa == a.sigma_Sd_mpa
    assert b.tau_wd_mpa == 0.0 and b.ok == a.ok


def test_24_5_7_3_tau_wd_e_fronteira():
    # Ae = 135 cm²; τwRd = 0,30·fctd(20) = 0,30·0,125·20^(2/3) = 0,27630 MPa.
    # V no limite: V = τwRd·Ae/10 = 3,730 kN -> passa; 1 % a mais -> não passa.
    t = 0.30 * _fctd(20.0)
    V = t * 135.0 / 10.0
    r = cs.secao_comprimida_com_cortante(100.0, V, 15.0, 20.0, 40.0, 60.0, 20.0)
    assert r.tau_wd_mpa == pytest.approx(t, rel=REL)
    assert r.tau_wRd_mpa == pytest.approx(t, rel=REL)
    assert r.ok
    r2 = cs.secao_comprimida_com_cortante(100.0, V * 1.01, 15.0, 20.0, 40.0, 60.0, 20.0)
    assert r2.ok_normal and not r2.ok_cortante and not r2.ok


def test_24_5_7_3_sigma_cmd_majora_tau_wRd():
    # σcmd = 2 MPa, fck = 20: fator 1 + 3·2/20 = 1,3.
    r = cs.secao_comprimida_com_cortante(100.0, 1.0, 15.0, 20.0, 40.0, 60.0, 20.0,
                                         sigma_cmd_mpa=2.0)
    assert r.tau_wRd_mpa == pytest.approx(0.30 * _fctd(20.0) * 1.3, rel=REL)


# ---------------------------------------------------------------------------
# 24.6.1 — NRd do pilar-parede (p. 229)
# ---------------------------------------------------------------------------
def test_24_6_1_NRd_sem_esbeltez():
    # ℓ = 0: NRd = 0,63·fcd·Ac = 0,63 × (20/1,68)/10 × 1500 = 0,75 × 1500 = 1125 kN.
    assert cs.NRd_pilar_parede_kn(20.0, 1500.0, 15.0, 0.0) == pytest.approx(1125.0, rel=REL)


def test_24_6_1_NRd_ponto_interior():
    # ℓ = 240, h = 15, α = 1: α·ℓ/32h = 0,5 -> NRd = 1125 × 0,75 = 843,75 kN.
    assert cs.NRd_pilar_parede_kn(20.0, 1500.0, 15.0, 240.0) == pytest.approx(843.75, rel=REL)
    # α = 0,8, ℓ = 300: 0,8·300/480 = 0,5 -> mesmo valor.
    assert cs.NRd_pilar_parede_kn(20.0, 1500.0, 15.0, 300.0, 0.8) == pytest.approx(843.75, rel=REL)


def test_24_6_1_NRd_esbeltez_de_fronteira():
    # α·ℓ = 32h: NRd = 0. ℓ = 480 (α = 1) e ℓ = 600 (α = 0,8), h = 15.
    assert cs.NRd_pilar_parede_kn(20.0, 1500.0, 15.0, 480.0) == pytest.approx(0.0, abs=1e-12)
    assert cs.NRd_pilar_parede_kn(20.0, 1500.0, 15.0, 600.0, 0.8) == pytest.approx(0.0, abs=1e-12)
    with pytest.raises(FNE):
        cs.NRd_pilar_parede_kn(20.0, 1500.0, 15.0, 481.0)


def test_24_6_1_alfa_nao_definido():
    with pytest.raises(FNE):
        cs.NRd_pilar_parede_kn(20.0, 1500.0, 15.0, 240.0, 0.9)


def test_24_6_1_usa_gama_c_1_68():
    # Com γc = 1,4 daria 0,63·20/1,4/10·1000 = 900 kN; o certo é 0,63·20/1,68/10·1000 = 750 kN.
    assert cs.NRd_pilar_parede_kn(20.0, 1000.0, 20.0, 0.0) == pytest.approx(750.0, rel=REL)


# ---------------------------------------------------------------------------
# 24.6.1 — Comprimento horizontal por carga concentrada (p. 229)
# ---------------------------------------------------------------------------
def test_24_6_1_comprimento_horizontal():
    # h = 15, distância entre apoios 30: 30 + 4·15 = 90 cm.
    assert cs.comprimento_horizontal_carga_cm(15.0, 30.0, 200.0) == pytest.approx(90.0)
    assert cs.comprimento_horizontal_carga_cm(15.0, 30.0, 60.0) == pytest.approx(60.0)
    assert cs.comprimento_horizontal_carga_cm(15.0, 30.0) == pytest.approx(90.0)
    assert cs.comprimento_horizontal_carga_cm(15.0, 30.0, 90.0) == pytest.approx(90.0)


# ---------------------------------------------------------------------------
# 24.6.1 — Espessura mínima (p. 229-230)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("l, fund, esperado", [
    (200.0, False, 10.0),   # 200/24 = 8,33 < 10 -> 10 cm
    (240.0, False, 10.0),   # 240/24 = 10 (fronteira)
    (264.0, False, 11.0),   # 264/24 = 11
    (480.0, False, 20.0),   # 480/24 = 20
    (300.0, True, 15.0),    # 12,5 < 15 -> 15 cm (fundação/sapata corrida)
    (360.0, True, 15.0),    # 360/24 = 15 (fronteira)
    (480.0, True, 20.0),    # 20 > 15
])
def test_24_6_1_espessura_minima(l, fund, esperado):
    assert cs.espessura_minima_pilar_parede_cm(l, fund) == pytest.approx(esperado, rel=REL)


# ---------------------------------------------------------------------------
# 24.6.1 — Verificação do pilar-parede (p. 229)
# ---------------------------------------------------------------------------
def test_24_6_1_verificar_pilar_parede_terco_central():
    # h = 15: terço central |e| <= 2,5 cm. Na fronteira passa; acima levanta erro.
    r = cs.verificar_pilar_parede_simples(80.0, 20.0, 100.0, 15.0, 240.0, e_cm=2.5)
    assert r.NRd_kn == pytest.approx(843.75, rel=REL)
    assert r.ok and r.ok_resistencia and r.ok_espessura
    with pytest.raises(FNE):
        cs.verificar_pilar_parede_simples(80.0, 20.0, 100.0, 15.0, 240.0, e_cm=2.51)


def test_24_6_1_verificar_pilar_parede_limites():
    # NSd = NRd passa; acima não. Espessura 10 cm com ℓ = 264 (mín. 11) reprova.
    assert cs.verificar_pilar_parede_simples(843.75, 20.0, 100.0, 15.0, 240.0).ok
    assert not cs.verificar_pilar_parede_simples(845.0, 20.0, 100.0, 15.0, 240.0).ok
    r = cs.verificar_pilar_parede_simples(10.0, 20.0, 100.0, 10.0, 264.0)
    assert r.ok_resistencia and not r.ok_espessura and not r.ok
    r = cs.verificar_pilar_parede_simples(10.0, 20.0, 100.0, 12.0, 200.0, fundacao=True)
    assert r.h_min_cm == pytest.approx(15.0) and not r.ok


# ---------------------------------------------------------------------------
# 24.6.1 — Armadura nas aberturas (p. 230)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("n, phi, lp, ok", [
    (2, 10.0, 50.0, True),
    (3, 12.5, 60.0, True),
    (1, 10.0, 50.0, False),
    (2, 8.0, 50.0, False),
    (2, 10.0, 49.0, False),
])
def test_24_6_1_armadura_aberturas(n, phi, lp, ok):
    assert cs.verificar_armadura_aberturas(n, phi, lp).ok is ok


# ---------------------------------------------------------------------------
# 24.6.2 — Blocos de fundação (p. 230)
# ---------------------------------------------------------------------------
def test_24_6_2_proibicao_sobre_estacas():
    assert cs.bloco_simples_permitido(False) is True
    assert cs.bloco_simples_permitido(True) is False
    with pytest.raises(FNE):
        cs.verificar_bloco_fundacao_simples(100.0, 100.0, 100.0, 30.0, 30.0, 40.0, 20.0,
                                            sobre_estacas=True)


def test_24_6_2_area_base_reusa_sapatas():
    # Nk = 1000 kN, σadm = 0,02 kN/cm² (0,2 MPa): 1,1·1000/0,02 = 55 000 cm²; K = 1 -> 50 000.
    assert cs.area_base_bloco_simples_cm2(1000.0, 0.02) == pytest.approx(55000.0, rel=REL)
    assert cs.area_base_bloco_simples_cm2(1000.0, 0.02, 1.0) == pytest.approx(50000.0, rel=REL)


def test_24_6_2_espessura_media():
    assert cs.verificar_espessura_bloco_simples(20.0)
    assert not cs.verificar_espessura_bloco_simples(19.0)


def test_24_6_2_momento_e_cortante_na_face():
    # N = 600, L = 150, a = 30: c = 60; M = 600·60²/(2·150) = 7200 kN·cm; V = 600·60/150 = 240 kN.
    assert cs.momento_secao_critica_bloco_kncm(600.0, 150.0, 30.0) == pytest.approx(7200.0)
    assert cs.cortante_secao_critica_bloco_kn(600.0, 150.0, 30.0) == pytest.approx(240.0)
    assert cs.momento_secao_critica_bloco_kncm(600.0, 30.0, 30.0) == 0.0
    with pytest.raises(FNE):
        cs.momento_secao_critica_bloco_kncm(600.0, 30.0, 40.0)


def test_24_6_2_verificar_bloco():
    # N = 100, 100 × 100, coluna 30 × 30, h = 40 contra o solo -> h de cálculo 35.
    # c = 35; M = 100·35²/200 = 612,5 kN·cm; σct = 6·612,5/(100·35²)·10 = 0,3 MPa.
    # V = 100·35/100 = 35 kN; Ac·τwRd = 100·35·0,27630/10 = 96,71 kN.
    r = cs.verificar_bloco_fundacao_simples(100.0, 100.0, 100.0, 30.0, 30.0, 40.0, 20.0)
    assert r.h_calculo_cm == pytest.approx(35.0)
    assert r.Msd_x_kncm == pytest.approx(612.5, rel=REL)
    assert r.sigma_ct_x_mpa == pytest.approx(0.3, rel=REL)
    assert r.sigma_ctRd_mpa == pytest.approx(0.85 * _fctd(20.0), rel=REL)
    assert r.Vsd_x_kn == pytest.approx(35.0, rel=REL)
    assert r.VRd_x_kn == pytest.approx(100.0 * 35.0 * 0.30 * _fctd(20.0) / 10.0, rel=REL)
    assert r.ok
    # Espessura média 19 cm reprova mesmo com o resto ok.
    r = cs.verificar_bloco_fundacao_simples(100.0, 100.0, 100.0, 30.0, 30.0, 40.0, 20.0,
                                            h_medio_cm=19.0)
    assert not r.ok_espessura and not r.ok


def test_24_6_2_cortante_no_limite():
    # VSd = Ac·τwRd exatamente: bloco 100 × 100, coluna 30, h = 40 (35 de cálculo).
    # V = N·35/100 = 96,71 -> N = 96,71/0,35. Flexão: σct = 0,3·N/100 = 0,829 > σctRd;
    # por isso a verificação isolada é pelos valores de cortante.
    t = 0.30 * _fctd(20.0)
    VR = 100.0 * 35.0 * t / 10.0
    N = VR / 0.35
    r = cs.verificar_bloco_fundacao_simples(N, 100.0, 100.0, 30.0, 30.0, 40.0, 20.0)
    assert r.Vsd_x_kn == pytest.approx(r.VRd_x_kn, rel=REL)
    r2 = cs.verificar_bloco_fundacao_simples(N * 1.001, 100.0, 100.0, 30.0, 30.0, 40.0, 20.0)
    assert r.ok_cortante and not r2.ok_cortante


# ---------------------------------------------------------------------------
# 24.6.3 — Pilares (p. 230)
# ---------------------------------------------------------------------------
def test_24_6_3_remissao_ao_pilar_parede():
    # 30 × 20, ℓ = 300: h = 20; NRd = 0,63·(20/1,68)/10·600·[1 − (300/640)²].
    esperado = 0.63 * _fcd(20.0) / 10.0 * 600.0 * (1.0 - (300.0 / 640.0) ** 2)
    assert cs.NRd_pilar_simples_kn(20.0, 30.0, 20.0, 300.0) == pytest.approx(esperado, rel=REL)
    assert cs.NRd_pilar_simples_kn(20.0, 20.0, 30.0, 300.0) == pytest.approx(esperado, rel=REL)


def test_24_6_3_nucleo_central():
    # Retângulo 30 × 60: e = h/6 no limite -> dentro; acima -> fora.
    assert cs.dentro_nucleo_central(5.0, 0.0, 30.0, 60.0)
    assert not cs.dentro_nucleo_central(5.01, 0.0, 30.0, 60.0)
    assert cs.dentro_nucleo_central(0.0, 10.0, 30.0, 60.0)
    assert not cs.dentro_nucleo_central(0.0, -10.1, 30.0, 60.0)
    # Losango: 6·2,5/30 + 6·5/60 = 0,5 + 0,5 = 1 -> limite, dentro.
    assert cs.dentro_nucleo_central(2.5, 5.0, 30.0, 60.0)
    assert not cs.dentro_nucleo_central(2.5, 5.1, 30.0, 60.0)


@pytest.mark.parametrize("H, esperado", [
    (150.0, 20.0),   # 15 < 20
    (200.0, 20.0),   # 20 = 20 (fronteira)
    (300.0, 30.0),   # 30 > 20
])
def test_24_6_3_dimensao_minima(H, esperado):
    assert cs.dimensao_minima_pilar_simples_cm(H) == pytest.approx(esperado, rel=REL)


def test_24_6_3_verificar_pilar():
    r = cs.verificar_pilar_simples(100.0, 20.0, 30.0, 30.0, 300.0, ex_cm=5.0)
    assert r.ok and r.nucleo_central and r.ok_dimensao
    r = cs.verificar_pilar_simples(100.0, 20.0, 30.0, 30.0, 300.0, ex_cm=5.1)
    assert not r.ok_nucleo and not r.ok
    r = cs.verificar_pilar_simples(100.0, 20.0, 25.0, 30.0, 300.0)
    assert not r.ok_dimensao and not r.ok


def test_24_6_3_acao_lateral():
    # b = 20, h = 30, N = 100: σ0 = 100/600·10 = 1,6667 MPa.
    f = cs.verificar_pilar_simples_acao_lateral
    r = f(100.0, 0.0, 20.0, 30.0, 20.0)
    assert r.sigma_max_mpa == pytest.approx(1000.0 / 600.0, rel=REL) and r.ok
    # e = h/6 = 5 (M = 500): σmax = 2·σ0, σmin = 0, seção toda comprimida.
    r = f(100.0, 500.0, 20.0, 30.0, 20.0)
    assert r.sigma_max_mpa == pytest.approx(2000.0 / 600.0, rel=REL)
    assert r.x_comprimido_cm == pytest.approx(30.0)
    # e = h/3 = 10 (M = 1000): x = 3·(15 − 10) = 15 = h/2 -> contém o centroide (limite);
    # σmax = 2·100/(20·15)·10 = 6,667 MPa.
    r = f(100.0, 1000.0, 20.0, 30.0, 20.0)
    assert r.x_comprimido_cm == pytest.approx(15.0, rel=REL)
    assert r.sigma_max_mpa == pytest.approx(2000.0 / 300.0, rel=REL) and r.ok
    # e = 10,5: x = 13,5 < 15 -> não contém o centroide.
    assert not f(100.0, 1050.0, 20.0, 30.0, 20.0).ok
    # σmax > σcRd = 10,119 MPa: N = 700, M = 0 -> 11,67 MPa.
    assert not f(700.0, 0.0, 20.0, 30.0, 20.0).ok


# ---------------------------------------------------------------------------
# 24.6.4 — Arcos (p. 230)
# ---------------------------------------------------------------------------
def test_24_6_4_sem_tracao_borda_do_nucleo():
    # b = 20, h = 30, N = 100, M = 500 (e = h/6): σmin = 0 exato -> passa.
    r = cs.verificar_sem_tracao(100.0, 500.0, 20.0, 30.0)
    assert r.sigma_min_mpa == pytest.approx(0.0, abs=1e-12) and r.ok
    assert r.sigma_max_mpa == pytest.approx(2000.0 / 600.0, rel=REL)
    assert cs.verificar_sem_tracao(100.0, -500.0, 20.0, 30.0).ok
    assert not cs.verificar_sem_tracao(100.0, 501.0, 20.0, 30.0).ok
    with pytest.raises(FNE):
        cs.verificar_sem_tracao(-100.0, 0.0, 20.0, 30.0)


def test_24_6_4_arco_varias_secoes():
    r = cs.verificar_arco_sem_tracao([(100.0, 0.0), (100.0, 400.0), (100.0, 300.0)], 20.0, 30.0)
    assert r.ok and r.indice_critico == 1
    r = cs.verificar_arco_sem_tracao([(100.0, 0.0), (100.0, 600.0)], 20.0, 30.0)
    assert not r.ok and r.indice_critico == 1


def test_24_6_4_majoracao_2a_ordem():
    # M1 = 100 -> M2,max = 110; 110 passa; acima reprova (não trunca).
    assert cs.momento_2a_ordem_max_arco_kncm(100.0) == pytest.approx(110.0, rel=REL)
    assert cs.verificar_majoracao_2a_ordem_arco(100.0, 110.0).ok
    r = cs.verificar_majoracao_2a_ordem_arco(100.0, 111.0)
    assert not r.ok and r.M2d_kncm == pytest.approx(111.0)
    with pytest.raises(FNE):
        cs.verificar_majoracao_2a_ordem_arco(0.0, 10.0)
