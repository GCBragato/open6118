"""Detalhamento de pilares — ABNT NBR 6118:2026, Seção 18.4.

Cobre a armadura longitudinal (18.4.2: diâmetro mínimo e máximo, distribuição
transversal, espaçamentos mínimo e máximo) e a armadura transversal (18.4.3:
diâmetro mínimo do estribo, espaçamento máximo básico, a redução admissível
com φt < φ/4 e a nota de dutilidade para concreto de alta resistência) dos
pilares comuns (18.4.1: maior dimensão da seção <= 5 vezes a menor; acima
disso, pilar-parede, 18.5 — ver ``classificacao_elementos_nbr6118.eh_pilar_parede``,
P11).

Convenções: geometria em cm; diâmetro em mm; página do PDF citada em cada
função (impressa = PDF - 18). Fora da faixa de validade de uma fórmula, as
funções levantam ``FaixaNormativaError`` (subclasse de ``ValueError``,
importada do núcleo); caso que a norma não define (por exemplo, o fator
24φ/12φ fora de CA-25/CA-50) também levanta ``FaixaNormativaError``, dizendo
que a norma não define aquele caso. Função de verificação devolve
``@dataclass(frozen=True)`` com ``ok``, ``governante`` e ``memoria`` (a
memória de cálculo).
"""

from __future__ import annotations

from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError


# ---------------------------------------------------------------------------
# 18.4.2.1 — Diâmetro mínimo e máximo da barra longitudinal (PDF p. 173)
# ---------------------------------------------------------------------------
PHI_LONGITUDINAL_MIN_MM = 10.0   # 18.4.2.1
FATOR_PHI_LONGITUDINAL_MAX = 1.0 / 8.0   # 1/8 da menor dimensão da seção


def phi_longitudinal_limites_mm(b_min_cm: float) -> tuple[float, float]:
    """Faixa admissível de diâmetro da barra longitudinal de pilar (18.4.2.1, p. 173).

    10 mm <= φ <= (1/8)·b_min, com b_min a menor dimensão da seção
    transversal, em cm (convertida para mm dentro da função: b_min_cm·10).

    Devolve (φ_min_mm, φ_max_mm). b_min_cm <= 0 levanta ``ValueError``.
    """
    b = float(b_min_cm)
    if b <= 0.0:
        raise ValueError("b_min_cm deve ser positivo.")
    phi_max_mm = b * 10.0 * FATOR_PHI_LONGITUDINAL_MAX
    return PHI_LONGITUDINAL_MIN_MM, phi_max_mm


# ---------------------------------------------------------------------------
# 18.4.2.2 — Distribuição transversal: número mínimo de barras (PDF p. 173)
# ---------------------------------------------------------------------------
N_MIN_BARRAS_CIRCULAR = 6

# Nomes usuais de seção poligonal -> número de vértices (1 barra por
# vértice, 18.4.2.2). Fora dessa lista, informe o número de vértices
# diretamente (int).
FORMAS_N_VERTICES = {
    "triangular": 3,
    "retangular": 4,
    "quadrada": 4,
    "pentagonal": 5,
    "hexagonal": 6,
    "octogonal": 8,
}


def n_min_barras(forma: str | int) -> int:
    """Número mínimo de barras longitudinais pela geometria da seção (18.4.2.2, p. 173).

    - Seção poligonal: pelo menos uma barra em cada vértice. ``forma`` pode
      ser o número de vértices (int, >= 3) ou um nome usual
      ('retangular'/'quadrada' = 4, 'triangular' = 3, 'pentagonal' = 5,
      'hexagonal' = 6, 'octogonal' = 8).
    - Seção circular: no mínimo 6 barras distribuídas ao longo do
      perímetro. ``forma='circular'``.
    """
    if isinstance(forma, str):
        chave = forma.strip().lower()
        if chave in ("circular", "circulo", "círculo"):
            return N_MIN_BARRAS_CIRCULAR
        if chave in FORMAS_N_VERTICES:
            return FORMAS_N_VERTICES[chave]
        raise ValueError(
            f"forma desconhecida: {forma!r}. Use 'circular', um nome usual "
            f"({sorted(FORMAS_N_VERTICES)}) ou o número de vértices (int)."
        )
    n = int(forma)
    if n < 3:
        raise ValueError("Seção poligonal precisa de pelo menos 3 vértices.")
    return n


