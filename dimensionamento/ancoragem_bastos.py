"""Ancoragem e Emenda de Armaduras Passivas (NBR 6118:2023).

Implementa o calculo de comprimentos de ancoragem e de transpasse seguindo
a apostila "ANCORAGEM E EMENDA DE ARMADURAS", Prof. Paulo Sergio Bastos,
UNESP/Bauru.

Casos cobertos:
    - Resistencia de aderencia fbd = eta1 * eta2 * eta3 * fctd  (Eq. 1)
    - Comprimento de ancoragem basico lb = phi/4 * fyd/fbd       (Eq. 3)
    - Comprimento de ancoragem necessario lb_nec                  (Eq. 4)
    - Comprimento minimo lb,min                                   (Eq. 5)
    - Comprimento de transpasse para barras tracionadas l0t       (Eq. 6/7)
    - Comprimento de transpasse para barras comprimidas l0c       (Eq. 8/9)

Convencoes:
    - fck, fyk em MPa.
    - phi (diametro) em mm.
    - Resultados de comprimento em cm.
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

ETA1_TIPO_ACO = {
    "CA-25": 1.00,
    "CA-50": 2.25,
    "CA-60": 1.00,
}


# ---------------------------------------------------------------------------
# Helpers
#
# Invólucros de uma linha sobre o núcleo normativo único
# (nucleo_nbr6118.py): mantidos com o mesmo nome e assinatura para não
# quebrar quem já chama, mas a fórmula mora só no núcleo agora.
# ---------------------------------------------------------------------------
def fctm_mpa(fck_mpa: float) -> float:
    """fct,m, MPa (8.2.5). ANC-07: agora cobre fck > 50 MPa (antes só tinha
    o ramo 0,3*fck^(2/3), sem o ramo logaritmico do Grupo II)."""
    return nbr.fct_m(fck_mpa)


def fctd_mpa(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fctd = fctk,inf/gama_c, MPa (9.3.2.1, 19.4.1)."""
    return nbr.fctd(fck_mpa, gama_c)


def fyd_mpa(fyk_mpa: float, gama_s: float = GAMA_S) -> float:
    """fyd = fyk/gama_s, MPa."""
    return nbr.fyd(fyk_mpa, gama_s)


def eta1(tipo_aco: str) -> float:
    """eta1 pela categoria do aco (Tabela 8.2): CA-25 1,00; CA-50 2,25;
    CA-60 1,00."""
    if tipo_aco not in ETA1_TIPO_ACO:
        raise ValueError(f"tipo_aco deve ser CA-25, CA-50 ou CA-60: {tipo_aco}")
    return nbr.eta1(tipo_aco)


def eta2(boa_aderencia: bool) -> float:
    """eta2 = 1,0 em boa aderencia; 0,7 em ma aderencia (9.3.2.1)."""
    return nbr.eta2(boa_aderencia)


def eta3(phi_mm: float) -> float:
    """eta3 = 1,0 para phi < 32 mm; (132 - phi)/100 para phi >= 32 mm
    (9.3.2.1)."""
    return nbr.eta3(phi_mm)


def fbd_mpa(fck_mpa: float, tipo_aco: str = "CA-50",
            boa_aderencia: bool = True, phi_mm: float = 10.0,
            gama_c: float = GAMA_C) -> float:
    """fbd = eta1 * eta2 * eta3 * fctd  (Eq. 1)."""
    return (eta1(tipo_aco) * eta2(boa_aderencia) * eta3(phi_mm)
            * fctd_mpa(fck_mpa, gama_c))


# ---------------------------------------------------------------------------
# Comprimento de ancoragem basico (Eq. 3)
# ---------------------------------------------------------------------------
def lb_basico_cm(phi_mm: float, fck_mpa: float, fyk_mpa: float = 500.0,
                 tipo_aco: str = "CA-50", boa_aderencia: bool = True,
                 gama_c: float = GAMA_C, gama_s: float = GAMA_S) -> float:
    """lb = (phi/4) * (fyd/fbd) -> cm.

    Com phi em mm, fyd e fbd em MPa, lb sai em mm; dividir por 10 para cm.
    """
    fbd = fbd_mpa(fck_mpa, tipo_aco, boa_aderencia, phi_mm, gama_c)
    fyd = fyd_mpa(fyk_mpa, gama_s)
    lb_mm = (phi_mm / 4.0) * (fyd / fbd)
    return lb_mm / 10.0


def lb_min_cm(phi_mm: float, lb_cm: float) -> float:
    """lb,min = max(0.3*lb, 10*phi, 10 cm)  (Eq. 5)."""
    return max(0.3 * lb_cm, 10.0 * phi_mm / 10.0, 10.0)


