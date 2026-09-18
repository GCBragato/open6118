"""Forca Cortante - Vigas em Concreto Armado (NBR 6118:2023).

Implementa o dimensionamento da armadura transversal seguindo a apostila
"DIMENSIONAMENTO DE VIGAS DE CONCRETO ARMADO - FORCA CORTANTE" (Mar/2025),
Prof. Paulo Sergio Bastos, UNESP/Bauru.

Casos cobertos:
    - Modelo de Calculo I (trelica classica de Ritter-Morsch, theta = 45 deg)
        - Verificacao da diagonal comprimida (VRd2)
        - Calculo da armadura transversal (Asw/s)
    - Modelo de Calculo II (trelica generalizada, 30 deg <= theta <= 45 deg)
        - VRd2 e Asw/s com Vc reduzido (Vc1)
    - Equacoes simplificadas (item 5.11 da apostila, Tabelas 5.2 e 5.3)
    - Armadura minima (Asw,min) item 5.10
    - Verificacao de laje sem armadura para forca cortante (NBR 19.4.1)

Convencoes:
    - fck, fyk em MPa (entrada).
    - bw, d em cm. VSd, VRd em kN. Asw em cm2/m.
    - fcd, fctd, fywd internamente em kN/cm2.
    - Estribos verticais (alfa = 90 deg) por padrao.
    - fywd <= 435 MPa = 43.5 kN/cm2 (limite NBR para CA-50/CA-60).

Estrutura segue o padrao de vigas_bastos.py e lajes_bastos.py.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
GAMA_C = 1.4
GAMA_S = 1.15
GAMA_F = 1.4

FYWD_MAX_KNCM2 = 43.5    # 435 MPa (NBR 6118 17.4.2.2)


# ---------------------------------------------------------------------------
# Helpers de resistencia
# ---------------------------------------------------------------------------
def fcd_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fcd em kN/cm2 a partir de fck em MPa."""
    return (fck_mpa / gama_c) * 0.1


def fctm_mpa(fck_mpa: float) -> float:
    """fct,m = 0.3 * fck^(2/3), MPa (NBR 6118 8.2.5, Grupo I)."""
    return 0.3 * fck_mpa ** (2.0 / 3.0)


