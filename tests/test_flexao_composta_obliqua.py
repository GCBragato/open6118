"""Testes do kernel FCO (NBR 6118:2023).

Inclui cross-check com PFOC (Cardoso Jr. / Grossmann): seção 40.3 x 71.5,
Nd=1150 kN, Mdx=23000 kN.cm, Mdy=8625 kN.cm -> razao=1.2918, alpha=-53.4°,
x_LN=36.91 cm.
"""

from __future__ import annotations

import math

import numpy as np

import pytest

from dimensionamento.rotinas.flexao_composta_obliqua import (
    Aco,
    AvisoNBR6118,
    Cabo,
    Concreto,
    CurvaApBilinear,
    ei_secante,
    CurvaCParabolaRetangulo,
    CurvaCParabolaRetanguloComTracao,
    Nd_max_kn,
    Parte,
    Secao,
    SecaoRetangular,
    _polygon_area,
    armadura_perimetral_retangular,
    dimensionar_as_fco,
    envoltoria_resistencia,
    esforcos_resistentes_pol,
    exporta_envoltoria_csv,
    main as fco_main,
    momento_resistente_fco_pol,
    solver_els,
    verificar_fco,
    verificar_fco_pol,
    verificar_fco_simplificado,
)


def _aprox(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def test_concreto_propriedades_fck20() -> None:
    c = Concreto(fck_mpa=20.0)
    assert _aprox(c.fcd_kncm2, 1.4286, 1e-3)
    assert _aprox(c.eps_c2_pmilh, 2.0, 1e-6)
    assert _aprox(c.eps_cu_pmilh, 3.5, 1e-6)
    assert _aprox(c.n_parabola, 2.0, 1e-6)


def test_concreto_propriedades_fck60() -> None:
    c = Concreto(fck_mpa=60.0)
    # NBR Anexo: eps_c2 = 2.0 + 0.085*10^0.53 = 2.288,
    #            eps_cu = 2.6 + 35*0.0081 = 2.884,
    #            n      = 1.4 + 23.4*0.0081 = 1.589.
    assert _aprox(c.eps_c2_pmilh, 2.288, 0.01)
    assert _aprox(c.eps_cu_pmilh, 2.884, 0.01)
    assert _aprox(c.n_parabola, 1.589, 0.01)


def test_armadura_perimetral_layout() -> None:
    barras = armadura_perimetral_retangular(
        base_cm=40.3, altura_cm=71.5, cobrimento_cm=2.5,
        nx=3, ny=3, fi_l_mm=10.0, fi_t_mm=5.0,
        area_por_barra_cm2=11.5 / 8,
    )
    assert len(barras) == 8
    # d_linha = 2.5 + (5 + 5)/10 = 3.5
    # extremos: x = +/-(40.3/2 - 3.5) = +/-16.65
    #           y = +/-(71.5/2 - 3.5) = +/-32.25
    xs = sorted({round(b.x_cm, 3) for b in barras})
    ys = sorted({round(b.y_cm, 3) for b in barras})
    assert _aprox(xs[0], -16.65, 0.01)
    assert _aprox(xs[-1], +16.65, 0.01)
    assert _aprox(ys[0], -32.25, 0.01)
    assert _aprox(ys[-1], +32.25, 0.01)


def test_pre_flight_compressao_pura() -> None:
    barras = armadura_perimetral_retangular(40, 60, 2.5, 3, 3, 10.0, 5.0, 1.0)
    s = SecaoRetangular(40, 60, 2.5, barras)
    c = Concreto(fck_mpa=25.0)
    a = Aco()
    Nmax = Nd_max_kn(s, c, a)
    # Nmax ~ 0.85*1.786*40*60 + 43.48*8 ~ 3991 kN
    assert 3500 < Nmax < 4200
    r = verificar_fco(s, c, a, Nd_kn=Nmax * 1.5, Mxd_kncm=1000, Myd_kncm=1000)
    assert r["status"] == "FORA_RANGE"


def test_uniaxial_simetria() -> None:
    """Uniaxial Mx (Myd=0): solver deve usar fallback (alpha=0)."""
    barras = armadura_perimetral_retangular(30, 60, 2.5, 3, 3, 16.0, 5.0)
    s = SecaoRetangular(30, 60, 2.5, barras)
    c = Concreto(fck_mpa=25.0)
    a = Aco()
    r = verificar_fco(s, c, a, Nd_kn=500, Mxd_kncm=15000, Myd_kncm=0)
    assert r.get("uniaxial", False)
    assert r["alpha_rad"] == 0.0
    assert r["razao"] > 0


def test_simetria_quadrada_45graus() -> None:
    """Quadrada com armadura simetrica e Mxd=Myd: alpha deve ~ 45 graus."""
    barras = armadura_perimetral_retangular(40, 40, 2.5, 4, 4, 16.0, 5.0)
    s = SecaoRetangular(40, 40, 2.5, barras)
    c = Concreto(fck_mpa=25.0)
    a = Aco()
    r = verificar_fco(s, c, a, Nd_kn=1000, Mxd_kncm=8000, Myd_kncm=8000, n_grid=60)
    assert r["status"] != "FORA_RANGE"
    assert _aprox(abs(r["alpha_graus"]), 45.0, 5.0)
    rel = abs(r["MRx_kncm"] - r["MRy_kncm"]) / max(r["MRx_kncm"], r["MRy_kncm"])
    assert rel < 0.05


def test_pfoc_referencia() -> None:
    """Cross-check com PFOC __main__: 40.3 x 71.5, Nd=1150 kN.

    PCalc/PFOC adota Mdx_PFOC = N*ed_x e Mdy_PFOC = N*ed_y onde ed_x, ed_y
    sao excentricidades nas direcoes x, y. Logo, em notacao classica:
        Myd (em torno de y) = N * ed_x = 8625 kN.cm
        Mxd (em torno de x) = N * ed_y = 23000 kN.cm

    PFOC referencia: razao = 1.2918, alpha = -53.39 graus, x_LN = 36.91 cm.
    """
    barras = armadura_perimetral_retangular(
        base_cm=40.3, altura_cm=71.5, cobrimento_cm=2.5,
        nx=3, ny=3, fi_l_mm=10.0, fi_t_mm=5.0,
        area_por_barra_cm2=11.5 / 8,
    )
    s = SecaoRetangular(40.3, 71.5, 2.5, barras)
    c = Concreto(fck_mpa=20.0)
    a = Aco()
    Nd = 1150.0
    r = verificar_fco(
        s, c, a, Nd_kn=Nd, Mxd_kncm=Nd * 20.0, Myd_kncm=Nd * 7.5,
        n_grid=80,
    )
    assert r["status"] in ("OK", "NAO_VERIFICA")
    assert _aprox(r["razao"], 1.2918, 0.04)
    assert _aprox(abs(r["alpha_graus"]), 53.39, 2.0)
    assert _aprox(r["x_LN_cm"], 36.91, 1.5)


def test_nbr_17_79_conservadora() -> None:
    """Eq. NBR 17.79: expoente=1.5 deve dar valor menor que expoente=1.0.

    A 17.2.5 da NBR 6118:2026 só prevê α = 1 e α = 1,2 (seção retangular):
    com 1,5 a função calcula, mas avisa (FCO-12).
    """
    razao = verificar_fco_simplificado(
        MRxd_kncm=20000, MRyd_kncm=40000,
        Mxd_kncm=10000, Myd_kncm=20000, expoente=1.0,
    )
    assert _aprox(razao, 1.0, 1e-6)
    with pytest.warns(AvisoNBR6118):
        razao_2 = verificar_fco_simplificado(
            MRxd_kncm=20000, MRyd_kncm=40000,
            Mxd_kncm=10000, Myd_kncm=20000, expoente=1.5,
        )
    assert razao_2 < razao


def test_dimensionar_as_fco() -> None:
    """Dimensionamento por bissecao em As: deve achar As tal que razao~1.0."""
    c = Concreto(fck_mpa=25.0)
    a = Aco()
    r = dimensionar_as_fco(
        base_cm=30.0, altura_cm=60.0, cobrimento_cm=2.5,
        nx=3, ny=3, fi_l_mm=16.0,
        concreto=c, aco=a,
        Nd_kn=600.0, Mxd_kncm=10000.0, Myd_kncm=20000.0,
        n_grid=50,
    )
    assert r["status"] == "OK"
    assert 0.95 < r["razao"] < 1.05
    assert r["As_total_cm2"] > 1.0


def test_curva_parabola_retangulo_isolada() -> None:
    """CurvaCParabolaRetangulo: tracao -> 0; eps=eps_c2 -> alpha_c*fcd."""
    curva = CurvaCParabolaRetangulo(
        fcd_kncm2=1.4286, eps_c2_pmilh=2.0, eps_cu_pmilh=3.5, n_parabola=2.0,
    )
    eps = np.array([-1.0, 0.0, 1.0, 2.0, 3.0, 5.0])
    sig = curva.sigma(eps)
    assert sig[0] == 0.0  # tracao -> 0
    assert sig[1] == 0.0  # eps=0
    assert _aprox(sig[3], 0.85 * 1.4286, 1e-6)  # eps=eps_c2 -> patamar
    assert _aprox(sig[4], 0.85 * 1.4286, 1e-6)  # patamar
    assert _aprox(sig[5], 0.85 * 1.4286, 1e-6)  # alem de eps_cu, mantem


def test_curva_com_tracao_simetria() -> None:
    """CurvaCParabolaRetanguloComTracao: ramo de tracao retorna sigma < 0."""
    curva = CurvaCParabolaRetanguloComTracao(
        fcd_kncm2=1.4286,
        eps_c2_pmilh=2.0,
        eps_cu_pmilh=3.5,
        n_parabola=2.0,
        fctk_kncm2=0.214,    # ~0.7 * 0.3 * 25^(2/3) / 10
        Eci_kncm2=2800.0,    # ~5600 * sqrt(25) / 100
    )
    eps_ct2 = 0.9 * 0.214 / 2800.0 * 1000.0  # ~0.0688 ‰
    eps = np.array([-eps_ct2 / 2, 0.0, 1.0])
    sig = curva.sigma(eps)
    assert sig[0] < 0  # tracao
    assert sig[1] == 0
    assert sig[2] > 0  # compressao
    # Verifica que no ramo linear: sigma = Eci * eps / 1000
    assert _aprox(sig[0], 2800.0 * (-eps_ct2 / 2) / 1000.0, 1e-6)


def test_solver_els_compressao_simples() -> None:
    """ELS sob (Nsd, 0, 0): kx=ky=0; eps_cg uniforme positivo."""
    barras = armadura_perimetral_retangular(40, 40, 2.5, 4, 4, 16.0)
    s = SecaoRetangular(40, 40, 2.5, barras)
    c = Concreto(fck_mpa=25.0)
    a = Aco()
    r = solver_els(s, c, a, Nsd_kn=400.0, Mxd_kncm=0.0, Myd_kncm=0.0, n_grid=40)
    assert r["convergiu"]
    assert _aprox(r["kx_pmilh_cm"], 0.0, 1e-4)
    assert _aprox(r["ky_pmilh_cm"], 0.0, 1e-4)
    assert r["eps_cg_pmilh"] > 0
    assert r["eps_cg_pmilh"] < c.eps_c2_pmilh
    assert r["residuo"] < 1.0


def test_solver_els_uniaxial_kx() -> None:
    """ELS sob (Nsd, Mxd, 0): ky=0; kx>0; deformacoes coerentes."""
    barras = armadura_perimetral_retangular(30, 60, 2.5, 3, 3, 16.0)
    s = SecaoRetangular(30, 60, 2.5, barras)
    c = Concreto(fck_mpa=25.0)
    a = Aco()
    r = solver_els(s, c, a, Nsd_kn=300.0, Mxd_kncm=8000.0, Myd_kncm=0.0, n_grid=40)
    assert r["convergiu"]
    assert _aprox(r["ky_pmilh_cm"], 0.0, 1e-4)
    assert r["kx_pmilh_cm"] > 0  # +y comprimido (Mxd > 0)
    assert r["eps_max_compr_pmilh"] > r["eps_min_pmilh"]
    assert r["residuo"] < 1.0


def test_solver_els_simetria_quadrada() -> None:
    """Quadrada simetrica com Mxd=Myd: kx ~ ky por simetria."""
    barras = armadura_perimetral_retangular(40, 40, 2.5, 4, 4, 16.0)
    s = SecaoRetangular(40, 40, 2.5, barras)
    c = Concreto(fck_mpa=25.0)
    a = Aco()
    r = solver_els(s, c, a, Nsd_kn=300.0, Mxd_kncm=4000.0, Myd_kncm=4000.0, n_grid=40)
    assert r["convergiu"]
    assert _aprox(r["kx_pmilh_cm"], r["ky_pmilh_cm"], 0.05 * abs(r["kx_pmilh_cm"]) + 1e-4)
    assert r["residuo"] < 1.0


def test_polygon_area_helpers() -> None:
    """Helper de area: retangulo unitario CCW = 1."""
    poly = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0))
    assert _aprox(_polygon_area(poly), 1.0, 1e-9)
    # Sentido horario: ainda retorna positivo (abs)
    poly_cw = tuple(reversed(poly))
    assert _aprox(_polygon_area(poly_cw), 1.0, 1e-9)


