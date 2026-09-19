"""Flexao Normal Simples - Vigas em Concreto Armado (NBR 6118:2023).

Nome ate 19/09/2026: vigas_bastos.py. O credito as apostilas esta abaixo.

Implementa o dimensionamento das vigas a flexao simples seguindo a apostila
"FLEXAO NORMAL SIMPLES - VIGAS" (Out/2023), Prof. Paulo Sergio Bastos,
UNESP/Bauru, baseada na NBR 6118:2023.

Casos cobertos:
    - Secao retangular com armadura simples (apostila item 7).
    - Secao retangular com armadura dupla (item 8).
    - Secao T com armadura simples (item 9).
    - Verificacao: momento resistente dado As (problema inverso).

Convencoes da apostila:
    - Diagrama retangular simplificado com y = lambda*x e sigma_cd =
      alpha_c*eta_c*fcd (Eq. 15-16 da apostila, generalizadas pelo nucleo
      normativo para o Grupo II tambem - NBR 6118:2026 17.2.2 e), 8.2.10.1).
    - Limite de dutilidade NBR 6118:2026 14.6.4.3: x/d <= 0.45 ate C50 e
      x/d <= 0.35 de C55 a C90 (nbr.xd_limite_dutilidade).
    - Aco CA-50 (fyk = 500 MPa) por padrao.
    - Coeficientes de ponderacao: gama_c = 1.4, gama_s = 1.15, gama_f = 1.4
      (combinacao normal).
    - Unidades: kN e cm em todas as funcoes (igual aos coeficientes K
      tabelados pelo professor).

As grandezas de material (fcd, fyd, eps_cu, lambda, tensao do bloco
retangular, x/d-limite e rho_min) delegam ao nucleo normativo
(nucleo_nbr6118.py); nao reimplemente essas formulas aqui.

Estrutura segue:
    - alv_est/viga_mista_v3.py: dataclasses de resultado, funcoes puras,
      testes contra exemplos numericos do livro.
    - open6118/dimensionamento/vigas.py: funcoes de calculo isoladas, sem GUI.
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
GAMA_C = 1.4
GAMA_S = 1.15
GAMA_F = 1.4

E_S = 21000.0          # kN/cm2 (modulo de elasticidade do aco - 210 GPa).
EPS_CU = 3.5           # %o (deformacao ultima do concreto, fck <= 50 MPa;
                       # valor de referencia do Grupo I - use nbr.eps_cu(fck)).
EPS_C2 = 2.0           # %o (idem, fck <= 50 MPa; use nbr.eps_c2(fck)).
LIMITE_BETA_X = 0.45   # NBR 6118 14.6.4.3 para fck <= 50 MPa; valor de
                       # referencia - use nbr.xd_limite_dutilidade(fck).
ALPHA_C = 0.85         # Coef. de referencia (fck <= 50); use nbr.alpha_c(fck).

# Taxas minimas de armadura de flexao (Tabela 17.3 da NBR 6118), so ate C50.
# Mantida para referencia; as_min() delega a nbr.rho_min_flexao(fck), que
# cobre C20 a C90 com interpolacao entre classes (corrige VIG-08).
RHO_MIN_TABELA = {
    20: 0.00150, 25: 0.00150, 30: 0.00150, 35: 0.00164, 40: 0.00179,
    45: 0.00194, 50: 0.00208,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fcd_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fck em MPa -> fcd em kN/cm2, delegado ao nucleo normativo (12.3.3)."""
    return nbr.mpa_para_kncm2(nbr.fcd(fck_mpa, gama_c))


def fyd_kncm2(fyk_mpa: float, gama_s: float = GAMA_S) -> float:
    """fyk em MPa -> fyd em kN/cm2, delegado ao nucleo normativo."""
    return nbr.mpa_para_kncm2(nbr.fyd(fyk_mpa, gama_s))


def eps_yd_permil(fyk_mpa: float, gama_s: float = GAMA_S) -> float:
    """Deformacao de inicio de escoamento em %o, delegado ao nucleo normativo."""
    return nbr.eps_yd(fyk_mpa, gama_s, nbr.ES_MPA)


def x2lim(d_cm: float, fck_mpa: float = 50.0) -> float:
    """Limite x entre dominios 2 e 3 (Fig. 17.1), delegado ao nucleo normativo.

    Antes fixo em 0.26*d (eps_cu = 3.5 %o, Grupo I); eps_cu agora depende de
    fck (nbr.eps_cu). fck_mpa entra no fim com padrao 50 (Grupo I) para nao
    quebrar quem chamava x2lim(d) sem fck.
    """
    return nbr.x_lim_dominio_2_3(d_cm, fck_mpa)


