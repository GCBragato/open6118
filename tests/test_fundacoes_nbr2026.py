"""Fundacoes (sapatas_nbr6118.py + blocos_nbr6118.py) contra a NBR 6118:2026 --
achados FUN-01 a FUN-04 (ver AUDITORIA_NBR6118_2026.md).

Valores esperados vem das reproducoes verificadas na auditoria de
18/09/2026 (achados_brutos.md / verificacao_resultados.md) e da propria
norma (paginas do PDF).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr  # noqa: E402
import sapatas_nbr6118 as SAP  # noqa: E402
import blocos_nbr6118 as BLO  # noqa: E402


def _aprox(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# FUN-01 -- blocos: Blevot mantido como criterio; 22.3.2 como informacao
# (decisao 2 do plano de correcao -- nao e defeito, e escolha documentada)
# ---------------------------------------------------------------------------
def test_FUN01_docstrings_nao_atribuem_blevot_a_nbr():
    """As docstrings dos limites de Blevot precisam deixar claro que os
    coeficientes 1,4/1,75/2,1/2,6 nao vem da NBR."""
    for fn in (BLO.sigma_lim_2_estacas, BLO.sigma_lim_3_estacas,
               BLO.sigma_lim_4_estacas, BLO.sigma_lim_5_estacas_pil,
               BLO.sigma_lim_5_estacas_est):
        doc = (fn.__doc__ or "").lower()
        assert "blevot" in doc
        assert "nao" in doc


def test_FUN01_alpha_v2():
    # 17.4.2.2 / 19.5.3.1 / 22.3.2 (todas com a mesma expressao)
    assert BLO.alpha_v2(25.0) == pytest.approx(0.9)
    assert BLO.alpha_v2(90.0) == pytest.approx(0.64)


def test_FUN01_fcd1_fcd3_22_3_2():
    # 22.3.2 (PDF p. 204): fcd1 = 0,85*av2*fcd (no CCC); fcd3 = 0,72*av2*fcd (no CCT)
    # C25: fcd = 25/1,4 = 17,857 MPa; av2 = 0,9
    fcd1_mpa = BLO.fcd1_no_pilar_kncm2(25.0) * 10.0
    fcd3_mpa = BLO.fcd3_na_estaca_kncm2(25.0) * 10.0
    assert fcd1_mpa == pytest.approx(0.85 * 0.9 * 25.0 / 1.4, rel=1e-9)   # 13,66 MPa
    assert fcd3_mpa == pytest.approx(0.72 * 0.9 * 25.0 / 1.4, rel=1e-9)   # 11,57 MPa


def test_FUN01_projetar_bloco_traz_22_3_2_sem_mudar_criterio_blevot():
    """Repro do achado: 2 estacas, Nk=657,4, e=80, pilar 30x20, phi_e=30,
    h=50, C25, KR=0,95 -> sigma_pil = 24,67 MPa, fcd1 = 13,66 MPa,
    razao = 1,81 (viola a 22.3.2 no no do pilar). ok_bielas continua
    sendo o criterio de Blevot (sigma_pil/est <= sigma_lim), inalterado
    pela informacao nova."""
    r = BLO.projetar_bloco(
        n_estacas=2, Nk_kn=657.4, e_cm=80.0, ap_cm=30.0, bp_cm=20.0,
        phi_e_cm=30.0, h_cm=50.0, fck_mpa=25.0, KR=0.95, cobrimento_cm=3.0,
    )
    assert r.sigma_pil_kncm2 * 10.0 == pytest.approx(24.67, abs=0.1)
    assert r.fcd1_kncm2 * 10.0 == pytest.approx(13.66, abs=0.05)
    assert r.razao_pil_fcd1 == pytest.approx(1.81, abs=0.02)
    assert r.ok_bielas_22_3_2 is False   # 22.3.2 sozinha reprovaria o no do pilar
    # ok_bielas (Blevot) continua sendo exatamente a comparacao original:
    assert r.ok_bielas == (r.sigma_pil_kncm2 <= r.sigma_lim_kncm2
                           and r.sigma_est_kncm2 <= r.sigma_lim_kncm2)


# ---------------------------------------------------------------------------
# FUN-02 -- sapatas: As,minimo (decisao 2: 0,67*rho_min = "laje" e o padrao)
# ---------------------------------------------------------------------------
def test_FUN02_as_min_flexao_sapata_criterios():
    # C25: rho_min = 0,15% (Tabela 17.3). Largura perp = 265 cm, h=70 cm.
    laje = SAP.as_min_flexao_sapata(265.0, 70.0, 25.0, "laje")
    cheio = SAP.as_min_flexao_sapata(265.0, 70.0, 25.0, "rho_min")
    nenhum = SAP.as_min_flexao_sapata(265.0, 70.0, 25.0, "nenhum")
    assert laje == pytest.approx(18.64, abs=0.02)
    assert cheio == pytest.approx(27.83, abs=0.02)
    assert nenhum == 0.0
    with pytest.raises(ValueError):
        SAP.as_min_flexao_sapata(265.0, 70.0, 25.0, "outro")


def test_FUN02_projetar_sapata_centrada_eleva_As_B_ao_minimo():
    """Repro do achado: exemplo 1 da apostila (Nk=1250, pilar 80x20,
    265x205, h=70, C25). Sem minimo, As_B = 16,21 cm2 (13% abaixo do
    minimo). Com o criterio padrao ("laje"), sobe para 18,64 cm2; As_A
    (15,01) ja estava acima do proprio minimo (14,42) e nao muda."""
    r = SAP.projetar_sapata_centrada(
        Nk_kn=1250.0, ap_cm=80.0, bp_cm=20.0, Padm_kncm2=0.026,
        h_cm=70.0, fck_mpa=25.0, A_cm=265.0, B_cm=205.0,
    )
    assert r.criterio_as_min == "laje"
    assert r.As_B_min_cm2 == pytest.approx(18.64, abs=0.02)
    assert r.As_B_cm2 == pytest.approx(18.64, abs=0.02)
    assert r.As_A_min_cm2 == pytest.approx(14.42, abs=0.02)
    assert r.As_A_cm2 == pytest.approx(15.01, abs=0.05)   # acima do minimo, nao muda


def test_FUN02_criterio_rho_min_cheio():
    r = SAP.projetar_sapata_centrada(
        Nk_kn=1250.0, ap_cm=80.0, bp_cm=20.0, Padm_kncm2=0.026,
        h_cm=70.0, fck_mpa=25.0, A_cm=265.0, B_cm=205.0,
        criterio_as_min="rho_min",
    )
    assert r.As_B_cm2 == pytest.approx(27.83, abs=0.05)


def test_FUN02_criterio_nenhum_preserva_valor_da_Eq_1_28():
    r = SAP.projetar_sapata_centrada(
        Nk_kn=1250.0, ap_cm=80.0, bp_cm=20.0, Padm_kncm2=0.026,
        h_cm=70.0, fck_mpa=25.0, A_cm=265.0, B_cm=205.0,
        criterio_as_min="nenhum",
    )
    assert r.As_B_cm2 == pytest.approx(16.20, abs=0.05)


def test_FUN02_projetar_sapata_corrida_aplica_minimo():
    r = SAP.projetar_sapata_corrida(
        Nk_por_metro_kn=1000.0, ap_cm=20.0, Padm_kncm2=0.025,
        h_cm=80.0, fck_mpa=25.0,
    )
    assert r["As_min_cm2_por_m"] == pytest.approx(
        0.67 * nbr.rho_min_flexao(25.0) * 100.0 * 80.0
    )
    assert r["As_cm2_por_m"] >= r["As_min_cm2_por_m"]


@pytest.mark.parametrize("fck", [20.0, 40.0, 45.0, 50.0, 55.0, 70.0, 90.0])
def test_FUN02_as_min_varredura_fck(fck):
    """rho_min cresce com fck (Tabela 17.3, Grupo II incluso -- decisao 1).
    A funcao nao pode falhar em nenhuma classe de C20 a C90."""
    As_min = SAP.as_min_flexao_sapata(200.0, 60.0, fck, "laje")
    assert As_min > 0.0
    assert As_min == pytest.approx(0.67 * nbr.rho_min_flexao(fck) * 200.0 * 60.0)


# ---------------------------------------------------------------------------
# FUN-03 -- sapatas: fct,m/tau_Rd do nucleo (ramo fck > 50, teto de 60 MPa)
# ---------------------------------------------------------------------------
def test_FUN03_fctm_c70_usa_ramo_acima_de_50():
    # Repro do achado: fctm sem o ramo >50 dava 5,10 MPa; correto: 4,61 MPa (-10,5%)
    fctm_velho_grupo_I = 0.3 * 70.0 ** (2.0 / 3.0)
    assert fctm_velho_grupo_I == pytest.approx(5.10, abs=0.01)
    assert nbr.fct_m(70.0) == pytest.approx(4.6105, abs=0.001)


def test_FUN03_cortante_usa_tau_Rd_do_nucleo():
    """cortante_sapata_flexivel deve usar nbr.tau_Rd (que ja aplica o
    ramo de fct,m acima de 50 MPa e o teto de 60 MPa), nao mais o fctm
    do Grupo I embutido localmente."""
    for fck in (30.0, 70.0, 90.0):
        r = SAP.cortante_sapata_flexivel(
            pd_kncm2=0.05, A_cm=250.0, B_cm=250.0, ap_cm=30.0, bp_cm=30.0,
            d_cm=35.0, fck_mpa=fck,
        )
        tau_rd_esperado = nbr.mpa_para_kncm2(nbr.tau_Rd(fck))
        k = max(1.0, 1.6 - 35.0 / 100.0)
        VRd1_A_esperado = tau_rd_esperado * k * 1.2 * 35.0 * 250.0
        assert r["VRd1_A_kN"] == pytest.approx(VRd1_A_esperado, rel=1e-9)


def test_FUN03_tau_Rd_teto_60_mpa():
    """19.4.1 (p. 181): tau_Rd e limitado ao correspondente a fck = 60 MPa.
    C90 nao pode dar um VRd1 maior que o de C60."""
    r_c60 = SAP.cortante_sapata_flexivel(
        pd_kncm2=0.05, A_cm=250.0, B_cm=250.0, ap_cm=30.0, bp_cm=30.0,
        d_cm=35.0, fck_mpa=60.0,
    )
    r_c90 = SAP.cortante_sapata_flexivel(
        pd_kncm2=0.05, A_cm=250.0, B_cm=250.0, ap_cm=30.0, bp_cm=30.0,
        d_cm=35.0, fck_mpa=90.0,
    )
    assert r_c90["VRd1_A_kN"] == pytest.approx(r_c60["VRd1_A_kN"], rel=1e-9)


@pytest.mark.parametrize("fck", [20.0, 40.0, 45.0, 50.0, 55.0, 70.0, 90.0])
def test_FUN03_varredura_fck_nao_falha(fck):
    r = SAP.cortante_sapata_flexivel(
        pd_kncm2=0.05, A_cm=250.0, B_cm=250.0, ap_cm=30.0, bp_cm=30.0,
        d_cm=35.0, fck_mpa=fck,
    )
    assert r["VRd1_A_kN"] > 0.0


# ---------------------------------------------------------------------------
# FUN-04 -- sapatas: secao critica a d (padrao NBR); d/2 = CEB-70 explicito
# ---------------------------------------------------------------------------
def test_FUN04_secao_critica_padrao_e_a_d():
    """Repro do achado: pd=0,05, sapata 250x250, pilar 30x30, d=35. O
    padrao NBR 19.4.1 (secao a d da face) da VSd_A = 937,50 kN; o
    comportamento antigo (d/2, CEB-70) dava 1156,25 kN (+23%, a favor da
    seguranca, mas indevidamente atribuido ao 19.4.1)."""
    r = SAP.cortante_sapata_flexivel(
        pd_kncm2=0.05, A_cm=250.0, B_cm=250.0, ap_cm=30.0, bp_cm=30.0,
        d_cm=35.0, fck_mpa=25.0,
    )
    assert r["secao_critica"] == "d"
    assert r["VSd_A_kN"] == pytest.approx(937.50, abs=0.5)


def test_FUN04_secao_critica_d_meio_rotulada_ceb70():
    r = SAP.cortante_sapata_flexivel(
        pd_kncm2=0.05, A_cm=250.0, B_cm=250.0, ap_cm=30.0, bp_cm=30.0,
        d_cm=35.0, fck_mpa=25.0, secao_critica="d/2",
    )
    assert r["VSd_A_kN"] == pytest.approx(1156.25, abs=0.5)
    assert "CEB-70" in (SAP.cortante_sapata_flexivel.__doc__ or "")


def test_FUN04_secao_critica_invalida_levanta():
    with pytest.raises(ValueError):
        SAP.cortante_sapata_flexivel(
            pd_kncm2=0.05, A_cm=250.0, B_cm=250.0, ap_cm=30.0, bp_cm=30.0,
            d_cm=35.0, fck_mpa=25.0, secao_critica="d/3",
        )