def test_secao_retangular_via_factory_equivale_legacy() -> None:
    """Secao.retangular(...) deve dar resultado proximo ao SecaoRetangular legacy."""
    barras = armadura_perimetral_retangular(40, 60, 2.5, 3, 3, 16.0)
    c = Concreto(fck_mpa=25.0)
    a = Aco()
    s_legacy = SecaoRetangular(40, 60, 2.5, barras)
    s_pol = Secao.retangular(40, 60, c, barras=barras, n_dy=40, n_dx=20)

    Nd, Mxd, Myd = 800.0, 12000.0, 8000.0
    r1 = verificar_fco(s_legacy, c, a, Nd, Mxd, Myd, n_grid=60)
    r2 = verificar_fco_pol(s_pol, a, Nd, Mxd, Myd)
    assert r1["status"] != "FORA_RANGE"
    assert r2["status"] != "FORA_RANGE"
    # Resultados devem ser proximos (discretizacoes diferentes):
    assert _aprox(r1["razao"], r2["razao"], 0.05)
    assert _aprox(abs(r1["alpha_graus"]), abs(r2["alpha_graus"]), 5.0)


def test_secao_L_poligonal() -> None:
    """Secao em L (40x40 com canto de 20x20 vazio): pode-se verificar a FCO."""
    # L: poligono CCW com 6 vertices
    poly_L = (
        (-20.0, -20.0),
        (20.0, -20.0),
        (20.0, 0.0),
        (0.0, 0.0),
        (0.0, 20.0),
        (-20.0, 20.0),
        (-20.0, -20.0),
    )
    c = Concreto(fck_mpa=25.0)
    # Algumas barras nos cantos da L (longe do canto reentrante)
    barras = (
        # Inferior
        type("B", (), {"x_cm": -16.0, "y_cm": -16.0, "area_cm2": 2.0})(),
        type("B", (), {"x_cm": 16.0, "y_cm": -16.0, "area_cm2": 2.0})(),
        # Superior
        type("B", (), {"x_cm": -16.0, "y_cm": 16.0, "area_cm2": 2.0})(),
        # Canto direito da parte inferior
        type("B", (), {"x_cm": 16.0, "y_cm": -4.0, "area_cm2": 2.0})(),
    )
    s = Secao(
        partes=(Parte(polygon=poly_L, concreto=c),),
        barras=barras,
        n_dy=30,
        n_dx=12,
    )
    a = Aco()
    # Area: 40x40 - 20x20 = 1600 - 400 = 1200 cm2
    assert _aprox(_polygon_area(poly_L), 1200.0, 1e-6)
    r = verificar_fco_pol(s, a, Nd_kn=300.0, Mxd_kncm=3000.0, Myd_kncm=3000.0)
    assert r["status"] != "FORA_RANGE"
    assert r["razao"] > 0


