"""Flexao Composta Obliqua (NBR 6118:2023).

Verificacao e dimensionamento de pilares retangulares submetidos a Nd,
Mxd e Myd. Metodologia baseada na monografia "PCalc" (Cardoso Jr., 2014)
e no projeto open-source PFOC (Daniel D. Grossmann).

Estrategia:
    - Materiais NBR: parabola-retangulo (concreto), bilinear (aco).
    - Integracao 2D vetorizada (fibras) sobre a secao retangular,
      com strain calculada a partir da posicao da LN inclinada.
    - Solver duplo aninhado:
        * Interno: brentq em x_LN dado alpha, tal que Nc + Ns = Nd.
        * Externo: brentq em alpha tal que arctan(MR_y/MR_x) = arctan(Myd/Mxd).
    - Pre-flight: calcula Nd_max (compressao pura) e Nd_min (tracao pura);
      valida Nd antes de chamar solver.
    - Fallback uniaxial: se um momento e nulo, fixa alpha e roda so o
      solver interno.
    - Diagnostico estruturado: dict com status, x_LN, alpha, residuo.

Convencoes:
    - fck em MPa. Geometria em cm. Forcas em kN, momentos em kN.cm.
    - Coords das barras: cartesianas, centradas no centroide da secao.
    - Mxd em torno do eixo x (causa flexao no plano y).
    - Myd em torno do eixo y (causa flexao no plano x).
    - alpha = angulo (rad) da LN com o eixo x. alpha=0 -> LN horizontal,
      flexao apenas em torno de x. alpha=pi/2 -> LN vertical.
    - Compressao positiva.

Validacoes embutidas:
    - PFOC __main__ (40.3x71.5, Nd=1150, Mdx=8625, Mdy=23000) -> razao=1.29.
    - Quadrada simetrica com Mxd=Myd -> alpha=45 graus, MRx=MRy.
    - Uniaxial (Myd=0): cross-check contra solver interno fixado em alpha=0.
    - NBR 17.79 cross-check: deve ser conservador relativamente ao numerico.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from functools import cached_property
from typing import Protocol, runtime_checkable

import numpy as np
from scipy.optimize import brentq


GAMA_C = 1.4
GAMA_S = 1.15
ES_KNCM2 = 21000.0    # modulo de elasticidade do aco
ALPHA_C = 0.85        # coeficiente do bloco de tensao do concreto


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
    """Parabola-retangulo NBR 6118:2023 (compressao apenas; tracao -> 0).

    Curva default para ELU. Valida tanto para fck <= 50 MPa (n=2, eps_c2=2,
    eps_cu=3.5) quanto para concretos de alta resistencia (n, eps_c2, eps_cu
    variaveis -- veja Concreto).
    """
    fcd_kncm2: float
    eps_c2_pmilh: float
    eps_cu_pmilh: float
    n_parabola: float
    alpha_c: float = ALPHA_C

    def sigma(self, eps: np.ndarray) -> np.ndarray:
        sigma = np.zeros_like(eps)
        mask_par = (eps > 0.0) & (eps <= self.eps_c2_pmilh)
        mask_rect = eps > self.eps_c2_pmilh
        if mask_par.any():
            arg = np.clip(1.0 - eps[mask_par] / self.eps_c2_pmilh, 0.0, 1.0)
            sigma[mask_par] = self.alpha_c * self.fcd_kncm2 * (
                1.0 - arg ** self.n_parabola
            )
        if mask_rect.any():
            sigma[mask_rect] = self.alpha_c * self.fcd_kncm2
        return sigma


@dataclass
class CurvaCParabolaRetanguloComTracao:
    """Parabola-retangulo na compressao + ramo linear/branda na tracao.

    Para analises onde a contribuicao da tracao do concreto importa (ELS-W
    no estagio I, validacoes pre-fissuracao). Modelo SECC tipo 2 adaptado:
        Compressao: parabola-retangulo NBR (igual a ParabolaRetangulo).
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

    def sigma(self, eps: np.ndarray) -> np.ndarray:
        sigma = np.zeros_like(eps)
        # Compressao: parabola + retangulo (mesmo da ParabolaRetangulo)
        mask_par = (eps > 0.0) & (eps <= self.eps_c2_pmilh)
        mask_rect = eps > self.eps_c2_pmilh
        if mask_par.any():
            arg = np.clip(1.0 - eps[mask_par] / self.eps_c2_pmilh, 0.0, 1.0)
            sigma[mask_par] = self.alpha_c * self.fcd_kncm2 * (
                1.0 - arg ** self.n_parabola
            )
        if mask_rect.any():
            sigma[mask_rect] = self.alpha_c * self.fcd_kncm2
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
    """Concreto NBR 6118:2023. Imutavel por convencao (nao alterar fck apos
    construcao -- as cached_property nao sao recalculadas).

    O parametro `curva` permite plugar uma curva constitutiva custom. Se
    nao informado, usa a parabola-retangulo NBR derivada de fck.
    """
    fck_mpa: float
    gama_c: float = GAMA_C
    curva: CurvaC | None = None

    @cached_property
    def fcd_kncm2(self) -> float:
        return (self.fck_mpa / self.gama_c) * 0.1

    @cached_property
    def eps_c2_pmilh(self) -> float:
        """Deformacao de inicio do patamar plastico (em por mil)."""
        if self.fck_mpa <= 50.0:
            return 2.0
        return 2.0 + 0.085 * (self.fck_mpa - 50.0) ** 0.53

    @cached_property
    def eps_cu_pmilh(self) -> float:
        """Deformacao ultima do concreto (em por mil)."""
        if self.fck_mpa <= 50.0:
            return 3.5
        return 2.6 + 35.0 * ((90.0 - self.fck_mpa) / 100.0) ** 4

    @cached_property
    def n_parabola(self) -> float:
        if self.fck_mpa <= 50.0:
            return 2.0
        return 1.4 + 23.4 * ((90.0 - self.fck_mpa) / 100.0) ** 4

    @cached_property
    def Eci_kncm2(self) -> float:
        """Modulo de elasticidade tangente inicial (NBR 8.2.8). kN/cm^2."""
        # alphaE = 1.0 (granito); para outros agregados, usuario pode passar
        # uma curva custom via `curva`.
        return 5600.0 * math.sqrt(self.fck_mpa) / 100.0  # MPa -> kN/cm^2

    @cached_property
    def fctk_inf_kncm2(self) -> float:
        """Resistencia a tracao caracteristica inferior (NBR 8.2.5). kN/cm^2."""
        if self.fck_mpa <= 50.0:
            fctm_mpa = 0.3 * self.fck_mpa ** (2.0 / 3.0)
        else:
            fctm_mpa = 2.12 * math.log(1.0 + 0.11 * self.fck_mpa)
        return 0.7 * fctm_mpa / 10.0

    @cached_property
    def _curva_efetiva(self) -> CurvaC:
        if self.curva is not None:
            return self.curva
        return CurvaCParabolaRetangulo(
            fcd_kncm2=self.fcd_kncm2,
            eps_c2_pmilh=self.eps_c2_pmilh,
            eps_cu_pmilh=self.eps_cu_pmilh,
            n_parabola=self.n_parabola,
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
    dos cabos ao equilibrio.
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
    Retorna ndarray (N, 3) com colunas (x_centro, y_centro, dA).
    """
    poly = parte.polygon
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

    if not elementos:
        return np.zeros((0, 3))
    return np.array(elementos, dtype=float)


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
    Usada como d para definir o pivo A do dominio 2."""
    if secao._barras_xyA.shape[0] == 0:
        return 1.0
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
    if secao._barras_xyA.shape[0] == 0:
        return 1.0
    cos_a, sin_a = math.cos(alpha), math.sin(alpha)
    x_b = secao._barras_xyA[:, 0]
    y_b = secao._barras_xyA[:, 1]
    yp_b = -x_b * sin_a + y_b * cos_a
    s_b = yp_max - yp_b
    return float(s_b.max())


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
) -> np.ndarray | float:
    """Deformacao (em por mil) numa fibra a profundidade s da face mais
    comprimida. s=0 e a face. Vetorizada.
    """
    x_lim_2_3 = eps_cu / (eps_cu + 10.0) * d_inc
    if x_LN <= x_lim_2_3:
        # Dominio 2: pivo A -> eps = 10 por mil em s=d_inc.
        return 10.0 * (x_LN - s) / (d_inc - x_LN)
    if x_LN <= h_inc:
        # Dominio 3/4/4a: pivo B -> eps = eps_cu em s=0.
        return eps_cu * (x_LN - s) / x_LN
    # Dominio 5: pivo C -> eps = eps_c2 em s = 3*h_inc/7.
    return eps_c2 * (x_LN - s) / (x_LN - 3.0 * h_inc / 7.0)