def alpha_ancoragem(com_gancho: bool = False,
                    barra_transv_soldada: bool = False) -> float:
    """alpha do item 9.4.2.5 da NBR.
    - 1.0: sem gancho;
    - 0.7: com gancho (cobrimento normal ao gancho >= 3 phi) OU com barra
            transversal soldada;
    - 0.5: gancho + barra transversal soldada.
    """
    if com_gancho and barra_transv_soldada:
        return 0.5
    if com_gancho or barra_transv_soldada:
        return 0.7
    return 1.0


# ---------------------------------------------------------------------------
# Comprimento de ancoragem necessario (Eq. 4)
# ---------------------------------------------------------------------------
@dataclass
class ResultadoAncoragem:
    phi_mm: float
    fck_mpa: float
    fyk_mpa: float
    tipo_aco: str
    boa_aderencia: bool
    com_gancho: bool

    eta1: float
    eta2: float
    eta3: float
    fctd_mpa: float
    fbd_mpa: float
    fyd_mpa: float

    lb_cm: float           # comprimento basico
    lb_min_cm: float       # minimo
    alpha: float
    As_calc_As_ef: float
    lb_nec_cm: float       # comprimento necessario adotado


def comprimento_ancoragem(
    phi_mm: float,
    fck_mpa: float,
    fyk_mpa: float = 500.0,
    tipo_aco: str = "CA-50",
    boa_aderencia: bool = True,
    com_gancho: bool = False,
    barra_transv_soldada: bool = False,
    As_calc: float = 1.0,
    As_ef: float = 1.0,
    gama_c: float = GAMA_C,
    gama_s: float = GAMA_S,
) -> ResultadoAncoragem:
    """Comprimento de ancoragem necessario lb,nec."""
    fctd = fctd_mpa(fck_mpa, gama_c)
    e1 = eta1(tipo_aco)
    e2 = eta2(boa_aderencia)
    e3 = eta3(phi_mm)
    fbd = e1 * e2 * e3 * fctd
    fyd = fyd_mpa(fyk_mpa, gama_s)
    lb = lb_basico_cm(phi_mm, fck_mpa, fyk_mpa, tipo_aco, boa_aderencia,
                      gama_c, gama_s)
    lb_min = lb_min_cm(phi_mm, lb)
    alpha = alpha_ancoragem(com_gancho, barra_transv_soldada)
    razao = max(0.0, As_calc / As_ef)
    lb_nec = max(alpha * lb * razao, lb_min)
    return ResultadoAncoragem(
        phi_mm=phi_mm,
        fck_mpa=fck_mpa,
        fyk_mpa=fyk_mpa,
        tipo_aco=tipo_aco,
        boa_aderencia=boa_aderencia,
        com_gancho=com_gancho,
        eta1=e1, eta2=e2, eta3=e3,
        fctd_mpa=fctd, fbd_mpa=fbd, fyd_mpa=fyd,
        lb_cm=lb, lb_min_cm=lb_min,
        alpha=alpha, As_calc_As_ef=razao, lb_nec_cm=lb_nec,
    )


# ---------------------------------------------------------------------------
# Emenda por transpasse (item 6.1)
# ---------------------------------------------------------------------------
def alpha_0t(percent_emendadas: float) -> float:
    """alpha_0t conforme Tabela 9.4 da NBR 6118.

    %  <= 20: 1.2; <= 25: 1.4; <= 33: 1.6; <= 50: 1.8; > 50: 2.0
    """
    p = percent_emendadas
    if p <= 20.0:
        return 1.2
    if p <= 25.0:
        return 1.4
    if p <= 33.0:
        return 1.6
    if p <= 50.0:
        return 1.8
    return 2.0


def transpasse_tracionado_cm(
    phi_mm: float, fck_mpa: float, percent_emendadas: float,
    fyk_mpa: float = 500.0, tipo_aco: str = "CA-50",
    boa_aderencia: bool = True, com_gancho: bool = False,
    As_calc: float = 1.0, As_ef: float = 1.0,
) -> dict:
    """l0t = alpha_0t * lb_nec >= l0t,min  (Eq. 6/7).

    l0t,min = max(0.3 * alpha_0t * lb, 15*phi, 20 cm)

    ANC-08: emenda por traspasse nao e permitida para phi > 32 mm (9.5.2).
    """
    if phi_mm > 32.0:
        raise ValueError(
            "Emenda por traspasse não é permitida para bitola > 32 mm (9.5.2)."
        )
    anc = comprimento_ancoragem(
        phi_mm=phi_mm, fck_mpa=fck_mpa, fyk_mpa=fyk_mpa,
        tipo_aco=tipo_aco, boa_aderencia=boa_aderencia,
        com_gancho=com_gancho, As_calc=As_calc, As_ef=As_ef,
    )
    a0t = alpha_0t(percent_emendadas)
    l0t_min = max(0.3 * a0t * anc.lb_cm, 15.0 * phi_mm / 10.0, 20.0)
    l0t = max(a0t * anc.lb_nec_cm, l0t_min)
    return {
        "lb_cm": anc.lb_cm,
        "lb_nec_cm": anc.lb_nec_cm,
        "alpha_0t": a0t,
        "l0t_min_cm": l0t_min,
        "l0t_cm": l0t,
    }


