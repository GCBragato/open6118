"""Sapatas de Fundação (NBR 6118:2023 + CEB-70).

Nome até 19/09/2026: sapatas_bastos.py. O crédito às apostilas está abaixo.

Implementa o dimensionamento de sapatas isoladas seguindo a apostila
"SAPATAS DE FUNDAÇÃO", Prof. Paulo Sérgio Bastos, UNESP/Bauru.

Casos cobertos:
    - Classificação rígida x flexível (NBR 6118 e CEB-70)        (Eq. 1.1/1.2)
    - Estimativa da área da base                                  (Eq. 1.6)
    - Dimensionamento com balanços iguais                         (Eq. 1.9)
    - Método do CEB-70 (momentos nas seções S1A/S1B)              (Eq. 1.27)
    - Armadura de flexão                                          (Eq. 1.28)
    - Verificação da diagonal comprimida (punção - superf. C)     (Eq. 1.17/1.18)
    - Método das Bielas (sapata rígida)                           (Eq. 1.31-1.36)

Convenções:
    - fck em MPa.
    - Geometria em cm. Pressão em kN/cm2 (= 10 MPa).
    - Forças em kN, momentos em kN.cm.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr


GAMA_C = 1.4
GAMA_S = 1.15
GAMA_F = nbr.GAMA_F  # Tabela 11.1 — lido do núcleo (P4)


def fcd_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fcd em kN/cm2 (delegado ao núcleo normativo: nbr.fcd, 12.3.3)."""
    return nbr.mpa_para_kncm2(nbr.fcd(fck_mpa, gama_c))


def fyd_kncm2(fyk_mpa: float = 500.0,
              gama_s: float = GAMA_S) -> float:
    """fyd em kN/cm2 (delegado ao núcleo normativo: nbr.fyd)."""
    return nbr.mpa_para_kncm2(nbr.fyd(fyk_mpa, gama_s))


# ---------------------------------------------------------------------------
# Classificação
# ---------------------------------------------------------------------------
def eh_rigida_nbr(h_cm: float, A_cm: float, ap_cm: float,
                  B_cm: float | None = None,
                  bp_cm: float | None = None) -> bool:
    """NBR 6118 22.6.1 (Eq. 1.1): rígida se h >= (A - ap)/3 nas duas direções.

    Se B/bp não forem fornecidos, verifica apenas a direção A.
    """
    cond_A = h_cm >= (A_cm - ap_cm) / 3.0
    if B_cm is None or bp_cm is None:
        return cond_A
    cond_B = h_cm >= (B_cm - bp_cm) / 3.0
    return cond_A and cond_B


def classificacao_ceb70(h_cm: float, cA_cm: float) -> str:
    """CEB-70 (Eq. 1.2): tg(beta) = h/cA.
    - tg < 0.5  -> flexivel
    - 0.5 <= tg <= 1.5  -> rigida
    - tg > 1.5  -> bloco (dispensa armadura de flexão)
    """
    tg = h_cm / cA_cm
    if tg < 0.5:
        return "flexivel"
    if tg <= 1.5:
        return "rigida"
    return "bloco"


# ---------------------------------------------------------------------------
# Estimativa de dimensões
# ---------------------------------------------------------------------------
def area_base_cm2(Nk_kn: float, Padm_kncm2: float,
                  K_maj: float = 1.1) -> float:
    """Ssap = K_maj * Nk / Padm (Eq. 1.6).
    K_maj ~ 1.1 para considerar peso próprio da sapata e do solo."""
    return K_maj * Nk_kn / Padm_kncm2


def dimensao_B_balancos_iguais(ap_cm: float, bp_cm: float,
                               Ssap_cm2: float) -> float:
    """B com balanços iguais (cA = cB): A - B = ap - bp (Eq. 1.9).

    Resolve B a partir de A = B + (ap - bp), Ssap = A*B:
       B^2 + (ap-bp)*B - Ssap = 0
       B = -(ap-bp)/2 + sqrt(((ap-bp)/2)^2 + Ssap)
    """
    delta_p = ap_cm - bp_cm
    return -delta_p / 2.0 + math.sqrt((delta_p / 2.0) ** 2 + Ssap_cm2)


# ---------------------------------------------------------------------------
# CEB-70 - Momentos nas seções S1
# ---------------------------------------------------------------------------
def momento_CEB70(p_kncm2: float, c_aba_cm: float, dim_pilar_cm: float,
                  largura_perp_cm: float) -> float:
    """Momento na seção S1 (Eq. 1.27) afastada 0.15*ap da face do pilar:
       M1d = pd * x^2 / 2 * largura_perp
    com x = c_aba + 0.15 * dim_pilar.
    """
    x = c_aba_cm + 0.15 * dim_pilar_cm
    return p_kncm2 * x * x / 2.0 * largura_perp_cm