def fctd_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fctd = 0.7 * fct,m / gama_c, em kN/cm2."""
    return 0.7 * fctm_mpa(fck_mpa) / gama_c * 0.1


def fywd_kncm2(fywk_mpa: float, gama_s: float = GAMA_S,
               estribo: bool = True) -> float:
    """Tensao de calculo da armadura transversal (kN/cm2).
    Limite NBR 6118: 435 MPa para estribos, 0.7*fyd para barras dobradas
    (sempre <= 435 MPa)."""
    fywd = fywk_mpa / gama_s
    if not estribo:
        fywd = 0.7 * fywd
    fywd = min(fywd, 435.0)
    return fywd * 0.1


def alfa_v2(fck_mpa: float) -> float:
    """alpha_v2 = 1 - fck/250 (Eq. 5.15)."""
    return 1.0 - fck_mpa / 250.0


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------
@dataclass
class ResultadoCortante:
    modelo: str             # "I", "II" ou "simplificada-I"/"simplificada-II"
    theta_deg: float        # angulo das bielas (45 ou 30..45)
    alfa_deg: float         # angulo dos estribos (geralmente 90)
    bw: float               # cm
    d: float                # cm
    fck: float              # MPa
    fywk: float             # MPa
    VSd: float              # kN

    VRd2: float             # kN
    Vc: float               # kN
    Vsw: float              # kN
    Asw_s: float            # cm2/cm (Asw por unidade de comprimento)
    Asw_m: float            # cm2/m
    Asw_min_m: float        # cm2/m
    VSd_min: float = 0.0    # kN (forca cortante limite para armadura minima)
    Asw_adotada: float = 0.0  # max(Asw_m, Asw_min_m)
    ok_bielas: bool = True  # True se VSd <= VRd2
    erro: str = ""


# ---------------------------------------------------------------------------
# Armadura minima (item 5.10)
# ---------------------------------------------------------------------------
def asw_min_cm2_por_m(bw_cm: float, fck_mpa: float, fywk_mpa: float = 500.0,
                     alfa_deg: float = 90.0) -> float:
    """Armadura transversal minima Asw,min (cm2/m). Eq. 5.45-5.46.

    rho_sw,min = 0.2 * fct,m / fywk
    Asw,min/s = rho_sw,min * bw * sin(alfa); para s = 100 cm e fct,m em
    kN/cm2, resulta Asw,min = 20 * fct,m * bw / fywk (alfa = 90 deg).
    """
    fctm_kncm2 = fctm_mpa(fck_mpa) * 0.1
    fywk_kncm2 = fywk_mpa * 0.1
    return (20.0 * fctm_kncm2 * bw_cm / fywk_kncm2
            * math.sin(math.radians(alfa_deg)))


# ---------------------------------------------------------------------------
# Modelo de Calculo I (theta = 45 deg)
# ---------------------------------------------------------------------------
def modelo_calculo_I(
    VSd_kn: float,
    bw_cm: float,
    d_cm: float,
    fck_mpa: float,
    fywk_mpa: float = 500.0,
    alfa_deg: float = 90.0,
    estribo: bool = True,
    gama_c: float = GAMA_C,
    gama_s: float = GAMA_S,
) -> ResultadoCortante:
    """Modelo de Calculo I (trelica classica, theta = 45 deg).

    Eq. 5.18: VRd2 = 0.27 * v2 * fcd * bw * d
    Eq. 5.20: Vc = Vc0 = 0.6 * fctd * bw * d (flexao simples)
    Eq. 5.25: Asw/s = Vsw / [0.9 * d * fywd * (sin alfa + cos alfa)]
    """
    fcd = fcd_kncm2(fck_mpa, gama_c)
    fctd = fctd_kncm2(fck_mpa, gama_c)
    fywd = fywd_kncm2(fywk_mpa, gama_s, estribo)
    v2 = alfa_v2(fck_mpa)

    VRd2 = 0.27 * v2 * fcd * bw_cm * d_cm
    Vc = 0.6 * fctd * bw_cm * d_cm
    Vsw = max(0.0, VSd_kn - Vc)

    alfa_rad = math.radians(alfa_deg)
    asw_s = Vsw / (0.9 * d_cm * fywd
                   * (math.sin(alfa_rad) + math.cos(alfa_rad)))
    asw_m = asw_s * 100.0

    asw_min_m = asw_min_cm2_por_m(bw_cm, fck_mpa, fywk_mpa, alfa_deg)
    VSd_min = Vc + asw_min_m / 100.0 * 0.9 * d_cm * fywd \
        * (math.sin(alfa_rad) + math.cos(alfa_rad))

    return ResultadoCortante(
        modelo="I",
        theta_deg=45.0,
        alfa_deg=alfa_deg,
        bw=bw_cm,
        d=d_cm,
        fck=fck_mpa,
        fywk=fywk_mpa,
        VSd=VSd_kn,
        VRd2=VRd2,
        Vc=Vc,
        Vsw=Vsw,
        Asw_s=asw_s,
        Asw_m=asw_m,
        Asw_min_m=asw_min_m,
        VSd_min=VSd_min,
        Asw_adotada=max(asw_m, asw_min_m),
        ok_bielas=VSd_kn <= VRd2,
        erro="" if VSd_kn <= VRd2 else f"VSd={VSd_kn:.1f} > VRd2={VRd2:.1f}",
    )


# ---------------------------------------------------------------------------
# Modelo de Calculo II (30 deg <= theta <= 45 deg)
# ---------------------------------------------------------------------------
def modelo_calculo_II(
    VSd_kn: float,
    bw_cm: float,
    d_cm: float,
    fck_mpa: float,
    theta_deg: float = 30.0,
    fywk_mpa: float = 500.0,
    alfa_deg: float = 90.0,
    estribo: bool = True,
    gama_c: float = GAMA_C,
    gama_s: float = GAMA_S,
) -> ResultadoCortante:
    """Modelo de Calculo II (trelica generalizada).

    Eq. 5.30: VRd2 = 0.54 * v2 * fcd * bw * d * sin^2(theta)
                     * (cot alfa + cot theta)
    Eq. 5.34: Vc1 = Vc0 * (VRd2 - VSd) / (VRd2 - Vc0) se VSd > Vc0;
              Vc1 = Vc0 se VSd <= Vc0.
    Eq. 5.35: Asw/s = Vsw /
              [0.9 * d * fywd * (cot alfa + cot theta) * sin alfa]
    """
    if not (30.0 - 1e-6 <= theta_deg <= 45.0 + 1e-6):
        raise ValueError(f"theta deve estar entre 30 e 45 deg (recebido {theta_deg}).")
    if not (45.0 - 1e-6 <= alfa_deg <= 90.0 + 1e-6):
        raise ValueError(f"alfa deve estar entre 45 e 90 deg (recebido {alfa_deg}).")

    fcd = fcd_kncm2(fck_mpa, gama_c)
    fctd = fctd_kncm2(fck_mpa, gama_c)
    fywd = fywd_kncm2(fywk_mpa, gama_s, estribo)
    v2 = alfa_v2(fck_mpa)

    theta_rad = math.radians(theta_deg)
    alfa_rad = math.radians(alfa_deg)
    sin_t = math.sin(theta_rad)
    cot_t = 1.0 / math.tan(theta_rad)
    cot_a = 1.0 / math.tan(alfa_rad) if abs(math.tan(alfa_rad)) > 1e-12 else 0.0

    VRd2 = 0.54 * v2 * fcd * bw_cm * d_cm * sin_t * sin_t * (cot_a + cot_t)
    Vc0 = 0.6 * fctd * bw_cm * d_cm

    if VSd_kn <= Vc0:
        Vc1 = Vc0
    elif VSd_kn >= VRd2:
        Vc1 = 0.0
    else:
        Vc1 = Vc0 * (VRd2 - VSd_kn) / (VRd2 - Vc0)
    Vc = Vc1
    Vsw = max(0.0, VSd_kn - Vc)

    asw_s = Vsw / (0.9 * d_cm * fywd * (cot_a + cot_t) * math.sin(alfa_rad))
    asw_m = asw_s * 100.0

    asw_min_m = asw_min_cm2_por_m(bw_cm, fck_mpa, fywk_mpa, alfa_deg)

    return ResultadoCortante(
        modelo="II",
        theta_deg=theta_deg,
        alfa_deg=alfa_deg,
        bw=bw_cm,
        d=d_cm,
        fck=fck_mpa,
        fywk=fywk_mpa,
        VSd=VSd_kn,
        VRd2=VRd2,
        Vc=Vc,
        Vsw=Vsw,
        Asw_s=asw_s,
        Asw_m=asw_m,
        Asw_min_m=asw_min_m,
        VSd_min=Vc0 + 0.0,  # quando VSd=Vc0 a armadura ainda e minima
        Asw_adotada=max(asw_m, asw_min_m),
        ok_bielas=VSd_kn <= VRd2,
        erro="" if VSd_kn <= VRd2 else f"VSd={VSd_kn:.1f} > VRd2={VRd2:.1f}",
    )


# ---------------------------------------------------------------------------
# Equacoes simplificadas (item 5.11)
# ---------------------------------------------------------------------------
def simplificada_modelo_I(
    VSd_kn: float, bw_cm: float, d_cm: float, fck_mpa: float,
) -> ResultadoCortante:
    """Equacoes simplificadas Modelo I (estribos verticais, CA-50/60).

    Eq. 5.47:  VRd2 = 0.027 * (1 - fck/250) * fcd * bw * d   (kN, fcd em MPa)
                     com fcd = fck/gama_c
    Eq. 5.57:  VSd,min = 0.0137 * bw * d * fck^(2/3)
    Eq. 5.59:  Asw = 2.55 * VSd / d - 0.023 * bw * fck^(2/3)   (cm2/m)
    """
    fck23 = fck_mpa ** (2.0 / 3.0)
    fcd_mpa = fck_mpa / GAMA_C
    VRd2 = 0.027 * (1.0 - fck_mpa / 250.0) * fcd_mpa * bw_cm * d_cm
    VSd_min = 0.0137 * bw_cm * d_cm * fck23
    if VSd_kn <= VSd_min:
        asw_m = 0.0  # cobre-se com armadura minima
    else:
        asw_m = 2.55 * VSd_kn / d_cm - 0.023 * bw_cm * fck23
    asw_min_m = asw_min_cm2_por_m(bw_cm, fck_mpa)
    return ResultadoCortante(
        modelo="simplificada-I",
        theta_deg=45.0,
        alfa_deg=90.0,
        bw=bw_cm,
        d=d_cm,
        fck=fck_mpa,
        fywk=500.0,
        VSd=VSd_kn,
        VRd2=VRd2,
        Vc=0.6 * fctd_kncm2(fck_mpa) * bw_cm * d_cm,
        Vsw=max(0.0, VSd_kn - 0.6 * fctd_kncm2(fck_mpa) * bw_cm * d_cm),
        Asw_s=asw_m / 100.0,
        Asw_m=asw_m,
        Asw_min_m=asw_min_m,
        VSd_min=VSd_min,
        Asw_adotada=max(asw_m, asw_min_m),
        ok_bielas=VSd_kn <= VRd2,
    )


def simplificada_modelo_II(
    VSd_kn: float, bw_cm: float, d_cm: float, fck_mpa: float,
    theta_deg: float = 30.0,
) -> ResultadoCortante:
    """VRd2 simplificado para o Modelo II (estribos verticais).

    Tabela 5.3 (apostila): VRd2 = 0.054 * (1 - fck/250) * fcd * bw * d
                                  * sin theta * cos theta
    com fcd = fck/gama_c em MPa.
    """
    sin_t = math.sin(math.radians(theta_deg))
    cos_t = math.cos(math.radians(theta_deg))
    fcd_mpa = fck_mpa / GAMA_C
    VRd2 = 0.054 * (1.0 - fck_mpa / 250.0) * fcd_mpa * bw_cm * d_cm \
        * sin_t * cos_t
    return _swap_vrd2_modelo_II(VSd_kn, bw_cm, d_cm, fck_mpa, theta_deg, VRd2)


def _swap_vrd2_modelo_II(VSd_kn, bw_cm, d_cm, fck_mpa, theta_deg, VRd2):
    """Helper: roda o Modelo II teorico e substitui VRd2 pela versao
    simplificada (e recalcula Vc1/Vsw em funcao do novo VRd2)."""
    base = modelo_calculo_II(VSd_kn, bw_cm, d_cm, fck_mpa, theta_deg)
    Vc0 = 0.6 * fctd_kncm2(fck_mpa) * bw_cm * d_cm
    if VSd_kn <= Vc0:
        Vc1 = Vc0
    elif VSd_kn >= VRd2:
        Vc1 = 0.0
    else:
        Vc1 = Vc0 * (VRd2 - VSd_kn) / (VRd2 - Vc0)
    Vsw = max(0.0, VSd_kn - Vc1)
    fywd = fywd_kncm2(500.0)
    theta_rad = math.radians(theta_deg)
    cot_t = 1.0 / math.tan(theta_rad)
    asw_s = Vsw / (0.9 * d_cm * fywd * cot_t)
    base.modelo = "simplificada-II"
    base.VRd2 = VRd2
    base.Vc = Vc1
    base.Vsw = Vsw
    base.Asw_s = asw_s
    base.Asw_m = asw_s * 100.0
    base.Asw_adotada = max(base.Asw_m, base.Asw_min_m)
    base.ok_bielas = VSd_kn <= VRd2
    return base


# ---------------------------------------------------------------------------
# Lajes / elementos lineares com bw > 5d (NBR 19.4.1)
# ---------------------------------------------------------------------------
def laje_sem_armadura(
    VSd_kn: float, bw_cm: float, d_cm: float, fck_mpa: float,
    rho_l: float = 0.0, sigma_cp_mpa: float = 0.0, k_imp: bool = True,
    gama_c: float = GAMA_C,
) -> dict:
    """Verifica laje sem armadura para forca cortante (NBR 6118 19.4.1).

    VRd1 = [tau_Rd * k * (1.2 + 40 * rho_l) + 0.15 * sigma_cp] * bw * d
    com:
        tau_Rd = 0.25 * fctd
        k = |1.6 - d| (d em metros, k >= 1) se as barras tracionadas chegam
            ao apoio; senao k = 1.
        rho_l = As1 / (bw*d) <= 0.02
    """
    fctd = fctd_kncm2(fck_mpa, gama_c)         # kN/cm2
    tau_rd = 0.25 * fctd                       # kN/cm2
    if k_imp:
        k = max(1.0, 1.6 - d_cm / 100.0)
    else:
        k = 1.0
    rho_l = min(rho_l, 0.02)
    sigma_cp = sigma_cp_mpa * 0.1              # kN/cm2
    VRd1 = (tau_rd * k * (1.2 + 40.0 * rho_l) + 0.15 * sigma_cp) \
        * bw_cm * d_cm
    return {
        "VRd1_kN": VRd1,
        "VSd_kN": VSd_kn,
        "tau_Rd_kNcm2": tau_rd,
        "k": k,
        "rho_l": rho_l,
        "ok": VSd_kn <= VRd1,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def _aprox(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def test_exemplo_5_15_modeloI() -> None:
    """Apostila 5.15.1.1 - Modelo I, C25, b=14, d=46, VSd=153 kN."""
    r = modelo_calculo_I(VSd_kn=153.0, bw_cm=14.0, d_cm=46.0, fck_mpa=25.0)
    assert _aprox(r.VRd2, 279.5, 0.5), f"VRd2={r.VRd2:.2f}"
    assert _aprox(r.Vc, 49.6, 0.3), f"Vc={r.Vc:.2f}"
    assert _aprox(r.Vsw, 103.4, 0.5), f"Vsw={r.Vsw:.2f}"
    assert _aprox(r.Asw_m, 5.73, 0.05), f"Asw={r.Asw_m:.3f}"
    print(f"  OK  Modelo I  VRd2={r.VRd2:.1f} Vc={r.Vc:.1f} "
          f"Vsw={r.Vsw:.1f} Asw={r.Asw_m:.2f} cm2/m")


def test_exemplo_5_15_modeloII_30() -> None:
    """Apostila 5.15.1.2 - Modelo II theta=30, mesma viga."""
    r = modelo_calculo_II(VSd_kn=153.0, bw_cm=14.0, d_cm=46.0, fck_mpa=25.0,
                          theta_deg=30.0)
    assert _aprox(r.VRd2, 242.0, 0.5), f"VRd2={r.VRd2:.2f}"
    assert _aprox(r.Vc, 22.9, 0.5), f"Vc={r.Vc:.2f}"
    assert _aprox(r.Vsw, 130.0, 0.5), f"Vsw={r.Vsw:.2f}"
    assert _aprox(r.Asw_m, 4.17, 0.05), f"Asw={r.Asw_m:.3f}"
    print(f"  OK  Modelo II VRd2={r.VRd2:.1f} Vc={r.Vc:.1f} "
          f"Vsw={r.Vsw:.1f} Asw={r.Asw_m:.2f} cm2/m")


def test_exemplo_5_15_simplificada_I() -> None:
    """Apostila 5.15.2.1 - Simplificada I, C25."""
    r = simplificada_modelo_I(VSd_kn=153.0, bw_cm=14.0, d_cm=46.0, fck_mpa=25.0)
    # Tabela: VRd2 = 0.43 bw d = 276.9 kN (coef arredondado); formula
    # exata Eq. 5.47 da 279.45 kN. Tolerancia cobre o arredondamento.
    assert _aprox(r.VRd2, 277.0, 3.0), f"VRd2={r.VRd2:.2f}"
    assert _aprox(r.VSd_min, 75.3, 0.5), f"VSd,min={r.VSd_min:.2f}"
    # Asw = 2.55 . 153 / 46 + 0.20 . 14 = 8.48 + 2.8? -- apostila usa 0.20
    # mas a forma generica e 0.023 . bw . fck^(2/3) = 0.023*14*25^(2/3)
    # = 0.023*14*8.55 = 2.75 -> Asw = 5.73 (apostila tabela arredonda 0.20)
    assert _aprox(r.Asw_m, 5.68, 0.15), f"Asw={r.Asw_m:.3f}"
    print(f"  OK  Simpl. I  VRd2={r.VRd2:.1f} VSd,min={r.VSd_min:.1f} "
          f"Asw={r.Asw_m:.2f} cm2/m")


def test_exemplo_5_15_simplificada_II_30() -> None:
    """Apostila 5.15.2.2 - Simplificada II theta=30, C25."""
    r = simplificada_modelo_II(VSd_kn=153.0, bw_cm=14.0, d_cm=46.0,
                               fck_mpa=25.0, theta_deg=30.0)
    # Tabela: VRd2 = 0.87 bw d sin30 cos30 = 242.6 kN
    assert _aprox(r.VRd2, 242.6, 1.0), f"VRd2={r.VRd2:.2f}"
    print(f"  OK  Simpl. II VRd2={r.VRd2:.1f} Vsw={r.Vsw:.1f} "
          f"Asw={r.Asw_m:.2f} cm2/m")


def test_armadura_minima_C25_b14() -> None:
    """Apostila: Asw,min = 20 * 0.256 * 14 / 50 = 1.43 cm2/m (CA-50)."""
    asw_min = asw_min_cm2_por_m(bw_cm=14.0, fck_mpa=25.0, fywk_mpa=500.0)
    assert _aprox(asw_min, 1.44, 0.05), f"Asw,min={asw_min:.3f}"
    print(f"  OK  Asw,min(C25,b=14) = {asw_min:.2f} cm2/m")


def test_v2_alfa_v2() -> None:
    """alpha_v2 = 1 - fck/250."""
    assert _aprox(alfa_v2(25.0), 0.90, 1e-6)
    assert _aprox(alfa_v2(50.0), 0.80, 1e-6)
    print("  OK  alfa_v2(C25)=0.90, alfa_v2(C50)=0.80")


def test_VRd2_consistencia_simpl_vs_teorica() -> None:
    """A simplificada (Eq. 5.47) e a teorica (Eq. 5.18) coincidem.
    0.27 * v2 * fcd[kN/cm2] * bw * d == 0.027 * v2 * fcd[MPa] * bw * d
    pois fcd[MPa] = 10 * fcd[kN/cm2]."""
    fck = 25.0
    bw, d = 14.0, 46.0
    teorica = 0.27 * (1.0 - fck / 250.0) * fcd_kncm2(fck) * bw * d
    simpl = 0.027 * (1.0 - fck / 250.0) * (fck / GAMA_C) * bw * d
    assert _aprox(teorica, simpl, 0.1), f"teor={teorica:.2f} simpl={simpl:.2f}"
    print(f"  OK  VRd2 teorica={teorica:.2f}  simpl={simpl:.2f}")


def test_laje_sem_armadura() -> None:
    """Laje C25, b=100, d=10, rho_l=0.005, sem protensao."""
    r = laje_sem_armadura(
        VSd_kn=15.0, bw_cm=100.0, d_cm=10.0, fck_mpa=25.0, rho_l=0.005,
    )
    # fct,m = 0.3*25^(2/3) = 2.565 MPa; fctd = 0.7*2.565/1.4 = 1.283 MPa
    # tau_Rd = 0.25 * fctd = 0.32 MPa = 0.032 kN/cm2
    # k = 1.6 - 0.10 = 1.5; rho fator = 1.2 + 40*0.005 = 1.4
    # VRd1 = 0.032 * 1.5 * 1.4 * 100 * 10 = 67.3 kN
    assert _aprox(r["VRd1_kN"], 67.3, 0.5), f"VRd1={r['VRd1_kN']:.2f}"
    print(f"  OK  Laje sem armadura: VRd1={r['VRd1_kN']:.1f} kN  ok={r['ok']}")


def run_tests() -> int:
    tests = [
        test_v2_alfa_v2,
        test_armadura_minima_C25_b14,
        test_exemplo_5_15_modeloI,
        test_exemplo_5_15_modeloII_30,
        test_exemplo_5_15_simplificada_I,
        test_exemplo_5_15_simplificada_II_30,
        test_VRd2_consistencia_simpl_vs_teorica,
        test_laje_sem_armadura,
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
    print("=== Exemplo 5.15 (apostila Bastos) ===")
    print("Viga C25, bw=14 cm, d=46 cm, VSd=153.0 kN, estribos verticais\n")
    for fn, label in [
        (lambda: modelo_calculo_I(153.0, 14.0, 46.0, 25.0), "Modelo I"),
        (lambda: modelo_calculo_II(153.0, 14.0, 46.0, 25.0, 30.0),
         "Modelo II (theta=30)"),
        (lambda: simplificada_modelo_I(153.0, 14.0, 46.0, 25.0),
         "Simplificada I"),
        (lambda: simplificada_modelo_II(153.0, 14.0, 46.0, 25.0, 30.0),
         "Simplificada II"),
    ]:
        r = fn()
        print(f"{label}:")
        print(f"  VRd2 = {r.VRd2:.1f} kN  (ok={r.ok_bielas})")
        print(f"  Vc   = {r.Vc:.1f} kN")
        print(f"  Vsw  = {r.Vsw:.1f} kN")
        print(f"  Asw  = {r.Asw_m:.2f} cm2/m  "
              f"(Asw,min = {r.Asw_min_m:.2f} cm2/m)")
        print()


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    _demo()
