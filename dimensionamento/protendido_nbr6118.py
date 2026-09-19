"""Concreto Protendido - Fundamentos (NBR 6118:2026).

Nome ate 19/09/2026: protendido_bastos.py. O credito as apostilas esta abaixo.

Implementa as analises elasticas e perdas de protensao seguindo a apostila
"FUNDAMENTOS DO CONCRETO PROTENDIDO", Prof. Paulo Sergio Bastos,
UNESP/Bauru. As grandezas de material (fct,m, Eci, Ecs, o diagrama
retangular e o limite de dutilidade) delegam ao nucleo normativo
(nucleo_nbr6118.py), que segue a NBR 6118:2026.

Casos cobertos:
    - Tensoes elasticas em viga protendida (Eq. 1.7-1.12)
    - Modulos de resistencia W_b, W_t (Eq. 1.9, 1.10)
    - Nucleo central de inercia (h/6 para retangular)
    - Estimativa de forca de protensao (axial e excentrica) - laje exemplo 1.6.1
    - Perda por relaxacao do aco (Eq. 5.11-5.13)
    - Perda por encurtamento elastico imediato do concreto (Eq. 5.56)
    - Perda por retracao/fluencia simplificada (Eq. 5.16, 5.17)
    - Perda progressiva simplificada com interacao retracao+fluencia+
      relaxacao (NBR 6118 9.6.3.4.2)

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

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
    import tempo_concreto_nbr6118 as tc
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr
    from dimensionamento import tempo_concreto_nbr6118 as tc


GAMA_C = 1.4
GAMA_S = 1.15

E_S_MPA = 210000.0
E_P_MPA = 200000.0    # aco de protensao (NBR 6118 8.4.5)


# ---------------------------------------------------------------------------
# Resistencias e modulos
# ---------------------------------------------------------------------------
def fctm_mpa(fck_mpa: float) -> float:
    """fct,m, MPa - delega ao nucleo (nbr.fct_m). Inclui o ramo de fck > 50
    (8.2.5); corrige PRO-01, que so tinha a formula do Grupo I."""
    return nbr.fct_m(fck_mpa)


def fct_flexao_mpa(fck_mpa: float, alpha: float = 1.5) -> float:
    """Resistencia a tracao na flexao: fct,f = alpha * fct,m,
    com alpha=1.2 para secao T, 1.5 para retangular."""
    return alpha * fctm_mpa(fck_mpa)


def Eci_mpa(fck_mpa: float, agregado: str = "granito") -> float:
    """Modulo de elasticidade tangente inicial Eci, MPa - delega ao nucleo
    (nbr.Eci). Inclui o ramo de fck > 50 (8.2.8); corrige PRO-01."""
    return nbr.Eci(fck_mpa, nbr.alpha_E(agregado))


def Ecs_mpa(fck_mpa: float, agregado: str = "granito") -> float:
    """Modulo de deformacao secante Ecs, MPa - delega ao nucleo (nbr.Ecs)."""
    return nbr.Ecs(fck_mpa, nbr.alpha_E(agregado))


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
# Tabela 8.3 (NBR 6118 8.4.8, PDF p. 51) - psi_1000 (%) por tipo de armadura
# (fio ou cordoalha), categoria de relaxacao (RN normal, RB baixa) e razao
# sigma_pi/fptk. "Barras" tem uma unica coluna (sem RN/RB).
TABELA_8_3_PSI_1000 = {
    ("cordoalha", "RN"): {0.5: 0.0, 0.6: 3.5, 0.7: 7.0, 0.8: 12.0},
    ("cordoalha", "RB"): {0.5: 0.0, 0.6: 1.3, 0.7: 2.5, 0.8: 3.5},
    ("fio", "RN"):       {0.5: 0.0, 0.6: 2.5, 0.7: 5.0, 0.8: 8.5},
    ("fio", "RB"):       {0.5: 0.0, 0.6: 1.0, 0.7: 2.0, 0.8: 3.0},
}
TABELA_8_3_PSI_1000_BARRA = {0.5: 0.0, 0.6: 1.5, 0.7: 4.0, 0.8: 7.0}


def psi_1000(tipo: str, relaxacao: str, sigma_pi_sobre_fptk: float) -> float:
    """psi_1000 (%) pela Tabela 8.3 (NBR 6118 8.4.8), por interpolacao linear
    entre as linhas de sigma_pi/fptk tabeladas. O texto de 8.4.8 define
    psi_1000 exatamente nessa faixa (tensoes de 0,5 fptk a 0,8 fptk).
    Abaixo de 0,5 fptk devolve 0: "para tensões inferiores a 0,5 fptk,
    admite-se que não haja perda de tensão por relaxação" (9.6.3.4.5,
    PDF p. 74; P30 — antes levantava ValueError). Acima de 0,8 fptk (ou
    razão negativa) levanta ValueError, a norma não cobre.

    tipo = 'fio', 'cordoalha' ou 'barra'; relaxacao = 'RN' ou 'RB'
    (ignorada para 'barra', que a tabela só dá numa coluna).
    Corrige PRO-04: os valores antigos de PSI_1000_TIPICOS não eram os da
    Tabela 8.3."""
    tipo_key = tipo.strip().lower()
    if tipo_key == "barra":
        tabela = TABELA_8_3_PSI_1000_BARRA
    else:
        if tipo_key not in ("fio", "cordoalha"):
            raise ValueError(
                f"tipo desconhecido: {tipo!r}. Use 'fio', 'cordoalha' ou 'barra'."
            )
        relax_key = relaxacao.strip().upper()
        if relax_key not in ("RN", "RB"):
            raise ValueError(f"relaxacao desconhecida: {relaxacao!r}. Use 'RN' ou 'RB'.")
        tabela = TABELA_8_3_PSI_1000[(tipo_key, relax_key)]

    razao = float(sigma_pi_sobre_fptk)
    pontos = sorted(tabela)
    if 0.0 <= razao < pontos[0]:
        return 0.0  # 9.6.3.4.5 (P30): sem perda por relaxação abaixo de 0,5 fptk
    if razao < pontos[0] or razao > pontos[-1]:
        raise ValueError(
            f"sigma_pi/fptk = {razao:g} fora da faixa da Tabela 8.3 "
            f"({pontos[0]:g} a {pontos[-1]:g})."
        )
    for r0, r1 in zip(pontos, pontos[1:]):
        if r0 <= razao <= r1:
            v0, v1 = tabela[r0], tabela[r1]
            return v0 + (v1 - v0) * (razao - r0) / (r1 - r0)
    raise AssertionError("Faixa de σpi/fptk inalcançável.")  # pragma: no cover


PSI_1000_TIPICOS = {
    # (categoria comercial, relaxacao) -> psi_1000 (%) a 0,8 fptk, Tabela 8.3.
    # CP-175 e fio; CP-190 e CP-210 sao cordoalhas (ver propriedades_cordoalha
    # abaixo). Corrige PRO-04 (valores antigos nao eram os da Tabela 8.3).
    ("CP-175", "RN"): 8.5,
    ("CP-175", "RB"): 3.0,
    ("CP-190", "RN"): 12.0,
    ("CP-190", "RB"): 3.5,
    ("CP-210", "RN"): 12.0,
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
    """delta sigma_pr = psi/100 * sigma_pi  (Eq. 5.10).

    Parcela ISOLADA de relaxacao. A NBR 6118 9.6.3.4.2 nao soma esta parcela
    com perda_retracao_kncm2 e perda_fluencia_kncm2: a perda progressiva
    exige considerar a interacao entre as tres causas (ha um denominador de
    interacao). Para o processo da norma use perda_progressiva_simplificada
    (corrige a lacuna PRO-07 - a soma das isoladas superestimou a perda em
    +41% no achado)."""
    return psi_percent / 100.0 * sigma_pi_kncm2


def perda_encurtamento_elastico_kncm2(
    sigma_cp_kncm2: float, fck_mpa: float, agregado: str = "granito",
    Ep_mpa: float = E_P_MPA,
) -> float:
    """delta sigma_p,enc = alpha_p * sigma_cp  (Eq. 5.56), com
    alpha_p = Ep/Eci (NBR 6118 9.1 e 9.6.3.3.2.1). Corrige PRO-03, que usava
    Ecs em vez de Eci.
    sigma_cp = tensao no concreto ao nivel do CG da armadura."""
    Eci = Eci_mpa(fck_mpa, agregado)
    alpha_p = Ep_mpa / Eci
    return alpha_p * sigma_cp_kncm2


def perda_retracao_kncm2(eps_cs_permil: float,
                         Ep_mpa: float = E_P_MPA) -> float:
    """delta sigma_pcs = eps_cs * Ep  (Eq. 5.16).
    eps_cs em por mil (deformacao de retracao no infinito).

    Parcela ISOLADA de retracao - ver nota de perda_relaxacao_kncm2 sobre
    nao somar as tres parcelas isoladas (9.6.3.4.2, PRO-07)."""
    eps = eps_cs_permil / 1000.0
    return abs(eps) * Ep_mpa * 0.1  # MPa -> kN/cm2


def perda_fluencia_kncm2(phi_inf: float, sigma_c_to_kncm2: float,
                         fck_mpa: float, agregado: str = "granito",
                         Ep_mpa: float = E_P_MPA) -> float:
    """delta sigma_pcc = alpha_p * phi * sigma_c(to)  (Eq. 5.17/5.18), com
    alpha_p = Ep/Eci. Corrige PRO-03, que usava Ecs em vez de Eci.

    Parcela ISOLADA de fluencia - ver nota de perda_relaxacao_kncm2 sobre
    nao somar as tres parcelas isoladas (9.6.3.4.2, PRO-07)."""
    Eci = Eci_mpa(fck_mpa, agregado)
    alpha_p = Ep_mpa / Eci
    return alpha_p * phi_inf * abs(sigma_c_to_kncm2)


# ---------------------------------------------------------------------------
# Perda progressiva simplificada (9.6.3.4.2 - fases unicas de operacao)
# ---------------------------------------------------------------------------
def perda_progressiva_simplificada(
    eps_cs_permil: float, psi_percent: float, phi_inf: float,
    sigma_c_p0g_mpa: float, sigma_p0_mpa: float,
    Ap_cm2: float, Ac_cm2: float, Ic_cm4: float, ep_cm: float,
    fck_mpa: float, agregado: str = "granito", Ep_mpa: float = E_P_MPA,
    t0_dias: float = 28.0, cimento: str = "CPII",
    Eci_t0_mpa: float | None = None,
) -> float:
    """Perda progressiva de protensao pelo processo simplificado da NBR 6118
    9.6.3.4.2 (fases unicas de operacao; PDF p. 71-73), considerando a
    interacao entre retracao, fluencia do concreto e relaxacao do aco -
    ao contrario de somar as tres parcelas isoladas (perda_retracao_kncm2 +
    perda_fluencia_kncm2 + perda_relaxacao_kncm2), que NAO e o processo da
    norma (superestimou a perda em +41% no achado que motivou esta funcao -
    lacuna PRO-07).

    delta_sigma_p(t,t0) = [|eps_cs|*Ep + alpha_p(t)*sigma_c,p0g*phi + sigma_p0*chi]
                          / [chi_p + chi_c*alpha_p*eta*rho_p]
    com:
        chi        = -ln(1 - psi/100)   (coeficiente de fluencia do aco)
        chi_c      = 1 + 0,5*phi
        chi_p      = 1 + chi
        eta        = 1 + ep^2*Ac/Ic
        rho_p      = Ap/Ac
        alpha_p    = Ep/Eci             (idade >= 28 dias; 9.1)
        alpha_p(t) = Ep/Eci(t)          (idade t0 < 28 dias; 9.1 e PDF p. 72)
    Para t0 >= 28 dias, alpha_p(t) = alpha_p. Para t0 < 28 dias,
    Eci(t0) = (fckj/fck)^0,5 (ou ^0,3)*Eci (8.2.8), com fckj = beta1*fck
    (12.3.3, pelo cimento). A estimativa de 8.2.8 vale de 7 a 28 dias; abaixo
    de 7 dias informe Eci_t0_mpa (de ensaio).

    Unidades - todas as tensoes desta funcao em MPa (nao kN/cm2 como o
    resto do modulo), para casar direto com a formula da norma:
        eps_cs_permil   : retracao entre t0 e t (negativa), em per mil (8.2.11).
        psi_percent     : coeficiente de relaxacao do aco psi(t,t0), em %
                          (psi_infinito ou psi_t_em_dias/psi_t_em_horas).
        phi_inf         : coeficiente de fluencia do concreto phi(t,t0)
                          (phi_eps_cs_NBR).
        sigma_c_p0g_mpa : tensao no concreto junto ao cabo resultante apos
                          as perdas imediatas e a carga permanente em t0,
                          MPa, positiva se compressao.
        sigma_p0_mpa    : tensao na armadura ativa apos as perdas imediatas
                          em t0, MPa, sempre positiva (tracao).
        Ap_cm2, Ac_cm2, Ic_cm4, ep_cm : area do cabo resultante, area e
                          inercia do concreto e excentricidade do cabo
                          resultante em relacao ao CG da secao de concreto.
        fck_mpa, agregado : para alpha_p = Ep/Eci.
        t0_dias, cimento  : idade do concreto na protensao/carregamento e o
                          cimento (para beta1), para alpha_p(t).
        Eci_t0_mpa      : Eci(t0) de ensaio; substitui a estimativa.

    Retorna delta_sigma_p em MPa (perda de tensao na armadura ativa)."""
    Eci = Eci_mpa(fck_mpa, agregado)
    alpha_p = Ep_mpa / Eci
    if Eci_t0_mpa is not None:
        alpha_p_t = Ep_mpa / Eci_t0_mpa
    elif t0_dias >= 28.0:
        alpha_p_t = alpha_p
    elif t0_dias >= 7.0:
        fckj_t0 = nbr.fckj(fck_mpa, t0_dias, cimento)
        alpha_p_t = Ep_mpa / nbr.Eci_idade(fck_mpa, fckj_t0, nbr.alpha_E(agregado))
    else:
        raise nbr.FaixaNormativaError(
            f"t0 = {t0_dias:g} dias: a estimativa de Eci(t) de 8.2.8 vale de 7 a 28 "
            "dias. Informe Eci_t0_mpa (módulo de elasticidade medido na idade t0)."
        )
    chi = -math.log(1.0 - psi_percent / 100.0)
    chi_c = 1.0 + 0.5 * phi_inf
    chi_p = 1.0 + chi
    eta = 1.0 + ep_cm ** 2 * Ac_cm2 / Ic_cm4
    rho_p = Ap_cm2 / Ac_cm2

    numerador = (abs(eps_cs_permil) / 1000.0 * Ep_mpa
                 + alpha_p_t * sigma_c_p0g_mpa * phi_inf
                 + sigma_p0_mpa * chi)
    denominador = chi_p + chi_c * alpha_p * eta * rho_p
    return numerador / denominador


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
    fct = alpha * 0.7 * fct,m  (fct,m do nucleo, com o ramo de fck > 50 -
    8.2.5; corrige PRO-01); resultado em kN/cm2."""
    alpha = {"t": 1.2, "duplo-t": 1.2, "duplo t": 1.2,
             "i": 1.3, "t-invertido": 1.3, "t invertido": 1.3,
             "retangular": 1.5}.get(secao.lower(), 1.5)
    fct_mpa = alpha * 0.7 * nbr.fct_m(fck_mpa)
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
    gama_s: float = GAMA_S, alpha_c: float | None = None,
) -> dict:
    """Momento fletor resistente MRd no ELU para secao retangular com
    armaduras Ap, As e A's, com o diagrama retangular de 17.2.2 e) da
    NBR 6118: y = lambda*x e tensao constante alpha_c*etac*fcd, ambos
    dependentes de fck para fck > 50 (corrige PRO-05, que usava
    lambda = 0,8 e alpha_c*fcd fixos, sem etac).

    Eq. 6.10: x = (sigma_pd*Ap + fyd*As - fyd*A's) / (tensao_kncm2 * lambda * bw)
    Eq. 6.11: MRd = sigma_pd*Ap*(dp - lambda/2*x) + fyd*As*(ds - lambda/2*x)
                  + fyd*A's*(lambda/2*x - d')

    sigma_pd e o valor de tensao na armadura de protensao no ELU
    (estimado, geralmente ~1.520 MPa para CP-190 RB).
    alpha_c=None (padrao) usa o alpha_c(fck) do nucleo (0,85 ate C50,
    decrescente acima - 17.2.2 e). Um valor explicito substitui so o
    alpha_c, mantendo etac e fcd do nucleo (compatibilidade com chamadas
    antigas que passavam alpha_c=0.85).
    "ductil" usa o limite x/d de 14.6.4.3 (0,45 ate C50; 0,35 acima -
    corrige PRO-06, que usava 0,45 fixo).
    Resultado: MRd em kN.cm.
    """
    fyd_kncm = fyk_mpa / gama_s * 0.1     # kN/cm2
    sigma_pd_kncm = sigma_pd_mpa * 0.1
    lam = nbr.lambda_retangulo(fck_mpa)
    if alpha_c is None:
        tensao_kncm2 = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck_mpa, gama_c))
    else:
        tensao_kncm2 = nbr.mpa_para_kncm2(
            alpha_c * nbr.eta_c(fck_mpa) * nbr.fcd(fck_mpa, gama_c))

    num = sigma_pd_kncm * Ap_cm2 + fyd_kncm * As_cm2 - fyd_kncm * As_linha_cm2
    den = tensao_kncm2 * lam * bw_cm
    x = num / den
    braco = lam / 2.0 * x
    MRd = (sigma_pd_kncm * Ap_cm2 * (dp_cm - braco)
           + fyd_kncm * As_cm2 * (ds_cm - braco)
           + fyd_kncm * As_linha_cm2 * (braco - d_linha_cm))
    xd = x / max(dp_cm, ds_cm)
    return {
        "x_cm": x,
        "MRd_kncm": MRd,
        "x_d": xd,
        "ductil": xd <= nbr.xd_limite_dutilidade(fck_mpa),
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
    t0_dias: float | None = None, cimento: str = "CPII",
    Eci_t0_mpa: float | None = None,
) -> float:
    """delta sigma_p = alpha_p(t) * (n-1)/(2n) * sigma_cpog  (Eq. 5.62, NBR 9.6.3.3.2.1,
    PDF p. 70), com alpha_p(t) = Ep/Eci(t0) (P30, via alpha_p_t). Sem t0_dias
    nem Eci_t0_mpa usa alpha_p = Ep/Eci de 28 dias (comportamento anterior).
    Corrige PRO-03, que usava Ecs em vez de Eci.

    Perda media por cabo na pos-tensao quando os cabos sao estirados
    sucessivamente. sigma_cpog = tensao no concreto adjacente ao cabo
    apos perdas por atrito e ancoragem (positiva se compressao).
    n_cabos = numero de grupos de cabos protendidos simultaneamente.
    """
    if n_cabos < 1:
        raise ValueError("n_cabos deve ser >= 1")
    alpha_p = alpha_p_t(fck_mpa, t0_dias, cimento, agregado, Ep_mpa, Eci_t0_mpa)
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
# NBR 6118 8.2.11 - Retracao e fluencia (Tabela 8.1, versao simplificada)
# ---------------------------------------------------------------------------
# A Tabela 8.1 (NBR 6118:2026 8.2.11, PDF p. 47) e phi_eps_cs_NBR foram
# promovidas ao nucleo no pacote P6 (19/09/2026); os nomes abaixo sao
# reexportacoes, para nao quebrar quem importa daqui. O procedimento completo
# do Anexo A (fluencia e retracao com precisao) esta em tempo_concreto_nbr6118.
TABELA_8_1_PHI = nbr.TABELA_8_1_PHI
TABELA_8_1_EPS_CS = nbr.TABELA_8_1_EPS_CS
_T0_TAB_8_1 = nbr._T0_TAB_8_1
_UMIDADE_TAB_8_1 = nbr._UMIDADE_TAB_8_1
_HFIC_TAB_8_1 = nbr._HFIC_TAB_8_1
_bloco_classe_tabela_8_1 = nbr._bloco_classe_tabela_8_1
_interp_1d = nbr._interp_1d_tabela_8_1
_interp_tabela_8_1 = nbr._interp_tabela_8_1
phi_eps_cs_NBR = nbr.phi_eps_cs_NBR


