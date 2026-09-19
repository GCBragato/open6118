"""Testes do P46 — Redistribuição com reequilíbrio e 2ª ordem global por
análise não linear.

Cobre, contra a ABNT NBR 6118:2026:

  - 14.5.3   Análise linear com redistribuição (p. 106): esforços recalculados
    para o equilíbrio de cada elemento e da estrutura; ELS sem redistribuição.
  - 14.6.4.2 Restrições para a redistribuição (p. 111): pilares, elementos
    comprimidos e consolos só em decorrência das vigas ligadas a eles.
  - 14.6.4.3 Limites (p. 112, via P13): δ ≥ 0,75 e x/d ≤ (δ − 0,44)/1,25 ou
    (δ − 0,56)/1,25.
  - 15.7.1   Nós móveis: não linearidade geométrica e física (p. 126), com as
    rigidezes de 15.7.3 (p. 126-127).
  - 15.5.3   γz no próprio modelo (p. 125) e 15.7.2 (0,95·γz, p. 126).

A norma não tabela resultados de análise: os valores esperados vêm de
soluções fechadas (viga contínua, pilar em balanço com P e H), com a conta no
comentário, e todo resultado confere o equilíbrio.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import analise_barras_nbr6118 as ab           # noqa: E402
import estabilidade_global_nbr6118 as eg      # noqa: E402
import nucleo_nbr6118 as nbr                  # noqa: E402

MAT = ab.Material.concreto(25.0)       # Ecs = 24 150 MPa (8.2.8)
SEC = ab.Secao.retangular(20.0, 50.0)  # I = 208 333,3 cm⁴
EI = MAT.E_kncm2 * SEC.I_cm4           # kN·cm²


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------
def _viga_continua(n_vaos=2, L=500.0, q=-20.0):
    """Viga contínua de n vãos iguais, apoios simples, carga q (kN/m)."""
    m = ab.Modelo("portico_plano")
    for i in range(n_vaos + 1):
        m.no(i, i * L, 0.0)
    for i in range(n_vaos):
        m.barra(f"v{i}", i, i + 1, SEC, MAT)
    m.apoio(0, "fixo")
    for i in range(1, n_vaos + 1):
        m.apoio(i, "uy")
    c = ab.CasoCarga("ELU")
    for i in range(n_vaos):
        c.distribuida(f"v{i}", q)
    return m, c


def _portico_simples(L=600.0, h=300.0, q=-30.0):
    """Pórtico de um vão: pilares engastados, viga com carga q (kN/m)."""
    m = ab.Modelo("portico_plano")
    m.no("A", 0.0, 0.0)
    m.no("B", 0.0, h)
    m.no("C", L, h)
    m.no("D", L, 0.0)
    m.barra("P1", "A", "B", ab.Secao.retangular(20.0, 40.0), MAT)
    m.barra("V1", "B", "C", SEC, MAT)
    m.barra("P2", "D", "C", ab.Secao.retangular(20.0, 40.0), MAT)
    m.apoio("A", "engaste")
    m.apoio("D", "engaste")
    c = ab.CasoCarga("ELU")
    c.distribuida("V1", q)
    return m, c


def _portico_andares(n_and=4, h=300.0, L=600.0, gv=-40.0, H=8.0, sentido=1.0):
    """Pórtico de n andares, um vão, com carga vertical nas vigas (kN/m) e
    força horizontal H (kN) em cada andar."""
    mat = ab.Material.concreto(30.0, estabilidade_global=True)   # 15.5.1
    P = ab.Secao.retangular(25.0, 40.0)
    V = ab.Secao.retangular(20.0, 50.0)
    m = ab.Modelo("portico_plano")
    for k in range(n_and + 1):
        m.no((0, k), 0.0, k * h)
        m.no((1, k), L, k * h)
    m.apoio((0, 0), "engaste")
    m.apoio((1, 0), "engaste")
    c = ab.CasoCarga("ELU")
    for k in range(n_and):
        m.barra(("p0", k), (0, k), (0, k + 1), P, mat)
        m.barra(("p1", k), (1, k), (1, k + 1), P, mat)
        m.barra(("v", k), (0, k + 1), (1, k + 1), V, mat)
        c.distribuida(("v", k), gv)
        c.nodal((0, k + 1), Fx=sentido * H)
    return m, c


def _balanco(n=10, L=300.0, H=10.0, fracao_pcr=0.2):
    """Pilar em balanço (engastado na base), H e P no topo, n barras."""
    Pcr = math.pi ** 2 * EI / (4.0 * L ** 2)   # Euler, balanço: le = 2L
    P = fracao_pcr * Pcr
    m = ab.Modelo("portico_plano")
    for i in range(n + 1):
        m.no(i, 0.0, i * L / n)
    for i in range(n):
        m.barra(i, i, i + 1, SEC, MAT)
    m.apoio(0, "engaste")
    c = ab.CasoCarga("ELU")
    c.nodal(n, Fx=H, Fy=-P)
    return m, c, P, Pcr


def _somar_reacoes(res, grau):
    return sum(d.get(grau, 0.0) for d in res.reacoes.values())


# ---------------------------------------------------------------------------
# 14.5.3 — Redistribuição com reequilíbrio (p. 106)
# ---------------------------------------------------------------------------
def test_viga_continua_redistribuida_momento_de_apoio_e_vao():
    """14.5.3 (p. 106). Dois vãos L = 500 cm, q = 20 kN/m = 0,2 kN/cm.
    Elástico: M_apoio = −q·L²/8 = −0,2·500²/8 = −6 250 kN·cm.
    δ = 0,8: M_apoio = −5 000 kN·cm nos dois lados do apoio.
    Vão (reequilíbrio): M(L/2) = q·L²/8 + M_apoio/2 = 6 250 − 2 500 = 3 750."""
    m, c = _viga_continua()
    r = ab.resolver(m, c)
    assert r.barras["v0"].extremidade_j["Mz"] == pytest.approx(-6250.0, rel=1e-9)
    rr = ab.redistribuir(m, r, [1], 0.8, caso=c)
    R = rr.resultado
    assert R.barras["v0"].extremidade_j["Mz"] == pytest.approx(-5000.0, rel=1e-9)
    assert R.barras["v1"].extremidade_i["Mz"] == pytest.approx(-5000.0, rel=1e-9)
    assert R.barras["v0"].em(250.0)["Mz"] == pytest.approx(3750.0, rel=1e-9)
    assert R.barras["v1"].em(250.0)["Mz"] == pytest.approx(3750.0, rel=1e-9)
    # estações coerentes com em()
    rb = R.barras["v0"]
    for x, mz in zip(rb.x_cm, rb.esforcos["Mz"]):
        assert rb.em(float(x))["Mz"] == pytest.approx(float(mz), rel=1e-9, abs=1e-6)
    assert rr.ok
    assert rr.momentos_redistribuidos_kncm[(1, "v0", "j")] == pytest.approx(-5000.0, rel=1e-9)


def test_viga_continua_redistribuida_continua_em_equilibrio():
    """14.5.3: reações depois da redistribuição. Extremo: q·L/2 − |M|/L =
    0,2·500/2 − 5 000/500 = 50 − 10 = 40 kN; central: 2·(50 + 10)
    = 120 kN; soma = 2·q·L = 200 kN. Em cada vão, a cortante varia q·L = 100."""
    m, c = _viga_continua()
    R = ab.redistribuir(m, ab.resolver(m, c), [1], 0.8).resultado
    assert R.reacoes[0]["uy"] == pytest.approx(40.0, rel=1e-9)
    assert R.reacoes[1]["uy"] == pytest.approx(120.0, rel=1e-9)
    assert R.reacoes[2]["uy"] == pytest.approx(40.0, rel=1e-9)
    assert _somar_reacoes(R, "uy") == pytest.approx(200.0, rel=1e-12)
    s = np.array(R.soma_cargas) + np.array(R.soma_reacoes)
    assert np.max(np.abs(s)) <= 1e-8 * 200.0 * 1000.0
    for bid in ("v0", "v1"):
        rb = R.barras[bid]
        # dVy/dx = −q (q = 0,2 kN/cm para baixo): Vj − Vi = −q·L = −100 kN
        assert rb.extremidade_j["Vy"] - rb.extremidade_i["Vy"] == pytest.approx(-100.0, rel=1e-9)
        Mi, Mj = rb.extremidade_i["Mz"], rb.extremidade_j["Mz"]
        # Mj = Mi + Vi·L − q·L²/2 (q para baixo, 0,2 kN/cm)
        assert Mj == pytest.approx(Mi + rb.extremidade_i["Vy"] * 500.0 - 0.2 * 500.0 ** 2 / 2.0,
                                   rel=1e-9, abs=1e-6)


def test_delta_unitario_reproduz_o_elastico():
    """14.6.4.3 (p. 112): δ = 1 é a análise linear sem redistribuição."""
    m, c = _viga_continua(3)
    r = ab.resolver(m, c)
    R = ab.redistribuir(m, r, [1, 2], 1.0).resultado
    for bid in r.barras:
        np.testing.assert_allclose(R.barras[bid].esforcos["Mz"], r.barras[bid].esforcos["Mz"],
                                   rtol=1e-9, atol=1e-6)
    assert R.reacoes[1]["uy"] == pytest.approx(r.reacoes[1]["uy"], rel=1e-9)


def test_tres_vaos_dois_apoios_com_deltas_diferentes():
    """14.5.3: três vãos, δ = 0,75 no apoio 1 e 0,9 no apoio 2; cada apoio
    chega ao seu δ·M e a estrutura continua em equilíbrio (ΣR = 3·q·L = 300)."""
    m, c = _viga_continua(3)
    r = ab.resolver(m, c)
    rr = ab.redistribuir(m, r, [1, 2], {1: 0.75, 2: 0.9})
    R = rr.resultado
    M1 = r.barras["v0"].extremidade_j["Mz"]
    M2 = r.barras["v1"].extremidade_j["Mz"]
    assert M1 == pytest.approx(-0.2 * 500.0 ** 2 / 10.0, rel=1e-9)   # 3 vãos: −q·L²/10
    assert R.barras["v0"].extremidade_j["Mz"] == pytest.approx(0.75 * M1, rel=1e-9)
    assert R.barras["v1"].extremidade_i["Mz"] == pytest.approx(0.75 * M1, rel=1e-9)
    assert R.barras["v1"].extremidade_j["Mz"] == pytest.approx(0.9 * M2, rel=1e-9)
    assert R.barras["v2"].extremidade_i["Mz"] == pytest.approx(0.9 * M2, rel=1e-9)
    assert _somar_reacoes(R, "uy") == pytest.approx(300.0, rel=1e-12)


@pytest.mark.parametrize("delta", [0.75, 1.0])
def test_delta_nas_bordas_da_faixa(delta):
    """14.6.4.3 (p. 112): δ ≥ 0,75 para qualquer caso; δ ≤ 1."""
    m, c = _viga_continua()
    rr = ab.redistribuir(m, ab.resolver(m, c), [1], delta)
    assert rr.resultado.barras["v0"].extremidade_j["Mz"] == pytest.approx(delta * -6250.0, rel=1e-9)


@pytest.mark.parametrize("delta", [0.7499, 1.0001])
def test_delta_fora_da_faixa_levanta_erro(delta):
    m, c = _viga_continua()
    with pytest.raises(nbr.FaixaNormativaError):
        ab.redistribuir(m, ab.resolver(m, c), [1], delta)


@pytest.mark.parametrize("fck, delta, lim", [
    (25.0, 0.8, (0.8 - 0.44) / 1.25),    # 0,288
    (50.0, 0.75, (0.75 - 0.44) / 1.25),  # 0,248 (borda fck = 50)
    (60.0, 0.8, (0.8 - 0.56) / 1.25),    # 0,192
    (90.0, 1.0, (1.0 - 0.56) / 1.25),    # 0,352
])
def test_limite_xd_com_redistribuicao_dos_dois_lados(fck, delta, lim):
    """14.6.4.3 (p. 112): x/d ≤ (δ − 0,44)/1,25 (fck ≤ 50) ou (δ − 0,56)/1,25."""
    m, c = _viga_continua()
    r = ab.resolver(m, c)
    no_limite = ab.redistribuir(m, r, [1], delta, fck_mpa=fck, xd=lim)
    assert no_limite.xd_limite[1] == pytest.approx(lim, rel=1e-12)
    assert no_limite.ok
    acima = ab.redistribuir(m, r, [1], delta, fck_mpa=fck, xd={1: lim + 1e-4})
    assert not acima.ok
    assert "14.6.4.3" in acima.governante


def test_xd_sem_fck_levanta_erro():
    m, c = _viga_continua()
    with pytest.raises(ValueError):
        ab.redistribuir(m, ab.resolver(m, c), [1], 0.8, xd=0.2)


def test_els_e_fadiga_dao_aviso():
    """14.5.3 (p. 106): ELS e fadiga podem usar a análise sem redistribuição;
    é desejável não redistribuir em serviço."""
    m, c = _viga_continua()
    r = ab.resolver(m, c)
    for est in ("ELS", "fadiga"):
        with pytest.warns(nbr.AvisoNBR6118):
            ab.redistribuir(m, r, [1], 0.9, estado_limite=est)


# ---------------------------------------------------------------------------
# 14.6.4.2 — Restrições (p. 111)
# ---------------------------------------------------------------------------
def test_portico_pilar_recebe_momento_so_em_decorrencia_da_viga():
    """14.6.4.2 (p. 111): no pórtico, a redistribuição da viga nos nós B e C
    muda o momento dos pilares na mesma medida (equilíbrio do nó, sem carga
    nodal: M_pilar,topo = M_viga,extremidade); os pilares não recebem rótula."""
    m, c = _portico_simples()
    r = ab.resolver(m, c)
    rr = ab.redistribuir(m, r, ["B", "C"], 0.85)
    R = rr.resultado
    for no, ext in (("B", "i"), ("C", "j")):
        Mel = getattr(r.barras["V1"], f"extremidade_{ext}")["Mz"]
        Mred = getattr(R.barras["V1"], f"extremidade_{ext}")["Mz"]
        assert Mred == pytest.approx(0.85 * Mel, rel=1e-9)
    # nó B: topo do P1 (extremidade j) e início da V1; ΣM = 0 → módulos iguais
    assert abs(R.barras["P1"].extremidade_j["Mz"]) == pytest.approx(
        abs(R.barras["V1"].extremidade_i["Mz"]), rel=1e-9)
    assert abs(R.barras["P2"].extremidade_j["Mz"]) == pytest.approx(
        abs(R.barras["V1"].extremidade_j["Mz"]), rel=1e-9)
    assert set(rr.pilares_alterados) == {"P1", "P2"}
    assert all(s[1] == "V1" for s in rr.secoes)
    assert any("14.6.4.2" in linha and "estabilidade global" in linha for linha in rr.memoria)
    # equilíbrio global: ΣRy = q·L = 0,3·600 = 180 kN; ΣRx = 0
    assert _somar_reacoes(R, "uy") == pytest.approx(180.0, rel=1e-12)
    assert _somar_reacoes(R, "ux") == pytest.approx(0.0, abs=1e-9)


def test_no_so_de_pilares_nao_admite_redistribuicao():
    """14.6.4.2: nó sem viga (só pilares) levanta erro."""
    m = ab.Modelo("portico_plano")
    m.no(0, 0.0, 0.0)
    m.no(1, 0.0, 300.0)
    m.no(2, 0.0, 600.0)
    m.barra("P1", 0, 1, SEC, MAT)
    m.barra("P2", 1, 2, SEC, MAT)
    m.apoio(0, "engaste")
    c = ab.CasoCarga("ELU").nodal(2, Fx=10.0, Fy=-100.0)
    r = ab.resolver(m, c)
    with pytest.raises(nbr.FaixaNormativaError, match="14.6.4.2"):
        ab.redistribuir(m, r, [1], 0.8)


def test_consolo_declarado_nao_recebe_rotula():
    """14.6.4.2: barra declarada como consolo (ou comprimida) é restrita."""
    m, c = _viga_continua()
    r = ab.resolver(m, c)
    with pytest.raises(nbr.FaixaNormativaError, match="14.6.4.2"):
        ab.redistribuir(m, r, [1], 0.8, consolos=["v0"], comprimidos=["v1"])
    # com só um lado restrito, a rótula vai na outra viga e o apoio chega a δ·M
    R = ab.redistribuir(m, r, [1], 0.8, consolos=["v0"]).resultado
    assert R.barras["v1"].extremidade_i["Mz"] == pytest.approx(-5000.0, rel=1e-9)


def test_trelica_nao_tem_momento_a_redistribuir():
    m = ab.Modelo("trelica_plana")
    m.no(0, 0.0, 0.0)
    m.no(1, 100.0, 0.0)
    m.barra(1, 0, 1, SEC, MAT)
    m.apoio(0, "fixo")
    m.apoio(1, "fixo")
    r = ab.resolver(m, ab.CasoCarga("c").nodal(1, Fx=1.0))
    with pytest.raises(ValueError):
        ab.redistribuir(m, r, [0], 0.9)


# ---------------------------------------------------------------------------
# 15.7.1 — 2ª ordem global (p. 126)
# ---------------------------------------------------------------------------
def test_balanco_momento_na_base_contra_solucao_fechada():
    """15.7.1 (p. 126). Balanço L = 300 cm, H = 10 kN e P = 0,2·Pcr no topo,
    Pcr = π²·EI/(4·L²). Solução fechada da barra: M_base = H·tan(kL)/k,
    k = √(P/EI); 10 barras com Kg consistente: tolerância relativa 1e-5."""
    m, c, P, Pcr = _balanco()
    with pytest.warns(nbr.AvisoNBR6118):
        pd = ab.analise_p_delta(m, c, rigidez="modelo")
    k = math.sqrt(P / EI)
    M_exato = 10.0 * math.tan(k * 300.0) / k
    assert -pd.resultado.barras[0].extremidade_i["Mz"] == pytest.approx(M_exato, rel=1e-5)
    assert pd.resultado.reacoes[0]["rz"] == pytest.approx(M_exato, rel=1e-5)


@pytest.mark.parametrize("fracao", [0.1, 0.2, 0.5])
def test_balanco_contra_fator_de_amplificacao(fracao):
    """Teste de aceite do P46: pilar em balanço contra 1/(1 − P/Pcr).
    Deslocamento do topo: δ = δ0/(1 − P/Pcr), δ0 = H·L³/(3·EI) (tolerância
    declarada 1 %: a série exata é 3·(tan u − u)/u³, u = kL, que difere de
    1/(1 − P/Pcr) em 0,3 % para P/Pcr = 0,5). Momento na base: H·L/(1 − P/Pcr)
    é uma cota superior; o exato H·tan(kL)/k fica abaixo, a até 9 % em
    P/Pcr = 0,5 (tolerância declarada: entre 0,90 e 1,00 do fator)."""
    m, c, P, Pcr = _balanco(fracao_pcr=fracao)
    with pytest.warns(nbr.AvisoNBR6118):
        pd = ab.analise_p_delta(m, c, rigidez="modelo")
    amp = 1.0 / (1.0 - P / Pcr)
    d0 = 10.0 * 300.0 ** 3 / (3.0 * EI)
    assert pd.resultado.deslocamentos[10]["ux"] == pytest.approx(d0 * amp, rel=1e-2)
    assert pd.fator_deslocamento == pytest.approx(amp, rel=1e-2)
    M = -pd.resultado.barras[0].extremidade_i["Mz"]
    assert 0.90 * 10.0 * 300.0 * amp <= M <= 10.0 * 300.0 * amp


def test_balanco_equilibrio_na_posicao_deformada():
    """15.7.1: M_base = H·L + P·δ_topo (equilíbrio na posição deformada);
    ΣFx e ΣFy fecham com as cargas."""
    m, c, P, Pcr = _balanco()
    with pytest.warns(nbr.AvisoNBR6118):
        pd = ab.analise_p_delta(m, c, rigidez="modelo", tol=1e-11)
    R = pd.resultado
    d = R.deslocamentos[10]["ux"]
    assert R.reacoes[0]["rz"] == pytest.approx(10.0 * 300.0 + P * d, rel=1e-8)
    assert R.reacoes[0]["ux"] == pytest.approx(-10.0, rel=1e-8)
    assert R.reacoes[0]["uy"] == pytest.approx(P, rel=1e-8)
    assert pd.iteracoes > 1
    assert any("critério" in linha for linha in pd.memoria)
    # parcela de 2ª ordem pela corda, linear na barra: em() igual às estações
    rb = R.barras[0]
    for x, mz, vy in zip(rb.x_cm, rb.esforcos["Mz"], rb.esforcos["Vy"]):
        e = rb.em(float(x))
        assert e["Mz"] == pytest.approx(float(mz), rel=1e-9, abs=1e-6)
        assert e["Vy"] == pytest.approx(float(vy), rel=1e-9, abs=1e-9)


def test_sem_carga_vertical_a_2a_ordem_e_a_1a():
    m, c0, P, Pcr = _balanco()
    c = ab.CasoCarga("H").nodal(10, Fx=10.0)
    with pytest.warns(nbr.AvisoNBR6118):
        pd = ab.analise_p_delta(m, c, rigidez="modelo")
    assert pd.fator_deslocamento == pytest.approx(1.0, rel=1e-12)
    assert pd.resultado.reacoes[0]["rz"] == pytest.approx(3000.0, rel=1e-9)


def test_carga_acima_da_critica_nao_converge():
    """P > Pcr: instabilidade, a iteração diverge."""
    m, c, P, Pcr = _balanco(fracao_pcr=1.2)
    with pytest.warns(nbr.AvisoNBR6118):
        with pytest.raises(ab.ErroConvergencia):
            ab.analise_p_delta(m, c, rigidez="modelo")


def test_nlf_aproximada_reduz_a_rigidez_dos_pilares():
    """15.7.3 (p. 126-127): pilares 0,8·Ec·Ic. No balanço, o deslocamento de
    1ª ordem com a NLF é δ0/0,8."""
    m, c, P, Pcr = _balanco(fracao_pcr=0.1)
    pd = ab.analise_p_delta(m, c)
    d0 = 10.0 * 300.0 ** 3 / (3.0 * EI)
    assert pd.resultado_1a_ordem.deslocamentos[10]["ux"] == pytest.approx(d0 / 0.8, rel=1e-9)
    assert pd.rigidez == "nlf_aproximada"
    assert any("15.7.3" in linha for linha in pd.memoria)


def test_nlf_com_menos_de_quatro_andares_levanta_erro():
    """15.7.3: a redução aproximada só vale com no mínimo quatro andares."""
    m, c = _portico_andares(3)
    with pytest.raises(nbr.FaixaNormativaError):
        ab.analise_p_delta(m, c, n_andares=3)
    ab.analise_p_delta(m, c, n_andares=4)   # 4 andares: vale


def test_p_delta_so_para_porticos():
    m = ab.Modelo("grelha")
    m.no(0, 0.0, 0.0)
    m.no(1, 100.0, 0.0)
    m.barra(1, 0, 1, SEC, MAT)
    m.apoio(0, "engaste")
    with pytest.raises(ValueError):
        ab.analise_p_delta(m, ab.CasoCarga("c").nodal(1, Fz=-1.0))


def test_modelo_com_rigidez_nlf_fatores():
    """15.7.3: lajes 0,3; vigas 0,4 (As' ≠ As) e 0,5 (As' = As); pilares 0,8.
    O fator multiplica o fator_EI já declarado."""
    m, _ = _portico_simples()
    m2, mem = ab.modelo_com_rigidez_nlf(m)
    assert m2.barras["P1"].fator_EI == pytest.approx(0.8)
    assert m2.barras["V1"].fator_EI == pytest.approx(0.4)
    assert m.barras["V1"].fator_EI == 1.0   # original intacto
    m3, _ = ab.modelo_com_rigidez_nlf(m, armadura_simetrica=True)
    assert m3.barras["V1"].fator_EI == pytest.approx(0.5)
    m4, _ = ab.modelo_com_rigidez_nlf(m, tipos={"V1": "laje", "P2": "viga_simetrica"})
    assert m4.barras["V1"].fator_EI == pytest.approx(0.3)
    assert m4.barras["P2"].fator_EI == pytest.approx(0.5)
    with pytest.raises(ValueError):
        ab.modelo_com_rigidez_nlf(m, tipos={"V1": "parede"})


def test_caso_combinado_igual_a_superposicao():
    """A combinação montada como um caso (Σ fator·caso) dá, na análise
    linear, a superposição dos resultados."""
    m, cg = _portico_simples()
    ch = ab.CasoCarga("H").nodal("B", Fx=5.0)
    comb = ab.caso_combinado([(cg, 1.4), (ch, 1.4 * 0.6)], "ELU")
    r = ab.resolver(m, comb)
    rg, rh = ab.resolver(m, cg), ab.resolver(m, ch)
    esperado = 1.4 * rg.reacoes["A"]["rz"] + 0.84 * rh.reacoes["A"]["rz"]
    assert r.reacoes["A"]["rz"] == pytest.approx(esperado, rel=1e-9)
    with pytest.raises(ValueError):
        ab.caso_combinado([])


# ---------------------------------------------------------------------------
# 15.5.3 — γz no próprio modelo (p. 125) e 15.7.2 (p. 126)
# ---------------------------------------------------------------------------
def _gama_z_a_mao(m, c, res):
    """M1 = Σ H·z; ΔM = Σ q·L·(ui + uj)/2 (carga uniforme na viga, deslocamento
    horizontal linear entre os nós) — kN·cm → kN·m."""
    M1 = sum(v[0] * m.nos[no].y_cm for no, v in c.nodais) / 100.0
    dM = 0.0
    for bid, _, dados in c.barra_cargas:
        b = m.barras[bid]
        q = -dados[3]                  # kN/cm, para baixo
        L = 600.0
        ui = res.deslocamentos[b.no_i]["ux"]
        uj = res.deslocamentos[b.no_j]["ux"]
        dM += q * L * (ui + uj) / 2.0
    return M1, dM / 100.0


def test_gama_z_do_modelo_igual_ao_gama_z_do_p26():
    """15.5.3 (p. 125): o γz do modelo é o gama_z do P26 com M1,tot,d e
    ΔMtot,d refeitos à mão a partir da análise de 1ª ordem com 15.7.3."""
    m, c = _portico_andares()
    g = eg.gama_z_do_modelo(m, c, n_andares=4)
    M1, dM = _gama_z_a_mao(m, c, g.resultado_1a_ordem)
    # M1 = 8·(3 + 6 + 9 + 12) = 240 kN·m
    assert M1 == pytest.approx(240.0, rel=1e-12)
    assert g.M1tot_d_knm == pytest.approx(M1, rel=1e-12)
    assert g.delta_Mtot_d_knm == pytest.approx(dM, rel=1e-9)
    assert g.gama_z == pytest.approx(eg.gama_z(M1, dM), rel=1e-12)
    # a análise usada é a de 15.7.3: pilares 0,8 e vigas 0,4
    m2, _ = ab.modelo_com_rigidez_nlf(m, n_andares=4)
    r2 = ab.resolver(m2, c)
    assert g.resultado_1a_ordem.deslocamentos[(0, 4)]["ux"] == pytest.approx(
        r2.deslocamentos[(0, 4)]["ux"], rel=1e-12)


def test_gama_z_do_modelo_independe_do_sentido():
    """Pórtico simétrico: o γz com H em −X é o mesmo que em +X."""
    m, c = _portico_andares()
    m_, c_ = _portico_andares(sentido=-1.0)
    g1 = eg.gama_z_do_modelo(m, c, n_andares=4)
    g2 = eg.gama_z_do_modelo(m_, c_, n_andares=4)
    assert g2.gama_z == pytest.approx(g1.gama_z, rel=1e-9)
    assert g2.M1tot_d_knm == pytest.approx(240.0, rel=1e-12)


def test_gama_z_do_modelo_carga_concentrada_na_viga_e_cota_base():
    """Carga concentrada na viga entra no ponto de aplicação; cota_base_cm
    desloca a referência de M1 (Σ H·(z − z_base))."""
    m, c = _portico_andares(gv=-10.0)
    c.concentrada(("v", 3), 300.0, -50.0, direcao="Y")
    g = eg.gama_z_do_modelo(m, c, n_andares=4)
    res = g.resultado_1a_ordem
    ui = res.deslocamentos[(0, 4)]["ux"]
    uj = res.deslocamentos[(1, 4)]["ux"]
    dM_esp = sum(0.1 * 600.0 * (res.deslocamentos[(0, k)]["ux"] + res.deslocamentos[(1, k)]["ux"]) / 2.0
                 for k in range(1, 5)) + 50.0 * (ui + uj) / 2.0
    assert g.delta_Mtot_d_knm == pytest.approx(dM_esp / 100.0, rel=1e-9)
    g2 = eg.gama_z_do_modelo(m, c, n_andares=4, cota_base_cm=-100.0)
    # M1 com base 1 m abaixo: 240 + 8·4·1 = 272 kN·m
    assert g2.M1tot_d_knm == pytest.approx(272.0, rel=1e-12)


def test_gama_z_do_modelo_erros():
    m, c = _portico_andares()
    with pytest.raises(nbr.FaixaNormativaError):
        eg.gama_z_do_modelo(m, c, n_andares=3)
    with pytest.raises(ValueError):
        eg.gama_z_do_modelo(m, c, direcao="Y")
    so_vertical = ab.CasoCarga("G")
    so_vertical.distribuida(("v", 0), -10.0)
    with pytest.raises(ValueError):
        eg.gama_z_do_modelo(m, so_vertical)


def test_classificar_nos_aceita_o_modelo():
    """15.4.2 com o γz do modelo: mesmo veredito que com o número pronto."""
    m, c = _portico_andares(gv=-120.0)
    g = eg.gama_z_do_modelo(m, c, n_andares=4)
    r_mod = eg.classificar_nos(modelo=m, combinacao=c, opcoes_modelo={"n_andares": 4})
    r_num = eg.classificar_nos(gama_z=g.gama_z)
    assert r_mod.gama_z == pytest.approx(g.gama_z, rel=1e-12)
    assert r_mod.nos_fixos == r_num.nos_fixos
    assert any("15.5.3" in linha for linha in r_mod.memoria)
    with pytest.raises(ValueError):
        eg.classificar_nos(modelo=m)
    with pytest.raises(ValueError):
        eg.classificar_nos(modelo=m, combinacao=c, gama_z=1.05)


@pytest.mark.parametrize("gv", [-40.0, -80.0, -120.0])
def test_p_delta_e_095_gama_z_proximos(gv):
    """Aceite do P46: com γz ≤ 1,3, a análise P-Δ (15.7.1) e a majoração das
    ações horizontais por 0,95·γz (15.7.2, p. 126) dão momentos na base
    próximos. Tolerância declarada: 5 % na soma dos momentos na base dos
    pilares; e o fator de amplificação dos deslocamentos da P-Δ fica a 2 %
    do γz (γz ≈ 1/(1 − ΔM/M1) é a mesma série geométrica)."""
    m, c = _portico_andares(gv=gv)
    g = eg.gama_z_do_modelo(m, c, n_andares=4)
    assert g.gama_z <= 1.3 and g.processo_095_valido
    pd = ab.analise_p_delta(m, c, n_andares=4)
    assert pd.fator_deslocamento == pytest.approx(g.gama_z, rel=2e-2)
    f = eg.majoracao_horizontal(g.gama_z)
    c095 = ab.CasoCarga("0,95·γz")
    for k in range(4):
        c095.distribuida(("v", k), gv)
        c095.nodal((0, k + 1), Fx=8.0 * f)
    m2, _ = ab.modelo_com_rigidez_nlf(m, n_andares=4)
    r095 = ab.resolver(m2, c095)
    base = [("p0", 0), ("p1", 0)]
    M_pd = sum(pd.resultado.barras[b].extremidade_i["Mz"] for b in base)
    M_095 = sum(r095.barras[b].extremidade_i["Mz"] for b in base)
    assert M_095 == pytest.approx(M_pd, rel=5e-2)


@pytest.mark.parametrize("dir_h", ["X", "Y"])
def test_balanco_portico_espacial_nas_duas_direcoes(dir_h):
    """15.7.1 no pórtico espacial (os dois planos de flexão): balanço
    vertical (eixo Z) de seção quadrada 30 × 30, H = 10 kN na direção X ou
    Y e P = 0,3·Pcr para baixo; M_base = H·tan(kL)/k (rel 1e-5)."""
    sec = ab.Secao.retangular(30.0, 30.0)
    EIq = MAT.E_kncm2 * sec.I_cm4
    L, n = 300.0, 10
    Pcr = math.pi ** 2 * EIq / (4.0 * L ** 2)
    P = 0.3 * Pcr
    m = ab.Modelo("portico_espacial")
    for i in range(n + 1):
        m.no(i, 0.0, 0.0, i * L / n)
    for i in range(n):
        m.barra(i, i, i + 1, sec, MAT)
    m.apoio(0, "engaste")
    c = ab.CasoCarga("ELU")
    c.nodal(n, **{"F" + dir_h.lower(): 10.0}, Fz=-P)
    with pytest.warns(nbr.AvisoNBR6118):
        pd = ab.analise_p_delta(m, c, rigidez="modelo")
    k = math.sqrt(P / EIq)
    M_exato = 10.0 * math.tan(k * L) / k
    reac = pd.resultado.reacoes[0]
    M_base = abs(reac["ry"] if dir_h == "X" else reac["rx"])
    assert M_base == pytest.approx(M_exato, rel=1e-5)
    assert pd.fator_deslocamento == pytest.approx(1.0 / (1.0 - 0.3), rel=1e-2)
