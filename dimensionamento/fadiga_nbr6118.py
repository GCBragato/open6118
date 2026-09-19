"""Fadiga da armadura, curvas S-N e vibração -- ABNT NBR 6118:2026, Seção 23
(Pacote P38).

Cobre a parte da Seção 23 que fecha com número e tabela verificáveis:
    - 23.3 (PDF p. 215-216) -- estado-limite de vibrações excessivas,
      fn > 1,2 fcrit, com a Tabela 23.1 (fcrit por tipo de uso) e o piso
      fn >= 3 Hz.
    - 23.5.1 (PDF p. 216-217) -- faixa de aplicabilidade da fadiga
      (20 000 a 2 000 000 de ciclos) e a regra de Palmgren-Miner.
    - 23.5.5 (PDF p. 220-223) -- verificação da fadiga da armadura passiva
      ou ativa, gama_f*Delta_sigma_Ss <= Delta_fsd,fad, com a Tabela 23.2
      (Delta_fsd,fad,min para 2x10^6 ciclos), a Tabela 23.3 (parâmetros
      das curvas S-N) e a curva S-N para outros números de ciclos, com o
      teto da barra reta (nota e) e o fator redutor do pino de dobramento
      (nota d).
    - 23.5.5, nota da p. 223 -- redução de 30% quando o relevo da nervura
      não atende r/h < 0,5 sem dado experimental.
    - 23.6 (PDF p. 223) -- estimativa do aumento progressivo de deformação
      (flecha) sob n ciclos de carga.

Fora do escopo deste pacote (não pedido pelo plano em P38): 23.5.4,
fadiga do concreto em compressão e em tração (fcd,fad, fctd,fad), e a
correção do ângulo das bielas por cortante cíclico (23.5.3); ambas citadas
aqui só como contexto porque aparecem nas mesmas páginas.

Convenções: como o núcleo -- tensão em MPa, diâmetro em mm, comprimento em
cm, número de ciclos adimensional (float, aceita notação científica).
Depende de P9 (els_fissuracao_nbr6118.tensoes_servico) para o
Delta_sigma_s de entrada de `verificar_fadiga_armadura`: este módulo não
recalcula tensão de seção, só compara com o limite normativo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
    import seguranca_nbr6118 as seg
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr
    from dimensionamento import seguranca_nbr6118 as seg

FaixaNormativaError = nbr.FaixaNormativaError


# ---------------------------------------------------------------------------
# 23.3 -- Tabela 23.1 e verificação de vibrações excessivas (PDF p. 215-216)
# ---------------------------------------------------------------------------
TABELA_23_1_FCRIT_HZ = {
    "ginasioacademia": 8.0,
    "saladancaconcertosemcadeirafixa": 7.0,
    "passarelapedestresciclistas": 4.5,
    "escritorio": 4.0,
    "salaconcertocomcadeirafixa": 3.5,
}
"""Tabela 23.1 -- fcrit (Hz), Frequência crítica para vibrações verticais
para alguns casos especiais de estruturas submetidas a vibrações pela ação
de pessoas (23.3, PDF p. 216). Chaves normalizadas por `nucleo_nbr6118._chave`
(sem acento, espaço, hífen ou sublinhado); use `fcrit_tabela_23_1` para
consultar com os nomes usuais ('ginasio_academia', 'escritorio' etc.)."""

_TABELA_23_1_NOMES = (
    "ginasio_academia",
    "sala_danca_concerto_sem_cadeira_fixa",
    "passarela_pedestres_ciclistas",
    "escritorio",
    "sala_concerto_com_cadeira_fixa",
)

FN_MIN_HZ = 3.0
"""Piso absoluto: 'em nenhum caso a frequência natural da estrutura do piso
pode ser inferior a 3 Hz' (23.3, PDF p. 216), independente de fcrit."""


