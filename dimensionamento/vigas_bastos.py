"""Flexao Normal Simples - Vigas em Concreto Armado (NBR 6118:2023).

Implementa o dimensionamento das vigas a flexao simples seguindo a apostila
"FLEXAO NORMAL SIMPLES - VIGAS" (Out/2023), Prof. Paulo Sergio Bastos,
UNESP/Bauru, baseada na NBR 6118:2023.

Casos cobertos:
    - Secao retangular com armadura simples (apostila item 7).
    - Secao retangular com armadura dupla (item 8).
    - Secao T com armadura simples (item 9).
    - Verificacao: momento resistente dado As (problema inverso).

Convencoes da apostila:
    - Concretos do Grupo I (fck <= 50 MPa); diagrama retangular simplificado
      com y = 0.8x e sigma_cd = 0.85 fcd (Eq. 15-16 da apostila).
    - Limite de ductilidade NBR 6118 14.6.4.3: x/d <= 0.45 para fck <= 50 MPa.
    - Aco CA-50 (fyk = 500 MPa) por padrao.
    - Coeficientes de ponderacao: gama_c = 1.4, gama_s = 1.15, gama_f = 1.4
      (combinacao normal).
    - Unidades: kN e cm em todas as funcoes (igual aos coeficientes K
      tabelados pelo professor).

Estrutura segue:
    - alv_est/viga_mista_v3.py: dataclasses de resultado, funcoes puras,
      testes contra exemplos numericos do livro.
    - open6118/dimensionamento/vigas.py: funcoes de calculo isoladas, sem GUI.
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

E_S = 21000.0          # kN/cm2 (modulo de elasticidade do aco - 210 GPa).
EPS_CU = 3.5           # %o (deformacao ultima do concreto, fck <= 50 MPa).
EPS_C2 = 2.0           # %o.
LIMITE_BETA_X = 0.45   # NBR 6118 14.6.4.3 para fck <= 50 MPa.
ALPHA_C = 0.85         # Coef. da tensao de calculo no diagrama retangular.

# Taxas minimas de armadura de flexao (Tabela 17.3 da NBR 6118).
RHO_MIN_TABELA = {
    20: 0.00150, 25: 0.00150, 30: 0.00150, 35: 0.00164, 40: 0.00179,
    45: 0.00194, 50: 0.00208,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fcd_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fck em MPa -> fcd em kN/cm2 (1 MPa = 0.1 kN/cm2)."""
    return (fck_mpa / gama_c) * 0.1


def fyd_kncm2(fyk_mpa: float, gama_s: float = GAMA_S) -> float:
    """fyk em MPa -> fyd em kN/cm2."""
    return (fyk_mpa / gama_s) * 0.1


def eps_yd_permil(fyk_mpa: float, gama_s: float = GAMA_S) -> float:
    """Deformacao de inicio de escoamento em %o (per mil)."""
    fyd = fyd_kncm2(fyk_mpa, gama_s)
    return (fyd / E_S) * 1000.0


def x2lim(d_cm: float) -> float:
    """Limite x entre dominios 2 e 3 (Grupo I, eps_cu = 3.5 %o). Eq. 3.13."""
    return 0.26 * d_cm


def x3lim(d_cm: float, fyk_mpa: float = 500.0,
          gama_s: float = GAMA_S) -> float:
    """Limite x entre dominios 3 e 4. Eq. 3.14."""
    eps_yd = eps_yd_permil(fyk_mpa, gama_s)
    return EPS_CU / (eps_yd + EPS_CU) * d_cm


def dominio(x_cm: float, d_cm: float, fyk_mpa: float = 500.0) -> int:
    """Retorna o dominio de deformacao (2, 3 ou 4)."""
    if x_cm <= x2lim(d_cm):
        return 2
    if x_cm <= x3lim(d_cm, fyk_mpa):
        return 3
    return 4


