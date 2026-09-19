"""Protensão: introdução da força e detalhamento de cabos — ABNT NBR 6118:2026.

Cobre (as páginas são as do PDF; a impressa é 18 a menos):
    - 9.6.2.2  ângulo de difusão β da protensão, casos de pós-tração (p. 68);
    - 9.6.2.3  distância de regularização ℓp, casos de pré-tração (p. 69);
    - 18.6.1.2 raio mínimo de curvatura dos cabos de protensão (p. 175);
    - 18.6.1.5 comprimento mínimo dos trechos retos nas extremidades dos
      cabos (p. 175);
    - 18.6.2.2 agrupamento de cabos em bainhas, pós-tração (p. 176);
    - 18.6.2.3 Tabela 18.1 (espaçamentos mínimos, pós-tração) e Tabela 18.2
      (espaçamentos mínimos, pré-tração) (p. 177).

A ancoragem por aderência da armadura ativa (9.3.2.2 e 9.4.5) está em
``ancoragem_nbr6118`` (fbpd, ηp2, ℓbp, ℓbpt, ℓbpd); este módulo cobre a
introdução da força ao concreto e o traçado/arranjo dos cabos.

Convenções: diâmetro em mm, comprimento em cm, ângulo em graus.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr


# ---------------------------------------------------------------------------
# 9.6.2.2 — Ângulo de difusão da protensão, casos de pós-tração (PDF p. 68)
# ---------------------------------------------------------------------------
def angulo_difusao_beta_graus() -> float:
    """Ângulo de abertura β do cone de difusão da força de protensão a
    partir da ancoragem, em casos de pós-tração (9.6.2.2, PDF p. 68).

    tg(β) = 2/3 (Figura 9.7). Usado para achar a distância de regularização
    das tensões em elementos pós-tracionados: a difusão parte da ancoragem
    dentro desse ângulo e, se atingir o plano médio da mesa a partir da
    alma, a difusão ao longo da mesa também segue o mesmo ângulo β.
    """
    return math.degrees(math.atan(2.0 / 3.0))


# ---------------------------------------------------------------------------
# 9.6.2.3 — Distância de regularização, casos de pré-tração (PDF p. 69)
# ---------------------------------------------------------------------------
def lp_regularizacao_cm(h_cm: float, lbpt_cm: float) -> float:
    """ℓp, distância de regularização das tensões de protensão em elementos
    pré-tracionados, cm (9.6.2.3, PDF p. 69).

    ℓp = raiz(h² + (0,6*ℓbpt)²) >= ℓbpt, com h a altura do elemento
    estrutural e ℓbpt o comprimento de transferência (9.4.5.2,
    ``ancoragem_nbr6118.lbpt_cm``). A partir de ℓp, as tensões de protensão
    podem ser consideradas linearmente distribuídas na seção. Para seções
    não retangulares, a norma permite calcular de forma semelhante à de
    9.6.2.2 (pós-tração), fora do escopo desta função.
    """
    lp = math.sqrt(h_cm ** 2 + (0.6 * lbpt_cm) ** 2)
    return max(lp, lbpt_cm)


# ---------------------------------------------------------------------------
# 18.6.1.2 — Raio mínimo de curvatura dos cabos de protensão (PDF p. 175)
# ---------------------------------------------------------------------------
RAIO_MINIMO_CURVATURA_M = {
    "fio": 4.0,
    "barra": 8.0,
    "cordoalha": 12.0,
}


def raio_minimo_curvatura_m(tipo: str) -> float:
    """Raio mínimo de curvatura, em metros, acima do qual se dispensa
    justificativa (ensaio) para a curvatura da armadura de protensão
    (18.6.1.2, PDF p. 175): 4 m para fios, 8 m para barras e 12 m para
    cordoalhas.

    Valores menores exigem investigação experimental adequadamente
    documentada (a norma não veda o raio menor, exige a justificativa —
    por isso esta função só devolve o piso dispensado de ensaio, sem
    levantar erro para um raio candidato menor: quem chama compara o raio
    de projeto com este piso e decide se documenta o ensaio).
    Nas proximidades das ancoragens (18.6.1.3), o raio mínimo pode ser
    reduzido, também mediante ensaio devidamente documentado.
    """
    chave = nbr._chave(tipo)
    if chave not in RAIO_MINIMO_CURVATURA_M:
        raise ValueError(
            f"tipo deve ser 'fio', 'barra' ou 'cordoalha': {tipo!r}"
        )
    return RAIO_MINIMO_CURVATURA_M[chave]


# ---------------------------------------------------------------------------
# 18.6.1.5 — Extremidades retas dos cabos de protensão (PDF p. 175)
# ---------------------------------------------------------------------------
def trecho_reto_extremidade_min_cm(monocordoalha_engraxada: bool = False) -> float:
    """Comprimento mínimo, em cm, do segmento reto na extremidade do cabo de
    protensão, necessário para alinhar o eixo do cabo com o eixo do
    dispositivo de ancoragem (18.6.1.5, PDF p. 175): 100 cm em geral; 50 cm
    no caso de monocordoalhas engraxadas.
    """
    return 50.0 if monocordoalha_engraxada else 100.0


# ---------------------------------------------------------------------------
# 18.6.2.2 — Agrupamento de cabos em bainhas, pós-tração (PDF p. 176)
# ---------------------------------------------------------------------------
MAX_CABOS_POR_BAINHA_TRECHO_RETO = 4
MAX_CABOS_ADJACENTES_EM_LINHA = 2
MAX_CABOS_POR_BAINHA_TRECHO_CURVO = 2


@dataclass(frozen=True)
class ResultadoAgrupamentoCabos:
    num_cabos_por_bainha: int
    trecho: str
    cabos_adjacentes_em_linha: int | None
    planos_paralelos: bool | None
    max_cabos_por_bainha: int
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_agrupamento_cabos(
    num_cabos_por_bainha: int,
    trecho: str = "reto",
    cabos_adjacentes_em_linha: int | None = None,
    planos_paralelos: bool | None = None,
) -> ResultadoAgrupamentoCabos:
    """Verifica os limites de agrupamento de cabos alojados numa mesma
    bainha, casos de pós-tração (18.6.2.2, PDF p. 176).

    trecho='reto': grupos de até 2, 3 ou 4 cabos, desde que não ocorram
    disposições em linha com mais de 2 cabos adjacentes
    (``cabos_adjacentes_em_linha``, se informado).
    trecho='curvo': só é permitido agrupar em pares (no máximo 2 cabos por
    bainha), com as curvaturas em planos paralelos, de modo a não existir
    pressão transversal entre eles (``planos_paralelos``, se informado;
    None não reprova essa condição, por falta de informação).
    """
    chave = nbr._chave(trecho)
    if chave == "reto":
        max_cabos = MAX_CABOS_POR_BAINHA_TRECHO_RETO
        ok_qtd = 1 <= num_cabos_por_bainha <= max_cabos
        ok_linha = (cabos_adjacentes_em_linha is None
                    or cabos_adjacentes_em_linha <= MAX_CABOS_ADJACENTES_EM_LINHA)
        ok = ok_qtd and ok_linha
        if not ok_qtd:
            governante = (f"18.6.2.2: trecho reto admite no máximo "
                          f"{max_cabos} cabos por bainha")
        elif not ok_linha:
            governante = ("18.6.2.2: trecho reto não admite mais de "
                          f"{MAX_CABOS_ADJACENTES_EM_LINHA} cabos adjacentes "
                          "em linha")
        else:
            governante = "18.6.2.2: atende o agrupamento em trecho reto"
        memoria = (
            f"trecho reto: {num_cabos_por_bainha} cabo(s) por bainha "
            f"(máximo {max_cabos}) -> {'ok' if ok_qtd else 'não ok'}.",
            f"cabos adjacentes em linha: "
            f"{cabos_adjacentes_em_linha if cabos_adjacentes_em_linha is not None else 'não informado'} "
            f"(máximo {MAX_CABOS_ADJACENTES_EM_LINHA}) -> "
            f"{'ok' if ok_linha else 'não ok'}.",
        )
        return ResultadoAgrupamentoCabos(
            num_cabos_por_bainha=num_cabos_por_bainha, trecho="reto",
            cabos_adjacentes_em_linha=cabos_adjacentes_em_linha,
            planos_paralelos=None, max_cabos_por_bainha=max_cabos,
            ok=ok, governante=governante, memoria=memoria,
        )
    if chave == "curvo":
        max_cabos = MAX_CABOS_POR_BAINHA_TRECHO_CURVO
        ok_qtd = 1 <= num_cabos_por_bainha <= max_cabos
        ok_planos = planos_paralelos is None or planos_paralelos
        ok = ok_qtd and ok_planos
        if not ok_qtd:
            governante = (f"18.6.2.2: trecho curvo só admite pares (no "
                          f"máximo {max_cabos} cabos por bainha)")
        elif not ok_planos:
            governante = ("18.6.2.2: trecho curvo exige curvaturas em "
                          "planos paralelos, sem pressão transversal entre "
                          "os cabos")
        else:
            governante = "18.6.2.2: atende o agrupamento em trecho curvo"
        memoria = (
            f"trecho curvo: {num_cabos_por_bainha} cabo(s) por bainha "
            f"(máximo {max_cabos}, só em pares) -> "
            f"{'ok' if ok_qtd else 'não ok'}.",
            f"curvaturas em planos paralelos: "
            f"{planos_paralelos if planos_paralelos is not None else 'não informado'} "
            f"-> {'ok' if ok_planos else 'não ok'}.",
        )
        return ResultadoAgrupamentoCabos(
            num_cabos_por_bainha=num_cabos_por_bainha, trecho="curvo",
            cabos_adjacentes_em_linha=None, planos_paralelos=planos_paralelos,
            max_cabos_por_bainha=max_cabos,
            ok=ok, governante=governante, memoria=memoria,
        )
    raise ValueError(f"trecho deve ser 'reto' ou 'curvo': {trecho!r}")


# ---------------------------------------------------------------------------
# 18.6.2.3 — Espaçamentos mínimos: Tabela 18.1 (pós-tração) e Tabela 18.2
# (pré-tração) (PDF p. 177)
# ---------------------------------------------------------------------------
# TABELA_18_1: disposicao -> (mult_phi_ext_ah, piso_ah_cm, mult_phi_ext_av, piso_av_cm)
TABELA_18_1 = {
    "isoladas": (1.0, 4.0, 1.0, 5.0),
    "agrupadas": (1.2, 4.0, 1.5, 5.0),
}

# TABELA_18_2: disposicao -> (mult_phi_ah, mult_dmax_ah, piso_ah_cm,
#                              mult_phi_av, mult_dmax_av, piso_av_cm)
TABELA_18_2 = {
    "isolados": (2.0, 1.2, 2.0, 2.0, 1.2, 2.0),
    "pares_horizontal": (3.0, 1.2, 2.5, 3.0, 1.2, 2.0),
    "pares_ambas_direcoes": (3.0, 1.2, 3.0, 3.0, 1.2, 3.0),
}

# nbr._chave() tira também o sublinhado ("pares_horizontal" ->
# "pareshorizontal"): os aliases normalizam a chave informada para a chave
# canônica das tabelas acima (mesmo padrão de fadiga_nbr6118.py).
_ALIASES_TABELA_18_1 = {nbr._chave(k): k for k in TABELA_18_1}
_ALIASES_TABELA_18_2 = {nbr._chave(k): k for k in TABELA_18_2}


@dataclass(frozen=True)
class ResultadoEspacamentoMinimo:
    disposicao: str
    ah_min_cm: float
    av_min_cm: float
    governante: str
    memoria: tuple[str, ...]


def espacamento_min_bainhas_cm(phi_ext_mm: float,
                               disposicao: str = "isoladas") -> ResultadoEspacamentoMinimo:
    """Espaçamentos livres mínimos, horizontal (ah) e vertical (av), entre
    bainhas de protensão, casos de pós-tração (Tabela 18.1, 18.6.2.3, PDF
    p. 177).

    disposicao='isoladas': ah >= φext e >= 4 cm; av >= φext e >= 5 cm.
    disposicao='agrupadas' (grupos de 2 a 4 cabos por bainha, 18.6.2.2):
    ah >= 1,2*φext e >= 4 cm; av >= 1,5*φext e >= 5 cm.
    φext é o diâmetro externo da bainha, informado em mm e convertido para
    cm dentro da função.
    """
    chave = _ALIASES_TABELA_18_1.get(nbr._chave(disposicao))
    if chave is None:
        raise ValueError(
            f"disposição deve ser 'isoladas' ou 'agrupadas': {disposicao!r}"
        )
    mult_ah, piso_ah, mult_av, piso_av = TABELA_18_1[chave]
    phi_ext_cm = phi_ext_mm / 10.0
    ah = max(mult_ah * phi_ext_cm, piso_ah)
    av = max(mult_av * phi_ext_cm, piso_av)
    governante = f"Tabela 18.1: bainhas {chave}"
    memoria = (
        f"φext = {phi_ext_mm:g} mm = {phi_ext_cm:g} cm; disposição {chave}.",
        f"ah,mín = máx({mult_ah:g}*φext, {piso_ah:g} cm) = "
        f"máx({mult_ah * phi_ext_cm:.2f}, {piso_ah:g}) = {ah:.2f} cm.",
        f"av,mín = máx({mult_av:g}*φext, {piso_av:g} cm) = "
        f"máx({mult_av * phi_ext_cm:.2f}, {piso_av:g}) = {av:.2f} cm.",
    )
    return ResultadoEspacamentoMinimo(
        disposicao=chave, ah_min_cm=ah, av_min_cm=av,
        governante=governante, memoria=memoria,
    )


def espacamento_min_fios_cm(phi_mm: float, dmax_mm: float,
                            disposicao: str = "isolados") -> ResultadoEspacamentoMinimo:
    """Espaçamentos livres mínimos, horizontal (ah) e vertical (av), entre
    fios ou cordoalhas de protensão, casos de pré-tração (Tabela 18.2,
    18.6.2.3, PDF p. 177).

    disposicao='isolados': ah, av >= 2*φ, >= 1,2*dmáx e >= 2 cm.
    disposicao='pares_horizontal' (pares na direção horizontal): ah >= 3*φ,
    >= 1,2*dmáx e >= 2,5 cm; av >= 3*φ, >= 1,2*dmáx e >= 2 cm.
    disposicao='pares_ambas_direcoes' (pares nas duas direções): ah, av >=
    3*φ, >= 1,2*dmáx e >= 3 cm.
    φ é o diâmetro do fio ou cordoalha e dmáx a dimensão máxima do agregado
    graúdo, ambos informados em mm (dmáx convertida para cm dentro da
    função, como φ).
    """
    chave = _ALIASES_TABELA_18_2.get(nbr._chave(disposicao))
    if chave is None:
        raise ValueError(
            "disposição deve ser 'isolados', 'pares_horizontal' ou "
            f"'pares_ambas_direcoes': {disposicao!r}"
        )
    mult_phi_ah, mult_dmax_ah, piso_ah, mult_phi_av, mult_dmax_av, piso_av = TABELA_18_2[chave]
    phi_cm = phi_mm / 10.0
    dmax_cm = dmax_mm / 10.0
    ah = max(mult_phi_ah * phi_cm, mult_dmax_ah * dmax_cm, piso_ah)
    av = max(mult_phi_av * phi_cm, mult_dmax_av * dmax_cm, piso_av)
    governante = f"Tabela 18.2: {chave}"
    memoria = (
        f"φ = {phi_mm:g} mm = {phi_cm:g} cm; dmáx = {dmax_mm:g} mm = "
        f"{dmax_cm:g} cm; disposição {chave}.",
        f"ah,mín = máx({mult_phi_ah:g}*φ, {mult_dmax_ah:g}*dmáx, "
        f"{piso_ah:g} cm) = máx({mult_phi_ah * phi_cm:.2f}, "
        f"{mult_dmax_ah * dmax_cm:.2f}, {piso_ah:g}) = {ah:.2f} cm.",
        f"av,mín = máx({mult_phi_av:g}*φ, {mult_dmax_av:g}*dmáx, "
        f"{piso_av:g} cm) = máx({mult_phi_av * phi_cm:.2f}, "
        f"{mult_dmax_av * dmax_cm:.2f}, {piso_av:g}) = {av:.2f} cm.",
    )
    return ResultadoEspacamentoMinimo(
        disposicao=chave, ah_min_cm=ah, av_min_cm=av,
        governante=governante, memoria=memoria,
    )