def As_flexao_sapata(M_kncm: float, d_cm: float,
                     fyk_mpa: float = 500.0,
                     gama_s: float = GAMA_S) -> float:
    """As = M / (0.85 * d * fyd)  (Eq. 1.28). Resultado em cm2."""
    fyd = fyd_kncm2(fyk_mpa, gama_s)
    return M_kncm / (0.85 * d_cm * fyd)


# ---------------------------------------------------------------------------
# Armadura mínima de flexão (FUN-02)
# ---------------------------------------------------------------------------
def as_min_flexao_sapata(largura_perp_cm: float, h_cm: float, fck_mpa: float,
                         criterio_as_min: str = "laje") -> float:
    """As,mínimo de flexão para sapata, em cm2 (decisão 2 do plano de
    correção contra a NBR 6118:2026 / achado FUN-02).

    A NBR 22.6 não fixa uma taxa mínima própria para sapatas: 22.6.4.1.3
    (sapata flexível) remete aos requisitos de lajes e punção (Seções 19
    e 20); a sapata rígida também trabalha à flexão nas duas direções,
    com a tração considerada uniforme na largura (22.6.2.2 a)). Por isso
    o mínimo de lajes armadas nas duas direções (Tabela 19.1) é adotado
    como padrão.

    largura_perp_cm : largura perpendicular às barras dessa direção (a
        OUTRA dimensão em planta da sapata -- para As_B use A_cm, para
        As_A use B_cm), combinada com h_cm na seção de referência bw*h.
    criterio_as_min:
        "laje"    (padrão) rho_s >= 0,67*rho_min -- Tabela 19.1, linha
                  "Armaduras positivas de lajes armadas nas duas direções";
        "rho_min" rho_s >= rho_min cheio -- Tabela 17.3 (elemento linear);
        "nenhum"  não aplica mínimo algum (uso apenas comparativo).
    rho_min vem de nbr.rho_min_flexao(fck) (Tabela 17.3, núcleo normativo;
    cobre C20 a C90, decisão 1).
    """
    if criterio_as_min == "nenhum":
        return 0.0
    if criterio_as_min == "laje":
        fator = 0.67
    elif criterio_as_min == "rho_min":
        fator = 1.0
    else:
        raise ValueError(
            f"criterio_as_min inválido: {criterio_as_min!r}. "
            "Use 'laje', 'rho_min' ou 'nenhum'."
        )
    return fator * nbr.rho_min_flexao(fck_mpa) * largura_perp_cm * h_cm


# ---------------------------------------------------------------------------
# Verificação da diagonal comprimida (punção na superfície C)
# ---------------------------------------------------------------------------
def tau_Sd_kncm2(FSd_kn: float, u0_cm: float, d_cm: float) -> float:
    """tau_Sd = FSd / (u0 * d)  (Eq. 1.18).
    u0 = perímetro do pilar."""
    return FSd_kn / (u0_cm * d_cm)


def tau_Rd2_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """tau_Rd,2 = 0.27 * alpha_v * fcd  (Eq. 1.17, NBR 19.5.3.1)."""
    fcd = fcd_kncm2(fck_mpa, gama_c)
    return 0.27 * nbr.alpha_v2(fck_mpa) * fcd


def verifica_diagonal(FSd_kn: float, u0_cm: float, d_cm: float,
                      fck_mpa: float) -> dict:
    sd = tau_Sd_kncm2(FSd_kn, u0_cm, d_cm)
    rd = tau_Rd2_kncm2(fck_mpa)
    return {
        "tau_Sd_kNcm2": sd,
        "tau_Rd2_kNcm2": rd,
        "tau_Sd_MPa": sd * 10.0,
        "tau_Rd2_MPa": rd * 10.0,
        "ok": sd <= rd,
    }


# ---------------------------------------------------------------------------
# Método das Bielas (Lebelle)
# ---------------------------------------------------------------------------
def d_min_bielas(A_cm: float, ap_cm: float) -> float:
    """d mínimo pelo método das bielas (Eq. 1.31): d >= (A - ap)/4."""
    return (A_cm - ap_cm) / 4.0


def tracao_base_bielas(P_kn: float, dim_lado_cm: float,
                       dim_pilar_cm: float, d_cm: float) -> float:
    """T = P * (lado - dim_pilar) / (8 * d)  (Eq. 1.32/1.33)."""
    return P_kn * (dim_lado_cm - dim_pilar_cm) / (8.0 * d_cm)


def As_bielas(T_kn: float, fyk_mpa: float = 500.0,
              gama_s: float = GAMA_S, gama_f: float = GAMA_F) -> float:
    """As = (gama_f * T) / fyd  (Eq. 1.35/1.36).
    T é força característica; aplicar gama_f."""
    fyd = fyd_kncm2(fyk_mpa, gama_s) * 10.0  # MPa
    # Mas a apostila usa fyd diretamente em MPa = 50/1.15:
    return gama_f * T_kn / (fyk_mpa / gama_s) * 10.0  # cm2


