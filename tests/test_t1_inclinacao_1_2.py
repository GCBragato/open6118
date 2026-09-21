"""Testes do pacote T1 — inclinação 1:2 das Figuras 14.3 e 14.4.

Cobre o bloco "=== T1: ..." de dimensionamento/analise_linear_nbr6118.py
contra a ABNT NBR 6118:2026:

  - 14.6.2.2 Largura efetiva com abertura na mesa, Figura 14.3, p. 109
    (bef_com_abertura_em_x_cm)
  - 14.6.2.3 Mísulas e variações bruscas de seção, Figura 14.4, p. 109-110
    (hef_variacao_brusca_em_x_cm, hef_misula_em_x_cm)

Triagem de 21/09/2026: as duas figuras trazem, junto de cada canto de
transição, um pequeno triângulo retângulo com os catetos rotulados 1 (direção
transversal) e 2 (direção do eixo), o símbolo gráfico usual de inclinação —
o que fixa a proporção da reta-limite em 1:2. Os valores esperados vêm da
imagem das páginas (SCRATCH\\nbr_png\\p109.png e p110.png), não do JSON do
plano.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import analise_linear_nbr6118 as al        # noqa: E402
import nucleo_nbr6118 as nbr               # noqa: E402


def _aprox(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


def test_modulo_tem_mensagens_ao_usuario_acentuadas():
    """Checagem mecânica (regra global de acentuação): o bloco T1 precisa
    ter texto ao usuário em português acentuado, não só o resto do módulo."""
    fonte = Path(al.__file__).read_text(encoding="utf-8")
    bloco = fonte[fonte.index("=== T1:"):]
    acentos = "áéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ"
    n_acentos = sum(bloco.count(c) for c in acentos)
    assert n_acentos > 40, (
        f"bloco T1 com apenas {n_acentos} caracteres acentuados; texto ao "
        "usuário deve estar em português acentuado."
    )


def test_inclinacao_e_meio():
    """A constante nomeada é 1:2 (0,5 cm de altura/largura por cm de eixo)."""
    assert _aprox(al.INCLINACAO_FIGURAS_14_3_E_14_4, 0.5)


# =============================================================================
# 14.6.2.2 — Largura efetiva com abertura, Figura 14.3 (p. 109)
# =============================================================================
def test_bef_abertura_x_zero_e_o_bef_na_face_da_abertura():
    """x=0 (na própria face da abertura): bef(0) = bef_na_abertura, ainda sem
    nenhuma contribuição da reta 1:2."""
    assert _aprox(al.bef_com_abertura_em_x_cm(80.0, 150.0, 0.0), 80.0)


def test_bef_abertura_ponto_interior_da_transicao():
    """Ponto interior: bef_na_abertura=80, bf=150, x=60 cm ->
    bef = 80 + 0,5*60 = 110 cm (ainda abaixo de bf=150, reta 1:2 governa)."""
    bef = al.bef_com_abertura_em_x_cm(80.0, 150.0, 60.0)
    assert _aprox(bef, 80.0 + 0.5 * 60.0)
    assert _aprox(bef, 110.0)


def test_bef_abertura_x_onde_a_reta_1_2_alcanca_bf():
    """A reta 1:2 alcança bf=150 exatamente quando x = (150-80)/0,5 = 140 cm;
    dos dois lados desse ponto, bef não passa de bf."""
    x_no_encontro = (150.0 - 80.0) / al.INCLINACAO_FIGURAS_14_3_E_14_4
    assert _aprox(x_no_encontro, 140.0)
    assert _aprox(al.bef_com_abertura_em_x_cm(80.0, 150.0, x_no_encontro), 150.0)
    # depois do encontro, preso em bf (clip)
    assert _aprox(al.bef_com_abertura_em_x_cm(80.0, 150.0, x_no_encontro + 100.0), 150.0)
    # um pouco antes, ainda na reta 1:2 (não colado em bf)
    bef_antes = al.bef_com_abertura_em_x_cm(80.0, 150.0, x_no_encontro - 10.0)
    assert bef_antes < 150.0
    assert _aprox(bef_antes, 80.0 + 0.5 * (x_no_encontro - 10.0))


def test_bef_abertura_sem_reducao_na_face_ja_igual_a_bf():
    """Quando a abertura não reduz nada (bef_na_abertura = bf), bef(x) = bf
    para todo x, inclusive x=0."""
    assert _aprox(al.bef_com_abertura_em_x_cm(150.0, 150.0, 0.0), 150.0)
    assert _aprox(al.bef_com_abertura_em_x_cm(150.0, 150.0, 40.0), 150.0)


def test_bef_abertura_entradas_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        al.bef_com_abertura_em_x_cm(80.0, 0.0, 10.0)  # bf_cm <= 0
    with pytest.raises(nbr.FaixaNormativaError):
        al.bef_com_abertura_em_x_cm(-1.0, 150.0, 10.0)  # bef_na_abertura < 0
    with pytest.raises(nbr.FaixaNormativaError):
        al.bef_com_abertura_em_x_cm(160.0, 150.0, 10.0)  # bef_na_abertura > bf
    with pytest.raises(nbr.FaixaNormativaError):
        al.bef_com_abertura_em_x_cm(80.0, 150.0, -1.0)  # x_cm < 0


# =============================================================================
# 14.6.2.3 — Variação brusca de seção, Figura 14.4 (p. 109-110)
# =============================================================================
def test_hef_brusca_x_zero_e_h_menor():
    """No próprio canto do degrau (x=0), hef = h_menor (o degrau ainda não
    contou nada do trecho maior)."""
    assert _aprox(al.hef_variacao_brusca_em_x_cm(25.0, 60.0, 0.0), 25.0)


def test_hef_brusca_ponto_interior():
    """h_menor=25, h_maior=60, x=20 cm -> hef = 25 + 0,5*20 = 35 cm."""
    assert _aprox(al.hef_variacao_brusca_em_x_cm(25.0, 60.0, 20.0), 35.0)


def test_hef_brusca_x_onde_a_reta_1_2_alcanca_h_maior():
    """A reta 1:2 alcança h_maior=60 quando x = (60-25)/0,5 = 70 cm."""
    x_no_encontro = (60.0 - 25.0) / al.INCLINACAO_FIGURAS_14_3_E_14_4
    assert _aprox(x_no_encontro, 70.0)
    assert _aprox(al.hef_variacao_brusca_em_x_cm(25.0, 60.0, x_no_encontro), 60.0)
    # depois do encontro, preso em h_maior (clip)
    assert _aprox(al.hef_variacao_brusca_em_x_cm(25.0, 60.0, x_no_encontro + 50.0), 60.0)


def test_hef_brusca_sem_variacao_de_secao():
    """h_menor = h_maior (sem variação real): hef = h_menor = h_maior para
    todo x."""
    assert _aprox(al.hef_variacao_brusca_em_x_cm(40.0, 40.0, 0.0), 40.0)
    assert _aprox(al.hef_variacao_brusca_em_x_cm(40.0, 40.0, 30.0), 40.0)


def test_hef_brusca_entradas_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        al.hef_variacao_brusca_em_x_cm(0.0, 60.0, 10.0)  # h_menor <= 0
    with pytest.raises(nbr.FaixaNormativaError):
        al.hef_variacao_brusca_em_x_cm(25.0, 0.0, 10.0)  # h_maior <= 0
    with pytest.raises(ValueError):
        al.hef_variacao_brusca_em_x_cm(60.0, 25.0, 10.0)  # ordem trocada
    with pytest.raises(nbr.FaixaNormativaError):
        al.hef_variacao_brusca_em_x_cm(25.0, 60.0, -1.0)  # x_cm < 0


# =============================================================================
# 14.6.2.3 — Mísula, Figura 14.4 (p. 109-110)
# =============================================================================
def test_hef_misula_x_zero_e_h_menor():
    """No início da mísula (x=0), hef = h_menor, qualquer que seja o
    comprimento da mísula."""
    assert _aprox(al.hef_misula_em_x_cm(25.0, 60.0, 100.0, 0.0), 25.0)
    assert _aprox(al.hef_misula_em_x_cm(25.0, 60.0, 10.0, 0.0), 25.0)


def test_hef_misula_mais_suave_que_1_para_2_conta_a_misula_inteira():
    """Mísula mais suave que 1:2: h_maior-h_menor=35 cm de acréscimo ao
    longo de comprimento_misula=100 cm -> inclinação real 0,35 < 0,5.
    Em todo ponto interior, h_real(x) < reta 1:2, então hef segue a mísula
    real inteira, inclusive no fim físico dela (x=comprimento_misula)."""
    h_menor, h_maior, comprimento = 25.0, 60.0, 100.0
    inclinacao_real = (h_maior - h_menor) / comprimento
    assert inclinacao_real < al.INCLINACAO_FIGURAS_14_3_E_14_4

    x_meio = 40.0
    h_real_meio = h_menor + inclinacao_real * x_meio
    assert _aprox(al.hef_misula_em_x_cm(h_menor, h_maior, comprimento, x_meio), h_real_meio)

    # no fim físico da mísula, hef = h_maior (a mísula suave conta inteira)
    assert _aprox(al.hef_misula_em_x_cm(h_menor, h_maior, comprimento, comprimento), h_maior)

    # depois do fim físico, a seção já é h_maior constante e a reta 1:2 (que
    # partiu mais devagar) já a ultrapassou -> continua h_maior
    assert _aprox(al.hef_misula_em_x_cm(h_menor, h_maior, comprimento, comprimento + 20.0), h_maior)


def test_hef_misula_mais_ingreme_que_1_para_2_fica_presa_na_reta():
    """Mísula mais íngreme que 1:2: h_maior-h_menor=35 cm de acréscimo ao
    longo de comprimento_misula=30 cm -> inclinação real 35/30 ~ 1,167 > 0,5.
    A partir de x>0, h_real(x) já ultrapassa a reta 1:2, então hef fica preso
    na reta 1:2 (não conta a mísula inteira, mesmo dentro da cunha física)."""
    h_menor, h_maior, comprimento = 25.0, 60.0, 30.0
    inclinacao_real = (h_maior - h_menor) / comprimento
    assert inclinacao_real > al.INCLINACAO_FIGURAS_14_3_E_14_4

    x_meio = 10.0
    h_real_meio = h_menor + inclinacao_real * x_meio  # = 25 + 11,667 = 36,667
    h_reta_1_2_meio = h_menor + 0.5 * x_meio           # = 25 + 5 = 30
    assert h_reta_1_2_meio < h_real_meio
    assert _aprox(al.hef_misula_em_x_cm(h_menor, h_maior, comprimento, x_meio), h_reta_1_2_meio)

    # no fim físico da mísula (x=comprimento=30), a seção real já é h_maior=60,
    # mas a reta 1:2 só chegou a 25+0,5*30=40 -> hef ainda preso na reta
    hef_fim_fisico = al.hef_misula_em_x_cm(h_menor, h_maior, comprimento, comprimento)
    assert _aprox(hef_fim_fisico, 40.0)
    assert hef_fim_fisico < h_maior

    # a reta 1:2 só alcança h_maior=60 em x=(60-25)/0,5=70 cm, bem depois do
    # fim físico da mísula (30 cm)
    x_no_encontro = (h_maior - h_menor) / al.INCLINACAO_FIGURAS_14_3_E_14_4
    assert _aprox(x_no_encontro, 70.0)
    assert _aprox(al.hef_misula_em_x_cm(h_menor, h_maior, comprimento, x_no_encontro), h_maior)
    assert _aprox(al.hef_misula_em_x_cm(h_menor, h_maior, comprimento, x_no_encontro + 15.0), h_maior)


def test_hef_misula_exatamente_1_para_2():
    """Mísula com inclinação real exatamente 1:2 (limite entre os dois
    casos): h_real(x) e a reta 1:2 coincidem em todo ponto interior."""
    h_menor, h_maior, comprimento = 25.0, 55.0, 60.0  # (55-25)/60 = 0,5
    inclinacao_real = (h_maior - h_menor) / comprimento
    assert _aprox(inclinacao_real, al.INCLINACAO_FIGURAS_14_3_E_14_4)

    for x in (0.0, 15.0, 30.0, 60.0):
        esperado = min(h_maior, h_menor + 0.5 * x)
        assert _aprox(al.hef_misula_em_x_cm(h_menor, h_maior, comprimento, x), esperado)


def test_hef_misula_sem_variacao_de_secao():
    """h_menor = h_maior: hef = h_menor = h_maior para todo x."""
    assert _aprox(al.hef_misula_em_x_cm(40.0, 40.0, 50.0, 0.0), 40.0)
    assert _aprox(al.hef_misula_em_x_cm(40.0, 40.0, 50.0, 25.0), 40.0)
    assert _aprox(al.hef_misula_em_x_cm(40.0, 40.0, 50.0, 100.0), 40.0)


def test_hef_misula_entradas_invalidas():
    with pytest.raises(nbr.FaixaNormativaError):
        al.hef_misula_em_x_cm(0.0, 60.0, 100.0, 10.0)  # h_menor <= 0
    with pytest.raises(nbr.FaixaNormativaError):
        al.hef_misula_em_x_cm(25.0, 0.0, 100.0, 10.0)  # h_maior <= 0
    with pytest.raises(ValueError):
        al.hef_misula_em_x_cm(60.0, 25.0, 100.0, 10.0)  # ordem trocada
    with pytest.raises(nbr.FaixaNormativaError):
        al.hef_misula_em_x_cm(25.0, 60.0, 0.0, 10.0)  # comprimento_misula <= 0
    with pytest.raises(nbr.FaixaNormativaError):
        al.hef_misula_em_x_cm(25.0, 60.0, -5.0, 10.0)  # comprimento_misula < 0
    with pytest.raises(nbr.FaixaNormativaError):
        al.hef_misula_em_x_cm(25.0, 60.0, 100.0, -1.0)  # x_cm < 0


# =============================================================================
# 14.6.2.2 / 14.6.2.3 — funções antigas continuam com o mesmo resultado
# =============================================================================
def test_funcoes_antigas_sem_posicao_x_nao_mudaram():
    """largura_efetiva_com_abertura e secao_efetiva_misula (sem parâmetro de
    posição) continuam com a mesma assinatura e o mesmo resultado de antes
    do pacote T1 (convenção 3.3.7 do plano)."""
    assert _aprox(al.largura_efetiva_com_abertura(120.0, 80.0), 80.0)
    assert _aprox(al.largura_efetiva_com_abertura(120.0, 150.0), 120.0)
    assert _aprox(al.secao_efetiva_misula(30.0, 50.0), 30.0)
    assert _aprox(al.secao_efetiva_misula(40.0, 40.0), 40.0)
