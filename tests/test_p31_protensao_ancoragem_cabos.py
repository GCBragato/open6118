"""Testes do P31 — Protensão: ancoragem ativa, introdução da força e cabos.

Cobre dimensionamento/ancoragem_nbr6118.py (bloco P31) e o novo
dimensionamento/protensao_detalhamento_nbr6118.py, contra a ABNT NBR
6118:2026:

  - 9.3.2.2  fbpd e ηp2 (armadura ativa pré-tracionada), p. 54
  - 9.4.5.1  ℓbp, comprimento de ancoragem básico, p. 59
  - 9.4.5.2  ℓbpt, comprimento de transferência, p. 59
  - 9.4.5.3  ℓbpd, comprimento de ancoragem necessário, p. 59
  - 9.6.2.2  ângulo de difusão β, pós-tração, p. 68
  - 9.6.2.3  distância de regularização ℓp, pré-tração, p. 69
  - 18.6.1.2 raio mínimo de curvatura, p. 175
  - 18.6.1.5 extremidades retas mínimas, p. 175
  - 18.6.2.2 agrupamento de cabos em bainhas, p. 176
  - 18.6.2.3 Tabelas 18.1 e 18.2, p. 177

Os valores esperados vêm da imagem de cada página (SCRATCH\\nbr_png\\pNNN.png),
não do JSON do plano nem de apostila; as contas à mão estão nos comentários.
"""

from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr                          # noqa: E402
import ancoragem_nbr6118 as anc                        # noqa: E402
import protensao_detalhamento_nbr6118 as pd            # noqa: E402


# ===========================================================================
# 9.3.2.2 — fbpd e ηp2 (PDF p. 54)
# ===========================================================================
def test_9322_eta_p2_boa_ma_aderencia():
    """ηp2 = 1,0 boa aderência; 0,7 má aderência (9.3.2.2, p. 54; mesma
    classificação de 9.3.1)."""
    assert anc.eta_p2(True) == pytest.approx(1.0)
    assert anc.eta_p2(False) == pytest.approx(0.7)


def test_9322_fbpd_cordoalha_boa_aderencia_28_dias():
    """fbpd = ηp1*ηp2*fctd. Cordoalha (ηp1=1,2), boa aderência (ηp2=1,0),
    fck=30 MPa aos 28 dias: fctd = 0,7*fctm/1,4.
    fctm(30) = 0,3*30^(2/3) = 2,896 MPa (8.2.5, grupo I).
    fctd = 0,7*2,896/1,4 = 1,448 MPa; fbpd = 1,2*1,0*1,448 = 1,7376 MPa.
    """
    fbpd = anc.fbpd_mpa(30.0, tipo="cordoalha", boa_aderencia=True)
    fctm = 0.3 * 30.0 ** (2.0 / 3.0)
    fctd = 0.7 * fctm / 1.4
    esperado = 1.2 * 1.0 * fctd
    assert fbpd == pytest.approx(esperado, rel=1e-9)
    assert fbpd == pytest.approx(1.7376, rel=2e-3)


def test_9322_fbpd_fio_liso_ma_aderencia():
    """Fio liso (ηp1=1,0), má aderência (ηp2=0,7), fck=25 MPa.
    fctm(25) = 0,3*25^(2/3) = 2,565 MPa; fctd = 0,7*2,565/1,4 = 1,2826 MPa.
    fbpd = 1,0*0,7*1,2826 = 0,8978 MPa.
    """
    fbpd = anc.fbpd_mpa(25.0, tipo="fio liso", boa_aderencia=False)
    fctm = 0.3 * 25.0 ** (2.0 / 3.0)
    fctd = 0.7 * fctm / 1.4
    esperado = 1.0 * 0.7 * fctd
    assert fbpd == pytest.approx(esperado, rel=1e-9)


def test_9322_fbpd_fio_dentado_maior_que_cordoalha():
    """ηp1: fio dentado (1,4) > cordoalha (1,2) > fio liso (1,0) — mesma
    fctd, fbpd cresce na mesma ordem."""
    fbpd_liso = anc.fbpd_mpa(30.0, tipo="fio liso")
    fbpd_cord = anc.fbpd_mpa(30.0, tipo="cordoalha")
    fbpd_dent = anc.fbpd_mpa(30.0, tipo="fio dentado")
    assert fbpd_liso < fbpd_cord < fbpd_dent
    assert fbpd_cord / fbpd_liso == pytest.approx(1.2, rel=1e-9)
    assert fbpd_dent / fbpd_liso == pytest.approx(1.4, rel=1e-9)