def transpasse_comprimido_cm(
    phi_mm: float, fck_mpa: float, fyk_mpa: float = 500.0,
    tipo_aco: str = "CA-50", boa_aderencia: bool = True,
    As_calc: float = 1.0, As_ef: float = 1.0,
) -> dict:
    """l0c = lb_nec >= l0c,min = max(0.6*lb, 15*phi, 20 cm)  (Eq. 8/9).

    ANC-08: emenda por traspasse nao e permitida para phi > 32 mm (9.5.2).
    """
    if phi_mm > 32.0:
        raise ValueError(
            "Emenda por traspasse não é permitida para bitola > 32 mm (9.5.2)."
        )
    anc = comprimento_ancoragem(
        phi_mm=phi_mm, fck_mpa=fck_mpa, fyk_mpa=fyk_mpa,
        tipo_aco=tipo_aco, boa_aderencia=boa_aderencia,
        com_gancho=False, As_calc=As_calc, As_ef=As_ef,
    )
    l0c_min = max(0.6 * anc.lb_cm, 15.0 * phi_mm / 10.0, 20.0)
    l0c = max(anc.lb_nec_cm, l0c_min)
    return {
        "lb_cm": anc.lb_cm,
        "lb_nec_cm": anc.lb_nec_cm,
        "l0c_min_cm": l0c_min,
        "l0c_cm": l0c,
    }


