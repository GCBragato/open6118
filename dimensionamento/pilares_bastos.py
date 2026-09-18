"""Pilares de Concreto Armado (NBR 6118:2026).

Implementa o dimensionamento de pilares isolados (no fixos) seguindo a
apostila "PILARES DE CONCRETO ARMADO", Prof. Paulo Sergio Bastos,
UNESP/Bauru, corrigida contra a NBR 6118:2026 (auditoria de 18/09/2026:
PIL-01 a PIL-04). Grandezas de material vem de nucleo_nbr6118.

Casos cobertos:
    - Indice de esbeltez lambda = 3.46 * le / h         (Eq. 62)
    - Esbeltez limite lambda1                           (Eq. 82)
    - Coeficiente alpha_b                               (Eq. 84)
    - Momento fletor minimo M1d,min                     (Eq. 92)
    - Excentricidade minima e1,min                      (Eq. 93)
    - Forca normal adimensional nu                      (Eq. 78)
    - Curvatura aproximada 1/r                          (Eq. 77)
    - Excentricidade de 2a ordem e2                     (Eq. 75)
    - Momento fletor de 2a ordem M2d                    (Eq. 76)
    - Momento total: pilar-padrao com curvatura aprox.
    - Momento total: pilar-padrao com rigidez kappa aprox. (Eq. 100-102)

Convencoes:
    - fck em MPa.
    - Geometria em cm. Forcas em kN. Momentos em kN.cm.
    - Os dois metodos do pilar-padrao so valem para lambda <= 90
      (15.8.3.3.2 e 15.8.3.3.3); acima disso as funcoes levantam erro.
    - M1d,A < M1d,min: usa-se M1d,min com alpha_b = 1,0 (11.3.3.4.3 e
      15.8.2 d), e o momento de 2a ordem se soma a ele.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr


GAMA_C = nbr.GAMA_C
GAMA_S = nbr.GAMA_S
LAMBDA_MAX_PILAR_PADRAO = 90.0   # 15.8.3.3.2 e 15.8.3.3.3


def fcd_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fcd em kN/cm² (valida 20 <= fck <= 90 MPa pelo núcleo)."""
    return nbr.mpa_para_kncm2(nbr.fcd(fck_mpa, gama_c))


# ---------------------------------------------------------------------------
# Esbeltez
# ---------------------------------------------------------------------------
def esbeltez_lambda(le_cm: float, h_cm: float) -> float:
    """lambda = le / i, i = h / sqrt(12). Para secao retangular,
    lambda = 3.46 * le / h  (Eq. 62)."""
    return 3.46 * le_cm / h_cm


def lambda1_limite(e1_cm: float, h_cm: float, alpha_b: float = 1.0) -> float:
    """lambda1 = (25 + 12.5 * e1/h) / alpha_b  (Eq. 82),
    limitada a 35 <= lambda1 <= 90."""
    val = (25.0 + 12.5 * e1_cm / h_cm) / alpha_b
    return min(max(val, 35.0), 90.0)


def alpha_b(MA_kncm: float, MB_kncm: float,
            tipo: str = "biapoiado",
            M1d_min_kncm: float | None = None) -> float:
    """alpha_b conforme NBR 6118:2026, 15.8.2 (PDF p. 128).

    a) 'biapoiado' (sem cargas transversais): 0,6 + 0,4*MB/MA, 0,4 <= ab <= 1,0,
       com MA o momento de maior valor absoluto e MB positivo se tracionar a
       mesma face que MA;
    b) 'biapoiado-cargas-transv': 1,0;
    c) 'balanco': 1,0;
    d) momentos menores que o momento minimo de 11.3.3.4.3: 1,0. Informe
       M1d_min_kncm para que este caso seja aplicado.
    """
    if tipo in ("biapoiado-cargas-transv", "balanco"):
        return 1.0
    if abs(MB_kncm) > abs(MA_kncm):   # MA e o de maior valor absoluto
        MA_kncm, MB_kncm = MB_kncm, MA_kncm
    if M1d_min_kncm is not None and abs(MA_kncm) < M1d_min_kncm:
        return 1.0
    if abs(MA_kncm) < 1e-9:
        return 1.0
    val = 0.6 + 0.4 * MB_kncm / MA_kncm
    return min(max(val, 0.4), 1.0)


