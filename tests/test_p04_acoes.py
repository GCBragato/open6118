"""Testes do P4 — ações e combinações (NBR 6118:2026, Seção 11 e 15.3.1).

Os valores esperados saem das Tabelas 11.1 a 11.4 e do texto da norma (página
do PDF indicada em cada teste). As contas à mão estão nos comentários.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import acoes_nbr6118 as ac  # noqa: E402

TOL = 1e-12


def G(Fk=100.0, **kw):
    return ac.Acao("Peso próprio", "permanente_direta", "permanente", Fk, **kw)


def Q(Fk=50.0, cat="com_predominancia", nome="Sobrecarga", **kw):
    return ac.Acao(nome, "variavel_direta", "variavel", Fk, categoria_psi=cat, **kw)


def W(Fk=30.0, **kw):
    return ac.Acao("Vento", "variavel_direta", "variavel", Fk, categoria_psi="vento", **kw)


# --- 11.2.2 classificação das ações (p. 76) -----------------------------------
def test_peso_proprio_classificado_como_permanente():
    g = G()
    assert ac.classificar_acao(g) == "permanente"
    assert g.natureza == "permanente_direta" and g.tipo == "permanente"


@pytest.mark.parametrize("natureza,tipo,esperado", [
    ("permanente_indireta", "retracao", "permanente"),
    ("permanente indireta", "protensao", "permanente"),
    ("variavel_direta", "variavel", "variavel"),
    ("variável indireta", "temperatura", "variavel"),
    ("excepcional", "excepcional", "excepcional"),
])
def test_classificacao_das_naturezas(natureza, tipo, esperado):
    kw = {"categoria_psi": "vento"} if natureza.startswith("variavel_d") else {}
    a = ac.Acao("A", natureza, tipo, 1.0, **kw)
    assert ac.classificar_acao(a) == esperado


def test_tipo_incompativel_com_natureza_levanta():
    with pytest.raises(ValueError):
        ac.Acao("X", "permanente_direta", "variavel", 1.0)
    with pytest.raises(ValueError):
        ac.Acao("X", "variavel_direta", "temperatura", 1.0, categoria_psi="vento")


def test_variavel_sem_categoria_psi_levanta_e_temperatura_assume_a_sua():
    with pytest.raises(ValueError):
        ac.Acao("Q", "variavel_direta", "variavel", 1.0)
    t = ac.Acao("T", "variavel_indireta", "temperatura", 1.0)
    assert t.psi == (0.6, 0.5, 0.3)


def test_fk_inf_so_em_permanente():
    with pytest.raises(ValueError):
        Q(Fk_inf=10.0)


# --- 11.7.1 Tabela 11.1 (p. 85), todas as células ------------------------------
@pytest.mark.parametrize("comb,coluna,sub,esperado", [
    ("normal", "permanente", "D", 1.4), ("normal", "permanente", "F", 1.0),
    ("normal", "variavel", "G", 1.4), ("normal", "variavel", "T", 1.2),
    ("normal", "protensao", "D", 1.2), ("normal", "protensao", "F", 0.9),
    ("normal", "recalque_retracao", "D", 1.2), ("normal", "recalque_retracao", "F", 0.0),
    ("especial", "permanente", "D", 1.3), ("especial", "permanente", "F", 1.0),
    ("especial", "variavel", "G", 1.2), ("especial", "variavel", "T", 1.0),
    ("especial", "protensao", "D", 1.2), ("especial", "protensao", "F", 0.9),
    ("especial", "recalque_retracao", "D", 1.2), ("especial", "recalque_retracao", "F", 0.0),
    ("excepcional", "permanente", "D", 1.2), ("excepcional", "permanente", "F", 1.0),
    ("excepcional", "variavel", "G", 1.0), ("excepcional", "variavel", "T", 0.0),
    ("excepcional", "protensao", "D", 1.2), ("excepcional", "protensao", "F", 0.9),
    ("excepcional", "recalque_retracao", "D", 0.0), ("excepcional", "recalque_retracao", "F", 0.0),
])
def test_tabela_11_1_celula(comb, coluna, sub, esperado):
    assert ac.gama_f_tabela_11_1(comb, coluna, sub) == esperado


def test_tabela_11_1_construcao_e_a_mesma_linha_de_especial():
    assert ac.gama_f_tabela_11_1("construcao", "permanente", "D") == 1.3
    assert ac.gama_f_tabela_11_1("de construção", "variavel", "G") == 1.2


def test_tabela_11_1_subcoluna_inexistente_levanta():
    with pytest.raises(ValueError):
        ac.gama_f_tabela_11_1("normal", "variavel", "D")
    with pytest.raises(ValueError):
        ac.gama_f_tabela_11_1("normal", "permanente", "G")


# --- Tabela 11.1, nota a: γg configurável (decisão 3) ------------------------
def test_gama_g_padrao_lido_do_nucleo():
    assert nbr.GAMA_G == 1.4 and nbr.GAMA_F == 1.4
    assert ac.gama_f(G(), "normal", favoravel=False) == 1.4


def test_gama_g_lido_na_hora_da_chamada(monkeypatch):
    monkeypatch.setattr(nbr, "GAMA_G", 1.3)
    assert ac.nbr is nbr
    assert ac.gama_f(G(), "normal", favoravel=False) == 1.3
    assert ac.gama_f_tabela_11_1("normal", "permanente", "D") == 1.3
    # A nota a só atinge a célula normal × permanente × D.
    assert ac.gama_f_tabela_11_1("especial", "permanente", "D") == 1.3
    assert ac.gama_f_tabela_11_1("excepcional", "permanente", "D") == 1.2
    assert ac.gama_f(Q(), "normal", favoravel=False) == 1.4


@pytest.mark.parametrize("g", [1.29, 1.41, 1.0, 1.5])
def test_gama_g_fora_da_nota_a_levanta(g):
    with pytest.raises(nbr.FaixaNormativaError):
        ac.gama_g_configurado(g)


@pytest.mark.parametrize("g", [1.3, 1.35, 1.4])
def test_gama_g_dentro_da_nota_a(g):
    assert ac.gama_g_configurado(g) == g


def test_gama_f_dos_modulos_vem_do_nucleo():
    import blocos_nbr6118, cortante_nbr6118, lajes_nbr6118, sapatas_nbr6118, vigas_nbr6118
    for m in (blocos_nbr6118, cortante_nbr6118, lajes_nbr6118, sapatas_nbr6118, vigas_nbr6118):
        assert m.GAMA_F == nbr.GAMA_F == 1.4


# --- gama_f por ação (Tabela 11.1) ------------------------------------------
def test_gama_f_por_tipo_de_acao():
    T = ac.Acao("T", "variavel_indireta", "temperatura", 1.0)
    P = ac.Acao("P", "permanente_indireta", "protensao", 1.0)
    R = ac.Acao("R", "permanente_indireta", "recalque_retracao", 1.0)
    E = ac.Acao("E", "excepcional", "excepcional", 1.0)
    assert ac.gama_f(T, "normal", False) == 1.2
    assert ac.gama_f(P, "normal", True) == 0.9
    assert ac.gama_f(R, "especial", False) == 1.2
    assert ac.gama_f(R, "excepcional", False) == 0.0
    assert ac.gama_f(Q(), "normal", True) == 0.0      # variável favorável não entra
    assert ac.gama_f(E, "excepcional", False) == 1.0
    with pytest.raises(nbr.FaixaNormativaError):
        ac.gama_f(E, "normal", False)


# --- 11.7.1 Tabela 11.2 (p. 85), todas as células ------------------------------
@pytest.mark.parametrize("cat,esperado", [
    ("sem_predominancia", (0.5, 0.4, 0.3)),
    ("com_predominancia", (0.7, 0.6, 0.4)),
    ("biblioteca_arquivo_oficina_garagem", (0.8, 0.7, 0.6)),
    ("vento", (0.6, 0.3, 0.0)),
    ("temperatura", (0.6, 0.5, 0.3)),
])
def test_tabela_11_2_linha(cat, esperado):
    assert ac.psi(cat) == esperado
    assert ac.TABELA_11_2_PSI[cat] == esperado


@pytest.mark.parametrize("apelido,cat", [
    ("residencial", "sem_predominancia"), ("hospedagem", "sem_predominancia"),
    ("escritório", "com_predominancia"), ("acesso público", "com_predominancia"),
    ("garagem", "biblioteca_arquivo_oficina_garagem"),
    ("Biblioteca", "biblioteca_arquivo_oficina_garagem"),
])
def test_tabela_11_2_apelidos_das_notas(apelido, cat):
    assert ac.psi(apelido) == ac.TABELA_11_2_PSI[cat]


def test_psi_explicito_e_invalido():
    assert ac.psi((0.7, 0.6, 0.4)) == (0.7, 0.6, 0.4)
    with pytest.raises(nbr.FaixaNormativaError):
        ac.psi((1.2, 0.6, 0.4))
    with pytest.raises(ValueError):
        ac.psi("hangar")
    with pytest.raises(ValueError):
        ac.psi((0.5, 0.4))


# --- 11.7 decomposição (p. 84) e 11.7.2 γf no ELS (p. 86) -----------------------
def test_gama_f_composto_e_gama_f1():
    assert ac.gama_f_composto(1.4 / 1.1, 0.6, 1.1) == pytest.approx(0.84, abs=TOL)
    # γf1 = (γf1·γf3)/γf3 = 1,4/1,1
    assert ac.gama_f1(1.4) == pytest.approx(1.4 / 1.1, abs=TOL)
    assert ac.GAMA_F3 == nbr.GAMA_F3 == 1.1


def test_gama_f_els():
    assert ac.gama_f_els("rara") == 1.0
    assert ac.gama_f_els("frequente", "com_predominancia") == 0.6
    assert ac.gama_f_els("quase permanente", "com_predominancia") == 0.4
    assert ac.gama_f_els("CQP", "vento") == 0.0
    with pytest.raises(ValueError):
        ac.gama_f_els("frequente")


# --- 11.6.2 valores representativos e 11.6.3 valores de cálculo (p. 84) ------
def test_valor_representativo():
    q = Q(100.0, cat="sem_predominancia")        # ψ = 0,5 / 0,4 / 0,3
    assert ac.valor_representativo(q) == 100.0
    assert ac.valor_representativo(q, "combinacao") == pytest.approx(50.0, abs=TOL)
    assert ac.valor_representativo(q, "frequente") == pytest.approx(40.0, abs=TOL)
    assert ac.valor_representativo(q, "quase_permanente") == pytest.approx(30.0, abs=TOL)
    g = G(100.0, Fk_inf=90.0)
    assert ac.valor_representativo(g, "caracteristico_inferior") == 90.0
    with pytest.raises(nbr.FaixaNormativaError):
        ac.valor_representativo(g, "combinacao")
    E = ac.Acao("Impacto", "excepcional", "excepcional", 80.0)
    assert ac.valor_representativo(E, "excepcional") == 80.0
    with pytest.raises(nbr.FaixaNormativaError):
        ac.valor_representativo(g, "excepcional")


def test_valor_calculo():
    assert ac.valor_calculo(100.0, 1.4) == pytest.approx(140.0, abs=TOL)
    with pytest.raises(ValueError):
        ac.valor_calculo(100.0, -1.0)


# --- 11.8.2.1 combinação última normal (Tabela 11.3, p. 87) ---------------------
def test_combinacao_normal_duas_variaveis_a_mao():
    # G = 100; Q = 50 (ψ0 = 0,7); W = 30 (ψ0 = 0,6); γg = γq = 1,4.
    # Q principal: 1,4·100 + 1,4·(50 + 0,6·30) = 140 + 95,2 = 235,2
    # W principal: 1,4·100 + 1,4·(30 + 0,7·50) = 140 + 91,0 = 231,0
    r = ac.combinacao_ultima([G(), Q(), W()])
    assert r.Fd == pytest.approx(235.2, abs=1e-9)
    assert r.principal == r.governante == "Sobrecarga"
    alt = dict(r.alternativas)
    assert alt["Sobrecarga"] == pytest.approx(235.2, abs=1e-9)
    assert alt["Vento"] == pytest.approx(231.0, abs=1e-9)
    assert r.gama_g == 1.4
    assert any("γg = 1,4 (nucleo_nbr6118.GAMA_G" in l for l in r.memoria)
    assert any("Varredura" in l for l in r.memoria)


def test_combinacao_normal_principal_explicito():
    r = ac.combinacao_ultima([G(), Q(), W()], principal="Vento")
    assert r.Fd == pytest.approx(231.0, abs=1e-9)
    assert r.alternativas == (("Vento", r.Fd),)


def test_combinacao_normal_com_indiretas():
    # + retração 10 (γεg = 1,2) + temperatura 20 (γεq·ψ0ε = 1,2·0,6):
    # 235,2 + 12 + 14,4 = 261,6
    R = ac.Acao("Retração", "permanente_indireta", "retracao", 10.0)
    T = ac.Acao("Temperatura", "variavel_indireta", "temperatura", 20.0)
    r = ac.combinacao_ultima([G(), Q(), W(), R, T])
    assert r.Fd == pytest.approx(261.6, abs=1e-9)
    assert r.principal == "Sobrecarga"
    with pytest.raises(nbr.FaixaNormativaError):
        ac.combinacao_ultima([G(), Q(), T], principal="Temperatura")


def test_gama_g_1_3_no_comeco_do_script_muda_a_combinacao(monkeypatch):
    # nucleo.GAMA_G = 1,3: 1,3·100 + 1,4·(50 + 0,6·30) = 130 + 95,2 = 225,2
    monkeypatch.setattr(nbr, "GAMA_G", 1.3)
    r = ac.combinacao_ultima([G(), Q(), W()])
    assert r.Fd == pytest.approx(225.2, abs=1e-9)
    assert r.gama_g == 1.3
    assert any("γg = 1,3 (nucleo_nbr6118.GAMA_G" in l for l in r.memoria)


def test_gama_g_explicito_prevalece_e_fica_na_memoria(monkeypatch):
    monkeypatch.setattr(nbr, "GAMA_G", 1.3)
    r = ac.combinacao_ultima([G(), Q(), W()], gama_g=1.4)
    assert r.Fd == pytest.approx(235.2, abs=1e-9)
    assert any("γg = 1,4 (argumento gama_g" in l for l in r.memoria)


def test_combinacao_normal_so_permanente():
    r = ac.combinacao_ultima([G()])
    assert r.Fd == pytest.approx(140.0, abs=TOL)
    assert r.principal == ""


def test_combinacao_minima_permanente_favoravel_usa_fk_inf():
    # sentido 'min': G favorável → 1,0·Fk,inf = 90; Q favorável não entra.
    r = ac.combinacao_ultima([G(100.0, Fk_inf=90.0), Q()], sentido="min")
    assert r.Fd == pytest.approx(90.0, abs=TOL)
    assert [p.papel for p in r.parcelas] == ["permanente", "excluida"]


def test_protensao_pkmax_pkmin():
    # Efeito da protensão: Pk,máx → −200, Pk,mín → −180; G = 100.
    # max: P favorável 0,9·(−180) = −162; G 1,4·100 = 140 → −22
    # min: P desfavorável 1,2·(−200) = −240; G favorável 1,0·100 → −140
    P = ac.Acao("Protensão", "permanente_indireta", "protensao", -200.0, Fk_inf=-180.0)
    assert ac.combinacao_ultima([G(), P]).Fd == pytest.approx(-22.0, abs=1e-9)
    assert ac.combinacao_ultima([G(), P], sentido="min").Fd == pytest.approx(-140.0, abs=1e-9)


def test_favoravel_explicito():
    # Vento marcado favorável: fica fora; Q principal 1,4·(100 + 50) = 210
    r = ac.combinacao_ultima([G(), Q(), W(favoravel=True)])
    assert r.Fd == pytest.approx(210.0, abs=1e-9)


# --- 11.8.2.2 especial ou de construção (Tabela 11.3, p. 87) ---------------------
def test_combinacao_especial():
    # Q principal: 1,3·100 + 1,2·(50 + 0,6·30) = 130 + 81,6 = 211,6
    # W principal: 1,3·100 + 1,2·(30 + 0,7·50) = 130 + 78,0 = 208,0
    r = ac.combinacao_ultima([G(), Q(), W()], tipo="especial")
    assert r.Fd == pytest.approx(211.6, abs=1e-9)
    assert ac.combinacao_ultima([G(), Q(), W()], tipo="construcao").Fd == pytest.approx(211.6, abs=1e-9)
    # Nota b: ψ0j → ψ2j. Q principal: 130 + 1,2·(50 + 0·30) = 190;
    # W principal: 130 + 1,2·(30 + 0,4·50) = 190 (empate) → 190
    rb = ac.combinacao_ultima([G(), Q(), W()], tipo="especial", psi2_nota_b=True)
    assert rb.Fd == pytest.approx(190.0, abs=1e-9)


def test_nota_b_nao_vale_na_normal():
    with pytest.raises(ValueError):
        ac.combinacao_ultima([G(), Q()], psi2_nota_b=True)


# --- 11.5 e 11.8.2.3 excepcional (Tabela 11.3, p. 83 e 87) -------------------------
def test_combinacao_excepcional():
    # 1,2·100 + 80 + 1,0·0,7·50 + 0·0,6·20 = 120 + 80 + 35 + 0 = 235
    E = ac.Acao("Impacto", "excepcional", "excepcional", 80.0)
    T = ac.Acao("Temperatura", "variavel_indireta", "temperatura", 20.0)
    r = ac.combinacao_ultima([G(), Q(), E, T], tipo="excepcional")
    assert r.Fd == pytest.approx(235.0, abs=1e-9)
    assert r.principal == "Impacto"
    # Nota b: ψ2 = 0,4 → 120 + 80 + 20 = 220
    rb = ac.combinacao_ultima([G(), Q(), E, T], tipo="excepcional", psi2_nota_b=True)
    assert rb.Fd == pytest.approx(220.0, abs=1e-9)


def test_excepcionais_uma_de_cada_vez():
    # E1 = 80, E2 = 120: governa E2 → 120 + 120 + 35 = 275
    E1 = ac.Acao("E1", "excepcional", "excepcional", 80.0)
    E2 = ac.Acao("E2", "excepcional", "excepcional", 120.0)
    r = ac.combinacao_ultima([G(), Q(), E1, E2], tipo="excepcional")
    assert r.Fd == pytest.approx(275.0, abs=1e-9)
    assert dict(r.alternativas) == pytest.approx({"E1": 235.0, "E2": 275.0})
    with pytest.raises(nbr.FaixaNormativaError):
        ac.combinacao_ultima([G(), Q(), E1], tipo="excepcional", principal="Sobrecarga")


def test_excepcional_fora_da_combinacao_normal():
    E = ac.Acao("Impacto", "excepcional", "excepcional", 80.0)
    r = ac.combinacao_ultima([G(), Q(), E])
    assert r.Fd == pytest.approx(140.0 + 70.0, abs=1e-9)


# --- 11.8.3.2 combinações de serviço (Tabela 11.4, p. 89) --------------------------
def test_combinacao_quase_permanente():
    # 100 + 0,4·50 + 0·30 = 120
    r = ac.combinacao_servico([G(), Q(), W()], "quase_permanente")
    assert r.Fd == pytest.approx(120.0, abs=1e-9)
    assert r.estado == "ELS" and r.principal == ""
    with pytest.raises(ValueError):
        ac.combinacao_servico([G(), Q()], "quase_permanente", principal="Sobrecarga")


def test_combinacao_frequente():
    # Q principal: 100 + 0,6·50 + 0·30 = 130; W principal: 100 + 0,3·30 + 0,4·50 = 129
    r = ac.combinacao_servico([G(), Q(), W()], "frequente")
    assert r.Fd == pytest.approx(130.0, abs=1e-9)
    assert r.principal == "Sobrecarga"
    assert dict(r.alternativas)["Vento"] == pytest.approx(129.0, abs=1e-9)


def test_combinacao_rara_governa_o_vento():
    # Q principal: 100 + 50 + 0,3·30 = 159; W principal: 100 + 30 + 0,6·50 = 160
    r = ac.combinacao_servico([G(), Q(), W()], "rara")
    assert r.Fd == pytest.approx(160.0, abs=1e-9)
    assert r.governante == "Vento"
    assert dict(r.alternativas)["Sobrecarga"] == pytest.approx(159.0, abs=1e-9)


def test_servico_permanentes_com_gama_1_e_temperatura_reduzida():
    # CQP com retração 10 e temperatura 20 (ψ2 = 0,3): 100 + 10 + 0,4·50 + 6 = 136
    R = ac.Acao("Retração", "permanente_indireta", "retracao", 10.0)
    T = ac.Acao("Temperatura", "variavel_indireta", "temperatura", 20.0)
    r = ac.combinacao_servico([G(), R, Q(), T], "CQP")
    assert r.Fd == pytest.approx(136.0, abs=1e-9)


# --- 15.3.1 Sd,tot (p. 121) -------------------------------------------------------
def test_sdtot_uma_variavel_linear():
    # Uma variável (sem ψ0j): Sd,tot = γf3·(γf/γf3)·(Fgk + Fq1k) = 1,4·150 = 210
    r = ac.combinacao_2a_ordem_sdtot([G(), Q()])
    assert r.Sd_tot == pytest.approx(210.0, abs=1e-9)
    assert r.F == pytest.approx(210.0 / 1.1, abs=1e-9)
    assert r.gama_f3 == 1.1


def test_sdtot_com_analise_nao_linear():
    # F = 210/1,1; S(F) = F·(1 + F/1000); Sd,tot = 1,1·S(F)
    F = 210.0 / 1.1
    esperado = 1.1 * F * (1.0 + F / 1000.0)
    r = ac.combinacao_2a_ordem_sdtot([G(), Q()], S=lambda f: f * (1.0 + f / 1000.0))
    assert r.Sd_tot == pytest.approx(esperado, abs=1e-9)
    assert ac.sd_tot_2a_ordem(100.0) == pytest.approx(110.0, abs=TOL)


def test_sdtot_varre_a_principal():
    r = ac.combinacao_2a_ordem_sdtot([G(), Q(), W()])
    assert r.Sd_tot == pytest.approx(235.2, abs=1e-9)
    assert r.principal == "Sobrecarga"


# --- 11.4.1.3 ação da água (p. 82) -------------------------------------------------
def test_acao_agua():
    A = ac.acao_agua("Água do reservatório", 100.0)
    assert ac.gama_f(A, "normal", False) == 1.2
    assert ac.gama_f(A, "especial", False) == 1.2
    assert ac.combinacao_ultima([A]).Fd == pytest.approx(120.0, abs=1e-9)
    assert ac.combinacao_ultima([A], sentido="min").Fd == pytest.approx(100.0, abs=1e-9)
    with pytest.raises(ValueError):
        ac.acao_agua("Chuva retida", 10.0, permanente=False)
    Av = ac.acao_agua("Chuva retida", 10.0, permanente=False, categoria_psi=(0.5, 0.4, 0.3))
    # Variável secundária: 1,2·0,5·10 = 6; G 140 + Q 70 → 216
    assert ac.combinacao_ultima([G(), Q(), Av], principal="Sobrecarga").Fd == pytest.approx(216.0, abs=1e-9)


# --- 11.4.2.1 temperatura uniforme (p. 82-83) --------------------------------------
@pytest.mark.parametrize("h,esperado", [
    (20.0, (10.0, 15.0)),
    (50.0, (10.0, 15.0)),     # a) não superior a 50 cm
    (55.0, (8.75, 13.75)),    # c) t = 0,25
    (60.0, (7.5, 12.5)),      # c) meio da faixa
    (70.0, (5.0, 10.0)),      # continuidade com b)
    (70.01, (5.0, 10.0)),     # b) superior a 70 cm
    (120.0, (5.0, 10.0)),
])
def test_temperatura_uniforme(h, esperado):
    lo, hi = ac.variacao_temperatura_uniforme(h)
    assert lo == pytest.approx(esperado[0], abs=1e-12)
    assert hi == pytest.approx(esperado[1], abs=1e-12)


def test_temperatura_uniforme_continua_perto_de_50():
    lo, hi = ac.variacao_temperatura_uniforme(50.0 + 1e-9)
    assert lo == pytest.approx(10.0, abs=1e-6) and hi == pytest.approx(15.0, abs=1e-6)


def test_temperatura_uniforme_elemento_nao_macico_fica_na_alinea_a():
    assert ac.variacao_temperatura_uniforme(80.0, macico_ou_oco_fechado=False) == (10.0, 15.0)


def test_temperatura_uniforme_dimensao_invalida():
    with pytest.raises(nbr.FaixaNormativaError):
        ac.variacao_temperatura_uniforme(0.0)


@pytest.mark.parametrize("tv,ti,esperado", [
    (28.0, 14.0, 10.0),   # 0,5·14 = 7 → limitado a 10
    (40.0, 14.0, 13.0),   # 0,5·26 = 13
    (50.0, 10.0, 15.0),   # 0,5·40 = 20 → limitado a 15
])
def test_temperatura_adotada(tv, ti, esperado):
    assert ac.variacao_temperatura_adotada_c(30.0, tv, ti) == pytest.approx(esperado, abs=TOL)


# --- 11.4.2.2 temperatura não uniforme (p. 83) --------------------------------------
def test_gradiente_minimo():
    assert ac.GRADIENTE_TERMICO_MIN_C == 5
    assert ac.diferenca_temperatura_faces_c() == 5.0
    assert ac.diferenca_temperatura_faces_c(3.0) == 5.0
    assert ac.diferenca_temperatura_faces_c(5.0) == 5.0
    assert ac.diferenca_temperatura_faces_c(8.0) == 8.0


def test_temperatura_linear_entre_faces():
    assert ac.temperatura_linear_c(20.0, 30.0, 5.0, 10.0) == pytest.approx(25.0, abs=TOL)
    assert ac.temperatura_linear_c(20.0, 25.0, 10.0, 10.0) == pytest.approx(25.0, abs=TOL)
    with pytest.raises(nbr.FaixaNormativaError):
        ac.temperatura_linear_c(20.0, 24.0, 5.0, 10.0)
    with pytest.raises(nbr.FaixaNormativaError):
        ac.temperatura_linear_c(20.0, 30.0, 11.0, 10.0)


# --- memória em português --------------------------------------------------------
def test_memoria_cita_item_e_formula():
    r = ac.combinacao_ultima([G(), Q(), W()])
    texto = "\n".join(r.memoria)
    assert "11.8.2.1" in texto and "Tabela 11.3" in texto
    assert "Fd = γg·Fgk" in texto
    assert "Sobrecarga (variável principal, desfavorável): 1,4 × 50 = 70" in texto
    assert "Vento (variável secundária, desfavorável): 1,4 × 0,6 × 30 = 25,2" in texto
    assert not math.isnan(r.Fd)


# --- Correções da verificação (volta 1) ----------------------------------------
def test_sdtot_com_acoes_indiretas_divide_cada_termo_pelo_proprio_gama():
    # 15.3.1 (p. 121) remete a combinação e os γf à Seção 11 (Tabela 11.3, normal):
    # F = (1,4/1,1)·100 + (1,4/1,1)·50 + (1,2/1,1)·0,6·20 + (1,2/1,1)·30
    #   = (140 + 70 + 14,4 + 36)/1,1 = 260,4/1,1
    T = ac.Acao("Temperatura", "variavel_indireta", "temperatura", 20.0)
    P = ac.Acao("Protensão", "permanente_indireta", "protensao", 30.0)
    r = ac.combinacao_2a_ordem_sdtot([G(), Q(), T, P], principal="Sobrecarga")
    termo_a_termo = (1.4 / 1.1) * 100.0 + (1.4 / 1.1) * 50.0 \
        + (1.2 / 1.1) * 0.6 * 20.0 + (1.2 / 1.1) * 30.0
    assert r.F == pytest.approx(termo_a_termo, abs=1e-9)
    assert r.Sd_tot == pytest.approx(260.4, abs=1e-9)
    # Com γf único de 1,4 o valor seria outro (1,4·(100 + 50 + 0,6·20 + 30)/1,1):
    assert r.F != pytest.approx(1.4 * 192.0 / 1.1, abs=1e-6)


def test_gama_f2_principal_governa_a_principal_da_combinacao_rara(monkeypatch):
    # 11.6.2 a): a principal da CR entra com γf2 = 1 (Fq1k). A constante é a fonte.
    base = ac.combinacao_servico([G(), Q()], "rara").Fd
    assert base == pytest.approx(150.0, abs=1e-9)
    monkeypatch.setattr(ac, "GAMA_F2_PRINCIPAL", 2.0)
    assert ac.combinacao_servico([G(), Q()], "rara").Fd == pytest.approx(200.0, abs=1e-9)


def test_resultados_de_combinacao_documentam_ausencia_de_ok():
    for cls in (ac.ResultadoCombinacao, ac.ResultadoSdTot):
        assert "ok" not in cls.__dataclass_fields__
        assert "Não há campo ``ok``" in cls.__doc__ or "Sem campo ``ok``" in cls.__doc__
