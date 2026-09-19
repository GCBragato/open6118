"""Bielas e tirantes — ABNT NBR 6118:2026, 22.3.

Núcleo genérico do método de bielas e tirantes (Strut-and-Tie), usado pelas
regiões especiais (blocos sobre estacas, sapatas, consolos, vigas-parede,
zonas de ancoragem etc.): a faixa admissível de inclinação das bielas
inclinadas (22.3.1), as tensões de cálculo máximas de bielas e nós (22.3.2)
e a área de aço de um tirante genérico (22.3.3).

Norma: ABNT NBR 6118:2026, 5a edição (11/03/2026). As páginas citadas são as
do PDF (a página impressa é 18 a menos).

Unidades: fck e tensões em MPa; funções com sufixo ``_kncm2`` devolvem
kN/cm2 (1 kN/cm2 = 10 MPa); forças em kN; áreas de aço em cm2.

Este módulo não reimplementa fórmula de material: fcd e alpha_v2 vêm do
núcleo normativo (``nucleo_nbr6118.py``).

``fcd1_kncm2`` e ``fcd3_kncm2`` existiam, com outros nomes, em
``blocos_nbr6118.py`` (``fcd1_no_pilar_kncm2`` / ``fcd3_na_estaca_kncm2``);
foram promovidas para cá (fonte única do método de bielas e tirantes, não só
de blocos), e ``blocos_nbr6118.py`` mantém os nomes antigos como
reexportação fina, para não quebrar quem já os chama.
"""

from __future__ import annotations

from dataclasses import dataclass

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError

GAMA_C = nbr.GAMA_C

# 22.3.1, PDF p. 204 — faixa admissível de inclinação das bielas inclinadas
TAN_THETA_MIN = 0.57
TAN_THETA_MAX = 2.0

_TIPOS_NO = {
    "ccc": "fcd1",
    "cct": "fcd3",
    "ctt": "fcd2",
    "ttt": "fcd2",
}


def _fcd_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fcd em kN/cm2 (delegado ao núcleo normativo: nbr.fcd, 12.3.3)."""
    return nbr.mpa_para_kncm2(nbr.fcd(fck_mpa, gama_c))


# ---------------------------------------------------------------------------
# 22.3.2 — Parâmetros de resistência de cálculo das bielas e regiões nodais
# (PDF p. 204)
# ---------------------------------------------------------------------------
def fcd1_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fcd1 = 0,85 * alpha_v2 * fcd, kN/cm2 (22.3.2, PDF p. 204).

    Tensão de compressão de cálculo máxima em bielas prismáticas (sem
    tirantes atravessando) ou em nós onde só confluem bielas comprimidas
    (nós CCC).
    """
    return 0.85 * nbr.alpha_v2(fck_mpa) * _fcd_kncm2(fck_mpa, gama_c)