def fcrit_tabela_23_1(uso: str) -> float:
    """fcrit (Hz) pela Tabela 23.1, pelo tipo de uso/destinação da estrutura
    (23.3, PDF p. 216).

    uso: 'ginasio_academia' (8,0 Hz), 'sala_danca_concerto_sem_cadeira_fixa'
    (7,0 Hz), 'passarela_pedestres_ciclistas' (4,5 Hz), 'escritorio'
    (4,0 Hz) ou 'sala_concerto_com_cadeira_fixa' (3,5 Hz). Valores na
    falta de determinação experimental (a norma permite adotá-los).
    """
    chave = nbr._chave(uso)
    if chave not in TABELA_23_1_FCRIT_HZ:
        raise ValueError(
            f"Uso desconhecido para a Tabela 23.1: {uso!r}. "
            f"Use um destes: {', '.join(_TABELA_23_1_NOMES)}."
        )
    return TABELA_23_1_FCRIT_HZ[chave]


@dataclass(frozen=True)
class ResultadoVibracao:
    """Verificação do estado-limite de vibrações excessivas (23.3, PDF p. 216)."""
    fn_hz: float
    fcrit_hz: float
    limite_hz: float
    fn_min_hz: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_vibracao(fn_hz: float, uso: str | None = None,
                       fcrit_hz: float | None = None) -> ResultadoVibracao:
    """Verifica fn > 1,2 fcrit e fn >= 3 Hz (23.3, PDF p. 215-216).

    fn_hz: frequência natural da estrutura, determinada por análise modal
    computacional ou experimental (a norma não entra em como calculá-la;
    número vindo de fora, ex.: SAP2000/TQS). Informe `uso` (consulta a
    Tabela 23.1) ou `fcrit_hz` diretamente (caso especial, máquina, ou
    valor determinado experimentalmente); um dos dois é obrigatório.

    A relação fn > 1,2 fcrit é uma avaliação simplificada, a critério do
    projetista (23.3); em qualquer caso, fn nunca pode ser menor que 3 Hz.
    """
    if fcrit_hz is None:
        if uso is None:
            raise ValueError(
                "Informe uso (para consultar a Tabela 23.1) ou fcrit_hz diretamente."
            )
        fcrit = fcrit_tabela_23_1(uso)
    else:
        fcrit = float(fcrit_hz)
    fn = float(fn_hz)
    limite = 1.2 * fcrit
    ok_afastamento = fn > limite
    ok_piso = fn >= FN_MIN_HZ
    ok = ok_afastamento and ok_piso
    if not ok_piso:
        governante = f"fn >= {FN_MIN_HZ:g} Hz (piso mínimo, 23.3) -- não ok"
    elif not ok_afastamento:
        governante = "fn > 1,2 fcrit (23.3) -- não ok"
    else:
        governante = "fn > 1,2 fcrit e fn >= 3 Hz (23.3) -- ok"
    memoria = (
        f"23.3: fn = {fn:g} Hz; fcrit = {fcrit:g} Hz; limite = 1,2 x fcrit = {limite:g} Hz.",
        f"fn > 1,2 fcrit: {fn:g} > {limite:g} -> {'ok' if ok_afastamento else 'não ok'}.",
        f"fn >= {FN_MIN_HZ:g} Hz (piso mínimo): {fn:g} >= {FN_MIN_HZ:g} -> "
        f"{'ok' if ok_piso else 'não ok'}.",
    )
    return ResultadoVibracao(fn, fcrit, limite, FN_MIN_HZ, ok, governante, memoria)


# ---------------------------------------------------------------------------
# 23.5.1 -- faixa de aplicabilidade e Palmgren-Miner (PDF p. 216-217)
# ---------------------------------------------------------------------------
N_CICLOS_MIN = 20_000.0
"""Abaixo disso a Seção 23 não trata a ação: 'não são tratadas nesta Norma
as ações de fadiga de alta intensidade, capazes de provocar danos com
menos de 20 000 repetições' (23.5.1, PDF p. 216)."""

