"""Kernel de flexão composta oblíqua contra a NBR 6118:2026 (FCO-01 a FCO-18).

Cada teste leva o ID do achado da auditoria (AUDITORIA_NBR6118_2026.md) e
usa o valor da norma como esperado. O oráculo é um integrador por camadas
escrito aqui, do zero: não importa o kernel nem o núcleo normativo.

Páginas: sempre as do PDF da NBR 6118:2026.
"""

from __future__ import annotations

import math
import warnings

import numpy as np
import pytest
from scipy.optimize import brentq

from dimensionamento import nucleo_nbr6118 as nbr
from dimensionamento.rotinas import fco_dispatch as D
from dimensionamento.rotinas import flexao_composta_obliqua as F
from dimensionamento.rotinas import flexao_composta_normal as FCN
from dimensionamento.rotinas import verificacao_pilar as VP


# ===========================================================================
# Oráculo independente: integração por camadas (flexão em torno de x)
# ===========================================================================
ES = 21000.0  # kN/cm², 210 GPa (8.3.5)


def _param(fck: float, gama_c: float = 1.4) -> dict:
    """Figura 8.2 (PDF p. 45) e 17.2.2 e) (p. 141), escrita aqui de novo."""
    eta = 1.0 if fck <= 40.0 else (40.0 / fck) ** (1.0 / 3.0)
    if fck <= 50.0:
        ec2, ecu, n = 2.0, 3.5, 2.0
    else:
        t = (90.0 - fck) / 100.0
        ec2 = 2.0 + 0.085 * (fck - 50.0) ** 0.53
        ecu = 2.6 + 35.0 * t ** 4
        n = 1.4 + 23.4 * t ** 4
    return {"fcd": fck / gama_c / 10.0, "pico": 0.85 * eta * fck / gama_c / 10.0,
            "ec2": ec2, "ecu": ecu, "n": n}


def _sc(eps, p: dict, pico: float | None = None) -> np.ndarray:
    """Parábola-retângulo; tração nula (17.2.2 d)."""
    e = np.asarray(eps, dtype=float)
    pk = p["pico"] if pico is None else pico
    par = pk * (1.0 - (1.0 - np.clip(e, 0.0, p["ec2"]) / p["ec2"]) ** p["n"])
    return np.where(e <= 0.0, 0.0, np.where(e >= p["ec2"], pk, par))


class Oraculo:
    """Seção retangular b x h em camadas horizontais, flexão em torno de x
    (M > 0 comprime +y). zonas: [(y_inf, y_sup, fck)]; barras: [(y, A)];
    cabos: [(y, A, eps_pre)] com aço de protensão bilinear (CP-190).

    Plano último (Figura 17.1, p. 142): a maior curvatura que respeita
    -10 por mil na armadura mais tracionada, eps_cu na fibra mais
    comprimida de cada concreto e eps_c2 no pivô C de cada concreto,
    (eps_cu - eps_c2)/eps_cu * h abaixo dela.
    """

    def __init__(self, b, h, barras=(), zonas=None, fck=None, cabos=(),
                 fyk=500.0, gama_c=1.4, gama_s=1.15, n_lam=6000):
        self.b, self.h = b, h
        self.y = (np.arange(n_lam) + 0.5) * h / n_lam - h / 2.0
        self.dA = b * h / n_lam
        zonas = zonas if zonas is not None else [(-h / 2.0, h / 2.0, fck)]
        self.zonas = [(y0, y1, _param(f, gama_c)) for y0, y1, f in zonas]
        self.iz = np.array([self._zona(v) for v in self.y])
        self.yb = np.array([y for y, _ in barras], dtype=float)
        self.Ab = np.array([A for _, A in barras], dtype=float)
        self.cabos = list(cabos)
        self.fyd = fyk / gama_s / 10.0
        self.fpyd = 1710.0 / 1.15 / 10.0
        ys = list(self.yb) + [c[0] for c in self.cabos]
        self.d = (h / 2.0 - min(ys)) if ys else 0.0

    def _zona(self, y: float) -> int:
        for i, (y0, y1, _) in enumerate(self.zonas):
            if y0 - 1e-9 <= y <= y1 + 1e-9:
                return i
        raise ValueError(y)

    def _sc_y(self, eps, ys, pico_fn=None):
        eps = np.asarray(eps, dtype=float)
        iz = np.array([self._zona(v) for v in np.atleast_1d(ys)])
        out = np.zeros_like(eps)
        for i, (_, _, p) in enumerate(self.zonas):
            m = iz == i
            out[m] = _sc(eps[m], p, None if pico_fn is None else pico_fn(p))
        return out

    def k(self, x: float) -> float:
        ks = []
        if self.d > x:
            ks.append(10.0 / (self.d - x))
        for _, y1, p in self.zonas:
            s_top = self.h / 2.0 - y1
            if x > s_top:
                ks.append(p["ecu"] / (x - s_top))
            rho = max(0.0, (p["ecu"] - p["ec2"]) / p["ecu"])
            s_c = s_top + rho * self.h
            if x > s_c:
                ks.append(min(p["ec2"], p["ecu"]) / (x - s_c))
        return min(ks)

    def _forcas(self, eps_de_y, pico_fn=None):
        """(N, M) para o campo de deformações eps_de_y(y)."""
        e = eps_de_y(self.y)
        sig = np.zeros_like(e)
        for i, (_, _, p) in enumerate(self.zonas):
            m = self.iz == i
            sig[m] = _sc(e[m], p, None if pico_fn is None else pico_fn(p))
        N = float(sig.sum() * self.dA)
        M = float((sig * self.y).sum() * self.dA)
        if self.yb.size:
            eb = eps_de_y(self.yb)
            dl = np.clip(eb / 1000.0 * ES, -self.fyd, self.fyd) - self._sc_y(eb, self.yb, pico_fn)
            N += float((dl * self.Ab).sum())
            M += float((dl * self.Ab * self.yb).sum())
        for yp, Ap, epre in self.cabos:
            ec = float(eps_de_y(np.array([yp]))[0])
            sp = float(np.clip((ec - epre) / 1000.0 * 20000.0, -self.fpyd, self.fpyd))
            dl = sp - float(self._sc_y(np.array([ec]), np.array([yp]), pico_fn)[0])
            N += dl * Ap
            M += dl * Ap * yp
        return N, M

    def esforcos(self, x: float):
        k = self.k(x)
        return self._forcas(lambda y: k * (x - (self.h / 2.0 - y)))

    def N_max(self) -> float:
        eb = min(min(p["ec2"], p["ecu"]) for _, _, p in self.zonas)
        return self._forcas(lambda y: np.full_like(np.asarray(y, dtype=float), eb))[0]

    def x_para(self, Nd: float) -> float:
        return brentq(lambda x: self.esforcos(x)[0] - Nd, 1e-6, 1e7 * self.h,
                      xtol=1e-12, rtol=1e-13, maxiter=500)

    def MRd(self, Nd: float) -> float:
        return self.esforcos(self.x_para(Nd))[1]

    def curvatura(self, N: float, M: float, pico_fn) -> float:
        """Curvatura (por mil/cm) de eps(y) = e0 + k*y com (N, M), na curva
        de pico pico_fn(p) (15.3.1: 1,10*fcd)."""
        def e0_de(k):
            return brentq(lambda e0: self._forcas(lambda y: e0 + k * y, pico_fn)[0] - N,
                          -40.0, 40.0, xtol=1e-12, rtol=1e-13, maxiter=300)

        def res(k):
            e0 = e0_de(k)
            return self._forcas(lambda y: e0 + k * y, pico_fn)[1] - M

        return brentq(res, 1e-9, 1.0, xtol=1e-14, rtol=1e-12, maxiter=300)


