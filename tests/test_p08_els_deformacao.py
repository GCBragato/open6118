"""P8 — ELS de deformação: rigidez equivalente, flecha e limites
(dimensionamento/els_deformacao_nbr6118.py).

Valores esperados tirados das imagens da NBR 6118:2026: Tabela 13.3
(PDF p. 97-99), 17.3.1 (PDF p. 145), 17.3.2.1.1 (PDF p. 146), 17.3.2.1.2 e
Tabela 17.1 (PDF p. 147-148), 19.3.1 (PDF p. 179). Quando o esperado depende
de conta, a conta está no comentário do teste.
"""

import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import els_deformacao_nbr6118 as els  # noqa: E402
import lajes_nbr6118 as lj  # noqa: E402
import viga_servico_nbr6118 as vs  # noqa: E402

Erro = nbr.FaixaNormativaError


# ---------------------------------------------------------------------------
# Tabela 13.3 (PDF p. 97-99) — todas as linhas
# ---------------------------------------------------------------------------
def test_aceitabilidade_visual_l250():
    # p. 97: Total, l/250. l=500 -> 2.0 cm; l=250 -> 1.0 cm (borda).
    lim, desc = els.deslocamento_limite("aceitabilidade_visual", vao_cm=500.0)
    assert lim == pytest.approx(2.0)
    lim2, _ = els.deslocamento_limite("aceitabilidade_visual", vao_cm=250.0)
    assert lim2 == pytest.approx(1.0)
    assert "Aceitabilidade sensorial" in desc


def test_aceitabilidade_vibracao_l350():
    # p. 97: devido a cargas variáveis de utilização, l/350.
    lim, _ = els.deslocamento_limite("aceitabilidade_vibracao", vao_cm=700.0)
    assert lim == pytest.approx(2.0)


def test_drenagem_l250():
    # p. 98, nota a: l/250. l=500 -> 2.0 cm.
    lim, _ = els.deslocamento_limite("drenagem", vao_cm=500.0)
    assert lim == pytest.approx(2.0)


def test_planicidade_total_l350_mais_contraflecha():
    # p. 98, nota b: l/350 + contraflecha. Sem contraflecha: l=500 -> 1.4286 cm.
    lim, _ = els.deslocamento_limite("planicidade_total", vao_cm=500.0)
    assert lim == pytest.approx(500.0 / 350.0, rel=1e-9)
    # Com contraflecha de 0.5 cm (dentro de l/350 = 1.4286 cm): soma direto.
    lim2, _ = els.deslocamento_limite(
        "planicidade_total", vao_cm=500.0, contraflecha_cm=0.5)
    assert lim2 == pytest.approx(500.0 / 350.0 + 0.5, rel=1e-9)
    # Fronteira: contraflecha == l/350 exatamente (500/350 cm) ainda é aceita.
    lim3, _ = els.deslocamento_limite(
        "planicidade_total", vao_cm=500.0, contraflecha_cm=500.0 / 350.0)
    assert lim3 == pytest.approx(2.0 * (500.0 / 350.0), rel=1e-9)


def test_planicidade_total_contraflecha_maior_que_l350_levanta_erro():
    # p. 98/99, nota b: "a atuação isolada da contraflecha não pode ocasionar
    # um desvio do plano maior que l/350." l=500 -> l/350 = 1.4286 cm; uma
    # contraflecha de 2.0 cm viola a nota e deve levantar FaixaNormativaError
    # em vez de simplesmente somar ao limite.
    with pytest.raises(Erro):
        els.deslocamento_limite(
            "planicidade_total", vao_cm=500.0, contraflecha_cm=2.0)


def test_planicidade_apos_piso_l600():
    # p. 98: l/600. l=500 -> 0.8333 cm.
    lim, _ = els.deslocamento_limite("planicidade_apos_piso", vao_cm=500.0)
    assert lim == pytest.approx(500.0 / 600.0, rel=1e-9)


