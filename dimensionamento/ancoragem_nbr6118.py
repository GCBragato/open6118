"""Ancoragem e Emenda de Armaduras Passivas (NBR 6118:2023).

Nome até 19/09/2026: ancoragem_bastos.py. O crédito às apostilas está abaixo.

Implementa o cálculo de comprimentos de ancoragem e de transpasse seguindo
a apostila "ANCORAGEM E EMENDA DE ARMADURAS", Prof. Paulo Sérgio Bastos,
UNESP/Bauru.

Casos cobertos:
    - Resistência de aderência fbd = eta1 * eta2 * eta3 * fctd  (Eq. 1)
    - Comprimento de ancoragem básico lb = phi/4 * fyd/fbd       (Eq. 3)
    - Comprimento de ancoragem necessário lb_nec                  (Eq. 4)
    - Comprimento mínimo lb,min                                   (Eq. 5)
    - Comprimento de transpasse para barras tracionadas l0t       (Eq. 6/7)
    - Comprimento de transpasse para barras comprimidas l0c       (Eq. 8/9)

Convenções:
    - fck, fyk em MPa.
    - phi (diâmetro) em mm.
    - Resultados de comprimento em cm.
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
    o ramo 0,3*fck^(2/3), sem o ramo logarítmico do Grupo II)."""
    return nbr.fct_m(fck_mpa)


