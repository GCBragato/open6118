"""Pilar-parede — ABNT NBR 6118:2026, 15.9 (efeito localizado de 2a ordem) e
18.5 (armadura transversal minima).

Cobre:
    - le_lamina_cm: comprimento equivalente ℓe de cada lamina do pilar-parede,
      pelos 4 casos de vinculacao (A, B, C, D) da Figura 15.4 (15.9.2, PDF
      p. 132);
    - esbeltez_lamina: esbeltez λi = 3,46·ℓei/hi de cada lamina, com a
      reducao de 0,85 quando topo e base sao engastados e β <= 1 (15.9.2);
    - dispensa_efeito_localizado: dispensa da analise dos efeitos
      localizados de 2a ordem quando todas as laminas tem λi < 35 e estao
      convenientemente fixadas as lajes (15.9.2);
    - largura_faixa_cm e decompor_em_faixas: decomposicao do pilar-parede em
      faixas verticais de largura ai = 3h <= 100 cm, com a forca normal Ni e
      o momento Myid de cada faixa, a partir da distribuicao aproximada
      nd(x) devida a Nd e M1xd (Figura 15.5, 15.9.3, PDF p. 133);
    - As_transversal_pilar_parede_cm2_por_m: armadura transversal minima por
      metro de face, 25 % da armadura longitudinal da maior face, quando a
      flexao de placa transversal nao e calculada (18.5, PDF p. 174).

Norma: ABNT NBR 6118:2026, 5a edicao (11/03/2026). As paginas citadas sao as
do PDF (a pagina impressa e 18 a menos).

Unidades: comprimentos e dimensoes em cm; forcas em kN; momentos em kN.cm;
armaduras em cm2/m. Nao ha grandeza de material neste pacote (nenhuma
fcd/fyd/Ecs e reimplementada aqui).

O que este modulo NAO faz: a analise completa de cada faixa como pilar
isolado equivalente (15.9.3, ultimo paragrafo) fica a cargo de quem chama
``decompor_em_faixas`` — cada ``Faixa`` devolvida (Ni, Myid) alimenta
``pilares_nbr6118.Mdtot_curvatura_aprox`` ou ``Mdtot_rigidez_aprox`` (P25)
com a geometria fora do plano da faixa (ℓe, h, fck, Ac), que nao faz parte
da decomposicao geometrica em si. A norma permite, nessa analise, nao
adotar αb > 0,6 quando Myid < M1d,min (ver docstring de
``decompor_em_faixas``); isso e responsabilidade de quem faz a chamada a
``pilares_nbr6118.alpha_b``/``Mdtot_*``, informando o teto de 0,6.

A classificacao pilar comum x pilar-parede (18.4.1/14.4.2.4) esta em
``classificacao_elementos_nbr6118.eh_pilar_parede`` (P11) e nao e
reimplementada aqui.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr


# ---------------------------------------------------------------------------
# 15.9.2 — Comprimento equivalente ℓe de lamina (Figura 15.4, PDF p. 132)
# ---------------------------------------------------------------------------
def le_lamina_cm(l_cm: float, b_cm: float, vinculacao: str) -> float:
    """Comprimento equivalente ℓe de uma lamina do pilar-parede (Figura 15.4, 15.9.2, PDF p. 132).

    β = ℓ/b, com ℓ a altura da lamina entre apoios e b a largura em planta.
    ``vinculacao`` (as letras da Figura 15.4):

        A — topo livre, base engastada:            ℓe = ℓ.
        B — topo e base livres (nao fixados
            horizontalmente):                       ℓe = ℓ/(1+(β/3)²), ℓe >= 0,3·ℓ.
        C — topo e base fixados horizontalmente
            (biapoiado):                             ℓe = ℓ/(1+β²)  se β <= 1;
                                                       ℓe = ℓ/(2β)    se β > 1.
        D — base engastada, topo livre
            horizontalmente:                         ℓe = 2·b <= ℓ  se β >= 7,0;
                                                       adota-se o caso B se β < 7,0.

    Continuidade conferida na imagem: o caso C e continuo em β = 1 (os dois
    ramos dao ℓe = ℓ/2). Os casos B e D **nao** coincidem em β = 7,0 — em
    β = 7,0, o caso D da ℓe = 2b, e o caso B (mesma β) da um valor menor;
    essa descontinuidade e da propria norma (texto e figura conferidos na
    imagem, PDF p. 132), nao um erro de transcricao — documentada aqui como
    a secao 8, item 5 do plano de implementacao pede para descontinuidades
    propositais da norma.

    Fonte: NBR 6118:2026, 15.9.2, Figura 15.4 (PDF p. 132).
    """
    l = float(l_cm)
    b = float(b_cm)
    if l <= 0.0 or b <= 0.0:
        raise nbr.FaixaNormativaError(
            f"15.9.2: ℓ = {l:g} cm e b = {b:g} cm devem ser positivos."
        )
    beta = l / b
    v = vinculacao.strip().upper()
    if v == "A":
        return l
    if v == "B":
        return max(l / (1.0 + (beta / 3.0) ** 2), 0.3 * l)
    if v == "C":
        if beta <= 1.0:
            return l / (1.0 + beta ** 2)
        return l / (2.0 * beta)
    if v == "D":
        if beta >= 7.0:
            return min(2.0 * b, l)
        return le_lamina_cm(l_cm, b_cm, "B")
    raise ValueError(
        f"15.9.2: vinculação {vinculacao!r} desconhecida. Use 'A', 'B', 'C' ou "
        "'D', conforme a Figura 15.4."
    )


# ---------------------------------------------------------------------------
# 15.9.2 — Esbeltez λi de lamina e dispensa dos efeitos localizados
# ---------------------------------------------------------------------------
LAMBDA_LIMITE_LAMINA = 35.0  # 15.9.2, PDF p. 132


def esbeltez_lamina(le_cm: float, h_cm: float, *,
                    engastado_topo_e_base: bool = False,
                    beta: float | None = None) -> float:
    """Esbeltez λi de uma lamina do pilar-parede (15.9.2, PDF p. 132).

    λi = 3,46 · ℓei / hi (mesma formula de ``pilares_nbr6118.esbeltez_lambda``,
    aqui com nome dedicado a lamina de pilar-parede, como o item da norma
    pede). Se o topo e a base da lamina forem engastados e β = ℓ/b <= 1, os
    valores de λi podem ser multiplicados por 0,85 (redução dada no texto
    logo apos a Figura 15.4, PDF p. 132); informe ``engastado_topo_e_base``
    e ``beta`` para aplicar essa redução.

    Fonte: NBR 6118:2026, 15.9.2 (PDF p. 132).
    """
    if h_cm <= 0.0:
        raise nbr.FaixaNormativaError(f"15.9.2: hi = {h_cm:g} cm deve ser positivo.")
    lam = 3.46 * float(le_cm) / float(h_cm)
    if engastado_topo_e_base and beta is not None and beta <= 1.0:
        lam *= 0.85
    return lam


@dataclass(frozen=True)
class DispensaLocalizadoPilarParede:
    """Resultado de ``dispensa_efeito_localizado`` (15.9.2)."""

    lambda_i: tuple[float, ...]
    limite: float
    fixado_as_lajes: tuple[bool, ...]
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def dispensa_efeito_localizado(
    lambda_i: Sequence[float],
    fixado_as_lajes: bool | Sequence[bool] = True,
) -> DispensaLocalizadoPilarParede:
    """Dispensa da analise dos efeitos localizados de 2a ordem do pilar-parede (15.9.2, PDF p. 132).

    Os efeitos localizados podem ser desprezados se, para CADA lamina do
    pilar-parede:

        a) a base e o topo da lamina estiverem convenientemente fixados as
           lajes do edificio (que conferem o efeito de diafragma
           horizontal);
        b) a esbeltez λi da lamina for menor que 35.

    A condição a) é por lâmina, não do pilar-parede como um todo (texto:
    "a base e o topo de CADA lâmina devem ser convenientemente fixados às
    lajes"). ``fixado_as_lajes`` aceita por isso tanto um único ``bool``
    (aplicado a todas as lâminas — reproduz o comportamento anterior, para
    quando a fixação é de fato decidida no nível do pavimento e vale para
    todas) quanto uma sequência de ``bool`` com um valor por lâmina, na
    mesma ordem e do mesmo tamanho de ``lambda_i``, para o caso em que
    lâminas diferentes têm fixação diferente.

    ``lambda_i`` traz o λi (ja com a reducao de 0,85 quando aplicavel, ver
    ``esbeltez_lamina``) de cada lamina do pilar-parede. O limite de 35 e
    comparado com tolerancia relativa de 1e-9 (mesma tolerancia do nucleo,
    3.3.6), de modo que λi = 35,00 e aceito e λi = 35,01 e recusado.

    Fonte: NBR 6118:2026, 15.9.2 (PDF p. 132).
    """
    lambdas = tuple(float(x) for x in lambda_i)
    if not lambdas:
        raise ValueError("15.9.2: informe ao menos uma lâmina em lambda_i.")
    if isinstance(fixado_as_lajes, bool):
        fixados = tuple(fixado_as_lajes for _ in lambdas)
    else:
        fixados = tuple(bool(x) for x in fixado_as_lajes)
        if len(fixados) != len(lambdas):
            raise ValueError(
                "15.9.2: fixado_as_lajes deve ser um único bool ou ter um valor "
                f"por lâmina ({len(lambdas)} lâminas, {len(fixados)} valores recebidos)."
            )
    tol = 1e-9
    piores = [lam for lam in lambdas if lam > LAMBDA_LIMITE_LAMINA + tol]
    nao_fixadas = [i for i, fix in enumerate(fixados) if not fix]
    ok = not nao_fixadas and not piores
    memoria = [
        "15.9.2: base e topo fixados às lajes, por lâmina = "
        + ", ".join(str(x) for x in fixados) + ".",
        "15.9.2: λi por lâmina = "
        + ", ".join(f"{x:.2f}" for x in lambdas)
        + f" (limite λi < {LAMBDA_LIMITE_LAMINA:g}).",
    ]
    if nao_fixadas:
        governante = (
            "15.9.2 a): base/topo não convenientemente fixados às lajes na(s) "
            "lâmina(s) de índice " + ", ".join(str(i) for i in nao_fixadas)
        )
    elif piores:
        governante = f"15.9.2 b): λi = {max(piores):.2f} não atende λi < 35 em ao menos uma lâmina"
    else:
        governante = "15.9.2: dispensados — todas as lâminas com λi < 35 e fixadas às lajes"
    memoria.append(
        "15.9.2: "
        + ("dispensada" if ok else "não dispensada")
        + " a análise dos efeitos localizados de 2ª ordem."
    )
    return DispensaLocalizadoPilarParede(
        lambda_i=lambdas,
        limite=LAMBDA_LIMITE_LAMINA,
        fixado_as_lajes=fixados,
        ok=ok,
        governante=governante,
        memoria=tuple(memoria),
    )


# ---------------------------------------------------------------------------
# 15.9.3 — Decomposicao em faixas verticais (Figura 15.5, PDF p. 133)
# ---------------------------------------------------------------------------
LARGURA_FAIXA_MAX_CM = 100.0  # 15.9.3, PDF p. 133
LAMBDA_LIMITE_FAIXAS = 90.0  # 15.9.3, ultimo paragrafo antes da Figura 15.5, PDF p. 133


@dataclass(frozen=True)
class Faixa:
    """Uma faixa vertical da decomposicao do pilar-parede (15.9.3)."""

    x_cm: float
    ai_cm: float
    Ni_kn: float
    Myid_kncm: float


def largura_faixa_cm(h_cm: float) -> float:
    """Largura ai de cada faixa vertical do pilar-parede: ai = 3h <= 100 cm (15.9.3, PDF p. 133)."""
    if h_cm <= 0.0:
        raise nbr.FaixaNormativaError(f"15.9.3: h = {h_cm:g} cm deve ser positivo.")
    return min(3.0 * float(h_cm), LARGURA_FAIXA_MAX_CM)


def nd_x_kn_por_cm(x_cm: float, Nd_kn: float, M1xd_kncm: float, b_cm: float) -> float:
    """Distribuição aproximada nd(x) dos esforços normais ao longo da largura b da lamina (Figura 15.5, 15.9.3, PDF p. 133).

    Distribuição linear (trapezoidal/triangular na Figura 15.5), analoga a
    N/A ± M·y/I de uma seção retangular de largura b e altura unitaria (a
    espessura h da lamina nao entra: nd(x) e forca por unidade de largura):

        nd(x) = Nd/b + 12 · M1xd · x / b³

    com x medido a partir do centro da largura b (positivo no sentido em
    que M1xd traciona), Nd em kN, M1xd em kN·cm, x e b em cm; nd(x) sai em
    kN/cm de largura. Integrando nd(x) em b recupera-se Nd; integrando
    x·nd(x) em b recupera-se M1xd — e assim que ``decompor_em_faixas``
    obtem Ni por faixa.

    Fonte: NBR 6118:2026, 15.9.3, Figura 15.5 (PDF p. 133).
    """
    b = float(b_cm)
    if b <= 0.0:
        raise nbr.FaixaNormativaError(f"15.9.3: b = {b:g} cm deve ser positivo.")
    return Nd_kn / b + 12.0 * float(M1xd_kncm) * float(x_cm) / (b ** 3)


def decompor_em_faixas(b_cm: float, h_cm: float, Nd_kn: float, M1xd_kncm: float,
                        m1yd_kncm_por_cm: float = 0.0,
                        M1d_min_kncm: float | None = None,
                        lambda_i_laminas: Sequence[float] | None = None) -> tuple[Faixa, ...]:
    """Decompõe o pilar-parede em faixas verticais, com Ni e Myid de cada uma (15.9.3, PDF p. 133).

    O efeito localizado de 2ª ordem e considerado decompondo o pilar-parede
    (largura total b, espessura h) em faixas verticais de largura
    ``ai = largura_faixa_cm(h) = 3h <= 100 cm``; a ultima faixa fica mais
    estreita quando b nao e multiplo exato de ai. Cada faixa e depois
    analisada como um pilar isolado equivalente (fora deste modulo — ver a
    docstring do modulo), submetido a:

        Ni    = força normal na faixa i, obtida integrando nd(x)
                (``nd_x_kn_por_cm``) na largura da faixa — com M1xd = 0,
                Ni = Nd·ai/b (igual em todas as faixas de largura ai);
        Myid  = m1yd · ai, elevado a M1d,mín quando este for informado (o
                momento minimo de 1ª ordem de 11.3.3.4.3,
                ``nucleo_nbr6118.M1d_min_kncm``, quando adotado para as
                imperfeições geométricas).

    A soma de Ni de todas as faixas e sempre igual a Nd (a parcela de
    M1xd tem soma nula, por construcao da distribuicao linear).

    Na analise de cada faixa como pilar isolado (fora deste modulo, com
    ``pilares_nbr6118.Mdtot_curvatura_aprox``/``Mdtot_rigidez_aprox``), a
    norma dispensa valores de αb > 0,6 quando Myid < M1d,mín (ultimo
    parágrafo de 15.9.3) — quem fizer essa chamada deve limitar o αb usado
    a 0,6 nesse caso.

    m1yd_kncm_por_cm: momento transversal m1yd por unidade de largura da
    lamina (definido na Figura 15.5, como esforço externo — nao calculado
    por este modulo); padrão 0,0 (carga so axial/no plano, M1xd apenas).

    lambda_i_laminas: esbeltez λi (``esbeltez_lamina``) de cada lâmina que
    compõe o pilar-parede, quando disponível. O processo aproximado deste
    item só vale "onde a esbeltez de cada lâmina que os constitui for menor
    que 90" (parágrafo imediatamente antes desta fórmula, PDF p. 133); se
    informado e alguma lâmina tiver λi >= 90, uma ``FaixaNormativaError`` é
    levantada em vez de decompor. Parâmetro opcional (padrão ``None``, sem
    verificação) para não quebrar chamadas existentes — quem chama deve
    informar ``lambda_i_laminas`` para obter a checagem automática do limite.

    Fonte: NBR 6118:2026, 15.9.3, Figura 15.5 (PDF p. 133).
    """
    b = float(b_cm)
    if b <= 0.0:
        raise nbr.FaixaNormativaError(f"15.9.3: b = {b:g} cm deve ser positivo.")
    if lambda_i_laminas is not None:
        tol = 1e-9
        # C1: a norma exige "menor que 90" (desigualdade estrita, 15.9.3, PDF
        # p. 132) -- λi = 90 exatamente também levanta, não só λi > 90.
        piores_lambda = [float(x) for x in lambda_i_laminas if float(x) >= LAMBDA_LIMITE_FAIXAS - tol]
        if piores_lambda:
            raise nbr.FaixaNormativaError(
                "15.9.3: o processo aproximado de decomposição em faixas só vale "
                "para lâminas com esbeltez menor que 90; recebido λi = "
                f"{max(piores_lambda):.2f}."
            )
    ai_nominal = largura_faixa_cm(h_cm)
    n_faixas = max(1, math.ceil(b / ai_nominal - 1e-9))
    faixas: list[Faixa] = []
    x0 = -b / 2.0
    for i in range(n_faixas):
        restante = b - i * ai_nominal
        largura = min(ai_nominal, restante)
        x_ini = x0 + i * ai_nominal
        x_fim = x_ini + largura
        xi = (x_ini + x_fim) / 2.0
        # Ni = integral de nd(x) na faixa = Nd*largura/b + 12*M1xd*largura*xi/b^3
        Ni = Nd_kn * largura / b + 12.0 * float(M1xd_kncm) * largura * xi / (b ** 3)
        Myid = float(m1yd_kncm_por_cm) * largura
        if M1d_min_kncm is not None:
            Myid = max(Myid, float(M1d_min_kncm))
        faixas.append(Faixa(x_cm=xi, ai_cm=largura, Ni_kn=Ni, Myid_kncm=Myid))
    return tuple(faixas)


# ---------------------------------------------------------------------------
# 18.5 — Armadura transversal minima de pilar-parede (PDF p. 174)
# ---------------------------------------------------------------------------
def As_transversal_pilar_parede_cm2_por_m(As_longitudinal_cm2_por_m: float) -> float:
    """Armadura transversal minima do pilar-parede, cm²/m de face (18.5, PDF p. 174).

    Quando a flexao de placa transversal do pilar-parede NAO for calculada,
    a armadura transversal por metro de face deve respeitar o minimo de
    25 % da armadura longitudinal por metro da MAIOR face da lamina
    considerada:

        As,transversal,mín = 0,25 · As,longitudinal

    Quando essa flexao de placa for calculada, prevalece a armadura minima
    de flexao de placas (remissao a lajes — fora deste modulo; ver
    ``lajes_nbr6118``).

    Fonte: NBR 6118:2026, 18.5 (PDF p. 174).
    """
    As_l = float(As_longitudinal_cm2_por_m)
    if As_l < 0.0:
        raise nbr.FaixaNormativaError(
            f"18.5: As,longitudinal = {As_l:g} cm²/m não pode ser negativa."
        )
    return 0.25 * As_l