def h_ficticia_cm(Ac_cm2: float, u_ar_cm: float, gama_humid: float = 1.0) -> float:
    """h_fic = gamma * 2*Ac / u_ar  (NBR 6118 A.2.4.2 e Tabela A.1).
    u_ar = perimetro em contato com o ar. Delega a
    tempo_concreto_nbr6118.espessura_ficticia_cm (P6); gama_humid=1,0
    (padrao) devolve a espessura ficticia sem ponderacao."""
    return gama_humid * tc.espessura_ficticia_cm(Ac_cm2, u_ar_cm)


# ---------------------------------------------------------------------------
# ELU - Secao T protendida (Eq. 6.16, 6.17)
# ---------------------------------------------------------------------------
def MRd_secao_T_protendida(
    bf_cm: float, bw_cm: float, hf_cm: float,
    dp_cm: float, ds_cm: float, d_linha_cm: float,
    Ap_cm2: float, As_cm2: float, As_linha_cm2: float,
    fck_mpa: float, sigma_pd_mpa: float = 1520.0,
    fyk_mpa: float = 500.0, gama_c: float = GAMA_C,
    gama_s: float = GAMA_S, alpha_c: float | None = None,
) -> dict:
    """MRd para secao T protendida (Eq. 6.16, 6.17), com lambda, tensao do
    bloco (alpha_c*etac*fcd) e limite de dutilidade dependentes de fck para
    fck > 50 (corrige PRO-05/PRO-06 - ver MRd_secao_retangular_protendida).

    Inicialmente assume secao retangular bf. Se lambda*x <= hf, retorna esse
    resultado. Caso contrario aplica formula T:
       x = (sigma_pd*Ap + fyd*As - tensao_kncm2*(bf-bw)*hf - fyd*A's)
            / (tensao_kncm2 * lambda * bw)
       MRd = tensao_kncm2*(bf-bw)*hf*(lambda/2*x - 0.5*hf)
             + sigma_pd*Ap*(dp - lambda/2*x) + fyd*As*(ds - lambda/2*x)
             + fyd*A's*(lambda/2*x - d')
    A mesa recebe a mesma tensao alpha_c*etac*fcd da nervura: com a mesa
    comprimida a largura nao diminui em direcao a borda comprimida (17.2.2 e).
    O codigo antigo multiplicava a mesa por um 0,85 extra (0,72*fcd em vez de
    0,85*fcd; achado PRO-09 da consolidacao, a favor da seguranca, ~3 % em MRd).
    alpha_c=None (padrao) usa o alpha_c(fck) do nucleo; um valor explicito
    substitui so o alpha_c, mantendo etac e fcd do nucleo (compatibilidade).
    """
    fyd_kncm = fyk_mpa / gama_s * 0.1
    sigma_pd_kncm = sigma_pd_mpa * 0.1
    lam = nbr.lambda_retangulo(fck_mpa)
    if alpha_c is None:
        tensao_kncm2 = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck_mpa, gama_c))
    else:
        tensao_kncm2 = nbr.mpa_para_kncm2(
            alpha_c * nbr.eta_c(fck_mpa) * nbr.fcd(fck_mpa, gama_c))

    # 1) Tentativa retangular bf
    r_ret = MRd_secao_retangular_protendida(
        bw_cm=bf_cm, dp_cm=dp_cm, ds_cm=ds_cm, d_linha_cm=d_linha_cm,
        Ap_cm2=Ap_cm2, As_cm2=As_cm2, As_linha_cm2=As_linha_cm2,
        fck_mpa=fck_mpa, sigma_pd_mpa=sigma_pd_mpa, fyk_mpa=fyk_mpa,
        gama_c=gama_c, gama_s=gama_s, alpha_c=alpha_c,
    )
    if lam * r_ret["x_cm"] <= hf_cm:
        r_ret["secao"] = "T-como-retangular-bf"
        return r_ret

    # 2) LN na nervura - Eq. 6.16, com a mesma tensao na mesa (17.2.2 e; PRO-09)
    Rcc_mes = tensao_kncm2 * (bf_cm - bw_cm) * hf_cm
    num = (sigma_pd_kncm * Ap_cm2 + fyd_kncm * As_cm2
           - Rcc_mes - fyd_kncm * As_linha_cm2)
    den = tensao_kncm2 * lam * bw_cm
    x = num / den
    braco = lam / 2.0 * x
    MRd = (Rcc_mes * (braco - 0.5 * hf_cm)
           + sigma_pd_kncm * Ap_cm2 * (dp_cm - braco)
           + fyd_kncm * As_cm2 * (ds_cm - braco)
           + fyd_kncm * As_linha_cm2 * (braco - d_linha_cm))
    xd = x / max(dp_cm, ds_cm)
    return {
        "x_cm": x,
        "MRd_kncm": MRd,
        "x_d": xd,
        "ductil": xd <= nbr.xd_limite_dutilidade(fck_mpa),
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

    Nao e item da NBR 6118 (apostila, item 4.6.2) - a norma nao impõe este
    metodo. As quatro equacoes foram re-derivadas em 09/2026 isolando ep em
    sigma_base_topo (a convencao de sinais deste modulo: compressao
    negativa, tracao positiva, sinal_P=-1): as originais tinham sinal
    trocado e nao reproduziam a tensao-alvo ao realimentar ep em
    sigma_base_topo (achado PRO-08).

    Retorna ep_min e ep_max (cm) e os 4 limites individuais.
    """
    eta_t = Ac_cm2 / Wt_cm3
    eta_b = Ac_cm2 / Wb_cm3

    # Eq. 4.77 (transferencia, fibra topo, tracao admissivel): isola ep de
    # sigma_t(Po, Mo, ep) = -Po/Ac + Po*ep/Wt - Mo/Wt = sigma_tr_o
    ep_77 = Mo_kncm / Po_kn + Wt_cm3 * sigma_tr_o_kncm2 / Po_kn + 1.0 / eta_t
    # Eq. 4.78 (transferencia, fibra base, compressao admissivel): isola ep de
    # sigma_b(Po, Mo, ep) = -Po/Ac - Po*ep/Wb + Mo/Wb = sigma_c_o
    ep_78 = Mo_kncm / Po_kn - Wb_cm3 * sigma_c_o_kncm2 / Po_kn - 1.0 / eta_b
    # Eq. 4.79 (apos perdas, fibra topo, compressao admissivel): isola ep de
    # sigma_t(R*Po, Mtot, ep) = -R*Po/Ac + R*Po*ep/Wt - Mtot/Wt = sigma_c_tot
    ep_79 = Mtot_kncm / (R * Po_kn) + Wt_cm3 * sigma_c_tot_kncm2 / (R * Po_kn) + 1.0 / eta_t
    # Eq. 4.80 (apos perdas, fibra base, tracao admissivel): isola ep de
    # sigma_b(R*Po, Mtot, ep) = -R*Po/Ac - R*Po*ep/Wb + Mtot/Wb = sigma_tr_tot
    ep_80 = Mtot_kncm / (R * Po_kn) - Wb_cm3 * sigma_tr_tot_kncm2 / (R * Po_kn) - 1.0 / eta_b

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

    ``categoria`` só precisa conter "CP-190" ou "CP-210": um eventual sufixo
    RN/RB (ex.: "CP-190 RB", "CP-190 RN") é aceito mas ignorado aqui de
    propósito, porque RN e RB têm a mesma geometria, massa e fptk dentro da
    mesma categoria (8.4.1) -- a diferença entre elas está na perda por
    relaxação (ver PSI_1000_TIPICOS), não na geometria do produto.
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
    """alpha_p = Ep/Eci (NBR 6118 9.1, 9.6.3.3.2.1 - corrige PRO-03, que usava
    Ecs). Ep=200 GPa, C50 -> Eci ~ 39.6 GPa (granito), alpha_p ~ 5.05.
    sigma_cp = 1.0 kN/cm2 (10 MPa) -> perda = 5.05 kN/cm2 = 50.5 MPa."""
    p = perda_encurtamento_elastico_kncm2(
        sigma_cp_kncm2=1.0, fck_mpa=50.0,
    )
    Eci = Eci_mpa(50.0)
    alpha_p_esperado = E_P_MPA / Eci
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
    """alpha_p = Ep/Eci (corrige PRO-03, que usava Ecs). phi=2.0,
    sigma_c(to)=10 MPa, C50 -> alpha_p~5.05; perda = 10.1 kN/cm2 = 101 MPa."""
    p = perda_fluencia_kncm2(phi_inf=2.0, sigma_c_to_kncm2=1.0,
                              fck_mpa=50.0)
    Eci = Eci_mpa(50.0)
    expected = (E_P_MPA / Eci) * 2.0 * 1.0
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
    """alpha_p = Ep/Eci (corrige PRO-03, que usava Ecs). n=4 cabos,
    sigma_cpog=10 MPa, C40 (Eci ~ 35.4 GPa, alpha_p ~ 5.65):
    delta = alpha_p * (n-1)/(2n) * sigma_cpog
          = 5.65 * 3/8 * 1.0 = 2.12 kN/cm2 = 21.2 MPa."""
    p = perda_encurtamento_cabos_restantes_kncm2(
        n_cabos=4, sigma_cpog_kncm2=1.0, fck_mpa=40.0,
    )
    Eci = Eci_mpa(40.0)
    expected = (E_P_MPA / Eci) * (3.0 / 8.0) * 1.0
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
    """Tabela 8.1 NBR 6118:2026 (8.2.11, PDF p.47): U=75%, h_fic=20cm,
    to=30d (padrao), fck=30 (padrao, bloco C20-C45): phi_inf=2.2,
    eps_cs=-0.33 permil. Corrige PRO-02: a versao antiga ignorava to_dias e
    dava 2.8 (valor de t0=5, nao t0=30) para este ponto."""
    phi, eps = phi_eps_cs_NBR(umidade_pct=75.0, h_fic_cm=20.0)
    assert _aprox(phi, 2.2, 0.01)
    assert _aprox(eps, -0.33, 0.001)
    print(f"  OK  phi_inf(75%, 20cm, t0=30, C20-C45) = {phi}, "
          f"eps_cs = {eps} permil")


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
    # Verifica balanco de forcas, com a mesma tensao 0,85*fcd na mesa e na
    # nervura (17.2.2 e; PRO-09: o 0,85 extra da mesa foi removido):
    fcd = 30.0 / 1.4 * 0.1
    Rcc_mes = 0.85 * fcd * (120 - 20) * 5.0
    Rcc_nerv = 0.85 * fcd * 0.8 * r["x_cm"] * 20.0
    assert _aprox(r["x_cm"], 45.96, 0.05), f"x={r['x_cm']:.2f}"
    Rpt = 150.0 * 15.0
    assert _aprox(Rcc_mes + Rcc_nerv, Rpt, 1.0), \
        f"Cc_mes+Cc_nerv={Rcc_mes+Rcc_nerv:.1f} vs Rpt={Rpt}"
    print(f"  OK  Secao T (LN na nervura): x={r['x_cm']:.2f}, "
          f"MRd={r['MRd_kncm']:.0f} kN.cm")


def test_fuso_limite_basico() -> None:
    """PRO-08: as 4 equacoes de fuso_limite_excentricidade foram
    re-derivadas isolando ep em sigma_base_topo (as originais tinham sinal
    trocado; o teste antigo so conferia se as chaves existiam). Entrada do
    achado: Po=800, Mo=4000, Ac=1800, Wb=Wt=18000, R=0.85, Mtot=9000,
    sigma_tr_o=0.10, sigma_c_o=-1.6, sigma_tr_tot=0.12, sigma_c_tot=-1.5.
    Esperado: ep_77=+17,25; ep_78=+31,00; ep_79=-16,47; ep_80=+0,059 cm -
    e cada um deve, ao realimentar sigma_base_topo, reproduzir a
    tensao-alvo correspondente."""
    Po, Mo, Mtot, R = 800.0, 4000.0, 9000.0, 0.85
    Ac, Wb, Wt = 1800.0, 18000.0, 18000.0
    sigma_tr_o, sigma_c_o = 0.10, -1.6
    sigma_tr_tot, sigma_c_tot = 0.12, -1.5

    fuso = fuso_limite_excentricidade(
        Po_kn=Po, Mo_kncm=Mo, Mtot_kncm=Mtot,
        Ac_cm2=Ac, Wb_cm3=Wb, Wt_cm3=Wt, R=R,
        sigma_tr_o_kncm2=sigma_tr_o, sigma_c_o_kncm2=sigma_c_o,
        sigma_tr_tot_kncm2=sigma_tr_tot, sigma_c_tot_kncm2=sigma_c_tot,
    )
    assert _aprox(fuso["ep_77_top_o"], 17.25, 0.005), fuso["ep_77_top_o"]
    assert _aprox(fuso["ep_78_base_o"], 31.00, 0.005), fuso["ep_78_base_o"]
    assert _aprox(fuso["ep_79_top_tot"], -16.47, 0.005), fuso["ep_79_top_tot"]
    assert _aprox(fuso["ep_80_base_tot"], 0.059, 0.005), fuso["ep_80_base_tot"]

    # Realimenta cada ep em sigma_base_topo: tem que reproduzir a tensao-alvo.
    _, st_o = sigma_base_topo(Po, fuso["ep_77_top_o"], Mo, Ac, Wb, Wt)
    assert _aprox(st_o, sigma_tr_o, 1e-6), f"st_o={st_o}"
    sb_o, _ = sigma_base_topo(Po, fuso["ep_78_base_o"], Mo, Ac, Wb, Wt)
    assert _aprox(sb_o, sigma_c_o, 1e-6), f"sb_o={sb_o}"
    _, st_tot = sigma_base_topo(R * Po, fuso["ep_79_top_tot"], Mtot, Ac, Wb, Wt)
    assert _aprox(st_tot, sigma_c_tot, 1e-6), f"st_tot={st_tot}"
    sb_tot, _ = sigma_base_topo(R * Po, fuso["ep_80_base_tot"], Mtot, Ac, Wb, Wt)
    assert _aprox(sb_tot, sigma_tr_tot, 1e-6), f"sb_tot={sb_tot}"

    print(f"  OK  Fuso limite (sinais corrigidos): "
          f"ep_77={fuso['ep_77_top_o']:.2f}, ep_78={fuso['ep_78_base_o']:.2f}, "
          f"ep_79={fuso['ep_79_top_tot']:.2f}, "
          f"ep_80={fuso['ep_80_base_tot']:.3f} cm")


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


# === P3: Catálogo de aço ativo (8.4.1, p.49) e dutilidade (8.4.6, p.50) ===
# Fios de aço de protensão (NBR 7482) -- valores nominais de catálogo de
# fabricante (ArcelorMittal/Belgo, ABNT NBR 7482, "Fios e Cordoalhas para
# Concreto Protendido"). Corrigido na verificação do pacote P3 (19/09/2026):
# os pares antigos não batiam com o catálogo, e a estrutura de uma única
# entrada por diâmetro não suporta os diâmetros que têm mais de uma
# categoria/fptk (6,0 mm e 7,0 mm existem em duas categorias, com a mesma
# área mas fptk diferente). A chave agora é (diâmetro, categoria). ATENÇÃO:
# a NBR 7482 não está entre as páginas da NBR 6118:2026 lidas para este
# pacote (é outra norma), então esta tabela não foi conferida contra o texto
# original da NBR 7482 -- só contra o catálogo de mercado citado acima.
# Conferir com o fabricante antes de uso em projeto real.
TABELA_FIOS_NBR7482 = {
    # (diam_mm, categoria): (area_mm2, fptk_MPa)
    (4.0, "CP-175"): (12.6, 1750.0),
    (5.0, "CP-175"): (19.6, 1750.0),
    (6.0, "CP-175"): (28.3, 1750.0),
    (6.0, "CP-190"): (28.3, 1900.0),
    (7.0, "CP-170"): (38.5, 1700.0),
    (7.0, "CP-190"): (38.5, 1900.0),
    (8.0, "CP-150"): (50.3, 1500.0),
    (9.0, "CP-145"): (63.6, 1450.0),
}


def propriedades_fio(diam_mm: float, categoria: str | None = None) -> dict:
    """Retorna propriedades do fio de aço de protensão (NBR 7482).

    Área em mm2; fptk conforme a categoria (CP) associada ao diâmetro pela
    tabela de catálogo. Alguns diâmetros (6,0 mm e 7,0 mm) existem em mais de
    uma categoria com fptk diferente -- nesse caso ``categoria`` é
    obrigatória; se o diâmetro só tiver uma categoria no catálogo, pode ser
    omitida. Ver ressalva de TABELA_FIOS_NBR7482 sobre a fonte.
    """
    opcoes = {c: (a, f) for (d, c), (a, f) in TABELA_FIOS_NBR7482.items() if d == diam_mm}
    if not opcoes:
        raise ValueError(f"diâmetro {diam_mm} não tabelado em TABELA_FIOS_NBR7482")
    if categoria is None:
        if len(opcoes) > 1:
            raise ValueError(
                f"diâmetro {diam_mm} tem mais de uma categoria no catálogo "
                f"({sorted(opcoes)}); informe categoria."
            )
        categoria = next(iter(opcoes))
    elif categoria not in opcoes:
        raise ValueError(
            f"categoria {categoria!r} não tabelada para o diâmetro {diam_mm} "
            f"(opções: {sorted(opcoes)})"
        )
    area, fptk = opcoes[categoria]
    return {
        "diam_mm": diam_mm,
        "area_mm2": area,
        "area_cm2": area / 100.0,
        "fptk_MPa": fptk,
        "categoria": categoria,
    }


# Catálogo unificado (8.4.1): fios (NBR 7482) e cordoalhas (NBR 7483). RN
# (relaxação normal) e RB (relaxação baixa) têm a mesma geometria, massa e
# fptk dentro de cada categoria (CP-190/CP-210) -- a diferença entre RN e RB
# está na perda por relaxação, já coberta por PSI_1000_TIPICOS (chave
# (categoria, "RN"/"RB")) e não na geometria do produto; por isso a mesma
# tabela geométrica atende as duas classes de relaxação, e
# propriedades_cordoalha() aceita (e ignora) o sufixo RN/RB na string de
# categoria.
TABELA_ACOS_ATIVOS = {
    "fios": TABELA_FIOS_NBR7482,
    "cordoalhas": {
        "CP-190": TABELA_CORDOALHAS_CP190_RB,
        "CP-210": TABELA_CORDOALHAS_CP210_RB,
    },
}


@dataclass(frozen=True)
class DutilidadeAcoAtivo:
    """Classificação de dutilidade de fio/cordoalha de aço ativo (8.4.6, p.50)."""
    eps_uk_pmilh: float
    minimo_pmilh: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def dutilidade_aco_ativo(eps_uk_pmilh: float, minimo_pmilh: float) -> DutilidadeAcoAtivo:
    """Classifica a dutilidade de um fio ou cordoalha de aço ativo (8.4.6).

    "Os fios e cordoalhas cujo valor de eps_uk for maior que o mínimo
    indicado nas ABNT NBR 7482 e ABNT NBR 7483, respectivamente, podem ser
    considerados como tendo dutilidade normal." (8.4.6, PDF p. 50)

    eps_uk_pmilh: alongamento após ruptura característico do lote/catálogo, em
        por mil.
    minimo_pmilh: mínimo exigido pela NBR 7482 (fio) ou NBR 7483 (cordoalha)
        para o produto em questão, em por mil (varia por fabricante/produto e
        deve ser informado pelo chamador).
    """
    ok = float(eps_uk_pmilh) > float(minimo_pmilh)
    governante = "dutilidade normal" if ok else "abaixo do mínimo normativo"
    memoria = (
        f"8.4.6 (p.50): eps_uk = {eps_uk_pmilh:g} por mil; "
        f"mínimo NBR 7482/7483 = {minimo_pmilh:g} por mil.",
        f"eps_uk {'>' if ok else '<='} mínimo -> {governante}.",
    )
    return DutilidadeAcoAtivo(
        eps_uk_pmilh=float(eps_uk_pmilh), minimo_pmilh=float(minimo_pmilh),
        ok=ok, governante=governante, memoria=memoria,
    )


# === P30: Protensão — força, limites e perdas (9.6.1 e 9.6.3, p. 67-74) ===
try:  # executado como script, ou com dimensionamento/ no sys.path
    import acoes_nbr6118 as _acoes_p30
    import seguranca_nbr6118 as _seg_p30
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import acoes_nbr6118 as _acoes_p30
    from dimensionamento import seguranca_nbr6118 as _seg_p30

from typing import Iterable as _Iterable_p30


def _fmt_p30(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


# 9.6.1.2.1 (PDF p. 67) — σpi na saída do aparelho de tração, em fração de fptk.
# Válidos para aços que atendam às ABNT NBR 7482 e ABNT NBR 7483.
TABELA_9_6_1_2_1_SIGMA_PI = {
    "pre_tracionada": 0.77,           # a) armadura pré-tracionada
    "pos_tracionada_aderente": 0.74,  # b) armadura pós-tracionada aderente
    "pos_tracionada_nao_aderente": 0.80,  # c) armadura pós-tracionada não aderente
    "barra_cp85_105": 0.72,           # d) barras de aço CP-85/105
}
_ALINEA_9_6_1_2_1 = {
    "pre_tracionada": "a", "pos_tracionada_aderente": "b",
    "pos_tracionada_nao_aderente": "c", "barra_cp85_105": "d",
}
_ALIAS_SISTEMA_P30 = {
    "pre": "pre_tracionada", "pretracionada": "pre_tracionada",
    "pretracao": "pre_tracionada", "pre_tracionada": "pre_tracionada",
    "pos_aderente": "pos_tracionada_aderente", "posaderente": "pos_tracionada_aderente",
    "pos_tracionada_aderente": "pos_tracionada_aderente",
    "postracionadaaderente": "pos_tracionada_aderente",
    "pos_nao_aderente": "pos_tracionada_nao_aderente",
    "posnaoaderente": "pos_tracionada_nao_aderente",
    "pos_tracionada_nao_aderente": "pos_tracionada_nao_aderente",
    "postracionadanaoaderente": "pos_tracionada_nao_aderente",
}
_ALIAS_ACO_P30 = {
    "fio_cordoalha": "fio_cordoalha", "fio": "fio_cordoalha", "cordoalha": "fio_cordoalha",
    "barra": "barra_cp85_105", "barra_cp85_105": "barra_cp85_105",
    "cp85/105": "barra_cp85_105", "cp-85/105": "barra_cp85_105",
}

# 9.6.1.2.3 (PDF p. 67) — tolerância de execução na pós-tração.
MAJORACAO_TOLERANCIA_EXECUCAO = 1.10   # "majorados em até 10 %"
FRACAO_MAX_CABOS_TOLERANCIA = 0.50     # "até o limite de 50 % dos cabos"

# 9.6.1.3 (PDF p. 68) — valores característicos superior e inferior.
LIMITE_PERDA_PK_SOBRE_PI = 0.35
FATOR_PK_SUP = 1.05
FATOR_PK_INF = 0.95


def _chave_p30(texto: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return s.strip().lower().replace("-", "_").replace(" ", "_")


def _sistema_p30(sistema: str) -> str:
    k = _chave_p30(sistema)
    if k in _ALIAS_SISTEMA_P30:
        return _ALIAS_SISTEMA_P30[k]
    k2 = k.replace("_", "")
    if k2 in _ALIAS_SISTEMA_P30:
        return _ALIAS_SISTEMA_P30[k2]
    raise ValueError(
        f"Sistema de protensão desconhecido: {sistema!r}. Use 'pre_tracionada', "
        "'pos_tracionada_aderente' ou 'pos_tracionada_nao_aderente'.")


def _aco_p30(aco: str) -> str:
    k = _chave_p30(aco)
    if k in _ALIAS_ACO_P30:
        return _ALIAS_ACO_P30[k]
    raise ValueError(
        f"Aço de protensão desconhecido: {aco!r}. Use 'fio_cordoalha' ou 'barra' (CP-85/105).")


def _positivo_p30(valor: float, nome: str) -> float:
    v = float(valor)
    if not v > 0.0:
        raise nbr.FaixaNormativaError(f"{nome} = {v:g}: tem de ser positivo.")
    return v


def sigma_pi_limite_mpa(fptk_mpa: float, sistema: str,
                        aco: str = "fio_cordoalha") -> float:
    """Limite de σpi na saída do aparelho de tração, MPa (9.6.1.2.1).

    Por ocasião da aplicação da força Pi (PDF p. 67):
        a) armadura pré-tracionada:           σpi = 0,77·fptk
        b) armadura pós-tracionada aderente:  σpi = 0,74·fptk
        c) armadura pós-tracionada não aderente: σpi = 0,80·fptk
        d) barras de aço CP-85/105:           σpi = 0,72·fptk
    Valores válidos para aços que atendam às ABNT NBR 7482 e ABNT NBR 7483.

    sistema: 'pre_tracionada', 'pos_tracionada_aderente' ou
    'pos_tracionada_nao_aderente' (aceita 'pre', 'pos_aderente',
    'pos_nao_aderente'). aco: 'fio_cordoalha' (padrão) ou 'barra' — com
    'barra' vale a alínea d), qualquer que seja o sistema. fptk em MPa.

    O texto de 2026 dá o limite só em função de fptk; não há mais a condição
    em fpyk da edição anterior.
    """
    fptk = _positivo_p30(fptk_mpa, "fptk")
    chave = "barra_cp85_105" if _aco_p30(aco) == "barra_cp85_105" else _sistema_p30(sistema)
    return TABELA_9_6_1_2_1_SIGMA_PI[chave] * fptk


@dataclass(frozen=True)
class ResultadoTensaoProtensao:
    """Verificação de tensão na armadura ativa (9.6.1.2)."""
    sigma_mpa: float
    limite_mpa: float
    fracao_fptk: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_sigma_pi(sigma_pi_mpa: float, fptk_mpa: float, sistema: str,
                       aco: str = "fio_cordoalha") -> ResultadoTensaoProtensao:
    """Verifica σpi na saída do aparelho de tração contra 9.6.1.2.1 (PDF p. 67).

    σpi <= limite de sigma_pi_limite_mpa (0,77, 0,74, 0,80 ou 0,72·fptk).
    Tensões em MPa. A comparação usa seguranca_nbr6118.verificar_seguranca
    (igualdade passa).
    """
    sigma = float(sigma_pi_mpa)
    lim = sigma_pi_limite_mpa(fptk_mpa, sistema, aco)
    fptk = float(fptk_mpa)
    chave = "barra_cp85_105" if _aco_p30(aco) == "barra_cp85_105" else _sistema_p30(sistema)
    frac = TABELA_9_6_1_2_1_SIGMA_PI[chave]
    alinea = _ALINEA_9_6_1_2_1[chave]
    r = _seg_p30.verificar_seguranca(lim, sigma, rotulo="σpi x limite", item="9.6.1.2.1")
    governante = ("σpi dentro do limite" if r.ok
                  else f"σpi acima do limite da alínea {alinea})")
    memoria = (
        f"9.6.1.2.1-{alinea}) (p. 67): limite σpi = {_fmt_p30(frac)}·fptk = "
        f"{_fmt_p30(frac)}·{_fmt_p30(fptk)} = {_fmt_p30(lim)} MPa.",
        f"σpi = {_fmt_p30(sigma)} MPa {'<=' if r.ok else '>'} {_fmt_p30(lim)} MPa -> "
        f"{'ok' if r.ok else 'não ok'}.",
    )
    return ResultadoTensaoProtensao(sigma, lim, frac, r.ok, governante, memoria)


def verificar_sigma_p0(sigma_p0_mpa: float, fptk_mpa: float) -> ResultadoTensaoProtensao:
    """Verifica σp0(x) ao término da operação de protensão (9.6.1.2.2, PDF p. 67).

    "A tensão σp0(x) da armadura pré-tracionada ou pós-tracionada, decorrente
    da força P0(x), não pode superar os limites estabelecidos em
    9.6.1.2.1-b)": σp0(x) <= 0,74·fptk, qualquer que seja o sistema.
    Tensões em MPa.
    """
    sigma = float(sigma_p0_mpa)
    fptk = _positivo_p30(fptk_mpa, "fptk")
    frac = TABELA_9_6_1_2_1_SIGMA_PI["pos_tracionada_aderente"]
    lim = frac * fptk
    r = _seg_p30.verificar_seguranca(lim, sigma, rotulo="σp0 x limite", item="9.6.1.2.2")
    governante = "σp0 dentro do limite" if r.ok else "σp0 acima de 0,74·fptk"
    memoria = (
        f"9.6.1.2.2 (p. 67): σp0(x) <= limite de 9.6.1.2.1-b) = 0,74·fptk = "
        f"0,74·{_fmt_p30(fptk)} = {_fmt_p30(lim)} MPa.",
        f"σp0 = {_fmt_p30(sigma)} MPa {'<=' if r.ok else '>'} {_fmt_p30(lim)} MPa -> "
        f"{'ok' if r.ok else 'não ok'}.",
    )
    return ResultadoTensaoProtensao(sigma, lim, frac, r.ok, governante, memoria)


@dataclass(frozen=True)
class ResultadoToleranciaExecucao:
    """Verificação da tolerância de execução (9.6.1.2.3)."""
    n_cabos: int
    n_cabos_majorados: int
    n_max_majorados: float
    limite_base_mpa: float
    limite_majorado_mpa: float
    sigma_max_mpa: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def tolerancia_execucao(sigmas_pi_mpa: _Iterable_p30[float],
                        fptk_mpa: float) -> ResultadoToleranciaExecucao:
    """Tolerância de execução na pós-tração: majoração de σpi (9.6.1.2.3, PDF p. 67).

    Constatadas irregularidades na protensão decorrentes de falhas
    executivas em elementos com armadura pós-tracionada, a força em
    qualquer cabo pode ser elevada, limitando σpi aos valores de
    9.6.1.2.1-b) majorados em até 10 %, até o limite de 50 % dos cabos:
        σpi <= 1,10·0,74·fptk = 0,814·fptk   em cada cabo;
        nº de cabos com σpi > 0,74·fptk <= 0,50·n.
    O texto remete à alínea b) também na pós-tração não aderente; a função
    segue o texto. A condição "desde que seja garantida a segurança da
    estrutura, principalmente nas regiões das ancoragens" não é verificada
    aqui e fica registrada na memória.

    sigmas_pi_mpa: σpi de cada cabo do elemento, MPa. fptk em MPa.
    """
    sigmas = [float(s) for s in sigmas_pi_mpa]
    if not sigmas:
        raise ValueError("Informe o σpi de pelo menos um cabo.")
    fptk = _positivo_p30(fptk_mpa, "fptk")
    base = TABELA_9_6_1_2_1_SIGMA_PI["pos_tracionada_aderente"] * fptk
    majorado = MAJORACAO_TOLERANCIA_EXECUCAO * base
    tol = 1e-9 * max(1.0, abs(base))
    n = len(sigmas)
    n_acima = sum(1 for s in sigmas if s > base + tol)
    n_max = FRACAO_MAX_CABOS_TOLERANCIA * n
    s_max = max(sigmas)
    ok_tensao = s_max <= majorado + tol
    ok_cabos = n_acima <= n_max + 1e-9
    ok = ok_tensao and ok_cabos
    if not ok_tensao:
        governante = "σpi acima de 1,10 vez o limite de 9.6.1.2.1-b)"
    elif not ok_cabos:
        governante = "mais de 50 % dos cabos com σpi majorado"
    else:
        governante = "dentro da tolerância de execução"
    memoria = (
        f"9.6.1.2.3 (p. 67): limite base 9.6.1.2.1-b) = 0,74·{_fmt_p30(fptk)} = "
        f"{_fmt_p30(base)} MPa; majorado = 1,10·{_fmt_p30(base)} = {_fmt_p30(majorado)} MPa.",
        f"σpi,máx = {_fmt_p30(s_max)} MPa {'<=' if ok_tensao else '>'} "
        f"{_fmt_p30(majorado)} MPa.",
        f"Cabos com σpi acima do limite base: {n_acima} de {n}; máximo 0,50·{n} = "
        f"{_fmt_p30(n_max)} -> {'ok' if ok_cabos else 'não ok'}.",
        "Condição da norma não verificada aqui: garantir a segurança da estrutura, "
        "principalmente nas regiões das ancoragens.",
    )
    return ResultadoToleranciaExecucao(n, n_acima, n_max, base, majorado, s_max,
                                       ok, governante, memoria)


def _soma_perdas_p30(perdas, nome: str) -> float:
    if isinstance(perdas, (int, float)):
        valores = [float(perdas)]
    else:
        valores = [float(p) for p in perdas]
    for v in valores:
        if v < 0.0:
            raise nbr.FaixaNormativaError(
                f"{nome}: perda negativa ({v:g} kN); as perdas entram em módulo.")
    return sum(valores)


def forca_media_kn(Pi_kn: float, perdas_imediatas_kn=0.0,
                   perdas_progressivas_kn=0.0) -> float:
    """Força média na armadura de protensão Pt(x), kN (9.6.1.1, PDF p. 67).

        Pt(x) = P0(x) − ΔPt(x) = Pi − ΔP0(x) − ΔPt(x)
        P0(x) = Pi − ΔP0(x)

    Pi é a força na saída do aparelho de tração; perdas_imediatas_kn é ΔP0(x)
    (atrito, acomodação da ancoragem, encurtamento imediato) e
    perdas_progressivas_kn é ΔPt(x) (retração, fluência e relaxação), na
    mesma abscissa x. Cada perda pode ser um número ou uma sequência de
    parcelas, que são somadas; todas em kN e em módulo (>= 0). Com
    perdas_progressivas_kn = 0 a função devolve P0(x). Pt(x) <= 0 levanta
    FaixaNormativaError (perdas maiores que a força aplicada).
    """
    Pi = _positivo_p30(Pi_kn, "Pi")
    dP0 = _soma_perdas_p30(perdas_imediatas_kn, "ΔP0(x)")
    dPt = _soma_perdas_p30(perdas_progressivas_kn, "ΔPt(x)")
    Pt = Pi - dP0 - dPt
    if not Pt > 0.0:
        raise nbr.FaixaNormativaError(
            f"Pt(x) = {Pi:g} − {dP0:g} − {dPt:g} = {Pt:g} kN: as perdas não podem "
            "igualar ou superar a força Pi.")
    return Pt


@dataclass(frozen=True)
class ForcaCaracteristicaProtensao:
    """Valores característicos da força de protensão (9.6.1.3)."""
    Pt_kn: float
    Pk_sup_kn: float
    Pk_inf_kn: float
    perda_max_kn: float
    limite_perda_kn: float
    usa_sup_inf: bool
    governante: str
    memoria: tuple[str, ...]


def Pk_sup_inf_kn(Pt_kn: float, perda_max_kn: float, Pi_kn: float,
                  obra_especial: bool = False) -> ForcaCaracteristicaProtensao:
    """Valores característicos Pk,t(x) superior e inferior (9.6.1.3, PDF p. 68).

    Para as obras em geral, Pk,t(x) = Pt(x) (valor médio), exceto quando a
    perda máxima [ΔP0(x) + ΔPt(x)]máx > 0,35·Pi. Nesse caso, e nas obras
    especiais projetadas por normas específicas que considerem os valores
    superior e inferior (obra_especial=True):
        [Pk,t(x)]sup = 1,05·Pt(x)
        [Pk,t(x)]inf = 0,95·Pt(x)
    Perda exatamente igual a 0,35·Pi não é "maior que": fica o valor médio.
    Forças em kN.
    """
    Pt = _positivo_p30(Pt_kn, "Pt(x)")
    Pi = _positivo_p30(Pi_kn, "Pi")
    perda = float(perda_max_kn)
    if perda < 0.0:
        raise nbr.FaixaNormativaError(f"Perda máxima = {perda:g} kN: tem de ser >= 0.")
    limite = LIMITE_PERDA_PK_SOBRE_PI * Pi
    acima = perda > limite * (1.0 + 1e-12)
    usa = acima or bool(obra_especial)
    if usa:
        sup, inf = FATOR_PK_SUP * Pt, FATOR_PK_INF * Pt
        governante = ("perda máxima > 0,35·Pi" if acima else "obra especial")
    else:
        sup = inf = Pt
        governante = "valor médio (perda máxima <= 0,35·Pi)"
    memoria = (
        f"9.6.1.3 (p. 68): [ΔP0 + ΔPt]máx = {_fmt_p30(perda)} kN; 0,35·Pi = "
        f"0,35·{_fmt_p30(Pi)} = {_fmt_p30(limite)} kN.",
        (f"[Pk,t]sup = 1,05·{_fmt_p30(Pt)} = {_fmt_p30(sup)} kN; "
         f"[Pk,t]inf = 0,95·{_fmt_p30(Pt)} = {_fmt_p30(inf)} kN ({governante})." if usa else
         f"Pk,t(x) = Pt(x) = {_fmt_p30(Pt)} kN ({governante})."),
    )
    return ForcaCaracteristicaProtensao(Pt, sup, inf, perda, limite, usa, governante, memoria)


def Pd_kn(Pt_kn: float, gama_p: float | None = None, combinacao: str = "normal",
          favoravel: bool = False) -> float:
    """Valor de cálculo da força de protensão Pd,t(x) = γp·Pt(x), kN (9.6.1.4, PDF p. 68).

    γp é o da Seção 11 (Tabela 11.1, coluna p): sem gama_p explícito, é lido
    de acoes_nbr6118.gama_f_tabela_11_1(combinacao, 'protensao', 'D' ou 'F')
    — 1,2 desfavorável e 0,9 favorável nas três combinações. Situações com γp
    próprio (ato da protensão, 17.2.4.3.1; M0, 17.4.2.2) passam o valor em
    gama_p. Força em kN.
    """
    Pt = _positivo_p30(Pt_kn, "Pt(x)")
    if gama_p is None:
        g = _acoes_p30.gama_f_tabela_11_1(combinacao, "protensao", "F" if favoravel else "D")
    else:
        g = _positivo_p30(gama_p, "γp")
    return g * Pt


# 9.6.3.3.2.2 (PDF p. 71) — coeficiente de atrito aparente μ (1/rad) e
# coeficiente k de perda por metro (1/m), na falta de dados experimentais:
# k = 0,065·μ para a bainha de polipropileno lubrificada e 0,01·μ nos outros casos.
TABELA_MU_K = {
    # contato: (μ, fator de k em k = fator·μ)
    "cabo_concreto_sem_bainha": (0.50, 0.01),
    "barra_ou_fio_com_mossas_bainha_metalica": (0.30, 0.01),
    "fio_liso_ou_cordoalha_bainha_metalica": (0.20, 0.01),
    "fio_liso_ou_cordoalha_bainha_metalica_lubrificada": (0.10, 0.01),
    "cordoalha_bainha_polipropileno_lubrificada": (0.07, 0.065),
}


def coeficientes_atrito(contato: str) -> tuple[float, float]:
    """(μ em 1/rad, k em 1/m) para a perda por atrito (9.6.3.3.2.2, PDF p. 71).

    Na falta de dados experimentais:
        μ = 0,50 entre cabo e concreto (sem bainha);
        μ = 0,30 entre barras ou fios com mossas ou saliências e bainha metálica;
        μ = 0,20 entre fios lisos ou cordoalhas e bainha metálica;
        μ = 0,10 entre fios lisos ou cordoalhas e bainha metálica lubrificada;
        μ = 0,07 entre a cordoalha e a bainha de polipropileno lubrificada;
        k = 0,065·μ (1/m) para a bainha de polipropileno lubrificada e
        k = 0,01·μ (1/m) para os outros casos.
    contato: uma das chaves de TABELA_MU_K. Os valores alimentam
    perda_atrito_kn(Pi, mu, theta, k, x).
    """
    k = _chave_p30(contato)
    if k not in TABELA_MU_K:
        raise ValueError(
            f"Contato desconhecido: {contato!r}. Opções: {', '.join(TABELA_MU_K)}.")
    mu, fator = TABELA_MU_K[k]
    return mu, fator * mu


def alpha_p_t(fck_mpa: float, t0_dias: float | None = None, cimento: str = "CPII",
              agregado: str = "granito", Ep_mpa: float = E_P_MPA,
              Eci_t0_mpa: float | None = None) -> float:
    """Razão αp(t) = Ep/Eci(t) na idade t0 do concreto (9.6.3.4.2, PDF p. 72).

    Eci(t) pela estimativa de 8.2.8 (nucleo.Eci_idade), com fckj = β1·fck
    (nucleo.fckj, pelo cimento). Sem t0 (None) ou com t0 >= 28 dias devolve
    αp = Ep/Eci. A estimativa vale de 7 a 28 dias: abaixo de 7 dias informe
    Eci_t0_mpa (de ensaio), que substitui a estimativa em qualquer idade.
    """
    if Eci_t0_mpa is not None:
        return Ep_mpa / _positivo_p30(Eci_t0_mpa, "Eci(t0)")
    alpha_e = nbr.alpha_E(agregado)
    if t0_dias is None or float(t0_dias) >= 28.0:
        return Ep_mpa / nbr.Eci(fck_mpa, alpha_e)
    if float(t0_dias) >= 7.0:
        fckj_t0 = nbr.fckj(fck_mpa, t0_dias, cimento)
        return Ep_mpa / nbr.Eci_idade(fck_mpa, fckj_t0, alpha_e)
    raise nbr.FaixaNormativaError(
        f"t0 = {float(t0_dias):g} dias: a estimativa de Eci(t) de 8.2.8 vale de 7 a 28 "
        "dias. Informe Eci_t0_mpa (módulo de elasticidade medido na idade t0).")


@dataclass(frozen=True)
class DeformacoesAcoConcreto:
    """Variações de deformação do aço e do concreto entre t0 e t (9.6.3.4.2)."""
    deps_pt_pmil: float
    deps_ct_pmil: float
    chi: float
    chi_p: float
    chi_c: float
    memoria: tuple[str, ...]


def deformacoes_aco_concreto(
    sigma_p0_mpa: float, delta_sigma_p_mpa: float,
    sigma_c_p0g_mpa: float, delta_sigma_c_mpa: float,
    phi: float, psi_percent: float, eps_cs_permil: float,
    fck_mpa: float, agregado: str = "granito", Ep_mpa: float = E_P_MPA,
    Eci_28_mpa: float | None = None,
) -> DeformacoesAcoConcreto:
    """Δεpt(t,t0) e Δεct(t,t0) do processo simplificado (9.6.3.4.2, PDF p. 72).

        Δεpt(t,t0) = σp0/Ep·χ(t,t0) − Δσp(t,t0)/Ep·χp
        Δεct(t,t0) = σc,p0g/Eci·φ(t,t0) − Δσc(t,t0)/Eci·χc + |εcs(t,t0)|
    com χ(t,t0) = −ln[1 − ψ(t,t0)], χc = 1 + 0,5·φ(t,t0), χp = 1 + χ(t,t0).

    Tensões em MPa (σp0 e Δσp positivas; σc,p0g positiva se compressão;
    Δσc é a variação da tensão do concreto adjacente ao cabo entre t0 e t);
    ψ em %; εcs em ‰ (entra em módulo). Eci é o de 28 dias (nucleo.Eci,
    com o agregado) ou Eci_28_mpa, se informado. Devolve Δεpt e Δεct em ‰.

    Conferência (dedução, não texto da norma): com Δσp da fórmula de
    9.6.3.4.2 e Δσc = η·ρp·Δσp, tem-se Δεpt + Δεct = 0 quando αp(t) = αp.
    """
    psi = float(psi_percent)
    if not 0.0 <= psi < 100.0:
        raise nbr.FaixaNormativaError(f"ψ = {psi:g} %: tem de estar em [0, 100).")
    if float(phi) < 0.0:
        raise nbr.FaixaNormativaError(f"φ = {float(phi):g}: tem de ser >= 0.")
    Eci = (_positivo_p30(Eci_28_mpa, "Eci") if Eci_28_mpa is not None
           else nbr.Eci(fck_mpa, nbr.alpha_E(agregado)))
    chi = -math.log(1.0 - psi / 100.0)
    chi_c = 1.0 + 0.5 * phi
    chi_p = 1.0 + chi
    deps_pt = (sigma_p0_mpa / Ep_mpa * chi - delta_sigma_p_mpa / Ep_mpa * chi_p) * 1000.0
    deps_ct = (sigma_c_p0g_mpa / Eci * phi - delta_sigma_c_mpa / Eci * chi_c) * 1000.0 \
        + abs(eps_cs_permil)
    memoria = (
        f"9.6.3.4.2 (p. 72): χ = −ln(1 − {_fmt_p30(psi / 100.0)}) = {_fmt_p30(chi)}; "
        f"χp = {_fmt_p30(chi_p)}; χc = 1 + 0,5·{_fmt_p30(phi)} = {_fmt_p30(chi_c)}.",
        f"Δεpt = {_fmt_p30(sigma_p0_mpa)}/{_fmt_p30(Ep_mpa)}·{_fmt_p30(chi)} − "
        f"{_fmt_p30(delta_sigma_p_mpa)}/{_fmt_p30(Ep_mpa)}·{_fmt_p30(chi_p)} = "
        f"{_fmt_p30(deps_pt)} ‰.",
        f"Δεct = {_fmt_p30(sigma_c_p0g_mpa)}/{_fmt_p30(Eci)}·{_fmt_p30(phi)} − "
        f"{_fmt_p30(delta_sigma_c_mpa)}/{_fmt_p30(Eci)}·{_fmt_p30(chi_c)} + "
        f"{_fmt_p30(abs(eps_cs_permil))} ‰ = {_fmt_p30(deps_ct)} ‰.",
    )
    return DeformacoesAcoConcreto(deps_pt, deps_ct, chi, chi_p, chi_c, memoria)


# 9.6.3.4.3 (PDF p. 73) — processo aproximado: coeficientes (a, b, c) de
# Δσp/σp0 [%] = a + (αp/b)·[φ(t∞,t0)]^c·(3 + σc,p0g).
TABELA_9_6_3_4_3_APROXIMADO = {
    "RN": (18.1, 47.0, 1.57),
    "RB": (7.4, 18.7, 1.07),
}
TOLERANCIA_RETRACAO_APROXIMADO = 0.25   # "não difira em mais de 25 %"
COEF_RETRACAO_APROXIMADO = -8.0e-5      # εcs de referência = −8·10^−5·φ(∞,t0)


def perda_progressiva_aproximada_pct(
    aco: str, phi_inf: float, sigma_c_p0g_mpa: float, eps_cs_permil: float,
    fck_mpa: float, agregado: str = "granito", Ep_mpa: float = E_P_MPA,
) -> float:
    """Perda progressiva pelo processo aproximado, Δσp(t∞,t0)/σp0 em % (9.6.3.4.3, PDF p. 73).

        a) aço RN: Δσp/σp0 = 18,1 + (αp/47)·[φ(t∞,t0)]^1,57·(3 + σc,p0g)
        b) aço RB: Δσp/σp0 = 7,4 + (αp/18,7)·[φ(t∞,t0)]^1,07·(3 + σc,p0g)
    com σc,p0g em MPa, positiva se compressão, e αp = Ep/Eci (Eci de 28 dias,
    pelo fck e o agregado). Perda por fluência, retração e relaxação juntas.

    Condição de aplicação: as mesmas de 9.6.3.4.2 (fases únicas de operação,
    cabo resultante — não verificadas aqui) e a retração não pode diferir em
    mais de 25 % do valor −8·10^−5·φ(∞,t0). eps_cs_permil é a retração em ‰
    (comparada em módulo com 0,08·φ ‰); fora da condição levanta
    FaixaNormativaError. Diferença de exatamente 25 % é aceita.
    aco: 'RN' ou 'RB'. Devolve a perda em % de σp0.
    """
    chave = str(aco).strip().upper()
    if chave not in TABELA_9_6_3_4_3_APROXIMADO:
        raise ValueError(f"Aço {aco!r} desconhecido: use 'RN' ou 'RB'.")
    phi = float(phi_inf)
    if phi < 0.0:
        raise nbr.FaixaNormativaError(f"φ(t∞,t0) = {phi:g}: tem de ser >= 0.")
    ref_pmil = abs(COEF_RETRACAO_APROXIMADO) * phi * 1000.0
    eps = abs(float(eps_cs_permil))
    if abs(eps - ref_pmil) > TOLERANCIA_RETRACAO_APROXIMADO * ref_pmil * (1.0 + 1e-9) + 1e-15:
        raise nbr.FaixaNormativaError(
            f"Processo aproximado (9.6.3.4.3) não se aplica: |εcs| = {eps:g} ‰ difere em "
            f"mais de 25 % de 8·10^−5·φ(∞,t0) = {ref_pmil:g} ‰. Use o processo "
            "simplificado de 9.6.3.4.2 (perda_progressiva_simplificada).")
    a, b, c = TABELA_9_6_3_4_3_APROXIMADO[chave]
    alpha_p = Ep_mpa / nbr.Eci(fck_mpa, nbr.alpha_E(agregado))
    return a + alpha_p / b * phi ** c * (3.0 + float(sigma_c_p0g_mpa))


# === P47: Esforços hiperestáticos de protensão (11.3.3.5 e 17.2.4.2.1, p. 81 e 143) ===
# "A ação da protensão deve ser considerada em todas as estruturas protendidas,
# incluindo... esforços hiperestáticos de protensão... Os esforços solicitantes
# gerados por essa protensão podem ser calculados diretamente a partir da
# excentricidade do cabo... e da força de protensão ou através de um conjunto
# de cargas externas equivalentes" (11.3.3.5, PDF p. 81). No ELU, "devem ser
# considerados... apenas os esforços solicitantes hiperestáticos de protensão.
# Os isostáticos de protensão não podem ser incluídos" (17.2.4.2.1, PDF p. 143).
import numpy as np

try:  # executado como script, ou com dimensionamento/ no sys.path
    import analise_barras_nbr6118 as _ab_p47
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import analise_barras_nbr6118 as _ab_p47


@dataclass(frozen=True)
class TrechoCabo:
    """Um trecho do cabo de protensão sobre uma barra do modelo de análise
    (P44), do nó i ao nó j dela (11.3.3.5, PDF p. 81).

    barra: id da barra do modelo (``analise_barras_nbr6118.Modelo``) em que
    este trecho do cabo está lançado; o cabo percorre a barra inteira,
    do nó i ao nó j. L_cm: comprimento do trecho (o da barra).
    e_i_cm, e_j_cm: excentricidade do cabo nos nós i e j, cm, no eixo
    transversal do pórtico plano (local y, a mesma convenção de sinal de Mz:
    e(x) entra em M1 = P·e diretamente, sem troca de sinal — ver
    ``momento_isostatico_cabo_kncm``). flecha_cm: desvio do cabo em relação à
    corda que liga e_i a e_j, na seção média do trecho, na mesma convenção.
    Perfil parabólico do 2º grau entre e_i, a flecha no meio e e_j (a mesma
    forma que 9.6.3.3.2.2, PDF p. 71, admite para o ângulo de desvio do
    cabo).
    """

    barra: object
    L_cm: float
    e_i_cm: float
    e_j_cm: float
    flecha_cm: float = 0.0

    def __post_init__(self):
        if self.L_cm <= 0.0:
            raise nbr.FaixaNormativaError(f"L = {_fmt_p30(self.L_cm)} cm: tem de ser positivo.")

    def excentricidade_cm(self, x_cm: float) -> float:
        """e(x), cm, a x_cm do nó i (0 <= x_cm <= L_cm), pela parábola do trecho."""
        x = float(x_cm)
        if not (-1e-9 <= x <= self.L_cm + 1e-9):
            raise ValueError(
                f"x = {_fmt_p30(x)} cm fora do trecho (0 a {_fmt_p30(self.L_cm)} cm).")
        u = min(max(x / self.L_cm, 0.0), 1.0)
        return self.e_i_cm * (1.0 - u) + self.e_j_cm * u + 4.0 * self.flecha_cm * u * (1.0 - u)


@dataclass(frozen=True)
class PerfilCabo:
    """Perfil do cabo de protensão ao longo de uma sequência de barras do
    modelo de análise, do início ao fim do cabo (11.3.3.5, PDF p. 81).

    trechos: tupla de ``TrechoCabo``, na ordem do percurso do cabo, de uma
    ancoragem (ou ponta) à outra. Quando dois trechos vizinhos compartilham o
    nó (barras emendadas em sequência) e têm a mesma excentricidade e a mesma
    inclinação nesse nó, o traçado é contínuo e as parcelas concentradas se
    cancelam; quando a excentricidade ou a inclinação mudam de um trecho para
    o outro, ``cargas_equivalentes_cabo`` já representa a força concentrada
    correspondente à mudança de traçado, sem precisar de um marcador à parte.
    """

    trechos: tuple

    def __post_init__(self):
        if not self.trechos:
            raise ValueError("PerfilCabo precisa de pelo menos um trecho.")


def _forcas_por_trecho_p47(n: int, P_kn) -> tuple:
    """P_kn normalizado para uma tupla de n forças positivas, kN."""
    if isinstance(P_kn, (int, float)):
        Ps = tuple(float(P_kn) for _ in range(n))
    else:
        Ps = tuple(float(p) for p in P_kn)
        if len(Ps) != n:
            raise ValueError(f"P: {len(Ps)} valor(es) para {n} trecho(s) do perfil do cabo.")
    for p in Ps:
        _positivo_p30(p, "P")
    return Ps


def cargas_equivalentes_cabo(perfil: PerfilCabo, P_kn) -> "_ab_p47.CasoCarga":
    """Cargas equivalentes do cabo de protensão sobre o concreto (11.3.3.5, PDF p. 81).

    Substitui o cabo, trecho a trecho (``TrechoCabo``, parábola do 2º grau),
    por três parcelas estaticamente equivalentes sobre a barra do modelo de
    análise (P44), em eixos locais:

        - força axial P nas duas extremidades do trecho (comprime o
          concreto; num nó compartilhado por dois trechos colineares com o
          mesmo P, as duas parcelas se cancelam e só sobra a força líquida
          nas ancoragens, nas pontas do cabo);
        - momento concentrado P·e em cada extremidade, pela excentricidade
          ali — a ancoragem (ponta do cabo) ou uma mudança de traçado entre
          trechos vizinhos com excentricidades diferentes no mesmo nó;
        - carga distribuída w = −8·P·flecha/L² ao longo do trecho, pela
          curvatura da parábola.

    Dedução (conferida no teste da viga biapoiada): para uma barra isostática
    (biapoiada), o momento fletor sob essas três parcelas reproduz, em cada
    ponto, exatamente M1(x) = P·e(x) — o momento isostático de protensão
    (``momento_isostatico_cabo_kncm``). É esse fato, e não um valor tabelado
    pela norma, que confere as parcelas e os sinais adotados aqui.

    P_kn: força de protensão, kN, positiva — um número (constante ao longo
    do cabo) ou uma sequência com um valor por trecho de ``perfil.trechos``
    (o P30, ``forca_media_kn``/``Pk_sup_inf_kn``/``Pd_kn``, entrega Pt(x),
    que varia ao longo do cabo pelas perdas). Devolve um
    ``analise_barras_nbr6118.CasoCarga``, pronto para ``resolver`` (P44).

    Só para modelo de pórtico plano (vigas contínuas e pórticos planos, o
    objetivo do pacote); o eixo transversal usado é o y local, o de Mz.
    """
    Ps = _forcas_por_trecho_p47(len(perfil.trechos), P_kn)
    caso = _ab_p47.CasoCarga("Cabo de protensão (11.3.3.5)")
    for trecho, P in zip(perfil.trechos, Ps):
        L = trecho.L_cm
        caso.concentrada(trecho.barra, 0.0, P, direcao="x")
        caso.concentrada(trecho.barra, L, -P, direcao="x")
        if trecho.e_i_cm != 0.0:
            caso.momento_concentrado(trecho.barra, 0.0, -P * trecho.e_i_cm, eixo="z")
        if trecho.e_j_cm != 0.0:
            caso.momento_concentrado(trecho.barra, L, P * trecho.e_j_cm, eixo="z")
        if trecho.flecha_cm != 0.0:
            w_kn_m = -8.0 * P * trecho.flecha_cm / (L * L) * 100.0
            caso.distribuida(trecho.barra, w_kn_m, direcao="y")
    return caso


def momento_isostatico_cabo_kncm(trecho: TrechoCabo, P_kn: float, x_cm: float) -> float:
    """Momento isostático de protensão M1(x) = P·e(x), kN·cm (11.3.3.5, PDF p. 81).

    O momento que a força P produziria pela excentricidade sozinha, sem os
    efeitos de continuidade da estrutura — o que 17.2.4.2.1 (PDF p. 143)
    proíbe considerar no ELU ("os isostáticos de protensão não podem ser
    incluídos"). x_cm a partir do nó i do trecho.
    """
    _positivo_p30(P_kn, "P")
    return float(P_kn) * trecho.excentricidade_cm(x_cm)


@dataclass(frozen=True)
class Cabo:
    """Cabo de protensão para ``esforcos_hiperestaticos_protensao``: o
    perfil (``PerfilCabo``) e a força P ao longo dele, kN (do P30 —
    ``forca_media_kn``, ``Pk_sup_inf_kn`` ou ``Pd_kn``), um número (constante)
    ou uma sequência com um valor por trecho do perfil."""

    perfil: PerfilCabo
    P_kn: object


@dataclass(frozen=True)
class EsforcosCaboBarra:
    """Esforços de protensão de uma barra com trecho de cabo (11.3.3.5, PDF p. 81).

    x_cm: estações ao longo da barra (as de ``ResultadoBarra.x_cm``).
    M_total_kncm: momento fletor total sob as cargas equivalentes do cabo (o
    que a estrutura real, com a sua continuidade, sente).
    M_isostatico_kncm: P·e(x) local (``momento_isostatico_cabo_kncm``).
    M_hiperestatico_kncm: total − isostático (11.3.3.5). N_kn: força normal
    total sob as cargas equivalentes (inclui a parcela axial do cabo).
    """

    x_cm: object
    M_total_kncm: object
    M_isostatico_kncm: object
    M_hiperestatico_kncm: object
    N_kn: object


@dataclass(frozen=True)
class ResultadoHiperestaticoProtensao:
    """Resultado de ``esforcos_hiperestaticos_protensao`` (11.3.3.5, PDF p. 81).

    barras: {id da barra: ``EsforcosCaboBarra``}, só as barras com trecho de
    cabo. resultado_analise: o ``ResultadoAnalise`` bruto da resolução (P44),
    com reações, deslocamentos e o equilíbrio já conferido (ver
    ``ResultadoAnalise.equilibrio_ok``). memoria: linhas da memória de
    cálculo.
    """

    barras: dict
    resultado_analise: object
    memoria: tuple


def esforcos_hiperestaticos_protensao(modelo, cabo: Cabo, n_estacoes: int = 11) -> ResultadoHiperestaticoProtensao:
    """Esforços hiperestáticos de protensão em viga contínua ou pórtico (11.3.3.5, PDF p. 81).

    Resolve as cargas equivalentes do cabo (``cargas_equivalentes_cabo``) no
    modelo de análise de barras (P44, ``analise_barras_nbr6118.resolver``) e,
    em cada barra com trecho de cabo, separa o momento fletor total (o da
    estrutura real) do isostático (P·e local,
    ``momento_isostatico_cabo_kncm``) e do hiperestático (a diferença):

        M_hiperestático(x) = M_total(x) − P·e(x)

    Numa estrutura isostática (viga biapoiada), M_total(x) = P·e(x) em todo
    ponto e o hiperestático é identicamente zero — a análise reproduz a
    demonstração do método das cargas equivalentes (ver
    ``cargas_equivalentes_cabo``). Numa estrutura hiperestática (viga
    contínua, pórtico), M_hiperestático(x) é, em geral, diferente de zero e
    varia linearmente entre apoios (por ser gerado só por reações de apoio,
    sem carga aplicada entre eles).

    Só cobre modelo de pórtico plano (``modelo.tipo == 'portico_plano'``):
    vigas contínuas e pórticos planos, como o objetivo do pacote pede; grelha
    e pórtico espacial ficam para quando o P45/P48 precisarem (o eixo
    transversal usado aqui é sempre o y local, o de Mz).
    """
    if modelo.tipo != "portico_plano":
        raise ValueError(
            "esforcos_hiperestaticos_protensao só cobre pórtico plano (vigas contínuas e "
            f"pórticos planos); modelo.tipo = {modelo.tipo!r}.")
    Ps = _forcas_por_trecho_p47(len(cabo.perfil.trechos), cabo.P_kn)
    caso = cargas_equivalentes_cabo(cabo.perfil, Ps)
    resultado = _ab_p47.resolver(modelo, caso, n_estacoes=n_estacoes)

    por_barra: dict = {}
    for trecho, P in zip(cabo.perfil.trechos, Ps):
        por_barra.setdefault(trecho.barra, []).append((trecho, P))

    barras = {}
    for bid, trechos_p in por_barra.items():
        rb = resultado.barras[bid]
        x = rb.x_cm
        m_iso = np.zeros_like(x)
        for trecho, P in trechos_p:
            m_iso = m_iso + np.array([momento_isostatico_cabo_kncm(trecho, P, xx) for xx in x])
        m_total = rb.esforcos["Mz"].copy()
        n_total = rb.esforcos["N"].copy()
        # As cargas do cabo (força axial e momento) entram nas duas pontas exatas da
        # barra (x = 0 e x = L). O extremo da barra não tem "lado direito" (nada além
        # dele), então a consulta pontual de analise_barras_nbr6118 (.em/esforcos, que
        # soma só o que está estritamente à direita da seção) não enxerga, exatamente
        # nesses dois pontos, a própria carga aplicada ali — o mesmo valor logo antes
        # (dentro da barra) já reflete corretamente essa carga. Corrige-se aqui, sem
        # mexer em analise_barras_nbr6118.py, substituindo as duas estações extremas
        # pelo valor a um deslocamento desprezível para dentro da barra.
        Lf = rb.L_flexivel_cm
        if x.size and Lf > 0.0:
            eps = max(Lf * 1e-9, 1e-9)
            if abs(x[0] - 0.0) <= 1e-9:
                v = rb.em(min(eps, Lf))
                m_total[0], n_total[0] = v["Mz"], v["N"]
            if abs(x[-1] - Lf) <= 1e-9:
                v = rb.em(max(Lf - eps, 0.0))
                m_total[-1], n_total[-1] = v["Mz"], v["N"]
        barras[bid] = EsforcosCaboBarra(
            x_cm=x.copy(), M_total_kncm=m_total, M_isostatico_kncm=m_iso,
            M_hiperestatico_kncm=m_total - m_iso, N_kn=n_total)

    memoria = (
        "11.3.3.5 (p. 81): esforços da protensão pelas cargas equivalentes do cabo, resolvidas "
        "na estrutura real (P44); M_hiperestático = M_total − P·e (isostático).",
        f"{len(por_barra)} barra(s) com trecho de cabo.",
    ) + resultado.memoria
    return ResultadoHiperestaticoProtensao(barras=barras, resultado_analise=resultado, memoria=memoria)


def pre_alongamento_protensao_pmil(sigma_pi_mpa: float, perdas_mpa=0.0,
                                   Ep_mpa: float = E_P_MPA) -> float:
    """Pré-alongamento da armadura ativa para o ELU (17.2.4.2.1, PDF p. 143).

        εp0 = [σpi,d − Σ perdas até t] / Ep

    "A consideração das armaduras ativas nos esforços resistentes deve ser
    feita a partir dos diagramas tensão-deformação especificados em 8.4.5 e
    da consideração dos pré-alongamentos delas. Esses pré-alongamentos devem
    ser calculados com base nas tensões iniciais de protensão com valores de
    cálculo (ver 11.7.1) e com a consideração de perdas na idade t em exame
    (ver 9.6.3)." sigma_pi_mpa: σpi(d), a tensão inicial de protensão com
    valor de cálculo (11.7.1). perdas_mpa: a soma das perdas até o instante t
    (9.6.3), em módulo — um número ou uma sequência de parcelas
    (perda_relaxacao_kncm2, perda_retracao_kncm2, perda_fluencia_kncm2 ou
    perda_progressiva_simplificada/perda_progressiva_aproximada_pct, todas
    convertidas para MPa antes de somar). O resultado (‰) entra como
    deformação inicial no diagrama de 8.4.5 (P3, ``nucleo_nbr6118.sigma_p``),
    somado à deformação de flexão da seção, para achar a tensão do aço ativo
    no ELU (fora do escopo deste pacote: P28, kernel de flexão).
    """
    sigma = _positivo_p30(sigma_pi_mpa, "σpi,d")
    dsigma = _soma_perdas_p30(perdas_mpa, "perdas até t")
    eps = (sigma - dsigma) / Ep_mpa * 1000.0
    if eps <= 0.0:
        raise nbr.FaixaNormativaError(
            f"εp0 = ({_fmt_p30(sigma)} − {_fmt_p30(dsigma)})/{_fmt_p30(Ep_mpa)} = {_fmt_p30(eps)} ‰: "
            "as perdas não podem igualar ou superar σpi,d.")
    return eps


def combinar_protensao_elu(M_hiperestatico_kncm, gama_p: float | None = None,
                           combinacao: str = "normal", favoravel: bool = False,
                           M_outras_acoes_kncm=0.0):
    """Momento de cálculo no ELU com a protensão (17.2.4.2.1, PDF p. 143).

    "Na verificação do ELU devem ser considerados, além do efeito de outras
    ações, apenas os esforços solicitantes hiperestáticos de protensão. Os
    isostáticos de protensão não podem ser incluídos": só o hiperestático
    entra, com o γp da Tabela 11.1 (coluna p, P30 — ``gama_f_tabela_11_1``),
    salvo valor explícito em gama_p (por exemplo, o ato da protensão,
    17.2.4.3.1, com γp = 1,0 na pré-tração ou 1,1 na pós-tração).

        Md = M_outras_ações,d + γp·M_hiperestático

    M_outras_acoes_kncm já deve vir com os γf das outras ações aplicados
    (P4/P5); o efeito isostático da protensão nunca entra aqui — ele já está
    incluído nas tensões da seção pela força de protensão diretamente, não
    pela combinação de esforços do ELU. A armadura ativa, à parte, entra
    pelos diagramas de 8.4.5 com o pré-alongamento
    (``pre_alongamento_protensao_pmil``). Aceita número ou sequência/array
    (para combinar ao longo de uma barra) em M_hiperestatico_kncm e em
    M_outras_acoes_kncm.
    """
    if gama_p is None:
        g = _acoes_p30.gama_f_tabela_11_1(combinacao, "protensao", "F" if favoravel else "D")
    else:
        g = _positivo_p30(gama_p, "γp")
    Mh = (float(M_hiperestatico_kncm) if isinstance(M_hiperestatico_kncm, (int, float))
          else np.asarray(M_hiperestatico_kncm, dtype=float))
    Mo = (float(M_outras_acoes_kncm) if isinstance(M_outras_acoes_kncm, (int, float))
          else np.asarray(M_outras_acoes_kncm, dtype=float))
    return Mo + g * Mh


# === P43: Método geral de cálculo das perdas progressivas (9.6.3.4.4, p. 73) ===
#
# 9.6.3.4.4 (PDF p. 73) não dá fórmula fechada: quando as ações permanentes
# (carga permanente ou protensão) são aplicadas parceladamente em idades
# diferentes, considera-se a fluência de cada camada de concreto e a relaxação
# de cada cabo separadamente; a relaxação de cada cabo pode ser considerada
# isolada, independentemente das ações permanentes aplicadas depois.
#
# O procedimento daqui é uma análise da seção no tempo, passo a passo:
#   - seção plana, ε(y) = ε0 + κ·y, estádio I e aderência (9.6.3.4.1);
#   - cada camada de concreto tem a sua fluência φ(t,τ), o seu Ec(τ) e a sua
#     retração, contadas na idade dela, e trabalha solidária a partir de
#     ``t_ativacao_dias``; a tensão na camada é linear (N/A e M/I próprios);
#   - concreto (A.2.5): o acréscimo súbito de tensão na idade τ tem
#     flexibilidade 1/Ec(τ) + φ(t,τ)/Eci (superposição); o acréscimo gradual
#     de um passo (t_{i−1}, t_i] tem, no fim do passo, 1/Ec(t_{i−1}) +
#     α·φ(t_i,t_{i−1})/Eci, com o α de A.2.5, e depois dele continua a fluir
#     com φ(t,t_{i−1}) − φ(t_i,t_{i−1}) (o α só vale dentro do próprio passo,
#     de modo que, com passos curtos, o resultado tende à forma integral);
#   - cabo (9.6.3.4.2 e 9.6.3.4.5): Δεp = σp0/Ep·χ(t,tp) + Σ Δσp/Ep·[1 + χ(t,tp)
#     − χ(τ,tp)], com χ = −ln(1 − ψ) e ψ do próprio cabo, contado da sua
#     protensão tp (relaxação isolada de cada cabo);
#   - com uma fase só, um passo e α = 0,5 com Ec(t0) = Eci, as equações são
#     exatamente as de 9.6.3.4.2 (Δεpt + Δεct = 0 no cabo resultante).
try:  # executado como script, ou com dimensionamento/ no sys.path
    import tempo_concreto_nbr6118 as _tc_p43
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import tempo_concreto_nbr6118 as _tc_p43

from typing import Callable as _Callable_p43, Sequence as _Sequence_p43

ALFA_METODO_GERAL_PADRAO = 0.8   # A.2.5 (p. 240): "nos outros casos usuais, α = 0,8"
PSI_INFINITO_SOBRE_PSI_1000 = 2.5   # 9.6.3.4.5 (p. 74): ψ(t∞,t0) ≅ 2,5·ψ1000
DT_INTERIOR_INFINITO_DIAS = 1.0e5   # subpassos até t0 + 10^5 dias quando t = ∞


@dataclass(frozen=True)
class CamadaConcreto:
    """Camada de concreto do método geral (9.6.3.4.4).

    Ac_cm2, Ic_cm4: área e inércia própria (em torno do centroide da camada).
    y_cm: ordenada do centroide no eixo de referência da seção (y cresce no
        sentido em que M positivo traciona: ε(y) = ε0 + κ·y).
    t_concretagem_dias, t_ativacao_dias: instantes, no eixo de tempo comum da
        obra, da concretagem e do início do trabalho solidário da camada
        (t_ativacao >= t_concretagem).
    phi_func: (idade_t, idade_τ) → φ(t,τ) da camada, com as idades contadas
        da concretagem dela (dias); φ(t,t) não entra (a resposta no instante
        do acréscimo é só elástica, 1/Ec).
    Eci_mpa: Eci de 8.2.8 aos 28 dias da camada.
    Ec_mpa: Ec(τ) em MPa, número ou função idade → Ec; None usa Eci.
    eps_cs_func: (idade_t, idade_t0) → εcs(t,t0) em ‰ (negativa); None, sem
        retração.
    """

    Ac_cm2: float
    Ic_cm4: float
    y_cm: float
    phi_func: _Callable_p43[[float, float], float]
    Eci_mpa: float
    t_concretagem_dias: float = 0.0
    t_ativacao_dias: float = 0.0
    Ec_mpa: object = None
    eps_cs_func: _Callable_p43[[float, float], float] | None = None
    nome: str = ""


@dataclass(frozen=True)
class CaboProtensao:
    """Cabo do método geral (9.6.3.4.4), aderente a partir da protensão.

    Ap_cm2, y_cm: área e ordenada do cabo (mesmo eixo das camadas).
    t_protensao_dias: instante da protensão no eixo de tempo comum.
    sigma_p0_mpa: σp0, tensão no cabo após as perdas imediatas dele (atrito,
        acomodação), positiva; a força Ap·σp0 é aplicada à seção ativa no
        instante (sem o próprio cabo) e o cabo passa a aderir em seguida.
    psi_1000_pct: ψ1000 da Tabela 8.3 (``psi_1000``), em %; ψ(t,tp) =
        ψ1000·[(t − tp)/41,67]^0,15, limitado a 2,5·ψ1000 (9.6.3.4.5).
    psi_func: alternativa, (t − tp em dias) → ψ(t,tp) em %; substitui a regra
        acima.
    """

    Ap_cm2: float
    y_cm: float
    t_protensao_dias: float
    sigma_p0_mpa: float
    psi_1000_pct: float = 0.0
    Ep_mpa: float = E_P_MPA
    psi_func: _Callable_p43[[float], float] | None = None
    nome: str = ""


@dataclass(frozen=True)
class ArmaduraPassivaMetodoGeral:
    """Armadura passiva aderente do método geral: elástica, a partir de t_ativacao_dias."""

    As_cm2: float
    y_cm: float
    t_ativacao_dias: float = 0.0
    Es_mpa: float = E_S_MPA
    nome: str = ""


@dataclass(frozen=True)
class FaseCarga:
    """Ação externa aplicada de uma vez no instante t_dias (N em kN, M em kN·cm).

    N positivo é tração; M em torno do eixo y = 0, positivo quando traciona
    as fibras de y positivo. A protensão não entra aqui: ela vem dos cabos.
    """

    t_dias: float
    N_kn: float = 0.0
    M_kncm: float = 0.0
    descricao: str = ""


@dataclass(frozen=True)
class ResultadoPerdasMetodoGeral:
    """Resultado do método geral de perdas progressivas (9.6.3.4.4)."""

    tempos_dias: tuple[float, ...]
    sigma_p_mpa: tuple[tuple[float, ...], ...]         # [cabo][nó]; nan antes da protensão
    sigma_c_n_mpa: tuple[tuple[float, ...], ...]       # [camada][nó]: N/A da camada
    sigma_c_m_mpa_por_cm: tuple[tuple[float, ...], ...]  # [camada][nó]: M/I próprio
    eps0_pmil: tuple[float, ...]
    kappa_pmil_por_cm: tuple[float, ...]
    sigma_p_final_mpa: tuple[float, ...]
    perda_progressiva_mpa: tuple[float, ...]   # soma dos acréscimos graduais (fluência, retração, relaxação)
    variacao_imediata_mpa: tuple[float, ...]   # soma dos acréscimos súbitos depois da protensão
    perda_total_mpa: tuple[float, ...]         # σp0 − σp(t_final)
    alfa: float
    n_subpassos: int
    memoria: tuple[str, ...]

    y_camadas_cm: tuple[float, ...] = ()

    def sigma_c_mpa(self, camada: int, y_cm: float, no: int = -1) -> float:
        """Tensão no concreto da camada na ordenada y (MPa), no nó pedido (último por padrão).

            σc(y) = N/A + (M/I)·(y − y_camada)
        """
        return (self.sigma_c_n_mpa[camada][no]
                + self.sigma_c_m_mpa_por_cm[camada][no] * (float(y_cm) - self.y_camadas_cm[camada]))


def _psi_cabo_p43(cabo: CaboProtensao, dt: float) -> float:
    """ψ(t,tp) do cabo em %, com dt = t − tp em dias (9.6.3.4.5, p. 74)."""
    if dt <= 0.0:
        return 0.0
    if cabo.psi_func is not None:
        psi = float(cabo.psi_func(dt))
    else:
        p1000 = float(cabo.psi_1000_pct)
        teto = PSI_INFINITO_SOBRE_PSI_1000 * p1000
        psi = teto if math.isinf(dt) else min(p1000 * (dt / 41.67) ** 0.15, teto)
    if not 0.0 <= psi < 100.0:
        raise nbr.FaixaNormativaError(f"ψ = {psi:g} %: tem de estar em [0, 100).")
    return psi


def _chi_cabo_p43(cabo: CaboProtensao, t: float) -> float:
    """χ(t,tp) = −ln[1 − ψ(t,tp)] (9.6.3.4.2, p. 72)."""
    return -math.log(1.0 - _psi_cabo_p43(cabo, t - float(cabo.t_protensao_dias)) / 100.0)


class _ElementoP43:
    """Estado de um elemento da seção: acréscimos de tensão com a idade de aplicação."""

    def __init__(self, tipo: str, obj, A: float, y: float, I: float = 0.0):
        self.tipo, self.obj, self.A, self.y, self.I = tipo, obj, A, y, I
        # (Δσ, τ, t_fim): t_fim é o fim do passo do acréscimo gradual; None se súbito.
        self.inc_n: list[tuple[float, float, float | None]] = []
        self.inc_m: list[tuple[float, float, float | None]] = []   # só camadas: Δ(M/I)
        self.sigma_n = 0.0
        self.sigma_m = 0.0

    # Flexibilidade J(t) de um acréscimo aplicado em τ (MPa⁻¹).
    def J(self, t: float, tau: float, t_fim: float | None, alfa: float) -> float:
        if self.tipo == "camada":
            c = self.obj
            idade_tau = tau - c.t_concretagem_dias
            Ec = _tc_p43._modulo_idade_p43(c.Ec_mpa if c.Ec_mpa is not None else c.Eci_mpa,
                                            idade_tau)
            if t <= tau:
                return 1.0 / Ec
            p = float(c.phi_func(t - c.t_concretagem_dias, idade_tau))
            if t_fim is None:            # acréscimo súbito: superposição
                return 1.0 / Ec + p / c.Eci_mpa
            if t <= t_fim:               # dentro do próprio passo: α de A.2.5
                return 1.0 / Ec + alfa * p / c.Eci_mpa
            p_fim = float(c.phi_func(t_fim - c.t_concretagem_dias, idade_tau))
            return 1.0 / Ec + (alfa * p_fim + p - p_fim) / c.Eci_mpa
        if self.tipo == "cabo":
            c = self.obj
            return (1.0 + _chi_cabo_p43(c, t) - _chi_cabo_p43(c, tau)) / c.Ep_mpa
        return 1.0 / self.obj.Es_mpa

    def historia(self, t_a: float, t_b: float, alfa: float) -> tuple[float, float]:
        """Deformação (e curvatura) diferida de t_a a t_b dos acréscimos já aplicados."""
        dn = sum(ds * (self.J(t_b, tau, g, alfa) - self.J(t_a, tau, g, alfa))
                 for ds, tau, g in self.inc_n)
        dm = sum(ds * (self.J(t_b, tau, g, alfa) - self.J(t_a, tau, g, alfa))
                 for ds, tau, g in self.inc_m)
        if self.tipo == "camada" and self.obj.eps_cs_func is not None:
            c = self.obj
            i0 = c.t_ativacao_dias - c.t_concretagem_dias
            ecs = (float(c.eps_cs_func(t_b - c.t_concretagem_dias, i0))
                   - (0.0 if t_a <= c.t_ativacao_dias
                      else float(c.eps_cs_func(t_a - c.t_concretagem_dias, i0))))
            dn += ecs / 1000.0
        return dn, dm


def _validar_p43(fases, camadas, cabos, armaduras, t_final: float) -> None:
    if not camadas:
        raise nbr.FaixaNormativaError("Informe ao menos uma camada de concreto.")
    for k, c in enumerate(camadas):
        if not (float(c.Ac_cm2) > 0.0 and float(c.Ic_cm4) >= 0.0 and float(c.Eci_mpa) > 0.0):
            raise nbr.FaixaNormativaError(
                f"Camada {k + 1}: Ac e Eci têm de ser positivos e Ic, não negativo.")
        if float(c.t_ativacao_dias) < float(c.t_concretagem_dias):
            raise nbr.FaixaNormativaError(
                f"Camada {k + 1}: t_ativacao = {c.t_ativacao_dias:g} dias anterior à "
                f"concretagem ({c.t_concretagem_dias:g} dias).")
    for k, c in enumerate(cabos):
        if not (float(c.Ap_cm2) > 0.0 and float(c.sigma_p0_mpa) > 0.0 and float(c.Ep_mpa) > 0.0):
            raise nbr.FaixaNormativaError(
                f"Cabo {k + 1}: Ap, σp0 e Ep têm de ser positivos.")
        if float(c.psi_1000_pct) < 0.0:
            raise nbr.FaixaNormativaError(f"Cabo {k + 1}: ψ1000 negativo.")
    for k, a in enumerate(armaduras):
        if not (float(a.As_cm2) > 0.0 and float(a.Es_mpa) > 0.0):
            raise nbr.FaixaNormativaError(f"Armadura passiva {k + 1}: As e Es têm de ser positivos.")
    instantes = ([float(f.t_dias) for f in fases] + [float(c.t_ativacao_dias) for c in camadas]
                 + [float(c.t_protensao_dias) for c in cabos]
                 + [float(a.t_ativacao_dias) for a in armaduras])
    if any(math.isinf(x) or math.isnan(x) for x in instantes):
        raise nbr.FaixaNormativaError("Os instantes das fases, camadas e cabos têm de ser finitos.")
    if max(instantes) > t_final:
        raise nbr.FaixaNormativaError(
            f"t_final = {t_final:g} dias anterior a uma fase ({max(instantes):g} dias).")


def _subnos_p43(t_a: float, t_b: float, n: int) -> list[float]:
    """Nós interiores de (t_a, t_b), em progressão geométrica de (t − t_a + 1)."""
    if n <= 1:
        return []
    fim = DT_INTERIOR_INFINITO_DIAS if math.isinf(t_b) else t_b - t_a
    return [t_a + (1.0 + fim) ** (k / n) - 1.0 for k in range(1, n)]


def perdas_metodo_geral(
    fases: _Sequence_p43[FaseCarga],
    camadas: _Sequence_p43[CamadaConcreto],
    cabos: _Sequence_p43[CaboProtensao],
    t_final_dias: float,
    armaduras: _Sequence_p43[ArmaduraPassivaMetodoGeral] = (),
    alfa: float = ALFA_METODO_GERAL_PADRAO,
    n_subpassos: int = 1,
    tempos_saida_dias: _Sequence_p43[float] = (),
) -> ResultadoPerdasMetodoGeral:
    """Perdas progressivas pelo método geral, fases em idades diferentes (9.6.3.4.4, PDF p. 73).

    Texto da norma: quando as ações permanentes (carga permanente ou
    protensão) são aplicadas parceladamente em idades diferentes (não
    satisfeitas as condições de 9.6.3.4.2), considera-se a fluência de cada
    camada de concreto e a relaxação de cada cabo separadamente; a relaxação
    de cada cabo pode ser considerada isolada, independentemente da aplicação
    posterior de outras ações permanentes. A norma não dá fórmula fechada;
    o procedimento adotado (análise da seção passo a passo no tempo) está
    descrito no comentário do bloco P43 deste módulo:

        concreto (A.2.5, p. 240): ε(t) = Σ Δσ(τ)·[1/Ec(τ) + α'·φ(t,τ)/Eci] + εcs
            α' = 1 para acréscimo súbito (fase) e α para o acréscimo gradual
            de cada passo, aplicado no início do passo τ = t_{i−1}; depois do
            fim do passo t_i, esse acréscimo continua a fluir com
            φ(t,t_{i−1}) − φ(t_i,t_{i−1});
        cabo (9.6.3.4.2 e 9.6.3.4.5, p. 72 e 74):
            ε(t) = σp0·[1 + χ(t,tp)]/Ep + Σ Δσp·[1 + χ(t,tp) − χ(τ,tp)]/Ep,
            χ = −ln(1 − ψ), ψ do próprio cabo desde a sua protensão tp;
        armadura passiva: elástica (Es);
        seção plana ε(y) = ε0 + κ·y e equilíbrio de N e M em cada nó.

    Entradas:
        fases: ações externas súbitas (``FaseCarga``: t, N em kN, M em kN·cm).
        camadas: ``CamadaConcreto`` (ao menos uma).
        cabos: ``CaboProtensao``.
        t_final_dias: fim da análise, no eixo de tempo comum (pode ser
            ``math.inf`` se as funções φ e εcs das camadas aceitarem).
        armaduras: ``ArmaduraPassivaMetodoGeral`` (opcional).
        alfa: α de A.2.5 para os acréscimos graduais, em (0; 1]; padrão 0,8
            ("outros casos usuais"). Com uma fase só, use 0,5 e Ec(t0) = Eci
            para reproduzir 9.6.3.4.2.
        n_subpassos: passos em cada intervalo entre instantes de fase, em
            progressão geométrica de (t − t_a + 1). Com muitos passos e
            α = 1, o resultado tende à forma integral de A.2.5 (superposição);
            α < 1 é a aproximação de passo longo e, com φ do Anexo A (que já
            tem φa e parte de φd logo após o carregamento), continua a pesar
            dentro de cada passo curto.
        tempos_saida_dias: instantes extras onde se quer o estado.

    Ordem no mesmo instante: ativam-se as camadas e as armaduras passivas,
    aplicam-se as fases de carga e depois protendem-se os cabos, um a um, na
    ordem da lista (cada cabo já aderente sofre o encurtamento imediato dos
    seguintes). Tensões em MPa (cabo positivo em tração; concreto com
    compressão negativa).

    Devolve ``ResultadoPerdasMetodoGeral``: por cabo, σp em cada nó, a perda
    progressiva (acréscimos graduais: fluência, retração e relaxação), a
    variação imediata por ações posteriores e a perda total σp0 − σp(t).
    """
    import numpy as _np

    t_final = float(t_final_dias)
    a = float(alfa)
    if not 0.0 < a <= 1.0:
        raise nbr.FaixaNormativaError(f"α = {a:g}: tem de estar em (0; 1] (A.2.5).")
    n_sub = int(n_subpassos)
    if n_sub < 1:
        raise nbr.FaixaNormativaError(f"n_subpassos = {n_sub}: tem de ser >= 1.")
    fases, camadas, cabos, armaduras = list(fases), list(camadas), list(cabos), list(armaduras)
    _validar_p43(fases, camadas, cabos, armaduras, t_final)
    saidas = [float(x) for x in tempos_saida_dias]
    if any(not (math.isfinite(x) and x <= t_final) for x in saidas):
        raise nbr.FaixaNormativaError("tempos_saida_dias têm de ser finitos e <= t_final.")

    el_cam = [_ElementoP43("camada", c, float(c.Ac_cm2), float(c.y_cm), float(c.Ic_cm4))
              for c in camadas]
    el_cab = [_ElementoP43("cabo", c, float(c.Ap_cm2), float(c.y_cm)) for c in cabos]
    el_arm = [_ElementoP43("passiva", c, float(c.As_cm2), float(c.y_cm)) for c in armaduras]
    ativos: list[_ElementoP43] = []

    eventos = sorted({float(f.t_dias) for f in fases}
                     | {float(c.t_ativacao_dias) for c in camadas}
                     | {float(c.t_protensao_dias) for c in cabos}
                     | {float(c.t_ativacao_dias) for c in armaduras})
    principais = sorted(set(eventos) | set(saidas) | {t_final})
    nos: list[float] = [principais[0]]
    for ta, tb in zip(principais, principais[1:]):
        nos.extend(_subnos_p43(ta, tb, n_sub) if ta >= eventos[0] else [])
        nos.append(tb)

    eps0 = 0.0
    kappa = 0.0
    residuo_max = 0.0

    def resolver(dN: float, dM: float, t: float, tau: float, t_fim: float | None,
                 t_ant: float | None) -> None:
        """Um passo: acha Δε0 e Δκ e aplica os acréscimos a cada elemento ativo."""
        nonlocal eps0, kappa, residuo_max
        if not ativos:
            raise nbr.FaixaNormativaError(
                f"Ação em t = {t:g} dias sem camada de concreto ativa na seção.")
        dados = []
        K = _np.zeros((2, 2))
        r = _np.array([dN, dM], dtype=float)
        for e in ativos:
            Jn = e.J(t, tau, t_fim, a)
            hn, hm = e.historia(t_ant, t, a) if t_ant is not None else (0.0, 0.0)
            k = e.A / Jn
            km = e.I / Jn
            K += _np.array([[k, k * e.y], [k * e.y, k * e.y * e.y + km]])
            r += _np.array([k * hn, k * e.y * hn + km * hm])
            dados.append((e, Jn, hn, hm))
        if abs(_np.linalg.det(K)) <= 1e-12 * max(1.0, float(_np.abs(K).max()) ** 2):
            raise nbr.FaixaNormativaError(
                f"Seção sem rigidez à flexão em t = {t:g} dias (verifique Ic das camadas).")
        de0, dk = _np.linalg.solve(K, r)
        sN = sM = 0.0
        for e, Jn, hn, hm in dados:
            dsn = (de0 + dk * e.y - hn) / Jn
            e.inc_n.append((float(dsn), tau, t_fim))
            e.sigma_n += float(dsn)
            sN += e.A * dsn
            sM += e.A * dsn * e.y
            if e.tipo == "camada":
                dsm = (dk - hm) / Jn
                e.inc_m.append((float(dsm), tau, t_fim))
                e.sigma_m += float(dsm)
                sM += e.I * dsm
        residuo_max = max(residuo_max, abs(sN - dN), abs(sM - dM))
        eps0 += float(de0)
        kappa += float(dk)

    hist_t: list[float] = []
    hist_p: list[list[float]] = [[] for _ in cabos]
    hist_cn: list[list[float]] = [[] for _ in camadas]
    hist_cm: list[list[float]] = [[] for _ in camadas]
    hist_e0: list[float] = []
    hist_k: list[float] = []
    gradual_p = [0.0] * len(cabos)
    subito_p = [0.0] * len(cabos)

    t_ant: float | None = None
    for t in nos:
        # 1) passo gradual de t_ant a t (fluência, retração, relaxação)
        if t_ant is not None and ativos:
            antes = [e.sigma_n for e in el_cab]
            resolver(0.0, 0.0, t, t_ant, t, t_ant)
            for i, e in enumerate(el_cab):
                gradual_p[i] += e.sigma_n - antes[i]
        # 2) eventos súbitos no instante t
        for e, obj in zip(el_cam + el_arm, camadas + armaduras):
            if float(obj.t_ativacao_dias) == t:
                ativos.append(e)
        dN = sum(float(f.N_kn) for f in fases if float(f.t_dias) == t) * 10.0   # kN → MPa·cm²
        dM = sum(float(f.M_kncm) for f in fases if float(f.t_dias) == t) * 10.0  # kN·cm → MPa·cm³
        if dN != 0.0 or dM != 0.0:
            antes = [e.sigma_n for e in el_cab]
            resolver(dN, dM, t, t, None, None)
            for i, e in enumerate(el_cab):
                subito_p[i] += e.sigma_n - antes[i]
        for i, (e, cabo) in enumerate(zip(el_cab, cabos)):
            if float(cabo.t_protensao_dias) != t:
                continue
            P = float(cabo.Ap_cm2) * float(cabo.sigma_p0_mpa)
            antes = [x.sigma_n for x in el_cab]
            resolver(-P, -P * float(cabo.y_cm), t, t, None, None)
            for j, x in enumerate(el_cab):
                subito_p[j] += x.sigma_n - antes[j]
            e.inc_n.append((float(cabo.sigma_p0_mpa), t, None))
            e.sigma_n = float(cabo.sigma_p0_mpa)
            ativos.append(e)
        hist_t.append(t)
        for i, (e, cabo) in enumerate(zip(el_cab, cabos)):
            hist_p[i].append(e.sigma_n if t >= float(cabo.t_protensao_dias) else math.nan)
        for i, e in enumerate(el_cam):
            hist_cn[i].append(e.sigma_n)
            hist_cm[i].append(e.sigma_m)
        hist_e0.append(eps0 * 1000.0)
        hist_k.append(kappa * 1000.0)
        t_ant = t

    sig_fin = tuple(e.sigma_n for e in el_cab)
    perda_prog = tuple(-g for g in gradual_p)
    perda_tot = tuple(float(c.sigma_p0_mpa) - s for c, s in zip(cabos, sig_fin))
    t_txt = "∞" if math.isinf(t_final) else f"{t_final:g}"
    memoria = [
        "9.6.3.4.4 (p. 73) — método geral: fluência de cada camada e relaxação de cada cabo "
        "consideradas separadamente, seção analisada passo a passo no tempo.",
        f"{len(camadas)} camada(s), {len(cabos)} cabo(s), {len(armaduras)} armadura(s) passiva(s), "
        f"{len(fases)} fase(s) de carga; {len(nos)} nós até t = {t_txt} dias, "
        f"{n_sub} subpasso(s) por intervalo; α = {_fmt_p30(a)} (A.2.5, p. 240).",
        f"Resíduo máximo de equilíbrio: {_fmt_p30(residuo_max / 10.0)} kN ou kN·cm.",
    ]
    for i, c in enumerate(cabos):
        nome = c.nome or f"cabo {i + 1}"
        memoria.append(
            f"{nome}: σp0 = {_fmt_p30(float(c.sigma_p0_mpa))} MPa em t = "
            f"{_fmt_p30(float(c.t_protensao_dias))} dias; perda progressiva = "
            f"{_fmt_p30(perda_prog[i])} MPa; variação imediata por ações posteriores = "
            f"{_fmt_p30(subito_p[i])} MPa; σp(t) = {_fmt_p30(sig_fin[i])} MPa; perda total = "
            f"{_fmt_p30(perda_tot[i])} MPa ({_fmt_p30(100.0 * perda_tot[i] / float(c.sigma_p0_mpa))} % de σp0).")
    res = ResultadoPerdasMetodoGeral(
        tempos_dias=tuple(hist_t),
        sigma_p_mpa=tuple(tuple(h) for h in hist_p),
        sigma_c_n_mpa=tuple(tuple(h) for h in hist_cn),
        sigma_c_m_mpa_por_cm=tuple(tuple(h) for h in hist_cm),
        eps0_pmil=tuple(hist_e0), kappa_pmil_por_cm=tuple(hist_k),
        sigma_p_final_mpa=sig_fin, perda_progressiva_mpa=perda_prog,
        variacao_imediata_mpa=tuple(subito_p), perda_total_mpa=perda_tot,
        alfa=a, n_subpassos=n_sub, memoria=tuple(memoria),
        y_camadas_cm=tuple(float(c.y_cm) for c in camadas),
    )
    return res


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    _demo()