# ===========================================================================
# 9.4.5.1 — Comprimento de ancoragem básico ℓbp (PDF p. 59)
# ===========================================================================
def test_9451_lbp_fio_isolado():
    """Fios isolados: ℓbp = (φ/4)*(fpyd/fbpd).
    φ=12,7mm, fpyd=1450MPa, fbpd=2,0MPa:
    ℓbp = (12,7/4)*(1450/2,0) = 3,175*725 = 2301,875 mm = 230,1875 cm.
    """
    lbp = anc.lbp_cm(phi_mm=12.7, fpyd_mpa=1450.0, fbpd_mpa_valor=2.0,
                     tipo="fio liso")
    assert lbp == pytest.approx(230.1875, rel=1e-9)


def test_9451_lbp_fio_dentado_mesma_formula_que_liso():
    """Fio dentado usa o mesmo multiplicador 1/4 de fio liso (ambos são
    'fios isolados' no texto de 9.4.5.1); só ηp1 (9.3.2.2) diferencia os
    dois na composição de fbpd."""
    lbp_liso = anc.lbp_cm(12.7, 1450.0, 2.0, tipo="fio liso")
    lbp_dent = anc.lbp_cm(12.7, 1450.0, 2.0, tipo="fio dentado")
    assert lbp_liso == pytest.approx(lbp_dent, rel=1e-9)


def test_9451_lbp_cordoalha_3_7_fios():
    """Cordoalhas de três ou sete fios: ℓbp = (7φ/36)*(fpyd/fbpd).
    φ=12,7mm, fpyd=1450MPa, fbpd=1,7376MPa (do teste de fbpd acima):
    ℓbp = (7*12,7/36)*(1450/1,7376) = 2,46944...*834,564... mm.
    """
    fbpd = anc.fbpd_mpa(30.0, tipo="cordoalha")
    lbp = anc.lbp_cm(phi_mm=12.7, fpyd_mpa=1450.0, fbpd_mpa_valor=fbpd,
                     tipo="cordoalha")
    esperado_mm = (7.0 * 12.7 / 36.0) * (1450.0 / fbpd)
    assert lbp == pytest.approx(esperado_mm / 10.0, rel=1e-9)


def test_9451_lbp_cordoalha_menor_que_fio_isolado_mesmo_fbpd():
    """7/36 ~= 0,1944 < 1/4 = 0,25: a cordoalha dá ℓbp menor que fio
    isolado, para o mesmo φ, fpyd e fbpd."""
    lbp_fio = anc.lbp_cm(12.7, 1450.0, 2.0, tipo="fio liso")
    lbp_cord = anc.lbp_cm(12.7, 1450.0, 2.0, tipo="cordoalha")
    assert lbp_cord < lbp_fio


def test_9451_lbp_tipo_invalido():
    with pytest.raises(ValueError):
        anc.lbp_cm(12.7, 1450.0, 2.0, tipo="barra")


# ===========================================================================
# 9.4.5.2 — Comprimento de transferência ℓbpt (PDF p. 59)
# ===========================================================================
def test_9452_lbpt_fios_liberacao_gradual():
    """Fios dentados ou lisos, liberação gradual (a):
    ℓbpt = 0,7*ℓbp*(σpi/fpyd).
    ℓbp=230,1875cm, σpi=1300MPa, fpyd=1450MPa:
    ℓbpt = 0,7*230,1875*(1300/1450) = 144,3486... cm.
    """
    lbpt = anc.lbpt_cm(lbp_cm_valor=230.1875, sigma_pi_mpa=1300.0,
                       fpyd_mpa=1450.0, tipo="fio liso",
                       liberacao_gradual=True)
    esperado = 0.7 * 230.1875 * (1300.0 / 1450.0)
    assert lbpt == pytest.approx(esperado, rel=1e-9)


