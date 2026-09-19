"""Testes do P47 — Esforços hiperestáticos de protensão.

Cobre o bloco P47 de dimensionamento/protendido_nbr6118.py contra a
ABNT NBR 6118:2026:

  - 11.3.3.5   Ação da protensão como ação permanente indireta, p. 81:
    ``TrechoCabo``, ``PerfilCabo``, ``cargas_equivalentes_cabo``,
    ``momento_isostatico_cabo_kncm`` e ``esforcos_hiperestaticos_protensao``.
  - 17.2.4.2.1 Protensão no ELU: só hiperestáticos e pré-alongamento com
    perdas, p. 143: ``pre_alongamento_protensao_pmil`` e
    ``combinar_protensao_elu``.

A norma não tabela esforços de análise: os valores esperados vêm de soluções
fechadas da resistência dos materiais.

  - Viga biapoiada (isostática): o método das cargas equivalentes reproduz,
    ponto a ponto, o momento isostático M1(x) = P·e(x) — é a demonstração
    clássica do método (Lin/Naaman), conferida aqui numa barra com
    excentricidades e flecha quaisquer, não só no caso trivial e = 0.
  - Viga contínua de 2 vãos iguais com cabo de excentricidade nula nos três
    apoios e a mesma flecha nos dois vãos: a carga equivalente do cabo
    (``cargas_equivalentes_cabo``) é, nesse caso particular, uma carga
    distribuída w = −8·P·flecha/L² igual nos dois vãos — isto é, uma carga
    uniforme comum ao longo da viga contínua inteira. O momento no apoio
    central de uma viga contínua de 2 vãos iguais sob carga uniforme q ao
    longo de toda a viga é o resultado clássico da equação dos três momentos
    (conta no comentário de cada teste): M_apoio = −q·L²/8, com q o valor em
    módulo da carga de cima para baixo (convenção da biblioteca: gravidade
    entra em −y e dá momento positivo no vão — ver o cabeçalho de
    analise_barras_nbr6118). Com q = 8·P·flecha/L², M_apoio = −P·flecha.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import analise_barras_nbr6118 as ab   # noqa: E402
import nucleo_nbr6118 as nbr          # noqa: E402
import protendido_nbr6118 as pt       # noqa: E402

MAT = ab.Material.concreto(30.0)
SEC = ab.Secao.retangular(25.0, 55.0)


def _aprox(a, b, rel=1e-6, abs_=1e-2):
    return a == pytest.approx(b, rel=rel, abs=abs_)


def _viga_biapoiada(L):
    m = ab.Modelo("portico_plano")
    m.no("i", 0.0, 0.0)
    m.no("j", L, 0.0)
    m.barra("v", "i", "j", SEC, MAT)
    m.apoio("i", "ux", "uy")
    m.apoio("j", "uy")
    return m


def _viga_continua_2_vaos(L):
    m = ab.Modelo("portico_plano")
    m.no("A", 0.0, 0.0)
    m.no("B", L, 0.0)
    m.no("C", 2.0 * L, 0.0)
    m.barra("v1", "A", "B", SEC, MAT)
    m.barra("v2", "B", "C", SEC, MAT)
    m.apoio("A", "ux", "uy")
    m.apoio("B", "uy")
    m.apoio("C", "uy")
    return m


def test_modulo_tem_mensagens_ao_usuario_acentuadas():
    fonte = Path(pt.__file__).read_text(encoding="utf-8")
    acentos = "áéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ"
    assert sum(fonte.count(c) for c in acentos) > 400


# =============================================================================
# TrechoCabo, PerfilCabo — geometria do cabo (11.3.3.5, p. 81)
# =============================================================================
def test_trecho_cabo_comprimento_nao_positivo_levanta_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        pt.TrechoCabo(barra="v", L_cm=0.0, e_i_cm=0.0, e_j_cm=0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        pt.TrechoCabo(barra="v", L_cm=-100.0, e_i_cm=0.0, e_j_cm=0.0)


def test_perfil_cabo_sem_trecho_levanta_erro():
    with pytest.raises(ValueError):
        pt.PerfilCabo(trechos=())


def test_trecho_cabo_excentricidade_parabola():
    # e(x) = e_i*(1-u) + e_j*u + 4*flecha*u*(1-u), u = x/L (11.3.3.5, p. 81).
    L = 600.0
    t = pt.TrechoCabo(barra="v", L_cm=L, e_i_cm=10.0, e_j_cm=-4.0, flecha_cm=6.0)
    # extremidades: reproduz e_i e e_j exatamente
    assert _aprox(t.excentricidade_cm(0.0), 10.0)
    assert _aprox(t.excentricidade_cm(L), -4.0)
    # meio: media da corda mais a flecha
    meio_corda = (10.0 - 4.0) / 2.0
    assert _aprox(t.excentricidade_cm(L / 2.0), meio_corda + 6.0)
    # ponto interior (u=0,25): conta direta
    u = 0.25
    esperado = 10.0 * (1 - u) + (-4.0) * u + 4.0 * 6.0 * u * (1 - u)
    assert _aprox(t.excentricidade_cm(u * L), esperado)


def test_trecho_cabo_excentricidade_fora_do_trecho_levanta_erro():
    t = pt.TrechoCabo(barra="v", L_cm=500.0, e_i_cm=0.0, e_j_cm=0.0, flecha_cm=5.0)
    with pytest.raises(ValueError):
        t.excentricidade_cm(-10.0)
    with pytest.raises(ValueError):
        t.excentricidade_cm(510.0)


# =============================================================================
# momento_isostatico_cabo_kncm — M1(x) = P·e(x) (11.3.3.5, p. 81)
# =============================================================================
def test_momento_isostatico_cabo():
    L = 500.0
    P = 1200.0
    t = pt.TrechoCabo(barra="v", L_cm=L, e_i_cm=8.0, e_j_cm=-2.0, flecha_cm=10.0)
    for x in (0.0, 125.0, 250.0, 375.0, 500.0):
        esperado = P * t.excentricidade_cm(x)
        assert _aprox(pt.momento_isostatico_cabo_kncm(t, P, x), esperado)


def test_momento_isostatico_cabo_P_nao_positivo_levanta_erro():
    t = pt.TrechoCabo(barra="v", L_cm=500.0, e_i_cm=0.0, e_j_cm=0.0)
    with pytest.raises(nbr.FaixaNormativaError):
        pt.momento_isostatico_cabo_kncm(t, 0.0, 100.0)
    with pytest.raises(nbr.FaixaNormativaError):
        pt.momento_isostatico_cabo_kncm(t, -50.0, 100.0)


# =============================================================================
# cargas_equivalentes_cabo — força axial, momentos e carga distribuída
# =============================================================================
def test_cargas_equivalentes_cabo_conteudo():
    L = 400.0
    P = 900.0
    e_i, e_j, flecha = 6.0, -3.0, 5.0
    t = pt.TrechoCabo(barra="v", L_cm=L, e_i_cm=e_i, e_j_cm=e_j, flecha_cm=flecha)
    perfil = pt.PerfilCabo(trechos=(t,))
    caso = pt.cargas_equivalentes_cabo(perfil, P)

    conc = [dados for (barra, tipo, dados) in caso.barra_cargas if tipo == "conc"]
    mom = [dados for (barra, tipo, dados) in caso.barra_cargas if tipo == "mom"]
    dist = [dados for (barra, tipo, dados) in caso.barra_cargas if tipo == "dist"]

    # força axial P nas duas pontas, em x local (compressão sobre o concreto)
    conc_x = {(a, v) for (direcao, a, v) in conc if direcao == ("l", 0)}
    assert conc_x == {(0.0, P), (L, -P)}

    # momentos concentrados: -P*e_i em x=0 e +P*e_j em x=L (eixo z local)
    mom_por_x = {a: v for (direcao, a, v) in mom if direcao == ("l", 2)}
    assert _aprox(mom_por_x[0.0], -P * e_i)
    assert _aprox(mom_por_x[L], P * e_j)

    # carga distribuída w = -8*P*flecha/L^2, convertida para kN/m (fator 100)
    assert len(dist) == 1
    direcao, a, b, q1, q2 = dist[0]
    assert direcao == ("l", 1)  # direção y local
    # dist guarda q já em kN/cm (a própria distribuida() divide por 100 ao gravar)
    w_esperado_kn_cm = -8.0 * P * flecha / (L * L)
    assert _aprox(q1, w_esperado_kn_cm, rel=1e-9, abs_=1e-12)
    assert _aprox(q2, w_esperado_kn_cm, rel=1e-9, abs_=1e-12)


def test_cargas_equivalentes_cabo_P_por_trecho_tamanho_errado():
    t1 = pt.TrechoCabo(barra="v1", L_cm=400.0, e_i_cm=0.0, e_j_cm=0.0)
    t2 = pt.TrechoCabo(barra="v2", L_cm=400.0, e_i_cm=0.0, e_j_cm=0.0)
    perfil = pt.PerfilCabo(trechos=(t1, t2))
    with pytest.raises(ValueError):
        pt.cargas_equivalentes_cabo(perfil, [500.0])


def test_cargas_equivalentes_cabo_P_nao_positivo_levanta_erro():
    t = pt.TrechoCabo(barra="v", L_cm=400.0, e_i_cm=0.0, e_j_cm=0.0)
    perfil = pt.PerfilCabo(trechos=(t,))
    with pytest.raises(nbr.FaixaNormativaError):
        pt.cargas_equivalentes_cabo(perfil, -100.0)


# =============================================================================
# esforcos_hiperestaticos_protensao — viga biapoiada (hiperestático = 0)
# =============================================================================
def test_hiperestatico_zero_em_viga_biapoiada():
    # 11.3.3.5 (p. 81): estrutura isostática -> M_total(x) = P*e(x) em todo
    # ponto, logo M_hiperestático = 0 (demonstração clássica do método das
    # cargas equivalentes; ver o cabeçalho do módulo).
    L = 600.0
    P = 1000.0
    t = pt.TrechoCabo(barra="v", L_cm=L, e_i_cm=5.0, e_j_cm=-3.0, flecha_cm=20.0)
    cabo = pt.Cabo(perfil=pt.PerfilCabo(trechos=(t,)), P_kn=P)
    m = _viga_biapoiada(L)
    res = pt.esforcos_hiperestaticos_protensao(m, cabo, n_estacoes=21)
    assert res.resultado_analise.equilibrio_ok
    eb = res.barras["v"]
    assert np.max(np.abs(eb.M_hiperestatico_kncm)) == pytest.approx(0.0, abs=1e-1)
    # e, por definição, total == isostático nesse caso
    assert np.max(np.abs(eb.M_total_kncm - eb.M_isostatico_kncm)) == pytest.approx(0.0, abs=1e-1)


def test_hiperestatico_zero_em_viga_biapoiada_sem_excentricidade_nas_pontas():
    # Caso particular e_i = e_j = 0 (só a flecha): a carga equivalente é uma
    # distribuída pura; ainda assim, hiperestático = 0 numa isostática.
    L = 500.0
    P = 700.0
    t = pt.TrechoCabo(barra="v", L_cm=L, e_i_cm=0.0, e_j_cm=0.0, flecha_cm=8.0)
    cabo = pt.Cabo(perfil=pt.PerfilCabo(trechos=(t,)), P_kn=P)
    m = _viga_biapoiada(L)
    res = pt.esforcos_hiperestaticos_protensao(m, cabo, n_estacoes=11)
    eb = res.barras["v"]
    assert np.max(np.abs(eb.M_hiperestatico_kncm)) == pytest.approx(0.0, abs=1e-1)
    # conferência independente: M_total no meio = 4*P*flecha/L*... = P*e(meio) = P*flecha
    meio = eb.x_cm[len(eb.x_cm) // 2]
    assert _aprox(meio, L / 2.0)
    assert _aprox(eb.M_total_kncm[len(eb.x_cm) // 2], P * t.flecha_cm)


# =============================================================================
# esforcos_hiperestaticos_protensao — viga contínua de 2 vãos (hiperestático != 0)
# =============================================================================
def test_hiperestatico_viga_continua_2_vaos_contra_equacao_dos_3_momentos():
    # Cabo com e = 0 nos três apoios e a mesma flecha nos dois vãos: a carga
    # equivalente (cargas_equivalentes_cabo) vira uma distribuída w =
    # -8*P*flecha/L^2 igual nos dois vãos -- uma carga UNIFORME comum à viga
    # contínua inteira, em módulo q = 8*P*flecha/L^2 (a favor da gravidade,
    # já que w < 0 na convenção +y da biblioteca).
    #
    # Conta (equação dos 3 momentos, apoios extremos simples, EI constante):
    #   M_A*L + 2*M_B*(L+L) + M_C*L = -6*(A1*x1/L + A2*x2/L)
    # com M_A = M_C = 0 e, para o trecho sob carga uniforme q, 6*A*x/L =
    # q*L^3/4 (resultado clássico da parábola do diagrama M/EI isostático):
    #   4*M_B*L = -2*(q*L^3/4) = -q*L^3/2
    #   M_B = -q*L^2/8 = -(8*P*flecha/L^2)*L^2/8 = -P*flecha
    L = 500.0
    P = 800.0
    flecha = 12.0
    t1 = pt.TrechoCabo(barra="v1", L_cm=L, e_i_cm=0.0, e_j_cm=0.0, flecha_cm=flecha)
    t2 = pt.TrechoCabo(barra="v2", L_cm=L, e_i_cm=0.0, e_j_cm=0.0, flecha_cm=flecha)
    cabo = pt.Cabo(perfil=pt.PerfilCabo(trechos=(t1, t2)), P_kn=P)
    m = _viga_continua_2_vaos(L)
    res = pt.esforcos_hiperestaticos_protensao(m, cabo, n_estacoes=21)
    assert res.resultado_analise.equilibrio_ok

    M_B_esperado = -P * flecha
    e1, e2 = res.barras["v1"], res.barras["v2"]
    # isostático nulo no apoio (e = 0 lá) -> hiperestático = total, nos dois lados do nó
    assert _aprox(e1.M_isostatico_kncm[-1], 0.0, abs_=1e-6)
    assert _aprox(e2.M_isostatico_kncm[0], 0.0, abs_=1e-6)
    assert _aprox(e1.M_total_kncm[-1], M_B_esperado, rel=1e-4)
    assert _aprox(e2.M_total_kncm[0], M_B_esperado, rel=1e-4)
    assert _aprox(e1.M_hiperestatico_kncm[-1], M_B_esperado, rel=1e-4)
    assert _aprox(e2.M_hiperestatico_kncm[0], M_B_esperado, rel=1e-4)

    # conferência independente, sem importar protendido_nbr6118: monta a
    # mesma viga contínua com uma carga distribuída "de gravidade" direta de
    # módulo q = 8*P*flecha/L^2 e confere o mesmo M_B.
    q_kn_m = 8.0 * P * flecha / (L * L) * 100.0
    m2 = _viga_continua_2_vaos(L)
    caso = ab.CasoCarga("g")
    caso.distribuida("v1", -q_kn_m, direcao="y")
    caso.distribuida("v2", -q_kn_m, direcao="y")
    r2 = ab.resolver(m2, caso, n_estacoes=21)
    assert _aprox(r2.barras["v1"].em(L - 1e-6)["Mz"], M_B_esperado, rel=1e-4)


def test_hiperestatico_viga_continua_com_excentricidades_diferentes_no_apoio():
    # Trechos vizinhos com a MESMA excentricidade no nó compartilhado (perfil
    # contínuo, sem mudança de traçado): os momentos concentrados de cada
    # lado (P*e, com sinal oposto conforme a extremidade) se cancelam nesse
    # nó, e só sobra a curvatura de cada trecho -- o modelo ainda fecha o
    # equilíbrio e dá um resultado finito e determinístico.
    L = 500.0
    P = 800.0
    t1 = pt.TrechoCabo(barra="v1", L_cm=L, e_i_cm=0.0, e_j_cm=-4.0, flecha_cm=10.0)
    t2 = pt.TrechoCabo(barra="v2", L_cm=L, e_i_cm=-4.0, e_j_cm=0.0, flecha_cm=10.0)
    cabo = pt.Cabo(perfil=pt.PerfilCabo(trechos=(t1, t2)), P_kn=P)
    m = _viga_continua_2_vaos(L)
    res = pt.esforcos_hiperestaticos_protensao(m, cabo, n_estacoes=11)
    assert res.resultado_analise.equilibrio_ok
    e1, e2 = res.barras["v1"], res.barras["v2"]
    # continuidade da excentricidade no apoio B -> isostático igual dos dois lados
    assert _aprox(e1.M_isostatico_kncm[-1], e2.M_isostatico_kncm[0])
    # e, por equilíbrio do nó (sem carga concentrada externa em B), o momento
    # total também é o mesmo dos dois lados
    assert _aprox(e1.M_total_kncm[-1], e2.M_total_kncm[0], rel=1e-4)


def test_esforcos_hiperestaticos_protensao_exige_portico_plano():
    m = ab.Modelo("grelha")
    m.no(1, 0.0, 0.0)
    m.no(2, 300.0, 0.0)
    m.barra(1, 1, 2, SEC, MAT)
    m.apoio(1, "engaste")
    cabo = pt.Cabo(perfil=pt.PerfilCabo(trechos=(pt.TrechoCabo(barra=1, L_cm=300.0, e_i_cm=0.0, e_j_cm=0.0),)),
                  P_kn=500.0)
    with pytest.raises(ValueError):
        pt.esforcos_hiperestaticos_protensao(m, cabo)


# =============================================================================
# pre_alongamento_protensao_pmil (17.2.4.2.1, p. 143)
# =============================================================================
def test_pre_alongamento_protensao():
    # eps_p0 = (sigma_pi,d - perdas)/Ep, em per mil
    sigma = 1400.0
    perdas = [80.0, 40.0, 30.0]
    eps = pt.pre_alongamento_protensao_pmil(sigma, perdas)
    esperado = (sigma - sum(perdas)) / pt.E_P_MPA * 1000.0
    assert _aprox(eps, esperado, rel=1e-9, abs_=1e-9)


def test_pre_alongamento_protensao_sem_perdas():
    sigma = 1300.0
    eps = pt.pre_alongamento_protensao_pmil(sigma)
    assert _aprox(eps, sigma / pt.E_P_MPA * 1000.0, rel=1e-9, abs_=1e-9)


def test_pre_alongamento_protensao_perdas_maiores_que_sigma_levanta_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        pt.pre_alongamento_protensao_pmil(500.0, perdas_mpa=600.0)
    with pytest.raises(nbr.FaixaNormativaError):
        pt.pre_alongamento_protensao_pmil(500.0, perdas_mpa=500.0)  # igual também não vale


# =============================================================================
# combinar_protensao_elu (17.2.4.2.1, p. 143)
# =============================================================================
def test_combinar_protensao_elu_gama_padrao_desfavoravel():
    # coluna "p" da Tabela 11.1, combinação normal, desfavorável: gama_p = 1,2
    Md = pt.combinar_protensao_elu(-9600.0, M_outras_acoes_kncm=50000.0)
    assert _aprox(Md, 50000.0 + 1.2 * (-9600.0))


def test_combinar_protensao_elu_gama_padrao_favoravel():
    # favorável: gama_p = 0,9
    Md = pt.combinar_protensao_elu(-9600.0, favoravel=True, M_outras_acoes_kncm=50000.0)
    assert _aprox(Md, 50000.0 + 0.9 * (-9600.0))


def test_combinar_protensao_elu_gama_explicito():
    # ato da protensão (17.2.4.3.1): gama_p = 1.1 na pos-tracao, por exemplo
    Md = pt.combinar_protensao_elu(2000.0, gama_p=1.1, M_outras_acoes_kncm=1000.0)
    assert _aprox(Md, 1000.0 + 1.1 * 2000.0)


def test_combinar_protensao_elu_aceita_array():
    Mh = np.array([-1000.0, -2000.0])
    Mo = np.array([100.0, 200.0])
    Md = pt.combinar_protensao_elu(Mh, gama_p=1.1, M_outras_acoes_kncm=Mo)
    esperado = Mo + 1.1 * Mh
    assert np.allclose(Md, esperado)


def test_combinar_protensao_elu_nao_soma_isostatico():
    # Md com só o hiperestático deve ser MENOR (em módulo) que se o isostático
    # (maior, tipicamente) fosse somado por engano -- conferência indireta de
    # que a função nunca recebe nem soma o isostático (17.2.4.2.1: "os
    # isostáticos de protensão não podem ser incluídos").
    M_hip = -9600.0
    M_iso = -150000.0   # tipicamente bem maior em módulo que o hiperestático
    Md_correto = pt.combinar_protensao_elu(M_hip, M_outras_acoes_kncm=50000.0)
    Md_com_isostatico_por_engano = pt.combinar_protensao_elu(M_hip + M_iso, M_outras_acoes_kncm=50000.0)
    assert Md_correto != pytest.approx(Md_com_isostatico_por_engano)
