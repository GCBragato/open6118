"""Detalhamento de lajes — ABNT NBR 6118:2026 (P18 do plano de implementação).

Cobre:

- 20.1 — prescrições gerais de detalhamento de lajes: diâmetro máximo de
  barra de flexão, espaçamento máximo da armadura principal, vedação de
  escalonamento e prolongamento mínimo da armadura positiva no apoio,
  armadura secundária positiva mínima e espaçamento máximo, espaçamento
  máximo de estribos em nervuras de laje nervurada (PDF p. 192);
- 20.3.1 — armaduras passivas de lajes sem vigas (lisas/cogumelo)
  calculadas pelo processo aproximado de 14.7.8: distribuição por faixas da
  Figura 20.2, mínimo de barras inferiores contínuas sobre os apoios
  (articulada com a armadura contra colapso progressivo de 19.5.4) e
  penetração mínima no capitel (PDF p. 194);
- 20.5.1 e 20.5.2 — lajes armadas com telas soldadas nervuradas (NBR 7481):
  ancoragem no apoio sobre viga e emenda por sobreposição de malhas ou fios
  (PDF p. 196);
- 20.6 — armadura de segurança na face inferior de laje em balanço
  (marquise), contra colapso total em caso de ruptura na seção de apoio
  (PDF p. 197).

Convenções: geometria e comprimentos em cm; diâmetro em mm; carga
distribuída em kN/m²; força em kN; momento em kN·cm; área de armadura em
cm² ou cm²/m. Página do PDF citada em cada função (impressa = PDF − 18).
Fora da faixa de validade, as funções levantam ``FaixaNormativaError``
(subclasse de ``ValueError``, do núcleo ``nucleo_nbr6118``). Função de
verificação ou dimensionamento devolve ``@dataclass(frozen=True)`` com os
valores, os limites, ``ok``, ``governante`` e ``memoria`` (a memória de
cálculo).

A Figura 20.2 (distribuição de armadura em lajes sem vigas) foi lida na
imagem da página (``SCRATCH\\nbr_png\\p194.png``); o texto extraído do PDF
embaralha os percentuais e as frações de vão (risco 7 do plano). Nessa
figura, o ponto de referência das cotas depende do tipo de apoio: no apoio
interno (única linha tracejada, "Eixo de apoio interno") as cotas partem do
eixo; no apoio externo a figura separa "Eixo de apoio externo" de "Face de
apoio", e as cotas de extensão mínima partem da face, não do eixo (ver
``distribuicao_faixas_laje_lisa``).

A armadura de 19.5.4 (colapso progressivo) ainda não está implementada em
nenhum módulo do worktree (P19 não integrado): ``barras_continuas_apoio_min``
recebe ``As_ccp_cm2`` como parâmetro, sem reimplementar 19.5.4.

Não confundir a armadura de segurança de laje em balanço aqui tratada (20.6)
com o γn de 13.2.4.1 (``lajes_nbr6118.gama_n_laje_balanco``), que majora o
momento de cálculo da própria laje em balanço: são exigências distintas com
o mesmo nome "balanço" (risco 3 do plano).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError

_TOL = 1e-9


def _fmt(v: float) -> str:
    return f"{v:.4g}"


def _positivo(valor: float, nome: str) -> float:
    v = float(valor)
    if v <= 0.0:
        raise FaixaNormativaError(f"{nome} deve ser positivo (recebido {v:g}).")
    return v


def _nao_negativo(valor: float, nome: str) -> float:
    v = float(valor)
    if v < 0.0:
        raise FaixaNormativaError(f"{nome} não pode ser negativo (recebido {v:g}).")
    return v


# ---------------------------------------------------------------------------
# 20.1 — Prescrições gerais (PDF p. 192)
# ---------------------------------------------------------------------------
def phi_max_laje_mm(h_cm: float) -> float:
    """Diâmetro máximo admissível de qualquer barra da armadura de flexão de laje (20.1, PDF p. 192).

    φmáx = h/8. ``h_cm`` é a espessura da laje, em cm; o resultado é φmáx em
    mm (h/8 dá cm, convertido ×10 para mm).
    """
    h = _positivo(h_cm, "h_cm")
    return (h / 8.0) * 10.0


def espacamento_max_principal_cm(h_cm: float, phi_mm: float) -> float:
    """Espaçamento máximo entre barras da armadura principal de flexão, na região dos maiores momentos fletores (20.1, PDF p. 192).

    s_máx = mín(2h, 20 cm). Para barras com φ >= 20 mm, a norma permite
    relaxar o espaçamento máximo para 15φ, que passa a valer no lugar do
    mínimo entre 2h e 20 cm (não se somam os dois critérios).
    """
    h = _positivo(h_cm, "h_cm")
    phi = _nao_negativo(phi_mm, "phi_mm")
    if phi >= 20.0:
        return 15.0 * (phi / 10.0)
    return min(2.0 * h, 20.0)


def prolongamento_positivo_apoio_cm(lb_nec_cm: float = 0.0) -> float:
    """Prolongamento mínimo da armadura positiva além do eixo teórico do apoio, sem escalonamento (20.1, PDF p. 192).

    Vale para laje maciça armada em uma ou em duas direções, em que seja
    dispensada armadura transversal (19.4.1) e não haja avaliação explícita
    dos acréscimos de armadura decorrentes dos momentos volventes: nesse
    caso, toda a armadura positiva deve ser levada até os apoios, sem
    escalonamento, e prolongada no mínimo 4 cm além do eixo teórico do
    apoio. Quando a ancoragem exigida pela Seção 9
    (``ancoragem_nbr6118.comprimento_ancoragem``, recebida em ``lb_nec_cm``)
    for maior, prevalece o maior dos dois comprimentos.
    """
    lb = _nao_negativo(lb_nec_cm, "lb_nec_cm")
    return max(4.0, lb)


def As_secundaria_min_cm2_por_m(As_principal_cm2_por_m: float) -> float:
    """Armadura secundária positiva mínima, em relação à armadura principal (20.1, PDF p. 192).

    As,sec,mín = 0,20 * As,principal (cm²/m). A emenda dessas barras deve
    respeitar os mesmos critérios de emenda das barras da armadura
    principal (não coberto por esta função; ver ``emendas_nbr6118``, P27).
    """
    As = _positivo(As_principal_cm2_por_m, "As_principal_cm2_por_m")
    return 0.20 * As


def espacamento_max_secundaria_cm() -> float:
    """Espaçamento máximo entre as barras da armadura secundária positiva: 33 cm (20.1, PDF p. 192)."""
    return 33.0


def espacamento_max_estribo_nervura_cm() -> float:
    """Espaçamento máximo dos estribos em nervuras de laje nervurada, quando necessários: 20 cm (20.1, PDF p. 192)."""
    return 20.0


# ---------------------------------------------------------------------------
# 20.3.1 — Lajes sem vigas: armaduras passivas (PDF p. 194)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DistribuicaoFaixasLajeLisa:
    """Extensões mínimas/máximas (cm) para a distribuição de armadura da Figura 20.2.

    No apoio interno (única linha tracejada na figura), a extensão é medida
    a partir do eixo do apoio. No apoio externo, a figura desenha uma linha
    de "Eixo de apoio externo" separada da "Face de apoio", e as cotas
    >= 0,35 l / >= 0,25 l / >= 15 cm partem da face, não do eixo.
    """

    l_cm: float
    # Faixa externa (região dos apoios)
    faixa_ext_sup_50pct_min_cm: float       # 50 % das barras superiores: extensão >= 0,35 l
    faixa_ext_sup_restante_min_cm: float    # restante (50 %) das barras superiores: extensão >= 0,25 l
    faixa_ext_inf_100pct_min_cm: float      # 100 % das barras inferiores, contínuas: extensão >= 15 cm
    faixa_ext_inf_colapso_prog_max_cm: float  # trecho <= 0,125 l da armadura contra colapso progressivo (19.5.4)
    # Faixa interna (região central)
    faixa_int_sup_100pct_min_cm: float      # 100 % das barras superiores: extensão >= 0,25 l
    faixa_int_inf_33pct_min_cm: float       # 33 % das barras inferiores, contínuas: extensão >= 15 cm
    faixa_int_inf_restante_max_cm: float    # restante (67 %): corte a <= 0,125 l (mínimo absoluto 15 cm)
    soma_percentuais_ok: bool
    memoria: tuple[str, ...]


def distribuicao_faixas_laje_lisa(l_cm: float) -> DistribuicaoFaixasLajeLisa:
    """Distribuição das armaduras passivas de lajes sem vigas (lisas/cogumelo), calculadas pelo processo aproximado de 14.7.8, entre faixa externa (região dos apoios) e faixa interna (região central) — Figura 20.2 (20.3.1, PDF p. 194).

    ``l_cm`` é o vão, na direção considerada, entre eixos de apoio, em cm.
    O ponto de referência das cotas, lido na Figura 20.2, depende do tipo de
    apoio, não da faixa (externa ou interna): no apoio interno há uma única
    linha tracejada ("Eixo de apoio interno") e todas as cotas desse lado
    partem dela; no apoio externo a figura desenha duas linhas distintas —
    "Eixo de apoio externo" e "Face de apoio" — e todas as cotas
    (>= 0,35 l, >= 0,25 l e >= 15 cm, tanto da faixa externa quanto da
    faixa interna) partem da FACE, não do eixo (só o traço da armadura, no
    desenho, começa no eixo). Os valores numéricos devolvidos por esta
    função (0,35 l etc.) não dependem do ponto de referência; o que muda é
    a partir de onde medi-los ao transferir esta memória para o desenho:

    - Faixa externa / região dos apoios:
      - barras superiores: 50 % com extensão >= 0,35 l; o restante (50 %)
        com extensão >= 0,25 l;
      - barras inferiores: 100 %, prolongadas continuamente sobre o apoio,
        com extensão >= 15 cm. A cota <= 0,125 l, ligada na figura à chamada
        "armadura contra colapso progressivo" (19.5.4), delimita o trecho,
        medido a partir do mesmo ponto de referência (face no apoio
        externo, eixo no apoio interno), em que essa armadura deve estar
        contida.
    - Faixa interna / região central:
      - barras superiores: 100 % com extensão >= 0,25 l;
      - barras inferiores: 33 % com extensão >= 15 cm (armadura contínua,
        também ligada a 19.5.4); o restante (67 %) pode ser cortado a uma
        distância <= 0,125 l do mesmo ponto de referência. Quando
        0,125 l < 15 cm, a figura combina as duas cotas no mesmo trecho e
        prevalece o mínimo absoluto de 15 cm (por isso o valor devolvido é
        máx(15, 0,125 l)).

    Os percentuais de cada linha somam sempre 100 % (50+50, 100, 33+67),
    fixados pela norma; ``soma_percentuais_ok`` registra essa checagem.

    Fonte: Figura 20.2 lida na imagem da página (o texto extraído do PDF
    embaralha os percentuais e as frações de vão).
    """
    l = _positivo(l_cm, "l_cm")

    ext_sup_50 = 0.35 * l
    ext_sup_restante = 0.25 * l
    ext_inf_100 = 15.0
    corte_0125l = max(15.0, 0.125 * l)
    int_sup_100 = 0.25 * l
    int_inf_33 = 15.0

    soma_ok = True  # 50 % + 50 % = 100 %; 100 % = 100 %; 33 % + 67 % = 100 %

    memoria = (
        f"20.3.1 Fig. 20.2 (faixa externa, barras superiores): 50% com "
        f">= 0,35l = {_fmt(ext_sup_50)} cm; restante (50%) com "
        f">= 0,25l = {_fmt(ext_sup_restante)} cm.",
        f"20.3.1 Fig. 20.2 (faixa externa, barras inferiores): 100% "
        f"contínuas com >= 15 cm; armadura contra colapso progressivo "
        f"(19.5.4) contida em <= 0,125l = {_fmt(corte_0125l)} cm "
        f"(mínimo absoluto 15 cm).",
        f"20.3.1 Fig. 20.2 (faixa interna, barras superiores): 100% com "
        f">= 0,25l = {_fmt(int_sup_100)} cm.",
        f"20.3.1 Fig. 20.2 (faixa interna, barras inferiores): 33% "
        f"contínuas com >= 15 cm; restante (67%) cortado a "
        f"<= 0,125l = {_fmt(corte_0125l)} cm (mínimo absoluto 15 cm).",
    )

    return DistribuicaoFaixasLajeLisa(
        l_cm=l,
        faixa_ext_sup_50pct_min_cm=ext_sup_50,
        faixa_ext_sup_restante_min_cm=ext_sup_restante,
        faixa_ext_inf_100pct_min_cm=ext_inf_100,
        faixa_ext_inf_colapso_prog_max_cm=corte_0125l,
        faixa_int_sup_100pct_min_cm=int_sup_100,
        faixa_int_inf_33pct_min_cm=int_inf_33,
        faixa_int_inf_restante_max_cm=corte_0125l,
        soma_percentuais_ok=soma_ok,
        memoria=memoria,
    )


N_MIN_BARRAS_CONTINUAS_APOIO = 2


@dataclass(frozen=True)
class ResultadoBarrasContinuasApoio:
    n_barras_continuas: int
    n_min: int
    FSd_kn: float
    fyd_mpa: float
    As_ccp_cm2: float
    capacidade_kn: float
    capacidade_min_kn: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def barras_continuas_apoio_min(
    n_barras_continuas: int, FSd_kn: float, fyd_mpa: float, As_ccp_cm2: float,
) -> ResultadoBarrasContinuasApoio:
    """Mínimo de barras inferiores contínuas sobre cada apoio de laje sem vigas, coordenado com a armadura contra colapso progressivo (20.3.1, PDF p. 194).

    Verifica em conjunto:

    1. pelo menos duas barras inferiores (``n_barras_continuas >= 2``)
       passam continuamente sobre o apoio;
    2. fyd * As,ccp >= 1,5 * FSd (19.5.4), com fyd em MPa (convertido para
       kN/cm² dentro da função), As,ccp em cm² e FSd em kN.

    19.5.4 (armadura contra colapso progressivo) ainda não está implementada
    em nenhum módulo (depende de P19, não integrado neste worktree):
    ``As_ccp_cm2`` e ``FSd_kn`` são recebidos como parâmetro, sem
    reimplementar aquele item.
    """
    n = int(n_barras_continuas)
    FSd = _nao_negativo(FSd_kn, "FSd_kn")
    fyd = _positivo(fyd_mpa, "fyd_mpa")
    As_ccp = _nao_negativo(As_ccp_cm2, "As_ccp_cm2")

    capacidade = nbr.mpa_para_kncm2(fyd) * As_ccp
    capacidade_min = 1.5 * FSd
    ok_n = n >= N_MIN_BARRAS_CONTINUAS_APOIO
    ok_ccp = capacidade + _TOL >= capacidade_min
    ok = ok_n and ok_ccp

    memoria = (
        f"20.3.1: {n} barra(s) inferior(es) contínua(s) sobre o apoio "
        f"(mínimo {N_MIN_BARRAS_CONTINUAS_APOIO}) -> "
        f"{'ok' if ok_n else 'reprovado'}.",
        f"19.5.4: fyd*As,ccp = {_fmt(capacidade)} kN >= 1,5*FSd = "
        f"{_fmt(capacidade_min)} kN -> {'ok' if ok_ccp else 'reprovado'}.",
    )
    if ok:
        governante = "20.3.1 e 19.5.4 atendidos"
    elif not ok_n:
        governante = "20.3.1 número mínimo de barras contínuas não atendido"
    else:
        governante = "19.5.4 armadura contra colapso progressivo insuficiente"

    return ResultadoBarrasContinuasApoio(
        n, N_MIN_BARRAS_CONTINUAS_APOIO, FSd, fyd, As_ccp,
        capacidade, capacidade_min, ok, governante, memoria,
    )


def penetracao_capitel_cm(phi_mm: float) -> float:
    """Penetração mínima no capitel das barras inferiores interrompidas, em lajes com capitéis (20.3.1, PDF p. 194).

    L,penetração >= máx(30 cm, 24φ), com φ em mm (24φ convertido para cm).
    """
    phi = _positivo(phi_mm, "phi_mm")
    return max(30.0, 24.0 * (phi / 10.0))


# ---------------------------------------------------------------------------
# 20.5 — Lajes armadas com telas soldadas nervuradas (PDF p. 196)
# ---------------------------------------------------------------------------
def ancoragem_tela_apoio_cm(phi_mm: float) -> float:
    """Comprimento de ancoragem da tela soldada nervurada (NBR 7481) estendida integralmente até o apoio sobre viga (20.5.1, PDF p. 196).

    l,anc = máx(10φ, 10 cm), com φ em mm (10φ convertido para cm).
    """
    phi = _positivo(phi_mm, "phi_mm")
    return max(10.0 * (phi / 10.0), 10.0)


TABELA_20_5_2_EMENDA_TELA: dict[str, dict[str, int]] = {
    "principal": {"malhas": 2, "fios": 3},
    "secundaria": {"malhas": 1, "fios": 2},
}


def emenda_tela_malhas(tipo_armadura: str) -> dict[str, int]:
    """Número mínimo de malhas ou de fios sobrepostos na emenda de armaduras em tela soldada nervurada (20.5.2, PDF p. 196).

    ``tipo_armadura``: "principal" (2 malhas ou 3 fios) ou "secundaria"
    (1 malha ou 2 fios). Devolve ``{"malhas": n, "fios": n}``: a emenda pode
    ser feita com qualquer um dos dois critérios (não é preciso somar).

    Vale para tela retangular. Em telas em L ou T, a emenda na direção da
    maior dimensão da malha pode ser reduzida em relação a estes valores, se
    respeitados ao menos os critérios de emenda de barras isoladas (não
    coberto por esta função).
    """
    chave = tipo_armadura.strip().lower()
    if chave == "secundária":
        chave = "secundaria"
    if chave not in TABELA_20_5_2_EMENDA_TELA:
        raise FaixaNormativaError(
            f"tipo_armadura = '{tipo_armadura}' inválido; use 'principal' ou 'secundaria'."
        )
    return dict(TABELA_20_5_2_EMENDA_TELA[chave])


# ---------------------------------------------------------------------------
# 20.6 — Armadura em lajes em balanço (PDF p. 197)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoArmaduraBalancoInferior:
    g_kn_m2: float
    vao_balanco_cm: float
    Mg_kncm: float
    d_cm: float
    h_cm: float
    fck_mpa: float
    fyk_mpa: float
    bw_cm: float
    As_cm2: float
    As_min_cm2: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def As_inferior_balanco(
    g_kn_m2: float, vao_balanco_cm: float, d_cm: float, h_cm: float,
    fck_mpa: float, fyk_mpa: float = 500.0, bw_cm: float = 100.0,
    gama_c: float = nbr.GAMA_C, gama_s: float = nbr.GAMA_S,
) -> ResultadoArmaduraBalancoInferior:
    """Armadura de segurança na face inferior de laje em balanço (caso típico de marquise), dimensionada para suportar isoladamente as ações permanentes, evitando o colapso total em caso de ruptura na seção de apoio (20.6, PDF p. 197).

    Mg = g * vão² / 2 (momento de uma faixa de 1 m de largura, em balanço,
    sob a carga permanente distribuída g, em kN/m², atuando isoladamente e
    sem majoração por coeficiente de ponderação: é uma verificação de
    robustez contra o colapso, não uma combinação de ações do ELU normal).

    A armadura é dimensionada para Mg com o bloco retangular simplificado do
    ELU (``nucleo_nbr6118.tensao_retangulo``/``lambda_retangulo``/``fyd``),
    sujeita ao mínimo absoluto de 17.3.5.2.1
    (``nucleo_nbr6118.As_min_flexao_retangular``).

    Não confundir com γn de 13.2.4.1 (``lajes_nbr6118.gama_n_laje_balanco``),
    que majora o momento de cálculo da própria laje em balanço no ELU normal:
    são exigências distintas com o mesmo nome "balanço".
    """
    g = _nao_negativo(g_kn_m2, "g_kn_m2")
    vao_cm = _positivo(vao_balanco_cm, "vao_balanco_cm")
    d = _positivo(d_cm, "d_cm")
    h = _positivo(h_cm, "h_cm")

    vao_m = vao_cm / 100.0
    Mg_knm_por_m = g * vao_m ** 2 / 2.0
    Mg_kncm = Mg_knm_por_m * 100.0

    fyd_val = nbr.mpa_para_kncm2(nbr.fyd(fyk_mpa, gama_s))
    tensao = nbr.mpa_para_kncm2(nbr.tensao_retangulo(fck_mpa, gama_c))
    lam = nbr.lambda_retangulo(fck_mpa)

    a = tensao * bw_cm * lam * lam / 2.0
    b = -tensao * bw_cm * lam * d
    c = Mg_kncm
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        raise FaixaNormativaError(
            "Seção insuficiente para Mg isolado (discriminante negativo); aumentar h."
        )
    x = (-b - math.sqrt(disc)) / (2.0 * a)
    As = Mg_kncm / (fyd_val * (d - 0.5 * lam * x))

    As_min = nbr.As_min_flexao_retangular(bw_cm, h, d, fck_mpa, fyk_mpa, gama_c, gama_s)
    As_final = max(As, As_min)
    governante = ("20.6 momento das ações permanentes isoladas" if As >= As_min
                  else "17.3.5.2.1 armadura mínima absoluta")

    memoria = (
        f"20.6: Mg = {_fmt(g)} kN/m2 * ({_fmt(vao_m)} m)^2 / 2 = "
        f"{_fmt(Mg_knm_por_m)} kN.m/m = {_fmt(Mg_kncm)} kN.cm/m "
        f"(ações permanentes isoladas, sem majoração).",
        f"20.6: As dimensionada para Mg = {_fmt(As)} cm2/m; As,min "
        f"(17.3.5.2.1) = {_fmt(As_min)} cm2/m -> As,inf = {_fmt(As_final)} cm2/m.",
    )

    return ResultadoArmaduraBalancoInferior(
        g, vao_cm, Mg_kncm, d, h, fck_mpa, fyk_mpa, bw_cm,
        As_final, As_min, True, governante, memoria,
    )
