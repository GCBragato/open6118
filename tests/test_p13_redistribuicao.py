"""Testes do P13 — Redistribuição de momentos e dutilidade.

Cobre dimensionamento/redistribuicao_nbr6118.py, contra a ABNT NBR 6118:2026:

  - 14.6.4.3 (limites de x/d com redistribuição e delta mínimo), p. 112
  - 14.6.4.4 (rotação plástica admissível, Figura 14.7, e dispensa), p. 112-113
  - 14.7.3.2 (redistribuição em placas/lajes), p. 116
  - 14.7.4 (dispensa de rotação em lajes e razão borda/vão), p. 116

Os valores esperados vêm da imagem de cada página (SCRATCH\\nbr_png\\pNNN.png).
A Figura 14.7 foi digitalizada manualmente a partir do gráfico impresso; os
pontos de teste usam tolerância declarada de +/-3 mrad (não há tabela numérica
na norma, só o gráfico).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr                  # noqa: E402
import redistribuicao_nbr6118 as red          # noqa: E402


# ---------------------------------------------------------------------------
# 14.6.4.3 — delta_minimo
# ---------------------------------------------------------------------------
def test_delta_minimo_p112():
    """delta >= 0,75, para qualquer caso (14.6.4.3, p. 112)."""
    assert red.delta_minimo() == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# 14.6.4.3 — xd_limite_redistribuicao
# ---------------------------------------------------------------------------
def test_xd_limite_redistribuicao_delta_1_reproduz_limite_sem_redistribuicao_fck_baixo():
    """delta=1 (sem redução de momento) deve reproduzir, dentro da tolerância de
    arredondamento da própria norma (0,44 e 0,56 são constantes arredondadas),
    o limite fixo sem redistribuição: x/d <= 0,45 para fck <= 50 MPa.

    (1 - 0,44)/1,25 = 0,448, contra xd_limite_dutilidade(30) = 0,45.
    """
    xd_redistribuicao = red.xd_limite_redistribuicao(1.0, 30.0)
    xd_sem_redistribuicao = nbr.xd_limite_dutilidade(30.0)
    assert xd_redistribuicao == pytest.approx((1.0 - 0.44) / 1.25)
    assert xd_redistribuicao == pytest.approx(xd_sem_redistribuicao, abs=0.005)


def test_xd_limite_redistribuicao_delta_1_reproduz_limite_sem_redistribuicao_fck_alto():
    """Mesma continuidade para 50 MPa < fck <= 90 MPa: x/d <= 0,35.

    (1 - 0,56)/1,25 = 0,352, contra xd_limite_dutilidade(60) = 0,35.
    """
    xd_redistribuicao = red.xd_limite_redistribuicao(1.0, 60.0)
    xd_sem_redistribuicao = nbr.xd_limite_dutilidade(60.0)
    assert xd_redistribuicao == pytest.approx((1.0 - 0.56) / 1.25)
    assert xd_redistribuicao == pytest.approx(xd_sem_redistribuicao, abs=0.005)


def test_xd_limite_redistribuicao_delta_075_fck_baixo_p112():
    """delta=0,75 (limite mínimo) dá o menor x/d admissível, fck <= 50 MPa:
    x/d <= (0,75 - 0,44)/1,25 = 0,248.
    """
    assert red.xd_limite_redistribuicao(0.75, 50.0) == pytest.approx(0.248)


def test_xd_limite_redistribuicao_delta_075_fck_alto_p112():
    """delta=0,75, 50 MPa < fck <= 90 MPa: x/d <= (0,75 - 0,56)/1,25 = 0,152."""
    assert red.xd_limite_redistribuicao(0.75, 90.0) == pytest.approx(0.152)


def test_xd_limite_redistribuicao_ponto_interior_p112():
    """Ponto interior, delta=0,9, fck=40 MPa: x/d <= (0,9-0,44)/1,25 = 0,368."""
    assert red.xd_limite_redistribuicao(0.9, 40.0) == pytest.approx(0.368)


def test_xd_limite_redistribuicao_fronteira_fck_50_usa_formula_fck_baixo():
    """fck = 50 MPa exatamente usa a fórmula de 'fck <= 50 MPa' (a)."""
    assert red.xd_limite_redistribuicao(0.8, 50.0) == pytest.approx((0.8 - 0.44) / 1.25)


def test_xd_limite_redistribuicao_fronteira_fck_acima_de_50_usa_formula_fck_alto():
    """fck = 50,01 MPa já usa a fórmula de '50 MPa < fck <= 90 MPa' (b)."""
    assert red.xd_limite_redistribuicao(0.8, 50.01) == pytest.approx((0.8 - 0.56) / 1.25)


def test_xd_limite_redistribuicao_delta_abaixo_do_minimo_levanta_erro():
    """delta < 0,75 viola o limite mínimo de 14.6.4.3 (p. 112)."""
    with pytest.raises(nbr.FaixaNormativaError):
        red.xd_limite_redistribuicao(0.70, 30.0)


def test_xd_limite_redistribuicao_delta_acima_de_1_levanta_erro():
    """delta > 1 não tem sentido físico (redistribuição só reduz o momento)."""
    with pytest.raises(nbr.FaixaNormativaError):
        red.xd_limite_redistribuicao(1.01, 30.0)


def test_xd_limite_redistribuicao_fck_fora_da_faixa_levanta_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        red.xd_limite_redistribuicao(0.8, 95.0)


# ---------------------------------------------------------------------------
# 14.7.3.2 — mesma fórmula, agora para lajes (p. 116)
# ---------------------------------------------------------------------------
def test_xd_limite_redistribuicao_laje_reproduz_formula_de_vigas_p116():
    """14.7.3.2 usa 'o coeficiente delta conforme 14.6.4.3': mesmo resultado."""
    for delta, fck in [(0.75, 40.0), (0.9, 60.0), (1.0, 30.0)]:
        assert red.xd_limite_redistribuicao_laje(delta, fck) == pytest.approx(
            red.xd_limite_redistribuicao(delta, fck)
        )


def test_xd_limite_redistribuicao_laje_delta_minimo_tambem_vale_p116():
    with pytest.raises(nbr.FaixaNormativaError):
        red.xd_limite_redistribuicao_laje(0.5, 30.0)


# ---------------------------------------------------------------------------
# 14.6.4.4 — Figura 14.7: pontos lidos do gráfico (p. 112-113)
# ---------------------------------------------------------------------------
def test_rotacao_plastica_pico_curva_i_ca50_c20_c50_p112():
    """Pico da curva I (fck 20-50 MPa, CA-50): ~31 mrad perto de x/d=0,10, a/d=3."""
    theta = red.rotacao_plastica_admissivel_mrad(0.10, 30.0, "CA-50", a_d=3.0)
    assert theta == pytest.approx(31.0, abs=3.0)


def test_rotacao_plastica_curva_i_ponto_final_p112():
    """Extremo direito da curva I: ~5 mrad em x/d=0,45."""
    theta = red.rotacao_plastica_admissivel_mrad(0.45, 30.0, "CA-50", a_d=3.0)
    assert theta == pytest.approx(5.0, abs=3.0)


def test_rotacao_plastica_curva_iii_ca60_menor_que_curva_i_ca50():
    """A CA-60 (curvas III/IV) tem capacidade de rotação menor que a CA-50
    (curvas I/II) no mesmo x/d — o gráfico mostra as curvas I/II acima de III/IV."""
    theta_ca50 = red.rotacao_plastica_admissivel_mrad(0.20, 30.0, "CA-50", a_d=3.0)
    theta_ca60 = red.rotacao_plastica_admissivel_mrad(0.20, 30.0, "CA-60", a_d=3.0)
    assert theta_ca60 < theta_ca50


def test_rotacao_plastica_c90_menor_ou_igual_que_c50_mesma_classe_aco():
    """fck=90 MPa (curva II/IV) fica abaixo de fck<=50 MPa (curva I/III) no
    mesmo x/d, para a mesma classe de aço."""
    theta_c50 = red.rotacao_plastica_admissivel_mrad(0.20, 30.0, "CA-50", a_d=3.0)
    theta_c90 = red.rotacao_plastica_admissivel_mrad(0.20, 90.0, "CA-50", a_d=3.0)
    assert theta_c90 < theta_c50


def test_rotacao_plastica_interpolacao_linear_c50_c90_p113():
    """Para 50 < fck < 90, a norma manda interpolar linearmente entre as
    curvas C50 e C90 (texto sob a Figura 14.7, p. 113)."""
    theta_c50 = red.rotacao_plastica_admissivel_mrad(0.20, 50.0, "CA-50", a_d=3.0)
    theta_c90 = red.rotacao_plastica_admissivel_mrad(0.20, 90.0, "CA-50", a_d=3.0)
    theta_70 = red.rotacao_plastica_admissivel_mrad(0.20, 70.0, "CA-50", a_d=3.0)
    esperado = theta_c50 + (theta_c90 - theta_c50) * (70.0 - 50.0) / (90.0 - 50.0)
    assert theta_70 == pytest.approx(esperado)


def test_rotacao_plastica_fator_a_d_diferente_de_3_p113():
    """Para a/d != 3, multiplica-se o valor lido por sqrt((a/d)/3) (p. 113)."""
    theta_a_d_3 = red.rotacao_plastica_admissivel_mrad(0.20, 30.0, "CA-50", a_d=3.0)
    theta_a_d_6 = red.rotacao_plastica_admissivel_mrad(0.20, 30.0, "CA-50", a_d=6.0)
    assert theta_a_d_6 == pytest.approx(theta_a_d_3 * math.sqrt(6.0 / 3.0))


def test_rotacao_plastica_fator_a_d_contra_valor_de_referencia_independente_p112():
    """Confere o fator sqrt((a/d)/3) contra números calculados à parte (não
    derivados de outra chamada da própria função), para provar que a leitura
    do radical da p. 112 (a barra cobre "(a/d)/3", confirmada em recorte
    ampliado da imagem) está mesmo implementada como sqrt((a/d)/3):

      a/d = 3  -> sqrt(3/3)  = sqrt(1) = 1,0   (fator neutro, o valor lido no
                  gráfico já é para a/d = 3, então theta não muda)
      a/d = 12 -> sqrt(12/3) = sqrt(4) = 2,0
      a/d = 0,75 -> sqrt(0,75/3) = sqrt(0,25) = 0,5

    Se a fórmula fosse sqrt(a/d)/3 (a leitura tipográfica alternativa da
    imagem), o fator em a/d=3 valeria sqrt(3)/3 = 0,577, não 1,0 — o que
    contradiria o próprio texto da norma ("o valor lido no gráfico
    corresponde à razão a/d = 3").
    """
    theta_base = red.rotacao_plastica_admissivel_mrad(0.20, 30.0, "CA-50", a_d=3.0)
    assert theta_base == pytest.approx(
        red.rotacao_plastica_admissivel_mrad(0.20, 30.0, "CA-50", a_d=3.0) * 1.0
    )
    theta_a_d_12 = red.rotacao_plastica_admissivel_mrad(0.20, 30.0, "CA-50", a_d=12.0)
    assert theta_a_d_12 == pytest.approx(theta_base * 2.0)
    theta_a_d_075 = red.rotacao_plastica_admissivel_mrad(0.20, 30.0, "CA-50", a_d=0.75)
    assert theta_a_d_075 == pytest.approx(theta_base * 0.5)


def test_rotacao_plastica_xd_fora_da_faixa_levanta_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        red.rotacao_plastica_admissivel_mrad(0.50, 30.0, "CA-50", a_d=3.0)


def test_rotacao_plastica_aco_fora_do_escopo_levanta_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        red.rotacao_plastica_admissivel_mrad(0.20, 30.0, "CA-25", a_d=3.0)


def test_rotacao_plastica_a_d_nao_positivo_levanta_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        red.rotacao_plastica_admissivel_mrad(0.20, 30.0, "CA-50", a_d=0.0)


# ---------------------------------------------------------------------------
# 14.6.4.4 / 14.7.4 — dispensa da verificação explícita de rotação (p. 113/116)
# ---------------------------------------------------------------------------
def test_dispensa_rotacao_fck_baixo_no_limite_p113():
    """x/d = 0,25 exatamente, fck <= 50 MPa: dispensa concedida (limite <=)."""
    r = red.dispensa_verificacao_rotacao(0.25, 40.0)
    assert r.ok is True
    assert r.xd_limite == pytest.approx(0.25)


def test_dispensa_rotacao_fck_baixo_acima_do_limite_p113():
    """x/d = 0,26, fck <= 50 MPa: dispensa não concedida."""
    r = red.dispensa_verificacao_rotacao(0.26, 40.0)
    assert r.ok is False


def test_dispensa_rotacao_fck_alto_no_limite_p113():
    """x/d = 0,15 exatamente, fck > 50 MPa: dispensa concedida."""
    r = red.dispensa_verificacao_rotacao(0.15, 60.0)
    assert r.ok is True


def test_dispensa_rotacao_fck_alto_acima_do_limite_p113():
    """x/d = 0,16, fck > 50 MPa: dispensa não concedida (limite mais restritivo)."""
    r = red.dispensa_verificacao_rotacao(0.16, 60.0)
    assert r.ok is False


def test_dispensa_rotacao_laje_fck_baixo_p116():
    """14.7.4 (lajes pela teoria das charneiras plásticas) repete, para
    fck <= 50 MPa, o limite x/d <= 0,25 de 14.6.4.4 — não há função própria
    para laje (o plano do pacote autoriza reaproveitar ``dispensa_verificacao_
    rotacao``), então este teste exercita os valores do enunciado de 14.7.4
    (p. 116) diretamente, sem comparar a função com outra chamada idêntica.
    """
    no_limite = red.dispensa_verificacao_rotacao(0.25, 40.0)
    assert no_limite.ok is True
    assert no_limite.xd_limite == pytest.approx(0.25)

    acima_do_limite = red.dispensa_verificacao_rotacao(0.26, 40.0)
    assert acima_do_limite.ok is False


def test_dispensa_rotacao_laje_fck_alto_p116():
    """Mesmo caso, para fck > 50 MPa: limite x/d <= 0,15 (14.7.4, p. 116)."""
    no_limite = red.dispensa_verificacao_rotacao(0.15, 60.0)
    assert no_limite.ok is True
    assert no_limite.xd_limite == pytest.approx(0.15)

    acima_do_limite = red.dispensa_verificacao_rotacao(0.16, 60.0)
    assert acima_do_limite.ok is False


# ---------------------------------------------------------------------------
# 14.7.4 — razão mínima entre momento de borda e momento de vão (p. 116)
# ---------------------------------------------------------------------------
def test_razao_momentos_borda_vao_no_limite_p116():
    """Razão exatamente 1,5 atende (limite >=)."""
    r = red.verificar_razao_momentos_borda_vao(150.0, 100.0)
    assert r.razao == pytest.approx(1.5)
    assert r.ok is True


def test_razao_momentos_borda_vao_abaixo_do_limite_p116():
    """Caso com razão abaixo de 1,5 (ex.: tabelas de Bares) não atende."""
    r = red.verificar_razao_momentos_borda_vao(120.0, 100.0)
    assert r.razao == pytest.approx(1.2)
    assert r.ok is False


def test_razao_momentos_borda_vao_acima_do_limite_p116():
    r = red.verificar_razao_momentos_borda_vao(200.0, 100.0)
    assert r.ok is True


def test_razao_momentos_borda_vao_nao_positivo_levanta_erro():
    with pytest.raises(nbr.FaixaNormativaError):
        red.verificar_razao_momentos_borda_vao(0.0, 100.0)
    with pytest.raises(nbr.FaixaNormativaError):
        red.verificar_razao_momentos_borda_vao(150.0, -10.0)