def fcd2_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fcd2 = 0,60 * alpha_v2 * fcd, kN/cm2 (22.3.2, PDF p. 204).

    Tensão de compressão de cálculo máxima em bielas atravessadas por mais
    de um tirante, ou em nós onde confluem dois ou mais tirantes tracionados
    (nós CTT ou TTT).
    """
    return 0.60 * nbr.alpha_v2(fck_mpa) * _fcd_kncm2(fck_mpa, gama_c)


def fcd3_kncm2(fck_mpa: float, gama_c: float = GAMA_C) -> float:
    """fcd3 = 0,72 * alpha_v2 * fcd, kN/cm2 (22.3.2, PDF p. 204).

    Tensão de compressão de cálculo máxima em bielas atravessadas por
    tirante único, ou em nós onde confluem bielas e um único tirante
    tracionado (nós CCT).
    """
    return 0.72 * nbr.alpha_v2(fck_mpa) * _fcd_kncm2(fck_mpa, gama_c)


# ---------------------------------------------------------------------------
# 22.3.1 — Faixa de inclinação admissível das bielas inclinadas (PDF p. 204)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoInclinacaoBiela:
    """Resultado de 22.3.1: faixa admissível de inclinação da biela."""

    tan_theta: float
    tan_theta_min: float
    tan_theta_max: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_inclinacao_biela(tan_theta: float) -> ResultadoInclinacaoBiela:
    """Verifica se a inclinação de uma biela inclinada está na faixa
    admissível (22.3.1, PDF p. 204): 0,57 <= tan(theta) <= 2, sendo theta o
    ângulo da biela em relação ao eixo da armadura longitudinal do elemento
    estrutural.

    ``tan_theta`` é a tangente do ângulo, adimensional. Não levanta
    ``FaixaNormativaError``: uma biela fora da faixa é um problema de
    modelo (o projetista ajusta a geometria da treliça), não um domínio de
    validade de fórmula — por isso o resultado tem ``ok`` em vez de erro.
    """
    tan = float(tan_theta)
    ok = TAN_THETA_MIN - 1e-9 <= tan <= TAN_THETA_MAX + 1e-9
    memoria = (
        f"22.3.1: tan(theta) = {tan:.4f}; faixa admissível "
        f"{TAN_THETA_MIN:g} <= tan(theta) <= {TAN_THETA_MAX:g}.",
        (
            "Dentro da faixa -> inclinação admissível."
            if ok
            else "Fora da faixa -> inclinação da biela não admissível; "
            "ajustar a geometria do modelo de biela-tirante."
        ),
    )
    return ResultadoInclinacaoBiela(
        tan_theta=tan, tan_theta_min=TAN_THETA_MIN, tan_theta_max=TAN_THETA_MAX,
        ok=ok, governante="22.3.1", memoria=memoria,
    )


# ---------------------------------------------------------------------------
# 22.3.3 — Parâmetros de resistência de cálculo dos tirantes (PDF p. 204)
# ---------------------------------------------------------------------------
def As_tirante_cm2(FSd_kn: float, fyd_kncm2: float) -> float:
    """As = FSd / fyd, cm2 (22.3.3, PDF p. 204).

    Área de aço necessária em qualquer tirante genérico do modelo de
    biela-tirante. ``FSd_kn`` é o valor de cálculo da força de tração
    determinada no tirante, kN; ``fyd_kncm2`` é a resistência de cálculo do
    aço, kN/cm2 (delegue a ``nucleo_nbr6118.fyd`` para obtê-la; este módulo
    não reimplementa fórmula de material).
    """
    fyd = float(fyd_kncm2)
    if fyd <= 0.0:
        raise FaixaNormativaError(f"fyd = {fyd:g} kN/cm2 deve ser positivo.")
    return float(FSd_kn) / fyd


# ---------------------------------------------------------------------------
# 22.3.2 — Verificação de um nó do modelo (fachada sobre fcd1/fcd2/fcd3)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoNoBielaTirante:
    """Resultado da verificação de tensão em um nó ou biela (22.3.2)."""

    tipo: str
    sigma_kncm2: float
    fcd_no_kncm2: float
    razao: float
    ok: bool
    governante: str
    memoria: tuple[str, ...]


def verificar_no(tipo: str, sigma_kncm2: float, fck_mpa: float,
                  gama_c: float = GAMA_C) -> ResultadoNoBielaTirante:
    """Verifica a tensão de compressão de cálculo em uma biela ou região
    nodal contra o parâmetro correspondente de 22.3.2 (PDF p. 204).

    ``tipo`` identifica o nó ou a biela:
        - 'CCC': biela prismática ou nó onde só confluem bielas -> fcd1;
        - 'CCT': biela atravessada por tirante único, nó onde confluem
          bielas e um único tirante -> fcd3;
        - 'CTT' ou 'TTT': biela atravessada por mais de um tirante, nó onde
          confluem dois ou mais tirantes -> fcd2.

    ``sigma_kncm2`` é a tensão de compressão de cálculo atuante, kN/cm2.
    Tipo desconhecido levanta ``ValueError`` (não é uma faixa numérica; é
    uma categoria inválida, como em ``nucleo_nbr6118.fyk_categoria``).
    """
    chave = str(tipo).strip().lower()
    if chave not in _TIPOS_NO:
        raise ValueError(
            f"Tipo de nó/biela desconhecido: {tipo!r}. Use 'CCC', 'CCT', "
            "'CTT' ou 'TTT'."
        )
    sigma = float(sigma_kncm2)
    nome_fcd = _TIPOS_NO[chave]
    fcd_no = {
        "fcd1": fcd1_kncm2,
        "fcd2": fcd2_kncm2,
        "fcd3": fcd3_kncm2,
    }[nome_fcd](fck_mpa, gama_c)
    razao = sigma / fcd_no
    ok = razao <= 1.0 + 1e-9
    memoria = (
        f"22.3.2: nó/biela tipo {chave.upper()} -> {nome_fcd} = {fcd_no:.4f} "
        f"kN/cm2 ({fcd_no * 10.0:.3f} MPa).",
        f"sigma = {sigma:.4f} kN/cm2; sigma/{nome_fcd} = {razao:.4f} "
        f"{'<= 1 -> ok.' if ok else '> 1 -> reprovado.'}",
    )
    return ResultadoNoBielaTirante(
        tipo=chave.upper(), sigma_kncm2=sigma, fcd_no_kncm2=fcd_no,
        razao=razao, ok=ok, governante="22.3.2", memoria=memoria,
    )