N_CICLOS_MAX = 2_000_000.0
"""Até isso a Seção 23 cobre a ação: 'as ações de fadiga de média e baixa
intensidade e número de repetições até 2 000 000 de ciclos são
consideradas nas disposições estabelecidas nesta Seção' (23.5.1,
PDF p. 217); e também o número de ciclos de referência da Tabela 23.2."""


def faixa_aplicabilidade(n_ciclos: float) -> float:
    """Confere que o número de ciclos está na faixa que a Seção 23 cobre,
    20 000 <= n <= 2 000 000 (23.5.1, PDF p. 216-217).

    Abaixo de 20 000 repetições a norma não trata a ação (fadiga de alta
    intensidade); acima de 2 000 000 de ciclos a combinação e as curvas
    S-N desta Seção deixam de estar cobertas (precisa de análise
    especial). Não numeriza a exceção da nota de 23.5.1 para pontes
    rodoviárias (exclusão de veículos com carga total até 30 kN do
    espectro): é uma regra de montagem do carregamento, não um limite
    numérico desta função. Levanta FaixaNormativaError fora da faixa;
    dentro dela, devolve n_ciclos (float), para uso encadeado.
    """
    n = float(n_ciclos)
    if n < N_CICLOS_MIN:
        raise FaixaNormativaError(
            f"n = {n:g} ciclos: abaixo de {N_CICLOS_MIN:g}, a NBR 6118:2026 não "
            "trata a ação (fadiga de alta intensidade, 23.5.1)."
        )
    if n > N_CICLOS_MAX:
        raise FaixaNormativaError(
            f"n = {n:g} ciclos: acima de {N_CICLOS_MAX:g}, fora da faixa coberta "
            "pela Seção 23 (23.5.1) -- requer análise especial."
        )
    return n


@dataclass(frozen=True)
class ResultadoPalmgrenMiner:
    """Dano acumulado de fadiga pela regra de Palmgren-Miner (23.5.1, PDF p. 217)."""
    dano_total: float
    parcelas: tuple[float, ...]
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def palmgren_miner(espectro) -> ResultadoPalmgrenMiner:
    """Regra de Palmgren-Miner, soma(n_i/N_i) <= 1 (23.5.1, PDF p. 217).

    espectro: sequência de pares (n_i, N_i) -- n_i é o número de
    repetições aplicadas sob a condição particular i de tensões; N_i é o
    número de repetições que causaria ruptura por fadiga na mesma
    condição (obtido, para o aço, de `curva_SN`/`delta_fsd_fad` com o
    Delta_sigma correspondente; para o concreto, de fcd,fad/fctd,fad, fora
    do escopo deste pacote -- o chamador calcula N_i e só entrega o par
    aqui). Reaproveita `seguranca_nbr6118.verificar_seguranca` para o
    critério soma <= 1 (Rd = 1, Sd = soma).
    """
    pares = [(float(ni), float(Ni)) for ni, Ni in espectro]
    if not pares:
        raise ValueError("Espectro de cargas vazio: informe ao menos um par (n_i, N_i).")
    parcelas = []
    linhas = ["23.5.1 (Palmgren-Miner): soma(n_i/N_i) <= 1."]
    for i, (ni, Ni) in enumerate(pares, start=1):
        if Ni <= 0.0:
            raise ValueError(f"N_i deve ser positivo (condição {i}): N_i = {Ni:g}.")
        if ni < 0.0:
            raise ValueError(f"n_i não pode ser negativo (condição {i}): n_i = {ni:g}.")
        parcela = ni / Ni
        parcelas.append(parcela)
        linhas.append(f"  condição {i}: n_i = {ni:g}, N_i = {Ni:g}, n_i/N_i = {parcela:.6g}.")
    dano_total = sum(parcelas)
    resultado_seg = seg.verificar_seguranca(
        Rd=1.0, Sd=dano_total, rotulo="Palmgren-Miner", item="23.5.1",
    )
    linhas.append(
        f"soma(n_i/N_i) = {dano_total:.6g} -> "
        f"{'ok' if resultado_seg.ok else 'não ok (ruptura por fadiga acumulada)'}."
    )
    return ResultadoPalmgrenMiner(
        dano_total, tuple(parcelas), resultado_seg.ok, resultado_seg.governante,
        tuple(linhas),
    )