def test_momento_resistente_fco_pol_simetrico() -> None:
    """Para retangulo via Secao, momento_resistente_fco_pol em theta=45 graus
    deve dar MRx ~ MRy (se quase quadrada)."""
    barras = armadura_perimetral_retangular(40, 40, 2.5, 4, 4, 16.0)
    c = Concreto(fck_mpa=25.0)
    s = Secao.retangular(40, 40, c, barras=barras, n_dy=40, n_dx=20)
    a = Aco()
    r = momento_resistente_fco_pol(s, a, Nd_kn=500.0, theta_d_rad=math.pi / 4.0)
    rel = abs(r["MRx_kncm"] - r["MRy_kncm"]) / max(r["MRx_kncm"], r["MRy_kncm"])
    assert rel < 0.05


def test_ei_secante_retangular() -> None:
    """EI secante deve ser positivo e finito, ordem de magnitude razoavel.

    Nota: a parabola-retangulo NBR tem tangente inicial em eps=0 dada por
    alpha_c*fcd*n/eps_c2, que e ~4-5x Eci. Logo EI secante em ELS estagio I
    fica naturalmente acima do EI bruto Eci*Ic. Para EI mais proximo do
    bruto, use uma curva constitutiva linear (CurvaCParabolaRetangulo nao
    representa Estagio I real -- e curva ELU).
    """
    barras = armadura_perimetral_retangular(30, 60, 2.5, 3, 3, 16.0)
    s = SecaoRetangular(30, 60, 2.5, barras)
    c = Concreto(fck_mpa=25.0)
    a = Aco()
    EI = ei_secante(s, c, a, Nsd_kn=400.0, Md_kncm=8000.0, eixo="x", n_grid=50)
    assert EI > 0
    assert math.isfinite(EI)
    # Ordem de magnitude: 1e7 a 1e10 kN.cm^2 para essa secao
    assert 1e7 < EI < 1e10


