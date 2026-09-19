"""Blocos de Fundação sobre Estacas (NBR 6118:2023 + Método de Blévot).

Nome até 19/09/2026: blocos_bastos.py. O crédito às apostilas está abaixo.

Implementa o dimensionamento de blocos rígidos sobre estacas seguindo a
apostila "BLOCOS DE FUNDAÇÃO", Prof. Paulo Sérgio Bastos, UNESP/Bauru,
pelo Método das Bielas (Blévot).

Casos cobertos:
    - Bloco sobre 2 estacas
    - Bloco sobre 3 estacas (em triângulo equilátero)
    - Bloco sobre 4 estacas (em quadrado)

Para cada um:
    - Limites de altura útil (45 deg <= beta <= 55 deg)
    - Tensão de compressão nas bielas (junto ao pilar e à estaca)
    - Tensão limite (Blévot, apostila): 1.4/1.75/2.1 * KR * fcd (2/3/4
      estacas). Este NÃO é um limite da NBR 6118 -- é o critério adotado
      por este módulo (decisão 2 do plano de correção / achado FUN-01).
      A verificação equivalente da própria norma (22.3.2: fcd1 = 0,85 *
      alpha_v2 * fcd no nó CCC sob o pilar; fcd3 = 0,72 * alpha_v2 * fcd
      no nó CCT sobre a estaca) sai ao lado, só como informação, em
      ResultadoBloco / verifica_bielas_22_3_2 -- não substitui ok_bielas.
    - Armadura principal
    - Armadura de suspensão
    - Armadura superior e de pele

Convenções:
    - fck, fyk em MPa.
    - Geometria em cm. Forças em kN. Áreas em cm2.
    - phi_e = diâmetro da estaca circular; ap, bp = lados do pilar.
    - "ap" = lado do pilar na direção das estacas (a direção "longa").
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
# 22.3.2 -- parâmetros de resistência das bielas e nos (informativo, FUN-01)
#
# fcd1_no_pilar_kncm2 e fcd3_na_estaca_kncm2 foram promovidas (P35) para
# bielas_tirantes_nbr6118.py (fcd1_kncm2 / fcd3_kncm2, junto com fcd2_kncm2,
# que este módulo não usava): são fórmulas de 22.3.2 em geral, não só de
# blocos. As duas funções abaixo viram reexportação fina, para não quebrar
# quem já as chama por este nome.
# ---------------------------------------------------------------------------
def alpha_v2(fck_mpa: float) -> float:
    """alpha_v2 = 1 - fck/250, fck em MPa (17.4.2.2, 19.5.3.1, 22.3.2).
    Delega ao núcleo normativo."""
    return nbr.alpha_v2(fck_mpa)


def fcd1_no_pilar_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fcd1 = 0,85 * alpha_v2 * fcd -- biela prismática / nó CCC, sob o
    pilar (22.3.2, PDF p. 204). NÃO é o critério adotado por este módulo
    (Blévot, ver sigma_lim_2/3/4_estacas etc.); é a verificação
    equivalente da própria NBR, calculada aqui só como informação
    (decisão 2 do plano de correção / achado FUN-01).

    Reexportação fina de bielas_tirantes_nbr6118.fcd1_kncm2 (P35): a fórmula
    mora lá agora, fonte única do método de bielas e tirantes."""
    try:  # executado como script, ou com dimensionamento/ no sys.path
        import bielas_tirantes_nbr6118 as bt
    except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
        from dimensionamento import bielas_tirantes_nbr6118 as bt
    return bt.fcd1_kncm2(fck_mpa, gama_c)


