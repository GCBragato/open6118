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


# === P48: treliças e modelos de cálculo de bielas e tirantes ===
# Itens cobertos (páginas do PDF da ABNT NBR 6118:2026):
#   - 21.2.3 Região de introdução da protensão (p. 199)
#   - 22.2   Limite convencional entre as regiões B e D (p. 202)
#   - 22.3.1 Procedimento para aplicação do método (p. 203-204)
#   - 22.4.3 Modelos de cálculo de viga-parede (p. 205)
#   - 22.6.3 Modelo de cálculo de sapata (p. 212)
#   - 22.7.3 Modelo de cálculo de bloco sobre estacas (p. 213)
# A treliça é resolvida pelo cálculo de barras do P44
# (``analise_barras_nbr6118``), nos tipos 'trelica_plana' e
# 'trelica_espacial'; as verificações de biela, nó e tirante são as de
# 22.3.2 e 22.3.3, já neste módulo (``verificar_no``, ``As_tirante_cm2``).
import math
from dataclasses import dataclass

import numpy as np

try:  # executado como script, ou com dimensionamento/ no sys.path
    import analise_barras_nbr6118 as _ab
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import analise_barras_nbr6118 as _ab


class TrelicaNaoIsostaticaError(ValueError):
    """A treliça de bielas e tirantes não é isostática, como 22.3.1 exige
    (hipostática — mecanismo —, hiperestática ou de forma crítica)."""


class TrelicaNaoAutoequilibradaError(ValueError):
    """As forças ativas e reativas aplicadas aos nós da treliça não formam
    o sistema autoequilibrado que 22.3.1 exige."""


# Seção e material fictícios da treliça: a treliça isostática de 22.3.1 tem
# esforços independentes da rigidez das barras; estes valores só servem para
# condicionar numericamente o sistema do método dos deslocamentos do P44.
_A_BARRA_BT_CM2 = 100.0
_E_BARRA_BT_MPA = 21000.0

# Tolerância relativa para classificar barra de força nula e para conferir o
# autoequilíbrio das forças aplicadas.
_TOL_REL_BT = 1e-8


def _secao_material_bt():
    return (_ab.Secao(A_cm2=_A_BARRA_BT_CM2),
            _ab.Material.elastico(E_mpa=_E_BARRA_BT_MPA))


def _num(x: float) -> str:
    """Número para a memória de cálculo do P48."""
    return f"{float(x):.4g}"


# ---------------------------------------------------------------------------
# 22.2 — Limite convencional entre as regiões B e D (PDF p. 202)
# ---------------------------------------------------------------------------
def extensao_regiao_d_cm(h_cm: float, n_lados: int = 1) -> float:
    """Extensão da região D medida a partir da seção efetiva da
    descontinuidade (22.2, PDF p. 202).

    Fórmula (transcrita da imagem): "o limite entre as regiões B e D pode ser
    considerado localizado a uma distância h (altura da seção transversal do
    elemento estrutural considerado) da seção efetiva da descontinuidade",
    isto é

        ext = n_lados * h

    ``h_cm`` é a altura da seção transversal do elemento, cm. ``n_lados`` é
    1 quando a descontinuidade é de extremidade (a região D avança só para um
    lado, como no apoio de viga ou na introdução de força concentrada na
    extremidade, Figura 22.1 b1 e b3) e 2 quando ela é interna e a região D
    avança para os dois lados (carga concentrada no meio do vão, Figura 22.1
    b2, onde a figura marca 2h). Devolve cm.

    Fora de ``n_lados`` em {1, 2} levanta ``ValueError``; ``h_cm`` não
    positivo levanta ``FaixaNormativaError``.

    Nota de modelagem (22.2 e Figura 22.1, PDF p. 202-203): quando há mudança
    de seção, cada lado usa o seu próprio h (h1 de um lado, h2 do outro);
    chame a função uma vez para cada lado.
    """
    h = float(h_cm)
    if h <= 0.0:
        raise FaixaNormativaError(
            f"h = {_num(h)} cm: a altura da seção tem de ser positiva.")
    if int(n_lados) not in (1, 2):
        raise ValueError(
            f"n_lados = {n_lados!r}: use 1 (descontinuidade de extremidade) "
            "ou 2 (descontinuidade interna, com região D dos dois lados).")
    return int(n_lados) * h


def classificar_regiao_bd(distancia_cm: float, h_cm: float) -> str:
    """Classifica a seção em região 'B' ou 'D' (22.2, PDF p. 202).

    ``distancia_cm`` é a distância da seção à seção efetiva da
    descontinuidade, cm; ``h_cm`` é a altura da seção transversal do
    elemento, cm. Devolve 'D' enquanto a distância não passa de h (hipótese
    da seção plana não aplicável, vale bielas e tirantes da Seção 22) e 'B'
    depois disso (distribuição linear de deformações, valem as Seções 17 a
    20).

    Distância negativa levanta ``FaixaNormativaError``.
    """
    x = float(distancia_cm)
    h = float(h_cm)
    if h <= 0.0:
        raise FaixaNormativaError(
            f"h = {_num(h)} cm: a altura da seção tem de ser positiva.")
    if x < 0.0:
        raise FaixaNormativaError(
            f"distância = {_num(x)} cm: a distância à seção da "
            "descontinuidade não pode ser negativa.")
    return "D" if x <= h + 1e-9 else "B"


# ---------------------------------------------------------------------------
# 22.3.1 — Treliça idealizada de bielas, tirantes e nós (PDF p. 203-204)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BarraTrelicaBT:
    """Barra da treliça idealizada, já classificada (22.3.1, PDF p. 203).

    ``N_kn`` é a força normal, tração positiva. ``tipo`` é 'biela'
    (compressão), 'tirante' (tração) ou 'nula' (força praticamente nula).
    ``tan_theta`` é a tangente do ângulo entre o eixo da barra e o eixo da
    armadura longitudinal do elemento (``math.inf`` quando a barra é
    perpendicular a esse eixo).
    """

    id: object
    no_i: object
    no_j: object
    L_cm: float
    N_kn: float
    tipo: str
    tan_theta: float


@dataclass(frozen=True)
class ResultadoTrelicaBT:
    """Resultado da análise da treliça de bielas e tirantes (22.3.1)."""

    nome: str
    espacial: bool
    barras: dict
    reacoes: dict
    bielas: tuple
    tirantes: tuple
    nulas: tuple
    autoequilibrado: bool
    ok: bool
    governante: str
    memoria: tuple

    def N_kn(self, id_barra) -> float:
        """Força normal na barra (tração positiva), kN."""
        return self.barras[id_barra].N_kn


@dataclass(frozen=True)
class ResultadoInclinacoesBT:
    """Resultado da conferência da inclinação das bielas (22.3.1)."""

    tan_theta: dict
    fora_da_faixa: tuple
    ok: bool
    governante: str
    memoria: tuple


