"""Regiões especiais — ABNT NBR 6118:2026, Seção 21.

Cobre 21.2.1 (pressão de contato em área reduzida), 21.2.2 (articulações de
concreto), 21.3.3 (furos que atravessam vigas na direção da altura) e
21.3.4, a) e b) (aberturas em lajes, seção remanescente e armadura de
reforço).

Os limites de dimensão de furos e aberturas que permitem *dispensar* a
verificação específica (13.2.5.1 e 13.2.5.2) já estão em
``limites_geometricos_nbr6118`` (P10) — são furos "na direção da largura"
(passam através da espessura/largura do elemento). Este módulo cobre a
Seção 21: furos "na direção da altura" (Figura 21.5 — um furo vertical que
atravessa a viga de cima a baixo, como uma tubulação vertical) e a
verificação da seção remanescente correspondente, que a Seção 13 não trata.

Norma: ABNT NBR 6118:2026, 5a edição (11/03/2026). As páginas citadas são as
do PDF (a página impressa é 18 a menos).

Unidades: força em kN (``_kn``); momento em kN·cm (``_kncm``); comprimento e
dimensão de seção em cm (``_cm``); área em cm² (``_cm2``); tensão e fck em
MPa (``_mpa``), convertidos para kN/cm² internamente quando necessário.

Este módulo não reimplementa fórmula de material nem de seção: fcd vem do
núcleo normativo (``nucleo_nbr6118``); a condição geral de segurança
Rd >= Sd vem de ``seguranca_nbr6118`` (P5); o momento e a força cortante
resistentes de uma seção retangular ou de uma faixa de laje reaproveitam,
respectivamente, ``vigas_nbr6118.momento_resistente_simples`` e
``cortante_nbr6118``/``lajes_nbr6118.cortante_resistente_laje``; o
comprimento de ancoragem da armadura de reforço de abertura em laje vem de
``ancoragem_nbr6118.comprimento_ancoragem`` (Seção 9).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
    import seguranca_nbr6118 as seg
    import vigas_nbr6118 as vig
    import cortante_nbr6118 as crt
    import lajes_nbr6118 as laj
    import ancoragem_nbr6118 as anc
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr
    from dimensionamento import seguranca_nbr6118 as seg
    from dimensionamento import vigas_nbr6118 as vig
    from dimensionamento import cortante_nbr6118 as crt
    from dimensionamento import lajes_nbr6118 as laj
    from dimensionamento import ancoragem_nbr6118 as anc

FaixaNormativaError = nbr.FaixaNormativaError
GAMA_C = nbr.GAMA_C
GAMA_S = nbr.GAMA_S


def fcd_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fcd em kN/cm², a partir de fck em MPa (delega ao núcleo, 12.3.3)."""
    return nbr.mpa_para_kncm2(nbr.fcd(fck_mpa, gama_c))


# ---------------------------------------------------------------------------
# 21.2.1 — Pressão de contato em área reduzida (PDF p. 197)
# ---------------------------------------------------------------------------
PROPORCAO_MAXIMA_LADOS_AC0 = 2.0


def validar_proporcao_ac0(lado_maior_cm: float, lado_menor_cm: float) -> float:
    """Proporção máxima entre os lados de Ac0 retangular, 21.2.1 (PDF p. 197).

    "No caso de Ac0 ser retangular, a proporção a ser considerada entre os
    lados não pode ser maior que 2." Devolve a razão lado_maior/lado_menor
    quando atendida; fora da faixa (razão > 2), levanta
    ``FaixaNormativaError``: a fórmula de ``FRd_area_reduzida`` deixa de se
    aplicar a uma Ac0 retangular tão alongada.
    """
    lm = float(lado_maior_cm)
    ln = float(lado_menor_cm)
    if ln <= 0.0 or lm <= 0.0:
        raise ValueError("lado_maior_cm e lado_menor_cm devem ser positivos.")
    if lm < ln:
        lm, ln = ln, lm
    razao = lm / ln
    if razao > PROPORCAO_MAXIMA_LADOS_AC0 + 1e-9:
        raise FaixaNormativaError(
            f"21.2.1: proporção lado_maior/lado_menor = {razao:.3g} > "
            f"{PROPORCAO_MAXIMA_LADOS_AC0:g}. A norma não permite considerar "
            "Ac0 retangular com essa proporção na fórmula de FRd em área "
            "reduzida."
        )
    return razao


