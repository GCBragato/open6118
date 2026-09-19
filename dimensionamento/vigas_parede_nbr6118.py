"""Vigas-parede — ABNT NBR 6118:2026, 22.4.4 (detalhamento).

A classificação viga comum x viga-parede (22.4.1) já está em
``classificacao_elementos_nbr6118.eh_viga_parede`` (P11); este módulo cobre
o detalhamento de 22.4.4: a distribuição da armadura negativa de flexão em
viga-parede contínua entre três faixas de altura (22.4.4.1), as taxas
mínimas de armadura horizontal e vertical (22.4.4.1 e 22.4.4.3) e a
armadura vertical de suspensão quando a carga é aplicada pela face inferior
(22.4.4.3).

Norma: ABNT NBR 6118:2026, 5a edição (11/03/2026). As páginas citadas são as
do PDF (a página impressa é 18 a menos).

Unidades: comprimento e dimensão de seção em cm (``_cm``); armadura em
cm2/m por face (``_cm2_por_m``); força em kN (``_kn``); tensão de cálculo do
aço em kN/cm2 (``_kncm2``); área de aço em cm2 (``_cm2``).

Este módulo não reimplementa fórmula de material: fyd vem do núcleo
normativo (``nucleo_nbr6118.py``) e a área de aço de um tirante genérico
vem de ``bielas_tirantes_nbr6118.As_tirante_cm2`` (22.3.3).
"""

from __future__ import annotations

from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError

# 22.4.4.1 e 22.4.4.3, PDF p. 205-206 — taxa mínima de armadura horizontal e
# vertical de viga-parede, por face, por metro: 0,075 %.
TAXA_ARMADURA_MINIMA_VIGA_PAREDE = 0.00075

# 22.4.4.1, PDF p. 205 — faixa de validade da distribuição em 3 faixas
L_H_MINIMO = 1.0
L_H_MAXIMO = 3.0


# ---------------------------------------------------------------------------
# 22.4.4.1 — Distribuição da armadura negativa em viga-parede contínua
# (PDF p. 205)
# ---------------------------------------------------------------------------
def repartir_As_negativa(As_cm2: float, l_h: float) -> tuple[float, float, float]:
    """Reparte a armadura negativa total ``As_cm2`` entre as três faixas de
    altura ``h`` de uma viga-parede contínua (22.4.4.1, PDF p. 205), sem
    considerar, para ``h``, valores superiores ao vão teórico ``l``
    (3 >= l/h >= 1):

        - 20 % superiores de h: As1 = (l/2h - 0,50) * As
        - 60 % centrais de h:   As2 = (1,50 - l/2h) * As
        - 20 % inferiores de h: As3 = 0

    Devolve (As1, As2, As3), cm2. Fora de 1 <= l/h <= 3 levanta
    ``FaixaNormativaError`` (a norma só define a repartição nessa faixa).
    """
    lh = float(l_h)
    if not (L_H_MINIMO - 1e-9 <= lh <= L_H_MAXIMO + 1e-9):
        raise FaixaNormativaError(
            f"l/h = {lh:g} fora da faixa de validade de 22.4.4.1 "
            f"({L_H_MINIMO:g} <= l/h <= {L_H_MAXIMO:g})."
        )
    As = float(As_cm2)
    As1 = (lh / 2.0 - 0.50) * As
    As2 = (1.50 - lh / 2.0) * As
    As3 = 0.0
    return As1, As2, As3


# ---------------------------------------------------------------------------
# 22.4.4.1 e 22.4.4.3 — Armadura mínima horizontal e vertical (PDF p. 205-206)
# ---------------------------------------------------------------------------
def As_horizontal_min_cm2_por_m(b_cm: float) -> float:
    """As,h,min = 0,075 % * b, por face, por metro (22.4.4.1, PDF p. 205).

    ``b_cm`` é a espessura da viga-parede, cm; devolve cm2/m (por face).
    """
    b = float(b_cm)
    if b <= 0.0:
        raise ValueError(f"b_cm tem de ser positivo; recebido {b:g}.")
    return TAXA_ARMADURA_MINIMA_VIGA_PAREDE * b * 100.0