def test_equipamento_sensivel_sem_numero():
    # p. 98: "de acordo com recomendação do fabricante do equipamento" —
    # não é uma célula "-" (norma não define o caso), é uma regra qualitativa
    # explícita; devolve None + texto, sem levantar erro.
    lim, desc = els.deslocamento_limite("equipamento_sensivel")
    assert lim is None
    assert "fabricante" in desc.lower()


@pytest.mark.parametrize("l_cm, esperado", [
    (100.0, 0.2),   # 100/500 = 0.2 cm < 1.0 cm -> l/500 governa
    (400.0, 0.8),   # 400/500 = 0.8 cm < 1.0 cm -> l/500 governa
    (500.0, 1.0),   # fronteira: 500/500 = 1.0 cm = 10 mm (empate)
    (600.0, 1.0),   # 600/500 = 1.2 cm > 1.0 cm -> 10 mm governa
])
def test_alvenaria_min_l500_10mm(l_cm, esperado):
    # p. 98, nota c: min(l/500, 10 mm). Testa os dois lados da fronteira
    # l=500 cm (onde l/500 = 10 mm exatamente).
    lim, _ = els.deslocamento_limite("alvenaria", vao_cm=l_cm)
    assert lim == pytest.approx(esperado, rel=1e-9)


@pytest.mark.parametrize("l_cm, esperado", [
    (500.0, 2.0),    # 500/250 = 2.0 cm < 2.5 cm -> l/250 governa
    (625.0, 2.5),    # fronteira: 625/250 = 2.5 cm = 25 mm (empate)
    (750.0, 2.5),    # 750/250 = 3.0 cm > 2.5 cm -> 25 mm governa
])
def test_divisoria_leve_min_l250_25mm(l_cm, esperado):
    # p. 98, nota c: min(l/250, 25 mm).
    lim, _ = els.deslocamento_limite("divisoria_leve", vao_cm=l_cm)
    assert lim == pytest.approx(esperado, rel=1e-9)


def test_movimento_lateral_vento_H_e_Hi_separados():
    # p. 98, notas d e e: H/1700 (deslocamento lateral total) e Hi/850
    # (entre pavimentos vizinhos) são dois critérios distintos, não um min.
    lim_H, desc = els.deslocamento_limite("movimento_lateral_vento", H_cm=3000.0)
    assert lim_H == pytest.approx(3000.0 / 1700.0, rel=1e-9)  # ~1.7647 cm
    lim_Hi, _ = els.deslocamento_limite("movimento_lateral_vento", Hi_cm=300.0)
    assert lim_Hi == pytest.approx(300.0 / 850.0, rel=1e-9)  # ~0.3529 cm
    assert "vento" in desc.lower()


def test_movimento_lateral_vento_exige_exatamente_um():
    with pytest.raises(ValueError):
        els.deslocamento_limite("movimento_lateral_vento")
    with pytest.raises(ValueError):
        els.deslocamento_limite("movimento_lateral_vento", H_cm=100.0, Hi_cm=50.0)


@pytest.mark.parametrize("l_cm, esperado", [
    (400.0, 1.0),   # 400/400 = 1.0 cm < 1.5 cm -> l/400 governa
    (600.0, 1.5),   # fronteira: 600/400 = 1.5 cm = 15 mm (empate)
    (800.0, 1.5),   # 800/400 = 2.0 cm > 1.5 cm -> 15 mm governa
])
def test_movimento_termico_vertical_min_l400_15mm(l_cm, esperado):
    # p. 98, nota f: min(l/400, 15 mm).
    lim, _ = els.deslocamento_limite("movimento_termico_vertical", vao_cm=l_cm)
    assert lim == pytest.approx(esperado, rel=1e-9)


def test_forro_termico_horizontal_Hi500():
    lim, _ = els.deslocamento_limite("forro_termico_horizontal", Hi_cm=300.0)
    assert lim == pytest.approx(300.0 / 500.0, rel=1e-9)