# ---------------------------------------------------------------------------
# 18.4.2.2 — Espaçamento mínimo livre entre barras longitudinais (PDF p. 173)
# ---------------------------------------------------------------------------
ESPACAMENTO_LIVRE_MIN_ABSOLUTO_MM = 20.0
FATOR_DMAX_AGREGADO = 1.2


def espacamento_min_livre_cm(phi_mm: float, phi_n_mm: float | None = None,
                              dmax_agregado_mm: float | None = None) -> float:
    """Espaçamento mínimo livre entre faces de barras longitudinais de pilar,
    fora da região de emendas (18.4.2.2, p. 173; vale também nas regiões de
    emenda por traspasse).

    max(20 mm; φ da barra, do feixe ou da luva; 1,2·dmáx do agregado graúdo).

    ``phi_mm``: diâmetro da barra isolada. ``phi_n_mm``: diâmetro
    equivalente do feixe ou da luva, quando houver (φn = φ·√n, ver
    ``nucleo_nbr6118.phi_n_feixe``). ``dmax_agregado_mm``: dimensão máxima
    característica do agregado graúdo, quando conhecida.

    Devolve o espaçamento em cm (conversão interna: os candidatos são
    calculados em mm e o maior deles é dividido por 10).
    """
    candidatos_mm = [ESPACAMENTO_LIVRE_MIN_ABSOLUTO_MM, float(phi_mm)]
    if phi_n_mm is not None:
        candidatos_mm.append(float(phi_n_mm))
    if dmax_agregado_mm is not None:
        candidatos_mm.append(FATOR_DMAX_AGREGADO * float(dmax_agregado_mm))
    return max(candidatos_mm) / 10.0


# ---------------------------------------------------------------------------
# 18.4.2.2 — Espaçamento máximo entre eixos das barras longitudinais (PDF p. 174)
# ---------------------------------------------------------------------------
ESPACAMENTO_EIXOS_MAX_ABSOLUTO_CM = 40.0  # 400 mm
FATOR_ESPACAMENTO_EIXOS = 2.0


def espacamento_max_eixos_cm(b_min_cm: float) -> float:
    """Espaçamento máximo entre eixos das barras (ou dos centros de feixes),
    ao longo do perímetro da seção (18.4.2.2, p. 174).

    min(2·b_min; 400 mm), com b_min a menor dimensão da seção no trecho
    considerado, em cm.
    """
    b = float(b_min_cm)
    if b <= 0.0:
        raise ValueError("b_min_cm deve ser positivo.")
    return min(FATOR_ESPACAMENTO_EIXOS * b, ESPACAMENTO_EIXOS_MAX_ABSOLUTO_CM)


# ---------------------------------------------------------------------------
# 18.4.3 — Diâmetro mínimo do estribo (PDF p. 174)
# ---------------------------------------------------------------------------
PHI_ESTRIBO_MIN_ABSOLUTO_MM = 5.0
FATOR_PHI_ESTRIBO_MIN = 1.0 / 4.0


def phi_min_estribo_pilar_mm(phi_longitudinal_mm: float) -> float:
    """Diâmetro mínimo do estribo de pilar (18.4.3, p. 174).

    max(5 mm; φ/4), com φ o diâmetro da barra longitudinal isolada ou o
    diâmetro equivalente do feixe que constitui a armadura longitudinal
    (``phi_longitudinal_mm``; para feixe, informe φn = φ·√n, ver
    ``nucleo_nbr6118.phi_n_feixe``).
    """
    phi = float(phi_longitudinal_mm)
    if phi <= 0.0:
        raise ValueError("phi_longitudinal_mm deve ser positivo.")
    return max(PHI_ESTRIBO_MIN_ABSOLUTO_MM, FATOR_PHI_ESTRIBO_MIN * phi)


# ---------------------------------------------------------------------------
# 18.4.3 — Espaçamento longitudinal máximo entre estribos (PDF p. 174)
# ---------------------------------------------------------------------------
S_ESTRIBO_MAX_ABSOLUTO_CM = 20.0  # 200 mm
FATOR_S_ESTRIBO_LONGITUDINAL = {"ca25": 24.0, "ca50": 12.0}


def _chave_aco(aco: str) -> str:
    return str(aco).strip().lower().replace("-", "").replace(" ", "")