def as_min(bw_cm: float, h_cm: float, fck_mpa: float) -> float:
    """Armadura minima de flexao (cm2). Tabela 17.3 da NBR 6118."""
    fck_int = int(round(fck_mpa))
    rho = RHO_MIN_TABELA.get(fck_int, 0.00208)
    return rho * bw_cm * h_cm


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------
@dataclass
class ResultadoFlexao:
    Md: float           # kN.cm (valor absoluto)
    bw: float           # cm
    d: float            # cm
    h: float            # cm
    fck: float          # MPa
    fyk: float          # MPa

    x: float            # cm (posicao da linha neutra)
    beta_x: float       # x/d
    dominio: int        # 2, 3 ou 4
    As: float           # cm2 (armadura tracionada)
    As_linha: float = 0.0     # cm2 (armadura comprimida; 0 se simples)
    As_min: float = 0.0       # cm2
    eps_cd: float = 0.0       # %o (concreto comprimido, fibra mais externa)
    eps_sd: float = 0.0       # %o (armadura tracionada)
    M1d: float = 0.0          # kN.cm (parcela do M associada a As1)
    M2d: float = 0.0          # kN.cm (parcela do M associada a A's ou mesa)
    tipo: str = "simples"
    erro: str = ""


# ---------------------------------------------------------------------------
# 1. Secao retangular - armadura simples (apostila item 7)
# ---------------------------------------------------------------------------
def secao_retangular_simples(
    Md_kncm: float,
    bw_cm: float,
    d_cm: float,
    h_cm: float,
    fck_mpa: float,
    fyk_mpa: float = 500.0,
    gama_c: float = GAMA_C,
    gama_s: float = GAMA_S,
) -> ResultadoFlexao:
    """Dimensiona armadura simples para secao retangular.

    Equacao 23 da apostila: |Md| = 0.68 bw x fcd (d - 0.4 x).
    Resolve quadratica em x e calcula As pela Eq. 25 com sigma_sd = fyd
    (valido nos dominios 2 e 3).
    """
    Md = abs(Md_kncm)
    fcd = fcd_kncm2(fck_mpa, gama_c)
    fyd = fyd_kncm2(fyk_mpa, gama_s)

    # 0.272 fcd bw x^2 - 0.68 fcd bw d x + Md = 0
    a = 0.272 * fcd * bw_cm
    b = -0.68 * fcd * bw_cm * d_cm
    c = Md

    disc = b * b - 4.0 * a * c
    if disc < 0:
        return ResultadoFlexao(
            Md=Md, bw=bw_cm, d=d_cm, h=h_cm, fck=fck_mpa, fyk=fyk_mpa,
            x=0, beta_x=0, dominio=0, As=0,
            erro=("Discriminante negativo: a secao nao resiste com armadura "
                  "simples. Use armadura dupla ou aumente h/fck."),
        )

    # Raiz menor (LN dentro da secao).
    x = (-b - math.sqrt(disc)) / (2.0 * a)
    beta_x = x / d_cm
    dom = dominio(x, d_cm, fyk_mpa)

    erro = ""
    if dom == 4 or beta_x > LIMITE_BETA_X:
        erro = (f"x/d = {beta_x:.3f} > {LIMITE_BETA_X} (limite NBR 6118 "
                f"14.6.4.3). Dimensionar com armadura dupla ou aumentar h.")

    As = Md / (fyd * (d_cm - 0.4 * x))

    if dom == 2:
        eps_sd = 10.0
        eps_cd = eps_sd * x / (d_cm - x) if d_cm > x else 0.0
    else:
        eps_cd = EPS_CU
        eps_sd = eps_cd * (d_cm - x) / x if x > 0 else 0.0

    return ResultadoFlexao(
        Md=Md, bw=bw_cm, d=d_cm, h=h_cm, fck=fck_mpa, fyk=fyk_mpa,
        x=x, beta_x=beta_x, dominio=dom,
        As=As, As_min=as_min(bw_cm, h_cm, fck_mpa),
        eps_cd=eps_cd, eps_sd=eps_sd, M1d=Md,
        tipo="simples", erro=erro,
    )