def fcd3_na_estaca_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fcd3 = 0,72 * alpha_v2 * fcd -- nó CCT, atravessado por tirante
    único, sobre a estaca (22.3.2, PDF p. 204). Mesma ressalva de
    fcd1_no_pilar_kncm2: informativo, não substitui ok_bielas (Blévot).

    Reexportação fina de bielas_tirantes_nbr6118.fcd3_kncm2 (P35): a fórmula
    mora lá agora, fonte única do método de bielas e tirantes."""
    try:  # executado como script, ou com dimensionamento/ no sys.path
        import bielas_tirantes_nbr6118 as bt
    except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
        from dimensionamento import bielas_tirantes_nbr6118 as bt
    return bt.fcd3_kncm2(fck_mpa, gama_c)


def verifica_bielas_22_3_2(sigma_pil_kncm2: float, sigma_est_kncm2: float,
                           fck_mpa: float, gama_c: float = GAMA_C) -> dict:
    """Verificação informativa das tensões nas bielas/nós pela NBR 6118
    22.3.2 (PDF p. 204), ao lado do critério de Blévot que o módulo usa
    de fato (ok_bielas, em ResultadoBloco). fcd1 no nó do pilar (CCC),
    fcd3 no nó da estaca (CCT); alpha_v2 = 1 - fck/250 (fck em MPa)."""
    fcd1 = fcd1_no_pilar_kncm2(fck_mpa, gama_c)
    fcd3 = fcd3_na_estaca_kncm2(fck_mpa, gama_c)
    razao_pil = sigma_pil_kncm2 / fcd1
    razao_est = sigma_est_kncm2 / fcd3
    return {
        "fcd1_kncm2": fcd1, "fcd3_kncm2": fcd3,
        "fcd1_MPa": fcd1 * 10.0, "fcd3_MPa": fcd3 * 10.0,
        "razao_pil_fcd1": razao_pil, "razao_est_fcd3": razao_est,
        "ok": razao_pil <= 1.0 and razao_est <= 1.0,
    }


def aest_quadrado_equivalente(phi_e_cm: float) -> float:
    """Lado de estaca quadrada com área = pi*phi^2/4."""
    return math.sqrt(math.pi) / 2.0 * phi_e_cm


# ---------------------------------------------------------------------------
# Bloco sobre 2 estacas
# ---------------------------------------------------------------------------
def d_limites_2_estacas(e_cm: float, ap_cm: float) -> tuple[float, float]:
    """45 deg <= beta <= 55 deg para 2 estacas (Blévot/Machado).
       d_min = 0.5 * (e - ap/2);  d_max = 0.71 * (e - ap/2)."""
    base = e_cm - ap_cm / 2.0
    return 0.5 * base, 0.71 * base


def beta_2_estacas(d_cm: float, e_cm: float, ap_cm: float) -> float:
    """tg(beta) = d / (e/2 - ap/4)  -> beta em radianos."""
    return math.atan(d_cm / (e_cm / 2.0 - ap_cm / 4.0))


def sigma_bielas_2_estacas(Nd_kn: float, Ap_cm2: float, Ae_cm2: float,
                           beta_rad: float) -> tuple[float, float]:
    """Tensão na biela junto ao pilar e junto à estaca (kN/cm2).
    sigma_pil = Nd / (Ap * sin^2 beta)
    sigma_est = Nd / (2 * Ae * sin^2 beta)"""
    sb2 = math.sin(beta_rad) ** 2
    sigma_pil = Nd_kn / (Ap_cm2 * sb2)
    sigma_est = Nd_kn / (2.0 * Ae_cm2 * sb2)
    return sigma_pil, sigma_est


def sigma_lim_2_estacas(fck_mpa: float, KR: float = 0.95,
                        gama_c: float = GAMA_C) -> float:
    """sigma_lim = 1,4 * KR * fcd (2 estacas).

    Coeficiente 1,4 do método das bielas de Blévot (apostila) -- NÃO da
    NBR 6118. A verificação equivalente da norma é a 22.3.2 (ver
    verifica_bielas_22_3_2 / fcd1_no_pilar_kncm2 / fcd3_na_estaca_kncm2),
    calculada à parte, só como informação (decisão 2 / achado FUN-01)."""
    return 1.4 * KR * fcd_kncm2(fck_mpa, gama_c)


def As_principal_2_estacas(Nd_kn: float, e_cm: float, ap_cm: float,
                           d_cm: float, fyk_mpa: float = 500.0,
                           gama_s: float = GAMA_S) -> float:
    """As = 1.15 * Nd * (2e - ap) / (8 * d * fyd)  (Blévot)."""
    fyd = fyd_kncm2(fyk_mpa, gama_s) * 10.0  # MPa
    fyd_kncm = fyd / 10.0
    return 1.15 * Nd_kn * (2.0 * e_cm - ap_cm) / (8.0 * d_cm * fyd_kncm)


# ---------------------------------------------------------------------------
# Bloco sobre 3 estacas (em triângulo equilátero)
# ---------------------------------------------------------------------------
def d_limites_3_estacas(e_cm: float, ap_cm: float) -> tuple[float, float]:
    """45 deg <= beta <= 55 deg para 3 estacas:
       d_min = 0.58*(e - ap/2);  d_max = 0.825*(e - ap/2)."""
    base = e_cm - ap_cm / 2.0
    return 0.58 * base, 0.825 * base


def sigma_bielas_3_estacas(Nd_kn: float, Ap_cm2: float, Ae_cm2: float,
                           beta_rad: float) -> tuple[float, float]:
    """sigma_pil = 3 * Nd / (Ap * sin^2 beta)
       sigma_est = Nd / (3 * Ae * sin^2 beta)."""
    sb2 = math.sin(beta_rad) ** 2
    sigma_pil = 3.0 * Nd_kn / (Ap_cm2 * sb2)
    sigma_est = Nd_kn / (3.0 * Ae_cm2 * sb2)
    return sigma_pil, sigma_est


def sigma_lim_3_estacas(fck_mpa: float, KR: float = 0.95,
                        gama_c: float = GAMA_C) -> float:
    """sigma_lim = 1,75 * KR * fcd (3 estacas).

    Coeficiente de Blévot (apostila) -- NÃO da NBR. Ver nota em
    sigma_lim_2_estacas (decisão 2 / achado FUN-01)."""
    return 1.75 * KR * fcd_kncm2(fck_mpa, gama_c)


def As_principal_3_estacas(Nd_kn: float, e_cm: float, ap_cm: float,
                           d_cm: float, fyk_mpa: float = 500.0,
                           gama_s: float = GAMA_S) -> float:
    """As,lado = sqrt(3) * Nd * (e*sqrt(3) - 0.9*ap) / (27 * d * fyd)."""
    fyd_kncm = fyd_kncm2(fyk_mpa, gama_s)
    return (math.sqrt(3.0) * Nd_kn
            * (e_cm * math.sqrt(3.0) - 0.9 * ap_cm)
            / (27.0 * d_cm * fyd_kncm))


# ---------------------------------------------------------------------------
# Bloco sobre 4 estacas (em quadrado)
# ---------------------------------------------------------------------------
def d_limites_4_estacas(e_cm: float, ap_cm: float) -> tuple[float, float]:
    """45 deg <= beta <= 55 deg:
       d_min = 0.71*(e - ap/2);  d_max = 1.0*(e - ap/2)."""
    base = e_cm - ap_cm / 2.0
    return 0.71 * base, 1.0 * base


def sigma_bielas_4_estacas(Nd_kn: float, Ap_cm2: float, Ae_cm2: float,
                           beta_rad: float) -> tuple[float, float]:
    """sigma_pil = 4 * Nd / (Ap * sin^2 beta);
       sigma_est = Nd / (4 * Ae * sin^2 beta)."""
    sb2 = math.sin(beta_rad) ** 2
    sigma_pil = 4.0 * Nd_kn / (Ap_cm2 * sb2)
    sigma_est = Nd_kn / (4.0 * Ae_cm2 * sb2)
    return sigma_pil, sigma_est


def sigma_lim_4_estacas(fck_mpa: float, KR: float = 0.95,
                        gama_c: float = GAMA_C) -> float:
    """sigma_lim = 2,1 * KR * fcd (4 estacas).

    Coeficiente de Blévot (apostila) -- NÃO da NBR. Ver nota em
    sigma_lim_2_estacas (decisão 2 / achado FUN-01)."""
    return 2.1 * KR * fcd_kncm2(fck_mpa, gama_c)


def As_principal_4_estacas(Nd_kn: float, e_cm: float, ap_cm: float,
                           d_cm: float, fyk_mpa: float = 500.0,
                           gama_s: float = GAMA_S) -> float:
    """As,lado = Nd * (2e - ap) / (16 * d * fyd)."""
    fyd_kncm = fyd_kncm2(fyk_mpa, gama_s)
    return Nd_kn * (2.0 * e_cm - ap_cm) / (16.0 * d_cm * fyd_kncm)


# ---------------------------------------------------------------------------
# Bloco sobre 5 estacas (item 9.1 - quadrado com estaca central)
# ---------------------------------------------------------------------------
def d_limites_5_estacas(e_cm: float, ap_cm: float) -> tuple[float, float]:
    """45 deg <= beta <= 55 deg para 5 estacas:
       d_min = 0.71*(e - ap/2);  d_max = 1.0*(e - ap/2)."""
    base = e_cm - ap_cm / 2.0
    return 0.71 * base, 1.0 * base


def sigma_bielas_5_estacas(Nd_kn: float, Ap_cm2: float, Ae_cm2: float,
                           beta_rad: float) -> tuple[float, float]:
    """sigma_pil = Nd / (Ap * sin^2 beta)
       sigma_est = Nd / (5 * Ae * sin^2 beta)."""
    sb2 = math.sin(beta_rad) ** 2
    sigma_pil = Nd_kn / (Ap_cm2 * sb2)
    sigma_est = Nd_kn / (5.0 * Ae_cm2 * sb2)
    return sigma_pil, sigma_est


def sigma_lim_5_estacas_pil(fck_mpa: float, KR: float = 0.95,
                            gama_c: float = GAMA_C) -> float:
    """sigma_lim_pil = 2,6 * KR * fcd (5 estacas, nó do pilar).

    Coeficiente de Blévot (apostila) -- NÃO da NBR. Ver nota em
    sigma_lim_2_estacas (decisão 2 / achado FUN-01)."""
    return 2.6 * KR * fcd_kncm2(fck_mpa, gama_c)


def sigma_lim_5_estacas_est(fck_mpa: float, KR: float = 0.95,
                            gama_c: float = GAMA_C) -> float:
    """sigma_lim_est = 2,1 * KR * fcd (5 estacas, nó da estaca).

    Coeficiente de Blévot (apostila) -- NÃO da NBR. Ver nota em
    sigma_lim_2_estacas (decisão 2 / achado FUN-01)."""
    return 2.1 * KR * fcd_kncm2(fck_mpa, gama_c)


def As_principal_5_estacas(Nd_kn: float, e_cm: float, ap_cm: float,
                           d_cm: float, fyk_mpa: float = 500.0,
                           gama_s: float = GAMA_S) -> float:
    """As,lado = Nd * (2e - ap) / (20 * d * fyd) (4/5 da fórmula de 4 estacas)."""
    fyd_kncm = fyd_kncm2(fyk_mpa, gama_s)
    return Nd_kn * (2.0 * e_cm - ap_cm) / (20.0 * d_cm * fyd_kncm)


def As_suspensao_5_estacas(Nd_kn: float, fyk_mpa: float = 500.0,
                           gama_s: float = GAMA_S) -> float:
    """As,susp = Nd / (7.5 * fyd) (apostila item 9.1.3)."""
    fyd_kncm = fyd_kncm2(fyk_mpa, gama_s)
    return Nd_kn / (7.5 * fyd_kncm)


# ---------------------------------------------------------------------------
# Armaduras complementares (suspensão, superior, pele)
# ---------------------------------------------------------------------------
def As_suspensao_total(Nd_kn: float, n_estacas: int,
                       fyk_mpa: float = 500.0,
                       gama_s: float = GAMA_S) -> float:
    """As,susp,total = Nd / (1.5 * ne * fyd)  (apostila item 7.4 generalizado)."""
    fyd = fyd_kncm2(fyk_mpa, gama_s)
    return Nd_kn / (1.5 * n_estacas * fyd)


def As_superior_dir(As_principal_cm2: float) -> float:
    """As,sup = 0.20 * As (em cada direção da malha)."""
    return 0.20 * As_principal_cm2


def Asp_pele_face(As_total_cm2: float) -> float:
    """Asp,face = (1/8) * As,total."""
    return As_total_cm2 / 8.0


# ---------------------------------------------------------------------------
# Resultado consolidado
# ---------------------------------------------------------------------------
@dataclass
class ResultadoBloco:
    n_estacas: int
    e_cm: float
    ap_cm: float
    bp_cm: float
    d_cm: float
    h_cm: float
    beta_deg: float
    sigma_pil_kncm2: float
    sigma_est_kncm2: float
    sigma_lim_kncm2: float
    ok_bielas: bool
    As_principal_cm2: float
    As_suspensao_cm2: float
    # 22.3.2, informativo (decisão 2 / achado FUN-01) -- não muda ok_bielas
    fcd1_kncm2: float = 0.0
    fcd3_kncm2: float = 0.0
    razao_pil_fcd1: float = 0.0
    razao_est_fcd3: float = 0.0
    ok_bielas_22_3_2: bool = True
    # P37 -- 22.7.1, 22.7.2.1 e 22.7.4.1 (detalhamento do bloco rígido)
    rigido_22_7_1: bool | None = None
    faixa_armadura_estaca_cm: float = 0.0
    F_tracao_dir_kn: float = 0.0
    As_distribuicao_dir_cm2: float = 0.0
    Asp_pele_face_cm2: float = 0.0
    em_linha_unica: bool = False
    armadura_lateral_superior_obrigatoria: bool = False
    exige_suspensao: bool = False
    motivo_suspensao: str = ""


def projetar_bloco(
    n_estacas: int, Nk_kn: float, e_cm: float, ap_cm: float, bp_cm: float,
    phi_e_cm: float, h_cm: float, fck_mpa: float,
    fyk_mpa: float = 500.0, KR: float = 0.95,
    gama_f: float = GAMA_F, gama_c: float = GAMA_C,
    gama_s: float = GAMA_S, cobrimento_cm: float = 3.0,
    a_bloco_cm: float | None = None, b_bloco_cm: float | None = None,
    espacamento_estacas_cm: float | None = None,
    em_linha_unica: bool | None = None,
    fracao_esforcos_distribuicao: float = 0.20,
    grande_volume: bool = False,
) -> ResultadoBloco:
    """Projeta bloco sobre 2, 3 ou 4 estacas, método das bielas (Blévot).

    ok_bielas usa os limites de Blévot -- o critério que este módulo
    adota (decisão 2 do plano de correção / achado FUN-01). fcd1/fcd3 e
    razao_pil_fcd1/razao_est_fcd3 trazem, lado a lado, a verificação
    equivalente da NBR 22.3.2, só como informação: não mudam ok_bielas.

    P37 -- o detalhamento de 22.7 (PDF p. 213-215) sai junto, nos campos
    novos de ``ResultadoBloco`` (todos com padrão que reproduz o
    comportamento anterior quando o dado não é informado):

    - ``rigido_22_7_1``: classificação rígido x flexível (22.7.1), só
      quando ``a_bloco_cm`` (e, para as duas direções, ``b_bloco_cm``) são
      informados -- a dimensão em planta do bloco não é dado das fórmulas
      de Blévot. Sem elas fica None;
    - ``faixa_armadura_estaca_cm`` = 1,2·φ,estaca (22.7.2.1 a);
    - ``F_tracao_dir_kn`` = As,principal·fyd, a força de tração total da
      direção, e ``As_distribuicao_dir_cm2`` = 20 % dela sobre fyd
      (22.7.4.1.2) -- que é exatamente ``As_superior_dir(As_principal)``;
    - ``Asp_pele_face_cm2`` = ``Asp_pele_face(As_principal)`` e
      ``armadura_lateral_superior_obrigatoria`` (22.7.4.1.5): obrigatória
      em bloco com duas ou mais estacas em uma única linha. Sem
      ``em_linha_unica`` explícito, supõe-se linha única só com 2 estacas;
    - ``exige_suspensao`` e ``motivo_suspensao`` (22.7.4.1.3), com o
      espaçamento entre estacas ``espacamento_estacas_cm`` (padrão e_cm) e
      a fração dos esforços coberta pela armadura de distribuição
      ``fracao_esforcos_distribuicao`` (padrão 0,20, o de 22.7.4.1.2).
      ``As_suspensao_cm2`` continua sendo o valor de Blévot/apostila,
      sempre calculado, como antes.

    ``grande_volume=True`` registra na classificação de 22.7.4.1.5 a
    conveniência de analisar armaduras complementares.
    """
    if n_estacas not in (2, 3, 4):
        raise ValueError("n_estacas deve ser 2, 3 ou 4.")

    aest = aest_quadrado_equivalente(phi_e_cm)
    d = h_cm - max(5.0, aest / 5.0) - cobrimento_cm
    Nd = gama_f * Nk_kn
    Ap = ap_cm * bp_cm
    Ae = math.pi * phi_e_cm ** 2 / 4.0

    if n_estacas == 2:
        beta = beta_2_estacas(d, e_cm, ap_cm)
        sigma_pil, sigma_est = sigma_bielas_2_estacas(Nd, Ap, Ae, beta)
        sigma_lim = sigma_lim_2_estacas(fck_mpa, KR, gama_c)
        As_p = As_principal_2_estacas(Nd, e_cm, ap_cm, d, fyk_mpa, gama_s)
    elif n_estacas == 3:
        # 3 estacas: usa-se a direção da mediana; beta = atan(d / (e/sqrt(3) - ap/4))
        # apostila usa fórmula simplificada para tensões via Ap/3
        beta = math.atan(d / (e_cm / math.sqrt(3.0) - ap_cm / 4.0))
        sigma_pil, sigma_est = sigma_bielas_3_estacas(Nd, Ap, Ae, beta)
        sigma_lim = sigma_lim_3_estacas(fck_mpa, KR, gama_c)
        As_p = As_principal_3_estacas(Nd, e_cm, ap_cm, d, fyk_mpa, gama_s)
    else:  # 4 estacas
        beta = math.atan(d / (e_cm / math.sqrt(2.0) - ap_cm / 4.0))
        sigma_pil, sigma_est = sigma_bielas_4_estacas(Nd, Ap, Ae, beta)
        sigma_lim = sigma_lim_4_estacas(fck_mpa, KR, gama_c)
        As_p = As_principal_4_estacas(Nd, e_cm, ap_cm, d, fyk_mpa, gama_s)

    As_susp = As_suspensao_total(Nd, n_estacas, fyk_mpa, gama_s)
    info_22_3_2 = verifica_bielas_22_3_2(sigma_pil, sigma_est, fck_mpa, gama_c)

    # --- P37: detalhamento de 22.7 (PDF p. 213-215) ---
    rigido = None
    if a_bloco_cm is not None:
        rigido = eh_rigido_bloco(h_cm, a_bloco_cm, ap_cm, b_bloco_cm, bp_cm)
    faixa = faixa_armadura_estaca_cm(phi_e_cm)
    fyd_kncm = fyd_kncm2(fyk_mpa, gama_s)
    F_tracao = As_p * fyd_kncm
    As_distr = As_distribuicao_bloco_cm2(F_tracao, fyk_mpa, gama_s,
                                         fracao_esforcos_distribuicao)
    lat = armaduras_lateral_e_superior_bloco(
        n_estacas, As_p, em_linha_unica=em_linha_unica,
        grande_volume=grande_volume,
    )
    susp = exigir_armadura_suspensao_bloco(
        fracao_esforcos_distribuicao,
        e_cm if espacamento_estacas_cm is None else espacamento_estacas_cm,
        h_cm, suspensao_prevista=True, avisar=False,
    )

    return ResultadoBloco(
        n_estacas=n_estacas, e_cm=e_cm, ap_cm=ap_cm, bp_cm=bp_cm,
        d_cm=d, h_cm=h_cm, beta_deg=math.degrees(beta),
        sigma_pil_kncm2=sigma_pil, sigma_est_kncm2=sigma_est,
        sigma_lim_kncm2=sigma_lim,
        ok_bielas=(sigma_pil <= sigma_lim and sigma_est <= sigma_lim),
        As_principal_cm2=As_p, As_suspensao_cm2=As_susp,
        fcd1_kncm2=info_22_3_2["fcd1_kncm2"],
        fcd3_kncm2=info_22_3_2["fcd3_kncm2"],
        razao_pil_fcd1=info_22_3_2["razao_pil_fcd1"],
        razao_est_fcd3=info_22_3_2["razao_est_fcd3"],
        ok_bielas_22_3_2=info_22_3_2["ok"],
        rigido_22_7_1=rigido,
        faixa_armadura_estaca_cm=faixa,
        F_tracao_dir_kn=F_tracao,
        As_distribuicao_dir_cm2=As_distr,
        Asp_pele_face_cm2=lat.Asp_pele_face_cm2,
        em_linha_unica=lat.em_linha_unica,
        armadura_lateral_superior_obrigatoria=lat.obrigatoria,
        exige_suspensao=susp.exige,
        motivo_suspensao=susp.motivo,
    )


# ---------------------------------------------------------------------------
# Tests (validados contra Exemplo 1 da apostila Bastos - 2 estacas)
# ---------------------------------------------------------------------------
def _aprox(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def test_aest_equivalente() -> None:
    """phi=30 cm: aest = sqrt(pi)/2 * 30 = 26.59 cm."""
    a = aest_quadrado_equivalente(30.0)
    assert _aprox(a, 26.59, 0.05), f"aest={a:.3f}"
    print(f"  OK  aest(phi=30) = {a:.2f} cm")


def test_d_limites_2_estacas_apostila() -> None:
    """Apostila ex.1: e=80, ap=30 -> d_min=32.5, d_max=46.15 cm."""
    dmin, dmax = d_limites_2_estacas(e_cm=80.0, ap_cm=30.0)
    assert _aprox(dmin, 32.5, 0.05), f"dmin={dmin:.2f}"
    assert _aprox(dmax, 46.15, 0.05), f"dmax={dmax:.2f}"
    print(f"  OK  2 estacas: d in [{dmin:.2f}, {dmax:.2f}] cm")


def test_beta_apostila() -> None:
    """e=80, ap=30, d=45: tg(beta) = 45/(40-7.5) = 1.385; beta = 54.16 deg."""
    b = beta_2_estacas(d_cm=45.0, e_cm=80.0, ap_cm=30.0)
    assert _aprox(math.degrees(b), 54.16, 0.05), f"beta={math.degrees(b)}"
    print(f"  OK  beta = {math.degrees(b):.2f} deg")


def test_sigma_bielas_apostila() -> None:
    """Nd=920.4, Ae=pi*30^2/4=706.86, Ap=20*30=600, beta=54.16:
    sigma_pil = 920.4 / (600 * sin^2 54.16) = 2.33 kN/cm2
    sigma_est = 920.4 / (2*706.86 * sin^2 54.16) = 0.99 kN/cm2."""
    beta = math.radians(54.16)
    Ap = 600.0
    Ae = math.pi * 30.0 ** 2 / 4.0
    sp, se = sigma_bielas_2_estacas(Nd_kn=920.4, Ap_cm2=Ap, Ae_cm2=Ae,
                                     beta_rad=beta)
    assert _aprox(sp, 2.33, 0.02), f"sigma_pil={sp:.3f}"
    assert _aprox(se, 0.99, 0.02), f"sigma_est={se:.3f}"
    print(f"  OK  sigma_pil = {sp:.2f}, sigma_est = {se:.2f} kN/cm2")


def test_sigma_lim_apostila() -> None:
    """C25, KR=0.95: cd,b,lim = 1.4 * 0.95 * 25/14 = 2.375 kN/cm2."""
    s = sigma_lim_2_estacas(fck_mpa=25.0, KR=0.95)
    assert _aprox(s, 2.375, 0.005), f"sigma_lim={s:.4f}"
    print(f"  OK  sigma_lim (2 est, C25) = {s:.3f} kN/cm2 ({s*10:.2f} MPa)")


def test_As_principal_apostila() -> None:
    """Apostila ex.1: As = 1.15*920.4*(2*80-30)/(8*45*43.48) = 8.79 cm2."""
    As = As_principal_2_estacas(Nd_kn=920.4, e_cm=80.0, ap_cm=30.0,
                                d_cm=45.0)
    assert _aprox(As, 8.79, 0.05), f"As={As:.3f}"
    print(f"  OK  As (2 est) = {As:.2f} cm2  (apostila: 8.79)")


def test_As_suspensao_apostila() -> None:
    """As,susp,total bloco 2 estacas: Nd/(3*fyd) = 920.4/(3*43.48) = 7.06 cm2.
    Em '1.5 ne' genérico = 1.5*2 = 3 -> mesmo valor."""
    As = As_suspensao_total(Nd_kn=920.4, n_estacas=2)
    assert _aprox(As, 7.06, 0.05), f"As_susp={As}"
    print(f"  OK  As,susp (total) = {As:.2f} cm2")


def test_d_limites_4_estacas() -> None:
    """e=200, ap=40: dmin = 0.71 * 180 = 127.8; dmax = 180."""
    dmin, dmax = d_limites_4_estacas(e_cm=200.0, ap_cm=40.0)
    assert _aprox(dmin, 127.8, 0.1), f"dmin={dmin}"
    assert _aprox(dmax, 180.0, 0.1)
    print(f"  OK  4 estacas: d in [{dmin:.1f}, {dmax:.1f}]")


def test_As_3_estacas_consistencia() -> None:
    """3 estacas: usar e=200, ap=30, d=120, Nd=2000.
    As,lado = sqrt(3)*2000*(200*sqrt(3)-0.9*30) / (27*120*43.48)
    = sqrt(3)*2000*(346.41-27) / 140876.4
    = 1.7321*2000*319.41 / 140876.4 = 1106621/140876.4 = 7.86 cm2."""
    As = As_principal_3_estacas(Nd_kn=2000.0, e_cm=200.0, ap_cm=30.0,
                                d_cm=120.0)
    expected = math.sqrt(3) * 2000 * (200 * math.sqrt(3) - 0.9 * 30) \
        / (27 * 120 * (500.0 / 1.15) / 10.0)
    assert _aprox(As, expected, 0.01), f"As={As:.3f} vs {expected:.3f}"
    print(f"  OK  As,lado (3 est) = {As:.2f} cm2  (esperado: {expected:.2f})")


def test_As_4_estacas_consistencia() -> None:
    """4 estacas, e=200, ap=40, d=140, Nd=3000:
    As,lado = 3000*(400-40) / (16*140*43.48) = 3000*360/97395.2 = 11.09 cm2."""
    As = As_principal_4_estacas(Nd_kn=3000.0, e_cm=200.0, ap_cm=40.0,
                                d_cm=140.0)
    expected = 3000.0 * 360.0 / (16.0 * 140.0 * (500.0 / 1.15) / 10.0)
    assert _aprox(As, expected, 0.05), f"As={As:.3f} vs {expected:.3f}"
    print(f"  OK  As,lado (4 est) = {As:.2f} cm2  (esperado: {expected:.2f})")


def test_projetar_bloco_2est_apostila() -> None:
    """Reproduz Exemplo 1 (2 estacas)."""
    r = projetar_bloco(
        n_estacas=2, Nk_kn=657.4, e_cm=80.0, ap_cm=30.0, bp_cm=20.0,
        phi_e_cm=30.0, h_cm=50.0, fck_mpa=25.0, KR=0.95,
        cobrimento_cm=3.0,
    )
    # d na apostila é 45 cm; nosso cálculo usa h - max(5, aest/5) - c
    # aest = 26.59; aest/5 = 5.32; max(5, 5.32) = 5.32 -> d = 50-5.32-3=41.7
    # Apostila adota d' simplificado = 5 cm -> d = 45. Nosso d será ~41.7
    assert 40.0 < r.d_cm < 46.0, f"d={r.d_cm}"
    assert _aprox(r.beta_deg, 51.5, 5.0), f"beta={r.beta_deg}"
    assert r.As_principal_cm2 > 8.0, f"As_p={r.As_principal_cm2}"
    print(f"  OK  Bloco 2est: d={r.d_cm:.1f}, beta={r.beta_deg:.1f}, "
          f"As_p={r.As_principal_cm2:.2f}, ok_bielas={r.ok_bielas}")


def test_d_limites_5_estacas() -> None:
    """e=200, ap=40: d_min = 0.71*180=127.8, d_max=180."""
    dmin, dmax = d_limites_5_estacas(e_cm=200.0, ap_cm=40.0)
    assert _aprox(dmin, 127.8, 0.1)
    assert _aprox(dmax, 180.0, 0.1)
    print(f"  OK  5 estacas: d in [{dmin:.1f}, {dmax:.1f}]")


def test_As_5_estacas_consistencia() -> None:
    """As,lado(5 estacas) = 0.8 * As,lado(4 estacas) (fórmula 4/5 da NBR)."""
    Nd, e, ap, d = 5000.0, 250.0, 40.0, 180.0
    As4 = As_principal_4_estacas(Nd, e, ap, d)
    As5 = As_principal_5_estacas(Nd, e, ap, d)
    assert _aprox(As5, 0.8 * As4, 0.05), f"As5={As5} vs 0.8*As4={0.8*As4}"
    print(f"  OK  As 5 estacas = {As5:.2f} cm2 (= 0.8 * As 4est = "
          f"{0.8*As4:.2f})")


def test_sigma_lim_5_estacas() -> None:
    """C25, KR=0.95: sigma_lim_pil = 2.6*0.95*25/14 = 4.41 kN/cm2;
    sigma_lim_est = 2.1*0.95*25/14 = 3.56 kN/cm2."""
    sp = sigma_lim_5_estacas_pil(25.0)
    se = sigma_lim_5_estacas_est(25.0)
    assert _aprox(sp, 4.41, 0.01)
    assert _aprox(se, 3.56, 0.01)
    print(f"  OK  sigma_lim 5est: pil={sp:.2f}, est={se:.2f} kN/cm2")


def run_tests() -> int:
    tests = [
        test_aest_equivalente,
        test_d_limites_2_estacas_apostila,
        test_beta_apostila,
        test_sigma_bielas_apostila,
        test_sigma_lim_apostila,
        test_As_principal_apostila,
        test_As_suspensao_apostila,
        test_d_limites_4_estacas,
        test_As_3_estacas_consistencia,
        test_As_4_estacas_consistencia,
        test_projetar_bloco_2est_apostila,
        test_d_limites_5_estacas,
        test_As_5_estacas_consistencia,
        test_sigma_lim_5_estacas,
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
    print("=== Exemplo 1 (Apostila Bastos) - bloco 2 estacas ===")
    print("  Nk=657.4 kN, pilar 20x30, estacas phi=30, e=80 cm, C25")
    r = projetar_bloco(
        n_estacas=2, Nk_kn=657.4, e_cm=80.0, ap_cm=30.0, bp_cm=20.0,
        phi_e_cm=30.0, h_cm=50.0, fck_mpa=25.0,
    )
    print(f"  d        = {r.d_cm:.1f} cm")
    print(f"  beta     = {r.beta_deg:.1f} deg")
    print(f"  sigma_pil = {r.sigma_pil_kncm2:.2f} kN/cm2 "
          f"({r.sigma_pil_kncm2*10:.1f} MPa)")
    print(f"  sigma_est = {r.sigma_est_kncm2:.2f} kN/cm2 "
          f"({r.sigma_est_kncm2*10:.1f} MPa)")
    print(f"  sigma_lim = {r.sigma_lim_kncm2:.2f} kN/cm2 "
          f"(ok={r.ok_bielas})")
    print(f"  As princ. = {r.As_principal_cm2:.2f} cm2")
    print(f"  As susp.  = {r.As_suspensao_cm2:.2f} cm2 (total)")


# === P37: fundações — blocos sobre estacas (22.7) ===
import warnings as _warnings37
from dataclasses import dataclass as _dataclass37

try:  # executado como script, ou com dimensionamento/ no sys.path
    import ancoragem_nbr6118 as _anc37
    import sapatas_nbr6118 as _sap37
    import seguranca_nbr6118 as _seg37
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import ancoragem_nbr6118 as _anc37
    from dimensionamento import sapatas_nbr6118 as _sap37
    from dimensionamento import seguranca_nbr6118 as _seg37


FATOR_FAIXA_ESTACA = 1.2
"""22.7.2.1 a (PDF p. 213): a faixa de concentração das trações, centrada no
eixo da estaca, tem largura igual a 1,2 vez o diâmetro da estaca."""

FRACAO_MINIMA_ARMADURA_NAS_FAIXAS = 0.85
"""22.7.4.1.1 (PDF p. 214): "mais de 85 %" da armadura de flexão nas faixas
definidas pelas estacas — desigualdade estrita, 85 % exatos não bastam."""

FRACAO_DISTRIBUICAO_BLOCO = 0.20
"""22.7.4.1.2 (PDF p. 214): a malha positiva adicional corresponde a 20 % do
total das forças de tração em cada direção."""

FRACAO_DISTRIBUICAO_GATILHO_SUSPENSAO = 0.25
"""22.7.4.1.3 (PDF p. 215): armadura de distribuição para mais de 25 % dos
esforços totais exige armadura de suspensão."""

FATOR_ESPACAMENTO_GATILHO_SUSPENSAO = 3.0
"""22.7.4.1.3 (PDF p. 215): espaçamento entre estacas maior que três vezes a
altura do bloco exige armadura de suspensão."""


def _f37(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


def _pos37(valor, nome: str, item: str) -> float:
    """Converte para float exigindo valor positivo (senão FaixaNormativaError)."""
    v = float(valor)
    if not v > 0.0:
        raise nbr.FaixaNormativaError(
            f"{nome} tem de ser positivo ({item}); recebido {_f37(v)}."
        )
    return v


# --- 22.7.1 — classificação rígido x flexível (PDF p. 213) ---------------
def eh_rigido_bloco(h_cm: float, a_cm: float, ap_cm: float,
                    b_cm: float | None = None,
                    bp_cm: float | None = None) -> bool:
    """Bloco rígido pelo critério análogo ao de sapatas (22.7.1, PDF p. 213).

    22.7.1: "Blocos são estruturas de volume usadas para transmitir às
    estacas e aos tubulões as cargas de fundação, podendo ser considerados
    rígidos ou flexíveis por critério análogo ao definido para sapatas." O
    critério de sapatas é o de 22.6.1 (PDF p. 211), nas duas direções:

        h >= (a − ap)/3

    Comprimentos em cm: ``h_cm`` é a altura do bloco, ``a_cm``/``b_cm`` as
    dimensões do bloco em planta e ``ap_cm``/``bp_cm`` as do pilar nas
    mesmas direções. Sem ``b_cm``/``bp_cm``, só a direção a é conferida.
    Delega a ``sapatas_nbr6118.eh_rigida_nbr``, fonte única da expressão.
    """
    return _sap37.eh_rigida_nbr(h_cm, a_cm, ap_cm, b_cm, bp_cm)


@_dataclass37(frozen=True)
class ResultadoClassificacaoBloco:
    """Classificação de bloco sobre estacas em rígido ou flexível (22.7.1)."""

    rigido: bool
    h_cm: float
    h_min_rigidez_cm: float
    classificacao: str
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def classificar_bloco(h_cm: float, a_cm: float, ap_cm: float,
                      b_cm: float | None = None,
                      bp_cm: float | None = None) -> ResultadoClassificacaoBloco:
    """Classifica o bloco em rígido ou flexível (22.7.1, PDF p. 213).

    Mesma expressão de ``eh_rigido_bloco``, com a memória de cálculo e o
    h mínimo de rigidez, h,mín = máx((a − ap)/3, (b − bp)/3). ``ok`` é
    verdadeiro para bloco rígido: é o único caso em que o método de bielas
    e tirantes deste módulo (22.7.2.1) se aplica; para bloco flexível a
    22.7.2.2 pede análise mais completa (distribuição dos esforços nas
    estacas, tirantes, cisalhamento e punção) e a 22.7.4.2 remete aos
    requisitos de lajes e punção (Seções 19 e 20). Comprimentos em cm.
    """
    h = _pos37(h_cm, "h", "22.7.1")
    a = _pos37(a_cm, "a", "22.7.1")
    ap = _pos37(ap_cm, "ap", "22.7.1")
    if ap > a:
        raise nbr.FaixaNormativaError(
            "O pilar não cabe no bloco na direção a (ap > a), 22.7.1."
        )
    h_min = (a - ap) / 3.0
    mem = [f"22.7.1 (critério análogo a 22.6.1): (a − ap)/3 = "
           f"({_f37(a)} − {_f37(ap)})/3 = {_f37(h_min)} cm."]
    if b_cm is not None and bp_cm is not None:
        b = _pos37(b_cm, "b", "22.7.1")
        bp = _pos37(bp_cm, "bp", "22.7.1")
        if bp > b:
            raise nbr.FaixaNormativaError(
                "O pilar não cabe no bloco na direção b (bp > b), 22.7.1."
            )
        h_min = max(h_min, (b - bp) / 3.0)
        mem.append(f"22.7.1: (b − bp)/3 = ({_f37(b)} − {_f37(bp)})/3 = "
                   f"{_f37((b - bp) / 3.0)} cm; h,mín = {_f37(h_min)} cm "
                   "(as duas direções).")
    else:
        mem.append("22.7.1: só a direção a foi informada; a direção b não "
                   "foi conferida.")
    rigido = eh_rigido_bloco(h, a, ap, b_cm, bp_cm)
    if rigido:
        gov = (f"22.7.1: bloco rígido — h = {_f37(h)} cm >= h,mín = "
               f"{_f37(h_min)} cm.")
    else:
        gov = (f"22.7.1: bloco flexível — h = {_f37(h)} cm < h,mín = "
               f"{_f37(h_min)} cm; aplicar 22.7.2.2 e 22.7.4.2 (lajes e "
               "punção, Seções 19 e 20).")
    mem.append(f"Resultado: {gov}")
    return ResultadoClassificacaoBloco(
        rigido=rigido, h_cm=h, h_min_rigidez_cm=h_min,
        classificacao="rigido" if rigido else "flexivel", ok=rigido,
        governante=gov, memoria=tuple(mem),
    )


# --- 22.7.2.1 a — faixa das trações sobre a estaca (PDF p. 213) ----------
def faixa_armadura_estaca_cm(phi_estaca_cm: float) -> float:
    """Largura da faixa de concentração das trações sobre a estaca (22.7.2.1 a, PDF p. 213).

    22.7.2.1 a: no bloco rígido há "trabalho à flexão nas duas direções,
    usualmente simulado por bielas e tirantes, mas com trações
    essencialmente concentradas nas linhas sobre as estacas (reticulado
    definido pelo eixo das estacas, com faixas de largura igual a 1,2 vez
    seu diâmetro)":

        largura da faixa = 1,2 · φ,estaca

    ``phi_estaca_cm`` é o diâmetro da estaca em cm (e o retorno sai em cm,
    na mesma unidade da geometria do módulo). Diâmetro não positivo levanta
    ``FaixaNormativaError``.
    """
    return FATOR_FAIXA_ESTACA * _pos37(phi_estaca_cm, "φ,estaca", "22.7.2.1")


# --- 22.7.4.1.1 — armadura de flexão nas faixas (PDF p. 214) -------------
@_dataclass37(frozen=True)
class ResultadoFaixas85:
    """Concentração da armadura de flexão nas faixas das estacas (22.7.4.1.1)."""

    As_faixas_cm2: float
    As_total_cm2: float
    fracao: float
    fracao_minima: float
    As_minima_nas_faixas_cm2: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_85pct_nas_faixas(As_faixas_cm2: float,
                               As_total_cm2: float) -> ResultadoFaixas85:
    """Mais de 85 % da armadura de flexão nas faixas das estacas (22.7.4.1.1, PDF p. 214).

    22.7.4.1.1: "A armadura de flexão deve ser disposta essencialmente
    (mais de 85 %) nas faixas definidas pelas estacas, considerando o
    equilíbrio com as respectivas bielas."

        As,faixas > 0,85 · As,total

    A desigualdade é **estrita**: 85 % exatos não atendem ("mais de 85 %").
    Áreas em cm², da mesma direção. As faixas são as de 22.7.2.1 a, de
    largura 1,2·φ,estaca (ver ``faixa_armadura_estaca_cm``). As,total não
    positiva, As,faixas negativa ou As,faixas maior que As,total levantam
    ``FaixaNormativaError``.
    """
    total = _pos37(As_total_cm2, "As,total", "22.7.4.1.1")
    faixas = float(As_faixas_cm2)
    if faixas < 0.0:
        raise nbr.FaixaNormativaError(
            "As,faixas não pode ser negativa (22.7.4.1.1)."
        )
    if faixas > total * (1.0 + 1e-12):
        raise nbr.FaixaNormativaError(
            f"As,faixas ({_f37(faixas)} cm²) não pode superar As,total "
            f"({_f37(total)} cm²), 22.7.4.1.1."
        )
    fracao = faixas / total
    minima = FRACAO_MINIMA_ARMADURA_NAS_FAIXAS * total
    ok = faixas > minima * (1.0 + 1e-12)
    mem = [
        f"22.7.4.1.1: As,faixas = {_f37(faixas)} cm² de As,total = "
        f"{_f37(total)} cm² — fração = {_f37(fracao * 100.0)} %.",
        f"22.7.4.1.1: exige-se mais de "
        f"{_f37(FRACAO_MINIMA_ARMADURA_NAS_FAIXAS * 100.0)} % (desigualdade "
        f"estrita): As,faixas > {_f37(minima)} cm².",
    ]
    if ok:
        gov = (f"22.7.4.1.1: {_f37(fracao * 100.0)} % da armadura nas faixas "
               "das estacas — passa (mais de 85 %).")
    else:
        gov = (f"22.7.4.1.1: só {_f37(fracao * 100.0)} % da armadura nas "
               f"faixas das estacas — a norma exige mais de "
               f"{_f37(FRACAO_MINIMA_ARMADURA_NAS_FAIXAS * 100.0)} % "
               f"(As,faixas > {_f37(minima)} cm²).")
    mem.append(f"Resultado: {gov}")
    return ResultadoFaixas85(
        As_faixas_cm2=faixas, As_total_cm2=total, fracao=fracao,
        fracao_minima=FRACAO_MINIMA_ARMADURA_NAS_FAIXAS,
        As_minima_nas_faixas_cm2=minima, ok=ok, governante=gov,
        memoria=tuple(mem),
    )


@_dataclass37(frozen=True)
class ResultadoDetalhamentoFlexaoBloco:
    """Detalhamento da armadura de flexão do bloco rígido (22.7.4.1.1)."""

    faixa_cm: float
    As_faixas_cm2: float
    As_total_cm2: float
    fracao: float
    ok_85pct: bool
    de_face_a_face: bool
    com_gancho_nas_duas_extremidades: bool
    lb_nec_cm: float | None
    comprimento_ancoragem_disponivel_cm: float | None
    ok_ancoragem: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def detalhamento_flexao_bloco(
    As_faixas_cm2: float, As_total_cm2: float, phi_estaca_cm: float,
    lb_nec_cm: float | None = None,
    comprimento_ancoragem_disponivel_cm: float | None = None,
    de_face_a_face: bool = True,
    com_gancho_nas_duas_extremidades: bool = True,
) -> ResultadoDetalhamentoFlexaoBloco:
    """Detalhamento da armadura de flexão do bloco rígido (22.7.4.1.1, PDF p. 214).

    22.7.4.1.1 reúne quatro exigências: a armadura "deve ser disposta
    essencialmente (mais de 85 %) nas faixas definidas pelas estacas,
    considerando o equilíbrio com as respectivas bielas"; "as barras devem
    se estender de face a face do bloco e terminar em gancho nas duas
    extremidades"; "deve-se assegurar a ancoragem das armaduras de cada uma
    dessas faixas, sobre as estacas, medida a partir das faces internas das
    estacas"; e, no caso de estacas tracionadas, a armadura da estaca vai
    ancorada no topo do bloco (ver ``ancoragem_estaca_tracionada``).

    Áreas em cm² (da mesma direção), comprimentos em cm. A faixa de
    22.7.2.1 a (1,2·φ,estaca) sai em ``faixa_cm``. ``lb_nec_cm`` é o
    comprimento de ancoragem necessário da armadura da faixa
    (``ancoragem_nbr6118.comprimento_ancoragem``, 9.4.2.5) e
    ``comprimento_ancoragem_disponivel_cm`` é o disponível **medido a
    partir da face interna da estaca** até a extremidade da barra; sem os
    dois, a ancoragem não é conferida (``ok_ancoragem=True``, e a memória
    registra).
    """
    faixa = faixa_armadura_estaca_cm(phi_estaca_cm)
    r85 = verificar_85pct_nas_faixas(As_faixas_cm2, As_total_cm2)
    mem = [f"22.7.2.1 a: faixa sobre o eixo da estaca = 1,2·φ = "
           f"{_f37(faixa)} cm."]
    mem.extend(r85.memoria[:-1])
    if de_face_a_face:
        mem.append("22.7.4.1.1: barras de face a face do bloco.")
    else:
        mem.append("22.7.4.1.1: as barras têm de se estender de face a face "
                   "do bloco — o detalhamento informado não atende.")
    if com_gancho_nas_duas_extremidades:
        mem.append("22.7.4.1.1: gancho nas duas extremidades das barras "
                   "(pino e ponta reta por 9.4.2.3).")
    else:
        mem.append("22.7.4.1.1: as barras têm de terminar em gancho nas duas "
                   "extremidades — o detalhamento informado não atende.")
    ok_anc = True
    if lb_nec_cm is not None and comprimento_ancoragem_disponivel_cm is not None:
        lb = _pos37(lb_nec_cm, "lb,nec", "22.7.4.1.1")
        disp = float(comprimento_ancoragem_disponivel_cm)
        s = _seg37.verificar_seguranca(
            disp, lb, "l,disponível x lb,nec (faixa, da face interna da estaca)",
            "22.7.4.1.1")
        ok_anc = s.ok
        mem.append(f"22.7.4.1.1: ancoragem sobre a estaca medida a partir da "
                   f"face interna — l,disponível = {_f37(disp)} cm, lb,nec = "
                   f"{_f37(lb)} cm.")
        mem.extend(s.memoria)
    else:
        mem.append("22.7.4.1.1: a ancoragem sobre a estaca (medida a partir "
                   "da face interna) não foi conferida — informe lb,nec e o "
                   "comprimento disponível.")
    ok = r85.ok and de_face_a_face and com_gancho_nas_duas_extremidades and ok_anc
    if not r85.ok:
        gov = r85.governante
    elif not de_face_a_face:
        gov = "22.7.4.1.1: as barras não se estendem de face a face do bloco."
    elif not com_gancho_nas_duas_extremidades:
        gov = "22.7.4.1.1: faltam os ganchos nas duas extremidades das barras."
    elif not ok_anc:
        gov = ("22.7.4.1.1: ancoragem insuficiente sobre a estaca, medida a "
               "partir da face interna.")
    else:
        gov = (f"22.7.4.1.1: {_f37(r85.fracao * 100.0)} % da armadura em "
               f"faixas de {_f37(faixa)} cm, de face a face, com gancho nas "
               "duas extremidades.")
    mem.append(f"Resultado: {gov}")
    return ResultadoDetalhamentoFlexaoBloco(
        faixa_cm=faixa, As_faixas_cm2=r85.As_faixas_cm2,
        As_total_cm2=r85.As_total_cm2, fracao=r85.fracao, ok_85pct=r85.ok,
        de_face_a_face=bool(de_face_a_face),
        com_gancho_nas_duas_extremidades=bool(com_gancho_nas_duas_extremidades),
        lb_nec_cm=None if lb_nec_cm is None else float(lb_nec_cm),
        comprimento_ancoragem_disponivel_cm=(
            None if comprimento_ancoragem_disponivel_cm is None
            else float(comprimento_ancoragem_disponivel_cm)),
        ok_ancoragem=ok_anc, ok=ok, governante=gov, memoria=tuple(mem),
    )


@_dataclass37(frozen=True)
class ResultadoEstacaTracionada:
    """Ancoragem da armadura de estaca tracionada no bloco (22.7.4.1.1)."""

    tracionada: bool
    Rd_tracao_kn: float
    As_estaca_nec_cm2: float
    lb_nec_cm: float
    comprimento_disponivel_cm: float
    estribos_de_transferencia: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def ancoragem_estaca_tracionada(
    Rd_tracao_kn: float, h_cm: float, phi_mm: float, fck_mpa: float,
    cobrimento_cm: float = 3.0, fyk_mpa: float = 500.0,
    tipo_aco: str = "CA-50", boa_aderencia: bool = True,
    com_gancho: bool = False, estribos_de_transferencia: bool = False,
    gama_c: float = GAMA_C, gama_s: float = GAMA_S,
) -> ResultadoEstacaTracionada:
    """Ancoragem da armadura de estaca tracionada no topo do bloco (22.7.4.1.1, PDF p. 214).

    22.7.4.1.1: "No caso de estacas tracionadas, a armadura da estaca deve
    ser ancorada no topo do bloco, conforme ilustra a Figura 22.7.
    Alternativamente, podem ser utilizados estribos que garantam a
    transferência da força de tração até o topo do bloco."

    ``Rd_tracao_kn`` é a força de tração de cálculo na estaca, em kN
    (valor não positivo significa estaca comprimida: a regra não se
    aplica, ``ok=True``). ``h_cm`` é a altura do bloco e ``cobrimento_cm``
    o cobrimento superior, ambos em cm; ``phi_mm`` é a bitola da armadura
    da estaca, em mm; ``fck_mpa`` e ``fyk_mpa`` em MPa. O comprimento
    disponível vai do arranque da armadura da estaca até o topo do bloco,
    descontado o cobrimento superior:

        l,disponível = h − cobrimento superior
        As,estaca    = Rd,tração/fyd
        condição     = l,disponível >= lb,nec   (ou estribos de transferência)

    lb,nec vem de ``ancoragem_nbr6118.comprimento_ancoragem`` (9.4.2.5,
    P21). Com ``estribos_de_transferencia=True``, a alternativa da norma é
    aceita e ``ok`` fica verdadeiro mesmo com l,disponível < lb,nec — a
    memória registra que a transferência foi confiada aos estribos.
    """
    Rd = float(Rd_tracao_kn)
    h = _pos37(h_cm, "h", "22.7.4.1.1")
    cob = float(cobrimento_cm)
    if cob < 0.0:
        raise nbr.FaixaNormativaError(
            "O cobrimento não pode ser negativo (22.7.4.1.1)."
        )
    disponivel = h - cob
    if Rd <= 0.0:
        mem = (f"22.7.4.1.1: Rd,tração = {_f37(Rd)} kN — a estaca não está "
               "tracionada; a ancoragem no topo do bloco não se aplica.",)
        gov = "22.7.4.1.1: estaca não tracionada — regra não aplicável."
        return ResultadoEstacaTracionada(
            tracionada=False, Rd_tracao_kn=Rd, As_estaca_nec_cm2=0.0,
            lb_nec_cm=0.0, comprimento_disponivel_cm=disponivel,
            estribos_de_transferencia=bool(estribos_de_transferencia),
            ok=True, governante=gov, memoria=mem + (f"Resultado: {gov}",),
        )
    fyd_kncm = fyd_kncm2(fyk_mpa, gama_s)
    As_nec = Rd / fyd_kncm
    anc = _anc37.comprimento_ancoragem(
        phi_mm=phi_mm, fck_mpa=fck_mpa, fyk_mpa=fyk_mpa, tipo_aco=tipo_aco,
        boa_aderencia=boa_aderencia, com_gancho=com_gancho,
        gama_c=gama_c, gama_s=gama_s,
    )
    lb = anc.lb_nec_cm
    mem = [
        f"22.7.4.1.1: estaca tracionada com Rd,tração = {_f37(Rd)} kN — a "
        "armadura da estaca deve ser ancorada no topo do bloco (Figura 22.7).",
        f"22.7.4.1.1: As,estaca = Rd,tração/fyd = {_f37(Rd)}/{_f37(fyd_kncm)} "
        f"= {_f37(As_nec)} cm².",
        f"9.4.2.5: lb,nec = {_f37(lb)} cm para φ {_f37(float(phi_mm))} mm, "
        f"C{_f37(float(fck_mpa))}"
        f"{', com gancho' if com_gancho else ', sem gancho'}.",
        f"22.7.4.1.1: l,disponível até o topo do bloco = h − c = {_f37(h)} − "
        f"{_f37(cob)} = {_f37(disponivel)} cm.",
    ]
    s = _seg37.verificar_seguranca(
        disponivel, lb, "l,disponível x lb,nec (estaca tracionada)",
        "22.7.4.1.1")
    mem.extend(s.memoria)
    ok = s.ok or bool(estribos_de_transferencia)
    if s.ok:
        gov = (f"22.7.4.1.1: a armadura da estaca ancora no topo do bloco — "
               f"l,disponível = {_f37(disponivel)} cm >= lb,nec = "
               f"{_f37(lb)} cm.")
    elif estribos_de_transferencia:
        gov = ("22.7.4.1.1: l,disponível < lb,nec, mas a transferência da "
               "força de tração até o topo do bloco é garantida por estribos "
               "(alternativa da própria norma).")
        mem.append(gov)
    else:
        gov = (f"22.7.4.1.1: a armadura da estaca não ancora no topo do bloco "
               f"— l,disponível = {_f37(disponivel)} cm < lb,nec = "
               f"{_f37(lb)} cm; aumentar h ou usar estribos de transferência.")
    mem.append(f"Resultado: {gov}")
    return ResultadoEstacaTracionada(
        tracionada=True, Rd_tracao_kn=Rd, As_estaca_nec_cm2=As_nec,
        lb_nec_cm=lb, comprimento_disponivel_cm=disponivel,
        estribos_de_transferencia=bool(estribos_de_transferencia), ok=ok,
        governante=gov, memoria=tuple(mem),
    )


# --- 22.7.4.1.2 — armadura de distribuição (PDF p. 214) ------------------
def As_distribuicao_bloco_cm2(F_tracao_total_kn: float,
                              fyk_mpa: float = 500.0,
                              gama_s: float = GAMA_S,
                              fracao: float = FRACAO_DISTRIBUICAO_BLOCO) -> float:
    """Malha positiva adicional de distribuição do bloco rígido (22.7.4.1.2, PDF p. 214).

    22.7.4.1.2: "Para controlar a fissuração, deve ser prevista armadura
    positiva adicional, independentemente da armadura principal de flexão,
    em malha uniformemente distribuída em duas direções ortogonais
    correspondente a 20 % do total das forças de tração em cada uma delas."

        As,distribuição = fração · F,tração,total,direção / fyd

    ``F_tracao_total_kn`` é o total das forças de tração **daquela
    direção**, em kN (não a força no pilar): é a resultante dos tirantes do
    reticulado de bielas e tirantes naquela direção. Quando a armadura
    principal daquela direção foi dimensionada a fyd, vale
    F,tração,total = As,principal·fyd, e então As,distribuição =
    0,20·As,principal — que é o que ``As_superior_dir`` calcula. Retorno em
    cm²; fyk em MPa. ``fracao`` fora de (0, 1] levanta
    ``FaixaNormativaError`` (o valor da norma é 0,20).
    """
    F = float(F_tracao_total_kn)
    if F < 0.0:
        raise nbr.FaixaNormativaError(
            "A força de tração total não pode ser negativa (22.7.4.1.2)."
        )
    fr = float(fracao)
    if not 0.0 < fr <= 1.0:
        raise nbr.FaixaNormativaError(
            f"A fração da armadura de distribuição tem de estar em (0, 1]; "
            f"a 22.7.4.1.2 dá 0,20 e foi recebido {_f37(fr)}."
        )
    return fr * F / fyd_kncm2(fyk_mpa, gama_s)


# --- 22.7.4.1.3 — armadura de suspensão (PDF p. 215) ---------------------
@_dataclass37(frozen=True)
class ResultadoSuspensaoBloco:
    """Exigência de armadura de suspensão no bloco (22.7.4.1.3)."""

    fracao_distribuicao: float
    fracao_limite: float
    espacamento_estacas_cm: float
    espacamento_limite_cm: float
    por_distribuicao: bool
    por_espacamento: bool
    exige: bool
    suspensao_prevista: bool
    motivo: str
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def exigir_armadura_suspensao_bloco(
    fracao_esforcos_distribuicao: float, espacamento_estacas_cm: float,
    h_bloco_cm: float, suspensao_prevista: bool = False,
    avisar: bool = True,
) -> ResultadoSuspensaoBloco:
    """Condição de exigência da armadura de suspensão do bloco (22.7.4.1.3, PDF p. 215).

    22.7.4.1.3: "Se for prevista armadura de distribuição para mais de
    25 % dos esforços totais ou se o espaçamento entre estacas for maior
    que três vezes a altura do bloco, deve ser prevista armadura de
    suspensão para a parcela de carga a ser equilibrada."

        exige se  fração da distribuição > 0,25
              ou  espaçamento entre estacas > 3·h,bloco

    As duas desigualdades são estritas: 25 % exatos e espaçamento igual a
    3·h não disparam. ``fracao_esforcos_distribuicao`` é adimensional (0,20
    é o valor de 22.7.4.1.2, que sozinho não dispara);
    ``espacamento_estacas_cm`` e ``h_bloco_cm`` em cm.
    ``suspensao_prevista`` declara se a armadura de suspensão foi prevista;
    ``ok`` é verdadeiro quando ela não é exigida ou quando foi prevista.
    ``avisar=True`` emite ``AvisoNBR6118`` quando é exigida e não foi
    prevista. A norma não dá aqui a fórmula da área: a "parcela de carga a
    ser equilibrada" vem do modelo de bielas e tirantes adotado (neste
    módulo, ``As_suspensao_total`` e ``As_suspensao_5_estacas``, de Blévot
    e da apostila, não da NBR).
    """
    fr = float(fracao_esforcos_distribuicao)
    if fr < 0.0:
        raise nbr.FaixaNormativaError(
            "A fração dos esforços coberta pela armadura de distribuição não "
            "pode ser negativa (22.7.4.1.3)."
        )
    esp = _pos37(espacamento_estacas_cm, "espaçamento entre estacas",
                 "22.7.4.1.3")
    h = _pos37(h_bloco_cm, "h do bloco", "22.7.4.1.3")
    lim_esp = FATOR_ESPACAMENTO_GATILHO_SUSPENSAO * h
    por_dist = fr > FRACAO_DISTRIBUICAO_GATILHO_SUSPENSAO * (1.0 + 1e-12)
    por_esp = esp > lim_esp * (1.0 + 1e-12)
    exige = por_dist or por_esp
    mem = [
        f"22.7.4.1.3: armadura de distribuição para {_f37(fr * 100.0)} % dos "
        f"esforços totais x limite de "
        f"{_f37(FRACAO_DISTRIBUICAO_GATILHO_SUSPENSAO * 100.0)} % "
        f"(estrito): {'dispara' if por_dist else 'não dispara'}.",
        f"22.7.4.1.3: espaçamento entre estacas = {_f37(esp)} cm x 3·h = "
        f"3·{_f37(h)} = {_f37(lim_esp)} cm (estrito): "
        f"{'dispara' if por_esp else 'não dispara'}.",
    ]
    if por_dist and por_esp:
        motivo = ("armadura de distribuição para mais de 25 % dos esforços "
                  "totais e espaçamento entre estacas maior que 3·h")
    elif por_dist:
        motivo = ("armadura de distribuição para mais de 25 % dos esforços "
                  "totais")
    elif por_esp:
        motivo = "espaçamento entre estacas maior que 3·h"
    else:
        motivo = ""
    prevista = bool(suspensao_prevista)
    ok = (not exige) or prevista
    if not exige:
        gov = ("22.7.4.1.3: armadura de suspensão não exigida (nenhuma das "
               "duas condições dispara).")
    elif prevista:
        gov = (f"22.7.4.1.3: armadura de suspensão exigida ({motivo}) e "
               "prevista, para a parcela de carga a ser equilibrada.")
    else:
        gov = (f"22.7.4.1.3: armadura de suspensão exigida ({motivo}) e não "
               "prevista — dimensionar para a parcela de carga a ser "
               "equilibrada.")
    mem.append(f"Resultado: {gov}")
    if avisar and exige and not prevista:
        _warnings37.warn(gov, nbr.AvisoNBR6118, stacklevel=2)
    return ResultadoSuspensaoBloco(
        fracao_distribuicao=fr,
        fracao_limite=FRACAO_DISTRIBUICAO_GATILHO_SUSPENSAO,
        espacamento_estacas_cm=esp, espacamento_limite_cm=lim_esp,
        por_distribuicao=por_dist, por_espacamento=por_esp, exige=exige,
        suspensao_prevista=prevista, motivo=motivo, ok=ok, governante=gov,
        memoria=tuple(mem),
    )


# --- 22.7.4.1.4 — arranque do pilar no bloco (PDF p. 215) ----------------
def altura_arranque_pilar_bloco(
    h_cm: float, lb_nec_cm: float, cobrimento_cm: float = 3.0,
    desconto_dobra_cm: float = 0.0,
):
    """Altura do bloco suficiente para ancorar a armadura de arranque (22.7.4.1.4, PDF p. 215).

    22.7.4.1.4: "O bloco deve ter altura suficiente para permitir a
    ancoragem da armadura de arranque dos pilares." É o mesmo requisito de
    22.6.4.1.2 para a sapata, e por isso delega a
    ``sapatas_nbr6118.altura_arranque_suficiente`` (fonte única da conta),
    citando aqui o item do bloco. Comprimentos em cm; devolve
    ``sapatas_nbr6118.ResultadoAlturaArranque``.
    """
    return _sap37.altura_arranque_suficiente(
        h_cm, lb_nec_cm, cobrimento_cm, desconto_dobra_cm,
        elemento="bloco", item="22.7.4.1.4",
    )


# --- 22.7.4.1.5 — armadura lateral e superior (PDF p. 215) ---------------
@_dataclass37(frozen=True)
class ResultadoArmaduraLateralSuperiorBloco:
    """Armadura lateral e superior do bloco (22.7.4.1.5)."""

    n_estacas: int
    em_linha_unica: bool
    obrigatoria: bool
    As_superior_dir_cm2: float
    Asp_pele_face_cm2: float
    grande_volume: bool
    armaduras_previstas: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def armaduras_lateral_e_superior_bloco(
    n_estacas: int, As_principal_dir_cm2: float,
    As_total_cm2: float | None = None, em_linha_unica: bool | None = None,
    grande_volume: bool = False, armaduras_previstas: bool = True,
    avisar: bool = True,
) -> ResultadoArmaduraLateralSuperiorBloco:
    """Armadura lateral e superior obrigatória em bloco de estacas em linha única (22.7.4.1.5, PDF p. 215).

    22.7.4.1.5: "Em blocos com duas ou mais estacas em uma única linha, é
    obrigatória a colocação de armaduras laterais e superior. Em blocos de
    fundação de grandes volumes, é conveniente a análise da necessidade de
    armaduras complementares."

    ``n_estacas`` é o número de estacas (>= 1). ``em_linha_unica`` diz se
    elas estão alinhadas; sem esse dado, supõe-se linha única só com 2
    estacas — com 3, 4 ou 5 estacas o arranjo usual (triângulo, quadrado,
    quadrado com estaca central) não é de linha única, e quem tiver um
    bloco de 3 ou mais estacas alinhadas passa ``em_linha_unica=True``.

    As áreas saem das funções já existentes do módulo:
    ``As_superior_dir(As_principal_dir_cm2)`` = 0,20·As,principal (a malha
    superior, que coincide com a de distribuição de 22.7.4.1.2) e
    ``Asp_pele_face(As_total_cm2)`` = As,total/8 por face (armadura de
    pele lateral; sem ``As_total_cm2``, usa As,principal da direção).
    Nenhuma das duas é fórmula da NBR — são as da apostila; a norma só
    torna as armaduras obrigatórias. ``armaduras_previstas=False`` com
    obrigatoriedade dá ``ok=False`` e, com ``avisar=True``,
    ``AvisoNBR6118``.
    """
    n = int(n_estacas)
    if n < 1:
        raise nbr.FaixaNormativaError(
            f"O número de estacas tem de ser pelo menos 1 (22.7.4.1.5); "
            f"recebido {n}."
        )
    As_p = float(As_principal_dir_cm2)
    if As_p < 0.0:
        raise nbr.FaixaNormativaError(
            "As,principal não pode ser negativa (22.7.4.1.5)."
        )
    As_tot = As_p if As_total_cm2 is None else float(As_total_cm2)
    if As_tot < 0.0:
        raise nbr.FaixaNormativaError(
            "As,total não pode ser negativa (22.7.4.1.5)."
        )
    linha = (n == 2) if em_linha_unica is None else bool(em_linha_unica)
    obrigatoria = linha and n >= 2
    As_sup = As_superior_dir(As_p)
    As_pele = Asp_pele_face(As_tot)
    mem = [
        f"22.7.4.1.5: bloco com {n} estaca(s), "
        + ("em uma única linha." if linha else "não alinhadas em linha única.")
    ]
    if obrigatoria:
        mem.append("22.7.4.1.5: armaduras laterais e superior obrigatórias "
                   "(duas ou mais estacas em uma única linha).")
    else:
        mem.append("22.7.4.1.5: a obrigatoriedade de armaduras laterais e "
                   "superior não se aplica a este arranjo.")
    mem.append(
        f"Armaduras adotadas (apostila, não da NBR): As,superior por direção "
        f"= 0,20·As,principal = {_f37(As_sup)} cm²; As,pele por face = "
        f"As,total/8 = {_f37(As_pele)} cm²."
    )
    if grande_volume:
        mem.append("22.7.4.1.5: bloco de grande volume — analisar a "
                   "necessidade de armaduras complementares.")
    previstas = bool(armaduras_previstas)
    ok = (not obrigatoria) or previstas
    if not obrigatoria:
        gov = ("22.7.4.1.5: armaduras laterais e superior não obrigatórias "
               "neste arranjo de estacas.")
    elif previstas:
        gov = ("22.7.4.1.5: armaduras laterais e superior obrigatórias e "
               "previstas.")
    else:
        gov = ("22.7.4.1.5: armaduras laterais e superior são obrigatórias em "
               "bloco com duas ou mais estacas em uma única linha e não "
               "foram previstas.")
    mem.append(f"Resultado: {gov}")
    if avisar and obrigatoria and not previstas:
        _warnings37.warn(gov, nbr.AvisoNBR6118, stacklevel=2)
    return ResultadoArmaduraLateralSuperiorBloco(
        n_estacas=n, em_linha_unica=linha, obrigatoria=obrigatoria,
        As_superior_dir_cm2=As_sup, Asp_pele_face_cm2=As_pele,
        grande_volume=bool(grande_volume), armaduras_previstas=previstas,
        ok=ok, governante=gov, memoria=tuple(mem),
    )


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    _demo()