# ---------------------------------------------------------------------------
# Sapata excêntrica (1 direção) - Eq. 1.39, 1.40, 1.41
# ---------------------------------------------------------------------------
def tensoes_sapata_excentrica_1d(
    N_kn: float, M_kncm: float, A_cm: float, B_cm: float,
) -> dict:
    """Tensões max/min na base de sapata isolada com excentricidade na
    direção A (um eixo).

    e = M/N (excentricidade da força normal)
    a) e <= A/6 (dentro do núcleo): sigma_max/min = (N/AB)*(1 +/- 6e/A)
    b) e = A/6 (no limite): sigma_max = 2N/(AB), sigma_min = 0
    c) e > A/6 (fora do núcleo): área tracionada -> redistribuição
       sigma_max = 2N / (3*B*(A/2 - e))
    """
    e = abs(M_kncm) / N_kn
    nucleo = A_cm / 6.0
    if e <= nucleo:
        # Caso a (Eq. 1.39)
        sigma_max = (N_kn / (A_cm * B_cm)) * (1.0 + 6.0 * e / A_cm)
        sigma_min = (N_kn / (A_cm * B_cm)) * (1.0 - 6.0 * e / A_cm)
        caso = "a-dentro-nucleo"
    elif _aprox(e, nucleo, 0.5):
        # Caso b (Eq. 1.40)
        sigma_max = 2.0 * N_kn / (A_cm * B_cm)
        sigma_min = 0.0
        caso = "b-limite-nucleo"
    else:
        # Caso c (Eq. 1.41)
        sigma_max = 2.0 * N_kn / (3.0 * B_cm * (A_cm / 2.0 - e))
        sigma_min = 0.0  # área tracionada desconsiderada
        caso = "c-fora-nucleo"
    return {
        "e_cm": e,
        "nucleo_cm": nucleo,
        "sigma_max_kncm2": sigma_max,
        "sigma_min_kncm2": sigma_min,
        "caso": caso,
        "ok_NBR_caracteristica": (e <= A_cm * (1.0 / 2.0 - 1.0 / 3.0)),
    }


def tensoes_sapata_excentrica_2d(
    N_kn: float, eA_cm: float, eB_cm: float,
    A_cm: float, B_cm: float,
) -> tuple[float, float, float, float]:
    """Tensões nos 4 cantos para excentricidade em 2 direções (núcleo central).

    sigma = N/(AB) * (1 +/- 6*eA/A +/- 6*eB/B)

    Retorna (sigma_++, sigma_+-, sigma_-+, sigma_--) em kN/cm2.
    Válido apenas quando eA/A + eB/B <= 1/6."""
    base = N_kn / (A_cm * B_cm)
    fA = 6.0 * eA_cm / A_cm
    fB = 6.0 * eB_cm / B_cm
    return (base * (1 + fA + fB), base * (1 + fA - fB),
            base * (1 - fA + fB), base * (1 - fA - fB))


# ---------------------------------------------------------------------------
# Sapata corrida (item 1.7)
# ---------------------------------------------------------------------------
def projetar_sapata_corrida(
    Nk_por_metro_kn: float, ap_cm: float, Padm_kncm2: float,
    h_cm: float, fck_mpa: float, fyk_mpa: float = 500.0,
    K_maj: float = 1.05, gama_f: float = GAMA_F,
    gama_s: float = GAMA_S, cobrimento_cm: float = 4.0,
    criterio_as_min: str = "laje",
) -> dict:
    """Sapata corrida sob carga uniforme (parede de comprimento >> largura).

    Trabalha sobre uma faixa de 1 m. A largura B é dimensionada para
    Padm; o momento e As são por metro de comprimento.

    Nk_por_metro: carga vertical característica por metro de parede [kN/m]
    ap          : largura da parede sobre a sapata [cm]
    Padm        : tensão admissível do solo [kN/cm2]
    criterio_as_min: ver ``as_min_flexao_sapata`` (achado FUN-02, decisão 2).

    Returns dict com B, c (balanço), pd, M1d/m, As_por_metro (>= mínimo).
    """
    # Dimensão B necessária (faixa de 100 cm)
    B = K_maj * Nk_por_metro_kn / 100.0 / Padm_kncm2  # cm
    c = (B - ap_cm) / 2.0
    d = h_cm - cobrimento_cm - 1.0
    Nd_por_m = gama_f * Nk_por_metro_kn / 100.0   # kN/cm
    pd = Nd_por_m / B                              # kN/cm2
    # Momento na seção S1 (CEB-70: x = c + 0.15*ap), por unidade de
    # comprimento (faixa 100 cm = considerada implicitamente)
    x = c + 0.15 * ap_cm
    M1d_por_m = pd * x * x / 2.0 * 100.0           # kN.cm/m
    fyd = fyd_kncm2(fyk_mpa, gama_s)
    As_por_m = M1d_por_m / (0.85 * d * fyd)        # cm2/m
    As_min_por_m = as_min_flexao_sapata(100.0, h_cm, fck_mpa, criterio_as_min)
    As_por_m = max(As_por_m, As_min_por_m)
    return {
        "B_cm": B,
        "c_cm": c,
        "h_cm": h_cm,
        "d_cm": d,
        "pd_kncm2": pd,
        "M1d_kncm_por_m": M1d_por_m,
        "As_cm2_por_m": As_por_m,
        "As_min_cm2_por_m": As_min_por_m,
        "rigida_nbr": h_cm >= (B - ap_cm) / 3.0,
    }


