"""Flexao Composta Obliqua (NBR 6118:2026).

Verificacao e dimensionamento de pilares retangulares submetidos a Nd,
Mxd e Myd. Metodologia baseada na monografia "PCalc" (Cardoso Jr., 2014)
e no projeto open-source PFOC (Daniel D. Grossmann).

Estrategia:
    - Materiais NBR: parabola-retangulo (concreto, pico 0,85*eta_c*fcd,
      Figura 8.2 e 17.2.2 e), bilinear (aco).
    - Integracao 2D vetorizada (fibras) sobre a secao retangular,
      com strain calculada a partir da posicao da LN inclinada.
    - Solver duplo aninhado:
        * Interno: brentq em x_LN dado alpha, tal que Nc + Ns = Nd.
        * Externo: brentq em alpha tal que a direcao de (MRx, MRy) seja a
          de (Mxd, Myd), COM SINAL: alpha e buscado no circulo inteiro, o
          que vale para secao e armadura assimetricas (17.2.1).
    - Pre-flight: calcula Nd_max (compressao pura, reta b da Figura 17.1) e
      Nd_min (tracao pura); valida Nd antes de chamar solver.
    - Fallback uniaxial: se um momento e nulo, fixa alpha e roda so o
      solver interno (se a secao nao for simetrica em relacao ao plano de
      flexao, cai no solver geral).
    - Diagnostico estruturado: dict com status, x_LN, alpha, residuo.

Convencoes:
    - fck em MPa. Geometria em cm. Forcas em kN, momentos em kN.cm.
    - Coords das barras: cartesianas, centradas no centroide da secao.
    - Mxd em torno do eixo x (causa flexao no plano y). Mxd > 0 comprime +y.
    - Myd em torno do eixo y (causa flexao no plano x). Myd > 0 comprime +x.
    - alpha = angulo (rad) da LN com o eixo x. alpha=0 -> LN horizontal,
      +y comprimido; alpha=pi -> -y comprimido; alpha=-pi/2 -> +x
      comprimido; alpha=+pi/2 -> -x comprimido.
    - Compressao positiva.

Material e parametros da norma: vem do nucleo normativo
(`dimensionamento/nucleo_nbr6118.py`): eta_c, eps_c2, eps_cu, n, fcd, Eci,
fct e a posicao do pivo C. fck fora de 20 a 90 MPa levanta
`FaixaNormativaError` (8.2.1).

Validacoes embutidas:
    - PFOC __main__ (40.3x71.5, Nd=1150, Mdx=8625, Mdy=23000) -> razao=1.29.
    - Quadrada simetrica com Mxd=Myd -> alpha=45 graus, MRx=MRy.
    - Uniaxial (Myd=0): cross-check contra solver interno fixado em alpha=0.
    - NBR 17.2.5 (processo aproximado): deve ser conservador em relacao ao
      numerico.
    - tests/test_fco_nbr2026.py: integrador por fibras independente (C20 a
      C90), secao assimetrica e paridade Python x C++.
"""

from __future__ import annotations

import math
import os
import sys
import warnings
from dataclasses import dataclass, field
from functools import cached_property, lru_cache
from typing import Protocol, runtime_checkable

import numpy as np
from scipy.optimize import brentq

try:  # importado como pacote (dimensionamento.rotinas.xxx)
    from dimensionamento import nucleo_nbr6118 as nbr
except ModuleNotFoundError:  # executado como script: poe dimensionamento/ no sys.path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import nucleo_nbr6118 as nbr


GAMA_C = nbr.GAMA_C
GAMA_S = nbr.GAMA_S
ES_KNCM2 = nbr.ES_MPA / 10.0   # modulo de elasticidade do aco (210 GPa, 8.3.5)
ALPHA_C = 0.85        # coeficiente 0,85 do pico 0,85*eta_c*fcd (Figura 8.2)
EPS_SU = nbr.EPS_SU   # alongamento-limite da armadura no pivo A (Figura 17.1), por mil
GAMA_F3 = nbr.GAMA_F3  # 15.3.1 -- formulacao de seguranca da relacao momento-curvatura
TOL_UNIAXIAL = 1e-6   # |M perpendicular|/|M| abaixo disso = flexao normal


class AvisoNBR6118(UserWarning):
    """Aviso de uso fora do que a NBR 6118:2026 preve (o calculo prossegue)."""


# ---------------------------------------------------------------------------
# Curvas constitutivas do concreto (Protocol + implementacoes plugaveis)
# ---------------------------------------------------------------------------
@runtime_checkable
class CurvaC(Protocol):
    """Modelo constitutivo do concreto.

    Convencoes:
        - eps em "por mil". Compressao positiva, tracao negativa.
        - sigma retornada em kN/cm^2.
        - Vetorizada: aceita np.ndarray e retorna np.ndarray.
    """

    def sigma(self, eps: np.ndarray) -> np.ndarray: ...


@dataclass
class CurvaCParabolaRetangulo:
    """Parabola-retangulo NBR 6118:2026 (compressao apenas; tracao -> 0).

    Curva default para ELU (Figura 8.2): pico alpha_c*eta_c*fcd, com
    alpha_c = 0,85 e eta_c = 1 ate C40 e (40/fck)^(1/3) acima (17.2.2 e).
    Valida para C20 a C90 (n, eps_c2, eps_cu variaveis -- veja Concreto,
    que ja monta a curva com o eta_c do nucleo). Quem montar a curva a mao
    deve passar `eta_c` (o padrao 1,0 so vale ate C40).

    Alem de eps_cu a norma nao define o diagrama; a curva mantem o patamar
    (uso numerico em solvers), como `nucleo_nbr6118.sigma_c`.
    """
    fcd_kncm2: float
    eps_c2_pmilh: float
    eps_cu_pmilh: float
    n_parabola: float
    alpha_c: float = ALPHA_C
    eta_c: float = 1.0

    @property
    def pico_kncm2(self) -> float:
        """Tensao do patamar, alpha_c*eta_c*fcd (kN/cm^2)."""
        return self.alpha_c * self.eta_c * self.fcd_kncm2

    def sigma(self, eps: np.ndarray) -> np.ndarray:
        sigma = np.zeros_like(eps)
        pico = self.pico_kncm2
        mask_par = (eps > 0.0) & (eps <= self.eps_c2_pmilh)
        mask_rect = eps > self.eps_c2_pmilh
        if mask_par.any():
            arg = np.clip(1.0 - eps[mask_par] / self.eps_c2_pmilh, 0.0, 1.0)
            sigma[mask_par] = pico * (1.0 - arg ** self.n_parabola)
        if mask_rect.any():
            sigma[mask_rect] = pico
        return sigma


@dataclass
class CurvaCParabolaRetanguloComTracao:
    """Parabola-retangulo na compressao + ramo linear/branda na tracao.

    Para analises onde a contribuicao da tracao do concreto importa (ELS-W
    no estagio I, validacoes pre-fissuracao). Modelo SECC tipo 2 adaptado:
        Compressao: parabola-retangulo NBR (igual a ParabolaRetangulo,
            pico alpha_c*eta_c*fcd -- passe `eta_c` acima de C40).
        Tracao:
            - Ramo linear de 0 ate -0.9*fctk em eps_ct2 = 0.9*fctk/Eci*1000.
            - Ramo decrescente de -0.9*fctk ate -fctk em -eps_ctu (default 0.15).
    """
    fcd_kncm2: float
    eps_c2_pmilh: float
    eps_cu_pmilh: float
    n_parabola: float
    fctk_kncm2: float
    Eci_kncm2: float
    eps_ctu_pmilh: float = 0.15
    alpha_c: float = ALPHA_C
    eta_c: float = 1.0

    def sigma(self, eps: np.ndarray) -> np.ndarray:
        sigma = np.zeros_like(eps)
        pico = self.alpha_c * self.eta_c * self.fcd_kncm2
        # Compressao: parabola + retangulo (mesmo da ParabolaRetangulo)
        mask_par = (eps > 0.0) & (eps <= self.eps_c2_pmilh)
        mask_rect = eps > self.eps_c2_pmilh
        if mask_par.any():
            arg = np.clip(1.0 - eps[mask_par] / self.eps_c2_pmilh, 0.0, 1.0)
            sigma[mask_par] = pico * (1.0 - arg ** self.n_parabola)
        if mask_rect.any():
            sigma[mask_rect] = pico
        # Tracao: ramo linear -> branda
        eps_ct2 = 0.9 * self.fctk_kncm2 / self.Eci_kncm2 * 1000.0
        mask_lin_t = (eps < 0.0) & (eps >= -eps_ct2)
        if mask_lin_t.any():
            sigma[mask_lin_t] = self.Eci_kncm2 * eps[mask_lin_t] / 1000.0
        mask_branda_t = (eps < -eps_ct2) & (eps >= -self.eps_ctu_pmilh)
        if mask_branda_t.any():
            t = (eps[mask_branda_t] + eps_ct2) / (-self.eps_ctu_pmilh + eps_ct2)
            sigma[mask_branda_t] = -(0.9 + 0.1 * t) * self.fctk_kncm2
        # Alem de eps_ctu (tracao): solta (fissurado)
        return sigma


# ---------------------------------------------------------------------------
# Materiais
# ---------------------------------------------------------------------------
@dataclass
class Concreto:
    """Concreto NBR 6118:2026. Imutavel por convencao (nao alterar fck apos
    construcao -- as cached_property nao sao recalculadas).

    Os parametros do material vem do nucleo normativo (`nucleo_nbr6118`):
    fcd, eta_c, eps_c2, eps_cu, n, Eci, fct e a posicao do pivo C. fck fora
    de 20 a 90 MPa levanta `FaixaNormativaError` (8.2.1).

    O parametro `curva` permite plugar uma curva constitutiva custom. Se
    nao informado, usa a parabola-retangulo NBR derivada de fck (pico
    0,85*eta_c*fcd). Os limites de deformacao (eps_c2, eps_cu, pivo C)
    continuam sendo os da norma para o fck informado.
    """
    fck_mpa: float
    gama_c: float = GAMA_C
    curva: CurvaC | None = None

    def __post_init__(self):
        # FCO-13: 8.2.1 -- a norma vale de C20 a C90.
        nbr.validar_fck(self.fck_mpa)

    @cached_property
    def fcd_kncm2(self) -> float:
        return nbr.mpa_para_kncm2(nbr.fcd(self.fck_mpa, self.gama_c))

    @cached_property
    def eta_c(self) -> float:
        """eta_c da Figura 8.2: 1,0 ate C40; (40/fck)^(1/3) acima."""
        return nbr.eta_c(self.fck_mpa)

    @cached_property
    def eps_c2_pmilh(self) -> float:
        """Deformacao de inicio do patamar plastico (em por mil)."""
        return nbr.eps_c2(self.fck_mpa)

    @cached_property
    def eps_cu_pmilh(self) -> float:
        """Deformacao ultima do concreto (em por mil)."""
        return nbr.eps_cu(self.fck_mpa)

    @cached_property
    def n_parabola(self) -> float:
        return nbr.n_parabola(self.fck_mpa)

    @cached_property
    def pivo_C_rel(self) -> float:
        """Profundidade do pivo C / h: (eps_cu - eps_c2)/eps_cu (Figura 17.1)."""
        return nbr.pivo_C_distancia_relativa(self.fck_mpa)

    @cached_property
    def eps_reta_b_pmilh(self) -> float:
        """Encurtamento uniforme da reta b (compressao centrada), por mil.

        eps_c2 (Figura 17.1). Em C90 a norma da eps_c2 = 2,6006 > eps_cu = 2,6;
        adota-se o menor dos dois.
        """
        return nbr.eps_compressao_uniforme(self.fck_mpa)

    @cached_property
    def Eci_kncm2(self) -> float:
        """Modulo de elasticidade tangente inicial (NBR 8.2.8). kN/cm^2."""
        # alphaE = 1.0 (granito); para outros agregados, usuario pode passar
        # uma curva custom via `curva`.
        return nbr.mpa_para_kncm2(nbr.Eci(self.fck_mpa))

    @cached_property
    def fctm_kncm2(self) -> float:
        """Resistencia media a tracao direta (NBR 8.2.5). kN/cm^2."""
        return nbr.mpa_para_kncm2(nbr.fct_m(self.fck_mpa))

    @cached_property
    def fctk_inf_kncm2(self) -> float:
        """Resistencia a tracao caracteristica inferior (NBR 8.2.5). kN/cm^2."""
        return nbr.mpa_para_kncm2(nbr.fctk_inf(self.fck_mpa))

    @cached_property
    def _curva_efetiva(self) -> CurvaC:
        if self.curva is not None:
            return self.curva
        return CurvaCParabolaRetangulo(
            fcd_kncm2=self.fcd_kncm2,
            eps_c2_pmilh=self.eps_c2_pmilh,
            eps_cu_pmilh=self.eps_cu_pmilh,
            n_parabola=self.n_parabola,
            eta_c=self.eta_c,
        )


@dataclass
class Aco:
    fyk_mpa: float = 500.0
    Es_kncm2: float = ES_KNCM2
    gama_s: float = GAMA_S

    @cached_property
    def fyd_kncm2(self) -> float:
        return (self.fyk_mpa / self.gama_s) * 0.1

    @cached_property
    def eps_yd_pmilh(self) -> float:
        return self.fyd_kncm2 / self.Es_kncm2 * 1000.0