# ---------------------------------------------------------------------------
# Seções usadas nos achados
# ---------------------------------------------------------------------------
ACO = F.Aco()
B, H = 20.0, 50.0
BARRAS_6F16 = F.armadura_perimetral_retangular(B, H, 2.5, nx=2, ny=3, fi_l_mm=16.0)
SEC_6F16 = F.SecaoRetangular(B, H, 2.5, BARRAS_6F16)
ORACULO_BARRAS_6F16 = [(b.y_cm, b.area_cm2) for b in BARRAS_6F16]

A20, A10 = math.pi * 1.0 ** 2, math.pi * 0.5 ** 2
BARRAS_ASSIM = (F.Barra(-6.5, -21.0, A20), F.Barra(0.0, -21.0, A20), F.Barra(6.5, -21.0, A20),
                F.Barra(-6.5, 21.0, A10), F.Barra(6.5, 21.0, A10))
SEC_ASSIM = F.SecaoRetangular(20.0, 50.0, 2.5, BARRAS_ASSIM)
SEC_ASSIM_ESPELHO = F.SecaoRetangular(
    20.0, 50.0, 2.5, tuple(F.Barra(b.x_cm, -b.y_cm, b.area_cm2) for b in BARRAS_ASSIM))

FCKS_NORMA = (20.0, 30.0, 40.0, 45.0, 50.0, 55.0, 60.0, 70.0, 80.0, 90.0)


def _rel(a: float, b: float) -> float:
    return abs(a / b - 1.0)


# ===========================================================================
# FCO-13 e FCO-14 -- Concreto: faixa de validade e delegação ao núcleo
# ===========================================================================
@pytest.mark.parametrize("fck", [15.0, 19.9, 90.1, 95.0, 120.0])
def test_fco13_concreto_fora_da_faixa_levanta(fck):
    """8.2.1 (PDF p. 41-42): a norma vale de C20 a C90."""
    with pytest.raises(nbr.FaixaNormativaError):
        F.Concreto(fck_mpa=fck)


def test_fco13_cabos_exigem_C25():
    """8.2.1: com armadura ativa, fck >= 25 MPa."""
    c20 = F.Concreto(fck_mpa=20.0)
    with pytest.raises(nbr.FaixaNormativaError):
        F.Secao.retangular(20.0, 60.0, c20, cabos=(F.Cabo(0.0, -25.0, 2.0, 6.0),))


@pytest.mark.parametrize("fck", FCKS_NORMA)
def test_fco14_concreto_delega_ao_nucleo(fck):
    c = F.Concreto(fck_mpa=fck)
    assert c.fcd_kncm2 == pytest.approx(nbr.fcd(fck) / 10.0, rel=1e-15)
    assert c.eta_c == nbr.eta_c(fck)
    assert c.eps_c2_pmilh == nbr.eps_c2(fck)
    assert c.eps_cu_pmilh == nbr.eps_cu(fck)
    assert c.n_parabola == nbr.n_parabola(fck)
    assert c.pivo_C_rel == nbr.pivo_C_distancia_relativa(fck)
    assert c.Eci_kncm2 == pytest.approx(nbr.Eci(fck) / 10.0, rel=1e-15)
    assert c.fctk_inf_kncm2 == pytest.approx(nbr.fctk_inf(fck) / 10.0, rel=1e-15)


@pytest.mark.parametrize("fck, Eci_mpa, fctm_mpa", [
    # 8.2.8 (p. 44): Eci = 21,5e3 (fck/10 + 1,25)^(1/3) acima de C50;
    # 8.2.5 (p. 42-43): fct,m = 2,12 ln[1 + 0,1 (fck + 8)] acima de C50.
    (70.0, 21.5e3 * (7.0 + 1.25) ** (1 / 3), 2.12 * math.log(1 + 0.1 * 78.0)),
    (90.0, 21.5e3 * (9.0 + 1.25) ** (1 / 3), 2.12 * math.log(1 + 0.1 * 98.0)),
    (30.0, 5600.0 * math.sqrt(30.0), 0.3 * 30.0 ** (2 / 3)),
])
def test_fco14_Eci_e_fct_grupo_II(fck, Eci_mpa, fctm_mpa):
    c = F.Concreto(fck_mpa=fck)
    assert c.Eci_kncm2 * 10.0 == pytest.approx(Eci_mpa, rel=1e-12)
    assert c.fctk_inf_kncm2 * 10.0 == pytest.approx(0.7 * fctm_mpa, rel=1e-12)


# ===========================================================================
# FCO-01 -- pico 0,85 ηc fcd (Figura 8.2, p. 45; 17.2.2 e, p. 141)
# ===========================================================================
@pytest.mark.parametrize("fck", [40.0, 45.0, 50.0, 55.0, 70.0, 90.0])
def test_fco01_curva_com_eta_c(fck):
    c = F.Concreto(fck_mpa=fck)
    eta = 1.0 if fck <= 40 else (40.0 / fck) ** (1 / 3)
    pico = 0.85 * eta * fck / 1.4 / 10.0
    # (em C90 a norma dá εcu = 2,6 < εc2 = 2,6006: o patamar começa em εc2)
    e_pat = max(c.eps_c2_pmilh, c.eps_cu_pmilh)
    sig = c._curva_efetiva.sigma(np.array([c.eps_c2_pmilh, e_pat, 5.0]))
    assert sig == pytest.approx([pico, pico, pico], rel=1e-12)