def test_forro_revestimento_colado_l350():
    lim, _ = els.deslocamento_limite("forro_revestimento_colado", vao_cm=500.0)
    assert lim == pytest.approx(500.0 / 350.0, rel=1e-9)


def test_forro_revestimento_pendurado_l175():
    lim, _ = els.deslocamento_limite("forro_revestimento_pendurado", vao_cm=500.0)
    assert lim == pytest.approx(500.0 / 175.0, rel=1e-9)


def test_ponte_rolante_H400():
    lim, _ = els.deslocamento_limite("ponte_rolante", H_cm=2000.0)
    assert lim == pytest.approx(2000.0 / 400.0, rel=1e-9)


def test_categoria_desconhecida_leva_a_erro():
    with pytest.raises(ValueError):
        els.deslocamento_limite("categoria_inexistente", vao_cm=100.0)


def test_categorias_com_vao_exigem_vao_cm():
    with pytest.raises(ValueError):
        els.deslocamento_limite("drenagem")


# ---------------------------------------------------------------------------
# 13.3, NOTA 1 e NOTA 2 — vão equivalente (PDF p. 99)
# ---------------------------------------------------------------------------
def test_vao_equivalente_balanco():
    # NOTA 1: vão equivalente = 2x o comprimento do balanço.
    assert els.vao_equivalente("balanco", 150.0) == pytest.approx(300.0)


def test_vao_equivalente_laje_passa_o_menor_vao():
    # NOTA 2: para lajes, l é o menor vão; a função apenas documenta a regra.
    assert els.vao_equivalente("laje", 400.0) == pytest.approx(400.0)


def test_vao_equivalente_parede_sobre_laje():
    # NOTA 2, exceção: lx=400, ly=700, parede na direção ly.
    # l = min(vao_direcao_parede, 2*menor_vao) = min(700, 2*400) = min(700, 800) = 700.
    l_eq = els.vao_equivalente("laje_parede", 700.0, vao_menor_cm=400.0)
    assert l_eq == pytest.approx(700.0)
    # Caso em que o dobro do menor vão é quem governa: lx=200, ly=700.
    l_eq2 = els.vao_equivalente("laje_parede", 700.0, vao_menor_cm=200.0)
    assert l_eq2 == pytest.approx(400.0)  # min(700, 400) = 400


def test_vao_equivalente_parede_exige_vao_menor():
    with pytest.raises(ValueError):
        els.vao_equivalente("laje_parede", 700.0)


def test_vao_equivalente_elemento_desconhecido():
    with pytest.raises(ValueError):
        els.vao_equivalente("coluna", 100.0)


# ---------------------------------------------------------------------------
# 17.3.1 — Momento de fissuração Mr (PDF p. 145)
# ---------------------------------------------------------------------------
def test_momento_fissuracao_retangular_bate_com_lajes_nbr6118():
    # Cross-check: mesma fórmula que lajes_nbr6118.momento_fissuracao
    # (retangular, fct,m), calculada a partir de Ic/yt da mesma seção.
    b, h, fck = 100.0, 12.0, 25.0
    Ic = b * h ** 3 / 12.0
    yt = h / 2.0
    Mr_generico = els.momento_fissuracao_kncm(Ic, yt, fck, forma="retangular",
                                              resistencia="fctm")
    Mr_legado = lj.momento_fissuracao(b, h, fck, alpha=1.5)
    assert Mr_generico == pytest.approx(Mr_legado, rel=1e-9)
    # Apostila 3.17.6 L2: Mr ~ 923 kN.cm (conferido também em lajes_nbr6118).
    assert Mr_generico == pytest.approx(923.0, abs=10.0)