# ---------------------------------------------------------------------------
# Aco de protensao (curva sigma-eps + Cabo + BarraP)
# ---------------------------------------------------------------------------
@runtime_checkable
class CurvaAp(Protocol):
    """Curva sigma-eps de aco de protensao. eps em "por mil"."""

    def sigma(self, eps: np.ndarray) -> np.ndarray: ...


@dataclass
class CurvaApBilinear:
    """Aco de protensao bilinear: linear ate fpyd, depois patamar.

    Defaults para cordoalha CP-190RB (NBR 7483).
    """
    fpyk_mpa: float = 1710.0   # tensao de escoamento (CP-190RB)
    fptk_mpa: float = 1900.0   # tensao de ruptura
    Ep_kncm2: float = 20000.0  # 200 GPa
    gama_s: float = GAMA_S
    eps_pu_pmilh: float = 35.0  # deformacao ultima (NBR)

    @cached_property
    def fpyd_kncm2(self) -> float:
        return (self.fpyk_mpa / self.gama_s) * 0.1

    @cached_property
    def eps_pyd_pmilh(self) -> float:
        return self.fpyd_kncm2 / self.Ep_kncm2 * 1000.0

    def sigma(self, eps: np.ndarray) -> np.ndarray:
        return np.where(
            np.abs(eps) <= self.eps_pyd_pmilh,
            eps / 1000.0 * self.Ep_kncm2,
            np.sign(eps) * self.fpyd_kncm2,
        )


@dataclass(frozen=True)
class Cabo:
    """Cabo de protensao (cordoalha pre-tracionada).

    Convencao:
        - x_cm, y_cm: posicao (cm), centroide da secao na origem.
        - area_cm2: area do cabo.
        - eps_pre_pmilh: magnitude da pre-deformacao do cabo (sempre positiva,
          em "por mil"). Tipicamente 5-8 ‰ apos perdas.
        - curva: curva sigma-eps. Default None -> CurvaApBilinear(CP-190RB).

    Equilibrio: ε_efetiva = ε_concreto_local - eps_pre_pmilh
    (compressao do concreto alivia a tracao da cordoalha; bastos.py adota
    compressao positiva, entao subtrai para tracionar o cabo no estado inicial).
    """
    x_cm: float
    y_cm: float
    area_cm2: float
    eps_pre_pmilh: float
    curva: CurvaAp = None  # type: ignore[assignment]


_CURVA_AP_DEFAULT = CurvaApBilinear()


def _cabo_curva(c: Cabo) -> CurvaAp:
    return c.curva if c.curva is not None else _CURVA_AP_DEFAULT


# ---------------------------------------------------------------------------
# Geometria
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Barra:
    x_cm: float
    y_cm: float
    area_cm2: float


