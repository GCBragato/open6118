"""Testes de regressão - cortante_nbr6118.py e torcao_nbr6118.py contra a
ABNT NBR 6118:2026 (achados CRT-01 a CRT-08 da auditoria de 18/09/2026).

Os valores esperados vêm da reprodução numérica de cada achado em
SCRATCH/achados_brutos.md, com os ajustes de SCRATCH/verificacao_resultados.md
(CRT-03: número corrigido pela verificação; CRT-08: achado da consolidação).
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dimensionamento"))

import nucleo_nbr6118 as nbr   # noqa: E402
import cortante_nbr6118 as crt  # noqa: E402
import torcao_nbr6118 as trc    # noqa: E402


FCKS_GRUPO_I_E_II = [45.0, 50.0, 55.0, 70.0, 90.0]   # faixa pedida no briefing


# ---------------------------------------------------------------------------
# CRT-01 - fct,m / fctd / fcd / fywd do cortante passam a vir do núcleo
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fck", FCKS_GRUPO_I_E_II)
def test_crt01_fctm_cortante_delega_nucleo(fck):
    assert crt.fctm_mpa(fck) == pytest.approx(nbr.fct_m(fck), rel=1e-12)


@pytest.mark.parametrize("fck", FCKS_GRUPO_I_E_II)
def test_crt01_fctd_e_fcd_cortante_delegam_nucleo(fck):
    assert crt.fctd_kncm2(fck) == pytest.approx(
        nbr.mpa_para_kncm2(nbr.fctd(fck)), rel=1e-12)
    assert crt.fcd_kncm2(fck) == pytest.approx(
        nbr.mpa_para_kncm2(nbr.fcd(fck)), rel=1e-12)


def test_crt01_fywd_cortante_delega_nucleo():
    assert crt.fywd_kncm2(500.0) == pytest.approx(
        nbr.mpa_para_kncm2(min(nbr.fyd(500.0), 435.0)), rel=1e-12)
    # barra dobrada (estribo=False): 0.7*fyd, mesmo teto de 435 MPa (17.4.2.2 b)
    assert crt.fywd_kncm2(600.0, estribo=False) == pytest.approx(
        nbr.mpa_para_kncm2(min(0.7 * nbr.fyd(600.0), 435.0)), rel=1e-12)


def test_crt01_reproducao_modelo_I_C70():
    """achados_brutos CRT-01: VSd=200, bw=20, d=50, fck=70 -> Vc0=138,31 kN
    e Asw=3,153 cm2/m (a fórmula antiga, só Grupo I, dava 152,86 e 2,409)."""
    r = crt.modelo_calculo_I(VSd_kn=200.0, bw_cm=20.0, d_cm=50.0, fck_mpa=70.0)
    assert r.Vc == pytest.approx(138.31, abs=0.02)
    assert r.Asw_m == pytest.approx(3.153, abs=0.005)


# ---------------------------------------------------------------------------
# CRT-02 - laje_sem_armadura usa nbr.tau_Rd (teto de fck = 60 MPa, 19.4.1)
# ---------------------------------------------------------------------------
def test_crt02_reproducao_laje_C90():
    """achados_brutos CRT-02: VSd=100, bw=100, d=20, fck=90, rho_l=0,01 ->
    VRd1=243,87 kN (sem o teto de 60 MPa dava 337,39 kN, contra a segurança)."""
    r = crt.laje_sem_armadura(VSd_kn=100.0, bw_cm=100.0, d_cm=20.0,
                              fck_mpa=90.0, rho_l=0.01)
    assert r["VRd1_kN"] == pytest.approx(243.87, abs=0.02)
    assert r["tau_Rd_kNcm2"] == pytest.approx(
        nbr.mpa_para_kncm2(nbr.tau_Rd(90.0)), rel=1e-9)


@pytest.mark.parametrize("fck", [25.0, 60.0])
def test_crt02_tau_Rd_nao_muda_ate_C60(fck):
    """Até fck=60 o teto não interfere: tau_Rd(fck) = 0,25*fctd(fck)."""
    r = crt.laje_sem_armadura(VSd_kn=15.0, bw_cm=100.0, d_cm=10.0, fck_mpa=fck)
    assert r["tau_Rd_kNcm2"] == pytest.approx(
        nbr.mpa_para_kncm2(0.25 * nbr.fctd(fck)), rel=1e-9)


def test_crt02_rho_l_continua_limitado_a_002():
    r = crt.laje_sem_armadura(VSd_kn=15.0, bw_cm=100.0, d_cm=10.0,
                              fck_mpa=25.0, rho_l=0.05)
    assert r["rho_l"] == pytest.approx(0.02)


# ---------------------------------------------------------------------------
# CRT-03 - modelo_calculo_I valida 45° <= alfa <= 90° (17.4.1.1.5)
# ---------------------------------------------------------------------------
def test_crt03_reproducao_modelo_I_rejeita_alfa_fora_da_faixa():
    """achados_brutos CRT-03 (número corrigido pela verificação): o Modelo I
    não validava alfa; a=30° só é válido no Modelo II. Agora levanta erro."""
    with pytest.raises(ValueError):
        crt.modelo_calculo_I(VSd_kn=150.0, bw_cm=20.0, d_cm=40.0,
                             fck_mpa=25.0, alfa_deg=30.0)


@pytest.mark.parametrize("alfa", [45.0, 90.0])
def test_crt03_modelo_I_aceita_limites_da_faixa(alfa):
    r = crt.modelo_calculo_I(VSd_kn=150.0, bw_cm=20.0, d_cm=40.0,
                             fck_mpa=25.0, alfa_deg=alfa)
    assert math.isfinite(r.Asw_m)


# ---------------------------------------------------------------------------
# CRT-04 - fct,m da torção também passa a vir do núcleo
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fck", FCKS_GRUPO_I_E_II)
def test_crt04_fctm_torcao_delega_nucleo(fck):
    assert trc.fctm_mpa(fck) == pytest.approx(nbr.fct_m(fck), rel=1e-12)


def test_crt04_fywd_torcao_delega_nucleo():
    assert trc.fywd_kncm2(500.0) == pytest.approx(
        nbr.mpa_para_kncm2(min(nbr.fyd(500.0), 435.0)), rel=1e-12)


# ---------------------------------------------------------------------------
# CRT-05 - fywk <= 500 MPa só nos mínimos de torção (17.5.1.2)
# ---------------------------------------------------------------------------
def test_crt05_reproducao_asw_min_torcao_CA60():
    """achados_brutos CRT-05: bw=30, C25, CA-60 -> 3,078 cm2/m (sem o teto
    de fywk dava 2,565, -16,7 %)."""
    asw_min = trc.Asw_min_cm2_por_m(bw_cm=30.0, fck_mpa=25.0, fywk_mpa=600.0)
    assert asw_min == pytest.approx(3.078, abs=0.005)


def test_crt05_as_long_min_torcao_tambem_limita_fywk():
    capado = trc.As_long_min_cm2_por_m(he_cm=10.0, fck_mpa=25.0, fywk_mpa=600.0)
    sem_teto = 20.0 * (nbr.fct_m(25.0) * 0.1) * 10.0 / (600.0 * 0.1)
    com_teto_500 = 20.0 * (nbr.fct_m(25.0) * 0.1) * 10.0 / (500.0 * 0.1)
    # capar fywk em 500 (< 600) reduz o denominador -> aumenta o mínimo
    assert capado > sem_teto
    assert capado == pytest.approx(com_teto_500, rel=1e-9)


def test_crt05_cortante_nao_tem_teto_de_fywk():
    """Dúvida do achado, confirmada pela lente NORMA: 17.4.1.1.1 (cortante)
    não traz o teto de 500 MPa que 17.5.1.2 (torção) traz - o Asw,min do
    cortante deve continuar usando fywk cru."""
    com_ca60 = crt.asw_min_cm2_por_m(bw_cm=30.0, fck_mpa=25.0, fywk_mpa=600.0)
    assert com_ca60 == pytest.approx(2.565, abs=0.005)   # não 3,078


# ---------------------------------------------------------------------------
# CRT-06 - seção vazada equivalente quando A/u < 2*c1 (17.5.1.4.1)
# ---------------------------------------------------------------------------
def test_crt06_reproducao_secao_esbelta():
    """achados_brutos CRT-06: bw=h=15, c1=4,125 -> he=3,75 cm. O código
    antigo adotava he=8,25 (o he_min); a norma manda he=A/u nesse regime,
    com Ae/ue pelos eixos das barras de canto: (bw-2c1)x(h-2c1)."""
    sec = trc.secao_vazada_retangular(15.0, 15.0, 4.125)
    assert sec["caso_esbelto"] is True
    assert sec["he_cm"] == pytest.approx(3.75, abs=0.01)
    assert sec["Ae_cm2"] == pytest.approx(45.5625, abs=0.01)
    assert sec["ue_cm"] == pytest.approx(27.0, abs=0.01)


def test_crt06_caso_normal_nao_regride():
    """Apostila 14.3.6 (bw=35, h=50, c1=4,125): A/u=10,29 >= 2c1=8,25, fora
    do regime esbelto; Ae/ue continuam pela fórmula genérica (bw-he)(h-he)."""
    sec = trc.secao_vazada_retangular(35.0, 50.0, 4.125, he_adotado_cm=10.0)
    assert sec["caso_esbelto"] is False
    assert sec["Ae_cm2"] == pytest.approx(1000.0, abs=0.5)
    assert sec["ue_cm"] == pytest.approx(130.0, abs=0.5)


def test_crt06_dimensionar_torcao_com_secao_esbelta_nao_quebra():
    r = trc.dimensionar_torcao(TSd_kncm=250.0, bw_cm=15.0, h_cm=15.0,
                               c1_cm=4.125, fck_mpa=25.0, fywk_mpa=500.0)
    assert r.he == pytest.approx(3.75, abs=0.01)
    assert r.Ae == pytest.approx(45.5625, abs=0.01)
    assert math.isfinite(r.Asw_m) and r.Asw_m > 0.0


# ---------------------------------------------------------------------------
# CRT-07 - 30° <= theta <= 45° nas funções de torção (17.5.1.1)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fn, kwargs", [
    (trc.TRd2_kncm,
     dict(fck_mpa=25.0, Ae_cm2=1000.0, he_cm=10.0, theta_deg=15.0)),
    (trc.Asw_torcao_cm2_por_m,
     dict(TSd_kncm=6808.0, Ae_cm2=1000.0, theta_deg=15.0)),
    (trc.As_long_torcao_cm2_por_m,
     dict(TSd_kncm=6808.0, Ae_cm2=1000.0, theta_deg=15.0)),
])
def test_crt07_reproducao_theta_fora_da_faixa(fn, kwargs):
    """achados_brutos CRT-07: theta=15° dava Asw=0,924 cm2/m contra 1,992
    (theta=30°, -53,6 %) sem nenhum aviso. Agora levanta ValueError."""
    with pytest.raises(ValueError):
        fn(**kwargs)


def test_crt07_dimensionar_torcao_propaga_validacao():
    with pytest.raises(ValueError):
        trc.dimensionar_torcao(TSd_kncm=6808.0, bw_cm=35.0, h_cm=50.0,
                               c1_cm=4.125, fck_mpa=25.0, theta_deg=15.0)


@pytest.mark.parametrize("theta", [30.0, 45.0])
def test_crt07_aceita_limites_da_faixa(theta):
    TRd = trc.TRd2_kncm(fck_mpa=25.0, Ae_cm2=1000.0, he_cm=10.0,
                        theta_deg=theta)
    assert math.isfinite(TRd)


# ---------------------------------------------------------------------------
# CRT-08 - equações simplificadas usam o fct,m certo (Grupo I e II)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fck", [30.0, 50.0, 70.0, 90.0])
def test_crt08_simplificada_bate_teorica_dentro_da_aproximacao(fck):
    """achados_brutos/consolidação CRT-08: VSd=250, bw=20, d=50. Antes da
    correção a simplificada divergia -13,5 % em C70 e zerava em C90 (VSd <
    VSd,min); trocando fck^(2/3) por nucleo_nbr6118.fct_m(fck)/0.3 (o
    "fck^(2/3) equivalente"), a divergência volta à faixa da própria
    aproximação da apostila (< 1 %) em qualquer fck, igual a C30/C50."""
    simpl = crt.simplificada_modelo_I(VSd_kn=250.0, bw_cm=20.0, d_cm=50.0,
                                      fck_mpa=fck)
    teorica = crt.modelo_calculo_I(VSd_kn=250.0, bw_cm=20.0, d_cm=50.0,
                                   fck_mpa=fck)
    assert simpl.Asw_m == pytest.approx(teorica.Asw_m, rel=0.01)


def test_crt08_C90_nao_zera_mais():
    """Com a fórmula antiga, VSd,min(C90)=275,1 kN > VSd=250 kN fazia a
    função devolver Asw=0 (só o mínimo); corrigido, VSd,min cai para
    ~230,4 kN e a armadura calculada passa a ser usada."""
    r = crt.simplificada_modelo_I(VSd_kn=250.0, bw_cm=20.0, d_cm=50.0,
                                  fck_mpa=90.0)
    assert r.Asw_m == pytest.approx(5.015, abs=0.01)
    assert r.Asw_m > 0.0


@pytest.mark.parametrize("fck", [30.0, 50.0])
def test_crt08_identico_ate_c50(fck):
    """Para fck <= 50, fct_m(fck)/0.3 == fck**(2/3) exatamente (Grupo I,
    já que fct_m = 0,3*fck^(2/3) nessa faixa): a correção não muda nada
    até C50, só acima."""
    assert nbr.fct_m(fck) / 0.3 == pytest.approx(fck ** (2.0 / 3.0), rel=1e-12)