@pytest.mark.parametrize("forma, alfa_esperado", [
    ("retangular", 1.5), ("T", 1.2), ("duplo_T", 1.2),
    ("I", 1.3), ("T_invertido", 1.3),
])
def test_momento_fissuracao_alfa_por_forma(forma, alfa_esperado):
    # 17.3.1, p. 145: alfa = 1,5 retangular; 1,2 T/duplo T; 1,3 I/T invertido.
    # Mr = alfa * fct * Ic / yt; com Ic=yt=1 e fct=1 (kN/cm2), Mr = alfa.
    fck = 30.0
    fct = nbr.mpa_para_kncm2(nbr.fct_m(fck))
    Mr = els.momento_fissuracao_kncm(1.0 / fct, 1.0, fck, forma=forma,
                                     resistencia="fctm")
    assert Mr == pytest.approx(alfa_esperado, rel=1e-9)


def test_momento_fissuracao_fctk_inf_e_070_de_fctm():
    # 8.2.5: fctk,inf = 0,7 * fct,m -> Mr com fctk,inf = 0,7 * Mr com fct,m.
    Ic, yt, fck = 50000.0, 15.0, 30.0
    Mr_fctm = els.momento_fissuracao_kncm(Ic, yt, fck, resistencia="fctm")
    Mr_fctkinf = els.momento_fissuracao_kncm(Ic, yt, fck, resistencia="fctk_inf")
    assert Mr_fctkinf == pytest.approx(0.7 * Mr_fctm, rel=1e-9)


def test_momento_fissuracao_forma_invalida():
    with pytest.raises(ValueError):
        els.momento_fissuracao_kncm(1000.0, 10.0, 25.0, forma="hexagonal")


def test_momento_fissuracao_resistencia_invalida():
    with pytest.raises(ValueError):
        els.momento_fissuracao_kncm(1000.0, 10.0, 25.0, resistencia="fctd")


@pytest.mark.parametrize("Ic, yt", [(-1.0, 10.0), (100.0, 0.0), (0.0, 10.0)])
def test_momento_fissuracao_geometria_invalida(Ic, yt):
    with pytest.raises(ValueError):
        els.momento_fissuracao_kncm(Ic, yt, 25.0)


# ---------------------------------------------------------------------------
# 17.3.2.1.1 — Rigidez equivalente (Branson), PDF p. 146
# ---------------------------------------------------------------------------
def test_rigidez_equivalente_Ma_igual_Mr_da_Ecs_Ic():
    # Ma = Mr -> (Mr/Ma)^3 = 1 -> (EI)eq = Ecs*Ic (seção não fissurada).
    Ecs, Ic, III, Mr = 2500.0, 50000.0, 15000.0, 900.0
    ei = els.rigidez_equivalente_kncm2(Ecs, Ic, III, Mr, Mr)
    assert ei == pytest.approx(Ecs * Ic, rel=1e-9)


def test_rigidez_equivalente_Ma_menor_que_Mr_da_Ecs_Ic():
    # Ma < Mr: a fórmula bruta passaria de Ecs*Ic, mas o teto <= Ecs*Ic
    # (seção não fissurada) prevalece.
    Ecs, Ic, III, Mr, Ma = 2500.0, 50000.0, 15000.0, 900.0, 500.0
    ei = els.rigidez_equivalente_kncm2(Ecs, Ic, III, Mr, Ma)
    assert ei == pytest.approx(Ecs * Ic, rel=1e-9)


def test_rigidez_equivalente_Ma_muito_maior_que_Mr_tende_a_Ecs_III():
    # Ma >> Mr -> (Mr/Ma)^3 -> 0 -> (EI)eq -> Ecs*III.
    Ecs, Ic, III, Mr = 2500.0, 50000.0, 15000.0, 900.0
    Ma = 1000.0 * Mr
    ei = els.rigidez_equivalente_kncm2(Ecs, Ic, III, Mr, Ma)
    assert ei == pytest.approx(Ecs * III, rel=1e-6)