# ---------------------------------------------------------------------------
# Sapata flexível (item 1.6.8) - verificação à força cortante
# ---------------------------------------------------------------------------
def cortante_sapata_flexivel(
    pd_kncm2: float, A_cm: float, B_cm: float, ap_cm: float, bp_cm: float,
    d_cm: float, fck_mpa: float, gama_c: float = GAMA_C,
    secao_critica: str = "d",
) -> dict:
    """Verificação da força cortante para sapata flexível (NBR 19.4.1).

    Força cortante na seção crítica, na direção A:
    VSd = pd * B * (cA - afastamento)

    secao_critica (achado FUN-04, decisão 3 do plano de correção):
        "d"   (padrão) -- a seção crítica fica a uma distância d da face
              do pilar, conforme 19.4.1 (PDF p. 181): "a uma distância d
              da face do apoio".
        "d/2" -- afastamento d/2, critério do CEB-70 -- NÃO é o da NBR;
              use apenas quando o método adotado for o CEB-70 inteiro,
              nunca atribuindo esse afastamento ao 19.4.1.

    VRd1 (sem armadura) = tau_Rd * k * (1,2 + 40 rho_l) * bw * d, com
    tau_Rd = 0,25*fctd e fck limitado a 60 MPa (19.4.1, via núcleo
    normativo). Para sapatas geralmente despreza-se rho_l e sigma_cp
    (toma o termo conservador da fórmula).
    """
    if secao_critica not in ("d", "d/2"):
        raise ValueError(
            f"secao_critica inválida: {secao_critica!r}. "
            "Use 'd' (NBR 19.4.1) ou 'd/2' (CEB-70)."
        )
    afastamento = d_cm if secao_critica == "d" else d_cm / 2.0

    cA = (A_cm - ap_cm) / 2.0
    cB = (B_cm - bp_cm) / 2.0
    if cA <= afastamento:
        VSd_A = 0.0
    else:
        VSd_A = pd_kncm2 * B_cm * (cA - afastamento)
    if cB <= afastamento:
        VSd_B = 0.0
    else:
        VSd_B = pd_kncm2 * A_cm * (cB - afastamento)

    # tau_Rd = 0,25 * fctd, com fck limitado a 60 MPa (19.4.1; FUN-03)
    tau_rd = nbr.mpa_para_kncm2(nbr.tau_Rd(fck_mpa, gama_c))
    k = max(1.0, 1.6 - d_cm / 100.0)
    VRd1_por_m = tau_rd * k * 1.2 * 1.0 * d_cm     # kN/cm de largura
    VRd1_A = VRd1_por_m * B_cm
    VRd1_B = VRd1_por_m * A_cm
    return {
        "VSd_A_kN": VSd_A, "VSd_B_kN": VSd_B,
        "VRd1_A_kN": VRd1_A, "VRd1_B_kN": VRd1_B,
        "ok_A": VSd_A <= VRd1_A,
        "ok_B": VSd_B <= VRd1_B,
        "secao_critica": secao_critica,
    }


# ---------------------------------------------------------------------------
# Resultado consolidado para sapata isolada centrada
# ---------------------------------------------------------------------------
@dataclass
class ResultadoSapata:
    A_cm: float
    B_cm: float
    h_cm: float
    d_cm: float
    cA_cm: float
    cB_cm: float
    rigida_nbr: bool
    rigida_ceb70: str
    p_kncm2: float
    M1A_kncm: float
    M1B_kncm: float
    As_A_cm2: float
    As_B_cm2: float
    tau_Sd_MPa: float
    tau_Rd2_MPa: float
    ok_diagonal: bool
    As_A_min_cm2: float = 0.0
    As_B_min_cm2: float = 0.0
    criterio_as_min: str = "laje"