def FRd_area_reduzida(
    Ac0_cm2: float,
    Ac1_cm2: float,
    fck_mpa: float,
    gama_c: float = GAMA_C,
    *,
    lado_maior_cm: float | None = None,
    lado_menor_cm: float | None = None,
) -> float:
    """FRd, resistência de cálculo ao esmagamento em área reduzida, 21.2.1 (PDF p. 197).

    FRd = Ac0·fcd·raiz(Ac1/Ac0) <= 3,3·fcd·Ac0

    onde Ac0 é a área reduzida carregada uniformemente e Ac1 é a área
    máxima de mesma forma e mesmo centro de gravidade que Ac0, inscrita na
    área total Ac2 (situada no mesmo plano de Ac0). fck em MPa; Ac0 e Ac1
    em cm²; devolve kN.

    Faixa de validade: Ac1 >= Ac0 (por definição, Ac1 contém Ac0). Fora
    disso levanta ``FaixaNormativaError``. Se Ac0 for retangular, informe
    ``lado_maior_cm``/``lado_menor_cm`` para também aplicar o limite de
    proporção de 21.2.1 (``validar_proporcao_ac0``) — sem eles, a proporção
    não é verificada aqui.

    "Os valores dados por essa equação devem ser reduzidos se a carga não
    for uniformemente distribuída ou se existirem tensões de cisalhamento.
    Essa expressão não se aplica a ancoragens de protensão" (21.2.1,
    PDF p. 198) — fora do escopo desta função, que cobre só a fórmula base.
    """
    Ac0 = float(Ac0_cm2)
    Ac1 = float(Ac1_cm2)
    if Ac0 <= 0.0:
        raise ValueError("Ac0_cm2 deve ser positivo.")
    if Ac1 < Ac0 - 1e-9:
        raise FaixaNormativaError(
            f"21.2.1: Ac1 = {Ac1:g} cm² < Ac0 = {Ac0:g} cm². Ac1 é a área "
            "máxima de mesma forma e mesmo centro de gravidade que Ac0, "
            "inscrita em Ac2 — não pode ser menor que Ac0."
        )
    if lado_maior_cm is not None and lado_menor_cm is not None:
        validar_proporcao_ac0(lado_maior_cm, lado_menor_cm)

    fcd = fcd_kncm2(fck_mpa, gama_c)
    valor = Ac0 * fcd * math.sqrt(Ac1 / Ac0)
    teto = 3.3 * fcd * Ac0
    return min(valor, teto)


# ---------------------------------------------------------------------------
# 21.2.2 — Articulações de concreto (PDF p. 198)
# ---------------------------------------------------------------------------
INCLINACAO_MAXIMA_ARTICULACAO = 1.0 / 8.0
DESLOCAMENTO_MAXIMO_ABSOLUTO_CM = 2.0
EXTENSAO_VOLUME_FRETADO_POR_C = 3.0