def test_fco01_Nd_max_C50_e_pre_teste():
    """Achado FCO-01/05: C50, 20x50, 6φ16 -> Nd,máx = 3290,8 kN (era 3523,6)."""
    c = F.Concreto(fck_mpa=50.0)
    assert F.Nd_max_kn(SEC_6F16, c, ACO) == pytest.approx(3290.8, abs=0.1)
    r = F.verificar_fco(SEC_6F16, c, ACO, 3500.0, 0.0, 0.0)
    assert r["status"] == "FORA_RANGE"  # era "OK" com Nd/Nd,máx = 1,064


def test_fco01_MRd_C50_nu05():
    """Achado FCO-01: C50, ν = 0,5 -> MRd = 22 765 kN·cm (era 24 696, +8,5 %)."""
    c = F.Concreto(fck_mpa=50.0)
    Nd = 0.5 * F.Nd_max_kn(SEC_6F16, c, ACO)
    r = F.verificar_fco(SEC_6F16, c, ACO, Nd, 1.0, 0.0, n_grid=250)
    assert r["razao"] == pytest.approx(22765.0, rel=5e-4)


# ===========================================================================
# FCO-02 -- pivô C a (εcu − εc2)·h/εcu (Figura 17.1, p. 142)
# ===========================================================================
@pytest.mark.parametrize("fck", [50.0, 55.0, 60.0, 70.0, 80.0, 90.0])
def test_fco02_pivo_C(fck):
    c = F.Concreto(fck_mpa=fck)
    ec2, ecu = c.eps_c2_pmilh, c.eps_cu_pmilh
    rho = max(0.0, (ecu - ec2) / ecu)
    assert c.pivo_C_rel == pytest.approx(rho, abs=1e-15)
    h, d = 50.0, 46.0
    for x in (1.0001 * h, 1.2 * h, 3.0 * h, 50.0 * h):
        e = F._strain(np.array([0.0, rho * h]), x, h, d, ec2, ecu, c.pivo_C_rel)
        assert e[1] == pytest.approx(min(ec2, ecu), rel=1e-12)   # pivô C
        assert e[0] <= ecu * (1 + 1e-12)                          # nunca passa de εcu
    # continuidade em x = h (dominios 4a e 5)
    e4a = F._strain(0.0, h, h, d, ec2, ecu, c.pivo_C_rel)
    e5 = F._strain(0.0, h * (1 + 1e-9), h, d, ec2, ecu, c.pivo_C_rel)
    assert e5 == pytest.approx(e4a, rel=1e-6)


@pytest.mark.parametrize("Nd, esperado", [(2806.0, 14749.0), (3407.0, 7477.0)])
def test_fco02_MRd_C70_achado(Nd, esperado):
    """Achado FCO-01 + FCO-02, C70: 23 073 -> 14 749 e 19 463 -> 7 477 kN·cm."""
    c = F.Concreto(fck_mpa=70.0)
    r = F.verificar_fco(SEC_6F16, c, ACO, Nd, 1.0, 0.0, n_grid=250)
    assert r["razao"] == pytest.approx(esperado, rel=1e-3)


# ===========================================================================
# Oráculo: MRd e Nd,máx de C20 a C90 (FCO-01, FCO-02, FCO-05, FCO-07)
# ===========================================================================
@pytest.mark.parametrize("fck", FCKS_NORMA)
def test_oraculo_MRd_e_Nd_max(fck):
    c = F.Concreto(fck_mpa=fck)
    ora = Oraculo(B, H, ORACULO_BARRAS_6F16, fck=fck)
    Nmax = F.Nd_max_kn(SEC_6F16, c, ACO)
    assert Nmax == pytest.approx(ora.N_max(), rel=1e-9)
    for nu in (0.0, 0.3, 0.6, 0.85, 0.95):
        Nd = nu * Nmax
        r = F.verificar_fco(SEC_6F16, c, ACO, Nd, 1.0, 0.0, n_grid=160)
        assert r["status"] == "OK"
        assert r["razao"] == pytest.approx(ora.MRd(Nd), rel=2e-3), f"C{fck:.0f} ν={nu}"


def test_oraculo_My_e_momento_negativo_C70():
    """Mesma seção, flexão em torno de y e com sinal negativo (C70)."""
    c = F.Concreto(fck_mpa=70.0)
    Nd = 0.6 * F.Nd_max_kn(SEC_6F16, c, ACO)
    # em torno de y: a seção vira 50 (em x) por 20 (em y); barras em x
    ora_y = Oraculo(H, B, [(b.x_cm, b.area_cm2) for b in BARRAS_6F16], fck=70.0)
    for My in (1.0, -1.0):
        r = F.verificar_fco(SEC_6F16, c, ACO, Nd, 0.0, My, n_grid=160)
        assert r["razao"] == pytest.approx(ora_y.MRd(Nd), rel=2e-3)
    ora_x = Oraculo(B, H, ORACULO_BARRAS_6F16, fck=70.0)
    r = F.verificar_fco(SEC_6F16, c, ACO, Nd, -1.0, 0.0, n_grid=160)
    assert r["razao"] == pytest.approx(ora_x.MRd(Nd), rel=2e-3)


# ===========================================================================
# FCO-03 -- sinal dos momentos
# ===========================================================================
def test_fco03_secao_assimetrica_momento_negativo():
    """Achado: 20x50, C30, 3φ20 em y = −21 e 2φ10 em y = +21, Nd = 0,
    Mxd = −8 000 -> NAO_VERIFICA com razão 0,378 (era OK com 2,114)."""
    c = F.Concreto(fck_mpa=30.0)
    r = F.verificar_fco(SEC_ASSIM, c, ACO, 0.0, -8000.0, 0.0)
    assert r["status"] == "NAO_VERIFICA"
    assert r["razao"] == pytest.approx(0.378, abs=0.003)
    # oráculo: 2φ10 tracionadas no topo, 3φ20 comprimidas embaixo
    ora = Oraculo(20.0, 50.0, [(21.0, 3 * A20), (-21.0, 2 * A10)], fck=30.0)  # espelhada
    assert r["razao"] * 8000.0 == pytest.approx(ora.MRd(0.0), rel=2e-3)
    # momento positivo continua como antes
    r_pos = F.verificar_fco(SEC_ASSIM, c, ACO, 0.0, 8000.0, 0.0)
    assert r_pos["status"] == "OK"
    assert r_pos["razao"] == pytest.approx(2.114, abs=0.002)


