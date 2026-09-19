# -*- coding: utf-8 -*-
"""Testes do pacote P42 — Flexo-torção de perfis abertos (NBR 6118:2026,
17.5.2, PDF p. 162-163)."""

import math

import pytest

from dimensionamento.torcao_perfis_abertos_nbr6118 import (
    FATOR_RIGIDEZ_FLEXO_TORCAO,
    FATOR_RIGIDEZ_TORCAO_UNIFORME,
    FaixaNormativaError,
    ResistenciaFlexoTorcao,
    RigidezFlexoTorcao,
    RigidezesReduzidas,
    TRd_flexo_torcao,
    rigidez_flexo_torcao,
    rigidezes_reduzidas,
)


# ---------------------------------------------------------------------------
# 17.5.2.2 — rigidezes reduzidas (0,15 e 0,50 da rigidez elástica)
# ---------------------------------------------------------------------------
def test_fatores_rigidez_reduzida_conforme_norma():
    """17.5.2.2 (PDF p. 162): 0,15 para torção uniforme, 0,50 para
    flexo-torção — os dois coeficientes citados no texto da norma."""
    assert FATOR_RIGIDEZ_TORCAO_UNIFORME == pytest.approx(0.15)
    assert FATOR_RIGIDEZ_FLEXO_TORCAO == pytest.approx(0.50)


def test_rigidezes_reduzidas_caso_basico():
    """GJ_elastico = 1000 kN.cm2; r_elastico = 2000 kN.cm/rad.
    Reduzida uniforme = 0,15 x 1000 = 150 kN.cm2.
    Reduzida flexo-torção = 0,50 x 2000 = 1000 kN.cm/rad.
    Como 1000 > 150, o mecanismo de maior rigidez reduzida é a flexo-torção."""
    r = rigidezes_reduzidas(1000.0, 2000.0)
    assert isinstance(r, RigidezesReduzidas)
    assert r.rigidez_torcao_uniforme_reduzida_kncm2 == pytest.approx(150.0)
    assert r.rigidez_flexo_torcao_reduzida_kncm_por_rad == pytest.approx(1000.0)
    assert r.governante == "flexo_torcao"
    assert r.ok is True


def test_rigidezes_reduzidas_torcao_uniforme_governante():
    """GJ_elastico = 10000 -> reduzida = 1500; r_elastico = 1000 -> reduzida
    = 500. 1500 > 500: torção uniforme é o mecanismo de maior rigidez."""
    r = rigidezes_reduzidas(10000.0, 1000.0)
    assert r.rigidez_torcao_uniforme_reduzida_kncm2 == pytest.approx(1500.0)
    assert r.rigidez_flexo_torcao_reduzida_kncm_por_rad == pytest.approx(500.0)
    assert r.governante == "torcao_uniforme"


def test_rigidezes_reduzidas_zero_e_fronteira():
    """Rigidez elástica nula é uma entrada válida (mecanismo inexistente
    nesse caso): a reduzida também sai nula, sem erro."""
    r = rigidezes_reduzidas(0.0, 0.0)
    assert r.rigidez_torcao_uniforme_reduzida_kncm2 == pytest.approx(0.0)
    assert r.rigidez_flexo_torcao_reduzida_kncm_por_rad == pytest.approx(0.0)


def test_rigidezes_reduzidas_negativa_levanta_erro():
    with pytest.raises(FaixaNormativaError):
        rigidezes_reduzidas(-1.0, 100.0)
    with pytest.raises(FaixaNormativaError):
        rigidezes_reduzidas(100.0, -1.0)


# ---------------------------------------------------------------------------
# 17.5.2.3 — rigidez à flexo-torção (Figura 17.5): theta=(a1+a2)/z; r=T/theta
# ---------------------------------------------------------------------------
def test_rigidez_flexo_torcao_caso_simetrico_a_mao():
    """Caso simétrico montado à mão: a1 = a2 = 0,5 cm, z = 50 cm,
    T = 1000 kN.cm.
    theta = (0,5 + 0,5) / 50 = 1,0 / 50 = 0,02 rad.
    r = 1000 / 0,02 = 50000 kN.cm/rad."""
    r = rigidez_flexo_torcao(a1_cm=0.5, a2_cm=0.5, z_cm=50.0, T_kncm=1000.0)
    assert isinstance(r, RigidezFlexoTorcao)
    assert r.theta_rad == pytest.approx(0.02)
    assert r.r_kncm_por_rad == pytest.approx(50000.0)
    assert r.ok is True
    # empate de flechas: parede_1 por convenção (a1 >= a2)
    assert r.governante == "parede_1"


def test_rigidez_flexo_torcao_caso_assimetrico():
    """a1 = 0,8 cm, a2 = 0,2 cm, z = 40 cm, T = 600 kN.cm.
    theta = (0,8 + 0,2) / 40 = 1,0 / 40 = 0,025 rad.
    r = 600 / 0,025 = 24000 kN.cm/rad. Parede 1 é a mais flexível (a1>a2)."""
    r = rigidez_flexo_torcao(a1_cm=0.8, a2_cm=0.2, z_cm=40.0, T_kncm=600.0)
    assert r.theta_rad == pytest.approx(0.025)
    assert r.r_kncm_por_rad == pytest.approx(24000.0)
    assert r.governante == "parede_1"

    r2 = rigidez_flexo_torcao(a1_cm=0.2, a2_cm=0.8, z_cm=40.0, T_kncm=600.0)
    assert r2.governante == "parede_2"
    assert r2.r_kncm_por_rad == pytest.approx(24000.0)


