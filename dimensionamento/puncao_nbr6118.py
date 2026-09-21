"""Punção em lajes — ABNT NBR 6118:2026, 19.5.1 a 19.5.3.3 (PDF p. 182 a 190).

Modelo de cálculo (19.5.1, PDF p. 182): verificação do cisalhamento em duas
ou mais superfícies críticas no entorno da força concentrada:

    - contorno C (perímetro do pilar ou da área carregada, u0): verificação
      indireta da compressão diagonal do concreto, τSd <= τRd2 (19.5.3.1);
    - contorno C′, afastado 2d de C (perímetro u): capacidade à punção
      associada à tração diagonal, τSd <= τRd1 sem armadura (19.5.3.2) ou
      τSd <= τRd3 com armadura (19.5.3.3);
    - contorno C″, afastado 2d do último contorno de armadura: só quando é
      preciso armadura de punção, τSd <= τRd1 (19.5.3.4). A disposição da
      armadura e o traçado de C″ são do P20; aqui C″ é verificado com o
      perímetro u″ informado pelo chamador.

Tensão solicitante (19.5.2, PDF p. 183 a 186): pilar interno com carregamento
simétrico (19.5.2.1), pilar interno com momento (19.5.2.2, Tabela 19.2 e Wp),
pilar de borda com e sem momento paralelo à borda livre (19.5.2.3) e pilar de
canto (19.5.2.4). Capitel, reentrância, abertura, Wp genérico por integração,
armadura obrigatória, colapso progressivo e laje protendida são do P20.

Unidades: força em kN, momento em kN·cm, comprimentos em cm, Wp em cm²,
tensões devolvidas em MPa (a conta é feita em kN/cm² e multiplicada por 10:
1 kN/cm² = 10 MPa), fck e fywd em MPa, taxas adimensionais.

Norma: ABNT NBR 6118:2026. As páginas citadas são as do PDF (a página
impressa é 18 a menos).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
    import seguranca_nbr6118 as seg
    import cortante_nbr6118 as cortante
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr
    from dimensionamento import seguranca_nbr6118 as seg
    from dimensionamento import cortante_nbr6118 as cortante

FaixaNormativaError = nbr.FaixaNormativaError

# ---------------------------------------------------------------------------
# Tabela 19.2 — valores de K (19.5.2.2, PDF p. 184)
# C1: dimensão do pilar paralela à excentricidade da força;
# C2: dimensão do pilar perpendicular à excentricidade da força.
# ---------------------------------------------------------------------------
TABELA_19_2_K = {0.5: 0.45, 1.0: 0.60, 2.0: 0.70, 3.0: 0.80}
K_CIRCULAR = 0.6                 # pilares circulares internos (19.5.2.2)

# 19.5.3.1 — τRd2 = 0,27·αv·fcd; ampliação de 20 % junto a pilar interno
COEF_TAU_RD2 = 0.27
AMPLIACAO_TAU_RD2 = 1.20

# 19.5.3.2 e 19.5.3.3
COEF_TAU_RD1 = 0.13              # sem armadura de punção
COEF_TAU_RD3_CONCRETO = 0.10     # parcela do concreto com armadura de punção
COEF_SIGMA_CP = 0.10
COEF_ARMADURA_RD3 = 1.5
RHO_MAX_PUNCAO = 0.02
KE_MAX = 2.0
SIGMA_CP_MAX_MPA = 3.5
SIGMA_CP_MIN_MPA = 1.0           # σcp,x ou σcp,y <= 1 MPa: despreza σcp
SR_MAX_FATOR_D = 0.75            # sr <= 0,75·d
FYWD_MAX_STUDS_MPA = 300.0       # conectores (studs), lajes até 15 cm
FYWD_MAX_ESTRIBOS_MPA = 250.0    # estribos CA-50 ou CA-60, lajes até 15 cm
H_LAJE_AUMENTO_FYWD_CM = 15.0    # acima disso vale o aumento de 19.4.2

# 19.5.2.3 — trecho reto de u* junto à borda: o menor entre 1,5d e 0,5C1
A_ESTRELA_FATOR_D = 1.5
A_ESTRELA_FATOR_C = 0.5

_TIPOS = ("interno", "borda", "canto")


def _fmt(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


def _positivo(valor: float, nome: str, item: str) -> float:
    v = float(valor)
    if not v > 0.0:
        raise FaixaNormativaError(f"{nome} tem de ser positivo ({item}); recebido {v:g}.")
    return v


def _nao_negativo(valor: float, nome: str, item: str) -> float:
    v = float(valor)
    if v < 0.0:
        raise FaixaNormativaError(f"{nome} não pode ser negativo ({item}); recebido {v:g}.")
    return v


def _tipo(tipo: str) -> str:
    t = nbr._chave(tipo)
    if t not in _TIPOS:
        raise ValueError(f"Tipo de pilar desconhecido: {tipo!r}. Use 'interno', 'borda' ou 'canto'.")
    return t


def _contorno(contorno: str) -> str:
    """'C' (contorno C, u0) ou 'Cl' (contorno C′, u). Aceita "C'" e "C′"."""
    c = str(contorno).strip().replace("′", "'").lower()
    if c == "c":
        return "C"
    if c in ("cl", "c'", "clinha"):
        return "Cl"
    raise ValueError(f"Contorno desconhecido: {contorno!r}. Use 'C' ou 'Cl' (C′).")


def _afastamento_cm(d_cm: float, contorno: str) -> float:
    """Afastamento r do contorno em relação ao pilar: 0 em C, 2d em C′."""
    return 0.0 if _contorno(contorno) == "C" else 2.0 * d_cm


# ---------------------------------------------------------------------------
# Altura útil — 19.5.2.1 (PDF p. 183) e 19.5.3.2 (PDF p. 188-189)
# ---------------------------------------------------------------------------
def d_medio_cm(dx_cm: float, dy_cm: float) -> float:
    """Altura útil da laje no contorno crítico, d = (dx + dy)/2 (19.5.2.1, PDF p. 183).

    dx e dy são as alturas úteis nas duas direções ortogonais, em cm.
    """
    dx = _positivo(dx_cm, "dx", "19.5.2.1")
    dy = _positivo(dy_cm, "dy", "19.5.2.1")
    return (dx + dy) / 2.0


# ---------------------------------------------------------------------------
# Perímetros críticos — Figuras 19.2, 19.3 e 19.4 (PDF p. 183, 185 e 186)
# ---------------------------------------------------------------------------
def perimetro_critico_cm(c1_cm: float, c2_cm: float, d_cm: float,
                         tipo: str = "interno", contorno: str = "Cl") -> float:
    """Perímetro do contorno C (u0) ou C′ (u) de pilar retangular (19.5.2, Figuras 19.2 a 19.4).

    C′ fica a 2d de C, com cantos em arco de raio 2d (PDF p. 183, 185 e 186):

        interno: u0 = 2·(C1 + C2)        u = 2·(C1 + C2) + 4·π·d
        borda:   u0 = 2·C1 + C2          u = 2·C1 + C2 + 2·π·d
        canto:   u0 = C1 + C2            u = C1 + C2 + π·d

    Na borda, C1 é o lado perpendicular à borda livre e C2 o paralelo
    (Figura 19.3); no canto, C1 e C2 são os dois lados do pilar. Em borda e
    canto, u0 é a parte do perímetro do pilar que fica dentro da laje (a face
    sobre a borda livre não conta): a norma só diz "u0 (perímetro do contorno
    C)" (19.5.3.1, PDF p. 188), e esta é a leitura da biblioteca.

    c1_cm, c2_cm, d_cm em cm, positivos. ``contorno`` = 'C' ou 'Cl' (C′).
    """
    c1 = _positivo(c1_cm, "C1", "19.5.2")
    c2 = _positivo(c2_cm, "C2", "19.5.2")
    d = _positivo(d_cm, "d", "19.5.2")
    t = _tipo(tipo)
    r = _afastamento_cm(d, contorno)
    if t == "interno":
        return 2.0 * (c1 + c2) + 2.0 * math.pi * r
    if t == "borda":
        return 2.0 * c1 + c2 + math.pi * r
    return c1 + c2 + math.pi * r / 2.0


def perimetro_critico_circular_cm(D_cm: float, d_cm: float, contorno: str = "Cl") -> float:
    """Perímetro do contorno C (u0 = π·D) ou C′ (u = π·(D + 4d)) de pilar circular interno (Figura 19.2, PDF p. 183)."""
    D = _positivo(D_cm, "D", "19.5.2.1")
    d = _positivo(d_cm, "d", "19.5.2.1")
    return math.pi * (D + 2.0 * _afastamento_cm(d, contorno))


def a_estrela_cm(c_cm: float, d_cm: float) -> float:
    """Trecho reto de u* junto à borda livre: o menor entre 1,5d e 0,5C (19.5.2.3 e 19.5.2.4, Figuras 19.3 e 19.4, PDF p. 185-186).

    Na borda, C = C1 (lado perpendicular à borda livre). No canto, cada trecho
    usa o lado do pilar ao longo do qual corre (Figura 19.4). Medido a partir
    da face interna do pilar, em direção à borda livre. cm.
    """
    c = _positivo(c_cm, "C", "19.5.2.3")
    d = _positivo(d_cm, "d", "19.5.2.3")
    return min(A_ESTRELA_FATOR_D * d, A_ESTRELA_FATOR_C * c)


def u_estrela_cm(c1_cm: float, c2_cm: float, d_cm: float, tipo: str = "borda") -> float:
    """Perímetro crítico reduzido u* de pilar de borda ou de canto (19.5.2.3 e 19.5.2.4, PDF p. 185-186).

        borda: u* = 2·a + C2 + 2·π·d,     a = min(1,5d; 0,5·C1)
        canto: u* = a1 + a2 + π·d,        a1 = min(1,5d; 0,5·C1), a2 = min(1,5d; 0,5·C2)

    C1 é o lado perpendicular à borda livre adotada e C2 o paralelo
    (Figuras 19.3 e 19.4). Pilar interno não tem u* (levanta ``ValueError``).
    """
    c1 = _positivo(c1_cm, "C1", "19.5.2.3")
    c2 = _positivo(c2_cm, "C2", "19.5.2.3")
    d = _positivo(d_cm, "d", "19.5.2.3")
    t = _tipo(tipo)
    if t == "interno":
        raise ValueError("u* só existe para pilar de borda ou de canto (19.5.2.3 e 19.5.2.4).")
    if t == "borda":
        return 2.0 * a_estrela_cm(c1, d) + c2 + 2.0 * math.pi * d
    return a_estrela_cm(c1, d) + a_estrela_cm(c2, d) + math.pi * d


def excentricidade_u_estrela_cm(c1_cm: float, c2_cm: float, d_cm: float,
                                tipo: str = "borda") -> float:
    """Excentricidade e* do centro de gravidade de u* em relação ao centro do pilar (19.5.2.3, PDF p. 185).

    A norma define MSd* = "momento de cálculo resultante da excentricidade do
    perímetro crítico reduzido u* em relação ao centro do pilar"; e* é essa
    excentricidade, medida na direção perpendicular à borda livre adotada, e
    MSd* = FSd·e*. As expressões fechadas saem da geometria das Figuras 19.3
    e 19.4 (trechos retos de comprimento a junto à face interna do pilar,
    arcos de raio 2d e trecho paralelo à borda a C1/2 + 2d do centro):

        borda: e* = [a·C1 − a² + C1·C2/2 + 2d·C2 + π·d·C1 + 8d²] / u*
        canto: e* = [(a1·C1 − a1²)/2 + π·d·C1/2 + 4d² + a2·(C1/2 + 2d)] / u*

    C1 é o lado perpendicular à borda livre adotada. Resultado em cm.
    """
    c1 = _positivo(c1_cm, "C1", "19.5.2.3")
    c2 = _positivo(c2_cm, "C2", "19.5.2.3")
    d = _positivo(d_cm, "d", "19.5.2.3")
    t = _tipo(tipo)
    if t == "interno":
        raise ValueError("e* só existe para pilar de borda ou de canto (19.5.2.3 e 19.5.2.4).")
    us = u_estrela_cm(c1, c2, d, t)
    if t == "borda":
        a = a_estrela_cm(c1, d)
        num = a * c1 - a * a + c1 * c2 / 2.0 + 2.0 * d * c2 + math.pi * d * c1 + 8.0 * d * d
        return num / us
    a1 = a_estrela_cm(c1, d)
    a2 = a_estrela_cm(c2, d)
    num = ((a1 * c1 - a1 * a1) / 2.0 + math.pi * d * c1 / 2.0 + 4.0 * d * d
           + a2 * (c1 / 2.0 + 2.0 * d))
    return num / us


# ---------------------------------------------------------------------------
# Tabela 19.2 — coeficiente K (19.5.2.2, PDF p. 184)
# ---------------------------------------------------------------------------
def K(c1_c2: float, interpolar: bool = True) -> float:
    """Coeficiente K da Tabela 19.2 em função de C1/C2 (19.5.2.2, PDF p. 184).

        C1/C2 | 0,5  | 1,0  | 2,0  | 3,0
        K     | 0,45 | 0,60 | 0,70 | 0,80

    C1 é a dimensão do pilar paralela à excentricidade da força e C2 a
    perpendicular. A norma só dá os quatro valores e não diz como tratar os
    intermediários: com ``interpolar=True`` (padrão) a função interpola
    linearmente, que é a prática corrente; com ``interpolar=False`` usa o K do
    degrau superior da tabela (o maior K, a favor da segurança). Fora de
    0,5 <= C1/C2 <= 3,0 a norma não define K e a função levanta
    ``FaixaNormativaError``. Para pilar circular interno, use ``K_CIRCULAR``
    (K = 0,6).
    """
    x = float(c1_c2)
    xs = tuple(sorted(TABELA_19_2_K))
    if not (xs[0] - 1e-12 <= x <= xs[-1] + 1e-12):
        raise FaixaNormativaError(
            f"C1/C2 = {x:g} fora da Tabela 19.2 (0,5 a 3,0): a norma não define K "
            "para essa proporção (19.5.2.2).")
    x = min(max(x, xs[0]), xs[-1])
    for xi in xs:
        if abs(x - xi) <= 1e-12:
            return TABELA_19_2_K[xi]
    for x0, x1 in zip(xs, xs[1:]):
        if x0 < x < x1:
            k0, k1 = TABELA_19_2_K[x0], TABELA_19_2_K[x1]
            if not interpolar:
                return k1
            return k0 + (k1 - k0) * (x - x0) / (x1 - x0)
    raise AssertionError("inalcançável")  # pragma: no cover


# ---------------------------------------------------------------------------
# Wp — módulo de resistência plástica do perímetro crítico (19.5.2.2 e 19.5.2.3)
# ---------------------------------------------------------------------------
def Wp_retangular_cm2(c1_cm: float, c2_cm: float, d_cm: float, contorno: str = "Cl") -> float:
    """Wp de pilar retangular interno, cm² (19.5.2.2, PDF p. 184).

        Wp = C1²/2 + C1·C2 + 4·C2·d + 16·d² + 2·π·d·C1

    C1 é a dimensão paralela à excentricidade (a do momento). É a integral
    Wp = ∫|e|·dℓ ao longo de u, com e medido do eixo pelo centro do pilar.
    Com ``contorno='C'`` a integral é feita sobre u0 (19.5.3.1 manda usar u0
    em lugar de u), o que dá Wp0 = C1²/2 + C1·C2 (a mesma expressão com o
    afastamento nulo).
    """
    c1 = _positivo(c1_cm, "C1", "19.5.2.2")
    c2 = _positivo(c2_cm, "C2", "19.5.2.2")
    d = _positivo(d_cm, "d", "19.5.2.2")
    r = _afastamento_cm(d, contorno)
    # com r = 2d: 2·C2·r = 4·C2·d; 4·r² = 16·d²; π·r·C1 = 2·π·d·C1
    return c1 * c1 / 2.0 + c1 * c2 + 2.0 * c2 * r + 4.0 * r * r + math.pi * r * c1


def Wp_circular_cm2(D_cm: float, d_cm: float, contorno: str = "Cl") -> float:
    """Wp de pilar circular interno, Wp = (D + 4d)², cm² (19.5.2.2, PDF p. 184).

    Com ``contorno='C'`` (integral sobre u0 = π·D) dá Wp0 = D².
    """
    D = _positivo(D_cm, "D", "19.5.2.2")
    d = _positivo(d_cm, "d", "19.5.2.2")
    return (D + 2.0 * _afastamento_cm(d, contorno)) ** 2


def Wp1_borda_cm2(c1_cm: float, c2_cm: float, d_cm: float, contorno: str = "Cl") -> float:
    """Wp1 de pilar de borda (momento no plano perpendicular à borda livre), cm² (19.5.2.3, PDF p. 185).

    A norma define Wp1 como "o módulo de resistência plástica perpendicular à
    borda livre, calculado para o perímetro u" e dá só a integral
    Wp = ∫|e|·dℓ (19.5.2.2). Resolvida em forma fechada sobre o perímetro u da
    Figura 19.3 (dois trechos de comprimento C1 perpendiculares à borda, dois
    arcos de raio 2d e o trecho paralelo à borda), com e medido do eixo
    paralelo à borda pelo centro do pilar:

        Wp1 = C1²/2 + C1·C2/2 + 2·C2·d + 8·d² + π·d·C1

    C1 perpendicular e C2 paralelo à borda livre. Com ``contorno='C'``, a
    mesma integral sobre u0 = 2·C1 + C2: Wp1,0 = C1²/2 + C1·C2/2.
    """
    c1 = _positivo(c1_cm, "C1", "19.5.2.3")
    c2 = _positivo(c2_cm, "C2", "19.5.2.3")
    d = _positivo(d_cm, "d", "19.5.2.3")
    r = _afastamento_cm(d, contorno)
    return c1 * c1 / 2.0 + c1 * c2 / 2.0 + c2 * r + 2.0 * r * r + math.pi * r * c1 / 2.0


def Wp2_borda_cm2(c1_cm: float, c2_cm: float, d_cm: float, contorno: str = "Cl") -> float:
    """Wp2 de pilar de borda (momento no plano paralelo à borda livre), cm² (19.5.2.3 b, PDF p. 185-186).

    "Módulo de resistência plástica na direção paralela à borda livre,
    calculado pelo perímetro u." Integral Wp = ∫|e|·dℓ sobre o u da
    Figura 19.3, com e medido do eixo perpendicular à borda pelo centro do
    pilar:

        Wp2 = C2²/4 + C1·C2 + 4·C1·d + 8·d² + π·d·C2

    C1 perpendicular e C2 paralelo à borda livre. Com ``contorno='C'``:
    Wp2,0 = C2²/4 + C1·C2.
    """
    c1 = _positivo(c1_cm, "C1", "19.5.2.3")
    c2 = _positivo(c2_cm, "C2", "19.5.2.3")
    d = _positivo(d_cm, "d", "19.5.2.3")
    r = _afastamento_cm(d, contorno)
    return c2 * c2 / 4.0 + c1 * c2 + 2.0 * c1 * r + 2.0 * r * r + math.pi * r * c2 / 2.0


def Wp1_canto_cm2(c1_cm: float, c2_cm: float, d_cm: float, contorno: str = "Cl") -> float:
    """Wp1 de pilar de canto para a borda livre adotada, cm² (19.5.2.4 sobre 19.5.2.3 a, PDF p. 186).

    Integral Wp = ∫|e|·dℓ sobre o perímetro u da Figura 19.4 (trecho de
    comprimento C1 perpendicular à borda adotada, um arco de raio 2d e o
    trecho de comprimento C2 paralelo a ela), com e medido do eixo paralelo à
    borda adotada pelo centro do pilar:

        Wp1 = C1²/4 + C1·C2/2 + 2·C2·d + 4·d² + π·d·C1/2

    C1 é o lado perpendicular e C2 o paralelo à borda livre adotada. Com
    ``contorno='C'`` (u0 = C1 + C2): Wp1,0 = C1²/4 + C1·C2/2.
    """
    c1 = _positivo(c1_cm, "C1", "19.5.2.4")
    c2 = _positivo(c2_cm, "C2", "19.5.2.4")
    d = _positivo(d_cm, "d", "19.5.2.4")
    r = _afastamento_cm(d, contorno)
    return c1 * c1 / 4.0 + c1 * c2 / 2.0 + c2 * r + r * r + math.pi * r * c1 / 4.0


# ---------------------------------------------------------------------------
# Tensão solicitante τSd — 19.5.2 (PDF p. 183 a 186)
# ---------------------------------------------------------------------------
def tau_Sd_mpa(FSd_kn: float, u_cm: float, d_cm: float,
               MSd_kncm: float = 0.0, K: float | None = None, Wp_cm2: float | None = None,
               MSd2_kncm: float = 0.0, K2: float | None = None,
               Wp2_cm2: float | None = None) -> float:
    """Tensão solicitante de punção, MPa (19.5.2.1 a 19.5.2.3, PDF p. 183 a 185).

        τSd = FSd/(u·d)                                        (19.5.2.1)
        τSd = FSd/(u·d) + K·MSd/(Wp·d)                          (19.5.2.2)
        τSd = FSd/(u*·d) + K1·MSd1/(Wp1·d) + K2·MSd2/(Wp2·d)    (19.5.2.3 b)

    Forma geral; quem escolhe u (u, u* ou u0), K, Wp e o momento (MSd ou
    MSd1 = MSd − MSd*) é o chamador ou as funções ``tau_Sd_interno_mpa``,
    ``tau_Sd_borda_mpa`` e ``tau_Sd_canto_mpa``. FSd em kN (pode ser reduzida
    da força distribuída aplicada na face oposta da laje dentro do contorno
    considerado, 19.5.2.1), u e d em cm, MSd em kN·cm, Wp em cm². A conta sai
    em kN/cm² e é multiplicada por 10 para MPa. Os momentos entram em módulo.
    Momento diferente de zero exige o K e o Wp correspondentes.
    """
    F = _nao_negativo(FSd_kn, "FSd", "19.5.2")
    u = _positivo(u_cm, "u", "19.5.2")
    d = _positivo(d_cm, "d", "19.5.2")
    tau = F / (u * d)
    for M, k, W, nome in ((MSd_kncm, K, Wp_cm2, "MSd"), (MSd2_kncm, K2, Wp2_cm2, "MSd2")):
        M = abs(float(M))
        if M == 0.0:
            continue
        if k is None or W is None:
            raise ValueError(f"{nome} diferente de zero exige o K e o Wp correspondentes (19.5.2.2).")
        tau += float(k) * M / (_positivo(W, "Wp", "19.5.2.2") * d)
    return tau * 10.0


def tau_Sd_interno_mpa(FSd_kn: float, c1_cm: float, c2_cm: float, d_cm: float,
                       MSd_kncm: float = 0.0, contorno: str = "Cl",
                       interpolar: bool = True) -> float:
    """τSd de pilar interno retangular, MPa (19.5.2.1 e 19.5.2.2, PDF p. 183-184).

        τSd = FSd/(u·d) + K·MSd/(Wp·d)

    C1 é o lado paralelo à excentricidade (ao plano do momento). K da
    Tabela 19.2 com C1/C2 (``interpolar`` como em ``K``), Wp de
    ``Wp_retangular_cm2``. Com ``contorno='C'`` usa u0 e Wp sobre u0
    (19.5.3.1). Com MSd = 0 é o caso simétrico de 19.5.2.1, e a Tabela 19.2
    não é consultada.
    """
    u = perimetro_critico_cm(c1_cm, c2_cm, d_cm, "interno", contorno)
    if float(MSd_kncm) == 0.0:
        return tau_Sd_mpa(FSd_kn, u, d_cm)
    k = K(float(c1_cm) / float(c2_cm), interpolar)
    W = Wp_retangular_cm2(c1_cm, c2_cm, d_cm, contorno)
    return tau_Sd_mpa(FSd_kn, u, d_cm, MSd_kncm, k, W)


def tau_Sd_interno_circular_mpa(FSd_kn: float, D_cm: float, d_cm: float,
                                MSd_kncm: float = 0.0, contorno: str = "Cl") -> float:
    """τSd de pilar interno circular, MPa (19.5.2.2, PDF p. 184).

        τSd = FSd/(u·d) + K·MSd/(Wp·d),  K = 0,6,  Wp = (D + 4d)²,  u = π·(D + 4d)
    """
    u = perimetro_critico_circular_cm(D_cm, d_cm, contorno)
    W = Wp_circular_cm2(D_cm, d_cm, contorno)
    return tau_Sd_mpa(FSd_kn, u, d_cm, MSd_kncm, K_CIRCULAR, W)


def MSd1_borda_kncm(FSd_kn: float, MSd_kncm: float, c1_cm: float, c2_cm: float,
                    d_cm: float, tipo: str = "borda") -> float:
    """MSd1 = (MSd − MSd*) >= 0, kN·cm, com MSd* = FSd·e* (19.5.2.3 a, PDF p. 185).

    MSd é o momento de cálculo no plano perpendicular à borda livre (em
    módulo, no sentido em que a excentricidade de u* o alivia, que é o do
    momento transmitido pela laje ao pilar de borda); e* de
    ``excentricidade_u_estrela_cm``. Serve também ao pilar de canto
    (19.5.2.4), com ``tipo='canto'``.
    """
    F = _nao_negativo(FSd_kn, "FSd", "19.5.2.3")
    M = _nao_negativo(MSd_kncm, "MSd", "19.5.2.3")
    Mest = F * excentricidade_u_estrela_cm(c1_cm, c2_cm, d_cm, tipo)
    return max(M - Mest, 0.0)


def tau_Sd_borda_mpa(FSd_kn: float, c1_cm: float, c2_cm: float, d_cm: float,
                     MSd_kncm: float = 0.0, MSd2_kncm: float = 0.0,
                     contorno: str = "Cl", interpolar: bool = True) -> float:
    """τSd de pilar de borda, MPa (19.5.2.3 a e b, PDF p. 185-186).

        a) τSd = FSd/(u*·d) + K1·MSd1/(Wp1·d)
        b) τSd = FSd/(u*·d) + K1·MSd1/(Wp1·d) + K2·MSd2/(Wp2·d)

    MSd1 = (MSd − MSd*) >= 0, com MSd no plano perpendicular à borda livre;
    MSd2 no plano paralelo à borda. K1 da Tabela 19.2 com C1/C2 e K2 com
    C2/(2·C1), C1 perpendicular e C2 paralelo à borda (Figura 19.3). Wp1 e
    Wp2 calculados para o perímetro u (``Wp1_borda_cm2``, ``Wp2_borda_cm2``).

    Contorno C (19.5.3.1, "com u0 em lugar de u"): a norma não detalha o
    contorno C de pilar de borda. A biblioteca usa u0 = 2·C1 + C2 (perímetro
    do pilar dentro da laje), Wp sobre u0 e o momento MSd inteiro, sem o
    desconto de MSd* (que só existe para o perímetro reduzido u*), o que fica
    a favor da segurança.
    """
    c1 = _positivo(c1_cm, "C1", "19.5.2.3")
    c2 = _positivo(c2_cm, "C2", "19.5.2.3")
    d = _positivo(d_cm, "d", "19.5.2.3")
    M1 = _nao_negativo(MSd_kncm, "MSd", "19.5.2.3")
    M2 = abs(float(MSd2_kncm))
    if _contorno(contorno) == "C":
        u = perimetro_critico_cm(c1, c2, d, "borda", "C")
    else:
        u = u_estrela_cm(c1, c2, d, "borda")
        M1 = MSd1_borda_kncm(FSd_kn, M1, c1, c2, d, "borda")
    k1 = K(c1 / c2, interpolar) if M1 > 0.0 else None
    k2 = K(c2 / (2.0 * c1), interpolar) if M2 > 0.0 else None
    W1 = Wp1_borda_cm2(c1, c2, d, contorno)
    W2 = Wp2_borda_cm2(c1, c2, d, contorno)
    return tau_Sd_mpa(FSd_kn, u, d, M1, k1, W1, M2, k2, W2)


def tau_Sd_canto_mpa(FSd_kn: float, c1_cm: float, c2_cm: float, d_cm: float,
                     MSd_kncm: float = 0.0, contorno: str = "Cl",
                     interpolar: bool = True) -> float:
    """τSd de pilar de canto para UMA borda livre adotada, MPa (19.5.2.4, PDF p. 186).

    "Aplica-se o disposto para o pilar de borda quando não age momento no
    plano paralelo à borda." A verificação é feita separadamente para cada
    borda livre, com o momento cujo plano é perpendicular à borda adotada; K
    com C1/C2, C1 o lado perpendicular e C2 o paralelo à borda adotada
    (Figura 19.4). Para a outra borda, troque C1 com C2 e passe o outro
    momento (``verificar_puncao`` faz as duas).

        τSd = FSd/(u*·d) + K1·MSd1/(Wp1·d),  MSd1 = (MSd − FSd·e*) >= 0

    u* = a1 + a2 + π·d; Wp1 de ``Wp1_canto_cm2``. No contorno C, a mesma
    leitura do pilar de borda: u0 = C1 + C2, Wp sobre u0 e MSd inteiro.
    """
    c1 = _positivo(c1_cm, "C1", "19.5.2.4")
    c2 = _positivo(c2_cm, "C2", "19.5.2.4")
    d = _positivo(d_cm, "d", "19.5.2.4")
    M1 = _nao_negativo(MSd_kncm, "MSd", "19.5.2.4")
    if _contorno(contorno) == "C":
        u = perimetro_critico_cm(c1, c2, d, "canto", "C")
    else:
        u = u_estrela_cm(c1, c2, d, "canto")
        M1 = MSd1_borda_kncm(FSd_kn, M1, c1, c2, d, "canto")
    k1 = K(c1 / c2, interpolar) if M1 > 0.0 else None
    W1 = Wp1_canto_cm2(c1, c2, d, contorno)
    return tau_Sd_mpa(FSd_kn, u, d, M1, k1, W1)


# ---------------------------------------------------------------------------
# Tensões resistentes — 19.5.3 (PDF p. 188 a 190)
# ---------------------------------------------------------------------------
def tau_Rd2_mpa(fck_mpa: float, gama_c: float = nbr.GAMA_C, ampliar_20pct: bool = False) -> float:
    """τRd2 = 0,27·αv·fcd, MPa — compressão diagonal no contorno C (19.5.3.1, PDF p. 188).

    αv = 1 − fck/250 (fck em MPa; ``nucleo.alpha_v2``), fcd = fck/γc
    (``nucleo.fcd``). Com ``ampliar_20pct=True`` devolve 1,2·τRd2: "pode ser
    ampliado de 20 % por efeito de estado múltiplo de tensões junto a um pilar
    interno, quando os vãos que chegam a esse pilar não diferem mais de 50 %
    e não existem aberturas junto ao pilar" — quem confere essas condições é
    o chamador.
    """
    t = COEF_TAU_RD2 * nbr.alpha_v2(fck_mpa) * nbr.fcd(fck_mpa, gama_c)
    return AMPLIACAO_TAU_RD2 * t if ampliar_20pct else t


def rho_puncao(rho_x: float, rho_y: float) -> float:
    """ρ = √(ρx·ρy) <= 0,02 (19.5.3.2, PDF p. 188-189).

    ρx e ρy são as taxas da armadura de flexão aderente (a não aderente é
    desprezada) nas duas direções, na largura do pilar ou da área carregada
    acrescida de 3d para cada lado (ou até a borda, quando mais perto que 3d).
    O teto de 0,02 é aplicado (acima dele, ρ = 0,02).
    """
    rx = _nao_negativo(rho_x, "ρx", "19.5.3.2")
    ry = _nao_negativo(rho_y, "ρy", "19.5.3.2")
    return min(math.sqrt(rx * ry), RHO_MAX_PUNCAO)


def ke_puncao(d_cm: float) -> float:
    """Coeficiente de escala ke = 1 + √(20/d) <= 2, d em cm (19.5.3.2, PDF p. 188-189)."""
    d = _positivo(d_cm, "d", "19.5.3.2")
    return min(1.0 + math.sqrt(20.0 / d), KE_MAX)


def sigma_cp_puncao_mpa(sigma_cp_x_mpa: float = 0.0, sigma_cp_y_mpa: float = 0.0) -> float:
    """σcp = (σcp,x + σcp,y)/2 <= 3,5 MPa (19.5.3.2, PDF p. 189).

    σcp,x = NSd,x/Ac e σcp,y = NSd,y/Ac, compressão positiva (forças axiais de
    compressão no contorno C′, por exemplo da protensão, já com as perdas).
    "Caso σcp,x <= 1 MPa ou σcp,y <= 1 MPa deve-se desprezar o efeito
    favorável de σcp": a função devolve 0 nesse caso. O teto de 3,5 MPa é
    aplicado.
    """
    sx, sy = float(sigma_cp_x_mpa), float(sigma_cp_y_mpa)
    if sx <= SIGMA_CP_MIN_MPA or sy <= SIGMA_CP_MIN_MPA:
        return 0.0
    return min((sx + sy) / 2.0, SIGMA_CP_MAX_MPA)


def _parcela_concreto_mpa(coef: float, fck_mpa: float, rho: float, d_cm: float) -> float:
    fck = nbr.validar_fck(fck_mpa)
    r = _nao_negativo(rho, "ρ", "19.5.3.2")
    r = min(r, RHO_MAX_PUNCAO)
    return coef * ke_puncao(d_cm) * (100.0 * r * fck) ** (1.0 / 3.0)


def tau_Rd1_mpa(fck_mpa: float, rho: float, d_cm: float, sigma_cp_mpa: float = 0.0) -> float:
    """τRd1 = 0,13·ke·(100·ρ·fck)^(1/3) + 0,10·σcp, MPa — C′ sem armadura de punção (19.5.3.2, PDF p. 188-189).

    ρ = √(ρx·ρy) <= 0,02 (``rho_puncao``; aqui o teto é aplicado de novo),
    ke = 1 + √(20/d) <= 2 com d em cm, fck em MPa, σcp em MPa já tratado por
    ``sigma_cp_puncao_mpa`` (<= 3,5 MPa; zero quando σcp,x ou σcp,y <= 1 MPa).
    Vale também em C1′ e C2′ com capitel e em C″ (19.5.3.4).
    """
    sc = _nao_negativo(sigma_cp_mpa, "σcp", "19.5.3.2")
    if sc > SIGMA_CP_MAX_MPA:
        raise FaixaNormativaError(f"σcp = {sc:g} MPa acima do teto de 3,5 MPa (19.5.3.2); "
                                  "use sigma_cp_puncao_mpa.")
    return _parcela_concreto_mpa(COEF_TAU_RD1, fck_mpa, rho, d_cm) + COEF_SIGMA_CP * sc


def fywd_max_puncao_mpa(tipo_armadura: str = "studs", h_cm: float | None = None) -> float:
    """Teto de fywd da armadura de punção, MPa (19.5.3.3, PDF p. 190, com 19.4.2, PDF p. 182).

    300 MPa para conectores (studs) e 250 MPa para estribos (CA-50 ou CA-60).
    "Para lajes com espessura maior do que 15 cm, esses valores podem ser
    aumentados conforme estabelecido em 19.4.2", que interpola de 250 MPa
    (h <= 15 cm) a 435 MPa (h > 35 cm) — ``cortante.fywd_max_laje_mpa`` (P15).
    Leitura da biblioteca: estribos seguem a reta de 19.4.2; studs ficam com
    o maior entre 300 MPa e a reta de 19.4.2 (a reta só passa de 300 MPa a
    partir de h ≈ 20,4 cm). Sem ``h_cm``, valem 300 e 250 MPa.
    """
    t = nbr._chave(tipo_armadura)
    if t in ("studs", "stud", "conectores", "conector"):
        base = FYWD_MAX_STUDS_MPA
    elif t in ("estribos", "estribo"):
        base = FYWD_MAX_ESTRIBOS_MPA
    else:
        raise ValueError(f"Tipo de armadura de punção desconhecido: {tipo_armadura!r}. "
                         "Use 'studs' ou 'estribos'.")
    if h_cm is None:
        return base
    h = _positivo(h_cm, "h", "19.5.3.3")
    if h <= H_LAJE_AUMENTO_FYWD_CM:
        return base
    return max(base, cortante.fywd_max_laje_mpa(h))


def tau_Rd3_mpa(fck_mpa: float, rho: float, d_cm: float, Asw_cm2: float, sr_cm: float,
                fywd_mpa: float, u_cm: float, alpha_graus: float = 90.0,
                sigma_cp_mpa: float = 0.0, tipo_armadura: str = "studs",
                h_cm: float | None = None) -> float:
    """τRd3, MPa — C′ com armadura de punção (19.5.3.3, PDF p. 189-190).

        τRd3 = 0,10·ke·(100·ρ·fck)^(1/3) + 0,10·σcp + 1,5·(d/sr)·Asw·fywd·sen α/(u·d)

    d, ke e ρ como em 19.5.3.2 (d em cm); sr = espaçamento radial entre
    linhas de armadura, sr <= 0,75·d (acima disso levanta
    ``FaixaNormativaError``); Asw = área da armadura de punção em um contorno
    completo paralelo a C′, cm²; α = ângulo entre o eixo da armadura e o plano
    da laje (0 < α <= 90°); u = perímetro crítico, ou o reduzido u* em pilar
    de borda ou de canto, cm; fywd em MPa, limitado por
    ``fywd_max_puncao_mpa(tipo_armadura, h_cm)`` (o menor dos dois é usado).

    Atenção: a parcela do concreto usa 0,10, e não o 0,13 de τRd1. Com
    Asw = 0 a expressão NÃO se reduz a τRd1: dá 0,10/0,13 ≈ 77 % da parcela do
    concreto de τRd1. É uma descontinuidade da própria norma (a armadura só é
    considerada quando τSd > τRd1), não erro de transcrição.
    """
    d = _positivo(d_cm, "d", "19.5.3.3")
    sr = _positivo(sr_cm, "sr", "19.5.3.3")
    if sr > SR_MAX_FATOR_D * d * (1.0 + 1e-12):
        raise FaixaNormativaError(
            f"sr = {sr:g} cm maior que 0,75·d = {SR_MAX_FATOR_D * d:g} cm (19.5.3.3).")
    Asw = _nao_negativo(Asw_cm2, "Asw", "19.5.3.3")
    u = _positivo(u_cm, "u", "19.5.3.3")
    a = float(alpha_graus)
    if not (0.0 < a <= 90.0):
        raise FaixaNormativaError(f"α = {a:g}° fora de (0°, 90°] (19.5.3.3).")
    fy = min(_positivo(fywd_mpa, "fywd", "19.5.3.3"), fywd_max_puncao_mpa(tipo_armadura, h_cm))
    sc = _nao_negativo(sigma_cp_mpa, "σcp", "19.5.3.3")
    if sc > SIGMA_CP_MAX_MPA:
        raise FaixaNormativaError(f"σcp = {sc:g} MPa acima do teto de 3,5 MPa (19.5.3.2).")
    concreto = _parcela_concreto_mpa(COEF_TAU_RD3_CONCRETO, fck_mpa, rho, d)
    armadura = COEF_ARMADURA_RD3 * (d / sr) * Asw * fy * math.sin(math.radians(a)) / (u * d)
    return concreto + COEF_SIGMA_CP * sc + armadura


# ---------------------------------------------------------------------------
# Verificação completa — 19.5.1 e 19.5.3 (C, C′ e C″)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoPuncao:
    """Resultado da verificação de punção (19.5.1 a 19.5.3.4)."""

    tipo: str
    d_cm: float
    u0_cm: float
    u_cm: float                       # u (interno) ou u* (borda e canto)
    tau_Sd_C_mpa: float
    tau_Rd2_mpa: float
    tau_Sd_Cl_mpa: float
    tau_Rd1_mpa: float
    armadura_necessaria: bool
    tau_Rd3_mpa: float | None
    tau_Sd_C2l_mpa: float | None
    tau_Rd1_C2l_mpa: float | None
    status_C: str
    status_Cl: str
    status_C2l: str
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_puncao(fck_mpa: float, d_cm: float, FSd_kn: float, c1_cm: float,
                     c2_cm: float | None = None, tipo: str = "interno",
                     MSd1_kncm: float = 0.0, MSd2_kncm: float = 0.0,
                     rho_x: float = 0.0, rho_y: float = 0.0,
                     sigma_cp_x_mpa: float = 0.0, sigma_cp_y_mpa: float = 0.0,
                     Asw_cm2: float | None = None, sr_cm: float | None = None,
                     fywd_mpa: float | None = None, alpha_graus: float = 90.0,
                     tipo_armadura: str = "studs", h_cm: float | None = None,
                     u_C2l_cm: float | None = None,
                     Wp_C2l_cm2: tuple[float, float] | None = None,
                     circular: bool = False, ampliar_tau_Rd2: bool = False,
                     interpolar_K: bool = True,
                     gama_c: float = nbr.GAMA_C,
                     afastamento_C2l_cruz_cm: float | None = None,
                     posicao: str | None = None) -> ResultadoPuncao:
    """Verificação de punção nos contornos C, C′ e C″ (19.5.1 a 19.5.3.4, PDF p. 182 a 190).

    Geometria:
        - ``tipo='interno'``: C1 paralelo ao plano de MSd1 e C2 paralelo ao de
          MSd2; ``circular=True`` e ``c1_cm`` = D para pilar circular (K = 0,6,
          só MSd1). Momentos nos dois planos: a biblioteca soma as duas
          parcelas, K·MSd/(Wp·d), uma por plano (a norma dá 19.5.2.2 com um
          momento; a soma segue 19.5.2.3 b);
        - ``tipo='borda'``: C1 perpendicular e C2 paralelo à borda livre; MSd1
          no plano perpendicular e MSd2 no plano paralelo à borda;
        - ``tipo='canto'``: C1 perpendicular à borda A e C2 perpendicular à
          borda B; MSd1 no plano perpendicular à borda A e MSd2 no plano
          perpendicular à borda B. Faz as duas verificações de 19.5.2.4 e
          adota a maior τSd.

    Verificações:
        1. C: τSd (com u0) <= τRd2 = 0,27·αv·fcd (19.5.3.1), 1,2·τRd2 com
           ``ampliar_tau_Rd2`` (só pilar interno).
        2. C′: τSd <= τRd1 (19.5.3.2). Se não passa e há armadura
           (``Asw_cm2``, ``sr_cm``, ``fywd_mpa``), τSd <= τRd3 (19.5.3.3), com
           u* em borda e canto.
        3. C″: só quando a armadura é necessária. τSd no perímetro u″
           (``u_C2l_cm``, afastado 2d do último contorno de armadura; o
           traçado é do P20) <= τRd1 (19.5.3.4). Os momentos entram inteiros,
           com o K de C′ e os Wp″ de ``Wp_C2l_cm2`` (plano 1, plano 2). Sem
           u″, C″ fica "não verificado" e ``ok`` é falso.
           Armadura em cruz (Figura 19.8, à direita): com
           ``afastamento_C2l_cruz_cm`` (distância de C″ à face do pilar, 2d
           além do último contorno de armadura) e sem ``u_C2l_cm``, u″ sai de
           ``u_C2l_cruz_cm`` e, com momento e sem ``Wp_C2l_cm2``, Wp″ sai de
           ``Wp_C2l_cruz_cm2`` (polo no centróide de C″; plano 1 ao longo de
           C1, plano 2 ao longo de C2). A NBR 6118 não dá a regra numérica
           (Figura 19.8); a construção é a do programa de punção do
           escritório (BRGTools, porte do LPUNC), adotada por decisão do
           engenheiro em 21/09/2026. ``posicao`` é a do pilar na laje, como
           em ``contorno_C2l_cruz`` (b = C1 em x, h = C2 em y).

    ρ = √(ρx·ρy) <= 0,02 e σcp de 19.5.3.2. FSd em kN, momentos em kN·cm,
    comprimentos em cm, tensões em MPa. As comparações passam por
    ``seguranca_nbr6118.verificar_seguranca``.
    """
    t = _tipo(tipo)
    d = _positivo(d_cm, "d", "19.5")
    F = _nao_negativo(FSd_kn, "FSd", "19.5")
    M1 = abs(float(MSd1_kncm))
    M2 = abs(float(MSd2_kncm))
    mem: list[str] = [f"Punção — pilar {t}{' circular' if circular else ''}, "
                      f"d = {_fmt(d)} cm, FSd = {_fmt(F)} kN (19.5)."]
    if circular:
        if t != "interno":
            raise ValueError("Pilar circular: a norma só trata o pilar interno (19.5.2.2).")
        if M2 != 0.0:
            raise ValueError("Pilar circular: informe o momento resultante em MSd1_kncm.")
    elif c2_cm is None:
        raise ValueError("Informe c2_cm para pilar retangular.")
    if ampliar_tau_Rd2 and t != "interno":
        raise ValueError("A ampliação de 20 % de τRd2 só vale junto a pilar interno (19.5.3.1).")

    # --- tensões solicitantes em C e C′ ---
    def _tau(contorno: str) -> float:
        if circular:
            return tau_Sd_interno_circular_mpa(F, c1_cm, d, M1, contorno)
        if t == "interno":
            u = perimetro_critico_cm(c1_cm, c2_cm, d, "interno", contorno)
            k1 = K(c1_cm / c2_cm, interpolar_K) if M1 > 0 else None
            k2 = K(c2_cm / c1_cm, interpolar_K) if M2 > 0 else None
            return tau_Sd_mpa(F, u, d, M1, k1, Wp_retangular_cm2(c1_cm, c2_cm, d, contorno),
                              M2, k2, Wp_retangular_cm2(c2_cm, c1_cm, d, contorno))
        if t == "borda":
            return tau_Sd_borda_mpa(F, c1_cm, c2_cm, d, M1, M2, contorno, interpolar_K)
        return max(tau_Sd_canto_mpa(F, c1_cm, c2_cm, d, M1, contorno, interpolar_K),
                   tau_Sd_canto_mpa(F, c2_cm, c1_cm, d, M2, contorno, interpolar_K))

    if circular:
        u0 = perimetro_critico_circular_cm(c1_cm, d, "C")
        u = perimetro_critico_circular_cm(c1_cm, d, "Cl")
    elif t == "interno":
        u0 = perimetro_critico_cm(c1_cm, c2_cm, d, t, "C")
        u = perimetro_critico_cm(c1_cm, c2_cm, d, t, "Cl")
    else:
        u0 = perimetro_critico_cm(c1_cm, c2_cm, d, t, "C")
        u = u_estrela_cm(c1_cm, c2_cm, d, t)
        mem.append(f"19.5.2.3: u* = {_fmt(u)} cm (trechos junto à borda: o menor entre "
                   f"1,5d e 0,5C); e* = {_fmt(excentricidade_u_estrela_cm(c1_cm, c2_cm, d, t))} cm"
                   " para a borda com C1 perpendicular.")
    tau_C = _tau("C")
    tau_Cl = _tau("Cl")
    if (M1 > 0 or M2 > 0) and not circular:
        mem.append("Tabela 19.2: K " + ("interpolado linearmente entre as colunas (a norma não "
                   "diz como tratar valores intermediários)" if interpolar_K else
                   "do degrau superior da tabela (a favor da segurança)") + ".")

    # --- contorno C ---
    rd2 = tau_Rd2_mpa(fck_mpa, gama_c, ampliar_tau_Rd2)
    mem.append(f"19.5.3.1 (contorno C): u0 = {_fmt(u0)} cm; τSd = {_fmt(tau_C)} MPa; "
               f"τRd2 = {'1,2 × ' if ampliar_tau_Rd2 else ''}0,27·αv·fcd = {_fmt(rd2)} MPa "
               f"(αv = {_fmt(nbr.alpha_v2(fck_mpa))}, fcd = {_fmt(nbr.fcd(fck_mpa, gama_c))} MPa, "
               f"γc = {_fmt(gama_c)}).")
    sC = seg.verificar_seguranca(rd2, tau_C, "τSd x τRd2 (C)", "19.5.3.1")
    mem.extend(sC.memoria)
    status_C = "ok" if sC.ok else "não passa"

    # --- contorno C′ ---
    rho = rho_puncao(rho_x, rho_y)
    sc = sigma_cp_puncao_mpa(sigma_cp_x_mpa, sigma_cp_y_mpa)
    ke = ke_puncao(d)
    rd1 = tau_Rd1_mpa(fck_mpa, rho, d, sc)
    mem.append(f"19.5.3.2 (contorno C′): u{'*' if t != 'interno' else ''} = {_fmt(u)} cm; "
               f"τSd = {_fmt(tau_Cl)} MPa; ρ = √(ρx·ρy) = {_fmt(rho)} (<= 0,02); "
               f"ke = 1 + √(20/d) = {_fmt(ke)} (<= 2); σcp = {_fmt(sc)} MPa; "
               f"τRd1 = 0,13·ke·(100·ρ·fck)^(1/3) + 0,10·σcp = {_fmt(rd1)} MPa.")
    s1 = seg.verificar_seguranca(rd1, tau_Cl, "τSd x τRd1 (C′)", "19.5.3.2")
    mem.extend(s1.memoria)
    armadura_necessaria = not s1.ok
    rd3 = None
    tau_C2 = None
    rd1_C2 = None
    status_C2 = "não necessário"
    ok_Cl = s1.ok
    ok_C2 = True
    if not armadura_necessaria:
        status_Cl = "ok sem armadura de punção"
    elif Asw_cm2 is None or sr_cm is None or fywd_mpa is None:
        status_Cl = "não passa: é necessária armadura de punção"
        ok_Cl = False
        mem.append("τSd > τRd1 em C′ e não foi informada armadura de punção (19.5.3.3).")
    else:
        rd3 = tau_Rd3_mpa(fck_mpa, rho, d, Asw_cm2, sr_cm, fywd_mpa, u, alpha_graus,
                          sc, tipo_armadura, h_cm)
        fy_ef = min(float(fywd_mpa), fywd_max_puncao_mpa(tipo_armadura, h_cm))
        mem.append(f"19.5.3.3 (C′ com armadura): Asw = {_fmt(Asw_cm2)} cm², sr = {_fmt(sr_cm)} cm "
                   f"(<= 0,75d = {_fmt(0.75 * d)} cm), fywd = {_fmt(fy_ef)} MPa, "
                   f"α = {_fmt(alpha_graus)}°; τRd3 = 0,10·ke·(100·ρ·fck)^(1/3) + 0,10·σcp + "
                   f"1,5·(d/sr)·Asw·fywd·sen α/(u·d) = {_fmt(rd3)} MPa.")
        s3 = seg.verificar_seguranca(rd3, tau_Cl, "τSd x τRd3 (C′)", "19.5.3.3")
        mem.extend(s3.memoria)
        ok_Cl = s3.ok
        status_Cl = "ok com armadura de punção" if s3.ok else "não passa com a armadura informada"

    if armadura_necessaria:
        if u_C2l_cm is None and afastamento_C2l_cruz_cm is not None:   # T2: C″ em cruz
            geo = ((None, None) if circular else (c1_cm, c2_cm))
            Dc = c1_cm if circular else None
            u_C2l_cm = u_C2l_cruz_cm(geo[0], geo[1], d, afastamento_C2l_cruz_cm, t, posicao, Dc)
            if (M1 > 0 or M2 > 0) and Wp_C2l_cm2 is None:
                Wp_C2l_cm2 = tuple(
                    Wp_C2l_cruz_cm2(geo[0], geo[1], d, afastamento_C2l_cruz_cm, t, posicao, Dc, ang)
                    if M > 0 else 0.0 for M, ang in ((M1, 0.0), (M2, 90.0)))
            mem.append(f"19.5.3.4 (C″ em cruz, Figura 19.8): C″ a {_fmt(afastamento_C2l_cruz_cm)} cm "
                       f"da face; u″ = {_fmt(u_C2l_cm)} cm — {FONTE_C2L_CRUZ}.")
        if u_C2l_cm is None:
            status_C2 = "não verificado: informe u_C2l_cm (19.5.3.4)"
            ok_C2 = False
            mem.append("19.5.3.4 (contorno C″): não verificado — falta o perímetro u″.")
        else:
            u2 = _positivo(u_C2l_cm, "u″", "19.5.3.4")
            k1 = k2 = W1 = W2 = None
            if M1 > 0 or M2 > 0:
                if Wp_C2l_cm2 is None:
                    raise ValueError("Com momento, C″ exige Wp_C2l_cm2 = (Wp″ plano 1, Wp″ plano 2).")
                W1, W2 = Wp_C2l_cm2
                if circular:
                    k1 = K_CIRCULAR
                elif t == "borda":
                    k1 = K(c1_cm / c2_cm, interpolar_K) if M1 > 0 else None
                    k2 = K(c2_cm / (2.0 * c1_cm), interpolar_K) if M2 > 0 else None
                else:
                    k1 = K(c1_cm / c2_cm, interpolar_K) if M1 > 0 else None
                    k2 = K(c2_cm / c1_cm, interpolar_K) if M2 > 0 else None
            if t == "canto" and (M1 > 0 or M2 > 0):
                tau_C2 = max(tau_Sd_mpa(F, u2, d, M1, k1, W1),
                             tau_Sd_mpa(F, u2, d, M2, k2, W2))
            else:
                tau_C2 = tau_Sd_mpa(F, u2, d, M1, k1, W1, M2, k2, W2)
            rd1_C2 = rd1
            mem.append(f"19.5.3.4 (contorno C″): u″ = {_fmt(u2)} cm; τSd = {_fmt(tau_C2)} MPa; "
                       f"τRd1 = {_fmt(rd1_C2)} MPa.")
            s2 = seg.verificar_seguranca(rd1_C2, tau_C2, "τSd x τRd1 (C″)", "19.5.3.4")
            mem.extend(s2.memoria)
            ok_C2 = s2.ok
            status_C2 = "ok" if s2.ok else "não passa: estender a armadura"

    ok = sC.ok and ok_Cl and ok_C2
    if not sC.ok:
        governante = "Contorno C: τSd > τRd2 — compressão diagonal do concreto (19.5.3.1)"
    elif not ok_Cl:
        governante = f"Contorno C′: {status_Cl} (19.5.3.2 e 19.5.3.3)"
    elif not ok_C2:
        governante = f"Contorno C″: {status_C2}"
    else:
        razoes = {"C": tau_C / rd2,
                  "C′": tau_Cl / (rd3 if rd3 is not None else rd1)}
        if tau_C2 is not None:
            razoes["C″"] = tau_C2 / rd1_C2
        g = max(razoes, key=razoes.get)
        governante = f"Contorno {g}: τSd/τRd = {_fmt(razoes[g])}"
    mem.append(f"Resultado: {'passa' if ok else 'não passa'} — {governante}.")
    return ResultadoPuncao(t, d, u0, u, tau_C, rd2, tau_Cl, rd1, armadura_necessaria, rd3,
                           tau_C2, rd1_C2, status_C, status_Cl, status_C2, ok, governante,
                           tuple(mem))


# === P20: punção — casos especiais, robustez e detalhamento ===
# 19.5.2.2 (Wp genérico), 19.5.2.5 (capitel), 19.5.2.6 (reentrância e
# abertura), 19.5.3.4 (disposição até C″), 19.5.3.5 (armadura obrigatória),
# 19.5.4 (colapso progressivo), 19.5.5 (laje protendida), 20.4 (estribos de
# punção) e 21.3.4 c (abertura próxima a pilar). PDF p. 184 a 201.
#
# Geometria em planta: polígonos como sequência de pontos (x, y) em cm, em
# qualquer sentido. O contorno crítico é guardado como uma tupla de "trechos":
#     ("reta", (x0, y0), (x1, y1))
#     ("arco", (xc, yc), r, t0, t1)      ângulos em radianos, t1 > t0 (anti-horário)
# e as integrais (comprimento, Wp) são feitas em forma fechada trecho a trecho.

FATOR_DIST_ABERTURA_D = 8.0          # 19.5.2.6: abertura a menos de 8d do contorno C
S0_MAX_FATOR_D = 0.50                # Figura 19.9: 1º contorno de armadura a <= 0,50d da face
ESP_TANGENCIAL_MAX_FATOR_D = 2.0     # Figura 19.8: linhas radiais a menos de 2d entre si
FRACAO_FSD_ARMADURA_OBRIGATORIA = 0.50   # 19.5.3.5
COEF_COLAPSO_PROGRESSIVO = 1.5       # 19.5.4: fyd·As,ccp >= 1,5·FSd
GAMA_F_COLAPSO_PROGRESSIVO = 1.2     # 19.5.4: FSd pode ser calculado com γf = 1,2
DIVISOR_PHI_ESTRIBO_PUNCAO = 20.0    # 20.4: φ do estribo <= h/20
_TOL_GEO = 1e-9


def _poligono(pontos, nome: str = "polígono") -> tuple[tuple[float, float], ...]:
    """Valida e devolve o polígono em sentido anti-horário, sem ponto repetido no fim."""
    pts = [(float(p[0]), float(p[1])) for p in pontos]
    if len(pts) >= 2 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) <= _TOL_GEO:
        pts = pts[:-1]
    if len(pts) < 3:
        raise ValueError(f"O {nome} precisa de pelo menos 3 vértices.")
    n = len(pts)
    area2 = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    if abs(area2) <= _TOL_GEO:
        raise ValueError(f"O {nome} tem área nula.")
    if area2 < 0.0:
        pts.reverse()
    return tuple(pts)


def _area_centroide(pol) -> tuple[float, tuple[float, float]]:
    n = len(pol)
    a2 = cx = cy = 0.0
    for i in range(n):
        x0, y0 = pol[i]
        x1, y1 = pol[(i + 1) % n]
        cr = x0 * y1 - x1 * y0
        a2 += cr
        cx += (x0 + x1) * cr
        cy += (y0 + y1) * cr
    return a2 / 2.0, (cx / (3.0 * a2), cy / (3.0 * a2))


def centroide_cm(poligono) -> tuple[float, float]:
    """Centro de gravidade da área do polígono (área carregada ou seção do pilar), cm."""
    return _area_centroide(_poligono(poligono))[1]


def poligono_convexo_circunscrito(poligono) -> tuple[tuple[float, float], ...]:
    """Polígono convexo circunscrito ao contorno C (envoltória convexa), 19.5.2.6 (PDF p. 187).

    "Se o contorno C apresentar reentrâncias, o contorno crítico C′ deve ser
    paralelo ao polígono circunscrito ao contorno C (ver Figura 19.6)." Na
    Figura 19.6 o polígono circunscrito ao pilar em L fecha a reentrância com
    uma reta inclinada (a linha tracejada): é a envoltória convexa, e não o
    retângulo envolvente. Devolve os vértices em sentido anti-horário, sem
    vértices colineares.
    """
    pts = sorted(set(_poligono(poligono)))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    inf: list = []
    for p in pts:
        while len(inf) >= 2 and cross(inf[-2], inf[-1], p) <= _TOL_GEO:
            inf.pop()
        inf.append(p)
    sup: list = []
    for p in reversed(pts):
        while len(sup) >= 2 and cross(sup[-2], sup[-1], p) <= _TOL_GEO:
            sup.pop()
        sup.append(p)
    return tuple(inf[:-1] + sup[:-1])


def _trechos_poligono(pol) -> tuple:
    n = len(pol)
    return tuple(("reta", pol[i], pol[(i + 1) % n]) for i in range(n))


def _trechos_paralelos(convexo, r: float, cantos: str = "arco") -> tuple:
    """Contorno paralelo, afastado r, de um polígono convexo anti-horário.

    ``cantos='arco'``: cantos em arco de raio r (o contorno C′ das Figuras
    19.2 e 19.6). ``cantos='retos'``: cantos vivos, no encontro das retas
    paralelas aos lados ("desprezando a curvatura dos cantos", 19.5.2.2).
    """
    if r <= 0.0:
        return _trechos_poligono(convexo)
    n = len(convexo)
    normais = []
    for i in range(n):
        (x0, y0), (x1, y1) = convexo[i], convexo[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0)
        normais.append(((y1 - y0) / L, -(x1 - x0) / L))
    trechos: list = []
    for i in range(n):
        v0, v1 = convexo[i], convexo[(i + 1) % n]
        ni, nj = normais[i], normais[(i + 1) % n]
        trechos.append(("reta", (v0[0] + r * ni[0], v0[1] + r * ni[1]),
                        (v1[0] + r * ni[0], v1[1] + r * ni[1])))
        t0 = math.atan2(ni[1], ni[0])
        dt = (math.atan2(nj[1], nj[0]) - t0) % (2.0 * math.pi)
        if dt <= _TOL_GEO:
            continue
        if cantos == "arco":
            trechos.append(("arco", v1, r, t0, t0 + dt))
        else:
            f = r / (1.0 + ni[0] * nj[0] + ni[1] * nj[1])
            canto = (v1[0] + f * (ni[0] + nj[0]), v1[1] + f * (ni[1] + nj[1]))
            trechos.append(("reta", (v1[0] + r * ni[0], v1[1] + r * ni[1]), canto))
            trechos.append(("reta", canto, (v1[0] + r * nj[0], v1[1] + r * nj[1])))
    return tuple(trechos)


def _comprimento(t) -> float:
    if t[0] == "reta":
        return math.hypot(t[2][0] - t[1][0], t[2][1] - t[1][1])
    return t[2] * (t[4] - t[3])


def _ponto(t, s: float) -> tuple[float, float]:
    if t[0] == "reta":
        return (t[1][0] + s * (t[2][0] - t[1][0]), t[1][1] + s * (t[2][1] - t[1][1]))
    a = t[3] + s * (t[4] - t[3])
    return (t[1][0] + t[2] * math.cos(a), t[1][1] + t[2] * math.sin(a))


def _sub(t, s0: float, s1: float):
    if t[0] == "reta":
        return ("reta", _ponto(t, s0), _ponto(t, s1))
    return ("arco", t[1], t[2], t[3] + s0 * (t[4] - t[3]), t[3] + s1 * (t[4] - t[3]))


def _cortes_raio(t, c, ang: float) -> list[float]:
    """Parâmetros s em (0, 1) onde o raio que parte de c com ângulo ang corta o trecho."""
    w = (math.cos(ang), math.sin(ang))
    out: list[float] = []
    if t[0] == "reta":
        p0, p1 = t[1], t[2]
        den = w[0] * (p1[1] - p0[1]) - w[1] * (p1[0] - p0[0])
        if abs(den) <= _TOL_GEO:
            return out
        num = w[0] * (p0[1] - c[1]) - w[1] * (p0[0] - c[0])
        cand = [-num / den]
    else:
        cc, r, t0, t1 = t[1], t[2], t[3], t[4]
        q = -(w[0] * (cc[1] - c[1]) - w[1] * (cc[0] - c[0])) / r
        if abs(q) > 1.0:
            return out
        base = math.asin(max(-1.0, min(1.0, q)))
        cand = []
        for b in (base, math.pi - base):
            a = ang + b
            a += 2.0 * math.pi * math.ceil((t0 - a) / (2.0 * math.pi))
            while a <= t1:
                cand.append((a - t0) / (t1 - t0))
                a += 2.0 * math.pi
    for s in cand:
        if _TOL_GEO < s < 1.0 - _TOL_GEO:
            p = _ponto(t, s)
            if w[0] * (p[0] - c[0]) + w[1] * (p[1] - c[1]) > 0.0:
                out.append(s)
    return out


def _integral_abs_e(t, p0, nrm) -> float:
    """∫|e|·dℓ sobre o trecho, com e = (p − p0)·nrm (distância ao eixo por p0 perpendicular a nrm)."""
    if t[0] == "reta":
        L = _comprimento(t)
        e0 = (t[1][0] - p0[0]) * nrm[0] + (t[1][1] - p0[1]) * nrm[1]
        e1 = (t[2][0] - p0[0]) * nrm[0] + (t[2][1] - p0[1]) * nrm[1]
        if e0 * e1 >= 0.0:
            return L * (abs(e0) + abs(e1)) / 2.0
        return L * (e0 * e0 + e1 * e1) / (2.0 * (abs(e0) + abs(e1)))
    cc, r, t0, t1 = t[1], t[2], t[3], t[4]
    phi = math.atan2(nrm[1], nrm[0])
    a = (cc[0] - p0[0]) * nrm[0] + (cc[1] - p0[1]) * nrm[1]

    def F(x):  # primitiva de (a + r·cos(x − φ))·r
        return r * (a * x + r * math.sin(x - phi))

    pontos = [t0, t1]
    if abs(a) < r:
        base = math.acos(-a / r)
        for b in (base, -base):
            x = phi + b
            x += 2.0 * math.pi * math.ceil((t0 - x) / (2.0 * math.pi))
            while x < t1:
                if x > t0:
                    pontos.append(x)
                x += 2.0 * math.pi
    pontos.sort()
    return sum(abs(F(b) - F(a_)) for a_, b in zip(pontos, pontos[1:]))


def _intervalo_angular(abertura, c) -> tuple[float, float]:
    """(ângulo inicial, abertura angular) das duas retas por c que tangenciam a abertura."""
    angs = [math.atan2(p[1] - c[1], p[0] - c[0]) for p in abertura]
    a0 = angs[0]
    deltas = [((a - a0 + math.pi) % (2.0 * math.pi)) - math.pi for a in angs]
    lo, hi = min(deltas), max(deltas)
    if hi - lo >= math.pi - 1e-9:
        raise ValueError("O centro de gravidade da área carregada fica dentro (ou no alinhamento) "
                         "da abertura: as retas tangentes de 19.5.2.6 não ficam definidas.")
    return a0 + lo, hi - lo


def _no_intervalo(ang: float, intervalo) -> bool:
    ini, amp = intervalo
    return ((ang - ini) % (2.0 * math.pi)) <= amp + 1e-12


def _dist_ponto_segmento(p, a, b) -> float:
    ax, ay = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + ay * ay
    s = 0.0 if L2 == 0.0 else max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2))
    return math.hypot(p[0] - a[0] - s * ax, p[1] - a[1] - s * ay)


def _segmentos_cruzam(a, b, c, d) -> bool:
    def cr(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    d1, d2, d3, d4 = cr(c, d, a), cr(c, d, b), cr(a, b, c), cr(a, b, d)
    return (d1 * d2 < 0.0) and (d3 * d4 < 0.0)


def _dentro(p, pol) -> bool:
    n = len(pol)
    dentro = False
    for i in range(n):
        (x0, y0), (x1, y1) = pol[i], pol[(i + 1) % n]
        if (y0 > p[1]) != (y1 > p[1]):
            x = x0 + (p[1] - y0) * (x1 - x0) / (y1 - y0)
            if x > p[0]:
                dentro = not dentro
    return dentro


def distancia_poligonos_cm(pol_a, pol_b) -> float:
    """Menor distância entre dois polígonos em planta, cm (0 se se tocam ou se sobrepõem)."""
    a = _poligono(pol_a)
    b = _poligono(pol_b)
    if _dentro(a[0], b) or _dentro(b[0], a):
        return 0.0
    dmin = math.inf
    for i in range(len(a)):
        a0, a1 = a[i], a[(i + 1) % len(a)]
        for j in range(len(b)):
            b0, b1 = b[j], b[(j + 1) % len(b)]
            if _segmentos_cruzam(a0, a1, b0, b1):
                return 0.0
            dmin = min(dmin, _dist_ponto_segmento(a0, b0, b1), _dist_ponto_segmento(a1, b0, b1),
                       _dist_ponto_segmento(b0, a0, a1), _dist_ponto_segmento(b1, a0, a1))
    return dmin


def _excluir_setores(trechos, c, intervalos) -> tuple[tuple, float]:
    """Tira dos trechos o que fica entre as retas tangentes (setores angulares vistos de c)."""
    if not intervalos:
        return tuple(trechos), 0.0
    angs = []
    for ini, amp in intervalos:
        angs += [ini, ini + amp]
    ficam: list = []
    excluido = 0.0
    for t in trechos:
        ss = {0.0, 1.0}
        for a in angs:
            ss.update(_cortes_raio(t, c, a))
        ss = sorted(ss)
        for s0, s1 in zip(ss, ss[1:]):
            if s1 - s0 <= 1e-14:
                continue
            pedaco = _sub(t, s0, s1)
            pm = _ponto(t, (s0 + s1) / 2.0)
            ang = math.atan2(pm[1] - c[1], pm[0] - c[0])
            if any(_no_intervalo(ang, iv) for iv in intervalos):
                excluido += _comprimento(pedaco)
            else:
                ficam.append(pedaco)
    return tuple(ficam), excluido


@dataclass(frozen=True)
class ContornoCritico:
    """Contorno crítico em planta (19.5.2.2 e 19.5.2.6): trechos, perímetro e aberturas descontadas."""

    contorno: str                      # 'C', 'Cl' (C′) ou 'r' (afastamento qualquer)
    afastamento_cm: float
    u_total_cm: float                  # perímetro sem desconto de abertura
    u_cm: float                        # perímetro efetivo (descontadas as aberturas)
    u_excluido_cm: float
    centro_cm: tuple[float, float]     # CG da área carregada
    reentrancia: bool                  # C tinha reentrância (usou-se a envoltória convexa)
    aberturas_consideradas: tuple[int, ...]   # índices das aberturas a menos de 8d de C
    distancias_aberturas_cm: tuple[float, ...]
    trechos: tuple
    memoria: tuple[str, ...]


def contorno_critico(poligono, d_cm: float, contorno: str = "Cl", aberturas=(),
                     afastamento_cm: float | None = None, cantos: str = "arco",
                     centro=None) -> ContornoCritico:
    """Contorno crítico C ou C′ de área carregada de forma qualquer, com reentrância e aberturas (19.5.2.6, PDF p. 187-188).

    - Contorno C: o próprio perímetro da área carregada (u0), mesmo com
      reentrância.
    - Contorno C′: paralelo, a 2d, ao polígono convexo circunscrito a C
      (``poligono_convexo_circunscrito``), com cantos em arco de raio 2d
      (Figuras 19.2 e 19.6). ``afastamento_cm`` troca 2d por outro afastamento
      (C1′ de capitel, C″ depois da armadura).
    - Aberturas: "se na laje existir abertura situada a menos de 8d do
      contorno C, não pode ser considerado o trecho do contorno crítico C′
      entre as duas retas que passam pelo centro de gravidade da área de
      aplicação da força e que tangenciam o contorno da abertura"
      (Figura 19.7). A distância é a menor distância entre o polígono da
      abertura e o de C; a menos de 8d (desigualdade estrita) a abertura conta,
      a 8d exatos não. O desconto é aplicado a C′ e aos contornos com
      afastamento; o contorno C não é descontado (a norma só fala em C′).

    Polígonos em cm, pontos (x, y), em qualquer sentido; ``aberturas`` é uma
    sequência de polígonos. ``centro`` = CG da área carregada (padrão: o CG do
    polígono). ``cantos='retos'`` despreza a curvatura dos cantos.
    """
    d = _positivo(d_cm, "d", "19.5.2")
    pol = _poligono(poligono, "polígono da área carregada")
    if cantos not in ("arco", "retos"):
        raise ValueError("cantos deve ser 'arco' ou 'retos'.")
    a_pol, c_pol = _area_centroide(pol)
    c = (float(centro[0]), float(centro[1])) if centro is not None else c_pol
    conv = poligono_convexo_circunscrito(pol)
    reentr = abs(_area_centroide(conv)[0] - a_pol) > 1e-9 * abs(a_pol)
    if afastamento_cm is not None:
        r = _nao_negativo(afastamento_cm, "afastamento", "19.5.2")
        nome = "r"
    else:
        nome = _contorno(contorno)
        r = _afastamento_cm(d, nome)
    mem: list[str] = []
    if r == 0.0:
        trechos = _trechos_poligono(pol)
        mem.append("Contorno C: perímetro da área carregada (u0).")
    else:
        trechos = _trechos_paralelos(conv, r, cantos)
        if reentr:
            mem.append("19.5.2.6: o contorno C tem reentrância; o contorno crítico é paralelo ao "
                       "polígono convexo circunscrito a C (Figura 19.6).")
        mem.append(f"Contorno afastado {_fmt(r)} cm do polígono convexo circunscrito a C, cantos "
                   + (f"em arco de raio {_fmt(r)} cm." if cantos == "arco" else "retos."))
    u_tot = sum(_comprimento(t) for t in trechos)
    consid: list[int] = []
    dists: list[float] = []
    intervalos = []
    lim = FATOR_DIST_ABERTURA_D * d
    for i, ab in enumerate(aberturas):
        abp = _poligono(ab, f"polígono da abertura {i + 1}")
        dist = distancia_poligonos_cm(pol, abp)
        dists.append(dist)
        if dist < lim * (1.0 - 1e-12):
            consid.append(i)
            intervalos.append(_intervalo_angular(poligono_convexo_circunscrito(abp), c))
            mem.append(f"19.5.2.6: abertura {i + 1} a {_fmt(dist)} cm de C, menos que 8d = "
                       f"{_fmt(lim)} cm; o trecho entre as retas tangentes pelo CG da área "
                       f"carregada ({_fmt(c[0])}; {_fmt(c[1])}) não é considerado.")
        else:
            mem.append(f"19.5.2.6: abertura {i + 1} a {_fmt(dist)} cm de C, não menos que 8d = "
                       f"{_fmt(lim)} cm; não reduz o contorno crítico.")
    excl = 0.0
    if intervalos:
        if r > 0.0:
            trechos, excl = _excluir_setores(trechos, c, intervalos)
        else:
            mem.append("Contorno C: a norma só manda descontar a abertura do contorno C′; "
                       "u0 fica inteiro.")
    u = u_tot - excl
    mem.append(f"u = {_fmt(u_tot)} cm" + (f" − {_fmt(excl)} cm (aberturas) = {_fmt(u)} cm."
                                         if excl > 0.0 else "."))
    return ContornoCritico(nome, r, u_tot, u, excl, c, reentr, tuple(consid), tuple(dists),
                           trechos, tuple(mem))


def perimetro_com_reentrancia_cm(poligono, d_cm: float, contorno: str = "Cl") -> float:
    """Perímetro u0 (C) ou u (C′) de área carregada com reentrâncias, cm (19.5.2.6, Figura 19.6, PDF p. 187).

    C′ é paralelo, a 2d, ao polígono convexo circunscrito a C, com cantos em
    arco: u = perímetro da envoltória convexa + 2·π·2d. Em C (u0) vale o
    perímetro real do polígono. Sem reentrância, reproduz os perímetros de
    ``perimetro_critico_cm``.
    """
    return contorno_critico(poligono, d_cm, contorno).u_cm


def perimetro_com_abertura(poligono, d_cm: float, aberturas, contorno: str = "Cl",
                           centro=None) -> ContornoCritico:
    """Contorno C′ descontado das aberturas a menos de 8d de C (19.5.2.6, Figura 19.7, PDF p. 187-188).

    Atalho de ``contorno_critico`` com as aberturas. O perímetro efetivo está
    em ``.u_cm`` e o descontado em ``.u_excluido_cm``; abertura a 8d ou mais
    do contorno C não desconta nada.
    """
    return contorno_critico(poligono, d_cm, contorno, aberturas=aberturas, centro=centro)


def Wp_generico_cm2(poligono, d_cm: float, direcao_excentricidade_graus: float = 0.0,
                    contorno: str = "Cl", aberturas=(), afastamento_cm: float | None = None,
                    cantos: str = "arco", centro=None) -> float:
    """Wp = ∫|e|·dℓ ao longo do perímetro crítico, para área carregada de forma qualquer, cm² (19.5.2.2, PDF p. 184).

        Wp = ∫₀ᵘ |e| dℓ

    dℓ é o comprimento infinitesimal no perímetro crítico u e e a distância de
    dℓ ao eixo que passa pelo centro do pilar e sobre o qual atua o momento
    MSd. ``direcao_excentricidade_graus`` é a direção da excentricidade da
    força (a de C1 na Tabela 19.2), medida do eixo x; o eixo do momento é
    perpendicular a ela e passa por ``centro`` (padrão: CG do polígono).

    A integral é feita em forma fechada, trecho a trecho, sobre o contorno de
    ``contorno_critico`` (C′ paralelo ao polígono convexo circunscrito, com
    cantos em arco de raio 2d; C com o perímetro do polígono). Reproduz as
    expressões fechadas de 19.5.2.2: Wp = C1²/2 + C1·C2 + 4·C2·d + 16·d² +
    2·π·d·C1 no retângulo e (D + 4d)² no círculo (este como limite do
    polígono regular inscrito). ``cantos='retos'`` faz o que a norma permite
    ("desprezando a curvatura dos cantos do perímetro crítico").

    Com ``aberturas``, a integral é feita só sobre o perímetro efetivo (sem os
    trechos descontados por 19.5.2.6): a norma define Wp sobre o perímetro
    crítico u, e u é o perímetro efetivo — leitura da biblioteca.
    """
    cont = contorno_critico(poligono, d_cm, contorno, aberturas, afastamento_cm, cantos, centro)
    a = math.radians(float(direcao_excentricidade_graus))
    nrm = (math.cos(a), math.sin(a))
    return sum(_integral_abs_e(t, cont.centro_cm, nrm) for t in cont.trechos)


def _retangulo(c1_cm: float, c2_cm: float) -> tuple[tuple[float, float], ...]:
    """Retângulo C1 (em x) por C2 (em y), centrado na origem."""
    a, b = float(c1_cm) / 2.0, float(c2_cm) / 2.0
    return ((-a, -b), (a, -b), (a, b), (-a, b))


# ---------------------------------------------------------------------------
# 19.5.2.5 — Capitel (Figura 19.5, PDF p. 186-187)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ContornosCapitel:
    """Contornos a verificar com capitel (19.5.2.5, Figura 19.5)."""

    caso: str
    verificar_C1l: bool
    verificar_C2l: bool
    afastamento_C1l_cm: float          # 2·dc, medido da face do pilar
    afastamento_C2l_cm: float          # lc + 2d, medido da face do pilar
    u_C1l_cm: float | None
    u_C2l_cm: float | None
    d_C1l_cm: float | None             # da
    d_C2l_cm: float                    # d
    memoria: tuple[str, ...]


def contornos_capitel(lc_cm: float, d_cm: float, dc_cm: float, da_cm: float | None = None,
                      c1_cm: float | None = None, c2_cm: float | None = None) -> ContornosCapitel:
    """Quais contornos críticos verificar quando existe capitel, e onde ficam (19.5.2.5, Figura 19.5, PDF p. 186-187).

        lc <= 2·(dc − d)          ⇒ basta verificar o contorno C2′;
        2·(dc − d) < lc <= 2·dc   ⇒ basta verificar o contorno C1′;
        lc > 2·dc                 ⇒ é necessário verificar C1′ e C2′.

    d = altura útil da laje no contorno C2′; dc = altura útil da laje na face
    do pilar; da = altura útil da laje no contorno C1′; lc = distância entre a
    borda do capitel e a face do pilar (cm).

    Posição dos contornos (Figura 19.5, retas 2:1): C1′ fica a 2·dc da face
    do pilar (a reta 2:1 que parte do pé do pilar, na profundidade dc) e C2′
    a 2d da borda do capitel, isto é, a lc + 2d da face do pilar. Com
    ``c1_cm`` e ``c2_cm`` (pilar interno retangular, capitel com a mesma aba
    lc nas quatro faces e borda retangular — leitura da biblioteca) a função
    dá os perímetros, com cantos em arco:

        u(C1′) = 2·(C1 + C2) + 2·π·(2·dc)
        u(C2′) = 2·(C1 + C2 + 4·lc) + 2·π·(2d)

    Em cada contorno, a verificação de 19.5.2 e 19.5.3.2 usa a altura útil
    dele (da em C1′, d em C2′). ``da_cm`` é exigido quando C1′ precisa ser
    verificado (depende da forma do capitel). Com lc = 0 o capitel some e o
    resultado é o caso comum: só C2′, a 2d da face, com u de
    ``perimetro_critico_cm``.
    """
    lc = _nao_negativo(lc_cm, "lc", "19.5.2.5")
    d = _positivo(d_cm, "d", "19.5.2.5")
    dc = _positivo(dc_cm, "dc", "19.5.2.5")
    if dc < d:
        raise FaixaNormativaError(f"dc = {dc:g} cm menor que d = {d:g} cm: com capitel a altura útil "
                                  "na face do pilar não é menor que a da laje (19.5.2.5).")
    lim1 = 2.0 * (dc - d)
    lim2 = 2.0 * dc
    tol = 1e-12 * max(1.0, lim2)
    if lc <= lim1 + tol:
        caso = f"lc = {_fmt(lc)} cm <= 2·(dc − d) = {_fmt(lim1)} cm: basta verificar C2′"
        v1, v2 = False, True
    elif lc <= lim2 + tol:
        caso = (f"2·(dc − d) = {_fmt(lim1)} cm < lc = {_fmt(lc)} cm <= 2·dc = {_fmt(lim2)} cm: "
                "basta verificar C1′")
        v1, v2 = True, False
    else:
        caso = f"lc = {_fmt(lc)} cm > 2·dc = {_fmt(lim2)} cm: verificar C1′ e C2′"
        v1, v2 = True, True
    da = None
    if v1 and da_cm is None:
        raise ValueError("C1′ precisa ser verificado: informe da_cm, a altura útil no contorno C1′ "
                         "(19.5.2.5, Figura 19.5).")
    if da_cm is not None:
        da = _positivo(da_cm, "da", "19.5.2.5")
    r1, r2 = 2.0 * dc, lc + 2.0 * d
    u1 = u2 = None
    if c1_cm is not None and c2_cm is not None:
        c1 = _positivo(c1_cm, "C1", "19.5.2.5")
        c2 = _positivo(c2_cm, "C2", "19.5.2.5")
        u1 = 2.0 * (c1 + c2) + 2.0 * math.pi * r1
        u2 = 2.0 * (c1 + c2 + 4.0 * lc) + 2.0 * math.pi * 2.0 * d
    mem = [f"19.5.2.5 (capitel): {caso}.",
           f"C1′ a 2·dc = {_fmt(r1)} cm da face do pilar (altura útil da); "
           f"C2′ a lc + 2d = {_fmt(r2)} cm da face do pilar (altura útil d = {_fmt(d)} cm)."]
    if u1 is not None:
        mem.append(f"u(C1′) = 2·(C1 + C2) + 2·π·2dc = {_fmt(u1)} cm; "
                   f"u(C2′) = 2·(C1 + C2 + 4·lc) + 2·π·2d = {_fmt(u2)} cm.")
    return ContornosCapitel(caso, v1, v2, r1, r2, u1 if v1 else None, u2 if v2 else None,
                            da, d, tuple(mem))


# ---------------------------------------------------------------------------
# 19.5.3.4 — Disposição da armadura de punção e contorno C″ (Figuras 19.8 e 19.9, PDF p. 190)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DisposicaoArmaduraPuncao:
    """Disposição radial da armadura de punção até o contorno C″ (19.5.3.4)."""

    s0_cm: float
    sr_cm: float
    n_contornos: int
    raios_contornos_cm: tuple[float, ...]      # distância de cada contorno de armadura à face
    afastamento_C2l_cm: float                  # distância de C″ à face do pilar
    u_C2l_cm: float
    Wp_C2l_cm2: tuple[float, float]            # (plano 1, plano 2); 0 quando não há momento
    tau_Sd_C2l_mpa: float
    tau_Rd1_mpa: float
    espacamento_tangencial_cm: float | None
    ok: bool
    governante: str
    memoria: tuple[str, ...]
    arranjo_C2l: str = "inteiro"               # T2: "inteiro" ou "cruz" (traçado de C″ usado)


def disposicao_armadura_puncao(FSd_kn: float, c1_cm: float, c2_cm: float, d_cm: float,
                               tau_Rd1_mpa: float, sr_cm: float, s0_cm: float | None = None,
                               MSd1_kncm: float = 0.0, MSd2_kncm: float = 0.0,
                               n_linhas_radiais: int | None = None, n_min_contornos: int = 1,
                               interpolar_K: bool = True,
                               n_max_contornos: int = 200,
                               arranjo: str = "radial") -> DisposicaoArmaduraPuncao:
    """Número de contornos de armadura de punção até C″ satisfazer τSd <= τRd1 (19.5.3.4, Figuras 19.8 e 19.9, PDF p. 190-191).

    "Quando for necessário utilizar armadura transversal, ela deve ser
    estendida em contornos paralelos a C′ até que, em um contorno C″
    afastado 2d do último contorno de armadura, não seja mais necessária
    armadura, isto é, τSd <= τRd1."

    Pilar interno retangular (C1 no plano de MSd1, C2 no plano de MSd2).
    Figura 19.9 (corte): 1º contorno a s0 <= 0,50·d da face do pilar
    (padrão s0 = 0,50·d); contornos seguintes a sr <= 0,75·d entre si. O
    contorno de armadura n fica a rn = s0 + (n − 1)·sr da face, e C″ a
    rn + 2d, com cantos em arco:

        u″ = 2·(C1 + C2) + 2·π·(rn + 2d)
        τSd″ = FSd/(u″·d) + K1·MSd1/(Wp1″·d) + K2·MSd2/(Wp2″·d)

    Wp″ por ``Wp_generico_cm2`` (integral sobre u″) e K da Tabela 19.2 como
    em C′. ``tau_Rd1_mpa`` é o τRd1 de 19.5.3.2 (``tau_Rd1_mpa``). A função
    devolve o menor n (>= ``n_min_contornos``) que satisfaz C″.

    Figura 19.8 (planta): o contorno C″ inteiro só vale com as linhas radiais
    a menos de 2d entre si no último contorno de armadura. Com
    ``n_linhas_radiais``, a função toma o espaçamento tangencial médio
    u(rn)/n_linhas (linhas distribuídas por igual ao longo do contorno de
    armadura) e, se não for menor que 2d, o contorno C″ inteiro não vale:
    vale o perímetro reduzido da Figura 19.8 (direita), o da armadura em
    cruz. Com ``arranjo='cruz'``, a armadura é tomada em cruz desde o início.

    A Figura 19.8 (à direita) não dá uma regra analítica para esse contorno
    reduzido: as duas cotas desenhadas (“> 2d” no braço, “d” entre a última
    linha de conectores e o arco) são só ilustrativas — a Figura não diz onde
    ao longo de cada braço o trecho reto termina nem onde exatamente entra o
    arco de concordância nem qual é o raio dele nos cantos entre braços, ao
    contrário da Figura 19.9, que dá ≤ 0,75d e ≤ 0,50d como regra numérica.
    Por isso o traçado não sai da norma: a NBR 6118 não dá a regra numérica
    (Figura 19.8); a construção é a do programa de punção do escritório
    (BRGTools, porte do LPUNC), adotada por decisão do engenheiro em
    21/09/2026 (pacote T2; antes, no fechamento F3, a função não traçava esse
    contorno, só sinalizava ``ok = False`` e pedia u″ à parte). u″ e Wp″ saem
    de ``u_C2l_cruz_cm`` e ``Wp_C2l_cruz_cm2`` (pilar interno, b = C1,
    h = C2), contorno a contorno, e o campo ``arranjo_C2l`` diz qual traçado
    ficou no resultado. Na cruz, u″ não cresce com o número de contornos (só
    ganha os trechos retos de d quando o último contorno passa de 2d da
    face): se C″ não passa, estender a armadura não resolve, e a busca para
    no limite ``n_max_contornos`` com ``ok = False``. Pilar de borda e de
    canto: use ``u_C2l_cruz_cm`` (ou calcule u″ à parte) e
    ``verificar_puncao``.
    """
    F = _nao_negativo(FSd_kn, "FSd", "19.5.3.4")
    c1 = _positivo(c1_cm, "C1", "19.5.3.4")
    c2 = _positivo(c2_cm, "C2", "19.5.3.4")
    d = _positivo(d_cm, "d", "19.5.3.4")
    rd1 = _positivo(tau_Rd1_mpa, "τRd1", "19.5.3.4")
    sr = _positivo(sr_cm, "sr", "19.5.3.4")
    s0 = S0_MAX_FATOR_D * d if s0_cm is None else _positivo(s0_cm, "s0", "19.5.3.4")
    if s0 > S0_MAX_FATOR_D * d * (1.0 + 1e-12):
        raise FaixaNormativaError(f"s0 = {s0:g} cm maior que 0,50·d = {S0_MAX_FATOR_D * d:g} cm "
                                  "(Figura 19.9).")
    if sr > SR_MAX_FATOR_D * d * (1.0 + 1e-12):
        raise FaixaNormativaError(f"sr = {sr:g} cm maior que 0,75·d = {SR_MAX_FATOR_D * d:g} cm "
                                  "(19.5.3.3 e Figura 19.9).")
    M1, M2 = abs(float(MSd1_kncm)), abs(float(MSd2_kncm))
    k1 = K(c1 / c2, interpolar_K) if M1 > 0.0 else None
    k2 = K(c2 / c1, interpolar_K) if M2 > 0.0 else None
    pol = _retangulo(c1, c2)
    arr = str(arranjo).strip().lower()
    if arr not in ("radial", "cruz"):
        raise ValueError("arranjo deve ser 'radial' ou 'cruz'.")
    nl = None
    if n_linhas_radiais is not None:
        nl = int(n_linhas_radiais)
        if nl < 1:
            raise ValueError("n_linhas_radiais tem de ser positivo.")
    lim = ESP_TANGENCIAL_MAX_FATOR_D * d
    n = max(1, int(n_min_contornos))
    sem_saida = False
    while True:
        rn = s0 + (n - 1) * sr
        r2 = rn + 2.0 * d
        st = None if nl is None else (2.0 * (c1 + c2) + 2.0 * math.pi * rn) / nl
        cruz = arr == "cruz" or (st is not None and st >= lim)
        if cruz:   # T2: Figura 19.8 (à direita), construção do BRGTools
            u2 = u_C2l_cruz_cm(c1, c2, d, r2, "interno")
            W1 = Wp_C2l_cruz_cm2(c1, c2, d, r2, "interno", None, None, 0.0) if M1 > 0.0 else 0.0
            W2 = Wp_C2l_cruz_cm2(c1, c2, d, r2, "interno", None, None, 90.0) if M2 > 0.0 else 0.0
        else:
            u2 = 2.0 * (c1 + c2) + 2.0 * math.pi * r2
            W1 = Wp_generico_cm2(pol, d, 0.0, afastamento_cm=r2) if M1 > 0.0 else 0.0
            W2 = Wp_generico_cm2(pol, d, 90.0, afastamento_cm=r2) if M2 > 0.0 else 0.0
        tau2 = tau_Sd_mpa(F, u2, d, M1, k1, W1 or None, M2, k2, W2 or None)
        if seg.verificar_seguranca(rd1, tau2).ok or n >= n_max_contornos:
            break
        # Na cruz, com o último contorno além de 2d, u″ não cresce mais: se só a
        # parcela FSd/(u″·d) já passa de τRd1, estender a armadura não resolve
        # (é a parada do BRGTools/LPUNC no ramo em cruz).
        sem_saida = cruz and rn > 2.0 * d + _TOL_GEO and F / (u2 * d) * 10.0 > rd1
        if sem_saida:
            break
        n += 1
    s_final = seg.verificar_seguranca(rd1, tau2, "τSd x τRd1 (C″)", "19.5.3.4")
    raios = tuple(s0 + i * sr for i in range(n))
    mem = [f"19.5.3.4 (Figura 19.9): s0 = {_fmt(s0)} cm (<= 0,50d = {_fmt(0.5 * d)} cm), "
           f"sr = {_fmt(sr)} cm (<= 0,75d = {_fmt(0.75 * d)} cm).",
           f"{n} contorno(s) de armadura; o último a {_fmt(raios[-1])} cm da face; C″ a "
           f"{_fmt(r2)} cm da face (2d além do último contorno)."]
    if st is not None:
        if st < lim:
            mem.append(f"Figura 19.8: espaçamento entre linhas radiais no último contorno = "
                       f"{_fmt(st)} cm < 2d = {_fmt(lim)} cm; C″ é o contorno inteiro.")
        else:
            mem.append(f"Figura 19.8: linhas radiais a {_fmt(st)} cm >= 2d = {_fmt(lim)} cm no "
                       "último contorno; o contorno C″ inteiro não vale: vale o perímetro reduzido "
                       "da armadura em cruz (Figura 19.8, à direita).")
    if cruz:
        r6 = c1 / math.sqrt(2.0) + 2.0 * d
        r8 = c2 / math.sqrt(2.0) + 2.0 * d
        retas = rn > 2.0 * d + _TOL_GEO
        mem.append(f"C″ em cruz — {FONTE_C2L_CRUZ}: arcos de 90° entre os braços, r6 = C1/√2 + 2d = "
                   f"{_fmt(r6)} cm e r8 = C2/√2 + 2d = {_fmt(r8)} cm"
                   + (f", mais 8 trechos retos de d = {_fmt(d)} cm (último contorno a mais de 2d "
                      "da face)" if retas else " (sem trechos retos: último contorno a até 2d da face)")
                   + ".")
        mem.append(f"u″ = π·(r6 + r8){' + 8·d' if retas else ''} = {_fmt(u2)} cm"
                   + (f"; Wp1″ = {_fmt(W1)} cm²" if W1 else "") + (f"; Wp2″ = {_fmt(W2)} cm²" if W2 else "")
                   + f"; τSd″ = {_fmt(tau2)} MPa; τRd1 = {_fmt(rd1)} MPa.")
    else:
        mem.append(f"u″ = 2·(C1 + C2) + 2·π·{_fmt(r2)} = {_fmt(u2)} cm; τSd″ = {_fmt(tau2)} MPa; "
                   f"τRd1 = {_fmt(rd1)} MPa.")
    mem.extend(s_final.memoria)
    ok = s_final.ok
    rotulo = "C″ em cruz" if cruz else "C″"
    if ok:
        governante = f"{rotulo}: τSd <= τRd1"
    elif sem_saida:
        governante = (f"{rotulo} não passa: FSd/(u″·d) = {_fmt(F / (u2 * d) * 10.0)} MPa > τRd1, e na "
                      "cruz u″ não cresce com mais contornos (aumente a seção do pilar ou o d, ou "
                      "use linhas radiais a menos de 2d)")
    else:
        governante = f"{rotulo} não passa com {n_max_contornos} contornos (limite de busca)"
    mem.append(f"Resultado: {'passa' if ok else 'não passa'} — {governante}.")
    return DisposicaoArmaduraPuncao(s0, sr, n, raios, r2, u2, (W1, W2), tau2, rd1, st, ok,
                                    governante, tuple(mem), "cruz" if cruz else "inteiro")


# ---------------------------------------------------------------------------
# 19.5.3.5 — Armadura de punção obrigatória (PDF p. 191)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoArmaduraObrigatoria:
    """Armadura de punção obrigatória quando a estabilidade global depende da laje (19.5.3.5)."""

    exigida: bool
    F_min_kn: float
    fywd_mpa: float
    Asw_min_cm2: float
    Asw_cm2: float | None
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def armadura_puncao_obrigatoria(FSd_kn: float, fywd_mpa: float, estabilidade_depende: bool = True,
                                alpha_graus: float = 90.0, tipo_armadura: str = "studs",
                                h_cm: float | None = None,
                                Asw_cm2: float | None = None) -> ResultadoArmaduraObrigatoria:
    """Armadura de punção mínima por robustez: equilibrar 50 % de FSd (19.5.3.5, PDF p. 191).

    "No caso de a estabilidade global da estrutura depender da resistência
    da laje à punção, deve ser prevista armadura de punção, mesmo que τSd
    seja menor que τRd1. Essa armadura deve equilibrar um mínimo de 50 % de
    FSd."

        Asw·fywd·sen α >= 0,50·FSd   ⇒   Asw,min = 0,50·FSd/(fywd·sen α)

    Asw é a área total da armadura de punção que atravessa a superfície de
    ruptura (leitura da biblioteca; a norma diz só "essa armadura"), cm²;
    fywd em MPa, limitado como em 19.5.3.3 (``fywd_max_puncao_mpa``); a
    conta converte fywd para kN/cm² (÷ 10). Com ``estabilidade_depende=False``
    a exigência não se aplica (``exigida = False``, ``ok = True``).
    """
    F = _nao_negativo(FSd_kn, "FSd", "19.5.3.5")
    a = float(alpha_graus)
    if not (0.0 < a <= 90.0):
        raise FaixaNormativaError(f"α = {a:g}° fora de (0°, 90°] (19.5.3.3).")
    fy = min(_positivo(fywd_mpa, "fywd", "19.5.3.5"), fywd_max_puncao_mpa(tipo_armadura, h_cm))
    Fmin = FRACAO_FSD_ARMADURA_OBRIGATORIA * F
    Amin = Fmin / (nbr.mpa_para_kncm2(fy) * math.sin(math.radians(a)))
    mem = [f"19.5.3.5: 0,50·FSd = {_fmt(Fmin)} kN; Asw,min = 0,50·FSd/(fywd·sen α) = "
           f"{_fmt(Amin)} cm² (fywd = {_fmt(fy)} MPa, α = {_fmt(a)}°)."]
    if not estabilidade_depende:
        mem.append("A estabilidade global não depende da punção da laje: armadura obrigatória "
                   "não exigida.")
        return ResultadoArmaduraObrigatoria(False, Fmin, fy, Amin, Asw_cm2, True,
                                            "19.5.3.5 não se aplica", tuple(mem))
    if Asw_cm2 is None:
        mem.append("Armadura adotada não informada.")
        return ResultadoArmaduraObrigatoria(True, Fmin, fy, Amin, None, False,
                                            f"19.5.3.5: prever Asw >= {_fmt(Amin)} cm²", tuple(mem))
    Asw = _nao_negativo(Asw_cm2, "Asw", "19.5.3.5")
    Rd = Asw * nbr.mpa_para_kncm2(fy) * math.sin(math.radians(a))
    s = seg.verificar_seguranca(Rd, Fmin, "Asw·fywd·sen α x 0,50·FSd", "19.5.3.5")
    mem.extend(s.memoria)
    gov = (f"19.5.3.5: Asw = {_fmt(Asw)} cm² equilibra {_fmt(Rd)} kN >= 0,50·FSd" if s.ok else
           f"19.5.3.5: Asw = {_fmt(Asw)} cm² < {_fmt(Amin)} cm² — não equilibra 50 % de FSd")
    return ResultadoArmaduraObrigatoria(True, Fmin, fy, Amin, Asw, s.ok, gov, tuple(mem))


# ---------------------------------------------------------------------------
# 19.5.4 — Colapso progressivo (PDF p. 191)
# ---------------------------------------------------------------------------
def FSd_colapso_progressivo_kn(Fk_kn: float, gama_f: float = GAMA_F_COLAPSO_PROGRESSIVO) -> float:
    """FSd para 19.5.4, que "pode ser calculado com γf igual a 1,2" (PDF p. 191): FSd = γf·Fk, kN."""
    return _positivo(gama_f, "γf", "19.5.4") * _nao_negativo(Fk_kn, "Fk", "19.5.4")


def As_colapso_progressivo_cm2(FSd_kn: float, fyk_mpa: float = 500.0,
                               gama_s: float = nbr.GAMA_S) -> float:
    """As,ccp mínima contra o colapso progressivo, cm² (19.5.4, Figura 19.10, PDF p. 191).

        fyd·As,ccp >= 1,5·FSd   ⇒   As,ccp,min = 1,5·FSd/fyd

    As,ccp é o somatório de todas as áreas das barras inferiores que cruzam
    cada uma das faces do pilar (as quatro faces somadas), ancoradas além do
    contorno C′ (ou C″, quando há armadura de punção). FSd em kN (pode ser
    calculado com γf = 1,2: ``FSd_colapso_progressivo_kn``); fyd =
    fyk/γs (``nucleo.fyd``) em MPa, convertido a kN/cm² (÷ 10).
    """
    F = _nao_negativo(FSd_kn, "FSd", "19.5.4")
    return COEF_COLAPSO_PROGRESSIVO * F / nbr.mpa_para_kncm2(nbr.fyd(fyk_mpa, gama_s))


@dataclass(frozen=True)
class ResultadoColapsoProgressivo:
    """Verificação da armadura contra colapso progressivo (19.5.4)."""

    FSd_kn: float
    fyd_mpa: float
    As_ccp_cm2: float
    As_ccp_min_cm2: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_colapso_progressivo(FSd_kn: float, As_ccp_cm2: float, fyk_mpa: float = 500.0,
                                  gama_s: float = nbr.GAMA_S) -> ResultadoColapsoProgressivo:
    """Verifica fyd·As,ccp >= 1,5·FSd (19.5.4, PDF p. 191). Unidades como em ``As_colapso_progressivo_cm2``."""
    F = _nao_negativo(FSd_kn, "FSd", "19.5.4")
    As = _nao_negativo(As_ccp_cm2, "As,ccp", "19.5.4")
    fyd = nbr.fyd(fyk_mpa, gama_s)
    Amin = As_colapso_progressivo_cm2(F, fyk_mpa, gama_s)
    Rd = nbr.mpa_para_kncm2(fyd) * As
    s = seg.verificar_seguranca(Rd, COEF_COLAPSO_PROGRESSIVO * F, "fyd·As,ccp x 1,5·FSd", "19.5.4")
    mem = [f"19.5.4: fyd = {_fmt(fyd)} MPa; As,ccp = {_fmt(As)} cm² (barras inferiores que cruzam "
           f"as faces do pilar); As,ccp,min = 1,5·FSd/fyd = {_fmt(Amin)} cm²."]
    mem.extend(s.memoria)
    gov = ("19.5.4: fyd·As,ccp >= 1,5·FSd" if s.ok else
           f"19.5.4: As,ccp = {_fmt(As)} cm² < {_fmt(Amin)} cm²")
    return ResultadoColapsoProgressivo(F, fyd, As, Amin, s.ok, gov, tuple(mem))


# ---------------------------------------------------------------------------
# 19.5.5 — Elementos protendidos (Figura 19.11, PDF p. 191-192)
# ---------------------------------------------------------------------------
def tau_Pd_mpa(cabos, u_cm: float, d_cm: float) -> float:
    """Tensão devida aos cabos inclinados, τPd = Σ Pk,inf,i·sen αi/(u·d), MPa (19.5.5, PDF p. 191-192).

    ``cabos``: sequência de (Pk,inf,i em kN, αi em graus) ou de
    (Pk,inf,i, αi, distância do cabo à face do pilar em cm). Pk,inf,i é a
    força de protensão no cabo i; αi a inclinação do cabo em relação ao plano
    da laje no contorno considerado (0 <= α <= 90°); u o perímetro crítico do
    contorno considerado, cm; d em cm. Só entram os cabos "que atravessam o
    contorno considerado e que passam a menos de d/2 da face do pilar": com a
    distância informada, cabo a d/2 ou mais é ignorado (desigualdade estrita);
    sem ela, o cabo conta. A conta sai em kN/cm² e é multiplicada por 10.
    """
    u = _positivo(u_cm, "u", "19.5.5")
    d = _positivo(d_cm, "d", "19.5.5")
    soma = 0.0
    for cabo in cabos:
        P = _nao_negativo(cabo[0], "Pk,inf", "19.5.5")
        a = float(cabo[1])
        if not (0.0 <= a <= 90.0):
            raise FaixaNormativaError(f"α = {a:g}° fora de [0°, 90°] (19.5.5).")
        if len(cabo) > 2 and cabo[2] is not None:
            dist = _nao_negativo(cabo[2], "distância do cabo à face do pilar", "19.5.5")
            if dist >= d / 2.0:
                continue
        soma += P * math.sin(math.radians(a))
    return soma / (u * d) * 10.0


def tau_Sd_efetivo_protendido_mpa(tau_Sd_mpa_: float, cabos, u_cm: float, d_cm: float) -> float:
    """τSd,ef = τSd − τPd, MPa (19.5.5, PDF p. 191).

    τSd é a tensão solicitante de 19.5.2 no mesmo contorno (mesmo u) e τPd a
    de ``tau_Pd_mpa``. A norma não limita o resultado; valor negativo quer dizer
    que a componente vertical dos cabos supera a solicitação (a verificação
    passa).
    """
    return float(tau_Sd_mpa_) - tau_Pd_mpa(cabos, u_cm, d_cm)


# ---------------------------------------------------------------------------
# 20.4 — Armaduras de punção: estribos (PDF p. 196)
# ---------------------------------------------------------------------------
def phi_max_estribo_puncao_mm(h_cm: float) -> float:
    """Diâmetro máximo do estribo de punção, φ <= h/20, mm (20.4, PDF p. 196).

    "O diâmetro da armadura de estribos não pode superar h/20 da laje." h em
    cm; a conta h/20 sai em cm e é multiplicada por 10 para mm.
    """
    h = _positivo(h_cm, "h", "20.4")
    return h / DIVISOR_PHI_ESTRIBO_PUNCAO * 10.0


@dataclass(frozen=True)
class ResultadoEstriboPuncao:
    """Verificação construtiva dos estribos de punção (20.4)."""

    phi_estribo_mm: float
    phi_longitudinal_mm: float
    phi_max_mm: float | None
    ok_diametro: bool
    ok_contato: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_contato_canto(phi_estribo_mm: float, phi_longitudinal_mm: float,
                            contato_mecanico: bool = True,
                            h_cm: float | None = None) -> ResultadoEstriboPuncao:
    """Estribo de punção: contato com as barras longitudinais nos cantos e diâmetros (20.4, PDF p. 196).

    "Deve haver contato mecânico das barras longitudinais com os cantos dos
    estribos, e estas barras devem possuir pelo menos diâmetro igual ao
    deles": φlongitudinal >= φestribo e ``contato_mecanico`` verdadeiro. Com
    ``h_cm``, confere também φestribo <= h/20 (``phi_max_estribo_puncao_mm``).
    Diâmetros em mm; igualdade passa nos dois limites.
    """
    pe = _positivo(phi_estribo_mm, "φ do estribo", "20.4")
    pl = _positivo(phi_longitudinal_mm, "φ longitudinal", "20.4")
    mem: list[str] = []
    s_long = seg.verificar_seguranca(pl, pe, "φlongitudinal x φestribo", "20.4")
    ok_contato = bool(contato_mecanico) and s_long.ok
    mem.append(f"20.4: φlongitudinal = {_fmt(pl)} mm >= φestribo = {_fmt(pe)} mm -> "
               f"{'ok' if s_long.ok else 'não ok'}; contato mecânico nos cantos: "
               f"{'sim' if contato_mecanico else 'não'}.")
    pmax = None
    ok_d = True
    if h_cm is not None:
        pmax = phi_max_estribo_puncao_mm(h_cm)
        s_d = seg.verificar_seguranca(pmax, pe, "h/20 x φestribo", "20.4")
        ok_d = s_d.ok
        mem.append(f"20.4: φestribo = {_fmt(pe)} mm <= h/20 = {_fmt(pmax)} mm -> "
                   f"{'ok' if ok_d else 'não ok'}.")
    ok = ok_d and ok_contato
    if not ok_d:
        gov = f"20.4: φestribo = {_fmt(pe)} mm > h/20 = {_fmt(pmax)} mm"
    elif not contato_mecanico:
        gov = "20.4: falta contato mecânico das barras longitudinais com os cantos dos estribos"
    elif not s_long.ok:
        gov = f"20.4: φlongitudinal = {_fmt(pl)} mm < φestribo = {_fmt(pe)} mm"
    else:
        gov = "20.4: estribo de punção atende"
    return ResultadoEstriboPuncao(pe, pl, pmax, ok_d, ok_contato, ok, gov, tuple(mem))


# ---------------------------------------------------------------------------
# 21.3.4 c — Abertura próxima a pilar em laje lisa ou cogumelo (PDF p. 201)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoPuncaoAbertura:
    """Punção de pilar interno com abertura próxima (21.3.4 c com 19.5.2.6)."""

    u0_cm: float
    u_total_cm: float
    u_cm: float
    u_excluido_cm: float
    aberturas_consideradas: tuple[int, ...]
    tau_Sd_C_mpa: float
    tau_Rd2_mpa: float
    tau_Sd_Cl_mpa: float
    tau_Rd1_mpa: float
    tau_Rd3_mpa: float | None
    armadura_necessaria: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def puncao_abertura_proxima_pilar(fck_mpa: float, d_cm: float, FSd_kn: float, c1_cm: float,
                                  c2_cm: float, aberturas, MSd1_kncm: float = 0.0,
                                  MSd2_kncm: float = 0.0, rho_x: float = 0.0, rho_y: float = 0.0,
                                  sigma_cp_x_mpa: float = 0.0, sigma_cp_y_mpa: float = 0.0,
                                  Asw_cm2: float | None = None, sr_cm: float | None = None,
                                  fywd_mpa: float | None = None, alpha_graus: float = 90.0,
                                  tipo_armadura: str = "studs", h_cm: float | None = None,
                                  interpolar_K: bool = True,
                                  gama_c: float = nbr.GAMA_C) -> ResultadoPuncaoAbertura:
    """Punção de pilar interno de laje lisa ou cogumelo com abertura próxima (21.3.4 c, PDF p. 201; 19.5.2.6, PDF p. 187-188).

    21.3.4 c: "no caso de aberturas em regiões próximas a pilares, nas lajes
    lisas ou cogumelo, o modelo de cálculo deve prever o equilíbrio das forças
    cortantes atuantes nessas regiões". O modelo adotado é o de 19.5:

    - C′ perde o trecho entre as retas tangentes à abertura que passam pelo
      CG do pilar, para cada abertura a menos de 8d do contorno C
      (``contorno_critico``); Wp1 e Wp2 integrados só sobre o perímetro
      efetivo (``Wp_generico_cm2``);
    - τSd = FSd/(u·d) + K1·MSd1/(Wp1·d) + K2·MSd2/(Wp2·d), K da Tabela 19.2;
    - C: τSd com u0 (sem desconto) <= τRd2, sem a ampliação de 20 %, que a
      norma só admite quando "não existem aberturas junto ao pilar" (19.5.3.1);
    - C′: τSd <= τRd1 ou, com armadura, <= τRd3 com o u efetivo.

    Pilar retangular C1 (x, plano de MSd1) × C2 (y, plano de MSd2), centrado
    na origem; aberturas como polígonos em cm nesse sistema. Sem abertura a
    menos de 8d, C′ fica como em ``verificar_puncao`` com pilar interno.
    """
    d = _positivo(d_cm, "d", "21.3.4")
    F = _nao_negativo(FSd_kn, "FSd", "21.3.4")
    c1 = _positivo(c1_cm, "C1", "21.3.4")
    c2 = _positivo(c2_cm, "C2", "21.3.4")
    M1, M2 = abs(float(MSd1_kncm)), abs(float(MSd2_kncm))
    pol = _retangulo(c1, c2)
    cont = contorno_critico(pol, d, "Cl", aberturas)
    mem = [f"21.3.4 c: pilar interno {_fmt(c1)} × {_fmt(c2)} cm com aberturas próximas; "
           f"d = {_fmt(d)} cm, FSd = {_fmt(F)} kN."]
    mem.extend(cont.memoria)
    k1 = K(c1 / c2, interpolar_K) if M1 > 0.0 else None
    k2 = K(c2 / c1, interpolar_K) if M2 > 0.0 else None
    u0 = perimetro_critico_cm(c1, c2, d, "interno", "C")
    tau_C = tau_Sd_mpa(F, u0, d, M1, k1, Wp_retangular_cm2(c1, c2, d, "C"),
                       M2, k2, Wp_retangular_cm2(c2, c1, d, "C"))
    W1 = Wp_generico_cm2(pol, d, 0.0, "Cl", aberturas) if M1 > 0.0 else None
    W2 = Wp_generico_cm2(pol, d, 90.0, "Cl", aberturas) if M2 > 0.0 else None
    tau_Cl = tau_Sd_mpa(F, cont.u_cm, d, M1, k1, W1, M2, k2, W2)
    rd2 = tau_Rd2_mpa(fck_mpa, gama_c, False)
    mem.append(f"19.5.3.1 (C): u0 = {_fmt(u0)} cm; τSd = {_fmt(tau_C)} MPa; τRd2 = {_fmt(rd2)} MPa "
               "(sem a ampliação de 20 %: há abertura junto ao pilar).")
    sC = seg.verificar_seguranca(rd2, tau_C, "τSd x τRd2 (C)", "19.5.3.1")
    mem.extend(sC.memoria)
    rho = rho_puncao(rho_x, rho_y)
    sc = sigma_cp_puncao_mpa(sigma_cp_x_mpa, sigma_cp_y_mpa)
    rd1 = tau_Rd1_mpa(fck_mpa, rho, d, sc)
    mem.append(f"19.5.3.2 (C′ efetivo): u = {_fmt(cont.u_cm)} cm"
               + (f", Wp1 = {_fmt(W1)} cm²" if W1 else "") + (f", Wp2 = {_fmt(W2)} cm²" if W2 else "")
               + f"; τSd = {_fmt(tau_Cl)} MPa; τRd1 = {_fmt(rd1)} MPa.")
    s1 = seg.verificar_seguranca(rd1, tau_Cl, "τSd x τRd1 (C′)", "19.5.3.2")
    mem.extend(s1.memoria)
    arm = not s1.ok
    rd3 = None
    ok_Cl = s1.ok
    if arm:
        if Asw_cm2 is None or sr_cm is None or fywd_mpa is None:
            mem.append("τSd > τRd1 em C′ e não foi informada armadura de punção (19.5.3.3).")
        else:
            rd3 = tau_Rd3_mpa(fck_mpa, rho, d, Asw_cm2, sr_cm, fywd_mpa, cont.u_cm, alpha_graus,
                              sc, tipo_armadura, h_cm)
            mem.append(f"19.5.3.3 (C′ efetivo com armadura): τRd3 = {_fmt(rd3)} MPa.")
            s3 = seg.verificar_seguranca(rd3, tau_Cl, "τSd x τRd3 (C′)", "19.5.3.3")
            mem.extend(s3.memoria)
            ok_Cl = s3.ok
    ok = sC.ok and ok_Cl
    if not sC.ok:
        gov = "Contorno C: τSd > τRd2 (19.5.3.1)"
    elif not ok_Cl:
        gov = ("Contorno C′ efetivo: é necessária armadura de punção" if rd3 is None else
               "Contorno C′ efetivo: τSd > τRd3 com a armadura informada")
    else:
        gov = ("Contorno C′ efetivo: ok sem armadura de punção" if not arm else
               "Contorno C′ efetivo: ok com armadura de punção (verifique C″, 19.5.3.4)")
    mem.append(f"Resultado: {'passa' if ok else 'não passa'} — {gov}.")
    return ResultadoPuncaoAbertura(u0, cont.u_total_cm, cont.u_cm, cont.u_excluido_cm,
                                   cont.aberturas_consideradas, tau_C, rd2, tau_Cl, rd1, rd3, arm,
                                   ok, gov, tuple(mem))


# === T2: punção — contorno C″ com armadura em cruz (construção do BRGTools) ===
# 19.5.3.4, Figura 19.8 (à direita), PDF p. 190. A Figura mostra o contorno C″
# reduzido entre os braços da armadura em cruz, com as cotas "> 2d" e "d", mas
# não dá a regra numérica do traçado. A construção abaixo é a do programa de
# punção do escritório (BRGTools, BRGTools.PuncaoLaje.Core/Calc/Perimetros.cs,
# função Cruz, porte fiel do LPUNC), adotada por decisão do engenheiro em
# 21/09/2026 (triagem do pacote T2).
#
# Sistema de eixos (o do BRGTools): origem no centro do pilar; x ao longo de b
# e y ao longo de h. Posição do pilar na laje:
#     borda: "esq" (borda livre à esquerda, x < 0), "dir", "sup" (borda livre
#            em cima, y > 0), "inf";
#     canto: "inf_esq" (bordas livres à esquerda e embaixo), "inf_dir",
#            "sup_esq", "sup_dir".

FONTE_C2L_CRUZ = ("a NBR 6118 não dá a regra numérica (Figura 19.8); a construção é a do "
                  "programa de punção do escritório (BRGTools, porte do LPUNC), adotada por "
                  "decisão do engenheiro em 21/09/2026")

POSICOES_C2L_CRUZ = {
    "interno": (None,),
    "borda": ("esq", "dir", "sup", "inf"),
    "canto": ("inf_esq", "inf_dir", "sup_esq", "sup_dir"),
}

# Tabela da construção (Perimetros.Cruz): para cada (tipo, posição), os arcos
# (braço, ângulo inicial, ângulo final, em radianos) e, depois de cada arco,
# os trechos retos de comprimento d que só entram quando o último contorno de
# armadura está a mais de 2d da face. Braços: "sup" (arco de raio r6 acima do
# pilar), "dir" (raio r8, à direita), "inf" (r6, abaixo), "esq" (r8, à
# esquerda). Retas: "sup_d" = ponta direita do arco superior, e assim por diante.
_A_CRUZ = math.pi / 4.0
_T_CRUZ = 1.5 * math.pi   # 3π/2
_P_CRUZ = math.pi
CONSTRUCAO_C2L_CRUZ = {
    ("interno", None): (("sup", _A_CRUZ, _P_CRUZ - _A_CRUZ, ("sup_d", "sup_e")),
                        ("dir", _T_CRUZ + _A_CRUZ, _P_CRUZ / 2 - _A_CRUZ, ("dir_s", "dir_i")),
                        ("inf", _P_CRUZ + _A_CRUZ, 2 * _P_CRUZ - _A_CRUZ, ("inf_d", "inf_e")),
                        ("esq", _P_CRUZ / 2 + _A_CRUZ, _T_CRUZ - _A_CRUZ, ("esq_s", "esq_i"))),
    ("borda", "esq"): (("sup", _A_CRUZ, _P_CRUZ / 2, ("sup_d",)),
                       ("dir", _T_CRUZ + _A_CRUZ, _P_CRUZ / 2 - _A_CRUZ, ("dir_s", "dir_i")),
                       ("inf", _T_CRUZ, 2 * _P_CRUZ - _A_CRUZ, ("inf_d",))),
    ("borda", "dir"): (("sup", _P_CRUZ / 2, _P_CRUZ - _A_CRUZ, ("sup_e",)),
                       ("inf", _P_CRUZ + _A_CRUZ, _T_CRUZ, ("inf_e",)),
                       ("esq", _P_CRUZ / 2 + _A_CRUZ, _T_CRUZ - _A_CRUZ, ("esq_s", "esq_i"))),
    ("borda", "sup"): (("dir", _T_CRUZ + _A_CRUZ, 2 * _P_CRUZ, ("dir_i",)),
                       ("inf", _P_CRUZ + _A_CRUZ, 2 * _P_CRUZ - _A_CRUZ, ("inf_d", "inf_e")),
                       ("esq", _P_CRUZ, _T_CRUZ - _A_CRUZ, ("esq_i",))),
    ("borda", "inf"): (("sup", _A_CRUZ, _P_CRUZ - _A_CRUZ, ("sup_d", "sup_e")),
                       ("dir", 0.0, _P_CRUZ / 2 - _A_CRUZ, ("dir_s",)),
                       ("esq", _P_CRUZ / 2 + _A_CRUZ, _P_CRUZ, ("esq_s",))),
    ("canto", "inf_esq"): (("sup", _A_CRUZ, _P_CRUZ / 2, ("sup_d",)),
                           ("dir", 0.0, _P_CRUZ / 2 - _A_CRUZ, ("dir_s",))),
    ("canto", "inf_dir"): (("sup", _P_CRUZ / 2, _P_CRUZ - _A_CRUZ, ("sup_e",)),
                           ("esq", _P_CRUZ / 2 + _A_CRUZ, _P_CRUZ, ("esq_s",))),
    ("canto", "sup_esq"): (("dir", _T_CRUZ + _A_CRUZ, 2 * _P_CRUZ, ("dir_i",)),
                           ("inf", _T_CRUZ, 2 * _P_CRUZ - _A_CRUZ, ("inf_d",))),
    ("canto", "sup_dir"): (("inf", _P_CRUZ + _A_CRUZ, _T_CRUZ, ("inf_e",)),
                           ("esq", _P_CRUZ, _T_CRUZ - _A_CRUZ, ("esq_i",))),
}


def _posicao_cruz(tipo: str, posicao: str | None) -> tuple[str, str | None]:
    t = _tipo(tipo)
    validas = POSICOES_C2L_CRUZ[t]
    if t == "interno":
        if posicao not in (None, "", "interno"):
            raise ValueError("Pilar interno não tem posição de borda: deixe posicao=None.")
        return t, None
    p = validas[0] if posicao is None else str(posicao).strip().lower()
    if p not in validas:
        raise ValueError(f"Posição {posicao!r} inválida para pilar de {t}; use uma de {validas}.")
    return t, p


def contorno_C2l_cruz(b_cm: float | None, h_cm: float | None, d_cm: float,
                      afastamento_C2l_cm: float, tipo: str = "interno",
                      posicao: str | None = None, D_cm: float | None = None) -> tuple:
    """Traçado do contorno C″ com a armadura de punção em cruz (19.5.3.4, Figura 19.8 à direita, PDF p. 190).

    Fonte: a NBR 6118 não dá a regra numérica (Figura 19.8); a construção é a
    do programa de punção do escritório (BRGTools, porte do LPUNC), adotada
    por decisão do engenheiro em 21/09/2026. Porte da função ``Cruz`` de
    ``BRGTools.PuncaoLaje.Core/Calc/Perimetros.cs``.

    Entre os quatro braços da cruz (ao longo dos eixos do pilar), o contorno é
    fechado por um arco por braço, de 90° no pilar interno, com as pontas a 2d
    (na diagonal de 45°) do canto externo do último contorno de armadura do
    braço. Com rn = ``afastamento_C2l_cm`` − 2d (distância do último contorno
    de armadura à face do pilar) e nb, nh os lados do pilar:

        r6 = (0,5·nb + 2d·cos 45°)/cos 45°      (arcos acima e abaixo do pilar)
        r8 = (0,5·nh + 2d·cos 45°)/cos 45°      (arcos à direita e à esquerda)

    Quando rn > 2d, cada ponta de arco ganha um trecho reto de comprimento d,
    na diagonal (as cotas "d" da Figura 19.8). Pilar circular de diâmetro D:
    nb = nh = D·cos 45° e rn acrescido de (D − nb)/2, como no programa. Borda
    e canto: só os arcos do lado da laje; no programa, os arcos junto à borda
    livre terminam no eixo do pilar (a 90° ou a 0°/180°).

    Devolve os trechos no formato da biblioteca: ("reta", p0, p1) e
    ("arco", centro, r, t0, t1), com t1 > t0 (anti-horário), comprimentos em
    cm, origem no centro do pilar, x ao longo de b e y ao longo de h.
    ``posicao``: borda "esq", "dir", "sup" ou "inf"; canto "inf_esq",
    "inf_dir", "sup_esq" ou "sup_dir" (lado ou lados da borda livre);
    padrão "esq" e "inf_esq". Pilar circular: ``D_cm`` no lugar de b e h.
    """
    t, p = _posicao_cruz(tipo, posicao)
    d = _positivo(d_cm, "d", "19.5.3.4")
    af = _positivo(afastamento_C2l_cm, "afastamento de C″", "19.5.3.4")
    if af - 2.0 * d <= _TOL_GEO:
        raise FaixaNormativaError(
            f"Afastamento de C″ = {af:g} cm não é maior que 2d = {2.0 * d:g} cm: C″ fica a 2d do "
            "último contorno de armadura, que está fora da face do pilar (19.5.3.4).")
    if D_cm is not None:
        D = _positivo(D_cm, "D", "19.5.3.4")
        nb = nh = D * math.cos(math.pi / 4.0)
        off = af - 2.0 * d + (D - nb) / 2.0
    else:
        if b_cm is None or h_cm is None:
            raise ValueError("Informe b_cm e h_cm (pilar retangular) ou D_cm (pilar circular).")
        nb = _positivo(b_cm, "b", "19.5.3.4")
        nh = _positivo(h_cm, "h", "19.5.3.4")
        off = af - 2.0 * d
    s45 = math.sin(math.pi / 4.0)
    c45 = math.cos(math.pi / 4.0)
    e3 = 2.0 * d * c45
    e4 = 2.0 * d * s45
    r6 = (0.5 * nb + e3) / c45
    r8 = (0.5 * nh + e3) / c45
    ext = off > 2.0 * d
    yS = 0.5 * nh + off - (r6 - 2.0 * d) * s45
    xD = 0.5 * nb + off - (r8 - 2.0 * d) * s45
    centros = {"sup": ((0.0, yS), r6), "inf": ((0.0, -yS), r6),
               "dir": ((xD, 0.0), r8), "esq": ((-xD, 0.0), r8)}

    def _reta(x0, y0, x1, y1):
        return ("reta", (x0, y0), (x1, y1))

    xa, ya = 0.5 * nb + e3, 0.5 * nh + off + e4      # pontas dos arcos sup/inf
    xb, yb = 0.5 * nb + off + e3, 0.5 * nh + e4      # pontas dos arcos dir/esq
    retas = {
        "sup_d": _reta(xa, ya, xa + d * s45, ya - d * c45),
        "sup_e": _reta(-xa, ya, -xa - d * s45, ya - d * c45),
        "inf_d": _reta(xa, -ya, xa + d * s45, -ya + d * c45),
        "inf_e": _reta(-xa, -ya, -xa - d * s45, -ya + d * c45),
        "dir_s": _reta(xb, yb, xb - d * c45, yb + d * s45),
        "dir_i": _reta(xb, -yb, xb - d * c45, -yb - d * s45),
        "esq_s": _reta(-xb, yb, -xb + d * c45, yb + d * s45),
        "esq_i": _reta(-xb, -yb, -xb + d * c45, -yb - d * s45),
    }
    trechos: list = []
    for braco, a0, a1, nomes in CONSTRUCAO_C2L_CRUZ[(t, p)]:
        c, r = centros[braco]
        if a1 < a0:   # o arco cruza 0/2π (Arco do BRGTools): leva o fim para depois de 2π
            a1 += 2.0 * math.pi
        trechos.append(("arco", c, r, a0, a1))
        if ext:
            trechos.extend(retas[n] for n in nomes)
    return tuple(trechos)


def u_C2l_cruz_cm(b_cm: float | None, h_cm: float | None, d_cm: float,
                  afastamento_C2l_cm: float, tipo: str = "interno",
                  posicao: str | None = None, D_cm: float | None = None) -> float:
    """Perímetro u″ do contorno C″ com a armadura de punção em cruz, cm (19.5.3.4, Figura 19.8 à direita, PDF p. 190).

    Fonte: a NBR 6118 não dá a regra numérica (Figura 19.8); a construção é a
    do programa de punção do escritório (BRGTools, porte do LPUNC), adotada
    por decisão do engenheiro em 21/09/2026. Soma dos comprimentos dos trechos
    de ``contorno_C2l_cruz`` (arco: raio × ângulo; reta: distância entre as
    pontas), como ``Wp.Comprimento`` do programa. Em forma fechada, com
    r6 = nb/√2 + 2d, r8 = nh/√2 + 2d e δ = 1 quando rn > 2d (0 caso contrário):

        interno: u″ = π·(r6 + r8) + 8·d·δ
        borda:   u″ = (π/2)·(r6 + r8) + 4·d·δ
        canto:   u″ = (π/4)·(r6 + r8) + 2·d·δ

    ``afastamento_C2l_cm`` é a distância de C″ à face do pilar (rn + 2d, com rn
    a distância do último contorno de armadura à face). Fora do trecho reto,
    u″ não depende de rn: na cruz, estender a armadura não aumenta u″ (só
    desloca o contorno). Argumentos como em ``contorno_C2l_cruz``.
    """
    return sum(_comprimento(t) for t in contorno_C2l_cruz(b_cm, h_cm, d_cm, afastamento_C2l_cm,
                                                          tipo, posicao, D_cm))


def _centroide_trechos(trechos) -> tuple[float, float]:
    L = sx = sy = 0.0
    for t in trechos:
        comp = _comprimento(t)
        if t[0] == "reta":
            mx, my = (t[1][0] + t[2][0]) / 2.0, (t[1][1] + t[2][1]) / 2.0
        else:
            delta = t[4] - t[3]
            cg = t[2] * math.sin(0.5 * delta) / (0.5 * delta)
            meio = 0.5 * (t[3] + t[4])
            mx, my = t[1][0] + cg * math.cos(meio), t[1][1] + cg * math.sin(meio)
        L += comp
        sx += comp * mx
        sy += comp * my
    return sx / L, sy / L


def Wp_C2l_cruz_cm2(b_cm: float | None, h_cm: float | None, d_cm: float,
                    afastamento_C2l_cm: float, tipo: str = "interno",
                    posicao: str | None = None, D_cm: float | None = None,
                    direcao_excentricidade_graus: float = 0.0,
                    polo: str = "perimetro") -> float:
    """Wp = ∫|e|·dℓ sobre o contorno C″ em cruz, cm² (19.5.2.2 aplicado a 19.5.3.4, PDF p. 184 e 190).

    O contorno é o de ``contorno_C2l_cruz`` (fonte: a NBR 6118 não dá a regra
    numérica (Figura 19.8); a construção é a do programa de punção do
    escritório (BRGTools, porte do LPUNC), adotada por decisão do engenheiro
    em 21/09/2026). A integral é feita em forma fechada, trecho a trecho, com
    e medido a partir do eixo perpendicular a ``direcao_excentricidade_graus``
    (0° = excentricidade ao longo de b, x; 90° = ao longo de h, y) que passa
    pelo polo. ``polo='perimetro'`` (padrão do programa): centróide do
    próprio contorno C″; ``polo='pilar'``: centro do pilar. No pilar interno
    os dois coincidem.
    """
    trechos = contorno_C2l_cruz(b_cm, h_cm, d_cm, afastamento_C2l_cm, tipo, posicao, D_cm)
    pl = str(polo).strip().lower()
    if pl == "perimetro":
        centro = _centroide_trechos(trechos)
    elif pl == "pilar":
        centro = (0.0, 0.0)
    else:
        raise ValueError("polo deve ser 'perimetro' ou 'pilar'.")
    a = math.radians(float(direcao_excentricidade_graus))
    nrm = (math.cos(a), math.sin(a))
    return sum(_integral_abs_e(t, centro, nrm) for t in trechos)