@pytest.mark.parametrize("fck", [30.0, 70.0])
@pytest.mark.parametrize("Mx, My", [(-8000.0, 0.0), (-6000.0, 1500.0), (-6000.0, -1500.0),
                                    (6000.0, -1500.0), (0.0, -2500.0)])
def test_fco03_assimetrica_igual_a_espelhada(fck, Mx, My):
    """Espelhar a seção em y e trocar o sinal de Mx é o mesmo problema.

    Os dois casos caem em faixas de α diferentes; a diferença que sobra é a
    da tolerância do solver (xtol = 1e-4 rad em α). O defeito dava 2,11 x 0,38.
    """
    c = F.Concreto(fck_mpa=fck)
    for Nd in (0.0, 600.0):
        r1 = F.verificar_fco(SEC_ASSIM, c, ACO, Nd, Mx, My, n_grid=60)
        r2 = F.verificar_fco(SEC_ASSIM_ESPELHO, c, ACO, Nd, -Mx, My, n_grid=60)
        assert r1["status"] == r2["status"]
        assert r1["razao"] == pytest.approx(r2["razao"], rel=1e-4)


@pytest.mark.parametrize("fck", [25.0, 50.0, 90.0])
def test_fco03_secao_simetrica_sinal_nao_importa(fck):
    c = F.Concreto(fck_mpa=fck)
    b = F.armadura_perimetral_retangular(30, 50, 3.0, 3, 4, 16.0)
    s = F.SecaoRetangular(30, 50, 3.0, b)
    Nd = 0.4 * F.Nd_max_kn(s, c, ACO)
    for mx, my in ((9000.0, 0.0), (0.0, 5000.0), (9000.0, 5000.0)):
        ref = F.verificar_fco(s, c, ACO, Nd, mx, my, n_grid=60)["razao"]
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            r = F.verificar_fco(s, c, ACO, Nd, sx * mx, sy * my, n_grid=60)
            assert r["razao"] == pytest.approx(ref, rel=1e-6)


def _secao_L(rot: bool):
    poly = ((-20.0, -20.0), (20.0, -20.0), (20.0, 0.0), (0.0, 0.0), (0.0, 20.0), (-20.0, 20.0), (-20.0, -20.0))
    bxy = ((-16.0, -16.0), (16.0, -16.0), (-16.0, 16.0), (16.0, -4.0), (-4.0, 16.0), (-4.0, -4.0))
    if rot:
        poly = tuple((-x, -y) for x, y in poly)
        bxy = tuple((-x, -y) for x, y in bxy)
    c = F.Concreto(fck_mpa=30.0)
    return F.Secao(partes=(F.Parte(polygon=poly, concreto=c),),
                   barras=tuple(F.Barra(x, y, 2.0) for x, y in bxy), n_dy=40, n_dx=20)


def test_fco03_secao_L_girada():
    """Achado: seção L girada 180°, Nd = 800, Mx = My = −6 000 saía "OK" (1,68)
    quando a compressão cai no canto vazio (≈ 0,79)."""
    L, L180 = _secao_L(False), _secao_L(True)
    r_neg = F.verificar_fco_pol(L180, ACO, 800.0, -6000.0, -6000.0)
    r_ref = F.verificar_fco_pol(L, ACO, 800.0, 6000.0, 6000.0)   # mesmo problema girado
    assert r_neg["status"] == "NAO_VERIFICA"
    assert r_neg["razao"] == pytest.approx(r_ref["razao"], rel=1e-6)
    assert r_neg["razao"] == pytest.approx(0.791, abs=0.005)
    r_pos = F.verificar_fco_pol(L180, ACO, 800.0, 6000.0, 6000.0)
    r_pos_ref = F.verificar_fco_pol(L, ACO, 800.0, -6000.0, -6000.0)
    assert r_pos["status"] == "OK"
    assert r_pos["razao"] == pytest.approx(r_pos_ref["razao"], rel=1e-6)


@pytest.mark.parametrize("fck", [30.0, 70.0])
def test_fco03_centro_plastico_deslocado(fck):
    """Armadura assimétrica e ν alto: com o topo comprimido o momento já sai
    negativo, a envoltória de N fixo não contém a origem e nem Nd centrado é
    resistido -- NAO_VERIFICA (antes, um raio com duas interseções podia dar
    "OK"). Abaixo disso, o valor bate com o oráculo."""
    c = F.Concreto(fck_mpa=fck)
    Nmax = F.Nd_max_kn(SEC_ASSIM, c, ACO)
    ora = Oraculo(20.0, 50.0, [(-21.0, 3 * A20), (21.0, 2 * A10)], fck=fck)
    for nu in (0.8, 0.9, 0.97):
        Nd = nu * Nmax
        M_topo = ora.MRd(Nd)
        r = F.verificar_fco(SEC_ASSIM, c, ACO, Nd, 1.0, 0.0, n_grid=120)
        if M_topo > 0.0:
            assert r["razao"] == pytest.approx(M_topo, rel=2e-3)
        else:
            assert r["status"] == "NAO_VERIFICA" and r["razao"] == 0.0
            assert F.verificar_fco(SEC_ASSIM, c, ACO, Nd, -5000.0, 2000.0, 60)["status"] == "NAO_VERIFICA"


def test_fco03_momento_resistente_em_qualquer_quadrante():
    c = F.Concreto(fck_mpa=30.0)
    for theta_g in (30.0, 120.0, -150.0, -60.0, 180.0, -90.0):
        th = math.radians(theta_g)
        r = F.momento_resistente_fco(SEC_ASSIM, c, ACO, 300.0, th, n_grid=60)
        assert math.atan2(r["My_kncm"], r["Mx_kncm"]) == pytest.approx(th if theta_g != 180.0 else math.pi, abs=2e-3)


# ===========================================================================
# FCO-05 -- Nd,máx com σs(εc2) (reta b, Figura 17.1; 8.3.6)
# ===========================================================================
def test_fco05_Nd_max_C30_CA50():
    """Achado: C30, 20x50, 6φ16 -> 2 306,1 kN (com fyd dava 2 324,0)."""
    c = F.Concreto(fck_mpa=30.0)
    assert F.Nd_max_kn(SEC_6F16, c, ACO) == pytest.approx(2306.1, abs=0.1)


def test_fco05_Nd_max_CA60():
    """CA-60, ρ = 4 %: aço a 2 por mil = 420 MPa, bem abaixo de fyd = 522 MPa."""
    a60 = F.Aco(fyk_mpa=600.0)
    c = F.Concreto(fck_mpa=30.0)
    As_barra = 0.04 * 30 * 30 / 8
    s = F.SecaoRetangular(30, 30, 3.0, F.armadura_perimetral_retangular(30, 30, 3.0, 3, 3, 20.0, 5.0, As_barra))
    As = s.As_total_cm2
    esperado = 0.85 * 3.0 / 1.4 * (900.0 - As) + 21000.0 * 0.002 * As
    assert F.Nd_max_kn(s, c, a60) == pytest.approx(esperado, rel=1e-12)