def n1_majoracao(lambda_val: float) -> float:
    """gamma_n1 para pilares com lambda > 140 (Eq. 83):
    gamma_n1 = 1 + (lambda - 140)/140."""
    if lambda_val <= 140.0:
        return 1.0
    return 1.0 + (lambda_val - 140.0) / 140.0


# ---------------------------------------------------------------------------
# Momento fletor minimo (Eq. 92, Eq. 93)
# ---------------------------------------------------------------------------
def M1d_min_kncm(Nd_kn: float, h_cm: float) -> float:
    """M1d,min = Nd * (1.5 + 0.03 * h_cm)  (apostila Eq. 92, h em cm).
    Originalmente NBR usa h em metros: Nd*(0.015 + 0.03 h_m); equivale a
    Nd*(1.5 + 0.03 h_cm)/100... mas a apostila simplifica colocando o
    fator 100 dentro -> e1,min = 1.5 + 0.03h em cm (Eq. 93)."""
    return nbr.M1d_min_kncm(Nd_kn, h_cm)


def e1_min_cm(h_cm: float) -> float:
    """e1,min = 1.5 + 0.03*h, com h em cm (Eq. 93)."""
    return 1.5 + 0.03 * h_cm


# ---------------------------------------------------------------------------
# Forca normal adimensional (Eq. 78)
# ---------------------------------------------------------------------------
def nu_adimensional(Nd_kn: float, Ac_cm2: float, fck_mpa: float,
                    gama_c: float = GAMA_C) -> float:
    """nu = Nd / (Ac * fcd)  (Eq. 78)."""
    return Nd_kn / (Ac_cm2 * fcd_kncm2(fck_mpa, gama_c))


# ---------------------------------------------------------------------------
# Pilar-padrao com curvatura aproximada (item 10.1.2)
# ---------------------------------------------------------------------------
def curvatura_aproximada(h_cm: float, nu: float) -> float:
    """1/r = 0.005 / (h * (nu + 0.5))  <=  0.005/h   (Eq. 77).
    Resultado em cm^-1."""
    cur = 0.005 / (h_cm * (nu + 0.5))
    cap = 0.005 / h_cm
    return min(cur, cap)


def e2_cm(le_cm: float, curvatura_inv_cm: float) -> float:
    """e2 = (le^2 / 10) * (1/r)  (Eq. 75)."""
    return le_cm * le_cm / 10.0 * curvatura_inv_cm


def M2d_kncm(Nd_kn: float, e2_cm_val: float) -> float:
    """M2d = Nd * e2  (Eq. 76)."""
    return Nd_kn * e2_cm_val


def _validar_lambda_pilar_padrao(le_cm: float, h_cm: float, metodo: str) -> float:
    """lambda <= 90 para os metodos do pilar-padrao (15.8.3.3.2 e 15.8.3.3.3)."""
    lam = esbeltez_lambda(le_cm, h_cm)
    if lam > LAMBDA_MAX_PILAR_PADRAO + 1e-9:   # tolerancia de arredondamento
        raise nbr.FaixaNormativaError(
            f"λ = {lam:.1f} > 90: o método do pilar-padrão {metodo} só pode ser "
            "empregado com λ ≤ 90 (NBR 6118:2026, 15.8.3.3). Acima disso é "
            "obrigatória a consideração da fluência (15.8.4), e o método geral "
            "é obrigatório para λ > 140 (15.8.3.2)."
        )
    return lam


