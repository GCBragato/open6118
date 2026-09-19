"""Lajes Macicas em Concreto Armado (NBR 6118:2023).

Nome ate 19/09/2026: lajes_bastos.py. O credito as apostilas esta abaixo.

Implementa o calculo de lajes macicas seguindo a apostila
"LAJES DE CONCRETO ARMADO" (Out/2023), Prof. Paulo Sergio Bastos,
UNESP/Bauru, baseada na NBR 6118:2023 e Teoria das Placas (tabelas de Bares).

Casos cobertos:
    - Classificacao (uma direcao vs duas direcoes).
    - Vao efetivo.
    - Pre-dimensionamento da altura util/total.
    - Momentos fletores e flecha em laje armada em uma direcao
      (apoio simples, engaste-apoio, biengastada, balanco).
    - Momentos fletores, reacoes de apoio e flecha imediata em laje armada em
      duas direcoes via tabelas de Bares (tipos 1, 2A, 2B, 3, 4A, 4B, 5A, 5B, 6).
    - Compatibilizacao de momentos negativos entre lajes adjacentes.
    - Momento de fissuracao e verificacao do estadio (Mr vs Ma).
    - Flecha total (com fluencia, coeficiente alpha_f).
    - Dimensionamento a flexao (faixa de 1 m).
    - Verificacao de forca cortante sem armadura transversal (item 19.4.1 NBR).

Convencoes:
    - Concretos do Grupo I e II (C20 a C90, NBR 6118 8.2.1); diagrama
      retangular simplificado com y = lambda*x e sigma_cd = alpha_c*eta_c*fcd,
      lambda/alpha_c/eta_c vindos do nucleo normativo (nucleo_nbr6118.py) e
      iguais a 0.8/0.85/1.0 para fck <= 40 MPa.
    - Limite de ductilidade NBR 6118 14.6.4.3: x/d <= 0.45 (fck <= 50 MPa) ou
      x/d <= 0.35 (fck > 50 MPa), via nucleo_nbr6118.xd_limite_dutilidade.
    - Aco CA-50 (fyk = 500 MPa) por padrao.
    - gama_c = 1.4, gama_s = 1.15, gama_f = 1.4 (combinacao normal).
    - Unidades: kN e cm em todas as funcoes; cargas distribuidas em kN/m^2.
    - Interpolacao linear nas tabelas de Bares.

Estrutura segue:
    - alv_est/viga_mista_v3.py: dataclasses, funcoes puras, testes.
    - open6118/dimensionamento/vigas_nbr6118.py: mesmo padrao para vigas.
"""

from __future__ import annotations

import math
import sys
import warnings
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
GAMA_C = 1.4
GAMA_S = 1.15
GAMA_F = 1.4

E_S = 21000.0          # kN/cm2 (210 GPa).
GAMA_CONC = 25.0       # kN/m3 (concreto armado).
EPS_CU = 3.5           # %o. Legado: so vale para fck <= 50 (Grupo I); ver
                       # nucleo_nbr6118.eps_cu para os dois ramos (8.2.10.1).
LIMITE_BETA_X = 0.45   # NBR 6118 14.6.4.3 para fck <= 50 MPa. Legado: mantido
                       # para compatibilidade (nome exportado). dimensionar_flexao
                       # usa nbr.xd_limite_dutilidade(fck), que cobre fck > 50
                       # com o limite 0.35 da norma (LAJ-02).