def test_ei_secante_diminui_com_momento() -> None:
    """EI secante diminui (ou estabiliza) conforme Md aumenta (escoamento).

    NBR 6118:2026, 15.3.1 e Figura 15.1 (FCO-10): a (EI)sec da reta AB é
    definida no ponto B (M = MRd/γf3) e não depende do momento atuante; o
    que diminui com o momento é a secante da curva AB (pico 1,10 fcd e
    N/γf3), a curva usada no cálculo das deformações -- `ponto="Md"`.
    Antes o teste afirmava a queda na curva de ELU, o que a norma não usa.
    """
    barras = armadura_perimetral_retangular(30, 60, 2.5, 3, 3, 16.0)
    s = SecaoRetangular(30, 60, 2.5, barras)
    c = Concreto(fck_mpa=25.0)
    a = Aco()
    EI_baixo = ei_secante(s, c, a, Nsd_kn=400.0, Md_kncm=2000.0, eixo="x", n_grid=40, ponto="Md")
    EI_alto = ei_secante(s, c, a, Nsd_kn=400.0, Md_kncm=10000.0, eixo="x", n_grid=40, ponto="Md")
    assert EI_alto < EI_baixo
    EI_B_1 = ei_secante(s, c, a, Nsd_kn=400.0, Md_kncm=2000.0, eixo="x", n_grid=40)
    EI_B_2 = ei_secante(s, c, a, Nsd_kn=400.0, Md_kncm=10000.0, eixo="x", n_grid=40)
    assert abs(EI_B_1 / EI_B_2 - 1.0) < 1e-9


