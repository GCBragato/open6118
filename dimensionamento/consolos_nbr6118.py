"""Consolos e dentes Gerber — ABNT NBR 6118:2026, 22.5.

Classificação de consolo curto/muito curto (22.5.1.1), o limite de
inclinação da abertura de carga sob a placa de apoio (22.5.1.2 c),
dimensionamento pelo modelo de biela-tirante (22.5.1.3) com a armadura
mínima do tirante (22.5.1.4.1), a restrição ao gancho vertical na
extremidade do tirante (22.5.1.4.1), a armadura de costura mínima
(22.5.1.4.3) e a de suspensão para carga indireta (22.5.1.4.4); e, para o
dente Gerber, o mesmo modelo com os ajustes de 22.5.2.2 (22.5.2.3) e a
armadura de suspensão obrigatória (22.5.2.4.2).

Norma: ABNT NBR 6118:2026, 5ª edição (11/03/2026). As páginas citadas são as
do PDF (a página impressa é 18 a menos).

Unidades: fck, fyk e tensões em MPa; funções e campos com sufixo ``_kncm2``
devolvem kN/cm2 (1 kN/cm2 = 10 MPa); forças em kN; geometria em cm; áreas de
aço em cm2.

Este módulo não reimplementa fórmula de material nem o núcleo do método de
biela-tirante: fcd, fyd, alpha_v2 vêm de ``nucleo_nbr6118.py``; fcd1, fcd3 e
``As_tirante_cm2`` vêm de ``bielas_tirantes_nbr6118.py`` (P35); o γn mínimo
de consolos e dentes Gerber vem de ``limites_geometricos_nbr6118.py``
(``gama_n_consolo_gerber``, P10) e é aplicado por padrão às forças de
cálculo, como qualquer outro parâmetro configurável do núcleo: lido na hora
da chamada, não no import, e aceito também como argumento explícito.

22.5.1.3 e 22.5.2.3 ("Modelo de cálculo") são descritivos na norma: exigem
equilíbrio geral (inclusive no nó de ligação com o pilar) e apoio
experimental ou embasamento em ensaios, mas não fecham uma fórmula (por
isso o mapa do plano marca ``conferido_na_imagem: false`` nesses dois
itens — não há fórmula na imagem da página para conferir). O que este
módulo faz, em ``dimensionar_consolo``/``dimensionar_dente_gerber``, é o
modelo clássico de braço de alavanca (z = 0,85·d) e equilíbrio de momento
para achar a força do tirante — a mesma família de escolha de
``blocos_nbr6118.py`` ao adotar o método de Blévot para blocos sobre
estacas: um critério de engenharia amplamente usado na prática brasileira
de projeto, documentado como tal, e não uma transcrição literal da norma.
A verificação da tensão de compressão na biela (22.5.1.2 c, contra fcd1 e
fcd3 de 22.3.2) **é feita** quando se informa a largura da placa de apoio
``a0_cm``: a própria norma dá a regra que faltava para a largura efetiva do
nó — a abertura de carga sob a placa, limitada à inclinação máxima de 1:2 em
relação à vertical (Figura 22.4). Ver o bloco F4 no fim deste arquivo
(``verificar_biela_consolo``, ``modelo_biela_tirante_consolo``,
``inclinacao_biela_consolo``), que também explica, com a evidência, o que
continua fora: o modelo atrito-cisalhamento e a treliça própria do dente
Gerber.
"""

from __future__ import annotations

from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

try:  # executado como script, ou com dimensionamento/ no sys.path
    import bielas_tirantes_nbr6118 as bt
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import bielas_tirantes_nbr6118 as bt

try:  # executado como script, ou com dimensionamento/ no sys.path
    import limites_geometricos_nbr6118 as lim
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import limites_geometricos_nbr6118 as lim

FaixaNormativaError = nbr.FaixaNormativaError

GAMA_C = nbr.GAMA_C
GAMA_S = nbr.GAMA_S

# 22.5.1.3, PDF p. 208 — braço de alavanca adotado por este módulo para o
# modelo de biela-tirante do consolo (ver docstring do módulo e de
# ``braco_alavanca_consolo_cm``); não é um valor dado pela norma.
Z_SOBRE_D = 0.85


def _validar_positivo(valor: float, nome: str) -> float:
    """Confere que uma grandeza geométrica ou de força é > 0."""
    v = float(valor)
    if not (v > 0.0):
        raise FaixaNormativaError(f"{nome} tem de ser positivo; recebido {v:g}.")
    return v


def _validar_nao_negativo(valor: float, nome: str) -> float:
    """Confere que uma grandeza (força, área) é >= 0."""
    v = float(valor)
    if v < 0.0:
        raise FaixaNormativaError(f"{nome} não pode ser negativo; recebido {v:g}.")
    return v