def projetar_sapata_centrada(
    Nk_kn: float, ap_cm: float, bp_cm: float, Padm_kncm2: float,
    h_cm: float, fck_mpa: float, fyk_mpa: float = 500.0,
    K_maj: float = 1.1, gama_f: float = GAMA_F,
    gama_c: float = GAMA_C, gama_s: float = GAMA_S,
    cobrimento_cm: float = 4.0, phi_barra_cm: float = 1.0,
    A_cm: float | None = None, B_cm: float | None = None,
    criterio_as_min: str = "laje",
) -> ResultadoSapata:
    """Projeta sapata isolada sob carga centrada (CEB-70).

    Se A_cm/B_cm forem omitidos, calcula com balanços iguais a partir
    de Ssap.

    criterio_as_min: ver ``as_min_flexao_sapata`` (achado FUN-02, decisão
    2 do plano de correção). As_A_cm2/As_B_cm2 saem elevados ao mínimo
    correspondente; o mínimo aplicado fica em As_A_min_cm2/As_B_min_cm2.
    """
    if A_cm is None or B_cm is None:
        Ssap = area_base_cm2(Nk_kn, Padm_kncm2, K_maj)
        B = dimensao_B_balancos_iguais(ap_cm, bp_cm, Ssap)
        A = B + (ap_cm - bp_cm)
    else:
        A, B = A_cm, B_cm

    cA = (A - ap_cm) / 2.0
    cB = (B - bp_cm) / 2.0
    d = h_cm - (cobrimento_cm + phi_barra_cm)

    Nd = gama_f * Nk_kn
    pd = Nd / (A * B)

    M1A = momento_CEB70(pd, cA, ap_cm, B)
    M1B = momento_CEB70(pd, cB, bp_cm, A)
    As_A = As_flexao_sapata(M1A, d, fyk_mpa, gama_s)
    As_B = As_flexao_sapata(M1B, d, fyk_mpa, gama_s)
    # FUN-02: As,mínimo (22.6.4.1.3 remete a lajes/Tabela 19.1). As_A corre
    # ao longo de A e se distribui ao longo de B (e vice-versa para As_B)
    # -- a largura perpendicular às barras de cada direção é a OUTRA
    # dimensão da sapata.
    As_A_min = as_min_flexao_sapata(B, h_cm, fck_mpa, criterio_as_min)
    As_B_min = as_min_flexao_sapata(A, h_cm, fck_mpa, criterio_as_min)
    As_A = max(As_A, As_A_min)
    As_B = max(As_B, As_B_min)

    u0 = 2.0 * (ap_cm + bp_cm)
    diag = verifica_diagonal(Nd, u0, d, fck_mpa)

    return ResultadoSapata(
        A_cm=A, B_cm=B, h_cm=h_cm, d_cm=d,
        cA_cm=cA, cB_cm=cB,
        rigida_nbr=eh_rigida_nbr(h_cm, A, ap_cm, B, bp_cm),
        rigida_ceb70=classificacao_ceb70(h_cm, cA),
        p_kncm2=pd,
        M1A_kncm=M1A, M1B_kncm=M1B,
        As_A_cm2=As_A, As_B_cm2=As_B,
        tau_Sd_MPa=diag["tau_Sd_MPa"], tau_Rd2_MPa=diag["tau_Rd2_MPa"],
        ok_diagonal=diag["ok"],
        As_A_min_cm2=As_A_min, As_B_min_cm2=As_B_min,
        criterio_as_min=criterio_as_min,
    )