def s_max_estribo_pilar_basico_cm(b_min_cm: float, phi_long_mm: float,
                                   aco: str = "CA-50") -> float:
    """Espaçamento longitudinal máximo básico entre estribos de pilar
    (18.4.3, p. 174), para posicionamento, para impedir a flambagem das
    longitudinais e para costurar as emendas.

    min(200 mm; menor dimensão da seção; 24φ para CA-25, 12φ para CA-50),
    com φ o diâmetro da barra longitudinal (ou o φn equivalente do feixe).

    A norma só dá o fator 24φ/12φ para CA-25 e CA-50: outra categoria
    levanta ``FaixaNormativaError`` (o caso não é definido).
    """
    chave = _chave_aco(aco)
    if chave not in FATOR_S_ESTRIBO_LONGITUDINAL:
        raise FaixaNormativaError(
            f"18.4.3 não define o fator de espaçamento (24φ/12φ) para aco={aco!r}; "
            "use CA-25 ou CA-50."
        )
    b = float(b_min_cm)
    phi = float(phi_long_mm)
    if b <= 0.0 or phi <= 0.0:
        raise ValueError("b_min_cm e phi_long_mm devem ser positivos.")
    s_fator_cm = FATOR_S_ESTRIBO_LONGITUDINAL[chave] * phi / 10.0
    return min(S_ESTRIBO_MAX_ABSOLUTO_CM, b, s_fator_cm)


def s_max_estribo_pilar_phi_reduzido_mm(phi_t_mm: float, phi_long_mm: float,
                                         fyk_mpa: float) -> float:
    """Limite adicional de espaçamento quando se adota φt < φ/4 (18.4.3, p. 174).

    smax = 90000·(φt²/φ)·(1/fyk), com φt e φ em mm e fyk em MPa; smax em mm.

    Só vale com φt e φ do mesmo tipo de aço, e quando φt < φ/4: fora dessa
    condição, levanta ``FaixaNormativaError`` (a norma não admite esta
    fórmula fora dela — o critério básico de 18.4.3 é quem manda).
    """
    phi_t = float(phi_t_mm)
    phi = float(phi_long_mm)
    fyk = float(fyk_mpa)
    if phi_t <= 0.0 or phi <= 0.0 or fyk <= 0.0:
        raise ValueError("phi_t_mm, phi_long_mm e fyk_mpa devem ser positivos.")
    if not (phi_t < phi / 4.0 - 1e-9):
        raise FaixaNormativaError(
            f"18.4.3: a fórmula de φt reduzido só vale com φt < φ/4 "
            f"({phi_t:g} mm < {phi / 4.0:g} mm); aqui φt não é menor."
        )
    return 90000.0 * (phi_t ** 2 / phi) * (1.0 / fyk)


FCK_MIN_ALTA_RESISTENCIA_DUTILIDADE = 55.0  # NOTA de 18.4.3: C55 a C90
FCK_MAX_ALTA_RESISTENCIA_DUTILIDADE = 90.0
FATOR_REDUCAO_DUTILIDADE = 0.5


def s_max_estribo_pilar_reduzido_dutilidade_cm(s_max_cm: float, fck_mpa: float) -> float:
    """Aplica a recomendação da NOTA de 18.4.3 (p. 174): para concreto de
    classe C55 a C90, reduzir o espaçamento máximo de estribos em 50 %,
    com ganchos de pelo menos 135°, visando à dutilidade dos pilares.

    Fora de C55-C90 devolve ``s_max_cm`` sem alteração (a nota não se
    aplica). ``fck_mpa`` fora de 20-90 MPa levanta ``FaixaNormativaError``
    (validado pelo núcleo).
    """
    fck = nbr.validar_fck(fck_mpa)
    s_max = float(s_max_cm)
    if FCK_MIN_ALTA_RESISTENCIA_DUTILIDADE - 1e-9 <= fck <= FCK_MAX_ALTA_RESISTENCIA_DUTILIDADE + 1e-9:
        return FATOR_REDUCAO_DUTILIDADE * s_max
    return s_max


