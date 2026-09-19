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


def projetar_bloco(
    n_estacas: int, Nk_kn: float, e_cm: float, ap_cm: float, bp_cm: float,
    phi_e_cm: float, h_cm: float, fck_mpa: float,
    fyk_mpa: float = 500.0, KR: float = 0.95,
    gama_f: float = GAMA_F, gama_c: float = GAMA_C,
    gama_s: float = GAMA_S, cobrimento_cm: float = 3.0,
) -> ResultadoBloco:
    """Projeta bloco sobre 2, 3 ou 4 estacas, método das bielas (Blévot).

    ok_bielas usa os limites de Blévot -- o critério que este módulo
    adota (decisão 2 do plano de correção / achado FUN-01). fcd1/fcd3 e
    razao_pil_fcd1/razao_est_fcd3 trazem, lado a lado, a verificação
    equivalente da NBR 22.3.2, só como informação: não mudam ok_bielas.
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


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    _demo()