# ---------------------------------------------------------------------------
# 2. Secao retangular - armadura dupla (apostila item 8)
# ---------------------------------------------------------------------------
def secao_retangular_dupla(
    Md_kncm: float,
    bw_cm: float,
    d_cm: float,
    d_linha_cm: float,
    h_cm: float,
    fck_mpa: float,
    fyk_mpa: float = 500.0,
    beta_x_lim: float = LIMITE_BETA_X,
    gama_c: float = GAMA_C,
    gama_s: float = GAMA_S,
) -> ResultadoFlexao:
    """Dimensiona armadura dupla fixando x = beta_x_lim * d (item 8).

    Decompoe Md = M1d + M2d (Eq. 39):
      M1d = 0.68 bw x fcd (d - 0.4 x)   - resistido por As1 + concreto.
      M2d = Md - M1d                     - resistido por A's e As2.

    A tensao na armadura comprimida sigma'_sd eh calculada por
    compatibilidade de deformacoes (Eq. 48), limitada a fyd.
    """
    Md = abs(Md_kncm)
    fcd = fcd_kncm2(fck_mpa, gama_c)
    fyd = fyd_kncm2(fyk_mpa, gama_s)

    x = beta_x_lim * d_cm
    M1d = 0.68 * bw_cm * x * fcd * (d_cm - 0.4 * x)
    M2d = Md - M1d

    if M2d <= 0:
        # Armadura simples ja resolve com folga; redireciona.
        return secao_retangular_simples(
            Md, bw_cm, d_cm, h_cm, fck_mpa, fyk_mpa, gama_c, gama_s,
        )

    # Deformacao na armadura comprimida (Eq. 48):
    # eps'_sd / (x - d') = eps_cu / x
    eps_sd_linha = EPS_CU * (x - d_linha_cm) / x  # %o
    eps_yd = eps_yd_permil(fyk_mpa, gama_s)
    if eps_sd_linha >= eps_yd:
        sigma_sd_linha = fyd  # kN/cm2
    else:
        # Lei de Hooke no trecho elastico do aco.
        sigma_sd_linha = (eps_sd_linha / 1000.0) * E_S

    As_linha = M2d / (sigma_sd_linha * (d_cm - d_linha_cm))

    # Armadura tracionada total: As = As1 + As2 (Eq. 46).
    As1 = M1d / (fyd * (d_cm - 0.4 * x))
    As2 = M2d / (fyd * (d_cm - d_linha_cm))
    As = As1 + As2

    eps_sd = EPS_CU * (d_cm - x) / x

    return ResultadoFlexao(
        Md=Md, bw=bw_cm, d=d_cm, h=h_cm, fck=fck_mpa, fyk=fyk_mpa,
        x=x, beta_x=x / d_cm, dominio=dominio(x, d_cm, fyk_mpa),
        As=As, As_linha=As_linha, As_min=as_min(bw_cm, h_cm, fck_mpa),
        eps_cd=EPS_CU, eps_sd=eps_sd, M1d=M1d, M2d=M2d,
        tipo="dupla", erro="",
    )