def test_9452_lbpt_cordoalha_liberacao_gradual():
    """Cordoalhas de três ou sete fios, liberação gradual:
    ℓbpt = 0,5*ℓbp*(σpi/fpyd)."""
    lbpt = anc.lbpt_cm(lbp_cm_valor=200.0, sigma_pi_mpa=1300.0,
                       fpyd_mpa=1450.0, tipo="cordoalha",
                       liberacao_gradual=True)
    esperado = 0.5 * 200.0 * (1300.0 / 1450.0)
    assert lbpt == pytest.approx(esperado, rel=1e-9)


def test_9452_lbpt_liberacao_subita_multiplica_por_1_25():
    """(b) liberação não gradual (súbita): o valor de (a) é multiplicado
    por 1,25 — mesmo tipo, mesmos dados, só muda liberacao_gradual."""
    lbpt_gradual = anc.lbpt_cm(200.0, 1300.0, 1450.0, "cordoalha", True)
    lbpt_subita = anc.lbpt_cm(200.0, 1300.0, 1450.0, "cordoalha", False)
    assert lbpt_subita == pytest.approx(1.25 * lbpt_gradual, rel=1e-9)


def test_9452_lbpt_fio_maior_que_cordoalha_mesmo_lbp():
    """0,7 > 0,5: para o mesmo ℓbp, σpi e fpyd, fio (dentado/liso) dá ℓbpt
    maior que cordoalha."""
    lbpt_fio = anc.lbpt_cm(200.0, 1300.0, 1450.0, "fio liso", True)
    lbpt_dentado = anc.lbpt_cm(200.0, 1300.0, 1450.0, "fio dentado", True)
    lbpt_cordoalha = anc.lbpt_cm(200.0, 1300.0, 1450.0, "cordoalha", True)
    assert lbpt_fio == pytest.approx(lbpt_dentado, rel=1e-9)
    assert lbpt_cordoalha < lbpt_fio


# ===========================================================================
# 9.4.5.3 — Comprimento de ancoragem necessário ℓbpd (PDF p. 59)
# ===========================================================================
def test_9453_lbpd_formula():
    """ℓbpd = ℓbpt + ℓbp*(fpyd - σp∞)/fpyd.
    ℓbpt=144,35cm, ℓbp=230,19cm, fpyd=1450MPa, σp∞=1100MPa:
    ℓbpd = 144,35 + 230,19*(1450-1100)/1450 = 144,35 + 55,563... cm.
    """
    lbpd = anc.lbpd_cm(lbpt_cm_valor=144.35, lbp_cm_valor=230.19,
                       fpyd_mpa=1450.0, sigma_p_inf_mpa=1100.0)
    esperado = 144.35 + 230.19 * (1450.0 - 1100.0) / 1450.0
    assert lbpd == pytest.approx(esperado, rel=1e-9)


def test_9453_lbpd_sem_perdas_reduz_ao_lbpt_mais_zero():
    """Se σp∞ = fpyd (nenhuma perda, caso limite teórico), o segundo termo
    zera e ℓbpd = ℓbpt."""
    lbpd = anc.lbpd_cm(100.0, 200.0, 1450.0, 1450.0)
    assert lbpd == pytest.approx(100.0, rel=1e-9)


# ===========================================================================
# sec9.py — fachada sobre ancoragem_nbr6118 (P31)
# ===========================================================================
def _sec9():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "secoes_norma"))
    import sec9 as legado
    return legado


def test_sec9_res_ade_ati_facade_mesmo_numero():
    legado = _sec9()
    with pytest.warns(DeprecationWarning):
        fbpd_legado = legado.res_ade_ati("cordoalha", "boa", fctd=1.4482)
    esperado = nbr.eta_p1("cordoalha") * anc.eta_p2(True) * 1.4482
    assert fbpd_legado == pytest.approx(esperado, rel=1e-9)


def test_sec9_comp_ancor_basico_ativo_facade_mesmo_numero():
    legado = _sec9()
    with pytest.warns(DeprecationWarning):
        lbp_legado = legado.comp_ancor_basico_ativo(12.7, 1450.0, 2.0, "grupo")
    lbp_novo = anc.lbp_cm(12.7, 1450.0, 2.0, tipo="cordoalha")
    assert lbp_legado == pytest.approx(lbp_novo, rel=1e-9)