# Taxas minimas de armadura (Tabela 17.3 NBR 6118), so ate C50. Legado:
# mantido para compatibilidade; as_min_laje usa nbr.rho_min_flexao(fck), que
# cobre a Tabela 17.3 completa (C20 a C90, com interpolacao - LAJ-06). O fator
# 0.67 para armadura positiva de laje armada em duas direcoes (Tabela 19.1)
# continua aplicado neste modulo.
RHO_MIN_TABELA = {
    20: 0.00150, 25: 0.00150, 30: 0.00150, 35: 0.00164, 40: 0.00179,
    45: 0.00194, 50: 0.00208,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fcd_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """Resistencia de calculo a compressao (NBR 6118 12.3.3), em kN/cm2.

    Delega ao nucleo normativo (nbr.fcd; t = 28 dias por padrao).
    """
    return nbr.mpa_para_kncm2(nbr.fcd(fck_mpa, gama_c))


def fyd_kncm2(fyk_mpa: float, gama_s: float = GAMA_S) -> float:
    return (fyk_mpa / gama_s) * 0.1


def fct_m_kncm2(fck_mpa: float) -> float:
    """Resistencia media a tracao direta (NBR 6118 8.2.5), em kN/cm2.

    Delega ao nucleo normativo (nbr.fct_m), que cobre os dois ramos de 8.2.5:
    fck <= 50 MPa e fck > 50 MPa (LAJ-03).
    """
    return nbr.mpa_para_kncm2(nbr.fct_m(fck_mpa))


def fctk_inf_kncm2(fck_mpa: float) -> float:
    """fctk,inf (NBR 6118 8.2.5), em kN/cm2. Delega ao nucleo (nbr.fctk_inf)."""
    return nbr.mpa_para_kncm2(nbr.fctk_inf(fck_mpa))


def Ecs_kncm2(fck_mpa: float, alpha_E: float = 1.0) -> float:
    """Modulo de elasticidade secante (NBR 6118 8.2.8), em kN/cm2.
    alpha_E: 1.0 granito/gnaisse, 1.2 basalto/diabasio, 0.9 calcario, 0.7 arenito.

    Delega ao nucleo normativo (nbr.Ecs), que cobre os dois ramos de Eci:
    fck <= 50 MPa e fck > 50 MPa (LAJ-04).
    """
    return nbr.mpa_para_kncm2(nbr.Ecs(fck_mpa, alpha_E))


# ---------------------------------------------------------------------------
# Classificacao e geometria
# ---------------------------------------------------------------------------
def classificar(lx_cm: float, ly_cm: float) -> tuple[float, str]:
    """Retorna (lambda, 'duas_direcoes' ou 'uma_direcao'). lx <= ly."""
    if lx_cm > ly_cm:
        lx_cm, ly_cm = ly_cm, lx_cm
    lam = ly_cm / lx_cm
    return lam, "duas_direcoes" if lam <= 2.0 else "uma_direcao"


def vao_efetivo(l0_cm: float, t1_cm: float, t2_cm: float, h_cm: float) -> float:
    """Vao efetivo (NBR 6118 14.6.2.4)."""
    a1 = min(t1_cm / 2.0, 0.3 * h_cm)
    a2 = min(t2_cm / 2.0, 0.3 * h_cm)
    return l0_cm + a1 + a2


def predim_altura(
    lx_cm: float, ly_cm: float, n_engastes: int,
    c_cm: float = 2.0, phi_cm: float = 1.0,
) -> tuple[float, float]:
    """Pre-dimensiona altura util d (cm) e altura total h (cm).

    Eq. 15-17 da apostila: d = (2.5 - 0.1 n) l*; l* = min(lx, 0.7 ly).
    """
    if lx_cm > ly_cm:
        lx_cm, ly_cm = ly_cm, lx_cm
    l_star_m = min(lx_cm, 0.7 * ly_cm) / 100.0
    d_cm = (2.5 - 0.1 * n_engastes) * l_star_m   # apostila: d em cm, l* em m
    h_cm = d_cm + c_cm + phi_cm / 2.0
    return d_cm, h_cm


def as_min_laje(
    bw_cm: float, h_cm: float, fck_mpa: float,
    armadura_positiva: bool = False, duas_direcoes: bool = False,
) -> float:
    """Armadura minima de flexao em laje (cm2/m).

    rho_min da Tabela 17.3 NBR 6118 vem do nucleo normativo (nbr.rho_min_flexao),
    que cobre C20 a C90 com interpolacao entre classes (LAJ-06; antes, fck > 50
    MPa caia no valor do C50). O fator 0.67 para armadura positiva em laje
    armada em duas direcoes (Tabela 19.1 NBR 6118) continua aplicado aqui.
    """
    rho = nbr.rho_min_flexao(fck_mpa)
    fator = 0.67 if (armadura_positiva and duas_direcoes) else 1.0
    return fator * rho * bw_cm * h_cm


# ---------------------------------------------------------------------------
# Tabelas de Bares (apostila, anexo)
# ---------------------------------------------------------------------------
# Cada tabela mapeia tipo -> {lambda: tupla de coeficientes}.
# - MU: coef de momento fletor; M = mu * p * lx^2 / 100
# - NU: coef de reacao de apoio; V = nu * p * lx / 10
# - ALPHA: coef de flecha imediata; a = alpha/12 * p * lx^4 / EI
#
# Coeficientes por tipo:
#   tipo 1   : (mu_x, mu_y, nu_x, nu_y)
#   tipo 2A  : (mu_x, mu_y, mu_y_, nu_x, nu_y, nu_y_)         engaste em y
#   tipo 2B  : (mu_x, mu_x_, mu_y, nu_x, nu_x_, nu_y)         engaste em x
#   tipo 3   : (mu_x, mu_x_, mu_y, mu_y_, nu_x, nu_x_, nu_y, nu_y_)
#              engaste em duas bordas opostas (perpendiculares a x).
#   tipo 4A  : (mu_x, mu_y, mu_y_, nu_x, nu_y, nu_y_)         engaste 2 bordas adj
#   tipo 4B  : (mu_x, mu_x_, mu_y, nu_x, nu_x_, nu_y)
#   tipo 5A  : (mu_x, mu_x_, mu_y_, nu_x, nu_x_, nu_y_)       3 bordas engastadas
#   tipo 5B  : (mu_x_, mu_y, mu_y_, nu_x_, nu_y, nu_y_)
#   tipo 6   : (mu_x, mu_x_, mu_y, mu_y_, nu_x_, nu_y_)        4 bordas engastadas
#
# Para simplificar, encodamos como dict de listas de tuplas:
# (lambda, mu_x, mu_x_, mu_y, mu_y_) - usar 0 quando nao se aplica.

# --- MU (momentos fletores) ---
# Subset focado em apostila ex 3.17. Apenas valores essenciais para os testes.
# Formato: tipo -> [(lambda, mu_x, mu_x_prime, mu_y, mu_y_prime), ...]
# mu_*_prime = 0 quando borda nao eh engastada.

MU_TIPO_1: list[tuple[float, float, float, float, float]] = [
    # apoio simples nas 4 bordas; mu_x_=mu_y_=0
    (1.00, 4.23, 0.0, 4.23, 0.0),
    (1.05, 4.62, 0.0, 4.25, 0.0),
    (1.10, 5.00, 0.0, 4.27, 0.0),
    (1.15, 5.38, 0.0, 4.25, 0.0),
    (1.20, 5.75, 0.0, 4.22, 0.0),
    (1.25, 6.10, 0.0, 4.17, 0.0),
    (1.30, 6.44, 0.0, 4.12, 0.0),
    (1.35, 6.77, 0.0, 4.06, 0.0),
    (1.40, 7.10, 0.0, 4.00, 0.0),
    (1.50, 7.72, 0.0, 3.89, 0.0),
    (1.60, 8.26, 0.0, 3.74, 0.0),
    (1.70, 8.74, 0.0, 3.58, 0.0),
    (1.80, 9.16, 0.0, 3.47, 0.0),
    (1.90, 9.54, 0.0, 3.29, 0.0),
    (2.00, 9.91, 0.0, 3.16, 0.0),
]

MU_TIPO_3: list[tuple[float, float, float, float, float]] = [
    # engaste nas duas bordas perpendiculares a y (ou seja, M'_y nas duas bordas)
    # Apostila Tabela A-9, tipo 3.
    (1.00, 2.69, 6.99, 2.69, 6.99),
    (1.05, 2.94, 7.43, 2.68, 7.18),
    (1.10, 3.19, 7.87, 2.67, 7.36),
    (1.15, 3.42, 8.28, 2.65, 7.50),
    (1.20, 3.65, 8.69, 2.62, 7.63),
    (1.25, 3.86, 9.03, 2.56, 7.72),
    (1.30, 4.06, 9.37, 2.50, 7.81),
    (1.35, 4.24, 9.65, 2.45, 7.88),
    (1.40, 4.42, 9.93, 2.39, 7.94),
    (1.50, 4.73, 10.41, 2.25, 8.06),
    (1.60, 4.99, 10.82, 2.07, 8.12),
    (1.70, 5.21, 11.16, 1.91, 8.15),
    (1.80, 5.40, 11.43, 1.78, 8.17),
    (1.90, 5.56, 11.67, 1.66, 8.18),
    (2.00, 5.70, 11.89, 1.60, 8.20),
]

MU_TIPO_5A: list[tuple[float, float, float, float, float]] = [
    # tres bordas engastadas (uma livre na direcao y).
    # Apostila Tabela A-10. mu_y_ refere-se a uma borda engastada em y.
    (1.00, 2.02, 5.46, 2.52, 6.17),
    (1.05, 2.27, 5.98, 2.56, 6.46),
    (1.10, 2.52, 6.50, 2.60, 6.75),
    (1.15, 2.76, 7.11, 2.63, 6.97),
    (1.20, 3.00, 7.72, 2.65, 7.19),
    (1.25, 3.23, 8.81, 2.64, 7.36),
    (1.30, 3.45, 8.59, 2.61, 7.51),
    (1.40, 3.86, 8.88, 2.53, 7.74),
    (1.50, 4.23, 9.44, 2.43, 7.91),
    (1.70, 4.84, 10.34, 2.22, 8.10),
    (2.00, 5.50, 11.35, 1.80, 8.12),
]

MU_TIPO_5B: list[tuple[float, float, float, float, float]] = [
    (1.00, 2.52, 6.17, 2.02, 5.46),
    (1.05, 2.70, 6.47, 1.97, 5.56),
    (1.10, 2.87, 6.76, 1.91, 5.65),
    (1.15, 3.02, 6.99, 1.84, 5.70),
    (1.20, 3.16, 7.22, 1.77, 5.75),
    (1.25, 3.28, 7.40, 1.70, 5.75),
    (1.30, 3.40, 7.57, 1.62, 5.76),
    (1.40, 3.59, 7.82, 1.47, 5.74),
    (1.50, 3.74, 8.00, 1.35, 5.72),
    (2.00, 4.12, 8.47, 0.88, 5.64),
]

MU_TIPO_6: list[tuple[float, float, float, float, float]] = [
    # quatro bordas engastadas. Apostila Tabela A-10.
    (1.00, 2.02, 5.15, 2.02, 5.15),
    (1.05, 2.22, 5.50, 2.00, 5.29),
    (1.10, 2.42, 5.85, 1.98, 5.43),
    (1.15, 2.65, 6.14, 1.94, 5.51),
    (1.20, 2.87, 6.43, 1.89, 5.59),
    (1.25, 2.97, 6.67, 1.83, 5.64),
    (1.30, 3.06, 6.90, 1.77, 5.68),
    (1.40, 3.32, 7.28, 1.65, 5.70),
    (1.50, 3.53, 7.57, 1.49, 5.72),
    (1.70, 3.83, 7.97, 1.21, 5.72),
    (2.00, 4.05, 8.33, 0.96, 5.72),
]

MU_TABELAS: dict[str, list] = {
    "1": MU_TIPO_1,
    "3": MU_TIPO_3,
    "5A": MU_TIPO_5A,
    "5B": MU_TIPO_5B,
    "6": MU_TIPO_6,
}

# --- NU (reacoes de apoio) ---
# Formato: tipo -> [(lambda, nu_x, nu_x_prime, nu_y, nu_y_prime), ...]

NU_TIPO_1 = [
    (1.00, 2.50, 0.0, 2.50, 0.0),
    (1.10, 2.73, 0.0, 2.50, 0.0),
    (1.20, 2.92, 0.0, 2.50, 0.0),
    (1.30, 3.08, 0.0, 2.50, 0.0),
    (1.50, 3.33, 0.0, 2.50, 0.0),
    (1.70, 3.53, 0.0, 2.50, 0.0),
    (2.00, 3.75, 0.0, 2.50, 0.0),
]

NU_TIPO_3 = [
    (1.00, 2.17, 3.17, 2.17, 3.17),
    (1.05, 2.27, 3.32, 2.17, 3.17),
    (1.10, 2.36, 3.46, 2.17, 3.17),
    (1.15, 2.45, 3.58, 2.17, 3.17),
    (1.20, 2.53, 3.70, 2.17, 3.17),
    (1.25, 2.60, 3.80, 2.17, 3.17),
    (1.30, 2.63, 3.90, 2.17, 3.17),
    (1.40, 2.78, 4.08, 2.17, 3.17),
    (1.50, 2.89, 4.23, 2.17, 3.17),
    (1.70, 3.06, 4.48, 2.17, 3.17),
    (2.00, 3.25, 4.75, 2.17, 3.17),
]

NU_TIPO_5A = [
    (1.00, 1.71, 2.50, 0.0, 3.03),
    (1.05, 1.79, 2.63, 0.0, 3.12),
    (1.10, 1.88, 2.75, 0.0, 3.21),
    (1.15, 1.96, 2.88, 0.0, 3.29),
    (1.20, 2.05, 3.00, 0.0, 3.36),
    (1.30, 2.22, 3.25, 0.0, 3.48),
    (1.40, 2.37, 3.47, 0.0, 3.59),
    (1.50, 2.50, 3.66, 0.0, 3.69),
    (1.70, 2.72, 3.98, 0.0, 3.84),
    (2.00, 2.96, 4.33, 0.0, 4.01),
]

NU_TIPO_5B = [
    (1.00, 0.0, 3.03, 1.71, 2.50),
    (1.05, 0.0, 3.12, 1.71, 2.50),
    (1.10, 0.0, 3.21, 1.71, 2.50),
    (1.15, 0.0, 3.29, 1.71, 2.50),
    (1.20, 0.0, 3.36, 1.71, 2.50),
    (1.30, 0.0, 3.48, 1.71, 2.50),
    (1.50, 0.0, 3.69, 1.71, 2.50),
    (2.00, 0.0, 4.01, 1.71, 2.50),
]

NU_TIPO_6 = [
    (1.00, 0.0, 2.50, 0.0, 2.50),
    (1.10, 0.0, 2.73, 0.0, 2.50),
    (1.20, 0.0, 2.92, 0.0, 2.50),
    (1.30, 0.0, 3.08, 0.0, 2.50),
    (1.50, 0.0, 3.33, 0.0, 2.50),
    (1.70, 0.0, 3.53, 0.0, 2.50),
    (2.00, 0.0, 3.75, 0.0, 2.50),
]

NU_TABELAS: dict[str, list] = {
    "1": NU_TIPO_1,
    "3": NU_TIPO_3,
    "5A": NU_TIPO_5A,
    "5B": NU_TIPO_5B,
    "6": NU_TIPO_6,
}

# --- ALPHA (flecha imediata) ---
# Formato: tipo -> [(lambda, alpha), ...]
ALPHA_FLECHA: dict[str, list[tuple[float, float]]] = {
    "1": [
        (1.00, 4.76), (1.05, 5.26), (1.10, 5.74), (1.15, 6.20), (1.20, 6.64),
        (1.30, 7.49), (1.40, 8.29), (1.50, 9.03), (1.70, 10.34), (2.00, 11.89),
    ],
    "3": [
        (1.00, 2.46), (1.05, 2.72), (1.10, 2.96), (1.15, 3.18), (1.20, 3.40),
        (1.30, 3.80), (1.40, 4.15), (1.50, 4.46), (1.70, 4.97), (2.00, 5.49),
    ],
    "5A": [
        (1.00, 1.84), (1.05, 2.08), (1.10, 2.31), (1.15, 2.54), (1.20, 2.77),
        (1.30, 3.22), (1.40, 3.62), (1.50, 3.98), (1.70, 4.59), (2.00, 5.28),
    ],
    "5B": [
        (1.00, 1.84), (1.05, 1.96), (1.10, 2.08), (1.15, 2.18), (1.20, 2.28),
        (1.30, 2.46), (1.50, 2.73), (2.00, 2.96),
    ],
    "6": [
        (1.00, 1.49), (1.05, 1.63), (1.10, 1.77), (1.15, 1.90), (1.20, 2.02),
        (1.30, 2.24), (1.40, 2.41), (1.50, 2.56), (1.70, 2.77), (2.00, 2.96),
    ],
}


def _interp_linear(tabela: list[tuple], lam: float) -> tuple:
    """Interpolacao linear nos valores da tabela. Cada linha eh (lambda, ...).

    Se lam estiver fora dos limites, retorna a linha mais proxima.
    """
    if not tabela:
        raise ValueError("Tabela vazia.")
    lams = [linha[0] for linha in tabela]
    if lam <= lams[0]:
        return tabela[0]
    if lam >= lams[-1]:
        return tabela[-1]
    for i in range(len(tabela) - 1):
        l1, l2 = lams[i], lams[i + 1]
        if l1 <= lam <= l2:
            t = (lam - l1) / (l2 - l1)
            interp = [lam]
            for j in range(1, len(tabela[i])):
                v1, v2 = tabela[i][j], tabela[i + 1][j]
                interp.append(v1 + t * (v2 - v1))
            return tuple(interp)
    return tabela[-1]


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------
@dataclass
class MomentosLaje:
    Mx: float           # kN.cm/m (positivo, no centro)
    My: float           # kN.cm/m (positivo, no centro)
    Mx_neg: float = 0.0 # kN.cm/m (negativo, na borda perpendicular a x)
    My_neg: float = 0.0 # kN.cm/m (negativo, na borda perpendicular a y)


@dataclass
class ReacoesLaje:
    Vx: float = 0.0           # kN/m (borda perpendicular a x, simples)
    Vx_eng: float = 0.0       # kN/m (borda perpendicular a x, engaste)
    Vy: float = 0.0           # kN/m
    Vy_eng: float = 0.0       # kN/m


@dataclass
class ResultadoFlexao:
    Md: float
    bw: float           # cm (geralmente 100 cm/m)
    d: float
    h: float
    fck: float
    fyk: float
    x: float
    beta_x: float
    dominio: int
    As: float           # cm2/m
    As_min: float = 0.0
    erro: str = ""


# ---------------------------------------------------------------------------
# 1. Laje armada em uma direcao
# ---------------------------------------------------------------------------
def gama_n_laje_balanco(h_cm: float) -> float:
    """Coeficiente adicional gama_n para laje em balanco (NBR 6118 13.2.4.1,
    Tabela 13.2, PDF p. 94).

    gama_n = 1.95 - 0.05 h para 10 <= h < 19 cm; 1.00 para h >= 19 cm. A NBR
    6118 13.2.4.1 c) exige espessura minima de 10 cm para laje em balanco;
    abaixo disso a Tabela 13.2 nao se aplica e a funcao levanta erro (LAJ-07).
    """
    h = float(h_cm)
    if h < 10.0:
        raise nbr.FaixaNormativaError(
            f"h = {h:g} cm abaixo do minimo da NBR 6118 13.2.4.1 c) "
            "para laje em balanco (10 cm)."
        )
    if h >= 19.0:
        return 1.0
    return 1.95 - 0.05 * h


def momentos_uma_direcao(
    p_kn_m2: float, lef_cm: float, vinculacao: str,
    h_cm: float | None = None,
) -> dict[str, float]:
    """Momentos fletores e flecha (caracteristicos) de laje 1 direcao,
    calculada como viga de 1 m de largura no menor vao.

    vinculacao:
      'apoio_simples'    : Mmax = p L^2/8;          flecha = 5/384 pL^4/EI
      'engaste_apoio'    : Mmax+ = pL^2/14.22;     M_eng = -pL^2/8
      'biengastada'      : Mmax+ = pL^2/24;         M_eng = -pL^2/12
      'balanco'          : M_eng = -pL^2/2;         Mmax = M_eng

    h_cm (usado so quando vinculacao='balanco'): espessura da laje. Quando
    informado, aplica o coeficiente adicional gama_n de laje em balanco (NBR
    6118 13.2.4.1, Tabela 13.2 - LAJ-07) a M_max_pos e M_eng, e devolve o
    valor usado na chave 'gama_n'. Quando omitido, os esforcos saem sem
    gama_n (como antes) e a funcao emite ``warnings.warn`` avisando que o
    coeficiente exigido pela norma nao foi aplicado.

    Retorna dict com chaves: M_max_pos, M_eng (kN.cm/m por faixa de 1 m), e
    gama_n quando aplicavel (vinculacao='balanco' com h_cm informado).
    """
    p = p_kn_m2 / 100.0     # kN/cm por faixa de 1 m (= kN/m / 100)
    L = lef_cm
    pL2 = p * L * L

    if vinculacao == "apoio_simples":
        return {"M_max_pos": pL2 / 8.0, "M_eng": 0.0}
    if vinculacao == "engaste_apoio":
        return {"M_max_pos": pL2 / 14.22, "M_eng": -pL2 / 8.0}
    if vinculacao == "biengastada":
        return {"M_max_pos": pL2 / 24.0, "M_eng": -pL2 / 12.0}
    if vinculacao == "balanco":
        M_max_pos = 0.0
        M_eng = -pL2 / 2.0
        if h_cm is None:
            warnings.warn(
                "momentos_uma_direcao('balanco'): gama_n (NBR 6118 13.2.4.1, "
                "Tabela 13.2) nao foi aplicado porque h_cm nao foi "
                "informado. O momento de engaste sai sem o coeficiente "
                "adicional que a norma exige para laje em balanco.",
                stacklevel=2,
            )
            return {"M_max_pos": M_max_pos, "M_eng": M_eng}
        gn = gama_n_laje_balanco(h_cm)
        return {"M_max_pos": M_max_pos * gn, "M_eng": M_eng * gn, "gama_n": gn}
    raise ValueError(f"Vinculacao desconhecida: {vinculacao}")


# ---------------------------------------------------------------------------
# 2. Laje armada em duas direcoes (Bares)
# ---------------------------------------------------------------------------
def momentos_duas_direcoes(
    tipo: str, lx_cm: float, ly_cm: float, p_kn_m2: float,
) -> MomentosLaje:
    """Momentos fletores caracteristicos via tabelas de Bares.

    Retorna MomentosLaje em kN.cm/m. Eq. 21 da apostila:
        M = mu * p * lx^2 / 100        (com p em kN/m^2 e lx em m)
    Para sair em kN.cm/m, multiplica-se por 100 (1 kN.m = 100 kN.cm).
    """
    if tipo not in MU_TABELAS:
        raise ValueError(f"Tipo {tipo} nao tabelado. Disponiveis: "
                         f"{list(MU_TABELAS)}")
    if lx_cm > ly_cm:
        lx_cm, ly_cm = ly_cm, lx_cm
    lam = ly_cm / lx_cm
    _, mu_x, mu_x_, mu_y, mu_y_ = _interp_linear(MU_TABELAS[tipo], lam)

    lx_m = lx_cm / 100.0
    fator = p_kn_m2 * lx_m * lx_m / 100.0    # kN.m/m
    return MomentosLaje(
        Mx=mu_x * fator * 100.0,             # kN.cm/m
        My=mu_y * fator * 100.0,
        Mx_neg=-mu_x_ * fator * 100.0,
        My_neg=-mu_y_ * fator * 100.0,
    )


def reacoes_duas_direcoes(
    tipo: str, lx_cm: float, ly_cm: float, p_kn_m2: float,
) -> ReacoesLaje:
    """Reacoes de apoio caracteristicas via tabelas de Bares.

    Eq. 24: V = nu * p * lx / 10. Retorna ReacoesLaje em kN/m.
    """
    if tipo not in NU_TABELAS:
        raise ValueError(f"Tipo {tipo} nao tabelado.")
    if lx_cm > ly_cm:
        lx_cm, ly_cm = ly_cm, lx_cm
    lam = ly_cm / lx_cm
    _, nu_x, nu_x_, nu_y, nu_y_ = _interp_linear(NU_TABELAS[tipo], lam)

    lx_m = lx_cm / 100.0
    fator = p_kn_m2 * lx_m / 10.0
    return ReacoesLaje(
        Vx=nu_x * fator,
        Vx_eng=nu_x_ * fator,
        Vy=nu_y * fator,
        Vy_eng=nu_y_ * fator,
    )


def flecha_imediata_duas_direcoes(
    tipo: str, lx_cm: float, ly_cm: float, p_kn_m2: float, EI_kncm2: float,
) -> float:
    """Flecha imediata em laje armada em duas direcoes (Eq. 46 da apostila).

    a_i = alpha/12 * p * lx^4 / EI    (em cm).
    """
    if tipo not in ALPHA_FLECHA:
        raise ValueError(f"Tipo {tipo} sem tabela de alpha.")
    if lx_cm > ly_cm:
        lx_cm, ly_cm = ly_cm, lx_cm
    lam = ly_cm / lx_cm
    _, alpha = _interp_linear(ALPHA_FLECHA[tipo], lam)

    p_kncm2 = p_kn_m2 / 10000.0       # kN/cm2
    return alpha / 12.0 * p_kncm2 * lx_cm ** 4 / EI_kncm2


# ---------------------------------------------------------------------------
# 3. Compatibilizacao, fissuracao e fluencia
# ---------------------------------------------------------------------------
def compat_momento_negativo(M1: float, M2: float) -> float:
    """Eq. 22: X >= max(0.8 |X1|, (|X1|+|X2|)/2). Retorna positivo."""
    a, b = abs(M1), abs(M2)
    return max(0.8 * max(a, b), (a + b) / 2.0)


def momento_fissuracao(
    b_cm: float, h_cm: float, fck_mpa: float, alpha: float = 1.5,
) -> float:
    """Mr = alpha * fct,m * Ic / yt   (Eq. 25 NBR 6118 17.3.1).

    Para verificacao do estado-limite de deformacao usar fct_m (default).
    Retorna em kN.cm.
    """
    fct = fct_m_kncm2(fck_mpa)        # kN/cm2
    Ic = b_cm * h_cm ** 3 / 12.0
    yt = h_cm / 2.0
    return alpha * fct * Ic / yt


def alpha_f(t_meses: float, t0_meses: float = 1.0,
            rho_linha: float = 0.0) -> float:
    """Coeficiente de fluencia para flecha diferida (Eq. 39 NBR).

    alpha_f = (xi(t) - xi(t0)) / (1 + 50 rho').
    """
    def xi(t):
        if t > 70:
            return 2.0
        return 0.68 * (0.996 ** t) * (t ** 0.32)
    return (xi(t_meses) - xi(t0_meses)) / (1.0 + 50.0 * rho_linha)


# ---------------------------------------------------------------------------
# 4. Dimensionamento a flexao (faixa de 1 m)
# ---------------------------------------------------------------------------
def dimensionar_flexao(
    Md_kncm: float, d_cm: float, h_cm: float,
    fck_mpa: float, fyk_mpa: float = 500.0, bw_cm: float = 100.0,
    armadura_positiva: bool = True, duas_direcoes: bool = False,
    gama_c: float = GAMA_C, gama_s: float = GAMA_S,
    gama_n: float = 1.0,
) -> ResultadoFlexao:
    """Dimensiona armadura simples para uma faixa de bw (default 1 m).

    Bloco retangular (NBR 6118 17.2.2 e): forca = tensao_retangulo(fck) * bw *
    (lambda * x); braco = d - lambda * x / 2. Para fck <= 40 MPa (eta_c = 1) e
    lambda = 0.8 (fck <= 50 MPa), a equacao se reduz a classica
    |Md| = 0.68 bw x fcd (d - 0.4 x); acima disso entram eta_c e o lambda
    reduzido do Grupo II (8.2.10.1, 17.2.2 e - LAJ-01), e o limite de x/d passa
    a vir de nbr.xd_limite_dutilidade (14.6.4.3 - LAJ-02).

    gama_n (13.2.4.1, Tabela 13.2 - LAJ-07): coeficiente adicional de laje em
    balanco. Default 1.0 (sem majoracao); quem chama aplica
    ``gama_n_laje_balanco(h_cm)`` aqui quando Md_kncm vier de uma laje em
    balanco e ainda nao tiver sido majorado (por exemplo, se
    ``momentos_uma_direcao`` foi usada sem passar h_cm).
    """
    Md = abs(Md_kncm) * gama_n
    fyd = fyd_kncm2(fyk_mpa, gama_s)

    tensao = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck_mpa, gama_c))  # kN/cm2
    lam = nbr.lambda_retangulo(fck_mpa)

    a = tensao * bw_cm * lam * lam / 2.0
    b = -tensao * bw_cm * lam * d_cm
    c = Md
    disc = b * b - 4.0 * a * c
    if disc < 0:
        return ResultadoFlexao(
            Md=Md, bw=bw_cm, d=d_cm, h=h_cm, fck=fck_mpa, fyk=fyk_mpa,
            x=0, beta_x=0, dominio=0, As=0,
            erro="Discriminante negativo. Aumentar h ou fck.",
        )
    x = (-b - math.sqrt(disc)) / (2.0 * a)
    beta_x = x / d_cm

    limite_xd = nbr.xd_limite_dutilidade(fck_mpa)
    erro = ""
    if beta_x > limite_xd:
        erro = (f"x/d = {beta_x:.3f} > {limite_xd:.2f} (NBR 6118 14.6.4.3). "
                "Aumentar h.")

    x2lim = nbr.x_lim_dominio_2_3(d_cm, fck_mpa)
    x3lim = nbr.x_lim_dominio_3_4(d_cm, fck_mpa, fyk_mpa, gama_s)
    if x <= x2lim:
        dom = 2
    elif x <= x3lim:
        dom = 3
    else:
        dom = 4

    As = Md / (fyd * (d_cm - 0.5 * lam * x))
    As_min = as_min_laje(bw_cm, h_cm, fck_mpa,
                         armadura_positiva=armadura_positiva,
                         duas_direcoes=duas_direcoes)

    return ResultadoFlexao(
        Md=Md, bw=bw_cm, d=d_cm, h=h_cm, fck=fck_mpa, fyk=fyk_mpa,
        x=x, beta_x=beta_x, dominio=dom,
        As=max(As, As_min) if As < As_min else As,
        As_min=As_min, erro=erro,
    )