@dataclass
class SecaoRetangular:
    base_cm: float
    altura_cm: float
    cobrimento_cm: float = 2.5
    barras: tuple[Barra, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.barras:
            arr = np.array(
                [(b.x_cm, b.y_cm, b.area_cm2) for b in self.barras],
                dtype=float,
            )
        else:
            arr = np.zeros((0, 3))
        self._barras_xyA = arr  # type: ignore[attr-defined]

    @property
    def Ac_cm2(self) -> float:
        return self.base_cm * self.altura_cm

    @property
    def As_total_cm2(self) -> float:
        return float(self._barras_xyA[:, 2].sum())

    @property
    def n_barras(self) -> int:
        return len(self.barras)


def armadura_perimetral_retangular(
    base_cm: float,
    altura_cm: float,
    cobrimento_cm: float,
    nx: int,
    ny: int,
    fi_l_mm: float,
    fi_t_mm: float = 5.0,
    area_por_barra_cm2: float | None = None,
) -> tuple[Barra, ...]:
    """Gera barras no perimetro (mesmo padrao do PFOC):
        - nx barras na linha superior e na linha inferior;
        - 2 barras (uma em cada lateral) em cada linha intermediaria;
        - total = 2*(nx + ny) - 4 barras.
    """
    if nx < 2 or ny < 2:
        raise ValueError("nx, ny >= 2.")
    d_linha = cobrimento_cm + (fi_t_mm + fi_l_mm / 2.0) / 10.0
    if area_por_barra_cm2 is None:
        area_por_barra_cm2 = math.pi * (fi_l_mm / 20.0) ** 2

    barras: list[Barra] = []
    for k in range(ny):
        y = -altura_cm / 2.0 + d_linha + k * (altura_cm - 2 * d_linha) / (ny - 1)
        n_at_row = nx if (k == 0 or k == ny - 1) else 2
        for cont in range(n_at_row):
            x = -base_cm / 2.0 + d_linha + cont * (base_cm - 2 * d_linha) / (n_at_row - 1)
            barras.append(Barra(x_cm=x, y_cm=y, area_cm2=area_por_barra_cm2))
    return tuple(barras)


# ---------------------------------------------------------------------------
# Geometria poligonal (Parte + Secao + helpers)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Parte:
    """Parte de uma secao poligonal.

    polygon: sequencia de (x, y) em cm, fechado (ultimo == primeiro). Sentido
        anti-horario produz area positiva.
    concreto: Concreto da parte (permite multi-fck na secao).
    """
    polygon: tuple[tuple[float, float], ...]
    concreto: "Concreto"


@dataclass
class Secao:
    """Secao geral, composta por uma ou mais partes poligonais + barras.

    Suporta secao L, T, U, circular aproximada (poligono de N lados),
    multi-fck (partes com concretos distintos), composicoes etc.

    Para retangulo simples, prefira a factory `Secao.retangular(...)`.

    Parametros de discretizacao (n_dy/n_dx) controlam precisao numerica:
        - n_dy: numero total de faixas horizontais (lamelas) na secao toda;
        - n_dx: subdivisoes em x dentro de cada lamela (importante em FCO).

    Cabos de protensao (opcional): adicione via `cabos`. Cada Cabo carrega
    sua pre-deformacao e curva sigma-eps. A integracao soma a contribuicao
    dos cabos ao equilibrio. Com cabos, fck >= 25 MPa (8.2.1).

    Secao com mais de um concreto: um unico plano de deformacao para a
    secao toda (17.2.2 a); cada concreto respeita os proprios limites
    (eps_cu na sua fibra mais comprimida e eps_c2 no seu pivo C, a
    (eps_cu - eps_c2)/eps_cu * h abaixo dessa fibra). Barras e cabos
    descontam o concreto da parte em que estao.
    """
    partes: tuple[Parte, ...]
    barras: tuple[Barra, ...] = field(default_factory=tuple)
    cabos: tuple[Cabo, ...] = field(default_factory=tuple)
    n_dy: int = 40
    n_dx: int = 20

    def __post_init__(self):
        if self.barras:
            arr = np.array(
                [(b.x_cm, b.y_cm, b.area_cm2) for b in self.barras],
                dtype=float,
            )
        else:
            arr = np.zeros((0, 3))
        self._barras_xyA = arr  # type: ignore[attr-defined]
        if self.cabos:
            # 8.2.1: concreto com armadura ativa -- C25 no minimo.
            for parte in self.partes:
                nbr.validar_fck(parte.concreto.fck_mpa, protendido=True)
        # Parte que contem cada barra/cabo (para descontar o concreto certo).
        self._barras_parte = np.array(  # type: ignore[attr-defined]
            [_indice_parte(self.partes, b.x_cm, b.y_cm) for b in self.barras],
            dtype=int,
        )
        self._cabos_parte = np.array(  # type: ignore[attr-defined]
            [_indice_parte(self.partes, c.x_cm, c.y_cm) for c in self.cabos],
            dtype=int,
        )

    @classmethod
    def retangular(
        cls,
        base_cm: float,
        altura_cm: float,
        concreto: "Concreto",
        barras: tuple[Barra, ...] = (),
        cabos: tuple[Cabo, ...] = (),
        n_dy: int = 40,
        n_dx: int = 20,
    ) -> "Secao":
        """Helper para retangulo centrado na origem."""
        b, h = base_cm / 2.0, altura_cm / 2.0
        polygon = ((-b, -h), (b, -h), (b, h), (-b, h), (-b, -h))
        return cls(
            partes=(Parte(polygon=polygon, concreto=concreto),),
            barras=barras,
            cabos=cabos,
            n_dy=n_dy,
            n_dx=n_dx,
        )

    @property
    def Ac_cm2(self) -> float:
        return float(sum(_polygon_area(p.polygon) for p in self.partes))

    @property
    def As_total_cm2(self) -> float:
        if self._barras_xyA.shape[0] == 0:
            return 0.0
        return float(self._barras_xyA[:, 2].sum())

    @property
    def n_barras(self) -> int:
        return len(self.barras)


def _polygon_area(polygon: tuple[tuple[float, float], ...]) -> float:
    """Area do poligono pela formula do shoelace. Sempre positiva."""
    s = 0.0
    n = len(polygon)
    for i in range(n - 1):
        x0, y0 = polygon[i]
        x1, y1 = polygon[i + 1]
        s += (x0 + x1) * (y1 - y0) / 2.0
    return abs(s)


def _polygon_bbox(
    polygon: tuple[tuple[float, float], ...],
) -> tuple[float, float, float, float]:
    """(x_min, y_min, x_max, y_max)."""
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return (min(xs), min(ys), max(xs), max(ys))


def _ponto_no_poligono(
    x: float, y: float, polygon: tuple[tuple[float, float], ...], tol: float = 1e-9,
) -> bool:
    """Ponto dentro do poligono (ray casting); ponto na borda conta como dentro."""
    n = len(polygon)
    for i in range(n - 1):
        x0, y0 = polygon[i]
        x1, y1 = polygon[i + 1]
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        if L2 == 0.0:
            continue
        t = ((x - x0) * dx + (y - y0) * dy) / L2
        if -tol <= t <= 1.0 + tol and abs((x - x0) * dy - (y - y0) * dx) <= tol * math.sqrt(L2):
            return True
    dentro = False
    for i in range(n - 1):
        x0, y0 = polygon[i]
        x1, y1 = polygon[i + 1]
        if (y0 > y) != (y1 > y):
            x_cruz = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if x < x_cruz:
                dentro = not dentro
    return dentro


def _indice_parte(partes, x: float, y: float) -> int:
    """Indice da primeira parte que contem (x, y); 0 se nenhuma contiver."""
    for i, parte in enumerate(partes):
        if _ponto_no_poligono(x, y, parte.polygon):
            return i
    return 0


def _list_y_split(polygon: tuple[tuple[float, float], ...]) -> list[float]:
    """Y dos vertices unicos + arestas horizontais. Usado para criar faixas
    de discretizacao alinhadas com mudancas de geometria (cantos)."""
    ys = sorted({round(p[1], 10) for p in polygon})
    return ys


def _cruzamentos_y(
    y_alvo: float,
    polygon: tuple[tuple[float, float], ...],
) -> list[float]:
    """X dos pontos onde a linha y=y_alvo cruza o poligono. Ordenados."""
    xs: list[float] = []
    for i in range(len(polygon) - 1):
        x0, y0 = polygon[i]
        x1, y1 = polygon[i + 1]
        if min(y0, y1) <= y_alvo <= max(y0, y1) and y0 != y1:
            t = (y_alvo - y0) / (y1 - y0)
            xs.append(x0 + t * (x1 - x0))
    return sorted(set(round(x, 10) for x in xs))


def _discretiza_parte(
    parte: Parte, n_dy_total: int, n_dx_lamela: int, h_total: float,
) -> np.ndarray:
    """Discretiza uma parte em elementos retangulares.

    Algoritmo SECC: lamelas horizontais (faixas de altura ~dy) cruzadas com o
    poligono, depois subdivisao em sublamelas em x para precisao FCO.
    Retorna ndarray (N, 3) com colunas (x_centro, y_centro, dA) -- somente
    leitura: a malha depende so da geometria e fica em cache.
    """
    return _discretiza_poligono(
        tuple(tuple(float(c) for c in p) for p in parte.polygon),
        int(n_dy_total), int(n_dx_lamela), float(h_total),
    )


@lru_cache(maxsize=256)
def _discretiza_poligono(
    poly: tuple[tuple[float, float], ...], n_dy_total: int, n_dx_lamela: int, h_total: float,
) -> np.ndarray:
    list_y = _list_y_split(poly)
    elementos: list[tuple[float, float, float]] = []

    for i in range(len(list_y) - 1):
        y1, y2 = list_y[i], list_y[i + 1]
        ny_local = max(2, int(round((y2 - y1) / h_total * n_dy_total)))
        dy_local = (y2 - y1) / ny_local
        for j in range(ny_local):
            yi = y1 + dy_local * (j + 0.5)
            xs = _cruzamentos_y(yi, poly)
            for k in range(0, len(xs) - 1, 2):
                x_left, x_right = xs[k], xs[k + 1]
                width = x_right - x_left
                if width <= 0:
                    continue
                dx_local = width / n_dx_lamela
                for m in range(n_dx_lamela):
                    x_centro = x_left + dx_local * (m + 0.5)
                    dA = dx_local * dy_local
                    elementos.append((x_centro, yi, dA))

    arr = np.array(elementos, dtype=float) if elementos else np.zeros((0, 3))
    arr.setflags(write=False)
    return arr


# ---------------------------------------------------------------------------
# Geometria auxiliar: rotacao
# ---------------------------------------------------------------------------
def _h_inc_yp_max(secao: SecaoRetangular, alpha: float) -> tuple[float, float]:
    """Retorna (h_inc, yp_max) onde y' = -x*sin(a) + y*cos(a)."""
    cos_a, sin_a = math.cos(alpha), math.sin(alpha)
    b, h = secao.base_cm, secao.altura_cm
    # 4 cantos -> 4 valores de y'
    yp_corners = np.array([
        -b / 2 * sin_a + h / 2 * cos_a,
        +b / 2 * sin_a + h / 2 * cos_a,
        -b / 2 * sin_a - h / 2 * cos_a,
        +b / 2 * sin_a - h / 2 * cos_a,
    ])
    yp_max = float(yp_corners.max())
    yp_min = float(yp_corners.min())
    return yp_max - yp_min, yp_max


def _d_inc(secao: SecaoRetangular, alpha: float, yp_max: float) -> float:
    """Profundidade da barra mais distante da face comprimida (cm).
    Usada como d para definir o pivo A do dominio 2.

    Sem armadura, nao ha pivo A (Figura 17.1): devolve 0, e a ruptura fica
    sempre governada pelo encurtamento do concreto (pivos B e C).
    """
    if secao._barras_xyA.shape[0] == 0:
        return 0.0
    cos_a, sin_a = math.cos(alpha), math.sin(alpha)
    x_b = secao._barras_xyA[:, 0]
    y_b = secao._barras_xyA[:, 1]
    yp_b = -x_b * sin_a + y_b * cos_a
    s_b = yp_max - yp_b
    return float(s_b.max())


def _h_inc_yp_max_pol(secao: Secao, alpha: float) -> tuple[float, float]:
    """Como _h_inc_yp_max mas para Secao poligonal: percorre vertices."""
    cos_a, sin_a = math.cos(alpha), math.sin(alpha)
    yp_min = float("inf")
    yp_max = float("-inf")
    for parte in secao.partes:
        for x, y in parte.polygon:
            yp = -x * sin_a + y * cos_a
            if yp < yp_min:
                yp_min = yp
            if yp > yp_max:
                yp_max = yp
    return yp_max - yp_min, yp_max


def _d_inc_pol(secao: Secao, alpha: float, yp_max: float) -> float:
    """Profundidade da armadura mais tracionada -- barras passivas e cabos --
    a partir da face comprimida (pivo A, Figura 17.1).

    Nos cabos, o limite de 10 por mil vale para o acrescimo de deformacao
    (17.2.2 b), que e a deformacao do concreto no nivel do cabo. Sem
    armadura nenhuma, nao ha pivo A: devolve 0.
    """
    cos_a, sin_a = math.cos(alpha), math.sin(alpha)
    s_max = None
    if secao._barras_xyA.shape[0] > 0:
        x_b = secao._barras_xyA[:, 0]
        y_b = secao._barras_xyA[:, 1]
        s_max = float((yp_max - (-x_b * sin_a + y_b * cos_a)).max())
    for c in secao.cabos:
        s_c = yp_max - (-c.x_cm * sin_a + c.y_cm * cos_a)
        s_max = s_c if s_max is None else max(s_max, s_c)
    return 0.0 if s_max is None else float(s_max)


def _zonas_concreto_pol(
    secao: Secao, alpha: float, yp_max: float,
) -> list[tuple[float, float, float, float]]:
    """Zonas da secao com os mesmos limites de deformacao (eps_c2, eps_cu).

    Devolve (s_topo, eps_c2, eps_cu, pivo_c_rel) por zona, sendo s_topo a
    profundidade do ponto mais comprimido da zona, medida perpendicularmente
    a LN. Concretos ate C50 tem os mesmos limites (2 e 3,5 por mil) e caem
    na mesma zona.
    """
    cos_a, sin_a = math.cos(alpha), math.sin(alpha)
    grupos: dict[tuple[float, float], list[float]] = {}
    for parte in secao.partes:
        c = parte.concreto
        chave = (c.eps_c2_pmilh, c.eps_cu_pmilh)
        topo = max(-x * sin_a + y * cos_a for x, y in parte.polygon)
        g = grupos.get(chave)
        if g is None:
            grupos[chave] = [topo, c.pivo_C_rel]
        else:
            g[0] = max(g[0], topo)
    return [
        (yp_max - topo, ec2, ecu, rho)
        for (ec2, ecu), (topo, rho) in grupos.items()
    ]


# ---------------------------------------------------------------------------
# Distribuicao de deformacoes (3 dominios via pivos A/B/C)
# ---------------------------------------------------------------------------
def _strain(
    s: np.ndarray | float,
    x_LN: float,
    h_inc: float,
    d_inc: float,
    eps_c2: float,
    eps_cu: float,
    pivo_c_rel: float | None = None,
) -> np.ndarray | float:
    """Deformacao (em por mil) numa fibra a profundidade s da face mais
    comprimida. s=0 e a face. Vetorizada. Figura 17.1 da NBR 6118:2026:

        - dominio 2: pivo A, -10 por mil na armadura mais tracionada (s = d_inc);
        - dominios 3, 4 e 4a: pivo B, eps_cu na face (s = 0);
        - dominio 5: pivo C, eps_c2 a (eps_cu - eps_c2)/eps_cu * h da face.

    `pivo_c_rel` e a profundidade do pivo C dividida por h
    (`nucleo_nbr6118.pivo_C_distancia_relativa`); sem ele, e calculado de
    eps_c2 e eps_cu pela mesma expressao. Vale 3/7 so ate C50 (FCO-02).
    Em C90 a norma da eps_c2 > eps_cu: o pivo C cai na face e usa-se
    min(eps_c2, eps_cu), o que mantem a deformacao continua em x = h.
    Sem armadura (d_inc = 0) nao ha dominio 2.
    """
    if pivo_c_rel is None:
        pivo_c_rel = max(0.0, (eps_cu - eps_c2) / eps_cu)
    x_lim_2_3 = eps_cu / (eps_cu + EPS_SU) * d_inc
    if x_LN <= x_lim_2_3:
        # Dominio 2: pivo A -> eps = -10 por mil em s=d_inc.
        return EPS_SU * (x_LN - s) / (d_inc - x_LN)
    if x_LN <= h_inc:
        # Dominio 3/4/4a: pivo B -> eps = eps_cu em s=0.
        return eps_cu * (x_LN - s) / x_LN
    # Dominio 5: pivo C -> eps = eps_c2 em s = pivo_c_rel*h_inc.
    return min(eps_c2, eps_cu) * (x_LN - s) / (x_LN - pivo_c_rel * h_inc)


def _strain_zonas(
    s: np.ndarray | float,
    x_LN: float,
    h_inc: float,
    d_inc: float,
    zonas: list[tuple[float, float, float, float]],
) -> np.ndarray | float:
    """Deformacao num plano UNICO para a secao inteira (17.2.2 a), com mais
    de um concreto (FCO-15).

    O plano e eps(s) = k*(x_LN - s), com a maior curvatura k que respeita
    ao mesmo tempo, para cada concreto: -10 por mil na armadura mais
    tracionada (pivo A); eps_cu na fibra mais comprimida desse concreto
    (pivo B); e eps_c2 no pivo C desse concreto, a
    (eps_cu - eps_c2)/eps_cu * h abaixo da sua fibra mais comprimida, com h
    a altura da secao (dominio 5). Com um concreto so, e exatamente a
    Figura 17.1 (`_strain`). A compressao uniforme fica limitada ao menor
    eps_c2 entre os concretos.
    """
    if len(zonas) == 1:
        _, ec2, ecu, rho = zonas[0]
        return _strain(s, x_LN, h_inc, d_inc, ec2, ecu, rho)
    ks = []
    if d_inc > x_LN:
        ks.append(EPS_SU / (d_inc - x_LN))
    for s_topo, ec2, ecu, rho in zonas:
        if x_LN > s_topo:
            ks.append(ecu / (x_LN - s_topo))
        s_c = s_topo + rho * h_inc
        if x_LN > s_c:
            ks.append(min(ec2, ecu) / (x_LN - s_c))
    return min(ks) * (x_LN - s)


# ---------------------------------------------------------------------------
# Modelos constitutivos vetorizados
# ---------------------------------------------------------------------------
def _sigma_concreto(
    eps: np.ndarray,
    fcd: float,
    eps_c2: float,
    eps_cu: float,
    n_par: float,
    eta_c: float = 1.0,
) -> np.ndarray:
    """Parabola-retangulo NBR. Tracao -> 0. Vetorizado.

    Mantida para compatibilidade. Novas chamadas devem usar
    `concreto._curva_efetiva.sigma(eps)` diretamente (que ja tem o eta_c).
    Acima de C40, passe `eta_c` (o padrao 1,0 so vale ate C40).
    """
    return CurvaCParabolaRetangulo(
        fcd_kncm2=fcd,
        eps_c2_pmilh=eps_c2,
        eps_cu_pmilh=eps_cu,
        n_parabola=n_par,
        eta_c=eta_c,
    ).sigma(eps)


def _sigma_aco(
    eps: np.ndarray,
    fyd: float,
    Es: float,
    eps_yd: float,
) -> np.ndarray:
    """Bilinear simetrico. eps em por mil. Sigma em kN/cm^2."""
    return np.where(
        np.abs(eps) <= eps_yd,
        eps / 1000.0 * Es,
        np.sign(eps) * fyd,
    )


# ---------------------------------------------------------------------------
# Integracao do concreto (2D, vetorizada)
# ---------------------------------------------------------------------------
def _integrar_concreto(
    secao: SecaoRetangular,
    concreto: Concreto,
    alpha: float,
    x_LN: float,
    n_grid: int = 80,
) -> tuple[float, float, float]:
    """Integra (Nc, Mxc, Myc) por fibras 2D na secao rotacionada.
    Retorna em (kN, kN.cm, kN.cm).
    """
    if x_LN <= 0.0:
        return 0.0, 0.0, 0.0

    eps_c2 = concreto.eps_c2_pmilh
    eps_cu = concreto.eps_cu_pmilh
    curva = concreto._curva_efetiva

    h_inc, yp_max = _h_inc_yp_max(secao, alpha)
    d_inc = _d_inc(secao, alpha, yp_max)

    b, h = secao.base_cm, secao.altura_cm
    nx = n_grid
    ny = n_grid
    dx = b / nx
    dy = h / ny
    dA = dx * dy

    x_centers = np.linspace(-b / 2 + dx / 2, b / 2 - dx / 2, nx)
    y_centers = np.linspace(-h / 2 + dy / 2, h / 2 - dy / 2, ny)
    X, Y = np.meshgrid(x_centers, y_centers, indexing="ij")
    cos_a, sin_a = math.cos(alpha), math.sin(alpha)
    Yp = -X * sin_a + Y * cos_a
    S = yp_max - Yp

    eps = _strain(S, x_LN, h_inc, d_inc, eps_c2, eps_cu, concreto.pivo_C_rel)
    sigma = curva.sigma(eps)

    Nc = float(sigma.sum() * dA)
    Mxc = float((sigma * Y).sum() * dA)
    Myc = float((sigma * X).sum() * dA)
    return Nc, Mxc, Myc


def _esforcos_barras(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    alpha: float,
    x_LN: float,
) -> tuple[float, float, float]:
    """Esforcos das barras: (sigma_s - sigma_c) * As para evitar dupla-contagem
    da area de concreto deslocada pelas barras.
    """
    if secao._barras_xyA.shape[0] == 0:
        return 0.0, 0.0, 0.0
    if x_LN <= 0.0:
        # Tracao pura -- todas as barras em tracao. eps -> grande negativo.
        eps_b = np.full(secao._barras_xyA.shape[0], -10.0)
        sigma_s = _sigma_aco(
            eps_b, aco.fyd_kncm2, aco.Es_kncm2, aco.eps_yd_pmilh
        )
        x_b = secao._barras_xyA[:, 0]
        y_b = secao._barras_xyA[:, 1]
        A_b = secao._barras_xyA[:, 2]
        Ns = float((sigma_s * A_b).sum())
        Mxs = float((sigma_s * A_b * y_b).sum())
        Mys = float((sigma_s * A_b * x_b).sum())
        return Ns, Mxs, Mys

    eps_c2 = concreto.eps_c2_pmilh
    eps_cu = concreto.eps_cu_pmilh
    curva = concreto._curva_efetiva

    h_inc, yp_max = _h_inc_yp_max(secao, alpha)
    d_inc = _d_inc(secao, alpha, yp_max)

    cos_a, sin_a = math.cos(alpha), math.sin(alpha)
    x_b = secao._barras_xyA[:, 0]
    y_b = secao._barras_xyA[:, 1]
    A_b = secao._barras_xyA[:, 2]
    yp_b = -x_b * sin_a + y_b * cos_a
    s_b = yp_max - yp_b

    eps_b = _strain(s_b, x_LN, h_inc, d_inc, eps_c2, eps_cu, concreto.pivo_C_rel)

    sigma_s = _sigma_aco(eps_b, aco.fyd_kncm2, aco.Es_kncm2, aco.eps_yd_pmilh)
    sigma_c = curva.sigma(eps_b)
    delta = sigma_s - sigma_c

    Ns = float((delta * A_b).sum())
    Mxs = float((delta * A_b * y_b).sum())
    Mys = float((delta * A_b * x_b).sum())
    return Ns, Mxs, Mys


def esforcos_resistentes(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    alpha: float,
    x_LN: float,
    n_grid: int = 80,
) -> tuple[float, float, float]:
    """(Nr, Mxr, Myr) totais (concreto + barras) em kN, kN.cm, kN.cm."""
    Nc, Mxc, Myc = _integrar_concreto(secao, concreto, alpha, x_LN, n_grid)
    Ns, Mxs, Mys = _esforcos_barras(secao, concreto, aco, alpha, x_LN)
    return Nc + Ns, Mxc + Mxs, Myc + Mys


# ---------------------------------------------------------------------------
# Integracao para Secao poligonal (multi-parte, multi-fck)
# ---------------------------------------------------------------------------
def _integrar_concreto_pol(
    secao: Secao,
    alpha: float,
    x_LN: float,
) -> tuple[float, float, float]:
    """Integra (Nc, Mxc, Myc) sobre todas as partes da Secao poligonal.

    Um unico plano de deformacao para a secao inteira (17.2.2 a); cada
    parte usa a curva do seu proprio Concreto (FCO-15).
    """
    if x_LN <= 0.0:
        return 0.0, 0.0, 0.0

    h_inc, yp_max = _h_inc_yp_max_pol(secao, alpha)
    d_inc = _d_inc_pol(secao, alpha, yp_max)
    zonas = _zonas_concreto_pol(secao, alpha, yp_max)
    cos_a, sin_a = math.cos(alpha), math.sin(alpha)

    _, y_min_global, _, y_max_global = _bbox_secao(secao)
    h_total = y_max_global - y_min_global

    Nc_total = Mxc_total = Myc_total = 0.0
    for parte in secao.partes:
        elements = _discretiza_parte(parte, secao.n_dy, secao.n_dx, h_total)
        if elements.shape[0] == 0:
            continue
        X = elements[:, 0]
        Y = elements[:, 1]
        dA = elements[:, 2]
        Yp = -X * sin_a + Y * cos_a
        S = yp_max - Yp
        eps = _strain_zonas(S, x_LN, h_inc, d_inc, zonas)
        sigma = parte.concreto._curva_efetiva.sigma(eps)
        Nc_total += float((sigma * dA).sum())
        Mxc_total += float((sigma * Y * dA).sum())
        Myc_total += float((sigma * X * dA).sum())

    return Nc_total, Mxc_total, Myc_total


def _bbox_secao(secao: Secao) -> tuple[float, float, float, float]:
    """(x_min, y_min, x_max, y_max) cobrindo todas as partes."""
    x_min = y_min = float("inf")
    x_max = y_max = float("-inf")
    for parte in secao.partes:
        for x, y in parte.polygon:
            if x < x_min:
                x_min = x
            if x > x_max:
                x_max = x
            if y < y_min:
                y_min = y
            if y > y_max:
                y_max = y
    return x_min, y_min, x_max, y_max


def _sigma_c_nas_partes(
    secao: Secao, idx_parte: np.ndarray, eps: np.ndarray,
) -> np.ndarray:
    """Tensao no concreto em pontos (barras/cabos), cada um com a curva do
    concreto da parte que o contem."""
    eps = np.asarray(eps, dtype=float)
    sig = np.zeros_like(eps)
    for i in np.unique(idx_parte):
        m = idx_parte == i
        sig[m] = secao.partes[int(i)].concreto._curva_efetiva.sigma(eps[m])
    return sig


def _esforcos_barras_pol(
    secao: Secao,
    aco: Aco,
    alpha: float,
    x_LN: float,
) -> tuple[float, float, float]:
    """Esforcos das barras na Secao poligonal.

    Deformacao do mesmo plano unico do concreto. Para a subtracao do
    concreto deslocado (sigma_c em cada barra), usa o concreto da parte que
    contem a barra (a primeira parte, se nenhuma contiver).
    """
    if secao._barras_xyA.shape[0] == 0:
        return 0.0, 0.0, 0.0

    x_b = secao._barras_xyA[:, 0]
    y_b = secao._barras_xyA[:, 1]
    A_b = secao._barras_xyA[:, 2]

    if x_LN <= 0.0:
        eps_b = np.full(secao._barras_xyA.shape[0], -10.0)
        sigma_s = _sigma_aco(eps_b, aco.fyd_kncm2, aco.Es_kncm2, aco.eps_yd_pmilh)
        Ns = float((sigma_s * A_b).sum())
        Mxs = float((sigma_s * A_b * y_b).sum())
        Mys = float((sigma_s * A_b * x_b).sum())
        return Ns, Mxs, Mys

    h_inc, yp_max = _h_inc_yp_max_pol(secao, alpha)
    d_inc = _d_inc_pol(secao, alpha, yp_max)
    zonas = _zonas_concreto_pol(secao, alpha, yp_max)
    cos_a, sin_a = math.cos(alpha), math.sin(alpha)
    yp_b = -x_b * sin_a + y_b * cos_a
    s_b = yp_max - yp_b

    eps_b = _strain_zonas(s_b, x_LN, h_inc, d_inc, zonas)

    sigma_s = _sigma_aco(eps_b, aco.fyd_kncm2, aco.Es_kncm2, aco.eps_yd_pmilh)
    sigma_c = _sigma_c_nas_partes(secao, secao._barras_parte, eps_b)
    delta = sigma_s - sigma_c

    Ns = float((delta * A_b).sum())
    Mxs = float((delta * A_b * y_b).sum())
    Mys = float((delta * A_b * x_b).sum())
    return Ns, Mxs, Mys


def _esforcos_cabos_pol(
    secao: Secao,
    alpha: float,
    x_LN: float,
) -> tuple[float, float, float]:
    """Esforcos das cordoalhas de protensao (pre-aderidas).

    Convencao: ε_efetiva_cabo = ε_concreto_local - ε_pre.
    Para σ_c subtraido na posicao do cabo, usa o concreto da parte que
    contem o cabo (a primeira parte, se nenhuma contiver).
    """
    if not secao.cabos:
        return 0.0, 0.0, 0.0

    x_p = np.array([c.x_cm for c in secao.cabos])
    y_p = np.array([c.y_cm for c in secao.cabos])
    A_p = np.array([c.area_cm2 for c in secao.cabos])
    eps_pre = np.array([c.eps_pre_pmilh for c in secao.cabos])

    if x_LN <= 0.0:
        # Tracao pura: ε_concreto = -10 ‰; ε_efetiva_cabo = -10 - eps_pre
        eps_efetiva = -10.0 - eps_pre
        sigma_p = np.array([
            float(_cabo_curva(c).sigma(np.array([eps_efetiva[i]]))[0])
            for i, c in enumerate(secao.cabos)
        ])
        Np = float((sigma_p * A_p).sum())
        Mxp = float((sigma_p * A_p * y_p).sum())
        Myp = float((sigma_p * A_p * x_p).sum())
        return Np, Mxp, Myp

    h_inc, yp_max = _h_inc_yp_max_pol(secao, alpha)
    d_inc = _d_inc_pol(secao, alpha, yp_max)
    zonas = _zonas_concreto_pol(secao, alpha, yp_max)
    cos_a, sin_a = math.cos(alpha), math.sin(alpha)
    yp_p = -x_p * sin_a + y_p * cos_a
    s_p = yp_max - yp_p

    eps_concreto_p = _strain_zonas(s_p, x_LN, h_inc, d_inc, zonas)
    eps_efetiva = eps_concreto_p - eps_pre

    sigma_p = np.array([
        float(_cabo_curva(c).sigma(np.array([eps_efetiva[i]]))[0])
        for i, c in enumerate(secao.cabos)
    ])
    sigma_c_p = _sigma_c_nas_partes(secao, secao._cabos_parte, eps_concreto_p)
    delta_p = sigma_p - sigma_c_p

    Np = float((delta_p * A_p).sum())
    Mxp = float((delta_p * A_p * y_p).sum())
    Myp = float((delta_p * A_p * x_p).sum())
    return Np, Mxp, Myp


def esforcos_resistentes_pol(
    secao: Secao,
    aco: Aco,
    alpha: float,
    x_LN: float,
) -> tuple[float, float, float]:
    """Versao Secao poligonal do esforcos_resistentes.

    Nao recebe `concreto` separado: usa o concreto de cada Parte.
    Inclui contribuicao de cabos de protensao se presentes.
    """
    Nc, Mxc, Myc = _integrar_concreto_pol(secao, alpha, x_LN)
    Ns, Mxs, Mys = _esforcos_barras_pol(secao, aco, alpha, x_LN)
    Np, Mxp, Myp = _esforcos_cabos_pol(secao, alpha, x_LN)
    return Nc + Ns + Np, Mxc + Mxs + Mxp, Myc + Mys + Myp


# ---------------------------------------------------------------------------
# ELS (Estado Limite de Servico) -- solver Newton-Raphson 3x3
# ---------------------------------------------------------------------------
def _esforcos_internos_els(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    eps_cg: float,
    kx: float,
    ky: float,
    n_grid: int = 80,
) -> tuple[float, float, float]:
    """Esforcos resistentes para deformacao linear (Bernoulli, sem pivos):

        eps(x, y) = eps_cg + kx*y + ky*x

    Convencoes:
        - eps em "por mil". eps_cg em "por mil". kx, ky em "por mil"/cm.
        - Compressao positiva.
        - Sinais de Mxr, Myr consistentes com `esforcos_resistentes` (ELU).
    """
    curva = concreto._curva_efetiva

    b, h = secao.base_cm, secao.altura_cm
    nx = ny = n_grid
    dx, dy = b / nx, h / ny
    dA = dx * dy

    x_centers = np.linspace(-b / 2 + dx / 2, b / 2 - dx / 2, nx)
    y_centers = np.linspace(-h / 2 + dy / 2, h / 2 - dy / 2, ny)
    X, Y = np.meshgrid(x_centers, y_centers, indexing="ij")
    eps_grid = eps_cg + kx * Y + ky * X
    sig_c = curva.sigma(eps_grid)
    Nc = float(sig_c.sum() * dA)
    Mxc = float((sig_c * Y).sum() * dA)
    Myc = float((sig_c * X).sum() * dA)

    if secao._barras_xyA.shape[0] > 0:
        x_b = secao._barras_xyA[:, 0]
        y_b = secao._barras_xyA[:, 1]
        A_b = secao._barras_xyA[:, 2]
        eps_b = eps_cg + kx * y_b + ky * x_b
        sigma_s = _sigma_aco(eps_b, aco.fyd_kncm2, aco.Es_kncm2, aco.eps_yd_pmilh)
        sigma_c_b = curva.sigma(eps_b)
        delta = sigma_s - sigma_c_b
        Ns = float((delta * A_b).sum())
        Mxs = float((delta * A_b * y_b).sum())
        Mys = float((delta * A_b * x_b).sum())
    else:
        Ns = Mxs = Mys = 0.0

    return Nc + Ns, Mxc + Mxs, Myc + Mys


def _concreto_curva_15_3_1(concreto: Concreto) -> Concreto:
    """Concreto com a curva da relacao momento-curvatura da Figura 15.1:
    parabola-retangulo com pico 1,10*fcd (mesmos eps_c2, eps_cu e n)."""
    return Concreto(
        fck_mpa=concreto.fck_mpa,
        gama_c=concreto.gama_c,
        curva=CurvaCParabolaRetangulo(
            fcd_kncm2=concreto.fcd_kncm2,
            eps_c2_pmilh=concreto.eps_c2_pmilh,
            eps_cu_pmilh=concreto.eps_cu_pmilh,
            n_parabola=concreto.n_parabola,
            alpha_c=1.10,
            eta_c=1.0,
        ),
    )


def _estado_els_eixo(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    N_kn: float,
    M_kncm: float,
    eixo: str,
    n_grid: int = 60,
) -> tuple[float, float, float, float]:
    """Estado de deformacao (eps_cg, kx, ky) com N e M em torno de `eixo`.

    Curvatura so em torno de `eixo` (brentq aninhados: eps_cg para N e a
    curvatura para M). Se a secao nao for simetrica em relacao ao plano de
    flexao, refina com o solver 3x3 (`solver_els`), com o momento na outra
    direcao nulo. Devolve (eps_cg, kx, ky, k_eixo) em por mil e por mil/cm.
    """
    ext = max(secao.base_cm, secao.altura_cm)

    def forcas(e0: float, k: float) -> tuple[float, float, float]:
        kx, ky = (k, 0.0) if eixo == "x" else (0.0, k)
        Nr, Mxr, Myr = _esforcos_internos_els(secao, concreto, aco, e0, kx, ky, n_grid)
        return (Nr, Mxr, Myr) if eixo == "x" else (Nr, Myr, Mxr)

    def e0_de_k(k: float) -> float:
        lim = 20.0 + abs(k) * ext
        return brentq(lambda e0: forcas(e0, k)[0] - N_kn, -lim, lim, xtol=1e-10, rtol=1e-12)

    def resid(k: float) -> float:
        return forcas(e0_de_k(k), k)[1] - M_kncm

    r0 = resid(0.0)
    if r0 == 0.0:
        k_sol = 0.0
    else:
        passo = 1e-3 if r0 < 0.0 else -1e-3
        k_a, k_b = 0.0, passo
        while resid(k_b) * r0 > 0.0:
            k_a, k_b = k_b, 2.0 * k_b
            if abs(k_b) > 50.0:
                raise ValueError(
                    f"Estado de deformação não encontrado para N = {N_kn:.1f} kN e "
                    f"M = {M_kncm:.1f} kN·cm (momento acima da capacidade da curva)."
                )
        k_sol = brentq(resid, min(k_a, k_b), max(k_a, k_b), xtol=1e-12, rtol=1e-11)
    e0 = e0_de_k(k_sol)
    _, _, M_perp = forcas(e0, k_sol)
    kx, ky = (k_sol, 0.0) if eixo == "x" else (0.0, k_sol)
    if abs(M_perp) > 1e-4 * max(abs(M_kncm), 1.0):
        Mx, My = (M_kncm, 0.0) if eixo == "x" else (0.0, M_kncm)
        r = solver_els(secao, concreto, aco, N_kn, Mx, My, n_grid=n_grid,
                       x0=(e0, kx, ky))
        if not r["convergiu"]:
            raise ValueError(f"Estado de deformação não convergiu: {r.get('mensagem')}")
        e0, kx, ky = r["eps_cg_pmilh"], r["kx_pmilh_cm"], r["ky_pmilh_cm"]
    return e0, kx, ky, (kx if eixo == "x" else ky)


def ei_secante(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    Nsd_kn: float,
    Md_kncm: float,
    eixo: str,
    n_grid: int = 60,
    gama_f3: float = GAMA_F3,
    ponto: str = "B",
) -> float:
    """Rigidez secante (EI)sec, kN.cm^2, pela 15.3.1 e Figura 15.1 (NBR 6118:2026).

    A relacao momento-curvatura usada no calculo das deformacoes (curva
    cheia AB) e obtida com pico de 1,10*fcd no concreto e forca normal
    NRd/gama_f3, com NRd = NSd e gama_f3 = 1,1. O ponto B dessa curva tem
    M = MRd/gama_f3, sendo MRd o momento resistente de calculo (curva de
    ELU, 0,85*eta_c*fcd) para NRd, no eixo e no sentido de Md. A reta AB
    define (EI)sec = (MRd/gama_f3)/(1/r)_B.

    ponto="B"  (padrao): (EI)sec da reta AB. Nao depende de |Md|; Md so
        informa o sentido do momento (importa em armadura assimetrica).
    ponto="Md": secante da curva AB no ponto M = |Md|/gama_f3 (a propria
        curva AB e a usada no calculo das deformacoes); exige |Md| <= MRd.

    eixo: 'x' -> Md em torno de x (gera curvatura kx);
          'y' -> Md em torno de y (gera curvatura ky).

    Necessario para metodos de 2a ordem (P3/P4/P5 do PCalc) em
    `pilares_bastos.py`.
    """
    if eixo not in ("x", "y"):
        raise ValueError(f"eixo deve ser 'x' ou 'y', recebido {eixo!r}.")
    if ponto not in ("B", "Md"):
        raise ValueError(f"ponto deve ser 'B' ou 'Md', recebido {ponto!r}.")

    sentido = 1.0 if Md_kncm >= 0.0 else -1.0
    theta = (0.0 if sentido > 0 else math.pi) if eixo == "x" else (
        math.pi / 2.0 if sentido > 0 else -math.pi / 2.0)
    try:
        if not _origem_dentro_ret(secao, concreto, aco, Nsd_kn, n_grid):
            raise ValueError(MSG_ORIGEM_FORA.format(Nd=Nsd_kn))
        _, _, Mx_r, My_r, _ = _resolver_direcao_ret(
            secao, concreto, aco, Nsd_kn, theta, n_grid)
    except ValueError as e:
        raise ValueError(f"MRd não encontrado para NSd = {Nsd_kn:.1f} kN: {e}") from e
    MRd = math.hypot(Mx_r, My_r)

    if ponto == "B":
        M_alvo = MRd / gama_f3
    else:
        if abs(Md_kncm) > MRd * (1.0 + 1e-9):
            raise ValueError(
                f"|Md| = {abs(Md_kncm):.1f} kN·cm acima de MRd = {MRd:.1f} kN·cm: "
                "fora da curva momento-curvatura (15.3.1)."
            )
        M_alvo = abs(Md_kncm) / gama_f3
    if M_alvo <= 0.0:
        return float("inf")

    concreto_ab = _concreto_curva_15_3_1(concreto)
    _, _, _, k = _estado_els_eixo(
        secao, concreto_ab, aco, Nsd_kn / gama_f3, sentido * M_alvo, eixo, n_grid)
    # k em "por mil"/cm -> 1/cm dividindo por 1000
    if abs(k) < 1e-12:
        return float("inf")
    return M_alvo / (abs(k) * 1e-3)


def solver_els(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    Nsd_kn: float,
    Mxd_kncm: float,
    Myd_kncm: float,
    n_grid: int = 60,
    tol: float = 1e-3,
    iter_max: int = 100,
    x0: tuple[float, float, float] | None = None,
) -> dict:
    """Resolve estado de deformacao em ELS por Newton-Raphson 3x3.

    Encontra (eps_cg, kx, ky) tal que (Nr, Mxr, Myr) = (Nsd, Mxd, Myd) usando
    `scipy.optimize.fsolve` (Powell hibrido com Jacobiano por diferencas
    finitas). Util para:
        - Verificacao de tensao maxima no concreto (NBR 17.2.2).
        - Verificacao de deformacao no aco (controle de fissuracao).
        - Calculo de EI secante (necessario para metodos rigorosos de 2a ordem).

    Usa a curva de ELU do concreto (lacuna registrada: sem estadios I e II
    normativos). `x0` e a estimativa inicial (eps_cg, kx, ky); padrao zeros.

    Retorna dict com diagnostico:
        eps_cg_pmilh, kx_pmilh_cm, ky_pmilh_cm,
        eps_max_compr_pmilh, eps_min_pmilh,
        sigma_c_max_kncm2,
        convergiu, n_iter, residuo
    """
    from scipy.optimize import fsolve

    def F(x: np.ndarray) -> list[float]:
        eps_cg, kx, ky = x
        Nr, Mxr, Myr = _esforcos_internos_els(
            secao, concreto, aco, float(eps_cg), float(kx), float(ky), n_grid
        )
        return [Nr - Nsd_kn, Mxr - Mxd_kncm, Myr - Myd_kncm]

    x0 = np.array([0.0, 0.0, 0.0] if x0 is None else list(x0), dtype=float)
    sol, info, ier, msg = fsolve(
        F, x0, full_output=True, xtol=tol, maxfev=iter_max * 10
    )
    convergiu = ier == 1

    eps_cg, kx, ky = float(sol[0]), float(sol[1]), float(sol[2])

    b, h = secao.base_cm, secao.altura_cm
    cantos = np.array([
        [-b / 2, -h / 2],
        [+b / 2, -h / 2],
        [+b / 2, +h / 2],
        [-b / 2, +h / 2],
    ])
    eps_cantos = eps_cg + kx * cantos[:, 1] + ky * cantos[:, 0]
    sig_c_cantos = concreto._curva_efetiva.sigma(eps_cantos)

    return {
        "convergiu": bool(convergiu),
        "eps_cg_pmilh": eps_cg,
        "kx_pmilh_cm": kx,
        "ky_pmilh_cm": ky,
        "eps_max_compr_pmilh": float(eps_cantos.max()),
        "eps_min_pmilh": float(eps_cantos.min()),
        "sigma_c_max_kncm2": float(sig_c_cantos.max()),
        "n_iter": int(info["nfev"]),
        "residuo": float(np.linalg.norm(F(sol))),
        "mensagem": msg if not convergiu else None,
    }


# ---------------------------------------------------------------------------
# Pre-flight: faixa viavel de Nd
# ---------------------------------------------------------------------------
def Nd_max_kn(secao: SecaoRetangular, concreto: Concreto, aco: Aco) -> float:
    """Nd maximo: compressao uniforme (reta b da Figura 17.1).

    Encurtamento eps_c2 na secao inteira: concreto no pico 0,85*eta_c*fcd
    (Figura 8.2 -- FCO-01) e aco com sigma_s(eps_c2) <= fyd (8.3.6 --
    FCO-05; no CA-50, 2 por mil dao 420 MPa, abaixo de fyd = 435 MPa).
    """
    eps_b = np.array([concreto.eps_reta_b_pmilh])
    sig_c = float(concreto._curva_efetiva.sigma(eps_b)[0])
    sig_s = float(_sigma_aco(eps_b, aco.fyd_kncm2, aco.Es_kncm2, aco.eps_yd_pmilh)[0])
    As = secao.As_total_cm2
    return sig_c * (secao.Ac_cm2 - As) + sig_s * As


def Nd_min_kn(secao: SecaoRetangular, aco: Aco) -> float:
    """Nd minimo: tracao pura, eps_s = -10 por mil em todas as barras.
    Retorna valor negativo (por convencao, compressao positiva)."""
    return -aco.fyd_kncm2 * secao.As_total_cm2


# ---------------------------------------------------------------------------
# Solvers
# ---------------------------------------------------------------------------
EPS_ALPHA = 1e-3               # folga nas pontas da faixa do quadrante (rad)
PASSO_ALPHA = math.pi / 16.0   # passo da busca de alpha no circulo inteiro


def _solve_x_generico(residual, h_inc: float, Nd: float, n_sample: int = 40,
                      contexto: str = "") -> float:
    """brentq em N(x_LN) - Nd = 0. Amostra n_sample pontos, escolhe primeiro
    intervalo com troca de sinal.

    No dominio 5 o esforco normal so chega a reta b (Nd_max) quando x_LN
    tende ao infinito; se a amostragem ate 20h nao alcanca Nd, a busca segue
    para x_LN de 100h a 10^6 h (FCO-05: o pre-teste aprovava e o solver
    quebrava).
    """
    x_min = 1e-3
    x_max = 5.0 * h_inc

    xs = np.linspace(x_min, x_max, n_sample)
    Ns = np.array([residual(x) for x in xs])
    sign_changes = np.where(np.diff(np.sign(Ns)) != 0)[0]

    if len(sign_changes) == 0:
        # Talvez x_max insuficiente -- expande
        x_max *= 4.0
        xs = np.linspace(x_min, x_max, n_sample)
        Ns = np.array([residual(x) for x in xs])
        sign_changes = np.where(np.diff(np.sign(Ns)) != 0)[0]
        if len(sign_changes) == 0:
            if Ns[-1] < 0.0:
                x_a, r_a = float(xs[-1]), float(Ns[-1])
                for fator in (1e2, 1e3, 1e4, 1e6):
                    x_b = fator * h_inc
                    r_b = residual(x_b)
                    if r_b >= 0.0:
                        return float(brentq(residual, x_a, x_b, xtol=1e-4, rtol=1e-6))
                    x_a, r_a = x_b, r_b
                if r_a >= -1e-6 * max(1.0, abs(Nd)):
                    return x_a  # compressao praticamente uniforme (reta b)
            raise ValueError(
                f"Sem raiz para x_LN{contexto}: Nd = {Nd:.1f} kN fora da faixa de N "
                f"alcançada pelos domínios 2 a 5, [{Nd + Ns.min():.1f}, "
                f"{Nd + Ns.max():.1f}] kN."
            )

    i = int(sign_changes[0])
    return float(brentq(residual, xs[i], xs[i + 1], xtol=1e-4, rtol=1e-6))


def _solve_x_LN(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    alpha: float,
    Nd: float,
    n_grid: int = 80,
    n_sample: int = 40,
) -> float:
    """brentq em N(x_LN) - Nd = 0 (ver `_solve_x_generico`)."""
    h_inc, _ = _h_inc_yp_max(secao, alpha)

    def residual(x: float) -> float:
        N, _, _ = esforcos_resistentes(secao, concreto, aco, alpha, x, n_grid)
        return N - Nd

    return _solve_x_generico(residual, h_inc, Nd, n_sample,
                             f" (α = {math.degrees(alpha):.1f}°)")


def _wrap_pi(a: float) -> float:
    """Leva a diferenca de dois angulos para (-pi, pi] (sem mexer se ja estiver)."""
    if a > math.pi:
        a -= 2.0 * math.pi
    elif a <= -math.pi:
        a += 2.0 * math.pi
    return a


def _resolver_direcao(esforcos, solve_x, theta_d: float):
    """Plano ultimo com N = Nd e momento resistente na direcao theta_d.

    theta_d = atan2(Myd, Mxd), COM SINAL (FCO-03): o solver busca alpha no
    circulo inteiro, o que vale para secao e armadura assimetricas.
    `esforcos(alpha, x)` -> (N, Mx, My); `solve_x(alpha)` -> x_LN para Nd.

    1. Flexao normal (theta_d sobre um eixo): LN paralela ao eixo; aceita se
       o momento resistente sair na direcao pedida (secao simetrica em
       relacao ao plano de flexao).
    2. Faixa do quadrante de theta_d (para Mxd, Myd > 0 e a faixa
       [-pi/2, 0] de sempre).
    3. Busca no circulo inteiro, em passos de pi/16, a partir da LN
       perpendicular a direcao do momento.

    Devolve (alpha, x_LN, Mx, My, uniaxial). Levanta ValueError se nao achar.
    """
    c_d, s_d = math.cos(theta_d), math.sin(theta_d)

    def avaliar(alpha: float) -> tuple[float, float, float]:
        x = solve_x(alpha)
        _, Mx, My = esforcos(alpha, x)
        return x, Mx, My

    def desvio(alpha: float) -> float:
        _, Mx, My = avaliar(alpha)
        return _wrap_pi(math.atan2(My, Mx) - theta_d)

    def desvio_seguro(alpha: float) -> float:
        try:
            return desvio(alpha)
        except (ValueError, RuntimeError):
            return float("nan")

    def aceitar(alpha: float):
        x, Mx, My = avaliar(alpha)
        if abs(_wrap_pi(math.atan2(My, Mx) - theta_d)) < 1e-2:
            return _wrap_pi(alpha), x, Mx, My, False
        return None

    # 1) Flexao normal.
    alpha_fixo = None
    if abs(s_d) < TOL_UNIAXIAL:
        alpha_fixo = 0.0 if c_d > 0.0 else math.pi
    elif abs(c_d) < TOL_UNIAXIAL:
        alpha_fixo = -math.pi / 2.0 if s_d > 0.0 else math.pi / 2.0
    if alpha_fixo is not None:
        x, Mx, My = avaliar(alpha_fixo)
        MR = math.hypot(Mx, My)
        if (MR > 0.0 and Mx * c_d + My * s_d > 0.0
                and abs(Mx * s_d - My * c_d) <= TOL_UNIAXIAL * MR):
            return alpha_fixo, x, Mx, My, True

    # 2) Faixa do quadrante.
    q = math.floor(theta_d / (math.pi / 2.0))
    base = q * (math.pi / 2.0)
    a_lo, a_hi = -base - math.pi / 2.0 + EPS_ALPHA, -base - EPS_ALPHA
    f_lo, f_hi = desvio_seguro(a_lo), desvio_seguro(a_hi)
    if math.isfinite(f_lo) and math.isfinite(f_hi) and f_lo * f_hi <= 0.0:
        try:
            r = aceitar(float(brentq(desvio, a_lo, a_hi, xtol=1e-4, rtol=1e-5)))
        except (ValueError, RuntimeError):
            r = None
        if r is not None:
            return r

    # 3) Circulo inteiro.
    alpha0 = -theta_d
    f0 = desvio_seguro(alpha0)
    if f0 == 0.0:
        r = aceitar(alpha0)
        if r is not None:
            return r
    sentido = 1.0 if not (f0 < 0.0) else -1.0
    for s in (sentido, -sentido):
        a_ant, f_ant = alpha0, f0
        for i in range(1, 17):
            a_i = alpha0 + s * i * PASSO_ALPHA
            f_i = desvio_seguro(a_i)
            if (math.isfinite(f_ant) and math.isfinite(f_i) and f_ant * f_i <= 0.0
                    and abs(f_ant) < math.pi / 2.0 and abs(f_i) < math.pi / 2.0):
                try:
                    r = aceitar(float(brentq(desvio, min(a_ant, a_i), max(a_ant, a_i),
                                             xtol=1e-4, rtol=1e-5)))
                except (ValueError, RuntimeError):
                    r = None
                if r is not None:
                    return r
            a_ant, f_ant = a_i, f_i
    raise ValueError(
        f"Solver alpha sem bracketing: nenhuma posição da LN leva o momento "
        f"resistente à direção θ = {math.degrees(theta_d):.1f}°."
    )


def _resolver_direcao_ret(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    Nd: float,
    theta_d: float,
    n_grid: int = 80,
):
    """`_resolver_direcao` para SecaoRetangular."""
    return _resolver_direcao(
        lambda a, x: esforcos_resistentes(secao, concreto, aco, a, x, n_grid),
        lambda a: _solve_x_LN(secao, concreto, aco, a, Nd, n_grid),
        theta_d,
    )


def _solve_alpha(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    Nd: float,
    theta_d: float,
    n_grid: int = 80,
) -> tuple[float, float]:
    """Retorna (alpha, x_LN) do plano ultimo com momento na direcao theta_d.

    theta_d = atan2(MRy, MRx), com sinal (qualquer quadrante). Para
    Mxd, Myd > 0 (theta_d entre 0 e pi/2) a busca e a de sempre, em
    [-pi/2, 0] (compressao em +x, +y).
    """
    alpha, x, _, _, _ = _resolver_direcao_ret(secao, concreto, aco, Nd, theta_d, n_grid)
    return alpha, x


def _esforcos_uniformes_ret(
    secao: SecaoRetangular, concreto: Concreto, aco: Aco, eps: float,
) -> tuple[float, float, float]:
    """(N, Mx, My) com deformacao uniforme eps (por mil) na secao inteira."""
    e = np.array([eps], dtype=float)
    sc = float(concreto._curva_efetiva.sigma(e)[0])
    ss = float(_sigma_aco(e, aco.fyd_kncm2, aco.Es_kncm2, aco.eps_yd_pmilh)[0])
    arr = secao._barras_xyA
    if arr.shape[0] == 0:
        return sc * secao.Ac_cm2, 0.0, 0.0
    As = float(arr[:, 2].sum())
    return (sc * (secao.Ac_cm2 - As) + ss * As,
            (ss - sc) * float((arr[:, 2] * arr[:, 1]).sum()),
            (ss - sc) * float((arr[:, 2] * arr[:, 0]).sum()))


def _origem_dentro(esforcos_unif, resolver, Nd: float, eps_b: float, escala_M: float) -> bool:
    """O ponto (Nd, 0, 0) esta dentro da envoltoria resistente com N = Nd?

    Com secao ou armadura assimetrica (ou mais de um concreto), o centro
    plastico nao coincide com o centroide e, perto de Nd_max, a envoltoria
    de N fixo pode nao conter a origem: nem o momento nulo e resistido.
    Um ponto interior C e o estado de deformacao uniforme com N = Nd
    (admissivel, nao ultimo). Se C estiver na origem, ela esta dentro;
    senao, pela convexidade, a origem esta dentro se e so se o raio que
    parte dela no sentido oposto a C encontra a envoltoria.
    """
    N_lo = esforcos_unif(-EPS_SU)[0]
    N_hi = esforcos_unif(eps_b)[0]
    if not (N_lo < Nd < N_hi):
        return True  # fora dessa faixa decidem o pre-teste e o solver
    eps_N = brentq(lambda e: esforcos_unif(e)[0] - Nd, -EPS_SU, eps_b,
                   xtol=1e-12, rtol=4.0 * np.finfo(float).eps)
    _, Cx, Cy = esforcos_unif(eps_N)
    if math.hypot(Cx, Cy) <= 1e-9 * escala_M:
        return True
    try:
        resolver(math.atan2(-Cy, -Cx))
    except (ValueError, RuntimeError):
        return False
    return True


def _origem_dentro_ret(secao, concreto, aco, Nd, n_grid) -> bool:
    return _origem_dentro(
        lambda e: _esforcos_uniformes_ret(secao, concreto, aco, e),
        lambda th: _resolver_direcao_ret(secao, concreto, aco, Nd, th, n_grid),
        Nd, concreto.eps_reta_b_pmilh,
        max(abs(Nd), Nd_max_kn(secao, concreto, aco)) * max(secao.base_cm, secao.altura_cm),
    )


MSG_ORIGEM_FORA = (
    "Com Nd = {Nd:.1f} kN nem o momento nulo é resistido: o centro plástico "
    "da seção não coincide com o centroide e a envoltória resistente para "
    "esse Nd não contém a origem."
)


# ---------------------------------------------------------------------------
# API alta-nivel
# ---------------------------------------------------------------------------
def momento_resistente_fco(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    Nd_kn: float,
    theta_d_rad: float,
    n_grid: int = 80,
) -> dict:
    """Calcula (MRx, MRy) tal que arctan(MRy/MRx) = theta_d_rad e Nr = Nd.

    theta_d_rad = atan2(MRy, MRx) em qualquer quadrante: 0 -> +Mx,
    pi/2 -> +My, pi -> -Mx, -pi/2 -> -My. MRx_kncm e MRy_kncm sao os
    modulos; Mx_kncm e My_kncm, os valores com sinal.
    """
    alpha, x_LN, Mx, My, _ = _resolver_direcao_ret(
        secao, concreto, aco, Nd_kn, theta_d_rad, n_grid)
    return {
        "MRx_kncm": abs(Mx),
        "MRy_kncm": abs(My),
        "Mx_kncm": Mx,
        "My_kncm": My,
        "MR_kncm": math.hypot(Mx, My),
        "alpha_rad": alpha,
        "alpha_graus": math.degrees(alpha),
        "x_LN_cm": x_LN,
    }


def _verificar_uniaxial(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    Nd_kn: float,
    Md_kncm: float,
    alpha: float,
    n_grid: int = 80,
) -> dict:
    """Verifica seção com flexão composta normal (alpha fixo).

    Mantida por compatibilidade: `verificar_fco` já trata a flexão normal
    (com sinal) em `_resolver_direcao`.
    """
    x_LN = _solve_x_LN(secao, concreto, aco, alpha, Nd_kn, n_grid)
    _, Mx, My = esforcos_resistentes(secao, concreto, aco, alpha, x_LN, n_grid)
    Mr = math.hypot(Mx, My)
    razao = Mr / abs(Md_kncm) if abs(Md_kncm) > 0 else float("inf")
    return {
        "status": _status_razao(razao),
        "razao": razao,
        "alpha_rad": alpha,
        "alpha_graus": math.degrees(alpha),
        "x_LN_cm": x_LN,
        "MRx_kncm": abs(Mx),
        "MRy_kncm": abs(My),
        "uniaxial": True,
    }


def verificar_fco(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    Nd_kn: float,
    Mxd_kncm: float,
    Myd_kncm: float,
    n_grid: int = 80,
) -> dict:
    """Verifica seção retangular sob FCO. Retorna dict com diagnóstico:
        - status: "OK" | "NAO_VERIFICA" | "FORA_RANGE" | "NAO_CONVERGIU"
        - razao: MR/MS (>= 1 OK)
        - alpha_rad / alpha_graus
        - x_LN_cm
        - MRx_kncm / MRy_kncm

    Os sinais de Mxd e Myd são respeitados (FCO-03): a resistência é
    calculada na direção de (Mxd, Myd), o que vale para seção e armadura
    assimétricas. O momento mínimo de 11.3.3.4.3 não é aplicado aqui: a
    envoltória mínima fica em `verificacao_pilar.py`.

    Seção ou armadura assimétrica com Nd alto: se o centro plástico não
    coincide com o centroide, a envoltória de N fixo pode não conter a
    origem -- nem Nd centrado é resistido. Nesse caso a função devolve
    NAO_VERIFICA com razão 0 (e, em pilar, a envoltória mínima da
    Figura 11.3, que envolve a origem, também não seria atendida).
    """
    Nd_max = Nd_max_kn(secao, concreto, aco)
    Nd_min = Nd_min_kn(secao, aco)
    if Nd_kn > Nd_max:
        return {
            "status": "FORA_RANGE",
            "razao": -1.0,
            "mensagem": f"Nd = {Nd_kn:.1f} kN > Nd,máx = {Nd_max:.1f} kN (compressão uniforme).",
        }
    if Nd_kn < Nd_min:
        return {
            "status": "FORA_RANGE",
            "razao": -1.0,
            "mensagem": f"Nd = {Nd_kn:.1f} kN < Nd,mín = {Nd_min:.1f} kN (tração uniforme).",
        }

    Md_total = math.hypot(Mxd_kncm, Myd_kncm)
    if Md_total < 1e-6:
        return {
            "status": "OK",
            "razao": float("inf"),
            "alpha_rad": 0.0,
            "x_LN_cm": float("nan"),
            "comentario": "Compressao/tracao sem flexao.",
        }

    theta_d = math.atan2(Myd_kncm, Mxd_kncm)
    try:
        if not _origem_dentro_ret(secao, concreto, aco, Nd_kn, n_grid):
            return {"status": "NAO_VERIFICA", "razao": 0.0,
                    "mensagem": MSG_ORIGEM_FORA.format(Nd=Nd_kn)}
        alpha_sol, x_sol, Mx_r, My_r, uniaxial = _resolver_direcao_ret(
            secao, concreto, aco, Nd_kn, theta_d, n_grid
        )
    except (ValueError, RuntimeError) as e:
        return {"status": "NAO_CONVERGIU", "razao": -1.0, "mensagem": str(e)}

    return _resultado_verificacao(alpha_sol, x_sol, Mx_r, My_r, Md_total, uniaxial)


def _status_razao(razao: float) -> str:
    """OK so com MR >= MS (17.2.1): razao >= 1, sem folga (FCO-11)."""
    return "OK" if razao >= 1.0 else "NAO_VERIFICA"


def _resultado_verificacao(alpha, x_LN, Mx_r, My_r, Md_total, uniaxial) -> dict:
    Mr = math.hypot(Mx_r, My_r)
    razao = Mr / Md_total
    r = {
        "status": _status_razao(razao),
        "razao": razao,
        "alpha_rad": alpha,
        "alpha_graus": math.degrees(alpha),
        "x_LN_cm": x_LN,
        "MRx_kncm": abs(Mx_r),
        "MRy_kncm": abs(My_r),
        "MR_kncm": Mr,
    }
    if uniaxial:
        r["uniaxial"] = True
    return r


def verificar_fco_simplificado(
    MRxd_kncm: float,
    MRyd_kncm: float,
    Mxd_kncm: float,
    Myd_kncm: float,
    expoente: float = 1.0,
    secao_retangular: bool = True,
) -> float:
    """Equacao de interacao simplificada (NBR 6118:2026, 17.2.5):

        (Mxd/MRxd)^a + (Myd/MRyd)^a <= 1.0

    Retorna valor da soma. <= 1.0 verifica.
    A norma preve a = 1 em geral (a favor da seguranca) e a = 1,2 para
    secao retangular. Valores de 1,2 a 2,0 aparecem em Bresler/CEB, mas
    nao na NBR: acima de 1,2 (ou acima de 1 com `secao_retangular=False`)
    a funcao calcula e emite `AvisoNBR6118`.
    """
    if MRxd_kncm <= 0 or MRyd_kncm <= 0:
        raise ValueError("MRxd e MRyd devem ser positivos.")
    limite = 1.2 if secao_retangular else 1.0
    if expoente > limite:
        warnings.warn(
            f"Expoente α = {expoente:g} acima do previsto na 17.2.5 da NBR 6118:2026 "
            f"para {'seção retangular (α = 1,2)' if secao_retangular else 'seção não retangular (α = 1)'}; "
            "o resultado fica contra a segurança em relação à norma.",
            AvisoNBR6118,
            stacklevel=2,
        )
    return (abs(Mxd_kncm) / MRxd_kncm) ** expoente + (
        abs(Myd_kncm) / MRyd_kncm
    ) ** expoente


def razao_dc_radial(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    Nd_kn: float,
    Mxd_kncm: float,
    Myd_kncm: float,
    n_grid: int = 60,
) -> dict:
    """Razao D/C como interseccao radial 3D na envoltoria resistente.

    Para um ponto solicitante S = (Nd, Mxd, Myd) no espaco (N, Mx, My),
    procura lambda > 0 tal que lambda*S esteja exatamente sobre a envoltoria
    resistente. D/C = 1/lambda. lambda > 1 significa ponto interno (OK),
    lambda < 1 significa fora (NAO_VERIFICA).

    Equivalente ao SDRD do TQS: combina utilizacao de Nd e Md numa unica
    razao, ao inves de verificar so Md/MRd como `verificar_fco`.

    Algoritmo: para cada lambda candidato, verifica se a envoltoria de momentos
    em Nd_alvo = lambda*Nd na direcao (Mxd, Myd) tem norma == lambda*|MS|.
    Brentq em lambda. A direcao respeita os sinais de Mxd e Myd (FCO-03) e
    a flexao normal (Mxd ou Myd nulo) usa a LN paralela ao eixo (FCO-18).
    """
    MS = math.hypot(Mxd_kncm, Myd_kncm)
    Nrd_max = Nd_max_kn(secao, concreto, aco)
    Nrd_min = Nd_min_kn(secao, aco)

    # Caso compressao/tracao quase pura: solucao analitica direta
    if MS < 1e-6:
        if abs(Nd_kn) < 1e-6:
            return {
                "status": "OK", "razao_dc": 0.0, "lambda": float("inf"),
                "comentario": "Ponto na origem.",
            }
        if Nd_kn > 0:
            lam = Nrd_max / Nd_kn
        else:
            lam = Nrd_min / Nd_kn  # ambos negativos -> positivo
        return {
            "status": "OK" if lam >= 1.0 else "NAO_VERIFICA",
            "razao_dc": 1.0 / lam if lam > 0 else float("inf"),
            "lambda": lam,
            "comentario": "Sem flexao: razao = Nd / Nrd.",
        }

    theta_d = math.atan2(Myd_kncm, Mxd_kncm)

    # lambda_max axial: nao podemos ultrapassar Nrd_max nem ir abaixo de Nrd_min
    if Nd_kn > 1e-6:
        lam_axial_max = Nrd_max / Nd_kn
    elif Nd_kn < -1e-6:
        lam_axial_max = Nrd_min / Nd_kn  # ambos negativos
    else:
        lam_axial_max = float("inf")  # Nd ~ 0, lambda nao limitado por axial

    def g(lam: float) -> float:
        Nd_target = lam * Nd_kn
        if Nd_target > Nrd_max - 1e-3 or Nd_target < Nrd_min + 1e-3:
            return -lam * MS - 1.0
        try:
            if not _origem_dentro_ret(secao, concreto, aco, Nd_target, n_grid):
                return -lam * MS - 1.0  # nem (lam*Nd, 0, 0) e resistido
            _, _, Mx_r, My_r, _ = _resolver_direcao_ret(
                secao, concreto, aco, Nd_target, theta_d, n_grid
            )
            MR = math.hypot(Mx_r, My_r)
        except (ValueError, RuntimeError):
            return float("nan")
        # Equilibrio na envoltoria: MR == lam*MS  =>  MR/lam == MS
        return MR / lam - MS

    # Bracketing: g(lam) > 0 -> ponto interno (lam pode crescer);
    #             g(lam) < 0 -> ponto externo (lam deve diminuir).
    g1 = g(1.0)
    if not math.isfinite(g1):
        return {
            "status": "NAO_CONVERGIU", "razao_dc": float("nan"),
            "lambda": float("nan"),
            "mensagem": "g(1.0) nao avaliavel (provavel solver alpha).",
        }

    if g1 > 0:
        lo, hi = 1.0, min(2.0, 0.95 * lam_axial_max if lam_axial_max < float("inf") else 100.0)
        if hi <= lo:
            return {
                "status": "OK", "razao_dc": 1.0 / lam_axial_max,
                "lambda": lam_axial_max,
                "comentario": "Limitado por Nrd_max.",
            }
        for _ in range(20):
            gh = g(hi)
            if math.isfinite(gh) and gh < 0:
                break
            new_hi = min(hi * 1.5, 0.95 * lam_axial_max) if lam_axial_max < float("inf") else hi * 1.5
            if new_hi <= hi * 1.001:
                # bateu no axial
                return {
                    "status": "OK", "razao_dc": 1.0 / hi, "lambda": hi,
                    "comentario": "Envoltoria axial atingida (lam_max).",
                }
            if math.isfinite(gh):
                lo = hi  # so avanca lo onde g(lo) > 0 e finito
            hi = new_hi
        else:
            return {
                "status": "NAO_CONVERGIU", "razao_dc": float("nan"),
                "lambda": float("nan"),
                "mensagem": "Nao achou bracketing superior.",
            }
    else:
        lo, hi = 1.0 / 2.0, 1.0
        for _ in range(20):
            gl = g(lo)
            if math.isfinite(gl) and gl > 0:
                break
            lo *= 0.5
            if lo < 1e-4:
                return {
                    "status": "NAO_CONVERGIU", "razao_dc": float("nan"),
                    "lambda": float("nan"),
                    "mensagem": "Nao achou bracketing inferior.",
                }
        else:
            return {
                "status": "NAO_CONVERGIU", "razao_dc": float("nan"),
                "lambda": float("nan"),
                "mensagem": "Nao achou bracketing inferior (loop esgotou).",
            }

    try:
        lam_sol = float(brentq(g, lo, hi, xtol=1e-3, rtol=1e-4, maxiter=50))
    except (ValueError, RuntimeError) as e:
        return {
            "status": "NAO_CONVERGIU", "razao_dc": float("nan"),
            "lambda": float("nan"),
            "mensagem": f"brentq falhou: {e}",
        }

    return {
        "status": "OK" if lam_sol >= 1.0 else "NAO_VERIFICA",
        "razao_dc": 1.0 / lam_sol,
        "lambda": lam_sol,
    }


def envoltoria_resistencia(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    Nd_kn: float,
    n_pontos: int = 24,
    n_grid: int = 60,
) -> list[tuple[float, float]]:
    """Diagrama de interacao MRx-MRy para Nd fixo. n_pontos no quadrante 0..pi/2."""
    pontos: list[tuple[float, float]] = []
    eps_t = 0.01
    thetas = np.linspace(eps_t, math.pi / 2.0 - eps_t, n_pontos)
    for theta in thetas:
        try:
            r = momento_resistente_fco(secao, concreto, aco, Nd_kn, float(theta), n_grid)
            pontos.append((r["MRx_kncm"], r["MRy_kncm"]))
        except ValueError:
            continue
    return pontos


def dimensionar_as_fco(
    base_cm: float,
    altura_cm: float,
    cobrimento_cm: float,
    nx: int,
    ny: int,
    fi_l_mm: float,
    concreto: Concreto,
    aco: Aco,
    Nd_kn: float,
    Mxd_kncm: float,
    Myd_kncm: float,
    fi_t_mm: float = 5.0,
    As_total_min_cm2: float | None = None,
    As_total_max_cm2: float | None = None,
    tol: float = 0.01,
    iter_max: int = 30,
    n_grid: int = 60,
    aplicar_as_min_pilar: bool = True,
) -> dict:
    """Itera area total da armadura ate razao=1.0. Geometria das barras
    permanece fixa (perimetral PFOC); apenas a area de cada barra varia.

    Armadura minima de pilar (17.3.5.3.1, FCO-09): As,min = 0,15*Nd/fyd >=
    0,004*Ac, sempre aplicada (`aplicar_as_min_pilar=False` so para quem
    usa a rotina fora de pilar). `As_total_min_cm2` e um piso adicional do
    usuario: vale o maior dos dois. As,max padrao = 8 % Ac (17.3.5.3.2 --
    inclui a regiao de emendas; fora dela o limite pratico e 4 %).

    O As devolvido tem sempre razao >= 1 (a bissecao para em
    1 <= razao < 1 + tol).
    """
    n_barras_total = 2 * (nx + ny) - 4
    if As_total_max_cm2 is None:
        As_total_max_cm2 = 0.08 * base_cm * altura_cm  # 8% (NBR limite superior)
    As_min_norma = (As_min_pilar_cm2(base_cm * altura_cm, Nd_kn, aco)
                    if aplicar_as_min_pilar else 0.0)
    if As_total_min_cm2 is None:
        As_min = As_min_norma if aplicar_as_min_pilar else 0.4
    else:
        As_min = max(As_total_min_cm2, As_min_norma)
    extras = {"As_min_cm2": As_min, "As_min_norma_cm2": As_min_norma}
    if As_min > As_total_max_cm2:
        return {
            "status": "INVIAVEL",
            "As_total_cm2": As_min,
            "razao": float("nan"),
            "comentario": (
                f"As,mín = {As_min:.2f} cm² acima de As,máx = "
                f"{As_total_max_cm2:.2f} cm² (17.3.5.3)."
            ),
            **extras,
        }

    def razao_para_As(As_total: float) -> float:
        area_unit = As_total / n_barras_total
        barras = armadura_perimetral_retangular(
            base_cm, altura_cm, cobrimento_cm, nx, ny, fi_l_mm, fi_t_mm,
            area_por_barra_cm2=area_unit,
        )
        secao = SecaoRetangular(base_cm, altura_cm, cobrimento_cm, barras)
        r = verificar_fco(secao, concreto, aco, Nd_kn, Mxd_kncm, Myd_kncm, n_grid)
        if r["status"] in ("FORA_RANGE", "NAO_CONVERGIU"):
            return -1.0
        return r["razao"]

    lo, hi = As_min, As_total_max_cm2
    r_lo = razao_para_As(lo)
    r_hi = razao_para_As(hi)

    if r_lo >= 1.0:
        return {
            "status": "OK",
            "As_total_cm2": lo,
            "razao": r_lo,
            "comentario": "As mínimo já resiste.",
            **extras,
        }
    if r_hi < 1.0:
        return {
            "status": "INVIAVEL",
            "As_total_cm2": hi,
            "razao": r_hi,
            "comentario": (
                f"Mesmo com As={hi:.1f} cm^2 (8% Ac) razao={r_hi:.3f} < 1."
            ),
            **extras,
        }

    r_hi_atual = r_hi
    for _ in range(iter_max):
        mid = 0.5 * (lo + hi)
        r_mid = razao_para_As(mid)
        if 1.0 <= r_mid < 1.0 + tol:
            return {"status": "OK", "As_total_cm2": mid, "razao": r_mid, **extras}
        if r_mid < 1.0:
            lo = mid
        else:
            hi, r_hi_atual = mid, r_mid
    return {
        "status": "OK",
        "As_total_cm2": hi,
        "razao": r_hi_atual,
        "comentario": f"Convergência parcial em {iter_max} iterações.",
        **extras,
    }


def As_min_pilar_cm2(Ac_cm2: float, Nd_kn: float, aco: Aco) -> float:
    """Armadura longitudinal minima de pilar, cm² (17.3.5.3.1):

        As,min = 0,15*Nd/fyd >= 0,004*Ac

    Com Nd de tracao (Nd < 0) sobra o piso de 0,004*Ac.
    """
    # Mesma expressao de nbr.As_min_pilar_cm2, mas com o fyd do objeto Aco
    # (que pode ter gama_s ou fyk proprios).
    return max(0.15 * max(Nd_kn, 0.0) / aco.fyd_kncm2, 0.004 * Ac_cm2)


# ---------------------------------------------------------------------------
# API alta-nivel para Secao poligonal
# ---------------------------------------------------------------------------
def _eps_reta_b_pol(secao: Secao) -> float:
    """Encurtamento uniforme da reta b com plano unico: o menor eps_c2 (e
    eps_cu) entre os concretos da secao."""
    return min(p.concreto.eps_reta_b_pmilh for p in secao.partes)


def Nd_max_kn_pol(secao: Secao, aco: Aco) -> float:
    """Nd maximo (compressao uniforme, reta b da Figura 17.1) para Secao
    poligonal.

    Encurtamento uniforme eps_b (plano unico: o menor eps_c2 dos
    concretos). Concreto de cada parte na sua curva (0,85*eta_c*fcd --
    FCO-01); barras com sigma_s(eps_b) <= fyd (FCO-05); cabos com a curva
    do aco de protensao no alongamento eps_b - eps_pre (17.2.4.2.1 --
    FCO-06). Barras e cabos descontam o concreto da parte em que estao.
    """
    eps_b = _eps_reta_b_pol(secao)
    e = np.array([eps_b])
    total = 0.0
    for parte in secao.partes:
        total += float(parte.concreto._curva_efetiva.sigma(e)[0]) * _polygon_area(parte.polygon)
    if secao._barras_xyA.shape[0] > 0:
        A_b = secao._barras_xyA[:, 2]
        eps_bs = np.full(A_b.shape[0], eps_b)
        sig_s = _sigma_aco(eps_bs, aco.fyd_kncm2, aco.Es_kncm2, aco.eps_yd_pmilh)
        sig_c = _sigma_c_nas_partes(secao, secao._barras_parte, eps_bs)
        total += float(((sig_s - sig_c) * A_b).sum())
    for i, c in enumerate(secao.cabos):
        sig_p = float(_cabo_curva(c).sigma(np.array([eps_b - c.eps_pre_pmilh]))[0])
        conc = secao.partes[int(secao._cabos_parte[i])].concreto
        sig_c = float(conc._curva_efetiva.sigma(e)[0])
        total += (sig_p - sig_c) * c.area_cm2
    return total


def Nd_min_kn_pol(secao: Secao, aco: Aco) -> float:
    """Nd minimo (tracao pura, reta a) para Secao poligonal: barras em
    -fyd e cabos com a curva no alongamento -10 - eps_pre por mil
    (17.2.4.2.1 -- FCO-06). Retorna valor negativo."""
    total = -aco.fyd_kncm2 * secao.As_total_cm2
    for c in secao.cabos:
        sig_p = float(_cabo_curva(c).sigma(np.array([-EPS_SU - c.eps_pre_pmilh]))[0])
        total += sig_p * c.area_cm2
    return total


def _solve_x_LN_pol(
    secao: Secao,
    aco: Aco,
    alpha: float,
    Nd: float,
    n_sample: int = 40,
) -> float:
    h_inc, _ = _h_inc_yp_max_pol(secao, alpha)

    def residual(x: float) -> float:
        N, _, _ = esforcos_resistentes_pol(secao, aco, alpha, x)
        return N - Nd

    return _solve_x_generico(residual, h_inc, Nd, n_sample,
                             f" (seção poligonal, α = {math.degrees(alpha):.1f}°)")


def _resolver_direcao_pol(secao: Secao, aco: Aco, Nd: float, theta_d: float):
    """`_resolver_direcao` para Secao poligonal."""
    return _resolver_direcao(
        lambda a, x: esforcos_resistentes_pol(secao, aco, a, x),
        lambda a: _solve_x_LN_pol(secao, aco, a, Nd),
        theta_d,
    )


def _polygon_area_centroide(
    polygon: tuple[tuple[float, float], ...],
) -> tuple[float, float, float]:
    """(area > 0, x_c, y_c) do poligono fechado."""
    A2 = Sx6 = Sy6 = 0.0
    for i in range(len(polygon) - 1):
        x0, y0 = polygon[i]
        x1, y1 = polygon[i + 1]
        cr = x0 * y1 - x1 * y0
        A2 += cr
        Sy6 += (x0 + x1) * cr
        Sx6 += (y0 + y1) * cr
    if A2 == 0.0:
        return 0.0, 0.0, 0.0
    return abs(A2) / 2.0, Sy6 / (3.0 * A2), Sx6 / (3.0 * A2)


def _esforcos_uniformes_pol(secao: Secao, aco: Aco, eps: float) -> tuple[float, float, float]:
    """(N, Mx, My) com deformacao uniforme eps (por mil) na Secao poligonal."""
    e = np.array([eps], dtype=float)
    N = Mx = My = 0.0
    for parte in secao.partes:
        A, xc, yc = _polygon_area_centroide(parte.polygon)
        sc = float(parte.concreto._curva_efetiva.sigma(e)[0])
        N += sc * A
        Mx += sc * A * yc
        My += sc * A * xc
    arr = secao._barras_xyA
    if arr.shape[0] > 0:
        eb = np.full(arr.shape[0], float(eps))
        d = (_sigma_aco(eb, aco.fyd_kncm2, aco.Es_kncm2, aco.eps_yd_pmilh)
             - _sigma_c_nas_partes(secao, secao._barras_parte, eb)) * arr[:, 2]
        N += float(d.sum())
        Mx += float((d * arr[:, 1]).sum())
        My += float((d * arr[:, 0]).sum())
    for i, c in enumerate(secao.cabos):
        sp = float(_cabo_curva(c).sigma(np.array([eps - c.eps_pre_pmilh]))[0])
        sc = float(secao.partes[int(secao._cabos_parte[i])].concreto._curva_efetiva.sigma(e)[0])
        d = (sp - sc) * c.area_cm2
        N += d
        Mx += d * c.y_cm
        My += d * c.x_cm
    return N, Mx, My


def _origem_dentro_pol(secao: Secao, aco: Aco, Nd: float) -> bool:
    x0, y0, x1, y1 = _bbox_secao(secao)
    escala = max(abs(Nd), Nd_max_kn_pol(secao, aco)) * math.hypot(x1 - x0, y1 - y0)
    return _origem_dentro(
        lambda e: _esforcos_uniformes_pol(secao, aco, e),
        lambda th: _resolver_direcao_pol(secao, aco, Nd, th),
        Nd, _eps_reta_b_pol(secao), escala,
    )


def _solve_alpha_pol(
    secao: Secao,
    aco: Aco,
    Nd: float,
    theta_d: float,
) -> tuple[float, float]:
    """(alpha, x_LN) com momento na direcao theta_d = atan2(MRy, MRx), com sinal."""
    alpha, x, _, _, _ = _resolver_direcao_pol(secao, aco, Nd, theta_d)
    return alpha, x


def verificar_fco_pol(
    secao: Secao,
    aco: Aco,
    Nd_kn: float,
    Mxd_kncm: float,
    Myd_kncm: float,
) -> dict:
    """Versao Secao poligonal de verificar_fco. Suporta multi-fck.

    Respeita os sinais de Mxd e Myd (FCO-03): vale para seções L, T, U e
    armaduras assimétricas em qualquer orientação.
    """
    Nd_max = Nd_max_kn_pol(secao, aco)
    Nd_min = Nd_min_kn_pol(secao, aco)
    if Nd_kn > Nd_max:
        return {
            "status": "FORA_RANGE",
            "razao": -1.0,
            "mensagem": f"Nd = {Nd_kn:.1f} kN > Nd,máx = {Nd_max:.1f} kN (compressão uniforme).",
        }
    if Nd_kn < Nd_min:
        return {
            "status": "FORA_RANGE",
            "razao": -1.0,
            "mensagem": f"Nd = {Nd_kn:.1f} kN < Nd,mín = {Nd_min:.1f} kN (tração uniforme).",
        }

    Md_total = math.hypot(Mxd_kncm, Myd_kncm)
    if Md_total < 1e-6:
        return {
            "status": "OK",
            "razao": float("inf"),
            "alpha_rad": 0.0,
            "x_LN_cm": float("nan"),
            "comentario": "Compressao/tracao sem flexao.",
        }

    theta_d = math.atan2(Myd_kncm, Mxd_kncm)
    try:
        if not _origem_dentro_pol(secao, aco, Nd_kn):
            return {"status": "NAO_VERIFICA", "razao": 0.0,
                    "mensagem": MSG_ORIGEM_FORA.format(Nd=Nd_kn)}
        alpha_sol, x_sol, Mx_r, My_r, uniaxial = _resolver_direcao_pol(
            secao, aco, Nd_kn, theta_d)
    except (ValueError, RuntimeError) as e:
        return {"status": "NAO_CONVERGIU", "razao": -1.0, "mensagem": str(e)}

    return _resultado_verificacao(alpha_sol, x_sol, Mx_r, My_r, Md_total, uniaxial)


def momento_resistente_fco_pol(
    secao: Secao,
    aco: Aco,
    Nd_kn: float,
    theta_d_rad: float,
) -> dict:
    """Calcula (MRx, MRy) tal que arctan(MRy/MRx) = theta_d_rad e Nr = Nd.

    theta_d_rad em qualquer quadrante (ver `momento_resistente_fco`).
    """
    alpha, x_LN, Mx, My, _ = _resolver_direcao_pol(secao, aco, Nd_kn, theta_d_rad)
    return {
        "MRx_kncm": abs(Mx),
        "MRy_kncm": abs(My),
        "Mx_kncm": Mx,
        "My_kncm": My,
        "MR_kncm": math.hypot(Mx, My),
        "alpha_rad": alpha,
        "alpha_graus": math.degrees(alpha),
        "x_LN_cm": x_LN,
    }


# ---------------------------------------------------------------------------
# Exportacao e visualizacao da envoltoria
# ---------------------------------------------------------------------------
def exporta_envoltoria_csv(
    pontos: list[tuple[float, float]],
    csv_path: str,
) -> None:
    """Salva pontos da envoltoria (MRx, MRy) em arquivo CSV."""
    import csv
    from pathlib import Path

    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["MRx_kncm", "MRy_kncm"])
        for mrx, mry in pontos:
            w.writerow([f"{mrx:.4f}", f"{mry:.4f}"])