# ---------------------------------------------------------------------------
# 22.5.1.1 — Classificação de consolo (PDF p. 206)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoClassificacaoConsolo:
    """Resultado de 22.5.1.1: classificação do elemento em balanço."""

    a_cm: float
    d_cm: float
    razao_a_d: float
    classificacao: str
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def classificar_consolo(a_cm: float, d_cm: float) -> ResultadoClassificacaoConsolo:
    """Classifica um elemento em balanço pela razão a/d (22.5.1.1, PDF p. 206)
    entre o afastamento da carga aplicada à face do apoio (a) e a altura
    útil do consolo (d):

        muito curto:            a < 0,5·d
        curto:                  0,5·d <= a <= d
        viga em balanço (fora do escopo de 22.5): a > d

    ``a_cm``: distância da carga aplicada à face do apoio, cm. ``d_cm``:
    altura útil do consolo, cm. ``ok`` é True para consolo curto ou muito
    curto (dimensionável por este módulo); False quando a > d — nesse caso,
    a norma manda tratar o elemento como viga em balanço comum, não mais
    como consolo (``dimensionar_consolo`` levanta ``FaixaNormativaError``
    nessa situação).
    """
    a = _validar_positivo(a_cm, "a_cm")
    d = _validar_positivo(d_cm, "d_cm")
    razao = a / d
    if razao < 0.5 - 1e-9:
        classificacao = "muito_curto"
        nota = "a/d < 0,5 -> consolo muito curto."
    elif razao <= 1.0 + 1e-9:
        classificacao = "curto"
        nota = "0,5 <= a/d <= 1 -> consolo curto."
    else:
        classificacao = "viga_em_balanco"
        nota = "a/d > 1 -> viga em balanço; não é consolo (22.5.1.1)."
    ok = classificacao != "viga_em_balanco"
    memoria = (
        f"22.5.1.1: a/d = {a:g}/{d:g} = {razao:.4f}.",
        nota,
    )
    return ResultadoClassificacaoConsolo(
        a_cm=a, d_cm=d, razao_a_d=razao, classificacao=classificacao,
        ok=ok, governante="22.5.1.1", memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 22.5.1.2 c) — Abertura de carga sob a placa de apoio, limite 1:2 (PDF p. 207)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoAberturaCarga:
    """Resultado de 22.5.1.2 c): largura de biela admissível pela abertura
    de carga sob a placa de apoio."""

    a0_cm: float
    profundidade_cm: float
    largura_max_cm: float
    largura_considerada_cm: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_abertura_carga(a0_cm: float, profundidade_cm: float,
                              largura_considerada_cm: float | None = None,
                              ) -> ResultadoAberturaCarga:
    """Largura efetiva de biela admissível pela abertura de carga sob a
    placa de apoio (22.5.1.2 c, PDF p. 207): para a verificação da biela,
    pode-se considerar a abertura de carga sob a placa de apoio, limitada a
    uma inclinação máxima de 1:2 (horizontal:vertical) a partir dos pontos
    extremos da área de apoio (Figura 22.4). A cada unidade de profundidade
    vertical, a largura pode aumentar no máximo meia unidade de cada lado,
    isto é, uma unidade no total:

        largura_max = a0 + profundidade

    ``a0_cm``: largura da placa de apoio, na direção considerada, cm.
    ``profundidade_cm``: distância vertical, a partir do plano da placa de
    apoio, até o nível em que a biela é verificada, cm. Se
    ``largura_considerada_cm`` for informada, a função também verifica se a
    largura efetivamente adotada no cálculo respeita esse limite (``ok``);
    se omitida, devolve só o limite (``largura_max_cm``), com ``ok=True``.
    """
    a0 = _validar_positivo(a0_cm, "a0_cm")
    prof = _validar_nao_negativo(profundidade_cm, "profundidade_cm")
    largura_max = a0 + prof
    if largura_considerada_cm is None:
        largura_usada = largura_max
        ok = True
    else:
        largura_usada = _validar_positivo(largura_considerada_cm, "largura_considerada_cm")
        ok = largura_usada <= largura_max + 1e-9
    memoria = (
        f"22.5.1.2 c): a0 = {a0:g} cm; inclinação máxima 1:2 (horizontal:vertical) em "
        f"profundidade de {prof:g} cm -> largura máxima = a0 + profundidade = "
        f"{a0:g} + {prof:g} = {largura_max:.4f} cm.",
        f"largura considerada = {largura_usada:.4f} cm "
        f"{'<= largura máxima -> ok.' if ok else '> largura máxima -> reprovado.'}",
    )
    return ResultadoAberturaCarga(
        a0_cm=a0, profundidade_cm=prof, largura_max_cm=largura_max,
        largura_considerada_cm=largura_usada, ok=ok,
        governante="22.5.1.2", memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 22.5.1.3 — Modelo de cálculo: braço de alavanca e força do tirante
# (PDF p. 208; ver ressalva na docstring do módulo)
# ---------------------------------------------------------------------------
def braco_alavanca_consolo_cm(d_cm: float) -> float:
    """Braço de alavanca interno adotado para o modelo de biela-tirante do
    consolo curto, cm: z = 0,85·d.

    A NBR 6118 22.5.1.3 não fornece uma expressão fechada para o braço de
    alavanca do consolo — exige apenas que o modelo contemple o equilíbrio
    global, inclusive no nó de ligação com o pilar. Este módulo adota a
    aproximação clássica z = 0,85·d (mesma ordem de grandeza do braço de
    alavanca de uma viga com armadura simples), usual na prática brasileira
    de projeto de consolos curtos. Quem dispuser de um valor mais preciso
    (por exemplo, de uma verificação por planos de deformação) pode
    calcular Rsd diretamente com ``Rsd_tirante_consolo_kn`` e o z próprio.
    """
    d = _validar_positivo(d_cm, "d_cm")
    return Z_SOBRE_D * d


def Rsd_tirante_consolo_kn(Fd_kn: float, Hd_kn: float, a_cm: float,
                            z_cm: float) -> float:
    """Força de tração de cálculo no tirante do consolo, kN (22.5.1.3):
    equilíbrio de momento em torno do nó de compressão junto ao pilar,

        Rsd = Fd·a/z + Hd

    ``Fd_kn``: força vertical de cálculo aplicada ao consolo (já com o γn
    de 22.2, se for o caso). ``a_cm``: distância da carga à face do apoio.
    ``z_cm``: braço de alavanca interno adotado (``braco_alavanca_consolo_cm``).
    ``Hd_kn``: força horizontal de cálculo, aplicada no nível do tirante —
    soma-se diretamente a Rsd, sem braço de alavanca, por atuar na própria
    linha do tirante (Figura 22.4).
    """
    a = _validar_positivo(a_cm, "a_cm")
    z = _validar_positivo(z_cm, "z_cm")
    return float(Fd_kn) * a / z + float(Hd_kn)


# ---------------------------------------------------------------------------
# 22.5.1.4.1 — Restrição ao uso de gancho vertical (PDF p. 208)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoGanchoVertical:
    """Resultado de 22.5.1.4.1: restrição ao gancho vertical na extremidade
    do tirante do consolo."""

    b_cm: float
    a_cm: float
    a0_cm: float
    limite_b_cm: float
    consolo_continuo: bool
    cargas_pequenas: bool
    permitido: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_gancho_vertical_consolo(
    b_cm: float, a_cm: float, a0_cm: float, consolo_continuo: bool,
    cargas_horizontais_verticais_pequenas: bool,
) -> ResultadoGanchoVertical:
    """Verifica se o gancho no plano vertical, na extremidade do tirante do
    consolo, é aceito (22.5.1.4.1, PDF p. 208).

    Na extremidade do consolo não pode ser usado gancho no plano vertical,
    para evitar ruínas por ruptura de canto ou do cobrimento lateral do
    gancho. Esses ganchos verticais só podem ser aceitos em consolos
    contínuos, com a largura b do consolo superior a quatro vezes o
    comprimento (a + a0), e na presença de pequenas cargas horizontais e
    verticais:

        permitido <=> consolo contínuo E b > 4·(a + a0) E cargas pequenas

    ``b_cm``: largura do consolo. ``a_cm``: distância da carga à face do
    apoio. ``a0_cm``: largura da placa de apoio (ou do comprimento de
    ancoragem equivalente). ``consolo_continuo``: True se o consolo for
    contínuo (não isolado). A norma não quantifica "pequenas cargas
    horizontais e verticais": ``cargas_horizontais_verticais_pequenas`` é
    um julgamento de projeto, informado explicitamente por quem chama a
    função.
    """
    b = _validar_positivo(b_cm, "b_cm")
    a = _validar_positivo(a_cm, "a_cm")
    a0 = _validar_positivo(a0_cm, "a0_cm")
    limite_b = 4.0 * (a + a0)
    largura_ok = b > limite_b + 1e-9
    continuo = bool(consolo_continuo)
    cargas_pequenas = bool(cargas_horizontais_verticais_pequenas)
    permitido = continuo and largura_ok and cargas_pequenas
    memoria = (
        f"22.5.1.4.1: b = {b:g} cm; 4·(a+a0) = 4·({a:g}+{a0:g}) = {limite_b:.4f} cm "
        f"-> b {'>' if largura_ok else '<='} 4·(a+a0).",
        f"consolo contínuo: {continuo}; cargas horizontais e verticais pequenas: "
        f"{cargas_pequenas}.",
        (
            "Gancho vertical na extremidade do tirante permitido (consolo contínuo, "
            "b > 4·(a+a0) e cargas pequenas)." if permitido else
            "Gancho vertical na extremidade do tirante proibido; usar ancoragem "
            "alternativa (alça no plano horizontal, barra transversal soldada ou "
            "chapa metálica soldada, 9.4.7.1, ver Figura 22.5)."
        ),
    )
    return ResultadoGanchoVertical(
        b_cm=b, a_cm=a, a0_cm=a0, limite_b_cm=limite_b, consolo_continuo=continuo,
        cargas_pequenas=cargas_pequenas, permitido=permitido, ok=permitido,
        governante="22.5.1.4.1", memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 22.5.1.4.3 — Armadura de costura mínima (PDF p. 209)
# ---------------------------------------------------------------------------
def As_costura_min_cm2(As_tirante_cm2: float) -> float:
    """As,costura,mín = 0,40 · As,tirante, cm² (22.5.1.4.3, PDF p. 209).

    Consolos curtos e muito curtos exigem armadura de costura obrigatória
    (nunca podem ficar sem ela): mínimo de 40 % da armadura do tirante, em
    estribos horizontais distribuídos na altura (2/3)·d (ver
    ``dimensionar_consolo`` para a altura de distribuição).
    """
    As_t = _validar_nao_negativo(As_tirante_cm2, "As_tirante_cm2")
    return 0.40 * As_t


# ---------------------------------------------------------------------------
# 22.5.1.4.4 — Armadura de suspensão do consolo, carga indireta (PDF p. 209)
# ---------------------------------------------------------------------------
def As_suspensao_consolo_cm2(Fd_indireta_kn: float, fyd_kncm2: float) -> float:
    """As,susp = Fd,indireta / fyd, cm² (22.5.1.4.4, PDF p. 209).

    Quando existir carga indireta aplicada ao consolo, deve-se prever
    armadura de suspensão dimensionada para a totalidade dessa carga.
    ``Fd_indireta_kn``: força de cálculo da carga indireta, kN (0 quando não
    houver carga indireta -> devolve 0). ``fyd_kncm2``: resistência de
    cálculo do aço, kN/cm2 (delegue a ``nucleo_nbr6118.fyd``).
    """
    Fd_ind = _validar_nao_negativo(Fd_indireta_kn, "Fd_indireta_kn")
    fyd = _validar_positivo(fyd_kncm2, "fyd_kncm2")
    return Fd_ind / fyd


# ---------------------------------------------------------------------------
# 22.5.1.3/.4 — Dimensionamento completo do consolo
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoConsolo:
    """Resultado do dimensionamento de um consolo (22.5.1.3 a 22.5.1.4.4)."""

    Fd_kn: float
    Hd_kn: float
    a_cm: float
    d_cm: float
    b_cm: float
    h_cm: float
    fck_mpa: float
    fyk_mpa: float
    modelo: str
    classificacao: str
    gama_n: float
    Fd_amp_kn: float
    Hd_amp_kn: float
    z_cm: float
    Rsd_kn: float
    As_tirante_cm2: float
    As_min_cm2: float
    As_cm2: float
    fcd1_kncm2: float
    fcd3_kncm2: float
    As_costura_min_cm2: float
    altura_costura_cm: float
    Fd_indireta_kn: float
    As_suspensao_cm2: float
    gancho_vertical: ResultadoGanchoVertical | None
    ok: bool
    governante: str
    memoria: tuple[str, ...]
    # F4: acrescentados no fechamento de 22.5.1.3 (ver o bloco F4 no fim do
    # arquivo). ``inclinacao_biela`` sai sempre; ``biela`` sai quando
    # ``a0_cm`` é informado, porque a verificação da compressão na biela
    # depende da largura da placa de apoio (22.5.1.2 c).
    inclinacao_biela: object = None
    biela: object = None


def dimensionar_consolo(
    Fd_kn: float, Hd_kn: float, a_cm: float, d_cm: float, b_cm: float,
    h_cm: float, fck_mpa: float, fyk_mpa: float = 500.0,
    modelo: str = "biela_tirante", gama_c: float = GAMA_C,
    gama_s: float = GAMA_S, gama_n: float | None = None,
    a0_cm: float | None = None, consolo_continuo: bool = False,
    cargas_horizontais_verticais_pequenas: bool = False,
    Fd_indireta_kn: float = 0.0, z_cm: float | None = None,
    b0_cm: float | None = None,
) -> ResultadoConsolo:
    """Dimensiona um consolo curto ou muito curto pelo modelo de
    biela-tirante (22.5.1.3, PDF p. 208), com a armadura mínima do tirante
    (17.3.5.2, via 22.5.1.4.1, PDF p. 208), a armadura de costura mínima
    (22.5.1.4.3, PDF p. 209), a de suspensão para carga indireta
    (22.5.1.4.4, PDF p. 209) e, se ``a0_cm`` for informado, a restrição de
    gancho vertical (22.5.1.4.1).

    Ver a docstring do módulo sobre o que 22.5.1.3 exige (equilíbrio geral)
    e o que este módulo adota (z = 0,85·d, Rsd = Fd·a/z + Hd): a fórmula não
    é literal da norma, é o modelo clássico de biela-tirante da prática de
    projeto. fcd1 (nó CCC, junto ao pilar) e fcd3 (nó CCT, sob o tirante)
    vêm no resultado sempre, como referência (22.3.2).

    A **inclinação da biela** (22.3.1: 0,57 <= tan(theta) <= 2, com
    tan(theta) = z/a) é conferida sempre e entra em ``ok``
    (``inclinacao_biela``). A **compressão na biela** (22.5.1.2 c) só pode
    ser verificada quando se conhece a largura da placa de apoio: informe
    ``a0_cm`` e a função chama ``verificar_biela_consolo``, guarda o
    resultado em ``biela`` e o leva para ``ok``. Sem ``a0_cm``, ``biela``
    fica None e a verificação continua por conta de quem chama.

    ``modelo='atrito'`` (atrito-cisalhamento, usual em consolos muito
    curtos) não está implementado: 22.5.1.3 cita o método apenas de forma
    qualitativa, sem os coeficientes de atrito necessários ao
    dimensionamento, e este módulo não inventa constante sem fonte
    normativa — levanta ``NotImplementedError``. É justamente na faixa de
    a/d < 0,425 que a inclinação da biela sai de 22.3.1, e ``ok`` fica
    False: o modelo de biela-tirante não cobre esse consolo.

    ``Fd_kn``, ``Hd_kn``: forças vertical e horizontal de cálculo, sem o γn
    de 22.2 (aplicado aqui, por padrão). ``a_cm``: distância da carga à
    face do apoio. ``d_cm``: altura útil. ``b_cm``, ``h_cm``: largura e
    altura total do consolo (para As,mín pela 17.3.5.2, viga fictícia
    b × h). ``fck_mpa``, ``fyk_mpa``: resistências características.
    ``gama_n``: coeficiente adicional de 22.2 (padrão: lido de
    ``limites_geometricos_nbr6118.gama_n_consolo_gerber()`` na hora da
    chamada; pode ser sobrescrito). ``a0_cm``, ``consolo_continuo``,
    ``cargas_horizontais_verticais_pequenas``: se ``a0_cm`` for informado, a
    função também verifica a restrição de gancho vertical (22.5.1.4.1) e
    guarda o resultado em ``gancho_vertical``; caso contrário,
    ``gancho_vertical`` fica None. ``Fd_indireta_kn``: força de carga
    indireta aplicada ao consolo, kN (22.5.1.4.4); padrão 0 (sem carga
    indireta -> sem exigência de armadura de suspensão por este item).
    ``z_cm``: braço de alavanca adotado, cm (padrão: 0,85·d). ``b0_cm``:
    largura da placa de apoio na direção transversal, cm, usada só na
    verificação da biela (padrão: a largura b do consolo inteira).
    """
    if modelo not in ("biela_tirante", "atrito"):
        raise ValueError(f"modelo desconhecido: {modelo!r}. Use 'biela_tirante' ou 'atrito'.")
    if modelo == "atrito":
        raise NotImplementedError(
            "modelo='atrito' (atrito-cisalhamento) não está implementado: a NBR "
            "6118 22.5.1.3 cita o método apenas descritivamente, sem os "
            "coeficientes de atrito necessários ao dimensionamento; use "
            "modelo='biela_tirante'."
        )

    classif = classificar_consolo(a_cm, d_cm)
    if not classif.ok:
        raise FaixaNormativaError(
            f"a = {float(a_cm):g} cm > d = {float(d_cm):g} cm: não é consolo "
            "(22.5.1.1); trate como viga em balanço."
        )

    gama_n_usado = float(gama_n) if gama_n is not None else lim.gama_n_consolo_gerber()
    Fd_amp = float(Fd_kn) * gama_n_usado
    Hd_amp = float(Hd_kn) * gama_n_usado

    z = braco_alavanca_adotado_cm(d_cm, z_cm)
    Rsd = Rsd_tirante_consolo_kn(Fd_amp, Hd_amp, a_cm, z)
    incl = inclinacao_biela_consolo(a_cm, d_cm, z_cm)

    fyd_kncm2 = nbr.mpa_para_kncm2(nbr.fyd(fyk_mpa, gama_s))
    As_tirante = bt.As_tirante_cm2(Rsd, fyd_kncm2)
    As_min = nbr.As_min_flexao_retangular(b_cm, h_cm, d_cm, fck_mpa, fyk_mpa, gama_c, gama_s)
    As = max(As_tirante, As_min)

    fcd1 = bt.fcd1_kncm2(fck_mpa, gama_c)
    fcd3 = bt.fcd3_kncm2(fck_mpa, gama_c)

    As_costura = As_costura_min_cm2(As)
    altura_costura = (2.0 / 3.0) * float(d_cm)

    As_susp = As_suspensao_consolo_cm2(Fd_indireta_kn, fyd_kncm2)

    gancho: ResultadoGanchoVertical | None = None
    biela = None
    if a0_cm is not None:
        gancho = verificar_gancho_vertical_consolo(
            b_cm, a_cm, a0_cm, consolo_continuo, cargas_horizontais_verticais_pequenas,
        )
        biela = verificar_biela_consolo(
            Fd_amp, a_cm, d_cm, b_cm, h_cm, a0_cm, fck_mpa, b0_cm=b0_cm,
            z_cm=z_cm, tipo="CCT", gama_c=gama_c,
        )

    memoria = [
        f"22.5.1.1: a/d = {float(a_cm):g}/{float(d_cm):g} -> consolo {classif.classificacao} "
        f"(a/d = {classif.razao_a_d:.4f}).",
        f"22.2: gama_n = {gama_n_usado:g}; Fd = {float(Fd_kn):g} kN -> Fd,amp = {Fd_amp:.4f} kN; "
        f"Hd = {float(Hd_kn):g} kN -> Hd,amp = {Hd_amp:.4f} kN.",
        (
            f"22.5.1.3: z = 0,85·d = 0,85·{float(d_cm):g} = {z:.4f} cm (aproximação adotada, ver "
            "docstring do módulo)."
            if z_cm is None else
            f"22.5.1.3: z = {z:.4f} cm (informado pelo projetista, no lugar da aproximação "
            f"0,85·d = {braco_alavanca_consolo_cm(d_cm):.4f} cm)."
        ),
        f"22.5.1.3: Rsd = Fd,amp·a/z + Hd,amp = {Fd_amp:.4f}·{float(a_cm):g}/{z:.4f} + "
        f"{Hd_amp:.4f} = {Rsd:.4f} kN.",
        f"22.3.3: As,tirante = Rsd/fyd = {Rsd:.4f}/{fyd_kncm2:.4f} = {As_tirante:.4f} cm2.",
        f"22.5.1.4.1: As,mín (17.3.5.2, viga fictícia {float(b_cm):g}×{float(h_cm):g} cm) = "
        f"{As_min:.4f} cm2 -> As = max(As,tirante, As,mín) = {As:.4f} cm2.",
        (
            f"22.3.2: fcd1 = {fcd1:.4f} kN/cm2, fcd3 = {fcd3:.4f} kN/cm2; a compressão na biela "
            "é verificada abaixo, com a abertura de carga sob a placa de apoio (22.5.1.2 c)."
            if a0_cm is not None else
            f"22.3.2 (referência): fcd1 = {fcd1:.4f} kN/cm2, fcd3 = {fcd3:.4f} kN/cm2; a "
            "compressão na biela não foi verificada porque a largura da placa de apoio (a0) "
            "não foi informada (22.5.1.2 c)."
        ),
        f"22.5.1.4.3: As,costura,mín = 0,40·As = 0,40·{As:.4f} = {As_costura:.4f} cm2, em estribos "
        f"horizontais distribuídos em (2/3)·d = {altura_costura:.4f} cm.",
        (
            f"22.5.1.4.4: Fd,indireta = {float(Fd_indireta_kn):g} kN -> As,susp = {As_susp:.4f} cm2."
            if float(Fd_indireta_kn) > 0.0 else
            "22.5.1.4.4: sem carga indireta informada -> sem exigência de armadura de suspensão."
        ),
    ]
    if biela is None:
        memoria.extend(incl.memoria)
    else:
        # biela.memoria já traz a conferência de inclinação de 22.3.1
        memoria.extend(biela.memoria)
    if gancho is not None:
        memoria.extend(gancho.memoria)
    ok = incl.ok and (biela is None or biela.ok)
    if ok:
        governante = "22.5.1.3"
    elif not incl.ok:
        governante = "22.3.1"
    else:
        governante = "22.5.1.2"

    return ResultadoConsolo(
        Fd_kn=float(Fd_kn), Hd_kn=float(Hd_kn), a_cm=float(a_cm), d_cm=float(d_cm),
        b_cm=float(b_cm), h_cm=float(h_cm), fck_mpa=float(fck_mpa), fyk_mpa=float(fyk_mpa),
        modelo=modelo, classificacao=classif.classificacao, gama_n=gama_n_usado,
        Fd_amp_kn=Fd_amp, Hd_amp_kn=Hd_amp, z_cm=z, Rsd_kn=Rsd,
        As_tirante_cm2=As_tirante, As_min_cm2=As_min, As_cm2=As,
        fcd1_kncm2=fcd1, fcd3_kncm2=fcd3,
        As_costura_min_cm2=As_costura, altura_costura_cm=altura_costura,
        Fd_indireta_kn=float(Fd_indireta_kn), As_suspensao_cm2=As_susp,
        gancho_vertical=gancho, ok=ok, governante=governante,
        memoria=tuple(memoria), inclinacao_biela=incl, biela=biela,
    )


# ---------------------------------------------------------------------------
# 22.5.2.4.2 — Armadura de suspensão do dente Gerber (PDF p. 211)
# ---------------------------------------------------------------------------
def As_suspensao_dente_cm2(Fd_kn: float, fyd_kncm2: float) -> float:
    """As,susp = Fd / fyd, cm² (22.5.2.4.2, PDF p. 211).

    Armadura de suspensão do dente Gerber: estribos na altura completa da
    viga, concentrados na extremidade (Figura 22.6), dimensionados para uma
    força no mínimo igual a Fd, de acordo com o modelo biela-tirante
    adotado. Ao contrário do consolo (22.5.1.4.4), aqui a suspensão é
    sempre exigida — não depende de haver carga indireta: no dente Gerber,
    a própria reação de apoio chega pela extremidade superior da viga
    apoiada e precisa ser suspensa até a armadura de flexão da viga que a
    recebe (22.5.2.4.1: a suspensão de 22.5.1.4.4 perde sentido aqui,
    porque é sempre carga "indireta").
    """
    Fd = _validar_nao_negativo(Fd_kn, "Fd_kn")
    fyd = _validar_positivo(fyd_kncm2, "fyd_kncm2")
    return Fd / fyd


# ---------------------------------------------------------------------------
# 22.5.2.3 — Dimensionamento do dente Gerber
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoDenteGerber:
    """Resultado do dimensionamento de um dente Gerber (22.5.2.3 a 22.5.2.4.2)."""

    consolo: ResultadoConsolo
    As_suspensao_dente_cm2: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def dimensionar_dente_gerber(
    Fd_kn: float, Hd_kn: float, a_cm: float, d_cm: float, b_cm: float,
    h_cm: float, fck_mpa: float, fyk_mpa: float = 500.0,
    modelo: str = "biela_tirante", gama_c: float = GAMA_C,
    gama_s: float = GAMA_S, gama_n: float | None = None,
    z_cm: float | None = None, a0_cm: float | None = None,
    b0_cm: float | None = None,
) -> ResultadoDenteGerber:
    """Dimensiona um dente Gerber (22.5.2.3, PDF p. 210), reaproveitando o
    modelo do consolo (22.5.1.3) com as correções de 22.5.2.2.

    22.5.2.3 é literal: "podem ser usados os mesmos princípios estabelecidos
    para os consolos, desde que sejam feitas as correções necessárias para
    contemplar as diferenças levantadas em 22.5.2.2". As três diferenças, e
    o que esta função faz com cada uma:

    a) "a biela é usualmente mais inclinada, porque deve procurar apoio na
       armadura de suspensão, dentro da viga, na extremidade oposta ao ponto
       de aplicação da carga (Figura 22.6)". **A correção está na geometria
       que se informa**: no dente Gerber, ``a_cm`` é a distância da carga à
       **linha da armadura de suspensão** (não à face de um pilar), e
       ``z_cm`` permite adotar o braço de alavanca real do dente no lugar da
       aproximação 0,85·d. Biela mais inclinada é, nesse modelo,
       tan(theta) = z/a maior, e a inclinação é conferida contra a faixa de
       22.3.1 (``consolo.inclinacao_biela``), que reprova o modelo de
       biela-tirante quando tan(theta) passa de 2.
    b) "a armadura principal deve penetrar na viga, procurando ancoragem nas
       bielas devidas ao cisalhamento na viga": é exigência de detalhamento
       e entra na memória de cálculo; o comprimento de ancoragem sai de
       ``ancoragem_nbr6118`` (Seção 9), com a geometria da viga que recebe o
       dente, que esta função não conhece.
    c) "a armadura de suspensão deve ser calculada para uma força no mínimo
       igual a Fd": ``As_suspensao_dente_cm2`` (22.5.2.4.2), sempre exigida.

    O que esta função **não** faz: montar uma treliça própria do dente, com
    o nó da suspensão em posição distinta. 22.5.2.2 a) descreve a biela mais
    inclinada sem dar inclinação, posição de nó nem geometria, e 22.5.2.3
    não fecha nada — não há na norma base para uma geometria específica. Por
    isso o dente Gerber continua sendo o consolo de 22.5.1.3 com a geometria
    que o projetista informar.

    Aplicam-se as recomendações de 22.5.1.4, exceto 22.5.1.4.4 (suspensão
    por carga indireta), que "perde sentido no caso da carga indireta"
    (22.5.2.4.1): por isso esta função chama ``dimensionar_consolo`` com
    ``Fd_indireta_kn=0`` e soma, à parte, a suspensão própria do dente
    Gerber (22.5.2.4.2, sempre exigida, para a totalidade de Fd,amp).

    Parâmetros iguais aos de ``dimensionar_consolo``. ``a0_cm`` (largura do
    aparelho de apoio) e ``b0_cm`` dispara a verificação da compressão na
    biela (22.5.1.2 c, via ``verificar_biela_consolo``), que entra em ``ok``;
    a restrição de gancho vertical do tirante (22.5.1.4.1) é avaliada junto,
    como no consolo. ``ok`` é o do consolo: inclinação da biela na faixa de
    22.3.1 e, quando ``a0_cm`` é informado, compressão na biela dentro de
    22.3.2.
    """
    consolo = dimensionar_consolo(
        Fd_kn, Hd_kn, a_cm, d_cm, b_cm, h_cm, fck_mpa, fyk_mpa, modelo,
        gama_c, gama_s, gama_n, a0_cm=a0_cm, Fd_indireta_kn=0.0, z_cm=z_cm,
        b0_cm=b0_cm,
    )
    fyd_kncm2 = nbr.mpa_para_kncm2(nbr.fyd(fyk_mpa, gama_s))
    As_susp_dente = As_suspensao_dente_cm2(consolo.Fd_amp_kn, fyd_kncm2)
    memoria = consolo.memoria + (
        "22.5.2.3: dente Gerber -- mesmos princípios do consolo (22.5.1.3), com as "
        "correções de 22.5.2.2.",
        f"22.5.2.2 a): a biela do dente é mais inclinada porque procura apoio na "
        f"armadura de suspensão dentro da viga; aqui a = {float(a_cm):g} cm é medido "
        f"até a linha da suspensão e tan(theta) = z/a = {consolo.z_cm:.4f}/"
        f"{float(a_cm):g} = {consolo.z_cm / float(a_cm):.4f}.",
        "22.5.2.2 b): a armadura principal (tirante) deve penetrar na viga, "
        "procurando ancoragem nas bielas devidas ao cisalhamento na viga -- "
        "detalhar o comprimento de ancoragem pela Seção 9 (ancoragem_nbr6118).",
        f"22.5.2.4.2 (22.5.2.2 c): As,susp (dente Gerber) = Fd,amp/fyd = "
        f"{consolo.Fd_amp_kn:.4f}/{fyd_kncm2:.4f} = {As_susp_dente:.4f} cm2 (sempre "
        "exigida, independente de carga indireta -- 22.5.2.4.1).",
    )
    return ResultadoDenteGerber(
        consolo=consolo, As_suspensao_dente_cm2=As_susp_dente, ok=consolo.ok,
        governante="22.5.2.3" if consolo.ok else consolo.governante,
        memoria=memoria,
    )


# === F4: modelo de cálculo do consolo e do dente Gerber (22.5.1.3 e 22.5.2.3) ===
# Fechamento dos dois itens que o P36 deixou parciais. O que a norma dá, e o
# que este bloco passa a fazer:
#
#   - 22.5.1.2 c) (PDF p. 207) exige a "verificação da resistência à compressão
#     da biela ou do cisalhamento equivalente na face do pilar" e dá a regra
#     geométrica que faltava: "pode ser considerada a abertura de carga sob a
#     placa de apoio, conforme indicado na Figura 22.4, limitada a uma
#     inclinação máxima de 1:2 em relação à vertical, nos pontos extremos A e
#     C (ou E) da área de apoio ampliada". Com ela, ``verificar_biela_consolo``
#     fecha a verificação que o P36 tinha deixado de fora por falta da largura
#     efetiva do nó, e ``dimensionar_consolo`` passa a fazê-la sozinho quando
#     ``a0_cm`` é informado.
#   - 22.5.1.2 (PDF p. 207) exige que o modelo "contemple o equilíbrio global,
#     inclusive no nó de ligação com o pilar": ``modelo_biela_tirante_consolo``
#     monta a treliça da Figura 22.4 como ``TrelicaBT`` (22.3.1, P48), que
#     confere isostaticidade e autoequilíbrio e devolve a força de cada barra.
#   - 22.3.1 (PDF p. 204) limita a inclinação da biela a
#     0,57 <= tan(theta) <= 2. Com z = 0,85·d isso vale para a/d entre 0,425 e
#     1,49, ou seja, cobre o consolo curto (0,5 <= a/d <= 1) inteiro e deixa de
#     fora o consolo muito curto de a/d < 0,425 — exatamente a faixa em que
#     22.5.1.3 manda usar atrito-cisalhamento em vez de biela-tirante. A
#     conferência passou a entrar no ``ok`` de ``dimensionar_consolo``.
#
# O que continua fora, com a evidência:
#
#   - ``modelo='atrito'`` (atrito-cisalhamento). A expressão
#     "atrito-cisalhamento" aparece uma única vez na ABNT NBR 6118:2026, em
#     22.5.1.3, e sem nenhum coeficiente de atrito, faixa de rugosidade ou
#     expressão associada; as demais ocorrências de "atrito" na norma são de
#     perda de protensão (9.6.3.3.2.2). Não há base normativa para a
#     constante, e este módulo não inventa constante sem fonte — continua
#     levantando ``NotImplementedError``.
#   - a treliça própria do dente Gerber. 22.5.2.3 diz só "os mesmos princípios
#     estabelecidos para os consolos, desde que sejam feitas as correções
#     necessárias para contemplar as diferenças levantadas em 22.5.2.2", e
#     22.5.2.2 a) descreve a biela "usualmente mais inclinada" sem dar
#     inclinação, posição de nó nem geometria. O que dá para fechar com base
#     normativa — e o que este bloco fecha — é parametrizar a geometria da
#     biela do dente (``z_cm``, e o ``a_cm`` medido até a linha da armadura de
#     suspensão, não até a face de um pilar) e conferi-la contra 22.3.1 e
#     22.3.2.

import math as _math_f4
from dataclasses import dataclass as _dataclass_f4


def braco_alavanca_adotado_cm(d_cm: float, z_cm: float | None = None) -> float:
    """Braço de alavanca usado pelo modelo, cm: ``z_cm`` quando informado,
    ``braco_alavanca_consolo_cm(d_cm)`` (= 0,85·d) quando não (22.5.1.3).

    A norma não dá z (ver a docstring do módulo). ``z_cm`` é a porta para
    quem tem um valor melhor — de uma verificação por planos de deformação,
    de um modelo plano elástico linear ou, no dente Gerber, da posição real
    da armadura de suspensão (22.5.2.2 a). Tem de ficar em 0 < z <= d.
    """
    d = _validar_positivo(d_cm, "d_cm")
    if z_cm is None:
        return braco_alavanca_consolo_cm(d)
    z = _validar_positivo(z_cm, "z_cm")
    if z > d + 1e-9:
        raise FaixaNormativaError(
            f"z = {z:g} cm não pode ser maior que a altura útil d = {d:g} cm.")
    return z


def inclinacao_biela_consolo(a_cm: float, d_cm: float,
                             z_cm: float | None = None):
    """Confere a inclinação da biela do consolo contra a faixa de 22.3.1
    (PDF p. 204): 0,57 <= tan(theta) <= 2, medida em relação ao eixo da
    armadura longitudinal — que, no consolo, é o próprio tirante.

        tan(theta) = z / a

    porque a biela vai do nó sob a carga (no nível do tirante) ao nó na base
    da face do pilar, z abaixo e a adentro (Figura 22.4, PDF p. 207).

    Com z = 0,85·d a faixa de 22.3.1 corresponde a 0,425 <= a/d <= 1,49: o
    consolo curto de 22.5.1.1 (0,5 <= a/d <= 1) cabe inteiro, e o consolo
    muito curto com a/d < 0,425 fica fora — é a faixa em que 22.5.1.3 manda
    usar o modelo atrito-cisalhamento, que este módulo não implementa (ver o
    comentário de abertura deste bloco). Não levanta erro: devolve o
    ``ResultadoInclinacaoBiela`` de ``bielas_tirantes_nbr6118``, com ``ok``.
    """
    a = _validar_positivo(a_cm, "a_cm")
    z = braco_alavanca_adotado_cm(d_cm, z_cm)
    return bt.verificar_inclinacao_biela(z / a)


@_dataclass_f4(frozen=True)
class ResultadoBielaConsolo:
    """Resultado da verificação da biela do consolo (22.5.1.2 c, com 22.3.2)."""

    Fd_kn: float
    a_cm: float
    d_cm: float
    h_cm: float
    z_cm: float
    L_biela_cm: float
    sen_theta: float
    tan_theta: float
    Rcd_kn: float
    a0_cm: float
    profundidade_difusao_cm: float
    largura_no_cm: float
    h_biela_cm: float
    b_biela_cm: float
    area_biela_cm2: float
    sigma_kncm2: float
    tipo_no: str
    fcd_no_kncm2: float
    razao: float
    inclinacao: object
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_biela_consolo(
    Fd_kn: float, a_cm: float, d_cm: float, b_cm: float, h_cm: float,
    a0_cm: float, fck_mpa: float, b0_cm: float | None = None,
    z_cm: float | None = None, tipo: str = "CCT", gama_c: float = GAMA_C,
) -> ResultadoBielaConsolo:
    """Verifica a compressão na biela do consolo (22.5.1.2 c, PDF p. 207,
    com 22.3.2, PDF p. 204), usando a abertura de carga sob a placa de apoio
    que a própria norma autoriza.

    Geometria (Figura 22.4, PDF p. 207):

        z    = 0,85·d, ou ``z_cm``            (braço de alavanca adotado)
        L    = raiz(a^2 + z^2)                (comprimento da biela)
        Rcd  = Fd · L / z                     (equilíbrio do nó sob a carga)
        sen(theta) = z / L

    Largura efetiva do nó, por 22.5.1.2 c) — "pode ser considerada a abertura
    de carga sob a placa de apoio [...] limitada a uma inclinação máxima de
    1:2 em relação à vertical, nos pontos extremos A e C (ou E) da área de
    apoio ampliada", isto é, meia unidade de largura de cada lado por unidade
    de profundidade (``verificar_abertura_carga``):

        profundidade de difusão = d' = h - d  (da face superior, onde está a
                                               placa, até o eixo do tirante)
        largura do nó           = a0 + d'
        h,biela                 = (a0 + d') · sen(theta)
        b,biela                 = b, ou min(b, b0 + d') quando ``b0_cm`` é
                                  informada (mesma difusão na direção
                                  transversal)
        sigma                   = Rcd / (h,biela · b,biela)

    e sigma é comparada, por ``bielas_tirantes_nbr6118.verificar_no``, ao
    parâmetro de 22.3.2 do tipo de nó: o padrão é **CCT** (fcd3), porque no
    nó sob a placa de apoio confluem a biela e o tirante único do consolo;
    use ``tipo='CCC'`` (fcd1) para o nó de ligação com o pilar, informando
    nesse caso a largura do nó daquele lado pela geometria do pilar.

    ``Fd_kn``: força vertical de cálculo **já amplificada** pelo γn de 22.2
    (``dimensionar_consolo`` passa Fd,amp). ``a_cm``, ``d_cm``, ``b_cm``,
    ``h_cm``: geometria do consolo, cm. ``a0_cm``: largura da placa de apoio
    na direção de a, cm. ``b0_cm``: largura da placa na direção transversal,
    cm (padrão: usa a largura b do consolo inteira). ``fck_mpa`` em MPa.

    Faixa: exige h > d (tem de haver cobrimento acima do tirante para a
    difusão) e a, d, b, h, a0 positivos; fora disso, ``FaixaNormativaError``.
    A inclinação da biela também é conferida (22.3.1) e entra no ``ok``.
    """
    Fd = _validar_nao_negativo(Fd_kn, "Fd_kn")
    a = _validar_positivo(a_cm, "a_cm")
    d = _validar_positivo(d_cm, "d_cm")
    b = _validar_positivo(b_cm, "b_cm")
    h = _validar_positivo(h_cm, "h_cm")
    a0 = _validar_positivo(a0_cm, "a0_cm")
    if h <= d + 1e-9:
        raise FaixaNormativaError(
            f"h = {h:g} cm tem de ser maior que d = {d:g} cm: a difusão de "
            "22.5.1.2 c) se dá da face superior até o eixo do tirante, em "
            "d' = h - d.")
    z = braco_alavanca_adotado_cm(d, z_cm)
    L = _math_f4.hypot(a, z)
    sen = z / L
    tan = z / a
    Rcd = Fd * L / z

    dlinha = h - d
    largura_no = verificar_abertura_carga(a0, dlinha).largura_max_cm
    h_biela = largura_no * sen
    if b0_cm is None:
        b_biela = b
    else:
        b0 = _validar_positivo(b0_cm, "b0_cm")
        b_biela = min(b, b0 + dlinha)
    area = h_biela * b_biela
    sigma = Rcd / area

    no = bt.verificar_no(tipo, sigma, fck_mpa, gama_c)
    incl = bt.verificar_inclinacao_biela(tan)
    ok = no.ok and incl.ok
    memoria = (
        f"22.5.1.3: z = {z:.4f} cm; L = raiz(a^2 + z^2) = raiz({a:g}^2 + "
        f"{z:.4f}^2) = {L:.4f} cm; sen(theta) = z/L = {sen:.4f}.",
        f"22.5.1.2 c): Rcd = Fd·L/z = {Fd:.4f}·{L:.4f}/{z:.4f} = {Rcd:.4f} kN "
        "(equilíbrio do nó sob a carga).",
        f"22.5.1.2 c): difusão 1:2 da placa de apoio em d' = h - d = {h:g} - "
        f"{d:g} = {dlinha:.4f} cm -> largura do nó = a0 + d' = {a0:g} + "
        f"{dlinha:.4f} = {largura_no:.4f} cm.",
        f"h,biela = largura do nó · sen(theta) = {largura_no:.4f}·{sen:.4f} = "
        f"{h_biela:.4f} cm; b,biela = {b_biela:.4f} cm -> área = {area:.4f} cm2.",
        f"sigma = Rcd/área = {Rcd:.4f}/{area:.4f} = {sigma:.4f} kN/cm2.",
    ) + no.memoria + incl.memoria
    return ResultadoBielaConsolo(
        Fd_kn=Fd, a_cm=a, d_cm=d, h_cm=h, z_cm=z, L_biela_cm=L, sen_theta=sen,
        tan_theta=tan, Rcd_kn=Rcd, a0_cm=a0, profundidade_difusao_cm=dlinha,
        largura_no_cm=largura_no, h_biela_cm=h_biela, b_biela_cm=b_biela,
        area_biela_cm2=area, sigma_kncm2=sigma, tipo_no=no.tipo,
        fcd_no_kncm2=no.fcd_no_kncm2, razao=no.razao, inclinacao=incl, ok=ok,
        governante="22.5.1.2", memoria=memoria,
    )


def modelo_biela_tirante_consolo(Fd_kn: float, Hd_kn: float, a_cm: float,
                                 d_cm: float, z_cm: float | None = None):
    """Treliça de bielas e tirantes do consolo curto (22.5.1.3, PDF p. 208;
    Figura 22.4, PDF p. 207), montada como ``TrelicaBT`` de 22.3.1 (P48).

    22.5.1.2 exige um modelo biela-tirante "que deve contemplar o equilíbrio
    global, inclusive no nó de ligação com o pilar". A treliça abaixo é esse
    equilíbrio escrito por inteiro, em vez da conta de braço de alavanca: a
    própria ``TrelicaBT`` confere a isostaticidade que 22.3.1 exige e resolve
    o equilíbrio de cada nó.

    Geometria (origem na face do pilar, no nível do tirante; x para fora do
    pilar, y para cima):

        - nó 'A' (0, 0): extremidade interna do tirante, no nó de ligação com
          o pilar;
        - nó 'C' (a, 0): nó sob a carga, onde o tirante se ancora na biela
          logo abaixo do aparelho de apoio;
        - nó 'B' (0, -z): base da biela, na face do pilar;
        - barras: 'A-C' (tirante do topo), 'C-B' (biela inclinada) e 'A-B'
          (face do pilar, que fecha a contagem de isostaticidade de 22.3.1 e
          sai com força nula neste modelo, porque toda a carga vertical desce
          pela biela até o nó B);
        - apoios: A em ux; B em ux e uy — 3 barras + 3 graus - 2·3 nós = 0.

    Forças em 'C': Fd para baixo e Hd para fora (22.5.1.2 d: a força
    horizontal e o efeito desfavorável da resultante inclinada). A solução
    fechada da treliça reproduz exatamente ``Rsd_tirante_consolo_kn``:

        N('A-C') = Fd·a/z + Hd  (tirante)     N('C-B') = -Fd·L/z  (biela)

    ``Fd_kn`` e ``Hd_kn`` já amplificados pelo γn de 22.2. Devolve a
    ``TrelicaBT`` pronta para ``resolver()``; o eixo da armadura longitudinal
    contra o qual 22.3.1 mede a inclinação das bielas é o x global, que é o
    padrão de ``resolver``.
    """
    a = _validar_positivo(a_cm, "a_cm")
    z = braco_alavanca_adotado_cm(d_cm, z_cm)
    t = bt.TrelicaBT(nome="consolo curto (22.5.1.3)", espacial=False)
    t.no("A", 0.0, 0.0).no("C", a, 0.0).no("B", 0.0, -z)
    t.barra("A-C", "A", "C").barra("C-B", "C", "B").barra("A-B", "A", "B")
    t.apoio("A", "ux").apoio("B", "ux", "uy")
    t.forca("C", Fx_kn=float(Hd_kn), Fy_kn=-float(Fd_kn))
    return t
