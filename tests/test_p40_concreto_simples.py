"""Testes do P40 — Concreto simples: núcleo e seções (NBR 6118:2026, 24.2 a 24.5.6).

Cobre dimensionamento/concreto_simples_nbr6118.py contra a ABNT NBR 6118:2026:

  - 24.2 (campo de aplicação), p. 224; 24.5.2.5 (peças curvas e torção de
    equilíbrio), p. 226
  - 24.3 (C15 a C40), p. 224
  - 24.4 (juntas a cada 15 m; armadura a 6 cm da junta), p. 224
  - 24.5.2.1 a 24.5.2.6 (γc = 1,68; σcRd, σctRd; τwRd; τRd <= 1,0 MPa), p. 225-226
  - 24.5.3 (h − 5 cm contra o solo), p. 226
  - 24.5.4.1 a 24.5.4.3 (deformações-limite; 0,8·fctd), p. 226-227
  - 24.5.5.1 a 24.5.5.3 e 24.5.6 (τwd = 3V/(2bh); seção crítica; torção), p. 227

Os valores esperados vêm da imagem de cada página (SCRATCH\\nbr_png\\pNNN.png).
As contas à mão estão nos comentários e usam só a norma (fct,m = 0,3·fck^(2/3),
8.2.5; fctk,inf = 0,7·fct,m; γc = 1,2 × 1,4 = 1,68).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr                   # noqa: E402
import concreto_simples_nbr6118 as cs          # noqa: E402

REL = 1e-9


def _fctd_mao(fck):
    """fctd = 0,7·0,3·fck^(2/3)/1,68 (8.2.5 e 24.5.2.1), MPa."""
    return 0.7 * 0.3 * fck ** (2.0 / 3.0) / 1.68


# ---------------------------------------------------------------------------
# γc = 1,68 isolado (24.5.2.1, p. 225)
# ---------------------------------------------------------------------------
def test_gama_c_simples_e_1_2_vezes_1_4():
    # 24.5.2.1: γc = 1,2 × 1,4 = 1,68
    assert cs.GAMA_C_SIMPLES == pytest.approx(1.68, rel=1e-12)


def _chamar_todas(fck=25.0):
    """Valores de todas as funções que dependem de γc."""
    return (
        cs.fctd_simples(fck), cs.fcd_simples(fck), cs.fcd_simples(fck, t_dias=7),
        cs.sigma_cRd(fck), cs.sigma_ctRd(fck), cs.tau_wRd(fck),
        cs.tau_wRd(fck, 3.0), cs.tau_Rd_laje_torcao_puncao(fck, "laje"),
        cs.tau_Rd_laje_torcao_puncao(fck, "torcao"),
        cs.tau_Rd_laje_torcao_puncao(fck, "puncao"),
        cs.sigma_ctRd_flexao_simplificada(fck),
        cs.tensoes_flexao_simplificada(fck).sigma_cRd_mpa,
        cs.tensoes_flexao_simplificada(fck).sigma_ctRd_mpa,
        cs.sigma_c_simples(1.0, fck), cs.sigma_c_simples(-0.1, fck),
        cs.verificar_cisalhamento(50.0, 20.0, 60.0, fck).tau_Rd_mpa,
        cs.verificar_torcao_cortante(0.1, 0.1, fck).tau_TRd_mpa,
    )


def test_nenhuma_funcao_herda_gama_c_do_nucleo(monkeypatch):
    # Aceite do P40: falha se alguma função chamar nucleo.fctd/fcd (com o
    # γc = 1,4 padrão) ou ler nucleo.GAMA_C.
    antes = _chamar_todas()

    def _proibido(*a, **k):
        raise AssertionError("concreto simples não pode usar fctd/fcd do núcleo")

    monkeypatch.setattr(nbr, "fctd", _proibido)
    monkeypatch.setattr(nbr, "fcd", _proibido)
    monkeypatch.setattr(nbr, "fctk_inf", _proibido)
    monkeypatch.setattr(nbr, "GAMA_C", 99.0)
    depois = _chamar_todas()
    assert depois == pytest.approx(antes, rel=1e-15)


def test_fctd_simples_usa_1_68_e_nao_1_4():
    # fck = 25: fct,m = 0,3·25^(2/3) = 2,564964; fctk,inf = 1,795475;
    # fctd = 1,795475/1,68 = 1,068735 MPa (com 1,4 daria 1,282482)
    assert cs.fctd_simples(25) == pytest.approx(1.795475 / 1.68, rel=1e-6)
    assert cs.fctd_simples(25) == pytest.approx(nbr.fctk_inf(25) / 1.68, rel=REL)
    assert cs.fctd_simples(25) != pytest.approx(nbr.fctd(25), rel=1e-3)


@pytest.mark.parametrize("fck", [15.0, 25.0, 40.0])
def test_fctd_simples_bordas_e_interior(fck):
    # 24.5.2.1 nas bordas C15 e C40 e no C25; C15: 0,7·0,3·6,082202/1,68 = 0,760275
    assert cs.fctd_simples(fck) == pytest.approx(_fctd_mao(fck), rel=REL)


def test_fctd_simples_c15_valor():
    assert cs.fctd_simples(15) == pytest.approx(0.760275, rel=1e-5)


@pytest.mark.parametrize("fck", [15.0, 30.0, 40.0])
def test_fcd_simples(fck):
    # 24.5.2.1 e 12.3.3: fcd = fck/1,68 (t >= 28 dias)
    assert cs.fcd_simples(fck) == pytest.approx(fck / 1.68, rel=REL)


def test_fcd_simples_idade_menor_que_28_dias():
    # 12.3.3: β1 = exp{0,25·[1 − (28/7)^(1/2)]} = exp(−0,25) = 0,778801 (CP II)
    # fcd = 0,778801·20/1,68 = 9,271440 MPa
    import math
    assert cs.fcd_simples(20, t_dias=7) == pytest.approx(math.exp(-0.25) * 20 / 1.68, rel=REL)


# ---------------------------------------------------------------------------
# 24.3 — C15 a C40 (p. 224)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fck", [15.0, 20.0, 40.0])
def test_validar_fck_simples_aceita(fck):
    assert cs.validar_fck_simples(fck) == fck


@pytest.mark.parametrize("fck", [10.0, 14.999, 40.001, 45.0])
def test_validar_fck_simples_rejeita(fck):
    with pytest.raises(nbr.FaixaNormativaError):
        cs.validar_fck_simples(fck)


@pytest.mark.parametrize("func", [cs.fctd_simples, cs.fcd_simples, cs.sigma_cRd,
                                  cs.sigma_ctRd, cs.tau_wRd,
                                  cs.tau_Rd_laje_torcao_puncao,
                                  cs.sigma_ctRd_flexao_simplificada])
def test_funcoes_rejeitam_fck_fora_de_c15_c40(func):
    with pytest.raises(nbr.FaixaNormativaError):
        func(45.0)
    with pytest.raises(nbr.FaixaNormativaError):
        func(10.0)


def test_c15_aceito_embora_o_nucleo_rejeite():
    # 8.2.1 (armado) começa em C20; 24.3 (simples) em C15
    with pytest.raises(nbr.FaixaNormativaError):
        nbr.fctd(15)
    assert cs.fctd_simples(15) > 0


# ---------------------------------------------------------------------------
# 24.2 e 24.5.2.5 — Campo de aplicação (p. 224 e 226)
# ---------------------------------------------------------------------------
def test_aplicavel_pilar_parede_apoiado_no_solo():
    r = cs.concreto_simples_aplicavel(apoio_vertical_continuo=True)
    assert r.ok and r.impedimentos == ()
    assert "aplicável" in r.governante


@pytest.mark.parametrize("kw", ["confinamento_lateral", "compressao_toda_secao",
                                "apoio_vertical_continuo"])
def test_aplicavel_cada_condicao_basica(kw):
    assert cs.concreto_simples_aplicavel(**{kw: True}).ok


def test_viga_fletida_sem_condicao_basica_nao_aplicavel():
    r = cs.concreto_simples_aplicavel()
    assert not r.ok
    assert "nenhuma condição básica" in r.governante


def test_outra_condicao_basica_declarada():
    r = cs.concreto_simples_aplicavel(outra_condicao="laje de piso apoiada no solo")
    assert r.ok
    assert any("laje de piso" in c for c in r.condicoes_basicas)


@pytest.mark.parametrize("kw", ["sujeita_a_sismo", "sujeita_a_explosao",
                                "dutilidade_importante", "peca_curva",
                                "torcao_de_equilibrio"])
def test_impedimentos_reprovam(kw):
    r = cs.concreto_simples_aplicavel(apoio_vertical_continuo=True, **{kw: True})
    assert not r.ok
    assert r.governante.startswith("Não permitido")


# ---------------------------------------------------------------------------
# 24.4 — Juntas (p. 224)
# ---------------------------------------------------------------------------
def test_juntas_constantes():
    assert cs.JUNTA_MAX_M == 15.0
    assert cs.DIST_ARMADURA_JUNTA_CM == 6.0


def test_juntas_15_m_ok_sem_exigencia():
    r = cs.verificar_juntas(15.0)
    assert r.ok and not r.exige_efeitos_termicos_retracao


def test_juntas_20_m_exige_efeitos():
    r = cs.verificar_juntas(20.0)
    assert r.exige_efeitos_termicos_retracao and not r.ok
    r2 = cs.verificar_juntas(20.0, efeitos_considerados=True)
    assert r2.exige_efeitos_termicos_retracao and r2.ok


def test_juntas_logo_acima_de_15_m():
    assert cs.verificar_juntas(15.01).exige_efeitos_termicos_retracao


def test_armadura_6_cm_ok_5_cm_reprova():
    assert cs.verificar_juntas(10.0, dist_armadura_junta_cm=6.0).ok
    r = cs.verificar_juntas(10.0, dist_armadura_junta_cm=5.0)
    assert not r.ok and not r.ok_armadura and r.ok_espacamento
    assert "6 cm" in r.governante


def test_juntas_espacamento_invalido():
    with pytest.raises(nbr.FaixaNormativaError):
        cs.verificar_juntas(0.0)


# ---------------------------------------------------------------------------
# 24.5.2.2 — Fibras extremas, 0,85 (p. 225)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fck", [15.0, 20.0, 40.0])
def test_sigma_cRd_085_fcd(fck):
    # fck = 20: σcRd = 0,85·20/1,68 = 10,119048 MPa
    assert cs.sigma_cRd(fck) == pytest.approx(0.85 * fck / 1.68, rel=REL)


def test_sigma_cRd_c20_valor():
    assert cs.sigma_cRd(20) == pytest.approx(10.119048, rel=1e-6)


@pytest.mark.parametrize("fck", [15.0, 25.0, 40.0])
def test_sigma_ctRd_085_fctd(fck):
    assert cs.sigma_ctRd(fck) == pytest.approx(0.85 * _fctd_mao(fck), rel=REL)


# ---------------------------------------------------------------------------
# 24.5.2.3 — τwRd (p. 225)
# ---------------------------------------------------------------------------
def test_tau_wRd_flexao_simples():
    # fck = 25: 0,30·1,068735 = 0,320620 MPa
    assert cs.tau_wRd(25) == pytest.approx(0.30 * _fctd_mao(25), rel=REL)


def test_tau_wRd_flexo_compressao_interior():
    # σcmd = 2 MPa, fck = 25: fator = 1 + 3·2/25 = 1,24
    assert cs.tau_wRd(25, 2.0) == pytest.approx(0.30 * _fctd_mao(25) * 1.24, rel=REL)


def test_tau_wRd_fator_no_teto_exato_e_acima():
    # (1 + 3·σcmd/fck) <= 2: σcmd = fck/3 dá exatamente 2; acima trunca em 2
    base = 0.30 * _fctd_mao(30)
    assert cs.tau_wRd(30, 10.0) == pytest.approx(2.0 * base, rel=REL)
    assert cs.tau_wRd(30, 15.0) == pytest.approx(2.0 * base, rel=REL)
    assert cs.tau_wRd(30, 9.9) == pytest.approx((1 + 3 * 9.9 / 30) * base, rel=REL)
    assert cs.fator_compressao_cisalhamento(30, 9.9) < 2.0


def test_tau_wRd_sigma_negativo_rejeitado():
    with pytest.raises(nbr.FaixaNormativaError):
        cs.tau_wRd(25, -1.0)


# ---------------------------------------------------------------------------
# 24.5.2.4 a 24.5.2.6 — τRd <= 1,0 MPa (p. 225-226)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("caso", ["laje", "torcao", "puncao", "Torção", "punção"])
def test_tau_Rd_tres_casos_mesma_expressao(caso):
    assert cs.tau_Rd_laje_torcao_puncao(25, caso) == pytest.approx(0.30 * _fctd_mao(25), rel=REL)


def test_tau_Rd_c40_nao_atinge_teto():
    # C40: 0,063·11,696071/1,68 = 0,438603 MPa < 1,0 MPa
    v = cs.tau_Rd_laje_torcao_puncao(40, "laje")
    assert v == pytest.approx(0.438603, rel=1e-5)
    assert v < 1.0


def test_tau_Rd_teto_de_1_mpa(monkeypatch):
    # O teto não governa em C15-C40; testa o limite forçando fctd alto.
    monkeypatch.setattr(cs, "fctd_simples", lambda fck: 5.0)   # 0,30·5 = 1,5 > 1,0
    for caso in ("laje", "torcao", "puncao"):
        assert cs.tau_Rd_laje_torcao_puncao(25, caso) == 1.0
    monkeypatch.setattr(cs, "fctd_simples", lambda fck: 1.0 / 0.30)   # exatamente 1,0
    assert cs.tau_Rd_laje_torcao_puncao(25) == pytest.approx(1.0, rel=REL)


def test_tau_Rd_caso_desconhecido():
    with pytest.raises(ValueError):
        cs.tau_Rd_laje_torcao_puncao(25, "viga")


# ---------------------------------------------------------------------------
# 24.5.3 — h − 5 cm contra o solo (p. 226)
# ---------------------------------------------------------------------------
def test_altura_contra_solo():
    assert cs.altura_contra_solo_cm(60.0) == 55.0
    assert cs.altura_contra_solo_cm(60.0, lancado_contra_solo=False) == 60.0


def test_altura_contra_solo_invalida():
    with pytest.raises(nbr.FaixaNormativaError):
        cs.altura_contra_solo_cm(5.0)
    assert cs.altura_contra_solo_cm(5.0, lancado_contra_solo=False) == 5.0


# ---------------------------------------------------------------------------
# 24.5.4.1 e 24.5.4.2 — Deformações (p. 226-227)
# ---------------------------------------------------------------------------
def test_limites_deformacao_constantes():
    assert cs.EPS_C_LIM_PMIL == 3.5          # 0,0035, igual ao εcu do armado até C50
    assert cs.EPS_C_LIM_PMIL == nbr.eps_cu(40)
    assert cs.EPS_CT_LIM_PMIL == 0.35        # 0,00035
    assert cs.EPS_C_MEDIA_PMIL == 2.0        # 0,002
    assert cs.EPS_CT_MEDIA_PMIL == 0.2       # 0,0002
    assert cs.EPS_C_MEDIA_PMIL < cs.EPS_C_LIM_PMIL
    assert cs.EPS_CT_MEDIA_PMIL < cs.EPS_CT_LIM_PMIL


def test_deformacoes_extremas_nos_limites_e_acima():
    assert cs.verificar_deformacoes_extremas(3.5, 0.35).ok
    r = cs.verificar_deformacoes_extremas(3.51, 0.35)
    assert not r.ok and not r.ok_compressao and r.ok_tracao
    r = cs.verificar_deformacoes_extremas(3.0, 0.36)
    assert not r.ok and r.ok_compressao and not r.ok_tracao


def test_deformacoes_medias_nos_limites_e_acima():
    assert cs.verificar_deformacoes_medias(2.0, 0.2).ok
    assert not cs.verificar_deformacoes_medias(2.01, 0.0).ok
    assert not cs.verificar_deformacoes_medias(0.0, 0.21).ok


def test_fibra_deformacao_media():
    assert cs.fibra_deformacao_media_cm(100.0) == pytest.approx(43.0)


def test_deformacao_negativa_rejeitada():
    with pytest.raises(nbr.FaixaNormativaError):
        cs.verificar_deformacoes_extremas(-1.0)


def test_diagrama_simples_pontos_da_figura_24_1():
    fck = 25.0
    pico_c = 0.85 * fck / 1.68
    pico_t = 0.85 * _fctd_mao(fck)
    assert cs.sigma_c_simples(0.0, fck) == 0.0
    # parábola: ε = 1 ‰ -> 0,75·pico
    assert cs.sigma_c_simples(1.0, fck) == pytest.approx(0.75 * pico_c, rel=REL)
    assert cs.sigma_c_simples(2.0, fck) == pytest.approx(pico_c, rel=REL)
    assert cs.sigma_c_simples(3.5, fck) == pytest.approx(pico_c, rel=REL)
    assert cs.sigma_c_simples(-0.1, fck) == pytest.approx(-0.75 * pico_t, rel=REL)
    assert cs.sigma_c_simples(-0.2, fck) == pytest.approx(-pico_t, rel=REL)
    assert cs.sigma_c_simples(-0.35, fck) == pytest.approx(-pico_t, rel=REL)
    with pytest.raises(nbr.FaixaNormativaError):
        cs.sigma_c_simples(3.6, fck)
    with pytest.raises(nbr.FaixaNormativaError):
        cs.sigma_c_simples(-0.36, fck)


# ---------------------------------------------------------------------------
# 24.5.4.3 — 0,8·fctd, diferente do 0,85 de 24.5.2.2 (p. 227)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fck", [15.0, 25.0, 40.0])
def test_sigma_ctRd_flexao_simplificada_0_8(fck):
    assert cs.sigma_ctRd_flexao_simplificada(fck) == pytest.approx(0.8 * _fctd_mao(fck), rel=REL)


def test_0_85_e_0_8_em_funcoes_diferentes():
    # 24.5.2.2 (0,85) x 24.5.4.3 (0,8): razão 0,85/0,8 = 1,0625
    assert cs.sigma_ctRd(25) / cs.sigma_ctRd_flexao_simplificada(25) == pytest.approx(1.0625, rel=REL)


def test_tensoes_flexao_simplificada():
    t = cs.tensoes_flexao_simplificada(25)
    assert t.sigma_ctRd_mpa == pytest.approx(0.8 * _fctd_mao(25), rel=REL)
    assert t.sigma_cRd_mpa == pytest.approx(0.85 * 25 / 1.68, rel=REL)
    assert any("0,8·fctd" in l for l in t.memoria)
    assert any("0,85·fcd" in l for l in t.memoria)


# ---------------------------------------------------------------------------
# 24.5.5 — Cisalhamento (p. 227)
# ---------------------------------------------------------------------------
def test_tau_wd_retangular():
    # VSd = 100 kN, b = 20 cm, h = 50 cm: 3·100/(2·20·50) = 0,15 kN/cm² = 1,5 MPa
    assert cs.tau_wd_retangular_mpa(100.0, 20.0, 50.0) == pytest.approx(1.5, rel=REL)


def test_tau_wd_1_5_vez_a_media():
    # 3/2 da tensão média V/(b·h)
    assert cs.tau_wd_retangular_mpa(80.0, 25.0, 40.0) == pytest.approx(
        1.5 * 80.0 / (25.0 * 40.0) * 10.0, rel=REL)


def test_tau_wd_contra_solo_usa_h_menos_5():
    # h = 55 contra o solo -> 50 cm: 3·100/(2·20·50)·10 = 1,5 MPa
    assert cs.tau_wd_retangular_mpa(100.0, 20.0, 55.0, lancado_contra_solo=True) == pytest.approx(1.5)


def test_secao_critica_peca_linear_a_h_e_laje_na_face():
    s = cs.secao_critica_cisalhamento(40.0)
    assert s.x_face_cm == 40.0 and s.reducao_no_apoio
    s = cs.secao_critica_cisalhamento(40.0, laje=True)
    assert s.x_face_cm == 0.0 and not s.reducao_no_apoio


def test_cortante_de_calculo():
    assert cs.cortante_de_calculo_kn(120.0, 100.0) == 100.0
    assert cs.cortante_de_calculo_kn(120.0, 100.0, laje=True) == 120.0


def test_verificar_cisalhamento_peca_linear_na_fronteira():
    # τwRd(25) = 0,30·fctd; V que dá τwd = τwRd: V = τ·2·b·h/(3·10)
    tau = 0.30 * _fctd_mao(25)
    V = tau * 2 * 20 * 60 / 30.0
    r = cs.verificar_cisalhamento(V, 20.0, 60.0, 25.0)
    assert r.ok and r.tau_wd_mpa == pytest.approx(tau, rel=REL)
    assert not cs.verificar_cisalhamento(V * 1.001, 20.0, 60.0, 25.0).ok


def test_verificar_cisalhamento_laje():
    r = cs.verificar_cisalhamento(10.0, 100.0, 20.0, 25.0, laje=True)
    assert r.tau_Rd_mpa == pytest.approx(0.30 * _fctd_mao(25), rel=REL)
    with pytest.raises(nbr.FaixaNormativaError):
        cs.verificar_cisalhamento(10.0, 100.0, 20.0, 25.0, sigma_cmd_mpa=1.0, laje=True)


# ---------------------------------------------------------------------------
# 24.5.6 — Torção e interação (p. 227)
# ---------------------------------------------------------------------------
def test_torcao_cortante_interacao_exatamente_1():
    fck = 25.0
    tR = 0.30 * _fctd_mao(fck)
    r = cs.verificar_torcao_cortante(0.5 * tR, 0.5 * tR, fck)
    assert r.interacao == pytest.approx(1.0, rel=REL)
    assert r.ok
    r = cs.verificar_torcao_cortante(0.5 * tR, 0.51 * tR, fck)
    assert r.ok_torcao and r.ok_cortante and not r.ok_interacao and not r.ok
    assert "interação" in r.governante


def test_torcao_nula_reduz_a_cortante_pura():
    fck = 30.0
    twRd = 0.30 * _fctd_mao(fck) * 1.5   # σcmd = 5: 1 + 3·5/30 = 1,5
    r = cs.verificar_torcao_cortante(0.0, twRd, fck, sigma_cmd_mpa=5.0)
    assert r.tau_wRd_mpa == pytest.approx(twRd, rel=REL)
    assert r.interacao == pytest.approx(1.0, rel=REL) and r.ok
    assert not cs.verificar_torcao_cortante(0.0, twRd * 1.01, fck, 5.0).ok


def test_torcao_isolada_acima_de_tTRd():
    fck = 25.0
    tR = 0.30 * _fctd_mao(fck)
    r = cs.verificar_torcao_cortante(1.01 * tR, 0.0, fck)
    assert not r.ok_torcao and not r.ok
    assert r.tau_TRd_mpa == pytest.approx(tR, rel=REL)