def test_curva_ap_bilinear() -> None:
    """CurvaApBilinear, padrao (ramo_inclinado=True): reta ate eps_pyd, depois
    segundo trecho ainda ascendente ate fptd em eps_pu (Figura 8.6, 8.4.5,
    PDF p. 50 -- decisao 2 de 19/09/2026, pacote P3). Antes deste pacote o
    padrao era o patamar horizontal; ver test_curva_ap_bilinear_patamar para
    o comportamento antigo, preservado com ramo_inclinado=False."""
    curva = CurvaApBilinear()
    eps_pyd = curva.eps_pyd_pmilh
    fpyd = curva.fpyd_kncm2
    fptd = curva.fptd_kncm2
    eps_pu = curva.eps_pu_pmilh
    eps = np.array([0.0, eps_pyd / 2, eps_pyd, eps_pyd * 2, eps_pu, -eps_pu])
    sig = curva.sigma(eps)
    assert sig[0] == 0.0
    assert _aprox(sig[1], curva.Ep_kncm2 * (eps_pyd / 2) / 1000.0, 1e-6)
    assert _aprox(sig[2], fpyd, 1e-6)
    # ponto interior do segundo trecho: reta de (eps_pyd, fpyd) a (eps_pu, fptd)
    esperado_interior = fpyd + (fptd - fpyd) * (eps_pyd * 2 - eps_pyd) / (eps_pu - eps_pyd)
    assert _aprox(sig[3], esperado_interior, 1e-6)
    assert esperado_interior > fpyd  # segundo trecho ainda ascendente, nao patamar
    assert _aprox(sig[4], fptd, 1e-6)  # extremo eps_pu -> fptd
    assert _aprox(sig[5], -fptd, 1e-6)  # simetrico em tracao


