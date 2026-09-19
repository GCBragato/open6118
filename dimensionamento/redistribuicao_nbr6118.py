"""Redistribuição de momentos e dutilidade — NBR 6118:2026, 14.6.4.3, 14.6.4.4,
14.7.3.2 e 14.7.4 (PDF p. 112-113 e p. 116).

Vigas e pórticos (14.6.4.3/14.6.4.4) e placas/lajes (14.7.3.2/14.7.4) usam,
para os limites de x/d com redistribuição e para a dispensa de verificação
explícita de rotação, as mesmas fórmulas. Este módulo implementa a fórmula
uma única vez (para vigas) e a laje chama a mesma função, citando os dois
itens da norma.

O limite de x/d **sem** redistribuição (δ = 1) já existe no núcleo como
``nucleo_nbr6118.xd_limite_dutilidade`` e é reaproveitado aqui, nunca
reimplementado.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError
validar_fck = nbr.validar_fck

__all__ = [
    "delta_minimo",
    "xd_limite_redistribuicao",
    "xd_limite_redistribuicao_laje",
    "rotacao_plastica_admissivel_mrad",
    "DispensaRotacaoPlastica",
    "dispensa_verificacao_rotacao",
    "VerificacaoRazaoMomentosBordaVao",
    "verificar_razao_momentos_borda_vao",
]


# ---------------------------------------------------------------------------
# 14.6.4.3 — Limites para redistribuição de momentos e condições de dutilidade
# (PDF p. 112)
# ---------------------------------------------------------------------------
def delta_minimo() -> float:
    """Limite inferior do coeficiente de redistribuição δ (14.6.4.3, PDF p. 112).

    δ ≥ 0,75, para qualquer caso (fck e classe de aço), onde
    δ = M_reduzido/M_elástico é a razão entre o momento fletor após a
    redistribuição e o momento obtido pela análise linear.
    """
    return 0.75


def xd_limite_redistribuicao(delta: float, fck_mpa: float) -> float:
    """Limite de x/d quando o momento M é reduzido para δ·M por redistribuição
    (14.6.4.3, PDF p. 112; a mesma fórmula vale para placas, 14.7.3.2, PDF p. 116).

    x/d <= (δ - 0,44)/1,25, para concretos com fck <= 50 MPa;
    x/d <= (δ - 0,56)/1,25, para concretos com 50 MPa < fck <= 90 MPa.

    δ é adimensional (M_reduzido/M_elástico) e deve respeitar δ >= 0,75
    (``delta_minimo``); δ > 1 não tem sentido físico (redistribuição reduz o
    momento, nunca aumenta). Fora de [0,75; 1,0] levanta ``FaixaNormativaError``.
    """
    fck = validar_fck(fck_mpa)
    d = float(delta)
    if not (delta_minimo() <= d <= 1.0):
        raise FaixaNormativaError(
            f"δ = {d:g} fora da faixa admitida pela NBR 6118:2026, 14.6.4.3 "
            f"({delta_minimo():g} <= δ <= 1,0)."
        )
    if fck <= 50.0:
        return (d - 0.44) / 1.25
    return (d - 0.56) / 1.25


def xd_limite_redistribuicao_laje(delta: float, fck_mpa: float) -> float:
    """Limite de x/d para redistribuição de momentos em placas/lajes (14.7.3.2,
    PDF p. 116), com o coeficiente δ conforme 14.6.4.3 (PDF p. 112).

    Mesma fórmula e mesmos limites de ``xd_limite_redistribuicao``; a norma
    apenas estende, em 14.7.3.2, o que já está definido em 14.6.4.3 para vigas
    também a placas. Reaproveita a mesma função, sem reimplementar a fórmula.
    """
    return xd_limite_redistribuicao(delta, fck_mpa)


# ---------------------------------------------------------------------------
# 14.6.4.4 — Análise não linear com verificação explícita da rotação plástica
# solicitante (Figura 14.7, PDF p. 112-113)
# ---------------------------------------------------------------------------
# Digitalização manual da Figura 14.7 (eixo x: x/d no ELU, de 0,00 a 0,45;
# eixo y: theta_pl admissível, em mrad, para a razão a/d = 3). Pontos lidos
# diretamente do gráfico impresso (SCRATCH\nbr_png\p113.png); a leitura tem
# tolerância declarada de aproximadamente +/-3 mrad (não há tabela numérica na
# norma, só o gráfico). Interpolação linear entre os pontos digitalizados, e
# entre as curvas C50/C90 quando 50 MPa < fck < 90 MPa (a própria norma manda
# interpolar linearmente entre as classes, ver texto abaixo da Figura 14.7).
CURVA_I_CA50_C20_C50_MRAD = (
    (0.02, 17.0), (0.10, 31.0), (0.15, 27.0), (0.20, 23.0), (0.25, 19.0),
    (0.30, 15.0), (0.35, 12.0), (0.40, 8.5), (0.45, 5.0),
)
CURVA_II_CA50_C90_MRAD = (
    (0.03, 17.0), (0.08, 29.0), (0.15, 24.0), (0.20, 20.0), (0.25, 16.0),
    (0.30, 12.5), (0.35, 9.5), (0.40, 6.5), (0.45, 3.5),
)
CURVA_III_CA60_C20_C50_MRAD = (
    (0.03, 12.0), (0.13, 21.0), (0.20, 16.0), (0.25, 13.5), (0.30, 11.0),
    (0.35, 9.0), (0.40, 7.0), (0.45, 5.0),
)
CURVA_IV_CA60_C90_MRAD = (
    (0.03, 12.0), (0.10, 19.0), (0.15, 16.5), (0.20, 14.0), (0.25, 11.5),
    (0.30, 9.5), (0.35, 7.5), (0.40, 5.5), (0.45, 3.5),
)

_XD_MAX_FIGURA_14_7 = 0.45


def _theta_curva_mrad(xd: float, curva: tuple[tuple[float, float], ...]) -> float:
    """Lê theta_pl (mrad) na curva digitalizada por interpolação linear.

    Abaixo do primeiro ponto lido, mantém (extrapolação constante) o valor do
    primeiro ponto; a norma não define a curva tão à esquerda e o objetivo é
    não superestimar a capacidade de rotação.
    """
    if not (0.0 <= xd <= _XD_MAX_FIGURA_14_7):
        raise FaixaNormativaError(
            f"x/d = {xd:g} fora do domínio da Figura 14.7 (0,00 a "
            f"{_XD_MAX_FIGURA_14_7:g}), NBR 6118:2026, 14.6.4.4."
        )
    if xd <= curva[0][0]:
        return curva[0][1]
    for (x0, y0), (x1, y1) in zip(curva, curva[1:]):
        if x0 <= xd <= x1:
            return y0 + (y1 - y0) * (xd - x0) / (x1 - x0)
    return curva[-1][1]  # inalcançável: última abscissa é _XD_MAX_FIGURA_14_7


_CURVAS_POR_ACO = {
    "CA-50": (CURVA_I_CA50_C20_C50_MRAD, CURVA_II_CA50_C90_MRAD),
    "CA-60": (CURVA_III_CA60_C20_C50_MRAD, CURVA_IV_CA60_C90_MRAD),
}


def rotacao_plastica_admissivel_mrad(xd: float, fck_mpa: float, aco: str,
                                      a_d: float) -> float:
    """Capacidade de rotação plástica admissível theta_pl (mrad), Figura 14.7
    (NBR 6118:2026, 14.6.4.4, PDF p. 112-113).

    Lida em uma das 4 curvas da Figura 14.7, em função de x/d no ELU (flexão
    simples) e da combinação fck × classe de aço:
      I:   fck 20 a 50 MPa, CA-50;   II:  fck = 90 MPa, CA-50;
      III: fck 20 a 50 MPa, CA-60;   IV:  fck = 90 MPa, CA-60.
    Para 50 MPa < fck < 90 MPa, interpola linearmente entre a curva C50 e a
    curva C90 da mesma classe de aço (texto sob a Figura 14.7: "Para classes
    de concreto entre C50 e C90, é válida a interpolação linear dos valores
    obtidos na Figura 14.7").

    O valor lido no gráfico corresponde à razão a/d = M_Sd/V_Sd/d = 3. Para
    outra razão a/d, multiplica-se pelo fator sqrt((a/d)/3) (texto de
    14.6.4.4, PDF p. 113), onde a_d é a razão a/d (adimensional) informada.

    Nota sobre a leitura da imagem (verificação registrada em 19/09/2026):
    a fonte do PDF imprime a barra do radical de forma que, numa leitura
    apressada, parece cobrir só "(a/d)", deixando "/3" fora da raiz. Um
    recorte ampliado de p. 112 (linha "multiplicar os valores extraídos da
    Figura 14.7 pelo fator...") mostra a barra do radical se estendendo até
    depois do "3", confirmando sqrt((a/d)/3), não sqrt(a/d)/3. Isso também é
    a única leitura fisicamente consistente com o parágrafo anterior ("o
    valor lido... corresponde à razão a/d = 3"): sqrt((a/d)/3) vale 1,0 em
    a/d = 3 (fator neutro, reproduz o valor lido no gráfico); sqrt(a/d)/3
    valeria 0,577 em a/d = 3, o que contradiria a própria norma.

    xd (x/d, adimensional) deve estar em [0,00; 0,45]; fck_mpa em [20; 90];
    aco em {"CA-50", "CA-60"}; a_d > 0. Fora disso levanta
    ``FaixaNormativaError``.
    """
    fck = validar_fck(fck_mpa)
    if aco not in _CURVAS_POR_ACO:
        raise FaixaNormativaError(
            f"Aço '{aco}' fora do escopo da Figura 14.7 (apenas CA-50 e CA-60)."
        )
    a_sobre_d = float(a_d)
    if a_sobre_d <= 0.0:
        raise FaixaNormativaError(f"a/d = {a_sobre_d:g} deve ser positivo (14.6.4.4).")

    curva_c50, curva_c90 = _CURVAS_POR_ACO[aco]
    theta_c50 = _theta_curva_mrad(xd, curva_c50)
    if fck <= 50.0:
        theta_base = theta_c50
    elif fck >= 90.0:
        theta_base = _theta_curva_mrad(xd, curva_c90)
    else:
        theta_c90 = _theta_curva_mrad(xd, curva_c90)
        theta_base = theta_c50 + (theta_c90 - theta_c50) * (fck - 50.0) / (90.0 - 50.0)

    fator_a_d = math.sqrt(a_sobre_d / 3.0)
    return theta_base * fator_a_d


# ---------------------------------------------------------------------------
# Dispensa da verificação explícita de rotação plástica
# (14.6.4.4, PDF p. 113, e 14.7.4, PDF p. 116, para lajes)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DispensaRotacaoPlastica:
    """Resultado da checagem de dispensa da verificação explícita de rotação
    plástica (14.6.4.4/14.7.4)."""
    xd: float
    fck_mpa: float
    xd_limite: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def dispensa_verificacao_rotacao(xd: float, fck_mpa: float) -> DispensaRotacaoPlastica:
    """Dispensa da verificação explícita da capacidade de rotação de rótulas
    plásticas (NBR 6118:2026, 14.6.4.4, PDF p. 113, e 14.7.4 para lajes
    analisadas pela teoria das charneiras plásticas, PDF p. 116).

    A verificação de 14.6.4.4 é dispensada, na análise plástica, desde que:
      x/d <= 0,25, se fck <= 50 MPa;
      x/d <= 0,15, se fck > 50 MPa.
    ``ok`` é True quando a dispensa se aplica (x/d dentro do limite); False
    quando x/d excede o limite e a verificação explícita da rotação plástica
    (``rotacao_plastica_admissivel_mrad``) passa a ser obrigatória.
    """
    fck = validar_fck(fck_mpa)
    x_sobre_d = float(xd)
    limite = 0.25 if fck <= 50.0 else 0.15
    ok = x_sobre_d <= limite
    item = "14.6.4.4/14.7.4"
    memoria = (
        f"{item}: limite de dispensa x/d <= {limite:g} "
        f"(fck = {fck:g} MPa {'<=' if fck <= 50.0 else '>'} 50 MPa).",
        f"{item}: x/d informado = {x_sobre_d:g}.",
        f"{item}: dispensa da verificação explícita de rotação "
        f"{'concedida' if ok else 'não concedida'}.",
    )
    return DispensaRotacaoPlastica(
        xd=x_sobre_d, fck_mpa=fck, xd_limite=limite, ok=ok,
        governante=item, memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 14.7.4 — Razão mínima entre momentos de borda e de vão, análise plástica de
# lajes retangulares (PDF p. 116)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class VerificacaoRazaoMomentosBordaVao:
    """Resultado da verificação da razão mínima 1,5:1 entre momento de borda e
    momento de vão (14.7.4, lajes retangulares, análise plástica)."""
    M_borda_kncm: float
    M_vao_kncm: float
    razao: float
    razao_minima: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_razao_momentos_borda_vao(
    M_borda_kncm: float, M_vao_kncm: float,
) -> VerificacaoRazaoMomentosBordaVao:
    """Razão mínima entre momento de borda e momento de vão em lajes
    retangulares analisadas pela teoria das charneiras plásticas (NBR
    6118:2026, 14.7.4, PDF p. 116).

    Deve ser adotada, para lajes retangulares, razão mínima de 1,5:1 entre
    momentos de borda (com continuidade e apoio indeslocável) e momentos de
    vão: M_borda/M_vao >= 1,5. M_borda_kncm e M_vao_kncm são os módulos dos
    momentos fletores, em kN·cm, e devem ser positivos.
    """
    m_borda = float(M_borda_kncm)
    m_vao = float(M_vao_kncm)
    if m_borda <= 0.0 or m_vao <= 0.0:
        raise FaixaNormativaError(
            "M_borda e M_vao devem ser positivos (14.7.4: razão entre módulos "
            "de momento de borda e de vão)."
        )
    razao_minima = 1.5
    razao = m_borda / m_vao
    ok = razao >= razao_minima
    item = "14.7.4"
    memoria = (
        f"{item}: razão mínima M_borda/M_vao >= {razao_minima:g} "
        "(lajes retangulares, borda contínua e apoio indeslocável, análise "
        "plástica pela teoria das charneiras).",
        f"{item}: M_borda = {m_borda:g} kN·cm; M_vao = {m_vao:g} kN·cm; "
        f"razão = {razao:g}.",
        f"{item}: razão {'atende' if ok else 'não atende'} ao mínimo de "
        f"{razao_minima:g}.",
    )
    return VerificacaoRazaoMomentosBordaVao(
        M_borda_kncm=m_borda, M_vao_kncm=m_vao, razao=razao,
        razao_minima=razao_minima, ok=ok, governante=item, memoria=memoria,
    )