def s_max_estribo_pilar_cm(b_min_cm: float, phi_long_mm: float, aco: str = "CA-50",
                            phi_t_mm: float | None = None, fyk_mpa: float | None = None,
                            fck_mpa: float | None = None) -> float:
    """Espaçamento longitudinal máximo entre estribos de pilar, reunindo os
    três critérios de 18.4.3 (p. 174): o básico (``s_max_estribo_pilar_basico_cm``),
    a redução opcional quando φt < φ/4 (``s_max_estribo_pilar_phi_reduzido_mm``,
    quando ``phi_t_mm`` e ``fyk_mpa`` são informados e a condição se aplica) e
    a redução recomendada de 50 % para concreto C55-C90
    (``s_max_estribo_pilar_reduzido_dutilidade_cm``, quando ``fck_mpa`` é
    informado). Quando houver necessidade de armadura transversal para
    cortante ou torção, compare também com os mínimos de 18.3 (vigas) e
    adote o menor -- fora do escopo desta função, que só cobre 18.4.3.
    """
    candidatos_cm = [s_max_estribo_pilar_basico_cm(b_min_cm, phi_long_mm, aco)]
    if phi_t_mm is not None and fyk_mpa is not None:
        try:
            s_reduzido_mm = s_max_estribo_pilar_phi_reduzido_mm(phi_t_mm, phi_long_mm, fyk_mpa)
            candidatos_cm.append(s_reduzido_mm / 10.0)
        except FaixaNormativaError:
            pass  # φt >= φ/4: este critério não se aplica, apenas o básico vale.
    s_antes_dutilidade = min(candidatos_cm)
    if fck_mpa is not None:
        return s_max_estribo_pilar_reduzido_dutilidade_cm(s_antes_dutilidade, fck_mpa)
    return s_antes_dutilidade