def test_curva_ap_bilinear_patamar() -> None:
    """CurvaApBilinear(ramo_inclinado=False): reproduz o patamar horizontal
    que era o comportamento padrao antes do pacote P3 (achado FCO-17 da
    auditoria)."""
    curva = CurvaApBilinear(ramo_inclinado=False)
    eps_pyd = curva.eps_pyd_pmilh
    fpyd = curva.fpyd_kncm2
    eps = np.array([0.0, eps_pyd / 2, eps_pyd, eps_pyd * 2, -eps_pyd * 2])
    sig = curva.sigma(eps)
    assert sig[0] == 0.0
    assert _aprox(sig[1], curva.Ep_kncm2 * (eps_pyd / 2) / 1000.0, 1e-6)
    assert _aprox(sig[2], fpyd, 1e-6)
    assert _aprox(sig[3], fpyd, 1e-6)  # patamar
    assert _aprox(sig[4], -fpyd, 1e-6)  # patamar tracao


def test_cabo_aumenta_capacidade_mxd_positivo() -> None:
    """Cabo na fibra inferior (-y) aumenta MR para Mxd > 0.

    Logica: Mxd > 0 traciona a fibra inferior; cabo pre-tracionado nessa
    fibra contribui adicional para o momento resistente positivo.
    """
    barras = armadura_perimetral_retangular(40, 60, 2.5, 3, 3, 16.0)
    c = Concreto(fck_mpa=25.0)
    a = Aco()
    s_sem = Secao.retangular(40, 60, c, barras=barras)
    cabo = Cabo(x_cm=0.0, y_cm=-25.0, area_cm2=2.0, eps_pre_pmilh=7.0)
    s_com = Secao.retangular(40, 60, c, barras=barras, cabos=(cabo,))
    Nd = 0.0  # sem normal externa para isolar efeito do cabo
    # Verifica que Nr difere (cabo adiciona forca interna)
    Nr_sem, _, _ = esforcos_resistentes_pol(s_sem, a, alpha=0.0, x_LN=20.0)
    Nr_com, _, _ = esforcos_resistentes_pol(s_com, a, alpha=0.0, x_LN=20.0)
    # Cabo tracionado (sigma negativa) reduz Nr (compressao positiva no concreto)
    assert Nr_com < Nr_sem