def test_rigidez_equivalente_ponto_interior():
    # Mr/Ma = 0.5 -> razao3 = 0.125.
    # (EI)eq = Ecs*(0.125*Ic + 0.875*III) = 2500*(0.125*50000 + 0.875*15000)
    #        = 2500*(6250 + 13125) = 2500*19375 = 48 437 500 kN.cm2.
    Ecs, Ic, III, Mr, Ma = 2500.0, 50000.0, 15000.0, 900.0, 1800.0
    ei = els.rigidez_equivalente_kncm2(Ecs, Ic, III, Mr, Ma)
    assert ei == pytest.approx(2500.0 * 19375.0, rel=1e-9)


def test_rigidez_equivalente_Ma_zero_da_Ecs_Ic():
    Ecs, Ic, III, Mr = 2500.0, 50000.0, 15000.0, 900.0
    ei = els.rigidez_equivalente_kncm2(Ecs, Ic, III, Mr, 0.0)
    assert ei == pytest.approx(Ecs * Ic, rel=1e-9)


def test_rigidez_equivalente_barras_lisas_reduz_Mr_a_metade():
    # 17.3.2.1.1, p. 146: com barras lisas, Mr entra reduzido à metade.
    Ecs, Ic, III, Mr, Ma = 2500.0, 50000.0, 15000.0, 900.0, 1800.0
    ei_lisas = els.rigidez_equivalente_kncm2(Ecs, Ic, III, Mr, Ma, barras_lisas=True)
    ei_direto = els.rigidez_equivalente_kncm2(Ecs, Ic, III, Mr / 2.0, Ma)
    assert ei_lisas == pytest.approx(ei_direto, rel=1e-9)


@pytest.mark.parametrize("Ecs, Ic, III", [(-1.0, 100.0, 10.0), (100.0, 0.0, 10.0)])
def test_rigidez_equivalente_entradas_invalidas(Ecs, Ic, III):
    with pytest.raises(ValueError):
        els.rigidez_equivalente_kncm2(Ecs, Ic, III, 100.0, 200.0)


def test_rigidez_equivalente_III_negativo():
    with pytest.raises(ValueError):
        els.rigidez_equivalente_kncm2(2500.0, 1000.0, -1.0, 100.0, 200.0)


# ---------------------------------------------------------------------------
# 17.3.2.1.2 e Tabela 17.1 (PDF p. 147-148) — xi(t)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("t_meses, xi_esperado", [
    (0.0, 0.0), (0.5, 0.54), (1.0, 0.68), (2.0, 0.84), (3.0, 0.95),
    (4.0, 1.04), (5.0, 1.12), (10.0, 1.36), (20.0, 1.64), (40.0, 1.89),
])
def test_xi_fluencia_tabela_17_1_celulas(t_meses, xi_esperado):
    assert els.xi_fluencia(t_meses) == pytest.approx(xi_esperado, abs=5e-3)


@pytest.mark.parametrize("t_meses", [70.0, 71.0, 200.0])
def test_xi_fluencia_patamar_maior_igual_70(t_meses):
    # Tabela 17.1: xi(t) = 2 para t > 70 meses; e o valor tabelado em t=70
    # também já é praticamente 2 (0,68*0,996^70*70^0.32).
    assert els.xi_fluencia(t_meses) == pytest.approx(2.0, abs=1e-2)


def test_xi_fluencia_negativo_leva_a_erro():
    with pytest.raises(Erro):
        els.xi_fluencia(-1.0)


# ---------------------------------------------------------------------------
# t0 ponderado e alfa_f (PDF p. 147-148)
# ---------------------------------------------------------------------------
def test_t0_ponderado_duas_parcelas():
    # t0 = (P1*t01 + P2*t02) / (P1+P2) = (100*1 + 50*3)/150 = 250/150 = 1.6667
    t0 = els.t0_ponderado([(100.0, 1.0), (50.0, 3.0)])
    assert t0 == pytest.approx(250.0 / 150.0, rel=1e-9)


def test_t0_ponderado_vazio_leva_a_erro():
    with pytest.raises(ValueError):
        els.t0_ponderado([])


def test_t0_ponderado_soma_zero_leva_a_erro():
    with pytest.raises(ValueError):
        els.t0_ponderado([(10.0, 1.0), (-10.0, 5.0)])