# ---------------------------------------------------------------------------
# 3. Secao T - armadura simples (apostila item 9)
# ---------------------------------------------------------------------------
def secao_T_simples(
    Md_kncm: float,
    bw_cm: float,
    bf_cm: float,
    hf_cm: float,
    d_cm: float,
    h_cm: float,
    fck_mpa: float,
    fyk_mpa: float = 500.0,
    gama_c: float = GAMA_C,
    gama_s: float = GAMA_S,
) -> ResultadoFlexao:
    """Dimensiona secao T com armadura simples.

    Caso A (0.8x <= hf): a regiao comprimida cabe na mesa, calcula como
        secao retangular bf x h.
    Caso B (0.8x > hf): a regiao comprimida invade a alma; decompoe a
        secao em mesa colaborante (Eq. 58) + alma (Eq. 60).
    """
    Md = abs(Md_kncm)
    fcd = fcd_kncm2(fck_mpa, gama_c)
    fyd = fyd_kncm2(fyk_mpa, gama_s)

    # Tentativa: secao retangular bf x h.
    r_ret = secao_retangular_simples(
        Md, bf_cm, d_cm, h_cm, fck_mpa, fyk_mpa, gama_c, gama_s,
    )
    if r_ret.erro:
        r_ret.tipo = "T (insuficiente como retangular)"
        return r_ret

    if 0.8 * r_ret.x <= hf_cm:
        # Caso A: 0.8x cabe na mesa.
        r_ret.tipo = "T (mesa, 0.8x <= hf)"
        # As_min usa bw da nervura, nao bf.
        r_ret.As_min = as_min(bw_cm, h_cm, fck_mpa)
        return r_ret

    # Caso B: 0.8x > hf. Decompoe a secao.
    M1d = ((bf_cm - bw_cm) * hf_cm * ALPHA_C * fcd
           * (d_cm - 0.5 * hf_cm))
    M2d = Md - M1d

    # M2d na alma (bw): equacao retangular para x.
    a = 0.272 * fcd * bw_cm
    b = -0.68 * fcd * bw_cm * d_cm
    c = M2d

    disc = b * b - 4.0 * a * c
    if disc < 0:
        return ResultadoFlexao(
            Md=Md, bw=bw_cm, d=d_cm, h=h_cm, fck=fck_mpa, fyk=fyk_mpa,
            x=0, beta_x=0, dominio=0, As=0,
            tipo="T (insuficiente)", M1d=M1d, M2d=M2d,
            erro=("Secao T insuficiente para armadura simples. Aumentar h "
                  "ou usar armadura dupla."),
        )

    x = (-b - math.sqrt(disc)) / (2.0 * a)
    beta_x = x / d_cm
    dom = dominio(x, d_cm, fyk_mpa)

    erro = ""
    if dom == 4 or beta_x > LIMITE_BETA_X:
        erro = (f"x/d = {beta_x:.3f} > {LIMITE_BETA_X} (limite NBR 6118). "
                f"Aumentar h ou usar armadura dupla.")

    As1 = M1d / (fyd * (d_cm - 0.5 * hf_cm))
    As2 = M2d / (fyd * (d_cm - 0.4 * x))
    As = As1 + As2

    if dom == 2:
        eps_sd = 10.0
        eps_cd = eps_sd * x / (d_cm - x) if d_cm > x else 0.0
    else:
        eps_cd = EPS_CU
        eps_sd = eps_cd * (d_cm - x) / x if x > 0 else 0.0

    return ResultadoFlexao(
        Md=Md, bw=bw_cm, d=d_cm, h=h_cm, fck=fck_mpa, fyk=fyk_mpa,
        x=x, beta_x=beta_x, dominio=dom,
        As=As, As_min=as_min(bw_cm, h_cm, fck_mpa),
        eps_cd=eps_cd, eps_sd=eps_sd, M1d=M1d, M2d=M2d,
        tipo="T (alma + mesa)", erro=erro,
    )


# ---------------------------------------------------------------------------
# 4. Verificacao - momento resistente dado As (apostila item 7.3, ex. 4 e 5)
# ---------------------------------------------------------------------------
def momento_resistente_simples(
    As_cm2: float,
    bw_cm: float,
    d_cm: float,
    fck_mpa: float,
    fyk_mpa: float = 500.0,
    gama_c: float = GAMA_C,
    gama_s: float = GAMA_S,
) -> tuple[float, float, int]:
    """Retorna (MRd em kN.cm, x em cm, dominio) para uma secao retangular.

    Supoe sigma_sd = fyd (valido nos dominios 2 e 3). A posicao da LN sai
    do equilibrio de forcas: 0.68 bw x fcd = As fyd  ->  x = As fyd / (0.68 bw fcd).
    """
    fcd = fcd_kncm2(fck_mpa, gama_c)
    fyd = fyd_kncm2(fyk_mpa, gama_s)
    x = (As_cm2 * fyd) / (0.68 * bw_cm * fcd)
    MRd = 0.68 * bw_cm * x * fcd * (d_cm - 0.4 * x)
    return MRd, x, dominio(x, d_cm, fyk_mpa)