# ---------------------------------------------------------------------------
# 23.5.5 -- Tabela 23.2 (Delta_fsd,fad,min a 2x10^6 ciclos, PDF p. 220-221)
# ---------------------------------------------------------------------------
_PHIS_TABELA_23_2 = (10.0, 12.5, 16.0, 20.0, 22.0, 25.0, 32.0, 40.0)

TABELA_23_2_PASSIVA_MPA = {
    # 'barras retas ou dobradas com D >= 25*phi' -- Tipo T1
    "barra_reta": {
        10.0: 190.0, 12.5: 190.0, 16.0: 190.0, 20.0: 185.0,
        22.0: 180.0, 25.0: 175.0, 32.0: 165.0, 40.0: 150.0,
    },
    # 'barras dobradas ou estribos com D < 25*phi', Dmin = 8*phi, phi >= 20 mm -- Tipo T1
    "estribo_dmin_8phi": {
        10.0: 105.0, 12.5: 105.0, 16.0: 105.0, 20.0: 105.0,
        22.0: 100.0, 25.0: 95.0, 32.0: 90.0, 40.0: 85.0,
    },
    # Dmin = 5*phi, phi < 20 mm -- células de phi >= 20 mm não definidas ('-')
    "estribo_dmin_5phi": {
        10.0: 90.0, 12.5: 90.0, 16.0: 90.0, 20.0: None,
        22.0: None, 25.0: None, 32.0: None, 40.0: None,
    },
    # Dmin = 3*phi, phi <= 10 mm -- só a célula phi=10 mm definida
    "estribo_dmin_3phi": {
        10.0: 85.0, 12.5: None, 16.0: None, 20.0: None,
        22.0: None, 25.0: None, 32.0: None, 40.0: None,
    },
    # Ambiente marinho, Classe IV -- Tipo T4
    "marinho_classe_iv": {phi: 110.0 for phi in _PHIS_TABELA_23_2},
    # Barras soldadas (incluindo solda por ponto ou das extremidades) e
    # conectores mecânicos -- Tipo T4
    "soldada_ou_conector_mecanico": {phi: 85.0 for phi in _PHIS_TABELA_23_2},
}
"""Tabela 23.2 -- Delta_fsd,fad,min (MPa) para 2x10^6 ciclos, armadura
passiva CA-50 (23.5.5, PDF p. 220-221). Célula None = '-' na tabela (a
norma não define aquele caso); ver `delta_fsd_fad`, que levanta
FaixaNormativaError para essas combinações."""

TABELA_23_2_TIPO_PASSIVA = {
    "barra_reta": "T1",
    "estribo_dmin_8phi": "T1",
    "estribo_dmin_5phi": "T1",
    "estribo_dmin_3phi": "T1",
    "marinho_classe_iv": "T4",
    "soldada_ou_conector_mecanico": "T4",
}
"""Tipo de curva S-N (Tabela 23.3) de cada linha da Tabela 23.2, armadura
passiva."""

TABELA_23_2_ATIVA_MPA = {
    # Pré-tração, fios retos ou cordoalhas retas -- Tipo T1
    "ativa_pretracao_reta": 150.0,
    # Pós-tração aderente
    "ativa_postracao_cabo_bainha_plastica": 140.0,  # T7
    "ativa_postracao_cabo_bainha_metalica": 110.0,  # T6
    "ativa_dispositivo_emenda": 70.0,                # T5
}
"""Tabela 23.2 -- Delta_fsd,fad,min (MPa) para 2x10^6 ciclos, armadura ativa
CP-190RB e CP-210RB (23.5.5, PDF p. 221). Não depende de phi (a tabela não
tabela por diâmetro para armadura ativa)."""