def test_rigidez_flexo_torcao_z_invalido():
    with pytest.raises(FaixaNormativaError):
        rigidez_flexo_torcao(a1_cm=1.0, a2_cm=1.0, z_cm=0.0, T_kncm=100.0)
    with pytest.raises(FaixaNormativaError):
        rigidez_flexo_torcao(a1_cm=1.0, a2_cm=1.0, z_cm=-10.0, T_kncm=100.0)


def test_rigidez_flexo_torcao_flecha_negativa():
    with pytest.raises(FaixaNormativaError):
        rigidez_flexo_torcao(a1_cm=-0.1, a2_cm=1.0, z_cm=50.0, T_kncm=100.0)
    with pytest.raises(FaixaNormativaError):
        rigidez_flexo_torcao(a1_cm=1.0, a2_cm=-0.1, z_cm=50.0, T_kncm=100.0)


def test_rigidez_flexo_torcao_theta_nulo_levanta_erro():
    """a1 = a2 = 0 -> theta = 0 -> rigidez indefinida (divisão por zero
    evitada com erro explícito, não com inf/nan silencioso)."""
    with pytest.raises(FaixaNormativaError):
        rigidez_flexo_torcao(a1_cm=0.0, a2_cm=0.0, z_cm=50.0, T_kncm=100.0)


# ---------------------------------------------------------------------------
# 17.5.2.4 — resistência à flexo-torção: TRd = delta_FRd,min * z
# ---------------------------------------------------------------------------
def test_TRd_flexo_torcao_caso_simetrico_a_mao():
    """Caso simétrico: as duas paredes têm o mesmo excedente de resistência
    à flexão. FRd = 100 kN, FSd = 40 kN nas duas -> delta = 60 kN nas duas.
    z = 80 cm -> TRd = 60 x 80 = 4800 kN.cm."""
    r = TRd_flexo_torcao(
        FRd_parede1_kn=100.0, FSd_parede1_kn=40.0,
        FRd_parede2_kn=100.0, FSd_parede2_kn=40.0,
        z_cm=80.0,
    )
    assert isinstance(r, ResistenciaFlexoTorcao)
    assert r.delta_FRd_parede1_kn == pytest.approx(60.0)
    assert r.delta_FRd_parede2_kn == pytest.approx(60.0)
    assert r.delta_FRd_min_kn == pytest.approx(60.0)
    assert r.TRd_kncm == pytest.approx(4800.0)
    assert r.ok is True
    assert r.governante == "parede_1"  # empate: parede_1 por convenção


def test_TRd_flexo_torcao_parede_2_governante():
    """Parede 2 tem excedente menor (40 < 60): governa o TRd.
    delta1 = 100-40 = 60; delta2 = 90-50 = 40; delta_min = 40.
    z = 80 -> TRd = 40 x 80 = 3200 kN.cm."""
    r = TRd_flexo_torcao(
        FRd_parede1_kn=100.0, FSd_parede1_kn=40.0,
        FRd_parede2_kn=90.0, FSd_parede2_kn=50.0,
        z_cm=80.0,
    )
    assert r.delta_FRd_min_kn == pytest.approx(40.0)
    assert r.governante == "parede_2"
    assert r.TRd_kncm == pytest.approx(3200.0)
    assert r.ok is True


def test_TRd_flexo_torcao_delta_zero_fronteira_nao_ok():
    """delta_FRd,min = 0 (parede exatamente no limite de flexão simples,
    sem folga nenhuma para torção adicional): TRd = 0, ok = False."""
    r = TRd_flexo_torcao(
        FRd_parede1_kn=100.0, FSd_parede1_kn=100.0,
        FRd_parede2_kn=100.0, FSd_parede2_kn=40.0,
        z_cm=80.0,
    )
    assert r.delta_FRd_min_kn == pytest.approx(0.0)
    assert r.TRd_kncm == pytest.approx(0.0)
    assert r.ok is False


def test_TRd_flexo_torcao_delta_negativo():
    """Parede já esgotada por flexão simples antes mesmo da torção
    (FSd > FRd): delta negativo, TRd negativo, ok = False."""
    r = TRd_flexo_torcao(
        FRd_parede1_kn=100.0, FSd_parede1_kn=120.0,
        FRd_parede2_kn=100.0, FSd_parede2_kn=40.0,
        z_cm=80.0,
    )
    assert r.delta_FRd_parede1_kn == pytest.approx(-20.0)
    assert r.delta_FRd_min_kn == pytest.approx(-20.0)
    assert r.TRd_kncm == pytest.approx(-1600.0)
    assert r.ok is False


def test_TRd_flexo_torcao_z_invalido():
    with pytest.raises(FaixaNormativaError):
        TRd_flexo_torcao(
            FRd_parede1_kn=100.0, FSd_parede1_kn=40.0,
            FRd_parede2_kn=100.0, FSd_parede2_kn=40.0,
            z_cm=0.0,
        )
    with pytest.raises(FaixaNormativaError):
        TRd_flexo_torcao(
            FRd_parede1_kn=100.0, FSd_parede1_kn=40.0,
            FRd_parede2_kn=100.0, FSd_parede2_kn=40.0,
            z_cm=-5.0,
        )