# ---------------------------------------------------------------------------
# Modelos constitutivos vetorizados
# ---------------------------------------------------------------------------
def _sigma_concreto(
    eps: np.ndarray,
    fcd: float,
    eps_c2: float,
    eps_cu: float,
    n_par: float,
) -> np.ndarray:
    """Parabola-retangulo NBR. Tracao -> 0. Vetorizado.

    Mantida para compatibilidade. Novas chamadas devem usar
    `concreto._curva_efetiva.sigma(eps)` diretamente.
    """
    return CurvaCParabolaRetangulo(
        fcd_kncm2=fcd,
        eps_c2_pmilh=eps_c2,
        eps_cu_pmilh=eps_cu,
        n_parabola=n_par,
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

    eps = _strain(S, x_LN, h_inc, d_inc, eps_c2, eps_cu)
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

    eps_b = _strain(s_b, x_LN, h_inc, d_inc, eps_c2, eps_cu)

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

    Cada parte usa seu proprio Concreto (curva, fcd, eps_c2, eps_cu).
    """
    if x_LN <= 0.0:
        return 0.0, 0.0, 0.0

    h_inc, yp_max = _h_inc_yp_max_pol(secao, alpha)
    d_inc = _d_inc_pol(secao, alpha, yp_max)
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
        eps_c2 = parte.concreto.eps_c2_pmilh
        eps_cu = parte.concreto.eps_cu_pmilh
        eps = _strain(S, x_LN, h_inc, d_inc, eps_c2, eps_cu)
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


def _esforcos_barras_pol(
    secao: Secao,
    aco: Aco,
    alpha: float,
    x_LN: float,
) -> tuple[float, float, float]:
    """Esforcos das barras na Secao poligonal.

    Para a subtracao do concreto deslocado (sigma_c em cada barra), usa o
    concreto da PRIMEIRA parte (simplificacao: assume todas as barras na
    mesma parte; relevante apenas se houver multi-fck).
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

    concreto = secao.partes[0].concreto
    h_inc, yp_max = _h_inc_yp_max_pol(secao, alpha)
    d_inc = _d_inc_pol(secao, alpha, yp_max)
    cos_a, sin_a = math.cos(alpha), math.sin(alpha)
    yp_b = -x_b * sin_a + y_b * cos_a
    s_b = yp_max - yp_b

    eps_c2 = concreto.eps_c2_pmilh
    eps_cu = concreto.eps_cu_pmilh
    eps_b = _strain(s_b, x_LN, h_inc, d_inc, eps_c2, eps_cu)

    sigma_s = _sigma_aco(eps_b, aco.fyd_kncm2, aco.Es_kncm2, aco.eps_yd_pmilh)
    sigma_c = concreto._curva_efetiva.sigma(eps_b)
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
    Para σ_c subtraido na posicao do cabo, usa o concreto da primeira parte
    (assumicao: cabos estao na parte principal).
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

    concreto = secao.partes[0].concreto
    h_inc, yp_max = _h_inc_yp_max_pol(secao, alpha)
    d_inc = _d_inc_pol(secao, alpha, yp_max)
    cos_a, sin_a = math.cos(alpha), math.sin(alpha)
    yp_p = -x_p * sin_a + y_p * cos_a
    s_p = yp_max - yp_p

    eps_concreto_p = _strain(
        s_p, x_LN, h_inc, d_inc,
        concreto.eps_c2_pmilh, concreto.eps_cu_pmilh,
    )
    eps_efetiva = eps_concreto_p - eps_pre

    sigma_p = np.array([
        float(_cabo_curva(c).sigma(np.array([eps_efetiva[i]]))[0])
        for i, c in enumerate(secao.cabos)
    ])
    sigma_c_p = concreto._curva_efetiva.sigma(eps_concreto_p)
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


def ei_secante(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    Nsd_kn: float,
    Md_kncm: float,
    eixo: str,
    n_grid: int = 60,
) -> float:
    """EI secante (kN.cm^2) = Md / (1/r), calculado pela seca FCO sob (Nsd, Md).

    Necessario para metodos rigorosos de 2a ordem (P3/P4/P5 do PCalc) em
    `pilares_bastos.py`. Resolve estado de deformacao ELS (Newton-Raphson 3x3)
    e retorna `Md / curvatura`.

    eixo: 'x' -> Md em torno de x (gera curvatura kx);
          'y' -> Md em torno de y (gera curvatura ky).
    """
    if eixo not in ("x", "y"):
        raise ValueError(f"eixo deve ser 'x' ou 'y', got {eixo!r}")

    Mx = Md_kncm if eixo == "x" else 0.0
    My = Md_kncm if eixo == "y" else 0.0
    r = solver_els(secao, concreto, aco, Nsd_kn, Mx, My, n_grid=n_grid)

    if not r["convergiu"]:
        raise ValueError(f"ELS nao convergiu: {r.get('mensagem')}")

    k = r["kx_pmilh_cm"] if eixo == "x" else r["ky_pmilh_cm"]
    # k em "por mil"/cm -> 1/cm dividindo por 1000
    if abs(k) < 1e-12:
        return float("inf")
    inv_r_cm = abs(k) * 1e-3
    return abs(Md_kncm) / inv_r_cm


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
) -> dict:
    """Resolve estado de deformacao em ELS por Newton-Raphson 3x3.

    Encontra (eps_cg, kx, ky) tal que (Nr, Mxr, Myr) = (Nsd, Mxd, Myd) usando
    `scipy.optimize.fsolve` (Powell hibrido com Jacobiano por diferencas
    finitas). Util para:
        - Verificacao de tensao maxima no concreto (NBR 17.2.2).
        - Verificacao de deformacao no aco (controle de fissuracao).
        - Calculo de EI secante (necessario para metodos rigorosos de 2a ordem).

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

    x0 = np.array([0.0, 0.0, 0.0])
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
    """Nd maximo: compressao pura, eps = eps_c2 em toda a secao."""
    Ac_liq = secao.Ac_cm2 - secao.As_total_cm2
    return ALPHA_C * concreto.fcd_kncm2 * Ac_liq + aco.fyd_kncm2 * secao.As_total_cm2


def Nd_min_kn(secao: SecaoRetangular, aco: Aco) -> float:
    """Nd minimo: tracao pura, eps_s = -10 por mil em todas as barras.
    Retorna valor negativo (por convencao, compressao positiva)."""
    return -aco.fyd_kncm2 * secao.As_total_cm2


# ---------------------------------------------------------------------------
# Solvers
# ---------------------------------------------------------------------------
def _solve_x_LN(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    alpha: float,
    Nd: float,
    n_grid: int = 80,
    n_sample: int = 40,
) -> float:
    """brentq em N(x_LN) - Nd = 0. Amostra n_sample pontos, escolhe primeiro
    intervalo com troca de sinal."""
    h_inc, _ = _h_inc_yp_max(secao, alpha)
    x_min = 1e-3
    x_max = 5.0 * h_inc

    def residual(x: float) -> float:
        N, _, _ = esforcos_resistentes(secao, concreto, aco, alpha, x, n_grid)
        return N - Nd

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
            raise ValueError(
                f"Sem raiz para x_LN: alpha={math.degrees(alpha):.1f}°, "
                f"Nd={Nd:.1f} kN, N range=[{Ns.min():.1f}, {Ns.max():.1f}] kN."
            )

    i = int(sign_changes[0])
    return float(brentq(residual, xs[i], xs[i + 1], xtol=1e-4, rtol=1e-6))


def _solve_alpha(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    Nd: float,
    theta_d: float,
    n_grid: int = 80,
) -> tuple[float, float]:
    """brentq em theta(alpha) - theta_d = 0. Retorna (alpha, x_LN)."""
    eps_a = 1e-3

    def residual(alpha: float) -> float:
        x = _solve_x_LN(secao, concreto, aco, alpha, Nd, n_grid)
        _, Mx, My = esforcos_resistentes(secao, concreto, aco, alpha, x, n_grid)
        theta_r = math.atan2(abs(My), abs(Mx))
        return theta_r - theta_d

    # Convencao: Mxd e Myd positivos -> compressao em (+x, +y) -> alpha < 0.
    # Faixa de busca: [-pi/2, 0]. Em alpha=0: theta_r=0 (so MRx). Em alpha=-pi/2:
    # theta_r=pi/2 (so MRy).
    a_lo, a_hi = -math.pi / 2.0 + eps_a, -eps_a
    f_lo = residual(a_lo)
    f_hi = residual(a_hi)
    if f_lo * f_hi > 0:
        raise ValueError(
            f"Solver alpha sem bracketing: f({math.degrees(a_lo):.1f}°)={f_lo:.3f}, "
            f"f({math.degrees(a_hi):.1f}°)={f_hi:.3f}, theta_d={math.degrees(theta_d):.1f}°."
        )
    alpha_sol = float(brentq(residual, a_lo, a_hi, xtol=1e-4, rtol=1e-5))
    x_sol = _solve_x_LN(secao, concreto, aco, alpha_sol, Nd, n_grid)
    return alpha_sol, x_sol


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
    """Calcula (MRx, MRy) tal que arctan(MRy/MRx) = theta_d_rad e Nr = Nd."""
    alpha, x_LN = _solve_alpha(secao, concreto, aco, Nd_kn, theta_d_rad, n_grid)
    _, Mx, My = esforcos_resistentes(secao, concreto, aco, alpha, x_LN, n_grid)
    return {
        "MRx_kncm": abs(Mx),
        "MRy_kncm": abs(My),
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
    """Verifica seção com flexão composta normal (alpha fixo)."""
    x_LN = _solve_x_LN(secao, concreto, aco, alpha, Nd_kn, n_grid)
    _, Mx, My = esforcos_resistentes(secao, concreto, aco, alpha, x_LN, n_grid)
    Mr = math.hypot(Mx, My)
    razao = Mr / abs(Md_kncm) if abs(Md_kncm) > 0 else float("inf")
    return {
        "status": "OK" if razao >= 0.99 else "NAO_VERIFICA",
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
    """
    Nd_max = Nd_max_kn(secao, concreto, aco)
    Nd_min = Nd_min_kn(secao, aco)
    if Nd_kn > Nd_max:
        return {
            "status": "FORA_RANGE",
            "razao": -1.0,
            "mensagem": f"Nd={Nd_kn:.1f} > Nd_max={Nd_max:.1f} (compressao pura).",
        }
    if Nd_kn < Nd_min:
        return {
            "status": "FORA_RANGE",
            "razao": -1.0,
            "mensagem": f"Nd={Nd_kn:.1f} < Nd_min={Nd_min:.1f} (tracao pura).",
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

    if abs(Myd_kncm) / Md_total < 1e-6:
        return _verificar_uniaxial(
            secao, concreto, aco, Nd_kn, abs(Mxd_kncm), 0.0, n_grid
        )
    if abs(Mxd_kncm) / Md_total < 1e-6:
        return _verificar_uniaxial(
            secao, concreto, aco, Nd_kn, abs(Myd_kncm), -math.pi / 2.0, n_grid
        )

    theta_d = math.atan2(abs(Myd_kncm), abs(Mxd_kncm))

    try:
        alpha_sol, x_sol = _solve_alpha(
            secao, concreto, aco, Nd_kn, theta_d, n_grid
        )
    except ValueError as e:
        return {"status": "NAO_CONVERGIU", "razao": -1.0, "mensagem": str(e)}

    _, Mx_r, My_r = esforcos_resistentes(
        secao, concreto, aco, alpha_sol, x_sol, n_grid
    )
    Mr = math.hypot(Mx_r, My_r)
    razao = Mr / Md_total

    return {
        "status": "OK" if razao >= 0.99 else "NAO_VERIFICA",
        "razao": razao,
        "alpha_rad": alpha_sol,
        "alpha_graus": math.degrees(alpha_sol),
        "x_LN_cm": x_sol,
        "MRx_kncm": abs(Mx_r),
        "MRy_kncm": abs(My_r),
        "MR_kncm": Mr,
    }


def verificar_fco_simplificado(
    MRxd_kncm: float,
    MRyd_kncm: float,
    Mxd_kncm: float,
    Myd_kncm: float,
    expoente: float = 1.0,
) -> float:
    """Equacao de interacao simplificada (NBR 17.79):

        (Mxd/MRxd)^a + (Myd/MRyd)^a <= 1.0

    Retorna valor da soma. <= 1.0 verifica.
    expoente=1.0 (a favor da seguranca, retangular). Tipicos:
        - 1.0 retangular (NBR conservador)
        - 1.2 a 2.0 sao valores de Bresler/CEB para retangulares
    """
    if MRxd_kncm <= 0 or MRyd_kncm <= 0:
        raise ValueError("MRxd e MRyd devem ser positivos.")
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
    Brentq em lambda.
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

    theta_d = math.atan2(abs(Myd_kncm), abs(Mxd_kncm))

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
            alpha, x_LN = _solve_alpha(
                secao, concreto, aco, Nd_target, theta_d, n_grid
            )
            _, Mx_r, My_r = esforcos_resistentes(
                secao, concreto, aco, alpha, x_LN, n_grid
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
            lo, hi = hi, new_hi
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
    As_total_min_cm2: float = 0.4,
    As_total_max_cm2: float | None = None,
    tol: float = 0.01,
    iter_max: int = 30,
    n_grid: int = 60,
) -> dict:
    """Itera area total da armadura ate razao=1.0. Geometria das barras
    permanece fixa (perimetral PFOC); apenas a area de cada barra varia."""
    n_barras_total = 2 * (nx + ny) - 4
    if As_total_max_cm2 is None:
        As_total_max_cm2 = 0.08 * base_cm * altura_cm  # 8% (NBR limite superior)

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

    lo, hi = As_total_min_cm2, As_total_max_cm2
    r_lo = razao_para_As(lo)
    r_hi = razao_para_As(hi)

    if r_lo >= 1.0:
        return {
            "status": "OK",
            "As_total_cm2": lo,
            "razao": r_lo,
            "comentario": "As minimo ja resiste.",
        }
    if r_hi < 1.0:
        return {
            "status": "INVIAVEL",
            "As_total_cm2": hi,
            "razao": r_hi,
            "comentario": (
                f"Mesmo com As={hi:.1f} cm^2 (8% Ac) razao={r_hi:.3f} < 1."
            ),
        }

    for _ in range(iter_max):
        mid = 0.5 * (lo + hi)
        r_mid = razao_para_As(mid)
        if abs(r_mid - 1.0) < tol:
            return {"status": "OK", "As_total_cm2": mid, "razao": r_mid}
        if r_mid < 1.0:
            lo = mid
        else:
            hi = mid
    return {
        "status": "OK",
        "As_total_cm2": hi,
        "razao": razao_para_As(hi),
        "comentario": f"Convergencia parcial em {iter_max} iter.",
    }


# ---------------------------------------------------------------------------
# API alta-nivel para Secao poligonal
# ---------------------------------------------------------------------------
def Nd_max_kn_pol(secao: Secao, aco: Aco) -> float:
    """Nd maximo (compressao pura) para Secao poligonal.

    Soma alpha_c * fcd * Ac_liq de cada parte + fyd * As_total das barras.
    """
    total = 0.0
    for parte in secao.partes:
        ac_parte = _polygon_area(parte.polygon)
        # Ac liquido da parte: subtrai a area das barras (aproximacao -- assume
        # que todas as barras estao na primeira parte).
        if parte is secao.partes[0]:
            ac_parte -= secao.As_total_cm2
        total += ALPHA_C * parte.concreto.fcd_kncm2 * ac_parte
    total += aco.fyd_kncm2 * secao.As_total_cm2
    return total


def Nd_min_kn_pol(secao: Secao, aco: Aco) -> float:
    """Nd minimo (tracao pura) para Secao poligonal."""
    return -aco.fyd_kncm2 * secao.As_total_cm2


def _solve_x_LN_pol(
    secao: Secao,
    aco: Aco,
    alpha: float,
    Nd: float,
    n_sample: int = 40,
) -> float:
    h_inc, _ = _h_inc_yp_max_pol(secao, alpha)
    x_min = 1e-3
    x_max = 5.0 * h_inc

    def residual(x: float) -> float:
        N, _, _ = esforcos_resistentes_pol(secao, aco, alpha, x)
        return N - Nd

    xs = np.linspace(x_min, x_max, n_sample)
    Ns = np.array([residual(x) for x in xs])
    sign_changes = np.where(np.diff(np.sign(Ns)) != 0)[0]

    if len(sign_changes) == 0:
        x_max *= 4.0
        xs = np.linspace(x_min, x_max, n_sample)
        Ns = np.array([residual(x) for x in xs])
        sign_changes = np.where(np.diff(np.sign(Ns)) != 0)[0]
        if len(sign_changes) == 0:
            raise ValueError(
                f"Sem raiz para x_LN (pol): alpha={math.degrees(alpha):.1f}°, "
                f"Nd={Nd:.1f} kN, N range=[{Ns.min():.1f}, {Ns.max():.1f}] kN."
            )

    i = int(sign_changes[0])
    return float(brentq(residual, xs[i], xs[i + 1], xtol=1e-4, rtol=1e-6))


def _solve_alpha_pol(
    secao: Secao,
    aco: Aco,
    Nd: float,
    theta_d: float,
) -> tuple[float, float]:
    eps_a = 1e-3

    def residual(alpha: float) -> float:
        x = _solve_x_LN_pol(secao, aco, alpha, Nd)
        _, Mx, My = esforcos_resistentes_pol(secao, aco, alpha, x)
        theta_r = math.atan2(abs(My), abs(Mx))
        return theta_r - theta_d

    a_lo, a_hi = -math.pi / 2.0 + eps_a, -eps_a
    f_lo = residual(a_lo)
    f_hi = residual(a_hi)
    if f_lo * f_hi > 0:
        raise ValueError(
            f"Solver alpha (pol) sem bracketing: f({math.degrees(a_lo):.1f}°)="
            f"{f_lo:.3f}, f({math.degrees(a_hi):.1f}°)={f_hi:.3f}, "
            f"theta_d={math.degrees(theta_d):.1f}°."
        )
    alpha_sol = float(brentq(residual, a_lo, a_hi, xtol=1e-4, rtol=1e-5))
    x_sol = _solve_x_LN_pol(secao, aco, alpha_sol, Nd)
    return alpha_sol, x_sol


def verificar_fco_pol(
    secao: Secao,
    aco: Aco,
    Nd_kn: float,
    Mxd_kncm: float,
    Myd_kncm: float,
) -> dict:
    """Versao Secao poligonal de verificar_fco. Suporta multi-fck."""
    Nd_max = Nd_max_kn_pol(secao, aco)
    Nd_min = Nd_min_kn_pol(secao, aco)
    if Nd_kn > Nd_max:
        return {
            "status": "FORA_RANGE",
            "razao": -1.0,
            "mensagem": f"Nd={Nd_kn:.1f} > Nd_max={Nd_max:.1f}.",
        }
    if Nd_kn < Nd_min:
        return {
            "status": "FORA_RANGE",
            "razao": -1.0,
            "mensagem": f"Nd={Nd_kn:.1f} < Nd_min={Nd_min:.1f}.",
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

    if abs(Myd_kncm) / Md_total < 1e-6:
        x_LN = _solve_x_LN_pol(secao, aco, 0.0, Nd_kn)
        _, Mx, My = esforcos_resistentes_pol(secao, aco, 0.0, x_LN)
        Mr = math.hypot(Mx, My)
        razao = Mr / abs(Mxd_kncm)
        return {
            "status": "OK" if razao >= 0.99 else "NAO_VERIFICA",
            "razao": razao,
            "alpha_rad": 0.0,
            "alpha_graus": 0.0,
            "x_LN_cm": x_LN,
            "MRx_kncm": abs(Mx),
            "MRy_kncm": abs(My),
            "uniaxial": True,
        }

    if abs(Mxd_kncm) / Md_total < 1e-6:
        alpha = -math.pi / 2.0
        x_LN = _solve_x_LN_pol(secao, aco, alpha, Nd_kn)
        _, Mx, My = esforcos_resistentes_pol(secao, aco, alpha, x_LN)
        Mr = math.hypot(Mx, My)
        razao = Mr / abs(Myd_kncm)
        return {
            "status": "OK" if razao >= 0.99 else "NAO_VERIFICA",
            "razao": razao,
            "alpha_rad": alpha,
            "alpha_graus": math.degrees(alpha),
            "x_LN_cm": x_LN,
            "MRx_kncm": abs(Mx),
            "MRy_kncm": abs(My),
            "uniaxial": True,
        }

    theta_d = math.atan2(abs(Myd_kncm), abs(Mxd_kncm))
    try:
        alpha_sol, x_sol = _solve_alpha_pol(secao, aco, Nd_kn, theta_d)
    except ValueError as e:
        return {"status": "NAO_CONVERGIU", "razao": -1.0, "mensagem": str(e)}

    _, Mx_r, My_r = esforcos_resistentes_pol(secao, aco, alpha_sol, x_sol)
    Mr = math.hypot(Mx_r, My_r)
    razao = Mr / Md_total

    return {
        "status": "OK" if razao >= 0.99 else "NAO_VERIFICA",
        "razao": razao,
        "alpha_rad": alpha_sol,
        "alpha_graus": math.degrees(alpha_sol),
        "x_LN_cm": x_sol,
        "MRx_kncm": abs(Mx_r),
        "MRy_kncm": abs(My_r),
        "MR_kncm": Mr,
    }


def momento_resistente_fco_pol(
    secao: Secao,
    aco: Aco,
    Nd_kn: float,
    theta_d_rad: float,
) -> dict:
    """Calcula (MRx, MRy) tal que arctan(MRy/MRx) = theta_d_rad e Nr = Nd."""
    alpha, x_LN = _solve_alpha_pol(secao, aco, Nd_kn, theta_d_rad)
    _, Mx, My = esforcos_resistentes_pol(secao, aco, alpha, x_LN)
    return {
        "MRx_kncm": abs(Mx),
        "MRy_kncm": abs(My),
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
        description="Verificacao FCO retangular (NBR 6118:2023)."
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