TABELA_23_2_TIPO_ATIVA = {
    "ativa_pretracao_reta": "T1",
    "ativa_postracao_cabo_bainha_plastica": "T7",
    "ativa_postracao_cabo_bainha_metalica": "T6",
    "ativa_dispositivo_emenda": "T5",
}

_ALIASES_PASSIVA = {nbr._chave(nome): nome for nome in TABELA_23_2_PASSIVA_MPA}
_ALIASES_ATIVA = {nbr._chave(nome): nome for nome in TABELA_23_2_ATIVA_MPA}
_CASOS_VALIDOS = tuple(TABELA_23_2_PASSIVA_MPA) + tuple(TABELA_23_2_ATIVA_MPA)


def _phi_na_grade(phi_mm: float, caso: str) -> float:
    phi = float(phi_mm)
    for p in _PHIS_TABELA_23_2:
        if abs(phi - p) < 1e-6:
            return p
    raise FaixaNormativaError(
        f"A Tabela 23.2 só tabela phi em {_PHIS_TABELA_23_2} mm para {caso!r}; "
        f"phi = {phi:g} mm não está na tabela (sem interpolação)."
    )


def _lookup_23_2(caso: str, phi_mm: float | None):
    """(Delta_fsd,fad,min a 2x10^6 ciclos, tipo, Delta_fsd,fad,min da barra
    reta no mesmo phi ou None) para `caso`."""
    chave = nbr._chave(caso)
    if chave in _ALIASES_ATIVA:
        nome = _ALIASES_ATIVA[chave]
        return TABELA_23_2_ATIVA_MPA[nome], TABELA_23_2_TIPO_ATIVA[nome], None
    if chave not in _ALIASES_PASSIVA:
        raise ValueError(
            f"Caso desconhecido para a Tabela 23.2: {caso!r}. "
            f"Use um destes: {', '.join(_CASOS_VALIDOS)}."
        )
    nome = _ALIASES_PASSIVA[chave]
    if phi_mm is None:
        raise ValueError(
            f"Informe phi_mm para o caso {caso!r} (Tabela 23.2, armadura passiva)."
        )
    phi = _phi_na_grade(phi_mm, caso)
    valor = TABELA_23_2_PASSIVA_MPA[nome][phi]
    if valor is None:
        raise FaixaNormativaError(
            f"A Tabela 23.2 não define Delta_fsd,fad,min para {caso!r} com "
            f"phi = {phi:g} mm ('-' na tabela, 23.5.5)."
        )
    tipo = TABELA_23_2_TIPO_PASSIVA[nome]
    barra_reta = (
        None if nome == "barra_reta" else TABELA_23_2_PASSIVA_MPA["barra_reta"][phi]
    )
    return valor, tipo, barra_reta


def fator_redutor_pino_dobramento(D_mm: float, phi_mm: float) -> float:
    """Fator redutor xi = 0,35 + 0,026*D/phi (23.5.5, nota d, PDF p. 221).

    Nota d da Tabela 23.2: 'Valores obtidos pela multiplicação do fator
    redutor xi em função do diâmetro do pino de dobramento D e do
    diâmetro da barra phi'. Os valores tabelados de barras dobradas ou
    estribos com D < 25*phi vêm de xi vezes o Delta_fsd,fad,min da barra
    reta do mesmo phi (`TABELA_23_2_PASSIVA_MPA['barra_reta']`). Serve
    para estimar Delta_fsd,fad,min de um pino de dobramento fora dos três
    Dmin tabelados (8*phi, 5*phi, 3*phi): multiplique o resultado pelo
    valor da barra reta no phi desejado. D_mm e phi_mm na mesma unidade
    (mm); em D = 25*phi, xi = 1,0 (recai no valor da barra reta, o teto da
    nota e).
    """
    D = float(D_mm)
    phi = float(phi_mm)
    if phi <= 0.0:
        raise ValueError("phi_mm deve ser positivo.")
    if D < 0.0:
        raise ValueError("D_mm não pode ser negativo.")
    return 0.35 + 0.026 * (D / phi)


