"""Durabilidade, cobrimento e abertura de fissura admissível — ABNT NBR 6118:2026.

Fecha o fluxo ambiente -> CAA -> a/c, classe mínima, cobrimento e wk,máx num
lugar só. Cobre a Seção 5.3.2 (Tabela 5.1, classes de consequência), a
Seção 6 (durabilidade e vida útil), a Seção 6.4 (Tabela 6.1, classes de
agressividade ambiental), a Seção 7.4 (Tabela 7.1, qualidade do concreto; e
7.4.7, cobrimento) e a Seção 13.4.2 (Tabela 13.4, wk,máx), com uma
normalização única de CAA (nucleo_nbr6118.normalizar_caa).

Convenções: tensão e fck em MPa; comprimentos de cobrimento e diâmetro em
mm; página do PDF citada em cada função (impressa = PDF - 18). Fora da
faixa de validade, as funções levantam ``FaixaNormativaError`` (subclasse
de ``ValueError``, importada do núcleo); célula que a norma não define
levanta ``ValueError`` comum, explicando o motivo.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError
AvisoNBR6118 = nbr.AvisoNBR6118


# ---------------------------------------------------------------------------
# Classes de consequência — Tabela 5.1 (5.3.2, PDF p. 32-33)
# ---------------------------------------------------------------------------
# Casos típicos citados literalmente na Tabela 5.1, normalizados (sem acento,
# espaço, hífen). Usados por classe_consequencia() como palavras-chave de
# reconhecimento em tipo_obra; qualquer um deles classifica direto em CC3.
TABELA_5_1_CC3_TIPOS = (
    "arquibancada", "saladeconcertos", "cinema", "teatro", "hospital",
    "escola", "ginasio", "arenamultiuso", "shoppingcenter",
    "estacaoferroviaria", "estacaometroviaria", "estacaoaquaviaria",
    "aeroporto", "ponte", "viaduto", "passarela", "obraindustrial",
    "obraportuaria", "obramineracao", "obratelecomunicacoes",
    "obraenergia", "estadio", "centrodeconvencoes", "barragem",
    "obrahidraulica", "marquise", "silo",
)


def classe_consequencia(
    tipo_obra: str = "",
    *,
    pavimentos_habitaveis: int | None = None,
    unifamiliar: bool | None = None,
    subsolo: bool = False,
    altura_muro_m: float | None = None,
    balanco_m: float | None = None,
    protendida: bool = False,
    reforma_elimina_pilar: bool = False,
    acrescimo_carga_pct: float | None = None,
    agricola_nao_ocupado: bool | None = None,
) -> str:
    """Classe de consequência CC1/CC2/CC3 pela Tabela 5.1 (5.3.2), p. 32-33.

    ``tipo_obra`` é uma descrição livre em português (ex.: "prédio
    residencial de 6 pavimentos", "casa térrea unifamiliar"); a função
    procura nela as palavras-chave dos casos típicos da Tabela 5.1
    (hospital, escola, ponte, silo etc., que são sempre CC3), a contagem de
    pavimentos ("N pavimentos") e "unifamiliar"/"térrea"/"agrícola" quando
    os argumentos nomeados equivalentes não são passados explicitamente.
    Os argumentos nomeados têm prioridade sobre o texto e permitem
    reproduzir cada célula da tabela sem depender de reconhecimento de
    texto: CC3 se protendida, subsolo, altura_muro_m > 2,5 m,
    balanco_m > 3 m, reforma_elimina_pilar, acrescimo_carga_pct > 5 % ou
    mais de 5 pavimentos habitáveis (edifício multifamiliar/comercial); CC2
    se muro <= 2,5 m, edifício multifamiliar/comercial com até 5
    pavimentos, ou reforma sem eliminação de pilar com acréscimo <= 5 %;
    CC1 se agrícola não ocupado permanentemente, ou unifamiliar com até 2
    pavimentos. Em caso de dúvida (nada bate), a função adota CC3, como
    manda 5.3.3 ("Caso, por algum motivo, haja dúvidas sobre a classe de
    consequência, deve-se adotar a classe CC3 para análise").
    """
    chave = nbr._chave(tipo_obra)

    if pavimentos_habitaveis is None:
        m = re.search(r"(\d+)\s*paviment", tipo_obra, re.IGNORECASE)
        if m:
            pavimentos_habitaveis = int(m.group(1))
    if unifamiliar is None:
        unifamiliar = ("unifamiliar" in chave) or ("terrea" in chave) or ("terreo" in chave)
    if agricola_nao_ocupado is None:
        agricola_nao_ocupado = "agricola" in chave

    # --- CC3 --------------------------------------------------------------
    if protendida:
        return "CC3"
    if subsolo:
        return "CC3"
    if altura_muro_m is not None and altura_muro_m > 2.5:
        return "CC3"
    if balanco_m is not None and balanco_m > 3.0:
        return "CC3"
    if reforma_elimina_pilar:
        return "CC3"
    if acrescimo_carga_pct is not None and acrescimo_carga_pct > 5.0:
        return "CC3"
    if pavimentos_habitaveis is not None and not unifamiliar and pavimentos_habitaveis > 5:
        return "CC3"
    if chave and any(p in chave or chave in p for p in TABELA_5_1_CC3_TIPOS):
        return "CC3"

    # --- CC2 ----------------------------------------------------------
    if altura_muro_m is not None:
        return "CC2"
    if pavimentos_habitaveis is not None and not unifamiliar:
        return "CC2"
    if acrescimo_carga_pct is not None and acrescimo_carga_pct <= 5.0:
        return "CC2"

    # --- CC1 ----------------------------------------------------------
    if agricola_nao_ocupado:
        return "CC1"
    if unifamiliar and (pavimentos_habitaveis is None or pavimentos_habitaveis <= 2):
        return "CC1"

    # 5.3.3 — em dúvida, adotar CC3 para análise.
    return "CC3"


# ---------------------------------------------------------------------------
# Vida útil de projeto — 6.1, 6.2.4 (PDF p. 34)
# ---------------------------------------------------------------------------
# 6.2.4: "Os procedimentos e requisitos desta Norma consideram a vida útil
# de projeto de 50 anos." É o horizonte de tempo pressuposto por todos os
# demais critérios de durabilidade (6.1) — CAA, cobrimento, wk,máx etc.
VIDA_UTIL_PROJETO_ANOS = 50


# ---------------------------------------------------------------------------
# Classes de agressividade ambiental — Tabela 6.1 (6.4, PDF p. 36)
# ---------------------------------------------------------------------------
# chave normalizada -> (índice da classe 0..3, notas de abrandamento aplicáveis)
TABELA_6_1 = {
    "rural": (0, frozenset()),
    "submerso": (0, frozenset()),
    "urbano": (1, frozenset({"a", "b"})),
    "marinho": (2, frozenset({"a"})),
    "industrial": (2, frozenset({"a", "b"})),
    "industrialquimico": (3, frozenset({"a", "c"})),
    "industrialagressivo": (3, frozenset({"a", "c"})),
    "respingosdemare": (3, frozenset()),
}
_ROMANOS_CAA = ("I", "II", "III", "IV")


def classe_agressividade(ambiente: str, microclima_seco: bool = False,
                         revestido: bool = False) -> str:
    """CAA I a IV pela Tabela 6.1 (6.4, p. 36), com as notas a/b/c.

    ambiente: 'rural' ou 'submerso' (CAA I); 'urbano' (CAA II); 'marinho'
    ou 'industrial' (CAA III, industrial comum); 'industrial químico'
    (também aceita 'industrial agressivo', a nota c: tanques industriais,
    galvanoplastia, fertilizantes, indústria química, solo/água
    contaminados) ou 'respingos de maré' (CAA IV).

    revestido=True usa a nota a (ambiente interno com microclima
    controlado — salas, dormitórios, banheiros — ou face com concreto
    revestido com argamassa e pintura): admite uma classe mais branda.
    microclima_seco=True usa a nota b (clima seco, UR <= 65 %, ou parte da
    estrutura protegida de chuva): idem. As duas notas não se acumulam (no
    máximo uma classe mais branda mesmo com as duas condições simultâneas;
    a norma não autoriza reduzir duas classes de uma vez). Levanta
    ValueError se a nota pedida não existir para o ambiente informado
    (p.ex. nota b para 'marinho', ou qualquer nota para 'respingos de
    maré').
    """
    chave = nbr._chave(ambiente)
    if chave not in TABELA_6_1:
        raise ValueError(
            f"Ambiente desconhecido: {ambiente!r}. Use um destes: {', '.join(sorted(TABELA_6_1))}."
        )
    indice, notas = TABELA_6_1[chave]
    reduz = False
    if revestido:
        if "a" not in notas:
            raise ValueError(
                f"A nota a (ambiente interno ou face revestida) não se aplica a {ambiente!r}."
            )
        reduz = True
    if microclima_seco:
        if "b" not in notas:
            raise ValueError(f"A nota b (clima seco, UR<=65%) não se aplica a {ambiente!r}.")
        reduz = True
    if reduz:
        indice = max(0, indice - 1)
    return _ROMANOS_CAA[indice]


# ---------------------------------------------------------------------------
# Qualidade do concreto de cobrimento — Tabela 7.1 (7.4.2, PDF p. 38)
# ---------------------------------------------------------------------------
TABELA_7_1_AC_MAXIMA = {   # relação a/c em massa, CAA I, II, III, IV
    "armado": (0.65, 0.60, 0.55, 0.45),
    "protendido": (0.60, 0.55, 0.50, 0.45),
}
TABELA_7_1_CLASSE_MINIMA = {   # classe de concreto mínima (ABNT NBR 8953)
    "armado": (20, 25, 30, 40),
    "protendido": (25, 30, 35, 40),
}


def relacao_ac_maxima(caa: str, protendido: bool = False) -> float:
    """Relação água/cimento máxima em massa, pela Tabela 7.1 (7.4.2, p. 38)."""
    tipo = "protendido" if protendido else "armado"
    indice = _ROMANOS_CAA.index(nbr.normalizar_caa(caa))
    return TABELA_7_1_AC_MAXIMA[tipo][indice]


def classe_concreto_minima(caa: str, protendido: bool = False) -> int:
    """Classe de concreto mínima (ABNT NBR 8953), pela Tabela 7.1 (7.4.2, p. 38).

    Devolve o número da classe (ex.: 30 para C30), sem o prefixo 'C'.
    """
    tipo = "protendido" if protendido else "armado"
    indice = _ROMANOS_CAA.index(nbr.normalizar_caa(caa))
    return TABELA_7_1_CLASSE_MINIMA[tipo][indice]


# ---------------------------------------------------------------------------
# Cobrimento nominal mínimo por barra/feixe/bainha — 7.4.7.5 (PDF p. 39)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoCobrimento:
    cnom_mm: float
    phi_mm: float
    phi_feixe_mm: float | None
    phi_bainha_mm: float | None
    minimo_barra_mm: float
    minimo_feixe_mm: float | None
    minimo_bainha_mm: float | None
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def phi_feixe_mm(phi_mm: float, n_barras: int) -> float:
    """Diâmetro equivalente do feixe de barras, mm (7.4.7.5, item e).

    φn = φ·√n (n = número de barras do feixe, cf. 9.4.2). Fachada de
    ``nucleo_nbr6118.phi_n_feixe`` (promovida ao núcleo no P24, por ser a
    mesma conta usada também no detalhamento de vigas e pilares).
    """
    return nbr.phi_n_feixe(phi_mm, n_barras)


def verificar_cobrimento(cnom_mm: float, phi_mm: float,
                         phi_feixe_mm: float | None = None,
                         phi_bainha_mm: float | None = None) -> ResultadoCobrimento:
    """Confere cnom contra os mínimos de 7.4.7.5, p. 39.

    d) cnom >= φ da barra;
    e) cnom >= φ do feixe (φn = φ·√n; ver phi_feixe_mm);
    f) cnom >= 0,5·φ da bainha.

    Quando cnom não atende o mínimo governante, emite AvisoNBR6118 (o
    cálculo prossegue com ok=False, para o chamador decidir).
    """
    minimo_barra = float(phi_mm)
    minimo_feixe = float(phi_feixe_mm) if phi_feixe_mm is not None else None
    minimo_bainha = 0.5 * float(phi_bainha_mm) if phi_bainha_mm is not None else None

    candidatos = [("barra (7.4.7.5 d)", minimo_barra)]
    if minimo_feixe is not None:
        candidatos.append(("feixe (7.4.7.5 e)", minimo_feixe))
    if minimo_bainha is not None:
        candidatos.append(("bainha (7.4.7.5 f)", minimo_bainha))
    governante, minimo_governante = max(candidatos, key=lambda c: c[1])

    cnom = float(cnom_mm)
    ok = cnom + 1e-9 >= minimo_governante
    memoria = [
        f"7.4.7.5 d) cnom >= phi_barra: {cnom:g} mm >= {minimo_barra:g} mm "
        f"-> {'ok' if cnom + 1e-9 >= minimo_barra else 'não ok'}"
    ]
    if minimo_feixe is not None:
        memoria.append(
            f"7.4.7.5 e) cnom >= phi_feixe: {cnom:g} mm >= {minimo_feixe:g} mm "
            f"-> {'ok' if cnom + 1e-9 >= minimo_feixe else 'não ok'}"
        )
    if minimo_bainha is not None:
        memoria.append(
            f"7.4.7.5 f) cnom >= 0,5*phi_bainha: {cnom:g} mm >= {minimo_bainha:g} mm "
            f"-> {'ok' if cnom + 1e-9 >= minimo_bainha else 'não ok'}"
        )
    memoria.append(
        f"Governante: {governante}; cnom = {cnom:g} mm "
        f"{'atende' if ok else 'não atende'} o mínimo de {minimo_governante:g} mm."
    )

    if not ok:
        warnings.warn(
            f"cnom = {cnom:g} mm não atende o mínimo de 7.4.7.5 ({governante} "
            f"exige {minimo_governante:g} mm).",
            AvisoNBR6118,
            stacklevel=2,
        )

    return ResultadoCobrimento(
        cnom_mm=cnom,
        phi_mm=float(phi_mm),
        phi_feixe_mm=minimo_feixe,
        phi_bainha_mm=(float(phi_bainha_mm) if phi_bainha_mm is not None else None),
        minimo_barra_mm=minimo_barra,
        minimo_feixe_mm=minimo_feixe,
        minimo_bainha_mm=minimo_bainha,
        ok=ok,
        governante=governante,
        memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# Agregado graúdo — 7.4.7.6 (PDF p. 39)
# ---------------------------------------------------------------------------
def dmax_agregado_mm(cnom_mm: float) -> float:
    """Dimensão máxima característica admissível do agregado graúdo, mm.

    dmáx <= 1,2·cnom (7.4.7.6): a função devolve o limite superior 1,2·cnom;
    o chamador confere a brita realmente usada contra esse valor.
    """
    return 1.2 * float(cnom_mm)
