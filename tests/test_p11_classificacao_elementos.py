"""Testes do P11 — classificação de elementos (NBR 6118:2026, Seções 14, 18 e 22).

Casos-limite exatos citados no plano: l/h = 2,0 e 3,0 (viga x viga-parede),
razão 5:1 no pilar, e h = vão/3 na placa. As contas estão nos comentários.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import classificacao_elementos_nbr6118 as ce  # noqa: E402


# --- 14.4.1 — elemento linear x de superfície (PDF p. 104) -------------------
def test_elemento_linear_caso_limite_igual_a_3():
    # l = 3*h exatamente -> ainda linear (limite inclusivo, >=)
    r = ce.eh_elemento_linear(l_cm=90.0, h_max_cm=30.0)
    assert r.razao == pytest.approx(3.0)
    assert r.linear is True
    assert r.governante == "14.4.1"


def test_elemento_linear_abaixo_do_limite_e_de_superficie():
    r = ce.eh_elemento_linear(l_cm=89.9, h_max_cm=30.0)
    assert r.linear is False


def test_elemento_linear_acima_do_limite():
    r = ce.eh_elemento_linear(l_cm=300.0, h_max_cm=30.0)
    assert r.linear is True


def test_elemento_linear_entrada_invalida_levanta():
    with pytest.raises(ValueError):
        ce.eh_elemento_linear(l_cm=0.0, h_max_cm=30.0)
    with pytest.raises(ValueError):
        ce.eh_elemento_linear(l_cm=90.0, h_max_cm=-1.0)


# --- 14.4.2.1 — placa espessa (PDF p. 104) -----------------------------------
def test_placa_caso_limite_h_igual_vao_sobre_3():
    # h = vao/3 exatamente -> ainda placa usual (limite exclusivo, >)
    r = ce.eh_placa_espessa(h_cm=100.0, vao_cm=300.0)
    assert r.limite == pytest.approx(100.0)
    assert r.espessa is False


def test_placa_espessa_acima_do_limite():
    r = ce.eh_placa_espessa(h_cm=100.01, vao_cm=300.0)
    assert r.espessa is True


def test_placa_bem_abaixo_do_limite():
    r = ce.eh_placa_espessa(h_cm=20.0, vao_cm=300.0)
    assert r.espessa is False


# --- 14.4.2.4/18.4.1 — pilar x pilar-parede (PDF p. 105 e 173) ---------------
def test_pilar_caso_limite_razao_5():
    # Secao 20x100 cm: razao = 5,0 -> pilar comum (limite inclusivo, <=)
    r = ce.eh_pilar_parede(b_cm=20.0, h_cm=100.0)
    assert r.razao == pytest.approx(5.0)
    assert r.pilar_parede is False
    assert r.governante == "14.4.2.4/18.4.1"


def test_pilar_acima_do_limite_e_parede():
    # Secao 20x101 cm: razao = 5,05 -> pilar-parede
    r = ce.eh_pilar_parede(b_cm=20.0, h_cm=101.0)
    assert r.razao == pytest.approx(5.05)
    assert r.pilar_parede is True


def test_pilar_ordem_dos_argumentos_e_livre():
    r1 = ce.eh_pilar_parede(b_cm=20.0, h_cm=100.0)
    r2 = ce.eh_pilar_parede(b_cm=100.0, h_cm=20.0)
    assert r1.dimensao_maior_cm == r2.dimensao_maior_cm == 100.0
    assert r1.dimensao_menor_cm == r2.dimensao_menor_cm == 20.0
    assert r1.pilar_parede == r2.pilar_parede


def test_pilar_quadrado_nunca_e_parede():
    r = ce.eh_pilar_parede(b_cm=40.0, h_cm=40.0)
    assert r.razao == pytest.approx(1.0)
    assert r.pilar_parede is False


# --- 14.4.2.2/18.3.1/22.4.1 — viga x viga-parede (PDF p. 104-105, 167, 204) --
def test_viga_isostatica_caso_limite_l_sobre_h_2():
    # l/h = 2,0 exatamente, isostatica -> viga comum (18.3.1 aplica-se, >=2,0)
    r = ce.eh_viga_parede(l_cm=600.0, h_cm=300.0, continua=False)
    assert r.razao == pytest.approx(2.0)
    assert r.viga_parede is False
    assert r.governante == "18.3.1/22.4.1"


def test_viga_isostatica_abaixo_do_limite_2_e_parede():
    # l/h = 1,9 biapoiada -> viga-parede (do teste sugerido no brief)
    r = ce.eh_viga_parede(l_cm=1.9 * 100.0, h_cm=100.0, continua=False)
    assert r.razao == pytest.approx(1.9)
    assert r.viga_parede is True


def test_viga_isostatica_acima_do_limite_2_e_usual():
    # l/h = 2,1 biapoiada -> viga usual
    r = ce.eh_viga_parede(l_cm=2.1 * 100.0, h_cm=100.0, continua=False)
    assert r.viga_parede is False


def test_viga_continua_caso_limite_l_sobre_h_3():
    # l/h = 3,0 exatamente, continua -> viga comum (18.3.1 aplica-se, >=3,0)
    r = ce.eh_viga_parede(l_cm=900.0, h_cm=300.0, continua=True)
    assert r.razao == pytest.approx(3.0)
    assert r.viga_parede is False


def test_viga_continua_abaixo_do_limite_3_e_parede():
    # l/h = 2,9 continua -> viga-parede (do teste sugerido no brief)
    r = ce.eh_viga_parede(l_cm=2.9 * 100.0, h_cm=100.0, continua=True)
    assert r.viga_parede is True


def test_viga_continua_de_6m_altura_2_5m_do_teste_sugerido_18_3_1():
    # l=6m, h=2,5m, continua -> l/h = 2,4 < 3,0 -> viga-parede
    r = ce.eh_viga_parede(l_cm=600.0, h_cm=250.0, continua=True)
    assert r.razao == pytest.approx(2.4)
    assert r.viga_parede is True
    # a mesma secao isostatica: l/h = 2,4 >= 2,0 -> viga comum
    r2 = ce.eh_viga_parede(l_cm=600.0, h_cm=250.0, continua=False)
    assert r2.viga_parede is False


def test_viga_divergencia_entre_regra_geral_e_especifica():
    # l/h = 2,5, isostatica: 14.4.2.2 (regra geral, <3,0) marcaria
    # viga-parede, mas 18.3.1/22.4.1 (regra especifica, isostatica >=2,0)
    # nao marca -> prevalece a regra especifica, e a divergencia fica
    # registrada nos campos e na memoria.
    r = ce.eh_viga_parede(l_cm=250.0, h_cm=100.0, continua=False)
    assert r.viga_parede_regra_geral is True
    assert r.viga_parede_regra_especifica is False
    assert r.viga_parede is False
    assert any("Divergência" in linha for linha in r.memoria)


def test_viga_continua_nunca_diverge_das_duas_regras():
    # Para viga continua as duas regras sao o mesmo limite (l/h < 3,0).
    for l_sobre_h in (1.0, 2.0, 2.9, 3.0, 3.5):
        r = ce.eh_viga_parede(l_cm=l_sobre_h * 100.0, h_cm=100.0, continua=True)
        assert r.viga_parede_regra_geral == r.viga_parede_regra_especifica


# --- 14.5.4 — restrições à análise plástica (PDF p. 106) ---------------------
def test_analise_plastica_permitida_sem_restricoes():
    r = ce.analise_plastica_permitida(
        segunda_ordem_global=False, dutilidade_suficiente=True
    )
    assert r.permitida is True
    assert r.ok is True


def test_analise_plastica_proibida_por_2a_ordem_global():
    r = ce.analise_plastica_permitida(
        segunda_ordem_global=True, dutilidade_suficiente=True
    )
    assert r.permitida is False


def test_analise_plastica_proibida_por_falta_de_dutilidade():
    r = ce.analise_plastica_permitida(
        segunda_ordem_global=False, dutilidade_suficiente=False
    )
    assert r.permitida is False


def test_analise_plastica_proibida_por_fadiga():
    r = ce.analise_plastica_permitida(
        segunda_ordem_global=False,
        dutilidade_suficiente=True,
        risco_fadiga=True,
    )
    assert r.permitida is False
    assert any("fadiga" in linha for linha in r.memoria)


def test_analise_plastica_proibida_por_todos_os_motivos_juntos():
    r = ce.analise_plastica_permitida(
        segunda_ordem_global=True,
        dutilidade_suficiente=False,
        risco_fadiga=True,
    )
    assert r.permitida is False
    memoria_completa = " ".join(r.memoria)
    assert "2ª ordem" in memoria_completa
    assert "dutilidade" in memoria_completa
    assert "fadiga" in memoria_completa


def test_analise_plastica_padrao_risco_fadiga_falso():
    # Reproduz o comportamento anterior a este pacote (so (a) e (b)).
    r = ce.analise_plastica_permitida(
        segunda_ordem_global=False, dutilidade_suficiente=True
    )
    assert r.risco_fadiga is False


# --- Separador decimal consistente nas memórias (vírgula, PT-BR) -----------
# Cada memória mistura número (antes: "3.0000", formatado com {:.4f}) com
# texto literal em português ("razão >= 3,0"). As duas convenções não podem
# conviver na mesma linha: o valor de 4 casas decimais também deve usar
# vírgula. (Não se usa regex genérica de "dígito.dígito" porque as próprias
# referências normativas, como "14.4.1" e "18.3.1", têm esse padrão.)
def _sem_4_casas_com_ponto(linha: str) -> bool:
    """True se a linha não tem um número de 4 casas decimais com ponto."""
    import re

    return re.search(r"\d\.\d{4}\b", linha) is None


def test_memoria_elemento_linear_usa_virgula_no_valor_numerico():
    r = ce.eh_elemento_linear(l_cm=100.0, h_max_cm=30.0)
    assert all(_sem_4_casas_com_ponto(linha) for linha in r.memoria)
    assert "3,3333" in r.memoria[0]


def test_memoria_placa_espessa_usa_virgula_no_valor_numerico():
    r = ce.eh_placa_espessa(h_cm=50.0, vao_cm=100.0)
    assert all(_sem_4_casas_com_ponto(linha) for linha in r.memoria)
    assert "33,3333" in r.memoria[0]


def test_memoria_pilar_parede_usa_virgula_no_valor_numerico():
    r = ce.eh_pilar_parede(b_cm=100.0, h_cm=15.0)
    assert all(_sem_4_casas_com_ponto(linha) for linha in r.memoria)
    assert "6,6667" in r.memoria[0]


def test_memoria_viga_parede_usa_virgula_no_valor_numerico():
    r = ce.eh_viga_parede(l_cm=250.0, h_cm=100.0, continua=False)
    assert all(_sem_4_casas_com_ponto(linha) for linha in r.memoria)
    assert "2,5000" in r.memoria[0]