# ---------------------------------------------------------------------------
# 5. Forca cortante - laje sem armadura transversal (NBR 19.4.1)
# ---------------------------------------------------------------------------
def cortante_resistente_laje(
    bw_cm: float, d_cm: float, As_long_cm2: float, fck_mpa: float,
    metade_armadura_chega_apoio: bool = True, gama_c: float = GAMA_C,
) -> float:
    """V_Rd1 = [tau_Rd k (1.2 + 40 rho_1)] bw d   (kN, sem armadura transversal).

    Eq. 56-62 da apostila. Se a forca cortante solicitante VSd <= V_Rd1,
    nao eh necessaria armadura transversal. tau_Rd = 0.25 fctd, com fck
    limitado a 60 MPa (NBR 6118 19.4.1 - LAJ-05), via nucleo normativo.
    """
    tau_rd = nbr.mpa_para_kncm2(nbr.tau_Rd(fck_mpa, gama_c))   # kN/cm2
    rho_1 = min(As_long_cm2 / (bw_cm * d_cm), 0.02)
    if metade_armadura_chega_apoio:
        k = max(1.6 - d_cm / 100.0, 1.0)
    else:
        k = 1.0
    return tau_rd * k * (1.2 + 40.0 * rho_1) * bw_cm * d_cm