def test_alpha_f_bate_com_lajes_nbr6118_t0_unico():
    # Cross-check com a versão antiga (t0 único), mesma fórmula.
    af_novo = els.alpha_f(t_meses=70.0, t0_meses=1.0, rho_linha=0.0)
    af_legado = lj.alpha_f(t_meses=70.0, t0_meses=1.0, rho_linha=0.0)
    assert af_novo == pytest.approx(af_legado, rel=1e-12)
    # Apostila 3.17.6.1 L2: alfa_f ~ 1.32 (referência de ordem de grandeza).
    assert af_novo == pytest.approx(1.32, abs=0.05)


def test_alpha_f_com_t0_ponderado_por_varias_cargas():
    # t0 ponderado entra no lugar do t0 único; resultado deve bater com
    # calcular t0_ponderado à parte e passar como float.
    cargas = [(100.0, 1.0), (50.0, 3.0)]
    af_seq = els.alpha_f(t_meses=70.0, t0_meses=cargas, rho_linha=0.1)
    t0 = els.t0_ponderado(cargas)
    af_float = els.alpha_f(t_meses=70.0, t0_meses=t0, rho_linha=0.1)
    assert af_seq == pytest.approx(af_float, rel=1e-12)


def test_alpha_f_rho_linha_negativo_leva_a_erro():
    with pytest.raises(ValueError):
        els.alpha_f(t_meses=70.0, t0_meses=1.0, rho_linha=-0.01)


# ---------------------------------------------------------------------------
# flecha_total (PDF p. 148 e p. 99, Notas 3, 5 e 6)
# ---------------------------------------------------------------------------
def test_flecha_total_caso_usual_multiplica_por_1_mais_alpha_f():
    # 17.3.2.1.2: "o valor da flecha total deve ser obtido multiplicando a
    # flecha imediata por (1 + alfa_f)".
    f_qp, af = 0.36, 1.32
    assert els.flecha_total(f_qp, af) == pytest.approx(f_qp * (1.0 + af), rel=1e-12)


def test_flecha_total_com_combinacao_adotada_diferente_da_qp():
    # Nota 3/6: deslocamento total = imediata(comb. adotada) +
    # imediata(qp)*alfa_f.
    f_qp, af, f_adotada = 0.30, 1.0, 0.45
    total = els.flecha_total(f_qp, af, f_imediata_comb_adotada_cm=f_adotada)
    assert total == pytest.approx(f_adotada + f_qp * af, rel=1e-12)


def test_flecha_total_cross_check_apostila_L2():
    # Apostila 3.17.6.1 L2 (também em lajes_nbr6118.teste_flecha_L2):
    # a_i ~ 0.36 cm, alfa_f ~ 1.32 -> a_t ~ 0.85 cm.
    Ecs = lj.Ecs_kncm2(25.0, alpha_E=1.0)
    Ic = 100.0 * 12.0 ** 3 / 12.0
    EI = Ecs * Ic
    a_i = lj.flecha_imediata_duas_direcoes("3", 586, 606, 4.73, EI)
    af = els.alpha_f(t_meses=70.0, t0_meses=1.0)
    a_t = els.flecha_total(a_i, af)
    assert a_t == pytest.approx(0.85, abs=0.05)


# ---------------------------------------------------------------------------
# verificar_flecha — 19.3.1 (PDF p. 179), usada por vigas e por lajes
# ---------------------------------------------------------------------------
def test_verificar_flecha_ok_dentro_do_limite():
    r = els.verificar_flecha(
        f_imediata_qp_cm=0.3, categoria="aceitabilidade_visual",
        t_meses=70.0, t0_meses=1.0, rho_linha=0.0, vao_cm=500.0,
    )
    assert isinstance(r, els.ResultadoFlecha)
    assert r.limite_cm == pytest.approx(2.0)
    assert r.f_total_cm == pytest.approx(0.3 * (1.0 + r.alpha_f), rel=1e-9)
    assert r.ok is True
    assert r.governante == "aceitabilidade_visual"


