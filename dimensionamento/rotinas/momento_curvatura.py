"""Relação momento-curvatura M, N, 1/r (NBR 6118:2026, 15.3.1 e 15.8.3.3.4).

Pacote P28. Constrói, para uma seção retangular com armadura conhecida e
força normal fixa, o diagrama M, N, 1/r da Figura 15.1 (PDF p. 121):

- curva cheia AB, usada no cálculo das deformações: concreto com pico
  1,10·fcd e força normal NRd/γf3, com γf3 = 1,1 (15.3.1);
- curva tracejada, de ELU (0,85·ηc·fcd), usada só para achar o momento
  resistente MRd correspondente a NRd = NSd;
- ponto B: M = MRd/γf3 na curva AB; a reta AB dá a rigidez secante
  (EI)sec, a mesma de ``flexao_composta_obliqua.ei_secante``.

O diagrama é o ingrediente do pilar-padrão acoplado a diagramas M, N, 1/r
(15.8.3.3.4) e do método geral (15.8.3.2), que ficam em
``rotinas/verificacao_pilar.py``. Tudo aqui é Python: o kernel em C++ só
faz o ELU de seção, e estes casos não passam pelo ``fco_dispatch``.

Convenções do kernel (``flexao_composta_obliqua``): compressão positiva;
eixo "x" = momento em torno de x (curvatura kx, dimensão altura_cm);
eixo "y" = momento em torno de y (curvatura ky, dimensão base_cm).
Unidades: kN, cm, kN·cm; curvatura em 1/cm (o kernel usa ‰/cm).
"""

from __future__ import annotations

import math
import os
import sys
import warnings
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

try:  # importado como pacote (dimensionamento.rotinas.momento_curvatura)
    from . import flexao_composta_obliqua as fco
except ImportError:  # executado como script: põe a raiz do repositório no sys.path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from dimensionamento.rotinas import flexao_composta_obliqua as fco

nbr = fco.nbr   # o mesmo núcleo normativo que o kernel usa

GAMA_F3 = nbr.GAMA_F3   # 15.3.1 (PDF p. 121)
_TOL_LIMITE = 1e-9


def _fmt(x: float) -> str:
    """Número para a memória de cálculo, com vírgula decimal."""
    return f"{x:.6g}".replace(".", ",")


@dataclass(frozen=True)
class DiagramaMNCurvatura:
    """Diagrama M, N, 1/r de uma seção para uma força normal (15.3.1, Figura 15.1).

    ``curvaturas_1_cm`` e ``momentos_kncm`` são os pontos da curva AB (pico
    1,10·fcd, força normal Nd/γf3), em módulo, do momento nulo até o limite
    de deformação da Figura 17.1 (último ponto). O momento é o da curva AB,
    isto é, já dividido por γf3: para um momento de cálculo Md, a curvatura
    é ``curvatura(Md/γf3)`` (15.3.1).
    """
    Nd_kn: float                    # NRd = NSd (compressão positiva)
    N_curva_kn: float               # Nd/γf3, força normal da curva AB
    gama_f3: float
    eixo: str
    sentido: float                  # +1 ou −1: sentido do momento
    curvaturas_1_cm: tuple[float, ...]
    momentos_kncm: tuple[float, ...]
    M_max_curva_kncm: float         # maior momento da curva AB
    curvatura_M_max_1_cm: float
    MRd_kncm: float                 # ELU (0,85·ηc·fcd) para NRd, no eixo e sentido
    M_B_kncm: float                 # MRd/γf3
    curvatura_B_1_cm: float         # (1/r) no ponto B
    EI_sec_kncm2: float             # (MRd/γf3)/(1/r)_B
    memoria: tuple[str, ...]

    def _ramo_ascendente(self) -> tuple[np.ndarray, np.ndarray]:
        k = np.asarray(self.curvaturas_1_cm)
        m = np.asarray(self.momentos_kncm)
        i = int(np.argmax(m))
        return k[: i + 1], m[: i + 1]

    def curvatura(self, M_kncm: float) -> float:
        """1/r (1/cm) no ramo ascendente da curva AB para o momento |M| (já ÷ γf3).

        Interpolação linear entre os pontos do diagrama. Acima do maior
        momento da curva não há equilíbrio: levanta ``FaixaNormativaError``.
        """
        M = abs(float(M_kncm))
        if M > self.M_max_curva_kncm * (1.0 + 1e-12):
            raise nbr.FaixaNormativaError(
                f"M = {M:.6g} kN·cm acima do máximo da curva M, N, 1/r "
                f"({self.M_max_curva_kncm:.6g} kN·cm): não há equilíbrio na seção (15.3.1)."
            )
        k, m = self._ramo_ascendente()
        return float(np.interp(M, m, k))

    def momento(self, curvatura_1_cm: float) -> float:
        """|M| da curva AB (kN·cm, já ÷ γf3) para a curvatura |1/r| (1/cm)."""
        c = abs(float(curvatura_1_cm))
        k = np.asarray(self.curvaturas_1_cm)
        if c > k[-1] * (1.0 + 1e-12):
            raise nbr.FaixaNormativaError(
                f"1/r = {c:.6g} 1/cm além do limite de deformação da Figura 17.1 "
                f"({k[-1]:.6g} 1/cm)."
            )
        return float(np.interp(c, k, np.asarray(self.momentos_kncm)))