def M1d_A_efetivo(Nd_kn: float, h_cm: float, M1d_A_kncm: float,
                  alpha_b_val: float = 1.0) -> tuple[float, float, float]:
    """M1d,A e alpha_b a usar no pilar-padrao, com o momento minimo.

    O efeito das imperfeicoes locais e atendido pelo momento minimo de 1a
    ordem M1d,min = Nd(0,015 + 0,03h), ao qual se somam os momentos de 2a
    ordem (11.3.3.4.3, PDF p. 80). Quando |M1d,A| < M1d,min, usa-se M1d,min
    com alpha_b = 1,0 (15.8.2 d, PDF p. 128).

    Devolve (M1d_A_ef, alpha_b_ef, M1d_min), momentos em kN.cm.
    """
    M1d_min = M1d_min_kncm(Nd_kn, h_cm)
    if abs(M1d_A_kncm) < M1d_min:
        return M1d_min, 1.0, M1d_min
    return abs(M1d_A_kncm), alpha_b_val, M1d_min


def Mdtot_curvatura_aprox(
    Nd_kn: float, le_cm: float, h_cm: float, fck_mpa: float,
    M1d_A_kncm: float, alpha_b_val: float = 1.0,
    Ac_cm2: float | None = None,
) -> dict:
    """Md,tot pelo metodo do pilar-padrao com curvatura aproximada (15.8.3.3.2).

    Md,tot = alpha_b * M1d,A + Nd * (le^2/10) * (1/r) >= M1d,A,
    com M1d,A >= M1d,min (e alpha_b = 1,0 quando o minimo governa).
    So vale para lambda <= 90.
    """
    if Ac_cm2 is None:
        # nao temos Ac aqui; o usuario deve passar
        raise ValueError("Ac_cm2 é necessário para calcular ν.")
    lam = _validar_lambda_pilar_padrao(le_cm, h_cm, "com curvatura aproximada")
    nu = nu_adimensional(Nd_kn, Ac_cm2, fck_mpa)
    cur = curvatura_aproximada(h_cm, nu)
    e2 = e2_cm(le_cm, cur)
    M2d = M2d_kncm(Nd_kn, e2)
    M1d_A_ef, ab_ef, M1d_min = M1d_A_efetivo(Nd_kn, h_cm, M1d_A_kncm, alpha_b_val)
    Md_tot = max(ab_ef * M1d_A_ef + M2d, M1d_A_ef)
    return {
        "lambda": lam,
        "nu": nu,
        "curvatura_inv_cm": cur,
        "e2_cm": e2,
        "M2d_kncm": M2d,
        "M1d_min_kncm": M1d_min,
        "M1d_A_ef_kncm": M1d_A_ef,
        "alpha_b_ef": ab_ef,
        "Md_tot_kncm": Md_tot,
    }


# ---------------------------------------------------------------------------
# Pilar-padrao com rigidez kappa aproximada (item 10.1.3)
# ---------------------------------------------------------------------------
def Mdtot_rigidez_aprox(
    Nd_kn: float, le_cm: float, h_cm: float, fck_mpa: float,
    M1d_A_kncm: float, alpha_b_val: float = 1.0,
    Ac_cm2: float | None = None,
) -> dict:
    """Md,tot pelo metodo do pilar-padrao com rigidez kappa aproximada (15.8.3.3.3).

    Formulacao direta para dimensionamento (PDF p. 130):
       a*Md,tot^2 + b*Md,tot + c = 0
       a = 5h
       b = h^2 * Nd - Nd*le^2/320 - 5h*alpha_b*M1d,A
       c = -Nd * h^2 * alpha_b * M1d,A
    Da-se a raiz positiva, com Md,tot >= M1d,A. M1d,A >= M1d,min (e
    alpha_b = 1,0 quando o minimo governa). So vale para lambda <= 90.
    """
    lam = _validar_lambda_pilar_padrao(le_cm, h_cm, "com rigidez κ aproximada")
    M1d_A_ef, ab_ef, M1d_min = M1d_A_efetivo(Nd_kn, h_cm, M1d_A_kncm, alpha_b_val)
    a = 5.0 * h_cm
    b = (h_cm * h_cm * Nd_kn - Nd_kn * le_cm * le_cm / 320.0
         - 5.0 * h_cm * ab_ef * M1d_A_ef)
    c = -Nd_kn * h_cm * h_cm * ab_ef * M1d_A_ef
    disc = b * b - 4.0 * a * c
    if disc < 0:
        raise ValueError("Discriminante negativo no método da rigidez κ aproximada.")
    Md_tot = (-b + math.sqrt(disc)) / (2.0 * a)
    Md_tot = max(Md_tot, M1d_A_ef)
    if Ac_cm2 is not None:
        nu = nu_adimensional(Nd_kn, Ac_cm2, fck_mpa)
        kappa = 32.0 * (1.0 + 5.0 * Md_tot / (h_cm * Nd_kn)) * nu
    else:
        nu = None
        kappa = None
    return {
        "lambda": lam,
        "Md_tot_kncm": Md_tot,
        "M1d_min_kncm": M1d_min,
        "M1d_A_ef_kncm": M1d_A_ef,
        "alpha_b_ef": ab_ef,
        "kappa_aprox": kappa,
        "nu": nu,
    }


