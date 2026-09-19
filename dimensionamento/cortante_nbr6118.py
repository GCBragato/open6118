"""Forca Cortante - Vigas em Concreto Armado (NBR 6118:2026).

Nome ate 19/09/2026: cortante_bastos.py. O credito as apostilas esta abaixo.

Implementa o dimensionamento da armadura transversal seguindo a apostila
"DIMENSIONAMENTO DE VIGAS DE CONCRETO ARMADO - FORCA CORTANTE" (Mar/2025),
Prof. Paulo Sergio Bastos, UNESP/Bauru, corrigida contra a NBR 6118:2026
(auditoria de 18/09/2026: CRT-01, CRT-02, CRT-03, CRT-08). Grandezas de
material (fct,m, fctd, fcd, fywd) vem de nucleo_nbr6118.

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

Estrutura segue o padrao de vigas_nbr6118.py e lajes_nbr6118.py.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
GAMA_C = nbr.GAMA_C
GAMA_S = nbr.GAMA_S
GAMA_F = nbr.GAMA_F  # Tabela 11.1 — lido do núcleo (P4)

FYWD_MAX_KNCM2 = 43.5    # 435 MPa (NBR 6118 17.4.2.2 b)

ALFA_MIN_DEG = 45.0      # 17.4.1.1.5 - inclinacao dos estribos
ALFA_MAX_DEG = 90.0


# ---------------------------------------------------------------------------
# Helpers de resistencia (legado: delegam ao nucleo_nbr6118)
# ---------------------------------------------------------------------------
def fcd_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fcd em kN/cm2 a partir de fck em MPa (delega ao nucleo, 12.3.3)."""
    return nbr.mpa_para_kncm2(nbr.fcd(fck_mpa, gama_c))


def fctm_mpa(fck_mpa: float) -> float:
    """fct,m, MPa (NBR 6118 8.2.5; delega ao nucleo).

    CRT-01: ate C50, fct,m = 0.3*fck^(2/3); acima disso,
    fct,m = 2.12*ln[1 + 0.1*(fck+8)] (Grupo II). A formula antiga
    (so o ramo do Grupo I) subestimava Vc e superestimava Asw acima de C50.
    """
    return nbr.fct_m(fck_mpa)


def fctd_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fctd = fctk,inf / gama_c, em kN/cm2 (delega ao nucleo)."""
    return nbr.mpa_para_kncm2(nbr.fctd(fck_mpa, gama_c))


def fywd_kncm2(fywk_mpa: float, gama_s: float = GAMA_S,
               estribo: bool = True) -> float:
    """Tensao de calculo da armadura transversal (kN/cm2).
    Limite NBR 6118 17.4.2.2 b): fyd (nucleo) para estribos, 0.7*fyd para
    barras dobradas (sempre <= 435 MPa)."""
    fywd = nbr.fyd(fywk_mpa, gama_s)
    if not estribo:
        fywd = 0.7 * fywd
    fywd = min(fywd, 435.0)
    return nbr.mpa_para_kncm2(fywd)


def alfa_v2(fck_mpa: float) -> float:
    """alpha_v2 = 1 - fck/250 (Eq. 5.15). Delega ao nucleo normativo."""
    return nbr.alpha_v2(fck_mpa)


def _validar_alfa_estribo(alfa_deg: float) -> None:
    """17.4.1.1.5: 45 deg <= alfa <= 90 deg (inclinacao dos estribos)."""
    if not (ALFA_MIN_DEG - 1e-6 <= alfa_deg <= ALFA_MAX_DEG + 1e-6):
        raise ValueError(
            f"alfa deve estar entre 45 e 90 deg (recebido {alfa_deg})."
        )


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
    regime_vc: str = "flexao_simples"  # P15: ramo de Vc (17.4.2.2 b / 17.4.2.3 b)


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
    Nsd_kn: float = 0.0,
    M0_kncm: float | None = None,
    MSd_max_kncm: float | None = None,
    linha_neutra_fora: bool = False,
    h_laje_cm: float | None = None,
) -> ResultadoCortante:
    """Modelo de Calculo I (trelica classica, theta = 45 deg).

    P15: os parâmetros Nsd_kn (compressão positiva), M0_kncm, MSd_max_kncm e
    linha_neutra_fora escolhem o ramo de Vc de 17.4.2.2 b) (ver
    ``vc_por_regime``); h_laje_cm limita fywd pela espessura da laje
    (19.4.2). Com os padrões, o resultado é o de antes (flexão simples).

    Eq. 5.18: VRd2 = 0.27 * v2 * fcd * bw * d
    Eq. 5.20: Vc = Vc0 = 0.6 * fctd * bw * d (flexao simples)
    Eq. 5.25: Asw/s = Vsw / [0.9 * d * fywd * (sin alfa + cos alfa)]

    CRT-03 (17.4.1.1.5): 45 deg <= alfa <= 90 deg, mesma faixa validada em
    modelo_calculo_II.
    """
    _validar_alfa_estribo(alfa_deg)
    fcd = fcd_kncm2(fck_mpa, gama_c)
    fctd = fctd_kncm2(fck_mpa, gama_c)
    fywd = fywd_kncm2(fywk_mpa, gama_s, estribo)
    v2 = alfa_v2(fck_mpa)
    if h_laje_cm is not None:  # P15, 19.4.2
        fywd = min(fywd, fywd_max_laje_mpa(h_laje_cm) / 10.0)

    VRd2 = 0.27 * v2 * fcd * bw_cm * d_cm
    Vc = 0.6 * fctd * bw_cm * d_cm
    Vc, regime_vc = vc_por_regime(Vc, Nsd_kn, M0_kncm, MSd_max_kncm,
                                  linha_neutra_fora, modelo="I")  # P15
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
        regime_vc=regime_vc,
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
    Nsd_kn: float = 0.0,
    M0_kncm: float | None = None,
    MSd_max_kncm: float | None = None,
    linha_neutra_fora: bool = False,
    h_laje_cm: float | None = None,
) -> ResultadoCortante:
    """Modelo de Calculo II (trelica generalizada).

    P15: Nsd_kn, M0_kncm, MSd_max_kncm e linha_neutra_fora escolhem o ramo
    de Vc de 17.4.2.3 b) sobre Vc1 (ver ``vc_por_regime``); h_laje_cm
    limita fywd pela espessura da laje (19.4.2). Com os padrões, o
    resultado é o de antes (flexão simples).

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
    if h_laje_cm is not None:  # P15, 19.4.2
        fywd = min(fywd, fywd_max_laje_mpa(h_laje_cm) / 10.0)

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
    Vc, regime_vc = vc_por_regime(Vc1, Nsd_kn, M0_kncm, MSd_max_kncm,
                                  linha_neutra_fora, modelo="II")  # P15
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
        regime_vc=regime_vc,
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

    CRT-08: as constantes 0.0137/0.023 da apostila embutem
    fct,m = 0.3*fck^(2/3) (Grupo I, 8.2.5). Para o resultado continuar
    identico ate C50 e ficar correto no Grupo II, fck^(2/3) e substituido
    pelo "fck^(2/3) equivalente" nucleo_nbr6118.fct_m(fck)/0.3 (identidade
    para fck <= 50; usa o ramo logaritmico do nucleo acima disso).
    """
    fck23 = nbr.fct_m(fck_mpa) / 0.3
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
        tau_Rd = 0.25 * fctd, com fck limitado a 60 MPa nesta formula
            (CRT-02, 19.4.1; delega a nucleo_nbr6118.tau_Rd)
        k = |1.6 - d| (d em metros, k >= 1) se as barras tracionadas chegam
            ao apoio; senao k = 1.
        rho_l = As1 / (bw*d) <= 0.02
    """
    tau_rd = nbr.mpa_para_kncm2(nbr.tau_Rd(fck_mpa, gama_c))   # kN/cm2
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


