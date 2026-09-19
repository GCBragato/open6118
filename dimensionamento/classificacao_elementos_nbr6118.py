"""Classificação de elementos estruturais — ABNT NBR 6118:2026, Seções 14, 18 e 22.

Classifica o elemento antes de escolher o método de análise ou o conjunto de
regras de dimensionamento a aplicar: elemento linear ou de superfície
(14.4.1, 14.4.2.1), viga comum ou viga-parede (14.4.2.2, 18.3.1, 22.4.1),
pilar comum ou pilar-parede (14.4.2.4, 18.4.1), e se a análise plástica de
estruturas reticuladas é permitida (14.5.4).

Norma: ABNT NBR 6118:2026, 5ª edição (11/03/2026). As páginas citadas são as
do PDF (a página impressa é 18 a menos).

Unidades: comprimento e dimensão de seção em cm (``_cm``); os demais
parâmetros são booleanos.

Este módulo só classifica: não reimplementa fórmula de material nem de
esforço resistente (isso é o núcleo normativo, ``nucleo_nbr6118.py``, e os
módulos de dimensionamento por elemento).
"""

from __future__ import annotations

from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError


def _validar_positivo(valor: float, nome: str) -> float:
    """Confere que uma grandeza geométrica (comprimento, dimensão) é > 0."""
    v = float(valor)
    if not (v > 0.0):
        raise ValueError(f"{nome} tem de ser positivo; recebido {v:g}.")
    return v


def _fmt4(valor: float) -> str:
    """Formata um número com 4 casas decimais e vírgula (padrão PT-BR).

    As memórias de cálculo deste módulo são texto em português; usar vírgula
    como separador decimal evita misturar convenções (ponto de ``{:.4f}`` ao
    lado de vírgula no texto literal, como em "razão >= 3,0") dentro da mesma
    linha de memorial.
    """
    return f"{valor:.4f}".replace(".", ",")


