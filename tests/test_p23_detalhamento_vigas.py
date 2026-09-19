"""Testes do P23 -- Detalhamento de vigas: estribos, torção e suspensão
(NBR 6118:2026, 18.2.4, 18.3.3.2, 18.3.3.3.2, 18.3.4, 18.3.6 e 18.3.7).

Valores esperados tirados da imagem das páginas do PDF (SCRATCH/nbr_png):
p167 (18.2.4, Figura 18.2), p170 (18.3.3.2, diâmetro do estribo), p171
(18.3.3.2 espaçamentos e emenda; 18.3.3.3.2; 18.3.4 estribo), p172 (18.3.4
barras longitudinais; 18.3.6 suspensão, Figura 18.4), p173 (18.3.7). As
contas à mão estão nos comentários de cada teste.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import cortante_nbr6118 as cort  # noqa: E402
import torcao_nbr6118 as tor  # noqa: E402
import detalhamento_vigas_nbr6118 as DV  # noqa: E402


# ===========================================================================
# 18.2.4 -- proteção contra flambagem (p. 167)
# ===========================================================================
def test_18_2_4_trecho_20_phi_t_exato():
    """20·φt: φt = 6,3 mm -> 126 mm = 12,6 cm; φt = 5 mm -> 10 cm (p. 167)."""
    assert DV.trecho_protegido_flambagem_cm(6.3) == pytest.approx(12.6, abs=1e-12)
    assert DV.trecho_protegido_flambagem_cm(5.0) == pytest.approx(10.0, abs=1e-12)


def test_18_2_4_so_barras_de_canto_dispensa_grampo():
    """4 barras só nos cantos: nenhuma intermediária -> sem grampo (p. 167)."""
    r = DV.protecao_flambagem([], 6.3, comprimento_face_cm=30.0)
    assert r.ok and not r.exige_estribo_suplementar


def test_18_2_4_duas_barras_no_trecho_ok_tres_nao():
    """φt = 5 mm -> trecho de 10 cm. Duas barras a 4 e 8 cm do canto: ok
    ("não houver mais de duas barras, não contando a de canto"). Três barras
    (3, 6, 9 cm): mais de duas no trecho -> grampo (p. 167)."""
    r2 = DV.protecao_flambagem([4.0, 8.0], 5.0)
    assert r2.ok and r2.n_barras_trecho_a == 2
    r3 = DV.protecao_flambagem([3.0, 6.0, 9.0], 5.0)
    assert not r3.ok and r3.exige_estribo_suplementar
    assert r3.barras_desprotegidas == (0, 1, 2)


def test_18_2_4_barra_no_limite_e_fora_dele():
    """φt = 5 mm: barra a 10,0 cm está no trecho (<= 20·φt); a 10,01 cm, fora
    -> grampo obrigatório (p. 167)."""
    assert DV.protecao_flambagem([10.0], 5.0).ok
    r = DV.protecao_flambagem([10.01], 5.0)
    assert not r.ok and r.barras_desprotegidas == (0,)


def test_18_2_4_dois_cantos_figura_18_2_b():
    """Face de 50 cm, φt = 5 mm (trecho 10 cm de cada canto). Barras a 5, 45
    cm: cada uma no trecho de um canto -> ok. Barra a 25 cm: fora dos dois
    trechos -> grampo (Figura 18.2-b, p. 167)."""
    assert DV.protecao_flambagem([5.0, 45.0], 5.0, comprimento_face_cm=50.0).ok
    r = DV.protecao_flambagem([5.0, 25.0, 45.0], 5.0, comprimento_face_cm=50.0)
    assert not r.ok and r.barras_desprotegidas == (1,)


# ===========================================================================
# 18.3.3.2 -- diâmetro do estribo (p. 170)
# ===========================================================================
def test_18_3_3_2_phi_estribo_limites_alta_aderencia():
    """bw = 15 cm: 5 mm <= φt <= 150/10 = 15 mm (p. 170)."""
    assert DV.phi_estribo_limites_mm(15.0) == pytest.approx((5.0, 15.0))


def test_18_3_3_2_phi_estribo_barra_lisa_trava_em_12():
    """bw = 15 cm, barra lisa: máx = min(15; 12) = 12 mm; bw = 10 cm: 10 mm (p. 170)."""
    assert DV.phi_estribo_limites_mm(15.0, "lisa") == pytest.approx((5.0, 12.0))
    assert DV.phi_estribo_limites_mm(10.0, "lisa") == pytest.approx((5.0, 10.0))


def test_18_3_3_2_phi_estribo_bw_largo():
    """bw = 200 cm: máx = 200 mm (não restritivo) (p. 170)."""
    assert DV.phi_estribo_limites_mm(200.0) == pytest.approx((5.0, 200.0))


def test_18_3_3_2_tela_4_2_so_com_protecao_corrosao():
    """Tela soldada: mínimo 4,2 mm desde que haja precaução contra corrosão;
    sem ela, 5 mm (p. 170)."""
    assert DV.phi_estribo_limites_mm(12.0, "tela", protecao_corrosao=True)[0] == 4.2
    assert DV.phi_estribo_limites_mm(12.0, "tela")[0] == 5.0
    # Proteção contra corrosão não reduz o mínimo de barra comum.
    assert DV.phi_estribo_limites_mm(12.0, "alta_aderencia", protecao_corrosao=True)[0] == 5.0


def test_18_3_3_2_phi_estribo_bw_estreito_sem_solucao():
    """bw = 4 cm: bw/10 = 4 mm < 5 mm -> não há estribo admissível (p. 170)."""
    with pytest.raises(nbr.FaixaNormativaError):
        DV.phi_estribo_limites_mm(4.0)


def test_18_3_3_2_barra_canto_minimo_igual_ao_estribo():
    """Estribo φ 6,3 mm -> barra de amarração/canto com φ >= 6,3 mm (p. 171)."""
    assert DV.phi_min_barra_canto_mm(6.3) == 6.3


# ===========================================================================
# 18.3.3.2 -- espaçamentos máximos (p. 171)
# ===========================================================================
def test_18_3_3_2_smax_ramo_baixo():
    """d = 46 cm, Vd = 0,5·VRd2: smáx = min(0,6·46 = 27,6; 30) = 27,6 cm (p. 171)."""
    assert DV.s_max_estribo_cm(50.0, 100.0, 46.0) == pytest.approx(27.6)


def test_18_3_3_2_smax_ramo_baixo_teto_300mm():
    """d = 60 cm, Vd = 0,5·VRd2: 0,6·60 = 36 > 30 -> 30 cm (p. 171)."""
    assert DV.s_max_estribo_cm(50.0, 100.0, 60.0) == pytest.approx(30.0)


def test_18_3_3_2_smax_ramo_alto():
    """d = 60 cm, Vd = 0,8·VRd2: smáx = min(0,3·60 = 18; 20) = 18 cm;
    d = 80 cm: min(24; 20) = 20 cm (p. 171)."""
    assert DV.s_max_estribo_cm(80.0, 100.0, 60.0) == pytest.approx(18.0)
    assert DV.s_max_estribo_cm(80.0, 100.0, 80.0) == pytest.approx(20.0)


def test_18_3_3_2_smax_degrau_067_dois_lados():
    """Degrau proposital (plano, 8.5). d = 46 cm, VRd2 = 300 kN.
    Vd = 0,67·300 = 201 kN -> ramo baixo: 27,6 cm.
    Vd = 201,01 kN -> ramo alto: min(0,3·46 = 13,8; 20) = 13,8 cm (p. 171)."""
    assert DV.s_max_estribo_cm(0.67 * 300.0, 300.0, 46.0) == pytest.approx(27.6)
    assert DV.s_max_estribo_cm(201.01, 300.0, 46.0) == pytest.approx(13.8)
    # O sinal do esforço não muda o limite.
    assert DV.s_max_estribo_cm(-201.01, 300.0, 46.0) == pytest.approx(13.8)


def test_18_3_3_2_st_max_ramos():
    """d = 46 cm: Vd = 0,1·VRd2 -> st = min(46; 80) = 46 cm; Vd = 0,5·VRd2 ->
    st = min(27,6; 35) = 27,6 cm. d = 100 cm: min(100; 80) = 80 cm e
    min(60; 35) = 35 cm (p. 171)."""
    assert DV.st_max_cm(10.0, 100.0, 46.0) == pytest.approx(46.0)
    assert DV.st_max_cm(50.0, 100.0, 46.0) == pytest.approx(27.6)
    assert DV.st_max_cm(10.0, 100.0, 100.0) == pytest.approx(80.0)
    assert DV.st_max_cm(50.0, 100.0, 100.0) == pytest.approx(35.0)


def test_18_3_3_2_st_max_degrau_020_dois_lados():
    """VRd2 = 300 kN, d = 46 cm. Vd = 0,20·300 = 60 kN -> 46 cm;
    Vd = 60,01 kN -> 0,6·46 = 27,6 cm (p. 171)."""
    assert DV.st_max_cm(0.20 * 300.0, 300.0, 46.0) == pytest.approx(46.0)
    assert DV.st_max_cm(60.01, 300.0, 46.0) == pytest.approx(27.6)


def test_18_3_3_2_smax_com_vrd2_do_modelo_I():
    """Integração com P15: VRd2 do Modelo I, C25, bw = 20, d = 46.
    VRd2 = 0,27·(1 − 25/250)·(2,5/1,4)·20·46 = 399,21 kN (17.4.2.2).
    Vd = 250 kN -> 250/399,2 = 0,626 <= 0,67 -> smáx = 27,6 cm."""
    r = cort.modelo_calculo_I(250.0, 20.0, 46.0, 25.0)
    assert r.VRd2 == pytest.approx(0.27 * 0.9 * 2.5 / 1.4 * 20 * 46, rel=1e-6)
    assert DV.s_max_estribo_cm(250.0, r.VRd2, 46.0) == pytest.approx(27.6)


def test_18_3_3_2_vrd2_invalido():
    with pytest.raises(ValueError):
        DV.s_max_estribo_cm(10.0, 0.0, 46.0)


def test_18_3_3_2_emenda_traspasse():
    """Traspasse só em tela ou barra de alta aderência (p. 171)."""
    assert DV.emenda_estribo_permitida("alta_aderencia")
    assert DV.emenda_estribo_permitida("CA-50")
    assert DV.emenda_estribo_permitida("tela")
    assert not DV.emenda_estribo_permitida("lisa")
    assert not DV.emenda_estribo_permitida("CA-25")
    with pytest.raises(ValueError):
        DV.emenda_estribo_permitida("bambu")


def test_18_3_3_2_verificacao_conjunta_ok_e_reprovada():
    """bw = 20, d = 46, VRd2 = 300, Vd = 150 (0,5): smáx = 27,6, st,máx =
    27,6. φt = 6,3 ok (5 <= 6,3 <= 20). s = 25 ok; s = 28 reprova. Barra de
    canto 5 mm < 6,3 reprova. Traspasse em lisa reprova (p. 170-171)."""
    r = DV.verificar_estribos_viga(6.3, 20.0, 46.0, 150.0, 300.0, s_cm=25.0, st_cm=15.0,
                                   phi_canto_mm=8.0, emenda_por_traspasse=True)
    assert r.ok and r.s_max_cm == pytest.approx(27.6) and r.st_max_cm == pytest.approx(27.6)
    assert DV.verificar_estribos_viga(6.3, 20.0, 46.0, 150.0, 300.0, s_cm=28.0).governante \
        == "18.3.3.2 espaçamento longitudinal máximo"
    assert not DV.verificar_estribos_viga(6.3, 20.0, 46.0, 150.0, 300.0, phi_canto_mm=5.0).ok
    r_lisa = DV.verificar_estribos_viga(6.3, 20.0, 46.0, 150.0, 300.0, tipo="lisa",
                                        emenda_por_traspasse=True)
    assert not r_lisa.ok
    assert any("não permitida" in m for m in r_lisa.memoria)
    # φt acima de bw/10: bw = 12 -> máx 12 mm; φt = 12,5 reprova.
    assert not DV.verificar_estribos_viga(12.5, 12.0, 46.0, 150.0, 300.0).ok


# ===========================================================================
# 18.3.3.3.2 -- barras dobradas (p. 171)
# ===========================================================================
def test_18_3_3_3_2_barras_dobradas_45_e_90():
    """α = 45°, d = 46: 0,6·46·(1 + 1) = 55,2 cm; α = 90°: 0,6·46 = 27,6 cm;
    α = 60°: 0,6·46·(1 + 0,57735) = 43,535 cm (p. 171)."""
    assert DV.s_max_barras_dobradas_cm(46.0, 45.0) == pytest.approx(55.2)
    assert DV.s_max_barras_dobradas_cm(46.0, 90.0) == pytest.approx(27.6)
    assert DV.s_max_barras_dobradas_cm(46.0, 60.0) == pytest.approx(
        0.6 * 46.0 * (1.0 + 1.0 / math.sqrt(3.0)))


def test_18_3_3_3_2_barras_dobradas_fora_da_faixa():
    """17.4.1.1.5: 45° <= α <= 90°."""
    with pytest.raises(nbr.FaixaNormativaError):
        DV.s_max_barras_dobradas_cm(46.0, 44.9)
    with pytest.raises(nbr.FaixaNormativaError):
        DV.s_max_barras_dobradas_cm(46.0, 90.1)


# ===========================================================================
# 18.3.4 -- torção (p. 171-172)
# ===========================================================================
def test_18_3_4_estribo_fechado_135():
    """Fechado com gancho a 135°: ok; aberto: reprova; 90°: reprova (p. 171)."""
    assert DV.verificar_estribo_torcao(True, 135.0).ok
    r_aberto = DV.verificar_estribo_torcao(False, 135.0)
    assert not r_aberto.ok and r_aberto.governante == "18.3.4 estribo fechado em todo o contorno"
    r90 = DV.verificar_estribo_torcao(True, 90.0)
    assert not r90.ok and r90.governante == "18.3.4 gancho a 135°"


def test_18_3_4_estribo_torcao_reusa_18_3_3_2():
    """Diâmetro e espaçamento de 18.3.3.2: s = 28 > 27,6 reprova (p. 171)."""
    ok = DV.verificar_estribo_torcao(True, 135.0, phi_t_mm=8.0, bw_cm=20.0, d_cm=46.0,
                                     Vd_kn=150.0, VRd2_kn=300.0, s_cm=20.0)
    assert ok.ok and ok.estribos_cortante is not None
    ruim = DV.verificar_estribo_torcao(True, 135.0, phi_t_mm=8.0, bw_cm=20.0, d_cm=46.0,
                                       Vd_kn=150.0, VRd2_kn=300.0, s_cm=28.0)
    assert not ruim.ok
    with pytest.raises(ValueError):
        DV.verificar_estribo_torcao(True, 135.0, phi_t_mm=8.0)


def test_18_3_4_espacamento_350mm():
    """Perímetro de 320 cm com 8 barras: 40 cm > 35 -> reprova; 10 barras:
    32 cm -> ok. Limite 35 cm exato passa (p. 172)."""
    assert DV.S_MAX_LONGITUDINAL_TORCAO_CM == 35.0
    assert not DV.verificar_espacamento_barras_torcao([320.0 / 8] * 8).ok
    assert DV.verificar_espacamento_barras_torcao([320.0 / 10] * 10).ok
    assert DV.verificar_espacamento_barras_torcao([35.0, 20.0]).ok
    assert not DV.verificar_espacamento_barras_torcao([35.01]).ok


def test_18_3_4_n_min_barras():
    """u = 320 cm: ⌈320/35⌉ = ⌈9,14⌉ = 10; u = 100: ⌈2,86⌉ = 3 < 4 vértices
    -> 4; u = 140: 140/35 = 4 exato -> 4 (p. 172)."""
    assert DV.n_min_barras_longitudinais_torcao(320.0) == 10
    assert DV.n_min_barras_longitudinais_torcao(100.0) == 4
    assert DV.n_min_barras_longitudinais_torcao(140.0, n_vertices=3) == 4


def test_18_3_4_barra_por_vertice():
    """Retangular: 4 vértices com barra -> ok; um vértice sem -> reprova (p. 172)."""
    assert DV.verificar_barra_por_vertice([1, 1, 1, 1]).ok
    r = DV.verificar_barra_por_vertice([1, 1, 0, 1])
    assert not r.ok and r.vertices_sem_barra == (2,)


def test_18_3_4_delta_Asl_delta_u():
    """As,long/ue = 4 cm²/m; trechos de 20, 30 e 50 cm -> 0,8, 1,2 e 2,0 cm²
    (soma 4,0 = 4·100/100). Barras de 0,8, 1,25, 2,0: ok; 1,1 no 2º: reprova
    (p. 172)."""
    exig = DV.distribuir_As_long_torcao_cm2(4.0, [20.0, 30.0, 50.0])
    assert exig == pytest.approx((0.8, 1.2, 2.0))
    assert sum(exig) == pytest.approx(4.0)
    assert DV.verificar_delta_Asl_delta_u([0.8, 1.25, 2.0], [20.0, 30.0, 50.0], 4.0).ok
    r = DV.verificar_delta_Asl_delta_u([0.8, 1.1, 2.0], [20.0, 30.0, 50.0], 4.0)
    assert not r.ok and r.barras_insuficientes == (1,)


def test_18_3_4_delta_Asl_com_torcao_nbr6118():
    """Integração: As,long/ue de torcao_nbr6118 distribuído no perímetro soma
    As,long/ue·ue."""
    taxa = tor.As_long_torcao_cm2_por_m(TSd_kncm=2000.0, Ae_cm2=600.0)
    trechos = [25.0, 25.0, 25.0, 25.0, 25.0, 25.0]
    assert sum(DV.distribuir_As_long_torcao_cm2(taxa, trechos)) == pytest.approx(taxa * 150.0 / 100.0)


# ===========================================================================
# 18.3.6 -- suspensão (p. 172)
# ===========================================================================
def test_18_3_6_viga_pendurada():
    """Fundo da apoiada −50 cm, da apoio −40 cm -> pendurada; −30 contra −40
    -> não; mesmo nível -> não (p. 172)."""
    assert DV.viga_pendurada(-50.0, -40.0)
    assert not DV.viga_pendurada(-30.0, -40.0)
    assert not DV.viga_pendurada(-40.0, -40.0)


def test_18_3_6_fator_reducao():
    """(1 − h_susp/h_apoio): h_susp = 0 -> 1; 20/60 -> 0,6667; 60/60 -> 0 (p. 172)."""
    assert DV.fator_reducao_suspensao(0.0, 60.0) == pytest.approx(1.0)
    assert DV.fator_reducao_suspensao(20.0, 60.0) == pytest.approx(1.0 - 20.0 / 60.0)
    assert DV.fator_reducao_suspensao(60.0, 60.0) == pytest.approx(0.0)
    assert DV.fator_reducao_suspensao(20.0, 60.0, faces_superiores_coincidentes=False) == 1.0
    with pytest.raises(nbr.FaixaNormativaError):
        DV.fator_reducao_suspensao(-1.0, 60.0)
    with pytest.raises(nbr.FaixaNormativaError):
        DV.fator_reducao_suspensao(61.0, 60.0)


def test_18_3_6_suspensao_caso_a_mao():
    """Fd = 100 kN, CA-50: fyd = 500/1,15 = 434,78 MPa = 43,478 kN/cm²;
    As = 100/43,478 = 2,300 cm². Viga de apoio h = 60: 75 % = 1,725 cm² em
    60 cm -> 2,875 cm²/m. Viga apoiada h = 40: 25 % = 0,575 cm² em 40 cm ->
    1,4375 cm²/m. Somando Asw de cortante 2,0 cm²/m na viga de apoio: 4,875
    (p. 172, Figura 18.4)."""
    r = DV.As_suspensao_viga(100.0, 60.0, 40.0, Asw_cisalhamento_viga_apoio_cm2_por_m=2.0)
    As = 100.0 / (500.0 / 1.15 / 10.0)
    assert r.As_tirante_cm2 == pytest.approx(As)
    assert r.As_tirante_cm2 == pytest.approx(2.30, abs=1e-3)
    assert r.As_viga_apoio_min_cm2 == pytest.approx(0.75 * As)
    assert r.As_viga_apoiada_max_cm2 == pytest.approx(0.25 * As)
    assert r.extensao_viga_apoio_cm == 60.0 and r.extensao_viga_apoiada_cm == 40.0
    assert r.taxa_viga_apoio_cm2_por_m == pytest.approx(0.75 * As / 0.60)
    assert r.taxa_viga_apoiada_cm2_por_m == pytest.approx(0.25 * As / 0.40)
    assert r.Asw_total_viga_apoio_cm2_por_m == pytest.approx(0.75 * As / 0.60 + 2.0)


def test_18_3_6_suspensao_viga_nao_continua_e_reducao():
    """Viga de apoio que não passa do cruzamento: extensão h/2 = 30 cm. Com
    fator (1 − 20/60): As = 2,300·0,6667 = 1,5333 cm² (p. 172)."""
    f = DV.fator_reducao_suspensao(20.0, 60.0)
    r = DV.As_suspensao_viga(100.0, 60.0, 40.0, fator_reducao=f,
                             viga_apoio_continua=False, viga_apoiada_continua=False)
    As = f * 100.0 / (500.0 / 1.15 / 10.0)
    assert r.As_tirante_cm2 == pytest.approx(As)
    assert r.extensao_viga_apoio_cm == 30.0 and r.extensao_viga_apoiada_cm == 20.0
    assert r.taxa_viga_apoio_cm2_por_m == pytest.approx(0.75 * As / 0.30)


def test_18_3_6_suspensao_pendurada_e_limites():
    """Pendurada: 100 % na viga de apoio (decisão declarada); fator < 1 e
    fração < 75 % levantam erro."""
    r = DV.As_suspensao_viga(100.0, 60.0, 40.0, pendurada=True)
    assert r.As_viga_apoio_min_cm2 == pytest.approx(r.As_tirante_cm2)
    assert r.As_viga_apoiada_max_cm2 == 0.0
    with pytest.raises(nbr.FaixaNormativaError):
        DV.As_suspensao_viga(100.0, 60.0, 40.0, pendurada=True, fator_reducao=0.8)
    with pytest.raises(nbr.FaixaNormativaError):
        DV.As_suspensao_viga(100.0, 60.0, 40.0, fracao_viga_apoio=0.74)
    r_full = DV.As_suspensao_viga(100.0, 60.0, 40.0, fracao_viga_apoio=1.0)
    assert r_full.As_viga_apoiada_max_cm2 == pytest.approx(0.0)


def test_18_3_6_suspensao_nao_e_a_de_bloco():
    """Risco 3 do plano: nome próprio, sem colidir com blocos_nbr6118."""
    import blocos_nbr6118 as bl
    assert DV.As_suspensao_viga is not getattr(bl, "As_suspensao_total")
    assert not hasattr(DV, "As_suspensao_total")


# ===========================================================================
# 18.3.7 -- ligação mesa-alma (p. 173)
# ===========================================================================
def test_18_3_7_minimo_1_5():
    assert DV.As_ligacao_mesa_alma_min_cm2_por_m() == 1.5


def test_18_3_7_verificacao_ligacao():
    """Sem necessária de cálculo: exigida 1,5. Laje ancorada com 1,0 ->
    adicional 0,5; com 0,5 adicional ok, 0,4 reprova. Necessária 2,4 >
    1,5 governa. Laje não ancorada não conta (p. 173)."""
    r = DV.verificar_ligacao_mesa_alma(0.0, 1.0, 0.5)
    assert r.ok and r.As_adicional_necessaria_cm2_por_m == pytest.approx(0.5)
    assert not DV.verificar_ligacao_mesa_alma(0.0, 1.0, 0.4).ok
    r2 = DV.verificar_ligacao_mesa_alma(2.4, 1.0, 1.0)
    assert r2.As_exigida_cm2_por_m == pytest.approx(2.4) and not r2.ok
    r3 = DV.verificar_ligacao_mesa_alma(0.0, 3.0, 0.0, laje_ancorada=False)
    assert not r3.ok and r3.As_adicional_necessaria_cm2_por_m == pytest.approx(1.5)
