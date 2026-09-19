"""Testes do P43 -- Método geral de perdas e fluência com tensão variável
(NBR 6118:2026, 9.6.3.4.4 e A.2.5).

Fontes (imagens das páginas do PDF, SCRATCH/nbr_png):
    - p073: 9.6.3.4.4, método geral (fluência de cada camada e relaxação de
      cada cabo, separadamente; relaxação isolada de cada cabo);
    - p072: 9.6.3.4.2, processo simplificado (a referência de uma fase só);
    - p074: 9.6.3.4.5, ψ(t,t0) = ψ1000·[(t − t0)/41,67]^0,15 e ψ(t∞) ≅ 2,5·ψ1000;
    - p240: A.2.5, forma integral e forma simplificada de εc(t).
As contas à mão estão nos comentários.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import protendido_nbr6118 as PT  # noqa: E402
import tempo_concreto_nbr6118 as tc  # noqa: E402

FE = nbr.FaixaNormativaError
EP = 200000.0
ECI_30 = 5600.0 * math.sqrt(30.0)   # 8.2.8, granito (αE = 1,0): 30 672,46 MPa


def _phi_anexo_a(t, tau):
    """φ(t,τ) do Anexo A (A.2.2.3), fck 30 MPa, hfic 20 cm, U = 70 %, CP II."""
    return tc.phi(t, tau, 30.0, 20.0, U_pct=70.0)


def _phi_const(valor):
    """φ(t,τ) = valor para t > τ (independente de τ)."""
    return lambda t, tau: valor if t > tau else 0.0


# ===========================================================================
# A.2.5 -- forma integral de εc(t) (PDF p. 240)
# ===========================================================================
def test_a25_tensao_constante_reproduz_forma_simplificada():
    # σc constante: a integral é nula e εc(t) = σc(t0)·[1/Ec(t0) + φ/Eci] + εcs,
    # que é a forma simplificada com Δσc = 0.
    s0, E0, phi, ecs = -10.0, 25000.0, _phi_anexo_a(1000.0, 28.0), -0.35
    r = tc.eps_c_integral([(28.0, s0), (400.0, s0)], 1000.0, _phi_anexo_a, E0, ECI_30,
                          eps_cs_pmil=ecs)
    esperado = tc.eps_c_total_simplificada_pmil(s0, 0.0, phi, ecs, E0, ECI_30)
    assert r.eps_integral_pmil == 0.0
    assert r.eps_c_pmil == pytest.approx(esperado, rel=1e-12)
    # conta: -10/25000·1000 = -0,4 ‰; -10/30672,46·φ·1000; -0,35 ‰
    assert r.eps_imediata_pmil == pytest.approx(-0.4, rel=1e-12)
    assert r.eps_fluencia_pmil == pytest.approx(-10.0 / ECI_30 * phi * 1000.0, rel=1e-12)


def test_a25_rampa_com_phi_independente_de_tau_reproduz_simplificada():
    # φ(t,τ) = 2,0 para qualquer τ: ∫ ∂σ/∂τ·[1/Ec + α·2/Eci] dτ = Δσ·[1/Ec + α·2/Eci],
    # exatamente o último termo da forma simplificada, com o mesmo α.
    for alfa in (0.5, 0.8, 1.0):
        r = tc.eps_c_integral([(28.0, -8.0), (1000.0, -5.0)], 1000.0, _phi_const(2.0),
                              30000.0, ECI_30, eps_cs_pmil=-0.3, alfa=alfa)
        esperado = tc.eps_c_total_simplificada_pmil(-8.0, 3.0, 2.0, -0.3, 30000.0, ECI_30,
                                                    alfa=alfa)
        assert r.eps_c_pmil == pytest.approx(esperado, rel=1e-12)
        assert r.delta_sigma_c_mpa == pytest.approx(3.0)


def test_a25_salto_em_t0_com_superposicao_e_forma_simplificada_alfa_1():
    # Acréscimo Δσ todo aplicado em t0 (salto): a superposição dá
    # Δσ·[1/Ec(t0) + φ(t,t0)/Eci], a forma simplificada com α = 1.
    phi = _phi_anexo_a(1000.0, 28.0)
    r = tc.eps_c_integral([(28.0, -10.0), (28.0, -6.0)], 1000.0, _phi_anexo_a, 28000.0,
                          ECI_30, integrando="superposicao")
    esperado = tc.eps_c_total_simplificada_pmil(-10.0, 4.0, phi, 0.0, 28000.0, ECI_30,
                                                alfa=1.0)
    assert r.eps_c_pmil == pytest.approx(esperado, rel=1e-12)


def test_a25_rampa_real_da_alfa_efetivo_entre_0_e_1_e_converge():
    # Com φ do Anexo A e Δσ linear de 28 a 1000 dias, o α que a forma
    # simplificada precisaria para dar a mesma integral fica em (0; 1): o
    # acréscimo tardio flui menos que o aplicado em t0. Gauss converge.
    phi = _phi_anexo_a(1000.0, 28.0)
    r8 = tc.eps_c_integral([(28.0, -10.0), (1000.0, -5.0)], 1000.0, _phi_anexo_a,
                           ECI_30, ECI_30, integrando="superposicao", n_pontos=8)
    r32 = tc.eps_c_integral([(28.0, -10.0), (1000.0, -5.0)], 1000.0, _phi_anexo_a,
                            ECI_30, ECI_30, integrando="superposicao", n_pontos=32)
    assert r8.eps_c_pmil == pytest.approx(r32.eps_c_pmil, rel=1e-4)
    alfa_ef = (r32.eps_integral_pmil / 1000.0 - 5.0 / ECI_30) / (5.0 * phi / ECI_30)
    assert 0.0 < alfa_ef < 1.0


def test_a25_integrando_impresso_phi_tau_t0():
    # Literal da página: α·φ(τ,t0). Com φ(t,t0) = k·(t − t0), rampa de t0 a t:
    # ∫ (Δσ/(t−t0))·[1/Ec + α·k·(τ − t0)/Eci] dτ = Δσ·[1/Ec + α·k·(t − t0)/(2·Eci)].
    k, t0, t, ds, Ec, alfa = 0.002, 30.0, 530.0, 4.0, 30000.0, 0.8
    f = lambda a, b: k * (a - b)  # noqa: E731
    r = tc.eps_c_integral([(t0, -10.0), (t, -10.0 + ds)], t, f, Ec, ECI_30, alfa=alfa,
                          integrando="impresso")
    integral = ds * (1.0 / Ec + alfa * k * (t - t0) / (2.0 * ECI_30)) * 1000.0
    assert r.eps_integral_pmil == pytest.approx(integral, rel=1e-12)
    # A superposição usa φ(t,τ) = k·(t − τ): com a rampa ocupando todo o
    # intervalo as duas integrais coincidem (simetria); com a rampa curta, não.
    r_sup = tc.eps_c_integral([(t0, -10.0), (t, -10.0 + ds)], t, f, Ec, ECI_30, alfa=alfa,
                              integrando="superposicao")
    assert r_sup.eps_integral_pmil == pytest.approx(integral, rel=1e-12)  # simétrico aqui
    r2 = tc.eps_c_integral([(t0, -10.0), (t0 + 100.0, -10.0 + ds)], t, f, Ec, ECI_30,
                           alfa=alfa, integrando="impresso")
    r2s = tc.eps_c_integral([(t0, -10.0), (t0 + 100.0, -10.0 + ds)], t, f, Ec, ECI_30,
                            alfa=alfa, integrando="superposicao")
    # impresso: Δσ·[1/Ec + α·k·50/Eci]; superposição: Δσ·[1/Ec + α·k·(500 − 50)/Eci]
    assert r2.eps_integral_pmil == pytest.approx(ds * (1 / Ec + alfa * k * 50 / ECI_30) * 1e3)
    assert r2s.eps_integral_pmil == pytest.approx(ds * (1 / Ec + alfa * k * 450 / ECI_30) * 1e3)


def test_a25_padrao_e_o_integrando_impresso_na_pagina_240():
    # A.2.5 (PDF p. 240): o integrando impresso é 1/Ec(τ) + α·φ(τ,t0)/Eci. Sem
    # passar ``integrando``, a função tem de reproduzir essa letra. Mesmo caso
    # do teste anterior (φ(a,b) = k·(a − b), rampa curta de 30 a 130 dias,
    # t = 530): impresso dá Δσ·[1/Ec + α·k·50/Eci]; a superposição daria
    # Δσ·[1/Ec + α·k·450/Eci], nove vezes a parcela de fluência.
    k, t0, t, ds, Ec, alfa = 0.002, 30.0, 530.0, 4.0, 30000.0, 0.8
    f = lambda a, b: k * (a - b)  # noqa: E731
    hist = [(t0, -10.0), (t0 + 100.0, -10.0 + ds)]
    r = tc.eps_c_integral(hist, t, f, Ec, ECI_30, alfa=alfa)
    # conta: 4·(1/30000 + 0,8·0,002·50/30672,46)·1000 = 0,133333 + 0,010433 = 0,143767 ‰
    assert r.eps_integral_pmil == pytest.approx(ds * (1 / Ec + alfa * k * 50 / ECI_30) * 1e3,
                                                rel=1e-12)
    assert r.eps_c_pmil == pytest.approx(
        tc.eps_c_integral(hist, t, f, Ec, ECI_30, alfa=alfa, integrando="impresso").eps_c_pmil,
        rel=1e-12)
    assert tc.eps_c_integral_pmil(hist, t, f, Ec, ECI_30, alfa=alfa) == pytest.approx(
        r.eps_c_pmil, rel=1e-12)
    assert "como impresso na página 240" in " ".join(r.memoria)
    # A superposição só por escolha explícita, e a memória registra a divergência.
    rs = tc.eps_c_integral(hist, t, f, Ec, ECI_30, alfa=alfa, integrando="superposicao")
    assert rs.eps_integral_pmil != pytest.approx(r.eps_integral_pmil, rel=1e-3)
    assert "diverge da letra da página 240" in " ".join(rs.memoria)


def test_a25_modulo_variavel_com_a_idade():
    # Ec(τ) como função: salto em τ = 10 usa Ec(10); σc(t0)/Ec(t0) usa Ec(t0).
    Ec = lambda tau: 20000.0 + 100.0 * tau  # noqa: E731
    r = tc.eps_c_integral([(7.0, -5.0), (10.0, -5.0), (10.0, -7.0)], 100.0, _phi_const(0.0),
                          Ec, ECI_30)
    assert r.eps_imediata_pmil == pytest.approx(-5.0 / 20700.0 * 1000.0)
    assert r.eps_integral_pmil == pytest.approx(-2.0 / 21000.0 * 1000.0)


def test_a25_historico_cortado_em_t():
    # O trecho de 28 a 128 dias é cortado em t = 78 (metade): Δσ = 2 MPa.
    r = tc.eps_c_integral([(28.0, -10.0), (128.0, -6.0), (200.0, 0.0)], 78.0,
                          _phi_const(0.0), 30000.0, ECI_30)
    assert r.delta_sigma_c_mpa == pytest.approx(2.0)
    assert r.eps_integral_pmil == pytest.approx(2.0 / 30000.0 * 1000.0)
    assert tc.eps_c_integral_pmil([(28.0, -10.0), (128.0, -6.0)], 78.0, _phi_const(0.0),
                                  30000.0, ECI_30) == pytest.approx(r.eps_c_pmil)


def test_a25_t_infinito():
    r = tc.eps_c_integral([(28.0, -10.0), (365.0, -8.0)], math.inf, _phi_anexo_a,
                          ECI_30, ECI_30)
    assert math.isfinite(r.eps_c_pmil)
    assert r.eps_c_pmil < tc.eps_c_integral([(28.0, -10.0), (365.0, -8.0)], 3650.0,
                                            _phi_anexo_a, ECI_30, ECI_30).eps_c_pmil


def test_a25_memoria():
    r = tc.eps_c_integral([(28.0, -10.0), (100.0, -8.0)], 1000.0, _phi_anexo_a, ECI_30,
                          ECI_30)
    texto = " ".join(r.memoria)
    # padrão = integrando impresso na p. 240, α·φ(τ,t0)
    assert "A.2.5" in texto and "α·φ(τ,t0)/Eci" in texto
    rs = tc.eps_c_integral([(28.0, -10.0), (100.0, -8.0)], 1000.0, _phi_anexo_a, ECI_30,
                           ECI_30, integrando="superposicao")
    assert "α·φ(t,τ)/Eci" in " ".join(rs.memoria)


@pytest.mark.parametrize("kwargs", [
    dict(historico_sigma=[]),
    dict(historico_sigma=[(28.0, -10.0), (20.0, -8.0)]),
    dict(historico_sigma=[(28.0, -10.0), (math.inf, -8.0)]),
    dict(t_dias=10.0),
    dict(alfa=0.0),
    dict(alfa=1.01),
    dict(Eci_mpa=0.0),
    dict(Ec_mpa=-1.0),
    dict(n_pontos=0),
])
def test_a25_fora_da_faixa(kwargs):
    base = dict(historico_sigma=[(28.0, -10.0), (100.0, -8.0)], t_dias=1000.0,
                phi_func=_phi_anexo_a, Ec_mpa=ECI_30, Eci_mpa=ECI_30)
    base.update(kwargs)
    with pytest.raises(FE):
        tc.eps_c_integral(**base)


def test_a25_integrando_desconhecido():
    with pytest.raises(ValueError):
        tc.eps_c_integral([(28.0, -10.0)], 100.0, _phi_anexo_a, ECI_30, ECI_30,
                          integrando="outro")


# ===========================================================================
# 9.6.3.4.4 -- método geral (PDF p. 73)
# ===========================================================================
A, I, EPC, AP, SP0 = 3000.0, 900000.0, 25.0, 12.0, 1300.0


def _uma_fase(phi, ecs_pmil, psi_pct=None, psi1000=0.0, Mg=15000.0, t_final=1000.0,
              alfa=0.5):
    cam = PT.CamadaConcreto(A, I, 0.0, _phi_const(phi), ECI_30,
                            eps_cs_func=lambda t, t0: ecs_pmil if t > t0 else 0.0)
    cab = PT.CaboProtensao(AP, EPC, 0.0, SP0, psi_1000_pct=psi1000,
                           psi_func=None if psi_pct is None else (lambda dt: psi_pct))
    return PT.perdas_metodo_geral([PT.FaseCarga(0.0, M_kncm=Mg)], [cam], [cab], t_final,
                                  alfa=alfa)


def _sigma_c_p0g(Mg):
    # σc,p0g (positiva se compressão) no cabo resultante, em MPa:
    # P = 12·1300/10 = 1560 kN; (P/A + P·ep²/I − Mg·ep/I)·10.
    P = AP * SP0 / 10.0
    return (P / A + P * EPC ** 2 / I - Mg * EPC / I) * 10.0


@pytest.mark.parametrize("phi, ecs, psi, Mg", [
    (2.5, -0.5, 6.0, 15000.0),
    (1.5, -0.3, 3.0, 0.0),
    (3.0, 0.0, 0.0, 30000.0),
    (0.0, -0.4, 0.0, 15000.0),
])
def test_9634_4_uma_fase_reproduz_processo_simplificado(phi, ecs, psi, Mg):
    # Uma fase, um passo, α = 0,5 e Ec(t0) = Eci: as equações do método geral
    # são as de 9.6.3.4.2 (p. 72) -> Δσp igual ao da fórmula fechada.
    r = _uma_fase(phi, ecs, psi_pct=psi, Mg=Mg)
    ref = PT.perda_progressiva_simplificada(ecs, psi, phi, _sigma_c_p0g(Mg), SP0, AP, A, I,
                                            EPC, 30.0)
    assert r.perda_progressiva_mpa[0] == pytest.approx(ref, rel=1e-9)
    assert r.perda_total_mpa[0] == pytest.approx(ref, rel=1e-9)
    assert r.variacao_imediata_mpa[0] == 0.0
    # tensão no concreto junto ao cabo em t0 = −σc,p0g (compressão negativa)
    assert r.sigma_c_mpa(0, EPC, 0) == pytest.approx(-_sigma_c_p0g(Mg), rel=1e-12)


def test_9634_4_uma_fase_psi_da_norma_em_t_finito_e_infinito():
    # ψ(t,t0) = ψ1000·(t/41,67)^0,15 (9.6.3.4.5, p. 74) em t = 1000 dias e
    # ψ(t∞) = 2,5·ψ1000 em t = ∞.
    psi1000 = 3.5
    for t_final, psi in ((1000.0, PT.psi_t_em_dias(psi1000, 1000.0)),
                         (math.inf, PT.psi_infinito(psi1000))):
        r = _uma_fase(2.0, -0.4, psi1000=psi1000, t_final=t_final)
        ref = PT.perda_progressiva_simplificada(-0.4, psi, 2.0, _sigma_c_p0g(15000.0), SP0,
                                                AP, A, I, EPC, 30.0)
        assert r.perda_progressiva_mpa[0] == pytest.approx(ref, rel=1e-9)


def test_9634_5_psi_limitado_a_2_5_psi1000():
    # (t − t0)/41,67 > 2,5^(1/0,15) = 451,8 -> a potência passaria de 2,5·ψ1000;
    # em 10^6 dias ψ fica no teto 2,5·ψ1000 (escolha declarada na docstring).
    cabo = PT.CaboProtensao(1.0, 0.0, 0.0, 1000.0, psi_1000_pct=3.0)
    assert PT._psi_cabo_p43(cabo, 1.0e6) == pytest.approx(7.5)
    assert PT._psi_cabo_p43(cabo, 1000.0) == pytest.approx(3.0 * (1000 / 41.67) ** 0.15)
    assert PT._psi_cabo_p43(cabo, math.inf) == pytest.approx(7.5)
    assert PT._psi_cabo_p43(cabo, 0.0) == 0.0


def test_9634_4_relaxacao_isolada_conta_da_protensao_do_cabo():
    # Concreto sem fluência nem retração, protensão em tp = 100 dias, t = 1100:
    # ψ = 3,5·(1000/41,67)^0,15 (conta a partir de tp, não da concretagem);
    # χ = −ln(1 − ψ); Δσp = σp0·χ/(1 + χ + αp·η·ρp) (9.6.3.4.2 com φ = εcs = 0).
    cam = PT.CamadaConcreto(A, I, 0.0, _phi_const(0.0), ECI_30)
    cab = PT.CaboProtensao(AP, EPC, 100.0, SP0, psi_1000_pct=3.5)
    r = PT.perdas_metodo_geral([], [cam], [cab], 1100.0)
    psi = 3.5 * (1000.0 / 41.67) ** 0.15
    chi = -math.log(1.0 - psi / 100.0)
    eta = 1.0 + EPC ** 2 * A / I
    esperado = SP0 * chi / (1.0 + chi + EP / ECI_30 * eta * AP / A)
    assert r.perda_progressiva_mpa[0] == pytest.approx(esperado, rel=1e-9)
    assert math.isnan(r.sigma_p_mpa[0][0])  # antes da protensão (nó t = 0)


def test_9634_4_encurtamento_imediato_do_cabo_ja_aderente():
    # Sem fluência, retração ou relaxação. Cabo 1 (y = 20 cm) protendido em
    # t = 0 e aderente; cabo 2 (y = −10 cm) protendido em t = 10 dias.
    # Seção em t = 10: concreto (E = 30 000 MPa, A = 3000, I = 900 000) + cabo 1
    # (Ep·Ap = 2·10^6):
    #   EA = 9·10^7 + 2·10^6 = 9,2·10^7; ES = 2·10^6·20 = 4·10^7;
    #   EI = 2,7·10^10 + 2·10^6·400 = 2,78·10^10.
    # Carga do cabo 2: N = −10·1200 = −12 000 MPa·cm²; M = −12 000·(−10) = +120 000.
    # det = 9,2e7·2,78e10 − (4e7)² = 2,556·10^18
    # ε0 = (−12000·2,78e10 − 4e7·120000)/det = −1,32394·10^-4
    # κ  = (9,2e7·120000 + 4e7·12000)/det = 4,50704·10^-6 1/cm
    # Δσp1 = Ep·(ε0 + 20·κ) = 200000·(−4,2254·10^-5) = −8,4507 MPa.
    cam = PT.CamadaConcreto(A, I, 0.0, _phi_const(0.0), 30000.0)
    c1 = PT.CaboProtensao(10.0, 20.0, 0.0, 1200.0)
    c2 = PT.CaboProtensao(10.0, -10.0, 10.0, 1200.0)
    r = PT.perdas_metodo_geral([], [cam], [c1, c2], 100.0)
    det = 9.2e7 * 2.78e10 - 4e7 ** 2
    e0 = (-12000.0 * 2.78e10 - 4e7 * 120000.0) / det
    k = (9.2e7 * 120000.0 + 4e7 * 12000.0) / det
    esperado = EP * (e0 + 20.0 * k)
    assert esperado == pytest.approx(-8.4507, abs=1e-4)
    assert r.variacao_imediata_mpa[0] == pytest.approx(esperado, rel=1e-9)
    assert r.variacao_imediata_mpa[1] == 0.0
    assert r.perda_progressiva_mpa == pytest.approx((0.0, 0.0), abs=1e-9)
    assert r.perda_total_mpa[0] == pytest.approx(-esperado, rel=1e-9)


def _equilibrio(r, camadas, cabos, no=-1):
    N = M = 0.0
    for i, c in enumerate(camadas):
        n = r.sigma_c_n_mpa[i][no] * c.Ac_cm2
        N += n
        M += n * c.y_cm + r.sigma_c_m_mpa_por_cm[i][no] * c.Ic_cm4
    for i, c in enumerate(cabos):
        s = r.sigma_p_mpa[i][no]
        if not math.isnan(s):
            N += s * c.Ap_cm2
            M += s * c.Ap_cm2 * c.y_cm
    return N / 10.0, M / 10.0   # kN e kN·cm


def _viga_composta():
    # Pré-moldada (0 a 60 cm de altura, y = 0 no topo da seção composta,
    # y para baixo): viga 20x60 com centroide em y = 40; laje 100x10 em y = 5,
    # concretada aos 60 dias e solidária aos 67.
    viga = PT.CamadaConcreto(1200.0, 20.0 * 60.0 ** 3 / 12.0, 40.0, _phi_anexo_a, ECI_30,
                             t_concretagem_dias=0.0, t_ativacao_dias=28.0,
                             eps_cs_func=lambda t, t0: tc.eps_cs_pmil(t, t0, 20.0, U_pct=70.0),
                             nome="viga")
    laje = PT.CamadaConcreto(1000.0, 100.0 * 10.0 ** 3 / 12.0, 5.0, _phi_anexo_a, ECI_30,
                             t_concretagem_dias=60.0, t_ativacao_dias=67.0,
                             eps_cs_func=lambda t, t0: tc.eps_cs_pmil(t, t0, 10.0, U_pct=70.0),
                             nome="laje")
    c1 = PT.CaboProtensao(6.0, 60.0, 28.0, 1300.0, psi_1000_pct=3.5)
    c2 = PT.CaboProtensao(4.0, 55.0, 90.0, 1300.0, psi_1000_pct=3.5)
    fases = [PT.FaseCarga(28.0, M_kncm=1200.0 * 2.5e-5 * 1000.0 ** 2 / 8.0, descricao="pp viga"),
             PT.FaseCarga(60.0, M_kncm=1000.0 * 2.5e-5 * 1000.0 ** 2 / 8.0, descricao="laje"),
             PT.FaseCarga(120.0, M_kncm=5000.0, descricao="revestimento")]
    return fases, [viga, laje], [c1, c2]


def test_9634_4_viga_composta_equilibrio_em_todos_os_nos():
    fases, camadas, cabos = _viga_composta()
    r = PT.perdas_metodo_geral(fases, camadas, cabos, 10000.0, n_subpassos=6,
                               tempos_saida_dias=(365.0,))
    assert 365.0 in r.tempos_dias
    for no in range(len(r.tempos_dias)):
        t = r.tempos_dias[no]
        N, M = _equilibrio(r, camadas, cabos, no)
        M_ext = sum(f.M_kncm for f in fases if f.t_dias <= t)
        assert N == pytest.approx(0.0, abs=1e-6)
        assert M == pytest.approx(M_ext, abs=1e-6 * max(1.0, M_ext))
    # a laje não tem tensão antes de ser solidária
    idx = r.tempos_dias.index(60.0)
    assert r.sigma_c_n_mpa[1][idx] == 0.0
    # perdas positivas e a do cabo 1 inclui o encurtamento pelo cabo 2
    assert all(p > 0.0 for p in r.perda_progressiva_mpa)
    assert r.variacao_imediata_mpa[0] != 0.0
    texto = " ".join(r.memoria)
    assert "9.6.3.4.4" in texto and "α = 0,8" in texto


def test_9634_4_passos_curtos_convergem_para_a_forma_integral():
    # Com α = 1 e passos curtos, a deformação do concreto junto ao cabo é a da
    # forma integral de A.2.5 aplicada ao histórico de tensão que o próprio
    # método gerou (diferença < 0,5 %).
    cam = PT.CamadaConcreto(A, I, 0.0, _phi_anexo_a, ECI_30, t_ativacao_dias=28.0)
    cab = PT.CaboProtensao(AP, EPC, 28.0, SP0, psi_1000_pct=3.5)
    r = PT.perdas_metodo_geral([PT.FaseCarga(28.0, M_kncm=15000.0)], [cam], [cab], 10000.0,
                               alfa=1.0, n_subpassos=60)
    hist = [(t, r.sigma_c_mpa(0, EPC, i)) for i, t in enumerate(r.tempos_dias)]
    eps_metodo = r.eps0_pmil[-1] + EPC * r.kappa_pmil_por_cm[-1]
    eps_integral = tc.eps_c_integral_pmil(hist, 10000.0, _phi_anexo_a, ECI_30, ECI_30,
                                          integrando="superposicao")
    assert eps_metodo == pytest.approx(eps_integral, rel=5e-3)
    # e a perda é estável com o refinamento
    r2 = PT.perdas_metodo_geral([PT.FaseCarga(28.0, M_kncm=15000.0)], [cam], [cab], 10000.0,
                                alfa=1.0, n_subpassos=120)
    assert r2.perda_progressiva_mpa[0] == pytest.approx(r.perda_progressiva_mpa[0], rel=5e-3)


def test_9634_4_uma_camada_sem_cabo_tensao_constante():
    # Só concreto sob N constante: σ fica constante e ε(t) = σ·[1/Ec + φ(t,t0)/Eci]
    # + εcs, a decomposição de A.2.1 (forma integral com integral nula).
    ecs = lambda t, t0: tc.eps_cs_pmil(t, t0, 20.0, U_pct=70.0)  # noqa: E731
    cam = PT.CamadaConcreto(A, I, 0.0, _phi_anexo_a, ECI_30, t_ativacao_dias=28.0,
                            eps_cs_func=ecs)
    r = PT.perdas_metodo_geral([PT.FaseCarga(28.0, N_kn=-3000.0)], [cam], [], 1000.0,
                               n_subpassos=5)
    sigma = -3000.0 * 10.0 / A   # −10 MPa
    assert r.sigma_c_n_mpa[0][-1] == pytest.approx(sigma, rel=1e-12)
    esperado = tc.eps_c_integral_pmil([(28.0, sigma)], 1000.0, _phi_anexo_a, ECI_30, ECI_30,
                                      eps_cs_pmil=ecs(1000.0, 28.0))
    assert r.eps0_pmil[-1] == pytest.approx(esperado, rel=1e-12)


def test_9634_4_armadura_passiva_reduz_a_perda():
    base = dict(phi=2.5, ecs=-0.5)
    cam = PT.CamadaConcreto(A, I, 0.0, _phi_const(base["phi"]), ECI_30,
                            eps_cs_func=lambda t, t0: base["ecs"] if t > t0 else 0.0)
    cab = PT.CaboProtensao(AP, EPC, 0.0, SP0, psi_func=lambda dt: 5.0)
    sem = PT.perdas_metodo_geral([], [cam], [cab], 1000.0)
    com = PT.perdas_metodo_geral([], [cam], [cab], 1000.0,
                                 armaduras=[PT.ArmaduraPassivaMetodoGeral(10.0, 27.0)])
    # a passiva restringe o encurtamento do concreto -> perda menor
    assert com.perda_progressiva_mpa[0] < sem.perda_progressiva_mpa[0]


@pytest.mark.parametrize("caso", [
    "sem_camada", "carga_antes", "t_final_curto", "alfa_zero", "alfa_maior",
    "subpassos_zero", "ap_negativo", "psi_100", "ativacao_antes", "sem_rigidez",
    "saida_depois",
])
def test_9634_4_fora_da_faixa(caso):
    cam = PT.CamadaConcreto(A, I, 0.0, _phi_const(2.0), ECI_30)
    cab = PT.CaboProtensao(AP, EPC, 0.0, SP0)
    args = dict(fases=[], camadas=[cam], cabos=[cab], t_final_dias=1000.0)
    if caso == "sem_camada":
        args["camadas"] = []
    elif caso == "carga_antes":
        args["camadas"] = [PT.CamadaConcreto(A, I, 0.0, _phi_const(2.0), ECI_30,
                                             t_ativacao_dias=28.0)]
        args["cabos"] = []
        args["fases"] = [PT.FaseCarga(10.0, M_kncm=100.0)]
    elif caso == "t_final_curto":
        args["fases"] = [PT.FaseCarga(2000.0, M_kncm=100.0)]
    elif caso == "alfa_zero":
        args["alfa"] = 0.0
    elif caso == "alfa_maior":
        args["alfa"] = 1.5
    elif caso == "subpassos_zero":
        args["n_subpassos"] = 0
    elif caso == "ap_negativo":
        args["cabos"] = [PT.CaboProtensao(-1.0, EPC, 0.0, SP0)]
    elif caso == "psi_100":
        args["cabos"] = [PT.CaboProtensao(AP, EPC, 0.0, SP0, psi_func=lambda dt: 100.0)]
    elif caso == "ativacao_antes":
        args["camadas"] = [PT.CamadaConcreto(A, I, 0.0, _phi_const(2.0), ECI_30,
                                             t_concretagem_dias=10.0, t_ativacao_dias=5.0)]
    elif caso == "sem_rigidez":
        args["camadas"] = [PT.CamadaConcreto(A, 0.0, 0.0, _phi_const(2.0), ECI_30)]
        args["cabos"] = []
        args["fases"] = [PT.FaseCarga(0.0, N_kn=-100.0)]
    elif caso == "saida_depois":
        args["tempos_saida_dias"] = (2000.0,)
    with pytest.raises(FE):
        PT.perdas_metodo_geral(**args)