def fctd_mpa(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fctd = fctk,inf/gama_c, MPa (9.3.2.1, 19.4.1)."""
    return nbr.fctd(fck_mpa, gama_c)


def fyd_mpa(fyk_mpa: float, gama_s: float = GAMA_S) -> float:
    """fyd = fyk/gama_s, MPa."""
    return nbr.fyd(fyk_mpa, gama_s)


def eta1(tipo_aco: str) -> float:
    """eta1 pela categoria do aço (Tabela 8.2): CA-25 1,00; CA-50 2,25;
    CA-60 1,00."""
    if tipo_aco not in ETA1_TIPO_ACO:
        raise ValueError(f"tipo_aco deve ser CA-25, CA-50 ou CA-60: {tipo_aco}.")
    return nbr.eta1(tipo_aco)


def eta2(boa_aderencia: bool) -> float:
    """eta2 = 1,0 em boa aderência; 0,7 em má aderência (9.3.2.1)."""
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
# Comprimento de ancoragem básico (Eq. 3)
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
# Comprimento de ancoragem necessário (Eq. 4)
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

    lb_cm: float           # comprimento básico
    lb_min_cm: float       # mínimo
    alpha: float
    As_calc_As_ef: float
    lb_nec_cm: float       # comprimento necessário adotado


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
    """Comprimento de ancoragem necessário lb,nec."""
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
    diametros_diferentes: tuple[float, ...] | None = None,
    distancia_livre_cm: float | None = None,
) -> dict:
    """l0t = alpha_0t * lb_nec >= l0t,min  (Eq. 6/7).

    l0t,min = max(0.3 * alpha_0t * lb, 15*phi, 20 cm)

    ANC-08: emenda por traspasse não é permitida para phi > 32 mm (9.5.2).

    P27 (9.5.2.1 e 9.5.2.2.2, PDF p. 62-63):
    - ``diametros_diferentes``: diâmetros (mm) das duas barras emendadas
      entre si, quando diferentes; o traspasse é calculado pela barra de
      menor diâmetro (9.5.2.1). ``phi_mm`` tem de ser um deles. Mais de
      duas barras levanta ``FaixaNormativaError``: a norma manda calcular
      com o esforço de cálculo em cada barra (chame a função barra a barra,
      com o As_calc/As_ef de cada uma).
    - ``distancia_livre_cm``: distância livre entre as barras emendadas.
      Se for maior que 4*phi, ela é somada ao l0t (9.5.2.2.2), e a armadura
      transversal da emenda tem de ser justificada (9.5.2.4); a chave
      ``justificar_armadura_transversal`` do retorno sai True.
    Sem esses dois argumentos, o resultado é o de antes do P27 (o retorno
    ganha só as chaves ``phi_calculo_mm``, ``acrescimo_distancia_livre_cm``
    e ``justificar_armadura_transversal``).
    """
    phi_mm = _phi_traspasse_p27(phi_mm, diametros_diferentes)
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
    acrescimo = _acrescimo_distancia_livre_p27(phi_mm, distancia_livre_cm)
    return {
        "lb_cm": anc.lb_cm,
        "lb_nec_cm": anc.lb_nec_cm,
        "alpha_0t": a0t,
        "l0t_min_cm": l0t_min,
        "l0t_cm": l0t + acrescimo,
        "phi_calculo_mm": phi_mm,
        "acrescimo_distancia_livre_cm": acrescimo,
        "justificar_armadura_transversal": acrescimo > 0.0,
    }


def transpasse_comprimido_cm(
    phi_mm: float, fck_mpa: float, fyk_mpa: float = 500.0,
    tipo_aco: str = "CA-50", boa_aderencia: bool = True,
    As_calc: float = 1.0, As_ef: float = 1.0,
    diametros_diferentes: tuple[float, ...] | None = None,
    distancia_livre_cm: float | None = None,
) -> dict:
    """l0c = lb_nec >= l0c,min = max(0.6*lb, 15*phi, 20 cm)  (Eq. 8/9).

    ANC-08: emenda por traspasse não é permitida para phi > 32 mm (9.5.2).

    P27: ``diametros_diferentes`` segue 9.5.2.1 (traspasse pela barra de
    menor diâmetro; mais de duas barras levanta ``FaixaNormativaError``),
    como em ``transpasse_tracionado_cm``. ``distancia_livre_cm``: a norma só
    prescreve o acréscimo da distância livre maior que 4*phi para barras
    tracionadas (9.5.2.2.2, PDF p. 63); aqui ele é aplicado também às
    comprimidas, por analogia e a favor da segurança, com ``AvisoNBR6118``.
    Sem esses dois argumentos, o resultado é o de antes do P27.
    """
    phi_mm = _phi_traspasse_p27(phi_mm, diametros_diferentes)
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
    acrescimo = _acrescimo_distancia_livre_p27(phi_mm, distancia_livre_cm)
    if acrescimo > 0.0:
        warnings.warn(
            "9.5.2.2.2 trata só de barras tracionadas; o acréscimo da "
            "distância livre maior que 4*phi foi aplicado ao traspasse "
            "comprimido por analogia, a favor da segurança.",
            nbr.AvisoNBR6118, stacklevel=2,
        )
    return {
        "lb_cm": anc.lb_cm,
        "lb_nec_cm": anc.lb_nec_cm,
        "l0c_min_cm": l0c_min,
        "l0c_cm": l0c + acrescimo,
        "phi_calculo_mm": phi_mm,
        "acrescimo_distancia_livre_cm": acrescimo,
        "justificar_armadura_transversal": acrescimo > 0.0,
    }


# ---------------------------------------------------------------------------
# Tests (validados contra Tabela A-1 e A-2 da apostila)
# ---------------------------------------------------------------------------
def _aprox(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def test_tabela_A1_ca50_C25_phi10_boa_sem() -> None:
    """CA-50, C25, phi=10mm, boa aderência, sem gancho -> 38 cm."""
    lb = lb_basico_cm(phi_mm=10.0, fck_mpa=25.0)
    assert _aprox(lb, 38.0, 0.5), f"lb={lb:.2f}"
    print(f"  OK  CA-50 C25 phi10 boa sem: lb = {lb:.2f} cm (Tabela A-1: 38)")


def test_tabela_A1_ca50_C25_phi10_ma_sem() -> None:
    """CA-50, C25, phi=10mm, má aderência, sem gancho -> 54 cm."""
    lb = lb_basico_cm(phi_mm=10.0, fck_mpa=25.0, boa_aderencia=False)
    assert _aprox(lb, 54.0, 0.5), f"lb={lb:.2f}"
    print(f"  OK  CA-50 C25 phi10 má sem:  lb = {lb:.2f} cm (Tabela A-1: 54)")


def test_tabela_A1_ca50_C25_phi10_boa_com() -> None:
    """CA-50, C25, phi=10mm, boa aderência, com gancho -> 27 cm."""
    r = comprimento_ancoragem(phi_mm=10.0, fck_mpa=25.0, com_gancho=True)
    assert _aprox(r.lb_nec_cm, 26.4, 0.7), f"lb_nec={r.lb_nec_cm:.2f}"
    print(f"  OK  CA-50 C25 phi10 boa com: lb_nec = {r.lb_nec_cm:.2f} cm "
          f"(Tabela A-1: 27)")


def test_tabela_A1_ca50_C20_phi10_boa_sem() -> None:
    """CA-50, C20, phi=10mm, boa aderência, sem gancho -> 44 cm."""
    lb = lb_basico_cm(phi_mm=10.0, fck_mpa=20.0)
    assert _aprox(lb, 44.0, 0.5), f"lb={lb:.2f}"
    print(f"  OK  CA-50 C20 phi10 boa sem: lb = {lb:.2f} cm (Tabela A-1: 44)")


def test_tabela_A1_ca50_C30_phi16_boa_sem() -> None:
    """CA-50, C30, phi=16mm, boa aderência, sem gancho -> 53 cm."""
    lb = lb_basico_cm(phi_mm=16.0, fck_mpa=30.0)
    assert _aprox(lb, 53.0, 0.5), f"lb={lb:.2f}"
    print(f"  OK  CA-50 C30 phi16 boa sem: lb = {lb:.2f} cm (Tabela A-1: 53)")


def test_tabela_A1_ca50_C25_phi32_boa_sem() -> None:
    """CA-50, C25, phi=32mm, boa aderência, sem gancho -> 121 cm.
    Para phi >= 32mm aplica-se eta3 = (132 - 32)/100 = 1.0 -> mesmo valor."""
    lb = lb_basico_cm(phi_mm=32.0, fck_mpa=25.0)
    assert _aprox(lb, 121.0, 1.0), f"lb={lb:.2f}"
    print(f"  OK  CA-50 C25 phi32 boa sem: lb = {lb:.2f} cm (Tabela A-1: 121)")


def test_tabela_A2_ca60_C25_phi8_boa_sem() -> None:
    """CA-60, C25, phi=8mm, boa aderência, sem gancho -> 81 cm.
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


# ---------------------------------------------------------------------------
# === P21: Ancoragem passiva, ganchos e estribos ===
#
# Completa a ancoragem por aderência: classificação da situação de aderência
# pela posição da barra (9.3.1), majoração para escorregamento (9.3.2.3),
# dispensa de confinamento (9.4.1.1), validação do uso de gancho por tipo de
# barra e solicitação (9.4.2.1), barra transversal soldada na ancoragem
# (9.4.2.2), geometria dos ganchos e Tabela 9.1 (9.4.2.3), armadura
# transversal na ancoragem (9.4.2.6) e ancoragem de estribos, Tabela 9.2
# (9.4.6).
# ---------------------------------------------------------------------------

# --- 9.3.1 — Posição da barra durante a concretagem (PDF p. 53) ------------
def situacao_aderencia(inclinacao_graus: float, h_cm: float, y_cm: float,
                       forma_deslizante: bool = False) -> bool:
    """Classifica a situação de aderência (True = boa) pela posição da barra
    durante a concretagem (9.3.1, PDF p. 53).

    - inclinação > 45 graus sobre a horizontal: sempre boa aderência;
    - horizontal, ou inclinação <= 45 graus: depende de h_cm e y_cm:
        - h_cm < 60: boa se a barra estiver no máximo 30 cm acima da face
          inferior do elemento (ou da junta de concretagem mais próxima) —
          y_cm é essa distância, e a condição é y_cm <= 30;
        - h_cm >= 60: boa se a barra estiver no mínimo 30 cm abaixo da face
          superior do elemento (ou da junta mais próxima) — y_cm é essa
          distância, e a condição é y_cm >= 30;
    - fôrma deslizante (forma_deslizante=True): sempre má aderência,
      independentemente dos demais parâmetros.

    Demais posições são má situação quanto à aderência (retorno False).
    """
    if forma_deslizante:
        return False
    if inclinacao_graus > 45.0:
        return True
    if h_cm < 60.0:
        return y_cm <= 30.0
    return y_cm >= 30.0


# --- 9.3.2.3 — Majoração para verificação do escorregamento (PDF p. 54) ----
FATOR_ESCORREGAMENTO = 1.75


def fbd_escorregamento(fbd_ou_fbpd_mpa: float) -> float:
    """Tensão de aderência majorada para a verificação do escorregamento da
    armadura em elementos estruturais fletidos (9.3.2.3, PDF p. 54): os
    valores de fbd (9.3.2.1) ou fbpd (9.3.2.2) são multiplicados por 1,75.
    """
    return FATOR_ESCORREGAMENTO * fbd_ou_fbpd_mpa


# --- 9.4.1.1 — Ancoragem por aderência: dispensa de confinamento (p. 55) ---
DISPOSITIVOS_COMBINAVEIS_ADERENCIA = ("gancho", "barra_transversal_soldada",
                                      "chapa_soldada_na_ponta")


def dispensa_confinamento(cobrimento_cm: float, espacamento_cm: float,
                          phi_mm: float) -> bool:
    """True quando o cobrimento e o espaçamento entre barras dispensam
    armadura transversal de confinamento na ancoragem por aderência
    (9.4.1.1, PDF p. 55): cobrimento da barra ancorada >= 3*phi e distância
    entre barras ancoradas >= 3*phi (nesse caso o próprio concreto confina).
    Caso contrário, a ancoragem deve ser confinada por armadura transversal
    (ver Ast_ancoragem, 9.4.2.6).
    """
    limite_cm = 3.0 * phi_mm / 10.0
    return cobrimento_cm >= limite_cm and espacamento_cm >= limite_cm


# --- 9.4.2.1 — Condições de ancoragem reta, com ou sem gancho (p. 55) ------
def validar_uso_gancho(tipo_barra: str, solicitacao: str, phi_mm: float,
                       com_gancho: bool, em_feixe: bool = False) -> None:
    """Valida se o uso (ou a ausência) de gancho é compatível com o tipo de
    barra e a solicitação (9.4.2.1, PDF p. 55). Não devolve valor: levanta
    ValueError quando a combinação é proibida pela norma.

    tipo_barra: 'lisa', 'entalhada' ou 'nervurada'.
    solicitacao: 'tracao', 'compressao' ou 'alternada' (alternância de
    tração e compressão na mesma barra).

    Proibições (levantam ValueError):
      a) barra lisa sem gancho — gancho é obrigatório para barra lisa;
      b) barra com solicitação alternada com gancho — deve ser sem gancho;
      barra comprimida (solicitacao='compressao') com gancho — barras
      comprimidas são sempre ancoradas sem gancho.

    Não recomendado, mas não proibido (emite aviso ``nucleo_nbr6118.AvisoNBR6118``,
    o cálculo prossegue): gancho com phi_mm > 32 mm, ou com feixe de barras
    (em_feixe=True).
    """
    tb = str(tipo_barra).strip().lower()
    sol = str(solicitacao).strip().lower()
    if tb == "lisa" and not com_gancho:
        raise ValueError(
            "Barra lisa exige gancho na ancoragem reta (9.4.2.1 a)."
        )
    if sol == "alternada" and com_gancho:
        raise ValueError(
            "Barra com alternância de tração e compressão deve ser ancorada "
            "sem gancho (9.4.2.1 b)."
        )
    if sol == "compressao" and com_gancho:
        raise ValueError(
            "Barra comprimida deve ser ancorada sem gancho (9.4.2.1)."
        )
    if com_gancho and (phi_mm > 32.0 or em_feixe):
        motivo = "phi > 32 mm" if phi_mm > 32.0 else "feixe de barras"
        warnings.warn(
            f"Gancho não é recomendado para {motivo} (9.4.2.1 c).",
            nbr.AvisoNBR6118,
            stacklevel=2,
        )


# --- 9.4.2.2 — Barras transversais soldadas na ancoragem (PDF p. 55-56) ---
@dataclass(frozen=True)
class ResultadoBarraTransversalSoldada:
    phi_mm: float
    phi_t_mm: float
    distancia_cm: float
    As_cm2: float
    fyd_mpa: float
    phi_t_min_mm: float
    distancia_min_cm: float
    forca_resistente_min_kn: float
    ok_diametro: bool
    ok_distancia: bool
    ok_solda: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_barra_transversal_soldada(
    phi_mm: float,
    phi_t_mm: float,
    distancia_cm: float,
    forca_solda_kn: float,
    As_cm2: float,
    fyd_mpa: float,
) -> ResultadoBarraTransversalSoldada:
    """Verifica as três condições geométricas e de resistência da barra
    transversal soldada usada para ancoragem por aderência (9.4.2.2, PDF
    p. 55-56; Figura 9.1):

    a) phi_t >= 0,60 * phi;
    b) distância da barra soldada ao ponto de início da ancoragem >= 5*phi;
    c) resistência ao cisalhamento da solda >= 0,3 * As * fyd (30 % da
       força resistida pela barra ancorada).
    """
    phi_t_min = 0.6 * phi_mm
    distancia_min = 5.0 * phi_mm / 10.0
    forca_min = 0.3 * As_cm2 * nbr.mpa_para_kncm2(fyd_mpa)
    ok_diametro = phi_t_mm >= phi_t_min
    ok_distancia = distancia_cm >= distancia_min
    ok_solda = forca_solda_kn >= forca_min
    ok = ok_diametro and ok_distancia and ok_solda
    if not ok_diametro:
        governante = "9.4.2.2 a) phi_t >= 0,60*phi"
    elif not ok_distancia:
        governante = "9.4.2.2 b) distância >= 5*phi"
    elif not ok_solda:
        governante = "9.4.2.2 c) resistência da solda >= 0,3*As*fyd"
    else:
        governante = "atende 9.4.2.2 a), b) e c)"
    memoria = (
        f"phi_t = {phi_t_mm:g} mm; mínimo 0,60*phi = 0,60*{phi_mm:g} = "
        f"{phi_t_min:.2f} mm -> {'ok' if ok_diametro else 'não ok'}.",
        f"distância ao início da ancoragem = {distancia_cm:g} cm; mínimo "
        f"5*phi = 5*{phi_mm:g}mm/10 = {distancia_min:.2f} cm -> "
        f"{'ok' if ok_distancia else 'não ok'}.",
        f"força da solda = {forca_solda_kn:g} kN; mínimo 0,3*As*fyd = "
        f"0,3*{As_cm2:g}cm2*{fyd_mpa:.2f}MPa = {forca_min:.2f} kN -> "
        f"{'ok' if ok_solda else 'não ok'}.",
    )
    return ResultadoBarraTransversalSoldada(
        phi_mm=phi_mm, phi_t_mm=phi_t_mm, distancia_cm=distancia_cm,
        As_cm2=As_cm2, fyd_mpa=fyd_mpa, phi_t_min_mm=phi_t_min,
        distancia_min_cm=distancia_min, forca_resistente_min_kn=forca_min,
        ok_diametro=ok_diametro, ok_distancia=ok_distancia, ok_solda=ok_solda,
        ok=ok, governante=governante, memoria=memoria,
    )


# --- 9.4.2.3 — Ganchos: Tabela 9.1, comprimento e solda transversal -------
# (PDF p. 56)
TABELA_9_1 = {
    # (faixa_bitola, tipo_aco) -> D/phi (Tabela 9.1, PDF p. 56)
    ("<20", "CA-25"): 4.0, ("<20", "CA-50"): 5.0, ("<20", "CA-60"): 6.0,
    (">=20", "CA-25"): 5.0, (">=20", "CA-50"): 8.0,
    # (">=20", "CA-60"): sem valor na tabela ("-")
}

_PONTA_RETA_GANCHO_MULT = {
    "semicircular": 2.0,
    "45": 4.0,
    "reto": 8.0,
}


def diametro_pino_gancho(phi_mm: float, aco: str) -> float:
    """Diâmetro do pino de dobramento (D), em múltiplos de phi, exigido
    para os ganchos das armaduras longitudinais de tração (Tabela 9.1,
    9.4.2.3, PDF p. 56). aco: 'CA-25', 'CA-50' ou 'CA-60'.
    """
    if aco not in ETA1_TIPO_ACO:
        raise ValueError(f"aco deve ser CA-25, CA-50 ou CA-60: {aco!r}.")
    faixa = "<20" if phi_mm < 20.0 else ">=20"
    D = TABELA_9_1.get((faixa, aco))
    if D is None:
        raise nbr.FaixaNormativaError(
            f"Tabela 9.1 não define o pino de dobramento para {aco} com "
            f"bitola {phi_mm:g} mm (faixa {faixa})."
        )
    return D


def comprimento_gancho(phi_mm: float, tipo: str,
                       tipo_barra: str | None = None) -> float:
    """Comprimento mínimo da ponta reta do gancho de armadura longitudinal
    de tração, em cm (9.4.2.3, PDF p. 56).

    tipo: 'semicircular' (ponta reta >= 2*phi), '45' (ângulo de 45 graus,
    ponta reta >= 4*phi) ou 'reto' (ângulo reto, ponta reta >= 8*phi).
    tipo_barra: se 'lisa', só é permitido gancho semicircular (a norma
    exige gancho semicircular para barra lisa); outro tipo levanta
    ValueError.
    """
    chave = str(tipo).strip().lower()
    mult = _PONTA_RETA_GANCHO_MULT.get(chave)
    if mult is None:
        raise ValueError(
            f"tipo de gancho deve ser 'semicircular', '45' ou 'reto': {tipo!r}."
        )
    if (tipo_barra is not None
            and str(tipo_barra).strip().lower() == "lisa"
            and chave != "semicircular"):
        raise ValueError("Barra lisa exige gancho semicircular (9.4.2.3).")
    return mult * phi_mm / 10.0


def pino_com_solda_transversal(
    phi_mm: float,
    aco: str,
    solda_antes_dobramento: bool,
    distancia_ao_inicio_curva_mm: float | None = None,
    sobre_trecho_curvo: bool = False,
) -> float:
    """Diâmetro do pino de dobramento (D, em múltiplos de phi) quando há
    barra soldada transversalmente ao gancho (9.4.2.3, PDF p. 56-57: a regra
    de solda após o dobramento está no início da p. 57).

    Se a solda ocorrer depois do dobramento (solda_antes_dobramento=False),
    mantém-se sempre a Tabela 9.1. Se ocorrer antes do dobramento: mantém-se
    a Tabela 9.1 quando o ponto de solda estiver na parte reta a uma
    distância >= 4*phi do início da curva; caso contrário (distância menor,
    ou solda sobre o trecho curvo), o pino mínimo passa a D = 20.
    """
    if not solda_antes_dobramento:
        return diametro_pino_gancho(phi_mm, aco)
    if sobre_trecho_curvo:
        return 20.0
    if distancia_ao_inicio_curva_mm is None:
        raise ValueError(
            "Informe distancia_ao_inicio_curva_mm quando a solda ocorre "
            "antes do dobramento e fora do trecho curvo."
        )
    if distancia_ao_inicio_curva_mm < 4.0 * phi_mm:
        return 20.0
    return diametro_pino_gancho(phi_mm, aco)


# --- 9.4.2.6 — Armadura transversal na ancoragem (PDF p. 57-58) -----------
@dataclass(frozen=True)
class ResultadoArmaduraTransversalAncoragem:
    """Armadura transversal exigida ao longo do comprimento de ancoragem
    (9.4.2.6.1/9.4.2.6.2). ``governante`` registra qual subitem da norma foi
    aplicado (9.4.2.6.1, phi < 32 mm, ou 9.4.2.6.2, phi >= 32 mm).

    Não há campo ``ok``: esta função dimensiona a armadura transversal
    exigida (Ast,min ou o espaçamento máximo de 5*phi), não compara uma
    armadura já definida com um limite — a verificação fica com quem usa
    o resultado (mesmo motivo de ``ResultadoCombinacao``, em
    acoes_nbr6118.py; convenção 3.3 do plano).
    """

    phi_mm: float
    duas_direcoes: bool
    As_barra_cm2: float | None
    fyd_barra_mpa: float | None
    fyd_transversal_mpa: float | None
    Ast_min_cm2: float | None
    espacamento_max_cm: float
    barra_adicional_alem_extremidade_cm: float | None
    governante: str
    memoria: tuple[str, ...]


def Ast_ancoragem(
    phi_mm: float,
    As_barra_cm2: float,
    fyd_barra_mpa: float,
    fyd_transversal_mpa: float | None = None,
    barra_comprimida: bool = False,
) -> ResultadoArmaduraTransversalAncoragem:
    """Armadura transversal ao longo do comprimento de ancoragem (9.4.2.6,
    PDF p. 57-58).

    phi_mm < 32 (9.4.2.6.1): a armadura transversal deve resistir a 25 % da
    força longitudinal da barra ancorada (a de maior diâmetro, se a
    ancoragem envolver barras diferentes):
        Ast * fyd_transversal >= 0,25 * As_barra * fyd_barra
    fyd_transversal_mpa, se omitido, usa o mesmo fyd_barra_mpa (mesmo aço).

    phi_mm >= 32 (9.4.2.6.2): a norma não dá uma fórmula de área — exige
    verificar a armadura em duas direções transversais ao conjunto de
    barras ancoradas, capazes de resistir às tensões de fendilhamento,
    respeitando o espaçamento máximo de 5*phi; Ast_min_cm2 sai None nesse
    ramo. Se barra_comprimida=True, uma das barras da armadura transversal
    deve ficar a 4*phi além da extremidade da barra ancorada.
    """
    espacamento_max_cm = 5.0 * phi_mm / 10.0
    if phi_mm < 32.0:
        governante = "9.4.2.6.1: phi < 32 mm"
        fyd_transv = fyd_transversal_mpa if fyd_transversal_mpa is not None else fyd_barra_mpa
        Ast_min = 0.25 * As_barra_cm2 * fyd_barra_mpa / fyd_transv
        memoria = (
            f"9.4.2.6.1: phi = {phi_mm:g} mm < 32 mm.",
            f"Ast,min = 0,25 * As * fyd_barra/fyd_transversal = 0,25 * "
            f"{As_barra_cm2:g} cm2 * {fyd_barra_mpa:.2f}/{fyd_transv:.2f} "
            f"= {Ast_min:.3f} cm2.",
        )
        return ResultadoArmaduraTransversalAncoragem(
            phi_mm=phi_mm, duas_direcoes=False,
            As_barra_cm2=As_barra_cm2, fyd_barra_mpa=fyd_barra_mpa,
            fyd_transversal_mpa=fyd_transv, Ast_min_cm2=Ast_min,
            espacamento_max_cm=espacamento_max_cm,
            barra_adicional_alem_extremidade_cm=None,
            governante=governante, memoria=memoria,
        )
    governante = "9.4.2.6.2: phi >= 32 mm"
    barra_adicional = 4.0 * phi_mm / 10.0 if barra_comprimida else None
    memoria = (
        f"9.4.2.6.2: phi = {phi_mm:g} mm >= 32 mm: verificar armadura em "
        f"duas direções transversais ao conjunto de barras ancoradas "
        f"(fendilhamento), espaçamento máximo 5*phi = "
        f"{espacamento_max_cm:.2f} cm.",
    )
    if barra_comprimida:
        memoria = memoria + (
            f"Barra comprimida: uma barra da armadura transversal a "
            f"4*phi = {barra_adicional:.2f} cm além da extremidade.",
        )
    return ResultadoArmaduraTransversalAncoragem(
        phi_mm=phi_mm, duas_direcoes=True,
        As_barra_cm2=None, fyd_barra_mpa=None, fyd_transversal_mpa=None,
        Ast_min_cm2=None, espacamento_max_cm=espacamento_max_cm,
        barra_adicional_alem_extremidade_cm=barra_adicional,
        governante=governante, memoria=memoria,
    )


# --- 9.4.6 — Ancoragem de estribos: Tabela 9.2, ganchos e solda (p. 60) ---
TABELA_9_2 = {
    # (faixa_bitola, tipo_aco) -> D/phi_t (Tabela 9.2, PDF p. 60)
    ("<=10", "CA-25"): 3.0, ("<=10", "CA-50"): 3.0, ("<=10", "CA-60"): 3.0,
    ("10-20", "CA-25"): 4.0, ("10-20", "CA-50"): 5.0,
    (">=20", "CA-25"): 5.0, (">=20", "CA-50"): 8.0,
    # ("10-20", "CA-60") e (">=20", "CA-60"): sem valor na tabela ("-")
}


def diametro_pino_estribo(phi_t_mm: float, aco: str) -> float:
    """Diâmetro do pino de dobramento (D), em múltiplos de phi_t, exigido
    para os ganchos de estribos (Tabela 9.2, 9.4.6.1, PDF p. 60).
    aco: 'CA-25', 'CA-50' ou 'CA-60'.
    """
    if aco not in ETA1_TIPO_ACO:
        raise ValueError(f"aco deve ser CA-25, CA-50 ou CA-60: {aco!r}.")
    if phi_t_mm <= 10.0:
        faixa = "<=10"
    elif phi_t_mm < 20.0:
        faixa = "10-20"
    else:
        faixa = ">=20"
    D = TABELA_9_2.get((faixa, aco))
    if D is None:
        raise nbr.FaixaNormativaError(
            f"Tabela 9.2 não define o pino de dobramento de estribos para "
            f"{aco} com bitola {phi_t_mm:g} mm (faixa {faixa})."
        )
    return D


def ponta_reta_estribo_cm(phi_t_mm: float, tipo: str,
                          aco_liso: bool = False) -> float:
    """Comprimento mínimo da ponta reta do gancho de estribo, em cm
    (9.4.6.1, PDF p. 60).

    tipo: 'semicircular' ou '135' (ângulo de 135 graus): ponta reta =
    max(5*phi_t, 5 cm); 'reto' (ângulo reto): ponta reta =
    max(10*phi_t, 7 cm), proibido para barra ou fio liso (aco_liso=True
    levanta ValueError nesse caso).
    """
    chave = str(tipo).strip().lower()
    if chave in ("semicircular", "135"):
        return max(5.0 * phi_t_mm / 10.0, 5.0)
    if chave == "reto":
        if aco_liso:
            raise ValueError(
                "Gancho de estribo em ângulo reto não pode ser usado para "
                "barra ou fio liso (9.4.6.1 b)."
            )
        return max(10.0 * phi_t_mm / 10.0, 7.0)
    raise ValueError(
        f"tipo de gancho de estribo deve ser 'semicircular', '135' ou "
        f"'reto': {tipo!r}."
    )


@dataclass(frozen=True)
class ResultadoAncoragemEstriboBarraSoldada:
    phi_t_mm: float
    num_barras_soldadas: int
    phi_t1_mm: float
    phi_t1_min_mm: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def ancoragem_estribo_barra_soldada(
    phi_t_mm: float, phi_t1_mm: float, num_barras_soldadas: int,
) -> ResultadoAncoragemEstriboBarraSoldada:
    """Verifica a condição geométrica de diâmetro da ancoragem de estribo
    por barra(s) transversal(is) soldada(s) (9.4.6.2, PDF p. 60-61; a
    condição de resistência da solda, comprovada por ensaio para a força
    As*fyd, fica fora do escopo numérico desta função).

    num_barras_soldadas=2 (estribo de um ou dois ramos): phi_t1 > 0,7*phi_t
    — a norma usa desigualdade estrita no texto (item a), embora a
    Figura 9.3 mostre phi_t1 >= 0,7*phi_t; adota-se aqui o texto (mais
    conservador — ver divergência registrada no retorno do pacote).
    num_barras_soldadas=1 (estribo de dois ramos): phi_t1 >= 1,4*phi_t.
    """
    if num_barras_soldadas == 2:
        phi_t1_min = 0.7 * phi_t_mm
        ok = phi_t1_mm > phi_t1_min
        governante = "9.4.6.2 a) duas barras soldadas: phi_t1 > 0,7*phi_t"
    elif num_barras_soldadas == 1:
        phi_t1_min = 1.4 * phi_t_mm
        ok = phi_t1_mm >= phi_t1_min
        governante = "9.4.6.2 b) uma barra soldada (estribo 2 ramos): phi_t1 >= 1,4*phi_t"
    else:
        raise ValueError("num_barras_soldadas deve ser 1 ou 2 (9.4.6.2).")
    memoria = (
        f"phi_t = {phi_t_mm:g} mm; phi_t1 adotado = {phi_t1_mm:g} mm; "
        f"phi_t1_min = {phi_t1_min:g} mm ({governante}) -> "
        f"{'ok' if ok else 'não ok'}.",
    )
    return ResultadoAncoragemEstriboBarraSoldada(
        phi_t_mm=phi_t_mm, num_barras_soldadas=num_barras_soldadas,
        phi_t1_mm=phi_t1_mm, phi_t1_min_mm=phi_t1_min, ok=ok,
        governante=governante, memoria=memoria,
    )


# ---------------------------------------------------------------------------
# === P27: Emendas por traspasse — diâmetros diferentes e distância livre ===
#
# Auxiliares de transpasse_tracionado_cm e transpasse_comprimido_cm
# (9.5.2.1 e 9.5.2.2.2, PDF p. 62-63). O resto das emendas (Tabela 9.3,
# armadura transversal, feixes, luvas, solda) está em emendas_nbr6118.py.
# ---------------------------------------------------------------------------
def _phi_traspasse_p27(phi_mm: float,
                       diametros_diferentes: tuple[float, ...] | None) -> float:
    """Diâmetro de cálculo do traspasse (9.5.2.1, PDF p. 62): com duas
    barras de diâmetros diferentes emendadas entre si, o da menor."""
    if diametros_diferentes is None:
        return phi_mm
    diams = tuple(float(d) for d in diametros_diferentes)
    if len(diams) > 2:
        raise nbr.FaixaNormativaError(
            "Com mais de duas barras de diâmetros diferentes emendadas, a "
            "norma manda calcular o traspasse com o esforço solicitante de "
            "cálculo em cada barra (9.5.2.1): chame a função para cada barra, "
            "com o As_calc/As_ef dela."
        )
    if len(diams) < 2 or min(diams) <= 0.0:
        raise ValueError(
            "diametros_diferentes deve trazer os dois diâmetros (mm), "
            "positivos, das barras emendadas entre si (9.5.2.1)."
        )
    if not any(abs(phi_mm - d) <= 1e-9 for d in diams):
        raise ValueError(
            f"phi_mm = {phi_mm:g} mm não é nenhum dos diâmetros emendados "
            f"{diams} (9.5.2.1)."
        )
    if max(diams) > 32.0:
        raise ValueError(
            "Emenda por traspasse não é permitida para bitola > 32 mm (9.5.2)."
        )
    return min(diams)


def _acrescimo_distancia_livre_p27(phi_mm: float,
                                   distancia_livre_cm: float | None) -> float:
    """Acréscimo ao traspasse pela distância livre entre as barras emendadas,
    cm (9.5.2.2.2, PDF p. 63): se a distância livre for maior que 4*phi,
    soma-se a própria distância livre; entre 0 e 4*phi (9.5.2.2.1), nada."""
    if distancia_livre_cm is None:
        return 0.0
    if distancia_livre_cm < 0.0:
        raise ValueError("distancia_livre_cm não pode ser negativa (9.5.2.2).")
    if distancia_livre_cm > 4.0 * phi_mm / 10.0:
        return float(distancia_livre_cm)
    return 0.0
