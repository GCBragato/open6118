"""Emendas, feixes, telas e dispositivos mecânicos — ABNT NBR 6118:2026.

Cobre (as páginas são as do PDF; a impressa é 18 a menos):
    - 9.4.3   ancoragem de feixes de barras por aderência (p. 58);
    - 9.4.4   ancoragem de telas soldadas por aderência (p. 58);
    - 9.4.7   ancoragem por dispositivos mecânicos (p. 61);
    - 9.4.7.1 barra transversal única soldada (p. 61);
    - 9.5.2   limites de bitola da emenda por traspasse, barra e feixe (p. 62);
    - 9.5.2.1 mesma seção transversal e Tabela 9.3 (p. 62-63);
    - 9.5.2.2.2 traspasse com distância livre maior que 4*phi (p. 63), em
      ``ancoragem_nbr6118.transpasse_tracionado_cm`` e
      ``transpasse_comprimido_cm`` (parâmetros ``diametros_diferentes`` e
      ``distancia_livre_cm``), reexportados aqui;
    - 9.5.2.4 armadura transversal nas emendas por traspasse (p. 64);
    - 9.5.2.5 emendas por traspasse em feixes (p. 64);
    - 9.5.3   emendas mecânicas por luvas (p. 65);
    - 9.5.4   emendas por solda (p. 65-66, Figura 9.6).

Reusa ``ancoragem_nbr6118`` (lb, lb,nec, α0t, armadura transversal de
9.4.2.6) e o núcleo (``phi_n_feixe``, ``fyd``, ``FaixaNormativaError``); a
condição Rd >= Sd vem de ``seguranca_nbr6118.verificar_seguranca``.

Convenções: diâmetro em mm, comprimento em cm, área em cm², tensão em MPa,
força em kN (As[cm²]·f[MPa]/10 = kN).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
    import ancoragem_nbr6118 as anc
    import seguranca_nbr6118 as seg
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr
    from dimensionamento import ancoragem_nbr6118 as anc
    from dimensionamento import seguranca_nbr6118 as seg

FaixaNormativaError = nbr.FaixaNormativaError

# 9.5.2.2 — reexportados: o traspasse de barras isoladas mora em
# ancoragem_nbr6118, e o P27 só acrescentou os parâmetros de 9.5.2.1 e
# 9.5.2.2.2.
transpasse_tracionado_cm = anc.transpasse_tracionado_cm
transpasse_comprimido_cm = anc.transpasse_comprimido_cm

_TOL = 1e-9

PHI_N_LIMITE_BARRA_UNICA_MM = 25.0     # 9.4.3 a)/b)
FATOR_AFASTAMENTO_FEIXE = 1.2          # 9.4.3 b)
PHI_MAX_TRASPASSE_MM = 32.0            # 9.5.2
DIAMETRO_MAX_FEIXE_TRASPASSE_MM = 45.0  # 9.5.2
FRACAO_MESMA_SECAO_TRASPASSE = 0.20    # 9.5.2.1
N_MAX_BARRAS_SECAO_FEIXE = 4           # 9.5.2.5
FATOR_SEPARACAO_EMENDAS_FEIXE = 1.3    # 9.5.2.5
FATOR_LUVA_SOLDA = 1.15                # 9.5.3 e 9.5.4
FATOR_REDUCAO_SOLDA_VARIAVEL = 0.80    # 9.5.4
MESMA_SECAO_SOLDA_PHI = 15.0           # 9.5.4


def _fmt(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


def _area_barra_cm2(phi_mm: float) -> float:
    """Área da seção de uma barra de diâmetro phi_mm, cm²."""
    return math.pi * (phi_mm / 10.0) ** 2 / 4.0


def _positivo(valor: float, nome: str) -> float:
    v = float(valor)
    if not v > 0.0:
        raise ValueError(f"{nome} deve ser positivo: {valor!r}.")
    return v


# ===========================================================================
# 9.4.3 — Ancoragem de feixes de barras por aderência (PDF p. 58)
# ===========================================================================
def phi_n_feixe_mm(phi_f_mm: float, n_barras: int) -> float:
    """Diâmetro equivalente do feixe, mm (9.4.3, PDF p. 58).

        φn = φf·√n

    φf é o diâmetro de cada barra do feixe e n o número de barras. Delegado
    a ``nucleo_nbr6118.phi_n_feixe`` (a fórmula mora no núcleo desde o P24);
    n < 2 levanta ``ValueError``.
    """
    return nbr.phi_n_feixe(_positivo(phi_f_mm, "phi_f_mm"), n_barras)


@dataclass(frozen=True)
class ResultadoAncoragemFeixe:
    """Ancoragem de feixe de barras por aderência (9.4.3).

    ``caso``: 'a' (φn <= 25 mm, barra única de diâmetro φn), 'b' (φn > 25 mm,
    cada barra ancorada isoladamente, extremidades afastadas) ou 'c' (φn >
    25 mm sem como afastar, barra única φn com armadura transversal
    obrigatória de 9.4.2.6). ``lb_nec_cm`` é o da barra única φn (casos a e c)
    ou o de cada barra individual (caso b). ``afastamento_min_extremidades_cm``
    só existe no caso b; ``armadura_transversal`` só no caso c (resultado de
    ``ancoragem_nbr6118.Ast_ancoragem`` com φn). Não há ``ok``: a função
    dimensiona, não compara com um detalhamento dado.
    """

    phi_f_mm: float
    n_barras: int
    phi_n_mm: float
    caso: str
    phi_calculo_mm: float
    lb_cm: float
    lb_nec_cm: float
    afastamento_min_extremidades_cm: float | None
    armadura_transversal: anc.ResultadoArmaduraTransversalAncoragem | None
    governante: str
    memoria: tuple[str, ...]


def ancoragem_feixe(
    phi_f_mm: float,
    n_barras: int,
    fck_mpa: float,
    fyk_mpa: float = 500.0,
    tipo_aco: str = "CA-50",
    boa_aderencia: bool = True,
    As_calc: float = 1.0,
    As_ef: float = 1.0,
    afastamento_possivel: bool = True,
    barra_comprimida: bool = False,
    gama_c: float = anc.GAMA_C,
    gama_s: float = anc.GAMA_S,
) -> ResultadoAncoragemFeixe:
    """Ancoragem de feixe de barras por aderência, por faixa de φn (9.4.3,
    PDF p. 58).

    φn = φf·√n. As barras do feixe têm ancoragem reta, sem ganchos (por isso
    não há parâmetro de gancho; o comprimento usa α = 1,0 de 9.4.2.5).

    a) φn <= 25 mm: o feixe é tratado como barra única de diâmetro φn,
       com o comprimento de ancoragem de 9.4.2 (lb e lb,nec com φ = φn).
    b) φn > 25 mm: a ancoragem é calculada para cada barra isolada (φ = φf),
       e a distância entre as extremidades das barras do feixe não pode ser
       menor que 1,2 vez o comprimento de ancoragem de cada barra individual:
           afastamento >= 1,2·lb,nec(φf)
       (adota-se o lb,nec da barra individual, com o mesmo As,calc/As,ef).
    c) φn > 25 mm e, por razões construtivas, impossível afastar
       (``afastamento_possivel=False``): ancoragem como barra única de
       diâmetro φn, com armadura transversal adicional obrigatória conforme
       9.4.2.6 — 9.4.2.6.1 se φn < 32 mm, 9.4.2.6.2 se φn >= 32 mm. A força
       longitudinal da "barra" é a do feixe inteiro (As = n·π·φf²/4, igual à
       área da barra de diâmetro φn) com fyd = fyk/γs.

    ``afastamento_possivel`` só importa quando φn > 25 mm. Comprimentos em cm.
    """
    phi_n = phi_n_feixe_mm(phi_f_mm, n_barras)
    n = int(n_barras)
    kw = dict(fck_mpa=fck_mpa, fyk_mpa=fyk_mpa, tipo_aco=tipo_aco,
              boa_aderencia=boa_aderencia, com_gancho=False,
              As_calc=As_calc, As_ef=As_ef, gama_c=gama_c, gama_s=gama_s)
    memoria = [
        f"9.4.3: φn = φf·√n = {_fmt(phi_f_mm)}·√{n} = {_fmt(phi_n)} mm.",
    ]
    afast = None
    Ast = None
    if phi_n <= PHI_N_LIMITE_BARRA_UNICA_MM + _TOL:
        caso = "a"
        phi_calc = phi_n
        r = anc.comprimento_ancoragem(phi_mm=phi_n, **kw)
        governante = "9.4.3 a): φn <= 25 mm, barra única de diâmetro φn"
        memoria.append(
            f"{governante}: lb = {_fmt(r.lb_cm)} cm; "
            f"lb,nec = {_fmt(r.lb_nec_cm)} cm (9.4.2)."
        )
    elif afastamento_possivel:
        caso = "b"
        phi_calc = float(phi_f_mm)
        r = anc.comprimento_ancoragem(phi_mm=phi_calc, **kw)
        afast = FATOR_AFASTAMENTO_FEIXE * r.lb_nec_cm
        governante = "9.4.3 b): φn > 25 mm, cada barra ancorada isoladamente"
        memoria.append(
            f"{governante}: lb,nec(φf = {_fmt(phi_calc)} mm) = "
            f"{_fmt(r.lb_nec_cm)} cm; afastamento mínimo entre extremidades "
            f"= 1,2·{_fmt(r.lb_nec_cm)} = {_fmt(afast)} cm."
        )
    else:
        caso = "c"
        phi_calc = phi_n
        r = anc.comprimento_ancoragem(phi_mm=phi_n, **kw)
        As_feixe = n * _area_barra_cm2(phi_f_mm)
        Ast = anc.Ast_ancoragem(phi_n, As_feixe, nbr.fyd(fyk_mpa, gama_s),
                                barra_comprimida=barra_comprimida)
        governante = ("9.4.3 c): φn > 25 mm sem afastamento possível, barra "
                      "única φn com armadura transversal obrigatória (9.4.2.6)")
        memoria.append(
            f"{governante}: lb = {_fmt(r.lb_cm)} cm; "
            f"lb,nec = {_fmt(r.lb_nec_cm)} cm; As do feixe = {n}·π·φf²/4 = "
            f"{_fmt(As_feixe)} cm²."
        )
        memoria.extend(Ast.memoria)
    return ResultadoAncoragemFeixe(
        phi_f_mm=float(phi_f_mm), n_barras=n, phi_n_mm=phi_n, caso=caso,
        phi_calculo_mm=phi_calc, lb_cm=r.lb_cm, lb_nec_cm=r.lb_nec_cm,
        afastamento_min_extremidades_cm=afast, armadura_transversal=Ast,
        governante=governante, memoria=tuple(memoria),
    )


# ===========================================================================
# 9.4.4 — Ancoragem de telas soldadas por aderência (PDF p. 58)
# ===========================================================================
def n_fios_transversais_tela_min(As_calc: float, As_ef: float) -> float:
    """Número mínimo (real) de fios transversais soldados ao longo do
    comprimento de ancoragem necessário da tela (9.4.4, PDF p. 58).

        n >= 4·As,calc/As,ef

    Vale para tela de fios lisos ou com mossas ancorada com os critérios das
    barras nervuradas. As,calc/As,ef > 1 (armadura efetiva menor que a
    calculada) levanta ``FaixaNormativaError``.
    """
    a_calc = float(As_calc)
    a_ef = _positivo(As_ef, "As_ef")
    if a_calc < 0.0:
        raise ValueError("As_calc não pode ser negativa (9.4.4).")
    razao = a_calc / a_ef
    if razao > 1.0 + _TOL:
        raise FaixaNormativaError(
            f"As,calc/As,ef = {razao:.4g} > 1: a armadura efetiva é menor que "
            "a calculada, e a ancoragem da tela (9.4.4) não se aplica."
        )
    return 4.0 * razao


def n_fios_transversais_tela(As_calc: float, As_ef: float) -> int:
    """Número inteiro mínimo de fios transversais soldados no comprimento de
    ancoragem necessário da tela: o menor inteiro n com n >= 4·As,calc/As,ef
    (9.4.4, PDF p. 58). Ex.: As,calc/As,ef = 0,8 -> 3,2 -> 4 fios.
    """
    n_real = n_fios_transversais_tela_min(As_calc, As_ef)
    return int(math.ceil(n_real - _TOL))


# ===========================================================================
# 9.4.7 — Ancoragem por dispositivos mecânicos (PDF p. 61)
# ===========================================================================
ESCORREGAMENTO_MAX_70_MM = 0.1   # para 70 % da força última
ESCORREGAMENTO_MAX_95_MM = 0.5   # para 95 % da força última
FRACAO_RD_SEM_FADIGA = 0.50
FRACAO_RD_COM_FADIGA = 0.70


@dataclass(frozen=True)
class ResultadoDispositivoMecanico:
    F_ultima_kn: float
    escorregamento_70_mm: float
    escorregamento_95_mm: float
    resistencia_calculo_kn: float
    Rd_max_kn: float
    fadiga: bool
    ok_escorregamento_70: bool
    ok_escorregamento_95: bool
    ok_resistencia: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_dispositivo_mecanico(
    F_ultima_kn: float,
    escorregamento_70_mm: float,
    escorregamento_95_mm: float,
    resistencia_calculo_kn: float,
    fadiga: bool = False,
) -> ResultadoDispositivoMecanico:
    """Verifica a ancoragem por dispositivo mecânico com os resultados de
    ensaio (9.4.7, PDF p. 61).

    - escorregamento entre a barra e o concreto, junto ao dispositivo:
      <= 0,1 mm para 70 % da força última e <= 0,5 mm para 95 % dela;
    - resistência de cálculo da ancoragem:
      <= 0,50·Fu (Fu medida no ensaio), quando os efeitos de fadiga são
      desprezíveis (``fadiga=False``);
      <= 0,70·Fu (Fu obtida em ensaio de fadiga), caso contrário
      (``fadiga=True``; ``F_ultima_kn`` é então a do ensaio de fadiga).

    A eficiência do conjunto e os efeitos localizados (21.2) ficam com o
    projeto; esta função só confere os números do ensaio. Forças em kN,
    escorregamentos em mm.
    """
    Fu = _positivo(F_ultima_kn, "F_ultima_kn")
    s70, s95 = float(escorregamento_70_mm), float(escorregamento_95_mm)
    if s70 < 0.0 or s95 < 0.0:
        raise ValueError("Escorregamento não pode ser negativo (9.4.7).")
    Rcalc = float(resistencia_calculo_kn)
    fracao = FRACAO_RD_COM_FADIGA if fadiga else FRACAO_RD_SEM_FADIGA
    Rd_max = fracao * Fu
    ok70 = s70 <= ESCORREGAMENTO_MAX_70_MM + _TOL
    ok95 = s95 <= ESCORREGAMENTO_MAX_95_MM + _TOL
    okR = seg.verificar_seguranca(Rd_max, Rcalc, "Rd,ancoragem <= fração de Fu",
                                  item="9.4.7")
    ok = ok70 and ok95 and okR.ok
    falhas = []
    if not ok70:
        falhas.append("escorregamento a 70 % de Fu > 0,1 mm")
    if not ok95:
        falhas.append("escorregamento a 95 % de Fu > 0,5 mm")
    if not okR.ok:
        falhas.append(f"resistência de cálculo > {_fmt(fracao)}·Fu")
    governante = "9.4.7: atende" if ok else "9.4.7: " + "; ".join(falhas)
    memoria = (
        f"9.4.7: escorregamento a 70 % de Fu = {_fmt(s70)} mm <= 0,1 mm -> "
        f"{'ok' if ok70 else 'não ok'}.",
        f"9.4.7: escorregamento a 95 % de Fu = {_fmt(s95)} mm <= 0,5 mm -> "
        f"{'ok' if ok95 else 'não ok'}.",
        f"9.4.7: Rd,máx = {_fmt(fracao)}·Fu = {_fmt(fracao)}·{_fmt(Fu)} = "
        f"{_fmt(Rd_max)} kN ({'ensaio de fadiga' if fadiga else 'fadiga desprezível'}); "
        f"resistência de cálculo adotada = {_fmt(Rcalc)} kN -> "
        f"{'ok' if okR.ok else 'não ok'}.",
    )
    return ResultadoDispositivoMecanico(
        F_ultima_kn=Fu, escorregamento_70_mm=s70, escorregamento_95_mm=s95,
        resistencia_calculo_kn=Rcalc, Rd_max_kn=Rd_max, fadiga=bool(fadiga),
        ok_escorregamento_70=ok70, ok_escorregamento_95=ok95,
        ok_resistencia=okR.ok, ok=ok, governante=governante, memoria=memoria,
    )


# ===========================================================================
# 9.4.7.1 — Barra transversal única (PDF p. 61)
# ===========================================================================
PHI_MAX_BARRA_TRANSVERSAL_UNICA_MM = 25.0


@dataclass(frozen=True)
class ResultadoBarraTransversalUnica:
    phi_mm: float
    phi_t_mm: float
    phi_max_mm: float
    espacamento_cm: float
    espacamento_max_cm: float
    ok_phi_t: bool
    ok_phi: bool
    ok_espacamento: bool
    ok_solda: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def barra_transversal_unica(
    phi_mm: float,
    phi_t_mm: float,
    menor_dimensao_cm: float,
    espacamento_cm: float,
    solda_contorno_completo: bool = True,
    solda_conforme_954: bool = True,
) -> ResultadoBarraTransversalUnica:
    """Verifica a barra transversal soldada como dispositivo de ancoragem
    integral da barra (9.4.7.1, PDF p. 61). Condições:

    - φt = φ da barra ancorada;
    - φ não maior que 1/6 da menor dimensão do elemento estrutural na região
      da ancoragem "ou 25 mm". Lido aqui como φ <= min(dimensão/6, 25 mm) —
      as duas condições, a favor da segurança (o texto não diz qual vale);
    - espaçamento entre as barras ancoradas <= 20·φ;
    - solda nos sentidos longitudinal e transversal, contornando toda a área
      de contato (``solda_contorno_completo``), e conforme 9.5.4
      (``solda_conforme_954``) — declarados pelo projetista.

    φ em mm; dimensão e espaçamento em cm.
    """
    phi = _positivo(phi_mm, "phi_mm")
    phi_t = _positivo(phi_t_mm, "phi_t_mm")
    dim = _positivo(menor_dimensao_cm, "menor_dimensao_cm")
    s = _positivo(espacamento_cm, "espacamento_cm")
    phi_max = min(dim * 10.0 / 6.0, PHI_MAX_BARRA_TRANSVERSAL_UNICA_MM)
    s_max = 20.0 * phi / 10.0
    ok_t = abs(phi_t - phi) <= _TOL
    ok_phi = phi <= phi_max + _TOL
    ok_s = s <= s_max + _TOL
    ok_solda = bool(solda_contorno_completo) and bool(solda_conforme_954)
    ok = ok_t and ok_phi and ok_s and ok_solda
    falhas = []
    if not ok_t:
        falhas.append("φt diferente de φ")
    if not ok_phi:
        falhas.append("φ > min(dimensão/6, 25 mm)")
    if not ok_s:
        falhas.append("espaçamento > 20·φ")
    if not ok_solda:
        falhas.append("solda fora do prescrito")
    governante = "9.4.7.1: atende" if ok else "9.4.7.1: " + "; ".join(falhas)
    memoria = (
        f"9.4.7.1: φt = {_fmt(phi_t)} mm; φ = {_fmt(phi)} mm -> "
        f"{'ok' if ok_t else 'não ok'} (φt = φ).",
        f"9.4.7.1: φ <= min(dimensão/6; 25 mm) = min({_fmt(dim * 10.0)}/6; 25) "
        f"= {_fmt(phi_max)} mm -> {'ok' if ok_phi else 'não ok'}.",
        f"9.4.7.1: espaçamento = {_fmt(s)} cm <= 20·φ = {_fmt(s_max)} cm -> "
        f"{'ok' if ok_s else 'não ok'}.",
        f"9.4.7.1: solda contornando toda a área de contato e conforme 9.5.4 -> "
        f"{'ok' if ok_solda else 'não ok'}.",
    )
    return ResultadoBarraTransversalUnica(
        phi_mm=phi, phi_t_mm=phi_t, phi_max_mm=phi_max, espacamento_cm=s,
        espacamento_max_cm=s_max, ok_phi_t=ok_t, ok_phi=ok_phi,
        ok_espacamento=ok_s, ok_solda=ok_solda, ok=ok, governante=governante,
        memoria=memoria,
    )


# ===========================================================================
# 9.5.2 — Limites de bitola da emenda por traspasse (PDF p. 62)
# ===========================================================================
def diametro_circulo_mesma_area_mm(diametros_mm) -> float:
    """Diâmetro do círculo de mesma área de um feixe, mm (9.5.2, PDF p. 62).

        d = √(Σ φi²)

    Com barras iguais, é o φn = φf·√n de 9.4.3.
    """
    diams = [_positivo(d, "diâmetro") for d in diametros_mm]
    if not diams:
        raise ValueError("Informe ao menos um diâmetro (9.5.2).")
    return math.sqrt(sum(d * d for d in diams))


@dataclass(frozen=True)
class ResultadoBitolaTraspasse:
    diametros_mm: tuple[float, ...]
    feixe: bool
    phi_max_mm: float
    diametro_equivalente_mm: float
    ok_barra: bool
    ok_feixe: bool
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_bitola_traspasse(diametros_mm) -> ResultadoBitolaTraspasse:
    """Verifica se a emenda por traspasse é permitida pela bitola (9.5.2,
    PDF p. 62).

    ``diametros_mm``: diâmetro da barra isolada (um número, ou sequência de
    um elemento) ou os diâmetros das barras de um feixe (sequência com dois
    ou mais).

    - barra: traspasse não permitido para bitola maior que 32 mm (φ <= 32);
    - feixe: o diâmetro do círculo de mesma área do feixe não pode passar de
      45 mm (√Σφi² <= 45 mm), respeitado 9.5.2.5 (ver
      ``escalonamento_emenda_feixe``); como a emenda do feixe é a de cada
      barra, cada barra também respeita φ <= 32 mm.
    """
    if isinstance(diametros_mm, (int, float)):
        diametros_mm = (diametros_mm,)
    diams = tuple(_positivo(d, "diâmetro") for d in diametros_mm)
    if not diams:
        raise ValueError("Informe ao menos um diâmetro (9.5.2).")
    feixe = len(diams) > 1
    phi_max = max(diams)
    d_eq = diametro_circulo_mesma_area_mm(diams)
    ok_barra = phi_max <= PHI_MAX_TRASPASSE_MM + _TOL
    ok_feixe = (d_eq <= DIAMETRO_MAX_FEIXE_TRASPASSE_MM + _TOL) if feixe else True
    ok = ok_barra and ok_feixe
    memoria = [
        f"9.5.2: maior bitola = {_fmt(phi_max)} mm <= 32 mm -> "
        f"{'ok' if ok_barra else 'não ok'}.",
    ]
    if feixe:
        memoria.append(
            f"9.5.2: feixe, diâmetro do círculo de mesma área = √Σφ² = "
            f"{_fmt(d_eq)} mm <= 45 mm -> {'ok' if ok_feixe else 'não ok'}."
        )
    if ok:
        governante = "9.5.2: traspasse permitido"
    elif not ok_barra:
        governante = "9.5.2: bitola > 32 mm, traspasse não permitido"
    else:
        governante = "9.5.2: feixe com círculo de mesma área > 45 mm"
    return ResultadoBitolaTraspasse(
        diametros_mm=diams, feixe=feixe, phi_max_mm=phi_max,
        diametro_equivalente_mm=d_eq, ok_barra=ok_barra, ok_feixe=ok_feixe,
        ok=ok, governante=governante, memoria=tuple(memoria),
    )


# ===========================================================================
# 9.5.2.1 — Proporção das barras emendadas (PDF p. 62-63)
# ===========================================================================
def mesma_secao(afastamento_cm: float, l0_cm: float,
                l0_outra_cm: float | None = None) -> bool:
    """True se duas emendas por traspasse estão na mesma seção transversal
    (9.5.2.1 e Figura 9.4, PDF p. 62).

    Estão na mesma seção as emendas que se superpõem (``afastamento_cm`` <= 0,
    negativo = superposição) ou cujas extremidades mais próximas estão
    afastadas de menos que 20 % do comprimento do trecho de traspasse:
        afastamento < 0,2·ℓ0
    Com dois comprimentos diferentes (``l0_outra_cm``), usa-se o maior: a
    Figura 9.4 mostra ℓ01 > ℓ02 e a cota < 0,2·ℓ01. Exatamente 0,2·ℓ0 já não
    é mesma seção (o texto diz "menos que").
    """
    l0 = _positivo(l0_cm, "l0_cm")
    if l0_outra_cm is not None:
        l0 = max(l0, _positivo(l0_outra_cm, "l0_outra_cm"))
    a = float(afastamento_cm)
    if a <= 0.0:
        return True
    return a < FRACAO_MESMA_SECAO_TRASPASSE * l0 - _TOL


def phi_traspasse_diametros_diferentes(diametros_mm) -> float:
    """Diâmetro pelo qual se calcula o traspasse de duas barras de diâmetros
    diferentes emendadas entre si: o menor (9.5.2.1, PDF p. 62).

    Mais de duas barras de diâmetros diferentes levanta
    ``FaixaNormativaError``: a norma manda calcular o traspasse com o esforço
    solicitante de cálculo em cada uma das barras, não com um diâmetro só.
    """
    diams = tuple(_positivo(d, "diâmetro") for d in diametros_mm)
    if len(diams) > 2:
        raise FaixaNormativaError(
            "Com mais de duas barras de diâmetros diferentes emendadas, a "
            "norma manda calcular o traspasse com o esforço solicitante de "
            "cálculo em cada barra (9.5.2.1)."
        )
    if len(diams) < 2:
        raise ValueError("Informe os dois diâmetros emendados (9.5.2.1).")
    return min(diams)


# Tabela 9.3 — Proporção máxima de barras tracionadas emendadas (PDF p. 63).
# (tipo de barra, situação) -> {carregamento: %}
TABELA_9_3 = {
    ("alta_aderencia", "uma_camada"): {"estatico": 100.0, "dinamico": 100.0},
    ("alta_aderencia", "mais_de_uma_camada"): {"estatico": 50.0, "dinamico": 50.0},
    ("lisa", "phi_menor_16"): {"estatico": 50.0, "dinamico": 25.0},
    ("lisa", "phi_maior_igual_16"): {"estatico": 25.0, "dinamico": 25.0},
}

_TIPOS_BARRA_9_3 = {
    "alta_aderencia": "alta_aderencia", "alta aderencia": "alta_aderencia",
    "alta aderência": "alta_aderencia", "alta_aderência": "alta_aderencia",
    "nervurada": "alta_aderencia", "lisa": "lisa",
}
_CARREGAMENTOS_9_3 = {
    "estatico": "estatico", "estático": "estatico",
    "dinamico": "dinamico", "dinâmico": "dinamico",
}


def proporcao_maxima_emendas_pct(
    tipo_barra: str,
    carregamento: str,
    n_camadas: int = 1,
    phi_mm: float | None = None,
) -> float:
    """Proporção máxima, em %, de barras tracionadas da armadura principal
    emendadas por traspasse na mesma seção (Tabela 9.3, PDF p. 63).

    tipo_barra: 'alta_aderencia' (ou 'nervurada') ou 'lisa'; a Tabela 9.3 não
    tem linha para barra entalhada, que levanta ``FaixaNormativaError``.
    carregamento: 'estatico' ou 'dinamico'.
    Alta aderência: a situação é o número de camadas (``n_camadas``: 1, ou
    mais de 1). Lisa: a situação é o diâmetro (``phi_mm`` obrigatório:
    φ < 16 mm ou φ >= 16 mm).

        Alta aderência, uma camada ........ 100 % | 100 %
        Alta aderência, mais de uma ....... 50 %  | 50 %
        Lisa, φ < 16 mm ................... 50 %  | 25 %
        Lisa, φ >= 16 mm .................. 25 %  | 25 %
                                        (estático | dinâmico)
    """
    tb = _TIPOS_BARRA_9_3.get(str(tipo_barra).strip().lower())
    if tb is None:
        raise FaixaNormativaError(
            f"A Tabela 9.3 não define a proporção de emendas para o tipo de "
            f"barra {tipo_barra!r}: só 'alta_aderencia' e 'lisa'."
        )
    carr = _CARREGAMENTOS_9_3.get(str(carregamento).strip().lower())
    if carr is None:
        raise ValueError(
            f"carregamento deve ser 'estatico' ou 'dinamico': {carregamento!r}."
        )
    if tb == "alta_aderencia":
        n = int(n_camadas)
        if n < 1:
            raise ValueError("n_camadas deve ser >= 1 (Tabela 9.3).")
        situacao = "uma_camada" if n == 1 else "mais_de_uma_camada"
    else:
        if phi_mm is None:
            raise ValueError(
                "Para barra lisa, a Tabela 9.3 depende do diâmetro: informe phi_mm."
            )
        phi = _positivo(phi_mm, "phi_mm")
        situacao = "phi_menor_16" if phi < 16.0 else "phi_maior_igual_16"
    return TABELA_9_3[(tb, situacao)][carr]


@dataclass(frozen=True)
class ResultadoProporcaoEmendas:
    pct_emendadas: float
    pct_maxima: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_proporcao_emendas(
    pct_emendadas: float,
    tipo_barra: str,
    carregamento: str,
    n_camadas: int = 1,
    phi_mm: float | None = None,
    comprimida_ou_distribuicao: bool = False,
) -> ResultadoProporcaoEmendas:
    """Verifica a proporção de barras emendadas por traspasse na mesma seção
    contra a Tabela 9.3 (9.5.2.1, PDF p. 63).

    Armadura permanentemente comprimida ou de distribuição
    (``comprimida_ou_distribuicao=True``): todas as barras podem ser
    emendadas na mesma seção (limite 100 %). Proporção maior que a da tabela
    não passa aqui: a norma só a admite com justificativa da integridade do
    concreto e da capacidade resistente da emenda, que fica com o projetista.
    """
    pct = float(pct_emendadas)
    if pct < 0.0 or pct > 100.0 + _TOL:
        raise ValueError("pct_emendadas deve estar entre 0 e 100 (9.5.2.1).")
    if comprimida_ou_distribuicao:
        pct_max = 100.0
        origem = ("9.5.2.1: armadura permanentemente comprimida ou de "
                  "distribuição, todas as barras podem ser emendadas")
    else:
        pct_max = proporcao_maxima_emendas_pct(tipo_barra, carregamento,
                                               n_camadas, phi_mm)
        origem = (f"Tabela 9.3: {tipo_barra}, carregamento {carregamento}, "
                  f"máximo {_fmt(pct_max)} %")
    ok = pct <= pct_max + _TOL
    governante = (f"{origem}" if ok else
                  f"{origem}; proporção maior só com justificativa (9.5.2.1)")
    memoria = (
        f"{origem}.",
        f"9.5.2.1: emendadas na mesma seção = {_fmt(pct)} % <= "
        f"{_fmt(pct_max)} % -> {'ok' if ok else 'não ok'}.",
    )
    return ResultadoProporcaoEmendas(pct, pct_max, ok, governante, memoria)


# ===========================================================================
# 9.5.2.4 — Armadura transversal nas emendas por traspasse (PDF p. 64)
# ===========================================================================
DISTANCIA_MAX_PRIMEIRA_BARRA_CM = 15.0  # Figura 9.5: <= 150 mm


@dataclass(frozen=True)
class ResultadoArmaduraTransversalEmenda:
    """Armadura transversal na emenda por traspasse de barra isolada
    (9.5.2.4). ``regra`` diz se valeu 9.4.2.6 (por remissão) ou a regra
    própria de 9.5.2.4.1. ``Ast_min_cm2`` é a área dos ramos paralelos ao
    plano da emenda; None quando 9.4.2.6.2 (φ >= 32 mm) não dá área.
    ``ok`` é None quando ``Ast_adotada_cm2`` não é informada (só
    dimensionamento)."""

    solicitacao: str
    phi_mm: float
    pct_emendadas: float | None
    regra: str
    fracao_forca_barra: float | None
    Ast_min_cm2: float | None
    Ast_por_terco_extremo_cm2: float | None
    barras_fechadas: bool | None
    distancia_limite_fechadas_cm: float | None
    distancia_max_primeira_barra_cm: float | None
    barra_alem_extremidade_cm: float | None
    Ast_adotada_cm2: float | None
    ok: bool | None
    governante: str
    memoria: tuple[str, ...]


_SOLICITACOES_EMENDA = {
    "tracionada": "tracionada", "tracao": "tracionada", "tração": "tracionada",
    "comprimida": "comprimida", "compressao": "comprimida",
    "compressão": "comprimida",
    "secundaria": "secundaria", "secundária": "secundaria",
}


def Ast_emenda(
    solicitacao: str,
    phi_mm: float,
    As_barra_cm2: float,
    fyd_barra_mpa: float,
    pct_emendadas: float | None = None,
    fyd_transversal_mpa: float | None = None,
    distancia_entre_emendas_cm: float | None = None,
    Ast_adotada_cm2: float | None = None,
) -> ResultadoArmaduraTransversalEmenda:
    """Armadura transversal nas emendas por traspasse de barras isoladas
    (9.5.2.4, PDF p. 64, Figura 9.5).

    solicitacao 'tracionada' (9.5.2.4.1, armadura principal):
    - φ < 16 mm e proporção emendada na mesma seção < 25 %: vale 9.4.2.6
      (``ancoragem_nbr6118.Ast_ancoragem``: Ast·fyd,t >= 0,25·As·fyd);
    - φ >= 16 mm ou proporção >= 25 %: a armadura transversal deve
        · resistir à força de uma barra emendada, contando os ramos
          paralelos ao plano da emenda: Ast·fyd,t >= As·fyd;
        · ser de barras fechadas se a distância entre as duas barras mais
          próximas de duas emendas na mesma seção for < 10·φ
          (``distancia_entre_emendas_cm``; sem ela, ``barras_fechadas`` sai
          None);
        · concentrar-se nos terços extremos da emenda — a Figura 9.5 mostra
          ΣAst/2 em cada terço extremo e a primeira barra a no máximo
          150 mm da extremidade.
    solicitacao 'comprimida' (9.5.2.4.2): os mesmos critérios, com pelo
    menos uma barra da armadura transversal a 4·φ além de cada extremidade
    da emenda.
    solicitacao 'secundaria' (9.5.2.4.3): vale 9.4.2.6.

    ``pct_emendadas`` (%) é obrigatória para tracionada e comprimida.
    ``fyd_transversal_mpa`` omitido = ``fyd_barra_mpa``. Traspasse de barra
    com φ > 32 mm não existe (9.5.2): levanta ``FaixaNormativaError``.
    ``Ast_adotada_cm2`` (opcional) é comparada com Ast,min via
    ``verificar_seguranca``.
    """
    sol = _SOLICITACOES_EMENDA.get(str(solicitacao).strip().lower())
    if sol is None:
        raise ValueError(
            "solicitacao deve ser 'tracionada', 'comprimida' ou 'secundaria': "
            f"{solicitacao!r}."
        )
    phi = _positivo(phi_mm, "phi_mm")
    if phi > PHI_MAX_TRASPASSE_MM + _TOL:
        raise FaixaNormativaError(
            "Emenda por traspasse não é permitida para bitola > 32 mm (9.5.2); "
            "não há armadura transversal de traspasse a calcular."
        )
    As = _positivo(As_barra_cm2, "As_barra_cm2")
    fyd_b = _positivo(fyd_barra_mpa, "fyd_barra_mpa")
    fyd_t = (_positivo(fyd_transversal_mpa, "fyd_transversal_mpa")
             if fyd_transversal_mpa is not None else fyd_b)
    pct = None
    if sol != "secundaria":
        if pct_emendadas is None:
            raise ValueError(
                "Informe pct_emendadas (proporção de barras emendadas na "
                "mesma seção, %) para emenda tracionada ou comprimida (9.5.2.4)."
            )
        pct = float(pct_emendadas)
        if pct < 0.0 or pct > 100.0 + _TOL:
            raise ValueError("pct_emendadas deve estar entre 0 e 100 (9.5.2.4).")

    item = {"tracionada": "9.5.2.4.1", "comprimida": "9.5.2.4.2",
            "secundaria": "9.5.2.4.3"}[sol]
    barra_alem = 4.0 * phi / 10.0 if sol == "comprimida" else None
    memoria = []
    fechadas = None
    lim_fechadas = None
    dist_primeira = None
    por_terco = None

    usa_9426 = sol == "secundaria" or (phi < 16.0 and pct < 25.0)
    if usa_9426:
        r = anc.Ast_ancoragem(phi, As, fyd_b, fyd_t)
        regra = "9.4.2.6"
        fracao = 0.25 if r.Ast_min_cm2 is not None else None
        Ast_min = r.Ast_min_cm2
        if sol == "secundaria":
            memoria.append("9.5.2.4.3: armadura secundária, vale 9.4.2.6.")
        else:
            memoria.append(
                f"{item}: φ = {_fmt(phi)} mm < 16 mm e emendadas = "
                f"{_fmt(pct)} % < 25 %: vale 9.4.2.6."
            )
        memoria.extend(r.memoria)
    else:
        regra = "9.5.2.4.1"
        fracao = 1.0
        Ast_min = As * fyd_b / fyd_t
        por_terco = Ast_min / 2.0
        dist_primeira = DISTANCIA_MAX_PRIMEIRA_BARRA_CM
        lim_fechadas = 10.0 * phi / 10.0
        motivo = "φ >= 16 mm" if phi >= 16.0 else "emendadas >= 25 %"
        memoria.append(
            f"{item}: φ = {_fmt(phi)} mm, emendadas = {_fmt(pct)} % ({motivo}): "
            f"a armadura transversal resiste à força de uma barra emendada "
            f"(ramos paralelos ao plano da emenda)."
        )
        memoria.append(
            f"Ast,min = As·fyd/fyd,t = {_fmt(As)}·{_fmt(fyd_b)}/{_fmt(fyd_t)} "
            f"= {_fmt(Ast_min)} cm²; ΣAst/2 = {_fmt(por_terco)} cm² em cada "
            f"terço extremo, primeira barra a <= 150 mm da extremidade "
            f"(Figura 9.5)."
        )
        if distancia_entre_emendas_cm is not None:
            d = float(distancia_entre_emendas_cm)
            fechadas = d < lim_fechadas - _TOL
            memoria.append(
                f"{item}: distância entre as barras mais próximas de duas "
                f"emendas = {_fmt(d)} cm {'<' if fechadas else '>='} 10·φ = "
                f"{_fmt(lim_fechadas)} cm -> barras "
                f"{'fechadas obrigatórias' if fechadas else 'fechadas não exigidas'}."
            )
    if barra_alem is not None:
        memoria.append(
            f"9.5.2.4.2: pelo menos uma barra transversal a 4·φ = "
            f"{_fmt(barra_alem)} cm além de cada extremidade da emenda."
        )

    ok = None
    if Ast_adotada_cm2 is not None and Ast_min is not None:
        v = seg.verificar_seguranca(float(Ast_adotada_cm2), Ast_min,
                                    "Ast,adotada x Ast,min", item=item)
        ok = v.ok
        memoria.extend(v.memoria)
    governante = f"{item}: regra de {regra}"
    return ResultadoArmaduraTransversalEmenda(
        solicitacao=sol, phi_mm=phi, pct_emendadas=pct, regra=regra,
        fracao_forca_barra=fracao, Ast_min_cm2=Ast_min,
        Ast_por_terco_extremo_cm2=por_terco, barras_fechadas=fechadas,
        distancia_limite_fechadas_cm=lim_fechadas,
        distancia_max_primeira_barra_cm=dist_primeira,
        barra_alem_extremidade_cm=barra_alem,
        Ast_adotada_cm2=(float(Ast_adotada_cm2)
                         if Ast_adotada_cm2 is not None else None),
        ok=ok, governante=governante, memoria=tuple(memoria),
    )


# ===========================================================================
# 9.5.2.5 — Emendas por traspasse em feixes de barras (PDF p. 64)
# ===========================================================================
@dataclass(frozen=True)
class ResultadoEmendaFeixe:
    n_barras_feixe: int
    phi_f_mm: float
    diametro_equivalente_mm: float
    n_max_barras_secao: int
    l0_individual_cm: float
    separacao_min_cm: float
    inicios_emendas_cm: tuple[float, ...]
    comprimento_zona_emendas_cm: float
    separacao_adotada_cm: float | None
    ok_n_barras: bool
    ok_diametro: bool
    ok_separacao: bool | None
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def escalonamento_emenda_feixe(
    n_barras_feixe: int,
    phi_f_mm: float,
    l0_individual_cm: float,
    separacao_adotada_cm: float | None = None,
) -> ResultadoEmendaFeixe:
    """Escalonamento das emendas por traspasse de um feixe de barras
    (9.5.2.5, PDF p. 64).

    - as barras do feixe são emendadas uma de cada vez; em qualquer seção do
      feixe emendado não pode haver mais de quatro barras. Na seção da
      emenda de uma barra ficam as n barras do feixe mais a barra que
      traspassa: n + 1 <= 4, isto é, feixe de no máximo 3 barras;
    - as emendas das barras do feixe ficam separadas entre si de 1,3 vez o
      comprimento de emenda individual: separação >= 1,3·ℓ0 (medida entre
      os inícios de emendas consecutivas — a norma não traz figura);
    - vale também 9.5.2: o círculo de mesma área do feixe (n barras) <= 45 mm
      e cada barra <= 32 mm.

    ``inicios_emendas_cm`` dá a posição do início de cada emenda com a
    separação mínima, a partir da primeira (0); ``comprimento_zona_emendas_cm``
    = (n − 1)·1,3·ℓ0 + ℓ0. ``separacao_adotada_cm`` (opcional) é conferida.
    """
    n = int(n_barras_feixe)
    if n < 2:
        raise ValueError("Feixe requer n_barras_feixe >= 2 (9.4.3, 9.5.2.5).")
    phi = _positivo(phi_f_mm, "phi_f_mm")
    l0 = _positivo(l0_individual_cm, "l0_individual_cm")
    bitola = verificar_bitola_traspasse((phi,) * n)
    n_secao = n + 1
    ok_n = n_secao <= N_MAX_BARRAS_SECAO_FEIXE
    sep_min = FATOR_SEPARACAO_EMENDAS_FEIXE * l0
    inicios = tuple(i * sep_min for i in range(n))
    zona = (n - 1) * sep_min + l0
    ok_sep = None
    if separacao_adotada_cm is not None:
        ok_sep = float(separacao_adotada_cm) >= sep_min - _TOL
    ok = ok_n and bitola.ok and (ok_sep is not False)
    memoria = [
        f"9.5.2.5: feixe de {n} barras de φ = {_fmt(phi)} mm, emendadas uma "
        f"de cada vez: {n} + 1 = {n_secao} barras na seção da emenda <= 4 -> "
        f"{'ok' if ok_n else 'não ok'}.",
        *bitola.memoria,
        f"9.5.2.5: separação entre emendas >= 1,3·ℓ0 = 1,3·{_fmt(l0)} = "
        f"{_fmt(sep_min)} cm; zona de emendas = {_fmt(zona)} cm.",
    ]
    if ok_sep is not None:
        memoria.append(
            f"9.5.2.5: separação adotada = {_fmt(float(separacao_adotada_cm))} "
            f"cm -> {'ok' if ok_sep else 'não ok'}."
        )
    falhas = []
    if not ok_n:
        falhas.append("mais de 4 barras na seção emendada")
    if not bitola.ok:
        falhas.append(bitola.governante)
    if ok_sep is False:
        falhas.append("separação < 1,3·ℓ0")
    governante = "9.5.2.5: atende" if ok else "9.5.2.5: " + "; ".join(falhas)
    return ResultadoEmendaFeixe(
        n_barras_feixe=n, phi_f_mm=phi,
        diametro_equivalente_mm=bitola.diametro_equivalente_mm,
        n_max_barras_secao=n_secao, l0_individual_cm=l0,
        separacao_min_cm=sep_min, inicios_emendas_cm=inicios,
        comprimento_zona_emendas_cm=zona,
        separacao_adotada_cm=(float(separacao_adotada_cm)
                              if separacao_adotada_cm is not None else None),
        ok_n_barras=ok_n, ok_diametro=bitola.ok, ok_separacao=ok_sep, ok=ok,
        governante=governante, memoria=tuple(memoria),
    )


# ===========================================================================
# 9.5.3 — Emendas mecânicas por luvas (PDF p. 65)
# ===========================================================================
@dataclass(frozen=True)
class ResultadoResistenciaEmenda:
    F_ensaio_kn: float
    As_cm2: float
    fy_barra_mpa: float
    F_escoamento_barra_kn: float
    F_min_kn: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def _resistencia_emenda_115(F_ensaio_kn: float, fy_barra_mpa: float,
                            As_cm2: float, item: str,
                            tipo: str) -> ResultadoResistenciaEmenda:
    F = _positivo(F_ensaio_kn, "F_ensaio_kn")
    fy = _positivo(fy_barra_mpa, "fy_barra_mpa")
    As = _positivo(As_cm2, "As_cm2")
    Fy = As * fy / 10.0
    Fmin = FATOR_LUVA_SOLDA * Fy
    v = seg.verificar_seguranca(F, Fmin, f"resistência da {tipo} x 1,15·As·fy",
                                item=item)
    memoria = (
        f"{item}: na ausência de norma específica, a {tipo} resiste a pelo "
        f"menos 15 % mais que o escoamento da barra: F,mín = 1,15·As·fy = "
        f"1,15·{_fmt(As)}·{_fmt(fy)}/10 = {_fmt(Fmin)} kN.",
        *v.memoria,
    )
    gov = (f"{item}: F,ensaio >= 1,15·As·fy" if v.ok
           else f"{item}: F,ensaio < 1,15·As·fy — não passa")
    return ResultadoResistenciaEmenda(F, As, fy, Fy, Fmin, v.ok, gov, memoria)


def verificar_luva(F_ensaio_kn: float, fy_barra_mpa: float,
                   As_cm2: float) -> ResultadoResistenciaEmenda:
    """Resistência da emenda mecânica por luva (9.5.3, PDF p. 65).

    A resistência da emenda deve atender às normas técnicas aplicáveis; na
    ausência delas, ser no mínimo 15 % maior que a resistência de escoamento
    da barra emendada, obtida em ensaios:
        F,ensaio >= 1,15·As·fy
    ``fy_barra_mpa`` é a tensão de escoamento da barra obtida em ensaio (na
    falta dela, o usuário pode passar fyk, e a verificação é a do valor
    nominal). As em cm², fy em MPa, forças em kN.
    """
    return _resistencia_emenda_115(F_ensaio_kn, fy_barra_mpa, As_cm2,
                                   "9.5.3", "luva")


# ===========================================================================
# 9.5.4 — Emendas por solda (PDF p. 65-66, Figura 9.6)
# ===========================================================================
PHI_MIN_TOPO_CALDEAMENTO_MM = 10.0
PHI_MIN_TOPO_ELETRODO_MM = 20.0
CORDAO_MIN_PHI = 5.0
AFASTAMENTO_CORDOES_MIN_PHI = 5.0
ESPESSURA_CORDAO_MIN_PHI = 0.3   # Figura 9.6, cortes a-a e b-b

TIPOS_EMENDA_SOLDA = ("topo_caldeamento", "topo_eletrodo", "traspasse",
                      "cobrejuntas")


@dataclass(frozen=True)
class ResultadoEmendaSolda:
    tipo: str
    phi_mm: float
    verificacoes: tuple[tuple[str, bool], ...]
    resistencia: ResultadoResistenciaEmenda | None
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_emenda_solda(
    tipo: str,
    phi_mm: float,
    n_cordoes: int | None = None,
    comprimento_cordao_mm: float | None = None,
    afastamento_cordoes_mm: float | None = None,
    espessura_cordao_mm: float | None = None,
    phi_cobrejunta_mm: float | None = None,
    F_ensaio_kn: float | None = None,
    fy_barra_mpa: float | None = None,
    As_cm2: float | None = None,
) -> ResultadoEmendaSolda:
    """Verifica a geometria e, se houver ensaio, a resistência da emenda por
    solda (9.5.4, PDF p. 65-66, Figura 9.6).

    tipo:
    - 'topo_caldeamento': de topo, por caldeamento, bitola >= 10 mm;
    - 'topo_eletrodo': de topo, com eletrodo, bitola >= 20 mm;
    - 'traspasse': pelo menos dois cordões longitudinais, cada um com
      comprimento >= 5·φ, afastados no mínimo 5·φ (``n_cordoes``,
      ``comprimento_cordao_mm``, ``afastamento_cordoes_mm`` obrigatórios);
      espessura do cordão >= 0,3·φ (Figura 9.6, corte a-a), se informada;
    - 'cobrejuntas': barras justapostas com cordões longitudinais de
      comprimento >= 5·φ cada (``comprimento_cordao_mm`` obrigatório), com o
      eixo baricêntrico do conjunto coincidente com o das barras emendadas
      (condição do projetista); espessura >= 0,3·φ2 da cobrejunta (Figura
      9.6, corte b-b), se informadas a espessura e ``phi_cobrejunta_mm``.

    Resistência: com ``F_ensaio_kn``, ``fy_barra_mpa`` e ``As_cm2``, confere
    F,ensaio >= 1,15·As·fy (na ausência de norma específica). A redução de
    20 % da resistência de barra tracionada com carga variável preponderante
    está em ``fator_resistencia_emenda_solda``; "mesma seção", em
    ``mesma_secao_solda``.
    """
    t = str(tipo).strip().lower()
    if t not in TIPOS_EMENDA_SOLDA:
        raise ValueError(
            f"tipo de emenda por solda deve ser um de {TIPOS_EMENDA_SOLDA}: {tipo!r}."
        )
    phi = _positivo(phi_mm, "phi_mm")
    checks: list[tuple[str, bool]] = []
    memoria: list[str] = []

    def _req(valor, nome):
        if valor is None:
            raise ValueError(f"Informe {nome} para emenda por solda '{t}' (9.5.4).")
        return float(valor)

    if t == "topo_caldeamento":
        ok = phi >= PHI_MIN_TOPO_CALDEAMENTO_MM - _TOL
        checks.append(("φ >= 10 mm", ok))
        memoria.append(f"9.5.4: de topo por caldeamento, φ = {_fmt(phi)} mm >= "
                       f"10 mm -> {'ok' if ok else 'não ok'}.")
    elif t == "topo_eletrodo":
        ok = phi >= PHI_MIN_TOPO_ELETRODO_MM - _TOL
        checks.append(("φ >= 20 mm", ok))
        memoria.append(f"9.5.4: de topo com eletrodo, φ = {_fmt(phi)} mm >= "
                       f"20 mm -> {'ok' if ok else 'não ok'}.")
    else:
        lc = _req(comprimento_cordao_mm, "comprimento_cordao_mm")
        lc_min = CORDAO_MIN_PHI * phi
        ok_lc = lc >= lc_min - _TOL
        checks.append(("cordão >= 5·φ", ok_lc))
        memoria.append(f"9.5.4: comprimento de cada cordão = {_fmt(lc)} mm >= "
                       f"5·φ = {_fmt(lc_min)} mm -> {'ok' if ok_lc else 'não ok'}.")
        if t == "traspasse":
            nc = int(_req(n_cordoes, "n_cordoes"))
            ok_n = nc >= 2
            checks.append(("pelo menos 2 cordões", ok_n))
            memoria.append(f"9.5.4: {nc} cordões longitudinais >= 2 -> "
                           f"{'ok' if ok_n else 'não ok'}.")
            af = _req(afastamento_cordoes_mm, "afastamento_cordoes_mm")
            af_min = AFASTAMENTO_CORDOES_MIN_PHI * phi
            ok_af = af >= af_min - _TOL
            checks.append(("cordões afastados >= 5·φ", ok_af))
            memoria.append(f"9.5.4: afastamento entre cordões = {_fmt(af)} mm >= "
                           f"5·φ = {_fmt(af_min)} mm -> {'ok' if ok_af else 'não ok'}.")
            phi_ref = phi
        else:
            phi_ref = (_positivo(phi_cobrejunta_mm, "phi_cobrejunta_mm")
                       if phi_cobrejunta_mm is not None else None)
        if espessura_cordao_mm is not None and phi_ref is not None:
            e = float(espessura_cordao_mm)
            e_min = ESPESSURA_CORDAO_MIN_PHI * phi_ref
            ok_e = e >= e_min - _TOL
            checks.append(("espessura do cordão >= 0,3·φ", ok_e))
            memoria.append(f"Figura 9.6: espessura do cordão = {_fmt(e)} mm >= "
                           f"0,3·{_fmt(phi_ref)} = {_fmt(e_min)} mm -> "
                           f"{'ok' if ok_e else 'não ok'}.")

    resist = None
    if F_ensaio_kn is not None:
        if fy_barra_mpa is None or As_cm2 is None:
            raise ValueError(
                "Para conferir a resistência (9.5.4), informe F_ensaio_kn, "
                "fy_barra_mpa e As_cm2."
            )
        resist = _resistencia_emenda_115(F_ensaio_kn, fy_barra_mpa, As_cm2,
                                         "9.5.4", "emenda soldada")
        checks.append(("F,ensaio >= 1,15·As·fy", resist.ok))
        memoria.extend(resist.memoria)

    ok = all(c for _, c in checks)
    falhas = [nome for nome, c in checks if not c]
    governante = (f"9.5.4 ({t}): atende" if ok
                  else f"9.5.4 ({t}): não atende — " + "; ".join(falhas))
    return ResultadoEmendaSolda(
        tipo=t, phi_mm=phi, verificacoes=tuple(checks), resistencia=resist,
        ok=ok, governante=governante, memoria=tuple(memoria),
    )


def mesma_secao_solda(distancia_centros_cm: float, phi_mm: float) -> bool:
    """True se duas emendas por solda estão na mesma seção: afastadas de
    centro a centro, na direção do eixo da barra, menos que 15·φ (9.5.4,
    PDF p. 66). Exatamente 15·φ já não é mesma seção. As emendas por solda
    podem ser feitas na totalidade das barras de uma seção.
    """
    d = float(distancia_centros_cm)
    if d < 0.0:
        raise ValueError("distancia_centros_cm não pode ser negativa (9.5.4).")
    return d < MESMA_SECAO_SOLDA_PHI * _positivo(phi_mm, "phi_mm") / 10.0 - _TOL


def fator_resistencia_emenda_solda(tracionada: bool,
                                   variavel_preponderante: bool) -> float:
    """Fator sobre a resistência de cada barra emendada por solda (9.5.4,
    PDF p. 66): 1,0 (sem redução); 0,8 (redução de 20 %) em barra
    tracionada com preponderância de carga variável.
    """
    if tracionada and variavel_preponderante:
        return FATOR_REDUCAO_SOLDA_VARIAVEL
    return 1.0


def resistencia_emenda_solda_kn(As_cm2: float, fyd_mpa: float,
                                tracionada: bool,
                                variavel_preponderante: bool) -> float:
    """Resistência de cálculo da barra emendada por solda, kN (9.5.4, PDF
    p. 66): As·fyd sem redução, ou 0,8·As·fyd em barra tracionada com
    preponderância de carga variável. As em cm², fyd em MPa (/10 -> kN).
    """
    As = _positivo(As_cm2, "As_cm2")
    f = _positivo(fyd_mpa, "fyd_mpa")
    return fator_resistencia_emenda_solda(tracionada, variavel_preponderante) * As * f / 10.0
