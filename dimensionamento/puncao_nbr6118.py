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
                     gama_c: float = nbr.GAMA_C) -> ResultadoPuncao:
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