# ---------------------------------------------------------------------------
# Tests (validados contra Tabela A-1 e A-2 da apostila)
# ---------------------------------------------------------------------------
def _aprox(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def test_tabela_A1_ca50_C25_phi10_boa_sem() -> None:
    """CA-50, C25, phi=10mm, boa aderencia, sem gancho -> 38 cm."""
    lb = lb_basico_cm(phi_mm=10.0, fck_mpa=25.0)
    assert _aprox(lb, 38.0, 0.5), f"lb={lb:.2f}"
    print(f"  OK  CA-50 C25 phi10 boa sem: lb = {lb:.2f} cm (Tabela A-1: 38)")


def test_tabela_A1_ca50_C25_phi10_ma_sem() -> None:
    """CA-50, C25, phi=10mm, ma aderencia, sem gancho -> 54 cm."""
    lb = lb_basico_cm(phi_mm=10.0, fck_mpa=25.0, boa_aderencia=False)
    assert _aprox(lb, 54.0, 0.5), f"lb={lb:.2f}"
    print(f"  OK  CA-50 C25 phi10 ma sem:  lb = {lb:.2f} cm (Tabela A-1: 54)")


def test_tabela_A1_ca50_C25_phi10_boa_com() -> None:
    """CA-50, C25, phi=10mm, boa aderencia, com gancho -> 27 cm."""
    r = comprimento_ancoragem(phi_mm=10.0, fck_mpa=25.0, com_gancho=True)
    assert _aprox(r.lb_nec_cm, 26.4, 0.7), f"lb_nec={r.lb_nec_cm:.2f}"
    print(f"  OK  CA-50 C25 phi10 boa com: lb_nec = {r.lb_nec_cm:.2f} cm "
          f"(Tabela A-1: 27)")


def test_tabela_A1_ca50_C20_phi10_boa_sem() -> None:
    """CA-50, C20, phi=10mm, boa aderencia, sem gancho -> 44 cm."""
    lb = lb_basico_cm(phi_mm=10.0, fck_mpa=20.0)
    assert _aprox(lb, 44.0, 0.5), f"lb={lb:.2f}"
    print(f"  OK  CA-50 C20 phi10 boa sem: lb = {lb:.2f} cm (Tabela A-1: 44)")


def test_tabela_A1_ca50_C30_phi16_boa_sem() -> None:
    """CA-50, C30, phi=16mm, boa aderencia, sem gancho -> 53 cm."""
    lb = lb_basico_cm(phi_mm=16.0, fck_mpa=30.0)
    assert _aprox(lb, 53.0, 0.5), f"lb={lb:.2f}"
    print(f"  OK  CA-50 C30 phi16 boa sem: lb = {lb:.2f} cm (Tabela A-1: 53)")


def test_tabela_A1_ca50_C25_phi32_boa_sem() -> None:
    """CA-50, C25, phi=32mm, boa aderencia, sem gancho -> 121 cm.
    Para phi >= 32mm aplica-se eta3 = (132 - 32)/100 = 1.0 -> mesmo valor."""
    lb = lb_basico_cm(phi_mm=32.0, fck_mpa=25.0)
    assert _aprox(lb, 121.0, 1.0), f"lb={lb:.2f}"
    print(f"  OK  CA-50 C25 phi32 boa sem: lb = {lb:.2f} cm (Tabela A-1: 121)")


def test_tabela_A2_ca60_C25_phi8_boa_sem() -> None:
    """CA-60, C25, phi=8mm, boa aderencia, sem gancho -> 81 cm.
    Para CA-60 eta1 = 1.0 (vs 2.25 do CA-50)."""
    lb = lb_basico_cm(phi_mm=8.0, fck_mpa=25.0, fyk_mpa=600.0,
                      tipo_aco="CA-60")
    assert _aprox(lb, 81.0, 0.5), f"lb={lb:.2f}"
    print(f"  OK  CA-60 C25 phi8  boa sem: lb = {lb:.2f} cm (Tabela A-2: 81)")


def test_lb_nec_com_relacao_As() -> None:
    """lb_nec proporcional a As,calc/As,ef. C25, phi=10, As_calc/As_ef=0.6,
    sem gancho: lb_nec = 0.6 * 38 = 22.8 mas tem que respeitar lb_min."""
    r = comprimento_ancoragem(
        phi_mm=10.0, fck_mpa=25.0, As_calc=0.6, As_ef=1.0,
    )
    # lb_min = max(0.3*38, 10*1.0, 10) = 11.4 cm
    # alpha=1, lb_nec = 1.0 * 38 * 0.6 = 22.8 cm > 11.4 -> adota 22.8
    assert _aprox(r.lb_nec_cm, 22.6, 0.5), f"lb_nec={r.lb_nec_cm:.2f}"
    assert _aprox(r.lb_min_cm, 11.3, 0.5), f"lb_min={r.lb_min_cm:.2f}"
    print(f"  OK  lb_nec(As_c/As_ef=0.6) = {r.lb_nec_cm:.2f} cm "
          f"(lb_min = {r.lb_min_cm:.2f})")


def test_alpha_0t() -> None:
    """Tabela 9.4 NBR 6118."""
    assert alpha_0t(20.0) == 1.2
    assert alpha_0t(25.0) == 1.4
    assert alpha_0t(33.0) == 1.6
    assert alpha_0t(50.0) == 1.8
    assert alpha_0t(75.0) == 2.0
    print("  OK  alpha_0t = [1.2, 1.4, 1.6, 1.8, 2.0]")


def test_transpasse_tracionado_50pct() -> None:
    """C25, phi=10mm, 50% emendadas, sem gancho.
    lb = 38 cm; alpha_0t = 1.8;  l0t = 1.8 * 38 = 68.4 cm."""
    r = transpasse_tracionado_cm(
        phi_mm=10.0, fck_mpa=25.0, percent_emendadas=50.0,
    )
    assert _aprox(r["l0t_cm"], 67.8, 0.7), f"l0t={r['l0t_cm']:.2f}"
    print(f"  OK  Transpasse 50%% emendadas: l0t = {r['l0t_cm']:.2f} cm")


def test_transpasse_comprimido() -> None:
    """C25, phi=10mm, comprimido. l0c = lb_nec = 38 cm; l0c,min = 22.8."""
    r = transpasse_comprimido_cm(phi_mm=10.0, fck_mpa=25.0)
    assert _aprox(r["l0c_cm"], 38.0, 0.5), f"l0c={r['l0c_cm']:.2f}"
    print(f"  OK  Transpasse comprimido: l0c = {r['l0c_cm']:.2f} cm "
          f"(min = {r['l0c_min_cm']:.2f})")


def run_tests() -> int:
    tests = [
        test_tabela_A1_ca50_C25_phi10_boa_sem,
        test_tabela_A1_ca50_C25_phi10_ma_sem,
        test_tabela_A1_ca50_C25_phi10_boa_com,
        test_tabela_A1_ca50_C20_phi10_boa_sem,
        test_tabela_A1_ca50_C30_phi16_boa_sem,
        test_tabela_A1_ca50_C25_phi32_boa_sem,
        test_tabela_A2_ca60_C25_phi8_boa_sem,
        test_lb_nec_com_relacao_As,
        test_alpha_0t,
        test_transpasse_tracionado_50pct,
        test_transpasse_comprimido,
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
    print("=== Comprimento de ancoragem - CA-50, C25, phi 10mm ===")
    for boa in (True, False):
        for ganc in (False, True):
            r = comprimento_ancoragem(phi_mm=10.0, fck_mpa=25.0,
                                      boa_aderencia=boa, com_gancho=ganc)
            print(f"  boa={boa!s:5}  gancho={ganc!s:5}  "
                  f"lb={r.lb_cm:.1f} cm  lb_nec={r.lb_nec_cm:.1f} cm")


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    _demo()