def test_sec9_comp_transferencia_facade_mesmo_numero():
    legado = _sec9()
    with pytest.warns(DeprecationWarning):
        lbpt_legado = legado.comp_transferencia(200.0, 1300.0, 1450.0,
                                                "isolado", liberacao_gradual=False)
    lbpt_novo = anc.lbpt_cm(200.0, 1300.0, 1450.0, tipo="fio liso",
                            liberacao_gradual=False)
    assert lbpt_legado == pytest.approx(lbpt_novo, rel=1e-9)


def test_sec9_comp_ancor_necessario_ativo_facade_mesmo_numero():
    legado = _sec9()
    with pytest.warns(DeprecationWarning):
        lbpd_legado = legado.comp_ancor_necessario_ativo(144.35, 230.19, 1450.0, 1100.0)
    lbpd_novo = anc.lbpd_cm(144.35, 230.19, 1450.0, 1100.0)
    assert lbpd_legado == pytest.approx(lbpd_novo, rel=1e-9)


# ===========================================================================
# 9.6.2.2 — Ângulo de difusão β, pós-tração (PDF p. 68)
# ===========================================================================
def test_9622_angulo_beta_tangente_2_tercos():
    """tg(β) = 2/3 (Figura 9.7)."""
    beta = pd.angulo_difusao_beta_graus()
    assert math.tan(math.radians(beta)) == pytest.approx(2.0 / 3.0, rel=1e-9)
    assert beta == pytest.approx(33.690068, rel=1e-6)


# ===========================================================================
# 9.6.2.3 — Distância de regularização ℓp, pré-tração (PDF p. 69)
# ===========================================================================
def test_9623_lp_formula_geral():
    """ℓp = raiz(h² + (0,6*ℓbpt)²), h=60cm, ℓbpt=40cm:
    ℓp = raiz(3600 + (24)²) = raiz(3600+576) = raiz(4176) = 64,622... cm."""
    lp = pd.lp_regularizacao_cm(h_cm=60.0, lbpt_cm=40.0)
    esperado = math.sqrt(60.0 ** 2 + (0.6 * 40.0) ** 2)
    assert lp == pytest.approx(esperado, rel=1e-9)
    assert lp >= 40.0


def test_9623_lp_nunca_menor_que_lbpt_h_pequeno():
    """h muito pequeno frente a 0,6*ℓbpt: a raiz tende a 0,6*ℓbpt, que é
    menor que ℓbpt — o piso ℓp >= ℓbpt (implícito no 'máx' da norma) tem
    de prevalecer."""
    lp = pd.lp_regularizacao_cm(h_cm=1.0, lbpt_cm=100.0)
    assert lp == pytest.approx(100.0, rel=1e-9)


def test_9623_lp_h_grande_domina_a_raiz():
    """h muito maior que 0,6*ℓbpt: ℓp ~= h (a raiz é dominada pelo primeiro
    termo) e continua >= ℓbpt."""
    lp = pd.lp_regularizacao_cm(h_cm=200.0, lbpt_cm=10.0)
    esperado = math.sqrt(200.0 ** 2 + (0.6 * 10.0) ** 2)
    assert lp == pytest.approx(esperado, rel=1e-9)
    assert lp == pytest.approx(200.0, rel=1e-3)
    assert lp >= 10.0


# ===========================================================================
# 18.6.1.2 — Raio mínimo de curvatura (PDF p. 175)
# ===========================================================================
def test_18612_raio_minimo_por_tipo():
    """R >= 4m fios; >= 8m barras; >= 12m cordoalhas, dispensam
    justificativa (18.6.1.2)."""
    assert pd.raio_minimo_curvatura_m("fio") == pytest.approx(4.0)
    assert pd.raio_minimo_curvatura_m("barra") == pytest.approx(8.0)
    assert pd.raio_minimo_curvatura_m("cordoalha") == pytest.approx(12.0)


def test_18612_tipo_invalido():
    with pytest.raises(ValueError):
        pd.raio_minimo_curvatura_m("fibra")


