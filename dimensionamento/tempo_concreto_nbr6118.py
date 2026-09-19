"""Fluência e retração do concreto — Anexo A da NBR 6118:2026 (A.2.2 a A.2.4).

Motor do procedimento “com precisão” do Anexo A, que serve à flecha diferida,
ao pilar esbelto e às perdas de protensão. O procedimento simplificado
(Tabela 8.1, 8.2.11) está no núcleo: ``nucleo_nbr6118.phi_eps_cs_NBR``.

Norma: ABNT NBR 6118:2026. As páginas citadas são as do PDF (a página
impressa é 18 a menos):
    - A.2.2.3 Valor da fluência ............................ PDF p. 234-235
    - A.2.3.2 Valor da retração e Tabela A.1 ............... PDF p. 236-238
    - A.2.4.1 Idade fictícia e Tabela A.2 .................. PDF p. 239
    - A.2.4.2 Espessura fictícia ........................... PDF p. 240

Unidades e cuidados:
    - fck em MPa; áreas em cm²; comprimentos em cm; idades em dias;
      temperaturas em °C; umidade relativa U em %; deformações em ‰.
    - **A espessura fictícia ponderada h = γ·hfic entra em centímetros em
      φ2c e ε2s e em metros em βf e βs.** Todas as funções daqui recebem
      ``h_pond_cm`` (em cm) e fazem a conversão para metro por dentro.
    - **t e t0 são idades fictícias** (A.2.4.1), com α da Tabela A.2: o α da
      fluência depende do cimento e o da retração vale 1 para todos, de modo
      que a mesma idade real dá idades fictícias diferentes nos dois
      fenômenos. Os parâmetros se chamam ``t_ficticia_dias`` e
      ``t0_ficticia_dias``; não passe neles a idade real (a Tabela 8.1 é que
      usa a idade real, ``to_dias``).
    - ``math.inf`` é aceito como t (t → ∞): βf, βs e βd tendem a 1.
    - Fora da faixa de validade as funções levantam ``FaixaNormativaError``
      (do núcleo), nunca devolvem número.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError


# ---------------------------------------------------------------------------
# Tabela A.1 — valores numéricos usuais para a fluência e a retração
# (A.2.3.2, PDF p. 237)
# ---------------------------------------------------------------------------
# Colunas de abatimento (ABNT NBR 16889), em cm: 0–4, 5–9 e 10–15.
FAIXAS_ABATIMENTO_CM = ((0.0, 4.0), (5.0, 9.0), (10.0, 15.0))
# Nota c: para U <= 90 %, 25 % menores no abatimento 0–4 cm e 25 % maiores
# no abatimento 10–15 cm, em relação à coluna 5–9 cm.
FATOR_ABATIMENTO_NOTA_C = (0.75, 1.0, 1.25)

# Por ambiente: U (%), φ1c e 10⁴·ε1s nas três faixas de abatimento e γ.
TABELA_A_1 = {
    "agua": {
        "descricao": "Na água",
        "U_pct": None,
        "phi1c": (0.6, 0.8, 1.0),
        "eps1s_1e4": (1.0, 1.0, 1.0),
        "gama": 30.0,
    },
    "muito_umido": {
        "descricao": "Em ambiente muito úmido imediatamente acima da água",
        "U_pct": 90.0,
        "phi1c": (1.0, 1.3, 1.6),
        "eps1s_1e4": (-1.9, -2.5, -3.1),
        "gama": 5.0,
    },
    "ar_livre": {
        "descricao": "Ao ar livre, em geral",
        "U_pct": 70.0,
        "phi1c": (1.5, 2.0, 2.5),
        "eps1s_1e4": (-3.8, -5.0, -6.2),
        "gama": 1.5,
    },
    "seco": {
        "descricao": "Em ambiente seco",
        "U_pct": 40.0,
        "phi1c": (2.3, 3.0, 3.8),
        "eps1s_1e4": (-4.7, -6.3, -7.9),
        "gama": 1.0,
    },
}

_AMBIENTE_ALIASES = {
    "agua": "agua", "naagua": "agua",
    "muitoumido": "muito_umido",
    "emambientemuitoumido": "muito_umido",
    "emambientemuitoumidoimediatamenteacimadaagua": "muito_umido",
    "arlivre": "ar_livre", "aoarlivre": "ar_livre", "aoarlivreemgeral": "ar_livre",
    "seco": "seco", "emambienteseco": "seco", "ambienteseco": "seco",
}

# Limite de U das notas a, c e d; faixa de U da nota b.
U_MAX_NOTAS_PCT = 90.0
U_MIN_NOTA_B_PCT = 40.0

# ---------------------------------------------------------------------------
# Tabela A.2 — α em função da velocidade de endurecimento do cimento
# (A.2.4.1, PDF p. 239)
# ---------------------------------------------------------------------------
TABELA_A_2_ALFA = {
    "lento": {"fluencia": 1.0, "retracao": 1.0},    # CP III e CP IV
    "normal": {"fluencia": 2.0, "retracao": 1.0},   # CP I e CP II
    "rapido": {"fluencia": 3.0, "retracao": 1.0},   # CP V-ARI
}

_CIMENTO_VELOCIDADE = {
    "lento": "lento", "normal": "normal", "rapido": "rapido",
    "cpi": "normal", "cpis": "normal",
    "cpii": "normal", "cpiie": "normal", "cpiif": "normal", "cpiiz": "normal",
    "cpiii": "lento", "cpiv": "lento",
    "cpv": "rapido", "cpvari": "rapido",
}
# Cimento representativo de cada velocidade para o s de 12.3.3 (os grupos
# de s coincidem com os da Tabela A.2: CP III/IV, CP I/II e CP V-ARI).
_CIMENTO_S_12_3_3 = {"lento": "CPIII", "normal": "CPII", "rapido": "CPV-ARI"}

_FENOMENO = {"fluencia": "fluencia", "retracao": "retracao"}

# ---------------------------------------------------------------------------
# Constantes de A.2.2.3 e A.2.3.2
# ---------------------------------------------------------------------------
PHI_D_INF = 0.4          # A.2.2.3 — valor final da deformação lenta reversível
H_POND_MIN_M = 0.05      # A.2.2.3 e A.2.3.2 — h fora de [0,05; 1,6] m trava
H_POND_MAX_M = 1.6
T_MIN_DIAS = 3.0         # A.2.2.3 e A.2.3.2 — βf e βs valem para t >= 3 dias


# ---------------------------------------------------------------------------
# Auxiliares de entrada
# ---------------------------------------------------------------------------
def _n(x: float, fmt: str = ".4g") -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return format(float(x), fmt).replace(".", ",")


def _ambiente(ambiente: str) -> str:
    chave = _AMBIENTE_ALIASES.get(nbr._chave(ambiente))
    if chave is None:
        raise ValueError(
            f"Ambiente desconhecido: {ambiente!r}. Use 'agua', 'muito_umido', "
            "'ar_livre' ou 'seco' (Tabela A.1)."
        )
    return chave


def velocidade_cimento(cimento: str) -> str:
    """Velocidade de endurecimento do cimento pela Tabela A.2 (A.2.4.1, PDF p. 239).

    Devolve 'lento' (CP III e CP IV), 'normal' (CP I, CP I-S, CP II-E, CP II-F
    e CP II-Z) ou 'rapido' (CP V-ARI). Aceita também os próprios rótulos
    'lento', 'normal' e 'rapido'. O sufixo RS (resistente a sulfatos) é
    ignorado: é propriedade de alguns dos tipos citados, não outro tipo.
    """
    chave = nbr._chave(cimento)
    if chave not in _CIMENTO_VELOCIDADE and chave.endswith("rs"):
        chave = chave[:-2]
    if chave not in _CIMENTO_VELOCIDADE:
        raise ValueError(
            f"Cimento desconhecido: {cimento!r}. Use CP I, CP II, CP III, CP IV "
            "ou CP V-ARI (Tabela A.2)."
        )
    return _CIMENTO_VELOCIDADE[chave]


def _faixa_abatimento(abatimento_cm: float) -> int:
    """Índice da coluna de abatimento da Tabela A.1 (0: 0–4; 1: 5–9; 2: 10–15 cm).

    A tabela dá as faixas em centímetros inteiros. Um abatimento entre 4 e
    5 cm ou entre 9 e 10 cm, que a tabela não nomeia, vai para a faixa de
    baixo (a faixa “0–4” é lida como “abaixo de 5 cm”). Abaixo de 0 ou acima
    de 15 cm a norma não define os valores: levanta FaixaNormativaError.
    """
    a = float(abatimento_cm)
    if not (0.0 <= a <= 15.0):
        raise FaixaNormativaError(
            f"Abatimento de {a:g} cm fora da Tabela A.1, que só define "
            "abatimentos de 0 cm a 15 cm (ABNT NBR 16889)."
        )
    if a < 5.0:
        return 0
    if a < 10.0:
        return 1
    return 2


def _validar_U_notas(U_pct: float, minimo: float = 0.0) -> float:
    U = float(U_pct)
    if not (minimo <= U <= U_MAX_NOTAS_PCT):
        raise FaixaNormativaError(
            f"U = {U:g} % fora da faixa da expressão da Tabela A.1 "
            f"({minimo:g} % a {U_MAX_NOTAS_PCT:g} %). Para peça na água, use "
            "ambiente='agua'."
        )
    return U


# ---------------------------------------------------------------------------
# Tabela A.1 — consulta por ambiente e expressões contínuas (notas a a d)
# ---------------------------------------------------------------------------
def phi1c_tabela(ambiente: str, abatimento_cm: float = 7.0) -> float:
    """φ1c da Tabela A.1 pela linha do ambiente (A.2.3.2, PDF p. 237).

    ambiente: 'agua', 'muito_umido' (U = 90 %), 'ar_livre' (U = 70 %) ou
    'seco' (U = 40 %). Consulta direta, sem interpolação.
    """
    return TABELA_A_1[_ambiente(ambiente)]["phi1c"][_faixa_abatimento(abatimento_cm)]


def eps1s_tabela_pmil(ambiente: str, abatimento_cm: float = 7.0) -> float:
    """ε1s da Tabela A.1 pela linha do ambiente, em ‰ (A.2.3.2, PDF p. 237).

    A tabela dá 10⁴·ε1s; o valor em ‰ é 10⁴·ε1s / 10 (−5,0 → −0,50 ‰).
    Positivo na água (inchamento), negativo nos demais ambientes.
    """
    v = TABELA_A_1[_ambiente(ambiente)]["eps1s_1e4"][_faixa_abatimento(abatimento_cm)]
    return v / 10.0


def gama_tabela(ambiente: str) -> float:
    """γ da Tabela A.1 pela linha do ambiente (A.2.3.2, PDF p. 237).

    Na água 30,0; muito úmido 5,0; ao ar livre 1,5; seco 1,0.
    """
    return TABELA_A_1[_ambiente(ambiente)]["gama"]


def phi1c(U_pct: float, abatimento_cm: float = 7.0) -> float:
    """φ1c contínuo em U — Tabela A.1, notas a e c (A.2.3.2, PDF p. 237).

    Nota a: φ1c = 4,45 − 0,035·U, para abatimento de 5 cm a 9 cm e U <= 90 %.
    Nota c: no abatimento de 0 cm a 4 cm o valor é 25 % menor (×0,75) e no de
    10 cm a 15 cm é 25 % maior (×1,25).

    U em %; faixa 0 % <= U <= 90 % (a nota a só fixa o teto). Para peça na
    água, use ``phi1c_tabela('agua', ...)``.
    """
    U = _validar_U_notas(U_pct)
    return FATOR_ABATIMENTO_NOTA_C[_faixa_abatimento(abatimento_cm)] * (4.45 - 0.035 * U)


def eps1s_1e4(U_pct: float, abatimento_cm: float = 7.0) -> float:
    """10⁴·ε1s contínuo em U — Tabela A.1, notas b e c (A.2.3.2, PDF p. 237).

    Nota b: 10⁴·ε1s = −8,09 + (U/15) − (U²/2 284) − (U³/133 765)
    + (U⁴/7 608 150), para abatimento de 5 cm a 9 cm e 40 % <= U <= 90 %.
    Nota c: ×0,75 no abatimento de 0 cm a 4 cm e ×1,25 no de 10 cm a 15 cm.
    """
    U = _validar_U_notas(U_pct, U_MIN_NOTA_B_PCT)
    base = -8.09 + U / 15.0 - U ** 2 / 2284.0 - U ** 3 / 133765.0 + U ** 4 / 7608150.0
    return FATOR_ABATIMENTO_NOTA_C[_faixa_abatimento(abatimento_cm)] * base


def eps1s_pmil(U_pct: float, abatimento_cm: float = 7.0) -> float:
    """ε1s contínuo em U, em ‰ — Tabela A.1, notas b e c (A.2.3.2, PDF p. 237).

    ε1s [‰] = 10⁴·ε1s / 10, com 10⁴·ε1s de ``eps1s_1e4``. Faixa
    40 % <= U <= 90 %.
    """
    return eps1s_1e4(U_pct, abatimento_cm) / 10.0


def gama_umidade(U_pct: float) -> float:
    """γ contínuo em U — Tabela A.1, nota d (A.2.3.2, PDF p. 237).

    γ = 1 + exp(−7,8 + 0,1·U), para U <= 90 % (U em %).

    Não coincide com os valores discretos da tabela: em U = 90 % dá 4,32
    contra 5,0 da linha “muito úmido”; em U = 40 % dá 1,02 contra 1,0. Para
    usar o valor da linha, chame ``gama_tabela``.
    """
    U = _validar_U_notas(U_pct)
    return 1.0 + math.exp(-7.8 + 0.1 * U)


# ---------------------------------------------------------------------------
# A.2.4 — idade fictícia e espessura fictícia
# ---------------------------------------------------------------------------
def alfa_cimento(cimento: str = "CPII", fenomeno: str = "fluencia") -> float:
    """α da Tabela A.2 (A.2.4.1, PDF p. 239).

    Fluência: 1 (CP III e CP IV), 2 (CP I e CP II), 3 (CP V-ARI).
    Retração: 1 para todos os cimentos.
    fenomeno: 'fluencia' ou 'retracao'.
    """
    fen = _FENOMENO.get(nbr._chave(fenomeno))
    if fen is None:
        raise ValueError(
            f"Fenômeno desconhecido: {fenomeno!r}. Use 'fluencia' ou 'retracao'."
        )
    return TABELA_A_2_ALFA[velocidade_cimento(cimento)][fen]


def idade_ficticia_dias(historico: Iterable[tuple[float, float]],
                        cimento: str = "CPII",
                        fenomeno: str = "fluencia") -> float:
    """Idade fictícia do concreto, em dias (A.2.4.1, PDF p. 239).

        t = α · Σᵢ (Tᵢ + 10)/30 · Δtef,i

    historico: sequência de pares (Tᵢ em °C, Δtef,i em dias), cada um o
    período em que a temperatura média diária do ambiente pode ser admitida
    constante. α vem da Tabela A.2 (``alfa_cimento``) e depende do fenômeno:
    a mesma idade real dá uma idade fictícia para a fluência e outra para a
    retração. A 20 °C a expressão se reduz a t = α·tef.

    Faixa: Tᵢ > −10 °C (abaixo disso o termo seria nulo ou negativo) e
    Δtef,i >= 0. A expressão não se aplica à cura a vapor (NOTA de A.2.4.1).
    """
    alfa = alfa_cimento(cimento, fenomeno)
    soma = 0.0
    n = 0
    for T_C, dt_dias in historico:
        T = float(T_C)
        dt = float(dt_dias)
        if T <= -10.0:
            raise FaixaNormativaError(
                f"Temperatura média de {T:g} °C: a expressão de A.2.4.1 exige "
                "T > −10 °C (com T <= −10 °C o termo (T + 10)/30 não é positivo)."
            )
        if dt < 0.0:
            raise ValueError(f"Período Δtef negativo ({dt:g} dias).")
        soma += (T + 10.0) / 30.0 * dt
        n += 1
    if n == 0:
        raise ValueError("O histórico de temperaturas está vazio.")
    return alfa * soma


def espessura_ficticia_cm(Ac_cm2: float, uar_cm: float) -> float:
    """Espessura fictícia hfic = 2·Ac/uar, em cm (A.2.4.2, PDF p. 240).

    Ac: área da seção transversal (cm²); uar: parte do perímetro externo
    da seção em contato com o ar (cm). Sem a ponderação γ.
    """
    Ac = float(Ac_cm2)
    u = float(uar_cm)
    if Ac <= 0.0 or u <= 0.0:
        raise ValueError("Ac e uar devem ser positivos.")
    return 2.0 * Ac / u


def _gama(U_pct: float | None, ambiente: str | None) -> float:
    if (U_pct is None) == (ambiente is None):
        raise ValueError("Informe U_pct ou ambiente (um dos dois, não os dois).")
    return gama_umidade(U_pct) if ambiente is None else gama_tabela(ambiente)


def espessura_ficticia_ponderada_cm(Ac_cm2: float, uar_cm: float,
                                    U_pct: float | None = None,
                                    ambiente: str | None = None) -> float:
    """Espessura fictícia ponderada h = γ·hfic, em cm (A.2.4.2 e Tabela A.1).

    hfic = 2·Ac/uar (A.2.4.2, PDF p. 240); γ pela nota d da Tabela A.1
    (γ = 1 + exp(−7,8 + 0,1·U), com ``U_pct``) ou pela linha do ambiente
    (com ``ambiente``; PDF p. 237). Informe um dos dois.
    """
    return _gama(U_pct, ambiente) * espessura_ficticia_cm(Ac_cm2, uar_cm)


def _validar_h_cm(h_pond_cm: float) -> float:
    h = float(h_pond_cm)
    if h <= 0.0:
        raise FaixaNormativaError("A espessura fictícia ponderada h deve ser positiva.")
    return h


def _validar_t(t_dias: float, nome: str = "t") -> float:
    t = float(t_dias)
    if not (t >= T_MIN_DIAS):
        raise FaixaNormativaError(
            f"{nome} = {t:g} dias: as curvas βf(t) e βs(t) do Anexo A valem "
            f"para idade fictícia t >= {T_MIN_DIAS:g} dias."
        )
    return t


def _h_metro_travado(h_pond_cm: float) -> float:
    """h em metros, travado em [0,05; 1,6] m (A.2.2.3 e A.2.3.2)."""
    h_m = _validar_h_cm(h_pond_cm) / 100.0
    return min(max(h_m, H_POND_MIN_M), H_POND_MAX_M)


# ---------------------------------------------------------------------------
# A.2.2.3 — valor da fluência
# ---------------------------------------------------------------------------
def fc_t0_sobre_fc_tinf(t0_ficticia_dias: float, cimento: str = "CPII",
                        fck_mpa: float | None = None) -> float:
    """fc(t0)/fc(t∞), crescimento da resistência com a idade (A.2.2.3 e 12.3.3).

    A.2.2.3 remete a 12.3, que dá fc(t)/fc(28) = β1(t) = exp{s·[1 − (28/t)^½]}.
    A resistência final fc(t∞) é o limite de β1 para t → ∞, exp(s), logo

        fc(t0)/fc(t∞) = β1(t0)/exp(s) = exp[−s·(28/t0)^½]

    com s de 12.3.3 (0,38 para CP III e CP IV, 0,25 para CP I e CP II, 0,20
    para CP V-ARI e para todo concreto C60 ou superior; ``nucleo.s_cimento``).
    Leitura adotada porque a hipótese c de A.2.2.2 fala da “resistência
    final”, não da resistência aos 28 dias; ela reproduz a Tabela 8.1 no
    bloco C50–C90 (ver os testes do P6). t0 é a idade fictícia em dias.
    """
    t0 = float(t0_ficticia_dias)
    if t0 <= 0.0:
        raise FaixaNormativaError("A idade t0 deve ser positiva (dias).")
    cim = _CIMENTO_S_12_3_3[velocidade_cimento(cimento)]
    s = nbr.s_cimento(cim, fck_mpa)
    return nbr.beta1(t0, cim, fck_mpa) / math.exp(s)


def phi_a(fck_mpa: float, t0_ficticia_dias: float, cimento: str = "CPII",
          razao_fc: float | None = None) -> float:
    """Coeficiente de fluência rápida φa (A.2.2.3, PDF p. 234).

        φa = 0,8·[1 − fc(t0)/fc(t∞)]   para concretos C20 a C45
        φa = 1,4·[1 − fc(t0)/fc(t∞)]   para concretos C50 a C90

    fc(t0)/fc(t∞) vem de ``fc_t0_sobre_fc_tinf`` (12.3), ou do argumento
    ``razao_fc`` (0 < razao_fc <= 1) quando o engenheiro tem o dado da obra.
    fck entre 45 e 50 MPa, sem classe na norma, segue o bloco C50–C90, como
    na Tabela 8.1.
    """
    fck = nbr.validar_fck(fck_mpa)
    if razao_fc is None:
        r = fc_t0_sobre_fc_tinf(t0_ficticia_dias, cimento, fck)
    else:
        r = float(razao_fc)
        if not (0.0 < r <= 1.0):
            raise FaixaNormativaError(
                f"fc(t0)/fc(t∞) = {r:g} fora de (0; 1]."
            )
    coef = 0.8 if nbr._bloco_classe_tabela_8_1(fck) == "C20-C45" else 1.4
    return coef * (1.0 - r)


def phi2c(h_pond_cm: float) -> float:
    """φ2c = (42 + h)/(20 + h), h = γ·hfic em **centímetros** (A.2.2.3, PDF p. 235)."""
    h = _validar_h_cm(h_pond_cm)
    return (42.0 + h) / (20.0 + h)


def phi_f_inf(fck_mpa: float, phi_1c: float, phi_2c: float) -> float:
    """Valor final da deformação lenta irreversível φf∞ (A.2.2.3, PDF p. 235).

        φf∞ = φ1c·φ2c          para concretos C20 a C45
        φf∞ = 0,45·φ1c·φ2c     para concretos C50 a C90
    """
    fck = nbr.validar_fck(fck_mpa)
    fator = 1.0 if nbr._bloco_classe_tabela_8_1(fck) == "C20-C45" else 0.45
    return fator * float(phi_1c) * float(phi_2c)


def beta_f(t_ficticia_dias: float, h_pond_cm: float) -> float:
    """βf(t), deformação lenta irreversível no tempo (A.2.2.3, PDF p. 235; Figura A.2).

        βf(t) = (t² + A·t + B)/(t² + C·t + D)
        A = 42h³ − 350h² + 588h + 113
        B = 768h³ − 3 060h² + 3 234h − 23
        C = −200h³ + 13h² + 1 090h + 183
        D = 7 579h³ − 31 916h² + 35 343h + 1 931

    h = γ·hfic em **metros**: a função recebe ``h_pond_cm`` e divide por 100.
    Fora de 0,05 m <= h <= 1,6 m adotam-se os extremos. t é a idade fictícia
    em dias, t >= 3; ``math.inf`` devolve 1.
    """
    t = _validar_t(t_ficticia_dias)
    h = _h_metro_travado(h_pond_cm)
    if math.isinf(t):
        return 1.0
    A = 42.0 * h ** 3 - 350.0 * h ** 2 + 588.0 * h + 113.0
    B = 768.0 * h ** 3 - 3060.0 * h ** 2 + 3234.0 * h - 23.0
    C = -200.0 * h ** 3 + 13.0 * h ** 2 + 1090.0 * h + 183.0
    D = 7579.0 * h ** 3 - 31916.0 * h ** 2 + 35343.0 * h + 1931.0
    return (t * t + A * t + B) / (t * t + C * t + D)


def beta_d(t_ficticia_dias: float, t0_ficticia_dias: float) -> float:
    """βd(t) = (t − t0 + 20)/(t − t0 + 70) (A.2.2.3, PDF p. 235).

    Deformação lenta reversível em função do tempo decorrido após o
    carregamento; exige t >= t0. t = ``math.inf`` devolve 1.
    """
    t = float(t_ficticia_dias)
    t0 = float(t0_ficticia_dias)
    if not (t >= t0):
        raise FaixaNormativaError(f"t = {t:g} dias anterior a t0 = {t0:g} dias.")
    if math.isinf(t):
        return 1.0
    return (t - t0 + 20.0) / (t - t0 + 70.0)


@dataclass(frozen=True)
class ResultadoFluencia:
    """φ(t,t0) do Anexo A com as parcelas e a memória de cálculo."""

    phi: float
    phi_a: float
    phi_f_inf: float
    phi_d_inf: float
    beta_f_t: float
    beta_f_t0: float
    beta_d: float
    phi_1c: float
    phi_2c: float
    gama: float
    h_pond_cm: float
    t_ficticia_dias: float
    t0_ficticia_dias: float
    memoria: tuple[str, ...]


def coeficiente_fluencia(t_ficticia_dias: float, t0_ficticia_dias: float,
                         fck_mpa: float, h_fic_cm: float,
                         U_pct: float | None = None,
                         ambiente: str | None = None,
                         abatimento_cm: float = 7.0,
                         cimento: str = "CPII",
                         razao_fc: float | None = None) -> ResultadoFluencia:
    """Coeficiente de fluência φ(t,t0), procedimento completo (A.2.2.3, PDF p. 234-235).

        φ(t,t0) = φa + φf∞·[βf(t) − βf(t0)] + φd∞·βd

    Válido também para a tração. Entradas:
        t_ficticia_dias, t0_ficticia_dias: idades fictícias (A.2.4.1, com o α
            de fluência da Tabela A.2; use ``idade_ficticia_dias``), t0 >= 3;
            t pode ser ``math.inf``.
        h_fic_cm: hfic = 2·Ac/uar **sem** ponderação (A.2.4.2); a função
            multiplica por γ.
        U_pct ou ambiente (um dos dois): com U, φ1c e γ saem das notas a, c e
            d da Tabela A.1 (U <= 90 %); com ambiente, da linha da tabela
            ('agua', 'muito_umido', 'ar_livre' ou 'seco').
        abatimento_cm: consistência no lançamento (0 a 15 cm; padrão 7 cm,
            faixa de 5 cm a 9 cm).
        cimento: para fc(t0)/fc(t∞) (12.3.3); ``razao_fc`` substitui a razão.
    """
    t0 = _validar_t(t0_ficticia_dias, "t0")
    t = float(t_ficticia_dias)
    if not (t >= t0):
        raise FaixaNormativaError(f"t = {t:g} dias anterior a t0 = {t0:g} dias.")
    gama = _gama(U_pct, ambiente)
    if ambiente is None:
        p1c = phi1c(U_pct, abatimento_cm)
        orig = f"U = {float(U_pct):g} %, notas a, c e d da Tabela A.1"
    else:
        p1c = phi1c_tabela(ambiente, abatimento_cm)
        orig = f"ambiente “{TABELA_A_1[_ambiente(ambiente)]['descricao']}”, Tabela A.1"
    hfic = _validar_h_cm(h_fic_cm)
    h = gama * hfic
    p2c = phi2c(h)
    pf = phi_f_inf(fck_mpa, p1c, p2c)
    pa = phi_a(fck_mpa, t0, cimento, razao_fc)
    bft = beta_f(t, h)
    bft0 = beta_f(t0, h)
    bd = beta_d(t, t0)
    phi_val = pa + pf * (bft - bft0) + PHI_D_INF * bd
    t_txt = "∞" if math.isinf(t) else f"{t:g}"
    memoria = (
        f"Anexo A (A.2.2.3) — fluência com {orig}, abatimento {_n(float(abatimento_cm), 'g')} cm.",
        f"γ = {_n(gama)}; h = γ·hfic = {_n(gama)}·{_n(hfic)} = {_n(h)} cm "
        f"({_n(h / 100.0)} m em βf, travado em [0,05; 1,6] m).",
        f"φ1c = {_n(p1c)}; φ2c = (42 + h)/(20 + h) = {_n(p2c)}.",
        f"φf∞ = {'' if pf == p1c * p2c else '0,45·'}φ1c·φ2c = {_n(pf)} "
        f"(fck = {_n(float(fck_mpa), 'g')} MPa).",
        f"φa = {_n(pa)} (t0 = {_n(t0, 'g')} dias fictícios).",
        f"βf(t = {t_txt}) = {_n(bft)}; βf(t0 = {_n(t0, 'g')}) = {_n(bft0)}; "
        f"βd = (t − t0 + 20)/(t − t0 + 70) = {_n(bd)}.",
        f"φ(t,t0) = φa + φf∞·[βf(t) − βf(t0)] + φd∞·βd = {_n(pa)} + {_n(pf)}·"
        f"({_n(bft)} − {_n(bft0)}) + {_n(PHI_D_INF, 'g')}·{_n(bd)} = {_n(phi_val)}.",
    )
    return ResultadoFluencia(
        phi=phi_val, phi_a=pa, phi_f_inf=pf, phi_d_inf=PHI_D_INF,
        beta_f_t=bft, beta_f_t0=bft0, beta_d=bd, phi_1c=p1c, phi_2c=p2c,
        gama=gama, h_pond_cm=h, t_ficticia_dias=t, t0_ficticia_dias=t0,
        memoria=memoria,
    )


def phi(t_ficticia_dias: float, t0_ficticia_dias: float, fck_mpa: float,
        h_fic_cm: float, U_pct: float | None = None, ambiente: str | None = None,
        abatimento_cm: float = 7.0, cimento: str = "CPII",
        razao_fc: float | None = None) -> float:
    """φ(t,t0) do Anexo A (A.2.2.3, PDF p. 234-235); atalho de ``coeficiente_fluencia``."""
    return coeficiente_fluencia(t_ficticia_dias, t0_ficticia_dias, fck_mpa, h_fic_cm,
                                U_pct, ambiente, abatimento_cm, cimento, razao_fc).phi


# ---------------------------------------------------------------------------
# A.2.3.2 — valor da retração
# ---------------------------------------------------------------------------
def eps2s(h_pond_cm: float) -> float:
    """ε2s = (33 + 2h)/(20,8 + 3h), h = γ·hfic em **centímetros** (A.2.3.2, PDF p. 237)."""
    h = _validar_h_cm(h_pond_cm)
    return (33.0 + 2.0 * h) / (20.8 + 3.0 * h)


def eps_cs_inf_pmil(eps_1s_pmil: float, eps_2s: float) -> float:
    """Valor final da retração εcs∞ = ε1s·ε2s, em ‰ (A.2.3.2, PDF p. 236)."""
    return float(eps_1s_pmil) * float(eps_2s)


def beta_s(t_ficticia_dias: float, h_pond_cm: float) -> float:
    """βs(t), evolução da retração no tempo (A.2.3.2, PDF p. 238; Figura A.3).

        βs(t) = [(t/100)³ + A·(t/100)² + B·(t/100)]
                / [(t/100)³ + C·(t/100)² + D·(t/100) + E]
        A = 40
        B = 116h³ − 282h² + 220h − 4,8
        C = 2,5h³ − 8,8h + 40,7
        D = −75h³ + 585h² + 496h − 6,8
        E = −169h⁴ + 88h³ + 584h² − 39h + 0,8

    h = γ·hfic em **metros**: a função recebe ``h_pond_cm`` e divide por 100.
    Fora de 0,05 m <= h <= 1,6 m adotam-se os extremos. t é a idade fictícia
    em dias, t >= 3; ``math.inf`` devolve 1.
    """
    t = _validar_t(t_ficticia_dias)
    h = _h_metro_travado(h_pond_cm)
    if math.isinf(t):
        return 1.0
    x = t / 100.0
    A = 40.0
    B = 116.0 * h ** 3 - 282.0 * h ** 2 + 220.0 * h - 4.8
    C = 2.5 * h ** 3 - 8.8 * h + 40.7
    D = -75.0 * h ** 3 + 585.0 * h ** 2 + 496.0 * h - 6.8
    E = -169.0 * h ** 4 + 88.0 * h ** 3 + 584.0 * h ** 2 - 39.0 * h + 0.8
    return (x ** 3 + A * x ** 2 + B * x) / (x ** 3 + C * x ** 2 + D * x + E)


@dataclass(frozen=True)
class ResultadoRetracao:
    """εcs(t,t0) do Anexo A com as parcelas e a memória de cálculo."""

    eps_cs_pmil: float
    eps_cs_inf_pmil: float
    eps_1s_pmil: float
    eps_2s: float
    beta_s_t: float
    beta_s_t0: float
    gama: float
    h_pond_cm: float
    t_ficticia_dias: float
    t0_ficticia_dias: float
    memoria: tuple[str, ...]


def retracao(t_ficticia_dias: float, t0_ficticia_dias: float, h_fic_cm: float,
             U_pct: float | None = None, ambiente: str | None = None,
             abatimento_cm: float = 7.0) -> ResultadoRetracao:
    """Retração εcs(t,t0) entre t0 e t, procedimento completo (A.2.3.2, PDF p. 236-238).

        εcs(t,t0) = εcs∞·[βs(t) − βs(t0)],   εcs∞ = ε1s·ε2s

    Entradas:
        t_ficticia_dias, t0_ficticia_dias: idades fictícias (A.2.4.1, com
            α = 1 da Tabela A.2 para a retração), t0 >= 3; t pode ser
            ``math.inf``. t0 é o instante em que a retração começa a ser
            considerada.
        h_fic_cm: hfic = 2·Ac/uar **sem** ponderação; a função multiplica por γ.
        U_pct (40 % <= U <= 90 %, notas b, c e d) ou ambiente (linha da
            Tabela A.1): um dos dois.
        abatimento_cm: 0 a 15 cm (padrão 7 cm).

    Resultado em ‰, negativo para encurtamento (positivo na água).
    """
    t0 = _validar_t(t0_ficticia_dias, "t0")
    t = float(t_ficticia_dias)
    if not (t >= t0):
        raise FaixaNormativaError(f"t = {t:g} dias anterior a t0 = {t0:g} dias.")
    gama = _gama(U_pct, ambiente)
    if ambiente is None:
        e1s = eps1s_pmil(U_pct, abatimento_cm)
        orig = f"U = {float(U_pct):g} %, notas b, c e d da Tabela A.1"
    else:
        e1s = eps1s_tabela_pmil(ambiente, abatimento_cm)
        orig = f"ambiente “{TABELA_A_1[_ambiente(ambiente)]['descricao']}”, Tabela A.1"
    hfic = _validar_h_cm(h_fic_cm)
    h = gama * hfic
    e2s = eps2s(h)
    einf = eps_cs_inf_pmil(e1s, e2s)
    bst = beta_s(t, h)
    bst0 = beta_s(t0, h)
    eps = einf * (bst - bst0)
    t_txt = "∞" if math.isinf(t) else f"{t:g}"
    memoria = (
        f"Anexo A (A.2.3.2) — retração com {orig}, abatimento {_n(float(abatimento_cm), 'g')} cm.",
        f"γ = {_n(gama)}; h = γ·hfic = {_n(gama)}·{_n(hfic)} = {_n(h)} cm "
        f"({_n(h / 100.0)} m em βs, travado em [0,05; 1,6] m).",
        f"ε1s = {_n(e1s)} ‰; ε2s = (33 + 2h)/(20,8 + 3h) = {_n(e2s)}.",
        f"εcs∞ = ε1s·ε2s = {_n(einf)} ‰.",
        f"βs(t = {t_txt}) = {_n(bst)}; βs(t0 = {_n(t0, 'g')}) = {_n(bst0)}.",
        f"εcs(t,t0) = εcs∞·[βs(t) − βs(t0)] = {_n(einf)}·({_n(bst)} − {_n(bst0)}) "
        f"= {_n(eps)} ‰.",
    )
    return ResultadoRetracao(
        eps_cs_pmil=eps, eps_cs_inf_pmil=einf, eps_1s_pmil=e1s, eps_2s=e2s,
        beta_s_t=bst, beta_s_t0=bst0, gama=gama, h_pond_cm=h,
        t_ficticia_dias=t, t0_ficticia_dias=t0, memoria=memoria,
    )


def eps_cs_pmil(t_ficticia_dias: float, t0_ficticia_dias: float, h_fic_cm: float,
                U_pct: float | None = None, ambiente: str | None = None,
                abatimento_cm: float = 7.0) -> float:
    """εcs(t,t0) do Anexo A em ‰ (A.2.3.2, PDF p. 236); atalho de ``retracao``."""
    return retracao(t_ficticia_dias, t0_ficticia_dias, h_fic_cm, U_pct, ambiente,
                    abatimento_cm).eps_cs_pmil
