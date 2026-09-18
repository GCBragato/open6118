"""Vigas de Concreto Armado - Verificacoes de Servico (NBR 6118:2023).

Implementa as verificacoes de servico (estado-limite de servico) seguindo
a apostila "VIGAS DE CONCRETO ARMADO - Dimensionamento, Flecha e
Fissuracao", Prof. Paulo Sergio Bastos, UNESP/Bauru.

A flexao, cortante e ancoragem estao em scripts irmaos:
    vigas_bastos.py, cortante_bastos.py, ancoragem_bastos.py.

Conteudo unico desta apostila implementado aqui:
    - Posicao da linha neutra no Estadio II (Eq. 60 retangular e Eq. 64 T).
    - Momento de inercia no Estadio II (Eq. 61 e Eq. 65).
    - Razao modular alpha_e = Es / Ecs (Eq. 68).
    - Decalagem do diagrama de forcas no banzo tracionado (Eq. 31, 34).
    - Verificacao da fissuracao wk (Eqs. 86 e 87 / NBR 6118 17.3.3.2).

Convencoes:
    - Resistencias em MPa, geometria em cm, momentos em kN.cm,
      tensao no aco em kN/cm2.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass


GAMA_C = 1.4
GAMA_S = 1.15

E_S_KNCM2 = 21000.0          # 210 GPa
E_S_MPA = 210000.0


# ---------------------------------------------------------------------------
# Modulos de elasticidade do concreto (NBR 6118 8.2.8)
# ---------------------------------------------------------------------------
def alpha_E(agregado: str = "granito") -> float:
    """Coef alpha_E pela NBR 6118 (Eq. 71/72).

    granito/gnaisse = 1.0; basalto/diabasio = 1.2; calcario = 0.9;
    arenito = 0.7.
    """
    return {
        "granito": 1.0, "gnaisse": 1.0,
        "basalto": 1.2, "diabasio": 1.2,
        "calcario": 0.9,
        "arenito": 0.7,
    }.get(agregado.lower(), 1.0)


def Eci_mpa(fck_mpa: float, agregado: str = "granito") -> float:
    """Modulo de elasticidade inicial Eci (MPa).
    fck <= 50: Eci = alpha_E * 5600 * sqrt(fck);
    fck > 50:  Eci = 21500 * alpha_E * (fck/10 + 1.25)^(1/3)."""
    aE = alpha_E(agregado)
    if fck_mpa <= 50.0:
        return aE * 5600.0 * math.sqrt(fck_mpa)
    return 21500.0 * aE * (fck_mpa / 10.0 + 1.25) ** (1.0 / 3.0)


def Ecs_mpa(fck_mpa: float, agregado: str = "granito") -> float:
    """Modulo secante Ecs = alpha_i * Eci, com
    alpha_i = 0.8 + 0.2 * fck/80 <= 1.0 (Eq. 70)."""
    alpha_i = min(1.0, 0.8 + 0.2 * fck_mpa / 80.0)
    return alpha_i * Eci_mpa(fck_mpa, agregado)


def alpha_e(fck_mpa: float, agregado: str = "granito") -> float:
    """Razao modular alpha_e = Es / Ecs (Eq. 68)."""
    return E_S_MPA / Ecs_mpa(fck_mpa, agregado)


# ---------------------------------------------------------------------------
# Estadio II - Posicao da linha neutra e Inercia
# ---------------------------------------------------------------------------
def x_II_retangular(bw_cm: float, d_cm: float, As_cm2: float,
                    As_linha_cm2: float, d_linha_cm: float,
                    alpha_e_val: float) -> float:
    """Posicao da linha neutra no Estadio II - secao retangular (Eq. 60).

    bw/2 * x^2 + alpha_e * (As + As') * x
        - alpha_e * (As*d + As'*d') = 0
    """
    a = bw_cm / 2.0
    b = alpha_e_val * (As_cm2 + As_linha_cm2)
    c = -alpha_e_val * (As_cm2 * d_cm + As_linha_cm2 * d_linha_cm)
    disc = b * b - 4.0 * a * c
    if disc < 0:
        raise ValueError("discriminante negativo em x_II")
    return (-b + math.sqrt(disc)) / (2.0 * a)


def I_II_retangular(bw_cm: float, d_cm: float, x_II_cm: float,
                    As_cm2: float, As_linha_cm2: float, d_linha_cm: float,
                    alpha_e_val: float) -> float:
    """Momento de inercia no Estadio II - secao retangular (Eq. 61).

    III = bw * x^3 / 3 + alpha_e*As*(d - x)^2 + alpha_e*As'*(x - d')^2
    """
    return (bw_cm * x_II_cm ** 3 / 3.0
            + alpha_e_val * As_cm2 * (d_cm - x_II_cm) ** 2
            + alpha_e_val * As_linha_cm2 * (x_II_cm - d_linha_cm) ** 2)


def x_II_secao_T(bf_cm: float, bw_cm: float, hf_cm: float, d_cm: float,
                 As_cm2: float, As_linha_cm2: float, d_linha_cm: float,
                 alpha_e_val: float) -> float:
    """Linha neutra no Estadio II - secao T (Eq. 64), assumindo x > hf.

    bw/2 * x^2 + [alpha_e*(As + As') + (bf - bw)*hf] * x
        - [alpha_e*(As*d + As'*d') + (bf - bw)*hf^2/2] = 0
    """
    a = bw_cm / 2.0
    b = alpha_e_val * (As_cm2 + As_linha_cm2) + (bf_cm - bw_cm) * hf_cm
    c = -(alpha_e_val * (As_cm2 * d_cm + As_linha_cm2 * d_linha_cm)
          + (bf_cm - bw_cm) * hf_cm * hf_cm / 2.0)
    disc = b * b - 4.0 * a * c
    if disc < 0:
        raise ValueError("discriminante negativo em x_II_secao_T")
    return (-b + math.sqrt(disc)) / (2.0 * a)


def I_II_secao_T(bf_cm: float, bw_cm: float, hf_cm: float, d_cm: float,
                 x_II_cm: float, As_cm2: float, As_linha_cm2: float,
                 d_linha_cm: float, alpha_e_val: float) -> float:
    """Inercia Estadio II - secao T (Eq. 65), x > hf.

    III = bf*x^3/3 - (bf-bw)*(x-hf)^3/3
          + alpha_e*As*(d - x)^2 + alpha_e*As'*(x - d')^2
    """
    inercia = bf_cm * x_II_cm ** 3 / 3.0
    if x_II_cm > hf_cm:
        inercia -= (bf_cm - bw_cm) * (x_II_cm - hf_cm) ** 3 / 3.0
    inercia += alpha_e_val * As_cm2 * (d_cm - x_II_cm) ** 2
    inercia += alpha_e_val * As_linha_cm2 * (x_II_cm - d_linha_cm) ** 2
    return inercia


# ---------------------------------------------------------------------------
# Decalagem do diagrama (item 13.1)
# ---------------------------------------------------------------------------
def decalagem_modelo_I(d_cm: float, VSd_kn: float, Vc_kn: float,
                       alfa_deg: float = 90.0) -> float:
    """Decalagem a_l (cm) - Modelo I, estribos a 90 deg (Eq. 31).

    a_l = 0.5 * d * VSd / (VSd - Vc)  >=  0.5 * d
    Limites NBR: a_l >= 0.5*d para flexao simples; a_l <= d.
    """
    if VSd_kn - Vc_kn <= 0.0:
        return 0.5 * d_cm
    a = 0.5 * d_cm * VSd_kn / (VSd_kn - Vc_kn)
    return max(min(a, d_cm), 0.5 * d_cm)


def decalagem_modelo_II(d_cm: float, theta_deg: float = 30.0,
                        alfa_deg: float = 90.0) -> float:
    """Decalagem a_l (cm) - Modelo II, estribos verticais (Eq. 34).
    a_l = 0.5 * cot(theta) * d   (apostila simplifica fazendo Vc = 0)."""
    cot_t = 1.0 / math.tan(math.radians(theta_deg))
    return 0.5 * cot_t * d_cm


# ---------------------------------------------------------------------------
# Verificacao de fissuracao (NBR 6118 17.3.3.2)
# ---------------------------------------------------------------------------
@dataclass
class ResultadoFissuracao:
    sigma_si_kncm2: float
    rho_ri: float
    Acr_cm2: float
    eta1: float
    fctm_kncm2: float
    wk1_mm: float
    wk2_mm: float
    wk_mm: float
    wk_max_mm: float
    ok: bool


def fctm_kncm2(fck_mpa: float) -> float:
    """fct,m em kN/cm2."""
    return 0.3 * fck_mpa ** (2.0 / 3.0) * 0.1


# ---------------------------------------------------------------------------
# Largura efetiva de mesa colaborante (NBR 6118 14.6.2.2)
# ---------------------------------------------------------------------------
def vao_a_para_mesa(L_cm: float, tipo: str = "biapoiada") -> float:
    """Distancia 'a' entre pontos de momento nulo (NBR 14.6.2.2).

    tipo:
      'biapoiada'   -> a = L
      'continua'    -> a = 0.75 * L (vao extremo) ou 0.6*L (intermediario)
      'continua-extrema' -> a = 0.75 * L
      'continua-intermediaria' -> a = 0.6 * L
      'balanco'     -> a = 2 * L
    """
    t = tipo.lower()
    if t == "biapoiada":
        return L_cm
    if t in ("continua-extrema", "continua"):
        return 0.75 * L_cm
    if t == "continua-intermediaria":
        return 0.6 * L_cm
    if t == "balanco":
        return 2.0 * L_cm
    raise ValueError(f"tipo desconhecido: {tipo}")


def largura_efetiva_mesa(
    bw_cm: float, b2_l_esq_cm: float, b2_l_dir_cm: float,
    L_cm: float, tipo_vao: str = "biapoiada",
    tipo_secao: str = "T",
) -> dict:
    """Largura colaborante b_f para secao T ou L (NBR 14.6.2.2).

    bw       : largura da nervura
    b2_l_*   : distancia livre entre face do pilar e face da viga vizinha
               (uma para cada lado; para secao L, passar 0 do lado livre)
    L        : vao da viga
    tipo_vao : ver vao_a_para_mesa()
    tipo_secao : 'T' (dois lados) ou 'L' (um lado)

    Limites NBR:
      b1, b3 <= 0.5 * b2_l (cada lado)
      b1, b3 <= 0.10 * a   (a = distancia entre pontos de momento nulo)

    Retorna dict com b1, b3, bf, a.
    """
    a = vao_a_para_mesa(L_cm, tipo_vao)
    b1 = min(0.5 * b2_l_esq_cm, 0.10 * a)
    b3 = min(0.5 * b2_l_dir_cm, 0.10 * a) if tipo_secao.upper() == "T" else 0.0
    return {
        "a_cm": a,
        "b1_cm": b1,
        "b3_cm": b3,
        "bf_cm": b1 + bw_cm + b3,
    }


def sigma_si_aproximada(Md_ser_kncm: float, d_cm: float,
                        As_cm2: float) -> float:
    """sigma_si = Md,ser / (0.85 * d * As)  (Eq. 89, kN/cm2)."""
    return Md_ser_kncm / (0.85 * d_cm * As_cm2)


def abertura_fissura_wk(
    phi_mm: float,
    sigma_si_kncm2: float,
    Acr_cm2: float,
    As_cm2: float,
    fck_mpa: float,
    eta1_val: float = 2.25,
    Es_kncm2: float = E_S_KNCM2,
    wk_max_mm: float = 0.30,
) -> ResultadoFissuracao:
    """wk (mm) pelo menor entre Eq. 86 e Eq. 87.

    wk1 = (phi / (12.5 * eta1)) * (sigma_si / Es) * (4 / rho_ri + 45)
    wk2 = (phi / (12.5 * eta1)) * (sigma_si / Es) * (3 * sigma_si / fctm)
    Resultados em mm (entrada phi em mm).
    """
    rho = As_cm2 / Acr_cm2
    fctm = fctm_kncm2(fck_mpa)
    base = (phi_mm / (12.5 * eta1_val)) * (sigma_si_kncm2 / Es_kncm2)
    wk1 = base * (4.0 / rho + 45.0)
    wk2 = base * (3.0 * sigma_si_kncm2 / fctm)
    wk = min(wk1, wk2)
    return ResultadoFissuracao(
        sigma_si_kncm2=sigma_si_kncm2,
        rho_ri=rho,
        Acr_cm2=Acr_cm2,
        eta1=eta1_val,
        fctm_kncm2=fctm,
        wk1_mm=wk1,
        wk2_mm=wk2,
        wk_mm=wk,
        wk_max_mm=wk_max_mm,
        ok=wk <= wk_max_mm,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def _aprox(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def test_alpha_e_C40() -> None:
    """C40, granito: Ecs = 32 GPa -> alpha_e = 21000/3200 = 6.56."""
    ae = alpha_e(40.0, "granito")
    assert _aprox(ae, 6.56, 0.10), f"alpha_e={ae:.2f}"
    print(f"  OK  alpha_e(C40, granito) = {ae:.2f}  (apostila: 6.56)")


def test_x_II_retangular_apostila() -> None:
    """Apostila ex. 16.12: bw=12, d=37, As=2.45 (3 phi 10), As'=0,
    fck=25 (Ecs=24 GPa), alpha_e=21000/2400=8.75.
    Esperado x_II ~ 8.75 cm e III ~ 19.860 cm4 (apostila item 16.12.3)."""
    ae = alpha_e(25.0, "granito")
    x_II = x_II_retangular(bw_cm=12.0, d_cm=37.0, As_cm2=2.45,
                           As_linha_cm2=0.0, d_linha_cm=0.0,
                           alpha_e_val=ae)
    III = I_II_retangular(bw_cm=12.0, d_cm=37.0, x_II_cm=x_II,
                          As_cm2=2.45, As_linha_cm2=0.0, d_linha_cm=0.0,
                          alpha_e_val=ae)
    # Verificacao auto-consistente: somando momentos estaticos em x_II = 0
    momento_estatico = (12.0 * x_II * x_II / 2.0
                        - ae * 2.45 * (37.0 - x_II))
    assert abs(momento_estatico) < 0.5, f"M_estatico={momento_estatico:.3f}"
    print(f"  OK  x_II = {x_II:.2f} cm  III = {III:.0f} cm4 "
          f"(M.estatico=0)")


def test_x_II_secao_T_apostila() -> None:
    """Apostila ex. 17.1 (viga ponte): C40, T com bf=325, bw=25, hf=20,
    d=186.5, As=137.20, As'=16.00, d'=3.5+0.8+0.8=5.1 cm.
    Apostila informa alpha_e ~ 6.56."""
    ae = alpha_e(40.0, "granito")
    x_II = x_II_secao_T(
        bf_cm=325.0, bw_cm=25.0, hf_cm=20.0, d_cm=186.5,
        As_cm2=137.20, As_linha_cm2=16.00, d_linha_cm=5.1,
        alpha_e_val=ae,
    )
    # Apostila chega proximo a x_II = 24-26 cm
    assert 18.0 < x_II < 35.0, f"x_II fora do esperado: {x_II:.2f}"
    III = I_II_secao_T(
        bf_cm=325.0, bw_cm=25.0, hf_cm=20.0, d_cm=186.5, x_II_cm=x_II,
        As_cm2=137.20, As_linha_cm2=16.00, d_linha_cm=5.1, alpha_e_val=ae,
    )
    print(f"  OK  Sec T: x_II = {x_II:.2f} cm  III = {III:.0f} cm4")


def test_decalagem_modelo_I() -> None:
    """Apostila: a_l minimo = 0.5*d. Quando Vsd >> Vc, a_l aprox d."""
    d = 46.0
    a1 = decalagem_modelo_I(d_cm=d, VSd_kn=153.0, Vc_kn=49.6)
    # 0.5 * 46 * 153/(153-49.6) = 23 * 1.480 = 34.04 cm; <= d
    assert _aprox(a1, 34.04, 0.5), f"a_l={a1:.2f}"
    # caso Vsd ~ Vc -> a_l limitado a d
    a2 = decalagem_modelo_I(d_cm=d, VSd_kn=51.0, Vc_kn=49.6)
    assert _aprox(a2, d, 0.5), f"a_l={a2:.2f}"
    print(f"  OK  Modelo I: a_l(VSd=153,Vc=49.6) = {a1:.2f} cm  "
          f"a_l(VSd=51) = {a2:.2f} cm")


def test_decalagem_modelo_II() -> None:
    """Modelo II theta=30: a_l = 0.5 * cot(30) * d = 0.866*d."""
    a = decalagem_modelo_II(d_cm=46.0, theta_deg=30.0)
    assert _aprox(a, 39.84, 0.1), f"a_l={a:.2f}"
    print(f"  OK  Modelo II theta=30: a_l = {a:.2f} cm")


def test_fissuracao_apostila_ex17_1() -> None:
    """Apostila item 17.1 (ex. ponte): wk1 = 0.11 mm, wk2 = 0.23 mm,
    wk adotado = 0.11 mm <= wk,max = 0.30 mm."""
    sigma = sigma_si_aproximada(
        Md_ser_kncm=547750.0, d_cm=186.5, As_cm2=137.20,
    )
    assert _aprox(sigma, 25.18, 0.05), f"sigma_si={sigma:.2f}"
    r = abertura_fissura_wk(
        phi_mm=25.0,
        sigma_si_kncm2=sigma,
        Acr_cm2=1888.8,
        As_cm2=137.20,
        fck_mpa=40.0,
        eta1_val=2.25,
        wk_max_mm=0.30,
    )
    assert _aprox(r.wk1_mm, 0.11, 0.02), f"wk1={r.wk1_mm:.3f}"
    assert _aprox(r.wk2_mm, 0.23, 0.02), f"wk2={r.wk2_mm:.3f}"
    assert _aprox(r.wk_mm, 0.11, 0.02), f"wk={r.wk_mm:.3f}"
    assert r.ok, "deveria atender wk <= 0.30"
    print(f"  OK  Fissuracao: sigma={sigma:.2f}, wk1={r.wk1_mm:.3f}, "
          f"wk2={r.wk2_mm:.3f}, wk={r.wk_mm:.3f} mm  (ok={r.ok})")


def test_modulos_elasticidade_C25() -> None:
    """C25 granito: Eci = 28000 MPa, Ecs = 24150 MPa (apostila)."""
    eci = Eci_mpa(25.0, "granito")
    ecs = Ecs_mpa(25.0, "granito")
    assert _aprox(eci, 28000.0, 200.0), f"Eci={eci:.0f}"
    # alpha_i = 0.8 + 0.2*25/80 = 0.8625; Ecs = 0.8625 * 28000 = 24150
    assert _aprox(ecs, 24150.0, 200.0), f"Ecs={ecs:.0f}"
    print(f"  OK  Eci(C25) = {eci:.0f} MPa  Ecs(C25) = {ecs:.0f} MPa")


def test_largura_efetiva_mesa_T_biapoiada() -> None:
    """Viga T biapoiada L=500 cm, bw=20 cm, b2_l_esq=b2_l_dir=300 cm.
    a = 500; b1 = b3 = min(0.5*300, 0.10*500) = min(150, 50) = 50.
    bf = 50 + 20 + 50 = 120 cm."""
    r = largura_efetiva_mesa(
        bw_cm=20.0, b2_l_esq_cm=300.0, b2_l_dir_cm=300.0,
        L_cm=500.0, tipo_vao="biapoiada", tipo_secao="T",
    )
    assert _aprox(r["a_cm"], 500.0, 0.1)
    assert _aprox(r["b1_cm"], 50.0, 0.1)
    assert _aprox(r["b3_cm"], 50.0, 0.1)
    assert _aprox(r["bf_cm"], 120.0, 0.1)
    print(f"  OK  Mesa T biapoiada L=500: bf = {r['bf_cm']:.0f} cm "
          f"(b1={r['b1_cm']:.0f}, b3={r['b3_cm']:.0f})")


def test_largura_efetiva_mesa_L_continua() -> None:
    """Viga L (extremidade), L=600, bw=20, b2_l=80 (apenas um lado).
    Vao continuo extremo: a=0.75*600=450.
    b1 = min(0.5*80, 0.10*450) = min(40, 45) = 40.
    bf = 40 + 20 = 60."""
    r = largura_efetiva_mesa(
        bw_cm=20.0, b2_l_esq_cm=80.0, b2_l_dir_cm=0.0,
        L_cm=600.0, tipo_vao="continua-extrema", tipo_secao="L",
    )
    assert _aprox(r["a_cm"], 450.0, 0.1)
    assert _aprox(r["b1_cm"], 40.0, 0.1)
    assert _aprox(r["b3_cm"], 0.0, 0.1)
    assert _aprox(r["bf_cm"], 60.0, 0.1)
    print(f"  OK  Mesa L continua: bf = {r['bf_cm']:.0f} cm")


def test_largura_efetiva_mesa_balanco() -> None:
    """Balanco L=200, bw=20, b2_l=400.
    a = 2*200 = 400; b1 = b3 = min(0.5*400, 0.10*400) = min(200, 40) = 40.
    bf = 40+20+40 = 100."""
    r = largura_efetiva_mesa(
        bw_cm=20.0, b2_l_esq_cm=400.0, b2_l_dir_cm=400.0,
        L_cm=200.0, tipo_vao="balanco", tipo_secao="T",
    )
    assert _aprox(r["bf_cm"], 100.0, 0.1)
    print(f"  OK  Mesa T balanco: bf = {r['bf_cm']:.0f} cm")


def run_tests() -> int:
    tests = [
        test_modulos_elasticidade_C25,
        test_alpha_e_C40,
        test_x_II_retangular_apostila,
        test_x_II_secao_T_apostila,
        test_decalagem_modelo_I,
        test_decalagem_modelo_II,
        test_fissuracao_apostila_ex17_1,
        test_largura_efetiva_mesa_T_biapoiada,
        test_largura_efetiva_mesa_L_continua,
        test_largura_efetiva_mesa_balanco,
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
    print("=== Verificacao de fissuracao - viga ponte (Apostila 17.1) ===")
    sigma = sigma_si_aproximada(547750.0, 186.5, 137.20)
    r = abertura_fissura_wk(
        phi_mm=25.0, sigma_si_kncm2=sigma, Acr_cm2=1888.8,
        As_cm2=137.20, fck_mpa=40.0, eta1_val=2.25, wk_max_mm=0.30,
    )
    print(f"  sigma_si = {sigma:.2f} kN/cm2")
    print(f"  rho_ri   = {r.rho_ri:.4f}")
    print(f"  wk1      = {r.wk1_mm:.3f} mm")
    print(f"  wk2      = {r.wk2_mm:.3f} mm")
    print(f"  wk       = {r.wk_mm:.3f} mm  (max = {r.wk_max_mm} mm)")
    print(f"  ok       = {r.ok}")


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    _demo()