# ===========================================================================
# 18.6.1.5 — Extremidades retas mínimas (PDF p. 175)
# ===========================================================================
def test_18615_extremidade_reta_geral_100cm():
    assert pd.trecho_reto_extremidade_min_cm() == pytest.approx(100.0)
    assert pd.trecho_reto_extremidade_min_cm(monocordoalha_engraxada=False) == pytest.approx(100.0)


def test_18615_extremidade_reta_monocordoalha_engraxada_50cm():
    assert pd.trecho_reto_extremidade_min_cm(monocordoalha_engraxada=True) == pytest.approx(50.0)


# ===========================================================================
# 18.6.2.2 — Agrupamento de cabos em bainhas (PDF p. 176)
# ===========================================================================
def test_18622_trecho_reto_ate_4_cabos_ok():
    for n in (1, 2, 3, 4):
        r = pd.verificar_agrupamento_cabos(n, trecho="reto")
        assert r.ok, f"n={n} deveria ser ok em trecho reto"


def test_18622_trecho_reto_5_cabos_reprova():
    r = pd.verificar_agrupamento_cabos(5, trecho="reto")
    assert not r.ok


def test_18622_trecho_reto_mais_de_2_adjacentes_em_linha_reprova():
    r_ok = pd.verificar_agrupamento_cabos(4, trecho="reto",
                                          cabos_adjacentes_em_linha=2)
    r_reprova = pd.verificar_agrupamento_cabos(4, trecho="reto",
                                               cabos_adjacentes_em_linha=3)
    assert r_ok.ok
    assert not r_reprova.ok


def test_18622_trecho_curvo_so_pares():
    r1 = pd.verificar_agrupamento_cabos(1, trecho="curvo")
    r2 = pd.verificar_agrupamento_cabos(2, trecho="curvo")
    r3 = pd.verificar_agrupamento_cabos(3, trecho="curvo")
    assert r1.ok
    assert r2.ok
    assert not r3.ok


def test_18622_trecho_curvo_planos_nao_paralelos_reprova():
    r = pd.verificar_agrupamento_cabos(2, trecho="curvo", planos_paralelos=False)
    assert not r.ok


def test_18622_trecho_invalido():
    with pytest.raises(ValueError):
        pd.verificar_agrupamento_cabos(2, trecho="diagonal")


# ===========================================================================
# 18.6.2.3 — Tabela 18.1, espaçamentos mínimos entre bainhas, pós-tração
# (PDF p. 177) — todas as células da tabela
# ===========================================================================
def test_18_1_isoladas_governa_diametro():
    """φext=80mm=8cm >= pisos: ah=máx(8,4)=8cm; av=máx(8,5)=8cm."""
    r = pd.espacamento_min_bainhas_cm(phi_ext_mm=80.0, disposicao="isoladas")
    assert r.ah_min_cm == pytest.approx(8.0)
    assert r.av_min_cm == pytest.approx(8.0)


def test_18_1_isoladas_governa_piso():
    """φext=20mm=2cm < pisos: ah=máx(2,4)=4cm; av=máx(2,5)=5cm."""
    r = pd.espacamento_min_bainhas_cm(phi_ext_mm=20.0, disposicao="isoladas")
    assert r.ah_min_cm == pytest.approx(4.0)
    assert r.av_min_cm == pytest.approx(5.0)


def test_18_1_agrupadas_governa_diametro():
    """φext=100mm=10cm: ah=máx(1,2*10,4)=12cm; av=máx(1,5*10,5)=15cm."""
    r = pd.espacamento_min_bainhas_cm(phi_ext_mm=100.0, disposicao="agrupadas")
    assert r.ah_min_cm == pytest.approx(12.0)
    assert r.av_min_cm == pytest.approx(15.0)


def test_18_1_agrupadas_governa_piso():
    """φext=20mm=2cm: ah=máx(1,2*2,4)=4cm; av=máx(1,5*2,5)=5cm."""
    r = pd.espacamento_min_bainhas_cm(phi_ext_mm=20.0, disposicao="agrupadas")
    assert r.ah_min_cm == pytest.approx(4.0)
    assert r.av_min_cm == pytest.approx(5.0)


