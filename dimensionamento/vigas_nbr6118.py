"""Flexão Normal Simples - Vigas em Concreto Armado (NBR 6118:2023).

Nome até 19/09/2026: vigas_bastos.py. O crédito às apostilas está abaixo.

Implementa o dimensionamento das vigas à flexão simples seguindo a apostila
"FLEXÃO NORMAL SIMPLES - VIGAS" (Out/2023), Prof. Paulo Sérgio Bastos,
UNESP/Bauru, baseada na NBR 6118:2023.

Casos cobertos:
    - Seção retangular com armadura simples (apostila item 7).
    - Seção retangular com armadura dupla (item 8).
    - Seção T com armadura simples (item 9).
    - Verificação: momento resistente dado As (problema inverso).

Convenções da apostila:
    - Diagrama retangular simplificado com y = lambda*x e sigma_cd =
      alpha_c*eta_c*fcd (Eq. 15-16 da apostila, generalizadas pelo núcleo
      normativo para o Grupo II também - NBR 6118:2026 17.2.2 e), 8.2.10.1).
    - Limite de dutilidade NBR 6118:2026 14.6.4.3: x/d <= 0.45 até C50 e
      x/d <= 0.35 de C55 a C90 (nbr.xd_limite_dutilidade).
    - Aço CA-50 (fyk = 500 MPa) por padrão.
    - Coeficientes de ponderação: gama_c = 1.4, gama_s = 1.15, gama_f = 1.4
      (combinação normal).
    - Unidades: kN e cm em todas as funções (igual aos coeficientes K
      tabelados pelo professor).

As grandezas de material (fcd, fyd, eps_cu, lambda, tensão do bloco
retangular, x/d-limite e rho_min) delegam ao núcleo normativo
(nucleo_nbr6118.py); não reimplemente essas fórmulas aqui.

Estrutura segue:
    - alv_est/viga_mista_v3.py: dataclasses de resultado, funções puras,
      testes contra exemplos numéricos do livro.
    - open6118/dimensionamento/vigas.py: funções de cálculo isoladas, sem GUI.
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
GAMA_C = nbr.GAMA_C  # lido do núcleo (C1: era literal 1.4)
GAMA_S = nbr.GAMA_S  # lido do núcleo (C1: era literal 1.15)
GAMA_F = nbr.GAMA_F  # Tabela 11.1 — lido do núcleo (P4)

E_S = 21000.0          # kN/cm2 (módulo de elasticidade do aço - 210 GPa).
EPS_CU = 3.5           # %o (deformação última do concreto, fck <= 50 MPa;
                       # valor de referência do Grupo I - use nbr.eps_cu(fck)).
EPS_C2 = 2.0           # %o (idem, fck <= 50 MPa; use nbr.eps_c2(fck)).
LIMITE_BETA_X = 0.45   # NBR 6118 14.6.4.3 para fck <= 50 MPa; valor de
                       # referência - use nbr.xd_limite_dutilidade(fck).
ALPHA_C = 0.85         # Coef. de referência (fck <= 50); use nbr.alpha_c(fck).

# Taxas mínimas de armadura de flexão (Tabela 17.3 da NBR 6118), só até C50.
# Mantida para referência; as_min() delega a nbr.rho_min_flexao(fck), que
# cobre C20 a C90 com interpolação entre classes (corrige VIG-08).
RHO_MIN_TABELA = {
    20: 0.00150, 25: 0.00150, 30: 0.00150, 35: 0.00164, 40: 0.00179,
    45: 0.00194, 50: 0.00208,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fcd_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fck em MPa -> fcd em kN/cm2, delegado ao núcleo normativo (12.3.3)."""
    return nbr.mpa_para_kncm2(nbr.fcd(fck_mpa, gama_c))


def fyd_kncm2(fyk_mpa: float, gama_s: float = GAMA_S) -> float:
    """fyk em MPa -> fyd em kN/cm2, delegado ao núcleo normativo."""
    return nbr.mpa_para_kncm2(nbr.fyd(fyk_mpa, gama_s))