# ---------------------------------------------------------------------------
# 23.5.5 -- Tabela 23.3 e curva S-N (Figura 23.2, PDF p. 222)
# ---------------------------------------------------------------------------
TABELA_23_3 = {
    "T1": {"N_estrela": 1.0e6, "k1": 5, "k2": 9},
    "T2": {"N_estrela": 1.0e6, "k1": 3, "k2": 7},
    "T3": {"N_estrela": 1.0e6, "k1": 3, "k2": 5},
    "T4": {"N_estrela": 1.0e7, "k1": 3, "k2": 5},
    "T5": {"N_estrela": 1.0e6, "k1": 5, "k2": 5},
    "T6": {"N_estrela": 1.0e6, "k1": 5, "k2": 7},
    "T7": {"N_estrela": 1.0e6, "k1": 5, "k2": 10},
}
"""Tabela 23.3 -- Tipos da curva S-N: N* (número de ciclos de transição) e
os expoentes k1 (ramo N <= N*) e k2 (ramo N > N*) da lei de potência
(23.5.5, PDF p. 222)."""

N_REFERENCIA_CICLOS = N_CICLOS_MAX
"""2x10^6 ciclos: o número de referência dos valores da Tabela 23.2."""


def curva_SN(delta_fad_min_mpa: float, tipo: str, n_ciclos: float) -> float:
    """Resistência à fadiga da armadura para um número de ciclos qualquer,
    a partir do valor tabelado a 2x10^6 ciclos (23.5.5, Figura 23.2,
    PDF p. 222).

    A curva S-N é formada por dois segmentos de reta em escala log-log,
    (Delta_fsd,fad)^m x N = constante, com m = k1 para N <= N* e m = k2
    para N > N* (N*, k1, k2 da Tabela 23.3, por `tipo`, 'T1' a 'T7'). A
    constante de cada trecho é calibrada pelo ponto conhecido
    (N = 2x10^6 ciclos, `delta_fad_min_mpa` da Tabela 23.2) e pela
    continuidade em N = N* entre os dois trechos -- por isso
    `curva_SN(delta_fad_min_mpa, tipo, 2e6)` reproduz `delta_fad_min_mpa`
    exatamente, e os dois ramos coincidem em N = N*. Não aplica o teto da
    barra reta (nota e): isso é `delta_fsd_fad`.
    """
    if tipo not in TABELA_23_3:
        raise ValueError(
            f"Tipo de curva S-N desconhecido: {tipo!r}. Use 'T1' a 'T7' (Tabela 23.3)."
        )
    n = float(n_ciclos)
    if n <= 0.0:
        raise ValueError("n_ciclos deve ser positivo.")
    delta0 = float(delta_fad_min_mpa)
    if delta0 <= 0.0:
        raise ValueError("delta_fad_min_mpa deve ser positivo.")
    par = TABELA_23_3[tipo]
    n_estrela, k1, k2 = par["N_estrela"], par["k1"], par["k2"]
    k_ancora = k1 if N_REFERENCIA_CICLOS <= n_estrela else k2
    c_ancora = delta0 ** k_ancora * N_REFERENCIA_CICLOS
    delta_estrela = (c_ancora / n_estrela) ** (1.0 / k_ancora)
    if n <= n_estrela:
        k = k1
        c = delta_estrela ** k1 * n_estrela
    else:
        k = k2
        c = delta_estrela ** k2 * n_estrela
    return (c / n) ** (1.0 / k)