def As_vertical_min_cm2_por_m(b_cm: float) -> float:
    """As,v,min = 0,075 % * b, por face, por metro (22.4.4.3, PDF p. 206).

    Mesma taxa e mesmo valor numérico de ``As_horizontal_min_cm2_por_m``;
    função separada porque a norma trata os dois casos em itens distintos
    (22.4.4.1 para a horizontal, 22.4.4.3 para a vertical).
    """
    b = float(b_cm)
    if b <= 0.0:
        raise ValueError(f"b_cm tem de ser positivo; recebido {b:g}.")
    return TAXA_ARMADURA_MINIMA_VIGA_PAREDE * b * 100.0


# ---------------------------------------------------------------------------
# 22.4.4.3 — Suspensão da carga aplicada pela face inferior (PDF p. 206)
# ---------------------------------------------------------------------------
def suspensao_carga_inferior(F_kn: float, fyd_kncm2: float) -> float:
    """Armadura vertical de suspensão quando a carga é aplicada pela face
    inferior de uma viga-parede (22.4.4.3, PDF p. 206).

    O texto da norma só exige, sem fórmula fechada, que "essa armadura deve
    ser capaz de suspender a totalidade da carga aplicada" (divergência
    JSON x imagem: o item veio marcado ``conferido_na_imagem=False`` porque
    a imagem não traz expressão numérica). Este módulo aplica, por decisão
    própria do escritório (não é uma fórmula literal do item 22.4.4.3), a
    mesma relação genérica de tirante de 22.3.3 (As = FSd/fyd,
    ``bielas_tirantes_nbr6118.As_tirante_cm2``), com ``F_kn`` = carga total
    aplicada pela face inferior a ser suspendida e distribuída na região de
    aplicação. ``fyd_kncm2`` é a resistência de cálculo do aço, kN/cm2.
    """
    try:  # executado como script, ou com dimensionamento/ no sys.path
        import bielas_tirantes_nbr6118 as bt
    except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
        from dimensionamento import bielas_tirantes_nbr6118 as bt

    return bt.As_tirante_cm2(F_kn, fyd_kncm2)


@dataclass(frozen=True)
class ResultadoSuspensaoCargaInferior:
    """Resultado, com memória, da suspensão de carga inferior (22.4.4.3)."""

    F_kn: float
    fyd_kncm2: float
    As_susp_cm2: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_suspensao_carga_inferior(
    F_kn: float, fyd_kncm2: float, As_vertical_disponivel_cm2: float | None = None,
) -> ResultadoSuspensaoCargaInferior:
    """Verifica a armadura vertical de suspensão da carga aplicada pela
    face inferior de uma viga-parede (22.4.4.3, PDF p. 206), com memória de
    cálculo. Devolve a área necessária (``suspensao_carga_inferior``) e,
    quando ``As_vertical_disponivel_cm2`` é informada, confere se ela basta
    (``ok``); sem essa informação, ``ok`` reflete só a validade dos dados de
    entrada.
    """
    As_necessaria = suspensao_carga_inferior(F_kn, fyd_kncm2)
    if As_vertical_disponivel_cm2 is None:
        ok = True
        linha_ok = "As,vertical,disponível não informada -> só a área necessária foi calculada."
    else:
        ok = float(As_vertical_disponivel_cm2) + 1e-9 >= As_necessaria
        linha_ok = (
            f"As,vertical,disponível = {float(As_vertical_disponivel_cm2):.3f} cm2 "
            f"{'>= As,necessária -> ok.' if ok else '< As,necessária -> reprovado.'}"
        )
    memoria = (
        "22.4.4.3: carregamento pela face inferior -> a armadura vertical "
        "deve suspender a totalidade da carga aplicada (sem fórmula fechada "
        "na norma; usa-se a relação genérica de tirante de 22.3.3).",
        f"As,susp = F/fyd = {float(F_kn):g}/{float(fyd_kncm2):g} = "
        f"{As_necessaria:.3f} cm2.",
        linha_ok,
    )
    return ResultadoSuspensaoCargaInferior(
        F_kn=float(F_kn), fyd_kncm2=float(fyd_kncm2), As_susp_cm2=As_necessaria,
        ok=ok, governante="22.4.4.3", memoria=memoria,
    )