@pytest.mark.parametrize("fck", [30.0, 90.0])
def test_fco05_Nd_proximo_do_maximo_converge(fck):
    """O pré-teste aprova Nd <= Nd,máx: o solver tem de achar a LN."""
    c = F.Concreto(fck_mpa=fck)
    Nmax = F.Nd_max_kn(SEC_6F16, c, ACO)
    for f in (0.99, 0.9999):
        r = F.verificar_fco(SEC_6F16, c, ACO, f * Nmax, 100.0, 0.0, n_grid=60)
        assert r["status"] in ("OK", "NAO_VERIFICA"), r
        rr = F.razao_dc_radial(SEC_6F16, c, ACO, f * Nmax, 100.0, 0.0, n_grid=60)
        assert rr["status"] in ("OK", "NAO_VERIFICA"), rr


# ===========================================================================
# FCO-06 -- Nd,máx e Nd,mín da seção poligonal com cabos (17.2.4.2.1, p. 143)
# ===========================================================================
def _secao_com_cabos():
    c = F.Concreto(fck_mpa=35.0)
    bq = F.armadura_perimetral_retangular(40, 40, 3.0, 2, 2, 12.5, 5.0)
    cabos = tuple(F.Cabo(x, y, 1.0, 6.0) for x in (-14.0, 14.0) for y in (-14.0, 14.0))
    return F.Secao.retangular(40, 40, c, barras=bq, cabos=cabos), bq


def test_fco06_Nd_max_pol_com_cabos():
    """Achado: 3 603,0 kN ignorando os cabos -> 3 267,2 kN."""
    s, bq = _secao_com_cabos()
    As = sum(b.area_cm2 for b in bq)
    # reta b: concreto a 2 por mil; cabo com 2 - 6 = -4 por mil (tracionado)
    esperado = 0.85 * 3.5 / 1.4 * (1600.0 - As - 4.0) + 42.0 * As + (-0.004 * 20000.0) * 4.0
    assert F.Nd_max_kn_pol(s, ACO) == pytest.approx(esperado, rel=1e-12)
    assert F.Nd_max_kn_pol(s, ACO) == pytest.approx(3267.2, abs=0.1)


def test_fco06_Nd_min_pol_com_cabos():
    s, bq = _secao_com_cabos()
    As = sum(b.area_cm2 for b in bq)
    fpyd = 1710.0 / 1.15 / 10.0
    esperado = -ACO.fyd_kncm2 * As - fpyd * 4.0   # cabos a -10 - 6 por mil: escoados
    assert F.Nd_min_kn_pol(s, ACO) == pytest.approx(esperado, rel=1e-12)


# ===========================================================================
# FCO-07 e FCO-08 -- backend C++ e dispatcher (decisão 7)
# ===========================================================================
requer_cpp = pytest.mark.skipif(not D.CPP_AVAILABLE, reason="backend C++ não compilado")


def _cpp(sec, conc, aco):
    C = D._cpp
    return (C.SecaoRetangular(sec.base_cm, sec.altura_cm, sec.cobrimento_cm,
                              [C.Barra(b.x_cm, b.y_cm, b.area_cm2) for b in sec.barras]),
            C.Concreto(conc.fck_mpa, conc.gama_c), C.Aco(aco.fyk_mpa, aco.Es_kncm2, aco.gama_s))


@requer_cpp
def test_fco07_backend_tem_as_correcoes():
    assert D.CPP_VERSAO >= D.VERSAO_KERNEL_MINIMA
    assert D.CPP_PARIDADE


@requer_cpp
@pytest.mark.parametrize("fck", [60.0, 90.0])
def test_fco07_patamar_alem_de_eps_cu(fck):
    """Achado: o C++ zerava σ além de εcu (C60 x = 1,2h: −23 %; C90 não convergia)."""
    c = F.Concreto(fck_mpa=fck)
    cs, cc, ca = _cpp(SEC_6F16, c, ACO)
    for xf in (1.2, 3.0, 1000.0):
        Np = F.esforcos_resistentes(SEC_6F16, c, ACO, 0.0, xf * H, 100)
        Nc = D._cpp.esforcos_resistentes(cs, cc, ca, 0.0, xf * H, 100)
        assert Nc[:2] == pytest.approx(Np[:2], rel=1e-9)
        assert Nc[2] == pytest.approx(Np[2], abs=1e-6)   # My = 0 (simetria)


@requer_cpp
@pytest.mark.parametrize("fck", [20.0, 40.0, 45.0, 50.0, 55.0, 70.0, 90.0])
def test_fco07_paridade_python_cpp(fck):
    """Paridade medida de C20 a C90, no domínio 5 (ν = 0,97) e na seção
    assimétrica, com momentos de qualquer sinal."""
    c = F.Concreto(fck_mpa=fck)
    for s in (SEC_6F16, SEC_ASSIM):
        cs, cc, ca = _cpp(s, c, ACO)
        Nmax = F.Nd_max_kn(s, c, ACO)
        assert D._cpp.Nd_max_kn(cs, cc, ca) == pytest.approx(Nmax, rel=1e-12)
        for nu in (0.3, 0.97):
            for mx, my in ((8000.0, 0.0), (-8000.0, 0.0), (0.0, -3000.0), (-6000.0, 2500.0)):
                rp = F.verificar_fco(s, c, ACO, nu * Nmax, mx, my, 40)
                rc = D._cpp.verificar_fco(cs, cc, ca, nu * Nmax, mx, my, 40)
                assert rc["status"] == rp["status"]
                assert rc["razao"] == pytest.approx(rp["razao"], rel=1e-8)
        for mx, my in ((8000.0, 0.0), (1.0, 3000.0), (-6000.0, 2500.0)):
            rp = F.razao_dc_radial(s, c, ACO, 0.4 * Nmax, mx, my, 40)
            rc = D._cpp.razao_dc_radial(cs, cc, ca, 0.4 * Nmax, mx, my, 40)
            assert rc["status"] == rp["status"]
            assert rc["razao_dc"] == pytest.approx(rp["razao_dc"], rel=1e-8)


@requer_cpp
def test_fco13_cpp_valida_fck():
    with pytest.raises(ValueError):
        D._cpp.Concreto(95.0, 1.4)


