"""Estabilidade global e imperfeições geométricas globais — ABNT NBR 6118:2026.

Cobre a classificação da estrutura em nós fixos ou nós móveis (15.4.2), os dois
processos aproximados de dispensa dos efeitos globais de 2ª ordem — o parâmetro
de instabilidade α (15.5.1, 15.5.2) e o coeficiente γz (15.5.3) —, as rigidezes
aproximadas para a não linearidade física na análise global (15.7.3), o
processo aproximado de majoração das ações horizontais por 0,95·γz (15.7.2) e
o desaprumo global dos elementos verticais, com a regra de combinação entre
vento e desaprumo (11.3.3.4.1).

Norma: ABNT NBR 6118:2026, 5ª edição (11/03/2026). As páginas citadas são as
do PDF (a página impressa é 18 a menos).

Unidades: este módulo trabalha com grandezas de análise global, em que a
própria norma expressa a altura em metros (11.3.3.4.1, 15.5.2) — por isso os
sufixos de comprimento aqui são ``_m`` (altura, deslocamento), além dos já
usuais ``_cm`` e ``_mm`` quando a grandeza é de seção. Força em kN (``_kn``) e
momento em kN·m (``_knm``), o par natural de H em metros. Rigidez EcsIc/EI
aparece em kN·m² (``_knm2``) quando combinada com H em metros (α, rigidez do
pilar equivalente) e em kN·cm² (``_kncm2``) quando combinada com Ic de seção
em cm4, como no núcleo (15.7.3).

Este módulo não reimplementa fórmula de material: Ecs vem de
``nucleo_nbr6118.Ecs`` (8.2.8); a majoração de 10% de 15.5.1 é só um fator
aplicado sobre esse valor.

De onde vêm as entradas — cada função recebe o resultado de uma análise de
pórtico/grelha, que pode vir do modelo próprio da biblioteca (pacote P46,
ainda não implementado) ou de um programa externo (TQS, SAP2000): deslocamento
de topo, M1,tot,d, ΔMtot,d. A docstring de cada função diz explicitamente qual
número é esperado e de onde ele normalmente sai.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError
AvisoNBR6118 = nbr.AvisoNBR6118


def _validar_positivo(valor: float, nome: str) -> float:
    """Confere que uma grandeza geométrica ou física é > 0."""
    v = float(valor)
    if not (v > 0.0):
        raise ValueError(f"{nome} tem de ser positivo; recebido {v:g}.")
    return v


def _fmt4(valor: float) -> str:
    """Formata um número com 4 casas decimais e vírgula (padrão PT-BR)."""
    return f"{valor:.4f}".replace(".", ",")


# ---------------------------------------------------------------------------
# 15.5.1 — Majoração do Ecs na análise de estabilidade global (PDF p. 124)
# ---------------------------------------------------------------------------
FATOR_ECS_ESTABILIDADE = 1.10  # 15.5.1: majoração de 10% permitida na análise
                                 # de estabilidade global que trata a estrutura
                                 # como um todo (não se aplica a esforços locais).


def Ecs_estabilidade_mpa(fck_mpa: float, alpha_e: float = 1.0,
                          majorar: bool = True) -> float:
    """Ecs representativo para a análise de estabilidade global, MPa (15.5.1).

    Na análise que trata a estrutura como um todo (o parâmetro α de 15.5.2 e
    o γz de 15.5.3, via as rigidezes de 15.7.3), o valor representativo do
    módulo de deformação secante (8.2.8) pode ser majorado em 10%:

        Ecs,estabilidade = 1,10 * Ecs(fck)   se majorar (padrão)
        Ecs,estabilidade = Ecs(fck)          se não

    fck_mpa: resistência característica do concreto, MPa.
    alpha_e: coeficiente do agregado graúdo de 8.2.8 (``nucleo_nbr6118.alpha_E``).
    majorar: aplica ou não o fator de 10% de 15.5.1 (padrão True).

    A majoração é uma permissão ("pode"), não uma obrigação: com
    ``majorar=False`` a função devolve o Ecs comum de 8.2.8, para quem prefere
    ficar do lado seguro sem a majoração.

    Fonte: NBR 6118:2026, 15.5.1 (PDF p. 124).
    """
    ecs = nbr.Ecs(fck_mpa, alpha_e)
    return ecs * FATOR_ECS_ESTABILIDADE if majorar else ecs


# ---------------------------------------------------------------------------
# 15.5.2 — Parâmetro de instabilidade α (PDF p. 124-125)
# ---------------------------------------------------------------------------
def parametro_alfa(Htot_m: float, Nk_kn: float, EcsIc_knm2: float) -> float:
    """Parâmetro de instabilidade α de uma estrutura reticulada simétrica (15.5.2).

        alfa = Htot * sqrt(Nk / (Ecs*Ic))

    Htot_m: altura total da estrutura, medida do topo da fundação (ou de um
        nível pouco deslocável do subsolo) até o topo, em metros.
    Nk_kn: somatório de todas as cargas verticais atuantes na estrutura, a
        partir do nível considerado para Htot, com valor característico, kN.
    EcsIc_knm2: rigidez EcsIc do pilar equivalente (ver
        ``rigidez_pilar_equivalente``), somatório da rigidez de todos os
        pilares na direção considerada, ou a rigidez de um pilar equivalente
        de seção constante quando a estrutura é de pórticos, treliças, mista
        ou com pilares de rigidez variável, kN·m². Ic com a seção bruta dos
        pilares; Ecs, com a majoração opcional de 15.5.1
        (``Ecs_estabilidade_mpa``).

    Vem de uma análise de pórtico/grelha 3D (modelo próprio, P46, ou de
    programa externo como o TQS/SAP2000): Nk é a soma das reações verticais
    características; EcsIc,equiv vem do deslocamento de topo sob carga
    horizontal (``rigidez_pilar_equivalente``).

    Fonte: NBR 6118:2026, 15.5.2 (PDF p. 124-125).
    """
    H = _validar_positivo(Htot_m, "Htot_m")
    N = _validar_positivo(Nk_kn, "Nk_kn")
    EI = _validar_positivo(EcsIc_knm2, "EcsIc_knm2")
    return H * math.sqrt(N / EI)


_CONTRAVENTAMENTO_ALFA1 = {
    "usual": 0.6,
    "associacaopilarparede": 0.6,
    "porticosassociadosapilarparede": 0.6,
    "parede": 0.7,
    "pilarparede": 0.7,
    "porticos": 0.5,
    "portico": 0.5,
}


def alfa1(n_andares: int, contraventamento: str = "usual") -> float:
    """Valor-limite α1 do parâmetro de instabilidade (15.5.2).

        alfa1 = 0,2 + 0,1*n   se n <= 3
        alfa1 = 0,6           se n >= 4  (estruturas usuais de edifícios)

    Para n >= 4, o valor-limite depende do tipo de contraventamento
    (exceções do texto, PDF p. 125):
        - "usual" (padrão), associação de pilares-parede, ou pórticos
          associados a pilares-parede: alfa1 = 0,6;
        - contraventamento constituído exclusivamente por pilares-parede
          ("parede"/"pilar_parede"): alfa1 = 0,7;
        - contraventamento só por pórticos ("porticos"): alfa1 = 0,5.
    Para n <= 3 a norma só dá a fórmula 0,2+0,1n, sem exceção por tipo de
    contraventamento; o parâmetro ``contraventamento`` é ignorado nesse caso.

    n_andares: número de níveis de barras horizontais (andares) acima da
        fundação ou de um nível pouco deslocável do subsolo.

    Fonte: NBR 6118:2026, 15.5.2 (PDF p. 124-125).
    """
    n = int(n_andares)
    if n < 1:
        raise ValueError(f"n_andares tem de ser >= 1; recebido {n_andares!r}.")
    if n <= 3:
        return 0.2 + 0.1 * n
    chave = nbr._chave(contraventamento)
    if chave not in _CONTRAVENTAMENTO_ALFA1:
        raise ValueError(
            f"contraventamento desconhecido: {contraventamento!r}. Use "
            f"'usual', 'pilar_parede' ou 'porticos'."
        )
    return _CONTRAVENTAMENTO_ALFA1[chave]


# ---------------------------------------------------------------------------
# 15.5.2 — Rigidez EcsIc de um pilar equivalente (PDF p. 125)
# ---------------------------------------------------------------------------
def rigidez_pilar_equivalente(Htot_m: float, F_kn: float, delta_topo_m: float) -> float:
    """Rigidez EcsIc de um pilar equivalente de seção constante (15.5.2).

    A norma pede um pilar equivalente, de seção constante, engastado na base
    e livre no topo, com a mesma altura Htot, que sofra o mesmo deslocamento
    de topo que a subestrutura de contraventamento sob o mesmo carregamento
    horizontal. Para um pilar em balanço com uma força horizontal F no topo,
    a mecânica das estruturas clássica dá o deslocamento de topo

        delta_topo = F * Htot^3 / (3 * EcsIc)

    e este módulo resolve para a rigidez equivalente:

        EcsIc,equiv = F * Htot^3 / (3 * delta_topo)

    Htot_m: altura total da estrutura (do topo da fundação ao topo), m.
    F_kn: força horizontal total aplicada no topo, na direção considerada, kN.
    delta_topo_m: deslocamento horizontal de topo da subestrutura de
        contraventamento sob F, obtido de uma análise de pórtico/grelha 3D
        (modelo próprio, P46, ou TQS/SAP2000), m.

    Retorna EcsIc,equiv em kN·m² (compatível com ``parametro_alfa`` e com
    ``gama_z``/``rigidezes_aproximadas`` quando também expressos em metros).

    Caso trivial (conferência): um único pilar isolado, de rigidez EI0,
    engastado na base, com o próprio F e o delta_topo que ele mesmo produz
    (delta_topo = F*Htot^3/(3*EI0)), devolve EcsIc,equiv = EI0 — o pilar
    equivalente de um único pilar é o próprio pilar, sem pórticos associados.

    Fonte: NBR 6118:2026, 15.5.2 (PDF p. 125); a fórmula do pilar em balanço é
    mecânica das estruturas clássica, não um número tabelado da norma.
    """
    H = _validar_positivo(Htot_m, "Htot_m")
    F = _validar_positivo(F_kn, "F_kn")
    delta = _validar_positivo(delta_topo_m, "delta_topo_m")
    return F * H ** 3 / (3.0 * delta)


# ---------------------------------------------------------------------------
# 15.5.3 — Coeficiente γz (PDF p. 125)
# ---------------------------------------------------------------------------
GAMA_Z_LIMITE_NOS_FIXOS = 1.10  # 15.5.3: nós fixos se gama_z <= 1,10


def gama_z(M1tot_d_knm: float, delta_Mtot_d_knm: float) -> float:
    """Coeficiente γz de avaliação dos esforços globais de 2ª ordem (15.5.3).

        gama_z = 1 / (1 - ΔMtot,d / M1,tot,d)

    Válido para estruturas reticuladas de no mínimo 4 andares, a partir de
    uma análise linear de 1ª ordem com as rigidezes aproximadas de 15.7.3
    (``rigidezes_aproximadas``). Nós fixos se gama_z <= 1,1
    (``GAMA_Z_LIMITE_NOS_FIXOS``).

    M1tot_d_knm: momento de tombamento na base — soma dos momentos de todas
        as forças horizontais da combinação considerada, com valores de
        cálculo, em relação à base da estrutura, kN·m. Vem de uma análise
        linear de 1ª ordem (modelo próprio, P46, ou TQS/SAP2000).
    delta_Mtot_d_knm: soma dos produtos de todas as forças verticais
        atuantes, com valores de cálculo, pelos deslocamentos horizontais de
        1ª ordem de seus respectivos pontos de aplicação, kN·m. Mesma origem
        que M1tot_d_knm.

    Caso-limite ΔMtot,d = 0 (estrutura sem deslocamento horizontal sob a
    combinação considerada): gama_z = 1,0.

    Fonte: NBR 6118:2026, 15.5.3 (PDF p. 125).
    """
    M1 = float(M1tot_d_knm)
    if not (M1 > 0.0):
        raise ValueError(
            f"M1tot_d_knm (momento de tombamento na base) tem de ser positivo; "
            f"recebido {M1:g}."
        )
    dM = float(delta_Mtot_d_knm)
    return 1.0 / (1.0 - dM / M1)


# ---------------------------------------------------------------------------
# 15.4.2 — Classificação em nós fixos ou nós móveis (PDF p. 123)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoClassificacaoNos:
    """Resultado de 15.4.2: estrutura de nós fixos x nós móveis."""

    alfa: float | None
    alfa1_valor: float | None
    gama_z: float | None
    gama_z_limite: float
    nos_fixos: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def classificar_nos(
    alfa: float | None = None,
    alfa1_valor: float | None = None,
    gama_z: float | None = None,
    gama_z_limite: float = GAMA_Z_LIMITE_NOS_FIXOS,
) -> ResultadoClassificacaoNos:
    """Classifica a estrutura em nós fixos ou nós móveis (15.4.2).

    Nós fixos: os deslocamentos horizontais dos nós são pequenos e os
    efeitos globais de 2ª ordem são desprezíveis (inferiores a 10% dos
    esforços de 1ª ordem). Nós móveis: caso contrário.

    Na prática, a classificação usa um dos dois processos aproximados de
    dispensa (15.5): alfa < alfa1 (15.5.2), ou gama_z <= 1,1 (15.5.3). Passe
    o par (alfa, alfa1_valor) — de ``parametro_alfa``/``alfa1`` — e/ou
    gama_z — de ``gama_z`` — conforme o processo escolhido.

    Quando os dois critérios são informados e discordam (um indica nós
    fixos, o outro nós móveis), esta função classifica como nós móveis: a
    norma não define qual dos dois processos aproximados prevalece sobre o
    outro, e nenhum dos dois é exato (são ambos aproximações para dispensar
    o cálculo rigoroso), então a decisão aqui é ficar do lado seguro quando
    eles não concordam — mesmo critério de "a favor da segurança" já usado
    noutros pontos do plano para lacuna da norma (ver PLANO, seção 8, item 6).

    A exceção de estruturas com deslocamento grande mas força normal pequena
    (por exemplo, postes), que dispensam a consideração dos efeitos de 2ª
    ordem mesmo sendo de nós móveis, não é avaliada aqui — é uma decisão de
    engenheiro sobre o caso concreto, fora do que este módulo automatiza.

    Fonte: NBR 6118:2026, 15.4.2 (PDF p. 123), com os limites de 15.5.2 e
    15.5.3 (PDF p. 124-125).
    """
    if alfa is None and gama_z is None:
        raise ValueError(
            "Informe ao menos um dos dois critérios: (alfa, alfa1_valor) ou gama_z."
        )
    if alfa is not None and alfa1_valor is None:
        raise ValueError("alfa1_valor é obrigatório quando alfa é informado.")

    memoria: list[str] = []
    veredictos: list[bool] = []

    if alfa is not None:
        a = float(alfa)
        a1 = float(alfa1_valor)
        fixos_alfa = a < a1 - 1e-9
        veredictos.append(fixos_alfa)
        memoria.append(
            f"15.5.2: alfa = {_fmt4(a)}, alfa1 = {_fmt4(a1)} -> "
            f"{'nós fixos (alfa < alfa1)' if fixos_alfa else 'nós móveis (alfa >= alfa1)'}."
        )

    if gama_z is not None:
        gz = float(gama_z)
        limite = float(gama_z_limite)
        fixos_gz = gz <= limite + 1e-9
        veredictos.append(fixos_gz)
        memoria.append(
            f"15.5.3: gama_z = {_fmt4(gz)}, limite = {_fmt4(limite)} -> "
            f"{'nós fixos (gama_z <= limite)' if fixos_gz else 'nós móveis (gama_z > limite)'}."
        )

    nos_fixos = all(veredictos)
    if len(veredictos) == 2 and veredictos[0] != veredictos[1]:
        memoria.append(
            "Critérios discordam; classificado como nós móveis (a favor da segurança)."
        )
    memoria.append(
        f"15.4.2: estrutura de {'nós fixos' if nos_fixos else 'nós móveis'}."
    )

    return ResultadoClassificacaoNos(
        alfa=None if alfa is None else float(alfa),
        alfa1_valor=None if alfa1_valor is None else float(alfa1_valor),
        gama_z=None if gama_z is None else float(gama_z),
        gama_z_limite=float(gama_z_limite),
        nos_fixos=nos_fixos,
        ok=True,
        governante="15.4.2",
        memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# 15.7.2 — Processo aproximado de majoração por 0,95·γz (PDF p. 126)
# ---------------------------------------------------------------------------
GAMA_Z_LIMITE_PROCESSO_095 = 1.30  # 15.7.2: processo só vale para gama_z <= 1,3


def majoracao_horizontal(gama_z: float) -> float:
    """Fator de majoração adicional das ações horizontais, 0,95·γz (15.7.2).

        fator = 0,95 * gama_z,   válido só se gama_z <= 1,3

    Aproxima os esforços finais (1ª + 2ª ordem globais) majorando
    adicionalmente as ações horizontais da combinação considerada por esse
    fator e refazendo a análise linear com as rigidezes de 15.7.3. Fora da
    faixa de validade (gama_z > 1,3), a norma não autoriza este processo
    aproximado — levanta ``FaixaNormativaError`` em vez de devolver um
    número (é preciso um processo mais rigoroso, não o 0,95·γz).

    gama_z: coeficiente de 15.5.3 (``gama_z``), adimensional.

    Fonte: NBR 6118:2026, 15.7.2 (PDF p. 126).
    """
    gz = float(gama_z)
    if not (gz <= GAMA_Z_LIMITE_PROCESSO_095 + 1e-9):
        raise FaixaNormativaError(
            f"gama_z = {_fmt4(gz)} > {GAMA_Z_LIMITE_PROCESSO_095:g}: o processo "
            f"aproximado de 15.7.2 (majoração por 0,95*gama_z) não vale; é "
            f"preciso um processo mais rigoroso para os efeitos de 2ª ordem."
        )
    return 0.95 * gz


# ---------------------------------------------------------------------------
# 15.7.3 — Rigidezes aproximadas para a não linearidade física (PDF p. 126-127)
# ---------------------------------------------------------------------------
TABELA_15_7_3_FATOR_EI_SEC = {
    "laje": 0.3,
    "viga_as_diferente": 0.4,   # As' != As
    "viga_as_igual": 0.5,       # As' == As
    "pilar": 0.8,
}


def rigidezes_aproximadas(
    elemento: str,
    Ec_mpa: float,
    Ic_cm4: float,
    As_igual: bool | None = None,
) -> float:
    """Rigidez aproximada (EI)sec para a não linearidade física na análise global (15.7.3).

        lajes:   (EI)sec = 0,3 * Ec * Ic
        vigas:   (EI)sec = 0,4 * Ec * Ic   se As' != As
                 (EI)sec = 0,5 * Ec * Ic   se As' == As
        pilares: (EI)sec = 0,8 * Ec * Ic

    Válido para a análise dos esforços globais de 2ª ordem em estruturas
    reticuladas com no mínimo 4 andares (mesmo contexto de ``gama_z`` e dos
    processos aproximados de 15.5.2/15.5.3). Os valores são aproximados e não
    podem ser usados para avaliar esforços LOCAIS de 2ª ordem.

    elemento: "laje", "viga" ou "pilar" (aceita variantes com acento/maiúscula).
    Ec_mpa: valor representativo do módulo de deformação do concreto,
        conforme 15.5.1 (``Ecs_estabilidade_mpa``, com ou sem a majoração de
        10%), MPa.
    Ic_cm4: momento de inércia da seção bruta de concreto, incluindo mesas
        colaborantes quando for o caso, cm4.
    As_igual: obrigatório para "viga" — True se As' == As (armadura de
        compressão igual à de tração), False caso contrário. Ignorado para
        "laje" e "pilar".

    Retorna (EI)sec em kN·cm² (Ec em MPa = 0,1 kN/cm²; Ic em cm4).

    Exceção da norma (não avaliada automaticamente aqui, e sem parâmetro
    para isso): em edifícios com menos de 4 pavimentos e força normal de
    cálculo pequena nos elementos verticais (Nsd < 0,10*Ac*fcd), a norma diz
    apenas que "a redução de rigidez desses elementos deve ser avaliada de
    forma específica" (15.7.3, PDF p. 127) — não dá uma fórmula alternativa.
    Esta função não verifica esse caso nem levanta aviso; cabe ao engenheiro
    reconhecê-lo e tratá-lo à parte, sem usar os fatores tabelados acima.

    Fonte: NBR 6118:2026, 15.7.3 (PDF p. 126-127).
    """
    chave = nbr._chave(elemento)
    if chave == "laje":
        fator = TABELA_15_7_3_FATOR_EI_SEC["laje"]
    elif chave == "pilar":
        fator = TABELA_15_7_3_FATOR_EI_SEC["pilar"]
    elif chave == "viga":
        if As_igual is None:
            raise ValueError(
                "As_igual é obrigatório para elemento='viga' "
                "(True se As' == As, False se As' != As)."
            )
        fator = (
            TABELA_15_7_3_FATOR_EI_SEC["viga_as_igual"]
            if As_igual
            else TABELA_15_7_3_FATOR_EI_SEC["viga_as_diferente"]
        )
    else:
        raise ValueError(
            f"elemento desconhecido: {elemento!r}. Use 'laje', 'viga' ou 'pilar'."
        )
    Ec_kncm2 = float(Ec_mpa) * 0.1
    Ic = _validar_positivo(Ic_cm4, "Ic_cm4")
    return fator * Ec_kncm2 * Ic


# ---------------------------------------------------------------------------
# 11.3.3.4.1 — Desaprumo global (PDF p. 79)
# ---------------------------------------------------------------------------
THETA1_MIN = 1.0 / 300.0   # estruturas reticuladas e imperfeições locais
THETA1_MAX = 1.0 / 200.0


@dataclass(frozen=True)
class ResultadoDesaprumoGlobal:
    """Resultado de 11.3.3.4.1: ângulo de desaprumo dos elementos verticais."""

    H_m: float
    n_pilares: int
    theta1: float
    theta_a: float
    caso: str
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def desaprumo_global(
    H_m: float,
    n_pilares: int,
    lajes_lisas_ou_cogumelo: bool = False,
    pilar_isolado_em_balanco: bool = False,
) -> ResultadoDesaprumoGlobal:
    """Ângulo de desaprumo dos elementos verticais para a análise global (11.3.3.4.1).

        theta1 = 1 / (100*sqrt(H)),  com 1/300 <= theta1 <= 1/200  (H em m)
        theta_a = theta1 * sqrt((1 + 1/n) / 2)

    Casos particulares da norma:
        - predominância de lajes lisas ou cogumelo: theta_a = theta1;
        - pilar isolado em balanço: theta1 = 1/200 (o valor máximo, direto,
          sem passar pela fórmula de theta1(H); theta_a também vale theta1
          nesse caso, por não haver "n" pilares associados a considerar).

    H_m: altura total da edificação, m.
    n_pilares: número de pilares que contribuem para o efeito do desaprumo
        global, associados à altura H adotada.
    lajes_lisas_ou_cogumelo: True para edifícios com predominância de lajes
        lisas ou cogumelo (theta_a = theta1).
    pilar_isolado_em_balanco: True para pilar isolado em balanço
        (theta1 = 1/200, fixo).

    NOTA da norma: o desaprumo não precisa ser considerado nos
    estados-limites de serviço.

    Fonte: NBR 6118:2026, 11.3.3.4.1 e Figura 11.1 (PDF p. 79).
    """
    H = _validar_positivo(H_m, "H_m")
    n = int(n_pilares)
    if n < 1:
        raise ValueError(f"n_pilares tem de ser >= 1; recebido {n_pilares!r}.")

    memoria: list[str] = []
    if pilar_isolado_em_balanco:
        theta1 = THETA1_MAX
        memoria.append(
            f"11.3.3.4.1: pilar isolado em balanço -> theta1 = 1/200 = {_fmt4(theta1)}."
        )
    else:
        theta1_bruto = 1.0 / (100.0 * math.sqrt(H))
        theta1 = min(max(theta1_bruto, THETA1_MIN), THETA1_MAX)
        memoria.append(
            f"11.3.3.4.1: theta1 = 1/(100*sqrt({H:g})) = {_fmt4(theta1_bruto)}, "
            f"limitado a [1/300, 1/200] -> theta1 = {_fmt4(theta1)}."
        )

    if lajes_lisas_ou_cogumelo:
        theta_a = theta1
        caso = "lajes_lisas_ou_cogumelo"
        memoria.append("Predominância de lajes lisas/cogumelo -> theta_a = theta1.")
    elif pilar_isolado_em_balanco:
        theta_a = theta1
        caso = "pilar_isolado_em_balanco"
        memoria.append("Pilar isolado em balanço -> theta_a = theta1.")
    else:
        fator_n = math.sqrt((1.0 + 1.0 / n) / 2.0)
        theta_a = theta1 * fator_n
        caso = "geral"
        memoria.append(
            f"theta_a = theta1*sqrt((1+1/{n})/2) = {_fmt4(theta1)}*{_fmt4(fator_n)} "
            f"= {_fmt4(theta_a)}."
        )

    return ResultadoDesaprumoGlobal(
        H_m=H,
        n_pilares=n,
        theta1=theta1,
        theta_a=theta_a,
        caso=caso,
        ok=True,
        governante="11.3.3.4.1",
        memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# 11.3.3.4.1 — Combinação entre vento e desaprumo (PDF p. 79)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoCombinacaoVentoDesaprumo:
    """Resultado de 11.3.3.4.1: combinação entre a ação do vento e o desaprumo."""

    M_vento: float
    M_desaprumo: float
    caso: str
    M_calculo: float
    considerar_theta1min: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def combinar_vento_desaprumo(
    M_vento: float, M_desaprumo: float
) -> ResultadoCombinacaoVentoDesaprumo:
    """Regra de combinação entre a ação do vento e o desaprumo global (11.3.3.4.1).

    A comparação (conforme a norma) é feita com os momentos totais na base da
    construção, na mesma direção e sentido da ação do vento — M_vento e
    M_desaprumo devem já estar nessa forma (por exemplo, momentos de
    tombamento de uma combinação P4, ou o M1,tot,d desta mesma análise).

        a) se 0,3*M_vento > M_desaprumo:  considera-se somente o vento;
        b) se M_vento < 0,3*M_desaprumo:  considera-se somente o desaprumo,
           respeitando theta1,mín (``desaprumo_global`` sem
           ``pilar_isolado_em_balanco``, que é quem levaria theta1 a 1/200
           sem o piso de 1/300 já embutido);
        c) demais casos: combinam-se as duas ações, sem necessidade de
           considerar theta1,mín. Admite-se considerar ambas atuando na mesma
           direção e sentido, como equivalentes a uma única ação do vento,
           artificialmente amplificada para cobrir a superposição — aqui,
           M_calculo = M_vento + M_desaprumo.

    Os dois limiares de 30% NÃO são o mesmo ponto: (a) compara 0,3*M_vento
    com M_desaprumo; (b) compara M_vento com 0,3*M_desaprumo. No caso-limite
    de qualquer um dos dois (igualdade exata), a norma usa "maior que" e
    "inferior a" (desigualdades estritas), então a igualdade cai no caso (c).

    M_vento: momento do vento na base, na direção e sentido considerados
        (valor de cálculo ou característico, desde que M_desaprumo esteja na
        mesma base de comparação).
    M_desaprumo: momento do desaprumo global na base, calculado com theta_a
        (``desaprumo_global``), na mesma base de comparação que M_vento.

    Fonte: NBR 6118:2026, 11.3.3.4.1 (PDF p. 79).
    """
    V = float(M_vento)
    D = float(M_desaprumo)
    if V < 0.0:
        raise ValueError(f"M_vento tem de ser >= 0; recebido {V:g}.")
    if D < 0.0:
        raise ValueError(f"M_desaprumo tem de ser >= 0; recebido {D:g}.")

    memoria: list[str] = []
    if 0.3 * V > D + 1e-9:
        caso = "a"
        M_calc = V
        considerar_theta1min = False
        memoria.append(
            f"11.3.3.4.1 a): 0,3*M_vento = {_fmt4(0.3 * V)} > M_desaprumo = "
            f"{_fmt4(D)} -> considera-se somente o vento."
        )
    elif V < 0.3 * D - 1e-9:
        caso = "b"
        M_calc = D
        considerar_theta1min = True
        memoria.append(
            f"11.3.3.4.1 b): M_vento = {_fmt4(V)} < 0,3*M_desaprumo = "
            f"{_fmt4(0.3 * D)} -> considera-se somente o desaprumo "
            f"(respeitando theta1,mín)."
        )
    else:
        caso = "c"
        M_calc = V + D
        considerar_theta1min = False
        memoria.append(
            f"11.3.3.4.1 c): demais casos (0,3*M_vento = {_fmt4(0.3 * V)} <= "
            f"M_desaprumo = {_fmt4(D)} e M_vento = {_fmt4(V)} >= 0,3*M_desaprumo "
            f"= {_fmt4(0.3 * D)}) -> combina-se vento e desaprumo, sem "
            f"necessidade de theta1,mín. M_calculo = M_vento + M_desaprumo = "
            f"{_fmt4(M_calc)}."
        )

    return ResultadoCombinacaoVentoDesaprumo(
        M_vento=V,
        M_desaprumo=D,
        caso=caso,
        M_calculo=M_calc,
        considerar_theta1min=considerar_theta1min,
        ok=True,
        governante="11.3.3.4.1",
        memoria=tuple(memoria),
    )
