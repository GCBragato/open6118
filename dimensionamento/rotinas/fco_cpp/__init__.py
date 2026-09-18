"""Backend C++ nativo para FCO (open6118).

Modulo binario compilado via pybind11. Expoe SecaoRetangular, Concreto,
Aco, Barra + verificar_fco e razao_dc_radial.

Para alternar entre Python e C++ em chamadas, use o dispatcher em
`dimensionamento.rotinas.fco_dispatch`.
"""

try:
    from . import _fco_native as _native
    AVAILABLE = True
except ImportError as _e:  # pragma: no cover
    _native = None
    AVAILABLE = False
    _import_error = _e

__all__ = ["AVAILABLE", "_native"]
