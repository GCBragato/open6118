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

Paridade (decisao 7 da auditoria NBR 6118:2026): o C++ so e usado quando o
caso tem paridade medida com o Python -- backend com as correcoes da
NBR 6118:2026 (`VERSAO_KERNEL` >= 2; paridade medida de C20 a C90, dominio 5
e secao assimetrica em tests/test_fco_nbr2026.py) e concreto com a curva
padrao da norma. Fora disso (curva de concreto do usuario, que o C++ nao
tem, ou backend antigo), o calculo cai para o Python com `AvisoNBR6118`,
em vez de descartar a curva em silencio (FCO-08).
"""

from __future__ import annotations

import warnings
from typing import Any

from .flexao_composta_obliqua import (
    Aco as PAco,
    AvisoNBR6118,
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

# Versao minima do backend C++ com as correcoes da NBR 6118:2026 (eta_c,
# pivo C, patamar alem de eps_cu, sinal dos momentos, Nd_max, flexao normal
# no razao_dc_radial).
VERSAO_KERNEL_MINIMA = 2
CPP_VERSAO = int(getattr(_cpp, "VERSAO_KERNEL", 1)) if CPP_AVAILABLE else 0
CPP_PARIDADE = CPP_AVAILABLE and CPP_VERSAO >= VERSAO_KERNEL_MINIMA

# Flag global default
USE_CPP: bool = False


def _to_cpp_concreto(c: PConcreto):
    if c.curva is not None:
        # FCO-08: o C++ so tem a parabola-retangulo da norma; nunca descartar
        # a curva do usuario em silencio (`_resolve` ja desvia para o Python).
        raise ValueError(
            "O backend C++ não aceita curva de concreto customizada; "
            "use o backend Python (use_cpp=False)."
        )
    return _cpp.Concreto(c.fck_mpa, c.gama_c)


def _to_cpp_aco(a: PAco):
    return _cpp.Aco(a.fyk_mpa, a.Es_kncm2, a.gama_s)


def _to_cpp_secao(s: PSec):
    barras = [_cpp.Barra(b.x_cm, b.y_cm, b.area_cm2) for b in s.barras]
    return _cpp.SecaoRetangular(s.base_cm, s.altura_cm, s.cobrimento_cm, barras)


def _motivo_sem_paridade(concreto: PConcreto) -> str | None:
    """Por que o caso nao tem paridade Python x C++ (None se tem)."""
    if not CPP_PARIDADE:
        return (
            f"o backend C++ compilado (versão {CPP_VERSAO}) não tem as correções da "
            "NBR 6118:2026; recompile com dimensionamento/rotinas/fco_cpp/build.bat"
        )
    if concreto.curva is not None:
        return "o backend C++ só tem a parábola-retângulo da norma e descartaria a curva de concreto informada"
    return None


def _resolve(use_cpp: bool | None, concreto: PConcreto | None = None) -> bool:
    if use_cpp is None:
        pedido = USE_CPP and CPP_AVAILABLE
    elif use_cpp and not CPP_AVAILABLE:
        raise RuntimeError(
            "use_cpp=True mas backend C++ nao disponivel. "
            "Compile com `dimensionamento/rotinas/fco_cpp/build.bat`."
        )
    else:
        pedido = use_cpp
    if not pedido:
        return False
    motivo = _motivo_sem_paridade(concreto) if concreto is not None else None
    if motivo is not None:
        warnings.warn(
            f"Cálculo feito em Python, não em C++: {motivo}.",
            AvisoNBR6118,
            stacklevel=3,
        )
        return False
    return True


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
    if _resolve(use_cpp, concreto):
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
    if _resolve(use_cpp, concreto):
        return _cpp.razao_dc_radial(
            _to_cpp_secao(secao),
            _to_cpp_concreto(concreto),
            _to_cpp_aco(aco),
            Nd_kn, Mxd_kncm, Myd_kncm, n_grid,
        )
    return _py_razao_dc_radial(secao, concreto, aco, Nd_kn, Mxd_kncm, Myd_kncm, n_grid)
