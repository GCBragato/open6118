"""Pilares (pilares_bastos.py) contra a NBR 6118:2026 — achados PIL-01 a PIL-04.

Valores esperados das reproduções verificadas na auditoria de 18/09/2026.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import pilares_bastos as P  # noqa: E402

# Exemplo 13.1.1 da apostila: pilar intermediário 20x50, Nd = 1400 kN, C30, le = 280 cm
BASE = dict(Nd_kn=1400.0, le_cm=280.0, h_cm=20.0, fck_mpa=30.0, Ac_cm2=1000.0)


def test_PIL01_curvatura_soma_M2d_ao_minimo():
    # 15.8.3.3.2 (p. 129) + 11.3.3.4.3 (p. 80): 2940 + 2379,19 = 5319,19 kN.cm
    r = P.Mdtot_curvatura_aprox(M1d_A_kncm=0.0, alpha_b_val=1.0, **BASE)
    assert r["Md_tot_kncm"] == pytest.approx(5319.19, abs=0.05)
    assert r["M1d_A_ef_kncm"] == pytest.approx(2940.0)


def test_PIL01_minimo_forca_alpha_b_1():
    # Com M1d,A < M1d,min, o alpha_b informado não vale: 15.8.2 d) manda 1,0
    r = P.Mdtot_curvatura_aprox(M1d_A_kncm=500.0, alpha_b_val=0.4, **BASE)
    assert r["alpha_b_ef"] == 1.0
    assert r["Md_tot_kncm"] == pytest.approx(5319.19, abs=0.05)


def test_PIL01_M1dA_acima_do_minimo_nao_muda():
    # M1d,A > M1d,min: usa o próprio M1d,A e o alpha_b informado
    r = P.Mdtot_curvatura_aprox(M1d_A_kncm=5000.0, alpha_b_val=0.8, **BASE)
    esperado = max(0.8 * 5000.0 + r["M2d_kncm"], 5000.0)
    assert r["Md_tot_kncm"] == pytest.approx(esperado)
    assert r["alpha_b_ef"] == 0.8


def test_PIL02_rigidez_com_minimo():
    # 15.8.3.3.3 (p. 130), formulação direta com M1d,A = M1d,min: 4460,81 kN.cm
    r = P.Mdtot_rigidez_aprox(M1d_A_kncm=0.0, alpha_b_val=1.0, **BASE)
    assert r["Md_tot_kncm"] == pytest.approx(4460.81, abs=0.05)


def test_PIL02_rigidez_piso_em_M1dA():
    # Md,tot >= M1d,A
    r = P.Mdtot_rigidez_aprox(M1d_A_kncm=20000.0, alpha_b_val=0.4, **BASE)
    assert r["Md_tot_kncm"] >= 20000.0


def test_PIL03_alpha_b_momentos_menores_que_minimo():
    # 15.8.2 d) (p. 128): MA = 500, MB = 200 < M1d,min = 2940 -> alpha_b = 1,0
    assert P.alpha_b(500.0, 200.0, M1d_min_kncm=2940.0) == 1.0
    # Sem informar o mínimo, vale a expressão a): 0,6 + 0,4·200/500 = 0,76
    assert P.alpha_b(500.0, 200.0) == pytest.approx(0.76)


def test_PIL03_alpha_b_MA_e_o_maior_em_modulo():
    # MA é o momento de maior valor absoluto (15.8.2 a)
    assert P.alpha_b(50.0, 100.0) == pytest.approx(P.alpha_b(100.0, 50.0))


@pytest.mark.parametrize("funcao", [P.Mdtot_curvatura_aprox, P.Mdtot_rigidez_aprox])
def test_PIL04_lambda_acima_de_90_recusado(funcao):
    # le = 600, h = 20 -> λ = 103,8 > 90 (15.8.3.3.2 e 15.8.3.3.3)
    with pytest.raises(nbr.FaixaNormativaError):
        funcao(Nd_kn=1400.0, le_cm=600.0, h_cm=20.0, fck_mpa=30.0,
               M1d_A_kncm=2940.0, Ac_cm2=1000.0)


def test_PIL04_lambda_90_aceito():
    le_90 = 90.0 * 20.0 / 3.46
    r = P.Mdtot_curvatura_aprox(Nd_kn=1400.0, le_cm=le_90, h_cm=20.0, fck_mpa=30.0,
                                M1d_A_kncm=2940.0, Ac_cm2=1000.0)
    assert r["lambda"] == pytest.approx(90.0)


def test_nu_usa_fcd_do_nucleo_e_valida_fck():
    assert P.nu_adimensional(1400.0, 1000.0, 70.0) == pytest.approx(1400.0 / (1000.0 * 70.0 / 1.4 / 10))
    with pytest.raises(nbr.FaixaNormativaError):
        P.nu_adimensional(1400.0, 1000.0, 95.0)