def eps_yd_permil(fyk_mpa: float, gama_s: float = GAMA_S) -> float:
    """Deformação de início de escoamento em %o, delegado ao núcleo normativo."""
    return nbr.eps_yd(fyk_mpa, gama_s, nbr.ES_MPA)


def x2lim(d_cm: float, fck_mpa: float = 50.0) -> float:
    """Limite x entre domínios 2 e 3 (Fig. 17.1), delegado ao núcleo normativo.

    Antes fixo em 0.26*d (eps_cu = 3.5 %o, Grupo I); eps_cu agora depende de
    fck (nbr.eps_cu). fck_mpa entra no fim com padrão 50 (Grupo I) para não
    quebrar quem chamava x2lim(d) sem fck.
    """
    return nbr.x_lim_dominio_2_3(d_cm, fck_mpa)


def x3lim(d_cm: float, fyk_mpa: float = 500.0, gama_s: float = GAMA_S,
          fck_mpa: float = 50.0) -> float:
    """Limite x entre domínios 3 e 4 (Fig. 17.1), delegado ao núcleo normativo.

    fck_mpa entra no fim com padrão 50 (Grupo I), pelo mesmo motivo de x2lim.
    """
    return nbr.x_lim_dominio_3_4(d_cm, fck_mpa, fyk_mpa, gama_s, nbr.ES_MPA)


def dominio(x_cm: float, d_cm: float, fyk_mpa: float = 500.0,
            fck_mpa: float = 50.0) -> int:
    """Retorna o domínio de deformação (2, 3 ou 4)."""
    if x_cm <= x2lim(d_cm, fck_mpa):
        return 2
    if x_cm <= x3lim(d_cm, fyk_mpa, GAMA_S, fck_mpa):
        return 3
    return 4


def as_min(bw_cm: float, h_cm: float, fck_mpa: float) -> float:
    """Armadura mínima de flexão (cm2), delegado ao núcleo normativo.

    Tabela 17.3 da NBR 6118:2026 (nbr.rho_min_flexao), interpolada entre
    classes e válida de C20 a C90 (corrige VIG-08: antes, fck fora dos
    múltiplos de 5 ou acima de C50 caía no valor do C50)."""
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

    x: float            # cm (posição da linha neutra)
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
    minimo_governou: bool = False   # True se As,min (17.3.5.2.1) > As de equilíbrio