@dataclass(frozen=True)
class ResultadoArticulacaoConcreto:
    c_cm: float
    limite_deslocamento_cm: float
    deslocamento_cm: float
    inclinacao: float
    inclinacao_limite: float
    extensao_volume_fretado_cm: float
    ok_deslocamento: bool
    ok_inclinacao: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_articulacao_concreto(
    c_cm: float,
    deslocamento_cm: float = 0.0,
    inclinacao: float = 0.0,
) -> ResultadoArticulacaoConcreto:
    """Articulação de concreto (núcleo reduzido), 21.2.2, Figura 21.2 (PDF p. 198).

    A articulação transmite esforços reduzidos a uma força cuja resultante
    de compressão tem inclinação máxima 1/8 em relação ao eixo da peça
    (``inclinacao`` é essa tangente, adimensional — informe abs(horizontal
    / vertical)). Dentro do volume a ser fretado (extensão 3·c a partir da
    articulação em cada direção, Figura 21.2), o deslocamento admissível da
    resultante é <= min(c/8, 2 cm).

    c_cm é a dimensão do núcleo reduzido da articulação; deslocamento_cm é
    a excentricidade informada da resultante dentro do volume fretado.
    """
    c = float(c_cm)
    if c <= 0.0:
        raise ValueError("c_cm deve ser positivo.")
    limite_desloc = min(c / 8.0, DESLOCAMENTO_MAXIMO_ABSOLUTO_CM)
    desloc = float(deslocamento_cm)
    ok_desloc = desloc <= limite_desloc + 1e-9

    inc = float(inclinacao)
    ok_inc = inc <= INCLINACAO_MAXIMA_ARTICULACAO + 1e-9

    ok = ok_desloc and ok_inc
    memoria = (
        f"21.2.2: limite de deslocamento = min(c/8, 2 cm) = "
        f"min({c/8.0:g}, 2) = {limite_desloc:g} cm; informado {desloc:g} cm "
        f"-> {'ok' if ok_desloc else 'não ok'}.",
        f"21.2.2: inclinação máxima da resultante de compressão = 1/8 = "
        f"{INCLINACAO_MAXIMA_ARTICULACAO:.4g}; informada {inc:.4g} -> "
        f"{'ok' if ok_inc else 'não ok'}.",
        f"21.2.2: volume a ser fretado com extensão 3c = {3.0*c:g} cm a "
        "partir da articulação, em cada direção (Figura 21.2).",
    )
    return ResultadoArticulacaoConcreto(
        c_cm=c,
        limite_deslocamento_cm=limite_desloc,
        deslocamento_cm=desloc,
        inclinacao=inc,
        inclinacao_limite=INCLINACAO_MAXIMA_ARTICULACAO,
        extensao_volume_fretado_cm=EXTENSAO_VOLUME_FRETADO_POR_C * c,
        ok_deslocamento=ok_desloc,
        ok_inclinacao=ok_inc,
        ok=ok,
        governante=("dentro dos limites (21.2.2)" if ok
                    else "fora dos limites de 21.2.2"),
        memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 21.3.3 — Furos que atravessam as vigas na direção da altura (PDF p. 200)
# ---------------------------------------------------------------------------
DIST_MIN_FURO_FACE_ABSOLUTA_CM = 5.0
DIST_MIN_ENTRE_FUROS_ABSOLUTA_CM = 5.0


def phi_max_furo_viga(bw_cm: float) -> float:
    """Diâmetro máximo de furo vertical em viga, 21.3.3 (PDF p. 200).

    "As aberturas em vigas [...] como furos para passagem de tubulação
    vertical [...] não podem ter diâmetros superiores a 1/3 da largura
    dessas vigas nas regiões desses furos." phi_max = bw/3, cm.
    """
    bw = float(bw_cm)
    if bw <= 0.0:
        raise ValueError("bw_cm deve ser positivo.")
    return bw / 3.0


def distancia_min_furo_face(cobrimento_cm: float) -> float:
    """Distância mínima entre um furo vertical e a face da viga, 21.3.3 (PDF p. 200).

    "A distância mínima de um furo à face mais próxima da viga deve ser no
    mínimo igual a 5 cm e duas vezes o cobrimento previsto nessa face."
    dist_min = max(5 cm, 2·cobrimento).
    """
    cob = float(cobrimento_cm)
    if cob < 0.0:
        raise ValueError("cobrimento_cm não pode ser negativo.")
    return max(DIST_MIN_FURO_FACE_ABSOLUTA_CM, 2.0 * cob)


@dataclass(frozen=True)
class ResultadoConjuntoFuros:
    phi_furo_cm: float
    dist_min_entre_faces_cm: float
    distancias_entre_faces_cm: tuple[float, ...]
    estribo_por_intervalo: tuple[bool, ...]
    ok_distancias: bool
    ok_estribos: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_conjunto_furos(
    phi_furo_cm: float,
    distancias_entre_faces_cm: Sequence[float],
    estribo_por_intervalo: Sequence[bool],
) -> ResultadoConjuntoFuros:
    """Conjunto de furos alinhados em viga, 21.3.3 (PDF p. 200).

    "No caso de ser necessário um conjunto de furos, estes devem ser
    alinhados e a distância entre suas faces deve ser de no mínimo 5 cm, ou
    o diâmetro do furo[, o que for maior,] e cada intervalo deve conter
    pelo menos um estribo." dist_min_entre_faces = max(5 cm, phi_furo);
    cada intervalo entre furos consecutivos precisa de >= 1 estribo.

    ``distancias_entre_faces_cm`` e ``estribo_por_intervalo`` têm um valor
    por intervalo entre furos consecutivos (n furos -> n-1 intervalos) e
    têm de ter o mesmo tamanho.
    """
    phi = float(phi_furo_cm)
    if phi <= 0.0:
        raise ValueError("phi_furo_cm deve ser positivo.")
    distancias = tuple(float(d) for d in distancias_entre_faces_cm)
    estribos = tuple(bool(e) for e in estribo_por_intervalo)
    if len(distancias) != len(estribos):
        raise ValueError(
            "distancias_entre_faces_cm e estribo_por_intervalo têm de ter "
            "o mesmo número de intervalos."
        )
    if not distancias:
        raise ValueError("Informe ao menos um intervalo entre furos.")

    dist_min = max(DIST_MIN_ENTRE_FUROS_ABSOLUTA_CM, phi)
    ok_distancias = all(d + 1e-9 >= dist_min for d in distancias)
    ok_estribos = all(estribos)
    ok = ok_distancias and ok_estribos

    memoria = [
        f"21.3.3: distância mínima entre faces de furos = max(5, "
        f"{phi:g}) = {dist_min:g} cm.",
    ]
    for i, (d, e) in enumerate(zip(distancias, estribos), start=1):
        memoria.append(
            f"  intervalo {i}: distância = {d:g} cm "
            f"({'>=' if d + 1e-9 >= dist_min else '<'} {dist_min:g} cm) -> "
            f"{'ok' if d + 1e-9 >= dist_min else 'não ok'}; estribo "
            f"{'presente' if e else 'ausente'} -> {'ok' if e else 'não ok'}."
        )

    return ResultadoConjuntoFuros(
        phi_furo_cm=phi,
        dist_min_entre_faces_cm=dist_min,
        distancias_entre_faces_cm=distancias,
        estribo_por_intervalo=estribos,
        ok_distancias=ok_distancias,
        ok_estribos=ok_estribos,
        ok=ok,
        governante=("conjunto de furos ok (21.3.3)" if ok
                    else "conjunto de furos não atende 21.3.3"),
        memoria=tuple(memoria),
    )


@dataclass(frozen=True)
class ResultadoSecaoRemanescenteFuroViga:
    bw_cm: float
    phi_furo_cm: float
    bw_remanescente_cm: float
    MRd_kncm: float
    MSd_kncm: float
    VRd_kn: float
    VSd_kn: float
    ok_flexao: bool
    ok_cortante: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def secao_remanescente_furo_viga(
    bw_cm: float,
    phi_furo_cm: float,
    d_cm: float,
    As_cm2: float,
    fck_mpa: float,
    MSd_kncm: float,
    VSd_kn: float,
    fyk_mpa: float = 500.0,
    gama_c: float = GAMA_C,
    gama_s: float = GAMA_S,
) -> ResultadoSecaoRemanescenteFuroViga:
    """Verificação da seção remanescente da viga na região do furo, 21.3.3 (PDF p. 200).

    "Deve ser verificada a redução da capacidade portante ao cisalhamento e
    à flexão na região da abertura. [...] A seção remanescente nessa
    região, tendo sido descontada a área ocupada pelo furo, deve ser capaz
    de resistir aos esforços previstos no cálculo." A norma não dá fórmula
    própria: a verificação é a condição geral Rd >= Sd (12.5.2) aplicada à
    seção com a largura reduzida pelo furo, bw_remanescente = bw - phi_furo.

    MRd vem de ``vigas_nbr6118.momento_resistente_simples`` (armadura As
    existente, agora com bw_remanescente) e VRd de
    ``cortante_nbr6118.simplificada_modelo_I`` (VRd2, esmagamento da biela,
    com bw_remanescente); MSd_kncm e VSd_kn são os esforços solicitantes de
    cálculo na seção do furo, sem redução (a demanda não muda).

    Fora da faixa (phi_furo_cm >= bw_cm, seção remanescente nula ou
    negativa) levanta ``FaixaNormativaError``.
    """
    bw = float(bw_cm)
    phi = float(phi_furo_cm)
    bw_rem = bw - phi
    if bw_rem <= 0.0:
        raise FaixaNormativaError(
            f"21.3.3: phi_furo_cm = {phi:g} cm >= bw_cm = {bw:g} cm — a "
            "seção remanescente é nula ou negativa."
        )

    MRd, x, dominio = vig.momento_resistente_simples(
        As_cm2, bw_rem, d_cm, fck_mpa, fyk_mpa, gama_c, gama_s,
    )
    r_cortante = crt.simplificada_modelo_I(VSd_kn, bw_rem, d_cm, fck_mpa)
    VRd = r_cortante.VRd2

    r_m = seg.verificar_seguranca(
        MRd, abs(MSd_kncm), "MRd x MSd (seção remanescente do furo)", "21.3.3",
    )
    r_v = seg.verificar_seguranca(
        VRd, abs(VSd_kn), "VRd2 x VSd (seção remanescente do furo)", "21.3.3",
    )
    ok = r_m.ok and r_v.ok

    memoria = (
        f"21.3.3: bw remanescente = {bw:g} - {phi:g} = {bw_rem:g} cm "
        f"(bw_cm - phi_furo_cm).",
        *r_m.memoria,
        *r_v.memoria,
    )
    return ResultadoSecaoRemanescenteFuroViga(
        bw_cm=bw, phi_furo_cm=phi, bw_remanescente_cm=bw_rem,
        MRd_kncm=MRd, MSd_kncm=abs(MSd_kncm),
        VRd_kn=VRd, VSd_kn=abs(VSd_kn),
        ok_flexao=r_m.ok, ok_cortante=r_v.ok, ok=ok,
        governante=("seção remanescente ok (21.3.3)" if ok
                    else "seção remanescente não resiste (21.3.3)"),
        memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 21.3.4 — Aberturas em lajes, a) e b) (PDF p. 201)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoSecaoRemanescenteAberturaLaje:
    b_cm: float
    largura_abertura_cm: float
    b_remanescente_cm: float
    MRd_kncm: float
    MSd_kncm: float
    VRd_kn: float | None
    VSd_kn: float | None
    ok_flexao: bool
    ok_cortante: bool | None
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def secao_remanescente_abertura_laje(
    b_cm: float,
    largura_abertura_cm: float,
    d_cm: float,
    As_cm2: float,
    fck_mpa: float,
    MSd_kncm: float,
    fyk_mpa: float = 500.0,
    gama_c: float = GAMA_C,
    gama_s: float = GAMA_S,
    *,
    VSd_kn: float | None = None,
) -> ResultadoSecaoRemanescenteAberturaLaje:
    """Seção remanescente de laje com abertura no ELU, 21.3.4 a) (PDF p. 201).

    "A seção do concreto remanescente da parte central ou sobre o apoio da
    laje deve ser capaz de equilibrar os esforços no estado-limite último,
    correspondentes a essa seção sem aberturas." A verificação é a condição
    geral Rd >= Sd (12.5.2) na faixa de largura b, descontada a largura da
    abertura: b_remanescente = b - largura_abertura. MSd_kncm é o momento
    solicitante de cálculo da faixa sem abertura (a demanda não muda com a
    abertura).

    MRd vem de ``vigas_nbr6118.momento_resistente_simples`` (a laje, para
    fins de flexão de uma faixa, é uma viga larga). Se ``VSd_kn`` for
    informado, também verifica a força cortante com
    ``lajes_nbr6118.cortante_resistente_laje`` (VRd1, 19.4.1); sem ele, a
    verificação de cortante fica de fora (``ok_cortante=None``).

    Fora da faixa (largura_abertura_cm >= b_cm) levanta
    ``FaixaNormativaError``.
    """
    b = float(b_cm)
    la = float(largura_abertura_cm)
    b_rem = b - la
    if b_rem <= 0.0:
        raise FaixaNormativaError(
            f"21.3.4 a): largura_abertura_cm = {la:g} cm >= b_cm = {b:g} cm "
            "— a seção remanescente é nula ou negativa."
        )

    MRd, x, dominio = vig.momento_resistente_simples(
        As_cm2, b_rem, d_cm, fck_mpa, fyk_mpa, gama_c, gama_s,
    )
    r_m = seg.verificar_seguranca(
        MRd, abs(MSd_kncm), "MRd x MSd (laje com abertura)", "21.3.4 a)",
    )

    memoria = [
        f"21.3.4 a): b remanescente = {b:g} - {la:g} = {b_rem:g} cm "
        "(b_cm - largura_abertura_cm).",
        *r_m.memoria,
    ]

    VRd: float | None = None
    ok_cortante: bool | None = None
    if VSd_kn is not None:
        VRd = laj.cortante_resistente_laje(b_rem, d_cm, As_cm2, fck_mpa)
        r_v = seg.verificar_seguranca(
            VRd, abs(VSd_kn), "VRd1 x VSd (laje com abertura)", "21.3.4 a)",
        )
        ok_cortante = r_v.ok
        memoria.extend(r_v.memoria)

    ok = r_m.ok and (ok_cortante if ok_cortante is not None else True)
    return ResultadoSecaoRemanescenteAberturaLaje(
        b_cm=b, largura_abertura_cm=la, b_remanescente_cm=b_rem,
        MRd_kncm=MRd, MSd_kncm=abs(MSd_kncm),
        VRd_kn=VRd, VSd_kn=(abs(VSd_kn) if VSd_kn is not None else None),
        ok_flexao=r_m.ok, ok_cortante=ok_cortante, ok=ok,
        governante=("seção remanescente ok (21.3.4 a)" if ok
                    else "seção remanescente não resiste (21.3.4 a)"),
        memoria=tuple(memoria),
    )


