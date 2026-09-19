"""Pilares de Concreto Armado (NBR 6118:2026).

Nome ate 19/09/2026: pilares_bastos.py. O credito as apostilas esta abaixo.

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

try:  # executado como script, ou com dimensionamento/ no sys.path
    import limites_geometricos_nbr6118 as _limites
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import limites_geometricos_nbr6118 as _limites


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


# === P10: gama_n de pilar esbelto critico com b < 19 cm (11.7.1, remissao a 13.2.3) ===
def aplicar_gama_n(b_cm: float, esforco: float) -> tuple[float, float]:
    """Aplica o coeficiente adicional gama_n ao esforco solicitante de
    calculo quando a menor dimensao b < 19 cm (11.7.1, PDF p. 84: "Para
    elementos estruturais esbeltos criticos para a seguranca de estrutura,
    como pilares e pilares-paredes com espessura inferior a 19 cm [...] os
    esforcos solicitantes de calculo devem ser multiplicados pelo
    coeficiente de ajustamento gama_n").

    Devolve (esforco majorado, gama_n usado). Para b >= 19 cm, gama_n = 1,0
    e o esforco volta inalterado. Delega a
    limites_geometricos_nbr6118.gama_n_pilar (13.2.3, Tabela 13.1); aquele
    modulo tambem cobre a dimensao minima e a area minima de 13.2.3.
    """
    gn = _limites.gama_n_pilar(b_cm)
    return esforco * gn, gn


# === P25: 2ª ordem local pelo pilar-padrão (15.3.1, 15.3.2, 15.6, 15.7.4, 15.8) ===
from dataclasses import replace as _replace_p25

LAMBDA_MAX_PILAR = 200.0            # 15.8.1 (PDF p. 127)
LAMBDA_GAMA_N1 = 140.0              # 15.8.1 (PDF p. 127) e 15.8.3.2 (PDF p. 129)
LAMBDA_FLUENCIA = 90.0              # 15.8.3.1 e 15.8.4 (PDF p. 129 e 131)
FRACAO_POUCO_COMPRIMIDO = 0.10      # 15.8.1: Nd < 0,10·fcd·Ac (PDF p. 127)
_TOL_P25 = 1e-9


def _fmt_p25(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


def _positivo_p25(valor: float, nome: str, item: str) -> float:
    v = float(valor)
    if not (v > 0.0) or math.isinf(v):
        raise nbr.FaixaNormativaError(
            f"{nome} = {v:g} inválido: tem de ser positivo e finito (NBR 6118:2026, {item})."
        )
    return v


# ---------------------------------------------------------------------------
# 15.3.1 — Rigidez secante adimensional κsec (PDF p. 122)
# ---------------------------------------------------------------------------
def kappa_sec(EI_sec_kncm2: float, Ac_cm2: float, h_cm: float, fcd_mpa: float) -> float:
    """Rigidez secante adimensional κsec (15.3.1, PDF p. 122).

        κsec = (EI)sec / (Ac · h² · fcd)

    (EI)sec em kN·cm² (por exemplo, de ``flexao_composta_obliqua.ei_secante``),
    Ac em cm², h (altura da seção considerada) em cm e fcd em MPa. O fcd é
    convertido para kN/cm² dentro da função (÷ 10), para que κsec saia
    adimensional. Serve para ábacos de interação N-M com os valores últimos
    NRd e MRd.
    """
    EI = float(EI_sec_kncm2)
    if not (EI > 0.0):
        raise nbr.FaixaNormativaError(
            f"(EI)sec = {EI:g} kN·cm² inválido: a rigidez secante tem de ser positiva (15.3.1)."
        )
    Ac = _positivo_p25(Ac_cm2, "Ac", "15.3.1")
    h = _positivo_p25(h_cm, "h", "15.3.1")
    fcd = _positivo_p25(fcd_mpa, "fcd", "15.3.1")
    return EI / (Ac * h * h * nbr.mpa_para_kncm2(fcd))


# ---------------------------------------------------------------------------
# 15.6 — Comprimento equivalente ℓe (PDF p. 125-126) e 15.8.2 (PDF p. 128)
# ---------------------------------------------------------------------------
def comprimento_equivalente_cm(l0_cm: float, h_cm: float, l_cm: float,
                               engastado_livre: bool = False) -> float:
    """Comprimento equivalente ℓe do pilar (15.6, PDF p. 126; 15.8.2, PDF p. 128).

    Pilar vinculado nas duas extremidades (15.6), o menor dos valores:

        ℓe = ℓ0 + h
        ℓe = ℓ

    ℓ0: distância entre as faces internas dos elementos estruturais, supostos
    horizontais, que vinculam o pilar; h: altura da seção transversal do
    pilar, medida no plano da estrutura em estudo; ℓ: distância entre os
    eixos dos elementos estruturais aos quais o pilar está vinculado. Tudo
    em cm.

    ``engastado_livre=True``: pilar engastado na base e livre no topo,
    ℓe = 2·ℓ (15.8.2, PDF p. 128); ℓ0 e h não entram.

    ℓ0 > ℓ é geometricamente impossível (a distância entre faces não passa
    da distância entre eixos) e levanta ``FaixaNormativaError``.
    """
    l = _positivo_p25(l_cm, "ℓ", "15.6")
    if engastado_livre:
        return 2.0 * l
    l0 = _positivo_p25(l0_cm, "ℓ0", "15.6")
    h = _positivo_p25(h_cm, "h", "15.6")
    if l0 > l + _TOL_P25:
        raise nbr.FaixaNormativaError(
            f"ℓ0 = {l0:g} cm maior que ℓ = {l:g} cm: a distância entre as faces "
            "internas não pode passar da distância entre os eixos (NBR 6118:2026, 15.6)."
        )
    return min(l0 + h, l)


# ---------------------------------------------------------------------------
# 15.8.2 — Índice de esbeltez λ = ℓe/i (PDF p. 127)
# ---------------------------------------------------------------------------
def raio_giracao_cm(I_cm4: float, A_cm2: float) -> float:
    """Raio de giração i = √(I/A), cm (15.8.2, PDF p. 127). I em cm⁴, A em cm²."""
    I = _positivo_p25(I_cm4, "I", "15.8.2")
    A = _positivo_p25(A_cm2, "A", "15.8.2")
    return math.sqrt(I / A)


def esbeltez(le_cm: float, I_cm4: float, A_cm2: float) -> float:
    """Índice de esbeltez λ = ℓe / i, com i = √(I/A) (15.8.2, PDF p. 127).

    Forma geral, para qualquer seção (circular, poligonal, composta): ℓe em
    cm (15.6), I em cm⁴ (momento de inércia da seção bruta no plano de
    flambagem considerado) e A em cm². Para seção retangular, i = h/√12 e
    λ = √12·ℓe/h ≈ 3,46·ℓe/h, que é o que ``esbeltez_lambda`` usa; para
    seção circular de diâmetro D, i = D/4 e λ = 4·ℓe/D.
    """
    le = _positivo_p25(le_cm, "ℓe", "15.8.2")
    return le / raio_giracao_cm(I_cm4, A_cm2)


# ---------------------------------------------------------------------------
# 15.8.1 — Limite λ <= 200 e coeficiente γn1 (PDF p. 127)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoEsbeltezLimite:
    """Verificação do limite de esbeltez de 15.8.1 e o que a faixa de λ exige."""
    lambda_: float
    lambda_max: float
    Nd_kn: float
    Nd_pouco_comprimido_kn: float     # 0,10·fcd·Ac, kN
    pouco_comprimido: bool            # Nd < 0,10·fcd·Ac
    gama_n1: float                    # 15.8.1, 1,0 para λ <= 140
    exige_fluencia: bool              # λ > 90 (15.8.3.1, 15.8.4)
    exige_metodo_geral: bool          # λ > 140 (15.8.3.2)
    pilar_padrao_permitido: bool      # λ <= 90 (15.8.3.3.2, 15.8.3.3.3)
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def gama_n1(lambda_val: float) -> float:
    """Coeficiente adicional γn1 dos efeitos locais de 2ª ordem (15.8.1, PDF p. 127).

        γn1 = 1 + (λ − 140)/140 >= 1

    Para λ <= 140, γn1 = 1,0. Mesma fórmula de ``n1_majoracao``, com
    validação de λ (não negativo e finito).
    """
    lam = float(lambda_val)
    if lam < 0.0 or math.isnan(lam) or math.isinf(lam):
        raise nbr.FaixaNormativaError(f"λ = {lam:g} inválido (15.8.1).")
    return n1_majoracao(lam)


def aplicar_gama_n1(M2d_kncm: float, lambda_val: float) -> tuple[float, float]:
    """Majora os efeitos locais de 2ª ordem por γn1 (15.8.1, PDF p. 127).

    "Para pilares com índice de esbeltez superior a 140, deve-se majorar os
    efeitos locais de 2ª ordem por um coeficiente adicional" γn1. O
    coeficiente multiplica a parcela de 2ª ordem (M2d), não o momento de
    1ª ordem. Devolve (γn1·M2d, γn1). Com λ <= 140, volta M2d inalterado.

    O pilar-padrão (λ <= 90) nunca ativa γn1; quem ativa são o método geral
    e o pilar-padrão acoplado a diagramas M, N, 1/r (15.8.3.2 e 15.8.3.3.4,
    pacote P28), que devem chamar esta função com o M2d que calcularem.
    """
    gn1 = gama_n1(lambda_val)
    return float(M2d_kncm) * gn1, gn1


def verificar_esbeltez_limite(lambda_val: float, Nd_kn: float, fck_mpa: float,
                              Ac_cm2: float, gama_c: float = GAMA_C) -> ResultadoEsbeltezLimite:
    """Limite geral de esbeltez λ <= 200 (15.8.1, PDF p. 127).

    "Os pilares devem ter índice de esbeltez menor ou igual a 200 (λ <= 200).
    Apenas no caso de elementos pouco comprimidos com força normal de
    cálculo menor que 0,10·fcd·Ac, o índice de esbeltez pode ser maior que
    200." λ = 200 passa; a exceção exige Nd < 0,10·fcd·Ac (estrito).

    Informa também o que a faixa de λ exige: fluência para λ > 90
    (15.8.3.1 e 15.8.4, PDF p. 129 e 131), método geral para λ > 140
    (15.8.3.2, PDF p. 129) e γn1 para λ > 140 (15.8.1). O pilar-padrão com
    curvatura ou rigidez κ aproximada só vale para λ <= 90.

    Nd em kN (compressão positiva; Nd <= 0 levanta FaixaNormativaError, porque
    a exceção vale só para elementos pouco comprimidos), fck em MPa, Ac em cm².
    """
    lam = float(lambda_val)
    if lam < 0.0 or math.isnan(lam) or math.isinf(lam):
        raise nbr.FaixaNormativaError(f"λ = {lam:g} inválido (15.8.1).")
    Ac = _positivo_p25(Ac_cm2, "Ac", "15.8.1")
    fcd = fcd_kncm2(fck_mpa, gama_c)
    Nd = float(Nd_kn)
    if not (Nd > 0.0) or math.isinf(Nd):
        raise nbr.FaixaNormativaError(
            f"Nd = {Nd:g} kN: o limite de esbeltez vale para pilar comprimido (Nd > 0); "
            "a exceção de 15.8.1 é para elementos pouco comprimidos, não tracionados."
        )
    N_lim = FRACAO_POUCO_COMPRIMIDO * fcd * Ac
    pouco = Nd < N_lim
    dentro = lam <= LAMBDA_MAX_PILAR + _TOL_P25
    ok = dentro or pouco
    gn1 = gama_n1(lam)
    if dentro:
        governante = f"λ = {_fmt_p25(lam)} <= 200"
    elif pouco:
        governante = (f"λ = {_fmt_p25(lam)} > 200, admitido: Nd = {_fmt_p25(Nd)} kN "
                      f"< 0,10·fcd·Ac = {_fmt_p25(N_lim)} kN")
    else:
        governante = (f"λ = {_fmt_p25(lam)} > 200 com Nd = {_fmt_p25(Nd)} kN "
                      f">= 0,10·fcd·Ac = {_fmt_p25(N_lim)} kN — não passa")
    memoria = (
        f"15.8.1: λ = {_fmt_p25(lam)}; limite λ <= 200.",
        f"15.8.1: 0,10·fcd·Ac = 0,10 × {_fmt_p25(fcd)} kN/cm² × {_fmt_p25(Ac)} cm² = "
        f"{_fmt_p25(N_lim)} kN; Nd = {_fmt_p25(Nd)} kN "
        f"({'pouco comprimido' if pouco else 'não é pouco comprimido'}).",
        f"15.8.1: γn1 = {_fmt_p25(gn1)}"
        + (f" = 1 + ({_fmt_p25(lam)} − 140)/140." if lam > LAMBDA_GAMA_N1 else " (λ <= 140)."),
        f"15.8.3: fluência {'obrigatória' if lam > LAMBDA_FLUENCIA else 'dispensada'} (λ > 90: 15.8.4); "
        f"método geral {'obrigatório' if lam > LAMBDA_GAMA_N1 else 'não obrigatório'} (λ > 140: 15.8.3.2).",
        f"Resultado: {governante} -> {'ok' if ok else 'não ok'}.",
    )
    return ResultadoEsbeltezLimite(
        lambda_=lam, lambda_max=LAMBDA_MAX_PILAR, Nd_kn=Nd,
        Nd_pouco_comprimido_kn=N_lim, pouco_comprimido=pouco, gama_n1=gn1,
        exige_fluencia=lam > LAMBDA_FLUENCIA,
        exige_metodo_geral=lam > LAMBDA_GAMA_N1,
        pilar_padrao_permitido=lam <= LAMBDA_MAX_PILAR_PADRAO + _TOL_P25,
        ok=ok, governante=governante, memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 15.8.4 — Fluência: excentricidade adicional ecc (PDF p. 131)
# ---------------------------------------------------------------------------
def carga_euler_Ne_kn(Eci_mpa: float, Ic_cm4: float, le_cm: float) -> float:
    """Ne = 10·Eci·Ic/ℓe², kN (15.8.4, PDF p. 131).

    Eci em MPa (8.2.8; ``nucleo_nbr6118.Eci``), convertido para kN/cm² dentro
    da função (÷ 10); Ic em cm⁴ (4.2.3, seção bruta); ℓe em cm (15.6).
    """
    Eci = nbr.mpa_para_kncm2(_positivo_p25(Eci_mpa, "Eci", "15.8.4"))
    Ic = _positivo_p25(Ic_cm4, "Ic", "15.8.4")
    le = _positivo_p25(le_cm, "ℓe", "15.8.4")
    return 10.0 * Eci * Ic / (le * le)


def ecc_fluencia_cm(Msg_kncm: float, Nsg_kn: float, ea_cm: float, phi: float,
                    Eci_mpa: float, Ic_cm4: float, le_cm: float) -> float:
    """Excentricidade adicional de fluência ecc, cm (15.8.4, PDF p. 131).

        ecc = (Msg/Nsg + ea) · (2,718^(φ·Nsg/(Ne − Nsg)) − 1)
        Ne  = 10·Eci·Ic/ℓe²

    Msg (kN·cm) e Nsg (kN): esforços da combinação quase permanente; ea (cm):
    excentricidade das imperfeições locais (Figura 11.2; ver
    ``ea_acidental_cm``); φ: coeficiente de fluência (Tabela 8.1,
    ``nucleo_nbr6118.phi_eps_cs_NBR``, ou Anexo A,
    ``tempo_concreto_nbr6118.coeficiente_fluencia``); Eci em MPa (8.1/8.2.8);
    Ic em cm⁴; ℓe em cm (15.6). A norma escreve a base 2,718 e diz que é o
    número de Euler; usa-se ``math.e``.

    Obrigatória para λ > 90 (15.8.4). O ecc se soma a e1, e o efeito de 2ª
    ordem é calculado por 15.8.3 como se fosse imediato. Usa-se |Msg|: a
    excentricidade de fluência amplifica a de 1ª ordem, no mesmo sentido.

    Faixa: Nsg > 0 (pilar comprimido) e Nsg < Ne. Com Nsg >= Ne a carga
    quase permanente passa da crítica de Euler e a expressão não tem
    sentido físico (o expoente diverge): levanta ``FaixaNormativaError``.
    """
    Nsg = float(Nsg_kn)
    if not (Nsg > 0.0):
        raise nbr.FaixaNormativaError(
            f"Nsg = {Nsg:g} kN: a excentricidade de fluência de 15.8.4 vale para pilar "
            "comprimido (Nsg > 0)."
        )
    fi = float(phi)
    if fi < 0.0 or math.isnan(fi) or math.isinf(fi):
        raise nbr.FaixaNormativaError(f"φ = {fi:g} inválido: o coeficiente de fluência é >= 0 (15.8.4).")
    ea = float(ea_cm)
    if ea < 0.0 or math.isnan(ea) or math.isinf(ea):
        raise nbr.FaixaNormativaError(f"ea = {ea:g} cm inválido: tem de ser >= 0 (15.8.4).")
    Ne = carga_euler_Ne_kn(Eci_mpa, Ic_cm4, le_cm)
    if Nsg >= Ne:
        raise nbr.FaixaNormativaError(
            f"Nsg = {Nsg:g} kN >= Ne = {Ne:g} kN: a força quase permanente atinge a carga "
            "crítica de Euler e a expressão de ecc (15.8.4) diverge; o pilar é instável."
        )
    try:
        fator = math.exp(fi * Nsg / (Ne - Nsg)) - 1.0
    except OverflowError:
        raise nbr.FaixaNormativaError(
            f"Nsg = {Nsg:g} kN muito próximo de Ne = {Ne:g} kN: o fator de fluência de 15.8.4 "
            "passa do maior número representável; o pilar é instável."
        ) from None
    return (abs(float(Msg_kncm)) / Nsg + ea) * fator


# ---------------------------------------------------------------------------
# 15.8.3.3.2 e 15.8.3.3.3 — Pilar-padrão numa direção, com λ1 de 15.8.2
# ---------------------------------------------------------------------------
METODOS_PILAR_PADRAO = ("curvatura", "rigidez")


@dataclass(frozen=True)
class ResultadoPilarPadraoDirecao:
    """Momento total Md,tot numa direção pelo pilar-padrão (15.8.3.3.2/3)."""
    direcao: str
    metodo: str
    h_cm: float
    le_cm: float
    lambda_: float
    lambda1: float
    dispensa_2a_ordem: bool         # λ < λ1 (15.8.2)
    MA_kncm: float                  # momento de 1ª ordem de maior valor absoluto (com sinal)
    MB_kncm: float                  # o outro extremo (com sinal)
    alpha_b: float
    M1d_min_kncm: float
    M1d_A_ef_kncm: float            # |M1d,A|, ou M1d,mín quando aplicado e maior
    nu: float
    M2d_kncm: float                 # parcela de 2ª ordem (já com γn1)
    gama_n1: float
    kappa: float | None             # só no método da rigidez κ
    Md_tot_kncm: float              # valor absoluto
    sinal: float                    # sentido de Md,tot (o de MA)
    memoria: tuple[str, ...]


def _md_tot_rigidez_p25(Nd: float, le: float, h: float, ab: float, M1dA: float) -> float:
    """Raiz positiva da formulação direta de 15.8.3.3.3 (PDF p. 130)."""
    a = 5.0 * h
    b = h * h * Nd - Nd * le * le / 320.0 - 5.0 * h * ab * M1dA
    c = -Nd * h * h * ab * M1dA
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        raise ValueError("Discriminante negativo no método da rigidez κ aproximada.")
    return (-b + math.sqrt(disc)) / (2.0 * a)


def pilar_padrao_direcao(
    Nd_kn: float, le_cm: float, h_cm: float, Ac_cm2: float, fck_mpa: float,
    MA_kncm: float, MB_kncm: float,
    metodo: str = "curvatura",
    tipo: str = "biapoiado",
    aplicar_minimo: bool = True,
    verificar_dispensa: bool = True,
    direcao: str = "",
    gama_c: float = GAMA_C,
) -> ResultadoPilarPadraoDirecao:
    """Md,tot numa direção pelo pilar-padrão (15.8.2, 15.8.3.3.2, 15.8.3.3.3; PDF p. 127-130).

    MA e MB são os momentos de cálculo de 1ª ordem nos extremos (nós fixos)
    ou os totais da análise global de 2ª ordem (nós móveis, 15.7.4), kN·cm,
    com sinal: MB positivo se tracionar a mesma face que MA. A função toma
    como MA o de maior valor absoluto.

    - λ = 3,46·ℓe/h, limitado a 90 (``_validar_lambda_pilar_padrao``).
    - αb por 15.8.2 (``alpha_b``), com o caso d) (momentos menores que o
      mínimo -> αb = 1,0).
    - ``aplicar_minimo=True`` (flexão composta normal): M1d,A >= M1d,mín =
      Nd(1,5 + 0,03h) (11.3.3.4.3), como ``Mdtot_curvatura_aprox``.
      ``aplicar_minimo=False``: M1d,A = |MA|, para a flexão oblíqua, em que o
      mínimo é verificado à parte pela envoltória da Figura 15.2 (15.3.2).
    - λ1 = (25 + 12,5·e1/h)/αb, 35 <= λ1 <= 90, com e1 = |MA|/Nd (15.8.2).
      Com ``verificar_dispensa`` e λ < λ1, os efeitos de 2ª ordem são
      desprezados e Md,tot = M1d,A.
    - ``metodo="curvatura"`` (15.8.3.3.2): Md,tot = αb·M1d,A + Nd·(ℓe²/10)·(1/r)
      >= M1d,A, 1/r = 0,005/[h(ν + 0,5)] <= 0,005/h.
    - ``metodo="rigidez"`` (15.8.3.3.3): a·Md,tot² + b·Md,tot + c = 0, a = 5h,
      b = h²Nd − Nd·ℓe²/320 − 5h·αb·M1d,A, c = −Nd·h²·αb·M1d,A; Md,tot >= M1d,A.

    A parcela de 2ª ordem passa por ``aplicar_gama_n1`` (15.8.1), que vale
    1,0 aqui porque λ <= 90. Unidades: kN, cm, kN·cm; fck em MPa.
    """
    if metodo not in METODOS_PILAR_PADRAO:
        raise ValueError(f"metodo deve ser 'curvatura' ou 'rigidez', recebido {metodo!r}.")
    Nd = float(Nd_kn)
    if not (Nd > 0.0):
        raise nbr.FaixaNormativaError(
            f"Nd = {Nd:g} kN: o pilar-padrão vale para flexo-compressão (Nd > 0; 15.8.1)."
        )
    h = _positivo_p25(h_cm, "h", "15.8.2")
    le = _positivo_p25(le_cm, "ℓe", "15.8.2")
    Ac = _positivo_p25(Ac_cm2, "Ac", "15.8.3.3.2")
    nome = "com curvatura aproximada" if metodo == "curvatura" else "com rigidez κ aproximada"
    item = "15.8.3.3.2" if metodo == "curvatura" else "15.8.3.3.3"
    lam = _validar_lambda_pilar_padrao(le, h, nome)

    MA, MB = float(MA_kncm), float(MB_kncm)
    if abs(MB) > abs(MA):
        MA, MB = MB, MA
    M1d_min = M1d_min_kncm(Nd, h)
    ab = alpha_b(MA, MB, tipo=tipo, M1d_min_kncm=M1d_min)
    if aplicar_minimo:
        M1dA_ef, ab_ef, _ = M1d_A_efetivo(Nd, h, MA, ab)
    else:
        M1dA_ef, ab_ef = abs(MA), ab
    e1 = abs(MA) / Nd
    lam1 = lambda1_limite(e1, h, ab_ef)
    dispensa = verificar_dispensa and lam < lam1
    nu = nu_adimensional(Nd, Ac, fck_mpa, gama_c)
    sinal = -1.0 if MA < 0.0 else 1.0

    memoria = [
        f"15.8.2 [{direcao or '-'}]: λ = 3,46·ℓe/h = 3,46 × {_fmt_p25(le)}/{_fmt_p25(h)} = {_fmt_p25(lam)} (<= 90).",
        f"15.8.2: MA = {_fmt_p25(MA)} kN·cm, MB = {_fmt_p25(MB)} kN·cm, tipo = {tipo}; αb = {_fmt_p25(ab_ef)}.",
        f"11.3.3.4.3: M1d,mín = Nd·(1,5 + 0,03h) = {_fmt_p25(Nd)} × (1,5 + 0,03 × {_fmt_p25(h)}) = {_fmt_p25(M1d_min)} kN·cm"
        + ("; aplicado a M1d,A." if aplicar_minimo else "; verificado à parte pela envoltória mínima (15.3.2)."),
        f"15.8.2: λ1 = (25 + 12,5·e1/h)/αb, 35 <= λ1 <= 90, e1 = {_fmt_p25(e1)} cm -> λ1 = {_fmt_p25(lam1)}.",
    ]
    kappa = None
    if dispensa:
        M2d, gn1 = 0.0, 1.0
        Md_tot = M1dA_ef
        memoria.append(f"15.8.2: λ = {_fmt_p25(lam)} < λ1 = {_fmt_p25(lam1)}: efeitos locais de 2ª ordem "
                       f"desprezados; Md,tot = M1d,A = {_fmt_p25(Md_tot)} kN·cm.")
    elif metodo == "curvatura":
        cur = curvatura_aproximada(h, nu)
        M2d_bruto = M2d_kncm(Nd, e2_cm(le, cur))
        M2d, gn1 = aplicar_gama_n1(M2d_bruto, lam)
        Md_tot = max(ab_ef * M1dA_ef + M2d, M1dA_ef)
        memoria.append(f"{item}: ν = {_fmt_p25(nu)}; 1/r = mín[0,005/(h(ν + 0,5)); 0,005/h] = {_fmt_p25(cur)} 1/cm.")
        memoria.append(f"{item}: Md,tot = αb·M1d,A + Nd·ℓe²/10·1/r = {_fmt_p25(ab_ef)} × {_fmt_p25(M1dA_ef)} + "
                       f"{_fmt_p25(M2d)} = {_fmt_p25(Md_tot)} kN·cm (>= M1d,A = {_fmt_p25(M1dA_ef)}).")
    else:
        Md_tot = max(_md_tot_rigidez_p25(Nd, le, h, ab_ef, M1dA_ef), M1dA_ef)
        M2d, gn1 = Md_tot - ab_ef * M1dA_ef, 1.0
        kappa = 32.0 * (1.0 + 5.0 * Md_tot / (h * Nd)) * nu
        memoria.append(f"{item}: a = 5h, b = h²Nd − Nd·ℓe²/320 − 5h·αb·M1d,A, c = −Nd·h²·αb·M1d,A; "
                       f"Md,tot = {_fmt_p25(Md_tot)} kN·cm (>= M1d,A = {_fmt_p25(M1dA_ef)}); "
                       f"κ = 32(1 + 5·Md,tot/(h·Nd))·ν = {_fmt_p25(kappa)}.")
    return ResultadoPilarPadraoDirecao(
        direcao=direcao, metodo=metodo, h_cm=h, le_cm=le, lambda_=lam, lambda1=lam1,
        dispensa_2a_ordem=dispensa, MA_kncm=MA, MB_kncm=MB, alpha_b=ab_ef,
        M1d_min_kncm=M1d_min, M1d_A_ef_kncm=M1dA_ef, nu=nu, M2d_kncm=M2d,
        gama_n1=gn1, kappa=kappa, Md_tot_kncm=Md_tot, sinal=sinal,
        memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# 15.7.4 — Efeitos locais em estruturas de nós móveis (PDF p. 127)
# ---------------------------------------------------------------------------
def efeitos_locais_nos_moveis(
    Nd_kn: float, le_cm: float, h_cm: float, Ac_cm2: float, fck_mpa: float,
    MA_2a_ordem_global_kncm: float, MB_2a_ordem_global_kncm: float,
    metodo: str = "curvatura",
    tipo: str = "biapoiado",
    gama_c: float = GAMA_C,
) -> ResultadoPilarPadraoDirecao:
    """Efeitos locais de 2ª ordem em estrutura de nós móveis (15.7.4, PDF p. 127).

    "A análise global de 2ª ordem fornece apenas os esforços nas
    extremidades das barras"; os elementos isolados são as barras
    comprimidas retiradas da estrutura, com comprimento ℓe de 15.6
    (``comprimento_equivalente_cm``), aplicando-se às suas extremidades os
    esforços da análise global de 2ª ordem. MA e MB são, então, os momentos
    totais (1ª ordem + 2ª ordem global) nos extremos (15.8.2 a), PDF
    p. 128), vindos da análise da própria biblioteca (P46) ou de um
    programa externo (por exemplo, os esforços finais do pórtico do TQS com
    γz ou P-Δ). Com MA e MB de 1ª ordem, o resultado é o de uma estrutura
    de nós fixos (15.6).

    O cálculo local é o pilar-padrão de ``pilar_padrao_direcao``, com o
    momento mínimo aplicado e a dispensa por λ1.
    """
    r = pilar_padrao_direcao(Nd_kn, le_cm, h_cm, Ac_cm2, fck_mpa,
                             MA_2a_ordem_global_kncm, MB_2a_ordem_global_kncm,
                             metodo=metodo, tipo=tipo, aplicar_minimo=True,
                             verificar_dispensa=True, direcao="nós móveis", gama_c=gama_c)
    linha = ("15.7.4: barra comprimida isolada com ℓe de 15.6 e, nos extremos, os momentos da "
             f"análise global de 2ª ordem: MA = {_fmt_p25(r.MA_kncm)} kN·cm, MB = {_fmt_p25(r.MB_kncm)} kN·cm.")
    return _replace_p25(r, memoria=(linha,) + r.memoria)


# ---------------------------------------------------------------------------
# 15.3.2 — Momentos totais mínimos para a envoltória da Figura 15.2 (PDF p. 122)
# ---------------------------------------------------------------------------
def momento_total_minimo_direcao(
    Nd_kn: float, le_cm: float, h_cm: float, Ac_cm2: float, fck_mpa: float,
    metodo: str = "curvatura", direcao: str = "", gama_c: float = GAMA_C,
) -> ResultadoPilarPadraoDirecao:
    """Md,tot,mín numa direção (15.3.2 e Figura 15.2, PDF p. 122).

    "[...] envoltória mínima com 2ª ordem, cujos momentos totais são
    calculados a partir dos momentos mínimos de 1ª ordem e de acordo com
    15.8.3." M1d,A = M1d,mín = Nd(1,5 + 0,03h) (11.3.3.4.3), αb = 1,0
    (15.8.2 d), e o pilar-padrão de 15.8.3.3.2 ou 15.8.3.3.3 na direção
    (h e ℓe da direção), sem dispensa por λ1: a função é chamada quando há
    necessidade de calcular os efeitos locais de 2ª ordem naquela direção.
    """
    return pilar_padrao_direcao(Nd_kn, le_cm, h_cm, Ac_cm2, fck_mpa, 0.0, 0.0,
                                metodo=metodo, tipo="biapoiado", aplicar_minimo=True,
                                verificar_dispensa=False, direcao=direcao, gama_c=gama_c)


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(run_tests())
    _demo()