# ---------------------------------------------------------------------------
# 1. Seção retangular - armadura simples (apostila item 7)
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
    """Dimensiona armadura simples para seção retangular.

    Generalização da Eq. 23 da apostila para o bloco retangular da NBR
    6118:2026 17.2.2 e): |Md| = lambda*bw*x*sigma_ret*(d - 0.5*lambda*x),
    com sigma_ret = alpha_c*eta_c*fcd (nbr.tensao_retangulo) e lambda =
    nbr.lambda_retangulo(fck) (0.8 até C50; decrescente de C55 a C90).
    Antes usava 0.68/0.272/0.4 fixos (sigma = 0.85 fcd sem eta_c), o que
    subestima o bloco já em C45/C50 (eta_c < 1) - VIG-02.
    Resolve quadrática em x e calcula As com sigma_sd = fyd
    (válido nos domínios 2 e 3). As,min (17.3.5.2.1) passa a ser aplicado
    ao resultado (As = max(As, As_min); antes só era informado - VIG-04).

    bw_as_min_cm: largura usada só para o As,min (17.3.5.2.1); por padrão
    igual a bw_cm. Uso: chamada de secao_T_simples no Caso A, que passa bf
    como bw_cm (bloco cabe na mesa) mas precisa do As,min com a largura da
    nervura, não da mesa.
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
            erro=("Discriminante negativo: a seção não resiste com armadura "
                  "simples. Use armadura dupla ou aumente h/fck."),
        )

    # Raiz menor (LN dentro da seção).
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
# 2. Seção retangular - armadura dupla (apostila item 8)
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

    Decompõe Md = M1d + M2d (Eq. 39), generalizado pelo bloco retangular da
    NBR 6118:2026 17.2.2 e) (nbr.tensao_retangulo, nbr.lambda_retangulo):
      M1d = lambda*bw*x*sigma_ret*(d - 0.5*lambda*x) - resistido por As1 + concreto.
      M2d = Md - M1d                                  - resistido por A's e As2.
    Antes usava 0.68*fcd*(d-0.4x) fixo (sigma = 0.85 fcd sem eta_c); com x
    fixo em beta_x_lim*d o erro não se cancela e se concentra em A's
    (VIG-01: -41% em C50).

    beta_x_lim: None usa o limite de dutilidade do fck
    (nbr.xd_limite_dutilidade - 0.45 até C50, 0.35 de C55 a C90; VIG-03).
    O padrão do parâmetro continua LIMITE_BETA_X (0.45) por compatibilidade
    com quem já chamava esta função sem argumentos nomeados; passe
    beta_x_lim=None para usar o limite correto também em fck > 50.

    A tensão na armadura comprimida sigma'_sd é calculada por
    compatibilidade de deformações (Eq. 48), limitada a fyd. As,min
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
        # Armadura simples já resolve com folga; redireciona.
        return secao_retangular_simples(
            Md, bw_cm, d_cm, h_cm, fck_mpa, fyk_mpa, gama_c, gama_s,
        )

    # Deformação na armadura comprimida (Eq. 48):
    # eps'_sd / (x - d') = eps_cu / x
    eps_cu_val = nbr.eps_cu(fck_mpa)
    eps_sd_linha = eps_cu_val * (x - d_linha_cm) / x  # %o
    eps_yd = eps_yd_permil(fyk_mpa, gama_s)
    if eps_sd_linha >= eps_yd:
        sigma_sd_linha = fyd  # kN/cm2
    else:
        # Lei de Hooke no trecho elástico do aço.
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
# 3. Seção T - armadura simples (apostila item 9)
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
    """Dimensiona seção T com armadura simples.

    Caso A (lambda*x <= hf): a região comprimida cabe na mesa, calcula como
        seção retangular bf x h.
    Caso B (lambda*x > hf): a região comprimida invade a alma; decompõe a
        seção em mesa colaborante (Eq. 58) + alma (Eq. 60).

    O bloco retangular usa nbr.tensao_retangulo (alpha_c*eta_c*fcd) e
    nbr.lambda_retangulo(fck) em vez de 0.85*fcd e lambda=0.8 fixos
    (VIG-02: sem eta_c, já incorreto em C45/C50). A fronteira do Caso A
    também usa lambda(fck) em vez de 0.8 fixo, pela mesma razão.
    """
    Md = abs(Md_kncm)
    fyd = fyd_kncm2(fyk_mpa, gama_s)
    lam = nbr.lambda_retangulo(fck_mpa)
    sigma_ret = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck_mpa, gama_c))
    limite_beta_x = nbr.xd_limite_dutilidade(fck_mpa)

    # Tentativa: seção retangular bf x h. As,min usa bw da nervura, não bf
    # (bw_as_min_cm evita que secao_retangular_simples aplique o piso de
    # As,min com a largura errada - complemento de VIG-04 para seção T).
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

    # Caso B: lambda*x > hf. Decompõe a seção.
    M1d = (bf_cm - bw_cm) * hf_cm * sigma_ret * (d_cm - 0.5 * hf_cm)
    M2d = Md - M1d

    # M2d na alma (bw): equação retangular para x (mesmo bloco de VIG-01/02).
    a = 0.5 * lam * lam * sigma_ret * bw_cm
    b = -lam * sigma_ret * bw_cm * d_cm
    c = M2d

    disc = b * b - 4.0 * a * c
    if disc < 0:
        return ResultadoFlexao(
            Md=Md, bw=bw_cm, d=d_cm, h=h_cm, fck=fck_mpa, fyk=fyk_mpa,
            x=0, beta_x=0, dominio=0, As=0,
            tipo="T (insuficiente)", M1d=M1d, M2d=M2d,
            erro=("Seção T insuficiente para armadura simples. Aumentar h "
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
# 4. Verificação - momento resistente dado As (apostila item 7.3, ex. 4 e 5)
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
    """Retorna (MRd em kN.cm, x em cm, domínio) para uma seção retangular.

    Supõe sigma_sd = fyd (válido nos domínios 2 e 3). A posição da LN sai
    do equilíbrio de forças com o bloco retangular da NBR 6118:2026
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
# Impressão
# ---------------------------------------------------------------------------
def imprimir(r: ResultadoFlexao) -> None:
    print(f"=== {r.tipo.upper()} ===")
    print(f"  Md  = {r.Md:>9.1f} kN.cm  | bw = {r.bw:.1f} cm | "
          f"d = {r.d:.2f} cm | h = {r.h:.1f} cm")
    print(f"  fck = {r.fck:>4.0f} MPa     | fyk = {r.fyk:.0f} MPa")
    if r.erro:
        print(f"  ATENÇÃO: {r.erro}")
    print(f"  x   = {r.x:>6.2f} cm  | x/d = {r.beta_x:.3f}  | "
          f"domínio {r.dominio}")
    print(f"  As  = {r.As:>6.2f} cm2  (As,min = {r.As_min:.2f} cm2)")
    if r.minimo_governou:
        print(f"  (As,min governou o dimensionamento - NBR 6118 17.3.5.2.1)")
    if r.As_linha > 0:
        print(f"  A's = {r.As_linha:>6.2f} cm2  (armadura comprimida)")
    if r.M1d and r.M2d:
        print(f"  M1d = {r.M1d:.1f} kN.cm  | M2d = {r.M2d:.1f} kN.cm")
    print(f"  eps_cd = {r.eps_cd:.2f} %o  |  eps_sd = {r.eps_sd:.2f} %o")