def x3lim(d_cm: float, fyk_mpa: float = 500.0, gama_s: float = GAMA_S,
          fck_mpa: float = 50.0) -> float:
    """Limite x entre dominios 3 e 4 (Fig. 17.1), delegado ao nucleo normativo.

    fck_mpa entra no fim com padrao 50 (Grupo I), pelo mesmo motivo de x2lim.
    """
    return nbr.x_lim_dominio_3_4(d_cm, fck_mpa, fyk_mpa, gama_s, nbr.ES_MPA)


def dominio(x_cm: float, d_cm: float, fyk_mpa: float = 500.0,
            fck_mpa: float = 50.0) -> int:
    """Retorna o dominio de deformacao (2, 3 ou 4)."""
    if x_cm <= x2lim(d_cm, fck_mpa):
        return 2
    if x_cm <= x3lim(d_cm, fyk_mpa, GAMA_S, fck_mpa):
        return 3
    return 4


def as_min(bw_cm: float, h_cm: float, fck_mpa: float) -> float:
    """Armadura minima de flexao (cm2), delegado ao nucleo normativo.

    Tabela 17.3 da NBR 6118:2026 (nbr.rho_min_flexao), interpolada entre
    classes e valida de C20 a C90 (corrige VIG-08: antes, fck fora dos
    multiplos de 5 ou acima de C50 caia no valor do C50)."""
    return nbr.rho_min_flexao(fck_mpa) * bw_cm * h_cm


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
    minimo_governou: bool = False   # True se As,min (17.3.5.2.1) > As de equilibrio


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
    bw_as_min_cm: float | None = None,
) -> ResultadoFlexao:
    """Dimensiona armadura simples para secao retangular.

    Generalizacao da Eq. 23 da apostila para o bloco retangular da NBR
    6118:2026 17.2.2 e): |Md| = lambda*bw*x*sigma_ret*(d - 0.5*lambda*x),
    com sigma_ret = alpha_c*eta_c*fcd (nbr.tensao_retangulo) e lambda =
    nbr.lambda_retangulo(fck) (0.8 ate C50; decrescente de C55 a C90).
    Antes usava 0.68/0.272/0.4 fixos (sigma = 0.85 fcd sem eta_c), o que
    subestima o bloco ja em C45/C50 (eta_c < 1) - VIG-02.
    Resolve quadratica em x e calcula As com sigma_sd = fyd
    (valido nos dominios 2 e 3). As,min (17.3.5.2.1) passa a ser aplicado
    ao resultado (As = max(As, As_min); antes so era informado - VIG-04).

    bw_as_min_cm: largura usada so para o As,min (17.3.5.2.1); por padrao
    igual a bw_cm. Uso: chamada de secao_T_simples no Caso A, que passa bf
    como bw_cm (bloco cabe na mesa) mas precisa do As,min com a largura da
    nervura, nao da mesa.
    """
    Md = abs(Md_kncm)
    fyd = fyd_kncm2(fyk_mpa, gama_s)
    lam = nbr.lambda_retangulo(fck_mpa)
    sigma_ret = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck_mpa, gama_c))
    limite_beta_x = nbr.xd_limite_dutilidade(fck_mpa)

    # 0.5*lambda^2*sigma_ret*bw*x^2 - lambda*sigma_ret*bw*d*x + Md = 0
    a = 0.5 * lam * lam * sigma_ret * bw_cm
    b = -lam * sigma_ret * bw_cm * d_cm
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
    dom = dominio(x, d_cm, fyk_mpa, fck_mpa)

    erro = ""
    if dom == 4 or beta_x > limite_beta_x:
        erro = (f"x/d = {beta_x:.3f} > {limite_beta_x:.2f} (limite de "
                f"dutilidade NBR 6118:2026 14.6.4.3 para fck = {fck_mpa:g} "
                f"MPa). Dimensione com armadura dupla ou aumente h.")

    As = Md / (fyd * (d_cm - 0.5 * lam * x))

    if dom == 2:
        eps_sd = nbr.EPS_SU
        eps_cd = eps_sd * x / (d_cm - x) if d_cm > x else 0.0
    else:
        eps_cd = nbr.eps_cu(fck_mpa)
        eps_sd = eps_cd * (d_cm - x) / x if x > 0 else 0.0

    largura_as_min = bw_cm if bw_as_min_cm is None else bw_as_min_cm
    As_min_val = as_min(largura_as_min, h_cm, fck_mpa)
    minimo_governou = As < As_min_val
    As = max(As, As_min_val)

    return ResultadoFlexao(
        Md=Md, bw=bw_cm, d=d_cm, h=h_cm, fck=fck_mpa, fyk=fyk_mpa,
        x=x, beta_x=beta_x, dominio=dom,
        As=As, As_min=As_min_val,
        eps_cd=eps_cd, eps_sd=eps_sd, M1d=Md,
        tipo="simples", erro=erro, minimo_governou=minimo_governou,
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
    beta_x_lim: float | None = LIMITE_BETA_X,
    gama_c: float = GAMA_C,
    gama_s: float = GAMA_S,
) -> ResultadoFlexao:
    """Dimensiona armadura dupla fixando x = beta_x_lim * d (item 8).

    Decompoe Md = M1d + M2d (Eq. 39), generalizado pelo bloco retangular da
    NBR 6118:2026 17.2.2 e) (nbr.tensao_retangulo, nbr.lambda_retangulo):
      M1d = lambda*bw*x*sigma_ret*(d - 0.5*lambda*x) - resistido por As1 + concreto.
      M2d = Md - M1d                                  - resistido por A's e As2.
    Antes usava 0.68*fcd*(d-0.4x) fixo (sigma = 0.85 fcd sem eta_c); com x
    fixo em beta_x_lim*d o erro nao se cancela e se concentra em A's
    (VIG-01: -41% em C50).

    beta_x_lim: None usa o limite de dutilidade do fck
    (nbr.xd_limite_dutilidade - 0.45 ate C50, 0.35 de C55 a C90; VIG-03).
    O padrao do parametro continua LIMITE_BETA_X (0.45) por compatibilidade
    com quem ja chamava esta funcao sem argumentos nomeados; passe
    beta_x_lim=None para usar o limite correto tambem em fck > 50.

    A tensao na armadura comprimida sigma'_sd eh calculada por
    compatibilidade de deformacoes (Eq. 48), limitada a fyd. As,min
    (17.3.5.2.1) passa a ser aplicado ao As total (VIG-04).
    """
    Md = abs(Md_kncm)
    fyd = fyd_kncm2(fyk_mpa, gama_s)
    if beta_x_lim is None:
        beta_x_lim = nbr.xd_limite_dutilidade(fck_mpa)
    lam = nbr.lambda_retangulo(fck_mpa)
    sigma_ret = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck_mpa, gama_c))

    x = beta_x_lim * d_cm
    M1d = lam * bw_cm * x * sigma_ret * (d_cm - 0.5 * lam * x)
    M2d = Md - M1d

    if M2d <= 0:
        # Armadura simples ja resolve com folga; redireciona.
        return secao_retangular_simples(
            Md, bw_cm, d_cm, h_cm, fck_mpa, fyk_mpa, gama_c, gama_s,
        )

    # Deformacao na armadura comprimida (Eq. 48):
    # eps'_sd / (x - d') = eps_cu / x
    eps_cu_val = nbr.eps_cu(fck_mpa)
    eps_sd_linha = eps_cu_val * (x - d_linha_cm) / x  # %o
    eps_yd = eps_yd_permil(fyk_mpa, gama_s)
    if eps_sd_linha >= eps_yd:
        sigma_sd_linha = fyd  # kN/cm2
    else:
        # Lei de Hooke no trecho elastico do aco.
        sigma_sd_linha = (eps_sd_linha / 1000.0) * E_S

    As_linha = M2d / (sigma_sd_linha * (d_cm - d_linha_cm))

    # Armadura tracionada total: As = As1 + As2 (Eq. 46).
    As1 = M1d / (fyd * (d_cm - 0.5 * lam * x))
    As2 = M2d / (fyd * (d_cm - d_linha_cm))
    As = As1 + As2

    eps_sd = eps_cu_val * (d_cm - x) / x

    As_min_val = as_min(bw_cm, h_cm, fck_mpa)
    minimo_governou = As < As_min_val
    As = max(As, As_min_val)

    return ResultadoFlexao(
        Md=Md, bw=bw_cm, d=d_cm, h=h_cm, fck=fck_mpa, fyk=fyk_mpa,
        x=x, beta_x=x / d_cm, dominio=dominio(x, d_cm, fyk_mpa, fck_mpa),
        As=As, As_linha=As_linha, As_min=As_min_val,
        eps_cd=eps_cu_val, eps_sd=eps_sd, M1d=M1d, M2d=M2d,
        tipo="dupla", erro="", minimo_governou=minimo_governou,
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

    Caso A (lambda*x <= hf): a regiao comprimida cabe na mesa, calcula como
        secao retangular bf x h.
    Caso B (lambda*x > hf): a regiao comprimida invade a alma; decompoe a
        secao em mesa colaborante (Eq. 58) + alma (Eq. 60).

    O bloco retangular usa nbr.tensao_retangulo (alpha_c*eta_c*fcd) e
    nbr.lambda_retangulo(fck) em vez de 0.85*fcd e lambda=0.8 fixos
    (VIG-02: sem eta_c, ja incorreto em C45/C50). A fronteira do Caso A
    tambem usa lambda(fck) em vez de 0.8 fixo, pela mesma razao.
    """
    Md = abs(Md_kncm)
    fyd = fyd_kncm2(fyk_mpa, gama_s)
    lam = nbr.lambda_retangulo(fck_mpa)
    sigma_ret = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck_mpa, gama_c))
    limite_beta_x = nbr.xd_limite_dutilidade(fck_mpa)

    # Tentativa: secao retangular bf x h. As,min usa bw da nervura, nao bf
    # (bw_as_min_cm evita que secao_retangular_simples aplique o piso de
    # As,min com a largura errada - complemento de VIG-04 para secao T).
    r_ret = secao_retangular_simples(
        Md, bf_cm, d_cm, h_cm, fck_mpa, fyk_mpa, gama_c, gama_s,
        bw_as_min_cm=bw_cm,
    )
    if r_ret.erro:
        r_ret.tipo = "T (insuficiente como retangular)"
        return r_ret

    if lam * r_ret.x <= hf_cm:
        # Caso A: lambda*x cabe na mesa.
        r_ret.tipo = "T (mesa, lambda*x <= hf)"
        return r_ret

    # Caso B: lambda*x > hf. Decompoe a secao.
    M1d = (bf_cm - bw_cm) * hf_cm * sigma_ret * (d_cm - 0.5 * hf_cm)
    M2d = Md - M1d

    # M2d na alma (bw): equacao retangular para x (mesmo bloco de VIG-01/02).
    a = 0.5 * lam * lam * sigma_ret * bw_cm
    b = -lam * sigma_ret * bw_cm * d_cm
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
    dom = dominio(x, d_cm, fyk_mpa, fck_mpa)

    erro = ""
    if dom == 4 or beta_x > limite_beta_x:
        erro = (f"x/d = {beta_x:.3f} > {limite_beta_x:.2f} (limite de "
                f"dutilidade NBR 6118:2026 14.6.4.3 para fck = {fck_mpa:g} "
                f"MPa). Aumente h ou use armadura dupla.")

    As1 = M1d / (fyd * (d_cm - 0.5 * hf_cm))
    As2 = M2d / (fyd * (d_cm - 0.5 * lam * x))
    As = As1 + As2

    if dom == 2:
        eps_sd = nbr.EPS_SU
        eps_cd = eps_sd * x / (d_cm - x) if d_cm > x else 0.0
    else:
        eps_cd = nbr.eps_cu(fck_mpa)
        eps_sd = eps_cd * (d_cm - x) / x if x > 0 else 0.0

    As_min_val = as_min(bw_cm, h_cm, fck_mpa)
    minimo_governou = As < As_min_val
    As = max(As, As_min_val)

    return ResultadoFlexao(
        Md=Md, bw=bw_cm, d=d_cm, h=h_cm, fck=fck_mpa, fyk=fyk_mpa,
        x=x, beta_x=beta_x, dominio=dom,
        As=As, As_min=As_min_val,
        eps_cd=eps_cd, eps_sd=eps_sd, M1d=M1d, M2d=M2d,
        tipo="T (alma + mesa)", erro=erro, minimo_governou=minimo_governou,
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
    do equilibrio de forcas com o bloco retangular da NBR 6118:2026
    17.2.2 e): lambda*bw*x*sigma_ret = As*fyd -> x = As*fyd/(lambda*bw*sigma_ret),
    com sigma_ret = nbr.tensao_retangulo(fck) e lambda = nbr.lambda_retangulo(fck)
    (antes 0.68*fcd fixo, sem eta_c - VIG-02).
    """
    fyd = fyd_kncm2(fyk_mpa, gama_s)
    lam = nbr.lambda_retangulo(fck_mpa)
    sigma_ret = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck_mpa, gama_c))
    x = (As_cm2 * fyd) / (lam * bw_cm * sigma_ret)
    MRd = lam * bw_cm * x * sigma_ret * (d_cm - 0.5 * lam * x)
    return MRd, x, dominio(x, d_cm, fyk_mpa, fck_mpa)


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
    if r.minimo_governou:
        print(f"  (As,min governou o dimensionamento - NBR 6118 17.3.5.2.1)")
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
