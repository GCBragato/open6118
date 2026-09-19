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
A verificação da tensão de compressão na biela (contra fcd1/fcd3, que este
módulo expõe como referência) fica fora do escopo automático desta função:
depende da largura efetiva do nó, que é geometria de apoio (placa, a0) sem
fórmula fechada no texto normativo.
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


def dimensionar_consolo(
    Fd_kn: float, Hd_kn: float, a_cm: float, d_cm: float, b_cm: float,
    h_cm: float, fck_mpa: float, fyk_mpa: float = 500.0,
    modelo: str = "biela_tirante", gama_c: float = GAMA_C,
    gama_s: float = GAMA_S, gama_n: float | None = None,
    a0_cm: float | None = None, consolo_continuo: bool = False,
    cargas_horizontais_verticais_pequenas: bool = False,
    Fd_indireta_kn: float = 0.0,
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
    vêm no resultado só como referência (22.3.2): verificar a tensão de
    compressão na biela exige a largura efetiva do nó, que depende da
    geometria de apoio (placa, a0) e não tem fórmula fechada na norma; quem
    tiver essa geometria calcula a tensão e chama
    ``bielas_tirantes_nbr6118.verificar_no`` diretamente.

    ``modelo='atrito'`` (atrito-cisalhamento, usual em consolos muito
    curtos) não está implementado: 22.5.1.3 cita o método apenas de forma
    qualitativa, sem os coeficientes de atrito necessários ao
    dimensionamento, e este módulo não inventa constante sem fonte
    normativa — levanta ``NotImplementedError``.

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

    z = braco_alavanca_consolo_cm(d_cm)
    Rsd = Rsd_tirante_consolo_kn(Fd_amp, Hd_amp, a_cm, z)

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
    if a0_cm is not None:
        gancho = verificar_gancho_vertical_consolo(
            b_cm, a_cm, a0_cm, consolo_continuo, cargas_horizontais_verticais_pequenas,
        )

    memoria = [
        f"22.5.1.1: a/d = {float(a_cm):g}/{float(d_cm):g} -> consolo {classif.classificacao} "
        f"(a/d = {classif.razao_a_d:.4f}).",
        f"22.2: gama_n = {gama_n_usado:g}; Fd = {float(Fd_kn):g} kN -> Fd,amp = {Fd_amp:.4f} kN; "
        f"Hd = {float(Hd_kn):g} kN -> Hd,amp = {Hd_amp:.4f} kN.",
        f"22.5.1.3: z = 0,85·d = 0,85·{float(d_cm):g} = {z:.4f} cm (aproximação adotada, ver "
        "docstring do módulo).",
        f"22.5.1.3: Rsd = Fd,amp·a/z + Hd,amp = {Fd_amp:.4f}·{float(a_cm):g}/{z:.4f} + "
        f"{Hd_amp:.4f} = {Rsd:.4f} kN.",
        f"22.3.3: As,tirante = Rsd/fyd = {Rsd:.4f}/{fyd_kncm2:.4f} = {As_tirante:.4f} cm2.",
        f"22.5.1.4.1: As,mín (17.3.5.2, viga fictícia {float(b_cm):g}×{float(h_cm):g} cm) = "
        f"{As_min:.4f} cm2 -> As = max(As,tirante, As,mín) = {As:.4f} cm2.",
        f"22.3.2 (referência): fcd1 = {fcd1:.4f} kN/cm2, fcd3 = {fcd3:.4f} kN/cm2 (verificar a "
        "tensão na biela exige a largura efetiva do nó, fora do escopo desta função).",
        f"22.5.1.4.3: As,costura,mín = 0,40·As = 0,40·{As:.4f} = {As_costura:.4f} cm2, em estribos "
        f"horizontais distribuídos em (2/3)·d = {altura_costura:.4f} cm.",
        (
            f"22.5.1.4.4: Fd,indireta = {float(Fd_indireta_kn):g} kN -> As,susp = {As_susp:.4f} cm2."
            if float(Fd_indireta_kn) > 0.0 else
            "22.5.1.4.4: sem carga indireta informada -> sem exigência de armadura de suspensão."
        ),
    ]
    if gancho is not None:
        memoria.extend(gancho.memoria)

    return ResultadoConsolo(
        Fd_kn=float(Fd_kn), Hd_kn=float(Hd_kn), a_cm=float(a_cm), d_cm=float(d_cm),
        b_cm=float(b_cm), h_cm=float(h_cm), fck_mpa=float(fck_mpa), fyk_mpa=float(fyk_mpa),
        modelo=modelo, classificacao=classif.classificacao, gama_n=gama_n_usado,
        Fd_amp_kn=Fd_amp, Hd_amp_kn=Hd_amp, z_cm=z, Rsd_kn=Rsd,
        As_tirante_cm2=As_tirante, As_min_cm2=As_min, As_cm2=As,
        fcd1_kncm2=fcd1, fcd3_kncm2=fcd3,
        As_costura_min_cm2=As_costura, altura_costura_cm=altura_costura,
        Fd_indireta_kn=float(Fd_indireta_kn), As_suspensao_cm2=As_susp,
        gancho_vertical=gancho, ok=True, governante="22.5.1.3",
        memoria=tuple(memoria),
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
) -> ResultadoDenteGerber:
    """Dimensiona um dente Gerber (22.5.2.3, PDF p. 210), reaproveitando o
    modelo do consolo (22.5.1.3) com os ajustes de 22.5.2.2: a biela do
    dente Gerber é usualmente mais inclinada, porque busca apoio na
    armadura de suspensão dentro da viga (Figura 22.6), em vez de se apoiar
    diretamente no pilar como no consolo — este módulo não modela essa
    geometria à parte; reaproveita ``dimensionar_consolo`` tal como está
    (mesma aproximação de braço de alavanca, z = 0,85·d) e acrescenta a
    suspensão obrigatória do dente Gerber.

    Aplicam-se as recomendações de 22.5.1.4, exceto 22.5.1.4.4 (suspensão
    por carga indireta), que "perde sentido no caso da carga indireta"
    (22.5.2.4.1): por isso esta função chama ``dimensionar_consolo`` com
    ``Fd_indireta_kn=0`` e soma, à parte, a suspensão própria do dente
    Gerber (22.5.2.4.2, sempre exigida, para a totalidade de Fd,amp).

    Parâmetros iguais aos de ``dimensionar_consolo`` (sem ``a0_cm`` etc.:
    o dente Gerber sempre exige suspensão em toda a altura da viga, então a
    restrição de gancho vertical do tirante não é o detalhe crítico aqui —
    quem precisar dela pode chamar ``verificar_gancho_vertical_consolo``
    à parte).
    """
    consolo = dimensionar_consolo(
        Fd_kn, Hd_kn, a_cm, d_cm, b_cm, h_cm, fck_mpa, fyk_mpa, modelo,
        gama_c, gama_s, gama_n, Fd_indireta_kn=0.0,
    )
    fyd_kncm2 = nbr.mpa_para_kncm2(nbr.fyd(fyk_mpa, gama_s))
    As_susp_dente = As_suspensao_dente_cm2(consolo.Fd_amp_kn, fyd_kncm2)
    memoria = consolo.memoria + (
        "22.5.2.3: dente Gerber -- mesmos princípios do consolo (22.5.1.3), com os "
        "ajustes de 22.5.2.2 (biela mais inclinada, apoio na armadura de suspensão).",
        f"22.5.2.4.2: As,susp (dente Gerber) = Fd,amp/fyd = {consolo.Fd_amp_kn:.4f}/"
        f"{fyd_kncm2:.4f} = {As_susp_dente:.4f} cm2 (sempre exigida, independente de "
        "carga indireta -- 22.5.2.4.1).",
    )
    return ResultadoDenteGerber(
        consolo=consolo, As_suspensao_dente_cm2=As_susp_dente, ok=True,
        governante="22.5.2.3", memoria=memoria,
    )
