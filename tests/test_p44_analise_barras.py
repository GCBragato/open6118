"""Testes do P44 — Análise de barras: pórtico plano, pórtico espacial, grelha e treliça.

Cobre dimensionamento/analise_barras_nbr6118.py contra a ABNT NBR 6118:2026:

  - 11.3.3.3 Deslocamentos de apoio, p. 78
  - 11.4.1.1 Cargas de utilização nas posições mais desfavoráveis, p. 81-82
  - 14.5.2   Análise linear (elástico-linear, seção bruta, Ecs), p. 105
  - 14.6.4.1 Valores de rigidez (Ecs e inércia bruta), p. 111
  - 14.8.1   Viga-parede e pilar-parede como elemento linear com
    deformação por cisalhamento, p. 119
  - opções: 14.6.6.2 (p. 115), 15.5.1 (p. 124) e 15.7.3 (p. 126-127)

A norma não tabela resultados de análise: os valores esperados vêm de
soluções fechadas da resistência dos materiais, com a conta no comentário de
cada teste, e todo resultado confere o equilíbrio. Os casos cobrem as duas
direções e os dois sentidos de carga (risco 11 do plano).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import analise_barras_nbr6118 as ab   # noqa: E402
import nucleo_nbr6118 as nbr          # noqa: E402

REL = 1e-9

MAT = ab.Material.concreto(25.0)       # Ecs = 24 150 MPa (8.2.8), Gc = Ecs/2,4 (8.2.9)
SEC = ab.Secao.retangular(20.0, 50.0)  # I = 20·50³/12 = 208 333,3 cm⁴
E = MAT.E_kncm2                        # 2 415 kN/cm²
G = MAT.G_kncm2
I = SEC.I_cm4
A = SEC.A_cm2


def _aprox(a, b, rel=1e-9, abs_=1e-9):
    return a == pytest.approx(b, rel=rel, abs=abs_)


def _conferir_equilibrio(r):
    """ΣF_cargas + ΣF_reações = 0 em forças e momentos (a própria função já
    levanta erro; aqui se confere de fora)."""
    s = np.array(r.soma_cargas) + np.array(r.soma_reacoes)
    escala = max(1.0, float(np.max(np.abs(r.soma_cargas))), float(np.max(np.abs(r.soma_reacoes))))
    assert np.all(np.abs(s) <= 1e-7 * escala * 1e3), s
    assert r.equilibrio_ok


def _viga_biapoiada(L=500.0, sentido_barra=+1, cis=False, sec=SEC):
    m = ab.Modelo("portico_plano")
    if sentido_barra > 0:
        m.no(1, 0.0, 0.0)
        m.no(2, L, 0.0)
    else:
        m.no(1, L, 0.0)
        m.no(2, 0.0, 0.0)
    m.barra(1, 1, 2, sec, MAT, cisalhamento=cis)
    m.apoio(1, "ux", "uy")
    m.apoio(2, "uy")
    return m


def test_modulo_tem_mensagens_ao_usuario_acentuadas():
    fonte = Path(ab.__file__).read_text(encoding="utf-8")
    acentos = "áéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ"
    assert sum(fonte.count(c) for c in acentos) > 300


# =============================================================================
# 14.5.2 / 14.6.4.1 — rigidez padrão: seção bruta e Ecs (p. 105 e 111)
# =============================================================================
def test_material_concreto_usa_ecs_e_gc_do_nucleo():
    # 14.5.2 manda Ecs (8.2.8) e ν/Gc de 8.2.9; Gc = Ecs/2,4
    assert _aprox(MAT.E_mpa, nbr.Ecs(25.0))
    assert _aprox(MAT.G_mpa, nbr.Gc(25.0))
    assert _aprox(MAT.G_mpa, MAT.E_mpa / 2.4)
    assert _aprox(MAT.alfa_termico, 1e-5)
    assert _aprox(MAT.E_kncm2, MAT.E_mpa / 10.0)
    # fck fora de C20 a C90 levanta erro do núcleo
    with pytest.raises(nbr.FaixaNormativaError):
        ab.Material.concreto(15.0)


def test_material_estabilidade_global_majorado_10pct_15_5_1():
    # 15.5.1 (p. 124): o Ecs pode ser majorado em 10 % na estabilidade global
    m = ab.Material.concreto(30.0, estabilidade_global=True)
    assert _aprox(m.E_mpa, 1.1 * nbr.Ecs(30.0))
    assert _aprox(m.G_mpa, 1.1 * nbr.Gc(30.0))


def test_material_elastico_generico_e_faixa():
    m = ab.Material.elastico(21000.0, nu=0.25)
    assert _aprox(m.G_mpa, 21000.0 / 2.5)
    with pytest.raises(nbr.FaixaNormativaError):
        ab.Material.elastico(21000.0, nu=0.5)
    with pytest.raises(nbr.FaixaNormativaError):
        ab.Material(E_mpa=0.0, G_mpa=1.0)


def test_secao_retangular_bruta():
    s = ab.Secao.retangular(20.0, 50.0)
    assert _aprox(s.A_cm2, 1000.0)
    assert _aprox(s.I_cm4, 20.0 * 50.0 ** 3 / 12.0)
    assert _aprox(s.I2_cm4, 50.0 * 20.0 ** 3 / 12.0)
    assert _aprox(s.Av_cm2, 5.0 / 6.0 * 1000.0)
    # J do retângulo: β·a·b³, β = 1/3 − 0,21·(0,4)·(1 − 0,4⁴/12) = 0,249512
    beta = 1 / 3 - 0.21 * 0.4 * (1 - 0.4 ** 4 / 12)
    assert _aprox(s.J_cm4, beta * 50.0 * 20.0 ** 3)
    # quadrado: β = 1/3 − 0,21·(1 − 1/12) = 0,140833 (valor clássico 0,1406)
    assert ab.constante_torcao_retangulo_cm4(30, 30) == pytest.approx(0.1406 * 30 ** 4, rel=2e-3)
    with pytest.raises(nbr.FaixaNormativaError):
        ab.Secao.retangular(0.0, 50.0)
    with pytest.raises(nbr.FaixaNormativaError):
        ab.Secao(A_cm2=-1.0)
    with pytest.raises(nbr.FaixaNormativaError):
        ab.Secao(A_cm2=1.0, I_cm4=-1.0)


def test_viga_biapoiada_usa_ecs_e_inercia_bruta():
    # 14.6.4.1: rigidez = Ecs·Ic (bruta). Flecha no meio = 5·q·L⁴/(384·E·I)
    L, q = 500.0, 12.0          # q = 12 kN/m = 0,12 kN/cm
    m = _viga_biapoiada(L)
    m.no(3, L / 2, 0.0)          # nó no meio: refaz com duas barras
    m2 = ab.Modelo("portico_plano")
    m2.no(1, 0, 0), m2.no(2, L / 2, 0), m2.no(3, L, 0)
    m2.barra(1, 1, 2, SEC, MAT)
    m2.barra(2, 2, 3, SEC, MAT)
    m2.apoio(1, "ux", "uy")
    m2.apoio(3, "uy")
    c = ab.CasoCarga("q").distribuida(1, -q, direcao="Y").distribuida(2, -q, direcao="Y")
    r = ab.resolver(m2, c)
    esperado = -5 * 0.12 * L ** 4 / (384 * E * I)
    assert _aprox(r.deslocamentos[2]["uy"], esperado)
    _conferir_equilibrio(r)


# =============================================================================
# Viga biapoiada — os dois sentidos da barra e da carga
# =============================================================================
@pytest.mark.parametrize("sentido_barra", [+1, -1])
@pytest.mark.parametrize("sinal", [-1.0, +1.0])
def test_viga_biapoiada_carga_uniforme(sentido_barra, sinal):
    # q·L²/8 = 0,1·500²/8 = 3 125 kN·cm; reações q·L/2 = 25 kN
    L, q = 500.0, 10.0
    m = _viga_biapoiada(L, sentido_barra)
    r = ab.resolver(m, ab.CasoCarga().distribuida(1, sinal * q, direcao="Y"))
    b = r.barras[1]
    # carga para baixo (sinal −1) dá momento de vão positivo quando o y local
    # aponta para cima (barra da esquerda para a direita); invertendo a barra,
    # o y local vira para baixo e o sinal de M troca
    ylocal = +1 if sentido_barra > 0 else -1
    Mmeio = b.em(L / 2)["Mz"]
    assert _aprox(Mmeio, -sinal * ylocal * 3125.0)
    assert _aprox(r.reacoes[1]["uy"], -sinal * 25.0)
    assert _aprox(r.reacoes[2]["uy"], -sinal * 25.0)
    assert _aprox(r.reacoes[1]["ux"], 0.0)
    # dM/dx = Vy: nas extremidades |V| = qL/2, e o momento nas faces é nulo
    assert _aprox(abs(b.extremidade_i["Vy"]), 25.0)
    assert _aprox(b.extremidade_i["Mz"], 0.0, abs_=1e-7)
    assert _aprox(b.extremidade_j["Mz"], 0.0, abs_=1e-7)
    dM = (b.em(250.001)["Mz"] - b.em(249.999)["Mz"]) / 0.002
    assert abs(dM - b.em(250.0)["Vy"]) < 1e-4
    x = 100.0
    assert _aprox(b.em(x)["Vy"] - b.em(0.0)["Vy"], ylocal * sinal * 0.1 * x)
    _conferir_equilibrio(r)


@pytest.mark.parametrize("direcao,comp", [("X", "ux"), ("Y", "uy")])
@pytest.mark.parametrize("sinal", [-1.0, +1.0])
def test_viga_biapoiada_carga_concentrada_duas_direcoes(direcao, comp, sinal):
    # P a 1/3 do vão: em Y, RA = P·b/L e RB = P·a/L; em X, a força axial vai
    # toda ao apoio fixo (nó 1) e a barra fica com N constante no trecho
    L, a, P = 600.0, 200.0, 30.0
    m = _viga_biapoiada(L)
    r = ab.resolver(m, ab.CasoCarga().concentrada(1, a, sinal * P, direcao=direcao))
    if direcao == "Y":
        assert _aprox(r.reacoes[1]["uy"], -sinal * P * (L - a) / L)
        assert _aprox(r.reacoes[2]["uy"], -sinal * P * a / L)
        # Mmáx = P·a·b/L = 30·200·400/600 = 4 000 kN·cm
        assert _aprox(r.barras[1].em(a)["Mz"], -sinal * P * a * (L - a) / L)
    else:
        assert _aprox(r.reacoes[1]["ux"], -sinal * P)
        # antes da carga: força para +X traciona o trecho entre o apoio fixo e ela
        assert _aprox(r.barras[1].em(a / 2)["N"], sinal * P)
        assert _aprox(r.barras[1].em(a + 50)["N"], 0.0, abs_=1e-9)
    _conferir_equilibrio(r)


def test_viga_biapoiada_trapezoidal_e_parcial():
    # carga triangular de 0 a q0 = 20 kN/m (0,2 kN/cm) em L = 600 cm:
    # R = q0·L/2 = 60 kN; RA = R/3 = 20 kN; RB = 2R/3 = 40 kN;
    # Mmáx em x = L/√3: q0·L²/(9√3) = 0,2·600²/(9·√3) = 4 618,8 kN·cm
    L = 600.0
    m = _viga_biapoiada(L)
    r = ab.resolver(m, ab.CasoCarga().distribuida(1, 0.0, -20.0, direcao="Y"))
    assert _aprox(r.reacoes[1]["uy"], 20.0)
    assert _aprox(r.reacoes[2]["uy"], 40.0)
    assert _aprox(r.barras[1].em(L / math.sqrt(3))["Mz"], 0.2 * L ** 2 / (9 * math.sqrt(3)))
    # parcial: uniforme de 10 kN/m de a = 100 a b = 300 cm: R = 20 kN a 200 cm
    # RA = 20·400/600 = 13,333; RB = 6,667
    r = ab.resolver(m, ab.CasoCarga().distribuida(1, -10.0, direcao="Y", a_cm=100.0, b_cm=300.0))
    assert _aprox(r.reacoes[1]["uy"], 20.0 * 400 / 600)
    assert _aprox(r.reacoes[2]["uy"], 20.0 * 200 / 600)
    _conferir_equilibrio(r)


def test_viga_biapoiada_momento_concentrado():
    # momento M no meio: reações ±M/L; M em torno de z local (anti-horário)
    L, M = 400.0, 1000.0
    m = _viga_biapoiada(L)
    r = ab.resolver(m, ab.CasoCarga().momento_concentrado(1, L / 2, M, eixo="z"))
    assert _aprox(r.reacoes[1]["uy"], M / L)
    assert _aprox(r.reacoes[2]["uy"], -M / L)
    # salto de −M no diagrama (Mz = EI·v''): à esquerda +M/2... à direita −M/2
    b = r.barras[1]
    assert _aprox(b.em(L / 2 - 1e-6)["Mz"], M / 2, rel=1e-6)
    assert _aprox(b.em(L / 2 + 1e-6)["Mz"], -M / 2, rel=1e-6)
    _conferir_equilibrio(r)


# =============================================================================
# Viga engastada (balanço) e biengastada
# =============================================================================
@pytest.mark.parametrize("sinal", [-1.0, 1.0])
def test_balanco_carga_na_ponta(sinal):
    # δ = P·L³/(3·E·I); M no engaste = P·L; θ = P·L²/(2·E·I)
    L, P = 300.0, 10.0
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, L, 0)
    m.barra(1, 1, 2, SEC, MAT)
    m.apoio(1, "engaste")
    r = ab.resolver(m, ab.CasoCarga().nodal(2, Fy=sinal * P))
    assert _aprox(r.deslocamentos[2]["uy"], sinal * P * L ** 3 / (3 * E * I))
    assert _aprox(r.deslocamentos[2]["rz"], sinal * P * L ** 2 / (2 * E * I))
    assert _aprox(r.reacoes[1]["uy"], -sinal * P)
    assert _aprox(r.reacoes[1]["rz"], -sinal * P * L)
    # momento na face do engaste: −P·L (tração em cima com carga para baixo)
    assert _aprox(r.barras[1].extremidade_i["Mz"], sinal * P * L)
    _conferir_equilibrio(r)


def test_balanco_vertical_carga_horizontal():
    # pilar em balanço (eixo Y), força horizontal H no topo: δx = H·L³/(3EI)
    L, H = 300.0, 5.0
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, 0, L)
    m.barra(1, 1, 2, SEC, MAT)
    m.apoio(1, "engaste")
    for s in (+1, -1):
        r = ab.resolver(m, ab.CasoCarga().nodal(2, Fx=s * H))
        assert _aprox(r.deslocamentos[2]["ux"], s * H * L ** 3 / (3 * E * I))
        assert _aprox(r.reacoes[1]["ux"], -s * H)
        assert _aprox(r.reacoes[1]["rz"], s * H * L)
        _conferir_equilibrio(r)


def test_biengastada_carga_uniforme_e_concentrada():
    # uniforme: M apoio = −q·L²/12, M vão = q·L²/24
    L, q = 600.0, 10.0
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, L, 0)
    m.barra(1, 1, 2, SEC, MAT)
    m.apoio(1, "engaste"), m.apoio(2, "engaste")
    r = ab.resolver(m, ab.CasoCarga().distribuida(1, -q, direcao="Y"))
    b = r.barras[1]
    assert _aprox(b.extremidade_i["Mz"], -0.1 * L ** 2 / 12)
    assert _aprox(b.extremidade_j["Mz"], -0.1 * L ** 2 / 12)
    assert _aprox(b.em(L / 2)["Mz"], 0.1 * L ** 2 / 24)
    # concentrada P em a: MA = −P·a·b²/L², MB = −P·a²·b/L²
    P, a = 40.0, 200.0
    bb = L - a
    r = ab.resolver(m, ab.CasoCarga().concentrada(1, a, -P, direcao="Y"))
    b = r.barras[1]
    assert _aprox(b.extremidade_i["Mz"], -P * a * bb ** 2 / L ** 2)
    assert _aprox(b.extremidade_j["Mz"], -P * a ** 2 * bb / L ** 2)
    # RA = P·b²·(3a + b)/L³
    assert _aprox(r.reacoes[1]["uy"], P * bb ** 2 * (3 * a + bb) / L ** 3)
    _conferir_equilibrio(r)


# =============================================================================
# Viga contínua de dois vãos — equação dos três momentos
# =============================================================================
@pytest.mark.parametrize("L1,L2", [(500.0, 500.0), (400.0, 600.0), (700.0, 300.0)])
def test_viga_continua_dois_vaos_tres_momentos(L1, L2):
    # três momentos com MA = MC = 0: 2·MB·(L1 + L2) = −q·(L1³ + L2³)/4
    # → MB = −q·(L1³ + L2³)/(8·(L1 + L2))
    q = 15.0
    qc = 0.15
    m = ab.Modelo("portico_plano")
    m.no("A", 0, 0), m.no("B", L1, 0), m.no("C", L1 + L2, 0)
    m.barra(1, "A", "B", SEC, MAT)
    m.barra(2, "B", "C", SEC, MAT)
    m.apoio("A", "ux", "uy"), m.apoio("B", "uy"), m.apoio("C", "uy")
    c = ab.CasoCarga("q").distribuida(1, -q, direcao="Y").distribuida(2, -q, direcao="Y")
    r = ab.resolver(m, c)
    MB = -qc * (L1 ** 3 + L2 ** 3) / (8 * (L1 + L2))
    assert _aprox(r.barras[1].extremidade_j["Mz"], MB)
    assert _aprox(r.barras[2].extremidade_i["Mz"], MB)
    # reação em A = q·L1/2 + MB/L1
    assert _aprox(r.reacoes["A"]["uy"], qc * L1 / 2 + MB / L1)
    assert _aprox(r.reacoes["C"]["uy"], qc * L2 / 2 + MB / L2)
    total = qc * (L1 + L2)
    assert _aprox(sum(v["uy"] for v in r.reacoes.values()), total)
    _conferir_equilibrio(r)


def test_recalque_apoio_central_viga_continua_11_3_3_3():
    # 11.3.3.3 (p. 78): deslocamento imposto δk,sup no apoio B de duas vãos
    # iguais L. A viga 2L biapoiada com força R no meio desce R·(2L)³/(48EI):
    # R = 6·E·I·Δ/L³ e MB = R·(2L)/4 = 3·E·I·Δ/L² (momento positivo, de vão)
    L, D = 500.0, -1.0    # 1 cm para baixo
    m = ab.Modelo("portico_plano")
    m.no("A", 0, 0), m.no("B", L, 0), m.no("C", 2 * L, 0)
    m.barra(1, "A", "B", SEC, MAT)
    m.barra(2, "B", "C", SEC, MAT)
    m.apoio("A", "ux", "uy"), m.apoio("B", "uy"), m.apoio("C", "uy")
    r = ab.resolver(m, ab.CasoCarga("recalque").deslocamento_apoio("B", uy=D))
    R = 6 * E * I * abs(D) / L ** 3
    assert _aprox(r.reacoes["B"]["uy"], -R)
    assert _aprox(r.reacoes["A"]["uy"], R / 2)
    assert _aprox(r.reacoes["C"]["uy"], R / 2)
    assert _aprox(r.barras[1].extremidade_j["Mz"], 3 * E * I * abs(D) / L ** 2)
    assert _aprox(r.deslocamentos["B"]["uy"], D)
    assert any("11.3.3.3" in linha for linha in r.memoria)
    _conferir_equilibrio(r)
    # sentido oposto: tudo troca de sinal
    r2 = ab.resolver(m, ab.CasoCarga().deslocamento_apoio("B", uy=-D))
    assert _aprox(r2.reacoes["B"]["uy"], R)


def test_recalque_em_grau_livre_levanta_erro():
    m = _viga_biapoiada()
    with pytest.raises(ValueError, match="11.3.3.3"):
        ab.resolver(m, ab.CasoCarga().deslocamento_apoio(2, ux=1.0))


def test_acao_deslocamentos_apoio_inferior_nulo():
    # 11.3.3.3: valor superior δk,sup; inferior nulo; uma única ação permanente
    ac = ab.acao_deslocamentos_apoio(1234.5)
    assert ac.Fk == 1234.5
    assert ac.Fk_inf == 0.0
    assert ac.natureza == "permanente_indireta"
    assert ac.tipo == "recalque_retracao"
    import acoes_nbr6118 as acoes
    # desfavorável: entra com γ da coluna de recalques; favorável: Fk_inf = 0
    r_desf = acoes.combinacao_ultima([ac], sentido="max")
    r_fav = acoes.combinacao_ultima([ab.acao_deslocamentos_apoio(-50.0)], sentido="max")
    assert r_desf.Fd > 0.0
    assert r_fav.Fd == 0.0


# =============================================================================
# Apoio elástico (mola)
# =============================================================================
def test_mola_no_meio_da_viga():
    # viga 2L biapoiada, carga q, mola k no meio:
    # δ0 = 5·q·(2L)⁴/(384EI); f = (2L)³/(48EI); R = δ0/(f + 1/k)
    L, qc, k = 400.0, 0.1, 50.0
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, L, 0), m.no(3, 2 * L, 0)
    m.barra(1, 1, 2, SEC, MAT), m.barra(2, 2, 3, SEC, MAT)
    m.apoio(1, "ux", "uy"), m.apoio(3, "uy")
    m.apoio(2, molas={"uy": k})
    r = ab.resolver(m, ab.CasoCarga().distribuida(1, -10, direcao="Y").distribuida(2, -10, direcao="Y"))
    d0 = 5 * qc * (2 * L) ** 4 / (384 * E * I)
    f = (2 * L) ** 3 / (48 * E * I)
    R = d0 / (f + 1 / k)
    assert _aprox(r.reacoes[2]["uy"], R)
    assert _aprox(r.deslocamentos[2]["uy"], -R / k)
    _conferir_equilibrio(r)


def test_mola_invalida():
    m = _viga_biapoiada()
    with pytest.raises(nbr.FaixaNormativaError):
        m.apoio(2, molas={"rz": -1.0})
    with pytest.raises(ValueError):
        m.apoio(2, molas={"uy": 10.0})   # uy já é restrito
    with pytest.raises(ValueError):
        m.apoio(2, molas={"uz": 10.0})   # grau fora do pórtico plano


# =============================================================================
# Pórtico simples (biarticulado) — método das forças
# =============================================================================
@pytest.mark.parametrize("Ib_Ic", [1.0, 3.0])
def test_portico_biarticulado_carga_vertical(Ib_Ic):
    # Empuxo H = q·L²/(4·h·(2k + 3)), k = (Ib/Ic)·(h/L) (método das forças:
    # δ10 = h·q·L³/(12·E·Ib); δ11 = 2h³/(3E·Ic) + h²·L/(E·Ib); H = δ10/δ11)
    L, h, q = 600.0, 300.0, 20.0
    qc = 0.2
    sec_c = ab.Secao.retangular(20, 40)
    Ic = sec_c.I_cm4
    sec_b = ab.Secao(A_cm2=1000.0, I_cm4=Ib_Ic * Ic)
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, 0, h), m.no(3, L, h), m.no(4, L, 0)
    m.barra("P1", 1, 2, sec_c, MAT)
    m.barra("V", 2, 3, sec_b, MAT)
    m.barra("P2", 4, 3, sec_c, MAT)
    m.apoio(1, "fixo"), m.apoio(4, "fixo")
    # sem deformação axial para bater com a solução de flexão pura
    m2 = ab.Modelo("portico_plano")
    big = 1e6
    m2.no(1, 0, 0), m2.no(2, 0, h), m2.no(3, L, h), m2.no(4, L, 0)
    m2.barra("P1", 1, 2, ab.Secao(A_cm2=big, I_cm4=Ic), MAT)
    m2.barra("V", 2, 3, ab.Secao(A_cm2=big, I_cm4=Ib_Ic * Ic), MAT)
    m2.barra("P2", 4, 3, ab.Secao(A_cm2=big, I_cm4=Ic), MAT)
    m2.apoio(1, "fixo"), m2.apoio(4, "fixo")
    r = ab.resolver(m2, ab.CasoCarga().distribuida("V", -q, direcao="Y"))
    k = Ib_Ic * h / L
    H = qc * L ** 2 / (4 * h * (2 * k + 3))
    assert r.reacoes[1]["ux"] == pytest.approx(H, rel=1e-5)
    assert r.reacoes[4]["ux"] == pytest.approx(-H, rel=1e-5)
    assert _aprox(r.reacoes[1]["uy"], qc * L / 2)
    # momento no nó da viga = −H·h (tração em cima)
    assert r.barras["V"].extremidade_i["Mz"] == pytest.approx(-H * h, rel=1e-5)
    _conferir_equilibrio(r)
    _conferir_equilibrio(ab.resolver(m, ab.CasoCarga().distribuida("V", -q, direcao="Y")))


@pytest.mark.parametrize("sinal", [1.0, -1.0])
def test_portico_biarticulado_carga_horizontal(sinal):
    # H no topo: por antissimetria cada base recebe H/2; o momento no topo
    # dos pilares é H·h/2; as reações verticais valem ±H·h/L
    L, h, Hh = 600.0, 300.0, 12.0
    m = ab.Modelo("portico_plano")
    big = 1e7
    m.no(1, 0, 0), m.no(2, 0, h), m.no(3, L, h), m.no(4, L, 0)
    s = ab.Secao(A_cm2=big, I_cm4=I)
    m.barra("P1", 1, 2, s, MAT), m.barra("V", 2, 3, s, MAT), m.barra("P2", 4, 3, s, MAT)
    m.apoio(1, "fixo"), m.apoio(4, "fixo")
    r = ab.resolver(m, ab.CasoCarga().nodal(2, Fx=sinal * Hh))
    assert r.reacoes[1]["ux"] == pytest.approx(-sinal * Hh / 2, rel=1e-6)
    assert r.reacoes[4]["ux"] == pytest.approx(-sinal * Hh / 2, rel=1e-6)
    assert r.reacoes[1]["uy"] == pytest.approx(-sinal * Hh * h / L, rel=1e-6)
    assert r.reacoes[4]["uy"] == pytest.approx(sinal * Hh * h / L, rel=1e-6)
    assert abs(r.barras["V"].extremidade_i["Mz"]) == pytest.approx(Hh * h / 2, rel=1e-6)
    _conferir_equilibrio(r)


def test_carga_global_em_barra_inclinada():
    # barra inclinada 3-4-5 biapoiada (fixo em i, rolete vertical em j) com
    # carga vertical global q por unidade de comprimento da barra:
    # resultante = q·L (L = 500), reações verticais q·L/2 cada
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, 400, 300)
    m.barra(1, 1, 2, SEC, MAT)
    m.apoio(1, "fixo"), m.apoio(2, "uy")
    r = ab.resolver(m, ab.CasoCarga().distribuida(1, -10.0, direcao="Y"))
    assert _aprox(r.reacoes[1]["uy"], 25.0)
    assert _aprox(r.reacoes[2]["uy"], 25.0)
    assert _aprox(r.reacoes[1]["ux"], 0.0, abs_=1e-9)
    # momento máximo = (q·cos α)·L²/8 com a componente normal; cos α = 0,8
    assert _aprox(r.barras[1].em(250.0)["Mz"], 0.1 * 0.8 * 500 ** 2 / 8)
    _conferir_equilibrio(r)


# =============================================================================
# Liberações de extremidade e trechos rígidos
# =============================================================================
def test_rotula_interna_viga_gerber():
    # engaste em A, rótula em B (fim da barra 1), rolete em C; carga q no
    # vão BC (L2): BC é biapoiada → RC = q·L2/2 e força em B = q·L2/2;
    # a força RB para baixo na ponta B do balanço AB dá, no engaste, a
    # reação de momento +RB·L1 (anti-horária)
    L1, L2, q = 300.0, 400.0, 10.0
    m = ab.Modelo("portico_plano")
    m.no("A", 0, 0), m.no("B", L1, 0), m.no("C", L1 + L2, 0)
    m.barra(1, "A", "B", SEC, MAT, liberacoes_j=("rz",))
    m.barra(2, "B", "C", SEC, MAT)
    m.apoio("A", "engaste"), m.apoio("C", "uy")
    r = ab.resolver(m, ab.CasoCarga().distribuida(2, -q, direcao="Y"))
    RB = 0.1 * L2 / 2
    assert _aprox(r.reacoes["C"]["uy"], RB)
    assert _aprox(r.reacoes["A"]["uy"], RB)
    assert _aprox(r.reacoes["A"]["rz"], RB * L1)
    assert _aprox(r.barras[1].extremidade_j["Mz"], 0.0, abs_=1e-7)
    assert _aprox(r.barras[2].extremidade_i["Mz"], 0.0, abs_=1e-7)
    _conferir_equilibrio(r)


def test_barra_rotulada_nas_duas_pontas_com_carga_transversal():
    # barra biarticulada num pórtico com carga transversal: vira biapoiada
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, 500, 0)
    m.barra(1, 1, 2, SEC, MAT, liberacoes_i="rotula", liberacoes_j="rotula")
    m.apoio(1, "engaste"), m.apoio(2, "engaste")
    r = ab.resolver(m, ab.CasoCarga().distribuida(1, -10, direcao="Y"))
    assert _aprox(r.reacoes[1]["rz"], 0.0, abs_=1e-7)
    assert _aprox(r.barras[1].em(250)["Mz"], 3125.0)


def test_liberacao_invalida_e_torcao_dupla():
    m = ab.Modelo("portico_espacial")
    m.no(1, 0, 0, 0), m.no(2, 100, 0, 0)
    with pytest.raises(ValueError):
        m.barra(1, 1, 2, SEC, MAT, liberacoes_i=("uy",))
    with pytest.raises(ValueError, match="mecanismo"):
        m.barra(1, 1, 2, SEC, MAT, liberacoes_i=("rx",), liberacoes_j=("rx",))


def test_trecho_rigido_no_engaste_14_6_2_1():
    # balanço com trecho rígido a no engaste: δ = P·(L − a)³/(3EI)
    #   + θ·a... como o trecho é rígido e o engaste perfeito, a parte flexível
    #   é um balanço de L − a: δ = P·(L − a)³/(3EI); M na face = P·(L − a);
    #   M no nó (reação) = P·L
    L, a, P = 300.0, 30.0, 10.0
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, L, 0)
    m.barra(1, 1, 2, SEC, MAT, trecho_rigido_i_cm=a)
    m.apoio(1, "engaste")
    r = ab.resolver(m, ab.CasoCarga().nodal(2, Fy=-P))
    assert _aprox(r.deslocamentos[2]["uy"], -P * (L - a) ** 3 / (3 * E * I))
    assert _aprox(r.barras[1].extremidade_i["Mz"], -P * (L - a))
    assert _aprox(r.reacoes[1]["rz"], P * L)
    assert _aprox(r.barras[1].L_flexivel_cm, L - a)
    _conferir_equilibrio(r)


def test_trecho_rigido_na_ponta_e_carga_sobre_ele():
    # balanço com trecho rígido b na ponta: força na ponta P age com braço
    # até a face: parte flexível de L − b com força P e momento P·b na face:
    # δface = P(L−b)³/(3EI) + P·b·(L−b)²/(2EI); θ = P(L−b)²/(2EI) + P·b·(L−b)/(EI)
    # δponta = δface + θ·b
    L, b, P = 300.0, 40.0, 10.0
    Lf = L - b
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, L, 0)
    m.barra(1, 1, 2, SEC, MAT, trecho_rigido_j_cm=b)
    m.apoio(1, "engaste")
    r = ab.resolver(m, ab.CasoCarga().nodal(2, Fy=-P))
    dface = P * Lf ** 3 / (3 * E * I) + P * b * Lf ** 2 / (2 * E * I)
    th = P * Lf ** 2 / (2 * E * I) + P * b * Lf / (E * I)
    assert _aprox(r.deslocamentos[2]["uy"], -(dface + th * b))
    # a mesma força aplicada como carga concentrada sobre o trecho rígido,
    # na ponta (s = L), dá o mesmo resultado; e uma distribuída só no trecho
    # rígido equivale à resultante no centroide
    r2 = ab.resolver(m, ab.CasoCarga().concentrada(1, L, -P, direcao="Y"))
    assert _aprox(r2.deslocamentos[2]["uy"], r.deslocamentos[2]["uy"])
    q = 10.0   # kN/m em 40 cm = 4 kN a 20 cm da ponta
    r3 = ab.resolver(m, ab.CasoCarga().distribuida(1, -q, direcao="Y", a_cm=L - b, b_cm=L))
    r4 = ab.resolver(m, ab.CasoCarga().concentrada(1, L - b / 2, -0.1 * b, direcao="Y"))
    assert _aprox(r3.deslocamentos[2]["uy"], r4.deslocamentos[2]["uy"])
    assert _aprox(r3.reacoes[1]["rz"], 0.1 * b * (L - b / 2))
    _conferir_equilibrio(r3)


def test_trecho_rigido_invalido():
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, 100, 0)
    with pytest.raises(nbr.FaixaNormativaError):
        m.barra(1, 1, 2, SEC, MAT, trecho_rigido_i_cm=60, trecho_rigido_j_cm=40)
    with pytest.raises(nbr.FaixaNormativaError):
        m.barra(1, 1, 2, SEC, MAT, trecho_rigido_i_cm=-1)


# =============================================================================
# 14.8.1 — deformação por cisalhamento (viga-parede e pilar-parede)
# =============================================================================
def test_balanco_timoshenko_viga_parede_14_8_1():
    # δ = P·L³/(3EI) + P·L/(G·Av), Av = 5/6·b·h (viga-parede curta 20×200)
    L, P = 300.0, 100.0
    sec = ab.Secao.retangular(20.0, 200.0)
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, L, 0)
    m.barra(1, 1, 2, sec, MAT, cisalhamento=True, elemento_parede=True)
    m.apoio(1, "engaste")
    r = ab.resolver(m, ab.CasoCarga().nodal(2, Fy=-P))
    flex = P * L ** 3 / (3 * E * sec.I_cm4)
    cis = P * L / (G * sec.Av_cm2)
    assert _aprox(r.deslocamentos[2]["uy"], -(flex + cis))
    assert cis > 0.25 * flex   # na viga-parede a parcela de cisalhamento pesa (aqui 32 %)
    assert any("14.8.1" in linha for linha in r.memoria)


def test_biapoiada_timoshenko_carga_concentrada_meio():
    # δ = P·L³/(48EI) + P·L/(4·G·Av)
    L, P = 400.0, 50.0
    sec = ab.Secao.retangular(20.0, 150.0)
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, L / 2, 0), m.no(3, L, 0)
    m.barra(1, 1, 2, sec, MAT, cisalhamento=True)
    m.barra(2, 2, 3, sec, MAT, cisalhamento=True)
    m.apoio(1, "fixo"), m.apoio(3, "uy")
    r = ab.resolver(m, ab.CasoCarga().nodal(2, Fy=-P))
    esp = P * L ** 3 / (48 * E * sec.I_cm4) + P * L / (4 * G * sec.Av_cm2)
    assert _aprox(r.deslocamentos[2]["uy"], -esp)
    # mesma viga numa barra só, com a carga concentrada na barra
    m2 = ab.Modelo("portico_plano")
    m2.no(1, 0, 0), m2.no(3, L, 0)
    m2.barra(1, 1, 3, sec, MAT, cisalhamento=True)
    m2.apoio(1, "fixo"), m2.apoio(3, "uy")
    r2 = ab.resolver(m2, ab.CasoCarga().concentrada(1, L / 2, -P, direcao="Y"))
    assert _aprox(r2.reacoes[1]["uy"], P / 2)
    # biengastada com cisalhamento e carga no meio: por simetria, M = P·L/8
    # nas pontas, com ou sem cisalhamento
    m3 = ab.Modelo("portico_plano")
    m3.no(1, 0, 0), m3.no(3, L, 0)
    m3.barra(1, 1, 3, sec, MAT, cisalhamento=True)
    m3.apoio(1, "engaste"), m3.apoio(3, "engaste")
    r3 = ab.resolver(m3, ab.CasoCarga().concentrada(1, L / 2, -P, direcao="Y"))
    assert _aprox(r3.barras[1].extremidade_i["Mz"], -P * L / 8)


def test_parede_sem_cisalhamento_levanta_erro_14_8_1():
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, 300, 0)
    with pytest.raises(nbr.FaixaNormativaError, match="14.8.1"):
        m.barra(1, 1, 2, SEC, MAT, elemento_parede=True)


def test_ajuste_rigidez_flexao_fator_EI():
    # 14.8.1 (ajuste da rigidez à flexão) e 15.7.3: δ ∝ 1/fator
    L, P = 300.0, 10.0
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, L, 0)
    m.barra(1, 1, 2, SEC, MAT, fator_EI=0.4)
    m.apoio(1, "engaste")
    r = ab.resolver(m, ab.CasoCarga().nodal(2, Fy=-P))
    assert _aprox(r.deslocamentos[2]["uy"], -P * L ** 3 / (3 * 0.4 * E * I))
    with pytest.raises(nbr.FaixaNormativaError):
        m.barra(2, 1, 2, SEC, MAT, fator_EI=0.0)


# =============================================================================
# 15.7.3 e 14.6.6.2 — opções de rigidez
# =============================================================================
def test_fatores_15_7_3_todas_as_linhas():
    assert ab.fator_rigidez_nlf_aproximada("laje") == 0.3
    assert ab.fator_rigidez_nlf_aproximada("viga") == 0.4
    assert ab.fator_rigidez_nlf_aproximada("viga", armadura_simetrica=True) == 0.5
    assert ab.fator_rigidez_nlf_aproximada("pilar") == 0.8
    assert ab.fator_rigidez_nlf_aproximada("pilar", n_andares=4) == 0.8
    with pytest.raises(nbr.FaixaNormativaError):
        ab.fator_rigidez_nlf_aproximada("pilar", n_andares=3)
    with pytest.raises(ValueError):
        ab.fator_rigidez_nlf_aproximada("parede")


def test_fator_torcao_14_6_6_2():
    assert _aprox(ab.fator_rigidez_torcao(), 0.15)
    assert _aprox(ab.fator_rigidez_torcao(classe_protensao=2), 1.0)
    assert _aprox(ab.fator_rigidez_torcao(classe_protensao=3), 1.0)
    assert ab.fator_rigidez_torcao(desprezar_para_elu=True) == 0.0


# =============================================================================
# Grelha — duas vigas cruzadas
# =============================================================================
@pytest.mark.parametrize("L1,L2", [(600.0, 600.0), (500.0, 700.0)])
@pytest.mark.parametrize("sinal", [-1.0, 1.0])
def test_grelha_duas_vigas_cruzadas(L1, L2, sinal):
    # vigas biapoiadas cruzando no meio; P no cruzamento. Compatibilidade:
    # P1·L1³/(48EI) = P2·L2³/(48EI), P1 + P2 = P → P1 = P·L2³/(L1³ + L2³).
    # Sem torção no cruzamento (meio do vão: rotação nula por simetria).
    P = 100.0
    m = ab.Modelo("grelha")
    m.no("c", 0, 0)
    m.no("x1", -L1 / 2, 0), m.no("x2", L1 / 2, 0)
    m.no("y1", 0, -L2 / 2), m.no("y2", 0, L2 / 2)
    for nome, a, b in (("X1", "x1", "c"), ("X2", "c", "x2"), ("Y1", "y1", "c"), ("Y2", "c", "y2")):
        m.barra(nome, a, b, SEC, MAT, fator_GJ=ab.fator_rigidez_torcao())
    for n in ("x1", "x2", "y1", "y2"):
        m.apoio(n, "uz")
    r = ab.resolver(m, ab.CasoCarga().nodal("c", Fz=sinal * P))
    P1 = P * L2 ** 3 / (L1 ** 3 + L2 ** 3)
    assert _aprox(r.reacoes["x1"]["uz"], -sinal * P1 / 2)
    assert _aprox(r.reacoes["y1"]["uz"], -sinal * (P - P1) / 2)
    assert _aprox(r.deslocamentos["c"]["uz"], sinal * P1 * L1 ** 3 / (48 * E * I))
    # momento no cruzamento na viga X: P1·L1/4 (positivo = de vão, com
    # carga para baixo)
    assert _aprox(r.barras["X1"].extremidade_j["My"], -sinal * P1 * L1 / 4)
    assert _aprox(r.barras["X1"].M[-1], -sinal * P1 * L1 / 4)
    _conferir_equilibrio(r)


def test_grelha_carga_distribuida_e_torcao():
    # viga em balanço na grelha (eixo X) com outra barra em L (eixo Y)
    # engastada em x=0; força P na ponta da barra em Y: a barra X sofre
    # torção T = P·L2 e o deslocamento é
    # P·L1³/(3EI) + P·L2³/(3EI) + P·L2²·L1/(GJ)
    L1, L2, P = 300.0, 200.0, 5.0
    m = ab.Modelo("grelha")
    m.no(1, 0, 0), m.no(2, L1, 0), m.no(3, L1, L2)
    m.barra(1, 1, 2, SEC, MAT)
    m.barra(2, 2, 3, SEC, MAT)
    m.apoio(1, "engaste")
    r = ab.resolver(m, ab.CasoCarga().nodal(3, Fz=-P))
    J = SEC.J_cm4
    esp = P * L1 ** 3 / (3 * E * I) + P * L2 ** 3 / (3 * E * I) + P * L2 ** 2 * L1 / (G * J)
    assert _aprox(r.deslocamentos[3]["uz"], -esp)
    assert _aprox(abs(r.barras[1].extremidade_i["T"]), P * L2)
    # reação: Fz = P, momento em torno de X = −P·L2 · (−1)... r × F na ponta:
    # r = (L1, L2, 0), F = (0, 0, −P): M = (−P·L2, P·L1, 0); reação = −M
    assert _aprox(r.reacoes[1]["uz"], P)
    assert _aprox(r.reacoes[1]["rx"], P * L2)
    assert _aprox(r.reacoes[1]["ry"], -P * L1)
    _conferir_equilibrio(r)
    # distribuída vertical global numa viga da grelha biapoiada
    m2 = ab.Modelo("grelha")
    m2.no(1, 0, 0), m2.no(2, 500, 0)
    m2.barra(1, 1, 2, SEC, MAT)
    m2.apoio(1, "uz", "rx"), m2.apoio(2, "uz")
    r2 = ab.resolver(m2, ab.CasoCarga().distribuida(1, -10.0, direcao="Z"))
    assert _aprox(r2.barras[1].em(250)["My"], 3125.0)
    assert _aprox(r2.reacoes[1]["uz"], 25.0)


def test_grelha_torcao_nula_para_elu():
    # GJ = 0 (14.6.6.2, ELU): a viga em L perde a torção e vira mecanismo se
    # a força for na ponta da barra em Y
    L1, L2, P = 300.0, 200.0, 5.0
    m = ab.Modelo("grelha")
    m.no(1, 0, 0), m.no(2, L1, 0), m.no(3, L1, L2)
    m.barra(1, 1, 2, SEC, MAT, fator_GJ=ab.fator_rigidez_torcao(desprezar_para_elu=True))
    m.barra(2, 2, 3, SEC, MAT)
    m.apoio(1, "engaste")
    with pytest.raises(ab.EstruturaHipostatica):
        ab.resolver(m, ab.CasoCarga().nodal(3, Fz=-P))


# =============================================================================
# Treliças — método dos nós
# =============================================================================
@pytest.mark.parametrize("sinal", [-1.0, 1.0])
def test_trelica_plana_isostatica_metodo_dos_nos(sinal):
    # A(0,0) fixo, B(400,0) rolete, C(200,150); P vertical em C.
    # sen θ = 150/250 = 0,6, tg θ = 0,75.
    # Nó C: 2·N·sen θ = −P → N_AC = N_BC = −P/(2·0,6) (compressão com P para baixo)
    # Nó A: N_AB + N_AC·cos θ = 0 → N_AB = P/(2·tg θ)
    P = 60.0
    m = ab.Modelo("trelica_plana")
    m.no("A", 0, 0), m.no("B", 400, 0), m.no("C", 200, 150)
    s = ab.Secao(A_cm2=10.0)
    m.barra("AB", "A", "B", s, MAT)
    m.barra("AC", "A", "C", s, MAT)
    m.barra("BC", "B", "C", s, MAT)
    m.apoio("A", "fixo"), m.apoio("B", "uy")
    r = ab.resolver(m, ab.CasoCarga().nodal("C", Fy=sinal * P))
    assert _aprox(r.barras["AC"].N[0], sinal * P / 1.2)
    assert _aprox(r.barras["BC"].N[5], sinal * P / 1.2)
    assert _aprox(r.barras["AB"].N[0], -sinal * P / 1.5)
    assert _aprox(r.reacoes["A"]["uy"], -sinal * P / 2)
    assert _aprox(r.reacoes["B"]["uy"], -sinal * P / 2)
    for b in r.barras.values():
        assert np.allclose(b.esforcos["Mz"], 0.0, atol=1e-9)
        assert np.allclose(b.esforcos["Vy"], 0.0, atol=1e-9)
    _conferir_equilibrio(r)


def test_trelica_plana_horizontal_e_deslocamento():
    # mesma treliça, força horizontal H em C: reação horizontal −H em A;
    # RA_y = −H·150/400, RB_y = +H·150/400
    H = 40.0
    m = ab.Modelo("trelica_plana")
    m.no("A", 0, 0), m.no("B", 400, 0), m.no("C", 200, 150)
    s = ab.Secao(A_cm2=10.0)
    m.barra("AB", "A", "B", s, MAT), m.barra("AC", "A", "C", s, MAT), m.barra("BC", "B", "C", s, MAT)
    m.apoio("A", "fixo"), m.apoio("B", "uy")
    r = ab.resolver(m, ab.CasoCarga().nodal("C", Fx=H))
    assert _aprox(r.reacoes["A"]["ux"], -H)
    assert _aprox(r.reacoes["A"]["uy"], -H * 150 / 400)
    assert _aprox(r.reacoes["B"]["uy"], H * 150 / 400)
    # barra de dois nós em tração simples: δ = N·L/(EA)
    m2 = ab.Modelo("trelica_plana")
    m2.no(1, 0, 0), m2.no(2, 250, 0)
    m2.barra(1, 1, 2, s, MAT)
    m2.apoio(1, "fixo"), m2.apoio(2, "uy")
    r2 = ab.resolver(m2, ab.CasoCarga().nodal(2, Fx=20.0))
    assert _aprox(r2.deslocamentos[2]["ux"], 20.0 * 250 / (E * 10.0))


def test_trelica_barra_com_carga_transversal_biapoiada():
    # barra de treliça com peso próprio: as reações nodais são q·L/2 e o
    # momento no meio da barra é q·L²/8 (a barra trabalha como biapoiada)
    m = ab.Modelo("trelica_plana")
    m.no(1, 0, 0), m.no(2, 500, 0)
    m.barra(1, 1, 2, ab.Secao(A_cm2=10.0), MAT)
    m.apoio(1, "fixo"), m.apoio(2, "uy")
    r = ab.resolver(m, ab.CasoCarga().distribuida(1, -10.0, direcao="Y"))
    assert _aprox(r.reacoes[1]["uy"], 25.0)
    assert _aprox(r.barras[1].em(250)["Mz"], 3125.0)


def test_trelica_espacial_tripe():
    # tripé simétrico: apoios a raio R = 300 no plano z = 0, ápice em
    # (0, 0, 400); comprimento da perna 500, cos φ = 400/500 = 0,8.
    # Carga vertical P: N = −P/(3·0,8) em cada perna
    P, Rr, H = 90.0, 300.0, 400.0
    m = ab.Modelo("trelica_espacial")
    m.no("T", 0, 0, H)
    s = ab.Secao(A_cm2=10.0)
    for k in range(3):
        ang = 2 * math.pi * k / 3
        m.no(k, Rr * math.cos(ang), Rr * math.sin(ang), 0.0)
        m.barra(k, k, "T", s, MAT)
        m.apoio(k, "fixo")
    r = ab.resolver(m, ab.CasoCarga().nodal("T", Fz=-P))
    for k in range(3):
        assert _aprox(r.barras[k].N[0], -P / 2.4)
        assert _aprox(r.reacoes[k]["uz"], P / 3)
    # carga horizontal em X: equilíbrio nas duas direções
    r2 = ab.resolver(m, ab.CasoCarga().nodal("T", Fx=10.0, Fy=-5.0))
    assert _aprox(sum(v["ux"] for v in r2.reacoes.values()), -10.0)
    assert _aprox(sum(v["uy"] for v in r2.reacoes.values()), 5.0)
    _conferir_equilibrio(r2)


# =============================================================================
# Pórtico espacial
# =============================================================================
def test_portico_espacial_balanco_em_L():
    # barra 1 em X (engastada na origem), barra 2 em Y; P vertical (−Z) na
    # ponta: δ = P·L1³/(3EI) + P·L2³/(3EI) + P·L2²·L1/(GJ)
    L1, L2, P = 300.0, 200.0, 5.0
    m = ab.Modelo("portico_espacial")
    m.no(1, 0, 0, 0), m.no(2, L1, 0, 0), m.no(3, L1, L2, 0)
    m.barra(1, 1, 2, SEC, MAT)
    m.barra(2, 2, 3, SEC, MAT)
    m.apoio(1, "engaste")
    r = ab.resolver(m, ab.CasoCarga().nodal(3, Fz=-P))
    J = SEC.J_cm4
    esp = P * L1 ** 3 / (3 * E * I) + P * L2 ** 3 / (3 * E * I) + P * L2 ** 2 * L1 / (G * J)
    assert _aprox(r.deslocamentos[3]["uz"], -esp)
    assert _aprox(r.reacoes[1]["uz"], P)
    assert _aprox(r.reacoes[1]["rx"], P * L2)
    assert _aprox(r.reacoes[1]["ry"], -P * L1)
    # força horizontal em X na ponta: flexão da barra 2 no plano horizontal
    # (I2), axial na barra 1 e flexão da barra 1 no plano horizontal pelo
    # momento H·L2 (rotação H·L2·L1/(E·I2), que move a ponta de ·L2):
    # δx = H·L2³/(3·E·I2) + H·L2²·L1/(E·I2) + H·L1/(EA)
    Hx = 3.0
    r2 = ab.resolver(m, ab.CasoCarga().nodal(3, Fx=Hx))
    esp2 = (Hx * L2 ** 3 / (3 * E * SEC.I2_cm4) + Hx * L2 ** 2 * L1 / (E * SEC.I2_cm4)
            + Hx * L1 / (E * A))
    assert _aprox(r2.deslocamentos[3]["ux"], esp2)
    _conferir_equilibrio(r)
    _conferir_equilibrio(r2)


def test_portico_espacial_pilar_vertical_dois_planos():
    # pilar vertical (eixo Z) engastado na base, 20×50: z local = X global
    # (padrão para barra vertical), I (b·h³/12, h = 50) no plano x-z local.
    # Força em X no topo usa I; força em Y usa I2.
    L = 300.0
    m = ab.Modelo("portico_espacial")
    m.no(1, 0, 0, 0), m.no(2, 0, 0, L)
    m.barra(1, 1, 2, SEC, MAT)
    m.apoio(1, "engaste")
    r = ab.resolver(m, ab.CasoCarga().nodal(2, Fx=4.0, Fy=-2.0, Fz=-100.0))
    assert _aprox(r.deslocamentos[2]["ux"], 4.0 * L ** 3 / (3 * E * I))
    assert _aprox(r.deslocamentos[2]["uy"], -2.0 * L ** 3 / (3 * E * SEC.I2_cm4))
    assert _aprox(r.deslocamentos[2]["uz"], -100.0 * L / (E * A))
    assert _aprox(r.barras[1].N[0], -100.0)
    _conferir_equilibrio(r)


def test_portico_espacial_vetor_ref_gira_eixos():
    # com vetor_ref = Y, o z local vira Y global e a força em Y usa I
    L = 300.0
    m = ab.Modelo("portico_espacial")
    m.no(1, 0, 0, 0), m.no(2, 0, 0, L)
    m.barra(1, 1, 2, SEC, MAT, vetor_ref=(0, 1, 0))
    m.apoio(1, "engaste")
    r = ab.resolver(m, ab.CasoCarga().nodal(2, Fy=-2.0))
    assert _aprox(r.deslocamentos[2]["uy"], -2.0 * L ** 3 / (3 * E * I))
    with pytest.raises(ValueError):
        m.barra(2, 1, 2, SEC, MAT, vetor_ref=(0, 0, 1))


def test_portico_espacial_liberacao_torcao_e_momento_concentrado():
    # barra em X biengastada, momento de torção Mx no meio: cada engaste
    # recebe Mx/2 (rigidezes iguais); com a torção liberada na ponta j,
    # tudo vai ao engaste i
    L, Mx = 400.0, 800.0
    m = ab.Modelo("portico_espacial")
    m.no(1, 0, 0, 0), m.no(2, L, 0, 0)
    m.barra(1, 1, 2, SEC, MAT)
    m.apoio(1, "engaste"), m.apoio(2, "engaste")
    r = ab.resolver(m, ab.CasoCarga().momento_concentrado(1, L / 2, Mx, eixo="x"))
    assert _aprox(r.reacoes[1]["rx"], -Mx / 2)
    assert _aprox(r.reacoes[2]["rx"], -Mx / 2)
    m2 = ab.Modelo("portico_espacial")
    m2.no(1, 0, 0, 0), m2.no(2, L, 0, 0)
    m2.barra(1, 1, 2, SEC, MAT, liberacoes_j=("rx",))
    m2.apoio(1, "engaste"), m2.apoio(2, "engaste")
    r2 = ab.resolver(m2, ab.CasoCarga().momento_concentrado(1, L / 4, Mx, eixo="X"))
    assert _aprox(r2.reacoes[1]["rx"], -Mx)
    assert _aprox(r2.reacoes[2]["rx"], 0.0, abs_=1e-7)
    _conferir_equilibrio(r2)


# =============================================================================
# Temperatura (11.4.2, valores do P4)
# =============================================================================
def test_temperatura_uniforme_barra_biengastada():
    # N = −E·A·α·ΔT (compressão no aquecimento)
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, 500, 0)
    m.barra(1, 1, 2, SEC, MAT)
    m.apoio(1, "engaste"), m.apoio(2, "engaste")
    r = ab.resolver(m, ab.CasoCarga().temperatura(1, delta_t_uniforme_c=15.0))
    assert _aprox(r.barras[1].N[3], -E * A * 1e-5 * 15.0)
    # livre (biapoiada com rolete): alonga α·ΔT·L sem esforço
    m2 = _viga_biapoiada(500.0)
    r2 = ab.resolver(m2, ab.CasoCarga().temperatura(1, delta_t_uniforme_c=-10.0))
    assert _aprox(r2.deslocamentos[2]["ux"], -1e-5 * 10.0 * 500.0)
    assert _aprox(r2.barras[1].N[0], 0.0, abs_=1e-9)


def test_gradiente_termico():
    # face superior (y local +) 10 °C mais quente, h = 50: κ0 = −α·ΔT/h
    # biengastada: M = −E·I·κ0 = E·I·α·ΔT/h (positivo: traciona embaixo)
    # biapoiada: sem esforço; flecha no meio = κ0·L²/8 (para cima)
    L, dT, h = 500.0, 10.0, 50.0
    k0 = -1e-5 * dT / h
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, L, 0)
    m.barra(1, 1, 2, SEC, MAT)
    m.apoio(1, "engaste"), m.apoio(2, "engaste")
    r = ab.resolver(m, ab.CasoCarga().temperatura(1, delta_t_faces_c=dT, altura_cm=h))
    assert np.allclose(r.barras[1].M, -E * I * k0, rtol=1e-9)
    m2 = ab.Modelo("portico_plano")
    m2.no(1, 0, 0), m2.no(2, L / 2, 0), m2.no(3, L, 0)
    m2.barra(1, 1, 2, SEC, MAT), m2.barra(2, 2, 3, SEC, MAT)
    m2.apoio(1, "fixo"), m2.apoio(3, "uy")
    c = ab.CasoCarga().temperatura(1, delta_t_faces_c=dT, altura_cm=h).temperatura(
        2, delta_t_faces_c=dT, altura_cm=h)
    r2 = ab.resolver(m2, c)
    assert _aprox(r2.deslocamentos[2]["uy"], -k0 * L ** 2 / 8)
    assert np.allclose(r2.barras[1].M, 0.0, atol=1e-8)
    with pytest.raises(nbr.FaixaNormativaError):
        ab.CasoCarga().temperatura(1, delta_t_faces_c=5.0)


def test_gradiente_termico_grelha_plano_principal():
    # na grelha o plano principal é o vertical (z local = Z): face de cima
    # mais quente numa viga biengastada → My = E·I·α·ΔT/h
    L, dT, h = 400.0, 8.0, 50.0
    m = ab.Modelo("grelha")
    m.no(1, 0, 0), m.no(2, L, 0)
    m.barra(1, 1, 2, SEC, MAT)
    m.apoio(1, "engaste"), m.apoio(2, "engaste")
    r = ab.resolver(m, ab.CasoCarga().temperatura(1, delta_t_faces_c=dT, altura_cm=h))
    assert np.allclose(r.barras[1].M, E * I * 1e-5 * dT / h, rtol=1e-9)


# =============================================================================
# Erros e conferências
# =============================================================================
def test_estrutura_hipostatica():
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0), m.no(2, 500, 0)
    m.barra(1, 1, 2, SEC, MAT)
    m.apoio(1, "fixo")   # gira em torno do pino
    with pytest.raises(ab.EstruturaHipostatica):
        ab.resolver(m, ab.CasoCarga().nodal(2, Fy=-1.0))


def test_carga_fora_do_plano():
    m = _viga_biapoiada()
    with pytest.raises(ValueError, match="fora do plano"):
        ab.resolver(m, ab.CasoCarga().nodal(2, Fz=1.0))
    with pytest.raises(ValueError, match="fora do plano"):
        ab.resolver(m, ab.CasoCarga().distribuida(1, -1.0, direcao="Z"))


def test_validacoes_do_modelo():
    with pytest.raises(ValueError):
        ab.Modelo("placa")
    m = ab.Modelo("portico_plano")
    m.no(1, 0, 0)
    with pytest.raises(ValueError):
        m.no(1, 1, 0)
    with pytest.raises(ValueError):
        m.no(2, 0, 0, 5.0)           # z ≠ 0 no modelo plano
    m.no(2, 0, 0)
    with pytest.raises(ValueError):
        m.barra(1, 1, 2, SEC, MAT)   # comprimento nulo
    with pytest.raises(ValueError):
        m.barra(1, 1, 9, SEC, MAT)   # nó inexistente
    with pytest.raises(ValueError):
        m.apoio(1, "uz")             # grau fora do plano
    with pytest.raises(ValueError):
        ab.resolver(ab.Modelo(), ab.CasoCarga())
    m3 = _viga_biapoiada()
    with pytest.raises(ValueError):
        ab.resolver(m3, ab.CasoCarga().distribuida(99, -1.0))
    with pytest.raises(ValueError):
        ab.resolver(m3, ab.CasoCarga().distribuida(1, -1.0, a_cm=100, b_cm=900))
    with pytest.raises(ValueError):
        ab.resolver(m3, ab.CasoCarga().concentrada(1, 900.0, -1.0))
    with pytest.raises(ValueError):
        ab.CasoCarga().distribuida(1, -1.0, direcao="w")
    with pytest.raises(ValueError):
        ab.resolver(m3, ab.CasoCarga().nodal(99, Fy=1.0))
    with pytest.raises(ValueError):
        ab.resolver(m3, ab.CasoCarga(), n_estacoes=1)
    with pytest.raises(ValueError):
        ab.resolver(m3, ab.CasoCarga()).barras[1].em(9999.0)


def test_verificar_equilibrio_levanta_erro():
    with pytest.raises(ab.ErroEquilibrio, match="equilíbrio"):
        ab._verificar_equilibrio((0, -10, 0, 0, 0, 0), (0, 9, 0, 0, 0, 0), 20.0, 2000.0)
    assert ab._verificar_equilibrio((0, -10, 0, 0, 0, 0), (0, 10, 0, 0, 0, 0), 20.0, 2000.0) == 0.0


def test_resultado_memoria_e_imutavel():
    m = _viga_biapoiada()
    r = ab.resolver(m, ab.CasoCarga("g").distribuida(1, -10.0, direcao="Y"))
    assert any("14.5.2" in linha for linha in r.memoria)
    assert any("14.6.4.1" in linha and "fissuração" in linha for linha in r.memoria)
    assert any("Ecs" in linha for linha in r.memoria)
    with pytest.raises(Exception):
        r.caso = "outro"


# =============================================================================
# 11.4.1.1 — alternância de cargas e envoltória
# =============================================================================
def _continua_dois_vaos(L=500.0):
    m = ab.Modelo("portico_plano")
    m.no("A", 0, 0), m.no("B", L, 0), m.no("C", 2 * L, 0)
    m.barra(1, "A", "B", SEC, MAT)
    m.barra(2, "B", "C", SEC, MAT)
    m.apoio("A", "ux", "uy"), m.apoio("B", "uy"), m.apoio("C", "uy")
    return m


def test_alternancia_viga_continua_dois_vaos_11_4_1_1():
    # dois vãos iguais L, q em cada vão (0,1 kN/cm):
    # só vão 1 carregado: MB = −qL²/16; RA = 7qL/16; M(L/2) no vão 1 = 3qL²/32
    # só vão 2 carregado: M(L/2) no vão 1 = MB/2 = −qL²/32
    # envoltória em L/2 do vão 1: máx 3qL²/32, mín −qL²/32
    # apoio B: mín = −qL²/8 (os dois carregados), máx = 0
    # vão 1, Mmáx = (7qL/16)²/(2q) = 49qL²/512 em x = 7L/16
    L, q = 500.0, 0.1
    m = _continua_dois_vaos(L)
    cq = ab.CasoCarga("q").distribuida(1, -10.0, direcao="Y").distribuida(2, -10.0, direcao="Y")
    r = ab.alternancia_cargas(m, cq, n_estacoes=17)
    env = r.envoltoria[1]
    i_meio = 8
    assert _aprox(env.x_cm[i_meio], L / 2)
    assert _aprox(env.maximo["Mz"][i_meio], 3 * q * L ** 2 / 32)
    assert _aprox(env.minimo["Mz"][i_meio], -q * L ** 2 / 32)
    assert _aprox(env.minimo["Mz"][-1], -q * L ** 2 / 8)
    assert _aprox(env.maximo["Mz"][-1], 0.0, abs_=1e-7)
    assert not r.dispensada
    assert r.n_arranjos == 2
    # reação em A: máx 7qL/16 (só vão 1), mín −qL/16 (só vão 2 levanta A)
    assert _aprox(r.reacoes_max["A"]["uy"], 7 * q * L / 16)
    assert _aprox(r.reacoes_min["A"]["uy"], -q * L / 16)
    # reação em B com os dois vãos: 10qL/8
    assert _aprox(r.reacoes_max["B"]["uy"], 10 * q * L / 8)
    assert any("11.4.1.1" in linha for linha in r.memoria)
    # Mmáx exato pelo método em()
    x0 = 7 * L / 16
    r1 = ab.resolver(m, ab.CasoCarga().distribuida(1, -10.0, direcao="Y"))
    assert _aprox(r1.barras[1].em(x0)["Mz"], 49 * q * L ** 2 / 512)


def test_alternancia_com_permanente_e_grupos():
    # g em tudo + q por vão; o grupo junta as duas barras do vão 1
    L = 500.0
    m = ab.Modelo("portico_plano")
    m.no("A", 0, 0), m.no("M", L / 2, 0), m.no("B", L, 0), m.no("C", 2 * L, 0)
    m.barra(1, "A", "M", SEC, MAT), m.barra(2, "M", "B", SEC, MAT), m.barra(3, "B", "C", SEC, MAT)
    m.apoio("A", "ux", "uy"), m.apoio("B", "uy"), m.apoio("C", "uy")
    cg = ab.CasoCarga("g")
    cq = ab.CasoCarga("q")
    for b in (1, 2, 3):
        cg.distribuida(b, -20.0, direcao="Y")
        cq.distribuida(b, -10.0, direcao="Y")
    r = ab.alternancia_cargas(m, cq, caso_g=cg, grupos=[[1, 2], [3]])
    assert r.n_arranjos == 2
    # no apoio B (fim da barra 2): mín = −(g + q)·L²/8
    assert _aprox(r.envoltoria[2].minimo["Mz"][-1], -(0.2 + 0.1) * L ** 2 / 8)
    # máx no apoio B = só g: −g·L²/8
    assert _aprox(r.envoltoria[2].maximo["Mz"][-1], -0.2 * L ** 2 / 8)


def test_alternancia_dispensada_14_6_6_3():
    # q = 3 kN/m² ≤ 5 e q ≤ 0,5·(g + q) = 4 → dispensa: tudo carregado junto
    L, q = 500.0, 0.1
    m = _continua_dois_vaos(L)
    cq = ab.CasoCarga("q").distribuida(1, -10.0, direcao="Y").distribuida(2, -10.0, direcao="Y")
    r = ab.alternancia_cargas(m, cq, q_kn_m2=3.0, g_kn_m2=5.0, n_estacoes=17)
    assert r.dispensada
    env = r.envoltoria[1]
    # com os dois vãos carregados, M(L/2) = qL²/16 (máx = mín)
    assert _aprox(env.maximo["Mz"][8], q * L ** 2 / 16)
    assert _aprox(env.minimo["Mz"][8], q * L ** 2 / 16)
    assert any("14.6.6.3" in linha and "dispensada" in linha for linha in r.memoria)
    # dos dois lados do limite: q = 5,0 com g = 5,0 dispensa; q = 5,01 não
    assert ab.alternancia_cargas(m, cq, q_kn_m2=5.0, g_kn_m2=5.0).dispensada
    assert not ab.alternancia_cargas(m, cq, q_kn_m2=5.01, g_kn_m2=5.0).dispensada
    # q > 0,5·(g + q): q = 3, g = 2,9 não dispensa
    assert not ab.alternancia_cargas(m, cq, q_kn_m2=3.0, g_kn_m2=2.9).dispensada


def test_alternancia_cargas_nodais_e_erros():
    m = _continua_dois_vaos()
    cq = ab.CasoCarga("q").nodal("B", Mz=100.0)
    r = ab.alternancia_cargas(m, cq)
    assert r.n_arranjos == 1
    with pytest.raises(ValueError):
        ab.alternancia_cargas(m, ab.CasoCarga("vazio"))
    with pytest.raises(ValueError, match="11.4.1.1"):
        ab.alternancia_cargas(m, ab.CasoCarga().temperatura(1, 5.0))


# =============================================================================
# Consistência interna: barra única contra a mesma barra dividida em nós
# =============================================================================
@pytest.mark.parametrize("cis", [False, True])
def test_espacial_barra_inclinada_igual_a_barra_dividida(cis):
    # barra inclinada no espaço, engastada em i e apoiada em j (uz), com
    # carga trapezoidal global, força concentrada e momento concentrado.
    # As forças de engastamento são exatas: dividir a barra em nós nos pontos
    # de quebra (com as cargas repartidas) tem de dar os mesmos
    # deslocamentos, e os esforços da barra única em x têm de igualar os das
    # extremidades das barras divididas.
    p0 = np.array([0.0, 0.0, 0.0])
    p1 = np.array([300.0, 200.0, 150.0])
    L = float(np.linalg.norm(p1))
    sec = ab.Secao.retangular(25.0, 60.0)
    s1, s2 = L / 3, 2 * L / 3
    q1, q2 = -8.0, -20.0          # kN/m em Z global, linear de 0 a L

    def q(s):
        return q1 + (q2 - q1) * s / L

    m1 = ab.Modelo("portico_espacial")
    m1.no(0, *p0), m1.no(1, *p1)
    m1.barra("u", 0, 1, sec, MAT, cisalhamento=cis)
    m1.apoio(0, "engaste"), m1.apoio(1, "uz", "ux")
    c1 = (ab.CasoCarga().distribuida("u", q1, q2, direcao="Z")
          .concentrada("u", s1, 7.0, direcao="y").momento_concentrado("u", s2, 300.0, eixo="X"))
    r1 = ab.resolver(m1, c1)

    m2 = ab.Modelo("portico_espacial")
    ex = (p1 - p0) / L
    m2.no(0, *p0), m2.no("a", *(p0 + s1 * ex)), m2.no("b", *(p0 + s2 * ex)), m2.no(1, *p1)
    for nome, a, b in (("1", 0, "a"), ("2", "a", "b"), ("3", "b", 1)):
        m2.barra(nome, a, b, sec, MAT, cisalhamento=cis)
    m2.apoio(0, "engaste"), m2.apoio(1, "uz", "ux")
    c2 = (ab.CasoCarga().distribuida("1", q(0), q(s1), direcao="Z")
          .distribuida("2", q(s1), q(s2), direcao="Z").distribuida("3", q(s2), q(L), direcao="Z")
          .concentrada("2", 0.0, 7.0, direcao="y").momento_concentrado("3", 0.0, 300.0, eixo="X"))
    r2 = ab.resolver(m2, c2)
    for g in ab.GRAUS:
        assert r1.deslocamentos[1][g] == pytest.approx(r2.deslocamentos[1][g], rel=1e-8, abs=1e-12)
        assert r1.reacoes[0][g] == pytest.approx(r2.reacoes[0][g], rel=1e-8, abs=1e-8)
    # esforços no meio do trecho 2 (x = L/2) contra a barra "2" em L/6
    e1 = r1.barras["u"].em(L / 2)
    e2 = r2.barras["2"].em(L / 6)
    for k in ("N", "Vy", "Vz", "T", "My", "Mz"):
        assert e1[k] == pytest.approx(e2[k], rel=1e-8, abs=1e-8)
    _conferir_equilibrio(r1)


def test_reciprocidade_maxwell_portico_espacial():
    # deslocamento em A por força unitária em B = deslocamento em B por
    # força unitária em A (Maxwell-Betti), num pórtico espacial com trecho
    # rígido, liberação e cisalhamento
    m = ab.Modelo("portico_espacial")
    m.no(1, 0, 0, 0), m.no(2, 0, 0, 300), m.no(3, 400, 0, 300), m.no(4, 400, 300, 300)
    m.no(5, 400, 300, 0)
    s = ab.Secao.retangular(20, 50)
    m.barra(1, 1, 2, s, MAT, trecho_rigido_j_cm=25)
    m.barra(2, 2, 3, s, MAT, trecho_rigido_i_cm=10, cisalhamento=True)
    m.barra(3, 3, 4, s, MAT, liberacoes_j=("rz",))
    m.barra(4, 5, 4, s, MAT)
    m.apoio(1, "engaste"), m.apoio(5, "engaste")
    ra = ab.resolver(m, ab.CasoCarga().nodal(3, Fy=1.0))
    rb = ab.resolver(m, ab.CasoCarga().nodal(2, Fx=1.0))
    assert ra.deslocamentos[2]["ux"] == pytest.approx(rb.deslocamentos[3]["uy"], rel=1e-9)
    rc = ab.resolver(m, ab.CasoCarga().nodal(4, Mz=1.0))
    rd = ab.resolver(m, ab.CasoCarga().nodal(3, Fz=1.0))
    assert rc.deslocamentos[3]["uz"] == pytest.approx(rd.deslocamentos[4]["rz"], rel=1e-9)
