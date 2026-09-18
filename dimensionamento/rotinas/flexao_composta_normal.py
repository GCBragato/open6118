"""Flexao Composta Normal (NBR 6118:2023).

Wrapper sobre o kernel FCO restrito ao caso uniaxial (Myd = 0). Toda a
mecanica de pivos/dominio/integracao reside em
`flexao_composta_obliqua.py`; aqui so se expoe uma API mais conveniente
para flexao normal (caso comum em vigas).

Convencoes herdadas do FCO:
    - fck em MPa. Geometria em cm. Forcas em kN. Momentos em kN.cm.
    - Compressao positiva.
    - Md em torno do eixo x (causa flexao no plano y).
"""

from __future__ import annotations

from .flexao_composta_obliqua import (
    Aco,
    Concreto,
    SecaoRetangular,
    dimensionar_as_fco,
    verificar_fco,
)


def verificar_fcn(
    secao: SecaoRetangular,
    concreto: Concreto,
    aco: Aco,
    Nd_kn: float,
    Md_kncm: float,
    n_grid: int = 80,
) -> dict:
    """Verifica secao sob flexao composta normal (Md em torno de x)."""
    return verificar_fco(secao, concreto, aco, Nd_kn, Md_kncm, 0.0, n_grid)


def dimensionar_as_fcn(
    base_cm: float,
    altura_cm: float,
    cobrimento_cm: float,
    nx: int,
    ny: int,
    fi_l_mm: float,
    concreto: Concreto,
    aco: Aco,
    Nd_kn: float,
    Md_kncm: float,
    fi_t_mm: float = 5.0,
    As_total_min_cm2: float = 0.4,
    As_total_max_cm2: float | None = None,
    tol: float = 0.01,
    iter_max: int = 30,
    n_grid: int = 60,
) -> dict:
    """Dimensiona armadura para flexao composta normal."""
    return dimensionar_as_fco(
        base_cm=base_cm,
        altura_cm=altura_cm,
        cobrimento_cm=cobrimento_cm,
        nx=nx,
        ny=ny,
        fi_l_mm=fi_l_mm,
        concreto=concreto,
        aco=aco,
        Nd_kn=Nd_kn,
        Mxd_kncm=Md_kncm,
        Myd_kncm=0.0,
        fi_t_mm=fi_t_mm,
        As_total_min_cm2=As_total_min_cm2,
        As_total_max_cm2=As_total_max_cm2,
        tol=tol,
        iter_max=iter_max,
        n_grid=n_grid,
    )