def delta_fsd_fad(caso: str, phi_mm: float | None = None,
                  n_ciclos: float = N_REFERENCIA_CICLOS) -> float:
    """Delta_fsd,fad: variação de tensão admissível à fadiga da armadura,
    MPa (23.5.5, Tabelas 23.2 e 23.3, PDF p. 220-222).

    caso, armadura passiva CA-50 (precisa de phi_mm, na grade da Tabela
    23.2 -- 10; 12,5; 16; 20; 22; 25; 32 ou 40 mm, sem interpolação):
    'barra_reta' (barras retas ou dobradas com D >= 25*phi),
    'estribo_dmin_8phi' (D = 8*phi, exigido para phi >= 20 mm),
    'estribo_dmin_5phi' (D = 5*phi, phi < 20 mm),
    'estribo_dmin_3phi' (D = 3*phi, phi <= 10 mm), 'marinho_classe_iv',
    'soldada_ou_conector_mecanico'.
    caso, armadura ativa CP-190RB/CP-210RB (phi_mm ignorado):
    'ativa_pretracao_reta', 'ativa_postracao_cabo_bainha_plastica',
    'ativa_postracao_cabo_bainha_metalica', 'ativa_dispositivo_emenda'.

    n_ciclos: 2x10^6 (padrão) devolve o valor tabelado direto; outro valor
    passa por `curva_SN`. 'Em nenhum caso deve-se considerar resistência à
    fadiga maior que a da barra reta' (23.5.5, PDF p. 222; nota e,
    PDF p. 221): para os casos de armadura passiva com barra reta
    correspondente (todos, exceto o próprio 'barra_reta'), o resultado é
    limitado por `curva_SN` do valor da barra reta no mesmo phi. Célula
    '-' da Tabela 23.2 (combinação caso/phi que a norma não define, ex.
    'estribo_dmin_5phi' com phi = 20 mm) levanta FaixaNormativaError.
    """
    valor_min, tipo, barra_reta_min = _lookup_23_2(caso, phi_mm)
    n = float(n_ciclos)
    if n <= 0.0:
        raise ValueError("n_ciclos deve ser positivo.")
    valor = curva_SN(valor_min, tipo, n)
    if barra_reta_min is not None:
        teto = curva_SN(barra_reta_min, TABELA_23_2_TIPO_PASSIVA["barra_reta"], n)
        valor = min(valor, teto)
    return valor


# ---------------------------------------------------------------------------
# 23.5.5 -- relevo de nervura (PDF p. 223) e verificação da fadiga da armadura
# ---------------------------------------------------------------------------
def fator_relevo(r_h: float) -> float:
    """Fator de redução por relevo de nervura fora da condição-padrão da
    Tabela 23.2 (23.5.5, PDF p. 223).

    Os valores da Tabela 23.2 valem para barras nervuradas de alta
    aderência cujas saliências transversais e longitudinais não se
    cruzam e satisfazem r/h < 0,5 (r = raio da curva de concordância da
    saliência com o corpo da barra; h = altura da saliência). Na falta de
    dados experimentais que comprovem que uma barra fora dessa
    configuração ainda satisfaz a Tabela 23.2, aplica-se redução de 30%
    na flutuação de tensão-limite: devolve 1,0 se r/h < 0,5 (usa a
    Tabela 23.2 direto), e 0,70 caso contrário.
    """
    return 1.0 if float(r_h) < 0.5 else 0.70