def _validar_secao(secao) -> None:
    if not isinstance(secao, fco.SecaoRetangular):
        raise TypeError(
            "O diagrama M, N, 1/r (15.3.1) está implementado para SecaoRetangular."
        )


def _estado(secao, conc_ab, aco, N_kn, k_pmil_cm, eixo, n_grid):
    """(eps_cg, M no eixo, M perpendicular) para curvatura k (‰/cm) e N fixo."""
    ext = max(secao.base_cm, secao.altura_cm)
    kx, ky = (k_pmil_cm, 0.0) if eixo == "x" else (0.0, k_pmil_cm)

    def forcas(e0):
        Nr, Mxr, Myr = fco._esforcos_internos_els(secao, conc_ab, aco, e0, kx, ky, n_grid)
        return (Nr, Mxr, Myr) if eixo == "x" else (Nr, Myr, Mxr)

    lim = 20.0 + abs(k_pmil_cm) * ext
    if forcas(lim)[0] < N_kn:
        raise nbr.FaixaNormativaError(
            f"N = {N_kn:.6g} kN acima da capacidade da seção à compressão na curva "
            "de 1,10·fcd (15.3.1)."
        )
    e0 = brentq(lambda e: forcas(e)[0] - N_kn, -lim, lim, xtol=1e-12, rtol=1e-12)
    _, M, Mp = forcas(e0)
    return e0, M, Mp


def _razao_limite(secao, concreto, e0, k_pmil_cm, eixo) -> float:
    """max(εtopo/εcu, εC/εc2, −εs/10‰) da deformada; <= 1 dentro da Figura 17.1."""
    meia = (secao.altura_cm if eixo == "x" else secao.base_cm) / 2.0
    h = 2.0 * meia
    kk = abs(k_pmil_cm)
    e_topo = e0 + kk * meia
    ecu = concreto.eps_cu_pmilh
    ec2 = min(concreto.eps_c2_pmilh, ecu)
    rho = concreto.pivo_C_rel
    e_C = e_topo - kk * rho * h
    r = max(e_topo / ecu, e_C / ec2)
    arr = secao._barras_xyA
    if arr.shape[0] > 0:
        coord = arr[:, 1] if eixo == "x" else arr[:, 0]
        eps_b = e0 + k_pmil_cm * coord
        r = max(r, -float(eps_b.min()) / nbr.EPS_SU)
    return r