# ---------------------------------------------------------------------------
# Testes contra exemplos numéricos da apostila
# ---------------------------------------------------------------------------
def teste_apostila_7_3_ex1() -> bool:
    """Apostila 7.3 ex.1: bw=20, h=50, d=47, C20, CA-50, Mk=+10000.
    Esperado: x ~ 18.1 cm, dom 3, As ~ 8.10 cm2."""
    r = secao_retangular_simples(
        Md_kncm=14000.0, bw_cm=20, d_cm=47, h_cm=50, fck_mpa=20,
    )
    print("\n--- Apostila 7.3 ex.1 (armadura simples, domínio 3) ---")
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
    """Apostila 7.3 ex.4 (verificação): bw=20, h=50, d=46, As=8.00, C20.
    Esperado: x ~ 17.9, Mk ~ 9650 kN.cm, dom 3."""
    MRd, x, dom = momento_resistente_simples(
        As_cm2=8.00, bw_cm=20, d_cm=46, fck_mpa=20,
    )
    Mk = MRd / GAMA_F
    print("\n--- Apostila 7.3 ex.4 (verificação) ---")
    print(f"  As = 8.00 cm2 | bw=20 | d=46 | C20 | CA-50")
    print(f"  x   = {x:.2f} cm  | domínio {dom}")
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
    Tabela A-1) e dá M1d = 21.486 kN.cm. Este script usa a equação direta
    (Eq. 40), mais precisa, e dá M1d ~ 21.953 -> A's ~ 1.82, As ~ 13.22.
    Tolerância maior cobre o arredondamento da tabela."""
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
    Mk=+8000. 0.8x > hf -> formulação T própria.
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


# === P12: armaduras mínima, máxima e de pele; instabilidade lateral (Onda 2) ===
#
# Completa os limites de armadura de viga que faltavam: taxa mecânica mínima
# de flexão (17.1), armadura de pele com seu espaçamento máximo (17.3.5.2.3 e
# 18.3.5), o teto de As + A's <= 4% Ac (17.3.5.2.4, valendo também para laje
# por 19.3.3.3), o critério de concentração de forças em grupos de barras
# (17.2.4.1) e a verificação aproximada de instabilidade lateral de vigas com
# a Tabela 15.1 (15.10). Reusa nucleo_nbr6118 para fcd, fyd, rho_min_flexao e
# xd_limite_dutilidade; não reimplementa nenhuma fórmula de material.
# ---------------------------------------------------------------------------

# --- 17.1 — Taxa mecânica mínima de armadura de flexão (PDF p. 140) --------
def omega_min(fck_mpa: float, fyk_mpa: float = 500.0,
             gama_c: float = GAMA_C, gama_s: float = GAMA_S) -> float:
    """Taxa mecânica mínima de armadura longitudinal de flexão para vigas
    (17.1, PDF p. 140): wmin = (As,min * fyd) / (Ac * fcd).

    Como As,min = rho_min(fck) * Ac (Tabela 17.3, nbr.rho_min_flexao), a
    razão independe da geometria da seção e se reduz a
    wmin = rho_min(fck) * fyd / fcd, com fyd e fcd em MPa (nbr.fyd, nbr.fcd) -
    a razão é adimensional, então a unidade de fyd/fcd não importa desde que
    seja a mesma nos dois. Grandeza usada só para checagem/relatório: o
    dimensionamento em si já usa As,min diretamente (as_min).

    A Tabela 17.3 (nbr.rho_min_flexao) pressupõe aço CA-50 (fyk = 500 MPa),
    d/h = 0,8, gama_c = 1,4 e gama_s = 1,15 (docstring de rho_min_flexao); fora
    desses valores, rho_min(fck) não reproduz As,min/Ac quando o critério do
    momento mínimo (não o piso de 0,15%) é quem governa, e o wmin calculado
    aqui ficaria incorreto. Por isso a função só aceita esses valores; para
    outro aço ou outro gama, calcule wmin a partir de
    ``nbr.As_min_flexao_retangular`` (que exige a geometria) dividido por Ac.
    """
    if fyk_mpa != 500.0 or gama_c != GAMA_C or gama_s != GAMA_S:
        raise nbr.FaixaNormativaError(
            "omega_min só vale para os parâmetros que a Tabela 17.3 "
            f"pressupõe (fyk = 500 MPa, gama_c = {GAMA_C:g}, gama_s = "
            f"{GAMA_S:g}); recebido fyk_mpa={fyk_mpa!r}, gama_c={gama_c!r}, "
            f"gama_s={gama_s!r}. Para outro aço ou outro gama, calcule wmin "
            "a partir de nbr.As_min_flexao_retangular (que exige a "
            "geometria) dividido por Ac."
        )
    fyd_mpa = nbr.fyd(fyk_mpa, gama_s)
    fcd_mpa = nbr.fcd(fck_mpa, gama_c)
    return nbr.rho_min_flexao(fck_mpa) * fyd_mpa / fcd_mpa


# --- 17.3.5.2.3 e 18.3.5 — Armadura de pele (PDF p. 153 e 172) -------------
TETO_PELE_CM2_POR_M = 5.0        # 17.3.5.2.3 — não precisa exceder 5 cm2/m por face
TAXA_PELE = 0.0010               # 17.3.5.2.3 — 0,10% de Ac,alma, por face
H_DISPENSA_PELE_CM = 60.0        # 17.3.5.2.3 — dispensável se h <= 60 cm


def armadura_pele_cm2_por_face(bw_cm: float, h_cm: float) -> float:
    """Armadura de pele mínima por face da alma, em cm2/m (17.3.5.2.3, PDF
    p. 153): 0,10% * Ac,alma por face, sem exceder 5 cm2/m por face.

    Expressa como taxa por metro de altura da alma (Ac,alma de uma faixa de
    1 m de altura = bw_cm * 100), que é a grandeza que o detalhista usa para
    escolher bitola e espaçamento (igual ao uso corrente em escritório e nos
    demais softwares de detalhamento); não é a área total da alma inteira.
    Dispensável em vigas com h <= 60 cm (17.3.5.2.3): retorna 0,0.

    AVISO: ``blocos_nbr6118.Asp_pele_face`` calcula outra grandeza (pele de
    bloco sobre estacas, 1/8 de As,total) - não confundir com esta função.
    """
    if h_cm <= H_DISPENSA_PELE_CM:
        return 0.0
    taxa = TAXA_PELE * bw_cm * 100.0
    return min(taxa, TETO_PELE_CM2_POR_M)


def espacamento_max_pele_cm(d_cm: float) -> float:
    """Espaçamento máximo entre barras de pele ao longo da altura da alma
    (18.3.5, PDF p. 172): min(d/3, 20 cm). A área da armadura de pele em si
    é calculada por ``armadura_pele_cm2_por_face`` (17.3.5.2.3)."""
    return min(d_cm / 3.0, 20.0)


# --- 17.3.5.2.4 e 19.3.3.3 — Soma máxima de As e A's (PDF p. 153 e 181) ----
@dataclass(frozen=True)
class ResultadoAsMaxViga:
    As: float
    As_linha: float
    Ac: float
    soma: float
    limite: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


LIMITE_AS_MAIS_AS_LINHA = 0.04   # 17.3.5.2.4 — (As + A's) <= 4% Ac


def verificar_As_max_viga(As_cm2: float, As_linha_cm2: float,
                          Ac_cm2: float) -> ResultadoAsMaxViga:
    """Verifica (As + A's) <= 4% Ac fora da zona de emendas (17.3.5.2.4,
    PDF p. 153). Vale também para a armadura máxima de flexão de laje, que
    19.3.3.3 (PDF p. 181) remete a este mesmo limite de 17.3.5.2.

    Não confere sozinha a dutilidade de 14.6.4.3 (que a norma também exige
    junto deste teto) - use ``verificar_limites_armadura_viga`` para as duas
    verificações combinadas a partir de um ``ResultadoFlexao``.
    """
    soma = As_cm2 + As_linha_cm2
    limite = LIMITE_AS_MAIS_AS_LINHA * Ac_cm2
    ok = soma <= limite
    governante = "As + A's <= 4% Ac (17.3.5.2.4)" if not ok else "nenhum (dentro do limite)"
    memoria = (
        f"As = {As_cm2:.2f} cm2, A's = {As_linha_cm2:.2f} cm2, "
        f"soma = {soma:.2f} cm2 (17.3.5.2.4).",
        f"Limite = 4% * Ac = 4% * {Ac_cm2:.2f} = {limite:.2f} cm2.",
        f"{'ok' if ok else 'não ok'}: soma {'<=' if ok else '>'} limite.",
    )
    return ResultadoAsMaxViga(
        As=As_cm2, As_linha=As_linha_cm2, Ac=Ac_cm2, soma=soma,
        limite=limite, ok=ok, governante=governante, memoria=memoria,
    )


@dataclass(frozen=True)
class ResultadoLimitesViga:
    as_max: ResultadoAsMaxViga
    beta_x: float
    limite_xd: float
    ok_dutilidade: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_limites_armadura_viga(resultado: ResultadoFlexao,
                                    Ac_cm2: float | None = None) -> ResultadoLimitesViga:
    """Confere, a partir de um ``ResultadoFlexao`` já dimensionado, o teto de
    As + A's <= 4% Ac (17.3.5.2.4) e a dutilidade de x/d <= xd_limite_dutilidade
    (17.2.3, que remete a 14.6.4.3), consolidando as duas verificações.

    Ac_cm2: área da seção para o limite de 4%; por padrão bw * h do próprio
    resultado (seção retangular). Passe explicitamente para seção T.
    """
    Ac = Ac_cm2 if Ac_cm2 is not None else resultado.bw * resultado.h
    r_as_max = verificar_As_max_viga(resultado.As, resultado.As_linha, Ac)
    limite_xd = nbr.xd_limite_dutilidade(resultado.fck)
    ok_xd = resultado.beta_x <= limite_xd
    ok = r_as_max.ok and ok_xd
    if not ok:
        motivos = []
        if not r_as_max.ok:
            motivos.append("As + A's > 4% Ac (17.3.5.2.4)")
        if not ok_xd:
            motivos.append("x/d acima do limite de dutilidade (17.2.3/14.6.4.3)")
        governante = "; ".join(motivos)
    else:
        governante = "nenhum (dentro dos limites)"
    memoria = r_as_max.memoria + (
        f"x/d = {resultado.beta_x:.3f}, limite de dutilidade = {limite_xd:.2f} "
        f"(17.2.3/14.6.4.3, fck = {resultado.fck:g} MPa).",
        f"{'ok' if ok_xd else 'não ok'}: x/d {'<=' if ok_xd else '>'} limite.",
    )
    return ResultadoLimitesViga(
        as_max=r_as_max, beta_x=resultado.beta_x, limite_xd=limite_xd,
        ok_dutilidade=ok_xd, ok=ok, governante=governante, memoria=memoria,
    )


# --- 17.2.4.1 — Concentração de forças de barras no centroide (p. 143) ----
FATOR_AGRUPAMENTO_H = 0.10   # 17.2.4.1 — distância < 10% de h


def agrupamento_barras_permitido(dist_cm: float, h_cm: float) -> bool:
    """17.2.4.1 (PDF p. 143): as forças de um grupo de barras podem ser
    consideradas concentradas no centroide correspondente se a distância
    deste centroide à barra mais afastada do grupo (medida normal à linha
    neutra) for menor que 10% de h. dist_cm é essa distância; devolve True
    quando o agrupamento é permitido."""
    return dist_cm < FATOR_AGRUPAMENTO_H * h_cm


# --- 15.10 — Instabilidade lateral de vigas e Tabela 15.1 (PDF p. 134) -----
TABELA_15_1 = {   # beta_fl pela tipologia da seção (15.10, Tabela 15.1)
    "retangular": 0.40,
    "t": 0.40,
    "i": 0.40,
    "duplo_t": 0.20,
    "caixao": 0.20,
}


@dataclass(frozen=True)
class ResultadoInstabilidadeLateral:
    b: float
    h: float
    l0: float
    tipo: str
    beta_fl: float
    limite_vao: float
    limite_altura: float
    ok_vao: bool
    ok_altura: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_instabilidade_lateral(b_cm: float, h_cm: float, l0_cm: float,
                                    tipo: str) -> ResultadoInstabilidadeLateral:
    """Verificação aproximada de instabilidade lateral (flambagem lateral)
    de vigas (15.10, PDF p. 134): b >= l0/50 e b >= beta_fl * h, com beta_fl
    pela Tabela 15.1 (0,40 para seção retangular, T ou I isoladas; 0,20 para
    duplo T ou seções em caixão, quando a mesa comprimida é compartilhada
    por duas almas).

    b_cm: largura da zona comprimida. h_cm: altura total da viga. l0_cm:
    comprimento do flange comprimido entre suportes que garantem o
    contraventamento lateral. tipo: chave de TABELA_15_1 ('retangular',
    't', 'i', 'duplo_t' ou 'caixao'), sem distinção de maiúsculas.
    """
    chave = str(tipo).strip().lower().replace(" ", "_").replace("-", "_")
    if chave not in TABELA_15_1:
        raise nbr.FaixaNormativaError(
            f"Tipologia de viga desconhecida na Tabela 15.1: {tipo!r}. "
            f"Use uma de {sorted(TABELA_15_1)}."
        )
    beta_fl = TABELA_15_1[chave]
    limite_vao = l0_cm / 50.0
    limite_altura = beta_fl * h_cm
    ok_vao = b_cm >= limite_vao
    ok_altura = b_cm >= limite_altura
    ok = ok_vao and ok_altura
    if ok:
        governante = "nenhum (dentro dos limites)"
    else:
        motivos = []
        if not ok_vao:
            motivos.append("b < l0/50")
        if not ok_altura:
            motivos.append("b < beta_fl * h")
        governante = "; ".join(motivos)
    memoria = (
        f"Tipologia = {tipo} -> beta_fl = {beta_fl:.2f} (Tabela 15.1).",
        f"b >= l0/50 = {l0_cm:.1f}/50 = {limite_vao:.2f} cm -> "
        f"{'ok' if ok_vao else 'não ok'} (b = {b_cm:.2f} cm).",
        f"b >= beta_fl*h = {beta_fl:.2f}*{h_cm:.1f} = {limite_altura:.2f} cm -> "
        f"{'ok' if ok_altura else 'não ok'} (b = {b_cm:.2f} cm).",
    )
    return ResultadoInstabilidadeLateral(
        b=b_cm, h=h_cm, l0=l0_cm, tipo=tipo, beta_fl=beta_fl,
        limite_vao=limite_vao, limite_altura=limite_altura,
        ok_vao=ok_vao, ok_altura=ok_altura, ok=ok,
        governante=governante, memoria=memoria,
    )


# === T3: armadura de pele, área total por face (17.3.5.2.3, PDF p. 153) ===
def armadura_pele_total_cm2_por_face(
    bw_cm: float, h_alma_cm: float, h_total_cm: float | None = None
) -> float:
    """Armadura de pele mínima por face da alma, em cm2 de área total
    (17.3.5.2.3, PDF p. 153): 0,10% * Ac,alma por face, sem exceder o
    equivalente a 5 cm2/m de altura da alma.

    Esta é a forma **principal** recomendada (área total por face, como na
    apostila do Prof. Bastos), a partir da qual o detalhista distribui as
    barras ao longo de h_alma respeitando o espaçamento máximo de
    ``espacamento_max_pele_cm``. Para a taxa por metro de altura (grandeza
    equivalente, usada por outros softwares de detalhamento), veja
    ``armadura_pele_cm2_por_face``.

    Ac,alma = bw_cm * h_alma_cm. ``h_alma_cm`` é a altura da alma: em viga
    retangular, a própria altura h da viga; em viga T, a altura da alma
    abaixo da mesa (não a altura total da viga).

    Dispensável em vigas com altura TOTAL <= 60 cm (17.3.5.2.3: "Em vigas
    com altura igual ou inferior a 60 cm..." — a norma fala da altura da
    viga, não da altura da alma). ``h_total_cm`` é essa altura total; se
    omitido, assume-se seção retangular e usa-se ``h_alma_cm`` (onde as
    duas coincidem). Para viga T, o chamador DEVE informar ``h_total_cm``
    explicitamente: uma viga T com altura total > 60 cm não é dispensada
    mesmo que a alma abaixo da mesa tenha <= 60 cm.

    O teto de 5 cm2/m por face (mesmo limite de ``armadura_pele_cm2_por_face``)
    é convertido para a área total distribuída em h_alma_cm: 5 cm2/m *
    (h_alma_cm / 100).
    """
    h_dispensa_cm = h_total_cm if h_total_cm is not None else h_alma_cm
    if h_dispensa_cm <= H_DISPENSA_PELE_CM:
        return 0.0
    area = TAXA_PELE * bw_cm * h_alma_cm
    teto = TETO_PELE_CM2_POR_M * (h_alma_cm / 100.0)
    return min(area, teto)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if "--test" in sys.argv:
        sys.exit(0 if rodar_testes() else 1)

    # Sem flag: roda os exemplos da apostila como demonstração.
    rodar_testes()


if __name__ == "__main__":
    main()