class TrelicaBT:
    """Treliça idealizada de bielas, tirantes e nós (22.3.1, PDF p. 203-204).

    Monta a treliça de uma região D e a resolve com o cálculo de barras do
    P44 (``analise_barras_nbr6118``), devolvendo a força de cada barra já
    classificada em biela (compressão) ou tirante (tração), pronta para
    ``verificar_no`` (22.3.2) e ``As_tirante_cm2`` (22.3.3).

    O que a norma exige e esta classe confere (22.3.1, PDF p. 203-204):

        - a treliça idealizada é **isostática**: com apoios declarados,
          m + r = g*n; sem apoios declarados (todas as forças ativas e
          reativas aplicadas nos nós), m = g*n - g_rb, com g_rb = 3 no plano
          e 6 no espaço;
        - as forças externas e as reações de apoio ficam **concentradas nos
          nós**, formando um **sistema autoequilibrado** (as reações devem
          ter sido obtidas antes, por análise linear ou não linear);
        - as bielas inclinadas devem ter 0,57 <= tan(theta) <= 2 em relação
          ao eixo da armadura longitudinal (conferido à parte, por
          ``verificar_inclinacoes_bielas``, porque é critério de geometria do
          modelo, não domínio de validade de fórmula).

    Unidades: coordenadas em cm, forças em kN.

    Geometria: com ``espacial=False`` a treliça é plana no plano x-y (x
    horizontal, y vertical); com ``espacial=True`` ela é espacial, com x e y
    horizontais e z vertical.

    Modos de apoio:

        - **com apoios** (``apoio``): use quando as reações são incógnitas da
          própria treliça isostática (viga-parede biapoiada, por exemplo);
        - **autoequilibrado** (nenhum apoio declarado): use quando as
          reações vêm de uma análise prévia e entram como força nodal, que é
          a forma literal de 22.3.1. A classe confere que a resultante de
          forças e de momentos é nula, prende automaticamente o número
          mínimo de graus que impede o movimento de corpo rígido (3 no plano,
          6 no espaço) e confere que essas reações fictícias saem nulas.
    """

    def __init__(self, nome: str = "treliça de bielas e tirantes",
                 espacial: bool = False):
        self.nome = str(nome)
        self.espacial = bool(espacial)
        self.nos: dict = {}
        self.barras: dict = {}
        self.apoios: dict = {}
        self.forcas: dict = {}

    @property
    def _graus(self) -> tuple:
        return ("ux", "uy", "uz") if self.espacial else ("ux", "uy")

    def no(self, id, x_cm: float, y_cm: float, z_cm: float = 0.0) -> "TrelicaBT":
        """Cria o nó ``id`` nas coordenadas dadas, cm."""
        if id in self.nos:
            raise ValueError(f"Nó {id!r} já existe na treliça.")
        if not self.espacial and abs(float(z_cm)) > 1e-12:
            raise ValueError(
                f"Nó {id!r}: a treliça plana fica no plano x-y (z = 0); use "
                "espacial=True para o modelo tridimensional.")
        self.nos[id] = (float(x_cm), float(y_cm), float(z_cm))
        return self

    def barra(self, id, no_i, no_j) -> "TrelicaBT":
        """Cria a barra ``id`` entre dois nós (biela ou tirante, conforme o
        sinal da força que sair da análise)."""
        if id in self.barras:
            raise ValueError(f"Barra {id!r} já existe na treliça.")
        for n in (no_i, no_j):
            if n not in self.nos:
                raise ValueError(f"Barra {id!r}: nó {n!r} não existe.")
        if no_i == no_j:
            raise ValueError(f"Barra {id!r}: nós inicial e final iguais.")
        self.barras[id] = (no_i, no_j)
        return self

    def apoio(self, no, *graus) -> "TrelicaBT":
        """Restringe graus de translação do nó ('ux', 'uy', 'uz', ou o
        atalho 'fixo' para todos os graus do modelo)."""
        if no not in self.nos:
            raise ValueError(f"Apoio: nó {no!r} não existe.")
        atual = self.apoios.setdefault(no, set())
        for g in graus:
            chave = nbr._chave(g)
            if chave in ("fixo", "engaste", "rotula", "articulado"):
                atual.update(self._graus)
            elif chave in self._graus:
                atual.add(chave)
            else:
                raise ValueError(
                    f"Grau {g!r} inválido para a treliça "
                    f"{'espacial' if self.espacial else 'plana'}: use "
                    f"{', '.join(self._graus)} ou 'fixo'.")
        return self

    def forca(self, no, Fx_kn: float = 0.0, Fy_kn: float = 0.0,
              Fz_kn: float = 0.0) -> "TrelicaBT":
        """Acrescenta uma força concentrada no nó, kN, nos eixos globais
        (22.3.1: as forças externas e as reações de apoio previamente
        obtidas ficam concentradas nos nós)."""
        if no not in self.nos:
            raise ValueError(f"Força: nó {no!r} não existe.")
        if not self.espacial and abs(float(Fz_kn)) > 1e-12:
            raise ValueError(
                f"Força no nó {no!r}: a treliça plana não tem direção z.")
        v = self.forcas.get(no, np.zeros(3))
        self.forcas[no] = v + np.array([Fx_kn, Fy_kn, Fz_kn], dtype=float)
        return self

    # -- conferências de 22.3.1 -------------------------------------------
    def grau_estatico(self) -> int:
        """Grau de estaticidade da treliça: 0 é isostática, negativo é
        hipostática (mecanismo) e positivo é hiperestática (22.3.1).

        Com apoios declarados: m + r - g*n. Sem apoios (autoequilibrado):
        m + g_rb - g*n, com g_rb = 3 no plano e 6 no espaço.
        """
        g = 3 if self.espacial else 2
        n = len(self.nos)
        m = len(self.barras)
        r = sum(len(s) for s in self.apoios.values())
        if r == 0:
            r = 6 if self.espacial else 3
        return m + r - g * n

    def _restricoes_minimas(self, ids: list) -> dict:
        """Escolhe o número mínimo de graus a prender (3 no plano, 6 no
        espaço) de modo que nenhum movimento de corpo rígido sobre; as
        reações nesses graus saem nulas num sistema autoequilibrado."""
        g = 3 if self.espacial else 2
        n_rb = 6 if self.espacial else 3
        coords = np.array([self.nos[i] for i in ids], dtype=float)
        d = coords - coords.mean(axis=0)
        escala = max(float(np.max(np.abs(d))), 1.0)
        dn = d / escala
        n = len(ids)
        if g == 2:
            R = np.zeros((2 * n, 3))
            R[0::2, 0] = 1.0
            R[1::2, 1] = 1.0
            R[0::2, 2] = -dn[:, 1]
            R[1::2, 2] = dn[:, 0]
        else:
            R = np.zeros((3 * n, 6))
            R[0::3, 0] = 1.0
            R[1::3, 1] = 1.0
            R[2::3, 2] = 1.0
            R[1::3, 3] = -dn[:, 2]
            R[2::3, 3] = dn[:, 1]
            R[0::3, 4] = dn[:, 2]
            R[2::3, 4] = -dn[:, 0]
            R[0::3, 5] = -dn[:, 1]
            R[1::3, 5] = dn[:, 0]
        sel: list = []
        for k in range(R.shape[0]):
            cand = sel + [k]
            if np.linalg.matrix_rank(R[cand], tol=1e-8) == len(cand):
                sel = cand
                if len(sel) == n_rb:
                    break
        if len(sel) < n_rb:
            raise TrelicaNaoIsostaticaError(
                "Não foi possível prender os movimentos de corpo rígido da "
                "treliça autoequilibrada: verifique se os nós não são todos "
                "coincidentes ou colineares.")
        graus = self._graus
        saida: dict = {}
        for k in sel:
            saida.setdefault(ids[k // g], []).append(graus[k % g])
        return {no: tuple(v) for no, v in saida.items()}

    def _conferir_autoequilibrio(self) -> tuple:
        soma_F = np.zeros(3)
        soma_M = np.zeros(3)
        escala_F = 0.0
        for no, F in self.forcas.items():
            p = np.array(self.nos[no], dtype=float)
            soma_F += F
            soma_M += np.cross(p, F)
            escala_F += float(np.linalg.norm(F))
        dim = max((float(np.max(np.abs(np.array(p)))) for p in self.nos.values()),
                  default=1.0)
        dim = max(dim, 1.0)
        if escala_F <= 0.0:
            raise TrelicaNaoAutoequilibradaError(
                "Treliça sem apoios e sem forças: 22.3.1 pede o sistema "
                "autoequilibrado das forças ativas e reativas nos nós.")
        erro_F = float(np.max(np.abs(soma_F))) / escala_F
        erro_M = float(np.max(np.abs(soma_M))) / (escala_F * dim)
        if max(erro_F, erro_M) > 1e-6:
            raise TrelicaNaoAutoequilibradaError(
                "As forças aplicadas aos nós não formam um sistema "
                "autoequilibrado, como 22.3.1 exige: resultante de forças = "
                f"({', '.join(_num(v) for v in soma_F)}) kN e de momentos = "
                f"({', '.join(_num(v) for v in soma_M)}) kN*cm em torno da "
                "origem. Inclua as reações de apoio obtidas na análise "
                "prévia, ou declare os apoios da treliça.")
        return soma_F, soma_M

    def resolver(self, eixo_longitudinal=(1.0, 0.0, 0.0)) -> ResultadoTrelicaBT:
        """Resolve a treliça isostática e autoequilibrada de 22.3.1 (PDF
        p. 203-204) e devolve a força de cada barra, já classificada em
        biela (compressão) ou tirante (tração).

        ``eixo_longitudinal`` é o eixo da armadura longitudinal do elemento
        estrutural, contra o qual 22.3.1 mede a inclinação das bielas
        (padrão: o eixo x global).

        Levanta ``TrelicaNaoIsostaticaError`` quando a treliça não é
        isostática (inclusive a forma crítica, isostática pela contagem mas
        com matriz singular) e ``TrelicaNaoAutoequilibradaError`` quando as
        forças nodais não se equilibram no modo autoequilibrado.
        """
        g = 3 if self.espacial else 2
        n = len(self.nos)
        m = len(self.barras)
        if m == 0 or n < 2:
            raise ValueError(
                "Treliça de bielas e tirantes com menos de 2 nós ou sem barras.")
        r = sum(len(s) for s in self.apoios.values())
        auto = (r == 0)
        n_rb = 6 if self.espacial else 3
        grau = self.grau_estatico()
        if grau != 0:
            estado = "hipostática (mecanismo)" if grau < 0 else "hiperestática"
            r_txt = (f"{n_rb} grau(s) de corpo rígido (modo autoequilibrado)"
                     if auto else f"{r} grau(s) de apoio")
            raise TrelicaNaoIsostaticaError(
                f"22.3.1 exige treliça isostática: a treliça {self.nome!r} é "
                f"{estado}. Contagem: {m} barra(s) + {r_txt} - "
                f"{g} x {n} nó(s) = {grau:+d} "
                f"(0 seria isostática). "
                + ("Acrescente barras ou apoios até fechar a contagem."
                   if grau < 0 else
                   "Retire barras ou apoios até fechar a contagem; a treliça "
                   "de bielas e tirantes não admite redundância."))
        if auto:
            self._conferir_autoequilibrio()

        mod = _ab.Modelo("trelica_espacial" if self.espacial else "trelica_plana")
        ids = list(self.nos)
        for i in ids:
            x, y, z = self.nos[i]
            mod.no(i, x, y, z)
        secao, material = _secao_material_bt()
        for bid, (i, j) in self.barras.items():
            mod.barra(bid, i, j, secao, material)
        restricoes = (self._restricoes_minimas(ids) if auto
                      else {no: tuple(sorted(s)) for no, s in self.apoios.items()})
        for no, graus in restricoes.items():
            mod.apoio(no, *graus)
        caso = _ab.CasoCarga(self.nome)
        for no, F in self.forcas.items():
            caso.nodal(no, Fx=float(F[0]), Fy=float(F[1]), Fz=float(F[2]))
        try:
            res = _ab.resolver(mod, caso, n_estacoes=2)
        except _ab.EstruturaHipostatica as exc:
            raise TrelicaNaoIsostaticaError(
                f"22.3.1 exige treliça isostática: a treliça {self.nome!r} "
                "fecha a contagem de barras e apoios, mas é de forma crítica "
                "(matriz de rigidez singular): há nó com barras colineares, "
                "apoios mal postos ou um subconjunto que forma mecanismo. "
                "Reveja a geometria do modelo.") from exc

        eixo = np.array(eixo_longitudinal, dtype=float)
        norma_eixo = float(np.linalg.norm(eixo))
        if norma_eixo <= 0.0:
            raise ValueError("eixo_longitudinal não pode ser o vetor nulo.")
        eixo = eixo / norma_eixo

        N = {bid: float(res.barras[bid].N[0]) for bid in self.barras}
        Nmax = max((abs(v) for v in N.values()), default=0.0)
        tol = _TOL_REL_BT * max(Nmax, 1.0)
        barras: dict = {}
        bielas, tirantes, nulas = [], [], []
        for bid, (i, j) in self.barras.items():
            pi = np.array(self.nos[i], dtype=float)
            pj = np.array(self.nos[j], dtype=float)
            d = pj - pi
            L = float(np.linalg.norm(d))
            cos = abs(float(np.dot(d, eixo))) / L
            cos = min(cos, 1.0)
            tan = math.inf if cos <= 1e-12 else math.sqrt(max(0.0, 1.0 - cos * cos)) / cos
            if N[bid] < -tol:
                tipo = "biela"
                bielas.append(bid)
            elif N[bid] > tol:
                tipo = "tirante"
                tirantes.append(bid)
            else:
                tipo = "nula"
                nulas.append(bid)
            barras[bid] = BarraTrelicaBT(
                id=bid, no_i=i, no_j=j, L_cm=L,
                N_kn=0.0 if tipo == "nula" else N[bid], tipo=tipo, tan_theta=tan)

        if auto:
            escala = sum(float(np.linalg.norm(F)) for F in self.forcas.values())
            residuo = max((abs(v) for d in res.reacoes.values() for v in d.values()),
                          default=0.0)
            if residuo > 1e-6 * max(escala, 1.0):
                raise TrelicaNaoAutoequilibradaError(
                    "As reações fictícias dos graus presos para impedir o "
                    f"movimento de corpo rígido não saíram nulas ({_num(residuo)} "
                    "kN): as forças nodais não formam sistema autoequilibrado.")
            reacoes = {}
        else:
            reacoes = {no: dict(v) for no, v in res.reacoes.items()}

        memoria = [
            f"22.3.1: treliça idealizada {self.nome!r}, "
            f"{'espacial' if self.espacial else 'plana'}, com {n} nó(s), "
            f"{m} barra(s) e "
            + (f"{n_rb} grau(s) preso(s) só para impedir o movimento de corpo "
               "rígido (forças ativas e reativas aplicadas nos nós)."
               if auto else f"{r} grau(s) de apoio."),
            "22.3.1: treliça isostática (grau de estaticidade 0) e sistema "
            "autoequilibrado; as reações de apoio vêm de análise linear ou "
            "não linear prévia.",
            f"Bielas (compressão): {len(bielas)}; tirantes (tração): "
            f"{len(tirantes)}; barras de força nula: {len(nulas)}.",
        ]
        for bid in self.barras:
            b = barras[bid]
            tan_txt = "perpendicular ao eixo" if b.tan_theta == math.inf else \
                f"tan(theta) = {_num(b.tan_theta)}"
            memoria.append(
                f"Barra {bid!r} ({b.no_i!r}-{b.no_j!r}): L = {_num(b.L_cm)} cm, "
                f"N = {_num(b.N_kn)} kN -> {b.tipo}; {tan_txt}.")
        memoria.append(
            "As forças acima alimentam 22.3.2 (verificar_no, com a área da "
            "biela ou da zona nodal) e 22.3.3 (As_tirante_cm2).")

        return ResultadoTrelicaBT(
            nome=self.nome, espacial=self.espacial, barras=barras,
            reacoes=reacoes, bielas=tuple(bielas), tirantes=tuple(tirantes),
            nulas=tuple(nulas), autoequilibrado=auto, ok=True,
            governante="22.3.1", memoria=tuple(memoria))


def verificar_inclinacoes_bielas(resultado: ResultadoTrelicaBT,
                                 incluir_tirantes: bool = False) -> ResultadoInclinacoesBT:
    """Confere a inclinação das bielas inclinadas da treliça contra a faixa
    de 22.3.1 (PDF p. 204): 0,57 <= tan(theta) <= 2, sendo theta o ângulo em
    relação ao eixo da armadura longitudinal do elemento estrutural.

    Só entram na conferência as barras **inclinadas**: as paralelas ao eixo
    longitudinal (tan(theta) = 0, bielas prismáticas e tirantes do banzo) são
    ignoradas, porque a faixa de 22.3.1 é de biela inclinada. Barras
    perpendiculares ao eixo (tan(theta) infinita) entram e reprovam.
    Com ``incluir_tirantes=True``, as diagonais tracionadas também são
    conferidas (a norma escreve "bielas inclinadas"; o padrão é False).

    Não levanta erro: inclinação fora da faixa é problema de geometria do
    modelo, que o projetista ajusta — o resultado traz ``ok`` e a lista das
    barras fora da faixa.
    """
    tipos = ("biela", "tirante") if incluir_tirantes else ("biela",)
    tans, fora = {}, []
    for bid, b in resultado.barras.items():
        if b.tipo not in tipos:
            continue
        if b.tan_theta <= 1e-9:
            continue
        tans[bid] = b.tan_theta
        if not (TAN_THETA_MIN - 1e-9 <= b.tan_theta <= TAN_THETA_MAX + 1e-9):
            fora.append(bid)
    ok = not fora
    memoria = [
        f"22.3.1: faixa admissível {TAN_THETA_MIN:g} <= tan(theta) <= "
        f"{TAN_THETA_MAX:g} para as bielas inclinadas, medida em relação ao "
        "eixo da armadura longitudinal do elemento estrutural.",
        f"{len(tans)} barra(s) inclinada(s) conferida(s); "
        f"{len(fora)} fora da faixa.",
    ]
    for bid in sorted(fora, key=repr):
        t = tans[bid]
        memoria.append(
            f"Barra {bid!r}: tan(theta) = "
            + ("infinita (perpendicular ao eixo)" if t == math.inf else _num(t))
            + " -> fora da faixa; ajustar a geometria da treliça.")
    if ok:
        memoria.append("Todas as bielas inclinadas estão na faixa -> ok.")
    return ResultadoInclinacoesBT(
        tan_theta=tans, fora_da_faixa=tuple(fora), ok=ok,
        governante="22.3.1", memoria=tuple(memoria))


def dimensionar_tirantes_cm2(resultado: ResultadoTrelicaBT,
                             fyd_kncm2: float) -> dict:
    """Área de aço de cada tirante da treliça, cm2 (22.3.3, PDF p. 204).

    Aplica As = FSd/fyd (``As_tirante_cm2``) a todas as barras classificadas
    como tirante no resultado da treliça. ``fyd_kncm2`` é a resistência de
    cálculo do aço, kN/cm2 (use ``nucleo_nbr6118.fyd`` e converta com
    ``nucleo_nbr6118.mpa_para_kncm2``). Devolve {id da barra: As, cm2}.
    """
    return {bid: As_tirante_cm2(resultado.barras[bid].N_kn, fyd_kncm2)
            for bid in resultado.tirantes}


# ---------------------------------------------------------------------------
# 22.4.3 — Modelos de cálculo de viga-parede (PDF p. 205)
# ---------------------------------------------------------------------------
# Braço de alavanca z do modelo de bielas e tirantes de viga-parede. A norma
# não dá z: 22.4.3 só exige que "a geometria das treliças deve ser tal que os
# valores das forças nos tirantes resultem o mais próximo possível dos
# obtidos em um modelo plano elástico linear". A geometria abaixo é a da
# literatura consagrada (Leonhardt & Mönnig, "Construções de Concreto",
# vol. 2; mesmas expressões no CEB-FIP MC90 e em Araújo, "Curso de Concreto
# Armado", vol. 4), calibrada exatamente contra o modelo elástico linear.
L_H_MAX_BIAPOIADA_LITERATURA = 2.0
L_H_MAX_CONTINUA_LITERATURA = 2.5


def braco_alavanca_viga_parede_cm(l_cm: float, h_cm: float,
                                  continua: bool = False) -> float:
    """Braço de alavanca z da treliça de viga-parede, cm (22.4.3, PDF p. 205).

    A NBR 6118:2026 não dá z; 22.4.3 exige que a geometria da treliça
    reproduza as forças do modelo plano elástico linear. Usa-se a geometria
    da literatura (Leonhardt & Mönnig, "Construções de Concreto", vol. 2;
    CEB-FIP MC90; Araújo, "Curso de Concreto Armado", vol. 4):

        biapoiada: z = 0,60 * l              se l/h < 1
                   z = 0,20 * (l + 2,0 * h)  se 1 <= l/h <= 2
        contínua:  z = 0,50 * l              se l/h < 1
                   z = 0,20 * (l + 1,5 * h)  se 1 <= l/h <= 2,5

    ``l_cm`` é o vão teórico e ``h_cm`` a altura da viga-parede, cm.
    ``continua=True`` usa as expressões de viga-parede contínua.

    Faixa: a classificação de viga-parede de 22.4.1 (PDF p. 204) é l/h < 2
    na biapoiada e l/h < 3 na contínua; as expressões acima só valem até
    l/h = 2 (biapoiada) e l/h = 2,5 (contínua). Fora disso levanta
    ``FaixaNormativaError`` — informe z diretamente ao modelo.
    """
    l = float(l_cm)
    h = float(h_cm)
    if l <= 0.0 or h <= 0.0:
        raise FaixaNormativaError(
            f"l = {_num(l)} cm e h = {_num(h)} cm têm de ser positivos.")
    lh = l / h
    limite = (L_H_MAX_CONTINUA_LITERATURA if continua
              else L_H_MAX_BIAPOIADA_LITERATURA)
    if lh > limite + 1e-9:
        raise FaixaNormativaError(
            f"l/h = {_num(lh)} acima de {limite:g}: a expressão de z da "
            f"literatura para viga-parede "
            f"{'contínua' if continua else 'biapoiada'} não cobre esse caso "
            "(22.4.1 classifica como viga-parede até l/h < "
            f"{'3' if continua else '2'}). Informe z diretamente.")
    if lh < 1.0:
        return (0.50 if continua else 0.60) * l
    return 0.20 * (l + (1.5 if continua else 2.0) * h)


def modelo_viga_parede_biapoiada(l_cm: float, h_cm: float,
                                 P_kn: float | None = None,
                                 q_kn_m: float | None = None,
                                 z_cm: float | None = None) -> TrelicaBT:
    """Treliça de bielas e tirantes de viga-parede biapoiada com carga
    superior (22.4.3, PDF p. 205; 22.3.1, PDF p. 203).

    Geometria da literatura (Leonhardt & Mönnig, vol. 2; Schlaich, Schäfer &
    Jennewein, 1987): banzo tracionado no nível da armadura inferior (y = 0),
    banzo comprimido a z acima dele, com z de
    ``braco_alavanca_viga_parede_cm`` quando ``z_cm`` não é informado.

        - **Carga concentrada no meio do vão** (``P_kn``): treliça de 3
          barras — nós A(0, 0) e B(l, 0) nos apoios, nó C(l/2, z) sob a
          carga; bielas 'A-C' e 'C-B' e tirante 'A-B'. A força no tirante sai
          T = P*l/(4*z).
        - **Carga uniforme superior** (``q_kn_m``, kN/m): a resultante de
          cada metade do vão, Q/2 com Q = q*l, é concentrada no nó do
          respectivo quarto de vão, como 22.3.1 pede ("nos nós são
          concentradas as forças externas"). Nós A(0, 0), C(l/2, 0), B(l, 0)
          no banzo tracionado e T1(l/4, z), T2(3l/4, z) no comprimido;
          barras 'A-T1', 'T1-C', 'C-T2', 'T2-B' (diagonais), 'T1-T2' (banzo
          comprimido), 'A-C' e 'C-B' (banzo tracionado). A força no tirante
          sai T = Q*l/(8*z) = q*l^2/(8*z), igual ao momento de vão dividido
          por z. As diagonais 'T1-C' e 'C-T2' saem nulas sob carga simétrica
          e existem para que a treliça seja isostática, como 22.3.1 exige.

    Apoios: A com ux e uy, B com uy (treliça isostática).
    Unidades: l, h e z em cm; P em kN; q em kN/m. Devolve a ``TrelicaBT``
    pronta para ``resolver``.

    Informe exatamente um entre ``P_kn`` e ``q_kn_m``.
    """
    l = float(l_cm)
    h = float(h_cm)
    if (P_kn is None) == (q_kn_m is None):
        raise ValueError(
            "Informe exatamente um entre P_kn (carga concentrada no meio do "
            "vão) e q_kn_m (carga uniforme superior).")
    z = float(z_cm) if z_cm is not None else braco_alavanca_viga_parede_cm(l, h, False)
    if not (0.0 < z < h):
        raise FaixaNormativaError(
            f"z = {_num(z)} cm tem de ficar entre 0 e h = {_num(h)} cm.")
    t = TrelicaBT(nome="viga-parede biapoiada (22.4.3)", espacial=False)
    if P_kn is not None:
        P = float(P_kn)
        t.no("A", 0.0, 0.0).no("B", l, 0.0).no("C", l / 2.0, z)
        t.barra("A-B", "A", "B").barra("A-C", "A", "C").barra("C-B", "C", "B")
        t.apoio("A", "ux", "uy").apoio("B", "uy")
        t.forca("C", Fy_kn=-P)
        return t
    Q = float(q_kn_m) * l / 100.0     # kN/m -> kN no vão l (cm)
    t.no("A", 0.0, 0.0).no("C", l / 2.0, 0.0).no("B", l, 0.0)
    t.no("T1", l / 4.0, z).no("T2", 3.0 * l / 4.0, z)
    t.barra("A-C", "A", "C").barra("C-B", "C", "B")
    t.barra("A-T1", "A", "T1").barra("T1-C", "T1", "C")
    t.barra("C-T2", "C", "T2").barra("T2-B", "T2", "B")
    t.barra("T1-T2", "T1", "T2")
    t.apoio("A", "ux", "uy").apoio("B", "uy")
    t.forca("T1", Fy_kn=-Q / 2.0).forca("T2", Fy_kn=-Q / 2.0)
    return t


def modelo_viga_parede_continua(l_cm: float, h_cm: float,
                                P_kn: float | None = None,
                                q_kn_m: float | None = None,
                                z_cm: float | None = None,
                                R_interno_kn: float | None = None) -> TrelicaBT:
    """Treliça de bielas e tirantes de viga-parede contínua de dois vãos
    iguais, com carga superior (22.4.3, PDF p. 205; 22.3.1, PDF p. 203).

    Geometria da literatura (Leonhardt & Mönnig, vol. 2; Schlaich, Schäfer &
    Jennewein, 1987): a resultante da carga de cada vão é concentrada no nó
    superior do meio do vão, o banzo tracionado inferior fica em y = 0 e o
    banzo superior a z acima; o banzo superior entre os dois nós carregados é
    o **tirante negativo** sobre o apoio central.

        - nós: A(0, 0), C(l, 0) e E(2l, 0) no nível inferior; T1(l/2, z) e
          T2(3l/2, z) no superior;
        - barras: 'A-T1', 'T1-C', 'C-T2', 'T2-E' (diagonais), 'T1-T2' (banzo
          superior, tirante negativo sobre o apoio central) e 'A-C', 'C-E'
          (banzo inferior, tirantes de vão);
        - apoios: A com ux e uy, E com uy; a **reação do apoio central entra
          como força nodal** em C, como 22.3.1 manda ("as reações de apoio
          devem ser previamente obtidas através de uma análise linear ou não
          linear").

    ``R_interno_kn`` é essa reação. Sem ela, usa-se o valor elástico da viga
    contínua de dois vãos iguais de barra: 11P/8 com carga concentrada no
    meio de cada vão, 1,25*q*l com carga uniforme. Para viga-parede, o
    projetista deve usar as reações da sua própria análise (22.4.3 pede
    modelo plano elástico linear, ou MEF).

    Unidades: l, h e z em cm; P em kN; q em kN/m. Informe exatamente um entre
    ``P_kn`` e ``q_kn_m``. Devolve a ``TrelicaBT`` pronta para ``resolver``.
    """
    l = float(l_cm)
    h = float(h_cm)
    if (P_kn is None) == (q_kn_m is None):
        raise ValueError(
            "Informe exatamente um entre P_kn (carga concentrada no meio de "
            "cada vão) e q_kn_m (carga uniforme superior).")
    z = float(z_cm) if z_cm is not None else braco_alavanca_viga_parede_cm(l, h, True)
    if not (0.0 < z < h):
        raise FaixaNormativaError(
            f"z = {_num(z)} cm tem de ficar entre 0 e h = {_num(h)} cm.")
    if P_kn is not None:
        P = float(P_kn)
        R_int = float(R_interno_kn) if R_interno_kn is not None else 11.0 * P / 8.0
    else:
        P = float(q_kn_m) * l / 100.0
        R_int = float(R_interno_kn) if R_interno_kn is not None else 1.25 * P
    t = TrelicaBT(nome="viga-parede contínua de dois vãos (22.4.3)", espacial=False)
    t.no("A", 0.0, 0.0).no("C", l, 0.0).no("E", 2.0 * l, 0.0)
    t.no("T1", l / 2.0, z).no("T2", 3.0 * l / 2.0, z)
    t.barra("A-C", "A", "C").barra("C-E", "C", "E")
    t.barra("A-T1", "A", "T1").barra("T1-C", "T1", "C")
    t.barra("C-T2", "C", "T2").barra("T2-E", "T2", "E")
    t.barra("T1-T2", "T1", "T2")
    t.apoio("A", "ux", "uy").apoio("E", "uy")
    t.forca("T1", Fy_kn=-P).forca("T2", Fy_kn=-P).forca("C", Fy_kn=R_int)
    return t


def verificar_apoio_viga_parede(R_kn: float, b_cm: float,
                                comprimento_apoio_cm: float, fck_mpa: float,
                                tipo: str = "CCT",
                                gama_c: float = GAMA_C) -> ResultadoNoBielaTirante:
    """Verificação indireta da compressão máxima nas bielas de viga-parede,
    pela tensão de compressão vertical no apoio (22.4.3, PDF p. 205).

    22.4.3: "A verificação da compressão máxima nas bielas pode ser feita
    indiretamente, limitando-se o valor de cálculo das tensões de compressão
    verticais nos apoios, conforme 22.3.2."

        sigma = R_d / (b * l_apoio)

    ``R_kn`` é a reação de cálculo no apoio, kN; ``b_cm`` a espessura da
    viga-parede e ``comprimento_apoio_cm`` o comprimento do apoio, cm.
    ``tipo`` é o tipo de nó de 22.3.2: 'CCT' é o padrão, porque no apoio de
    uma viga-parede biapoiada confluem bielas e o tirante do banzo inferior;
    use 'CCC' quando nenhum tirante é ancorado no nó e 'CTT' quando dois ou
    mais são. Devolve o ``ResultadoNoBielaTirante`` de ``verificar_no``.
    """
    b = float(b_cm)
    la = float(comprimento_apoio_cm)
    if b <= 0.0 or la <= 0.0:
        raise FaixaNormativaError(
            f"b = {_num(b)} cm e o comprimento do apoio = {_num(la)} cm têm "
            "de ser positivos.")
    sigma = abs(float(R_kn)) / (b * la)
    res = verificar_no(tipo, sigma, fck_mpa, gama_c)
    memoria = (
        "22.4.3: verificação indireta da biela de viga-parede pela tensão de "
        "compressão vertical no apoio, conforme 22.3.2.",
        f"sigma = Rd/(b*l_apoio) = {_num(abs(float(R_kn)))}/"
        f"({_num(b)}*{_num(la)}) = {_num(sigma)} kN/cm2.",
    ) + res.memoria
    return ResultadoNoBielaTirante(
        tipo=res.tipo, sigma_kncm2=res.sigma_kncm2, fcd_no_kncm2=res.fcd_no_kncm2,
        razao=res.razao, ok=res.ok, governante="22.4.3", memoria=memoria)


# ---------------------------------------------------------------------------
# 22.6.3 e 22.7.3 — Modelos tridimensionais de bielas e tirantes
# (PDF p. 212 e 213)
# ---------------------------------------------------------------------------
def _reacoes_lineares(posicoes: list, N_kn: float, ex_cm: float,
                      ey_cm: float) -> list:
    """Distribuição linear (bloco/sapata rígidos) da força do pilar entre os
    apoios, sobre as posições dos nós do modelo: R_i = N/n + Mx*y_i/Sy +
    My*x_i/Sx, com Mx = N*ey e My = N*ex."""
    n = len(posicoes)
    xs = np.array([p[0] for p in posicoes], dtype=float)
    ys = np.array([p[1] for p in posicoes], dtype=float)
    Sx = float(np.sum(xs ** 2))
    Sy = float(np.sum(ys ** 2))
    R = np.full(n, float(N_kn) / n)
    if abs(ex_cm) > 0.0:
        if Sx <= 0.0:
            raise FaixaNormativaError(
                "Excentricidade em x sem apoios distribuídos em x: não há "
                "como distribuir a reação.")
        R += float(N_kn) * float(ex_cm) * xs / Sx
    if abs(ey_cm) > 0.0:
        if Sy <= 0.0:
            raise FaixaNormativaError(
                "Excentricidade em y sem apoios distribuídos em y: não há "
                "como distribuir a reação.")
        R += float(N_kn) * float(ey_cm) * ys / Sy
    return [float(v) for v in R]


def _ordem_perimetro(posicoes: list) -> list:
    """Ordem dos apoios pelo ângulo polar em torno do centroide, para fechar
    o perímetro de tirantes."""
    xs = np.array([p[0] for p in posicoes], dtype=float)
    ys = np.array([p[1] for p in posicoes], dtype=float)
    cx, cy = float(np.mean(xs)), float(np.mean(ys))
    ang = np.arctan2(ys - cy, xs - cx)
    return [int(k) for k in np.argsort(ang)]


def modelo_bloco_estacas(posicoes_estacas_cm, Nd_kn: float, d_cm: float,
                         ap_cm: float = 0.0, bp_cm: float | None = None,
                         ex_cm: float = 0.0, ey_cm: float = 0.0,
                         reacoes_estacas_kn=None, tirantes=None) -> TrelicaBT:
    """Modelo de bielas e tirantes tridimensional de bloco sobre estacas
    (22.7.3, PDF p. 213; 22.3.1, PDF p. 203).

    22.7.3 aceita "modelos tridimensionais lineares ou não lineares e
    modelos biela-tirante tridimensionais". O modelo montado aqui é o
    clássico de Blévot, na forma de treliça espacial:

        - **nó do pilar** no ponto de aplicação da força, (ex, ey, d), com a
          força Nd para baixo;
        - **nó de cada estaca** no nível do topo do bloco inferior (z = 0),
          com a reação da estaca para cima;
        - uma **biela** do nó do pilar a cada nó de estaca e **tirantes**
          ligando os nós de estaca.

    Recuo de Blévot: o nó da estaca fica recuado, componente a componente,
    de ap/4 em x e bp/4 em y, porque a biela parte do centroide da parcela da
    seção do pilar associada àquela estaca e não do eixo do pilar. Com
    ``ap_cm = bp_cm = 0`` a biela parte do eixo. O recuo nunca passa do
    próprio valor (estaca sob o pilar vira nó no eixo, com biela vertical).
    Para bloco de duas estacas alinhadas em x isso reproduz exatamente o
    método das bielas: T = Nd*(2e - ap)/(8*d).

    Reações: ``reacoes_estacas_kn`` recebe as reações obtidas na análise
    prévia que 22.3.1 exige. Sem elas, usa-se a distribuição linear de bloco
    rígido sobre as posições dos nós do modelo. As reações passadas têm de
    equilibrar a força do pilar, senão ``resolver`` levanta
    ``TrelicaNaoAutoequilibradaError``.

    Topologia dos tirantes (``tirantes``: lista de pares de índices das
    estacas). Padrão, escolhido para que a treliça seja isostática como
    22.3.1 exige:

        - 2 estacas: treliça **plana** (x vertical no plano x-y do modelo),
          com o único tirante entre as duas estacas;
        - 3 estacas: treliça espacial com os 3 tirantes do perímetro;
        - 4 estacas: os 4 tirantes do perímetro mais uma diagonal, necessária
          para fechar a isostaticidade; sob carga centrada a diagonal sai
          nula;
        - 5 ou mais estacas: informe ``tirantes``; a contagem de
          isostaticidade de ``resolver`` recusa topologia que não feche.

    Unidades: posições e d em cm; Nd em kN (valor positivo, compressão do
    pilar). Devolve a ``TrelicaBT`` pronta para ``resolver``.
    """
    pos = [(float(p[0]), float(p[1])) for p in posicoes_estacas_cm]
    n = len(pos)
    if n < 2:
        raise ValueError("O bloco precisa de pelo menos 2 estacas.")
    d = float(d_cm)
    if d <= 0.0:
        raise FaixaNormativaError(
            f"d = {_num(d)} cm: a altura útil do bloco tem de ser positiva.")
    ap = float(ap_cm)
    bp = float(ap_cm if bp_cm is None else bp_cm)
    if ap < 0.0 or bp < 0.0:
        raise FaixaNormativaError("ap e bp não podem ser negativos.")

    def _recuar(v: float, c: float) -> float:
        if abs(v) <= c / 4.0:
            return 0.0
        return math.copysign(abs(v) - c / 4.0, v)

    pos_mod = [(_recuar(x, ap), _recuar(y, bp)) for x, y in pos]
    if reacoes_estacas_kn is None:
        R = _reacoes_lineares(pos_mod, float(Nd_kn), float(ex_cm), float(ey_cm))
    else:
        R = [float(v) for v in reacoes_estacas_kn]
        if len(R) != n:
            raise ValueError(
                f"reacoes_estacas_kn tem {len(R)} valor(es) para {n} estaca(s).")

    plano = (n == 2 and all(abs(y) < 1e-9 for _, y in pos_mod)
             and abs(float(ey_cm)) < 1e-9)
    t = TrelicaBT(nome=f"bloco sobre {n} estacas (22.7.3)", espacial=not plano)
    if plano:
        t.no("P", float(ex_cm), d)
        for k, (x, _) in enumerate(pos_mod):
            t.no(k, x, 0.0)
            t.barra(("biela", k), "P", k)
            t.forca(k, Fy_kn=R[k])
        t.barra(("tirante", 0, 1), 0, 1)
        t.forca("P", Fy_kn=-float(Nd_kn))
        return t

    t.no("P", float(ex_cm), float(ey_cm), d)
    for k, (x, y) in enumerate(pos_mod):
        t.no(k, x, y, 0.0)
        t.barra(("biela", k), "P", k)
        t.forca(k, Fz_kn=R[k])
    t.forca("P", Fz_kn=-float(Nd_kn))
    if tirantes is None:
        ordem = _ordem_perimetro(pos_mod)
        pares = [(ordem[i], ordem[(i + 1) % n]) for i in range(n)]
        if n == 4:
            pares.append((ordem[0], ordem[2]))
    else:
        pares = [(int(a), int(b)) for a, b in tirantes]
    for a, b in pares:
        t.barra(("tirante", min(a, b), max(a, b)), a, b)
    return t


def modelo_sapata(a_cm: float, b_cm: float, ap_cm: float, bp_cm: float,
                  d_cm: float, Nd_kn: float, ex_cm: float = 0.0,
                  ey_cm: float = 0.0) -> TrelicaBT:
    """Modelo de bielas e tirantes tridimensional de sapata sob pilar
    (22.6.3, PDF p. 212; 22.3.1, PDF p. 203).

    22.6.3 manda usar "modelos tridimensionais lineares ou modelos
    biela-tirante tridimensionais", contemplando o trabalho à flexão nas duas
    direções de 22.6.2 e o fendilhamento na região de contato pilar-sapata
    de 21.2 (para este, veja ``modelo_zona_ancoragem``).

    Geometria clássica do método das bielas (Lebelle; CEB): a pressão do
    terreno é concentrada na resultante de cada quadrante da base, em
    (±a/4, ±b/4), e a biela de cada quadrante parte do centroide do quadrante
    correspondente da seção do pilar, em (±ap/4, ±bp/4) — o que equivale, no
    modelo de nó único do pilar, a nós de base em (±(a-ap)/4, ±(b-bp)/4).
    A treliça é a de ``modelo_bloco_estacas`` com quatro apoios: 4 bielas, os
    4 tirantes do perímetro e uma diagonal (nula sob carga centrada), que
    fecha a isostaticidade de 22.3.1.

    Sob carga centrada, cada um dos dois tirantes paralelos a x recebe
    Nd*(a-ap)/(16*d) e a soma dos dois, isto é a tração total da direção x,
    vale Nd*(a-ap)/(8*d) — o valor do método das bielas de
    ``sapatas_nbr6118.tracao_base_bielas``. O mesmo vale na direção y com b
    e bp.

    Unidades: dimensões em cm; Nd em kN. ``ex_cm`` e ``ey_cm`` são as
    excentricidades da força do pilar, cm; com elas, as reações dos quatro
    quadrantes saem da distribuição linear de sapata rígida (22.6.1) sobre as
    posições dos nós do modelo. Devolve a ``TrelicaBT`` pronta para
    ``resolver``.
    """
    a, b = float(a_cm), float(b_cm)
    if a <= 0.0 or b <= 0.0:
        raise FaixaNormativaError("As dimensões da sapata têm de ser positivas.")
    if float(ap_cm) >= a or float(bp_cm) >= b:
        raise FaixaNormativaError(
            f"O pilar ({_num(ap_cm)} x {_num(bp_cm)} cm) não cabe na sapata "
            f"({_num(a)} x {_num(b)} cm).")
    pos = [(a / 4.0, b / 4.0), (a / 4.0, -b / 4.0),
           (-a / 4.0, -b / 4.0), (-a / 4.0, b / 4.0)]
    t = modelo_bloco_estacas(pos, Nd_kn, d_cm, ap_cm=ap_cm, bp_cm=bp_cm,
                             ex_cm=ex_cm, ey_cm=ey_cm)
    t.nome = "sapata sob pilar (22.6.3)"
    return t


# ---------------------------------------------------------------------------
# 21.2.3 — Região de introdução da protensão (PDF p. 199)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoZonaAncoragem:
    """Resultado do modelo de bielas e tirantes da zona de ancoragem da
    protensão (21.2.3, com a Seção 22)."""

    P_kn: float
    a_cm: float
    h_prisma_cm: float
    T_fendilhamento_kn: float
    x_tirante_cm: float
    C_biela_kn: float
    tan_theta: float
    As_tirante_cm2: float | None
    sigma_ancoragem_kncm2: float | None
    no_ancoragem: ResultadoNoBielaTirante | None
    ok: bool
    governante: str
    memoria: tuple


def prisma_simetrico_cm(h_cm: float, e_cm: float = 0.0) -> float:
    """Altura do prisma simétrico de ancoragem, cm (21.2.3, PDF p. 199).

    h' = h - 2*|e|: o prisma simétrico de Guyon é a parte da seção centrada
    na ancoragem, de altura igual ao dobro da distância da ancoragem à borda
    mais próxima. ``h_cm`` é a altura da seção e ``e_cm`` a excentricidade da
    ancoragem em relação ao centro da seção, cm. Com e = 0, h' = h.

    Fonte: Guyon (1953), prisma simétrico; mesma definição em Schlaich &
    Schäfer (1987) e na AASHTO LRFD 5.9.5.6.5. A NBR 6118:2026 não dá
    expressão fechada em 21.2.3: ela exige modelo tridimensional ou bielas e
    tirantes da Seção 22 (ver ``forca_fendilhamento_kn``).
    """
    h = float(h_cm)
    e = abs(float(e_cm))
    if h <= 0.0:
        raise FaixaNormativaError(
            f"h = {_num(h)} cm: a altura da seção tem de ser positiva.")
    hp = h - 2.0 * e
    if hp <= 0.0:
        raise FaixaNormativaError(
            f"e = {_num(e)} cm: a excentricidade da ancoragem tem de ser "
            f"menor que h/2 = {_num(h / 2.0)} cm.")
    return hp


def forca_fendilhamento_kn(P_kn: float, a_cm: float, h_cm: float,
                           e_cm: float = 0.0) -> float:
    """Força de fendilhamento (tração transversal) da zona de ancoragem da
    protensão, kN (21.2.3, PDF p. 199, com a Seção 22).

        T = 0,25 * P * (1 - a/h')       com h' = h - 2*|e|

    ``P_kn`` é a força de cálculo da ancoragem, kN; ``a_cm`` a dimensão da
    placa de ancoragem na direção considerada e ``h_cm`` a altura da seção na
    mesma direção, cm; ``e_cm`` a excentricidade da ancoragem, cm.

    A NBR 6118:2026 **não traz esta expressão**: 21.2.3 só exige modelos
    tridimensionais, ou o método das bielas e tirantes da Seção 22,
    considerando o equilíbrio global, a tração transversal (fendilhamento) e
    o esmagamento. A expressão acima é o resultado fechado do modelo de
    bielas e tirantes do prisma simétrico (Guyon, 1953; Schlaich & Schäfer,
    1987; adotada na AASHTO LRFD 5.9.5.6.5a como 0,25*ΣPu*(1 - a/h)) e é
    exatamente o que a treliça de ``modelo_zona_ancoragem`` devolve.

    Faixa: 0 < a < h'. Fora disso levanta ``FaixaNormativaError``.
    """
    P = float(P_kn)
    a = float(a_cm)
    hp = prisma_simetrico_cm(h_cm, e_cm)
    if not (0.0 < a < hp):
        raise FaixaNormativaError(
            f"a = {_num(a)} cm tem de ficar entre 0 e h' = {_num(hp)} cm "
            "(dimensão da placa menor que o prisma simétrico de ancoragem).")
    return 0.25 * P * (1.0 - a / hp)


def posicao_fendilhamento_cm(h_cm: float, e_cm: float = 0.0) -> float:
    """Distância da face de ancoragem ao tirante de fendilhamento, cm
    (21.2.3, PDF p. 199, com a Seção 22).

        d_burst = h'/2                  com h' = h - 2*|e|

    É onde a treliça do prisma simétrico coloca o tirante transversal — o
    ponto em que a difusão da força fica completa (Guyon, 1953; Schlaich &
    Schäfer, 1987; AASHTO LRFD 5.9.5.6.5a, que escreve 0,5*(h - 2e)). A
    armadura de fendilhamento deve ser distribuída em torno dessa posição.
    """
    return prisma_simetrico_cm(h_cm, e_cm) / 2.0


def modelo_zona_ancoragem(P_kn: float, a_cm: float, h_cm: float,
                          e_cm: float = 0.0, fck_mpa: float | None = None,
                          area_ancoragem_cm2: float | None = None,
                          fyd_kncm2: float | None = None,
                          gama_c: float = GAMA_C) -> ResultadoZonaAncoragem:
    """Modelo de bielas e tirantes da região de introdução da protensão
    (21.2.3, PDF p. 199, com 22.3.2 e 22.3.3).

    21.2.3 exige que a zona de ancoragem seja analisada e projetada
    considerando (a) o equilíbrio global da região, (b) a tração transversal
    (fendilhamento) e (c) o esmagamento por compressão, com modelo
    tridimensional ou pelo método das bielas e tirantes da Seção 22. O modelo
    aqui é o do prisma simétrico, na forma consagrada de bielas e tirantes
    (Guyon, 1953; Schlaich & Schäfer, 1987; AASHTO LRFD 5.9.5.6.5a):

        - a força P entra pela placa e se divide em duas metades, a ±a/4 do
          eixo do prisma;
        - cada metade se difunde até ±h'/4 na seção que fica a h' da face,
          onde a tensão volta a ser uniforme (h' = h - 2|e| é o prisma
          simétrico; note que h' é exatamente a extensão da região D de 22.2);
        - o desvio de cada metade se completa na seção x = h'/2, onde fica o
          **tirante de fendilhamento**;
        - o equilíbrio de nó dá, em forma fechada,
          T = (P/2)*((h' - a)/4)/(h'/2) = 0,25*P*(1 - a/h'),
          e a biela inclinada C = -(P/2)*L/(h'/2), com
          L = sqrt((h'/2)^2 + ((h' - a)/4)^2).

    Verificações acopladas: com ``fck_mpa`` e ``area_ancoragem_cm2``, o nó da
    ancoragem é verificado por ``verificar_no`` (22.3.2) como nó CCT (a
    biela chega e o tirante de fendilhamento atravessa a região); com
    ``fyd_kncm2``, a armadura do tirante sai de ``As_tirante_cm2`` (22.3.3).

    Unidades: P em kN; a, h e e em cm; fck em MPa; área em cm2; fyd em
    kN/cm2. Devolve ``ResultadoZonaAncoragem``.
    """
    P = float(P_kn)
    if P <= 0.0:
        raise FaixaNormativaError(
            f"P = {_num(P)} kN: a força de ancoragem tem de ser positiva.")
    a = float(a_cm)
    hp = prisma_simetrico_cm(h_cm, e_cm)
    T = forca_fendilhamento_kn(P, a, h_cm, e_cm)
    x_t = posicao_fendilhamento_cm(h_cm, e_cm)
    dy = (hp - a) / 4.0
    L = math.hypot(x_t, dy)
    C = -(P / 2.0) * L / x_t
    tan_theta = dy / x_t
    As = As_tirante_cm2(T, fyd_kncm2) if fyd_kncm2 is not None else None
    sigma = None
    no = None
    if area_ancoragem_cm2 is not None:
        area = float(area_ancoragem_cm2)
        if area <= 0.0:
            raise FaixaNormativaError(
                f"area_ancoragem_cm2 = {_num(area)}: tem de ser positiva.")
        sigma = P / area
        if fck_mpa is not None:
            no = verificar_no("CCT", sigma, fck_mpa, gama_c)
    ok = True if no is None else no.ok
    memoria = [
        "21.2.3: a região de introdução da protensão exige modelo "
        "tridimensional, ou bielas e tirantes da Seção 22, considerando o "
        "equilíbrio global, o fendilhamento (tração transversal) e o "
        "esmagamento por compressão.",
        "Modelo do prisma simétrico (Guyon, 1953; Schlaich & Schäfer, 1987; "
        "AASHTO LRFD 5.9.5.6.5a). A NBR 6118:2026 não traz expressão fechada "
        "para o fendilhamento; esta é a da literatura declarada.",
        f"Prisma simétrico: h' = h - 2*|e| = {_num(h_cm)} - 2*{_num(abs(float(e_cm)))} "
        f"= {_num(hp)} cm; placa a = {_num(a)} cm.",
        f"Tirante de fendilhamento: T = 0,25*P*(1 - a/h') = 0,25*{_num(P)}*"
        f"(1 - {_num(a)}/{_num(hp)}) = {_num(T)} kN, na seção x = h'/2 = "
        f"{_num(x_t)} cm da face de ancoragem.",
        f"Biela inclinada: tan(theta) = ((h' - a)/4)/(h'/2) = {_num(tan_theta)}; "
        f"C = -(P/2)*L/(h'/2) = {_num(C)} kN (compressão), L = {_num(L)} cm.",
        f"Extensão da região D (22.2): h' = {_num(hp)} cm a partir da face de "
        "ancoragem.",
    ]
    if As is not None:
        memoria.append(
            f"22.3.3: As = T/fyd = {_num(T)}/{_num(fyd_kncm2)} = {_num(As)} cm2, "
            "distribuída em torno da seção do tirante.")
    if sigma is not None:
        memoria.append(
            f"Esmagamento sob a ancoragem: sigma = P/Ac0 = {_num(P)}/"
            f"{_num(area_ancoragem_cm2)} = {_num(sigma)} kN/cm2.")
    if no is not None:
        memoria.extend(no.memoria)
    return ResultadoZonaAncoragem(
        P_kn=P, a_cm=a, h_prisma_cm=hp, T_fendilhamento_kn=T, x_tirante_cm=x_t,
        C_biela_kn=C, tan_theta=tan_theta, As_tirante_cm2=As,
        sigma_ancoragem_kncm2=sigma, no_ancoragem=no, ok=ok,
        governante="21.2.3", memoria=tuple(memoria))
