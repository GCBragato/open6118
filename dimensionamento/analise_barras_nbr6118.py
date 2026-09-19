"""Análise linear de estruturas de barras (ABNT NBR 6118:2026, Seções 11 e 14).

Módulo do pacote P44 do plano de implementação. Dá à biblioteca um cálculo
próprio de estruturas de barras pelo método dos deslocamentos, com as
hipóteses da análise linear da norma, para que ela produza os esforços em vez
de só recebê-los. Itens cobertos (páginas do PDF):

    - 11.3.3.3 Deslocamentos de apoio como ação permanente indireta (p. 78):
      caso de carga com deslocamento imposto de apoio (valor característico
      superior δk,sup) e ``acao_deslocamentos_apoio`` com o inferior nulo.
    - 11.4.1.1 Cargas de utilização nas posições mais desfavoráveis
      (p. 81-82): ``alternancia_cargas``, com a envoltória e a dispensa de
      14.6.6.3 (P14).
    - 14.5.2   Análise linear (p. 105): comportamento elástico-linear, seção
      bruta e módulo secante Ecs com o ν e o Gc de 8.2.8 e 8.2.9 (p. 44-45).
    - 14.6.4.1 Valores de rigidez (p. 111): Ecs e momento de inércia da seção
      bruta como padrão; flecha exige fissuração e fluência (17.3.2.1, P8).
    - 14.8.1   Vigas-parede e pilares-parede (p. 119): elemento linear
      equivalente com deformação por cisalhamento (Timoshenko) e ajuste da
      rigidez à flexão.

Opções que vêm de outros itens: a rigidez à torção reduzida de 14.6.6.2
(p. 115, via ``analise_linear_nbr6118.rigidez_torcao_reduzida``), as
rigidezes aproximadas de 15.7.3 (p. 126-127) e a majoração de 10 % do módulo
na estabilidade global de 15.5.1 (p. 124).

Tipos de modelo e graus de liberdade por nó:

    ============== =============================== ======================
    tipo           graus ativos                    plano
    ============== =============================== ======================
    portico_plano  ux, uy, rz (3)                  XY (z = 0)
    grelha         uz, rx, ry (3)                  XY (z = 0), carga em Z
    portico_espacial ux, uy, uz, rx, ry, rz (6)    qualquer
    trelica_plana  ux, uy (2), só força normal     XY (z = 0)
    trelica_espacial ux, uy, uz (3), só normal     qualquer
    ============== =============================== ======================

Unidades: coordenadas e comprimentos em cm; forças em kN; momentos em kN·cm;
carga distribuída em kN/m (convertida para kN/cm dentro das funções);
módulos em MPa na entrada (convertidos para kN/cm², 1 kN/cm² = 10 MPa);
deslocamentos em cm e rotações em rad; molas em kN/cm (translação) e
kN·cm/rad (rotação); temperatura em °C.

Eixos locais da barra: x do nó inicial para o final; z no plano que contém x
e o vetor de referência (padrão: Z global; em barra paralela a Z, X global);
y = z × x. No pórtico plano e na grelha, z local = Z global. O momento de
inércia ``I`` da seção é o do plano principal: no pórtico plano, flexão no
plano XY (em torno de z local); na grelha e no pórtico espacial, flexão no
plano x-z local (em torno de y local), que é o plano vertical da barra
horizontal. ``I2`` é o do outro plano.

Convenção dos esforços ao longo da barra (x medido a partir da face inicial
da parte flexível, isto é, depois do trecho rígido):

    - N: força normal, tração positiva;
    - Vy, Vz: força cortante, soma das forças à esquerda da seção na direção
      y (ou z) local, de modo que dMz/dx = Vy e dMy/dx = Vz;
    - T: momento de torção;
    - Mz = E·I·v'' e My = E·I·w'' (v, w deslocamentos em y e z locais):
      momento positivo traciona a face de y (ou z) local negativo. Na viga
      horizontal com carga da gravidade, o momento positivo é o de vão.

As funções não têm valor esperado na norma: os testes usam soluções fechadas
e todo resultado confere o equilíbrio (soma das reações e das cargas nula,
em forças e momentos); se não fechar, ``resolver`` levanta
``ErroEquilibrio``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

try:  # executado como script, ou com dimensionamento/ no sys.path
    import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # importado como pacote (dimensionamento.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr

FaixaNormativaError = nbr.FaixaNormativaError


class ErroEquilibrio(RuntimeError):
    """O resultado da análise não fecha o equilíbrio (soma das reações e das
    cargas diferente de zero além da tolerância)."""


class EstruturaHipostatica(ValueError):
    """A matriz de rigidez é singular: a estrutura é hipostática (mecanismo)
    ou tem grau de liberdade carregado sem rigidez."""


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
GRAUS = ("ux", "uy", "uz", "rx", "ry", "rz")
_IDX = {g: i for i, g in enumerate(GRAUS)}

TIPOS_MODELO = {
    "portico_plano": (0, 1, 5),
    "grelha": (2, 3, 4),
    "portico_espacial": (0, 1, 2, 3, 4, 5),
    "trelica_plana": (0, 1),
    "trelica_espacial": (0, 1, 2),
}
_TIPOS_PLANOS = ("portico_plano", "grelha", "trelica_plana")
_TIPOS_TRELICA = ("trelica_plana", "trelica_espacial")

FATOR_CISALHAMENTO_RETANGULO = 5.0 / 6.0   # área de cisalhamento Av = 5/6·A (seção retangular)
MAJORACAO_EC_ESTABILIDADE_GLOBAL = 1.10     # 15.5.1 (p. 124): Ecs pode ser majorado em 10 %

# 15.7.3 (PDF p. 126-127) — rigidez secante aproximada (EI)sec = fator·Ec·Ic
TABELA_15_7_3_FATOR_EI = {
    "laje": 0.3,
    "viga": 0.4,           # As' ≠ As
    "viga_simetrica": 0.5,  # As' = As
    "pilar": 0.8,
}
N_ANDARES_MIN_15_7_3 = 4

TOL_EQUILIBRIO = 1e-6

_GAUSS_X, _GAUSS_W = np.polynomial.legendre.leggauss(5)   # exata até grau 9


def _fmt(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


# ---------------------------------------------------------------------------
# Material e seção — 8.2.8, 8.2.9 (PDF p. 44-45), 14.5.2 (p. 105), 14.6.4.1 (p. 111)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Material:
    """Material elástico-linear da barra (14.5.2, PDF p. 105).

    E_mpa: módulo de elasticidade, MPa. G_mpa: módulo de elasticidade
    transversal, MPa. alfa_termico: coeficiente de dilatação térmica, 1/°C.
    Para o concreto, use ``Material.concreto``, que tira Ecs, Gc e α do
    núcleo (8.2.8, 8.2.9 e 8.2.3).
    """

    E_mpa: float
    G_mpa: float
    alfa_termico: float = nbr.ALFA_TERMICO_CONCRETO
    descricao: str = ""

    def __post_init__(self):
        if self.E_mpa <= 0.0 or self.G_mpa <= 0.0:
            raise FaixaNormativaError(
                f"Módulos E = {_fmt(self.E_mpa)} MPa e G = {_fmt(self.G_mpa)} MPa "
                "têm de ser positivos.")

    @classmethod
    def concreto(cls, fck_mpa: float, alpha_e: float = 1.0,
                 estabilidade_global: bool = False) -> "Material":
        """Concreto com o módulo secante da análise linear (14.5.2 e 14.6.4.1).

        E = Ecs = αi·Eci (8.2.8, PDF p. 44) e G = Gc = Ecs/2,4 (8.2.9, PDF
        p. 45, que corresponde a ν = 0,2), ambos do núcleo; α = 10⁻⁵/°C
        (8.2.3). Com ``estabilidade_global=True``, E e G são majorados em
        10 %, como 15.5.1 (PDF p. 124) permite na análise de estabilidade
        global da estrutura como um todo.

        Faixa: a do núcleo (C20 a C90).
        """
        E = nbr.Ecs(fck_mpa, alpha_e)
        G = nbr.Gc(fck_mpa, alpha_e)
        desc = f"Concreto C{_fmt(fck_mpa)}: Ecs = {_fmt(E)} MPa (8.2.8), Gc = Ecs/2,4 = {_fmt(G)} MPa (8.2.9)"
        if estabilidade_global:
            E *= MAJORACAO_EC_ESTABILIDADE_GLOBAL
            G *= MAJORACAO_EC_ESTABILIDADE_GLOBAL
            desc += ", majorados em 10 % para a estabilidade global (15.5.1)"
        return cls(E_mpa=E, G_mpa=G, alfa_termico=nbr.ALFA_TERMICO_CONCRETO, descricao=desc)

    @classmethod
    def elastico(cls, E_mpa: float, nu: float = nbr.POISSON_CONCRETO,
                 alfa_termico: float = nbr.ALFA_TERMICO_CONCRETO) -> "Material":
        """Material elástico genérico com G = E/[2·(1 + ν)]."""
        if not (-1.0 < nu < 0.5):
            raise FaixaNormativaError(f"ν = {_fmt(nu)} fora do intervalo (−1; 0,5).")
        return cls(E_mpa=E_mpa, G_mpa=E_mpa / (2.0 * (1.0 + nu)), alfa_termico=alfa_termico,
                   descricao=f"Elástico: E = {_fmt(E_mpa)} MPa, ν = {_fmt(nu)}")

    @property
    def E_kncm2(self) -> float:
        return self.E_mpa / 10.0

    @property
    def G_kncm2(self) -> float:
        return self.G_mpa / 10.0


def constante_torcao_retangulo_cm4(b_cm: float, h_cm: float) -> float:
    """Constante de torção de Saint-Venant do retângulo, cm⁴.

    J = β·a·b³, com a ≥ b os lados e β = 1/3 − 0,21·(b/a)·[1 − (b/a)⁴/12]
    (aproximação clássica da teoria da elasticidade, erro < 0,5 %). A norma
    não dá esta fórmula; ela é o J elástico sobre o qual 14.6.6.2 aplica a
    redução.
    """
    if b_cm <= 0.0 or h_cm <= 0.0:
        raise FaixaNormativaError("Lados do retângulo têm de ser positivos.")
    a, b = max(b_cm, h_cm), min(b_cm, h_cm)
    r = b / a
    beta = 1.0 / 3.0 - 0.21 * r * (1.0 - r ** 4 / 12.0)
    return beta * a * b ** 3


@dataclass(frozen=True)
class Secao:
    """Seção transversal bruta da barra (14.5.2 e 14.6.4.1).

    A_cm2: área. I_cm4: momento de inércia do plano principal (ver o
    cabeçalho do módulo). I2_cm4: do outro plano (só pórtico espacial).
    J_cm4: constante de torção (grelha e pórtico espacial). Av_cm2 e
    Av2_cm2: áreas de cisalhamento associadas a I e a I2 (só com
    deformação por cisalhamento; padrão 5/6·A).
    """

    A_cm2: float
    I_cm4: float = 0.0
    I2_cm4: float = 0.0
    J_cm4: float = 0.0
    Av_cm2: float | None = None
    Av2_cm2: float | None = None

    def __post_init__(self):
        if self.A_cm2 <= 0.0:
            raise FaixaNormativaError(f"A = {_fmt(self.A_cm2)} cm²: tem de ser positiva.")
        for nome in ("I_cm4", "I2_cm4", "J_cm4"):
            if getattr(self, nome) < 0.0:
                raise FaixaNormativaError(f"{nome} = {_fmt(getattr(self, nome))}: não pode ser negativo.")
        for nome in ("Av_cm2", "Av2_cm2"):
            v = getattr(self, nome)
            if v is not None and v <= 0.0:
                raise FaixaNormativaError(f"{nome} = {_fmt(v)} cm²: tem de ser positiva.")

    @classmethod
    def retangular(cls, b_cm: float, h_cm: float) -> "Secao":
        """Seção retangular bruta: h é a altura no plano principal.

        A = b·h; I = b·h³/12; I2 = h·b³/12; J pelo retângulo
        (``constante_torcao_retangulo_cm4``); Av = Av2 = 5/6·A.
        """
        if b_cm <= 0.0 or h_cm <= 0.0:
            raise FaixaNormativaError("b e h da seção têm de ser positivos.")
        A = b_cm * h_cm
        return cls(A_cm2=A, I_cm4=b_cm * h_cm ** 3 / 12.0, I2_cm4=h_cm * b_cm ** 3 / 12.0,
                   J_cm4=constante_torcao_retangulo_cm4(b_cm, h_cm),
                   Av_cm2=FATOR_CISALHAMENTO_RETANGULO * A,
                   Av2_cm2=FATOR_CISALHAMENTO_RETANGULO * A)

    @property
    def Av_efetiva_cm2(self) -> float:
        return self.Av_cm2 if self.Av_cm2 is not None else FATOR_CISALHAMENTO_RETANGULO * self.A_cm2

    @property
    def Av2_efetiva_cm2(self) -> float:
        return self.Av2_cm2 if self.Av2_cm2 is not None else FATOR_CISALHAMENTO_RETANGULO * self.A_cm2


def fator_rigidez_nlf_aproximada(elemento: str, armadura_simetrica: bool = False,
                                 n_andares: int | None = None) -> float:
    """Fator de (EI)sec = fator·Ec·Ic da não linearidade física aproximada
    (15.7.3, PDF p. 126-127).

    lajes: (EI)sec = 0,3·Ec·Ic; vigas: 0,4·Ec·Ic com As' ≠ As e 0,5·Ec·Ic com
    As' = As; pilares: 0,8·Ec·Ic. Ic é o da seção bruta, com as mesas
    colaborantes quando for o caso, e Ec o de 15.5.1 (``Material.concreto``
    com ``estabilidade_global=True``).

    Só para os esforços globais de 2ª ordem em estruturas reticuladas com no
    mínimo quatro andares; os valores não servem para esforços locais de 2ª
    ordem. Com ``n_andares`` < 4, levanta erro: a norma manda avaliar a
    redução de forma específica. Use o fator em ``Modelo.barra(fator_EI=...)``.
    """
    chave = nbr._chave(elemento)
    if chave in ("laje", "lajes"):
        f = TABELA_15_7_3_FATOR_EI["laje"]
    elif chave in ("viga", "vigas"):
        f = TABELA_15_7_3_FATOR_EI["viga_simetrica" if armadura_simetrica else "viga"]
    elif chave in ("pilar", "pilares"):
        f = TABELA_15_7_3_FATOR_EI["pilar"]
    else:
        raise ValueError(f"Elemento {elemento!r} desconhecido: use 'laje', 'viga' ou 'pilar' (15.7.3).")
    if n_andares is not None and n_andares < N_ANDARES_MIN_15_7_3:
        raise FaixaNormativaError(
            f"{n_andares} andar(es): 15.7.3 só vale para estruturas reticuladas com no mínimo "
            "quatro andares; abaixo disso, a redução de rigidez deve ser avaliada de forma "
            "específica.")
    return f


def fator_rigidez_torcao(classe_protensao: int | None = None,
                         desprezar_para_elu: bool = False) -> float:
    """Fator sobre o GJ elástico da viga em grelha e pórtico espacial
    (14.6.6.2, PDF p. 115): 0,15 em concreto armado e protensão parcial;
    1,0 com protensão limitada ou completa (classes 2 e 3); 0 quando se
    despreza a torção de compatibilidade no ELU. Delega a
    ``analise_linear_nbr6118.rigidez_torcao_reduzida`` (P14).
    """
    try:
        import analise_linear_nbr6118 as al
    except ModuleNotFoundError:  # importado como pacote
        from dimensionamento import analise_linear_nbr6118 as al
    return al.rigidez_torcao_reduzida(1.0, classe_protensao, desprezar_para_elu)


# ---------------------------------------------------------------------------
# Modelo: nós, barras, apoios
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class No:
    id: object
    x_cm: float
    y_cm: float
    z_cm: float = 0.0

    @property
    def xyz(self) -> np.ndarray:
        return np.array([self.x_cm, self.y_cm, self.z_cm], dtype=float)


@dataclass(frozen=True)
class Barra:
    """Barra do modelo, com a seção bruta e o material (14.5.2, 14.6.4.1).

    liberacoes_i, liberacoes_j: graus locais liberados na extremidade
    ('rx', 'ry', 'rz'; ou 'rotula' para ry e rz), aplicados na face da parte
    flexível. trecho_rigido_i_cm, trecho_rigido_j_cm: comprimento do trecho
    rígido a partir de cada nó, ao longo do eixo (14.6.2.1; ver
    ``analise_linear_nbr6118.trecho_rigido_cm``). cisalhamento: considera a
    deformação por cisalhamento (Timoshenko). elemento_parede: marca a
    barra como elemento linear equivalente de viga-parede ou pilar-parede
    (14.8.1), que exige ``cisalhamento=True``. fator_EI: ajuste da rigidez à
    flexão (14.8.1 e 15.7.3). fator_GJ: ajuste da rigidez à torção
    (14.6.6.2). trelica: barra biarticulada, só com força normal.
    vetor_ref: vetor no plano x-z local (só pórtico espacial).
    """

    id: object
    no_i: object
    no_j: object
    secao: Secao
    material: Material
    liberacoes_i: tuple = ()
    liberacoes_j: tuple = ()
    trecho_rigido_i_cm: float = 0.0
    trecho_rigido_j_cm: float = 0.0
    cisalhamento: bool = False
    elemento_parede: bool = False
    fator_EI: float = 1.0
    fator_GJ: float = 1.0
    trelica: bool = False
    vetor_ref: tuple | None = None


def _normalizar_liberacoes(lib) -> tuple:
    if lib is None:
        return ()
    if isinstance(lib, str):
        lib = (lib,)
    saida = []
    for g in lib:
        chave = nbr._chave(g)
        if chave in ("rotula", "articulacao"):
            saida += ["ry", "rz"]
        elif chave in ("rx", "ry", "rz"):
            saida.append(chave)
        else:
            raise ValueError(f"Liberação {g!r} inválida: use 'rx', 'ry', 'rz' ou 'rotula'.")
    return tuple(sorted(set(saida)))


class Modelo:
    """Modelo de barras para ``resolver`` (método dos deslocamentos).

    tipo: 'portico_plano', 'grelha', 'portico_espacial', 'trelica_plana' ou
    'trelica_espacial' (ver o cabeçalho do módulo).
    """

    def __init__(self, tipo: str = "portico_plano"):
        chave = {nbr._chave(t): t for t in TIPOS_MODELO}.get(nbr._chave(tipo))
        if chave is None:
            raise ValueError(f"Tipo de modelo {tipo!r} desconhecido: use {', '.join(TIPOS_MODELO)}.")
        self.tipo = chave
        self.nos: dict = {}
        self.barras: dict = {}
        self.apoios: dict = {}   # id nó -> set de índices restritos
        self.molas: dict = {}    # id nó -> {índice: rigidez}

    @property
    def graus_ativos(self) -> tuple:
        return TIPOS_MODELO[self.tipo]

    def no(self, id, x_cm: float, y_cm: float, z_cm: float = 0.0) -> No:
        """Cria o nó ``id`` nas coordenadas dadas, cm."""
        if id in self.nos:
            raise ValueError(f"Nó {id!r} já existe.")
        if self.tipo in _TIPOS_PLANOS and abs(z_cm) > 0.0:
            raise ValueError(f"Nó {id!r}: o modelo {self.tipo} fica no plano XY (z = 0).")
        n = No(id, float(x_cm), float(y_cm), float(z_cm))
        self.nos[id] = n
        return n

    def barra(self, id, no_i, no_j, secao: Secao, material: Material,
              liberacoes_i=(), liberacoes_j=(), trecho_rigido_i_cm: float = 0.0,
              trecho_rigido_j_cm: float = 0.0, cisalhamento: bool = False,
              elemento_parede: bool = False, fator_EI: float = 1.0, fator_GJ: float = 1.0,
              trelica: bool = False, vetor_ref=None) -> Barra:
        """Cria a barra ``id`` do nó ``no_i`` ao ``no_j`` (ver ``Barra``)."""
        if id in self.barras:
            raise ValueError(f"Barra {id!r} já existe.")
        for n in (no_i, no_j):
            if n not in self.nos:
                raise ValueError(f"Barra {id!r}: nó {n!r} não existe.")
        if no_i == no_j:
            raise ValueError(f"Barra {id!r}: nós inicial e final iguais.")
        L = float(np.linalg.norm(self.nos[no_j].xyz - self.nos[no_i].xyz))
        if L <= 0.0:
            raise ValueError(f"Barra {id!r} com comprimento nulo.")
        if trecho_rigido_i_cm < 0.0 or trecho_rigido_j_cm < 0.0:
            raise FaixaNormativaError(f"Barra {id!r}: trecho rígido negativo.")
        if trecho_rigido_i_cm + trecho_rigido_j_cm >= L:
            raise FaixaNormativaError(
                f"Barra {id!r}: os trechos rígidos ({_fmt(trecho_rigido_i_cm)} + "
                f"{_fmt(trecho_rigido_j_cm)} cm) ocupam todo o comprimento ({_fmt(L)} cm).")
        if elemento_parede and not cisalhamento:
            raise FaixaNormativaError(
                f"Barra {id!r}: viga-parede ou pilar-parede representado por elemento linear "
                "exige a deformação por cisalhamento (14.8.1); use cisalhamento=True.")
        if fator_EI <= 0.0 or fator_GJ < 0.0:
            raise FaixaNormativaError(f"Barra {id!r}: fator_EI tem de ser > 0 e fator_GJ ≥ 0.")
        trelica = bool(trelica) or self.tipo in _TIPOS_TRELICA
        if not trelica and self.tipo not in _TIPOS_TRELICA:
            if self.tipo == "portico_plano" and secao.I_cm4 <= 0.0:
                raise FaixaNormativaError(f"Barra {id!r}: I = 0 no pórtico plano.")
            if self.tipo in ("grelha", "portico_espacial") and secao.I_cm4 <= 0.0:
                raise FaixaNormativaError(f"Barra {id!r}: I = 0.")
            if self.tipo == "portico_espacial" and secao.I2_cm4 <= 0.0:
                raise FaixaNormativaError(f"Barra {id!r}: I2 = 0 no pórtico espacial.")
        if vetor_ref is not None:
            if self.tipo != "portico_espacial":
                raise ValueError("vetor_ref só se aplica ao pórtico espacial.")
            vetor_ref = tuple(float(v) for v in vetor_ref)
            _eixos_locais(self.nos[no_i].xyz, self.nos[no_j].xyz, vetor_ref)   # valida
        b = Barra(id, no_i, no_j, secao, material,
                  _normalizar_liberacoes(liberacoes_i), _normalizar_liberacoes(liberacoes_j),
                  float(trecho_rigido_i_cm), float(trecho_rigido_j_cm), bool(cisalhamento),
                  bool(elemento_parede), float(fator_EI), float(fator_GJ), trelica, vetor_ref)
        if "rx" in b.liberacoes_i and "rx" in b.liberacoes_j and not trelica:
            raise ValueError(f"Barra {id!r}: torção liberada nas duas extremidades forma mecanismo.")
        self.barras[id] = b
        return b

    def apoio(self, no, *graus, molas: dict | None = None) -> None:
        """Restringe graus do nó (apoio rígido) e/ou põe molas.

        graus: 'ux', 'uy', 'uz', 'rx', 'ry', 'rz', ou os atalhos 'engaste'
        (todos os graus ativos) e 'fixo' (todas as translações ativas).
        molas: {grau: rigidez}, em kN/cm ou kN·cm/rad (apoio elástico).
        Graus fora do tipo de modelo são ignorados nos atalhos e levantam erro
        quando nomeados.
        """
        if no not in self.nos:
            raise ValueError(f"Apoio: nó {no!r} não existe.")
        restr = self.apoios.setdefault(no, set())
        for g in graus:
            chave = nbr._chave(g)
            if chave == "engaste":
                restr.update(self.graus_ativos)
            elif chave in ("fixo", "rotula", "articulado"):
                restr.update(i for i in self.graus_ativos if i < 3)
            elif chave in _IDX:
                i = _IDX[chave]
                if i not in self.graus_ativos:
                    raise ValueError(f"Grau {g!r} não existe no modelo {self.tipo}.")
                restr.add(i)
            else:
                raise ValueError(f"Grau {g!r} inválido.")
        for g, k in (molas or {}).items():
            chave = nbr._chave(g)
            if chave not in _IDX or _IDX[chave] not in self.graus_ativos:
                raise ValueError(f"Mola no grau {g!r} inválida para o modelo {self.tipo}.")
            if k <= 0.0:
                raise FaixaNormativaError(f"Rigidez de mola {_fmt(k)} tem de ser positiva.")
            if _IDX[chave] in restr:
                raise ValueError(f"Nó {no!r}: grau {chave} já é restrito; não cabe mola.")
            self.molas.setdefault(no, {})[_IDX[chave]] = float(k)
        for i in restr:
            if i in self.molas.get(no, {}):
                raise ValueError(f"Nó {no!r}: grau {GRAUS[i]} tem mola e apoio rígido.")


# ---------------------------------------------------------------------------
# Casos de carga
# ---------------------------------------------------------------------------
_DIRECOES = {"x": ("l", 0), "y": ("l", 1), "z": ("l", 2),
             "X": ("g", 0), "Y": ("g", 1), "Z": ("g", 2)}


def _direcao(d: str) -> tuple:
    if d not in _DIRECOES:
        raise ValueError(f"Direção {d!r} inválida: use 'x', 'y', 'z' (locais) ou 'X', 'Y', 'Z' (globais).")
    return _DIRECOES[d]


class CasoCarga:
    """Caso de carga: cargas nodais, cargas nas barras, temperatura e
    deslocamento imposto de apoio.

    Os valores entram já como o valor característico (ou representativo)
    da ação; a combinação é do P4 (``acoes_nbr6118``), por superposição dos
    resultados.
    """

    def __init__(self, nome: str = "caso"):
        self.nome = nome
        self.nodais: list = []        # (no, vetor 6)
        self.barra_cargas: list = []  # (barra, tipo, dados)
        self.temperaturas: list = []  # (barra, dtu, dtf, h, plano)
        self.recalques: dict = {}     # no -> {idx: valor}

    def nodal(self, no, Fx: float = 0.0, Fy: float = 0.0, Fz: float = 0.0,
              Mx: float = 0.0, My: float = 0.0, Mz: float = 0.0) -> "CasoCarga":
        """Força (kN) e momento (kN·cm) no nó, eixos globais."""
        self.nodais.append((no, np.array([Fx, Fy, Fz, Mx, My, Mz], dtype=float)))
        return self

    def distribuida(self, barra, q_kn_m: float, q2_kn_m: float | None = None,
                    direcao: str = "y", a_cm: float = 0.0, b_cm: float | None = None) -> "CasoCarga":
        """Carga distribuída uniforme (q2 = None) ou trapezoidal, kN/m, por
        unidade de comprimento da barra, de a_cm a b_cm (medidos do nó
        inicial; b_cm = None vai até o nó final). ``direcao``: 'x', 'y', 'z'
        locais ou 'X', 'Y', 'Z' globais. A parte sobre trecho rígido vai
        direto ao nó."""
        q2 = q_kn_m if q2_kn_m is None else q2_kn_m
        self.barra_cargas.append((barra, "dist", (_direcao(direcao), float(a_cm),
                                                  None if b_cm is None else float(b_cm),
                                                  q_kn_m / 100.0, q2 / 100.0)))
        return self

    def concentrada(self, barra, a_cm: float, P_kn: float, direcao: str = "y") -> "CasoCarga":
        """Força concentrada na barra, kN, a a_cm do nó inicial."""
        self.barra_cargas.append((barra, "conc", (_direcao(direcao), float(a_cm), float(P_kn))))
        return self

    def momento_concentrado(self, barra, a_cm: float, M_kncm: float, eixo: str = "z") -> "CasoCarga":
        """Momento concentrado na barra, kN·cm, em torno do eixo dado
        ('x', 'y', 'z' locais ou 'X', 'Y', 'Z' globais)."""
        self.barra_cargas.append((barra, "mom", (_direcao(eixo), float(a_cm), float(M_kncm))))
        return self

    def temperatura(self, barra, delta_t_uniforme_c: float = 0.0, delta_t_faces_c: float = 0.0,
                    altura_cm: float | None = None, plano: str = "principal") -> "CasoCarga":
        """Variação de temperatura na parte flexível da barra (11.4.2).

        delta_t_uniforme_c: variação uniforme, °C (11.4.2.1; valor de
        ``acoes_nbr6118.variacao_temperatura_adotada_c``).
        delta_t_faces_c: T(face do eixo local positivo) − T(face negativa) no
        plano pedido, °C (11.4.2.2; ``acoes_nbr6118.diferenca_temperatura_faces_c``),
        com variação linear na altura ``altura_cm``. plano: 'principal' (o
        do I) ou 'secundario' (o do I2). Curvatura imposta κ0 = −α·ΔT/h.
        """
        if delta_t_faces_c != 0.0 and (altura_cm is None or altura_cm <= 0.0):
            raise FaixaNormativaError("Gradiente térmico exige altura_cm > 0.")
        chave = nbr._chave(plano)
        if chave not in ("principal", "secundario"):
            raise ValueError("plano deve ser 'principal' ou 'secundario'.")
        self.temperaturas.append((barra, float(delta_t_uniforme_c), float(delta_t_faces_c),
                                  altura_cm, chave))
        return self

    def deslocamento_apoio(self, no, **deslocamentos) -> "CasoCarga":
        """Deslocamento imposto de apoio (11.3.3.3, PDF p. 78), cm ou rad.

        Entra o valor característico superior δk,sup, da avaliação
        pessimista da rigidez do material de fundação (quantil de 5 %); o
        inferior é nulo. Todos os deslocamentos de apoio do caso formam uma
        única ação, com o mesmo coeficiente de ponderação (ver
        ``acao_deslocamentos_apoio``). O grau tem de ser restrito no modelo.
        Exemplo: ``caso.deslocamento_apoio(3, uy=-1.0)``.
        """
        d = self.recalques.setdefault(no, {})
        for g, v in deslocamentos.items():
            chave = nbr._chave(g)
            if chave not in _IDX:
                raise ValueError(f"Grau {g!r} inválido.")
            d[_IDX[chave]] = float(v)
        return self


def acao_deslocamentos_apoio(Fk_sup: float, nome: str = "Deslocamentos de apoio"):
    """Ação dos deslocamentos de apoio para a combinação do P4 (11.3.3.3, PDF p. 78).

    Fk_sup: efeito (esforço, reação...) do caso de carga com os valores
    característicos superiores δk,sup de todos os apoios. O valor
    característico inferior é nulo (Fk_inf = 0), e o conjunto é uma única
    ação permanente indireta, coluna de recalques da Tabela 11.1, ponderada
    por um só coeficiente. A norma só manda considerar os deslocamentos de
    apoio quando geram esforços significativos em relação às outras ações
    (estrutura hiperestática e muito rígida); o julgamento é do projetista.
    """
    try:
        import acoes_nbr6118 as ac
    except ModuleNotFoundError:  # importado como pacote
        from dimensionamento import acoes_nbr6118 as ac
    return ac.Acao(nome=nome, natureza="permanente_indireta", tipo="recalque_retracao",
                   Fk=float(Fk_sup), Fk_inf=0.0)


# ---------------------------------------------------------------------------
# Elemento: rigidez local, forças de engastamento, liberações, trecho rígido
# ---------------------------------------------------------------------------
def _eixos_locais(xi: np.ndarray, xj: np.ndarray, vetor_ref=None) -> np.ndarray:
    ex = (xj - xi) / np.linalg.norm(xj - xi)
    if vetor_ref is None:
        ref = np.array([0.0, 0.0, 1.0])
        if np.linalg.norm(np.cross(ex, ref)) < 1e-9:
            ref = np.array([1.0, 0.0, 0.0])
    else:
        ref = np.asarray(vetor_ref, dtype=float)
    ez = ref - np.dot(ref, ex) * ex
    nz = np.linalg.norm(ez)
    if nz < 1e-9:
        raise ValueError("vetor_ref paralelo ao eixo da barra.")
    ez /= nz
    ey = np.cross(ez, ex)
    return np.vstack([ex, ey, ez])


def _rigidez_local(L, EA, GJ, EIz, EIy, GAy, GAz) -> np.ndarray:
    """Matriz 12×12 do elemento de pórtico espacial (Timoshenko quando GA
    é finito; GA = None dá Euler-Bernoulli)."""
    k = np.zeros((12, 12))
    k[0, 0] = k[6, 6] = EA / L
    k[0, 6] = k[6, 0] = -EA / L
    k[3, 3] = k[9, 9] = GJ / L
    k[3, 9] = k[9, 3] = -GJ / L
    # plano x-y: v (1, 7), θz (5, 11)
    phi = 0.0 if GAy is None else 12.0 * EIz / (GAy * L * L)
    c = EIz / (L ** 3 * (1.0 + phi))
    blk = c * np.array([[12, 6 * L, -12, 6 * L],
                        [6 * L, (4 + phi) * L * L, -6 * L, (2 - phi) * L * L],
                        [-12, -6 * L, 12, -6 * L],
                        [6 * L, (2 - phi) * L * L, -6 * L, (4 + phi) * L * L]])
    idx = [1, 5, 7, 11]
    k[np.ix_(idx, idx)] += blk
    # plano x-z: w (2, 8), θy (4, 10)
    phi = 0.0 if GAz is None else 12.0 * EIy / (GAz * L * L)
    c = EIy / (L ** 3 * (1.0 + phi))
    blk = c * np.array([[12, -6 * L, -12, -6 * L],
                        [-6 * L, (4 + phi) * L * L, 6 * L, (2 - phi) * L * L],
                        [-12, 6 * L, 12, 6 * L],
                        [-6 * L, (2 - phi) * L * L, 6 * L, (4 + phi) * L * L]])
    idx = [2, 4, 8, 10]
    k[np.ix_(idx, idx)] += blk
    return k


def _integrais_trapezio(x, x1, x2, q1, q2):
    """Para a carga linear q(s) de x1 a x2: ∫q ds e ∫q·(s − x) ds sobre
    s em (max(x, x1), x2]. x pode ser vetor."""
    x = np.asarray(x, dtype=float)
    if x2 <= x1:
        z = np.zeros_like(x)
        return z, z
    c1 = (q2 - q1) / (x2 - x1)
    c0 = q1 - c1 * x1
    a = np.maximum(x, x1)
    b = x2
    ativo = a < b
    a = np.where(ativo, a, b)
    I0 = c0 * (b - a) + c1 * (b * b - a * a) / 2.0
    I1 = c0 * (b * b - a * a) / 2.0 + c1 * (b ** 3 - a ** 3) / 3.0
    return I0, I1 - x * I0


class _Cargas:
    """Cargas de uma barra na parte flexível, eixos locais, x a partir da face i."""

    def __init__(self):
        self.dist = []    # (comp 0..2, x1, x2, q1, q2)  kN/cm
        self.conc = []    # (comp 0..5, x, valor)        kN ou kN·cm
        self.eps0 = 0.0   # deformação imposta uniforme
        self.kap_y = 0.0  # curvatura imposta no plano x-y (v'')
        self.kap_z = 0.0  # curvatura imposta no plano x-z (w'')

    def quebras(self):
        q = []
        for _, x1, x2, _, _ in self.dist:
            q += [x1, x2]
        q += [x for _, x, _ in self.conc]
        return q

    def direita(self, x, comp_f, comp_m=None, sinal_m=1.0):
        """(F, M): soma das forças comp_f em (x, L] e soma dos momentos em
        torno de x (F·(s − x) + sinal·momentos comp_m)."""
        x = np.asarray(x, dtype=float)
        F = np.zeros_like(x)
        M = np.zeros_like(x)
        for c, x1, x2, q1, q2 in self.dist:
            if c == comp_f:
                i0, i1 = _integrais_trapezio(x, x1, x2, q1, q2)
                F += i0
                M += i1
        for c, s, v in self.conc:
            m = s > x
            if c == comp_f:
                F += np.where(m, v, 0.0)
                M += np.where(m, v * (s - x), 0.0)
            elif comp_m is not None and c == comp_m:
                M += np.where(m, sinal_m * v, 0.0)
        return F, M

    def totais(self, comp_f, comp_m=None, sinal_m=1.0):
        """(ΣF, ΣF·s + sinal·Σmomentos) sobre toda a barra, com s medido de x = 0."""
        F, M = self.direita(np.array([-1e-300]), comp_f, comp_m, sinal_m)
        return float(F[0]), float(M[0])


def _pontos_gauss(L, quebras):
    pts = sorted(set([0.0, L] + [min(max(q, 0.0), L) for q in quebras]))
    xs, ws = [], []
    for a, b in zip(pts[:-1], pts[1:]):
        if b - a <= 0.0:
            continue
        xs.append(0.5 * (b - a) * _GAUSS_X + 0.5 * (a + b))
        ws.append(0.5 * (b - a) * _GAUSS_W)
    return np.concatenate(xs), np.concatenate(ws)


def _forcas_engastamento(L, EA, GJ, EIz, EIy, GAy, GAz, cg: _Cargas) -> np.ndarray:
    """Forças de engastamento perfeito (12, eixos locais, convenção de
    rigidez), pelo método da flexibilidade na barra em balanço (engastada em
    i, livre em j): deslocamentos da ponta pela carga de unidade, anulados
    pelas forças em j; as de i saem do equilíbrio. Exato para carga linear
    por trechos, com ou sem deformação por cisalhamento."""
    xg, wg = _pontos_gauss(L, cg.quebras())
    f = np.zeros(12)

    # Axial
    N0, _ = cg.direita(xg, 0)
    du = float(np.sum(wg * N0)) / EA + cg.eps0 * L
    f[6] = -du * EA / L
    sx, _ = cg.totais(0)
    f[0] = -f[6] - sx

    # Torção
    T0 = np.zeros_like(xg)
    for c, s, v in cg.conc:
        if c == 3:
            T0 += np.where(s > xg, v, 0.0)
    smx = sum(v for c, _, v in cg.conc if c == 3)
    if GJ > 0.0:
        f[9] = -(float(np.sum(wg * T0)) / GJ) * GJ / L
    f[3] = -f[9] - smx

    def plano(comp_f, comp_m, sinal_m, EI, GA, kap):
        V0, M0 = cg.direita(xg, comp_f, comp_m, sinal_m)
        inv_ga = 0.0 if GA is None else 1.0 / GA
        dv = float(np.sum(wg * (M0 * (L - xg) / EI + V0 * inv_ga))) + kap * L * L / 2.0
        dt = float(np.sum(wg * M0)) / EI + kap * L
        flex = np.array([[L ** 3 / (3 * EI) + L * inv_ga, L * L / (2 * EI)],
                         [L * L / (2 * EI), L / EI]])
        Fj = -np.linalg.solve(flex, [dv, dt])
        sF, sM = cg.totais(comp_f, comp_m, sinal_m)
        Fi_v = -Fj[0] - sF
        Fi_m = -(Fj[1] + L * Fj[0] + sM)
        return Fi_v, Fi_m, Fj[0], Fj[1]

    # plano x-y: força y (1), momento z (5)
    a, b, c, d = plano(1, 5, 1.0, EIz, GAy, cg.kap_y)
    f[1], f[5], f[7], f[11] = a, b, c, d
    # plano x-z em variáveis (w, θ' = −θy, M' = −My): força z (2), momento y (4) com sinal −1
    a, b, c, d = plano(2, 4, -1.0, EIy, GAz, cg.kap_z)
    f[2], f[4], f[8], f[10] = a, -b, c, -d
    return f


@dataclass
class _Elemento:
    barra: Barra
    L: float
    Lf: float
    lam: np.ndarray
    k_cond: np.ndarray       # 12×12 local, face a face, já condensada
    T_off: np.ndarray        # face <- nó (12×12 local)
    lib: tuple               # índices locais liberados (0..11)
    k_full: np.ndarray       # 12×12 sem condensação
    props: tuple             # (EA, GJ, EIz, EIy, GAy, GAz)


def _montar_elemento(modelo: Modelo, b: Barra) -> _Elemento:
    xi, xj = modelo.nos[b.no_i].xyz, modelo.nos[b.no_j].xyz
    L = float(np.linalg.norm(xj - xi))
    Lf = L - b.trecho_rigido_i_cm - b.trecho_rigido_j_cm
    lam = _eixos_locais(xi, xj, b.vetor_ref)
    s, m = b.secao, b.material
    E, G = m.E_kncm2, m.G_kncm2
    EA = E * s.A_cm2
    if b.trelica:
        GJ, EIz, EIy, GAy, GAz = 0.0, 1.0, 1.0, None, None
        lib = (4, 5, 10, 11)
    else:
        GJ = G * s.J_cm4 * b.fator_GJ
        if modelo.tipo == "portico_plano":
            Iz, Iy, Avy, Avz = s.I_cm4, s.I2_cm4, s.Av_efetiva_cm2, s.Av2_efetiva_cm2
        else:
            Iy, Iz, Avz, Avy = s.I_cm4, s.I2_cm4, s.Av_efetiva_cm2, s.Av2_efetiva_cm2
        EIz = E * Iz * b.fator_EI
        EIy = E * Iy * b.fator_EI
        # plano inativo sem inércia: valor simbólico (os graus estão travados)
        if EIz <= 0.0:
            EIz = 1.0
        if EIy <= 0.0:
            EIy = 1.0
        GAy = G * Avy if b.cisalhamento else None
        GAz = G * Avz if b.cisalhamento else None
        lib = tuple([_IDX[g] for g in b.liberacoes_i] + [6 + _IDX[g] for g in b.liberacoes_j])
    k = _rigidez_local(Lf, EA, GJ, EIz, EIy, GAy, GAz)
    kc = _condensar_k(k, lib)
    if b.trelica:
        for i in (1, 2, 7, 8):
            kc[i, :] = 0.0
            kc[:, i] = 0.0
    T = np.eye(12)
    ai, aj = b.trecho_rigido_i_cm, b.trecho_rigido_j_cm
    T[1, 5] += ai
    T[2, 4] -= ai
    T[7, 11] -= aj
    T[8, 10] += aj
    return _Elemento(b, L, Lf, lam, kc, T, lib, k, (EA, GJ, EIz, EIy, GAy, GAz))


def _condensar_k(k, lib):
    if not lib:
        return k.copy()
    c = list(lib)
    r = [i for i in range(12) if i not in lib]
    kc = np.zeros((12, 12))
    kcc = k[np.ix_(c, c)]
    kc[np.ix_(r, r)] = k[np.ix_(r, r)] - k[np.ix_(r, c)] @ np.linalg.solve(kcc, k[np.ix_(c, r)])
    return kc


def _condensar_f(k, f, lib):
    if not lib:
        return f.copy()
    c = list(lib)
    r = [i for i in range(12) if i not in lib]
    fc = np.zeros(12)
    fc[r] = f[r] - k[np.ix_(r, c)] @ np.linalg.solve(k[np.ix_(c, c)], f[c])
    return fc


def _T12(lam):
    T = np.zeros((12, 12))
    for i in range(4):
        T[3 * i:3 * i + 3, 3 * i:3 * i + 3] = lam
    return T


def _carga_local(el: _Elemento, direcao, valor):
    """Componentes locais (3) de um valor numa direção local ou global."""
    tipo, i = direcao
    if tipo == "l":
        v = np.zeros(3)
        v[i] = valor
        return v
    g = np.zeros(3)
    g[i] = valor
    return el.lam @ g


def _processar_cargas(modelo: Modelo, el: _Elemento, cargas_barra, temps):
    b = el.barra
    L, ai, aj = el.L, b.trecho_rigido_i_cm, b.trecho_rigido_j_cm
    Lf = el.Lf
    xi = modelo.nos[b.no_i].xyz
    lam = el.lam
    cg = _Cargas()
    f_rig = np.zeros(12)
    res = np.zeros(6)

    def no_do_trecho(s):
        """(deslocamento do vetor, abscissa do nó) do trecho rígido que contém s."""
        return (0, 0.0) if s <= ai + 1e-12 else (6, L)

    def rigido(o, F, Im):
        # resultante F (3, local) e ∫q·(s − s_nó) (momento de braço) vão ao nó:
        # momento = ex × F·braço = (0, −Fz, Fy)·braço
        f_rig[o:o + 3] -= F
        f_rig[o + 3:o + 6] -= np.array([0.0, -F[2], F[1]]) * Im

    for tipo, dados in cargas_barra:
        if tipo == "dist":
            direcao, a, bb, q1, q2 = dados
            bb = L if bb is None else bb
            if not (0.0 <= a < bb <= L + 1e-9):
                raise ValueError(f"Barra {b.id!r}: carga distribuída fora da barra (a = {_fmt(a)}, "
                                 f"b = {_fmt(bb)}, L = {_fmt(L)} cm).")
            bb = min(bb, L)
            vloc = _carga_local(el, direcao, 1.0)

            def q_em(s):
                return q1 + (q2 - q1) * (s - a) / (bb - a)

            # resultante global: ∫q ds · d e ∫q·(xi + s·ex) × d ds
            i0 = (q1 + q2) / 2.0 * (bb - a)
            i1 = float(_integrais_trapezio(np.array([0.0]), a, bb, q1, q2)[1][0])
            dg = lam.T @ vloc
            res[:3] += i0 * dg
            res[3:] += np.cross(xi, dg) * i0 + np.cross(lam[0], dg) * i1
            for z0, z1, flex in ((0.0, ai, False), (ai, L - aj, True), (L - aj, L, False)):
                s0, s1 = max(a, z0), min(bb, z1)
                if s1 - s0 <= 1e-12:
                    continue
                qa, qb = q_em(s0), q_em(s1)
                if flex:
                    for c in range(3):
                        if vloc[c] != 0.0:
                            cg.dist.append((c, s0 - ai, s1 - ai, qa * vloc[c], qb * vloc[c]))
                else:
                    o, s_no = no_do_trecho(0.5 * (s0 + s1))
                    I0, Ia = _integrais_trapezio(np.array([s0]), s0, s1, qa, qb)
                    I0, Ia = float(I0[0]), float(Ia[0])
                    Im = Ia + (s0 - s_no) * I0     # ∫q·(s − s_nó) ds
                    rigido(o, I0 * vloc, Im / I0 if I0 != 0.0 else 0.0)
                    if I0 == 0.0:   # triângulos opostos: resultante nula, só o binário
                        f_rig[o + 3:o + 6] -= np.array([0.0, -vloc[2], vloc[1]]) * Im
        elif tipo in ("conc", "mom"):
            direcao, s, v = dados
            if not (0.0 <= s <= L + 1e-9):
                raise ValueError(f"Barra {b.id!r}: carga concentrada fora da barra (a = {_fmt(s)} cm).")
            vloc = _carga_local(el, direcao, v)
            dg = lam.T @ vloc
            if tipo == "conc":
                res[:3] += dg
                res[3:] += np.cross(xi + s * lam[0], dg)
            else:
                res[3:] += dg
            if ai - 1e-12 <= s <= L - aj + 1e-12:
                off = 0 if tipo == "conc" else 3
                for c in range(3):
                    if vloc[c] != 0.0:
                        cg.conc.append((off + c, min(max(s - ai, 0.0), Lf), vloc[c]))
            else:
                o, s_no = no_do_trecho(s)
                if tipo == "conc":
                    rigido(o, vloc, s - s_no)
                else:
                    f_rig[o + 3:o + 6] -= vloc
        else:  # pragma: no cover
            raise ValueError(tipo)

    principal = "y" if modelo.tipo == "portico_plano" else "z"
    for dtu, dtf, h, plano in temps:
        cg.eps0 += b.material.alfa_termico * dtu
        if dtf != 0.0:
            kap = -b.material.alfa_termico * dtf / h
            eixo = principal if plano == "principal" else ("z" if principal == "y" else "y")
            if eixo == "y":
                cg.kap_y += kap
            else:
                cg.kap_z += kap
    return cg, f_rig, res


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------
_ESFORCOS = ("N", "Vy", "Vz", "T", "My", "Mz")


@dataclass(frozen=True)
class ResultadoBarra:
    """Esforços de uma barra (convenção no cabeçalho do módulo).

    x_cm: estações ao longo da parte flexível, a partir da face i.
    esforcos: {'N', 'Vy', 'Vz', 'T', 'My', 'Mz'} -> vetor nas estações.
    extremidade_i, extremidade_j: esforços nas faces (dict).
    forcas_nos_local: forças que os nós aplicam na barra (12, eixos locais,
    no nó, convenção de rigidez).
    plano_principal: 'y' (pórtico plano) ou 'z' (grelha e espacial).
    """

    id: object
    L_cm: float
    L_flexivel_cm: float
    trecho_rigido_i_cm: float
    x_cm: np.ndarray
    esforcos: dict
    extremidade_i: dict
    extremidade_j: dict
    forcas_nos_local: np.ndarray
    plano_principal: str
    _Fj: np.ndarray = field(repr=False, default=None)
    _cargas: object = field(repr=False, default=None)

    def em(self, x_cm: float) -> dict:
        """Esforços na seção x_cm (a partir da face i da parte flexível)."""
        x = float(x_cm)
        if not (-1e-9 <= x <= self.L_flexivel_cm + 1e-9):
            raise ValueError(f"x = {_fmt(x)} cm fora da parte flexível (0 a {_fmt(self.L_flexivel_cm)} cm).")
        v = _esforcos_em(np.array([x]), self.L_flexivel_cm, self._Fj, self._cargas)
        return {k: float(a[0]) for k, a in v.items()}

    @property
    def M(self) -> np.ndarray:
        """Momento do plano principal (Mz no pórtico plano; My na grelha e no espacial)."""
        return self.esforcos["Mz" if self.plano_principal == "y" else "My"]

    @property
    def V(self) -> np.ndarray:
        """Cortante do plano principal (Vy no pórtico plano; Vz na grelha e no espacial)."""
        return self.esforcos["Vy" if self.plano_principal == "y" else "Vz"]

    @property
    def N(self) -> np.ndarray:
        return self.esforcos["N"]


def _esforcos_em(x, Lf, Fj, cg: _Cargas) -> dict:
    Nx, _ = cg.direita(x, 0)
    Fy, My_ = cg.direita(x, 1, 5, 1.0)
    Fz, Mz_ = cg.direita(x, 2, 4, -1.0)
    T = np.zeros_like(x)
    for c, s, v in cg.conc:
        if c == 3:
            T += np.where(s > x, v, 0.0)
    return {
        "N": Fj[6] + Nx,
        "Vy": -(Fj[7] + Fy),
        "Vz": -(Fj[8] + Fz),
        "T": Fj[9] + T,
        "My": -Fj[10] + Fj[8] * (Lf - x) + Mz_,
        "Mz": Fj[11] + Fj[7] * (Lf - x) + My_,
    }


@dataclass(frozen=True)
class ResultadoAnalise:
    """Resultado de ``resolver`` para um caso de carga.

    deslocamentos: {nó: {grau: valor}} (cm, rad) nos graus ativos.
    reacoes: {nó: {grau: valor}} (kN, kN·cm), eixos globais, nos graus
    restritos e nas molas. barras: {id: ResultadoBarra}.
    soma_cargas, soma_reacoes: resultante (Fx, Fy, Fz, Mx, My, Mz) em torno
    da origem. erro_equilibrio: resíduo relativo da conferência.

    Deslocamento com seção bruta não é flecha de verificação: para flecha,
    a fissuração e a fluência são obrigatórias (14.6.4.1, 17.3.2.1; P8).
    """

    tipo: str
    caso: str
    deslocamentos: dict
    reacoes: dict
    barras: dict
    soma_cargas: tuple
    soma_reacoes: tuple
    erro_equilibrio: float
    equilibrio_ok: bool
    memoria: tuple


def _verificar_equilibrio(soma_cargas, soma_reacoes, escala_f, escala_m, tol=TOL_EQUILIBRIO):
    """Confere ΣF + ΣR = 0 em forças e momentos; levanta ``ErroEquilibrio``."""
    sc, sr = np.asarray(soma_cargas, float), np.asarray(soma_reacoes, float)
    d = sc + sr
    ef = float(np.max(np.abs(d[:3]))) / max(escala_f, 1e-12)
    em = float(np.max(np.abs(d[3:]))) / max(escala_m, 1e-12)
    erro = max(ef, em)
    if erro > tol:
        raise ErroEquilibrio(
            f"O equilíbrio não fecha: soma das cargas ({'; '.join(_fmt(float(v)) for v in sc)}) e "
            f"soma das reações ({'; '.join(_fmt(float(v)) for v in sr)}); resíduo relativo "
            f"{_fmt(erro)} > {_fmt(tol)}.")
    return erro


# ---------------------------------------------------------------------------
# Solução — 14.5.2 (p. 105) e 14.6.4.1 (p. 111)
# ---------------------------------------------------------------------------
def resolver(modelo: Modelo, caso: CasoCarga, n_estacoes: int = 11) -> ResultadoAnalise:
    """Análise linear da estrutura de barras pelo método dos deslocamentos
    (14.5.2, PDF p. 105; 14.6.4.1, PDF p. 111).

    Hipóteses da análise linear: comportamento elástico-linear, seção bruta
    de concreto e módulo secante Ecs (8.2.8) com Gc = Ecs/2,4 (8.2.9), salvo
    os ajustes que cada barra declara (fator_EI, fator_GJ, cisalhamento).
    Pequenos deslocamentos (14.5.1): equilíbrio na geometria indeformada.

    Monta a matriz de rigidez esparsa, resolve K·u = P, calcula as reações
    (apoios rígidos, molas e deslocamentos impostos) e os esforços nas
    extremidades e em ``n_estacoes`` estações de cada barra. Confere o
    equilíbrio global (soma das reações igual à soma das cargas, em forças
    e momentos em torno da origem) e o resíduo do sistema; se não fechar,
    levanta ``ErroEquilibrio``. Estrutura hipostática levanta
    ``EstruturaHipostatica``.
    """
    if not modelo.barras:
        raise ValueError("Modelo sem barras.")
    if n_estacoes < 2:
        raise ValueError("n_estacoes tem de ser ≥ 2.")
    ids = list(modelo.nos)
    pos = {n: i for i, n in enumerate(ids)}
    ndof = 6 * len(ids)
    ativos = np.zeros(ndof, dtype=bool)
    for i in range(len(ids)):
        for g in modelo.graus_ativos:
            ativos[6 * i + g] = True

    # cargas por barra
    por_barra = {bid: [] for bid in modelo.barras}
    for bid, tipo, dados in caso.barra_cargas:
        if bid not in modelo.barras:
            raise ValueError(f"Caso {caso.nome!r}: barra {bid!r} não existe.")
        por_barra[bid].append((tipo, dados))
    temps = {bid: [] for bid in modelo.barras}
    for bid, dtu, dtf, h, plano in caso.temperaturas:
        if bid not in modelo.barras:
            raise ValueError(f"Caso {caso.nome!r}: barra {bid!r} não existe.")
        temps[bid].append((dtu, dtf, h, plano))

    linhas, cols, vals = [], [], []
    P = np.zeros(ndof)
    soma_cargas = np.zeros(6)
    info = {}
    for bid, b in modelo.barras.items():
        el = _montar_elemento(modelo, b)
        cg, f_rig, res = _processar_cargas(modelo, el, por_barra[bid], temps[bid])
        EA, GJ, EIz, EIy, GAy, GAz = el.props
        f_face = _forcas_engastamento(el.Lf, EA, GJ, EIz, EIy, GAy, GAz, cg)
        f_face_c = _condensar_f(el.k_full, f_face, el.lib)
        k_no = el.T_off.T @ el.k_cond @ el.T_off
        f_no = el.T_off.T @ f_face_c + f_rig
        T12 = _T12(el.lam)
        kg = T12.T @ k_no @ T12
        fg = T12.T @ f_no
        dofs = np.r_[6 * pos[b.no_i] + np.arange(6), 6 * pos[b.no_j] + np.arange(6)]
        rr, cc = np.meshgrid(dofs, dofs, indexing="ij")
        linhas.append(rr.ravel())
        cols.append(cc.ravel())
        vals.append(kg.ravel())
        P[dofs] -= fg
        soma_cargas += res
        info[bid] = (el, cg, f_face_c, T12, dofs, f_rig)

    for no, v in caso.nodais:
        if no not in pos:
            raise ValueError(f"Caso {caso.nome!r}: nó {no!r} não existe.")
        P[6 * pos[no]:6 * pos[no] + 6] += v
        soma_cargas[:3] += v[:3]
        soma_cargas[3:] += v[3:] + np.cross(modelo.nos[no].xyz, v[:3])

    escala_P = max(float(np.max(np.abs(P))), 1e-300)
    fora = ~ativos & (np.abs(P) > 1e-9 * escala_P)
    if np.any(fora):
        i = int(np.argmax(fora))
        raise ValueError(
            f"Caso {caso.nome!r}: carga fora do plano do modelo {modelo.tipo} (nó {ids[i // 6]!r}, "
            f"grau {GRAUS[i % 6]}).")

    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(linhas), np.concatenate(cols))),
                      shape=(ndof, ndof)).tocsr()
    kmola = np.zeros(ndof)
    for no, d in modelo.molas.items():
        for g, k in d.items():
            kmola[6 * pos[no] + g] = k
    restr = np.zeros(ndof, dtype=bool)
    for no, s in modelo.apoios.items():
        for g in s:
            restr[6 * pos[no] + g] = True
    u = np.zeros(ndof)
    for no, d in caso.recalques.items():
        if no not in pos:
            raise ValueError(f"Caso {caso.nome!r}: nó {no!r} não existe.")
        for g, v in d.items():
            if not restr[6 * pos[no] + g]:
                raise ValueError(
                    f"Deslocamento imposto no nó {no!r}, grau {GRAUS[g]}, que não é restrito "
                    "(11.3.3.3 aplica o deslocamento a um apoio).")
            u[6 * pos[no] + g] = v

    diag = K.diagonal() + kmola
    livres = ativos & ~restr
    escala_k = max(float(np.max(np.abs(diag[ativos]))), 1e-300)
    sem_rigidez = livres & (np.abs(diag) <= 1e-12 * escala_k)
    if np.any(sem_rigidez & (np.abs(P) > 1e-9 * escala_P)):
        i = int(np.argmax(sem_rigidez & (np.abs(P) > 1e-9 * escala_P)))
        raise EstruturaHipostatica(
            f"Grau {GRAUS[i % 6]} do nó {ids[i // 6]!r} carregado e sem rigidez.")
    livres &= ~sem_rigidez
    f_idx = np.flatnonzero(livres)
    s_idx = np.flatnonzero(ativos & ~livres)
    Kt = K + sp.diags(kmola)
    if f_idx.size:
        Kff = Kt[f_idx][:, f_idx].tocsc()
        rhs = P[f_idx] - Kt[f_idx][:, s_idx] @ u[s_idx]
        try:
            lu = spla.splu(Kff)
        except RuntimeError as exc:
            raise EstruturaHipostatica(
                "Matriz de rigidez singular: estrutura hipostática (mecanismo).") from exc
        dU = np.abs(lu.U.diagonal())
        if dU.size and float(np.min(dU)) <= 1e-11 * float(np.max(dU)):
            raise EstruturaHipostatica(
                "Matriz de rigidez singular: estrutura hipostática (mecanismo).")
        u[f_idx] = lu.solve(rhs)
        residuo = float(np.max(np.abs(Kff @ u[f_idx] - rhs))) if rhs.size else 0.0
        if residuo > 1e-6 * max(float(np.max(np.abs(rhs))), escala_k * float(np.max(np.abs(u))), 1e-300):
            raise ErroEquilibrio(f"Resíduo do sistema K·u = P alto ({residuo:.3e}).")

    Ku = K @ u
    R = np.zeros(ndof)
    R[restr] = Ku[restr] - P[restr]
    R[kmola > 0] = -kmola[kmola > 0] * u[kmola > 0]

    soma_reacoes = np.zeros(6)
    reacoes = {}
    for no in ids:
        i = pos[no]
        r = R[6 * i:6 * i + 6]
        graus = [g for g in modelo.graus_ativos if restr[6 * i + g] or kmola[6 * i + g] > 0]
        if graus:
            reacoes[no] = {GRAUS[g]: float(r[g]) for g in graus}
        soma_reacoes[:3] += r[:3]
        soma_reacoes[3:] += r[3:] + np.cross(modelo.nos[no].xyz, r[:3])

    # escala da conferência: forças e momentos (divididos pela maior dimensão)
    # das cargas nodais equivalentes e das reações
    dim = max((float(np.max(np.abs(n.xyz))) for n in modelo.nos.values()), default=1.0)
    dim = max(dim, max(el.L for el, *_ in info.values()))
    e_f = np.arange(ndof) % 6 < 3
    escala_f = (float(np.sum(np.abs(R[e_f])) + np.sum(np.abs(P[e_f])))
                + float(np.sum(np.abs(R[~e_f])) + np.sum(np.abs(P[~e_f]))) / dim)
    if escala_f == 0.0:
        erro = 0.0
    else:
        erro = _verificar_equilibrio(soma_cargas, soma_reacoes, escala_f, escala_f * dim)

    desloc = {no: {GRAUS[g]: float(u[6 * pos[no] + g]) for g in modelo.graus_ativos} for no in ids}

    barras = {}
    for bid, (el, cg, f_face_c, T12, dofs, f_rig) in info.items():
        b = el.barra
        u_loc_no = T12 @ u[dofs]
        u_face = el.T_off @ u_loc_no
        F_face = el.k_cond @ u_face + f_face_c
        F_no = el.T_off.T @ F_face + f_rig
        x = np.linspace(0.0, el.Lf, n_estacoes)
        esf = _esforcos_em(x, el.Lf, F_face, cg)
        Fi = F_face
        ext_i = {"N": -Fi[0], "Vy": Fi[1], "Vz": Fi[2], "T": -Fi[3], "My": Fi[4], "Mz": -Fi[5]}
        ext_j = {"N": Fi[6], "Vy": -Fi[7], "Vz": -Fi[8], "T": Fi[9], "My": -Fi[10], "Mz": Fi[11]}
        barras[bid] = ResultadoBarra(
            id=bid, L_cm=el.L, L_flexivel_cm=el.Lf, trecho_rigido_i_cm=b.trecho_rigido_i_cm,
            x_cm=x, esforcos=esf, extremidade_i={k: float(v) for k, v in ext_i.items()},
            extremidade_j={k: float(v) for k, v in ext_j.items()}, forcas_nos_local=F_no,
            plano_principal="y" if modelo.tipo == "portico_plano" else "z",
            _Fj=F_face.copy(), _cargas=cg)

    mat = {b.material.descricao for b in modelo.barras.values() if b.material.descricao}
    memoria = [
        f"Análise linear (14.5.2, p. 105) do modelo {modelo.tipo}, caso {caso.nome!r}: "
        f"{len(ids)} nó(s), {len(modelo.barras)} barra(s), {int(f_idx.size)} grau(s) livre(s).",
        "Hipóteses: comportamento elástico-linear, seção bruta e módulo secante Ecs "
        "(14.5.2 e 14.6.4.1, p. 111), salvo os ajustes declarados em cada barra.",
    ]
    memoria += sorted(mat)
    if any(b.cisalhamento for b in modelo.barras.values()):
        memoria.append("Barras com deformação por cisalhamento (Timoshenko), como pede 14.8.1 para "
                       "viga-parede e pilar-parede representados por elemento linear (p. 119).")
    if caso.recalques:
        memoria.append("Deslocamentos impostos de apoio com os valores característicos superiores "
                       "δk,sup (11.3.3.3, p. 78); o inferior é nulo.")
    memoria.append(
        f"Equilíbrio: ΣF das cargas = ({', '.join(_fmt(v) for v in soma_cargas[:3])}) kN; "
        f"ΣF das reações = ({', '.join(_fmt(v) for v in soma_reacoes[:3])}) kN; "
        f"resíduo relativo {_fmt(erro)}.")
    memoria.append("Deslocamentos com seção bruta: a flecha de verificação exige fissuração e "
                   "fluência (14.6.4.1, 17.3.2.1).")
    return ResultadoAnalise(
        tipo=modelo.tipo, caso=caso.nome, deslocamentos=desloc, reacoes=reacoes, barras=barras,
        soma_cargas=tuple(float(v) for v in soma_cargas),
        soma_reacoes=tuple(float(v) for v in soma_reacoes),
        erro_equilibrio=float(erro), equilibrio_ok=True, memoria=tuple(memoria))


# ---------------------------------------------------------------------------
# 11.4.1.1 — Posições mais desfavoráveis das cargas de utilização (p. 81-82)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EnvoltoriaBarra:
    x_cm: np.ndarray
    maximo: dict
    minimo: dict


@dataclass(frozen=True)
class ResultadoAlternancia:
    """Envoltória das cargas variáveis nas posições mais desfavoráveis.

    envoltoria: {barra: EnvoltoriaBarra} com máximo e mínimo de cada esforço
    nas estações. reacoes_max, reacoes_min: {nó: {grau: valor}}.
    dispensada: True quando 14.6.6.3 dispensa a alternância (todas as
    variáveis aplicadas juntas). n_arranjos: número de parcelas
    independentes superpostas.
    """

    envoltoria: dict
    reacoes_max: dict
    reacoes_min: dict
    dispensada: bool
    n_arranjos: int
    ok: bool
    governante: str
    memoria: tuple


def alternancia_cargas(modelo: Modelo, caso_q: CasoCarga, caso_g: CasoCarga | None = None,
                       grupos: Iterable[Iterable] | None = None,
                       q_kn_m2: float | None = None, g_kn_m2: float | None = None,
                       n_estacoes: int = 11) -> ResultadoAlternancia:
    """Cargas variáveis de utilização nas posições mais desfavoráveis, com a
    envoltória (11.4.1.1, PDF p. 81-82).

    O caso ``caso_q`` é repartido em parcelas independentes: as cargas de
    cada grupo de barras (padrão: cada barra carregada, isto é, vão a vão
    quando cada vão é uma barra; ``grupos`` agrupa barras de um mesmo vão) e
    cada carga nodal. Por superposição linear, o máximo de cada esforço em
    cada estação soma as parcelas positivas e o mínimo as negativas, o que
    equivale a escolher, para cada efeito, o arranjo mais desfavorável de
    vãos carregados. ``caso_g`` (opcional) é somado a tudo.

    Dispensa (14.6.6.3, PDF p. 115, via ``analise_linear_nbr6118.
    dispensa_alternancia_cargas``, P14): com q_kn_m2 e g_kn_m2 informados e
    q ≤ 5 kN/m² e q ≤ 0,5·(g + q), a alternância é dispensada, e a
    envoltória usa todas as variáveis juntas.

    caso_q só pode ter cargas nodais e de barra (temperatura e deslocamento
    de apoio não são cargas de utilização).
    """
    if caso_q.temperaturas or caso_q.recalques:
        raise ValueError("caso_q só admite cargas nodais e de barra (11.4.1.1).")
    try:
        import analise_linear_nbr6118 as al
    except ModuleNotFoundError:  # importado como pacote
        from dimensionamento import analise_linear_nbr6118 as al

    memoria = []
    dispensada = False
    if q_kn_m2 is not None and g_kn_m2 is not None:
        dispensada = al.dispensa_alternancia_cargas(q_kn_m2, g_kn_m2)
        memoria.append(
            f"14.6.6.3 (p. 115): q = {_fmt(q_kn_m2)} kN/m² e g + q = {_fmt(q_kn_m2 + g_kn_m2)} kN/m²: "
            + ("q ≤ 5 kN/m² e q ≤ 0,5·(g + q), alternância dispensada."
               if dispensada else "a alternância de cargas é obrigatória."))

    # parcelas
    carregadas = []
    for bid, _, _ in caso_q.barra_cargas:
        if bid not in carregadas:
            carregadas.append(bid)
    if grupos is None:
        grupos_l = [[bid] for bid in carregadas]
    else:
        grupos_l = [list(g) for g in grupos]
        cobertas = {b for g in grupos_l for b in g}
        for bid in carregadas:
            if bid not in cobertas:
                grupos_l.append([bid])
    parcelas = []
    for g in grupos_l:
        c = CasoCarga(f"{caso_q.nome} [{', '.join(str(b) for b in g)}]")
        c.barra_cargas = [item for item in caso_q.barra_cargas if item[0] in g]
        if c.barra_cargas:
            parcelas.append(c)
    for no, v in caso_q.nodais:
        c = CasoCarga(f"{caso_q.nome} [nó {no}]")
        c.nodais = [(no, v)]
        parcelas.append(c)
    if not parcelas:
        raise ValueError("caso_q sem cargas.")

    res_q = [resolver(modelo, c, n_estacoes) for c in parcelas]
    res_g = resolver(modelo, caso_g, n_estacoes) if caso_g is not None else None

    envoltoria = {}
    for bid in modelo.barras:
        base = res_g.barras[bid].esforcos if res_g else None
        x = res_q[0].barras[bid].x_cm
        mx, mn = {}, {}
        for e in _ESFORCOS:
            b0 = base[e] if base is not None else np.zeros_like(x)
            vs = np.array([r.barras[bid].esforcos[e] for r in res_q])
            if dispensada:
                tot = b0 + vs.sum(axis=0)
                mx[e], mn[e] = tot, tot.copy()
            else:
                mx[e] = b0 + np.clip(vs, 0.0, None).sum(axis=0)
                mn[e] = b0 + np.clip(vs, None, 0.0).sum(axis=0)
        envoltoria[bid] = EnvoltoriaBarra(x, mx, mn)

    reac_max, reac_min = {}, {}
    for no in res_q[0].reacoes:
        reac_max[no], reac_min[no] = {}, {}
        for g in res_q[0].reacoes[no]:
            b0 = res_g.reacoes[no][g] if res_g else 0.0
            vs = np.array([r.reacoes[no][g] for r in res_q])
            if dispensada:
                reac_max[no][g] = reac_min[no][g] = float(b0 + vs.sum())
            else:
                reac_max[no][g] = float(b0 + vs[vs > 0].sum())
                reac_min[no][g] = float(b0 + vs[vs < 0].sum())
    memoria.insert(0, f"11.4.1.1 (p. 81-82): cargas de utilização de {caso_q.nome!r} nas posições "
                      f"mais desfavoráveis, em {len(parcelas)} parcela(s) independente(s) "
                      "superpostas pelo sinal do efeito.")
    if res_g:
        memoria.append(f"Somado o caso permanente {caso_g.nome!r} em todas as envoltórias.")
    return ResultadoAlternancia(envoltoria=envoltoria, reacoes_max=reac_max, reacoes_min=reac_min,
                                dispensada=dispensada, n_arranjos=len(parcelas), ok=True,
                                governante="dispensa 14.6.6.3" if dispensada else "alternância 11.4.1.1",
                                memoria=tuple(memoria))