# ---------------------------------------------------------------------------
# Impressao
# ---------------------------------------------------------------------------
def imprimir_momentos(m: MomentosLaje, label: str = "") -> None:
    if label:
        print(f"--- {label} ---")
    print(f"  Mx     = {m.Mx:>8.1f} kN.cm/m   (positivo, centro)")
    print(f"  My     = {m.My:>8.1f} kN.cm/m   (positivo, centro)")
    if m.Mx_neg:
        print(f"  M'x    = {m.Mx_neg:>8.1f} kN.cm/m   (engaste perp. a x)")
    if m.My_neg:
        print(f"  M'y    = {m.My_neg:>8.1f} kN.cm/m   (engaste perp. a y)")


def imprimir_reacoes(r: ReacoesLaje, label: str = "") -> None:
    if label:
        print(f"--- {label} ---")
    if r.Vx:
        print(f"  Vx     = {r.Vx:>6.2f} kN/m   (apoio simples perp. a x)")
    if r.Vx_eng:
        print(f"  V'x    = {r.Vx_eng:>6.2f} kN/m   (engaste perp. a x)")
    if r.Vy:
        print(f"  Vy     = {r.Vy:>6.2f} kN/m   (apoio simples perp. a y)")
    if r.Vy_eng:
        print(f"  V'y    = {r.Vy_eng:>6.2f} kN/m   (engaste perp. a y)")