# ---------------------------------------------------------------------------
# Tests (validados contra Exemplo 1 e 2 da apostila Bastos)
# ---------------------------------------------------------------------------
def _aprox(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def test_classificacao_rigida_apostila() -> None:
    """Apostila ex.1: A=265, ap=80, h=70 -> (A-ap)/3 = 61.67;
    h=70 > 61.67 -> rígida pela NBR."""
    assert eh_rigida_nbr(h_cm=70.0, A_cm=265.0, ap_cm=80.0,
                         B_cm=205.0, bp_cm=20.0)
    print("  OK  Classificação NBR: rígida (70 >= 61.67 e 61.67)")


def test_classificacao_ceb70() -> None:
    """tg(beta) = h/cA = 70/92.5 = 0.757; entre 0.5 e 1.5 -> rígida."""
    cl = classificacao_ceb70(h_cm=70.0, cA_cm=92.5)
    assert cl == "rigida", f"classificacao={cl}"
    print(f"  OK  CEB-70: tg(beta) = {70/92.5:.3f} -> {cl}")


def test_estimativa_area_apostila() -> None:
    """Apostila ex.1: Nk=1250 kN, Padm=0.026 kN/cm2.
    Ssap = 1.1 * 1250 / 0.026 = 52885 cm2."""
    s = area_base_cm2(Nk_kn=1250.0, Padm_kncm2=0.026, K_maj=1.1)
    assert _aprox(s, 52885.0, 5.0), f"Ssap={s}"
    print(f"  OK  Ssap = {s:.0f} cm2  (apostila: 52885)")


def test_B_balancos_iguais_apostila() -> None:
    """Apostila ex.1: ap=80, bp=20, Ssap=52885 -> B = 201.9 cm."""
    B = dimensao_B_balancos_iguais(ap_cm=80.0, bp_cm=20.0,
                                    Ssap_cm2=52885.0)
    assert _aprox(B, 201.9, 0.2), f"B={B:.2f}"
    print(f"  OK  B = {B:.2f} cm  (apostila: 201.9 -> adotado 205)")


def test_momento_CEB70_apostila() -> None:
    """Apostila ex.1: pd=0.03221 kN/cm2, cA=92.5, ap=80, B=205.
    xA = 92.5 + 0.15*80 = 104.5; M1A = 0.03221 * 104.5^2/2 * 205 = 36053 kN.cm.
    cB=92.5, bp=20, A=265; xB = 92.5 + 3 = 95.5;
    M1B = 0.03221 * 95.5^2/2 * 265 = 38924 kN.cm."""
    M1A = momento_CEB70(p_kncm2=0.03221, c_aba_cm=92.5,
                         dim_pilar_cm=80.0, largura_perp_cm=205.0)
    M1B = momento_CEB70(p_kncm2=0.03221, c_aba_cm=92.5,
                         dim_pilar_cm=20.0, largura_perp_cm=265.0)
    assert _aprox(M1A, 36053.0, 50.0), f"M1A={M1A:.0f}"
    assert _aprox(M1B, 38924.0, 50.0), f"M1B={M1B:.0f}"
    print(f"  OK  M1A = {M1A:.0f}  M1B = {M1B:.0f} kN.cm")


def test_As_flexao_apostila() -> None:
    """As,A = 36053 / (0.85*65*43.48) = 15.01 cm2;
    As,B = 38924 / (0.85*65*43.48) = 16.20 cm2."""
    As_A = As_flexao_sapata(M_kncm=36053.0, d_cm=65.0)
    As_B = As_flexao_sapata(M_kncm=38924.0, d_cm=65.0)
    assert _aprox(As_A, 15.01, 0.05), f"As_A={As_A:.3f}"
    assert _aprox(As_B, 16.20, 0.05), f"As_B={As_B:.3f}"
    print(f"  OK  As_A = {As_A:.2f}  As_B = {As_B:.2f} cm2")


def test_diagonal_comprimida_apostila() -> None:
    """FSd = 1750 kN, u0 = 200 cm, d = 65 cm, C25.
    tau_Sd = 1750/(200*65) = 0.135 kN/cm2 = 1.35 MPa
    tau_Rd2 = 0.27 * (1-25/250) * 25/14 = 0.434 kN/cm2 = 4.34 MPa."""
    r = verifica_diagonal(FSd_kn=1750.0, u0_cm=200.0, d_cm=65.0,
                          fck_mpa=25.0)
    assert _aprox(r["tau_Sd_MPa"], 1.35, 0.02), f"tau_Sd={r['tau_Sd_MPa']}"
    assert _aprox(r["tau_Rd2_MPa"], 4.34, 0.02), f"tau_Rd2={r['tau_Rd2_MPa']}"
    assert r["ok"]
    print(f"  OK  tau_Sd = {r['tau_Sd_MPa']:.2f} MPa <= "
          f"tau_Rd2 = {r['tau_Rd2_MPa']:.2f} MPa")


def test_metodo_bielas_d_min() -> None:
    """Ex.2: A=265, ap=80 -> d_min = 46.25 cm."""
    d = d_min_bielas(A_cm=265.0, ap_cm=80.0)
    assert _aprox(d, 46.25, 0.1), f"d_min={d}"
    print(f"  OK  Método bielas: d_min = {d:.2f} cm  (apostila: 46.3)")


def test_metodo_bielas_tracao() -> None:
    """Ex.2: P=1250, A=265, ap=80, d=65.
    Tx = 1250 * (265-80) / (8*65) = 444.7 kN."""
    Tx = tracao_base_bielas(P_kn=1250.0, dim_lado_cm=265.0,
                             dim_pilar_cm=80.0, d_cm=65.0)
    assert _aprox(Tx, 444.7, 0.1), f"Tx={Tx:.2f}"
    print(f"  OK  Tx = {Tx:.2f} kN  (apostila: 444.7)")


def test_metodo_bielas_armadura() -> None:
    """Ex.2: T=444.7, gama_f=1.4, fyd=43.48 -> As = 14.32 cm2."""
    As = As_bielas(T_kn=444.7)
    assert _aprox(As, 14.32, 0.05), f"As={As:.3f}"
    print(f"  OK  As (bielas) = {As:.2f} cm2  (apostila: 14.32)")


def test_projetar_sapata_completo() -> None:
    """Reproduz o Exemplo 1 com A,B fixados.

    FUN-02 (22.6.4.1.3 remete a lajes; Tabela 19.1, "armaduras positivas
    de lajes armadas nas duas direções": rho_s >= 0,67*rho_min): a Eq.
    1.28 pura dava As_B = 16,20 cm2, 13% abaixo do mínimo de 18,64 cm2
    (rho_min(C25) = 0,15%; 0,67*0,0015*265*70 = 18,64). As_A (15,01) já
    estava acima do seu mínimo (14,42 = 0,67*0,0015*205*70) e não muda.
    """
    r = projetar_sapata_centrada(
        Nk_kn=1250.0, ap_cm=80.0, bp_cm=20.0, Padm_kncm2=0.026,
        h_cm=70.0, fck_mpa=25.0, A_cm=265.0, B_cm=205.0,
        cobrimento_cm=4.0, phi_barra_cm=1.0,
    )
    assert _aprox(r.cA_cm, 92.5, 0.1)
    assert _aprox(r.d_cm, 65.0, 0.1)
    assert r.rigida_nbr
    assert _aprox(r.As_A_cm2, 15.01, 0.05)
    assert _aprox(r.As_B_cm2, 18.64, 0.05)
    assert r.ok_diagonal
    print(f"  OK  Sapata 265x205x70: As_A = {r.As_A_cm2:.2f}, "
          f"As_B = {r.As_B_cm2:.2f} (mínimo Tab. 19.1), diag={r.ok_diagonal}")


def test_sapata_excentrica_dentro_nucleo() -> None:
    """N=1000 kN, M=20000 kN.cm, A=200 cm, B=200 cm.
    e = 20 cm < A/6 = 33.3 cm -> caso a.
    sigma_max = (1000/40000)*(1 + 6*20/200) = 0.025*1.6 = 0.04 kN/cm2
    sigma_min = 0.025*0.4 = 0.01 kN/cm2."""
    r = tensoes_sapata_excentrica_1d(N_kn=1000.0, M_kncm=20000.0,
                                     A_cm=200.0, B_cm=200.0)
    assert r["caso"] == "a-dentro-nucleo"
    assert _aprox(r["sigma_max_kncm2"], 0.04, 0.001)
    assert _aprox(r["sigma_min_kncm2"], 0.01, 0.001)
    print(f"  OK  Excêntrica dentro núcleo: e={r['e_cm']:.1f} cm, "
          f"sigma_max/min = {r['sigma_max_kncm2']:.4f}/"
          f"{r['sigma_min_kncm2']:.4f} kN/cm2")


def test_sapata_excentrica_fora_nucleo() -> None:
    """e > A/6: parte tracionada. N=1000, M=70000, A=200, B=200.
    e = 70 cm > A/6 = 33.3
    sigma_max = 2*1000 / (3*200*(100-70)) = 2000/18000 = 0.1111 kN/cm2."""
    r = tensoes_sapata_excentrica_1d(N_kn=1000.0, M_kncm=70000.0,
                                     A_cm=200.0, B_cm=200.0)
    assert r["caso"] == "c-fora-nucleo"
    assert _aprox(r["sigma_max_kncm2"], 0.1111, 0.001)
    assert _aprox(r["sigma_min_kncm2"], 0.0, 0.001)
    print(f"  OK  Excêntrica fora núcleo: e={r['e_cm']:.1f} cm, "
          f"sigma_max = {r['sigma_max_kncm2']:.4f} kN/cm2")


def test_sapata_excentricidade_2d() -> None:
    """N=1000, eA=10, eB=5, A=200, B=200.
    sigma_++ = (1000/40000)*(1 + 6*10/200 + 6*5/200) = 0.025*1.45 = 0.03625
    sigma_-- = 0.025*0.55 = 0.01375."""
    s = tensoes_sapata_excentrica_2d(1000.0, 10.0, 5.0, 200.0, 200.0)
    assert _aprox(s[0], 0.03625, 0.0005)
    assert _aprox(s[3], 0.01375, 0.0005)
    print(f"  OK  Excentricidade 2D: sigma 4 cantos = "
          f"{s[0]:.4f}, {s[1]:.4f}, {s[2]:.4f}, {s[3]:.4f} kN/cm2")


def test_sapata_corrida_basica() -> None:
    """Parede ap=20 cm, Nk=300 kN/m, Padm=0.20 kN/cm2 (2 MPa).
    K_maj=1.05 -> B = 1.05*300/100/0.20 = 15.75 cm.
    Mas B<ap não faz sentido; ajuste para teste real:
    Nk=1000 kN/m, Padm=0.025 kN/cm2 -> B = 1.05*1000/100/0.025 = 420 cm."""
    r = projetar_sapata_corrida(
        Nk_por_metro_kn=1000.0, ap_cm=20.0, Padm_kncm2=0.025,
        h_cm=80.0, fck_mpa=25.0,
    )
    assert _aprox(r["B_cm"], 420.0, 1.0)
    assert r["c_cm"] > 0
    assert r["As_cm2_por_m"] > 0
    print(f"  OK  Sapata corrida: B={r['B_cm']:.0f}, c={r['c_cm']:.0f}, "
          f"As={r['As_cm2_por_m']:.2f} cm2/m  (rigida={r['rigida_nbr']})")


def test_cortante_sapata_flexivel() -> None:
    """Sapata 250x250x40, ap=bp=30, pd=0.05 kN/cm2 (~5 MPa), C25.
    cA = cB = 110; d = 35.

    FUN-04 (19.4.1, p.181: seção crítica "a uma distância d da face do
    apoio"; decisão 3 do plano de correção): o padrão agora é a seção a
    d, não mais a d/2 do CEB-70.
    VSd_A (seção a d)   = 0.05 * 250 * (110 - 35)   = 937.50 kN.
    VSd_A (d/2, CEB-70) = 0.05 * 250 * (110 - 17.5) = 1156.25 kN
    (valor antigo, "+23% a favor da segurança", só alcançável agora com
    secao_critica="d/2" explícito)."""
    r = cortante_sapata_flexivel(
        pd_kncm2=0.05, A_cm=250.0, B_cm=250.0, ap_cm=30.0, bp_cm=30.0,
        d_cm=35.0, fck_mpa=25.0,
    )
    assert r["secao_critica"] == "d"
    assert _aprox(r["VSd_A_kN"], 937.50, 1.0)
    print(f"  OK  Cortante sapata flex (seção a d): VSd_A={r['VSd_A_kN']:.0f}, "
          f"VRd1_A={r['VRd1_A_kN']:.0f} kN  (ok={r['ok_A']})")

    r_ceb70 = cortante_sapata_flexivel(
        pd_kncm2=0.05, A_cm=250.0, B_cm=250.0, ap_cm=30.0, bp_cm=30.0,
        d_cm=35.0, fck_mpa=25.0, secao_critica="d/2",
    )
    assert _aprox(r_ceb70["VSd_A_kN"], 1156.25, 1.0)
    print(f"  OK  Cortante sapata flex (CEB-70, d/2): "
          f"VSd_A={r_ceb70['VSd_A_kN']:.0f} kN")


def run_tests() -> int:
    tests = [
        test_classificacao_rigida_apostila,
        test_classificacao_ceb70,
        test_estimativa_area_apostila,
        test_B_balancos_iguais_apostila,
        test_momento_CEB70_apostila,
        test_As_flexao_apostila,
        test_diagonal_comprimida_apostila,
        test_metodo_bielas_d_min,
        test_metodo_bielas_tracao,
        test_metodo_bielas_armadura,
        test_projetar_sapata_completo,
        test_sapata_excentrica_dentro_nucleo,
        test_sapata_excentrica_fora_nucleo,
        test_sapata_excentricidade_2d,
        test_sapata_corrida_basica,
        test_cortante_sapata_flexivel,
    ]
    falhas = 0
    for t in tests:
        try:
            print(f"[{t.__name__}]")
            t()
        except AssertionError as e:
            falhas += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception as e:
            falhas += 1
            print(f"  ERRO {t.__name__}: {e}")
    print(f"\n{len(tests) - falhas}/{len(tests)} OK")
    return falhas


def _demo() -> None:
    print("=== Exemplo 1 (Apostila Bastos) - sapata isolada centrada ===")
    print("  Nk=1250 kN, pilar 20x80, Padm=0.26 MPa, C25, h=70 cm")
    r = projetar_sapata_centrada(
        Nk_kn=1250.0, ap_cm=80.0, bp_cm=20.0, Padm_kncm2=0.026,
        h_cm=70.0, fck_mpa=25.0, A_cm=265.0, B_cm=205.0,
    )
    print(f"  Dim base : {r.A_cm:.0f} x {r.B_cm:.0f} cm")
    print(f"  cA, cB   : {r.cA_cm:.1f}, {r.cB_cm:.1f} cm")
    print(f"  Rígida   : NBR={r.rigida_nbr}  CEB-70={r.rigida_ceb70}")
    print(f"  pd       : {r.p_kncm2:.5f} kN/cm2 ({r.p_kncm2*10:.3f} MPa)")
    print(f"  M1A,d    : {r.M1A_kncm:.0f} kN.cm")
    print(f"  M1B,d    : {r.M1B_kncm:.0f} kN.cm")
    print(f"  As_A     : {r.As_A_cm2:.2f} cm2")
    print(f"  As_B     : {r.As_B_cm2:.2f} cm2")
    print(f"  Diagonal : tau_Sd={r.tau_Sd_MPa:.2f} <= "
          f"tau_Rd2={r.tau_Rd2_MPa:.2f} MPa ({r.ok_diagonal})")


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    _demo()