@dataclass(frozen=True)
class ResultadoFadigaArmadura:
    """Verificação da fadiga da armadura, passiva ou ativa (23.5.5, PDF p. 220)."""
    delta_sigma_s_mpa: float
    gama_f: float
    delta_sigma_sd_mpa: float
    delta_fsd_fad_mpa: float
    caso: str
    phi_mm: float | None
    n_ciclos: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_fadiga_armadura(delta_sigma_s_mpa: float, caso: str,
                              phi_mm: float | None = None,
                              n_ciclos: float = N_REFERENCIA_CICLOS,
                              gama_f: float = 1.0,
                              r_h: float | None = None) -> ResultadoFadigaArmadura:
    """Verifica gama_f x Delta_sigma_Ss <= Delta_fsd,fad (23.5.5, PDF p. 220).

    delta_sigma_s_mpa: máxima variação de tensão calculada na armadura
    (Delta_sigma_S,s), sob a combinação frequente de ações (23.5.2) e o
    modelo linear elástico do Estádio II (23.5.3) -- vem de fora deste
    pacote (P9: `els_fissuracao_nbr6118.tensoes_servico`, com a diferença
    entre a tensão na barra sob a carga máxima e sob a carga mínima do
    ciclo); esta função não recalcula tensão de seção, só compara com o
    limite normativo. caso, phi_mm, n_ciclos: repassados a
    `delta_fsd_fad` (Tabelas 23.2 e 23.3). gama_f: 1,0 por padrão
    (23.5.3, PDF p. 218). r_h: r/h da saliência da barra (23.5.5,
    PDF p. 223); None (padrão) assume a condição-padrão atendida
    (r/h < 0,5, sem redução) -- informe para aplicar `fator_relevo`.
    """
    delta_sigma_s = float(delta_sigma_s_mpa)
    limite = delta_fsd_fad(caso, phi_mm, n_ciclos)
    reducao = 1.0 if r_h is None else fator_relevo(r_h)
    limite_efetivo = limite * reducao
    delta_sigma_sd = float(gama_f) * delta_sigma_s
    resultado_seg = seg.verificar_seguranca(
        Rd=limite_efetivo, Sd=delta_sigma_sd, rotulo="fadiga da armadura",
        item="23.5.5",
    )
    memoria = (
        f"23.5.5: caso = {caso}, phi = {phi_mm if phi_mm is not None else '-'} mm, "
        f"N = {float(n_ciclos):g} ciclos.",
        f"Delta_fsd,fad = {limite:g} MPa"
        + (
            f"; fator de relevo (r/h) = {reducao:g} -> "
            f"Delta_fsd,fad efetivo = {limite_efetivo:g} MPa."
            if r_h is not None else "."
        ),
        f"gama_f x Delta_sigma_Ss = {float(gama_f):g} x {delta_sigma_s:g} = "
        f"{delta_sigma_sd:g} MPa.",
        f"gama_f x Delta_sigma_Ss <= Delta_fsd,fad: {delta_sigma_sd:g} <= "
        f"{limite_efetivo:g} -> {'ok' if resultado_seg.ok else 'não ok'}.",
    )
    return ResultadoFadigaArmadura(
        delta_sigma_s, float(gama_f), delta_sigma_sd, limite_efetivo, caso,
        phi_mm, float(n_ciclos), resultado_seg.ok, resultado_seg.governante,
        memoria,
    )


# ---------------------------------------------------------------------------
# 23.6 -- Deformação progressiva sob ciclos de carga (PDF p. 223)
# ---------------------------------------------------------------------------
def deformacao_progressiva(a1: float, n: float) -> float:
    """Estimativa da deformação (ex.: flecha) no n-ésimo ciclo de carga
    máxima, a_n = a1 x [1,5 - 0,5 x exp(-0,05 x n^0,25)] (23.6, PDF p. 223).

    a1: deformação no primeiro ciclo devido à carga máxima, na unidade que
    se quiser para o resultado (ex.: cm de flecha). n: número de ciclos,
    n >= 1. Soma-se ao efeito de fluência (não o substitui, 23.6), na
    falta de dados experimentais conclusivos. Em n = 1, o fator vale
    1,5 - 0,5 x exp(-0,05) = 1,0244; quando n tende a infinito, o fator
    tende assintoticamente a 1,5.
    """
    a_1 = float(a1)
    num = float(n)
    if num < 1.0:
        raise ValueError("n (número de ciclos) deve ser >= 1.")
    fator = 1.5 - 0.5 * math.exp(-0.05 * num ** 0.25)
    return a_1 * fator