@requer_cpp
def test_fco08_dispatcher_nao_descarta_curva():
    """Achado: C50 com curva do usuário -> C++ ignorava a curva (+8,5 %)."""
    c50 = F.Concreto(fck_mpa=50.0)
    curva = F.CurvaCParabolaRetangulo(fcd_kncm2=c50.fcd_kncm2, eps_c2_pmilh=2.0,
                                      eps_cu_pmilh=3.5, n_parabola=2.0, eta_c=0.9)
    cc = F.Concreto(fck_mpa=50.0, curva=curva)
    rp = D.verificar_fco(SEC_6F16, cc, ACO, 1500.0, 1.0, 0.0, 60, use_cpp=False)
    with pytest.warns(F.AvisoNBR6118):
        rc = D.verificar_fco(SEC_6F16, cc, ACO, 1500.0, 1.0, 0.0, 60, use_cpp=True)
    assert rc["razao"] == rp["razao"]
    with pytest.warns(F.AvisoNBR6118):
        rr = D.razao_dc_radial(SEC_6F16, cc, ACO, 1500.0, 1000.0, 0.0, 60, use_cpp=True)
    assert rr == D.razao_dc_radial(SEC_6F16, cc, ACO, 1500.0, 1000.0, 0.0, 60, use_cpp=False)
    with pytest.raises(ValueError):
        D._to_cpp_concreto(cc)


@requer_cpp
def test_fco08_dispatcher_usa_cpp_com_paridade():
    c = F.Concreto(fck_mpa=70.0)
    with warnings.catch_warnings():
        warnings.simplefilter("error", F.AvisoNBR6118)
        rc = D.verificar_fco(SEC_ASSIM, c, ACO, 800.0, -8000.0, 1500.0, 40, use_cpp=True)
    rp = D.verificar_fco(SEC_ASSIM, c, ACO, 800.0, -8000.0, 1500.0, 40, use_cpp=False)
    assert rc["razao"] == pytest.approx(rp["razao"], rel=1e-8)


# ===========================================================================
# FCO-09 -- As,mín de pilar (17.3.5.3.1, p. 153)
# ===========================================================================
def test_fco09_As_min_pilar():
    """Achado: pilar 30x60, C30, Nd = 300 kN -> 0,40 cm²; a norma pede 7,20 cm²."""
    c = F.Concreto(fck_mpa=30.0)
    r = F.dimensionar_as_fco(30.0, 60.0, 2.5, 3, 3, 16.0, c, ACO, 300.0, 1000.0, 1000.0, n_grid=40)
    assert r["As_total_cm2"] == pytest.approx(7.20, abs=1e-9)
    assert r["status"] == "OK"
    # 0,15 Nd/fyd governa com Nd grande
    fyd = 500.0 / 1.15 / 10.0   # kN/cm²
    assert F.As_min_pilar_cm2(1800.0, 3000.0, ACO) == pytest.approx(0.15 * 3000.0 / fyd)
    assert F.As_min_pilar_cm2(1800.0, -500.0, ACO) == pytest.approx(0.004 * 1800.0)


def test_fco09_fcn_herda_As_min():
    c = F.Concreto(fck_mpa=30.0)
    r = FCN.dimensionar_as_fcn(30.0, 60.0, 2.5, 3, 3, 16.0, c, ACO, 300.0, 1000.0, n_grid=40)
    assert r["As_total_cm2"] == pytest.approx(7.20, abs=1e-9)
    # piso do usuário maior que o da norma prevalece
    r = FCN.dimensionar_as_fcn(30.0, 60.0, 2.5, 3, 3, 16.0, c, ACO, 300.0, 1000.0,
                               As_total_min_cm2=9.0, n_grid=40)
    assert r["As_total_cm2"] == pytest.approx(9.0, abs=1e-9)


def test_fco09_fco11_dimensionamento_devolve_razao_maior_que_1():
    c = F.Concreto(fck_mpa=30.0)
    r = F.dimensionar_as_fco(30.0, 60.0, 2.5, 3, 3, 16.0, c, ACO, 900.0, 20000.0, 9000.0, n_grid=40)
    assert r["status"] == "OK"
    assert r["As_total_cm2"] > r["As_min_norma_cm2"]
    assert 1.0 <= r["razao"] < 1.01


# ===========================================================================
# FCO-10 -- (EI)sec da 15.3.1 e Figura 15.1 (p. 121)
# ===========================================================================
B8 = F.armadura_perimetral_retangular(30, 60, 2.5, 3, 3, 16.0, 5.0)
S8 = F.SecaoRetangular(30, 60, 2.5, B8)


def test_fco10_ei_secante_achado():
    """Achado: 30x60, 8φ16, C30, NSd = 1 500 -> 6,34e8 kN·cm² (era 5,06e8)."""
    c = F.Concreto(fck_mpa=30.0)
    EI = F.ei_secante(S8, c, ACO, 1500.0, 1.0, "x", n_grid=100)
    assert EI == pytest.approx(6.34e8, rel=5e-3)


@pytest.mark.parametrize("fck, Nsd", [(30.0, 600.0), (30.0, 1500.0), (70.0, 2500.0)])
def test_fco10_ei_secante_oraculo(fck, Nsd):
    """Ponto B: M = MRd/1,1 na curva de pico 1,10 fcd com N = NSd/1,1."""
    c = F.Concreto(fck_mpa=fck)
    ora = Oraculo(30.0, 60.0, [(b.y_cm, b.area_cm2) for b in B8], fck=fck)
    MB = ora.MRd(Nsd) / 1.1
    k = ora.curvatura(Nsd / 1.1, MB, pico_fn=lambda p: 1.10 * p["fcd"])
    EI_ora = MB / (k * 1e-3)
    EI = F.ei_secante(S8, c, ACO, Nsd, 1.0, "x", n_grid=120)
    assert EI == pytest.approx(EI_ora, rel=5e-3)


def test_fco10_ei_ponto_B_e_ponto_Md():
    c = F.Concreto(fck_mpa=30.0)
    EI_a = F.ei_secante(S8, c, ACO, 1500.0, 2000.0, "x", n_grid=60)
    EI_b = F.ei_secante(S8, c, ACO, 1500.0, -9000.0, "x", n_grid=60)
    assert EI_a == pytest.approx(EI_b, rel=1e-6)   # (EI)sec não depende de Md
    EI_1 = F.ei_secante(S8, c, ACO, 1500.0, 5000.0, "x", n_grid=60, ponto="Md")
    EI_2 = F.ei_secante(S8, c, ACO, 1500.0, 25000.0, "x", n_grid=60, ponto="Md")
    assert EI_2 < EI_1