# ---------------------------------------------------------------------------
# Excentricidade acidental (Eq. 80)
# ---------------------------------------------------------------------------
def ea_acidental_cm(le_cm: float) -> float:
    """ea = theta1 * le / 2; theta1 = 1/(100*sqrt(le_m)),
    com 1/300 <= theta1 <= 1/200 (11.3.3.4.1: theta1,min = 1/300 para
    estruturas reticuladas e imperfeicoes locais; theta1,max = 1/200).
    Resultado: ea = le/(200*sqrt(le_m)).
    Nota: a norma admite substituir as imperfeicoes locais pelo momento
    minimo de 11.3.3.4.3 (M1d_min_kncm), que e o que o pilar-padrao usa.
    """
    le_m = le_cm / 100.0
    theta1 = 1.0 / (100.0 * math.sqrt(le_m))
    theta1 = min(max(theta1, 1.0 / 300.0), 1.0 / 200.0)
    return theta1 * le_cm / 2.0


# ---------------------------------------------------------------------------
# Tests (validados contra Exemplo 13.1.1 da apostila)
# ---------------------------------------------------------------------------
def _aprox(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def test_esbeltez_apostila() -> None:
    """Pilar 20x50, le=280: lambda_x = 19.4, lambda_y = 48.4."""
    lx = esbeltez_lambda(le_cm=280.0, h_cm=50.0)
    ly = esbeltez_lambda(le_cm=280.0, h_cm=20.0)
    assert _aprox(lx, 19.4, 0.05), f"lambda_x={lx:.2f}"
    assert _aprox(ly, 48.4, 0.05), f"lambda_y={ly:.2f}"
    print(f"  OK  lambda_x = {lx:.2f}  lambda_y = {ly:.2f}")


def test_M1d_min_apostila() -> None:
    """Pilar intermediario, Nd=1400 kN, sec 20x50.
    M1d,min,x = 4200, M1d,min,y = 2940 kN.cm."""
    Mx = M1d_min_kncm(Nd_kn=1400.0, h_cm=50.0)
    My = M1d_min_kncm(Nd_kn=1400.0, h_cm=20.0)
    assert _aprox(Mx, 4200.0, 1.0), f"Mx={Mx:.1f}"
    assert _aprox(My, 2940.0, 1.0), f"My={My:.1f}"
    print(f"  OK  M1d,min,x = {Mx:.0f}  M1d,min,y = {My:.0f} kN.cm")


def test_lambda1_pilar_intermediario() -> None:
    """Pilar intermediario tem e1 = 0 -> lambda1 = 25/1 = 25 -> 35 (limite)."""
    l1 = lambda1_limite(e1_cm=0.0, h_cm=20.0, alpha_b=1.0)
    assert _aprox(l1, 35.0, 0.01), f"lambda1={l1:.2f}"
    print(f"  OK  lambda1 (e1=0, alpha_b=1) = {l1:.2f}")


def test_nu_apostila() -> None:
    """C30, Ac=1000, Nd=1400: nu = 0.6533."""
    nu = nu_adimensional(Nd_kn=1400.0, Ac_cm2=1000.0, fck_mpa=30.0)
    assert _aprox(nu, 0.65, 0.01), f"nu={nu:.4f}"
    print(f"  OK  nu = {nu:.4f}  (apostila: 0.65)")


def test_curvatura_e2_M2d_apostila() -> None:
    """Dir y do exemplo 13.1.1: h=20, nu=0.65, le=280.
    1/r = 0.005/(20*1.15) = 2.174e-4
    e2 = (280^2/10) * 2.174e-4 = 1.70 cm
    M2d = 1400 * 1.70 = 2380 kN.cm."""
    cur = curvatura_aproximada(h_cm=20.0, nu=0.6533)
    e2 = e2_cm(le_cm=280.0, curvatura_inv_cm=cur)
    M2d = M2d_kncm(Nd_kn=1400.0, e2_cm_val=e2)
    assert _aprox(cur, 2.174e-4, 1e-6), f"1/r={cur}"
    assert _aprox(e2, 1.70, 0.02), f"e2={e2:.3f}"
    assert _aprox(M2d, 2384.0, 5.0), f"M2d={M2d:.1f}"
    print(f"  OK  1/r = {cur:.4e} cm-1  e2 = {e2:.2f} cm  M2d = {M2d:.0f}")


def test_Mdtot_curvatura_apostila() -> None:
    """Dir y exemplo 13.1.1: M1d,A = 0 (pilar intermediario).
    M1d,A < M1d,min -> M1d,A = M1d,min = 2940 e alpha_b = 1,0; o M2d se soma
    (11.3.3.4.3 e 15.8.2 d): Md,tot,y = 2940 + 2379 = 5319 kN.cm.
    Apostila: 2940 + 2380 = 5320 kN.cm. (Auditoria PIL-01: o codigo antigo
    tomava max(M2d, M1d,min) = 2940 e este teste so conferia as parcelas.)"""
    r = Mdtot_curvatura_aprox(
        Nd_kn=1400.0, le_cm=280.0, h_cm=20.0, fck_mpa=30.0,
        M1d_A_kncm=0.0, alpha_b_val=1.0, Ac_cm2=1000.0,
    )
    assert _aprox(r["M2d_kncm"], 2379.2, 1.0), f"M2d={r['M2d_kncm']}"
    assert _aprox(r["M1d_min_kncm"], 2940.0, 1.0)
    assert _aprox(r["Md_tot_kncm"], 5320.0, 2.0), f"Md_tot={r['Md_tot_kncm']}"
    assert r["alpha_b_ef"] == 1.0
    print(f"  OK  M2d = {r['M2d_kncm']:.0f}  M1d,min = "
          f"{r['M1d_min_kncm']:.0f}  Md,tot = {r['Md_tot_kncm']:.0f}")


def test_alpha_b_biapoiado() -> None:
    """MA=100, MB=50 (mesma face): alpha_b = 0.6 + 0.4*0.5 = 0.8."""
    a = alpha_b(MA_kncm=100.0, MB_kncm=50.0)
    assert _aprox(a, 0.8, 0.01), f"alpha_b={a}"
    # MA=100, MB=-100: alpha_b = 0.6 + 0.4*(-1) = 0.2 -> limitado a 0.4
    a2 = alpha_b(MA_kncm=100.0, MB_kncm=-100.0)
    assert _aprox(a2, 0.4, 0.01), f"alpha_b={a2}"
    # Pilar em balanco
    a3 = alpha_b(MA_kncm=100.0, MB_kncm=0.0, tipo="balanco")
    assert _aprox(a3, 1.0, 0.01)
    # 15.8.2 d): momentos menores que o minimo -> 1,0 (auditoria PIL-03)
    a4 = alpha_b(MA_kncm=500.0, MB_kncm=200.0, M1d_min_kncm=2940.0)
    assert _aprox(a4, 1.0, 1e-9), f"alpha_b={a4}"
    print(f"  OK  αb: 0,8; 0,4 (limite); 1,0 (balanço); 1,0 (< mínimo)")


def test_rigidez_aprox_consistencia() -> None:
    """Comparacao entre os dois metodos para o exemplo da apostila.
    Apostila Tabela ex.1: ambos os metodos dao armaduras proximas, com
    rigidez kappa dando armadura ~5% menor."""
    # Pilar interm, dir y: M1d,A = M1d,min,y = 2940 (sem M2 explicito)
    r = Mdtot_rigidez_aprox(
        Nd_kn=1400.0, le_cm=280.0, h_cm=20.0, fck_mpa=30.0,
        M1d_A_kncm=2940.0, alpha_b_val=1.0, Ac_cm2=1000.0,
    )
    # Formulacao direta de 15.8.3.3.3: a=100, b=-77000, c=-1,6464e9 -> 4460,8
    assert _aprox(r["Md_tot_kncm"], 4460.8, 1.0), f"Md_tot={r['Md_tot_kncm']}"
    # M1d,A = 0 tem de dar o mesmo resultado (minimo governa; PIL-02)
    r0 = Mdtot_rigidez_aprox(
        Nd_kn=1400.0, le_cm=280.0, h_cm=20.0, fck_mpa=30.0,
        M1d_A_kncm=0.0, alpha_b_val=1.0, Ac_cm2=1000.0,
    )
    assert _aprox(r0["Md_tot_kncm"], r["Md_tot_kncm"], 1e-6)
    print(f"  OK  Md,tot (rigidez aprox) = {r['Md_tot_kncm']:.0f} kN.cm  "
          f"kappa={r['kappa_aprox']:.1f}")


def test_lambda_maior_que_90_recusado() -> None:
    """15.8.3.3.2/3: pilar-padrao so para lambda <= 90 (auditoria PIL-04)."""
    for f in (Mdtot_curvatura_aprox, Mdtot_rigidez_aprox):
        try:
            f(Nd_kn=1400.0, le_cm=600.0, h_cm=20.0, fck_mpa=30.0,
              M1d_A_kncm=2940.0, Ac_cm2=1000.0)
        except ValueError:
            continue
        raise AssertionError(f"{f.__name__} aceitou lambda = 103,8")
    print("  OK  λ = 103,8 recusado nos dois métodos")


def test_excentricidade_acidental() -> None:
    """ea para le = 280 cm = 2.8 m.
    theta1 = 1/(100*sqrt(2.8)) = 1/167.33 = 0.00598
    Limitado: max(1/300, min(1/200, 0.00598)) = 1/200 = 0.005
    ea = 0.005 * 280 / 2 = 0.7 cm."""
    ea = ea_acidental_cm(le_cm=280.0)
    assert _aprox(ea, 0.7, 0.05), f"ea={ea:.3f}"
    print(f"  OK  ea(le=280) = {ea:.2f} cm")


def run_tests() -> int:
    tests = [
        test_esbeltez_apostila,
        test_M1d_min_apostila,
        test_lambda1_pilar_intermediario,
        test_nu_apostila,
        test_curvatura_e2_M2d_apostila,
        test_Mdtot_curvatura_apostila,
        test_alpha_b_biapoiado,
        test_rigidez_aprox_consistencia,
        test_lambda_maior_que_90_recusado,
        test_excentricidade_acidental,
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
    print("=== Exemplo 13.1.1 - pilar intermediario 20x50 ===")
    print("  Nk = 1000 kN, C30, le = 280 cm")
    Nd = 1400.0
    Ac = 1000.0
    print(f"  lambda_x = {esbeltez_lambda(280.0, 50.0):.2f}")
    print(f"  lambda_y = {esbeltez_lambda(280.0, 20.0):.2f}")
    print(f"  M1d,min,x = {M1d_min_kncm(Nd, 50.0):.0f} kN.cm")
    print(f"  M1d,min,y = {M1d_min_kncm(Nd, 20.0):.0f} kN.cm")
    nu = nu_adimensional(Nd, Ac, 30.0)
    print(f"  nu = {nu:.3f}")
    cur = curvatura_aproximada(20.0, nu)
    e2 = e2_cm(280.0, cur)
    M2d = M2d_kncm(Nd, e2)
    print(f"  Dir y: 1/r = {cur:.4e}, e2 = {e2:.2f} cm, "
          f"M2d = {M2d:.0f} kN.cm")
    print(f"  Md,tot,y = M1d,min,y + M2d = "
          f"{M1d_min_kncm(Nd, 20.0) + M2d:.0f} kN.cm")


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    _demo()