def test_verificar_flecha_excede_limite_emite_aviso():
    with warnings.catch_warnings(record=True) as reg:
        warnings.simplefilter("always")
        r = els.verificar_flecha(
            f_imediata_qp_cm=5.0, categoria="aceitabilidade_visual",
            t_meses=70.0, t0_meses=1.0, rho_linha=0.0, vao_cm=500.0,
        )
    assert r.ok is False
    assert any(issubclass(w.category, els.AvisoNBR6118) for w in reg)


def test_verificar_flecha_sem_limite_numerico():
    r = els.verificar_flecha(
        f_imediata_qp_cm=0.1, categoria="equipamento_sensivel",
    )
    assert r.limite_cm is None
    assert r.ok is None


def test_verificar_flecha_usada_para_laje_19_3_1():
    # 19.3.1, p. 179: para lajes, usar "os critérios dados em 17.3.2,
    # considerando a possibilidade de fissuração (Estádio II)" — ou seja, a
    # rigidez que entra na flecha imediata precisa vir de
    # rigidez_equivalente_kncm2 (Branson), não de Ecs*Ic (Estádio I, seção
    # bruta). Este teste monta uma faixa de laje de 1 m com Ma > Mr (seção
    # fissurada) e confere que:
    #   1) a rigidez fissurada (EI_II) é estritamente menor que Ecs*Ic;
    #   2) a flecha resultante (com EI_II) é maior que a flecha que sairia
    #      da seção bruta não fissurada (EI_I) — prova que o Estádio II
    #      (rigidez_equivalente_kncm2) está de fato sendo usado, e não
    #      Ecs*Ic puro.
    fck = 25.0
    Ecs = lj.Ecs_kncm2(fck, alpha_E=1.0)          # kN/cm2
    bw_cm, h_cm, d_cm, As_cm2 = 100.0, 12.0, 10.0, 5.0
    Ic = bw_cm * h_cm ** 3 / 12.0
    yt_cm = h_cm / 2.0
    alpha_e = nbr.ES_MPA / (Ecs * 10.0)           # Ecs em kN/cm2 -> MPa

    Mr = els.momento_fissuracao_kncm(
        Ic, yt_cm, fck, forma="retangular", resistencia="fctm")
    Ma = 1.8 * Mr  # momento de serviço acima de Mr -> seção fissurada

    x_II = vs.x_II_retangular(bw_cm, d_cm, As_cm2, 0.0, 0.0, alpha_e)
    III = vs.I_II_retangular(bw_cm, d_cm, x_II, As_cm2, 0.0, 0.0, alpha_e)
    EI_II = els.rigidez_equivalente_kncm2(Ecs, Ic, III, Mr, Ma)
    EI_I = Ecs * Ic

    assert EI_II < EI_I  # Estádio II reduz a rigidez frente à seção bruta

    a_i_estadio_ii = lj.flecha_imediata_duas_direcoes(
        "3", 586, 606, 4.73, EI_II)
    a_i_estadio_i = lj.flecha_imediata_duas_direcoes(
        "3", 586, 606, 4.73, EI_I)
    assert a_i_estadio_ii > a_i_estadio_i  # rigidez menor -> flecha maior

    # A flecha total (imediata + diferida) desta faixa acaba excedendo o
    # limite de aceitabilidade_visual — o que não é o foco deste teste (ver
    # test_verificar_flecha_excede_limite_emite_aviso para isso) — por isso
    # o AvisoNBR6118 é silenciado aqui.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", els.AvisoNBR6118)
        r = els.verificar_flecha(
            f_imediata_qp_cm=a_i_estadio_ii, categoria="aceitabilidade_visual",
            t_meses=70.0, t0_meses=1.0, vao_cm=586.0,
        )
    assert r.f_imediata_cm == pytest.approx(a_i_estadio_ii)
    assert r.limite_cm == pytest.approx(586.0 / 250.0)