def test_envoltoria_e_csv(tmp_path) -> None:
    """Envoltoria gera lista de pontos validos; CSV e gerado corretamente."""
    barras = armadura_perimetral_retangular(40, 60, 2.5, 3, 3, 16.0)
    s = SecaoRetangular(40, 60, 2.5, barras)
    c = Concreto(fck_mpa=25.0)
    a = Aco()
    pontos = envoltoria_resistencia(s, c, a, Nd_kn=600.0, n_pontos=8, n_grid=40)
    assert len(pontos) > 0
    for mrx, mry in pontos:
        assert mrx > 0
        assert mry > 0
    csv_path = tmp_path / "envoltoria.csv"
    exporta_envoltoria_csv(pontos, str(csv_path))
    assert csv_path.exists()
    text = csv_path.read_text(encoding="utf-8")
    assert "MRx_kncm,MRy_kncm" in text
    assert len(text.splitlines()) == len(pontos) + 1  # +1 cabecalho


def test_cli_smoke(capsys) -> None:
    """CLI roda end-to-end com argumentos minimos e retorna exit code."""
    rc = fco_main([
        "--base", "40.3", "--altura", "71.5", "--fck", "20",
        "--nx", "3", "--ny", "3", "--fi-l", "10",
        "--area-barra", str(11.5 / 8),
        "--nsd", "1150", "--mxd", "23000", "--myd", "8625",
        "--n-grid", "60",
    ])
    captured = capsys.readouterr()
    # PFOC ref razao=1.29 -> status OK
    assert rc == 0
    assert "razao" in captured.out
    assert "status" in captured.out


@pytest.mark.parametrize(
    "fck_mpa,base,altura,nsd,mxd,myd,esperado_min,esperado_max",
    [
        # C60 (alta resistencia): deve usar formulas n, eps_c2, eps_cu variaveis
        (60.0, 40, 60, 1500, 12000, 8000, 0.5, 5.0),
        # Compressao quase pura (Md baixo): razao alta
        (25.0, 30, 60, 600, 100, 100, 5.0, 200.0),
    ],
    ids=["C60_biaxial", "compr_quase_pura"],
)
def test_casos_parametrizados(
    fck_mpa, base, altura, nsd, mxd, myd, esperado_min, esperado_max,
) -> None:
    """Casos extras alem dos cross-checks PFOC/quadrada/uniaxial."""
    barras = armadura_perimetral_retangular(base, altura, 2.5, 3, 3, 16.0)
    s = SecaoRetangular(base, altura, 2.5, barras)
    c = Concreto(fck_mpa=fck_mpa)
    a = Aco()
    r = verificar_fco(s, c, a, Nd_kn=nsd, Mxd_kncm=mxd, Myd_kncm=myd, n_grid=60)
    assert r["status"] != "FORA_RANGE", f"r={r}"
    assert r["status"] != "NAO_CONVERGIU", f"r={r}"
    assert esperado_min <= r["razao"] <= esperado_max, (
        f"razao={r['razao']:.3f} fora de [{esperado_min}, {esperado_max}]"
    )


def test_concreto_com_curva_custom_muda_resultado() -> None:
    """Plugar curva com tracao deve aumentar (levemente) MR."""
    curva = CurvaCParabolaRetanguloComTracao(
        fcd_kncm2=1.4286,
        eps_c2_pmilh=2.0,
        eps_cu_pmilh=3.5,
        n_parabola=2.0,
        fctk_kncm2=0.214,
        Eci_kncm2=2800.0,
    )
    barras = armadura_perimetral_retangular(40, 60, 2.5, 3, 3, 16.0)
    s = SecaoRetangular(40, 60, 2.5, barras)
    a = Aco()
    c_default = Concreto(fck_mpa=20.0)
    c_com_tracao = Concreto(fck_mpa=20.0, curva=curva)
    r1 = verificar_fco(s, c_default, a, Nd_kn=500, Mxd_kncm=15000, Myd_kncm=0, n_grid=60)
    r2 = verificar_fco(s, c_com_tracao, a, Nd_kn=500, Mxd_kncm=15000, Myd_kncm=0, n_grid=60)
    # Razao com tracao deve ser >= razao sem tracao (concreto contribui na tracao)
    assert r2["razao"] >= r1["razao"] - 1e-3