def test_18_1_disposicao_invalida():
    with pytest.raises(ValueError, match="disposição"):
        pd.espacamento_min_bainhas_cm(50.0, disposicao="triplas")


# ===========================================================================
# 18.6.2.3 — Tabela 18.2, espaçamentos mínimos entre fios/cordoalhas,
# pré-tração (PDF p. 177) — todas as células da tabela
# ===========================================================================
def test_18_2_isolados_governa_diametro():
    """φ=20mm=2cm, dmáx=9,5mm=0,95cm: ah=av=máx(2*2, 1,2*0,95, 2)=máx(4;1,14;2)=4cm."""
    r = pd.espacamento_min_fios_cm(phi_mm=20.0, dmax_mm=9.5, disposicao="isolados")
    assert r.ah_min_cm == pytest.approx(4.0)
    assert r.av_min_cm == pytest.approx(4.0)


def test_18_2_isolados_governa_dmax():
    """φ=5mm=0,5cm, dmáx=25mm=2,5cm: 2*φ=1cm; 1,2*dmáx=3cm; piso=2cm ->
    ah=av=3cm (dmáx governa)."""
    r = pd.espacamento_min_fios_cm(phi_mm=5.0, dmax_mm=25.0, disposicao="isolados")
    assert r.ah_min_cm == pytest.approx(3.0)
    assert r.av_min_cm == pytest.approx(3.0)


def test_18_2_isolados_governa_piso():
    """φ=5mm=0,5cm, dmáx=9,5mm=0,95cm: 2*φ=1cm; 1,2*dmáx=1,14cm; piso=2cm
    -> ah=av=2cm (piso governa)."""
    r = pd.espacamento_min_fios_cm(phi_mm=5.0, dmax_mm=9.5, disposicao="isolados")
    assert r.ah_min_cm == pytest.approx(2.0)
    assert r.av_min_cm == pytest.approx(2.0)


def test_18_2_pares_horizontal_governa_diametro():
    """φ=20mm=2cm, dmáx=9,5mm=0,95cm: 3*φ=6cm >> pisos -> ah=av=6cm."""
    r = pd.espacamento_min_fios_cm(phi_mm=20.0, dmax_mm=9.5,
                                   disposicao="pares_horizontal")
    assert r.ah_min_cm == pytest.approx(6.0)
    assert r.av_min_cm == pytest.approx(6.0)


def test_18_2_pares_horizontal_governa_piso_ah_2_5_av_2():
    """φ=1mm=0,1cm, dmáx=9,5mm=0,95cm: 3*φ=0,3cm; 1,2*dmáx=1,14cm; pisos
    2,5cm (ah) e 2cm (av) -> ah=2,5cm; av=2cm (pisos diferentes por eixo)."""
    r = pd.espacamento_min_fios_cm(phi_mm=1.0, dmax_mm=9.5,
                                   disposicao="pares_horizontal")
    assert r.ah_min_cm == pytest.approx(2.5)
    assert r.av_min_cm == pytest.approx(2.0)


def test_18_2_pares_ambas_direcoes_governa_diametro():
    """φ=20mm=2cm, dmáx=9,5mm=0,95cm: 3*φ=6cm -> ah=av=6cm."""
    r = pd.espacamento_min_fios_cm(phi_mm=20.0, dmax_mm=9.5,
                                   disposicao="pares_ambas_direcoes")
    assert r.ah_min_cm == pytest.approx(6.0)
    assert r.av_min_cm == pytest.approx(6.0)


def test_18_2_pares_ambas_direcoes_governa_piso_3cm():
    """φ=1mm=0,1cm, dmáx=9,5mm=0,95cm: 3*φ=0,3cm; 1,2*dmáx=1,14cm; piso
    3cm nos dois eixos -> ah=av=3cm."""
    r = pd.espacamento_min_fios_cm(phi_mm=1.0, dmax_mm=9.5,
                                   disposicao="pares_ambas_direcoes")
    assert r.ah_min_cm == pytest.approx(3.0)
    assert r.av_min_cm == pytest.approx(3.0)


def test_18_2_disposicao_invalida():
    with pytest.raises(ValueError, match="disposição"):
        pd.espacamento_min_fios_cm(10.0, 9.5, disposicao="triplos")