def plota_envoltoria(
    pontos: list[tuple[float, float]],
    png_path: str | None = None,
    titulo: str = "Envoltoria de Resistencia FCO",
):
    """Plota envoltoria (MRx, MRy). Retorna fig matplotlib.

    Se png_path fornecido, salva. Para visualizar interativamente, use
    `import matplotlib.pyplot as plt; plt.show()` apos.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError(
            "matplotlib necessario para plotar envoltoria. "
            "Instale com `pip install matplotlib`."
        ) from e

    if not pontos:
        raise ValueError("Nenhum ponto na envoltoria.")

    fig, ax = plt.subplots(figsize=(6, 5))
    xs = [p[0] for p in pontos] + [pontos[0][0]]
    ys = [p[1] for p in pontos] + [pontos[0][1]]
    ax.plot(xs, ys, "b-o", markersize=3, label="MR")
    ax.set_xlabel("MRx (kN.cm)")
    ax.set_ylabel("MRy (kN.cm)")
    ax.set_title(titulo)
    ax.grid(True)
    ax.axhline(0, color="k", linewidth=0.5)
    ax.axvline(0, color="k", linewidth=0.5)
    ax.set_aspect("equal", adjustable="box")

    if png_path:
        from pathlib import Path
        Path(png_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(png_path, dpi=150, bbox_inches="tight")

    return fig


# ---------------------------------------------------------------------------
# CLI minimo
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    """CLI: verifica uma secao retangular sob (Nsd, Mxd, Myd).

    Exemplo:
        python -m dimensionamento.rotinas.flexao_composta_obliqua \\
            --base 40.3 --altura 71.5 --fck 20 \\
            --nx 3 --ny 3 --fi-l 10 \\
            --nsd 1150 --mxd 23000 --myd 8625
    """
    import argparse
    import json

    p = argparse.ArgumentParser(
        description="Verificação FCO retangular (NBR 6118:2026)."
    )
    p.add_argument("--base", type=float, required=True, help="Base (cm)")
    p.add_argument("--altura", type=float, required=True, help="Altura (cm)")
    p.add_argument("--cob", type=float, default=2.5, help="Cobrimento (cm)")
    p.add_argument("--fck", type=float, required=True, help="fck (MPa)")
    p.add_argument("--nx", type=int, default=3, help="Barras por face horizontal")
    p.add_argument("--ny", type=int, default=3, help="Barras por face vertical")
    p.add_argument("--fi-l", type=float, default=16.0, help="Bitola long (mm)")
    p.add_argument("--fi-t", type=float, default=5.0, help="Bitola transv (mm)")
    p.add_argument("--area-barra", type=float, default=None,
                   help="Area por barra (cm2). Se omitido, calcula de fi-l.")
    p.add_argument("--nsd", type=float, required=True, help="Nsd (kN)")
    p.add_argument("--mxd", type=float, required=True, help="Mxd (kN.cm)")
    p.add_argument("--myd", type=float, required=True, help="Myd (kN.cm)")
    p.add_argument("--n-grid", type=int, default=80, help="Grid de fibras")
    p.add_argument("--csv", type=str, default=None,
                   help="Salva envoltoria de Nsd em CSV no caminho indicado.")
    p.add_argument("--png", type=str, default=None,
                   help="Salva grafico da envoltoria em PNG.")
    args = p.parse_args(argv)

    barras = armadura_perimetral_retangular(
        args.base, args.altura, args.cob, args.nx, args.ny, args.fi_l, args.fi_t,
        area_por_barra_cm2=args.area_barra,
    )
    s = SecaoRetangular(args.base, args.altura, args.cob, barras)
    c = Concreto(fck_mpa=args.fck)
    a = Aco()

    r = verificar_fco(s, c, a, args.nsd, args.mxd, args.myd, n_grid=args.n_grid)
    print(json.dumps(r, indent=2, ensure_ascii=False, default=str))

    if args.csv or args.png:
        pontos = envoltoria_resistencia(
            s, c, a, Nd_kn=args.nsd, n_pontos=24, n_grid=args.n_grid,
        )
        if args.csv:
            exporta_envoltoria_csv(pontos, args.csv)
            print(f"Envoltoria salva em {args.csv}")
        if args.png:
            plota_envoltoria(pontos, png_path=args.png,
                             titulo=f"Envoltoria FCO (Nsd={args.nsd} kN)")
            print(f"Grafico salvo em {args.png}")

    return 0 if r.get("status") in ("OK",) else 1


if __name__ == "__main__":
    sys.exit(main())