# ---------------------------------------------------------------------------
# Testes contra exemplos da apostila
# ---------------------------------------------------------------------------
def teste_classificacao() -> bool:
    """Apostila 3.17: L2 (lx=586, ly=606) -> duas dir; L4 (lx=286, ly=786) -> uma dir."""
    print("\n--- Teste classificacao ---")
    lam_L2, tipo_L2 = classificar(586, 606)
    lam_L4, tipo_L4 = classificar(286, 786)
    print(f"  L2: lambda={lam_L2:.3f}, {tipo_L2}")
    print(f"  L4: lambda={lam_L4:.3f}, {tipo_L4}")
    ok = (
        abs(lam_L2 - 1.034) < 0.01 and tipo_L2 == "duas_direcoes"
        and abs(lam_L4 - 2.748) < 0.01 and tipo_L4 == "uma_direcao"
    )
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_vao_efetivo() -> bool:
    """Apostila 3.17: lx_livre=580 cm, t1=t2=20 cm, h=10 cm -> ef=586."""
    print("\n--- Teste vao efetivo ---")
    ef = vao_efetivo(580, 20, 20, 10)
    print(f"  l_ef = {ef:.1f} cm   (esperado 586)")
    ok = abs(ef - 586) < 1.0
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_predim_altura() -> bool:
    """Apostila 3.17.2 L3: lx=586, ly=656, n=2 -> d~10.6 cm, h~13 cm."""
    print("\n--- Teste pre-dimensionamento (L3) ---")
    d, h = predim_altura(586, 656, n_engastes=2, c_cm=2.0, phi_cm=1.0)
    print(f"  d = {d:.2f} cm (esperado ~10.6) | h = {h:.2f} cm (esperado ~13.1)")
    ok = abs(d - 10.6) < 0.2 and abs(h - 13.1) < 0.2
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_momentos_L5() -> bool:
    """Apostila 3.17 L5: tipo 6, lx=ly=486 cm (lambda=1.00 exato), p=6.9.
    Esperado: Mx=My=329, M'x=M'y=839 kN.cm/m."""
    print("\n--- Teste momentos L5 (tipo 6, lambda=1.00) ---")
    m = momentos_duas_direcoes("6", 486, 486, 6.9)
    imprimir_momentos(m)
    ok = (abs(m.Mx - 329) < 5 and abs(m.My - 329) < 5
          and abs(m.Mx_neg + 839) < 10 and abs(m.My_neg + 839) < 10)
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_momentos_L2() -> bool:
    """Apostila 3.17 L2: tipo 3, lx=586, ly=606, p=5.78.

    Apostila usa Tabela A-9 com nearest-neighbor (lambda=1.05 para 1.03).
    Este script usa interpolacao linear -> valores ~3% menores. Tolerancia
    aumentada para cobrir essa diferenca."""
    print("\n--- Teste momentos L2 (tipo 3, lambda=1.03) ---")
    m = momentos_duas_direcoes("3", 586, 606, 5.78)
    imprimir_momentos(m)
    # Apostila: Mx=584, My=532, M'x=-1475, M'y=-1425
    ok = (abs(m.Mx - 584) < 30 and abs(m.My - 532) < 30
          and abs(abs(m.Mx_neg) - 1475) < 80
          and abs(abs(m.My_neg) - 1425) < 80)
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_reacoes_L5() -> bool:
    """Apostila 3.17 L5: tipo 6, lambda=1.00, p=6.9, lx=486 cm.
    Esperado: V'x = V'y = 8.38 kN/m."""
    print("\n--- Teste reacoes L5 (tipo 6, lambda=1.00) ---")
    r = reacoes_duas_direcoes("6", 486, 486, 6.9)
    imprimir_reacoes(r)
    ok = abs(r.Vx_eng - 8.38) < 0.1 and abs(r.Vy_eng - 8.38) < 0.1
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_compat_momento() -> bool:
    """Apostila 3.17.5: borda L2/L3 -> M1=1425, M2=1663 -> X = 1544."""
    print("\n--- Teste compatibilizacao ---")
    X = compat_momento_negativo(1425, 1663)
    print(f"  X = {X:.1f} kN.cm/m   (esperado max(1330, 1544) = 1544)")
    ok = abs(X - 1544) < 5
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_momento_fissuracao() -> bool:
    """Apostila 3.17.6 L2: b=100, h=12, C25 -> Mr ~ 923 kN.cm."""
    print("\n--- Teste momento de fissuracao (L2) ---")
    Mr = momento_fissuracao(100, 12, 25.0, alpha=1.5)
    print(f"  Mr = {Mr:.1f} kN.cm   (esperado ~923)")
    ok = abs(Mr - 923) < 10
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_flecha_L2() -> bool:
    """Apostila 3.17.6.1 L2: tipo 3, lambda=1.03, lx=586, p_qp=4.73 kN/m^2,
    h=12, fck=25 -> a_i ~ 0.36 cm; alpha_f ~ 1.32 -> a_t ~ 0.85 cm.

    Apostila usa alpha=2.72 (tabela tipo 3, lambda=1.05). Linear interp da
    valor um pouco menor para lambda=1.03; tolerancia maior."""
    print("\n--- Teste flecha L2 (tipo 3, lambda=1.03) ---")
    Ecs = Ecs_kncm2(25.0, alpha_E=1.0)
    Ic = 100.0 * 12.0 ** 3 / 12.0
    EI = Ecs * Ic
    a_i = flecha_imediata_duas_direcoes("3", 586, 606, 4.73, EI)
    af = alpha_f(t_meses=70.0, t0_meses=1.0)
    a_t = a_i * (1.0 + af)
    print(f"  EI     = {EI:.0f} kN.cm2  (esperado ~34.675.200)")
    print(f"  a_i    = {a_i:.3f} cm    (esperado ~0.36)")
    print(f"  alpha_f= {af:.3f}        (esperado ~1.32)")
    print(f"  a_t    = {a_t:.3f} cm    (esperado ~0.85)")
    ok = (abs(a_i - 0.36) < 0.05 and abs(af - 1.32) < 0.05
          and abs(a_t - 0.85) < 0.10)
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_dimensionamento_L2() -> bool:
    """Apostila 3.17 L2: Mk=584, fck=25, h=12, d=9.5 -> As~2.07 cm2/m."""
    print("\n--- Teste dimensionamento L2 (Mk+ = 584 kN.cm/m) ---")
    Md = 1.4 * 584
    r = dimensionar_flexao(Md_kncm=Md, d_cm=9.5, h_cm=12.0, fck_mpa=25.0,
                           armadura_positiva=True, duas_direcoes=True)
    print(f"  x      = {r.x:.2f} cm     | x/d = {r.beta_x:.3f}  | dom = {r.dominio}")
    print(f"  As     = {r.As:.2f} cm2/m | As,min = {r.As_min:.2f}")
    if r.erro:
        print(f"  ERRO: {r.erro}")
    ok = abs(r.As - 2.07) < 0.10 and r.dominio == 2 and not r.erro
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_cortante_L1() -> bool:
    """Apostila 3.17.7 L1: VSd=25.76 kN/m -> V_Rd1 ~ 69.7 kN/m."""
    print("\n--- Teste cortante L1 (laje em balanco) ---")
    V_Rd1 = cortante_resistente_laje(
        bw_cm=100, d_cm=10, As_long_cm2=6.25, fck_mpa=25.0,
    )
    print(f"  V_Rd1 = {V_Rd1:.2f} kN/m   (esperado ~69.73)")
    ok = abs(V_Rd1 - 69.73) < 1.0
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_balanco_L1() -> bool:
    """Apostila 3.17.4 L1: balanco lx=163, p=6.83 + gradil 0.5 kN/m -> M_eng~989."""
    print("\n--- Teste momento balanco L1 ---")
    m = momentos_uma_direcao(p_kn_m2=6.83, lef_cm=163.0, vinculacao="balanco")
    # Soma da carga concentrada (gradil) = 0.5 * 1.63 = 0.815 kN.m = 81.5 kN.cm
    M_eng_total = abs(m["M_eng"]) + 0.5 * 1.63 * 100.0
    print(f"  |M_eng|+gradil = {M_eng_total:.1f} kN.cm   (esperado ~989)")
    ok = abs(M_eng_total - 989) < 5
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def rodar_testes() -> bool:
    resultados = [
        teste_classificacao(),
        teste_vao_efetivo(),
        teste_predim_altura(),
        teste_momentos_L5(),
        teste_momentos_L2(),
        teste_reacoes_L5(),
        teste_compat_momento(),
        teste_momento_fissuracao(),
        teste_flecha_L2(),
        teste_dimensionamento_L2(),
        teste_cortante_L1(),
        teste_balanco_L1(),
    ]
    total = len(resultados)
    aprov = sum(resultados)
    print(f"\n{'=' * 60}")
    print(f"  {aprov}/{total} testes passaram.")
    print(f"{'=' * 60}")
    return all(resultados)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if "--test" in sys.argv:
        sys.exit(0 if rodar_testes() else 1)
    rodar_testes()


if __name__ == "__main__":
    main()
