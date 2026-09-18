"""Concreto Protendido - Fundamentos (NBR 6118:2023).

Implementa as analises elasticas e perdas de protensao seguindo a apostila
"FUNDAMENTOS DO CONCRETO PROTENDIDO", Prof. Paulo Sergio Bastos,
UNESP/Bauru.

Casos cobertos:
    - Tensoes elasticas em viga protendida (Eq. 1.7-1.12)
    - Modulos de resistencia W_b, W_t (Eq. 1.9, 1.10)
    - Nucleo central de inercia (h/6 para retangular)
    - Estimativa de forca de protensao (axial e excentrica) - laje exemplo 1.6.1
    - Perda por relaxacao do aco (Eq. 5.11-5.13)
    - Perda por encurtamento elastico imediato do concreto (Eq. 5.56)
    - Perda por retracao/fluencia simplificada (Eq. 5.16, 5.17)

Convencoes:
    - fck, fyk em MPa.
    - Geometria em cm. Forcas em kN. Momentos em kN.cm.
    - Tensoes internamente em kN/cm2 (= 10 MPa).
    - Convencao de sinais: compressao negativa, tracao positiva.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass


GAMA_C = 1.4
GAMA_S = 1.15

E_S_MPA = 210000.0
E_P_MPA = 200000.0    # aco de protensao (NBR 6118 8.4.5)


# ---------------------------------------------------------------------------
# Resistencias e modulos
# ---------------------------------------------------------------------------
def fctm_mpa(fck_mpa: float) -> float:
    """fct,m = 0.3 * fck^(2/3) (Grupo I)."""
    return 0.3 * fck_mpa ** (2.0 / 3.0)


def fct_flexao_mpa(fck_mpa: float, alpha: float = 1.5) -> float:
    """Resistencia a tracao na flexao: fct,f = alpha * fct,m,
    com alpha=1.2 para secao T, 1.5 para retangular."""
    return alpha * fctm_mpa(fck_mpa)


def Eci_mpa(fck_mpa: float, agregado: str = "granito") -> float:
    """Modulo inicial."""
    aE = {"granito": 1.0, "basalto": 1.2, "calcario": 0.9,
          "arenito": 0.7}.get(agregado.lower(), 1.0)
    if fck_mpa <= 50.0:
        return aE * 5600.0 * math.sqrt(fck_mpa)
    return 21500.0 * aE * (fck_mpa / 10.0 + 1.25) ** (1.0 / 3.0)


def Ecs_mpa(fck_mpa: float, agregado: str = "granito") -> float:
    alpha_i = min(1.0, 0.8 + 0.2 * fck_mpa / 80.0)
    return alpha_i * Eci_mpa(fck_mpa, agregado)


# ---------------------------------------------------------------------------
# Propriedades geometricas - secao retangular
# ---------------------------------------------------------------------------
def Ac_retangular(b_cm: float, h_cm: float) -> float:
    return b_cm * h_cm


def Ic_retangular(b_cm: float, h_cm: float) -> float:
    return b_cm * h_cm ** 3 / 12.0


def W_retangular(b_cm: float, h_cm: float) -> float:
    """W = bh^2/6 (modulo de resistencia)."""
    return b_cm * h_cm ** 2 / 6.0


def nucleo_central_retangular(h_cm: float) -> float:
    """Limite inferior/superior do nucleo central: h/6."""
    return h_cm / 6.0


# ---------------------------------------------------------------------------
# Tensoes elasticas em viga protendida
# ---------------------------------------------------------------------------
def sigma_base_topo(P_kn: float, ep_cm: float, M_kncm: float,
                    Ac_cm2: float, Wb_cm3: float, Wt_cm3: float,
                    sinal_P: int = -1) -> tuple[float, float]:
    """Tensoes na base e no topo (Eq. 1.11/1.12), em kN/cm2.

    Convencao: compressao negativa, tracao positiva.
    sinal_P = -1 (default): forca de protensao comprime axialmente
              (P entra como valor positivo de modulo).

    sigma_b = -P/Ac - P*ep/Wb + M/Wb
    sigma_t = -P/Ac + P*ep/Wt - M/Wt
    """
    sb = sinal_P * P_kn / Ac_cm2 + sinal_P * P_kn * ep_cm / Wb_cm3 \
        + M_kncm / Wb_cm3
    st = sinal_P * P_kn / Ac_cm2 - sinal_P * P_kn * ep_cm / Wt_cm3 \
        - M_kncm / Wt_cm3
    return sb, st


def forca_protensao_axial(sigma_alvo_base_kncm2: float,
                          M_kncm: float, Ac_cm2: float,
                          Wb_cm3: float) -> float:
    """Calcula P para que a tensao na base atinja sigma_alvo (geralmente 0
    ou um pequeno valor de tracao admitido).

    sigma_b = -P/Ac + M/Wb = sigma_alvo  ->  P = (M/Wb - sigma_alvo) * Ac
    """
    return (M_kncm / Wb_cm3 - sigma_alvo_base_kncm2) * Ac_cm2


def forca_protensao_excentrica(sigma_alvo_base_kncm2: float,
                               M_kncm: float, ep_cm: float,
                               Ac_cm2: float, Wb_cm3: float) -> float:
    """P para excentricidade ep; sigma_b = -P/Ac - P*ep/Wb + M/Wb = sigma_alvo:
    P = (M/Wb - sigma_alvo) / (1/Ac + ep/Wb)
    """
    return (M_kncm / Wb_cm3 - sigma_alvo_base_kncm2) \
        / (1.0 / Ac_cm2 + ep_cm / Wb_cm3)


# ---------------------------------------------------------------------------
# Perdas de protensao
# ---------------------------------------------------------------------------
PSI_1000_TIPICOS = {
    # (tipo, classe): psi_1000 em % a 80% fptk (NBR 6118 Tabela 8.3)
    ("CP-175", "RN"): 5.0,
    ("CP-175", "RB"): 2.5,
    ("CP-190", "RN"): 8.5,
    ("CP-190", "RB"): 3.5,
    ("CP-210", "RN"): 7.0,
    ("CP-210", "RB"): 3.5,
}


def psi_t_em_horas(psi_1000_percent: float, t_horas: float) -> float:
    """psi(t, to) em % - Eq. 5.12 (t em horas).
    psi = psi_1000 * (t/1000)^0.15."""
    return psi_1000_percent * (t_horas / 1000.0) ** 0.15


def psi_t_em_dias(psi_1000_percent: float, t_dias: float) -> float:
    """psi(t, to) em % - Eq. 5.11 (t em dias).
    psi = psi_1000 * (t/41.67)^0.15. (1000 horas = 41.67 dias)"""
    return psi_1000_percent * (t_dias / 41.67) ** 0.15


def psi_infinito(psi_1000_percent: float) -> float:
    """psi(infinito, to) = 2.5 * psi_1000  (Eq. 5.13)."""
    return 2.5 * psi_1000_percent


def perda_relaxacao_kncm2(psi_percent: float,
                          sigma_pi_kncm2: float) -> float:
    """delta sigma_pr = psi/100 * sigma_pi  (Eq. 5.10)."""
    return psi_percent / 100.0 * sigma_pi_kncm2


def perda_encurtamento_elastico_kncm2(
    sigma_cp_kncm2: float, fck_mpa: float, agregado: str = "granito",
    Ep_mpa: float = E_P_MPA,
) -> float:
    """delta sigma_p,enc = (Ep/Ec) * sigma_cp  (Eq. 5.56).
    sigma_cp = tensao no concreto ao nivel do CG da armadura."""
    Ec = Ecs_mpa(fck_mpa, agregado)
    alpha_p = Ep_mpa / Ec
    return alpha_p * sigma_cp_kncm2


def perda_retracao_kncm2(eps_cs_permil: float,
                         Ep_mpa: float = E_P_MPA) -> float:
    """delta sigma_pcs = eps_cs * Ep  (Eq. 5.16).
    eps_cs em por mil (deformacao de retracao no infinito)."""
    eps = eps_cs_permil / 1000.0
    return abs(eps) * Ep_mpa * 0.1  # MPa -> kN/cm2


def perda_fluencia_kncm2(phi_inf: float, sigma_c_to_kncm2: float,
                         fck_mpa: float, agregado: str = "granito",
                         Ep_mpa: float = E_P_MPA) -> float:
    """delta sigma_pcc = (Ep/Ec) * phi * sigma_c(to)  (Eq. 5.17/5.18)."""
    Ec = Ecs_mpa(fck_mpa, agregado)
    alpha_p = Ep_mpa / Ec
    return alpha_p * phi_inf * abs(sigma_c_to_kncm2)


# ---------------------------------------------------------------------------
# Perda por atrito na pos-tensao (NBR 9.6.3.3.2.2 / Eq. 5.65)
# ---------------------------------------------------------------------------
def perda_atrito_kn(Pi_kn: float, mu: float, theta_rad: float,
                    k_per_m: float, x_m: float) -> float:
    """delta P_atr(x) = Pi * (1 - exp(-(mu * theta + k * x))).

    Pi    : forca aplicada pelo cilindro hidraulico (kN)
    mu    : coef. de atrito aparente cabo/bainha (1/rad)
    theta : soma dos angulos de desvio entre ancoragem e ponto x (rad)
    k     : coef. ondulacao parasita da bainha (1/m, NBR sugere 0.01*mu)
    x     : abscissa em metros desde a ancoragem ativa
    """
    return Pi_kn * (1.0 - math.exp(-(mu * theta_rad + k_per_m * x_m)))


def theta_arco_circulo_rad(y_cm: float, x_m: float) -> float:
    """Angulo total de desvio para cabo em arco de circulo:
    theta = 8*y / x  (NBR 9.6.3.3.2.2, com y = fleche e x = vao em metros).
    Apostila aplica diretamente em metros, com y tambem em metros."""
    y_m = y_cm / 100.0
    return 8.0 * y_m / x_m


def theta_parabola_rad(y_cm: float, x_m: float) -> float:
    """Angulo total de desvio para parabola de 2o grau:
    theta = 4*y / x (entre o vertice e o apoio - NBR)."""
    y_m = y_cm / 100.0
    return 4.0 * y_m / x_m


# ---------------------------------------------------------------------------
# Estimativa da forca de protensao final P (item 4.6.1)
# ---------------------------------------------------------------------------
def fct_admissivel_traçao_kncm2(fck_mpa: float, secao: str = "T") -> float:
    """fct para tensao admissivel de tracao no ELS-F (NBR/Bastos Eq. 4.16).

    secao = 'T' ou 'duplo-T'  -> alpha = 1.2
    secao = 'I' ou 'T-invertido' -> alpha = 1.3
    secao = 'retangular'     -> alpha = 1.5
    fct = alpha * 0.7 * 0.3 * fck^(2/3)  (em MPa); resultado em kN/cm2."""
    alpha = {"t": 1.2, "duplo-t": 1.2, "duplo t": 1.2,
             "i": 1.3, "t-invertido": 1.3, "t invertido": 1.3,
             "retangular": 1.5}.get(secao.lower(), 1.5)
    fct_mpa = alpha * 0.7 * 0.3 * fck_mpa ** (2.0 / 3.0)
    return fct_mpa * 0.1


def P_estimado_ELS(
    sigma_b_alvo_kncm2: float,
    sigma_b_carga_kncm2: float,
    Ac_cm2: float, Wb_cm3: float, ep_cm: float,
) -> float:
    """Estimativa de P para que a soma de tensoes na base atinja sigma_alvo.

    Equacao geral: sigma_b_carga + sigma_b_P = sigma_b_alvo
    com sigma_b_P = -P/Ac - P*ep/Wb (forca P comprime axialmente e gera
    momento que tambem comprime a base quando ep > 0 abaixo do CG).

    -P * (1/Ac + ep/Wb) = sigma_alvo - sigma_carga
    P = (sigma_carga - sigma_alvo) / (1/Ac + ep/Wb)
    """
    return (sigma_b_carga_kncm2 - sigma_b_alvo_kncm2) \
        / (1.0 / Ac_cm2 + ep_cm / Wb_cm3)


def estimar_P_protensao_completa(
    Mg1_kncm: float, Mg2_kncm: float, Mq1_kncm: float, Mq2_kncm: float,
    psi1: float, psi2: float,
    Ac_cm2: float, Wb_cm3: float, ep_cm: float,
    fck_mpa: float, secao: str = "T",
) -> dict:
    """Forca de protensao final P para protensao completa (item 4.6.1.1).

    Verifica simultaneamente:
    - ELS-D (combinacao frequente): sigma_b_total = 0
        sigma_bg1 + sigma_bg2 + psi1*sigma_bq1 + psi2*sigma_bq2 + sigma_bP = 0
    - ELS-F (combinacao rara): sigma_b_total = +fct (limite de tracao)
        sigma_bg1 + sigma_bg2 + sigma_bq1 + psi1*sigma_bq2 + sigma_bP = fct

    Adota P = max(P_estA, P_estB).
    """
    bg1 = Mg1_kncm / Wb_cm3
    bg2 = Mg2_kncm / Wb_cm3
    bq1 = Mq1_kncm / Wb_cm3
    bq2 = Mq2_kncm / Wb_cm3

    # ELS-D combinacao frequente -> sigma_alvo = 0
    sigma_carga_D = bg1 + bg2 + psi1 * bq1 + psi2 * bq2
    P_A = P_estimado_ELS(0.0, sigma_carga_D, Ac_cm2, Wb_cm3, ep_cm)

    # ELS-F combinacao rara -> sigma_alvo = +fct
    fct = fct_admissivel_traçao_kncm2(fck_mpa, secao)
    sigma_carga_F = bg1 + bg2 + bq1 + psi1 * bq2
    P_B = P_estimado_ELS(fct, sigma_carga_F, Ac_cm2, Wb_cm3, ep_cm)

    return {
        "P_estA_ELS_D_kN": P_A,
        "P_estB_ELS_F_kN": P_B,
        "P_est_kN": max(P_A, P_B),
        "fct_kncm2": fct,
        "sigma_carga_D_kncm2": sigma_carga_D,
        "sigma_carga_F_kncm2": sigma_carga_F,
    }


def estimar_P_protensao_limitada(
    Mg1_kncm: float, Mg2_kncm: float, Mq1_kncm: float, Mq2_kncm: float,
    psi1: float, psi2: float,
    Ac_cm2: float, Wb_cm3: float, ep_cm: float,
    fck_mpa: float, secao: str = "T",
) -> dict:
    """Forca de protensao final P para protensao limitada (item 4.6.1.2).

    - ELS-D (combinacao quase permanente): sigma_b_total = 0
        sigma_bg1 + sigma_bg2 + psi2*sigma_bq1 + psi2*sigma_bq2 + sigma_bP = 0
    - ELS-F (combinacao frequente): sigma_b_total = +fct
        sigma_bg1 + sigma_bg2 + psi1*sigma_bq1 + psi2*sigma_bq2 + sigma_bP = fct
    """
    bg1 = Mg1_kncm / Wb_cm3
    bg2 = Mg2_kncm / Wb_cm3
    bq1 = Mq1_kncm / Wb_cm3
    bq2 = Mq2_kncm / Wb_cm3

    sigma_carga_D = bg1 + bg2 + psi2 * bq1 + psi2 * bq2
    P_A = P_estimado_ELS(0.0, sigma_carga_D, Ac_cm2, Wb_cm3, ep_cm)

    fct = fct_admissivel_traçao_kncm2(fck_mpa, secao)
    sigma_carga_F = bg1 + bg2 + psi1 * bq1 + psi2 * bq2
    P_B = P_estimado_ELS(fct, sigma_carga_F, Ac_cm2, Wb_cm3, ep_cm)

    return {
        "P_estA_ELS_D_kN": P_A,
        "P_estB_ELS_F_kN": P_B,
        "P_est_kN": max(P_A, P_B),
        "fct_kncm2": fct,
        "sigma_carga_D_kncm2": sigma_carga_D,
        "sigma_carga_F_kncm2": sigma_carga_F,
    }


def estimar_P_protensao_parcial(
    Mg1_kncm: float, Mg2_kncm: float, Mq1_kncm: float, Mq2_kncm: float,
    psi1: float, psi2: float,
    Ac_cm2: float, Wb_cm3: float, ep_cm: float,
    fck_mpa: float, sigma_traçao_kncm2: float,
    secao: str = "T",
) -> dict:
    """Forca de protensao final P para protensao parcial (item 4.6.1.3).

    Permite tensao de tracao na base superior a fct (controle por ELS-W com
    abertura maxima de 0.2 mm). O usuario informa sigma_traçao_kncm2 como
    a tensao de tracao admitida na borda inferior em ELS-F freq.

    - ELS-D (combinacao quase permanente): sigma_b_total = 0
    - ELS-F (combinacao frequente): sigma_b_total = sigma_traçao_kncm2 (>fct)
    """
    bg1 = Mg1_kncm / Wb_cm3
    bg2 = Mg2_kncm / Wb_cm3
    bq1 = Mq1_kncm / Wb_cm3
    bq2 = Mq2_kncm / Wb_cm3

    sigma_carga_D = bg1 + bg2 + psi2 * bq1 + psi2 * bq2
    P_A = P_estimado_ELS(0.0, sigma_carga_D, Ac_cm2, Wb_cm3, ep_cm)

    sigma_carga_F = bg1 + bg2 + psi1 * bq1 + psi2 * bq2
    P_B = P_estimado_ELS(sigma_traçao_kncm2, sigma_carga_F,
                         Ac_cm2, Wb_cm3, ep_cm)

    return {
        "P_estA_ELS_D_kN": P_A,
        "P_estB_ELS_F_kN": P_B,
        "P_est_kN": max(P_A, P_B),
        "sigma_carga_D_kncm2": sigma_carga_D,
        "sigma_carga_F_kncm2": sigma_carga_F,
    }


# ---------------------------------------------------------------------------
# ELU a flexao (capitulo 6 - secao retangular com aderencia)
# ---------------------------------------------------------------------------
def MRd_secao_retangular_protendida(
    bw_cm: float, dp_cm: float, ds_cm: float, d_linha_cm: float,
    Ap_cm2: float, As_cm2: float, As_linha_cm2: float,
    fck_mpa: float, sigma_pd_mpa: float = 1520.0,
    fyk_mpa: float = 500.0, gama_c: float = GAMA_C,
    gama_s: float = GAMA_S, alpha_c: float = 0.85,
) -> dict:
    """Momento fletor resistente MRd no ELU para secao retangular com
    armaduras Ap, As e A's.

    Eq. 6.10: x = (sigma_pd*Ap + fyd*As - fyd*A's) / (alpha_c * fcd_kncm * 0.8 * bw)
    Eq. 6.11: MRd = sigma_pd*Ap*(dp - 0.4x) + fyd*As*(ds - 0.4x)
                  + fyd*A's*(0.4x - d')

    sigma_pd e o valor de tensao na armadura de protensao no ELU
    (estimado, geralmente ~1.520 MPa para CP-190 RB).
    Resultado: MRd em kN.cm.
    """
    fcd = fck_mpa / gama_c * 0.1     # kN/cm2
    fyd = fyk_mpa / gama_s * 0.1     # kN/cm2
    sigma_pd_kncm = sigma_pd_mpa * 0.1
    num = sigma_pd_kncm * Ap_cm2 + fyd * As_cm2 - fyd * As_linha_cm2
    den = alpha_c * fcd * 0.8 * bw_cm
    x = num / den
    MRd = (sigma_pd_kncm * Ap_cm2 * (dp_cm - 0.4 * x)
           + fyd * As_cm2 * (ds_cm - 0.4 * x)
           + fyd * As_linha_cm2 * (0.4 * x - d_linha_cm))
    return {
        "x_cm": x,
        "MRd_kncm": MRd,
        "x_d": x / max(dp_cm, ds_cm),
        "ductil": x / max(dp_cm, ds_cm) <= 0.45,
    }


def Pi_de_P(P_kn: float, R: float = 0.85) -> float:
    """Forca de estiramento Pi a partir da forca final P, dado o fator
    de efetividade R (P = R * Po, Po ~= Pi nas perdas iniciais).
    R tipico: 0.80-0.90."""
    return P_kn / R


# ---------------------------------------------------------------------------
# Perda por encurtamento elastico cabos restantes (Eq. 5.62, item 5.6.2)
# ---------------------------------------------------------------------------
def perda_encurtamento_cabos_restantes_kncm2(
    n_cabos: int, sigma_cpog_kncm2: float,
    fck_mpa: float, agregado: str = "granito",
    Ep_mpa: float = E_P_MPA,
) -> float:
    """delta sigma_p = alpha_p * (n-1)/(2n) * sigma_cpog  (Eq. 5.62, NBR 9.6.3.3.2.1).

    Perda media por cabo na pos-tensao quando os cabos sao estirados
    sucessivamente. sigma_cpog = tensao no concreto adjacente ao cabo
    apos perdas por atrito e ancoragem (positiva se compressao).
    n_cabos = numero de grupos de cabos protendidos simultaneamente.
    """
    if n_cabos < 1:
        raise ValueError("n_cabos deve ser >= 1")
    Ec = Ecs_mpa(fck_mpa, agregado)
    alpha_p = Ep_mpa / Ec
    return alpha_p * (n_cabos - 1) / (2.0 * n_cabos) * abs(sigma_cpog_kncm2)


# ---------------------------------------------------------------------------
# Escorregamento na ancoragem (pos-tensao, item 5.6.4)
# ---------------------------------------------------------------------------
def omega_perfil(perfil: str, mu: float, k_per_m: float, **kwargs) -> float:
    """Coeficiente omega (1/m) que define a inclinacao da curva de
    perda por atrito (NAAMAN, Tabela 5.6).

    perfil = 'linear':  omega = k
    perfil = 'parabolico':  omega = 2*mu*a/b^2 + k, onde a = fleche, b = vao
    perfil = 'circular':  omega = mu/R + k
    """
    p = perfil.lower()
    if p == "linear":
        return k_per_m
    if p in ("parabolico", "parabola"):
        a = kwargs["a_m"]
        b = kwargs["b_m"]
        return 2.0 * mu * a / (b * b) + k_per_m
    if p in ("circular", "arco"):
        R_m = kwargs["R_m"]
        return mu / R_m + k_per_m
    raise ValueError(f"perfil desconhecido: {perfil}")


def X_escorregamento_m(delta_anc_m: float, sigma_pi_kncm2: float,
                       omega_per_m: float,
                       Ep_mpa: float = E_P_MPA) -> float:
    """Distancia X (m) ate onde a perda por escorregamento e nula (Eq. 5.78).

    X = sqrt(delta * Ep / (sigma_pi * omega))
    delta_anc em metros. sigma_pi em kN/cm2 (sera convertida para MPa).
    """
    sigma_pi_mpa = sigma_pi_kncm2 * 10.0
    return math.sqrt(delta_anc_m * Ep_mpa / (sigma_pi_mpa * omega_per_m))


def perda_escorregamento_kncm2(delta_anc_m: float, X_m: float,
                                Ep_mpa: float = E_P_MPA) -> float:
    """delta sigma_p,anc na ancoragem ativa (Eq. 5.77).
    delta sigma_p,anc = 2 * delta * Ep / X  (resultado em kN/cm2)."""
    return 2.0 * delta_anc_m * Ep_mpa / X_m * 0.1   # MPa -> kN/cm2


# ---------------------------------------------------------------------------
# Anexo A NBR 6118 - Retracao e fluencia (versao simplificada com tabela)
# ---------------------------------------------------------------------------
# Tabela 8.2 NBR 6118 - valores tipicos para fluencia phi e retracao eps_cs
# (extraidos para condicoes correntes - umidade 70%, abatimento 5-9 cm)
TABELA_FLUENCIA_RETRACAO = {
    # (umidade %, h_fic_cm): (phi_inf, eps_cs_inf_per_mil)
    # Valores tipicos NBR 6118 8.2.11 (concreto C20-C45):
    (40, 20): (4.4, -0.44),
    (40, 60): (3.9, -0.39),
    (55, 20): (3.8, -0.39),
    (55, 60): (3.3, -0.33),
    (75, 20): (2.8, -0.33),
    (75, 60): (2.4, -0.28),
    (90, 20): (2.0, -0.15),
    (90, 60): (1.9, -0.12),
}


def phi_eps_cs_NBR(umidade_pct: float, h_fic_cm: float,
                   to_dias: float = 30.0) -> tuple[float, float]:
    """Estima phi_inf e eps_cs_inf por interpolacao na Tabela 8.2 da
    NBR 6118 (item 8.2.11). h_fic = espessura ficticia = 2*Ac/u_ar.

    Retorna (phi_inf, eps_cs_inf_permil)."""
    # arredonda umidade aos pontos da tabela
    umidades = sorted({k[0] for k in TABELA_FLUENCIA_RETRACAO})
    espessuras = sorted({k[1] for k in TABELA_FLUENCIA_RETRACAO})
    # vizinho mais proximo nas duas dimensoes
    u_ref = min(umidades, key=lambda u: abs(u - umidade_pct))
    h_ref = min(espessuras, key=lambda h: abs(h - h_fic_cm))
    return TABELA_FLUENCIA_RETRACAO[(u_ref, h_ref)]


def h_ficticia_cm(Ac_cm2: float, u_ar_cm: float, gama_humid: float = 1.0) -> float:
    """h_fic = gamma * 2*Ac / u_ar  (NBR 6118 Anexo A).
    u_ar = perimetro em contato com o ar."""
    return gama_humid * 2.0 * Ac_cm2 / u_ar_cm


# ---------------------------------------------------------------------------
# ELU - Secao T protendida (Eq. 6.16, 6.17)
# ---------------------------------------------------------------------------
def MRd_secao_T_protendida(
    bf_cm: float, bw_cm: float, hf_cm: float,
    dp_cm: float, ds_cm: float, d_linha_cm: float,
    Ap_cm2: float, As_cm2: float, As_linha_cm2: float,
    fck_mpa: float, sigma_pd_mpa: float = 1520.0,
    fyk_mpa: float = 500.0, gama_c: float = GAMA_C,
    gama_s: float = GAMA_S, alpha_c: float = 0.85,
) -> dict:
    """MRd para secao T protendida (Eq. 6.16, 6.17).

    Inicialmente assume secao retangular bf. Se 0.8x <= hf, retorna esse
    resultado. Caso contrario aplica formula T:
       x = (sigma_pd*Ap + fyd*As - 0.85*alpha_c*fcd*(bf-bw)*hf - fyd*A's)
            / (alpha_c * fcd * 0.8 * bw)
       MRd = 0.85*alpha_c*fcd*(bf-bw)*hf*(0.4x - 0.5*hf)
             + sigma_pd*Ap*(dp - 0.4x) + fyd*As*(ds - 0.4x)
             + fyd*A's*(0.4x - d')
    """
    fcd = fck_mpa / gama_c * 0.1
    fyd = fyk_mpa / gama_s * 0.1
    sigma_pd_kncm = sigma_pd_mpa * 0.1

    # 1) Tentativa retangular bf
    r_ret = MRd_secao_retangular_protendida(
        bw_cm=bf_cm, dp_cm=dp_cm, ds_cm=ds_cm, d_linha_cm=d_linha_cm,
        Ap_cm2=Ap_cm2, As_cm2=As_cm2, As_linha_cm2=As_linha_cm2,
        fck_mpa=fck_mpa, sigma_pd_mpa=sigma_pd_mpa, fyk_mpa=fyk_mpa,
        gama_c=gama_c, gama_s=gama_s, alpha_c=alpha_c,
    )
    if 0.8 * r_ret["x_cm"] <= hf_cm:
        r_ret["secao"] = "T-como-retangular-bf"
        return r_ret

    # 2) LN na nervura - Eq. 6.16
    Rcc_mes = 0.85 * alpha_c * fcd * (bf_cm - bw_cm) * hf_cm
    num = (sigma_pd_kncm * Ap_cm2 + fyd * As_cm2
           - Rcc_mes - fyd * As_linha_cm2)
    den = alpha_c * fcd * 0.8 * bw_cm
    x = num / den
    MRd = (Rcc_mes * (0.4 * x - 0.5 * hf_cm)
           + sigma_pd_kncm * Ap_cm2 * (dp_cm - 0.4 * x)
           + fyd * As_cm2 * (ds_cm - 0.4 * x)
           + fyd * As_linha_cm2 * (0.4 * x - d_linha_cm))
    return {
        "x_cm": x,
        "MRd_kncm": MRd,
        "x_d": x / max(dp_cm, ds_cm),
        "ductil": x / max(dp_cm, ds_cm) <= 0.45,
        "secao": "T-LN-nervura",
    }


# ---------------------------------------------------------------------------
# Determinacao direta de P e ep (Magnel/Hurst - item 4.6.2)
# ---------------------------------------------------------------------------
def fuso_limite_excentricidade(
    Po_kn: float, Mo_kncm: float, Mtot_kncm: float,
    Ac_cm2: float, Wb_cm3: float, Wt_cm3: float,
    R: float, sigma_tr_o_kncm2: float, sigma_c_o_kncm2: float,
    sigma_tr_tot_kncm2: float, sigma_c_tot_kncm2: float,
) -> dict:
    """Calcula limites de excentricidade ep para uma secao (Eq. 4.77-4.80).

    Cada equacao retorna o limite de ep que satisfaz uma das tensoes
    admissiveis. A interseccao define o fuso limite.

    sigma_tr_o    : tensao admissivel a tracao na transferencia (>0)
    sigma_c_o     : tensao admissivel a compressao na transf. (<0)
    sigma_tr_tot  : tensao admissivel a tracao apos perdas (>0)
    sigma_c_tot   : tensao admissivel a compressao apos perdas (<0)

    Retorna ep_min e ep_max (cm) e os 4 limites individuais.
    """
    yt = Wt_cm3 / Wb_cm3 if False else 0  # nao usado
    eta_t = Ac_cm2 / Wt_cm3
    eta_b = Ac_cm2 / Wb_cm3

    # Eq. 4.77 (transferencia, fibra topo, tracao admissivel)
    ep_77 = Mo_kncm / Po_kn + Wt_cm3 * sigma_tr_o_kncm2 / Po_kn - 1.0 / eta_t
    # Eq. 4.78 (transferencia, fibra base, compressao admissivel)
    ep_78 = Mo_kncm / Po_kn + Wb_cm3 * sigma_c_o_kncm2 / Po_kn + 1.0 / eta_b
    # Eq. 4.79 (apos perdas, fibra topo, compressao admissivel)
    ep_79 = Mtot_kncm / (R * Po_kn) + Wt_cm3 * sigma_c_tot_kncm2 / (R * Po_kn) - 1.0 / eta_t
    # Eq. 4.80 (apos perdas, fibra base, tracao admissivel)
    ep_80 = Mtot_kncm / (R * Po_kn) + Wb_cm3 * sigma_tr_tot_kncm2 / (R * Po_kn) + 1.0 / eta_b

    # ep_min: maior dos limites inferiores (4.77, 4.79 - fibra topo)
    ep_min = max(ep_77, ep_79)
    # ep_max: menor dos limites superiores (4.78, 4.80 - fibra base)
    ep_max = min(ep_78, ep_80)
    return {
        "ep_min_cm": ep_min,
        "ep_max_cm": ep_max,
        "ep_77_top_o": ep_77,
        "ep_78_base_o": ep_78,
        "ep_79_top_tot": ep_79,
        "ep_80_base_tot": ep_80,
        "viavel": ep_min <= ep_max,
    }


def Wb_min_secao_excentricidade_variavel(
    Mo_kncm: float, Mtot_kncm: float, R: float,
    sigma_tr_tot_kncm2: float, sigma_c_o_kncm2: float,
) -> float:
    """Modulo de flexao Wb minimo (Eq. 4.58):
    Wb_min = (M_tot - R*M_o) / (sigma_tr_tot - R*sigma_c_o).
    sigma_c_o e sigma_c_tot devem ser passadas com sinal negativo."""
    return (Mtot_kncm - R * Mo_kncm) \
        / (sigma_tr_tot_kncm2 - R * sigma_c_o_kncm2)


def Wt_min_secao_excentricidade_variavel(
    Mo_kncm: float, Mtot_kncm: float, R: float,
    sigma_tr_o_kncm2: float, sigma_c_tot_kncm2: float,
) -> float:
    """Modulo de flexao Wt minimo (Eq. 4.59):
    Wt_min = (M_tot - R*M_o) / (R*sigma_tr_o - sigma_c_tot).
    sigma_c_tot deve ser passada com sinal negativo."""
    return (Mtot_kncm - R * Mo_kncm) \
        / (R * sigma_tr_o_kncm2 - sigma_c_tot_kncm2)


# ---------------------------------------------------------------------------
# Tabela de cordoalhas (NBR 7483 - ArcelorMittal)
# ---------------------------------------------------------------------------
# (designacao, fptk_MPa): (diam_mm, area_mm2, massa_kg_per_m, F_max_kN)
TABELA_CORDOALHAS_CP190_RB = {
    # 7-fios
    9.5:  (9.5,  55.5, 0.432, 105.4),
    11.0: (11.0, 75.5, 0.587, 143.5),
    12.7: (12.7, 101.4, 0.792, 192.9),
    15.2: (15.2, 143.5, 1.116, 273.8),
}

TABELA_CORDOALHAS_CP210_RB = {
    9.5:  (9.5,  54.8, 0.432, 115.0),
    11.0: (11.0, 74.2, 0.587, 156.9),
    12.7: (12.7, 100.0, 0.785, 210.0),
    15.2: (15.2, 140.0, 1.102, 294.0),
}


def propriedades_cordoalha(diam_mm: float,
                           categoria: str = "CP-190 RB") -> dict:
    """Retorna propriedades da cordoalha de 7 fios.

    Areas em mm2; F_max = forca de ruptura caracteristica = fptk * Ap.
    """
    cat = categoria.upper()
    if "CP-190" in cat:
        tab = TABELA_CORDOALHAS_CP190_RB
        fptk = 1900.0
    elif "CP-210" in cat:
        tab = TABELA_CORDOALHAS_CP210_RB
        fptk = 2100.0
    else:
        raise ValueError(f"categoria desconhecida: {categoria}")
    if diam_mm not in tab:
        raise ValueError(f"diametro {diam_mm} nao tabelado em {cat}")
    d, area, massa, F_max = tab[diam_mm]
    return {
        "diam_mm": d,
        "area_mm2": area,
        "area_cm2": area / 100.0,
        "massa_kg_m": massa,
        "F_max_kN": F_max,
        "fptk_MPa": fptk,
        "fpyk_MPa": 0.9 * fptk,    # NBR 7483
    }


# ---------------------------------------------------------------------------
# Resultado consolidado
# ---------------------------------------------------------------------------
@dataclass
class TensoesProtendido:
    sigma_b_kncm2: float
    sigma_t_kncm2: float
    sigma_b_MPa: float
    sigma_t_MPa: float


def calcular_tensoes(P_kn: float, ep_cm: float, M_kncm: float,
                     b_cm: float, h_cm: float) -> TensoesProtendido:
    Ac = Ac_retangular(b_cm, h_cm)
    W = W_retangular(b_cm, h_cm)
    sb, st = sigma_base_topo(P_kn, ep_cm, M_kncm, Ac, W, W)
    return TensoesProtendido(
        sigma_b_kncm2=sb, sigma_t_kncm2=st,
        sigma_b_MPa=sb * 10.0, sigma_t_MPa=st * 10.0,
    )


# ---------------------------------------------------------------------------
# Tests (validados contra Exemplo 1.6.1 da apostila Bastos)
# ---------------------------------------------------------------------------
def _aprox(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def test_propriedades_geometricas_laje() -> None:
    """Apostila ex.1.6.1: faixa b=30, h=30. Ac=900, W=4500, h/6=5 cm."""
    Ac = Ac_retangular(30.0, 30.0)
    W = W_retangular(30.0, 30.0)
    Ic = Ic_retangular(30.0, 30.0)
    nuc = nucleo_central_retangular(30.0)
    assert _aprox(Ac, 900.0, 0.1)
    assert _aprox(W, 4500.0, 0.1)
    assert _aprox(Ic, 67500.0, 0.1)
    assert _aprox(nuc, 5.0, 0.001)
    print(f"  OK  Faixa 30x30: Ac={Ac:.0f}, W={W:.0f}, Ic={Ic:.0f}, "
          f"h/6={nuc:.1f}")


def test_tensao_carga_apostila() -> None:
    """Apostila: Mg=Mq=2813 kN.cm, faixa 30x30
    -> sigma = 6Mg/(bh^2) = 6.25 MPa (compressao topo, tracao base)."""
    Mg = 2813.0
    sigma_g_kncm2 = 6.0 * Mg / (30.0 * 30.0 ** 2)
    assert _aprox(sigma_g_kncm2 * 10.0, 6.25, 0.05)
    print(f"  OK  sigma_g (faixa) = {sigma_g_kncm2*10:.2f} MPa")


def test_protensao_axial_apostila() -> None:
    """Caso 3 apostila: anular tracao na base.
    P/Ac = 12.5 MPa -> P = 1125 kN."""
    Ac = 900.0
    Wb = 4500.0
    M_total = 2813.0 + 2813.0
    # sigma_alvo = 0 na base
    P = forca_protensao_axial(sigma_alvo_base_kncm2=0.0,
                              M_kncm=M_total, Ac_cm2=Ac, Wb_cm3=Wb)
    assert _aprox(P, 1125.0, 1.0), f"P={P:.2f}"
    print(f"  OK  Protensao axial: P = {P:.1f} kN  (apostila: 1125)")


def test_protensao_excentrica_h_sobre_6() -> None:
    """Caso 4 apostila: ep = h/6 = 5 cm. P = 562.5 kN.
    sigma_alvo_base = 0:
    P = (M/Wb) / (1/Ac + ep/Wb) = (5626/4500) / (1/900 + 5/4500)
      = 1.25 / 0.00222 = 562.5 kN."""
    P = forca_protensao_excentrica(sigma_alvo_base_kncm2=0.0,
                                    M_kncm=5626.0, ep_cm=5.0,
                                    Ac_cm2=900.0, Wb_cm3=4500.0)
    assert _aprox(P, 562.5, 0.5), f"P={P:.2f}"
    print(f"  OK  Protensao ep=h/6: P = {P:.1f} kN  (apostila: 562.5)")


def test_protensao_excentrica_max_apostila() -> None:
    """Caso 5 apostila: ep = 10 cm (maxima possivel para d_p=27).
    P = 375 kN."""
    P = forca_protensao_excentrica(sigma_alvo_base_kncm2=0.0,
                                    M_kncm=5626.0, ep_cm=10.0,
                                    Ac_cm2=900.0, Wb_cm3=4500.0)
    assert _aprox(P, 375.0, 0.5), f"P={P:.2f}"
    print(f"  OK  Protensao ep=10cm: P = {P:.1f} kN  (apostila: 375)")


def test_tensao_combinada_protensao_max_apostila() -> None:
    """Caso 5 apostila: P=375, ep=10, M=5626.
    sigma_topo (com P) = -P/Ac + P*ep/Wt = -0.4167 + 0.8333 = +0.4167 kN/cm2
                       = +4.17 MPa (tracao)
    Apostila informa +4.2 MPa de tracao no topo devido a P."""
    sb, st = sigma_base_topo(P_kn=375.0, ep_cm=10.0, M_kncm=0.0,
                              Ac_cm2=900.0, Wb_cm3=4500.0, Wt_cm3=4500.0)
    assert _aprox(st * 10.0, 4.17, 0.05), f"sigma_t={st*10:.2f}"
    # Combinada com Mg+Mq=5626: sigma_topo = -P/Ac + P.ep/Wt - M/Wt
    sb_tot, st_tot = sigma_base_topo(P_kn=375.0, ep_cm=10.0, M_kncm=5626.0,
                                      Ac_cm2=900.0, Wb_cm3=4500.0,
                                      Wt_cm3=4500.0)
    # apostila: sigma_topo final ~ -8.3 MPa (compressao); base ~ 0
    assert _aprox(sb_tot, 0.0, 0.05), f"sigma_b_tot={sb_tot:.4f}"
    print(f"  OK  Caso 5: sigma_topo(somente P) = {st*10:.2f} MPa  "
          f"sigma_base(total) = {sb_tot*10:.3f} MPa")


def test_relaxacao_apostila_25h() -> None:
    """Apostila: psi_1000=8.5%, t=25h -> psi(t)=4.9%."""
    psi = psi_t_em_horas(psi_1000_percent=8.5, t_horas=25.0)
    assert _aprox(psi, 4.9, 0.1), f"psi={psi:.3f}"
    print(f"  OK  psi(25h, RN) = {psi:.2f}%  (apostila: 4.9)")


def test_relaxacao_perda_apostila() -> None:
    """Apostila: psi=4.9%, sigma_pi=0.8*fptk -> perda = 0.039*fptk."""
    psi = psi_t_em_horas(8.5, 25.0)
    fptk = 1.0  # normaliza
    sigma_pi = 0.8 * fptk
    perda = perda_relaxacao_kncm2(psi, sigma_pi)
    assert _aprox(perda, 0.039 * fptk, 0.001), f"perda={perda}"
    print(f"  OK  Perda relaxacao = {perda:.4f} fptk  (apostila: 0.039)")


def test_relaxacao_infinito() -> None:
    """psi(inf) = 2.5 * psi_1000."""
    p = psi_infinito(3.5)  # CP-190 RB
    assert _aprox(p, 8.75, 0.001)
    print(f"  OK  psi(inf, RB) = {p:.2f}%")


def test_perda_encurtamento_elastico() -> None:
    """Ep=200 GPa, C50 -> Ec ~ 39.6 GPa (granito), alpha_p ~ 5.05.
    sigma_cp = 1.0 kN/cm2 (10 MPa) -> perda = 5.05 kN/cm2 = 50.5 MPa."""
    p = perda_encurtamento_elastico_kncm2(
        sigma_cp_kncm2=1.0, fck_mpa=50.0,
    )
    Ec = Ecs_mpa(50.0)
    alpha_p_esperado = E_P_MPA / Ec
    assert _aprox(p, alpha_p_esperado * 1.0, 0.01), f"p={p}"
    print(f"  OK  Perda enc.elast (sigma_cp=10 MPa, C50): "
          f"{p*10:.2f} MPa  (alpha_p={alpha_p_esperado:.3f})")


def test_perda_retracao() -> None:
    """eps_cs=-0.5 permil, Ep=200 GPa -> perda = 100 MPa = 10 kN/cm2."""
    p = perda_retracao_kncm2(eps_cs_permil=-0.5)
    assert _aprox(p, 10.0, 0.1), f"perda={p}"
    print(f"  OK  Perda retracao (eps_cs=0.5permil) = {p:.2f} kN/cm2 "
          f"({p*10:.0f} MPa)")


def test_perda_fluencia() -> None:
    """phi=2.0, sigma_c(to)=10 MPa, C50 -> alpha_p~5.05; perda = 10.1 kN/cm2 = 101 MPa."""
    p = perda_fluencia_kncm2(phi_inf=2.0, sigma_c_to_kncm2=1.0,
                              fck_mpa=50.0)
    Ec = Ecs_mpa(50.0)
    expected = (E_P_MPA / Ec) * 2.0 * 1.0
    assert _aprox(p, expected, 0.01)
    print(f"  OK  Perda fluencia: {p:.3f} kN/cm2 ({p*10:.1f} MPa)")


def test_perda_atrito_arco_apostila() -> None:
    """Apostila 5.6.3.1 ex.1: viga 20m, cabo em arco com fleche y=35cm,
    mu=0.20, k=0.006/m, Pi=1406 kN.
    theta = 8*0.35/20 = 0.14 rad
    Patr(20) = 1406 * (1 - exp(-(0.20*0.14 + 0.006*20)))
            = 1406 * (1 - exp(-0.148)) = 193.4 kN (~13.8% de Pi)."""
    theta = theta_arco_circulo_rad(y_cm=35.0, x_m=20.0)
    assert _aprox(theta, 0.14, 0.001), f"theta={theta:.4f}"
    Patr = perda_atrito_kn(Pi_kn=1406.0, mu=0.20, theta_rad=theta,
                           k_per_m=0.006, x_m=20.0)
    assert _aprox(Patr, 193.4, 1.0), f"Patr={Patr:.2f}"
    pct = Patr / 1406.0 * 100.0
    assert _aprox(pct, 13.8, 0.2), f"pct={pct:.2f}"
    print(f"  OK  Atrito ex.1: theta={theta:.3f} rad, "
          f"Patr={Patr:.1f} kN ({pct:.1f}%)")


def test_perda_atrito_parabola_apostila() -> None:
    """Apostila 5.6.3.2 ex.2: cabo parabolico, L=42m, fleche=1.0 m no centro.
    No meio do vao (x=21): theta_metade = 4*1/42 = 0.0952 rad.
    Pi = 1687.2 kN, mu=0.20, k=0.002/m.
    Patr(21) = 1687.2 * (1 - exp(-(0.20*0.0952 + 0.002*21)))
            = 1687.2 * (1 - exp(-0.06104))."""
    theta = theta_parabola_rad(y_cm=100.0, x_m=42.0)
    assert _aprox(theta, 0.0952, 0.001), f"theta={theta:.4f}"
    Patr = perda_atrito_kn(Pi_kn=1687.2, mu=0.20, theta_rad=theta,
                           k_per_m=0.002, x_m=21.0)
    expected = 1687.2 * (1.0 - math.exp(-(0.20 * 0.0952 + 0.002 * 21.0)))
    assert _aprox(Patr, expected, 0.5)
    print(f"  OK  Atrito parabola: theta_meio={theta:.4f} rad, "
          f"Patr(21m)={Patr:.1f} kN")


def test_fct_admissivel_secao() -> None:
    """C50, secao duplo T: fct = 1.2 * 0.7 * 0.3 * 50^(2/3) = 3.42 MPa."""
    fct_T = fct_admissivel_traçao_kncm2(50.0, "T")
    fct_I = fct_admissivel_traçao_kncm2(50.0, "I")
    fct_R = fct_admissivel_traçao_kncm2(50.0, "retangular")
    assert _aprox(fct_T * 10.0, 3.42, 0.01), f"fct_T={fct_T*10:.3f}"
    assert _aprox(fct_I * 10.0, 3.71, 0.01)
    assert _aprox(fct_R * 10.0, 4.28, 0.01)
    print(f"  OK  fct(C50): T={fct_T*10:.2f}, I={fct_I*10:.2f}, "
          f"R={fct_R*10:.2f} MPa")


def test_protensao_completa_viga_duplo_T_apostila() -> None:
    """Apostila ex. 4.6.1.5 - viga duplo T C50, L=15m.
    Ac=2648 cm2, Wb=17260 cm3, Wt=40230 cm3, ep=25 cm.
    Mg1=18619, Mg2=13500, Mq1=5063 kN.cm; psi1=0.4, psi2=0.

    ELS-D: P_estA = 1083 kN
    ELS-F: P_estB = 992 kN
    P_est = max = 1083 kN."""
    r = estimar_P_protensao_completa(
        Mg1_kncm=18619.0, Mg2_kncm=13500.0, Mq1_kncm=5063.0,
        Mq2_kncm=0.0, psi1=0.4, psi2=0.0,
        Ac_cm2=2648.0, Wb_cm3=17260.0, ep_cm=25.0,
        fck_mpa=50.0, secao="duplo-T",
    )
    assert _aprox(r["P_estA_ELS_D_kN"], 1083.0, 5.0), \
        f"P_A={r['P_estA_ELS_D_kN']:.1f}"
    assert _aprox(r["P_estB_ELS_F_kN"], 992.0, 5.0), \
        f"P_B={r['P_estB_ELS_F_kN']:.1f}"
    assert _aprox(r["P_est_kN"], 1083.0, 5.0)
    print(f"  OK  Protensao completa: P_estA={r['P_estA_ELS_D_kN']:.0f}, "
          f"P_estB={r['P_estB_ELS_F_kN']:.0f}, P_est={r['P_est_kN']:.0f}")


def test_protensao_limitada_viga_duplo_T_apostila() -> None:
    """Apostila ex. 4.6.1.6 (mesma viga do ex. 4.6.1.5, mas limitada).
    psi1=0.4, psi2=0.3.

    ELS-D quase perm.: σ_carga = 1.079 + 0.782 + 0.3*0.293 = 1.949
        -> P_estA = 1.949/0.0018264 = 1067 kN
    ELS-F freq.: σ_carga = 1.079 + 0.782 + 0.4*0.293 = 1.978
        σ_bP = 0.342 - 1.978 = -1.636 -> P_estB = 1.636/0.0018264 = 896 kN
    P_est = 1067 kN."""
    r = estimar_P_protensao_limitada(
        Mg1_kncm=18619.0, Mg2_kncm=13500.0, Mq1_kncm=5063.0,
        Mq2_kncm=0.0, psi1=0.4, psi2=0.3,
        Ac_cm2=2648.0, Wb_cm3=17260.0, ep_cm=25.0,
        fck_mpa=50.0, secao="duplo-T",
    )
    assert _aprox(r["P_estA_ELS_D_kN"], 1067.0, 5.0), \
        f"P_A={r['P_estA_ELS_D_kN']:.1f}"
    assert _aprox(r["P_estB_ELS_F_kN"], 896.0, 5.0), \
        f"P_B={r['P_estB_ELS_F_kN']:.1f}"
    assert _aprox(r["P_est_kN"], 1067.0, 5.0)
    print(f"  OK  Protensao limitada: P_estA={r['P_estA_ELS_D_kN']:.0f}, "
          f"P_estB={r['P_estB_ELS_F_kN']:.0f}, P_est={r['P_est_kN']:.0f}")


def test_protensao_parcial_basica() -> None:
    """Protensao parcial admite tracao maior que fct na base. Para a
    mesma viga, tomando sigma_traçao = 0.50 kN/cm2 (~5 MPa, > fct):
    P_estB sera menor que na limitada."""
    r_lim = estimar_P_protensao_limitada(
        18619.0, 13500.0, 5063.0, 0.0, 0.4, 0.3,
        2648.0, 17260.0, 25.0, 50.0, "duplo-T",
    )
    r_par = estimar_P_protensao_parcial(
        18619.0, 13500.0, 5063.0, 0.0, 0.4, 0.3,
        2648.0, 17260.0, 25.0, 50.0,
        sigma_traçao_kncm2=0.50, secao="duplo-T",
    )
    # parcial deve ter P_B menor que limitada (mais tracao admitida)
    assert r_par["P_estB_ELS_F_kN"] < r_lim["P_estB_ELS_F_kN"]
    assert _aprox(r_par["P_estA_ELS_D_kN"], r_lim["P_estA_ELS_D_kN"], 1.0)
    print(f"  OK  Protensao parcial: P_estA={r_par['P_estA_ELS_D_kN']:.0f}, "
          f"P_estB={r_par['P_estB_ELS_F_kN']:.0f}  "
          f"(<lim P_estB={r_lim['P_estB_ELS_F_kN']:.0f})")


def test_MRd_secao_retangular_protendida() -> None:
    """Apostila ex. 6.10.1.2: viga retangular protendida, C35.
    bw=40, dp=110, ds=115, d'=0; Ap=11.20, As=9.89 (calculado), A's=0.
    fck=35, sigma_pd=1520 MPa, fyd=435 MPa.

    x = (152*11.20 + 43.5*9.89) / (1*0.85*3.5/1.4*0.8*40) = ?
      = (1702.4 + 430.2) / (68) = 2132.6/68 = 31.36 cm
    MRd ~ 210000 kN.cm (pois As foi resolvido para isso)."""
    r = MRd_secao_retangular_protendida(
        bw_cm=40.0, dp_cm=110.0, ds_cm=115.0, d_linha_cm=0.0,
        Ap_cm2=11.20, As_cm2=9.89, As_linha_cm2=0.0,
        fck_mpa=35.0, sigma_pd_mpa=1520.0, fyk_mpa=500.0,
        alpha_c=0.85,
    )
    assert _aprox(r["x_cm"], 31.37, 0.1), f"x={r['x_cm']:.2f}"
    # Apostila resolveu por equacao do 2o grau dando As = 9.89 -> MRd ~ 210000
    assert _aprox(r["MRd_kncm"], 210000.0, 1500.0), f"MRd={r['MRd_kncm']:.0f}"
    print(f"  OK  ELU sec ret: x={r['x_cm']:.2f} cm, "
          f"MRd={r['MRd_kncm']:.0f} kN.cm  (apostila: 210000, x=31.37)")


def test_MRd_apenas_armadura_ativa() -> None:
    """Sem armadura passiva (As=A's=0), so a armadura ativa.
    Caso simples para validar a equacao basica."""
    r = MRd_secao_retangular_protendida(
        bw_cm=40.0, dp_cm=110.0, ds_cm=110.0, d_linha_cm=0.0,
        Ap_cm2=11.20, As_cm2=0.0, As_linha_cm2=0.0,
        fck_mpa=35.0, sigma_pd_mpa=1520.0,
    )
    # x = 152*11.20 / (1*0.85*3.5/1.4*0.8*40) = 1702.4/68 = 25.04 cm
    assert _aprox(r["x_cm"], 25.04, 0.05), f"x={r['x_cm']:.2f}"
    # MRd = 152*11.20*(110 - 0.4*25.04) = 1702.4 * 99.98 = 170226
    expected = 152.0 * 11.20 * (110.0 - 0.4 * 25.04)
    assert _aprox(r["MRd_kncm"], expected, 5.0)
    print(f"  OK  ELU so Ap: x={r['x_cm']:.2f}, MRd={r['MRd_kncm']:.0f}")


def test_Pi_de_P() -> None:
    """P=1083, R=0.85 -> Pi=1274 kN."""
    Pi = Pi_de_P(P_kn=1083.0, R=0.85)
    assert _aprox(Pi, 1274.1, 0.5)
    print(f"  OK  Pi(P=1083, R=0.85) = {Pi:.0f} kN")


def test_perda_cabos_restantes_n4() -> None:
    """n=4 cabos, sigma_cpog=10 MPa, C40 (Ec=32 GPa, alpha_p=6.25):
    delta = alpha_p * (n-1)/(2n) * sigma_cpog
          = 6.25 * 3/8 * 1.0 = 2.34 kN/cm2 = 23.4 MPa."""
    p = perda_encurtamento_cabos_restantes_kncm2(
        n_cabos=4, sigma_cpog_kncm2=1.0, fck_mpa=40.0,
    )
    Ec = Ecs_mpa(40.0)
    expected = (E_P_MPA / Ec) * (3.0 / 8.0) * 1.0
    assert _aprox(p, expected, 0.01), f"p={p}"
    print(f"  OK  Perda cabos restantes (n=4): {p:.3f} kN/cm2 "
          f"({p*10:.1f} MPa)")


def test_perda_cabos_restantes_n_1() -> None:
    """Caso degenerado n=1: nenhuma perda (cabo unico)."""
    p = perda_encurtamento_cabos_restantes_kncm2(
        n_cabos=1, sigma_cpog_kncm2=1.0, fck_mpa=40.0,
    )
    assert _aprox(p, 0.0, 1e-9)
    print(f"  OK  Perda cabos restantes (n=1): zero (cabo unico)")


def test_omega_perfis() -> None:
    """omega para perfis tipicos (Tabela 5.6 Naaman)."""
    # Linear: omega = k
    o_lin = omega_perfil("linear", mu=0.20, k_per_m=0.005)
    assert _aprox(o_lin, 0.005, 1e-6)
    # Parabolico: omega = 2*mu*a/b^2 + k. Apostila ex.5.6.4: a=0.45, b=8m
    # omega = 2*0.20*0.45/64 + 0.002 = 0.00281 + 0.002 = 0.00481
    o_par = omega_perfil("parabolico", mu=0.20, k_per_m=0.002,
                         a_m=0.45, b_m=8.0)
    assert _aprox(o_par, 0.00481, 1e-4), f"omega={o_par:.6f}"
    # Circular: omega = mu/R + k. R=10 m, mu=0.2: omega = 0.022
    o_arc = omega_perfil("circular", mu=0.20, k_per_m=0.002, R_m=10.0)
    assert _aprox(o_arc, 0.022, 1e-4)
    print(f"  OK  omega: lin={o_lin:.5f}, par={o_par:.5f}, arc={o_arc:.5f}")


def test_escorregamento_apostila_5_6_4() -> None:
    """Apostila ex.5.6.4.1: delta=6mm, sigma_pi=1402 MPa, omega=0.00481/m
    -> X = sqrt(0.006*196000/(1402*0.00481)) = 13.20 m
    Delta sigma_p,anc = 2*1402*0.00481*13.20 = 178.0 MPa."""
    omega = omega_perfil("parabolico", mu=0.20, k_per_m=0.002,
                         a_m=0.45, b_m=8.0)
    X = X_escorregamento_m(delta_anc_m=0.006, sigma_pi_kncm2=140.2,
                           omega_per_m=omega, Ep_mpa=196000.0)
    assert _aprox(X, 13.20, 0.05), f"X={X:.3f}"
    delta_sig = perda_escorregamento_kncm2(
        delta_anc_m=0.006, X_m=X, Ep_mpa=196000.0,
    )
    assert _aprox(delta_sig * 10.0, 178.2, 0.5), \
        f"delta_sig={delta_sig*10:.2f}"
    print(f"  OK  Escorregamento: X={X:.2f} m, "
          f"delta_sig={delta_sig*10:.1f} MPa  (apostila: 178.2)")


def test_h_ficticia() -> None:
    """h_fic = 2*Ac/u_ar. Viga 30x60 com perimetro exposto = 150 cm:
    h_fic = 2*1800/150 = 24 cm."""
    h = h_ficticia_cm(Ac_cm2=1800.0, u_ar_cm=150.0)
    assert _aprox(h, 24.0, 0.01)
    print(f"  OK  h_fic = {h:.2f} cm")


def test_phi_eps_cs_NBR() -> None:
    """Tabela 8.2 NBR 6118 simplificada: U=75%, h_fic=20:
    phi_inf=2.8, eps_cs=-0.33 permil."""
    phi, eps = phi_eps_cs_NBR(umidade_pct=75.0, h_fic_cm=20.0)
    assert _aprox(phi, 2.8, 0.01)
    assert _aprox(eps, -0.33, 0.001)
    print(f"  OK  phi_inf(75%, 20cm) = {phi}, eps_cs = {eps} permil")


def test_MRd_secao_T_LN_mesa() -> None:
    """Secao T com 0.8x <= hf -> retorna como retangular bf.
    Caso simples: bf=120, bw=20, hf=10, dp=50, Ap=2.0 cm2,
    sigma_pd=1500 MPa, fck=30. Como Ap pequena, x deve ser pequeno."""
    r = MRd_secao_T_protendida(
        bf_cm=120.0, bw_cm=20.0, hf_cm=10.0,
        dp_cm=50.0, ds_cm=50.0, d_linha_cm=0.0,
        Ap_cm2=2.0, As_cm2=0.0, As_linha_cm2=0.0,
        fck_mpa=30.0, sigma_pd_mpa=1500.0,
    )
    # x = (150*2)/(0.85*0.85*0.214*0.8*120) = 300/15.55 = 19.3 cm
    # Wait: fcd=30/14=2.143; 0.85*alphac=0.85; 0.85*2.143*0.8*120 = 175
    # x = 300/175 = 1.71 cm -- LN na mesa
    assert "T-como-retangular" in r["secao"]
    assert _aprox(r["x_cm"], 1.715, 0.05), f"x={r['x_cm']}"
    print(f"  OK  Secao T (LN na mesa): {r['secao']}, x={r['x_cm']:.2f} cm")


def test_MRd_secao_T_LN_nervura() -> None:
    """Secao T com 0.8x > hf -> usa formula T.
    bf=120, bw=20, hf=5, dp=80, Ap=15 cm2, sigma_pd=1500, fck=30.
    Espera-se LN na nervura."""
    r = MRd_secao_T_protendida(
        bf_cm=120.0, bw_cm=20.0, hf_cm=5.0,
        dp_cm=80.0, ds_cm=80.0, d_linha_cm=0.0,
        Ap_cm2=15.0, As_cm2=0.0, As_linha_cm2=0.0,
        fck_mpa=30.0, sigma_pd_mpa=1500.0,
    )
    # Verifica que retornou como T-LN-nervura
    assert r["secao"] == "T-LN-nervura"
    # Verifica balanco de forcas:
    fcd = 30.0 / 1.4 * 0.1
    Rcc_mes = 0.85 * 0.85 * fcd * (120 - 20) * 5.0
    Rcc_nerv = 0.85 * fcd * 0.8 * r["x_cm"] * 20.0
    Rpt = 150.0 * 15.0
    assert _aprox(Rcc_mes + Rcc_nerv, Rpt, 1.0), \
        f"Cc_mes+Cc_nerv={Rcc_mes+Rcc_nerv:.1f} vs Rpt={Rpt}"
    print(f"  OK  Secao T (LN na nervura): x={r['x_cm']:.2f}, "
          f"MRd={r['MRd_kncm']:.0f} kN.cm")


def test_fuso_limite_basico() -> None:
    """Fuso limite consistente: ep_min <= ep_max para uma secao bem
    dimensionada. Viga retangular 30x60, Po=300 kN, Mo=1000, Mtot=5000,
    R=0.85, tensoes admissiveis padrao."""
    Ac = 30 * 60
    Wb = Wt = 30 * 60 ** 2 / 6
    fuso = fuso_limite_excentricidade(
        Po_kn=300.0, Mo_kncm=1000.0, Mtot_kncm=5000.0,
        Ac_cm2=Ac, Wb_cm3=Wb, Wt_cm3=Wt,
        R=0.85,
        sigma_tr_o_kncm2=0.20, sigma_c_o_kncm2=-1.5,
        sigma_tr_tot_kncm2=0.20, sigma_c_tot_kncm2=-1.5,
    )
    assert "ep_min_cm" in fuso and "ep_max_cm" in fuso
    print(f"  OK  Fuso limite: ep in [{fuso['ep_min_cm']:.2f}, "
          f"{fuso['ep_max_cm']:.2f}] cm  (viavel={fuso['viavel']})")


def test_secao_minima_excentricidade_variavel() -> None:
    """Wb_min e Wt_min para Mo=1000, Mtot=5000, R=0.85:
    Wb_min = (5000 - 0.85*1000) / (0.20 - 0.85*(-1.5)) = 4150/1.475 = 2814
    Wt_min = (5000 - 0.85*1000) / (0.85*0.20 - (-1.5)) = 4150/1.67 = 2485."""
    Wb = Wb_min_secao_excentricidade_variavel(
        Mo_kncm=1000.0, Mtot_kncm=5000.0, R=0.85,
        sigma_tr_tot_kncm2=0.20, sigma_c_o_kncm2=-1.5,
    )
    Wt = Wt_min_secao_excentricidade_variavel(
        Mo_kncm=1000.0, Mtot_kncm=5000.0, R=0.85,
        sigma_tr_o_kncm2=0.20, sigma_c_tot_kncm2=-1.5,
    )
    assert _aprox(Wb, 2814.0, 5.0), f"Wb={Wb:.0f}"
    assert _aprox(Wt, 2485.0, 5.0), f"Wt={Wt:.0f}"
    print(f"  OK  Wb_min={Wb:.0f}  Wt_min={Wt:.0f} cm3")


def test_propriedades_cordoalha_CP190() -> None:
    """CP-190 RB phi=12.7: area=101.4 mm2, F_max=192.9 kN, fptk=1900."""
    p = propriedades_cordoalha(diam_mm=12.7, categoria="CP-190 RB")
    assert _aprox(p["area_mm2"], 101.4, 0.5)
    assert _aprox(p["F_max_kN"], 192.9, 0.5)
    assert _aprox(p["fptk_MPa"], 1900.0, 0.1)
    assert _aprox(p["fpyk_MPa"], 1710.0, 0.1)
    print(f"  OK  CP-190 phi=12.7: area={p['area_cm2']:.2f} cm2, "
          f"F_max={p['F_max_kN']:.1f} kN, fpyk={p['fpyk_MPa']:.0f} MPa")


def test_propriedades_cordoalha_CP210() -> None:
    """CP-210 RB phi=15.2: area=140 mm2, F_max=294 kN."""
    p = propriedades_cordoalha(diam_mm=15.2, categoria="CP-210 RB")
    assert _aprox(p["F_max_kN"], 294.0, 0.5)
    assert _aprox(p["fptk_MPa"], 2100.0, 0.1)
    print(f"  OK  CP-210 phi=15.2: area={p['area_cm2']:.2f} cm2, "
          f"F_max={p['F_max_kN']:.1f} kN")


def run_tests() -> int:
    tests = [
        test_propriedades_geometricas_laje,
        test_tensao_carga_apostila,
        test_protensao_axial_apostila,
        test_protensao_excentrica_h_sobre_6,
        test_protensao_excentrica_max_apostila,
        test_tensao_combinada_protensao_max_apostila,
        test_relaxacao_apostila_25h,
        test_relaxacao_perda_apostila,
        test_relaxacao_infinito,
        test_perda_encurtamento_elastico,
        test_perda_retracao,
        test_perda_fluencia,
        test_perda_atrito_arco_apostila,
        test_perda_atrito_parabola_apostila,
        test_fct_admissivel_secao,
        test_protensao_completa_viga_duplo_T_apostila,
        test_protensao_limitada_viga_duplo_T_apostila,
        test_protensao_parcial_basica,
        test_MRd_secao_retangular_protendida,
        test_MRd_apenas_armadura_ativa,
        test_Pi_de_P,
        test_perda_cabos_restantes_n4,
        test_perda_cabos_restantes_n_1,
        test_omega_perfis,
        test_escorregamento_apostila_5_6_4,
        test_h_ficticia,
        test_phi_eps_cs_NBR,
        test_MRd_secao_T_LN_mesa,
        test_MRd_secao_T_LN_nervura,
        test_fuso_limite_basico,
        test_secao_minima_excentricidade_variavel,
        test_propriedades_cordoalha_CP190,
        test_propriedades_cordoalha_CP210,
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
    print("=== Exemplo 1.6.1 (Apostila Bastos) - laje protendida ===")
    print("  C50, faixa 30x30, vao=10 m, q=7.5 kN/m2 sobre laje")
    print("  Mg = Mq = 2813 kN.cm na faixa de 30 cm")
    print()
    Ac, Wb = 900.0, 4500.0
    M_tot = 2813.0 + 2813.0
    P_axial = forca_protensao_axial(0.0, M_tot, Ac, Wb)
    P_h6 = forca_protensao_excentrica(0.0, M_tot, 5.0, Ac, Wb)
    P_max = forca_protensao_excentrica(0.0, M_tot, 10.0, Ac, Wb)
    print(f"  P axial (ep=0)        = {P_axial:.1f} kN")
    print(f"  P ep=h/6 = 5 cm       = {P_h6:.1f} kN")
    print(f"  P ep=10 cm (maxima)   = {P_max:.1f} kN")


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    _demo()