# ---------------------------------------------------------------------------
# Verificação conjunta do detalhamento (18.4.2 e 18.4.3)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoDetalhamentoPilar:
    b_min_cm: float
    phi_long_mm: float
    phi_long_min_mm: float
    phi_long_max_mm: float
    n_min_barras: int
    n_barras: int
    phi_n_feixe_mm: float | None
    espacamento_livre_min_cm: float
    espacamento_livre_real_cm: float | None
    espacamento_eixos_max_cm: float
    espacamento_eixos_real_cm: float | None
    phi_estribo_mm: float
    phi_estribo_min_mm: float
    s_estribo_max_cm: float
    s_estribo_real_cm: float | None
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_detalhamento_pilar(
    b_min_cm: float,
    forma: str | int,
    n_barras: int,
    phi_long_mm: float,
    phi_estribo_mm: float,
    *,
    aco_longitudinal: str = "CA-50",
    n_barras_feixe: int = 1,
    dmax_agregado_mm: float | None = None,
    espacamento_livre_real_cm: float | None = None,
    espacamento_eixos_real_cm: float | None = None,
    s_estribo_real_cm: float | None = None,
    fyk_mpa: float | None = None,
    fck_mpa: float | None = None,
) -> ResultadoDetalhamentoPilar:
    """Reúne as verificações de 18.4.2 e 18.4.3 (p. 173-174) para um pilar comum
    (18.4.1: maior dimensão <= 5x a menor; acima disso, ver
    ``classificacao_elementos_nbr6118.eh_pilar_parede`` e 18.5).

    ``forma``: geometria da seção (ver ``n_min_barras``). ``n_barras_feixe``:
    número de barras por feixe, se houver (>= 2 usa φn = φ·√n em todos os
    limites que dependem do diâmetro longitudinal; 1 = barra isolada).
    Os parâmetros ``*_real_*`` são os valores efetivamente adotados no
    detalhamento; quando omitidos, o respectivo critério não é confrontado
    (a função ainda devolve o limite calculado).
    """
    b = float(b_min_cm)
    phi_long = float(phi_long_mm)
    phi_estribo = float(phi_estribo_mm)
    n = int(n_barras)

    phi_min, phi_max = phi_longitudinal_limites_mm(b)
    n_min = n_min_barras(forma)
    phi_n = nbr.phi_n_feixe(phi_long, n_barras_feixe) if n_barras_feixe and n_barras_feixe > 1 else None
    phi_para_espacamentos = phi_n if phi_n is not None else phi_long

    esp_livre_min = espacamento_min_livre_cm(phi_long, phi_n, dmax_agregado_mm)
    esp_eixos_max = espacamento_max_eixos_cm(b)
    phi_estribo_min = phi_min_estribo_pilar_mm(phi_para_espacamentos)
    s_estribo_max = s_max_estribo_pilar_cm(
        b, phi_long, aco_longitudinal,
        phi_t_mm=phi_estribo, fyk_mpa=fyk_mpa, fck_mpa=fck_mpa,
    )

    memoria: list[str] = []
    checagens: list[tuple[str, bool]] = []

    ok_phi_long = phi_min - 1e-9 <= phi_long <= phi_max + 1e-9
    checagens.append(("18.4.2.1 diâmetro da barra longitudinal", ok_phi_long))
    memoria.append(
        f"18.4.2.1: {phi_min:g} mm <= φ = {phi_long:g} mm <= {phi_max:g} mm "
        f"(1/8 de {b:g} cm) -> {'ok' if ok_phi_long else 'reprovado'}."
    )

    ok_n_barras = n >= n_min
    checagens.append(("18.4.2.2 número mínimo de barras", ok_n_barras))
    memoria.append(
        f"18.4.2.2: n = {n} barras >= mínimo de {n_min} ({forma!r}) -> "
        f"{'ok' if ok_n_barras else 'reprovado'}."
    )

    memoria.append(
        f"18.4.2.2: espaçamento livre mínimo = {esp_livre_min:.2f} cm "
        f"(máx. entre 20 mm, φ{'n' if phi_n is not None else ''} = "
        f"{phi_para_espacamentos:g} mm e 1,2·dmáx)."
    )
    if espacamento_livre_real_cm is not None:
        ok_esp_livre = float(espacamento_livre_real_cm) + 1e-9 >= esp_livre_min
        checagens.append(("18.4.2.2 espaçamento livre mínimo", ok_esp_livre))
        memoria.append(
            f"18.4.2.2: espaçamento livre adotado = {float(espacamento_livre_real_cm):.2f} cm "
            f"-> {'ok' if ok_esp_livre else 'reprovado'}."
        )

    memoria.append(f"18.4.2.2: espaçamento máximo entre eixos = {esp_eixos_max:.2f} cm.")
    if espacamento_eixos_real_cm is not None:
        ok_esp_eixos = float(espacamento_eixos_real_cm) <= esp_eixos_max + 1e-9
        checagens.append(("18.4.2.2 espaçamento máximo entre eixos", ok_esp_eixos))
        memoria.append(
            f"18.4.2.2: espaçamento entre eixos adotado = {float(espacamento_eixos_real_cm):.2f} cm "
            f"-> {'ok' if ok_esp_eixos else 'reprovado'}."
        )

    ok_phi_estribo = phi_estribo + 1e-9 >= phi_estribo_min
    checagens.append(("18.4.3 diâmetro mínimo do estribo", ok_phi_estribo))
    memoria.append(
        f"18.4.3: φt = {phi_estribo:g} mm >= φt,mín = {phi_estribo_min:g} mm "
        f"(máx. entre 5 mm e φ/4 = {phi_para_espacamentos / 4.0:g} mm) -> "
        f"{'ok' if ok_phi_estribo else 'reprovado'}."
    )

    memoria.append(f"18.4.3: espaçamento máximo entre estribos = {s_estribo_max:.2f} cm.")
    if s_estribo_real_cm is not None:
        ok_s_estribo = float(s_estribo_real_cm) <= s_estribo_max + 1e-9
        checagens.append(("18.4.3 espaçamento máximo entre estribos", ok_s_estribo))
        memoria.append(
            f"18.4.3: espaçamento entre estribos adotado = {float(s_estribo_real_cm):.2f} cm "
            f"-> {'ok' if ok_s_estribo else 'reprovado'}."
        )

    ok = all(okk for _, okk in checagens)
    reprovados = [nome for nome, okk in checagens if not okk]
    governante = reprovados[0] if reprovados else "nenhum critério reprovado (18.4)"

    return ResultadoDetalhamentoPilar(
        b_min_cm=b, phi_long_mm=phi_long, phi_long_min_mm=phi_min, phi_long_max_mm=phi_max,
        n_min_barras=n_min, n_barras=n, phi_n_feixe_mm=phi_n,
        espacamento_livre_min_cm=esp_livre_min,
        espacamento_livre_real_cm=(float(espacamento_livre_real_cm) if espacamento_livre_real_cm is not None else None),
        espacamento_eixos_max_cm=esp_eixos_max,
        espacamento_eixos_real_cm=(float(espacamento_eixos_real_cm) if espacamento_eixos_real_cm is not None else None),
        phi_estribo_mm=phi_estribo, phi_estribo_min_mm=phi_estribo_min,
        s_estribo_max_cm=s_estribo_max,
        s_estribo_real_cm=(float(s_estribo_real_cm) if s_estribo_real_cm is not None else None),
        ok=ok, governante=governante, memoria=tuple(memoria),
    )