# ===========================================================================
# FCO-11 -- OK só com razão >= 1 (17.2.1)
# ===========================================================================
def test_fco11_razao_abaixo_de_1_nao_verifica():
    c = F.Concreto(fck_mpa=30.0)
    MR = F.verificar_fco(SEC_6F16, c, ACO, 800.0, 1.0, 1.0, n_grid=60)["MR_kncm"]
    Md = MR / 0.995
    r = F.verificar_fco(SEC_6F16, c, ACO, 800.0, Md / math.sqrt(2), Md / math.sqrt(2), n_grid=60)
    assert r["razao"] == pytest.approx(0.995, rel=1e-4)
    assert r["status"] == "NAO_VERIFICA"   # antes: "OK" a partir de 0,99
    Md = MR / 1.001
    r = F.verificar_fco(SEC_6F16, c, ACO, 800.0, Md / math.sqrt(2), Md / math.sqrt(2), n_grid=60)
    assert r["status"] == "OK"


# ===========================================================================
# FCO-12 -- expoente da 17.2.5 (p. 145)
# ===========================================================================
def test_fco12_aviso_de_expoente():
    args = (10000.0, 10000.0, 6000.0, 6000.0)
    with warnings.catch_warnings():
        warnings.simplefilter("error", F.AvisoNBR6118)
        assert F.verificar_fco_simplificado(*args, expoente=1.0) == pytest.approx(1.2)
        F.verificar_fco_simplificado(*args, expoente=1.2)                  # retangular: ok
        F.verificar_fco_simplificado(*args, expoente=1.0, secao_retangular=False)
    with pytest.warns(F.AvisoNBR6118):
        F.verificar_fco_simplificado(*args, expoente=1.5)
    with pytest.warns(F.AvisoNBR6118):
        F.verificar_fco_simplificado(*args, expoente=1.2, secao_retangular=False)


# ===========================================================================
# FCO-15 -- um plano de deformação para a seção inteira (17.2.2 a, p. 140)
# ===========================================================================
P_INF = ((-10.0, -25.0), (10.0, -25.0), (10.0, 0.0), (-10.0, 0.0), (-10.0, -25.0))
P_SUP = ((-10.0, 0.0), (10.0, 0.0), (10.0, 25.0), (-10.0, 25.0), (-10.0, 0.0))


def _secao_duas_classes(f_inf: float, f_sup: float, n_dy: int = 200):
    return F.Secao(partes=(F.Parte(P_INF, F.Concreto(fck_mpa=f_inf)),
                           F.Parte(P_SUP, F.Concreto(fck_mpa=f_sup))),
                   barras=tuple(BARRAS_6F16), n_dy=n_dy, n_dx=4)


def test_fco15_deformacao_continua_na_interface():
    s = _secao_duas_classes(30.0, 70.0, n_dy=40)
    h_inc, yp_max = F._h_inc_yp_max_pol(s, 0.0)
    d = F._d_inc_pol(s, 0.0, yp_max)
    zonas = F._zonas_concreto_pol(s, 0.0, yp_max)
    for x in (10.0, 30.0, 45.0, 60.0, 500.0):
        e = F._strain_zonas(np.array([24.999999, 25.0, 25.000001]), x, h_inc, d, zonas)
        assert e[0] == pytest.approx(e[2], abs=1e-5)


@pytest.mark.parametrize("f_inf, f_sup", [(30.0, 70.0), (70.0, 30.0), (40.0, 90.0)])
def test_fco15_multi_fck_contra_oraculo(f_inf, f_sup):
    s = _secao_duas_classes(f_inf, f_sup)
    ora = Oraculo(B, H, ORACULO_BARRAS_6F16, zonas=[(-25.0, 0.0, f_inf), (0.0, 25.0, f_sup)])
    assert F.Nd_max_kn_pol(s, ACO) == pytest.approx(ora.N_max(), rel=1e-9)
    # a mesma seção comprimida por baixo (espelhada em y)
    ora_inv = Oraculo(B, H, [(-y, A) for y, A in ORACULO_BARRAS_6F16],
                      zonas=[(-25.0, 0.0, f_sup), (0.0, 25.0, f_inf)])
    for nu in (0.2, 0.5, 0.8, 0.95):
        Nd = nu * ora.N_max()
        r = F.verificar_fco_pol(s, ACO, Nd, 1.0, 0.0)
        M_pos, M_neg = ora.MRd(Nd), -ora_inv.MRd(Nd)
        if M_neg < 0.0 < M_pos:
            assert r["razao"] == pytest.approx(M_pos, rel=3e-3), f"ν={nu}"
        else:
            # centro plástico fora do centroide: com esse Nd, nenhum estado
            # último dá momento nulo -- a envoltória não contém a origem e
            # a seção não resiste nem Nd centrado (ν alto, concretos distintos)
            assert r["status"] == "NAO_VERIFICA" and r["razao"] == 0.0, f"ν={nu}: {r}"


def test_fco15_ate_C50_uma_zona_so():
    """C30 e C50 têm os mesmos limites (2 e 3,5 por mil): uma zona só."""
    s = _secao_duas_classes(30.0, 50.0, n_dy=40)
    _, yp_max = F._h_inc_yp_max_pol(s, 0.3)
    assert len(F._zonas_concreto_pol(s, 0.3, yp_max)) == 1


# ===========================================================================
# FCO-16 -- pivô A nos cabos; sem armadura não há pivô A (Figura 17.1)
# ===========================================================================
def test_fco16_so_cabo_pivo_A_no_cabo():
    """Achado: seção só com cabo usava d = 1 cm (+0,4 %)."""
    c35 = F.Concreto(fck_mpa=35.0)
    s = F.Secao.retangular(20.0, 60.0, c35, barras=(), cabos=(F.Cabo(0.0, -25.0, 2.0, 6.0),),
                           n_dy=240, n_dx=4)
    _, yp_max = F._h_inc_yp_max_pol(s, 0.0)
    assert F._d_inc_pol(s, 0.0, yp_max) == pytest.approx(55.0)
    ora = Oraculo(20.0, 60.0, (), fck=35.0, cabos=[(-25.0, 2.0, 6.0)])
    for Nd in (0.0, 500.0):
        r = F.verificar_fco_pol(s, ACO, Nd, 1.0, 0.0)
        assert r["razao"] == pytest.approx(ora.MRd(Nd), rel=2e-3)