def diagrama_M_N_curvatura(
    secao,
    concreto,
    aco,
    Nd_kn: float,
    n_pontos: int = 40,
    eixo: str = "x",
    sentido: float = 1.0,
    gama_f3: float = GAMA_F3,
    n_grid: int = 60,
) -> DiagramaMNCurvatura:
    """Diagrama M, N, 1/r da seção para a força normal Nd (15.3.1 e Figura 15.1, PDF p. 121).

    "O principal efeito da não linearidade física pode [...] ser considerado
    através da construção da relação momento-curvatura para cada seção, com
    armadura suposta conhecida, e para o valor da força normal atuante."
    Formulação de segurança de 15.3.1: Sd,tot = γf3·S(F), com as cargas
    divididas por γf3 = 1,1. Daí:

    - curva AB: concreto parábola-retângulo com pico 1,10·fcd (mesmos εc2,
      εcu e n; ``flexao_composta_obliqua._concreto_curva_15_3_1``), aço
      bilinear de cálculo e força normal NRd/γf3, com NRd = NSd = Nd;
    - curva de ELU (0,85·ηc·fcd), só para MRd com NRd (``momento_resistente_fco``);
    - ponto B: M = MRd/γf3 na curva AB, (EI)sec = (MRd/γf3)/(1/r)_B.

    Cada ponto resolve o equilíbrio de força normal com a curvatura imposta
    no eixo (``_esforcos_internos_els``, Bernoulli, 17.2.2 a); a curvatura
    vai de 0 até a deformada que atinge o primeiro limite da Figura 17.1
    (εcu na face, εc2 no pivô C ou −10 ‰ na armadura), em ``n_pontos``
    pontos uniformes, mais o ponto B. Seção não simétrica em relação ao
    plano de flexão gera momento na outra direção, que o diagrama não
    anula; acima de 0,1 % do momento emite ``AvisoNBR6118``.

    Nd em kN (compressão positiva; tração também é aceita), ``eixo`` "x"
    (altura_cm) ou "y" (base_cm), ``sentido`` +1 ou −1 (sinal do momento
    na convenção do kernel). Devolve ``DiagramaMNCurvatura``.
    """
    _validar_secao(secao)
    if eixo not in ("x", "y"):
        raise ValueError(f"eixo deve ser 'x' ou 'y', recebido {eixo!r}.")
    if sentido not in (1, -1, 1.0, -1.0):
        raise ValueError(f"sentido deve ser +1 ou −1, recebido {sentido!r}.")
    if int(n_pontos) < 5:
        raise ValueError("n_pontos deve ser pelo menos 5.")
    gf3 = float(gama_f3)
    if not (gf3 >= 1.0):
        raise nbr.FaixaNormativaError(f"γf3 = {gf3:g} inválido (15.3.1: γf3 = 1,1).")
    Nd = float(Nd_kn)
    s = float(sentido)
    N_ab = Nd / gf3
    conc_ab = fco._concreto_curva_15_3_1(concreto)

    # MRd (curva tracejada, ELU) com NRd = Nd, no eixo e no sentido pedidos.
    theta = (0.0 if s > 0 else math.pi) if eixo == "x" else (
        math.pi / 2.0 if s > 0 else -math.pi / 2.0)
    Nmax = fco.Nd_max_kn(secao, concreto, aco)
    Nmin = fco.Nd_min_kn(secao, aco)
    if not (Nmin < Nd < Nmax):
        raise nbr.FaixaNormativaError(
            f"Nd = {Nd:.6g} kN fora da faixa resistente da seção "
            f"({Nmin:.6g} a {Nmax:.6g} kN, retas a e b da Figura 17.1)."
        )
    try:
        r_elu = fco.momento_resistente_fco(secao, concreto, aco, Nd, theta, n_grid)
    except (ValueError, RuntimeError) as e:
        raise nbr.FaixaNormativaError(f"MRd não encontrado para Nd = {Nd:.6g} kN: {e}") from e
    MRd = float(r_elu["MR_kncm"])

    # Curvatura-limite (Figura 17.1) por bisseção; razão cresce com a curvatura.
    def razao(k):
        e0, _, _ = _estado(secao, conc_ab, aco, N_ab, s * k, eixo, n_grid)
        return _razao_limite(secao, concreto, e0, s * k, eixo)

    r0 = razao(0.0)
    if r0 > 1.0 + _TOL_LIMITE:
        raise nbr.FaixaNormativaError(
            f"Com N = Nd/γf3 = {N_ab:.6g} kN a deformação uniforme já passa de εc2 "
            "(reta b, Figura 17.1): não há curva M, N, 1/r."
        )
    k_hi = 1e-3
    while razao(k_hi) < 1.0:
        k_hi *= 2.0
        if k_hi > 1e3:
            raise nbr.FaixaNormativaError("Curvatura-limite da Figura 17.1 não encontrada.")
    k_lim = brentq(lambda k: razao(k) - 1.0, 0.0, k_hi, xtol=1e-12, rtol=1e-10)

    ks = [k_lim * i / (int(n_pontos) - 1) for i in range(int(n_pontos))]
    Ms = []
    Mp_max = 0.0
    for k in ks:
        _, M, Mp = _estado(secao, conc_ab, aco, N_ab, s * k, eixo, n_grid)
        Ms.append(s * M)
        Mp_max = max(Mp_max, abs(Mp))
    aviso_perp = Mp_max / max(max(abs(m) for m in Ms), 1e-300)
    if aviso_perp > 1e-3:
        warnings.warn(
            f"Seção não simétrica em relação ao plano de flexão: momento perpendicular de "
            f"até {100 * aviso_perp:.2g} % do momento no diagrama M, N, 1/r (15.3.1), "
            "que impõe curvatura só no eixo pedido.",
            nbr.AvisoNBR6118, stacklevel=2,
        )
    Ms[0] = 0.0

    # Ponto B: M = MRd/γf3 na curva AB.
    M_B = MRd / gf3
    i_max = int(np.argmax(Ms))
    M_max = Ms[i_max]
    if M_B > M_max:
        raise nbr.FaixaNormativaError(
            f"MRd/γf3 = {M_B:.6g} kN·cm acima do máximo da curva AB ({M_max:.6g} kN·cm) (15.3.1)."
        )
    j = next(i for i in range(1, i_max + 1) if Ms[i] >= M_B)

    def res_B(k):
        return s * _estado(secao, conc_ab, aco, N_ab, s * k, eixo, n_grid)[1] - M_B

    k_B = brentq(res_B, ks[j - 1], ks[j], xtol=1e-14, rtol=1e-12) if Ms[j] > M_B else ks[j]
    pares = sorted(set(zip(ks, Ms)) | {(k_B, M_B)})
    ks_pmil = [p[0] for p in pares]
    Ms = [p[1] for p in pares]
    curv = tuple(k * 1e-3 for k in ks_pmil)          # ‰/cm -> 1/cm
    i_max = int(np.argmax(Ms))
    EI_sec = M_B / (k_B * 1e-3) if k_B > 0.0 else float("inf")

    memoria = (
        f"15.3.1: diagrama M, N, 1/r, eixo {eixo}, sentido {'+' if s > 0 else '−'}; "
        f"Nd = NRd = {_fmt(Nd)} kN; γf3 = {_fmt(gf3)}.",
        f"15.3.1: curva AB com pico 1,10·fcd e N = Nd/γf3 = {_fmt(N_ab)} kN, "
        f"{len(curv)} pontos até o limite de deformação da Figura 17.1 "
        f"(1/r = {_fmt(curv[-1])} 1/cm).",
        f"15.3.1: MRd (curva de ELU, 0,85·ηc·fcd, NRd = {_fmt(Nd)} kN) = {_fmt(MRd)} kN·cm.",
        f"15.3.1: ponto B: M = MRd/γf3 = {_fmt(M_B)} kN·cm, 1/r = {_fmt(k_B * 1e-3)} 1/cm; "
        f"(EI)sec = {_fmt(EI_sec)} kN·cm².",
        f"15.3.1: maior momento da curva AB = {_fmt(Ms[i_max])} kN·cm.",
    )
    return DiagramaMNCurvatura(
        Nd_kn=Nd, N_curva_kn=N_ab, gama_f3=gf3, eixo=eixo, sentido=s,
        curvaturas_1_cm=curv, momentos_kncm=tuple(Ms),
        M_max_curva_kncm=float(Ms[i_max]), curvatura_M_max_1_cm=float(curv[i_max]),
        MRd_kncm=MRd, M_B_kncm=M_B, curvatura_B_1_cm=k_B * 1e-3,
        EI_sec_kncm2=EI_sec, memoria=memoria,
    )