# === P15: Força cortante completa (vigas e lajes) ===
#
# Fecha a força cortante de 17.4 e 19.4: exceções à armadura transversal
# mínima (17.4.1.1.2), limite das barras dobradas (17.4.1.1.3), redução de
# VSd junto ao apoio (17.4.1.2.1), componente tangencial da protensão
# (17.4.1.2.2), altura variável (17.4.1.2.3), condição dupla VRd2/VRd3 no
# modo verificação (17.4.2.1), os três ramos de Vc com M0 (17.4.2.2 b e
# 17.4.2.3 b), FSd,cor (17.4.2.2 c), espaçamento para fissuração inclinada
# da alma (17.6), aℓ = 1,5d e fywd máximo em lajes (19.4.1 e 19.4.2).
# As páginas citadas são as do PDF (impressa + 18).
# ---------------------------------------------------------------------------
import warnings as _warnings_p15
from dataclasses import dataclass as _dataclass_p15

try:
    import seguranca_nbr6118 as _seg_p15
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import seguranca_nbr6118 as _seg_p15

FaixaNormativaError = nbr.FaixaNormativaError
AvisoNBR6118 = nbr.AvisoNBR6118


def _fmt_p15(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


# --- 17.4.2.2 b) — M0, momento de descompressão (PDF p. 157-158) -----------
# γf e γp da tensão que M0 anula: constantes locais, nunca o padrão do
# núcleo (plano, seção 8, risco 4).
GAMA_F_M0 = 1.0
GAMA_P_M0 = 0.9


def M0_kncm(P_kn: float, ep_cm: float, N_kn: float, W1_cm3: float,
            Ac_cm2: float) -> float:
    """Momento M0 que anula a compressão na borda tracionada por MSd,máx (17.4.2.2 b), PDF p. 157-158).

    M0 = Pd·(W1/Ac + ep) + NSd·(W1/Ac)

    com Pd = γp·P e NSd = γf·N, sendo γp = 0,9 e γf = 1,0 os valores que a
    norma fixa para esta tensão (``GAMA_P_M0`` e ``GAMA_F_M0``). Por isso a
    função recebe as forças **sem** ponderação:

    - P_kn: força de protensão no tempo considerado, já com todas as perdas
      (kN, positiva);
    - ep_cm: excentricidade do cabo, positiva no sentido da fibra mais
      tracionada por MSd,máx (caso em que a protensão comprime essa borda);
      só os momentos isostáticos de protensão entram aqui — os
      hiperestáticos já estão em MSd,máx;
    - N_kn: forças normais de diversas origens concomitantes com VSd,
      compressão positiva (kN); os momentos dessas forças não entram, pois
      já estão em MSd,máx;
    - W1_cm3: módulo de resistência na fibra mais tracionada (cm³, > 0);
    - Ac_cm2: área de concreto (cm², > 0).

    Devolve M0 em kN·cm. Resultado negativo significa tração na borda: não é
    flexo-compressão, e ``vc_por_regime`` recusa esse M0.
    """
    if W1_cm3 <= 0.0 or Ac_cm2 <= 0.0:
        raise FaixaNormativaError(
            "W1 e Ac têm de ser positivos no cálculo de M0 (17.4.2.2 b)."
        )
    if P_kn < 0.0:
        raise FaixaNormativaError(
            "A força de protensão P entra em M0 como valor positivo (17.4.2.2 b)."
        )
    Pd = GAMA_P_M0 * P_kn
    Nsd = GAMA_F_M0 * N_kn
    return Pd * (W1_cm3 / Ac_cm2 + ep_cm) + Nsd * (W1_cm3 / Ac_cm2)


# --- 17.4.2.2 b) e 17.4.2.3 b) — os três ramos de Vc (PDF p. 157 e 159) ----
def vc_por_regime(Vc_base_kn: float, Nsd_kn: float = 0.0,
                  M0_kncm: float | None = None,
                  MSd_max_kncm: float | None = None,
                  linha_neutra_fora: bool = False,
                  modelo: str = "I") -> tuple[float, str]:
    """Parcela Vc pelo regime de solicitação normal (17.4.2.2 b), PDF p. 157; 17.4.2.3 b), PDF p. 159).

    Vc_base_kn é Vc0 = 0,6·fctd·bw·d no modelo I e Vc1 no modelo II.

    - Vc = 0 nos elementos tracionados com a linha neutra fora da seção
      (Nsd_kn < 0 e linha_neutra_fora=True);
    - Vc = Vc_base na flexão simples (Nsd_kn = 0, sem M0) e na flexo-tração
      com a linha neutra cortando a seção (Nsd_kn < 0);
    - Vc = Vc_base·(1 + M0/MSd,máx) <= 2·Vc_base na flexo-compressão, ramo
      usado sempre que M0_kncm é informado (protensão, compressão ou as
      duas; M0 de ``M0_kncm``). No modelo I a norma escreve "<= 2Vc0"; no
      modelo II, "< 2Vc1". O teto numérico é o mesmo e é aplicado como
      min(..., 2·Vc_base).

    Nsd_kn > 0 (compressão) sem M0: devolve Vc_base (M0 = 0, a favor da
    segurança, pois com compressão M0 > 0) e emite ``AvisoNBR6118``.
    MSd_max_kncm é o momento de cálculo máximo na seção (ou no semitramo,
    conforme 17.4.2.2 b), tomado em módulo e não nulo. Devolve (Vc, regime).
    """
    if Nsd_kn < 0.0 and linha_neutra_fora:
        if M0_kncm is not None:
            raise FaixaNormativaError(
                "Elemento tracionado com a linha neutra fora da seção não é "
                "flexo-compressão: não informe M0 (17.4.2.2 b)."
            )
        return 0.0, "tracao_ln_fora"
    if linha_neutra_fora:
        raise FaixaNormativaError(
            "linha_neutra_fora só se aplica a elemento tracionado (Nsd < 0); "
            "com Nsd >= 0 a seção não fica toda tracionada (17.4.2.2 b)."
        )
    if M0_kncm is not None:
        if MSd_max_kncm is None or abs(MSd_max_kncm) <= 0.0:
            raise FaixaNormativaError(
                "Na flexo-compressão, Vc = Vc0·(1 + M0/MSd,máx) exige MSd,máx "
                "não nulo (17.4.2.2 b)."
            )
        if M0_kncm < 0.0:
            raise FaixaNormativaError(
                f"M0 = {M0_kncm:g} kN·cm negativo: a borda fica tracionada, o "
                "que não é flexo-compressão (17.4.2.2 b)."
            )
        vc = Vc_base_kn * (1.0 + M0_kncm / abs(MSd_max_kncm))
        return min(vc, 2.0 * Vc_base_kn), "flexo_compressao"
    if Nsd_kn > 0.0:
        _warnings_p15.warn(
            f"Modelo {modelo}: flexo-compressão sem M0; adotado Vc = Vc_base "
            "(M0 = 0, a favor da segurança). Informe M0_kncm e MSd_max_kncm "
            "para Vc = Vc_base·(1 + M0/MSd,máx) (17.4.2.2 b).",
            AvisoNBR6118, stacklevel=3,
        )
        return Vc_base_kn, "flexo_compressao_sem_M0"
    if Nsd_kn < 0.0:
        return Vc_base_kn, "flexo_tracao"
    return Vc_base_kn, "flexao_simples"


# --- 19.4.2 — fywd máximo em lajes com armadura transversal (PDF p. 182) --
FYWD_LAJE_H_MIN_CM = 15.0
FYWD_LAJE_H_MAX_CM = 35.0
FYWD_LAJE_MIN_MPA = 250.0
FYWD_LAJE_MAX_MPA = 435.0


def fywd_max_laje_mpa(h_cm: float) -> float:
    """Tensão máxima nos estribos de laje em função da espessura (19.4.2, PDF p. 182).

    - 250 MPa para lajes com espessura até 15 cm;
    - 435 MPa (fywd) para lajes com espessura maior que 35 cm;
    - interpolação linear entre 15 cm e 35 cm, que a norma permite.

    h_cm em cm, positivo. O valor devolvido é um teto: a tensão usada é
    min(fywd, este teto), com fywd de 17.4.2.2 b) (``fywd_laje_kncm2``).
    """
    if h_cm <= 0.0:
        raise FaixaNormativaError("A espessura da laje tem de ser positiva (19.4.2).")
    if h_cm <= FYWD_LAJE_H_MIN_CM:
        return FYWD_LAJE_MIN_MPA
    if h_cm >= FYWD_LAJE_H_MAX_CM:
        return FYWD_LAJE_MAX_MPA
    return FYWD_LAJE_MIN_MPA + (FYWD_LAJE_MAX_MPA - FYWD_LAJE_MIN_MPA) * (
        (h_cm - FYWD_LAJE_H_MIN_CM) / (FYWD_LAJE_H_MAX_CM - FYWD_LAJE_H_MIN_CM))


def fywd_laje_kncm2(fywk_mpa: float, h_cm: float, gama_s: float = GAMA_S,
                    estribo: bool = True) -> float:
    """fywd dos estribos de laje, kN/cm² (19.4.2 sobre 17.4.2.2 b), PDF p. 182 e 157).

    fywd = min(fyd, ou 0,7·fyd em barras dobradas; 435 MPa;
    fywd_max_laje_mpa(h)), convertido de MPa para kN/cm² (÷ 10).
    """
    return min(fywd_kncm2(fywk_mpa, gama_s, estribo),
               fywd_max_laje_mpa(h_cm) / 10.0)


# --- 19.4.1 — aℓ = 1,5d nas lajes sem armadura transversal (PDF p. 182) ---
AL_LAJE_FATOR_D = 1.5


def a_l_laje_cm(d_cm: float) -> float:
    """Decalagem aℓ = 1,5·d na distribuição da armadura longitudinal da laje (19.4.1, PDF p. 182).

    "A distribuição dessa armadura ao longo da laje deve respeitar o
    prescrito em 18.3.2.3.1, considerando para aℓ o valor 1,5d." d em cm.
    """
    if d_cm <= 0.0:
        raise FaixaNormativaError("A altura útil d tem de ser positiva (19.4.1).")
    return AL_LAJE_FATOR_D * d_cm


def sigma_cp_mpa(Nsd_kn: float, Ac_cm2: float) -> float:
    """σcp = NSd/Ac, MPa, compressão positiva (19.4.1, PDF p. 181).

    NSd em kN (força longitudinal devida à protensão ou ao carregamento,
    compressão positiva), Ac em cm²; kN/cm² × 10 = MPa.
    """
    if Ac_cm2 <= 0.0:
        raise FaixaNormativaError("Ac tem de ser positiva no cálculo de σcp (19.4.1).")
    return Nsd_kn / Ac_cm2 * 10.0


# --- 17.4.1.1.2 — exceções à armadura transversal mínima (PDF p. 154) -----
@_dataclass_p15(frozen=True)
class ResultadoRegimeAswMin:
    """Qual regra de armadura transversal mínima vale (17.4.1.1.2)."""

    regime: str            # 'asw_min_17_4_1_1_1', 'laje_19_4',
                           # 'nervura_laje_19_4_1' ou 'asw_min_secao_18'
    dispensa_asw_min_17: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def regime_asw_minima(bw_cm: float, d_cm: float, elemento: str = "viga",
                      predominantemente_comprimido: bool = False,
                      sigma_tracao_max_mpa: float | None = None,
                      fck_mpa: float | None = None,
                      VSd_kn: float | None = None,
                      Vc_kn: float | None = None,
                      VRd1_kn: float | None = None) -> ResultadoRegimeAswMin:
    """Decide se vale a Asw,min de 17.4.1.1.1 ou uma das exceções (17.4.1.1.2, PDF p. 154).

    elemento: 'viga', 'nervura' (nervura de laje nervurada, 13.2.4.2 a e b),
    'pilar' ou 'fundacao' (elemento linear de fundação).

    a) bw > 5·d: tratar como laje (19.4), regime 'laje_19_4'. A condição é
       estrita, como está em 17.4.1.1.2 (bw = 5d continua viga); o título
       de 19.4 diz "bw >= 5d".
    b) nervura: pode ser verificada como laje, com bw = soma das larguras
       das nervuras no trecho; a armadura transversal pode ser dispensada
       quando atendido 19.4.1 (VSd <= VRd1, informados em VSd_kn e VRd1_kn).
       Sem VRd1_kn, o regime é informado e a dispensa fica em aberto (False).
    c) pilar ou fundação predominantemente comprimidos que atendem, na
       combinação mais desfavorável do ELU e com a seção em estádio I, a
       tensão de tração máxima <= fctk (sigma_tracao_max_mpa, tração
       positiva; fctk tomado como fctk,inf de 8.2.5, a favor da segurança)
       e VSd <= Vc (Vc de 17.4.2.2). Nesse caso a armadura mínima é a da
       Seção 18 (regime 'asw_min_secao_18').

    Fora das exceções, regime 'asw_min_17_4_1_1_1' (use asw_min_cm2_por_m).
    """
    if bw_cm <= 0.0 or d_cm <= 0.0:
        raise FaixaNormativaError("bw e d têm de ser positivos (17.4.1.1.2).")
    el = nbr._chave(elemento)
    if el not in ("viga", "nervura", "pilar", "fundacao"):
        raise ValueError(
            f"Elemento '{elemento}' desconhecido: use 'viga', 'nervura', "
            "'pilar' ou 'fundacao' (17.4.1.1.2)."
        )
    mem = [f"17.4.1.1.2: elemento = {elemento}, bw = {_fmt_p15(bw_cm)} cm, "
           f"d = {_fmt_p15(d_cm)} cm, 5d = {_fmt_p15(5.0 * d_cm)} cm."]
    if bw_cm > 5.0 * d_cm:
        mem.append("a) bw > 5d: tratar como laje (19.4); a Asw,min de 17.4.1.1.1 não se aplica.")
        return ResultadoRegimeAswMin("laje_19_4", True, True,
                                     "bw > 5d: laje (19.4)", tuple(mem))
    if el == "nervura":
        if VSd_kn is not None and VRd1_kn is not None:
            dispensa = _seg_p15.verificar_seguranca(VRd1_kn, VSd_kn, "VSd x VRd1",
                                                    "19.4.1").ok
            mem.append(f"b) nervura verificada como laje: VSd = {_fmt_p15(VSd_kn)} kN, "
                       f"VRd1 = {_fmt_p15(VRd1_kn)} kN -> "
                       f"{'dispensa a armadura transversal' if dispensa else 'exige armadura transversal'}.")
        else:
            dispensa = False
            mem.append("b) nervura: pode ser verificada como laje (19.4.1); "
                       "informe VSd e VRd1 para decidir a dispensa.")
        return ResultadoRegimeAswMin("nervura_laje_19_4_1", dispensa, True,
                                     "nervura de laje nervurada (19.4.1)", tuple(mem))
    if el in ("pilar", "fundacao") and predominantemente_comprimido:
        if None in (sigma_tracao_max_mpa, fck_mpa, VSd_kn, Vc_kn):
            raise FaixaNormativaError(
                "17.4.1.1.2 c) exige sigma_tracao_max_mpa, fck_mpa, VSd_kn e Vc_kn."
            )
        fctk = nbr.fctk_inf(fck_mpa)
        ok_sigma = sigma_tracao_max_mpa <= fctk + 1e-9
        ok_v = _seg_p15.verificar_seguranca(Vc_kn, VSd_kn, "VSd x Vc", "17.4.1.1.2").ok
        mem.append(f"c) estádio I: σt,máx = {_fmt_p15(sigma_tracao_max_mpa)} MPa "
                   f"<= fctk = {_fmt_p15(fctk)} MPa -> {'ok' if ok_sigma else 'não ok'}; "
                   f"VSd = {_fmt_p15(VSd_kn)} kN <= Vc = {_fmt_p15(Vc_kn)} kN -> "
                   f"{'ok' if ok_v else 'não ok'}.")
        if ok_sigma and ok_v:
            mem.append("Exceção c) atendida: armadura transversal mínima da Seção 18.")
            return ResultadoRegimeAswMin("asw_min_secao_18", True, True,
                                         "pilar ou fundação comprimido: Seção 18",
                                         tuple(mem))
        mem.append("Exceção c) não atendida: vale a Asw,min de 17.4.1.1.1.")
    else:
        mem.append("Nenhuma exceção: vale a Asw,min de 17.4.1.1.1.")
    return ResultadoRegimeAswMin("asw_min_17_4_1_1_1", False, True,
                                 "Asw,min de 17.4.1.1.1", tuple(mem))


# --- 17.4.1.1.3 — barras dobradas <= 60 % de Vsw (PDF p. 155) --------------
LIMITE_BARRAS_DOBRADAS = 0.60


@_dataclass_p15(frozen=True)
class ResultadoBarrasDobradas:
    """Limite de 60 % da força resistida pela armadura transversal (17.4.1.1.3)."""

    Vsw_dobradas_kn: float
    Vsw_total_kn: float
    limite_kn: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_limite_barras_dobradas(Vsw_dobradas_kn: float,
                                     Vsw_total_kn: float) -> ResultadoBarrasDobradas:
    """Barras dobradas não podem suportar mais que 60 % de Vsw (17.4.1.1.3, PDF p. 155).

    Vsw,dobradas <= 0,6·Vsw,total, com Vsw,total a parcela resistida por toda
    a armadura transversal (estribos + barras dobradas), em kN.
    """
    if Vsw_dobradas_kn < 0.0 or Vsw_total_kn < 0.0:
        raise FaixaNormativaError("As parcelas de Vsw têm de ser não negativas (17.4.1.1.3).")
    if Vsw_dobradas_kn > Vsw_total_kn + 1e-9:
        raise FaixaNormativaError(
            "A parcela das barras dobradas não pode passar de Vsw total (17.4.1.1.3)."
        )
    lim = LIMITE_BARRAS_DOBRADAS * Vsw_total_kn
    s = _seg_p15.verificar_seguranca(lim, Vsw_dobradas_kn, "Vsw,dobradas x 0,6·Vsw",
                                     "17.4.1.1.3")
    mem = (f"17.4.1.1.3: Vsw,dobradas = {_fmt_p15(Vsw_dobradas_kn)} kN <= "
           f"0,6·Vsw = 0,6 × {_fmt_p15(Vsw_total_kn)} = {_fmt_p15(lim)} kN -> "
           f"{'ok' if s.ok else 'não ok'}.",)
    return ResultadoBarrasDobradas(Vsw_dobradas_kn, Vsw_total_kn, lim, s.ok,
                                   "barras dobradas <= 60 % de Vsw" if s.ok
                                   else "barras dobradas > 60 % de Vsw: não passa",
                                   mem)


# --- 17.4.1.2.1 — cargas próximas aos apoios (PDF p. 155) -----------------
def fator_reducao_carga_concentrada(a_cm: float, d_cm: float) -> float:
    """Fator a/(2d) da força cortante de carga concentrada junto ao apoio (17.4.1.2.1 b), PDF p. 155).

    a_cm: distância da carga ao eixo teórico do apoio (cm); d_cm: altura
    útil (cm). Para a <= 2d o fator é a/(2d); para a > 2d não há redução
    (fator 1).
    """
    if a_cm < 0.0 or d_cm <= 0.0:
        raise FaixaNormativaError("a >= 0 e d > 0 em 17.4.1.2.1 b).")
    if a_cm <= 2.0 * d_cm:
        return a_cm / (2.0 * d_cm)
    return 1.0


@_dataclass_p15(frozen=True)
class ResultadoReducaoApoio:
    """VSd junto ao apoio com as reduções de 17.4.1.2.1."""

    VSd_reduzido_kn: float     # para o cálculo da armadura transversal (VRd3)
    VSd_sem_reducao_kn: float  # para a verificação da biela (VRd2)
    x_cm: float
    apoio_direto: bool
    memoria: tuple[str, ...]


def VSd_reduzido_apoio(d_cm: float, V_face_distribuida_kn: float = 0.0,
                       q_kn_por_cm: float = 0.0, x_cm: float = 0.0,
                       cargas_concentradas: tuple = (),
                       V_cabos_inclinados_kn: float = 0.0,
                       apoio_direto: bool = True) -> ResultadoReducaoApoio:
    """VSd reduzido para cargas próximas aos apoios (17.4.1.2.1, PDF p. 155).

    Vale só no apoio direto (carga e reação em faces opostas, comprimindo o
    elemento); no apoio indireto as reduções não são permitidas. Não vale
    para a verificação da biela (VRd2): por isso o resultado traz também o
    VSd sem redução.

    Em módulo, com a seção entre o apoio e as cargas:

    a) carga distribuída: entre o apoio e a seção a d/2 da face, a força
       cortante pode ser tomada constante e igual à dessa seção:
       V_dist(x) = V_face − q·max(x, d/2), com x medido da face (cm),
       V_face em kN e q em kN/cm;
    b) carga concentrada a uma distância a <= 2d do eixo teórico do apoio:
       no trecho de comprimento a, a força cortante que ela provoca é
       multiplicada por a/(2d). ``cargas_concentradas`` é uma sequência de
       pares (V_kn, a_cm), com V a parcela da força cortante na seção
       devida àquela carga;
    c) cabos inclinados de protensão: a parcela V_cabos_inclinados_kn não
       é reduzida.

    Devolve ``ResultadoReducaoApoio`` com VSd reduzido (para Asw) e sem
    redução (para VRd2).
    """
    if d_cm <= 0.0 or x_cm < 0.0 or q_kn_por_cm < 0.0:
        raise FaixaNormativaError("d > 0, x >= 0 e q >= 0 em 17.4.1.2.1.")
    mem = [f"17.4.1.2.1: d = {_fmt_p15(d_cm)} cm, seção a x = {_fmt_p15(x_cm)} cm "
           f"da face, apoio {'direto' if apoio_direto else 'indireto'}."]
    v_dist = V_face_distribuida_kn - q_kn_por_cm * x_cm
    v_conc = sum(float(v) for v, _a in cargas_concentradas)
    v_sem = v_dist + v_conc + V_cabos_inclinados_kn
    if not apoio_direto:
        mem.append("Apoio indireto: reduções não permitidas; VSd = "
                   f"{_fmt_p15(v_sem)} kN.")
        return ResultadoReducaoApoio(v_sem, v_sem, x_cm, False, tuple(mem))
    x_red = max(x_cm, d_cm / 2.0)
    v_dist_red = V_face_distribuida_kn - q_kn_por_cm * x_red
    mem.append(f"a) carga distribuída: V = V_face − q·max(x, d/2) = "
               f"{_fmt_p15(V_face_distribuida_kn)} − {_fmt_p15(q_kn_por_cm)} × "
               f"{_fmt_p15(x_red)} = {_fmt_p15(v_dist_red)} kN.")
    v_conc_red = 0.0
    for v, a in cargas_concentradas:
        if a < x_cm:
            raise FaixaNormativaError(
                f"Carga concentrada em a = {a:g} cm antes da seção x = {x_cm:g} cm: "
                "a redução vale no trecho entre o apoio e a carga (17.4.1.2.1 b)."
            )
        f = fator_reducao_carga_concentrada(a, d_cm)
        v_conc_red += f * float(v)
        mem.append(f"b) carga concentrada: V = {_fmt_p15(v)} kN, a = {_fmt_p15(a)} cm, "
                   f"fator a/(2d) = {_fmt_p15(f)} -> {_fmt_p15(f * v)} kN.")
    if V_cabos_inclinados_kn:
        mem.append(f"Cabos inclinados de protensão: {_fmt_p15(V_cabos_inclinados_kn)} kN, "
                   "sem redução.")
    v_red = v_dist_red + v_conc_red + V_cabos_inclinados_kn
    mem.append(f"VSd reduzido (armadura transversal) = {_fmt_p15(v_red)} kN; "
               f"VSd sem redução (biela, VRd2) = {_fmt_p15(v_sem)} kN.")
    return ResultadoReducaoApoio(v_red, v_sem, x_cm, True, tuple(mem))


# --- 17.4.1.2.2 — componente tangencial da protensão (PDF p. 155) ---------
@_dataclass_p15(frozen=True)
class ResultadoProtensaoTangencial:
    """Condição Ap·fpyd + As·fyd >= VSd (17.4.1.2.2)."""

    VSd_kn: float
    resistencia_kn: float
    exigida: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_protensao_tangencial(VSd_kn: float, Ap_cm2: float, As_cm2: float,
                                   fpyk_mpa: float, fyk_mpa: float = 500.0,
                                   efeito_favoravel: bool = True,
                                   gama_s: float = GAMA_S) -> ResultadoProtensaoTangencial:
    """Armadura de tração junto à face tracionada quando a protensão alivia VSd (17.4.1.2.2, PDF p. 155).

    VSd já deve incluir a projeção da força de protensão na sua direção, com
    o valor de cálculo no tempo considerado. Quando esse efeito é favorável
    (efeito_favoravel=True), a armadura longitudinal de tração junto à face
    tracionada por flexão deve satisfazer:

        Ap·fpyd + As·fyd >= VSd

    com fpyd = fpyk/γs e fyd = fyk/γs (MPa; cm² × MPa ÷ 10 = kN). Quando o
    efeito não é favorável, a condição não é exigida (ok=True).
    """
    if min(Ap_cm2, As_cm2) < 0.0:
        raise FaixaNormativaError("Ap e As têm de ser não negativas (17.4.1.2.2).")
    fpyd = fpyk_mpa / gama_s
    fyd = nbr.fyd(fyk_mpa, gama_s)
    r = (Ap_cm2 * fpyd + As_cm2 * fyd) / 10.0
    mem = [f"17.4.1.2.2: Ap·fpyd + As·fyd = ({_fmt_p15(Ap_cm2)} × {_fmt_p15(fpyd)} + "
           f"{_fmt_p15(As_cm2)} × {_fmt_p15(fyd)})/10 = {_fmt_p15(r)} kN; "
           f"VSd = {_fmt_p15(VSd_kn)} kN."]
    if not efeito_favoravel:
        mem.append("Efeito da protensão desfavorável: condição não exigida.")
        return ResultadoProtensaoTangencial(VSd_kn, r, False, True,
                                            "condição não exigida", tuple(mem))
    s = _seg_p15.verificar_seguranca(r, abs(VSd_kn), "Ap·fpyd + As·fyd x VSd",
                                     "17.4.1.2.2")
    mem.extend(s.memoria)
    return ResultadoProtensaoTangencial(VSd_kn, r, True, s.ok,
                                        "Ap·fpyd + As·fyd >= VSd" if s.ok
                                        else "Ap·fpyd + As·fyd < VSd: não passa",
                                        tuple(mem))


# --- 17.4.1.2.3 — elementos com altura variável (PDF p. 155-156) ----------
def VSd_red_altura_variavel(VSd_kn: float, MSd_kncm: float, z_cm: float,
                            beta_c_graus: float, beta_t_graus: float,
                            theta_deg: float = 45.0) -> float:
    """|VSd,red| resistida pela alma em vigas de altura variável (17.4.1.2.3, PDF p. 155-156).

    |VSd| − |VSd,red| = [|MSd/z| − |VSd,red|·(cotg θ)/2]·tg βc
                      + [|MSd/z| + |VSd,red|·(cotg θ)/2]·tg βt

    A equação é linear em |VSd,red|; isolando:

    |VSd,red| = (|VSd| − |MSd/z|·(tg βc + tg βt))
                / (1 + (cotg θ/2)·(tg βt − tg βc))

    βc: ângulo entre o banzo comprimido e o eixo; βt: ângulo entre a
    armadura de tração e o eixo, em graus, com os sinais obtidos pelo
    sentido das forças finais de compressão e de tração da flexão com a
    força cortante concomitante (positivo quando a componente alivia a
    alma). θ: inclinação das bielas (30° a 45°). z: braço de alavanca (cm).
    VSd em kN, MSd em kN·cm. Com βc = βt = 0, |VSd,red| = |VSd|.
    """
    if not (30.0 - 1e-6 <= theta_deg <= 45.0 + 1e-6):
        raise FaixaNormativaError(f"θ = {theta_deg:g}° fora de 30° a 45° (17.4.1.2.3).")
    if z_cm <= 0.0:
        raise FaixaNormativaError("z tem de ser positivo (17.4.1.2.3).")
    for b in (beta_c_graus, beta_t_graus):
        if not (-90.0 < b < 90.0):
            raise FaixaNormativaError(f"β = {b:g}° fora de (−90°, 90°) (17.4.1.2.3).")
    tc = math.tan(math.radians(beta_c_graus))
    tt = math.tan(math.radians(beta_t_graus))
    cot_t = 1.0 / math.tan(math.radians(theta_deg))
    fz = abs(MSd_kncm / z_cm)
    den = 1.0 + cot_t / 2.0 * (tt - tc)
    if den <= 0.0:
        raise FaixaNormativaError(
            "Combinação de βc, βt e θ sem solução em 17.4.1.2.3 (denominador <= 0)."
        )
    v_red = (abs(VSd_kn) - fz * (tc + tt)) / den
    if v_red < 0.0:
        raise FaixaNormativaError(
            f"|VSd,red| = {v_red:g} kN negativo: as componentes dos banzos superam "
            "VSd; confira os sinais de βc e βt (17.4.1.2.3)."
        )
    return v_red


# --- 17.4.2.2 c) — força de tração decalada, forma direta (PDF p. 158) ----
def FSd_cor_kn(MSd_kncm: float, z_cm: float, VSd_kn: float, a_l_cm: float,
               d_cm: float, MSd_max_kncm: float, z_max_cm: float) -> float:
    """Força de tração no banzo tracionado com a decalagem (17.4.2.2 c), PDF p. 158; vale no modelo II, 17.4.2.3 c).

    FSd,cor = MSd/z + |VSd|·aℓ/d <= MSd,máx/z_máx

    MSd em kN·cm (em módulo); z, aℓ, d e z_máx em cm; VSd em kN. MSd,máx é o
    momento de cálculo máximo no trecho em análise e z_máx o braço
    correspondente. Alternativa ao deslocamento do diagrama de momentos
    (``decalagem_modelo_I/II`` em viga_servico_nbr6118). Devolve kN.
    """
    if min(z_cm, d_cm, z_max_cm) <= 0.0 or a_l_cm < 0.0:
        raise FaixaNormativaError("z, d e z_máx positivos e aℓ >= 0 (17.4.2.2 c).")
    f = abs(MSd_kncm) / z_cm + abs(VSd_kn) * a_l_cm / d_cm
    return min(f, abs(MSd_max_kncm) / z_max_cm)


# --- 17.6 — fissuração inclinada da alma (PDF p. 164) ---------------------
S_MAX_FISSURACAO_ALMA_CM = 15.0


def verificar_espacamento_fissuracao_alma(s_cm: float,
                                          caso_especial: bool = True) -> bool:
    """s <= 15 cm quando a fissuração inclinada da alma importa (17.6, PDF p. 164).

    "Usualmente, não é necessário verificar"; nos casos especiais
    (caso_especial=True), o espaçamento da armadura transversal fica limitado
    a 15 cm. Com caso_especial=False, devolve True (sem exigência).
    """
    if s_cm <= 0.0:
        raise FaixaNormativaError("O espaçamento s tem de ser positivo (17.6).")
    if not caso_especial:
        return True
    return s_cm <= S_MAX_FISSURACAO_ALMA_CM + 1e-9


# --- 17.4.2.1 — condição dupla VRd2 e VRd3 no modo verificação (PDF p. 156)
@_dataclass_p15(frozen=True)
class ResultadoVerificacaoCortante:
    """Verificação de seção com Asw existente (17.4.2.1)."""

    modelo: str
    theta_deg: float
    alfa_deg: float
    VSd_kn: float
    VRd2_kn: float
    Vc_kn: float
    Vsw_kn: float
    VRd3_kn: float
    Asw_cm2_por_m: float
    Asw_min_cm2_por_m: float
    fywd_kncm2: float
    regime_vc: str
    ok_VRd2: bool
    ok_VRd3: bool
    ok_asw_min: bool
    ok_espacamento_alma: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_cortante(Asw_cm2_por_m: float, VSd_kn: float, bw_cm: float,
                       d_cm: float, fck_mpa: float, modelo: str = "I",
                       theta_deg: float | None = None,
                       fywk_mpa: float = 500.0, alfa_deg: float = 90.0,
                       estribo: bool = True, gama_c: float = GAMA_C,
                       gama_s: float = GAMA_S, Nsd_kn: float = 0.0,
                       M0_kncm: float | None = None,
                       MSd_max_kncm: float | None = None,
                       linha_neutra_fora: bool = False,
                       h_laje_cm: float | None = None,
                       verificar_asw_min: bool = True,
                       s_cm: float | None = None,
                       controle_fissuracao_alma: bool = False,
                       ) -> ResultadoVerificacaoCortante:
    """Verifica a seção com Asw existente: VSd <= VRd2 e VSd <= VRd3 = Vc + Vsw (17.4.2.1, PDF p. 156).

    Modelo I (17.4.2.2, θ = 45°, PDF p. 156-157):
        VRd2 = 0,27·αv2·fcd·bw·d
        Vsw = (Asw/s)·0,9·d·fywd·(sen α + cos α)
    Modelo II (17.4.2.3, 30° <= θ <= 45°, padrão θ = 30°, PDF p. 158-159):
        VRd2 = 0,54·αv2·fcd·bw·d·sen²θ·(cotg α + cotg θ)
        Vsw = (Asw/s)·0,9·d·fywd·(cotg α + cotg θ)·sen α
    Vc pelo ramo de ``vc_por_regime`` (Vc0 no modelo I; Vc1 no II, que
    depende de VSd). Asw_cm2_por_m em cm²/m (Asw/s = valor/100 em cm²/cm),
    bw e d em cm, VSd em kN, fck e fywk em MPa.

    Extras: com verificar_asw_min (padrão), exige Asw >= Asw,min de
    17.4.1.1.1; h_laje_cm limita fywd pela espessura da laje (19.4.2);
    com controle_fissuracao_alma e s_cm, exige s <= 15 cm (17.6).
    As comparações Rd >= Sd passam por seguranca_nbr6118.verificar_seguranca.
    """
    mod = str(modelo).strip().upper()
    if mod not in ("I", "II"):
        raise ValueError("modelo tem de ser 'I' ou 'II' (17.4.2.2 e 17.4.2.3).")
    if Asw_cm2_por_m < 0.0:
        raise FaixaNormativaError("Asw tem de ser não negativa (17.4.2.1).")
    if mod == "I":
        if theta_deg is not None and abs(theta_deg - 45.0) > 1e-6:
            raise FaixaNormativaError("O modelo I admite só θ = 45° (17.4.2.2).")
        r = modelo_calculo_I(VSd_kn, bw_cm, d_cm, fck_mpa, fywk_mpa, alfa_deg,
                             estribo, gama_c, gama_s, Nsd_kn, M0_kncm,
                             MSd_max_kncm, linha_neutra_fora, h_laje_cm)
        a = math.radians(alfa_deg)
        fator = math.sin(a) + math.cos(a)
        th = 45.0
        f_txt = "(sen α + cos α)"
    else:
        th = 30.0 if theta_deg is None else theta_deg
        r = modelo_calculo_II(VSd_kn, bw_cm, d_cm, fck_mpa, th, fywk_mpa,
                              alfa_deg, estribo, gama_c, gama_s, Nsd_kn,
                              M0_kncm, MSd_max_kncm, linha_neutra_fora,
                              h_laje_cm)
        a = math.radians(alfa_deg)
        cot_a = 0.0 if abs(alfa_deg - 90.0) < 1e-12 else 1.0 / math.tan(a)
        fator = (cot_a + 1.0 / math.tan(math.radians(th))) * math.sin(a)
        f_txt = "(cotg α + cotg θ)·sen α"
    fywd = fywd_kncm2(fywk_mpa, gama_s, estribo)
    if h_laje_cm is not None:
        fywd = min(fywd, fywd_max_laje_mpa(h_laje_cm) / 10.0)
    Vsw = Asw_cm2_por_m / 100.0 * 0.9 * d_cm * fywd * fator
    VRd3 = r.Vc + Vsw
    s2 = _seg_p15.verificar_seguranca(r.VRd2, VSd_kn, "VSd x VRd2", "17.4.2.1")
    s3 = _seg_p15.verificar_seguranca(VRd3, VSd_kn, "VSd x VRd3", "17.4.2.1")
    ok_min = (not verificar_asw_min) or Asw_cm2_por_m >= r.Asw_min_m - 1e-9
    ok_s = True
    if controle_fissuracao_alma:
        if s_cm is None:
            raise FaixaNormativaError("Informe s_cm para o controle de 17.6.")
        ok_s = verificar_espacamento_fissuracao_alma(s_cm, True)
    mem = [
        f"17.4.2.1, modelo {mod}: θ = {_fmt_p15(th)}°, α = {_fmt_p15(alfa_deg)}°, "
        f"bw = {_fmt_p15(bw_cm)} cm, d = {_fmt_p15(d_cm)} cm, fck = {_fmt_p15(fck_mpa)} MPa.",
        f"VRd2 = {_fmt_p15(r.VRd2)} kN.",
        f"Vc ({r.regime_vc}) = {_fmt_p15(r.Vc)} kN.",
        f"Vsw = (Asw/s)·0,9·d·fywd·{f_txt} = {_fmt_p15(Asw_cm2_por_m / 100.0)} × 0,9 × "
        f"{_fmt_p15(d_cm)} × {_fmt_p15(fywd)} × {_fmt_p15(fator)} = {_fmt_p15(Vsw)} kN.",
        f"VRd3 = Vc + Vsw = {_fmt_p15(VRd3)} kN.",
        *s2.memoria, *s3.memoria,
    ]
    if verificar_asw_min:
        mem.append(f"17.4.1.1.1: Asw = {_fmt_p15(Asw_cm2_por_m)} cm²/m >= Asw,min = "
                   f"{_fmt_p15(r.Asw_min_m)} cm²/m -> {'ok' if ok_min else 'não ok'}.")
    if controle_fissuracao_alma:
        mem.append(f"17.6: s = {_fmt_p15(s_cm)} cm <= 15 cm -> {'ok' if ok_s else 'não ok'}.")
    falhas = []
    if not s2.ok:
        falhas.append("VSd > VRd2 (biela)")
    if not s3.ok:
        falhas.append("VSd > VRd3 (tração diagonal)")
    if not ok_min:
        falhas.append("Asw < Asw,min")
    if not ok_s:
        falhas.append("s > 15 cm (17.6)")
    ok = not falhas
    if ok:
        governante = ("VRd2" if r.VRd2 <= VRd3 else "VRd3") + ": ok"
    else:
        governante = "; ".join(falhas)
    return ResultadoVerificacaoCortante(
        mod, th, alfa_deg, VSd_kn, r.VRd2, r.Vc, Vsw, VRd3, Asw_cm2_por_m,
        r.Asw_min_m, fywd, r.regime_vc, s2.ok, s3.ok, ok_min, ok_s, ok,
        governante, tuple(mem))


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    _demo()