@dataclass(frozen=True)
class ResultadoReforcoAberturaLaje:
    As_interrompidas_cm2: tuple[float, ...]
    As_reforco_cm2: float
    lb_nec_cm: float | None
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def As_reforco_abertura(
    As_barras_interrompidas_cm2: Sequence[float],
    *,
    phi_reforco_mm: float | None = None,
    fck_mpa: float | None = None,
    fyk_mpa: float = 500.0,
    tipo_aco: str = "CA-50",
    boa_aderencia: bool = True,
    com_gancho: bool = False,
    gama_c: float = GAMA_C,
    gama_s: float = GAMA_S,
) -> ResultadoReforcoAberturaLaje:
    """Armadura de reforço equivalente à interrompida por abertura em laje, 21.3.4 b) (PDF p. 201).

    "As seções das armaduras interrompidas devem ser substituídas por
    seções equivalentes de reforço, devidamente ancoradas nas bordas [da
    abertura]." As,reforço >= soma das As das barras interrompidas.

    ``As_barras_interrompidas_cm2`` é a área de cada barra interrompida
    (cm²); a soma é a armadura de reforço mínima, a dispor a cada borda da
    abertura. Se ``phi_reforco_mm`` e ``fck_mpa`` forem informados, também
    calcula o comprimento de ancoragem necessário dessa armadura de reforço
    a partir da borda, via ``ancoragem_nbr6118.comprimento_ancoragem``
    (Seção 9) — sem eles, ``lb_nec_cm`` fica ``None``.
    """
    valores = tuple(float(v) for v in As_barras_interrompidas_cm2)
    if not valores:
        raise ValueError("Informe ao menos uma barra interrompida.")
    if any(v < 0.0 for v in valores):
        raise ValueError("Área de barra interrompida não pode ser negativa.")

    As_reforco = sum(valores)
    memoria = [
        f"21.3.4 b): As,reforço >= soma das As interrompidas = "
        f"{' + '.join(f'{v:g}' for v in valores)} = {As_reforco:g} cm², "
        "a dispor em cada borda da abertura, devidamente ancorada.",
    ]

    lb_nec: float | None = None
    if phi_reforco_mm is not None and fck_mpa is not None:
        r_anc = anc.comprimento_ancoragem(
            phi_reforco_mm, fck_mpa, fyk_mpa, tipo_aco, boa_aderencia,
            com_gancho, gama_c=gama_c, gama_s=gama_s,
        )
        lb_nec = r_anc.lb_nec_cm
        memoria.append(
            f"21.3.4 b) + Seção 9: comprimento de ancoragem necessário da "
            f"armadura de reforço (phi {phi_reforco_mm:g} mm) = "
            f"{lb_nec:g} cm."
        )

    return ResultadoReforcoAberturaLaje(
        As_interrompidas_cm2=valores,
        As_reforco_cm2=As_reforco,
        lb_nec_cm=lb_nec,
        ok=True,
        governante="As,reforço = soma das interrompidas (21.3.4 b)",
        memoria=tuple(memoria),
    )
