"""Testes do pacote F1 - Fechamento: geometria efetiva (abertura na mesa e
mísulas), NBR 6118:2026.

Fecha a revisão dos dois itens que ficaram "parciais" no P14, em
dimensionamento/analise_linear_nbr6118.py:

  - 14.6.2.2 Largura efetiva bef com abertura na laje, Figura 14.3, p. 109
  - 14.6.2.3 Mísulas e variações bruscas de seção, Figura 14.4, p. 109-110

Os dois itens continuam "parciais": a Figura 14.3 e a Figura 14.4 são regras
gráficas, sem ângulo, proporção ou comprimento de cunha dados no texto ou no
desenho (conferido em zoom alto nas duas figuras - ver a docstring de cada
função). Este arquivo acrescenta os testes que faltavam para a leitura
reforçada nesta revisão, sem duplicar os já existentes em
tests/test_p14_analise_linear.py.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import analise_linear_nbr6118 as al  # noqa: E402


def _aprox(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# 14.6.2.2 - Largura efetiva com abertura, Figura 14.3 (PDF p. 109)
# ---------------------------------------------------------------------------
def test_largura_efetiva_com_abertura_corte_total_da_mesa():
    """bef_geometrico_cm = 0 é um valor válido (a Figura 14.3 permite ler
    bef = 0 quando a abertura, na projeção das retas 1 e 2, toma toda a
    largura colaborante naquele trecho); a função só levanta erro para
    bef_geometrico_cm < 0, nunca para 0 (14.6.2.2, Figura 14.3, p. 109)."""
    assert _aprox(al.largura_efetiva_com_abertura(150.0, 0.0), 0.0)


def test_largura_efetiva_com_abertura_bef_intermediario_nao_e_alterado():
    """Quando o bef já lido no desenho da Figura 14.3 está dentro da faixa
    (0 <= bef <= bf), a função devolve o próprio valor lido, sem
    reinterpretar a geometria da abertura (14.6.2.2, p. 109): ela só aplica
    o teto bf, nunca substitui o valor gráfico do caso concreto."""
    assert _aprox(al.largura_efetiva_com_abertura(200.0, 137.5), 137.5)


def test_largura_efetiva_com_abertura_bf_minimo_valido():
    """bf_cm no limiar da faixa (> 0, arbitrariamente pequeno) ainda é
    aceito; só bf_cm <= 0 é inválido (14.6.2.2, p. 109)."""
    assert _aprox(al.largura_efetiva_com_abertura(0.01, 0.005), 0.005)
    with pytest.raises(al.FaixaNormativaError):
        al.largura_efetiva_com_abertura(0.0, 0.0)


# ---------------------------------------------------------------------------
# 14.6.2.3 - Mísulas e variações bruscas de seção, Figura 14.4 (PDF p. 109-110)
# ---------------------------------------------------------------------------
def test_secao_efetiva_misula_sem_parametro_de_posicao():
    """A Figura 14.4 (p. 109-110) não dá comprimento de cunha nem
    inclinação para o traçado 2 (mísula): não há como parametrizar uma
    posição ao longo da transição, e por isso a assinatura pública desta
    função não recebe (nem deve receber) parâmetro de posição - ela sempre
    devolve o piso seguro h_menor_cm, garantido em toda a cunha (ver
    docstring de secao_efetiva_misula, revisão F1)."""
    parametros = list(inspect.signature(al.secao_efetiva_misula).parameters)
    assert parametros == ["h_menor_cm", "h_maior_cm"]


def test_secao_efetiva_misula_viga_com_misula_de_apoio():
    """Caso típico de mísula de apoio (viga de 25 cm de altura no vão e
    60 cm junto ao pilar, mísula entre os dois): a altura efetiva no trecho
    de transição é a do trecho constante menor, 25 cm - a norma não dá base
    para contar nada da altura extra da mísula nesse trecho (14.6.2.3,
    Figura 14.4, p. 109-110)."""
    assert _aprox(al.secao_efetiva_misula(25.0, 60.0), 25.0)


def test_secao_efetiva_misula_variacao_pequena():
    """Mesmo com uma variação pequena entre os dois trechos (39,9 cm e
    40,0 cm), a função continua devolvendo o menor dos dois - o piso
    garantido em toda a cunha, sem arredondar para o maior (14.6.2.3,
    p. 109-110)."""
    assert _aprox(al.secao_efetiva_misula(39.9, 40.0), 39.9)


def test_secao_efetiva_misula_negativo_invalido():
    """h_menor_cm ou h_maior_cm negativos não são uma altura/largura válida
    de seção transversal (14.6.2.3, p. 109-110)."""
    with pytest.raises(al.FaixaNormativaError):
        al.secao_efetiva_misula(-10.0, 50.0)
    with pytest.raises(al.FaixaNormativaError):
        al.secao_efetiva_misula(10.0, -50.0)