# ---------------------------------------------------------------------------
# Impressao
# ---------------------------------------------------------------------------
def imprimir(r: ResultadoFlexao) -> None:
    print(f"=== {r.tipo.upper()} ===")
    print(f"  Md  = {r.Md:>9.1f} kN.cm  | bw = {r.bw:.1f} cm | "
          f"d = {r.d:.2f} cm | h = {r.h:.1f} cm")
    print(f"  fck = {r.fck:>4.0f} MPa     | fyk = {r.fyk:.0f} MPa")
    if r.erro:
        print(f"  ATENCAO: {r.erro}")
    print(f"  x   = {r.x:>6.2f} cm  | x/d = {r.beta_x:.3f}  | "
          f"dominio {r.dominio}")
    print(f"  As  = {r.As:>6.2f} cm2  (As,min = {r.As_min:.2f} cm2)")
    if r.As_linha > 0:
        print(f"  A's = {r.As_linha:>6.2f} cm2  (armadura comprimida)")
    if r.M1d and r.M2d:
        print(f"  M1d = {r.M1d:.1f} kN.cm  | M2d = {r.M2d:.1f} kN.cm")
    print(f"  eps_cd = {r.eps_cd:.2f} %o  |  eps_sd = {r.eps_sd:.2f} %o")


# ---------------------------------------------------------------------------
# Testes contra exemplos numericos da apostila
# ---------------------------------------------------------------------------
def teste_apostila_7_3_ex1() -> bool:
    """Apostila 7.3 ex.1: bw=20, h=50, d=47, C20, CA-50, Mk=+10000.
    Esperado: x ~ 18.1 cm, dom 3, As ~ 8.10 cm2."""
    r = secao_retangular_simples(
        Md_kncm=14000.0, bw_cm=20, d_cm=47, h_cm=50, fck_mpa=20,
    )
    print("\n--- Apostila 7.3 ex.1 (armadura simples, dominio 3) ---")
    imprimir(r)
    ok = (abs(r.x - 18.1) < 0.2 and abs(r.As - 8.10) < 0.1
          and r.dominio == 3 and not r.erro)
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_apostila_7_3_ex3() -> bool:
    """Apostila 7.3 ex.3: bw=22, h=60, d=55, C25, CA-50, Mk=-15000.
    Esperado: x ~ 16.2, dom 3, As ~ 9.95."""
    r = secao_retangular_simples(
        Md_kncm=21000.0, bw_cm=22, d_cm=55, h_cm=60, fck_mpa=25,
    )
    print("\n--- Apostila 7.3 ex.3 (armadura simples, momento negativo) ---")
    imprimir(r)
    ok = (abs(r.x - 16.2) < 0.3 and abs(r.As - 9.95) < 0.1
          and r.dominio == 3 and not r.erro)
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_apostila_7_3_ex4() -> bool:
    """Apostila 7.3 ex.4 (verificacao): bw=20, h=50, d=46, As=8.00, C20.
    Esperado: x ~ 17.9, Mk ~ 9650 kN.cm, dom 3."""
    MRd, x, dom = momento_resistente_simples(
        As_cm2=8.00, bw_cm=20, d_cm=46, fck_mpa=20,
    )
    Mk = MRd / GAMA_F
    print("\n--- Apostila 7.3 ex.4 (verificacao) ---")
    print(f"  As = 8.00 cm2 | bw=20 | d=46 | C20 | CA-50")
    print(f"  x   = {x:.2f} cm  | dominio {dom}")
    print(f"  MRd = {MRd:.1f} kN.cm  ->  Mk = {Mk:.1f} kN.cm")
    ok = abs(x - 17.9) < 0.2 and abs(Mk - 9650) < 30 and dom == 3
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_apostila_8_3_ex1() -> bool:
    """Apostila 8.3 ex.1 (armadura dupla): bw=20, h=50, d=45, d'=3, C25,
    Mk=-15700. Esperado: As ~ 13.41, A's ~ 2.10, x = 0.45*45 = 20.25."""
    r = secao_retangular_dupla(
        Md_kncm=21980.0, bw_cm=20, d_cm=45, d_linha_cm=3, h_cm=50,
        fck_mpa=25,
    )
    print("\n--- Apostila 8.3 ex.1 (armadura dupla) ---")
    imprimir(r)
    ok = (abs(r.x - 20.25) < 0.1 and abs(r.As - 13.41) < 0.1
          and abs(r.As_linha - 2.10) < 0.1)
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_apostila_8_3_ex2() -> bool:
    """Apostila 8.3 ex.2 (armadura dupla): bw=14, h=60, d=54, d'=4, C30,
    Mk=-18500. Esperado: As ~ 13.17, A's ~ 2.03.

    Apostila resolve via Kc tabelado (Kc lim = 1.9, valor arredondado da
    Tabela A-1) e da M1d = 21.486 kN.cm. Este script usa a equacao direta
    (Eq. 40), mais precisa, e da M1d ~ 21.953 -> A's ~ 1.82, As ~ 13.22.
    Tolerancia maior cobre o arredondamento da tabela."""
    r = secao_retangular_dupla(
        Md_kncm=25900.0, bw_cm=14, d_cm=54, d_linha_cm=4, h_cm=60,
        fck_mpa=30,
    )
    print("\n--- Apostila 8.3 ex.2 (armadura dupla, viga estreita) ---")
    imprimir(r)
    ok = (abs(r.x - 24.30) < 0.2 and abs(r.As - 13.17) < 0.3
          and abs(r.As_linha - 2.03) < 0.3)
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_apostila_9_2_ex1() -> bool:
    """Apostila 9.2.4 ex.1 (T): bf=100, hf=8, bw=20, h=50, d=45, C20,
    Mk=+15000. 0.8x < hf -> mesa colaborante toda comprimida.
    Esperado: x ~ 5.0, dom 2, As ~ 11.23."""
    r = secao_T_simples(
        Md_kncm=21000.0, bw_cm=20, bf_cm=100, hf_cm=8,
        d_cm=45, h_cm=50, fck_mpa=20,
    )
    print("\n--- Apostila 9.2.4 ex.1 (T - 0.8x < hf) ---")
    imprimir(r)
    ok = (abs(r.x - 5.0) < 0.2 and abs(r.As - 11.23) < 0.1
          and r.dominio == 2)
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_apostila_9_2_ex2() -> bool:
    """Apostila 9.2.4 ex.2 (T): bf=45, hf=7, bw=18, h=30, d=25, C25,
    Mk=+8000. 0.8x > hf -> formulacao T propria.
    Esperado: x ~ 11.2, dom 3, As ~ 12.20."""
    r = secao_T_simples(
        Md_kncm=11200.0, bw_cm=18, bf_cm=45, hf_cm=7,
        d_cm=25, h_cm=30, fck_mpa=25,
    )
    print("\n--- Apostila 9.2.4 ex.2 (T - 0.8x > hf) ---")
    imprimir(r)
    ok = (abs(r.x - 11.2) < 0.2 and abs(r.As - 12.20) < 0.2
          and r.dominio == 3)
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def teste_apostila_9_2_ex3() -> bool:
    """Apostila 9.2.4 ex.3 (laje nervurada): bf=60, hf=4, bw=10, h=29, d=26.5,
    C30, Mk=+1350. Esperado: 0.8x < hf, dom 2, As ~ 1.64 cm2/nervura."""
    r = secao_T_simples(
        Md_kncm=1890.0, bw_cm=10, bf_cm=60, hf_cm=4,
        d_cm=26.5, h_cm=29, fck_mpa=30,
    )
    print("\n--- Apostila 9.2.4 ex.3 (laje nervurada) ---")
    imprimir(r)
    ok = (abs(r.x - 0.8) < 0.3 and abs(r.As - 1.64) < 0.1
          and r.dominio == 2)
    print(f"  {'PASSOU' if ok else 'FALHOU'}")
    return ok


def rodar_testes() -> bool:
    resultados = [
        teste_apostila_7_3_ex1(),
        teste_apostila_7_3_ex3(),
        teste_apostila_7_3_ex4(),
        teste_apostila_8_3_ex1(),
        teste_apostila_8_3_ex2(),
        teste_apostila_9_2_ex1(),
        teste_apostila_9_2_ex2(),
        teste_apostila_9_2_ex3(),
    ]
    total = len(resultados)
    aprov = sum(resultados)
    print(f"\n{'='*60}")
    print(f"  {aprov}/{total} testes passaram.")
    print(f"{'='*60}")
    return all(resultados)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if "--test" in sys.argv:
        sys.exit(0 if rodar_testes() else 1)

    # Sem flag: roda os exemplos da apostila como demonstracao.
    rodar_testes()


if __name__ == "__main__":
    main()
