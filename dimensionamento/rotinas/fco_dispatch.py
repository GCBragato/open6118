"""Dispatcher Python <-> C++ para FCO.

Mantem o pipeline Python original intacto. Permite trocar para o backend
C++ via flag global `USE_CPP` (modulo) ou parametro `use_cpp` por chamada.

Uso:
    from dimensionamento.rotinas import fco_dispatch as fco

    # Usar Python (default)
    res = fco.verificar_fco(secao_py, concreto_py, aco_py, Nd, Mx, My)

    # Usar C++ (per-call):
    res = fco.verificar_fco(secao_py, concreto_py, aco_py, Nd, Mx, My, use_cpp=True)

    # Ativar globalmente:
    fco.USE_CPP = True
    res = fco.verificar_fco(secao_py, concreto_py, aco_py, Nd, Mx, My)

Quando `use_cpp=True`, os objetos Python (Concreto, Aco, SecaoRetangular,
Barra) sao convertidos transparentemente para os tipos C++. Nenhum codigo
Python precisa mudar.
"""

from __future__ import annotations

from typing import Any

from .flexao_composta_obliqua import (
    Aco as PAco,
    Barra as PBarra,
    Concreto as PConcreto,
    SecaoRetangular as PSec,
    verificar_fco as _py_verificar_fco,
    razao_dc_radial as _py_razao_dc_radial,
)

try:
    from .fco_cpp import _native as _cpp
    CPP_AVAILABLE = _cpp is not None
except ImportError:
    _cpp = None
    CPP_AVAILABLE = False

# Flag global default
USE_CPP: bool = False


def _to_cpp_concreto(c: PConcreto):
    return _cpp.Concreto(c.fck_mpa, c.gama_c)


def _to_cpp_aco(a: PAco):
    return _cpp.Aco(a.fyk_mpa, a.Es_kncm2, a.gama_s)


def _to_cpp_secao(s: PSec):
    barras = [_cpp.Barra(b.x_cm, b.y_cm, b.area_cm2) for b in s.barras]
    return _cpp.SecaoRetangular(s.base_cm, s.altura_cm, s.cobrimento_cm, barras)


def _resolve(use_cpp: bool | None) -> bool:
    if use_cpp is None:
        return USE_CPP and CPP_AVAILABLE
    if use_cpp and not CPP_AVAILABLE:
        raise RuntimeError(
            "use_cpp=True mas backend C++ nao disponivel. "
            "Compile com `dimensionamento/rotinas/fco_cpp/build.bat`."
        )
    return use_cpp


def verificar_fco(
    secao: PSec,
    concreto: PConcreto,
    aco: PAco,
    Nd_kn: float,
    Mxd_kncm: float,
    Myd_kncm: float,
    n_grid: int = 80,
    *,
    use_cpp: bool | None = None,
) -> dict:
    if _resolve(use_cpp):
        return _cpp.verificar_fco(
            _to_cpp_secao(secao),
            _to_cpp_concreto(concreto),
            _to_cpp_aco(aco),
            Nd_kn, Mxd_kncm, Myd_kncm, n_grid,
        )
    return _py_verificar_fco(secao, concreto, aco, Nd_kn, Mxd_kncm, Myd_kncm, n_grid)


def razao_dc_radial(
    secao: PSec,
    concreto: PConcreto,
    aco: PAco,
    Nd_kn: float,
    Mxd_kncm: float,
    Myd_kncm: float,
    n_grid: int = 60,
    *,
    use_cpp: bool | None = None,
) -> dict:
    if _resolve(use_cpp):
        return _cpp.razao_dc_radial(
            _to_cpp_secao(secao),
            _to_cpp_concreto(concreto),
            _to_cpp_aco(aco),
            Nd_kn, Mxd_kncm, Myd_kncm, n_grid,
        )
    return _py_razao_dc_radial(secao, concreto, aco, Nd_kn, Mxd_kncm, Myd_kncm, n_grid)