# ---------------------------------------------------------------------------
# 14.4.1 — Elemento linear x elemento de superfície (PDF p. 104)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ClassificacaoElementoLinear:
    """Resultado de 14.4.1: elemento linear (barra) x elemento de superfície."""

    comprimento_cm: float
    maior_dimensao_secao_cm: float
    razao: float
    linear: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def eh_elemento_linear(l_cm: float, h_max_cm: float) -> ClassificacaoElementoLinear:
    """Classifica um elemento como linear (barra) ou de superfície (14.4.1).

    São elementos lineares (vigas, pilares, tirantes, arcos) aqueles em que o
    comprimento longitudinal supera em pelo menos 3 vezes a maior dimensão da
    seção transversal:

        l_cm >= 3 * h_max_cm  ->  elemento linear

    O limite é inclusivo (>=): no caso-limite l = 3*h_max, o elemento ainda é
    linear. Abaixo disso, trata-se de elemento de superfície (14.4.2).

    l_cm: comprimento longitudinal do elemento, cm.
    h_max_cm: maior dimensão da seção transversal, cm.

    Fonte: NBR 6118:2026, 14.4.1 (PDF p. 104).
    """
    l = _validar_positivo(l_cm, "l_cm")
    h_max = _validar_positivo(h_max_cm, "h_max_cm")
    razao = l / h_max
    linear = razao >= 3.0
    memoria = (
        f"14.4.1: l/h_max = {l:g}/{h_max:g} = {_fmt4(razao)}.",
        (
            "razão >= 3,0 -> elemento linear (barra)."
            if linear
            else "razão < 3,0 -> elemento de superfície (14.4.2)."
        ),
    )
    return ClassificacaoElementoLinear(
        comprimento_cm=l,
        maior_dimensao_secao_cm=h_max,
        razao=razao,
        linear=linear,
        ok=True,
        governante="14.4.1",
        memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 14.4.2.1 — Placa espessa (PDF p. 104)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ClassificacaoPlaca:
    """Resultado de 14.4.2.1: placa usual x placa espessa."""

    espessura_cm: float
    vao_cm: float
    razao: float
    limite: float
    espessa: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def eh_placa_espessa(h_cm: float, vao_cm: float) -> ClassificacaoPlaca:
    """Classifica uma placa (laje) como espessa quando h > vão/3 (14.4.2.1).

    Placas com espessura maior que 1/3 do vão saem da faixa das hipóteses
    usuais de placa fina e devem ser estudadas como placas espessas, por
    teoria própria:

        h_cm > (1/3) * vao_cm  ->  placa espessa

    O limite é exclusivo (>): no caso-limite h = vão/3, a placa ainda é
    placa usual.

    h_cm: espessura da placa, cm.
    vao_cm: vão da placa, cm.

    Fonte: NBR 6118:2026, 14.4.2.1 (PDF p. 104).
    """
    h = _validar_positivo(h_cm, "h_cm")
    vao = _validar_positivo(vao_cm, "vao_cm")
    limite = vao / 3.0
    razao = h / vao
    espessa = h > limite
    memoria = (
        f"14.4.2.1: h = {h:g} cm, vão/3 = {_fmt4(limite)} cm.",
        (
            "h > vão/3 -> placa espessa (fora das hipóteses de placa fina, "
            "estudar por teoria própria)."
            if espessa
            else "h <= vão/3 -> placa usual (hipóteses de 14.7.1 aplicáveis)."
        ),
    )
    return ClassificacaoPlaca(
        espessura_cm=h,
        vao_cm=vao,
        razao=razao,
        limite=limite,
        espessa=espessa,
        ok=True,
        governante="14.4.2.1",
        memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 14.4.2.4 e 18.4.1 — Pilar x pilar-parede (PDF p. 105 e 173)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ClassificacaoPilar:
    """Resultado de 14.4.2.4/18.4.1: pilar comum x pilar-parede."""

    dimensao_maior_cm: float
    dimensao_menor_cm: float
    razao: float
    limite: float
    pilar_parede: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def eh_pilar_parede(b_cm: float, h_cm: float) -> ClassificacaoPilar:
    """Classifica um pilar como comum ou pilar-parede pela razão 5:1.

    Duas redações da mesma proporção geométrica:

        - 14.4.2.4: há pilar-parede quando, em alguma das superfícies que o
          compõem, a menor dimensão da seção transversal é menor que 1/5 da
          maior (elemento de superfície, plano ou casca cilíndrica).
        - 18.4.1: as exigências de 18.4 (pilares) valem quando a maior
          dimensão da seção transversal não excede 5 vezes a menor; quando
          excede, o pilar deve ser tratado como pilar-parede, com 18.5.
          Não vale para as regiões especiais da Seção 21.

    As duas equivalem à mesma razão (menor < maior/5, ou maior > 5*menor); o
    limite de 5,0 é o caso-limite de pilar comum (o excesso é que muda a
    classificação, não a igualdade):

        dimensao_maior_cm <= 5 * dimensao_menor_cm  ->  pilar comum (18.4)
        dimensao_maior_cm >  5 * dimensao_menor_cm  ->  pilar-parede (18.4.2.4 e 18.5)

    b_cm, h_cm: as duas dimensões da seção transversal do pilar, cm (ordem
    livre; a função identifica maior e menor).

    Não vale para as regiões especiais da Seção 21 (18.4.1).

    Fonte: NBR 6118:2026, 14.4.2.4 (PDF p. 105) e 18.4.1 (PDF p. 173).
    """
    d1 = _validar_positivo(b_cm, "b_cm")
    d2 = _validar_positivo(h_cm, "h_cm")
    maior, menor = (d1, d2) if d1 >= d2 else (d2, d1)
    limite = 5.0 * menor
    razao = maior / menor
    pilar_parede = maior > limite
    memoria = (
        f"18.4.1/14.4.2.4: maior = {maior:g} cm, menor = {menor:g} cm, "
        f"razão = {_fmt4(razao)}.",
        (
            "razão > 5,0 -> pilar-parede (14.4.2.4 e 18.5, além de 18.4.2.4); "
            "não vale para regiões especiais da Seção 21."
            if pilar_parede
            else "razão <= 5,0 -> pilar comum, aplica-se 18.4."
        ),
    )
    return ClassificacaoPilar(
        dimensao_maior_cm=maior,
        dimensao_menor_cm=menor,
        razao=razao,
        limite=limite,
        pilar_parede=pilar_parede,
        ok=True,
        governante="14.4.2.4/18.4.1",
        memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 14.4.2.2, 18.3.1 e 22.4.1 — Viga x viga-parede (PDF p. 104-105, 167 e 204)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ClassificacaoViga:
    """Resultado de 14.4.2.2/18.3.1/22.4.1: viga comum x viga-parede."""

    vao_cm: float
    altura_cm: float
    razao: float
    continua: bool
    limite_especifico: float
    viga_parede_regra_geral: bool
    viga_parede_regra_especifica: bool
    viga_parede: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def eh_viga_parede(l_cm: float, h_cm: float, continua: bool) -> ClassificacaoViga:
    """Classifica uma viga (chapa) como viga comum ou viga-parede.

    Duas regras da norma, com escopos diferentes:

        - 14.4.2.2 (regra geral das chapas): há viga-parede quando o vão é
          menor que 3 vezes a maior dimensão da seção transversal
          (l_cm < 3 * h_cm), sem distinguir isostática de contínua.
        - 18.3.1 e 22.4.1 (regra específica de vigas, mais refinada): as
          prescrições de 18.3 (vigas comuns) valem para viga isostática com
          l/h >= 2,0 e para viga contínua com l/h >= 3,0; l é o vão teórico
          (o dobro do comprimento teórico, no caso de balanço) e h a altura
          total da viga. Abaixo desses limites, 22.4.1 trata a viga como
          viga-parede (Seção 22).

    A regra específica (18.3.1/22.4.1) é quem governa a classificação final,
    por ser a redação mais recente e mais fina, escrita especificamente para
    vigas (a de 14.4.2.2 é a definição geral de "chapas", da qual viga é um
    caso). As duas regras concordam sempre para viga contínua (mesmo limite,
    l/h < 3,0) e para viga isostática fora da faixa 2,0 <= l/h < 3,0; só
    divergem para viga isostática com 2,0 <= l/h < 3,0, onde 14.4.2.2 marcaria
    viga-parede e 18.3.1/22.4.1 não — a divergência fica registrada na
    memória e em ``viga_parede_regra_geral``.

    l_cm: vão teórico da viga, cm (o dobro do vão teórico, se em balanço).
    h_cm: altura total da seção transversal, cm.
    continua: True para viga contínua, False para viga isostática (biapoiada).

    Fonte: NBR 6118:2026, 14.4.2.2 (PDF p. 104-105), 18.3.1 (PDF p. 167) e
    22.4.1 (PDF p. 204).
    """
    l = _validar_positivo(l_cm, "l_cm")
    h = _validar_positivo(h_cm, "h_cm")
    razao = l / h
    limite_especifico = 3.0 if continua else 2.0

    regra_geral = razao < 3.0  # 14.4.2.2
    regra_especifica = razao < limite_especifico  # 18.3.1/22.4.1

    viga_parede = regra_especifica
    divergem = regra_geral != regra_especifica

    linhas = [
        f"14.4.2.2/18.3.1/22.4.1: l/h = {l:g}/{h:g} = {_fmt4(razao)} "
        f"({'contínua' if continua else 'isostática'}).",
        (
            "14.4.2.2 (regra geral): l/h < 3,0 -> viga-parede."
            if regra_geral
            else "14.4.2.2 (regra geral): l/h >= 3,0 -> não é viga-parede por essa regra."
        ),
        (
            f"18.3.1/22.4.1 (regra específica, limite {limite_especifico:g}): "
            f"l/h < {limite_especifico:g} -> viga-parede."
            if regra_especifica
            else f"18.3.1/22.4.1 (regra específica, limite {limite_especifico:g}): "
            f"l/h >= {limite_especifico:g} -> viga comum, aplica-se 18.3."
        ),
    ]
    if divergem:
        linhas.append(
            "Divergência: a regra geral de 14.4.2.2 e a regra específica de "
            "18.3.1/22.4.1 discordam nesta faixa (viga isostática com "
            "2,0 <= l/h < 3,0); prevalece a regra específica de 18.3.1/22.4.1."
        )
    linhas.append(
        f"Classificação final: {'viga-parede' if viga_parede else 'viga comum'} "
        "(governa 18.3.1/22.4.1)."
    )

    return ClassificacaoViga(
        vao_cm=l,
        altura_cm=h,
        razao=razao,
        continua=bool(continua),
        limite_especifico=limite_especifico,
        viga_parede_regra_geral=regra_geral,
        viga_parede_regra_especifica=regra_especifica,
        viga_parede=viga_parede,
        ok=True,
        governante="18.3.1/22.4.1",
        memoria=tuple(linhas),
    )


# ---------------------------------------------------------------------------
# 14.5.4 — Restrições à análise plástica (PDF p. 106)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AnalisePlastica:
    """Resultado de 14.5.4: análise plástica de estruturas reticuladas permitida ou não."""

    segunda_ordem_global: bool
    dutilidade_suficiente: bool
    risco_fadiga: bool
    permitida: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def analise_plastica_permitida(
    segunda_ordem_global: bool,
    dutilidade_suficiente: bool,
    risco_fadiga: bool = False,
) -> AnalisePlastica:
    """Diz se a análise plástica de uma estrutura reticulada é permitida (14.5.4).

    A análise estrutural é denominada plástica quando as não linearidades
    puderem ser consideradas (materiais rígido-plásticos perfeitos ou
    elastoplásticos perfeitos), e só serve para verificações de ELU. A norma
    proíbe a análise plástica de estruturas reticuladas quando:

        a) se consideram os efeitos de 2ª ordem global; ou
        b) não houver dutilidade suficiente para que as configurações de
           rótula adotadas sejam atingidas.

    Além disso, no caso de carregamento cíclico com possibilidade de fadiga,
    deve-se evitar o cálculo plástico (Seção 23):

        permitida = NÃO segunda_ordem_global E dutilidade_suficiente E NÃO risco_fadiga

    segunda_ordem_global: True se a análise considera efeitos globais de 2ª
        ordem.
    dutilidade_suficiente: True se há dutilidade suficiente para que as
        configurações de rótula plástica adotadas sejam atingidas.
    risco_fadiga: True se há carregamento cíclico com possibilidade de
        fadiga. Padrão False (reproduz o critério anterior a este pacote,
        que só considerava (a) e (b)).

    Fonte: NBR 6118:2026, 14.5.4 (PDF p. 106).
    """
    seg_ordem = bool(segunda_ordem_global)
    dutil = bool(dutilidade_suficiente)
    fadiga = bool(risco_fadiga)

    motivos: list[str] = []
    if seg_ordem:
        motivos.append(
            "consideram-se efeitos de 2ª ordem global (14.5.4-a)."
        )
    if not dutil:
        motivos.append(
            "não há dutilidade suficiente para as configurações de rótula "
            "adotadas (14.5.4-b)."
        )
    if fadiga:
        motivos.append(
            "há carregamento cíclico com possibilidade de fadiga; deve-se "
            "evitar o cálculo plástico (14.5.4, último parágrafo; ver Seção 23)."
        )

    permitida = not motivos
    memoria = (
        f"14.5.4: 2ª ordem global = {seg_ordem}, dutilidade suficiente = "
        f"{dutil}, risco de fadiga = {fadiga}.",
        (
            "Nenhuma restrição aplicável -> análise plástica permitida."
            if permitida
            else "Análise plástica NÃO permitida: " + " ".join(motivos)
        ),
    )
    return AnalisePlastica(
        segunda_ordem_global=seg_ordem,
        dutilidade_suficiente=dutil,
        risco_fadiga=fadiga,
        permitida=permitida,
        ok=permitida,
        governante="14.5.4",
        memoria=memoria,
    )