def test_fco16_sem_armadura_sem_pivo_A():
    s = F.SecaoRetangular(20.0, 50.0, 2.5, ())
    _, yp_max = F._h_inc_yp_max(s, 0.0)
    assert F._d_inc(s, 0.0, yp_max) == 0.0
    c = F.Concreto(fck_mpa=30.0)
    ora = Oraculo(20.0, 50.0, (), fck=30.0)
    r = F.verificar_fco(s, c, ACO, 800.0, 1.0, 0.0, n_grid=160)
    assert r["razao"] == pytest.approx(ora.MRd(800.0), rel=2e-3)


# ===========================================================================
# FCO-18 -- razao_dc_radial em flexão normal
# ===========================================================================
@pytest.mark.parametrize("Mx, My", [(8000.0, 0.0), (0.0, 3000.0), (1.0, 3000.0), (8000.0, 1.0),
                                    (-8000.0, 0.0), (0.0, -3000.0)])
def test_fco18_razao_dc_radial_flexao_normal(Mx, My):
    """Achado: (8000, 0), (0, 3000) e (1, 3000) davam NAO_CONVERGIU."""
    c = F.Concreto(fck_mpa=30.0)
    r = F.razao_dc_radial(SEC_6F16, c, ACO, 800.0, Mx, My)
    assert r["status"] in ("OK", "NAO_VERIFICA"), r
    # continuidade com o caso quase uniaxial
    Mx2, My2 = (Mx, My + 1.0) if abs(My) < 1.0 else (Mx + 1.0, My)
    r2 = F.razao_dc_radial(SEC_6F16, c, ACO, 800.0, Mx2, My2)
    assert r["razao_dc"] == pytest.approx(r2["razao_dc"], rel=2e-3)


def test_fco18_radial_com_Nd_nulo_igual_a_verificar_fco():
    """Com Nd = 0, λ só escala o momento: razão D/C = MS/MR."""
    c = F.Concreto(fck_mpa=30.0)
    for Mx, My in ((8000.0, 0.0), (0.0, -3000.0), (-5000.0, 2000.0)):
        r = F.razao_dc_radial(SEC_ASSIM, c, ACO, 0.0, Mx, My, n_grid=60)
        v = F.verificar_fco(SEC_ASSIM, c, ACO, 0.0, Mx, My, n_grid=60)
        assert r["razao_dc"] == pytest.approx(1.0 / v["razao"], rel=2e-3)


# ===========================================================================
# FCO-04 -- envoltória mínima de 1ª ordem (11.3.3.4.3 e Figura 11.3, p. 80-81)
# ===========================================================================
def test_fco04_momento_minimo():
    """M1d,mín = Nd (0,015 + 0,03 h), h em metros."""
    assert VP.momento_minimo_1a_ordem_kncm(2100.0, 20.0) == pytest.approx(2100.0 * (0.015 + 0.03 * 0.20) * 100)
    assert VP.momentos_minimos_1a_ordem(2100.0, 20.0, 50.0) == pytest.approx((6300.0, 4410.0))
    assert VP.momento_minimo_1a_ordem_kncm(-300.0, 50.0) == 0.0
    pts = VP.envoltoria_minima(1000.0, 20.0, 50.0, n_pontos=16)
    a, b = VP.momentos_minimos_1a_ordem(1000.0, 20.0, 50.0)
    for mx, my in pts:
        assert (mx / a) ** 2 + (my / b) ** 2 == pytest.approx(1.0)


def test_fco04_envoltoria_minima_achado():
    """Achado: C30, 20x50, 6φ16, Nd = 2 100: com M1d,mín,yy = 4 410 kN·cm a
    razão é 0,340 -- não passa (o kernel dava "OK" com Md = 0)."""
    c = F.Concreto(fck_mpa=30.0)
    r = VP.verificar_envoltoria_minima(SEC_6F16, c, ACO, 2100.0)
    assert r["M1d_min_yy_kncm"] == pytest.approx(4410.0)
    assert r["status"] == "NAO_VERIFICA"
    assert r["razao_min"] == pytest.approx(0.340, abs=0.003)
    assert abs(r["My_critico_kncm"]) == pytest.approx(4410.0, rel=1e-3)


def test_fco04_envoltoria_minima_passa_e_2a_ordem():
    c = F.Concreto(fck_mpa=30.0)
    b = F.armadura_perimetral_retangular(40, 40, 3.0, 3, 3, 16.0)
    s = F.SecaoRetangular(40, 40, 3.0, b)
    r1 = VP.verificar_envoltoria_minima(s, c, ACO, 1500.0)
    assert r1["status"] == "OK" and r1["razao_min"] > 1.0
    # envoltória com 2ª ordem (Figura 15.2): semi-eixos maiores, razão menor
    r2 = VP.verificar_envoltoria_minima(s, c, ACO, 1500.0,
                                        Md_tot_min_xx_kncm=3.0 * r1["M1d_min_xx_kncm"],
                                        Md_tot_min_yy_kncm=3.0 * r1["M1d_min_yy_kncm"])
    assert r2["razao_min"] == pytest.approx(r1["razao_min"] / 3.0, rel=1e-3)
    assert r2["envoltoria"].startswith("2ª ordem")


def test_fco04_envoltoria_minima_assimetrica_bate_com_varredura():
    """Seção assimétrica: o mínimo refinado não pode passar do mínimo de uma
    varredura fina da elipse."""
    c = F.Concreto(fck_mpa=30.0)
    Nd = 900.0
    r = VP.verificar_envoltoria_minima(SEC_ASSIM, c, ACO, Nd, n_grid=60)
    a, b = r["semi_eixo_xx_kncm"], r["semi_eixo_yy_kncm"]
    varredura = min(F.verificar_fco(SEC_ASSIM, c, ACO, Nd, a * math.cos(t), b * math.sin(t), 60)["razao"]
                    for t in np.linspace(0, 2 * math.pi, 73))
    assert r["razao_min"] <= varredura * (1 + 1e-6)
    assert r["razao_min"] == pytest.approx(varredura, rel=5e-3)


def test_fco04_verificar_secao_pilar_combina():
    c = F.Concreto(fck_mpa=30.0)
    r = VP.verificar_secao_pilar(SEC_6F16, c, ACO, 2100.0, 0.0, 0.0)
    assert r["solicitacao"]["status"] == "OK"          # Md = 0: a seção sozinha passa
    assert r["envoltoria_minima"]["status"] == "NAO_VERIFICA"
    assert r["status"] == "NAO_VERIFICA"


def test_fco04_secao_poligonal_nao_retangular_recusada():
    with pytest.raises(ValueError):
        VP.verificar_envoltoria_minima(_secao_L(False), None, ACO, 800.0)
